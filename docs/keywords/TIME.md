<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `TIME` — the frame counter, readable and settable

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`TIME` is a counter that goes up by one at every video frame interrupt — 50
times a second on the VG-8020, a European (PAL) machine. A program reads it
like a variable (`T=TIME`) and sets it with `TIME=n`. zerobas reads and writes
the same counter, at the same published address, with the same rules as the
Philips VG-8020.

## Syntax

```
TIME
TIME = <numeric expression>
```

Two forms: reading it anywhere a number can stand, and the assignment, which
must be a statement of its own.

## Details

- **It counts frames, not seconds**, and how fast depends on the machine's
  video interrupt, not on BASIC. It wraps from 65535 back to 0 with no error.
- **The value is 0 to 65535, never negative.** `TIME=40000:PRINT TIME` prints
  40000. It is therefore not an integer: `A%=TIME` is `Overflow` (error 6) once
  the counter is above 32767.
- **The counter is the published `JIFFY` cell** (`&HFC9E`, two bytes), so
  `PEEK` and `POKE` see and change the same value.
- **Assigning truncates toward zero** after wrapping values of 32768 and up by
  −65536: `TIME=1.6` stores 1, `TIME=-1` stores 65535. Outside −32768 to 65535
  is `Overflow` (error 6).
- **It stops when the frame interrupt is switched off** (bit 5 of video
  register 1, `VDP(1)`), on both machines — which is what proves the counter
  is driven by the real interrupt.
- **Errors:**

| you write | you get |
|---|---|
| `TIME=70000`, `TIME=-32769` | error 6, `Overflow` |
| `TIME="A"`, `A$=TIME` | error 13, `Type mismatch` |
| `TIME=` | error 24, `Missing operand` |
| `LET TIME=5`, `TIME 5`, a bare `TIME` | error 2, `Syntax error` |

`TIME` can only be assigned by a statement that starts with it: `FOR TIME=…`,
`READ TIME` and `SWAP TIME,A` are `Syntax error` too. The error sets are {13}
for reading and {6, 13, 24} for assigning, the same on both machines.

## Example

`TIME` keeps counting while the program runs, so the example does not print
it directly: it prints a value that cannot change within two seconds, and a
comparison.

```
10 TIME=30000
20 PRINT INT(TIME/100)
30 T=TIME:FOR I=1 TO 400:NEXT
40 PRINT TIME>T
50 ON ERROR GOTO 90
60 TIME=70000
70 A$=TIME
80 END
90 PRINT "Error";ERR:RESUME NEXT
RUN
 300
-1
Error 6
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_time.out`](../../scratchpad/kwdoc_time.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: reading or setting `TIME` uses
the same amount of free memory on both machines, but the work-area cells each
side writes along the way differ.

## What we found, and how

- **`TIME` did not exist** (added 2026-07-26). zerobas read it as the variable
  `TI`, which is always 0, so a loop like `IF TIME-T<400 THEN …` never ended —
  silently. Measuring the VG-8020 first settled the details above: the value
  is unsigned, the write uses the same wrap-then-truncate rule as `POKE`, and
  the four error codes ([spec-basic-time.md](../spec-basic-time.md)).
- **The first measurement of the write rule was wrong.** It read as rounding
  (`TIME=1.6` → 2) because the counter can tick between the assignment and the
  `PRINT`. Re-measured with a deliberate delay before each assignment and the
  smallest reading kept, every case fits truncation.
- **`TIME=` with nothing after it** is raised as `Missing operand` at the
  assignment itself (D-TIME-3), because at the time zerobas still accepted a
  bare `A=` silently.
- **A read could be torn.** The counter is two bytes and the interrupt can
  change it between them; zerobas reads and writes it with interrupts briefly
  off (D-TIME-2).

## Where it lives

The read is `ev_f_time` in [basic/expr.asm](../../basic/expr.asm), sharing its
tail with `ERL`; the assignment is `ex_time_assign` in
[basic/time.asm](../../basic/time.asm), dispatched from
[basic/interp.asm](../../basic/interp.asm) when a statement starts with `TIME`.

## Related concepts

- [Interrupts and traps](../concepts/interrupts-and-traps.md) — what runs between statements

## Tests that cover it

- `make time-acceptance` — the token, the read, the write rule and the error
  surface, against the VG-8020.
- `make kwsweep` — a counter-advances row, a write-and-read-back row with two
  different values, and the error rows for {6, 13, 24}.
- `make kwram` — the RAM-usage comparison.
