<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `IF` — run part of a line only when a condition holds

> **Spec:** DRAFT 1 (2026-11-25) — 60 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kif.py`](../../probes/basic/spec/kif.py)); every rule is executable and every recorded
> output is read by one. Goldfish pass 1 acted on (2026-11-25: the model is now an interpreter, 28 more
> cases); not yet re-reviewed ([the keyword plan](spec-plan.md)).
>
> **Status (2026-10-24):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No recorded
> difference since `IF 1 GOTO` was fixed on 2026-10-24.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`IF A>3 THEN PRINT "big" ELSE PRINT "small"` evaluates the condition and runs
the `THEN` part when it is true (not zero), the `ELSE` part when it is false.
Either part can be statements or just a line number to jump to. `THEN` and
`ELSE` are covered here: they only ever appear inside an `IF`, and have no
pages of their own. zerobas behaves like the Philips VG-8020 in every case we
have measured.

## Syntax

```
IF <condition> THEN <statements> | <line number> [ELSE <statements> | <line number>]
IF <condition> GOTO <line number> [ELSE <statements> | <line number>]
```

## Details

- **True means not zero**, fractions included: `IF .5 THEN` and
  `IF -.5 THEN` take the `THEN` part.
- **A string is not a condition**: `IF A$ THEN`, `IF "X" THEN` are
  `Type mismatch` (error 13).
- **`THEN 100` and `ELSE 100` are jumps**: a bare line number after either
  means `GOTO` that line.
- **The parts run to the end of the line.** When the condition is false and
  there is no `ELSE`, everything after `THEN` on that line is skipped,
  including statements after a `:`. When the `THEN` part runs, the `ELSE`
  part is skipped.
- **An `ELSE` belongs to the nearest `IF` that does not have one yet.** In
  `IF 0 THEN IF 1 THEN B=1 ELSE B=2`, the `ELSE` is the inner `IF`'s, so a
  false outer condition runs neither; add a second `ELSE` and that one is the
  outer `IF`'s. Each nested `IF` claims one `ELSE`.
- **An empty part is allowed**: `IF 1 THEN` and `IF 0 THEN 30 ELSE` do
  nothing, on both machines.

### Errors

| you write | you get |
|---|---|
| `IF THEN 30` (no condition), `IF 1 GOTO "A"` | 2 `Syntax error` |
| `IF 1 THEN 99`, `IF 0 THEN 30 ELSE 99`, `IF 1 GOTO 99`, no line 99 | 8 `Undefined line number` |
| `IF "A" THEN 30`, `IF "A" GOTO 30` | 13 `Type mismatch` |
| `IF 1 GOTO` (no line number) | accepted: `GOTO` without a line number works as `THEN` |

Besides its condition's own errors (`IF 1/0`: 11), `IF` raises 2, 8 and 13, the
same on both machines: 13 for a string condition, 8 for a missing line a taken
jump names, 2 for a malformed IF and for junk after `ELSE`.

## Example

```
10 A=5:IF A>3 THEN PRINT "Big"
20 IF A>9 THEN PRINT "Huge" ELSE 40
30 PRINT "skipped"
40 IF .5 THEN PRINT "Half is true"
50 B=9
60 IF 0 THEN IF 1 THEN B=1 ELSE B=2
70 IF 2>1 GOTO 90
80 B=0
90 PRINT "B=";B
100 ON ERROR GOTO 130
110 IF "A" THEN 120
120 END
130 PRINT "Error";ERR:RESUME NEXT
RUN
Big
Half is true
B= 9
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_if.out`](../../scratchpad/kwdoc_if.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/if_rules.py`](../../probes/basic/spec/if_rules.py), model in
[`kif_model.py`](../../probes/basic/spec/kif_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does.

**Evidence.** One probe, [`probes/basic/spec/kif.py`](../../probes/basic/spec/kif.py) (kgosub.py's frame on the shared
RAM-record harness [`ramrec.py`](../../probes/basic/spec/ramrec.py)), typed on both machines as two programs, groups FX
(the first run's cases) and FY (goldfish pass 1's separating cases); run file
[`scratchpad/KIF_run1.out`](../../scratchpad/KIF_run1.out) (2026-11-25). Each case is a block of 30 lines: line n sets
WP% to 1 and runs the IF under test, each part a case wants to see marks a bit (`(mark) k` below is `WP%=WP% OR k`),
and line n+1 -- reached only by FALLING THROUGH line n -- goes straight to the record, so a false IF that skipped the
rest of its line cannot run the case's target lines (n+5 ..). Line n ends `:GOTO n+25` except in the few cases that
must END at THEN or ELSE. The record holds the first and last error, a counter and WP%. The error handler keeps the
first error WITHOUT an IF (`WE=WE-(WE=0)*ERR`; the first run's used IF, the keyword under test -- FX re-measured
byte-identical under the new one). The model, [`kif_model.py`](../../probes/basic/spec/kif_model.py), is an
INTERPRETER of the laws the rules state; it holds no per-case answer.
- **[KIF FX *i*]**:
  0: `WP%=1:IF 1 THEN (mark) 2:(mark) 4`
  1: `WP%=1:IF 0 THEN (mark) 2:(mark) 4`
  2: `WP%=1:IF -1 THEN (mark) 2`
  3: `WP%=1:IF .5 THEN (mark) 2`
  4: `WP%=1:IF 1E-30 THEN (mark) 2`
  5: `WP%=1:WK=0:IF WK THEN (mark) 2`
  6: `WP%=1:IF 1 THEN {L5}`; line n+5: `(mark) 4`
  7: `WP%=1:IF 0 THEN {L5}`; line n+5: `(mark) 4`
  8: `WP%=1:IF 1 GOTO {L5}`; line n+5: `(mark) 4`
  9: `WP%=1:IF 0 GOTO {L5}:(mark) 2`; line n+5: `(mark) 4`
  10: `WP%=1:IF 1 THEN (mark) 2 ELSE (mark) 4`
  11: `WP%=1:IF 0 THEN (mark) 2 ELSE (mark) 4`
  12: `WP%=1:IF 0 THEN (mark) 2 ELSE {L5}`; line n+5: `(mark) 8`
  13: `WP%=1:IF 0 THEN (mark) 2 ELSE (mark) 4:(mark) 8`
  14: `WP%=1:IF 1 THEN (mark) 2 ELSE (mark) 4:(mark) 8`
  15: `WP%=1:IF 1 THEN IF 0 THEN (mark) 2 ELSE (mark) 4`
  16: `WP%=1:IF 0 THEN IF 1 THEN (mark) 2 ELSE (mark) 4`
  17: `WP%=1:IF 0 THEN IF 1 THEN (mark) 2 ELSE (mark) 4 ELSE (mark) 8`
  18: `WP%=1:IF 1 THEN IF 1 THEN (mark) 2 ELSE (mark) 4 ELSE (mark) 8`
  19: `WP%=1:IF "A"<"B" THEN (mark) 2`
  20: `WP%=1:WK$="A":IF WK$ THEN (mark) 2`
  21: `WP%=1:IF 1 THEN`
  22: `WP%=1:IF 1 (mark) 2`
  23: `WP%=1:IF THEN (mark) 2`
  24: `WP%=1:IF 1/0 THEN (mark) 2:(mark) 4`
  25: `WP%=1:IF 1 THEN 65000`
  26: `WP%=1:IF 0 THEN 65000:(mark) 2`
  27: `WP%=1:GOTO {L5}`; line n+5: `WN%=WN%+1:IF WN%<3 THEN {L5}`
  28: `WP%=1:FOR I=1 TO 3:IF I=2 THEN (mark) 2:NEXT`
  29: `WP%=1:FOR I=1 TO 3:WN%=WN%+1:IF I=9 THEN (mark) 2:NEXT`
  30: `WP%=1:IF 1 THEN (mark) 2 ELSE 65000`
  31: `WP%=1:IF 1 THEN:(mark) 2`
- **[KIF FY *i*]** (goldfish pass 1):
  0: `WP%=1:IF 1 THEN IF 0 THEN (mark) 2 ELSE (mark) 4 ELSE (mark) 8`
  1: `WP%=1:IF 0 THEN (mark) 2:IF 1 THEN (mark) 4 ELSE (mark) 8`
  2: `WP%=1:IF 0 THEN (mark) 2 ELSE IF 0 THEN (mark) 4 ELSE (mark) 8`
  3: `WP%=1:IF 0 THEN WK=139 ELSE (mark) 4`
  4: `WP%=1:IF 0 THEN WK=161:(mark) 2 ELSE (mark) 4`
  5: `WP%=1:IF 1 THEN` (no `:GOTO` appended)
  6: `WP%=1:IF 0 THEN:(mark) 2`
  7: `WP%=1:IF 1 GOTO 65000`
  8: `WP%=1:IF 0 GOTO 65000:(mark) 2`
  9: `WP%=1:IF 0 THEN (mark) 2 ELSE 65000`
  10: `WP%=1:IF "B"<"A" THEN (mark) 2`
  11: `WP%=1:WK=1:POKE VARPTR(WK),0:IF WK THEN (mark) 2`
  12: `WP%=1:WK%=0:IF WK% THEN (mark) 2`
  13: `WP%=1:IF .1# THEN (mark) 2`
  14: `WP%=1:IF -.5 THEN (mark) 2`
  15: `WP%=1:IF 1/0 THEN (mark) 2 ELSE (mark) 4:(mark) 8`
  16: `WP%=1:IF "A"<5 THEN (mark) 2 ELSE (mark) 4:(mark) 8`
  17: `WP%=1:IF "A" THEN (mark) 2`
  18: `WP%=1:IF 1 GOTO "A"`
  19: `WP%=1:IF 1 GOTO` (no `:GOTO` appended)
  20: `WP%=1:IF 0 THEN {L5} ELSE {L10}`; line n+5: `(mark) 4`; line n+10: `(mark) 8`
  21: `WP%=1:IF 1 THEN {L5} ELSE (mark) 2`; line n+5: `(mark) 4`
  22: `WP%=1:IF 0 GOTO {L5} ELSE (mark) 4`; line n+5: `(mark) 8`
  23: `WP%=1:IF 1 GOTO (mark) 2`
  24: `WP%=1:IF 0 THEN (mark) 2 ELSE` (no `:GOTO` appended)
  25: `WP%=1:IF 0 THEN (mark) 2 ELSE ,`
  26: `WP%=1:FOR I=1 TO 3:IF I<9 THEN WN%=WN%+1:NEXT`
  27: `WP%=1:IF THEN {L5}`; line n+5: `(mark) 4`

**Controls** ([`kif_controls.py`](../../probes/basic/spec/kif_controls.py)): each changes ONE law of the interpreter model and runs over the reference's cases: “a fraction is false (cut to its whole part)” is FALSE on 4 of the 10 cases R-IF-TRUTH selects (e.g. KIF FX 3); “a string comparison is always true” is FALSE on 1 of the 10 cases R-IF-TRUTH selects (e.g. KIF FY 10); “any non-zero byte makes a number true” is FALSE on 1 of the 10 cases R-IF-TRUTH selects (e.g. KIF FY 11); “a false IF skips only THEN's statement” is FALSE on 4 of the 6 cases R-IF-LINE selects (e.g. KIF FX 1); “a missing line is error 8 even when not taken” is FALSE on 2 of the 15 cases R-IF-JUMP selects (e.g. KIF FX 26); “IF ... GOTO needs a line number” is FALSE on 2 of the 15 cases R-IF-JUMP selects (e.g. KIF FY 19); “an ELSE reached by a true IF runs its part too” is FALSE on 4 of the 14 cases R-IF-ELSE selects (e.g. KIF FX 10); “only an IF directly after THEN / ELSE opens a level” is FALSE on 1 of the 14 cases R-IF-ELSE selects (e.g. KIF FY 1); “a constant's byte can be taken for IF / ELSE” is FALSE on 2 of the 14 cases R-IF-ELSE selects (e.g. KIF FY 3); “THEN followed by nothing is a Syntax error” is FALSE on 4 of the 5 cases R-IF-EMPTY selects (e.g. KIF FX 21); “RESUME NEXT goes on only at the next `:`” is FALSE on 2 of the 10 cases R-IF-ERRORS selects (e.g. KIF FY 15); “a condition that failed counts as false” is FALSE on 3 of the 10 cases R-IF-ERRORS selects (e.g. KIF FX 24).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/if_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/if_rules.py --write` -->

**6 rules; 6 hold on the reference. Of the 240 recorded outputs (each case's first and last error, WN% (a counter) and WP% (the bits of the parts of the line that ran)): 240 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. Truth

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-IF-TRUTH** A number is true unless it is zero -- -1, .5, -.5, 1E-30, a double are true; 0, an integer 0 and a variable holding 0 are false, and so is a number whose EXPONENT byte is zero whatever its digits (POKEd). A comparison is a number like any other ("A"<"B" true, "B"<"A" false). | 10 | ✓ | ✓ |

#### 2. THEN, ELSE and the rest of the line

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-IF-LINE** A true IF runs THEN's statements AND the rest of the line (a NEXT behind it included); a false IF skips the WHOLE rest of the line -- every statement after it, a GOTO and a NEXT included (a loop on one line ends there). | 6 | ✓ | ✓ |
| **R-IF-JUMP** THEN n, ELSE n and IF ... GOTO n jump to line n when taken (also back to the IF's own line); a missing line is error 8 only when the jump is taken. `IF c GOTO` with no line number after it is THEN: what follows runs as a statement (nothing at all is no error). | 15 | ✓ | ✓ |
| **R-IF-ELSE** ELSE runs when the IF is false -- its statements and the rest of the line after them, or a jump to ELSE n. When the IF is true, the first ELSE reached ends the line. A false IF finds its ELSE by counting: every IF further on opens a level -- after a colon or inside ELSE's part too -- and every ELSE closes one; a constant is never taken for a token (`WK=139`, `WK=161`). | 14 | ✓ | ✓ |
| **R-IF-EMPTY** THEN or ELSE followed by nothing, or by a colon, is no error -- true or false. | 5 | ✓ | ✓ |

#### 3. Errors

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-IF-ERRORS** A string as the condition is error 13 (Type mismatch), and so is a comparison of a string with a number; no THEN, no condition, junk after ELSE or a string after GOTO is error 2; the condition's own error is that error (1/0: 11). RESUME NEXT then goes on at the next `:` OR ELSE after the error -- and an ELSE reached that way ends the line, so neither part runs. | 10 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

None known in behaviour. The one rung not yet proven is **RAM usage**.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] IF with a relational chain and AND / OR conditions (the operators pages cover the values; the branch here is
  only "non-zero").
- [A] ELSE directly after THEN n with a missing THEN line, taken (`IF 1 THEN 99 ELSE ...`).

## What we found, and how

- **`GOTO` after the condition is `THEN` when no line number follows** (fixed
  2026-10-24, D-IFGOTOBARE, found 2026-09-27 by the every-error enumeration,
  [t6enum_b6.out](../../scratchpad/t6enum_b6.out)). On the VG-8020
  `IF 1 GOTO PRINT "X"` prints `X`, `IF 1 GOTO :PRINT "R"` prints `R`, and
  `IF 1 GOTO` alone carries on; zerobas raised `Syntax error` for all three.
  A plain `GOTO` with no line number is `Syntax error` on both ([`ifgoto_run.out`](../../scratchpad/ifgoto_run.out), [after](../../scratchpad/ifgoto_after.out)).
- **A false `IF` ran a nested `IF`'s `ELSE`** (fixed 2026-09-02, D-IFSEM).
  zerobas looked for the first `ELSE` on the line, so
  `B=9:IF 0 THEN IF 1 THEN B=1 ELSE B=2` left `B` at 2 where both references
  leave 9. Two rules fit that row — "a false `IF` ends the line" and "each
  nested `IF` claims one `ELSE`" — and only a row with a second `ELSE`
  (both references: 3) separates them; the first rule would have been the
  wrong fix. `IF` had been reviewed because, although nearly every test uses
  it, almost nothing measured it ([spec-basic-ifsem.md](../spec-basic-ifsem.md)).
- **`IF 0 THEN 20 ELSE 30` was `Syntax error`** (fixed 2026-08-01, D-LNREF):
  the line number after `ELSE` was not stored as a line-number reference, so
  the jump code that was already written never ran.
- **A fractional condition was judged on its whole-number part**, so
  `IF .5 THEN` took the false branch; found and fixed in a review on
  2026-07-11. The reference treats any non-zero number as true.
- **The `ELSE` and `GOTO` forms had no rows in the keyword sweep** until
  D-KWIF2: the only row took the `THEN` branch, so an `ELSE` that was read and
  then ignored would have passed.

## Where it lives

`ex_if` and `if_skip_to_else` (the nesting-aware search for the matching
`ELSE`) in [basic/interp.asm](../../basic/interp.asm). A line number after
`THEN` or `ELSE` goes to `GOTO`'s own `ex_goto_at`.

## Tests that cover it

- `make ifsem-acceptance` — nested `IF`s and their `ELSE`s, fractional
  conditions, string conditions.
- `make kwsweep` — the `THEN`, `ELSE` and `GOTO` rows, and the error rows for
  {2, 8, 13}.
- `make kwram` — the RAM-usage comparison.
