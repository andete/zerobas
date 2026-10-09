<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `RUN` — start the program

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error not yet proven. No known
> divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`RUN` starts the program in memory from its first line, with a clean slate:
variables and arrays are cleared, `DATA` starts again from the top, open
files are closed. `RUN 100` does the same but starts at line 100.
`RUN "name"` loads a program from disk or tape and runs it. zerobas behaves
like the Philips VG-8020 (and, for the disk form, the National CF-3300) in
every case we have measured.

## Syntax

```
RUN
RUN <line number>
RUN <file name>[,R]
```

`RUN` can be typed at the prompt or used inside a program.

## Details

- **Everything is reset first**: variables and arrays, the `DATA` pointer, an
  `ON ERROR GOTO`, and the resume point of [`CONT`](CONT.md).
- **Open files are closed** (measured on the CF-3300): a program that left
  `#1` open finds it closed after the next `RUN` — `PRINT #1` is
  `File not OPEN` (error 59). `END` and `NEW` do not close files.
- **`RUN 20` starts at line 20**, typed or in a program, with or without the
  space (`RUN20`). A missing line is `Undefined line number` (error 8).
- **A bare `RUN` inside a program restarts it.** Because the variables are
  cleared, a program that always reaches its `RUN` restarts for ever, on the
  references as here.
- **`RUN "name"` replaces the program in memory** and runs the new one;
  nothing is printed after it ends but the prompt. A file that is not there
  leaves the old program alone and is `File not found` on the CF-3300.
  `RUN "CAS:name"` loads from tape. On a machine without a disk drive, such
  as the VG-8020, only the tape form exists.
- **Only `,R` may follow the name**: `RUN "A",5` is `Syntax error` on both
  references, from disk and from tape.
- **The name is an ordinary string expression**: `RUN A$` works, and a
  number (`RUN A+0`) is `Type mismatch` (error 13, measured on the CF-3300).

## Example

```
10 V=VPEEK(4096)
20 PRINT "Pass";V+1;"A=";A
30 A=5:IF V=1 THEN END
40 VPOKE 4096,1:RUN
RUN
Pass 1 A= 0
Pass 2 A= 0
```

Variables do not survive a `RUN`, so the program keeps its "second pass" flag
in video memory, which does (cell 4096 is outside everything `SCREEN 0`
uses). `A` is set to 5 before the restart and is 0 again after it.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_run.out`](../../scratchpad/kwdoc_run.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

Two rungs are not yet proven. **Every error**: `RUN`'s full set of errors has
not been enumerated, because `RUN` switches off `ON ERROR GOTO` — the very
thing the every-error rows use to catch and report an error — so `RUN 99`
inside such a row gave no reading. Its common
errors (`RUN 999`, a missing file, a bad option) are measured and agree.
And **RAM usage**.

## What we found, and how

- **`RUN` did not close open files** (fixed 2026-09-27, D-RUNCLOSE), so the
  next program could still write to a channel the last one left open. Found
  because the keyword sweep's own disk rows, each started with a `RUN`, were
  leaking channels into each other
  ([runclose_run.out](../../scratchpad/runclose_run.out)).
- **A bare `RUN` inside a program stopped with a bogus error** after a while
  (fixed 2026-09-09, D-BARERUN). The fix had been ready since August but had
  no test, because a correct `RUN` loops for ever and leaves nothing to read.
  The test that worked makes the correct behaviour visible instead: an
  endless `PRINT "X";` before the `RUN` fills the screen with X on the
  references, and showed 210 X's and an error here
  ([before](../../scratchpad/barerun.out),
  [after](../../scratchpad/barerun_after.out)).
- **`RUN 20` and `RUN "name"` typed with a space ignored their argument**
  (fixed 2026-08-31, D-RUNARG). `RUN 20` ran from the top, and `RUN "name"`,
  `RUN A$` and `RUN (A)` ran whatever program was already in memory — a wrong
  program run, the worst kind of difference. The prompt's quick path for a
  bare `RUN` took any `RUN` followed by a space
  ([spec-basic-runarg.md](../spec-basic-runarg.md)).
- **`RUN 20` inside a program did not start at line 20** (fixed 2026-08-22,
  D-RUNLINE): it was routed to a restart from the top and surfaced as a
  `Syntax error` — the in-program half of the same rule
  ([spec-basic-runline.md](../spec-basic-runline.md)).
- **`RUN "name"` printed `Illegal function call in 3346`** after the loaded
  program had run correctly, and a missing file ran the old program instead
  (fixed 2026-08-07, D-RUNTAIL, with its tape twin D-CASTAIL the same day;
  [spec-basic-runtail.md](../spec-basic-runtail.md)).
- **A bad option after the name was ignored** (fixed 2026-10-07, D-LOADTAIL):
  `RUN "A",5` printed `load error` and carried on, where both references
  raise a `Syntax error` that `ON ERROR` can catch
  ([after](../../scratchpad/loadtail_after.out)).

## Where it lives

`ex_run` in [basic/interp.asm](../../basic/interp.asm) hands over to `do_run`
in [basic/cload.asm](../../basic/cload.asm), which tells the four forms apart
and loads a file when there is one. `run_prog` and `run_prog_at` in
[basic/program.asm](../../basic/program.asm) close the files, clear the
variables and start the run loop; `dl_bare` there decides which typed `RUN`
lines take the quick path.

## Related concepts

- [The cassette](../concepts/cassette.md) — files on tape, and how BASIC finds them
- [Variables](../concepts/variables.md) — names, types, arrays, and where they live

## Tests that cover it

- `make kwsweep` — the bare (restart), line and file rows, and `RUN 999`.
- `make runline-acceptance` — `RUN 20`, `RUN20` and `RUN 20:` typed at the
  prompt.
- `make runtail-acceptance` and `make loadtail-acceptance` — `RUN "name"`,
  its missing-file case and its options.
- `make kwram` — the RAM-usage comparison.
