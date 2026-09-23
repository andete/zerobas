# `DSKI$` / `DSKO$` — direct sector access (D-DSKIO)

Filed 2026-06-22 as *"NOT a clean sector ↔ string pair … obscure semantics …
blocked on three counts"*; ruled IN by Joost 2026-09-10 (*"DSKI$ DSKO$ should
also be implemented"*), TIER 1 (missing keywords). This spec is the black-box
model measured on the CF-3300 on 2026-09-11 and the design that fits it.

## 1. What the reference does (CF-3300, black box)

| row | program | face |
|---|---|---|
| `vp`  | `A$=DSKI$(0,0)`: `LEN(A$)`, the descriptor's address, 4 bytes there | `0  27471  119 103 111 34` |
| `dir` | `A$=DSKI$(0,7)`, same readout | `27471 wgo"` |
| `s2`  | `A$=DSKI$(0,0):B$=DSKI$(0,7)`, both addresses | `27471 27471 …` |
| `o2`  | `A$=DSKI$(0,0):DSKO$ 0,0` | `OK` |
| `o1`  | `DSKO$ 0` | `ERR 2` |
| `bad` | `A$=DSKI$(0,9999)` | `OK 0` |
| `drv` | `A$=DSKI$(1,0)` (single-drive machine) | `OK 0` |
| `dr3` | `A$=DSKI$(3,0)` | `ERR 62` (Bad drive name) |

1. **`DSKI$` evaluates to the empty string, and the string's descriptor points
   into ROM** (27471 = $6B4F, the same for every drive and sector; `PEEK`
   there reads main-ROM bytes). The old filing's *"does NOT return the sector
   as the string value"* was right; *"data goes to a system buffer, accessed
   elsewhere"* is now measured rather than suspected:
2. **The sector lands in the disk ROM's sector buffer, whose address is the
   word at `$F351`.** Measured by a Tcl write-watchpoint RAM dump around the
   calls (`scratchpad/dskio_scout.py`): after `DSKI$(0,0)` the boot sector
   (`EB FE 90 "ZEROBAS "`) sits at **$EB95**, after `DSKI$(0,7)` the root
   directory (`TEST    BIN`) does; and `$F351` holds `95 EB`. That is the MSX
   idiom `A=PEEK(&HF351)+256*PEEK(&HF352)`, measured here rather than
   remembered. (`$F34D` → $EF95, `$F34F` → $ED95, `$F353` → $DE90 are the
   ROM's other work pointers; only `$F351` is the one `DSKI$` fills.)
3. **`DSKO$ d,s` writes that same buffer to sector `s`.** `DSKI$(0,7)`, then
   `POKE &HEB95,ASC("X")`, then `DSKO$ 0,7`: `FILES` lists `XEST    .BIN` and
   the private image's sector 7 begins `XEST    BIN` on disk.
4. `DSKO$` is a **statement only** (`A$=DSKO$(0,0)` is `Syntax error`,
   D-KWREST); `DSKI$` a **function only** (`DSKI$ 0,0` in statement position is
   ERR 2 on the VG-8020 too).
5. Out-of-range sector 9999 and drive 1 (B: on a one-drive machine) are
   accepted silently; drive 3 is `ERR 62`. These are TIER 3/5 faces; the
   happy path is rows `vp`/`dir`/`o2`.

## 2. Diskless (VG-8020)

| row | program | face |
|---|---|---|
| `vi`  | `A$=DSKI$(0,0)` | `ERR 5` |
| `vo`  | `DSKO$ 0,0` | `ERR 5` |
| `vi1` | `A$=DSKI$(0)` | `ERR 5` |
| `vo1` | `DSKO$ 0` | `ERR 5` |
| `vis` | `DSKI$ 0,0` (statement position) | `ERR 2` |

Same class as `ATTR$`/`CMD`/`SET`/`IPL`: **the handler refuses on sight**, before
any argument is parsed (`DSKO$ 0` is ERR 5 here and ERR 2 with a disk ROM). So
the hook gate comes BEFORE the parse, on both keywords.

## 3. Design

* Tokens (oracle crunch, D-KWREST): `DSKI$` = `$FF $EA` (function),
  `DSKO$` = `$D1` (statement). `kwtable.inc` rows after `DSKF`; neither is a
  prefix of a longer word. Re-pin `check_kwtable_identity.py`.
* Hook cells: `H_DSKO` = `$FDF4`, `H_DSKI` = `$FE17` (the standard MSX slots;
  unused here until now), claimed by `disk/kernel.asm`'s `hook_tab` with
  `hk_present`, like `H_DSKF`/`H_NAME`/`H_KILL`.
* Buffer pointer: `DSKBUF_PTR equ $F351` (word), set once at disk-ROM init to
  **`FWBUF`** ($E7C0), our directory/raw metadata sector buffer. It named
  `FSECTOR_BUF` until 2026-09-23; that is the open channel's staged *data*
  sector, and sharing it meant `DSKO$ 0,0` with a file open wrote the file's
  records over sector 0 (D-ALIASWCELL). The reference answers the same cell with
  `$EB95`, its directory/raw buffer, disjoint from its file-data buffer at
  `$ED95` — so this is its geometry, not a workaround. Nothing pins the value:
  every probe reads the buffer *through* the pointer.
  to `FSECTOR_BUF` ($E5C0). The band `$F34D..$F358` was ASKED of the zerobas
  machine (planted pattern, disk workload incl. two channels, KILL, FILES,
  DSKF, strings, DEF FN — all 12 bytes survived); it is outside the sysvar
  sweep's `$F380..$FFFE` denominator.
* Parse (main page 1, shared): `dsk_core` — store the tenant op, gate on the
  hook (ERR 5 unclaimed), `drive` via `eval_byte_arg`, `,`, `sector` via
  `eval_int16_checked` into `FWR_DIRSEC` (a sector-number word the dirverb
  tenant already owns for `NAME`), then `dirverb_op`; `DISKOP_STATUS` ≠ 0 →
  `load_error`.
* Bodies (sub page 1, `dirverb_tenant` ops 4/5): `ld de,(FWR_DIRSEC)`,
  `ld hl,(DSKBUF_PTR)`, `read_sector` / `fatprim_write_sector`, CF → STATUS.
* `DSKI$` returns the empty string via `STRSCR` length 0 → `str_mkf_desc`.
* Nodisk rows for `nodisk-acceptance`: `k.dski` `PRINT LEN(DSKI$(0,0))` and
  `h.dsko` `DSKO$ 0,0`, both `ERR 5` on VG-8020 and zb-nodisk.

## 4. Gate

`probes/disk/diskbasic_probe_dskio.py` (`make dskio-acceptance`): rows `vp`
(LEN=0), `dir` (after `DSKI$(0,7)`, `PEEK` the buffer through `$F351` and read
`TEST    BIN`), `boot` (after `DSKI$(0,0)`, `ZEROBAS ` at +3), `o2` (POKE the
buffer, `DSKO$ 0,7`, `FILES` shows `XEST`), `o1` (ERR 2), each on a private
copy of `disk/test720.dsk`; survey column cf3300. The buffer ADDRESS differs
between machines by design ($EB95 vs $E5C0) — the gate reads it through the
pointer, never a literal.

## 5. Measured after shipping (2026-09-11)

* The gate converges on both machines: `len` 0 / `dir` `TESTBIN` / `boot`
  `235 254 144 ZERO` / `dsko` OK with `XEST    BIN` read back from sector 7 of
  the private image / `o1` ERR 2.
* `DSKO$ 0,0;` (a trailing `;`) is `ERR 2` on the CF-3300 as well — which is
  what `nodisk-acceptance`'s zb-disk column shows for `h.dsko`, since that
  harness appends `;` to every statement. Not a divergence.
* **No disk in the drive (D-DSKNODISK, TIER 3):** the CF-3300 answers
  **`ERR 70`** (Disk offline) to `A$=DSKI$(0,0)` and to `DSKO$ 0,0`. Here
  `DSKI$` raises ERR 2 — `dsk_core`'s `load_error` exit, taken inside an
  expression, sets ERRMARK and the statement reports a Syntax error — and
  `DSKO$` raises nothing (the write's DSKIO failure is not reported). The
  nodisk harness mounts no image on its zb-disk side, which is why its
  `k.dski` column reads ERR 2 there; that column is not gated. Filed in
  TODO.md; the fix is the ERR 70 extension Joost ruled to add.
