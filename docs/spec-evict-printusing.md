<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# Spec — evict the PRINT USING render engine to the sub-ROM

Status: **SIGNED OFF 2026-07-18** (user, this session; user implements directly). The first eviction commissioned directly to free
main-window space (staging B of the signed-off [decision-phase3-space-strategy.md](decision-phase3-space-strategy.md)).
Its purpose is to unblock **error-handling S2a** (needs ~230 B of slot-0 window; measured
overrun ~143 B low + ~85 B page-1 over the current 3 B / 5 B free — see
[spec-basic-error-handling-s2a-packet.md](spec-basic-error-handling-s2a-packet.md) and the
`wip/s2a-mechanism` branch), and to prove the durable eviction mechanism the rest of Phase 3
needs. Repack-only; lean 16 KB `basic.rom` stays byte-identical.

## 0. AS-BUILT (2026-07-18) — the lower-risk 2-leaf cut, not the full render-move

The design §3 below planned to move the whole render engine (incl. the number/string
render halves + `pu_fmt_int`/`INT2DEC`) for ~347 B. **As built, only the two PURE format
scanners `pu_to_field` + `pu_emit_tail` were evicted** (RAM + `pchar` only — no `eval`, no
`pu_deref_body`, no `div10`), leaving the recently-fragile value-render/deref paths
(`pu_do_number`/`pu_do_string`/`pu_fmt_int`, incl. the 003ff70 fix) **100 % resident and
untouched**. The value renders stay main-side and stream directly via `pchar`, so ordering
is preserved: a `TOFIELD`/`TAIL` op renders leading/trailing literals into `DETOKBUF`, the
resident stub drains it (honouring PRDEST), then the value render emits directly — in order.

Deliberate deviation vs §3/§5, in the spirit of §7's "load-bearing differential risk":
much lower regression risk on the paths that have bitten us ~12×, at a smaller yield.

**Measured yield: page-1 5 B → 222 B (freed 217 B)**; low region unchanged (3 B). Sufficient
for S2a's ~85 B page-1 need directly, and its other content homes in the freed page-1 (the
`wip/s2a-mechanism` "~143 B low" figure was pre-string-dedup). If S2b overruns, `format.asm`
is the recorded second-tier reserve (§1). Files: `basic/pu-render.inc` (shared body),
`sub/printusing.asm` (tenant, indices 6/7, reuses `sub/detok.asm`'s `pchar`),
`basic/printusing.asm` (repack stubs / lean include), `sub/sub.asm` + both `SUBROM_IDX_*`
copies + Makefile `SUB_PARTS`.

**Gates (all green except a pre-existing, non-eviction failure):** lean `basic.rom`
byte-identical; `check_reloc`/`check_kwtable_identity`/`check_resident_abi`/
`check_tenant_closure` OK + manual page-0 closure audit (tenant → `pu_to_field`/`pu_emit_tail`
→ `pchar`, all sub-local); `unit-test` 46/46; PRINT USING **screen** differential byte-identical
to VG-8020; PRINT# USING **file** differential byte-identical to CF-3300 (guards 003ff70 +
PRDEST); `string`/`input`/`float`/`math`-acceptance ALL PASS; `array-acceptance` 150/150;
`diskbasic-acceptance` 34 lean + 34 repack. **`repack-boot` "live PRINT 12+34" FAILS, but
PRE-EXISTING** — it fails identically on clean `main` (cold-boot title passes; the ROM boots
and every other BASIC gate runs PRINT fine); a matrix-typing timing issue in that gate on
this host, unrelated to the eviction. Follow-up DONE (commit 2838ea5):
`check_tenant_closure.py --page0` now mechanically audits page-0 tenants (no
low-region/BIOS/sub-page-1 escape), wired into `subrom-closure-check` +
`basic-reloc` — the tenant's manual audit is now gated (§7 note resolved).

## 1. Why PRINT USING (the audit result)

A full leaf-audit (§8d visibility rules) of every plausible main-window eviction candidate:

| Module | Size | Verdict |
|---|---|---|
| **printusing.asm** | 676 B | **CHOSEN** — shape-C split, ~347 B page-1 yield (see §3) |
| format.asm | 377 B | second-tier reserve (~150–200 B via RAM sector-image build; touches oracle-validated FAT) |
| screen.asm | 251 B | DISQUALIFIED — 5 direct BIOS calls + eval/exec interleaved → ~0 B carvable |
| list.asm | 102 B | DISQUALIFIED — detok already evicted; remnant is dispatch + `ln_div_entry` (program.asm's error printer needs it resident) |
| float.asm | 483 B | DISQUALIFIED — hot shared service (`flt_int_result`/`flt_to_int16` per-conversion); §8d keeps services resident |
| input.asm | 465 B | DISQUALIFIED — interactive I/O (CHGET is ISR-fed; ISR paged out under a DI page-0 tenant) |
| bload/cload/save/files/field | 588–1894 B | DISQUALIFIED this round — funnel through shared fat.asm (CALSLT/DSKIO) |

PRINT USING is cold (only the `PRINT USING` statement + STR$'s integer formatter), and its
render leaves are pure text-formatting — the exact profile the proven `detok.asm` eviction
already fits.

## 2. Visibility contract (the §8d rule this obeys)

The tenant lands on **sub page-0** (`SUBROM_ENTRY_BASE_P0`). A page-0 tenant sees main
**page-1** + RAM, but NOT the low region (`$2812–$3FFF`) and NOT the BIOS/ISR. So every
routine the tenant calls must be sub-local, RAM, or a page-1 main routine whose *transitive*
closure never dips below `$4000`. The render leaves qualify because their only external needs
are `pchar`→(becomes a buffer append) and `div10`@$32CA (LOW) → the **sub-local div10 clone**
already in [sub/detok.asm:82](../sub/detok.asm).

## 3. The cut (measured spans from build/basic-reloc.sym)

**Design = the detok pattern:** the tenant renders into a RAM buffer; main drains it via
`print_string`→`pchar`, honouring PRDEST — so the **PRINT# USING file form is byte-for-byte
untouched** (the 003ff70 format-copy fix and its PRDEST routing stay main-side verbatim).

### Stays main (page-1) — the eval/parse/loop heads + the STR$ path
- `ex_print_using` head: `str_eval`, the format-string copy via `pu_deref_body`, the `pu_main`
  loop (`skip_spaces` / separators / `exec_stmt` / `stmt_error`), and the `eval`/`str_eval`
  call heads of `pu_do_number`/`pu_do_string`. These touch page-1/low services (eval, the
  format copy) and MUST stay resident.
- **`pu_fmt_int` stays resident** (~58 B). STR$ ([str-engine.asm:629](../basic/str-engine.asm))
  keeps calling it directly — the string path is entirely unchanged (zero risk to
  string-acceptance). The tenant does NOT call this resident copy (it would drag in the
  resident `div10`@LOW, invisible to page-0); the tenant renders integers with its own
  sub-local `INT2DEC` over the sub `div10` clone.

### Moves to the sub-ROM (page-0 tenant `pu_engine`, ~470 B measured)
`pu_has_field` (33) + `pu_to_field`/`ptf_*` (214) + `pu_emit_tail` (41) + `pu_do_number`
render half (~34) + `pu_emit_str0` (9) + `pu_do_string` render half (~81) + a sub-local
`INT2DEC` digit renderer (~58, over the sub `div10` clone). Every `call pchar` in the moved
code becomes a sub-local DETOKBUF append (size-neutral).

### New main-side glue (~65 B est.)
One shared `pu_call` stub (marshal op + args to RAM, `call subrom_call`, `jp c,
subrom_absent_error`, drain DETOKBUF via `print_string`) + 5-byte per-op call sites.

## 4. ABI

- **Entry:** append `jp pu_engine` as **`SUBROM_IDX_PU` = 6** on `SUBROM_ENTRY_BASE_P0`
  (indices 0–5 taken: PING/TOKENISE/DETOK/INTTEST/ARY/STRHEAP — append-only, never reorder).
- **Dispatch:** `IX = SUBROM_ENTRY_BASE_P0 + 3*6`; one entry, **op selector in RAM** (`PU_OP`,
  a new 1-byte sysvar — A is not CALSLT-safe, the math-pack lesson). Args/results in RAM
  (existing PU_* sysvars: PU_TYPE/PU_W/PU_POS/PU_FLAGS; the value for INT2DEC in a 2-byte RAM
  arg; string body ptr+len in RAM — main derefs STRPTR *before* the call so the tenant needs
  no `pu_deref_body` clone).
- **Ops:** `TOFIELD` (scan format literals→DETOKBUF, set PU_TYPE/PU_W/PU_POS/PU_FLAGS),
  `INT2DEC` (2-byte value→NUMBUF+len), `NUMFIELD` (padded / `%`-overflow render→DETOKBUF),
  `STRFIELD` (body ptr/len→DETOKBUF), `TAIL`.
- **Render buffer:** reuse **DETOKBUF** (`$BE00`, 512 B) — LIST and PRINT USING never nest
  within one statement; max render (a 255-B `&` field) fits. Its cursor is a RAM sysvar.
- **Absence:** `jp c, subrom_absent_error` (as detok) — reduced builds without the sub-ROM
  get the proper error.
- **DI:** short spans, no interrupt trampoline needed.

## 5. Space accounting

Movable measured 470 B; `pu_fmt_int` (58 B) stays; new glue ~65 B est. → **net page-1 yield
≈ 347 B** (±60 B on the glue estimate; the 470 B movable is measured). Target was ≥300 B for
S2a + S2b margin. If S2b later overruns, format.asm (~150–200 B) is the recorded follow-up.
**Measure the real yield post-implementation** (`check_reloc.py`); the estimate runs ~1.4×.

## 6. Lean byte-identity

The moved body is kept inline under `IF ROM_BASE >= $4000` (the [list.asm:109](../basic/list.asm)
precedent — lean has no sub-ROM, so it keeps the resident PRINT USING). Every sub-side and
glue byte is repack-only. **Verify lean `build/basic.rom` SHA is unchanged** (shasum, not
assumed).

## 7. Definition of Done (gates)

- Add `sub/printusing.asm` to Makefile **`SUB_PARTS`** (the stale-tenant landmine
  [makefile-subparts-stale-tenant]); force-rebuild sub.rom.
- `make build/basic-reloc.rom` + `check_reloc.py` — re-measure both regions, record the yield.
- lean `build/basic.rom` shasum byte-identical.
- `check_tenant_closure.py` + `check_resident_abi.py`. **NOTE:** the closure tool today only
  audits page-1 tenants' "no page-1 escape"; for a page-0 tenant the rule is inverted (no
  LOW-region / no BIOS escape, page-1 OK). Either extend the tool with a page-0 mode
  (preferred — mechanical enforcement of the exact easy-to-violate rule) or do the manual
  page-0-direction closure audit arrays' resolver used, and record it.
- Rebuild+reinstall the IPS before machine probes ([ips-rebuild-after-basic-change]).
- **PRINT USING differential**: `probes/basic/basic_probe_printusing.py` (screen form) +
  `disk_probe_printusing_file.py` (file form vs the CF-3300 oracle — this is the one that
  guards the 003ff70 fix + PRDEST routing). Both must stay byte-identical to the oracle.
- `string-acceptance` (the STR$ integer path through the resident `pu_fmt_int`).
- Standing set: `unit-test`, `array-acceptance` (150), `input`/`float`/`math`-acceptance,
  `diskbasic-acceptance` (34 lean + 34 repack), `repack-boot`.
- The recurring lesson applies: a green assemble that was never RUN can be catastrophic — RUN
  the suites; the PRINT USING differential is the load-bearing empirical check here.

## 8. Clean-room

Original code; the moved bytes are ours (PRINT USING is zerobas-authored). The eviction is a
pure relocation of our own code into our own sub-ROM — no C-BIOS interaction, no reference
disassembly. The sub `div10` clone is the existing own-design one ([no-reference-rom-disasm]).
