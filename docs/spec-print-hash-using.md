# Spec (DRAFT — sign-off pending): `PRINT# USING` file-form fix

Status: **DRAFT / investigation complete, implementation NOT started.** Awaiting
sign-off before any ROM change. Repack-only (like every Phase-3 feature); lean
16 KB `basic.rom` stays byte-identical.

## Problem

`PRINT# n, USING "fmt"; values…` — the file form of `PRINT USING` — is dispatched
by [basic/print.asm:92](../basic/print.asm) (the file-form item loop routes a
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
`pu_emit_tail` ([basic/printusing.asm:319](../basic/printusing.asm)) then walks
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

## Proposed fix (to be validated during implementation)

1. **Make the format copy self-contained against the entry preamble.** Capture the
   format string's length + body pointer from the `str_eval` result *before* any
   step that can disturb the transient descriptor, or copy via an
   entry-preamble-independent length. The copy must never exceed the true format
   length. (Confirm the exact corrupted quantity — descriptor length byte vs
   `STRPTR` target — with a during-emit dump, not a post-statement one.)
2. Re-verify the `syntax error` on multi-value reuse disappears once the overrun is
   fixed (it is most likely a downstream consequence of the same overrun desyncing
   the value-list cursor — verify, don't assume).
3. **Gate:** `disk_probe_printusing_file.py` → PASS (file byte-identical to CF-3300),
   `basic_probe_printusing.py` still green, `make diskbasic-acceptance-repack` → 34/34,
   full lean byte-identity (`tools/check_reloc.py`), unit-tests green.

## Scope / space

Repack-only. Space is likely neutral-to-small (the fix is a corrected length source,
not new strings), but measure `__MEAS_LOW_END`/`__MEAS_PAGE1_END` — page-1 has ~2 B
free after D-2. If it does not fit, the format-copy hardening is small enough to
self-fund or golf locally before considering a tenant.

## Documentation debt to correct alongside

- [TODO.md:278](../TODO.md) lists `PRINT# USING` under a **DONE** umbrella — false;
  it is unfinished/broken. Correct to reflect the real state (see the interim
  doc-truth fix already applied).
- On landing: update [basic/printusing.asm:25–27](../basic/printusing.asm) and
  [basic/PROVENANCE.md:1855](../basic/PROVENANCE.md) from "deferred / later item" to
  implemented + gated.

## Clean-room

Original code; field semantics from the public MSX-BASIC reference; CF-3300 is the
black-box disk oracle only (byte comparison of the written file — no disassembly).
