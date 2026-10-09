<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `VDP` — read or write a video chip register

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`VDP(n)` gives access to the registers of the video chip (the VDP, a
TMS9918-family chip on an MSX1). `A=VDP(n)` reads register `n`;
`VDP(n)=v` writes it. Registers 0 to 7 control the screen mode, the table
addresses and the colours; `VDP(8)` is the status register. zerobas behaves
like the Philips VG-8020 in every case we have measured.

## Syntax

```
VDP(<register>)                  -- as a value, in an expression
VDP(<register>) = <value>        -- as a statement
```

## Details

- **Registers 0–7 cannot be read from the chip itself**, on any MSX. A read
  returns the copy the system keeps in memory of the last value written; a
  write updates that copy *and* the chip.
- **`VDP(8)` is the status register** — the copy the system takes at every
  frame interrupt, not a live read of the chip. It is read-only:
  `VDP(8)=0` is error 5. It is where a sprite collision shows.
- **The write really reaches the chip.** Clearing bit 5 of register 1
  (`VDP(1)=VDP(1) AND 223`) turns off the frame interrupt; `TIME` then stops
  counting on both machines, which only the chip can cause. Be careful: with
  that bit clear the keyboard is not read either, so restore the register
  before the program ends.
- **Index and value are truncated toward zero, then checked**: `VDP(3.9)`
  reads register 3, `VDP(-0.4)` register 0, and `VDP(0)=255.6` writes 255.
- **It is not a variable.** `LET VDP(0)=2`, `FOR VDP(0)=…` and
  `SWAP VDP(0),A` are syntax errors; `VDP(0)=` with nothing after is
  `Missing operand`.
- Its sibling `BASE(n)` reads and writes the table addresses the same way.

| you write | you get |
|---|---|
| `A=VDP(9)`, `A=VDP(-1)` | error 5, `Illegal function call` |
| `VDP(8)=0`, `VDP(0)=256`, `VDP(0)=-1` | error 5, `Illegal function call` |
| `A=VDP("A")`, `VDP(7)="A"` | error 13, `Type mismatch` |
| `A=VDP`, `LET VDP(0)=2`, `VDP(0,1)=2` | error 2, `Syntax error` |
| `VDP(7)=` | error 24, `Missing operand` |

The errors measured for `VDP` are {2, 5, 13} when reading and {5, 13, 24}
when writing, the same on both machines.

## Example

```
10 PRINT VDP(1)
20 V=VDP(7):VDP(7)=5:A=VDP(7)
30 VDP(7)=V:PRINT A
40 ON ERROR GOTO 70
50 VDP(8)=0
60 END
70 PRINT "Error";ERR:RESUME NEXT
RUN
 240
 5
Error 5
```

Register 1 reads 240 in SCREEN 0. Register 7 holds colours (the backdrop
among them), so the program saves it, writes 5, reads 5 back and restores it.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_vdp.out`](../../scratchpad/kwdoc_vdp.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **`VDP` arrived on 2026-07-22** (graphics slice G8). Before that it was not
  a keyword at all. The reference was measured first: which registers, what
  a read returns, that `LET VDP(0)=2` is refused, and that the index is
  truncated before it is checked
  ([spec-basic-graphics-g8.md](../spec-basic-graphics-g8.md)).
- **"No test can see the chip" was too pessimistic.** The first write test
  could only read the memory copy back. Joost, 2026-09-14: *"if you choose a
  clever write, you can see the effects in the visual appearance of the
  screen"*. The test that followed stops the frame interrupt and watches
  `TIME` freeze — something only a write that reached the chip can do.
- **The argument ranges were checked again** (2026-09-09, D-VDPDOM) after the
  same kind of code in `POKE`/`VPOKE`/`OUT` turned out to accept bad values.
  Here the check sits one layer further down and was already right: all
  seven cases agree on all three machines.
- **A program that leaves the frame interrupt off** (2026-09-24, D-VDPIE):
  on both machines the keyboard then stops working — no difference a user
  can see.

## Where it lives

In [basic/graphics.asm](../../basic/graphics.asm): `ev_f_vdp` and `g8_fn` read
a register; `ex_vdp_assign` handles `VDP(n)=v`, reached from the statement
dispatch because there is no separate statement token. The write itself is
`gfx_vdp_wr` in [sub/graphics.asm](../../sub/graphics.asm).

## Related concepts

- [Screen modes](../concepts/screen-modes.md) — the four MSX1 displays

## Tests that cover it

- `make graphics-acceptance` — reads, writes and the error surface against
  the VG-8020, including the frame-interrupt check.
- `make kwsweep` — the value of `VDP(1)`, a write read back with two
  different values, the write that freezes `TIME`, and the error rows.
- `make kwram` — the RAM-usage comparison.
