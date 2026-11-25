<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `IF` — run part of a line only when a condition holds

> **Spec:** DRAFT 1 (2026-11-25) — 32 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kif.py`](../../probes/basic/spec/kif.py)); every rule is executable and every recorded
> output is read by one. Not yet reviewed ([the keyword plan](spec-plan.md)).
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
have measured but one.

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

The whole set of errors `IF` raises is {2, 8, 13} for `THEN` and `GOTO` and
{8, 13} for `ELSE`, the same on both machines.

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
RAM-record harness [`ramrec.py`](../../probes/basic/spec/ramrec.py)), typed on both machines; run file
[`scratchpad/KIF_run1.out`](../../scratchpad/KIF_run1.out) (2026-11-25). Each case is a block of 30 lines: line n sets
WP% to 1 and runs the IF under test, each part a case wants to see marks a bit (`(mark) k` below is `WP%=WP% OR k`),
and line n+1 -- reached only by FALLING THROUGH line n -- goes straight to the record, so a false IF that skipped the
rest of its line cannot run the case's target lines (n+5 ..). The record holds the first and last error, a counter
and WP%.
- **[KIF FX *i*]**:
  0: `WP%=1:IF 1 THEN (mark) 2:(mark) 4`
  1: `WP%=1:IF 0 THEN (mark) 2:(mark) 4`
  2: `WP%=1:IF -1 THEN (mark) 2`
  3: `WP%=1:IF .5 THEN (mark) 2`
  4: `WP%=1:IF 1E-30 THEN (mark) 2`
  5: `WP%=1:WK=0:IF WK THEN (mark) 2`
  6: `WP%=1:IF 1 THEN n+5` (line n+5: `(mark) 4`)
  7: `WP%=1:IF 0 THEN n+5` (line n+5: `(mark) 4`)
  8: `WP%=1:IF 1 GOTO n+5` (line n+5: `(mark) 4`)
  9: `WP%=1:IF 0 GOTO n+5:(mark) 2` (line n+5: `(mark) 4`)
  10: `WP%=1:IF 1 THEN (mark) 2 ELSE (mark) 4`
  11: `WP%=1:IF 0 THEN (mark) 2 ELSE (mark) 4`
  12: `WP%=1:IF 0 THEN (mark) 2 ELSE n+5` (line n+5: `(mark) 8`)
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
  27: `WP%=1:GOTO n+5` (line n+5: `WN%=WN%+1:IF WN%<3 THEN n+5`)
  28: `WP%=1:FOR I=1 TO 3:IF I=2 THEN (mark) 2:NEXT`
  29: `WP%=1:FOR I=1 TO 3:WN%=WN%+1:IF I=9 THEN (mark) 2:NEXT`
  30: `WP%=1:IF 1 THEN (mark) 2 ELSE 65000`
  31: `WP%=1:IF 1 THEN:(mark) 2`

**Controls** ([`kif_controls.py`](../../probes/basic/spec/kif_controls.py)): each is a rival rule run over the
reference's cases: “a false IF skips only THEN's statement” is FALSE on 3 of the 5 cases R-IF-LINE selects (e.g. KIF FX 1); “an ELSE belongs to the OUTER IF” is FALSE on 2 of the 9 cases R-IF-ELSE selects (e.g. KIF FX 15); “ELSE runs only its own statement” is FALSE on 1 of the 9 cases R-IF-ELSE selects (e.g. KIF FX 13); “a fraction or a tiny number is false (truncated to 0)” is FALSE on 2 of the 5 cases R-IF-TRUTH selects (e.g. KIF FX 3); “THEN followed by nothing is a Syntax error” is FALSE on 1 of the 2 cases R-IF-EMPTY selects (e.g. KIF FX 21).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/if_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/if_rules.py --write` -->

**6 rules; 6 hold on the reference. Of the 128 recorded outputs (each case's first and last error, WN% (a counter) and WP% (the bits of the parts of the line that ran)): 128 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. Truth

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-IF-TRUTH** Any non-zero number is true -- -1, .5, 1E-30 -- and 0 (also a variable holding 0) false; a string comparison is a number like any other ("A"<"B" is true). | 5 | ✓ | ✓ |

#### 2. THEN, ELSE and the rest of the line

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-IF-LINE** A true IF runs THEN's statements AND the rest of the line; a false IF skips the WHOLE rest of the line -- every statement after it, a GOTO and a NEXT included (a loop on one line ends there). | 5 | ✓ | ✓ |
| **R-IF-JUMP** THEN n, and IF ... GOTO n, jump to line n when true (also back to the IF's own line); a missing line is only an error when the jump is taken (error 8). | 7 | ✓ | ✓ |
| **R-IF-ELSE** ELSE runs when the IF is false -- its statements and every statement after them on the line, or a jump to ELSE n -- and none of it when true. An ELSE belongs to the NEAREST unmatched IF: IF a THEN IF b THEN x ELSE y runs y only when a is true and b false, and a second ELSE belongs to the outer IF. | 9 | ✓ | ✓ |
| **R-IF-EMPTY** THEN followed by nothing, or by a colon, is no error. | 2 | ✓ | ✓ |

#### 3. Errors

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-IF-ERRORS** A string as the condition is error 13 (Type mismatch); no THEN, or no condition, error 2; the condition's own error is that error (1/0: 11), and RESUME NEXT then carries on after THEN's statement. | 4 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

None known in behaviour. The one rung not yet proven is **RAM usage**.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] IF with a relational chain and AND / OR conditions (the operators pages cover the values; the branch here is
  only "non-zero").
- [A] ELSE directly after THEN n (`IF 0 THEN 100 ELSE 200` measured; `IF 1 THEN 100 ELSE ...` with a missing 100 not).

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
