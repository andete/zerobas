<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `GOSUB` — call a subroutine

> **Status (2026-10-16):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
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
- **Anything after the line number in the same statement is ignored.**
  `GOSUB 100 ZZ` is accepted on both references; the `ZZ` is never run, and
  a `:` statement after it still runs when the subroutine returns.
- **Nesting is limited by free memory**, not by a fixed count. A subroutine
  that keeps calling itself ends in `Out of memory` (error 7).
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

## Differences from the reference

None known in behaviour.

The one rung not yet proven is **RAM usage**. Each open `GOSUB` now uses 7
bytes of free memory, as on the VG-8020 (since 2026-10-17; it was 8). A
runaway recursion still stops a little sooner here -- 4069 calls against 4084
after `CLEAR 200` ([`gosubedge_7b.out`](../../scratchpad/gosubedge_7b.out)) --
because zerobas keeps a slightly larger reserve for its own stack before it
refuses a frame (256 bytes, the reference about 130).

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
