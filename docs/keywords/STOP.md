<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `STOP` — pause the program with a `Break` message

> **Spec:** DRAFT 1 (2026-11-25) — 6 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kstop.py`](../../probes/basic/spec/kstop.py), with END's, STOP's, CONT's and RUN's
> cases together; it reads the screen); every rule is executable and every recorded output is read by one. Not yet
> reviewed ([the keyword plan](spec-plan.md)).
>
> **Status (2026-11-01):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors: not applicable · RAM usage not yet proven · every error not yet
> proven. No recorded difference since `STOP 1` was fixed on 2026-10-24.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`STOP` halts the program and prints `Break in <line>`, exactly as pressing
Ctrl-STOP would. Unlike [`END`](END.md) it is a pause: variables, open loops
and subroutines are kept, and [`CONT`](CONT.md) carries on with the next
statement. It is the classic debugging tool — stop, `PRINT` a few variables,
`CONT`. zerobas behaves like the Philips VG-8020 in every case we have
measured.

## Syntax

```
STOP
```

`STOP ON`, `STOP OFF` and `STOP STOP` are a different statement: they
switch the `ON STOP GOSUB` trap for the Ctrl-STOP key.

## Details

- **The message is `Break in <line>`** in a program. Typed at the prompt,
  `STOP` prints a bare `Break`.
- **`CONT` resumes at the statement after the `STOP`**, mid-line if there is
  one. Each new `STOP` moves the resume point.
- **A typed `STOP` does not spoil a pending `CONT`.** After a program stops,
  typing `STOP` at the prompt (or `END`, or a line with an error) and then
  `CONT` still continues the program.
- **Inside an `ON ERROR` handler, `STOP` keeps the handler active**, so `CONT`
  resumes inside it; `END` would finish it.
- **The message appears on the text screen.** A `STOP` in a `SCREEN 2`
  program returns to the text screen first, as an error message does.
- **Music stops.** A `PLAY` still sounding is silenced, and `CONT` does not
  bring it back.
- **Common errors: not applicable.** `STOP` has no arguments to get wrong;
  Joost ruled on 2026-09-29 to declare the common-errors rung not applicable
  for `END`, `STOP`, `REM`, `CLS` and `LLIST`.

## Example

```
10 FOR I=1 TO 3
20 PRINT I
30 IF I=2 THEN STOP
40 NEXT
RUN
 1
 2
Break in 30
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_stop.out`](../../scratchpad/kwdoc_stop.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)). The
[`CONT`](CONT.md) page shows the same pause followed by `CONT`.

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/stop_rules.py`](../../probes/basic/spec/stop_rules.py), model in
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
token, the function-key line dropped. A rule reads the case's RESPONSE: the screen without the prompts and without the
echo of what was typed (each typed line cut at the line width, 37). Run file
[`scratchpad/KSP_run1.out`](../../scratchpad/KSP_run1.out) (2026-11-25).
- **[KST FX *i*]** (STOP), the lines typed after NEW / CLS:
  4: `10 PRINT "[A]":STOP:PRINT "[B]"` / `RUN`
  5: `10 PRINT "[A]":STOP:PRINT "[B]"` / `RUN` / `CONT`
  6: `10 GOSUB 30:PRINT "[C]":END` / `30 PRINT "[A]":STOP:PRINT "[B]":RETURN` / `RUN` / `CONT`
  7: `10 FOR I=1 TO 3:PRINT "[";I;"]";:STOP:NEXT` / `RUN` / `CONT` / `CONT`
  8: `STOP`
  9: `10 A=5:STOP:PRINT "[";A;"]"` / `RUN` / `A=7` / `CONT`

**Controls** ([`kstop_controls.py`](../../probes/basic/spec/kstop_controls.py)): each is a rival rule run over the
reference's cases: “STOP in direct mode prints nothing” is FALSE on 1 of the 2 cases R-STOP-BREAK selects (e.g. KST FX 8); “CONT repeats the statement before the STOP” is FALSE on 1 of the 4 cases R-STOP-CONT selects (e.g. KST FX 5).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/stop_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/stop_rules.py --write` -->

**2 rules; 2 hold on the reference. Of the 56 recorded outputs (each case's normalised screen (prompts as <prompt>, the echo of the typed lines read as typed)): 56 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. Stopping

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-STOP-BREAK** STOP stops the program with `Break in n` (n its line); in direct mode it prints `Break` alone. | 2 | ✓ | ✓ |

#### 2. Going on

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-STOP-CONT** CONT goes on with the statement AFTER the STOP: inside a GOSUB the RETURN still works, inside a FOR the loop goes on (each STOP stopping again), and a variable changed while stopped is seen. | 4 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

None recorded. `STOP ON 1` and `STOP,` are `Syntax error` on the VG-8020 too.
The rungs not yet proven are **RAM usage** and **every error**.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] What the probe cannot reach yet: CTRL+STOP (a held key), STOP ON / OFF (the traps region), files left open at
  END, `RUN "name"` (the files region).

## What we found, and how

- **`Break in` did not start a new row when the cursor was mid-row** (fixed
  2026-11-01, D-BRKFRESH). After `PRINT"AB";:STOP` both reference machines
  show `AB` and then `Break in 10` on the next row, as they do for an error
  message; zerobas printed `ABBreak in 10`. Found by a whole program -- the
  class marks rung of the program ladder stops after a `TRON` trace
  ([`progladder_marks.out`](../../scratchpad/progladder_marks.out)) -- and
  pinned by a row of its own
  ([`brkfresh_refs.out`](../../scratchpad/brkfresh_refs.out)).
- **`STOP 1` broke the program where it should be an error** (fixed
  2026-10-24, D-BAREEXTRA, found 2026-09-27 by the every-error enumeration,
  [t6enum_b7.out](../../scratchpad/t6enum_b7.out)). The VG-8020 raises
  `Syntax error in 10`; zerobas printed `Break in 10`, as if the `1` were not
  there ([`stmteq_run.out`](../../scratchpad/stmteq_run.out), [after](../../scratchpad/stmteq_after.out)).
- **`Break in 10` was invisible in graphics mode** (fixed 2026-09-27,
  D-GFXERRMSG). zerobas printed the message into the `SCREEN 2` picture and
  went back to text only for the prompt, so the user saw nothing but the
  prompt. The VG-8020 returns to the text screen first.
- **A typed `STOP` destroyed a pending `CONT`** (fixed 2026-07-30, D-CONTR).
  The old rule had been taken from a single row measured with nothing to
  continue, where "destroys it" and "leaves it alone" look the same; a row
  with a live resume point underneath showed the reference leaves it alone
  ([spec-basic-cont-record.md](../spec-basic-cont-record.md)).
- **A stopped program kept playing music** (fixed 2026-09-03, D-GICINI):
  both references silence the sound chip at a break; zerobas held the note
  for ever ([spec-basic-gicini.md](../spec-basic-gicini.md)).
- **Why `STOP` keeps an error handler and `END` does not** was measured on
  2026-07-29 (D-ONEFLG): two rows say "must not clear", and a deliberately
  wrong build failed exactly those two
  ([spec-basic-oneflg-reset-scope.md](../spec-basic-oneflg-reset-scope.md)).

## Where it lives

`ex_stop` in [basic/program.asm](../../basic/program.asm) sends a bare `STOP`
to `do_break`, which Ctrl-STOP uses too: it records the `CONT` point
(`cont_record`), silences the sound, returns to the text screen and prints
`Break` with `print_in_lineno`. `STOP ON`/`OFF`/`STOP` are handled in the
same routine.

## Related concepts

- [Errors](../concepts/errors.md) — codes, messages and `ON ERROR`
- [Interrupts and traps](../concepts/interrupts-and-traps.md) — what runs between statements

## Tests that cover it

- `make kwsweep` — the everyday row (the `Break in 10` message is what it
  reads) and the `STOP 1` error row.
- `make missing-acceptance` (the `trace` battery) — `bx-stop1`, `STOP 1` after
  a printed marker, against the references.
- `make abort-acceptance` — the `CONT` point a `STOP` records, and what typed
  statements do to it.
- `make direct-ctrl-acceptance` — a `STOP` typed at the prompt.
- `make gicini-acceptance` — music after a `STOP` and after `CONT`.
- `make kwram` — the RAM-usage comparison.
