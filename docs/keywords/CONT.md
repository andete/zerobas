<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no answers=CONT|CONT -->

# `CONT` — continue a stopped program

> **Spec:** DRAFT 1 (2026-11-25) — 4 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kstop.py`](../../probes/basic/spec/kstop.py), with END's, STOP's, CONT's and RUN's
> cases together; it reads the screen); every rule is executable and every recorded output is read by one. Not yet
> reviewed ([the keyword plan](spec-plan.md)).
>
> **Status (2026-11-06):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓.
> No recorded difference since 2026-11-06 (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`CONT`, typed at the prompt, carries on with a program that stopped — at a
[`STOP`](STOP.md), a Ctrl-STOP, an [`END`](END.md), or an error. Variables,
open `FOR` loops and `GOSUB`s are as they were. With nothing to continue it
is `Can't CONTINUE` (error 17). zerobas behaves like the Philips VG-8020 in
every case we have measured, at the prompt and inside a program.

## Syntax

```
CONT
```

No arguments.

## Details

- **Where it continues depends on how the program stopped:**

  | the program stopped at | `CONT` continues |
  |---|---|
  | `STOP` or Ctrl-STOP | at the next statement |
  | `END` | right after the `END`, mid-line if more statements follow it |
  | an error that was not caught | at the failing statement, so the same error comes back |
  | the last line | nowhere: it returns to the prompt silently |

- **`CONT` does not use the resume point up.** A second `CONT` after the
  program has stopped again continues from the new stop; after a program that
  ran to its end, every further `CONT` returns silently.
- **What you type in between does not matter**: an ordinary line, a typed
  `STOP`, a typed `END`, even a typed error leave the resume point alone. Only
  `RUN`, `NEW`, `CLEAR` and editing the program clear it.
- **The rest of the typed line is ignored**: `CONT:PRINT 1` prints nothing
  extra, on the VG-8020 too.
- **Music stopped by the break does not come back.**

### Errors

| situation | error |
|---|---|
| nothing to continue: at power-on, after `NEW` or `CLEAR`, after an edit to the program | 17 `Can't CONTINUE` |
| `CONT` written inside a program, nothing to continue | 17 `Can't CONTINUE in <line>`; an `ON ERROR` handler catches it |

## Example

```
10 PRINT "One"
20 STOP
30 PRINT "Two"
40 END:PRINT "Three"
RUN
One
Break in 20
CONT
Two
CONT
Three
```

The first `CONT` continues after the `STOP`; the second continues after the
`END`, on the same line.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_cont.out`](../../scratchpad/kwdoc_cont.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/cont_rules.py`](../../probes/basic/spec/cont_rules.py), model in
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
- **[KST FX *i*]** (CONT), the lines typed after NEW / CLS:
  10: `CONT`
  11: `10 PRINT "[A]":X=1/0:PRINT "[B]"` / `RUN` / `CONT`
  12: `10 PRINT "[A]":STOP:PRINT "[B]"` / `RUN` / `20 PRINT "[C]"` / `CONT`
  13: `10 PRINT "[A]":STOP:PRINT "[B]"` / `RUN` / `PRINT 1+1` / `CONT`

**Controls** ([`kstop_controls.py`](../../probes/basic/spec/kstop_controls.py)): each is a rival rule run over the
reference's cases: “CONT after an error cannot continue” is FALSE on 1 of the 4 cases R-CONT-WHEN selects (e.g. KST FX 11); “a direct statement in between blocks CONT” is FALSE on 1 of the 4 cases R-CONT-WHEN selects (e.g. KST FX 13); “an added line keeps CONT possible” is FALSE on 1 of the 4 cases R-CONT-WHEN selects (e.g. KST FX 12).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/cont_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/cont_rules.py --write` -->

**1 rules; 1 hold on the reference. Of the 35 recorded outputs (each case's normalised screen (prompts as <prompt>, the echo of the typed lines read as typed)): 35 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. When CONT can go on

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-CONT-WHEN** CONT before anything ran, or after a program line was added or changed, prints `Can't CONTINUE`; a direct statement in between does not stop it; after an ERROR, CONT runs the failing statement again and raises the same error. | 4 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

None recorded. The three that stood until 2026-11-06 are under *What we found*.

The rung not yet proven is **RAM usage**.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] What the probe cannot reach yet: CTRL+STOP (a held key), STOP ON / OFF (the traps region), files left open at
  END, `RUN "name"` (the files region).

## What we found, and how

- **`CONT` after a typed `CLEAR` went back into the program** (fixed
  2026-11-06, D-CLEARCONT). On the VG-8020 and the CF-3300, `CLEAR` typed while
  a program sits at a `STOP` ends the resume point: `CONT` says
  `Can't CONTINUE`. zerobas continued into a program whose `FOR` loop `CLEAR`
  had just wiped, and stopped with `NEXT without FOR in 40`. Found by the typed
  session [`S12_progedit.ses`](../../probes/sessions/S12_progedit.ses)
  ([`sessions_S12_progedit.out`](../../scratchpad/sessions_S12_progedit.out));
  the CF-3300 run ([`clearcont_cf.ses`](../../scratchpad/clearcont_cf.ses),
  [`clearcont_cf.out`](../../scratchpad/clearcont_cf.out)) also shows that an
  ordinary line such as `A=5` between two stops leaves `CONT` working.
- **`CONT` inside a program said `Can't CONTINUE` and ran on** (fixed
  2026-10-24, D-CONTPROG). On the VG-8020 it is error 17 like any other: an
  `ON ERROR` handler catches it, and without one the program stops with
  `Can't CONTINUE in 20`. zerobas printed the message without a line and went
  on to the next statement, so a handler never saw it
  ([`contusr_run.out`](../../scratchpad/contusr_run.out), from
  [`contusr_probe.py`](../../scratchpad/contusr_probe.py); found 2026-09-12 and
  2026-09-28). The message used to be printed directly on purpose, so that
  `CONT` typed at the prompt cannot jump into a finished program; that path is
  kept for the prompt, and only a running program now raises an ordinary error,
  as Joost ruled on 2026-09-27 (*"add the line"*). After the fix all five
  cases read as on the VG-8020
  ([`contusr_after.out`](../../scratchpad/contusr_after.out)). The same
  measurement showed that a `CONT` in a program is not always an error: after a
  `STOP` that was continued from the prompt, the program's own `CONT` continues
  from that `STOP` again, on both machines.
- **`CONT` only worked after `STOP`** (fixed 2026-07-30, D-CONTR). After
  `END`, after an error, or after the program ran off its end, zerobas said
  `Can't CONTINUE`; the VG-8020 continues in each case, each from a different
  place. 34 boots of measurement pinned the table above, and showed two more
  things: `CONT` never uses the point up, and a typed `STOP` must not destroy
  it ([spec-basic-cont-record.md](../spec-basic-cont-record.md)).
- **`CONT` that ran off the end printed `Illegal function call in 3346`**, a
  line that did not exist (fixed 2026-07-29, D-CONTD). `CONT` restarted the
  run loop from one level too deep, so the loop's exit returned into itself
  ([spec-basic-cont-depth.md](../spec-basic-cont-depth.md)).
- **`CONT` had no row in the keyword sweep** until 2026-09-24 (D-CONTROW).
  The first version agreed for the wrong reason: it read the screen only up
  to the `Break`, so it could not see whether `CONT` did anything. The row now
  waits for a marker that only the continued program prints.

## Where it lives

`ex_cont` in [basic/program.asm](../../basic/program.asm). Every way a run
stops records its resume point through `cont_record` (same file), called from
`do_break` (`STOP`, Ctrl-STOP), `ex_end` and the error and end-of-program
exits in [basic/interp.asm](../../basic/interp.asm).

## Related concepts

- [Errors](../concepts/errors.md) — codes, messages and `ON ERROR`
- [Interrupts and traps](../concepts/interrupts-and-traps.md) — what runs between statements
- [Program text](../concepts/program-text.md) — how a typed line becomes a program line

## Tests that cover it

- `make abort-acceptance` — every stop `CONT` can continue from, the typed
  statements that must leave it alone, and the three that clear it.
- `make sessions-acceptance` — session `S12_progedit`: `CONT` after `CLEAR`,
  after an edited line, after `DELETE`, after `RENUM` and after `NEW`, typed
  at the prompt.
- `make kwsweep` — the everyday row (`STOP`, then `CONT` typed at the prompt)
  and `CONT` with nothing to continue.
- `make missing-acceptance` — `CONT` inside a program, caught by `ON ERROR`
  and not caught (rows `ct-trap`, `ct-plain`).
- `make kwram` — the RAM-usage comparison.
