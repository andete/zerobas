# `PRINT# USING` file-form fix — LANDED 2026-07-18

Status: **LANDED.** One-line fix (repack-only): `pu_deref_body` preserves A across the
length→ldir-count window. All gates green; lean 16 KB `basic.rom` byte-identical.

The fix confirmed the root cause below exactly. Empirical verification: emit-time
`PU_FMTLEN` now 3 (was 255); `disk_probe_printusing_file.py` PASS (byte-identical to
CF-3300) 10/10 stable; `diskbasic-acceptance-repack` 34/34; lean disk 34/34;
`basic_probe_printusing.py` (screen) still green; unit 46/46; string / array (150) /
float / math / input / error acceptance all PASS. Actual fix was slightly different
from proposal step 1 (see "As landed" below): the corrupted quantity was **A (the copy
count)**, clobbered by `pu_deref_body`, not the descriptor length read.

## Problem

`PRINT# n, USING "fmt"; values…` — the file form of `PRINT USING` — is dispatched
by [basic/print.asm:143](../basic/print.asm) (the file-form item loop routes a
following `USING` token into `ex_print_using` with `PRDEST=1`), but the formatter's
format-string **copy step was never made file-form-safe**. The module header itself
records the file form as deferred ([basic/printusing.asm:25](../basic/printusing.asm)),
and [basic/PROVENANCE.md:1855](../basic/PROVENANCE.md) calls it "a later item." So
the dispatch is wired but the feature is unfinished, and it emits corruption.

`probes/disk/disk_probe_printusing_file.py` (in the `diskbasic-acceptance-repack`
gate, currently 33/34) correctly detects this. It is **not** a harness flake — two
earlier diagnoses (including mine) wrongly labelled it an injection race; the
empirical disproof is below.

## Observed behaviour (repack, C-BIOS_MSX1_EU_REPACK_DISK, black-box)

Program (direct mode, `a$="cat"`):

| statement | on-disk bytes | correct (CF-3300) |
| --- | --- | --- |
| `print#1,using"###";5` | `  5";\x16\x00 AS ` | `  5` |
| `print#1,using"[!]";a$` | `[c]";A$\x00AS ` | `[c]` |
| `print#1,using"## ";1;2;3` | (nothing) → **`syntax error`** | ` 1  2  3 ` |

The field itself is formatted correctly (`  5`, `[c]`); the corruption is trailing
residue emitted **after** the value. Plain `PRINT#1,"hello"`→file is correct, and
screen `PRINT USING` (incl. format-reuse `"## ";1;2;3`) is correct
(`basic_probe_printusing.py`, green). The National CF-3300 writes the byte-identical
correct file. So the defect is specific to zerobas's `PRINT# USING` **file form**.

## Root cause (empirically pinned, 2026-07-18)

RAM dump of `PU_FMT`/`PU_FMTLEN` (`$EED6`) right after `print#1,using"###";5`:

```
PU_FMT[0:16] = b'###";\x16\x00 AS #\x12\x00...'
```

The intended format `###` is followed by the tail of the **tokenised direct-line
buffer** (`";` … ` AS #1` is literally from the preceding `open"u.dat" ... as #1`
line). i.e. the format-string copy in `ex_print_using`
([basic/printusing.asm:50–67](../basic/printusing.asm)) reads a **wrong/oversized
length** and overruns `"###"` into adjacent buffer bytes.
`pu_emit_tail` ([basic/printusing.asm:207](../basic/printusing.asm)) then walks
`PU_FMT[PU_POS..PU_FMTLEN)` and streams that residue into the file — exactly the
`";\x16\x00 AS ` seen on disk.

Why the screen form is unaffected: the trigger is the file-form **entry preamble**.
Before `ex_print_using`, the file form runs `eval` (channel number) + `fch_valid` +
`fch_select` ([basic/print.asm:37–62](../basic/print.asm)); `fch_select` LDIRs a
channel context over the engine globals. This perturbs the temporary string
descriptor that `STRPTR` points at (a string **constant**'s descriptor is transient),
so the `ld a,(hl)` length read at [printusing.asm:51](../basic/printusing.asm)
picks up a stale/oversized length. The screen form has no such preamble.

**Empirical disproof of the "harness race" theory:** the probe was rewritten to
KEYBUF injection (omsx_repl, atomic lines) and the screen captured — the six source
lines echoed perfectly clean, yet the file was still corrupt and `syntax error`
still showed. Clean injection ⇒ the corruption is the ROM, not the harness.

## As landed

The during-emit watchpoint (not the earlier post-statement dump, which the REPL had
clobbered) pinned the corrupted quantity precisely: **not** the descriptor length read
(that was correctly 3), but **A, reused as the `ldir` copy count**. In `ex_print_using`
([basic/printusing.asm](../basic/printusing.asm)) the repack path is
`ld (PU_FMTLEN),a` → `call pu_deref_body` → (shared tail) `ld c,a` / `ld b,0` / `ldir`.
`pu_deref_body` ([basic/str-engine.asm](../basic/str-engine.asm)) did `ld a,(hl)` to
fetch the pointer-low byte, **clobbering A** — so `ld c,a` used the literal's address
low byte (here `$FF`) as the count. The `ldir` copied 255 bytes of token stream into
`PU_FMT`, overrunning `PU_FMT+32` (= `PU_FMTLEN`) and setting it to a garbage 255;
`pu_emit_tail` then streamed the residue. The lean path is `inc hl` (no A-clobber), so
lean was always correct. Screen `PRINT USING` escaped it only when the literal's address
low byte stayed ≤ ~32, so the overrun never reached `PU_FMTLEN` — luck, not correctness.

**Fix:** `pu_deref_body` now `push af`/`pop af` around its body, preserving every register
except HL. Repack-only, LOW region (+2 B, 22→20 B free; page-1 untouched at 2 B). This
also removes the latent overrun for every other `pu_deref_body` caller (print_strval,
LSET/RSET, CVI, string fields). The multi-value `syntax error` was indeed a downstream
consequence of the same overrun and disappeared with the fix (verified, not assumed).

Watchpoint evidence:
`FMTLEN pc=0x5447 val=0x03` (correct len write) → `FMT+4 pc=0x5457 val=0x3B` +
`FMTLEN pc=0x5457 val=0xFF` (the 255-byte `ldir` overrunning `PU_FMTLEN`).

**Gate (all green):** `disk_probe_printusing_file.py` PASS (byte-identical to CF-3300)
10/10; `basic_probe_printusing.py` green; `diskbasic-acceptance-repack` 34/34; lean disk
34/34; `tools/check_reloc.py` lean byte-identical; unit 46/46; string/array/float/math/
input/error acceptance all PASS.

## Scope / space

Repack-only. Space is likely neutral-to-small (the fix is a corrected length source,
not new strings), but measure `__MEAS_LOW_END`/`__MEAS_PAGE1_END` — page-1 has ~2 B
free after D-2. If it does not fit, the format-copy hardening is small enough to
self-fund or golf locally before considering a tenant.

## Documentation debt to correct alongside

- [../TODO.md:12036 (T-027472)](../TODO.md) lists `PRINT# USING` under a **DONE** umbrella — false;
  it is unfinished/broken. Correct to reflect the real state (see the interim
  doc-truth fix already applied).
- On landing: update [basic/printusing.asm:25–27](../basic/printusing.asm) and
  [basic/PROVENANCE.md:1855](../basic/PROVENANCE.md) from "deferred / later item" to
  implemented + gated.

## Clean-room

Original code; field semantics from the public MSX-BASIC reference; CF-3300 is the
black-box disk oracle only (byte comparison of the written file — no disassembly).
