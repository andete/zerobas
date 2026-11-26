<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `END` — stop the program

> **Spec:** DRAFT 1 (2026-11-25) — 8 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kstop.py`](../../probes/basic/spec/kstop.py), with END's, STOP's, CONT's and RUN's
> cases together; it reads the screen); every rule is executable and every recorded output is read by one.
> Goldfish pass 1 acted on (2026-11-25: the model is now an interpreter that predicts the whole screen, 4 more
> cases); not yet re-reviewed ([the keyword plan](spec-plan.md)).
>
> **Status (2026-10-24):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors: not applicable · RAM usage not yet proven · every error not yet
> proven. No recorded difference since `END 1` was fixed on 2026-10-24.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`END` stops the program and returns to the prompt, with no message. It is how
a program keeps from running on into the subroutines written after its main
part. zerobas behaves like the Philips VG-8020 for every case we have
measured.

## Syntax

```
END
```

No arguments.

## Details

- **Statements after `END` do not run**, whether on the same line or later
  lines.
- **`CONT` after `END` continues**, right after the `END` — mid-line if more
  statements follow it on the same line. See [`CONT`](CONT.md).
- **`END` finishes an `ON ERROR` handler for good.** If a handler ends the
  program, the next error is caught normally, and a typed `RESUME` is
  `RESUME without error`. ([`STOP`](STOP.md) is different: it only pauses,
  and `CONT` resumes inside the handler.)
- **`END` closes the open files**, a disk file and `CRT:` alike, on the
  VG-8020 (with a Sony HBD-F1 drive) and on the CF-3300: after `OPEN ... AS #1:END`
  and `RUN`, `PRINT #1` is `File not OPEN` (KST FY 2;
  [`disk_probe_endclose.py`](../../probes/disk/disk_probe_endclose.py), 2026-11-26).
  An older note had a disk file stay open on the CF-3300; the measurement does not
  bear it out.
- **Music keeps playing.** A `PLAY` queue still sounding when the program
  ends is left to finish; only an error or a break silences it.
- **Common errors: not applicable.** `END` has no arguments to get wrong;
  Joost ruled on 2026-09-29 to declare the common-errors rung not applicable
  for `END`, `STOP`, `REM`, `CLS` and `LLIST`.

## Example

```
10 PRINT "Start"
20 GOSUB 100
30 PRINT "Back"
40 END
50 PRINT "Never"
100 PRINT "In sub"
110 RETURN
RUN
Start
In sub
Back
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_end.out`](../../scratchpad/kwdoc_end.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/end_rules.py`](../../probes/basic/spec/end_rules.py), model in
[`kstop_model.py`](../../probes/basic/spec/kstop_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does.

**Evidence.** One probe, [`probes/basic/spec/kstop.py`](../../probes/basic/spec/kstop.py): these statements stop or
restart the program, so a program cannot record them -- the probe reads the SCREEN. Each case starts with `NEW` and
`CLS`, types a short program and the commands it names (RUN, CONT, ...), and keeps the screen NORMALISED: lines
stripped, the prompt -- "Ok" on the VG-8020, "ZB" on zerobas, a deliberate difference (basic/repl.asm) -- read as one
token, the function-key line dropped. Two groups, FX (the first run's cases) and FY (goldfish pass 1's separating
cases); run file [`scratchpad/KSP_run1.out`](../../scratchpad/KSP_run1.out) (JSON, 2026-11-25). The model,
[`kstop_model.py`](../../probes/basic/spec/kstop_model.py), is an INTERPRETER: it types each case into a small BASIC
and predicts the WHOLE screen -- every prompt (so a hang cannot pass as "does nothing"), the echo of every typed line
(wrapped at 37), the output and the messages; it holds no per-case answer.
- **[KST FX *i*]** (END), the lines typed after NEW / CLS:
  0: `10 PRINT "[A]":END:PRINT "[B]"` / `RUN`
  1: `10 PRINT "[A]":END` / `20 PRINT "[B]"` / `RUN` / `CONT`
  2: `END`
  3: `10 GOSUB 30:PRINT "[A]"` / `20 END` / `30 END` / `RUN`
- **[KST FY *i*]** (END, goldfish pass 1), the lines typed after NEW / CLS:
  0: `10 GOSUB 30:PRINT "[A]":END` / `30 END:RETURN` / `RUN` / `CONT`
  1: `10 PRINT "[A]":END:PRINT "[B]"` / `20 PRINT "[C]"` / `RUN` / `CONT`
  2: `10 OPEN "CRT:" FOR OUTPUT AS #1:END` / `RUN` / `PRINT #1,"[X]"`
  3: `10 ON ERROR GOTO 100` / `20 X=1/0` / `100 PRINT "[H]":END` / `RUN` / `RESUME`

**Controls** ([`kstop_controls.py`](../../probes/basic/spec/kstop_controls.py)): each changes ONE law of the interpreter model and runs over the reference's cases: “CONT after END cannot continue” is FALSE on 3 of the 6 cases R-END-STOP selects (e.g. KST FX 1); “CONT after END goes on at the next LINE” is FALSE on 2 of the 6 cases R-END-STOP selects (e.g. KST FY 0); “END drops a pending GOSUB” is FALSE on 1 of the 6 cases R-END-STOP selects (e.g. KST FY 0); “END leaves files open -- zerobas's (and the CF-3300 page claim's)” is FALSE on 1 of the 2 cases R-END-CLOSE selects (e.g. KST FY 2).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/end_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/end_rules.py --write` -->

**2 rules; 2 hold on the reference. Of the 58 recorded outputs (each case's normalised screen (prompts as <prompt>, the echo of the typed lines, the output, the messages)): 58 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. Stopping

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-END-STOP** END stops the program where it stands, with no message, and the prompt returns; in direct mode it does nothing. CONT after END goes on with the statement after it -- mid-line if one follows -- and a GOSUB still pending is KEPT (its RETURN works). | 6 | ✓ | ✓ |
| **R-END-CLOSE** END closes every open file (a `PRINT #1` after it is `File not OPEN`) and finishes an error handler (a typed RESUME is then `RESUME without error`). | 2 | ✓ | ✗ 1: KST FY 2 |

<!-- RULES END -->

## Differences from the reference

- **END leaves files open** (rule R-END-CLOSE, case KST FY 2; [D-ENDCLOSE](../../todo/open/D-ENDCLOSE.md)):
  both references close them (a disk file and `CRT:`); on zerobas a `PRINT #1` after
  END still prints, or goes into the still-open disk file.

The rung not yet proven is **RAM usage**.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] What the probe cannot reach yet: CTRL+STOP (a held key), STOP ON / OFF (the traps region), `RUN "name"`
  (the files region), a DISK file left open at END (D-ENDCLOSE: the VG-8020 closes a `CRT:` file).

## What we found, and how

- **`END 1` ended the program silently** (fixed 2026-10-24, D-BAREEXTRA, found
  2026-09-27, [t6enum_b5.out](../../scratchpad/t6enum_b5.out)). The VG-8020
  raises `Syntax error in 10` without ending; zerobas never checked that the
  statement stops after `END`. It does now, before it records the `CONT` point
  ([`stmteq_run.out`](../../scratchpad/stmteq_run.out), [after](../../scratchpad/stmteq_after.out)).
- **`CONT` after `END` said `Can't CONTINUE`** (fixed 2026-07-30, D-CONTR).
  The source carried a comment stating, as fact, that `END` leaves nothing to
  continue; it had never been measured, and it was wrong. Measuring also
  showed *where* `END` resumes: right after itself, mid-line
  ([spec-basic-cont-record.md](../spec-basic-cont-record.md)).
- **Ending inside an error handler left the handler marked busy** (fixed
  2026-07-29, D-ONEFLG), so the next program's first error was not caught.
  The reference clears it when a run ends or aborts, but not on a `STOP`
  ([spec-basic-oneflg-reset-scope.md](../spec-basic-oneflg-reset-scope.md)).
- **That `END` leaves music playing was measured, not assumed** (2026-09-03,
  D-GICINI): it is one of the rows that pinned the rule "an abort silences
  `PLAY`, a clean end does not"
  ([spec-basic-gicini.md](../spec-basic-gicini.md)).

## Where it lives

`ex_end` in [basic/interp.asm](../../basic/interp.asm): it records the
`CONT` point through `cont_record` in
[basic/program.asm](../../basic/program.asm), clears the error-handler flag,
and stops the run loop.

## Related concepts

- [Program text](../concepts/program-text.md) — how a typed line becomes a program line

## Tests that cover it

- `make kwsweep` — the everyday row: an `END` that keeps the program from
  falling into its subroutine.
- `make missing-acceptance` (the `trace` battery) — `bx-end1`, `END 1` after a
  printed marker, against the references.
- `make abort-acceptance` — `CONT` after `END`, mid-line and at the end of a
  line.
- `make error-trap-acceptance` — what `END` does to an active error handler.
- `make gicini-acceptance` — music after `END`.
- `make kwram` — the RAM-usage comparison.
