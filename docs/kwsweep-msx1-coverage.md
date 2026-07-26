<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# MSX1 BASIC keyword-completeness sweep — the coverage denominator

**Status:** measured 2026-07-26 · probe
[`probes/basic/basic_probe_kwsweep.py`](../probes/basic/basic_probe_kwsweep.py) ·
reference Philips VG-8020 · zerobas `C-BIOS_MSX1_EU_REPACK_DISK` at
`zerobas-main-eu.rom=664f4898977d` (`sub.rom=e7bf1c86f40c`), `git=8d9bca1`

> The **ROM hash is the pin, not the git rev.** A parallel session was committing
> to this tree during the sweep (HEAD moved `f59a5c7`→`8d9bca1`), but the built
> ROMs were byte-identical before and after the run — the probe's own
> before/after fingerprint check confirms it, and aborts the report if they ever
> differ.

## Why this exists

zerobas found two missing keywords **by accident**, six days apart, and both had
the same silent shape — the word parses as an ordinary **variable**, so nothing
errors and the program simply computes the wrong answer:

* **`TIME`** — collateral from the T3 KEY slice (`20e04b4`). Parses as the
  variable `TI`, reads 0 forever, so `IF TIME-T<400 GOTO` never terminates.
* **`TAB(`** — found while auditing coverage for this sweep. Worse: it was
  recorded as *"Already faithful (NO work)"* in
  [`spec-basic-df2-2-intarg-coercion.md`](spec-basic-df2-2-intarg-coercion.md)
  §1.2, because `PRINT TAB(99999)` raises ERR 6 on **both** sides. It does so for
  structurally different reasons — zerobas has no `TAB(`, so `TAB` is an *array*
  and the subscript bound-check produces the same code. **The differential case
  passed; the feature does not exist.**

Two accidental finds is a pattern, not luck. This sweep measures the whole
reserved-word set at once so "complete MSX1 BASIC" has an honest denominator.

## Method — two layers, because one lies

| Layer | Question | How |
|---|---|---|
| **1 CRUNCH** | does zerobas *tokenise* the word? | store `1 <body>`, diff token bytes vs the VG-8020 |
| **2 SUPPORT** | does a *program* observe the right thing? | execute a usage where a variable/array parse gives a **visibly different** answer, compare outcome class |

Neither layer is sufficient alone, and the repo already owns both counter-examples:

* **`INTERVAL`** (the `60e0ab6` retraction) — absent from every MSX1 keyword
  table, because it is not a keyword at all but the compound `INT`+`"ER"`+`VAL`.
  It works. *Layer 1 alone would call it missing.*
* **`TAB(`** — identical error code on both sides. *Layer 2 alone, written
  carelessly, calls it present.*

Layer 2 rows are therefore designed against the failure mode: `PRINT TAB(99999)`
is the in-tree example of how **not** to write one. The probe keeps a deliberately
**WEAK** row (`time`, using `TIME>=T` → `0>=0` → true on a machine with no `TIME`
at all) as a standing demonstration that a passing differential proves nothing
unless the absent-feature parse answers *differently*. It is excluded from the
tally.

## Headline

Of **162** MSX1 reserved words swept: **123 tokenise**, **39 do not**. Of those 39,
**3 work anyway** (`DEFSNG`/`DEFDBL`/`DEFSTR` — no `kwtable.inc` entry by design,
they reach `ex_def_type` as `DEF_TOKEN` + literal ASCII) and **1 is `INTERVAL`**
(needs no token). **35 words are genuinely absent.**

### SILENT-GAP — zerobas answers, and the answer is wrong (9)

The worst class: no error, no diagnostic, just a wrong number. Every one of these
is a live `TIME`-shaped landmine in a user program today.

| word | reference | zerobas | absent-parse |
|---|---|---|---|
| `TAB(` | `[    X]` | `[ 0 X]` | array element |
| `SPC(` | `[     X]` | `[ 0 X]` | array element |
| `CSRLIN` | `[ 4 ]` | `[ 0 ]` | numeric var |
| `POS` | `[ 5 ]` | `[ 0 ]` | array element |
| `FRE` | `[-1 ]` | `[ 0 ]` | array element |
| `TIME` | `[-1 ]` | `[ 0 ]` | var `TI` (advances vs doesn't) |
| `EQV` | `[-7 ]` | `[ 5  0  3 ]` | var → three PRINT items |
| `IMP` | `[-5 ]` | `[ 5  0  3 ]` | var → three PRINT items |
| `BIN$` | `[101]` | `[]` | string array element |

`EQV`/`IMP` deserve a note: `PRINT 5 EQV 3` prints **three separate values**
because the operator is read as a variable between two literals. Nothing in the
language flags it.

### MISSING — zerobas raises a syntax error (6)

Honest failures. Visible, diagnosable, not silent: `LOCATE`, `SWAP`, `TRON`,
`TROFF`, `MOTOR`, `DEF FN`/`FN`.

### NO-ORACLE — not answered by this run (5)

`MKI$` `MKS$` `MKD$` `CVS` `CVD`. The MK/CV family lives in Disk BASIC, and the
default reference is a **diskless** VG-8020 while the zerobas side is
`..._REPACK_DISK` — so these rows were comparing *machines*, not *languages*. The
probe now routes them to `National_CF-3300`, which does not yet yield a readable
SCREEN-0 capture under `omsx_repl` (a trivial `PRINT 1+1` returns VRAM pattern
garbage — likely still in the boot video mode when the capture fires). Rather than
answer from the wrong machine, the probe reports `NO-ORACLE`. Blocks no finding:
`MKS$`/`MKD$`/`CVS`/`CVD` are already tracked as deferred in `TODO.md`.

### Not executed — 18 words, crunch-only

Real coverage holes **in this probe**, listed in its output with reasons rather
than silently dropped: destructive (`DSKO$`, `IPL`), interactive (`AUTO`,
`INPUT$(n)`), non-terminating (`WAIT`), printer-bound with the known unplugged-
`LSTOUT` hang hazard (`LPRINT`, `LLIST`, `LPOS`, `LFILES`), disk-fixture-dependent
(`COPY`, `SET`, `ATTR$`, `DSKI$`, `LOC`), or already covered elsewhere
(`INTERVAL` → the T5 slice probe).

**`INPUT$` is the one to watch here:** it crunches *identically* to the reference
(because `INPUT` is a keyword and `$` follows), so Layer 1 says "present" while
support is untested — the exact `INTERVAL` shape. It is tracked as open in
`TODO.md`, but this sweep has **not** confirmed its behaviour either way.

## What the sweep does not cover

The reserved-word surface only. Statement **option surfaces** are out of scope:
`SCREEN 3`, `KEY LIST`, `ON ERROR` variants, argument-form coverage of words that
*are* present. A word can be present and still be wrong in its third argument.

## Apparatus notes (the probe's own scars)

Four defects were caught by the probe's self-checks before any of them reached a
conclusion — recorded because each is a reusable trap:

1. **The probe destroyed its own anchor.** `LOCATE 10,0:PRINT"[X]"` moved the
   cursor onto the echoed command and overprinted it, so `screen_tail` could not
   find the echo → `?noecho`. Fixed to `LOCATE 10` (column only). A startup guard
   (`MAX_DIRECT_ECHO`) now rejects any direct-mode line too wide to echo on one
   row, so this cannot recur silently.
2. **Direct mode tested the wrong thing.** The reference answers `Illegal direct`
   to a direct-mode `DEF FN` — so the original row measured the direct-mode
   restriction, not the feature. Moved to stored mode.
3. **The control group failed, correctly.** `MKI$` — implemented and working in
   zerobas — came back as the *reference* erroring. That was the diskless-machine
   asymmetry above, caught only because known-good words are measured alongside
   suspected-missing ones.
4. **Verdict ordering mattered.** An early revision checked "did zerobas tokenise
   it?" *before* comparing outputs, and duly labelled `DEFSNG`/`DEFDBL`/`DEFSTR`
   as SILENT-GAP while printing two identical answers. Agreement now wins first.

The probe also fingerprints `build/*.rom` before and after each run and **aborts
the report** if they changed mid-flight — the machine XML points straight at the
project tree, so a concurrent `make` in another session silently changes the
measurement target.
