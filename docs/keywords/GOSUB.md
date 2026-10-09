<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `GOSUB` — call a subroutine

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
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

The one rung not yet proven is **RAM usage**, and here there is a measured
gap: each open `GOSUB` uses 8 bytes of free memory on zerobas and 7 on the
VG-8020 (`FRE(0)` read inside a running program, 2026-09-26). Joost ruled on
2026-09-27 that zerobas should *"shrink ours only"* — never use more than the
reference. Taking the eighth byte out turned out to need a redesign of every
kind of stack frame, and that price is back with him. zerobas also has less
free memory than the VG-8020 overall, so a runaway recursion reaches
`Out of memory` at a smaller depth.

## What we found, and how

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
- `make ramfree-acceptance` — a recursion to `Out of memory` that must not
  disturb other memory.
- `make kwram` — the RAM-usage comparison.
