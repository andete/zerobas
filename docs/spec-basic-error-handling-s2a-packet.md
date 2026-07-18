# S2a implementation packet — dispatcher + ERR/ERL + ERROR n

**Status:** pinned & ready to implement (2026-07-18). This is the mechanical-implementation
elaboration of the SIGNED-OFF spec [spec-basic-error-handling-s2.md](spec-basic-error-handling-s2.md)
§8 slice **S2a**. All ABI is black-box-pinned; the design below resolves the §7 space
question empirically. Repack-only (every byte behind `IF ROM_BASE < $4000`); lean 16 KB
`basic.rom` stays byte-identical. Builds on S1 (`fre_abort_low` funnel + ` in <line>`).

**S2a scope (NO trapping — `ONELIN` stays 0):** the `raise_error` dispatcher, the RAM
cells, choice-B site-funnelling, the FPERR→ERR map, the `ERR`/`ERL` functions, `ERROR n`,
and the `ERROR`/`ERR`/`ERL` tokens. Behaviour-preserving for untrapped errors (S1 gates
stay green); independently testable via `ERROR n` + `PRINT ERR`/`ERL`. `ON ERROR`/`RESUME`/
the trap branch/`SAVSTK` are **S2b** — do NOT build them here.

---

## 1. Pinned tokens (black-box, `probes/basic/basic_probe_pin_errtokens.py`)

| keyword | token | kind | notes |
|---|---|---|---|
| `ERROR` | **$A6** | 1-byte statement token | same token in `ERROR n` and `ON ERROR GOTO` |
| `ERR`   | **$E2** | 1-byte value token (expr.asm) | `a=err` → `41 EF E2` |
| `ERL`   | **$E1** | 1-byte value token (expr.asm) | `a=erl` → `41 EF E1` |
| (`RESUME` = **$A7** — S2b only, do not add yet) | | | |

Cross-check: ON=$95/GOTO=$89/NEXT=$83 came back identical to the existing equs → method
validated. Add `ERROR_TOKEN=$A6`, `ERR_TOKEN=$E2`, `ERL_TOKEN=$E1` equs (basic/sysvars.inc,
next to ON_TOKEN).

**Kwtable ordering hazard (hard):** "ERR" is a prefix of "ERROR"; `match_kw` returns the
FIRST matching entry, so the kwtable entry for **`ERROR` MUST precede `ERR`** (else "ERROR"
crunches to ERR+"OR"). `ERL` has no prefix conflict. Add all three to the kwtable
(basic/kwtable.inc — the sub-side crunch/decrunch table; **mind SUB_PARTS staleness**
[makefile-subparts-stale-tenant], force-rebuild sub.rom). `ERR`/`ERL` are value tokens →
also need detokeniser entries; `ERROR` is a statement token.

---

## 2. ERR-code ABI (published MSX numbering, allowed-source L110)

Every error site / FPERR code maps to one MSX ERR code + its (lowercase house-style) message:

| ERR | message string | reached from |
|---|---|---|
| 1  | next without for      | err_nofor |
| 2  | syntax error          | err_syntax (×2 today), FPERR 4 |
| 3  | return without gosub  | err_noret |
| 4  | out of data           | err_data |
| 5  | illegal function call | err_illegal_fn, FPERR 3 & 8 |
| 6  | overflow              | err_overflow, FPERR 1 |
| 7  | out of memory         | err_mem / err_stack(=err_mem), FPERR 6 (`err_mem_arr` cap. — keep) |
| 8  | undefined line number | err_line |
| 9  | subscript out of range| FPERR 5 |
| 10 | redimensioned array   | FPERR 7 |
| 11 | division by zero      | FPERR 2 |
| 13 | type mismatch         | type_mismatch_error, FPERR 10 |
| 16 | string formula too complex | FPERR 9 |
| 17 | can't continue        | err_cont |
| 22 | (RESUME without error — S2b) | |
| 23 | unprintable error     | `ERROR n` with an out-of-table code |

Note the arrays arc deliberately kept **capitalised, reference-verbatim** array strings
(`err_mem_arr`, `err_illegal_fn_arr`, `err_subscript`, `err_redim`) distinct from the
lowercase shared strings (spec-basic-arrays §9.5). Those stay as-is — they are the *message*
for FPERR 5/6/7/8; the code→ERR map still yields 9/7/10/5. Do NOT merge the capitalised
array strings into the lowercase ones.

---

## 3. Design — choice B, self-funding via string dedup

The signed-off §9-Q1 decision is **B**: every site carries an ERR code and funnels through
`raise_error`, which is the single path. Concretely:

**(a) One code→message table replaces three things** — the per-site `ld hl,msg`, the FPERR
`fre_msgtab`, and the duplicate string bodies. Build `err_msgtab` indexed by ERR code
(1..N word entries; holes at 12/14/15/… → point at the code-23 "unprintable error"
string). Each ERR code's message is stored **once**; delete the now-duplicate bodies
("out of memory" ×3→×1, "syntax error" ×2→×1). The capitalised array strings stay separate
(their codes 9/7/10/5 index the table at their own entries).

**(b) Direct error sites** (program.asm/interp.asm, page-1): today `ld hl,msg` (3B) +
`jp fre_abort_low` (3B). Become `ld a,<code>` (2B) + `jp raise_error` (3B) → −1B each, and
the `ld hl,msg` disappears (raise_error derives it). ~9 sites.

**(c) FPERR sites:** `fp_runtime_error` already has FPERR in A. Replace its `fre_msgtab`
lookup with a small `fperr_to_err` map (FPERR 1..10 → ERR {6,11,5,2,9,7,10,5,16,13}), then
`jp raise_error`. This deletes `fre_msgtab` (20B) in favour of the 10-byte code map.

**(d) `raise_error`** (main-side — it is `jp`-reached and ends by `jp` into the low-region
abort body, so it CANNOT be a CALSLT tenant; place in the low region next to `fre_abort_low`):
```
raise_error:            ; in: A = MSX ERR code (1..23)
    ld   (ERRCODE),a
    call record_errline         ; §4
    ld   a,(ERRCODE)
    <index err_msgtab by A -> HL = message>   ; out-of-range -> code-23 string
    ; S2a: no handler check, no trap. Fall straight into the S1 abort body:
    jp   fre_abort_low          ; (or fall through if placed immediately above it)
```
(S2b inserts the `ONELIN`/trap decision between `record_errline` and the abort — leave a
clean seam. Do NOT add `SAVSTK` here in S2a; it is unused without a trap — deferring its
two writes saves 8 scarce bytes. Flag this as an intentional spec deviation vs §8's listing.)

**(e) `record_errline`** (pure-RAM leaf — reads CURLINE/DIRECTF, writes ERRLINE):
run mode (DIRECTF=0) → `ERRLINE := (CURLINE+2)`; direct mode → `ERRLINE := 65535`. ~15B.

**(f) `ERR` / `ERL`** (expr.asm value-token evaluators): `ERR` → widen `ERRCODE` (1 byte)
to the numeric FAC; `ERL` → `ERRLINE` (word) to FAC. Reuse the existing int→FAC path.

**(g) `ERROR n`** (statement, interp.asm switch): eval the arg → A; `jp raise_error`. An
out-of-table code still reaches raise_error and prints "unprintable error" (code 23) via the
table's hole handling — reference-faithful enough for S2a (exact echo-of-code is S2b polish).

---

## 4. New RAM cells (spec §4; pin exact addrs — measure the VARTAB window still clear)

| cell | size | proposed | set by |
|---|---|---|---|
| `ERRCODE` | 1 | $E1C5 | raise_error |
| `ERRLINE` | 2 | $E1C6 | record_errline |

(S2a needs only these two. `ONELIN`/`ONEFLG`/`ERRRESUME`/`SAVSTK` are S2b.)

> **CORRECTION (2026-07-18, adversarial verify pass).** The original text here said
> "Cold boot + `clear_vars` zero `ERRCODE`/`ERRLINE` … — reference." **The `clear_vars`
> part was empirically false.** Boot-per-case diff vs the VG-8020 reference
> (`ERROR 11 : NEW/CLEAR/RUN : PRINT ERR`) shows the reference **PRESERVES** `ERR`/`ERL`
> across `NEW`, `CLEAR`, and `RUN` — they hold the last raised error's code/line until the
> *next* error, and are zeroed **only at cold boot**. The implementation was corrected to
> zero them in `init` alone (the sole cold-only hook), not `clear_vars`. Cold boot still
> reads 0 (verified). Lesson (recurring): the packet asserted "reference" without an
> empirical capture; the green suite missed it because no case read `ERR` after
> `NEW`/`CLEAR`/`RUN`.

**Known S2a gap deferred to S2b (packet-sanctioned, §3(g)):** `ERROR 0` on the reference
raises `ERR 5` (illegal function call — arg 0 rejected), whereas S2a records code 0 and
prints "unprintable error". `ERROR n` for `n` in 1..255 matches the reference (raw code
held, incl. out-of-table `ERROR 200`→200, `ERROR 23`→23). The `ERROR 0` argument-validation
is S2b's ERROR-n-echo polish, consistent with §3(g)'s "reference-faithful enough for S2a."

---

## 5. Space plan (§7 discipline — measure, then tenant the spillover)

Reclaim (main): dup-string dedup (~44B) + per-site `ld hl,msg` removal (~27B) + `fre_msgtab`
removal (~20B) ≈ **~91B**. New cost: `err_msgtab` (~34–46B) + raise_error + record_errline +
`fperr_to_err` + ERR/ERL + ERROR n ≈ **~120B**. Estimated net ≈ **+30B main** — over the
3B low / 5B page-1 headroom. **Do NOT trust this estimate** (runs ~1.4×; [recurring D-2
lesson: measure per-region byte budgets empirically]). Procedure:
1. Implement (a)–(g) main-side, `make build/basic-reloc.rom`, read `__MEAS_LOW_END` /
   `__MEAS_PAGE1_END`.
2. If page-1 or low overruns: move the pure-RAM leaves to the sub-ROM per
   [subrom-tenant-playbook] shape A/C — **`record_errline`** (pure RAM) and the **ERR/ERL**
   FAC-return evaluators are the natural cuts; keep `raise_error` + the sites + `err_msgtab`
   main-side (they are `jp`-reached / main-data). Sub-ROM has ~10 KB free per page.
3. Re-measure; prove main fits and by how much; run `check_tenant_closure`/`check_resident_abi`
   if a tenant was added.

---

## 6. Definition of Done (gates — a green build that was NEVER RUN can be catastrophic)

Run ALL of these; do not declare done on a green assemble alone:
- `make unit-test`
- `make error-acceptance` — **S1 families A/B (untrapped abort + ` in <line>`) MUST be
  byte-unchanged** (S2a is behaviour-preserving for untrapped errors), PLUS new S2a cases:
  `ERROR 5` → `illegal function call`; `PRINT ERR` after a trapped-less error via `ERROR n`;
  `ERL` in run vs direct (65535). Extend `probes/basic/basic_probe_error*.py`.
- `make array-acceptance` (150), `input`/`string`/`float`/`math`-acceptance,
  `diskbasic-acceptance` (34 lean + 34 repack), the tape battery, `repack-boot`.
- **lean `basic.rom` SHA byte-identical** (shasum, don't assume) — every S2a byte is behind
  `IF ROM_BASE < $4000`.
- If a sub tenant was added: `check_tenant_closure` + `check_resident_abi` green; re-run the
  crunch gate (kwtable changed) and `basic_probe_pin_errtokens.py` (tokens land).

---

## 7. Clean-room

Original code. ERR-code numbering + statement/function semantics from the published
MSX-BASIC reference (L110, grade B). Token bytes black-box-pinned on the VG-8020
(`basic_probe_pin_errtokens.py`), no ROM disassembly [no-reference-rom-disasm]. The abort
transcripts are black-box behaviour captures.
