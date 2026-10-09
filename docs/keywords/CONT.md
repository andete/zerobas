<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no answers=CONT|CONT -->

# `CONT` — continue a stopped program

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error not yet proven.
> Two recorded differences, both about `CONT` used inside a running program
> (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`CONT`, typed at the prompt, carries on with a program that stopped — at a
[`STOP`](STOP.md), a Ctrl-STOP, an [`END`](END.md), or an error. Variables,
open `FOR` loops and `GOSUB`s are as they were. With nothing to continue it
is `Can't CONTINUE` (error 17). zerobas behaves like the Philips VG-8020 in
every case we have measured from the prompt.

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
  `RUN`, `NEW` and editing the program clear it.
- **The rest of the typed line is ignored**: `CONT:PRINT 1` prints nothing
  extra, on the VG-8020 too.
- **Music stopped by the break does not come back.**

### Errors

| situation | error |
|---|---|
| nothing to continue: at power-on, after `NEW`, after an edit to the program | 17 `Can't CONTINUE` |
| `CONT` written inside a program | 17 `Can't CONTINUE` on the VG-8020; see *Differences* |

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

## Differences from the reference

Both concern `CONT` written *inside* a program, which can never continue
anything:

- **The line number is missing.** The VG-8020 prints `Can't CONTINUE in 10`;
  zerobas prints `Can't CONTINUE` (found 2026-09-12;
  [kwdrain_contsuffix.out](../../scratchpad/kwdrain_contsuffix.out)). zerobas
  prints the message directly instead of raising an ordinary error, on
  purpose, so that the case typed at the prompt cannot jump into a finished
  program. Joost ruled on 2026-09-27: *"add the line"* in a program, and keep
  the prompt's path.
- **An `ON ERROR` handler does not see it.** On the VG-8020 the error is
  error 17 like any other and the handler catches it; in the measured case
  zerobas ran on to the next line instead (D-CONTPROG, found 2026-09-28;
  [t6enum_b10.out](../../scratchpad/t6enum_b10.out)). This is why the
  "every error" rung is not proven: 17 is the only error `CONT` raises.

Both are TIER 6 items in [TODO.md](../../TODO.md), and probably one fix.

The other rung not yet proven is **RAM usage**.

## What we found, and how

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

## Tests that cover it

- `make abort-acceptance` — every stop `CONT` can continue from, the typed
  statements that must leave it alone, and the three that clear it.
- `make kwsweep` — the everyday row (`STOP`, then `CONT` typed at the prompt)
  and `CONT` with nothing to continue. There is no agreeing row yet for 17
  inside a program (see *Differences*).
- `make kwram` — the RAM-usage comparison.
