<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `RESUME` — leave an error handler and carry on

> **Spec:** DRAFT 1 (2026-11-25) — 21 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kerr.py`](../../probes/basic/spec/kerr.py), with ERROR's, ERR's, ERL's and RESUME's
> cases together; it reads the screen); every rule is executable and every recorded output is read by one. Not
> yet reviewed ([the keyword plan](spec-plan.md)).
>
> **Status (2026-11-25):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ (D-RESUMEMISS fixed 2026-11-25) · RAM usage not yet proven · every error ✗ (D-ONERRVAR).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`RESUME` ends an `ON ERROR GOTO` handler and tells BASIC where to continue:
at the statement that failed (to try it again), at the statement after it, or
at a line you name. It is the other half of `ON ERROR GOTO`, which is why that
statement is described here too. zerobas behaves like the Philips VG-8020 in
every case we have measured.

## Syntax

```
RESUME
RESUME 0
RESUME NEXT
RESUME <line number>
```

## Details

- **`RESUME` and `RESUME 0` run the failing statement again**, from its start.
  The handler is expected to have fixed the cause first; if it has not, the
  same error happens again.
- **`RESUME NEXT` continues with the statement after the failing one** — on
  the same line if the failing statement was followed by `:`, otherwise on the
  next line. A `:` inside a string in the failing statement does not confuse it.
  When the failing statement was the last one of the program — or of a line
  typed at the prompt, with a program's `ON ERROR GOTO` still set — the run
  simply ends and `Ok` appears.
- **`RESUME <line>` continues at the start of that line.**
- **Every `RESUME` sets `ERR` back to 0 but leaves `ERL` alone**: read after
  the `RESUME`, they give `0` and the line that failed.
- **`RESUME` with no error to resume from** is `RESUME without error`
  (error 22).
- **A handler that runs off the end of the program without `RESUME`** stops with
  `No RESUME` (error 21), naming the *last line that ran* — not the handler's
  first line — and `ERL` becomes that line. A handler that ends with `END`
  instead stops quietly.
- **An error inside the handler, before its `RESUME`,** is not caught again:
  the program stops with that second error's message.
- **`STOP` inside a handler keeps the handler open**; `CONT` carries on inside
  it, and its `RESUME` still works.

### `ON ERROR GOTO`

- **`ON ERROR GOTO <line>`** arms a handler; any later error jumps to that line.
  An undefined line is `Undefined line number` (error 8) when the statement
  runs, not when the error happens.
- **`ON ERROR GOTO 0`** disarms it — and, executed *inside* an active handler,
  it also re-raises the error that entered the handler, untrapped, with the
  original code and the original line. This is how a handler hands an error it
  does not want back to BASIC.
- **`ON ERROR GOTO` with nothing after it** is the same as `ON ERROR GOTO 0`.
- **`ON ERROR GOTO <line>` inside a handler** simply arms the new line and
  carries on.
- **A non-number after `GOTO`** (`ON ERROR GOTO A`) reads as no line, so it is
  `ON ERROR GOTO 0` on the VG-8020: inside a handler it re-raises the original
  error (KER FX 34). (This page said "a Syntax error the handler does not
  catch" -- zerobas's behaviour, D-ONERRVAR.)
- **The handler is disarmed** whenever the variables are cleared: `RUN`, `NEW`,
  `CLEAR` (and `MAXFILES`), and editing any program line.

## Example

```
10 ON ERROR GOTO 90
20 B=-1
30 A=SQR(B):PRINT "SQR";A
40 ERROR 7:PRINT "after"
50 ERROR 9
60 PRINT "not run"
70 PRINT "line 70":END
90 PRINT "Error";ERR;"in";ERL
100 IF ERR=5 THEN B=9:RESUME
110 IF ERR=7 THEN RESUME NEXT
120 RESUME 70
RUN
Error 5 in 30
SQR 3
Error 7 in 40
after
Error 9 in 50
line 70
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_resume.out`](../../scratchpad/kwdoc_resume.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

The first error is repaired and retried (`SQR(9)` is 3), the second is
skipped, and the third jumps over line 60.

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/resume_rules.py`](../../probes/basic/spec/resume_rules.py), loader in
[`kerr_model.py`](../../probes/basic/spec/kerr_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does.

**Evidence.** One probe, [`probes/basic/spec/kerr.py`](../../probes/basic/spec/kerr.py). A probe that records into RAM
catches every error with ON ERROR / RESUME NEXT -- the keywords under test -- so this one reads the SCREEN, as
[`kstop.py`](../../probes/basic/spec/kstop.py) does: each case starts with `NEW` and `CLS`, types a short program and
the commands it names, and keeps the normalised screen (the prompt -- "Ok" there, "ZB" here, a deliberate difference
-- read as one token). The model is kstop's small BASIC ([`kstop_model.py`](../../probes/basic/spec/kstop_model.py)),
ONE interpreter for every screen-reading keyword probe: it types each case and predicts the WHOLE screen, every prompt
included. Run file [`scratchpad/KER_run1.out`](../../scratchpad/KER_run1.out) (JSON, 2026-11-25).
- **[KER FX *i*]** (RESUME), the lines typed after NEW / CLS:
  19: `10 ON ERROR GOTO 100` / `20 D=0` / `30 X=1/D:PRINT "[";X;"]":END` / `100 D=1:RESUME` / `RUN`
  20: `10 ON ERROR GOTO 100` / `20 D=0` / `30 X=1/D:PRINT "[";X;"]":END` / `100 D=1:RESUME 0` / `RUN`
  21: `10 ON ERROR GOTO 100` / `20 X=1/0:PRINT "[B]"` / `30 PRINT "[C]":END` / `100 RESUME NEXT` / `RUN`
  22: `10 ON ERROR GOTO 100` / `20 X=1/0` / `30 PRINT "[C]":END` / `100 RESUME NEXT` / `RUN`
  23: `10 ON ERROR GOTO 100` / `20 PRINT ":";1/0:PRINT "[B]":END` / `100 RESUME NEXT` / `RUN`
  24: `10 ON ERROR GOTO 100` / `20 X=1/0` / `30 PRINT "[C]"` / `40 PRINT "[D]":END` / `100 RESUME 40` / `RUN`
  25: `10 ON ERROR GOTO 100` / `20 X=1/0` / `100 RESUME 99` / `RUN`
  26: `10 RESUME` / `RUN`
  27: `10 ON ERROR GOTO 100` / `20 X=1/0` / `30 PRINT "[C]"` / `100 PRINT "[H]"` / `RUN`
  28: `10 ON ERROR GOTO 100` / `20 X=1/0` / `30 PRINT "[C]"` / `100 PRINT "[H]"` / `RUN` / `PRINT ERR;ERL`
  29: `10 ON ERROR GOTO 100` / `20 X=1/0:PRINT "[B]":END` / `100 Y=1/0:RESUME NEXT` / `RUN`
  30: `10 ON ERROR GOTO 100` / `20 X=1/0:PRINT "[B]":END` / `100 ON ERROR GOTO 0` / `RUN`
  31: `10 ON ERROR GOTO 999` / `20 PRINT "[B]"` / `RUN`
  32: `10 ON ERROR GOTO 100` / `20 ON ERROR GOTO 0` / `30 X=1/0:PRINT "[B]"` / `100 PRINT "[H]":RESUME NEXT` / `RUN`
  33: `10 ON ERROR GOTO 100` / `20 X=1/0:PRINT "[B]":END` / `100 PRINT "[H]":ON ERROR GOTO 200:RESUME NEXT` / `200 PRINT "[I]":RESUME NEXT` / `RUN`
  34: `10 ON ERROR GOTO 100` / `20 X=1/0:PRINT "[B]":END` / `100 ON ERROR GOTO A` / `RUN`
  35: `10 ON ERROR GOTO 100` / `20 X=1/0:Y=1/0` / `30 PRINT "[";ERR;"]":END` / `100 PRINT "[H]";ERR;:RESUME NEXT` / `RUN`
  36: `10 ON ERROR GOTO 100` / `20 END` / `100 PRINT "[H]":RESUME NEXT` / `RUN` / `PRINT 1/0:PRINT "[T]"`
  37: `10 ON ERROR GOTO 100` / `20 X=1/0` / `30 PRINT "[C]":END` / `100 PRINT "[H]":RUN 30` / `RUN` / `RESUME`
  38: `10 ON ERROR GOTO 100` / `20 X=1/0` / `100 PRINT "[H]":END` / `RUN` / `PRINT 1/0:PRINT "[T]"`
  39: `10 ON ERROR GOTO 100` / `20 END` / `100 PRINT "[H]":END` / `RUN` / `RESUME`

**Controls** ([`kerr_controls.py`](../../probes/basic/spec/kerr_controls.py)): each changes ONE law of the interpreter
and runs over the reference's cases: “RESUME NEXT always goes to the next line” is FALSE on 2 of the 8 cases R-RESUME-FORMS selects (e.g. KER FX 21); “RESUME to a missing line stops silently -- zerobas's” is FALSE on 1 of the 8 cases R-RESUME-FORMS selects (e.g. KER FX 25); “RESUME's own error is trapped too” is FALSE on 1 of the 8 cases R-RESUME-HANDLER selects (e.g. KER FX 39); “END inside a handler disarms ON ERROR” is FALSE on 1 of the 8 cases R-RESUME-HANDLER selects (e.g. KER FX 38); “an error typed at the prompt never reaches a handler” is FALSE on 2 of the 8 cases R-RESUME-HANDLER selects (e.g. KER FX 36); “an error inside the handler enters it again” is FALSE on 1 of the 8 cases R-RESUME-HANDLER selects (e.g. KER FX 29); “GOTO 0 inside a handler only disarms” is FALSE on 2 of the 5 cases R-RESUME-ONERROR selects (e.g. KER FX 30); “a missing handler line is found only at the error” is FALSE on 1 of the 5 cases R-RESUME-ONERROR selects (e.g. KER FX 31); “a non-number after GOTO is error 2 -- zerobas's” is FALSE on 1 of the 5 cases R-RESUME-ONERROR selects (e.g. KER FX 34).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/resume_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/resume_rules.py --write` -->

**3 rules; 3 hold on the reference. Of the 176 recorded outputs (each case's normalised screen (prompts as <prompt>, the echo of the typed lines, the output, the messages)): 176 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. Where it goes on

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-RESUME-FORMS** RESUME and RESUME 0 run the failing statement again (the handler having fixed the cause); RESUME NEXT runs the statement after it -- on the same line after a `:`, else the next line; a `:` inside a string does not count; RESUME n goes to line n, and a missing n is error 8 in the handler's line, untrapped. RESUME with no error is error 22 (RESUME without error). | 8 | ✓ | ✓ |

#### 2. The handler

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-RESUME-HANDLER** A handler is entered by any error while it is armed and none is active -- one typed at the prompt too (RESUME NEXT then goes on along the typed line), and after an earlier handler ended with END; NOT RESUME's own error, and not an error inside the active handler (that one stops the program). After RESUME the handler catches the next error again. A handler that runs off the end of the program stops with `No RESUME` in the last line that ran (ERR 21, ERL that line); RUN inside it clears it. | 8 | ✓ | ✓ |

#### 3. ON ERROR GOTO

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-RESUME-ONERROR** ON ERROR GOTO n arms line n -- a missing n is error 8 at once; ON ERROR GOTO 0 disarms, and so does a non-number after GOTO (`ON ERROR GOTO A` is GOTO 0). Inside the active handler, GOTO 0 re-raises the error that entered it, untrapped, with its own line; GOTO n there arms n and goes on. | 5 | ✓ | ✗ 1: KER FX 34 |

<!-- RULES END -->

## Differences from the reference

- **`ON ERROR GOTO A`** (rule R-RESUME-ONERROR, case KER FX 34;
  [D-ONERRVAR](../../todo/open/D-ONERRVAR.md)): a non-number after GOTO is GOTO 0 on the reference
  (inside a handler it re-raises the original error); zerobas says `Syntax error`.

Two rungs are not yet proven. **Every error**: the set of errors `RESUME`
itself can raise has not been measured, because the tool that enumerates error
sets reads each error through an `ON ERROR` handler, and it got no reading for
any `RESUME` case on the VG-8020. **RAM usage**: the RAM comparison has not yet
been able to rate `RESUME`'s test programs.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Errors inside a GOSUB or a FOR in the handler, ERR / ERL after RUN and CLEAR, an error trap
  (ON KEY ...) firing inside an error handler.

## What we found, and how

- **`RESUME 99` to a missing line hung zerobas** (fixed 2026-11-25, D-RESUMEMISS, found
  by the spec probe's KER FX 25). The `RESUME <line>` arm left the handler -- cleared
  the "handler active" flag -- BEFORE it looked the line up, so the missing line's
  error 8 found the trap still armed and no handler active: the handler ran again,
  met the same `RESUME 99`, and so on for ever. The VG-8020 looks first, inside the
  handler, and stops with `Undefined line number in 100`. zerobas now does the same,
  in the same 6 bytes of main ROM.
- **`RESUME NEXT` skipped a statement after a `PRINT USING` type error at the
  end of a line** (fixed 2026-11-05, D-RESNEXTEOL; see
  [`PRINT`](PRINT.md)). The error surfaced only once the next line had begun,
  so `ERL` named that line and `RESUME NEXT` went past its first statement.
  Six other errors raised at a line's end were already right and are the
  controls ([readings](../../scratchpad/resnexteol_measure.out)).

- **`RESUME NEXT` after the last statement never stopped** (fixed 2026-10-30,
  D-RESNEXTDIRECT). After an error on a program's last line, or in a line
  typed at the prompt while a program's `ON ERROR GOTO` was still set,
  zerobas went on past the end of the program, ran whatever bytes followed as
  statements, and caught its own errors there forever. The VG-8020 ends the
  run. Found when a test program left an unread key, which reached the
  prompt and raised an error there. `RESUME NEXT` now resumes on the failing
  line's own end, and the ordinary step to the next line ends the run.

- **`RESUME NEXT` skipped the rest of the line after some errors** (fixed
  2026-10-09, D-RESNEXTOVF). With `20 PRINT 1E62*9:PRINT "A"` the VG-8020
  resumes at `PRINT "A"`; zerobas went on at the next line
  ([`resnext_run.out`](../../scratchpad/resnext_run.out)). It looked like an
  `Overflow` problem — division by zero and `SQR(-1)` resumed correctly — but
  the cause was the search for "the next statement": it read the stored line
  byte by byte, and a number in the program is stored with its value bytes
  (`1E62` is `1D 7F 10 00 00`), so a 0 byte ended the line early and a byte
  `&H3A`, the code of `:`, ended the statement early (`58*…` resumed on the
  `*`, a second error). It now steps over each number whole.
- **Error trapping arrived on 2026-07-18 and 2026-07-19**, after the first
  measurement showed that an untrapped error did not even stop a zerobas
  program. `ERR` going back to 0 on `RESUME` while `ERL` stays was measured on
  the VG-8020 and added the same day:
  [spec-basic-error-handling.md](../spec-basic-error-handling.md).
- **`CLEAR` or `MAXFILES` in a running program did not disarm the handler**
  (fixed 2026-07-29, D-ONELIN). Measuring showed the rule is "whenever the
  variables are cleared", program edits included.
- **`No RESUME` was never raised** (fixed 2026-07-31, D-ERR21): a handler that
  ran off the end of the program ended silently. The line it names turned out
  to be the last line that ran, not the handler's — the earlier write-up had
  measured a program where the two were the same line:
  [spec-basic-err21-no-resume.md](../spec-basic-err21-no-resume.md).
- **`ON ERROR GOTO 0` inside a handler just disarmed** (fixed 2026-08-09,
  D-ONERR0); both references re-raise the original error. A cheaper fix that
  re-ran the failing statement was rejected by a row showing the reference
  does not re-run it:
  [onerr0-msx1-characterization.md](../onerr0-msx1-characterization.md).
- **`ON ERROR GOTO A` was caught by the current handler** (fixed 2026-09-02,
  D-ONERRGO); on both references it is not. The obvious fix would have made a
  bare `ON ERROR GOTO` an error as well, where the references treat it as
  `ON ERROR GOTO 0`: [spec-basic-onerrgo.md](../spec-basic-onerrgo.md).
- **Only `RESUME NEXT` had a test** until 2026-09-15 (D-KWRETRES). The bare and
  line forms got rows that only the right form can pass: the retried `SQR`
  must give 3, and the line form must skip an assignment in between.

## Where it lives

- `ex_resume` in [basic/interp.asm](../../basic/interp.asm); `RESUME without
  error` leaves through `ex_resume_noerr` / `raise_error_forced` in the same
  file. `RESUME NEXT`'s search for the end of the failing statement is
  `scan_stmt_end` in the sub-ROM, [sub/errtrap.asm](../../sub/errtrap.asm).
- `No RESUME` is raised by `e21_no_resume` in
  [basic/arrays.asm](../../basic/arrays.asm).
- `ON ERROR GOTO` is `ex_on_error` (disarm: `oe_disable`) in
  [basic/program.asm](../../basic/program.asm).

## Related concepts

- [Errors](../concepts/errors.md) — codes, messages and `ON ERROR`

## Tests that cover it

- `make error-trap-acceptance` — the three destinations, `RESUME without
  error`, `No RESUME`, nested errors, and what disarms a handler.
- `make onerr0-acceptance` — `ON ERROR GOTO 0` and its operand, on both
  references.
- `make resnext-acceptance` — `RESUME NEXT` after a fault in a statement that
  holds numbers stored with zero or `:`-like bytes, and four controls.
- `make resnextend-acceptance` — `RESUME NEXT` after an error on the last
  program line and in a typed line, each run to its end (D-RESNEXTDIRECT).
- `make kwsweep` — one row per form (bare, `NEXT`, line), and `RESUME` typed
  with no error (22).
- `make kwram` — the RAM-usage comparison.
