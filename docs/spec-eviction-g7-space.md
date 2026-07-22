# Spec — the G7 eviction: funding the sprite statements' resident half

**Status: LANDED (2026-07-22).** Commits `f6a578a` (carve 1) and `8cc45d2`
(carve 2 + G7 switch-on). The fourth eviction of the graphics arc, after G4's
(`fat_rand_*` + line editor, +769 B), G5's (`cas_open_match`, +144 B) and G6's
(DEFtype, +115 B).

---

## 1. The measured deficit

G6 left **45 B** of page-1 tail. G7's resident half —
`SPRITE$(n)=` / `A$=SPRITE$(n)` / `PUT SPRITE` / `SPRITE ON|OFF|STOP` plus
`SCREEN`'s sprite-size argument — measured **433 B** with both halves written
and the tenant already carrying everything downstream of the evaluated values
(§8 of [spec-basic-graphics-g7.md](spec-basic-graphics-g7.md)). A first cut with
the table arithmetic and the merge resident measured 483 B.

**Deficit: 388 B** (`__MEAS_PAGE1_END` $7FD3 → $8184).

## 2. Why it took more than one carve

`scratchpad/g6_carve_scout.py` on the clean build finds **no single clean carve**
anywhere near 388 B. The largest single-entry, page-0-CLEAN carves are
`read_one_value` 168 B, `fia_walked` 146 B, `ds_lp` 125 B, `do_kill` 124 B. The
big ones that exist (`if_then` 157 B, `var_name_key` 138 B) are on hot paths — a
CALSLT per `IF` or per variable reference is not a trade worth making — and
everything above ~200 B either straddles (`reaches subrom_call`) or explodes its
closure through `eval`.

⚠️ **Scout caveat learned here:** run it on a build whose image actually FITS.
With the overrun image in place, symbols past $8000 are classified as page-0 and
the verdicts are quietly wrong.

The plan signed off was three carves (`read_one_value` + `fia_walked` +
`do_kill`, ~438 B). Two were enough: the scout under-counts a carve (it only sees
labels its call graph reaches, not fall-through-only blocks), and a further
tenant-side re-split closed the last 23 B.

## 3. Carve 1 — the READ/DATA value engine (+234 B)

`read_one_value` + `data_seek` + `data_parse_int` → **page-0 tenant
`SUBROM_IDX_READVAL` = 10** ([sub/readdata.asm](../sub/readdata.asm)).

- **Why it qualifies:** it walks tokenised program RAM (`DATAPTR`/`DATALINE`/
  `RESTORE_LINE`/`DATASTATE`) and parses ASCII. No `eval`, no float pack, no
  BIOS — the transitive test the G6 spec §8 writes down.
- **Warm, not hot:** one CALSLT per READ item, dominated by the variable store
  around it.
- **Marshalling:** `read_one_value`'s `(CF, DE)` contract cannot ride back
  through `subrom_call`, so the tenant lands it in `RDV_ST`/`RDV_VAL` and a 17 B
  resident stub rebuilds it.
- **Lean cart:** the body is [basic/readdata-body.inc](../basic/readdata-body.inc),
  included inline for `ROM_BASE >= $4000` — byte-identical, the casmatch pattern.
- **`tok_skip` is now shared:** [basic/tokskip-body.inc](../basic/tokskip-body.inc),
  included by the resident and by page 0's copy, so a token stride can never be
  right in one page and stale in the other (a float literal's `$00` mantissa byte
  read as a terminator is exactly the bug a DATA scanner would hide).
  `sub/lineedit.asm` keeps its page-1 copy under `le_` labels — page 0 and page 1
  are never mapped together, so each page needs one.
- Measured `__MEAS_PAGE1_END` $7FD3 → **$7EE9**.

## 4. Carve 2 — `fat_io_append`'s resume-point tail (+131 B)

`fia_walked` … `fia_bytes_m1` → **fatprim-tenant row
`DISKOP_SEL_FIA_WALKED` = 18** ([sub/fiawalk.asm](../sub/fiawalk.asm)); no new
tenant index, the G4 `fat_rand_*` pattern.

- **Why it qualifies:** it is pure arithmetic over `FAT_*`/`FWR_*` and
  `FSECTOR_BUF` and **calls nothing at all**; every path returns `Cy = 0`, so the
  resident shim needs no status marshalling.
- Body shared verbatim with the lean cart:
  [basic/fiawalked-body.inc](../basic/fiawalked-body.inc).
- Measured $7EE9 → **$7E66** (410 B free).

## 5. The last 23 B — a tenant-side re-split, not a third carve

With 410 B free and a 433 B resident half, two moves closed the gap instead of
carving `do_kill`:

- `SPRITE$(n)=` hands the tenant the **string descriptor** (`GFX_SDESC`) instead
  of staging the bytes resident: the copy, the truncate and the zero-pad all
  happen in the tenant, which can read page-3 RAM perfectly well.
- The VDP **register-1 write** for `SCREEN`'s sprite size becomes tenant op 12
  (a direct port pair + the `RG1SAV` mirror update) instead of a resident
  `WRTVDP` call — the page-0 island owns the ports, and a page-0 tenant has no
  BIOS anyway.

Final image ends **$7FF7 — 9 B of page-1 tail free.**

## 6. What the gates said

`graphics-acceptance` PASS (Phases A–P, including G7's new N/O/P);
`graphics-floor-acceptance` PASS and `graphics-floor-teeth` PASS (after the
wiring fix, §7); `unit-test` 51/51; `diskbasic-acceptance` 34/34;
`bdos-acceptance` 12/12; lean cart byte-identical (`e22d8c5f…`). READ/DATA was
additionally spot-differentialled against the reference (values, `RESTORE`,
out-of-data, `&H`, negative, float-literal-in-program) before the G7 work
resumed.

## 7. Two harness findings this eviction produced

1. **`gfx_vram_rd` had no fetch-window settle.** The G2 lesson
   ([memory: vdp-direct-port-read-fetch-window]) had been applied only to
   `gfx_rd_raw`; the G1 di-guarded primitive never got it, and G7's block reads
   are the first code to use it in anger — a 4-byte attribute read came back
   ROTATED. The NOPs are now part of "the guard" (stripped by `GFX_UNGUARDED`),
   which exposed the deeper point: **with the settle present and only the DI
   stripped, the floor gate no longer fails** — so what the G1 teeth check was
   really detecting all along was the missing fetch window, not the latch race.
2. **`make graphics-floor-teeth` never actually ran unguarded.** It exported
   `ZB_GFX_UNGUARDED=1`, which nothing read, so it tested the ordinary guarded
   ROM and could only ever report FAIL. It now builds and installs an unguarded
   `sub.rom`, runs the probe, and restores the real machine — and passes.
