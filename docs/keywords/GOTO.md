<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `GOTO` — jump to a line

> **Spec:** DRAFT 1 (2026-11-25) — 13 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kgosub.py`](../../probes/basic/spec/kgosub.py), with GOTO's, GOSUB's and RETURN's cases
> together); every rule is executable and every recorded output is read by one. Not yet reviewed ([the keyword
> plan](spec-plan.md)).
>
> **Status (2026-11-25):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No recorded
> difference since the `IF … GOTO` form was fixed on 2026-10-24.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`GOTO 100` continues the program at line 100. Nothing is remembered, so there
is no way back (for that, use [`GOSUB`](GOSUB.md)). zerobas behaves like the
Philips VG-8020 in every case we have measured, errors included.

## Syntax

```
GOTO <line number>
ON <expression> GOTO <line number>[,<line number>...]
IF <condition> GOTO <line number>
```

The line number is a constant; `GOTO A` and `GOTO "100"` are not allowed.

## Details

- **Anything after the line number is never reached**, so `GOTO 100 ZZ` is
  accepted on both machines.
- **A line number stops before it would pass 65529.** The digits of
  `GOTO 70000` are read as `GOTO 7000` followed by a stray `0`, so with no
  line 7000 it is `Undefined line number` on both machines
  ([spec-basic-lnref.md](../spec-basic-lnref.md)).
- **`ON n GOTO 100,200,300`** jumps to the n-th line in the list. `n` is
  truncated, not rounded (`ON 1.7` takes the first). `ON 0` or an `n` past the
  end of the list does nothing and the program carries on; a negative `n` or
  one above 255 is `Illegal function call` (error 5), and one beyond the
  integer range is `Overflow` (error 6). A string is `Type mismatch`
  (error 13), and an empty list is `Syntax error`.
- **`IF <condition> GOTO <line>`** is `IF` without `THEN`; see [`IF`](IF.md).

### Errors

| you write | you get |
|---|---|
| `GOTO 99` when there is no line 99 | 8 `Undefined line number` |
| `GOTO 70000` | 8 `Undefined line number` (read as 7000, see above) |
| `GOTO`, `GOTO "A"`, `GOTO -1` | 2 `Syntax error` |

The whole set of errors `GOTO` raises is {2, 8}, the same on both machines.

## Example

```
10 N=1
20 PRINT N;
30 N=N*2
40 IF N>100 THEN 60
50 GOTO 20
60 PRINT:ON 2 GOTO 70,80
70 PRINT "One"
80 PRINT "Two"
90 ON ERROR GOTO 120
100 GOTO 999
110 END
120 PRINT "Error";ERR:RESUME NEXT
RUN
 1  2  4  8  16  32  64
Two
Error 8
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_goto.out`](../../scratchpad/kwdoc_goto.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/goto_rules.py`](../../probes/basic/spec/goto_rules.py), model in
[`kgosub_model.py`](../../probes/basic/spec/kgosub_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does.

**Evidence.** One probe, [`probes/basic/spec/kgosub.py`](../../probes/basic/spec/kgosub.py) (on the shared RAM-record
harness [`ramrec.py`](../../probes/basic/spec/ramrec.py)), typed on both machines; run file
[`scratchpad/KGS_run1.out`](../../scratchpad/KGS_run1.out) (2026-11-25; zerobas's side on that day's build). Each case
is a block of 30 lines from its base n: line n starts from nothing (`CLEAR`, `ON ERROR` set again), runs the
statement(s) under test and ends `GOTO n+25`; the case's own target lines sit at n+5 .. n+20; n+25 records the first
and the last error (RESUME NEXT carries on after one), a counter WN% and WP%, the bits of the lines the case reached
(1 line n, 2 the rest of line n after a GOSUB, 4 / 8 / 16 lines n+5 / n+10 / n+15) -- so a rule says WHICH lines ran.
A loop that could run for ever carries the guard `ON -(WN%>20) GOTO n+25` (21 = "did not stop").
- **[KGS FX *i*]** (GOTO):
  0: `WP%=1:GOTO n+5:WP%=WP% OR 2` (line n+5: `WP%=WP% OR 4`)
  1: `GOTO n+10` (line n+5: `WP%=WP% OR 4`; line n+10: `WP%=WP% OR 8`)
  2: `WN%=0:GOTO n+5` (line n+5: `WN%=WN%+1:WP%=WP% OR 4:<guard>:GOTO n+5`)
  3: `GOTO 65000`
  4: `GOTO 65530`
  5: `GOTO`
  6: `WK=1:GOTO WK`
  7: `GO TO n+5` (line n+5: `WP%=WP% OR 4`)
  8: `GOTO n+5 7` (line n+5: `WP%=WP% OR 4`)
  25: `GOSUB n+5:WP%=WP% OR 2` (line n+5: `WP%=WP% OR 4:GOTO n+10`; line n+10: `WP%=WP% OR 8:RETURN`)
  27: `GO  TO n+5` (line n+5: `WP%=WP% OR 4`)
  28: `IF 1 THEN GO TO n+5` (line n+5: `WP%=WP% OR 4`)
  29: `GO`

**Controls** ([`kgosub_controls.py`](../../probes/basic/spec/kgosub_controls.py)): each is a rival rule run over the
reference's cases: “`GO TO` is no keyword (a Syntax error) -- zerobas's” is FALSE on 2 of the 4 cases R-GOTO-GOTO selects (e.g. KGS FX 7); “a line past 65529 is a Syntax error” is FALSE on 1 of the 5 cases R-GOTO-ERRORS selects (e.g. KGS FX 4); “text after the line number is a Syntax error” is FALSE on 1 of the 5 cases R-GOTO-ERRORS selects (e.g. KGS FX 8).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/goto_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/goto_rules.py --write` -->

**3 rules; 3 hold on the reference. Of the 52 recorded outputs (each case's first and last error, WN% (a counter; 21 = the probe's guard ended a loop that did not stop) and WP% (the bits of the lines the case reached)): 52 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. The jump

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-GOTO-JUMP** GOTO n continues at line n: the rest of its own line and every line in between are skipped; a GOTO back to its own line loops; a GOTO inside a subroutine leaves the GOSUB pending, so a RETURN on the line it reaches comes back after the GOSUB. | 4 | ✓ | ✓ |
| **R-GOTO-GOTO** `GO TO` written with exactly ONE space is GOTO -- also after THEN; two spaces, or `GO` alone, are error 2 (Syntax error). | 4 | ✓ | ✓ |

#### 2. Errors

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-GOTO-ERRORS** A line that does not exist is error 8 (Undefined line number) -- also a number past 65529 and a number followed by more text (`GOTO n 7`, read as one number); no number, or a variable, is error 2. | 5 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

None known in behaviour (`GO TO` with one space is GOTO since 2026-11-25, D-GOTOSPACE). A plain `GOTO` with no line number is `Syntax error` on both machines; inside `IF`, see [`IF`](IF.md). The one rung
not yet proven is **RAM usage**.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] ON ... GOTO (the composite region), GOTO into a FOR's body from outside it.

## What we found, and how

- **`IF 1 GOTO` with no line number was `Syntax error` here** (fixed
  2026-10-24, D-IFGOTOBARE): on the VG-8020 a `GOTO` after `IF`'s condition
  without a line number works as `THEN` ([`ifgoto_run.out`](../../scratchpad/ifgoto_run.out), [after](../../scratchpad/ifgoto_after.out)).
- **A jump stored as a line POINTER was a Syntax error** (fixed 2026-10-12,
  D-BASICROM). After a jump runs, the reference rewrites its operand from a line
  number into the address of the line, in the program text itself; a program
  stored after it ran -- a BASIC cartridge, a file saved from a real MSX --
  carries that form, and zerobas refused it: Vampier's 3D Golf Simulation
  cartridge stopped at its first GOSUB. zerobas now follows it (it never writes
  it). `RESTORE` is not one of them: the reference answers a pointer there
  with `Undefined line number`, and so does zerobas
  ([`basicrom_gate.out`](../../scratchpad/basicrom_gate.out)).
- **Big line numbers wrapped** (fixed 2026-08-01, D-LNREF). `GOTO 99999` was
  stored as a jump to line 34463. The reference neither wraps nor refuses: it
  splits the digits at 65529, the same ceiling as a program line's own number
  ([lnref-msx1-characterization.md](../lnref-msx1-characterization.md)).
- **`GOTO` had no test of its own** (D-KWGOTOROW). It was used by dozens of
  rows in the keyword sweep and was the subject of none — its only row was the
  `GOTO 9999` error. Being used is not being measured: the row added puts a
  statement after the `GOTO` that must be skipped, so a `GOTO` that fell
  through shows a different value.
- **`ON n GOTO`'s selector was checked on 2026-08-30** (D-ONDOM) and found
  correct everywhere: 15 rows, no difference. The rows that matter are the
  ones that do *not* raise — an `n` past the list falls through silently, so
  a wrong answer there has no error to notice
  ([spec-basic-ondom.md](../spec-basic-ondom.md)).

## Where it lives

`ex_goto` and `goto_resolve` in [basic/interp.asm](../../basic/interp.asm).
The line number is read by the shared `req_lineno` (also used by `GOSUB`,
`RESUME` and `ON ERROR GOTO`); `goto_resolve` is shared with `RESUME <line>`.
`ON … GOTO` is `ex_on` and `eon_seek_nth` in
[basic/program.asm](../../basic/program.asm).

## Related concepts

- [Program text](../concepts/program-text.md) — how a typed line becomes a program line

## Tests that cover it

- `make kwsweep` — the jump row, the `ON 2 GOTO` row, and the error rows for
  {2, 8}.
- `make lnblank-acceptance` — how line-number references are stored, the
  65529 split included.
- `make kwram` — the RAM-usage comparison.
