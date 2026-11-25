<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `GOSUB` — call a subroutine

> **Spec:** DRAFT 1 (2026-11-25) — 13 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kgosub.py`](../../probes/basic/spec/kgosub.py), with GOTO's, GOSUB's and RETURN's cases
> together); every rule is executable and every recorded output is read by one. Goldfish pass 1 acted on
> (2026-11-25: the model is now an interpreter, 5 more cases); not yet re-reviewed ([the keyword
> plan](spec-plan.md)).
>
> **Status (2026-11-25):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✗ (D-GOSUBFRAME).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`GOSUB 100` jumps to line 100 and remembers where it came from; the
[`RETURN`](RETURN.md) at the end of the subroutine comes back to the statement
after the `GOSUB`. Subroutines may call subroutines. zerobas behaves like the
Philips VG-8020 in every case we have measured, errors included.

## Syntax

```
GOSUB <line number>
ON <expression> GOSUB <line number>[,<line number>...]
```

The line number is a constant; `GOSUB A` and `GOSUB "100"` are not allowed.

## Details

- **`RETURN` comes back to the next statement**, not the next line:
  `GOSUB 100:PRINT "back"` prints `back`.
- **The line number is read as GOTO's**: more digits are part of it, even
  across a space (`GOSUB 230 5` is `GOSUB 2305`); anything else after it is
  ignored. `GOSUB 100 ZZ` is accepted on both references; the `ZZ` is never
  run, and a `:` statement after it still runs when the subroutine returns.
- **Nesting is limited by free memory**, not by a fixed count. A subroutine
  that keeps calling itself ends in `Out of memory` (error 7) -- an older
  probe's measurement ([`gosubedge_7b.out`](../../scratchpad/gosubedge_7b.out)); the spec
  probe's guard stops at 21 levels (Open).
- **`ON n GOSUB 100,200,300`** calls the n-th line in the list. `n` is
  truncated, not rounded (`ON 1.7` takes the first). `ON 0` or an `n` past the
  end of the list does nothing and the program carries on; a negative `n` or
  one above 255 is `Illegal function call` (error 5), and one beyond the
  integer range is `Overflow` (error 6). [`GOTO`](GOTO.md) has the same `ON`
  form.
- **A `GOSUB` remembers which loops were open.** A `RETURN` throws away the
  `FOR` loops opened inside the subroutine and keeps the ones opened before
  the call.

### Errors

| you write | you get |
|---|---|
| `GOSUB 99` when there is no line 99 | 8 `Undefined line number` |
| `GOSUB 70000` | 8 `Undefined line number` — a line number stops before it would pass 65529, so this reads as `GOSUB 7000` |
| `GOSUB`, `GOSUB "A"`, `GOSUB -1` | 2 `Syntax error` |
| a subroutine that never returns, calling itself | 7 `Out of memory` |

The whole set of errors `GOSUB` raises is {2, 8}, the same on both machines;
`Out of memory` depends on how much memory is free (see *Differences*).

## Example

```
10 FOR I=1 TO 3:GOSUB 100:NEXT
20 ON 2 GOSUB 200,300
30 ON ERROR GOTO 400
40 GOSUB 999
50 END
100 PRINT "Square of";I;"is";I*I
110 RETURN
200 PRINT "One":RETURN
300 PRINT "Two":RETURN
400 PRINT "Error";ERR:RESUME NEXT
RUN
Square of 1 is 1
Square of 2 is 4
Square of 3 is 9
Two
Error 8
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_gosub.out`](../../scratchpad/kwdoc_gosub.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/gosub_rules.py`](../../probes/basic/spec/gosub_rules.py), model in
[`kgosub_model.py`](../../probes/basic/spec/kgosub_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does.

**Evidence.** One probe, [`probes/basic/spec/kgosub.py`](../../probes/basic/spec/kgosub.py) (on the shared RAM-record
harness [`ramrec.py`](../../probes/basic/spec/ramrec.py)), typed on both machines as two programs, groups FX (the first
run's cases) and FY (goldfish pass 1's separating cases); run file
[`scratchpad/KGS_run1.out`](../../scratchpad/KGS_run1.out) (2026-11-25). Each case is a block of 30 lines from its base
n: line n starts from nothing (`CLEAR`, `ON ERROR` set again), runs the statement(s) under test and ends `GOTO n+25`;
the case's own target lines sit at n+5 .. n+20 (an FY case may add an ABSOLUTE line, 6553 or 7000, far past every
case); n+25 records the first and the last error (RESUME NEXT carries on after one), a counter WN% and WP%, the bits
of the lines the case reached (2 the rest of line n after a GOSUB, 4 / 8 / 16 lines n+5 / n+10 / n+15) -- so a rule
says WHICH lines ran. A loop that could run for ever carries the guard `ON -(WN%>20) GOTO n+25` (21 = "more than 20").
**The frame uses GOTO**, the keyword under test, on purpose: a frame GOTO that went wrong would land outside its case,
and the record frame's own check refuses such a run -- it cannot produce a plausible wrong record. The model,
[`kgosub_model.py`](../../probes/basic/spec/kgosub_model.py), is an INTERPRETER: it runs each case's lines with the laws
the rules state (the line number's reading, one stack for GOSUB and FOR, RETURN's order of checks) and holds no
per-case answer.
- **[KGS FX *i*]** (GOSUB):
  9: `GOSUB {L5}:WP%=WP% OR 2` (line n+5: `WP%=WP% OR 4:RETURN`) -- GOSUB / RETURN comes back after the GOSUB
  10: `GOSUB {L5}:WP%=WP% OR 2` (line n+10: `WP%=WP% OR 8:RETURN`; line n+5: `WP%=WP% OR 4:GOSUB {L10}:WP%=WP% OR 16:RETURN`) -- nested GOSUBs
  11: `WN%=0:GOSUB {L5}` (line n+10: `RETURN`; line n+5: `WN%=WN%+1:IF WN%<5 THEN GOSUB {L5}`) -- recursion five deep, each level falling through to RETURN
  12: `GOSUB 65000` -- a line that does not exist
  13: `GOSUB` -- no line number
  14: `GOSUB {L5}:WP%=WP% OR 2` (line n+5: `WP%=WP% OR 4`) -- a subroutine without RETURN (runs on into the record)
  15: `WN%=0:GOSUB {L5}` (line n+5: `WN%=WN%+1:<guard>:GOSUB {L5}`) -- unbounded recursion (the guard ends it)
  26: `GO SUB {L5}:WP%=WP% OR 2` (line n+5: `WP%=WP% OR 4:RETURN`) -- GO SUB with a space
- **[KGS FY *i*]** (GOSUB, goldfish pass 1):
  7: `WN%=0:GOSUB {L5}:WP%=WP% OR 2` (line n+10: `WN%=WN%+10:RETURN`; line n+5: `WN%=WN%+1:IF WN%<3 THEN GOSUB {L5}`) -- recursion three deep, the returns counted
  8: `GOSUB 65000:WN%=WN%+1:RETURN` -- GOSUB to a missing line pushes no frame
  9: `IF 1 THEN GOSUB {L5}:WP%=WP% OR 2` (line n+5: `RETURN`) -- GOSUB in a THEN clause comes back to it
  10: `GOSUB {L5a} {L5b}:WP%=WP% OR 2` (line n+5: `WP%=WP% OR 4:RETURN`) -- GOSUB: digits joined across a space
  11: `GOSUB {L5} ZZ:WP%=WP% OR 2` (line n+5: `WP%=WP% OR 4:RETURN`) -- GOSUB: letters after the line number

**Controls** ([`kgosub_controls.py`](../../probes/basic/spec/kgosub_controls.py)): each changes ONE law of the interpreter model and runs over the reference's cases: “a RETURN unwinds every GOSUB” is FALSE on 3 of the 9 cases R-GOSUB-CALL selects (e.g. KGS FX 10); “the number stops at a space” is FALSE on 1 of the 9 cases R-GOSUB-CALL selects (e.g. KGS FY 10); “the frame is pushed before the line is looked up -- zerobas's” is FALSE on 1 of the 4 cases R-GOSUB-ERRORS selects (e.g. KGS FY 8).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/gosub_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/gosub_rules.py --write` -->

**2 rules; 2 hold on the reference. Of the 52 recorded outputs (each case's first and last error, WN% (a counter; 21 = the probe's guard ended a loop that did not stop) and WP% (the bits of the lines the case reached)): 52 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. The call

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-GOSUB-CALL** GOSUB n runs line n on; RETURN continues after the GOSUB on its own line -- also inside a THEN clause, whose rest then runs. GOSUBs nest and recurse, each RETURN closing one level (three deep: three RETURNs); recursion without a RETURN runs on (the guard stopped it at 21 levels, no error). A subroutine without RETURN simply runs on. The line number is read as GOTO's (digits joined across a space; letters after it ignored). | 9 | ✓ | ✓ |

#### 2. Errors

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-GOSUB-ERRORS** A line that does not exist is error 8, and NO frame is pushed (a RETURN after it is error 3); no line number is error 2; `GO SUB` with a space is error 2 (only GO TO has a spelled-out form). | 4 | ✓ | ✗ 1: KGS FY 8 |

<!-- RULES END -->

## Differences from the reference

- **A GOSUB to a missing line pushes a frame** (rule R-GOSUB-ERRORS, case KGS FY 8;
  [D-GOSUBFRAME](../../todo/open/D-GOSUBFRAME.md)): after `GOSUB 65000` (error 8 on both), a
  RETURN is error 3 on the reference; zerobas's RETURN comes back to the failed GOSUB first.

The one rung not yet proven is **RAM usage**. Each open `GOSUB` now uses 7
bytes of free memory, as on the VG-8020 (since 2026-10-17; it was 8). A
runaway recursion still stops a little sooner here -- 4069 calls against 4084
after `CLEAR 200` ([`gosubedge_7b.out`](../../scratchpad/gosubedge_7b.out)) --
because zerobas keeps a slightly larger reserve for its own stack before it
refuses a frame (256 bytes, the reference about 130).

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] The recursion limit against free memory (the Differences paragraph's 4069 / 4084 comes from an older probe).

## What we found, and how

- **A `GOSUB` cost one byte more than on the reference** (fixed 2026-10-17).
  zerobas's frame kept two pointers: the previous `FOR` floor and the previous
  `GOSUB` frame. Between those two there is never more than one trap record
  (3 bytes), so the second pointer became a one-byte distance from the first,
  and the frame is 7 bytes. A runaway recursion now reaches 4069 calls instead
  of 3561. The check that a `GOSUB` inside an `ON INTERVAL` handler still
  returns correctly is the trap gate's `int.nest` row; the existing trap tests
  did not notice when that one byte was cut.

- **A `GOSUB` with little memory left was `Out of memory`, and a trapped
  overflow left its calls standing** (fixed 2026-10-16, D-GOSUBOOM). Head over
  Heels lowers the top of memory with its own `CLEAR` and then calls a
  subroutine with about 670 bytes free: zerobas refused, because it kept 768
  bytes clear below every call; the VG-8020 refuses only with about 130 left.
  Those 768 bytes existed so that, after a recursion ran out of memory and the
  error was trapped, expressions could still run with every call still open --
  but the VG-8020 does not keep them open: in the handler of that error, a
  `RETURN` is `RETURN without GOSUB`, where zerobas went back into the recursion
  and repeated the error for ever. zerobas now closes every open `GOSUB` and
  `FOR` on that error, as the reference does, and keeps 256 bytes clear. A
  trapped error that is not this overflow still keeps its calls on both
  ([before](../../scratchpad/gosubedge_probe.out),
  [after](../../scratchpad/gosubedge_after.out),
  [`gosuboom_after.out`](../../scratchpad/gosuboom_after.out)).
- **A jump stored as a line POINTER was a Syntax error** (fixed 2026-10-12,
  D-BASICROM). After a jump runs, the reference rewrites its operand from a line
  number into the address of the line, in the program text itself; a program
  stored after it ran -- a BASIC cartridge, a file saved from a real MSX --
  carries that form, and zerobas refused it: Vampier's 3D Golf Simulation
  cartridge stopped at its first GOSUB. zerobas now follows it (it never writes
  it). `RESTORE` is not one of them: the reference answers a pointer there
  with `Undefined line number`, and so does zerobas
  ([`basicrom_gate.out`](../../scratchpad/basicrom_gate.out)).
- **`GOSUB` could only nest 8 deep** (fixed 2026-09-04, D-CTLPOOL). zerobas
  kept subroutine calls in a fixed table of eight; the VG-8020 measured about
  4000 at power-on and the CF-3300 about 3300. Calls now live in one pool
  shared with `FOR` loops and bounded by memory, as on the reference
  ([spec-basic-trapsvc.md](../spec-basic-trapsvc.md) §17). On 2026-09-12
  (D-SPMERGE) that pool and the processor's own stack became one.
- **A tail after the line number broke the return** (fixed 2026-09-08,
  D-FLOWTAIL). `GOSUB 100 ZZ` ran the subroutine, then `RETURN` came back onto
  the `ZZ` and raised `Syntax error`. One more row separated the two possible
  rules: `GOSUB 100 ZZ:A=A+10` adds 10 on both references, so the return point
  is the end of the *statement*, not the end of the line
  ([before](../../scratchpad/flowtail_sep.out),
  [after](../../scratchpad/flowtail_after.out)).
- **`RETURN` kept loops the subroutine had opened** (fixed 2026-08-19,
  D-FORRET); see [`RETURN`](RETURN.md).
- **`ON n GOSUB`'s selector was checked on 2026-08-30** (D-ONDOM) and found
  correct everywhere: 15 rows, no difference
  ([spec-basic-ondom.md](../spec-basic-ondom.md)).

## Where it lives

`ex_gosub` and `gosub_push` in [basic/program.asm](../../basic/program.asm);
`ON … GOSUB` is `ex_on`, `eon_seek_nth` and `eon_gosub` in the same file. The
line number is read by the shared `req_lineno`, and the statement tail is
skipped by `skip_stmt_tail`, both in [basic/interp.asm](../../basic/interp.asm).
How the reference lays out its frames, read from RAM only, is in
[reference-stack-frames.md](../reference-stack-frames.md).

## Related concepts

- [Interrupts and traps](../concepts/interrupts-and-traps.md) — what runs between statements
- [The memory map](../concepts/memory-map.md) — where BASIC keeps things in RAM

## Tests that cover it

- `make kwsweep` — the everyday row (a subroutine that sets a variable the
  caller prints), the `ON 2 GOSUB` row, and the error rows for {2, 8}.
- `make ctllim-acceptance` — the frame pool driven to its floor.
- `make gosuboom-acceptance` — a call near the memory edge, and what a trapped
  overflow leaves (`RETURN` / `NEXT` in its handler).
- `make ramfree-acceptance` — a recursion to `Out of memory` that must not
  disturb other memory.
- `make kwram` — the RAM-usage comparison.
