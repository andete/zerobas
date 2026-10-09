<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `BASE` — where each screen mode keeps its tables in video memory

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`BASE(n)` is the video-memory (VRAM) address of one of the tables a screen
mode uses — the name table, the colour table, the pattern table and the two
sprite tables. It can be read, and assigned to move a table. zerobas keeps the
same 20-entry table as the Philips VG-8020, with the same starting values, the
same checks, and the same odd behaviour when a table of the current mode is
moved.

## Syntax

```
BASE(<n>)
BASE(<n>) = <address>
```

`n` is 0 to 19. The assignment must be a statement of its own.

## Details

- **Twenty slots, five per screen mode:** `n \ 5` is the mode (0 to 3) and
  `n MOD 5` the table: 0 name, 1 colour, 2 pattern generator, 3 sprite
  attributes, 4 sprite patterns.
- **The starting values are the same on both machines:**

  | n | SCREEN | values (decimal) |
  |---|---|---|
  | 0–4 | 0 | 0, 0, 2048, 0, 0 |
  | 5–9 | 1 | 6144, 8192, 0, 6912, 14336 |
  | 10–14 | 2 | 6144, 8192, 0, 6912, 14336 |
  | 15–19 | 3 | 2048, 0, 0, 6912, 14336 |

- **Reading never depends on the current mode**; every slot can be read from
  any screen.
- **An assigned address must be below 16384 and a multiple of the table's
  step**: &H400 for a name table, &H80 for colour and sprite attributes,
  &H800 for pattern tables — except SCREEN 2's colour and pattern tables,
  which only take multiples of &H2000. Anything else is `Illegal function
  call` (error 5).
- **Assigning to a slot of another mode only stores the value.** Assigning
  to the current mode's slot also reprograms the video chip — and in SCREEN 1
  and SCREEN 2 the VG-8020 programs it from the *next* mode's slots, while
  `SCREEN` itself is unchanged. zerobas reproduces that, as measured; a plain
  `SCREEN` statement puts everything right again
  ([spec-basic-graphics-g8.md](../spec-basic-graphics-g8.md) §4.4).
- **Errors:**

| you write | you get |
|---|---|
| `BASE(20)`, `BASE(-1)`, `BASE(20)=0` | error 5, `Illegal function call` |
| `BASE(5)=-1`, `BASE(5)=&H1C01` | error 5, `Illegal function call` |
| `BASE(5)=70000` | error 6, `Overflow` |
| `BASE("A")`, `BASE(5)="A"` | error 13, `Type mismatch` |
| `BASE(5)=` | error 24, `Missing operand` |
| `A=BASE`, `LET BASE(0)=…` | error 2, `Syntax error` |

The error sets are {2, 5, 13} for reading and {5, 6, 13, 24} for assigning,
the same on both machines.

## Example

```
10 FOR I=5 TO 9:PRINT BASE(I);:NEXT
20 PRINT
30 V=BASE(5):BASE(5)=&H1C00
40 PRINT BASE(5):BASE(5)=V
50 ON ERROR GOTO 90
60 PRINT BASE(20)
70 BASE(5)=70000
80 END
90 PRINT "Error";ERR:RESUME NEXT
RUN
 6144  8192  0  6912  14336
 7168
Error 5
Error 6
```

The program runs in SCREEN 0 and moves a SCREEN 1 table, so the display is not
disturbed; line 40 puts the old value back.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_base.out`](../../scratchpad/kwdoc_base.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: reading `BASE` uses the same
amount of free memory on both machines, but the VG-8020 writes a few
work-area cells that zerobas does not, and an assignment writes different
cells on each side.

## What we found, and how

- **`BASE` used to answer 0 for everything** (fixed 2026-07-22, graphics slice
  G8). It was a placeholder from the time zerobas had no per-mode table.
  Measuring the VG-8020 showed its table and zerobas's were already identical
  at power-on, so the real `BASE` became a plain read of it, and the
  assignment was added with the reference's checks.
- **The SCREEN 1/2 reprogramming quirk is reproduced on purpose** (G8,
  decision D8-1). It was established with a poisoned value in the next
  mode's slot, so it could not be a coincidence of matching defaults.
- **The argument checks were suspected and found sound** (2026-09-09,
  D-VDPDOM). The parser hands over a 16-bit number, which looked like the
  `POKE` fault; the check turned out to sit one layer down, and every
  out-of-range case tried agreed on all three machines
  ([`vdpdom_run.out`](../../scratchpad/vdpdom_run.out)).

## Where it lives

`ev_f_base` and `ex_base_assign` (`g8_assign`) in
[basic/graphics.asm](../../basic/graphics.asm), dispatched from
[basic/expr.asm](../../basic/expr.asm) and
[basic/interp.asm](../../basic/interp.asm); the table work and the checks are
in the graphics tenant, [sub/graphics.asm](../../sub/graphics.asm). The table
is the published work-area cells at `&HF3B3`, two bytes per slot.

## Tests that cover it

- `make graphics-acceptance` — the table, the assignment rules and the
  reprogramming quirk.
- `make kwsweep` — a read row (`BASE(2)`), an assignment read back
  (`BASE(5)`), and the error rows for both forms.
- `make kwram` — the RAM-usage comparison.
