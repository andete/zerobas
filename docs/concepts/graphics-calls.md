<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# The graphics calls — pixels, cursor and PAINT in the BIOS

> **Status (2026-11-19):** the shared facts of the graphics region's nineteen BIOS calls (MAPXYC,
> FETCHC, STOREC, SETATR, GTASPC, SCALXY, the six cursor moves, READC, SETC, NSETCX, GRPPRT, PNTINI,
> SCANR, SCANL). Each call's state, and the differences its page names, are in the generated
> [BIOS index](../bios/index.md), never repeated here. Speed is deliberately left out of these docs
> until on-par speed is established.

## Summary

BASIC's graphics statements (PSET, LINE, CIRCLE, PAINT, DRAW, PRINT #) reach the screen through a
small set of BIOS calls that work on one **current graphics position** and one **colour**. MAPXYC
turns a coordinate into the position; the cursor moves step it a pixel at a time; READC, SETC and
NSETCX read and set pixels there; GRPPRT draws a character; PNTINI, SCANR and SCANL are PAINT's
helpers. They work in the two graphics modes, SCREEN 2 (256 x 192 pixels, 2 colours per 8-pixel
cell row) and SCREEN 3 (64 x 48 blocks of 4 x 4 pixels, any colour each).

zerobas draws the same pixels in the ordinary cases; most of its differences are at edges -- moved
tables, colours over 15, off-screen positions -- and in the flags left behind. The one that showed
in ordinary use, **D-SETCLAST** (setting a SCREEN 2 cell row's last background pixel in a third
colour recoloured its other seven pixels), is fixed, for SETC and NSETCX alike (2026-11-19).

## How it works

Every statement below carries its source:
- **[P]** the published interface, the MSX2 Technical Handbook (rated in
  [allowed-sources.md](../allowed-sources.md));
- **[M]** measured by this project (the per-call pages);
- **[A]** not yet established.

### The current position and colour

- **CLOC** ($F92A, 2 bytes) is the VRAM address of the pattern byte that holds the pixel, **CMASK**
  ($F92C) the pixel's bit in it [P]. In SCREEN 2 CMASK is one bit, $80 the leftmost pixel; in SCREEN
  3 it is a nibble mask, $F0 for the left block of the byte, $0F for the right one [M]
  ([MAPXYC](../bios/MAPXYC.md)). FETCHC / STOREC read and write the pair [M].
- **ATRBYT** ($F3F2) is the colour the pixel calls write [P]; SETATR sets it, refusing 16 and up with
  the carry [M] ([SETATR](../bios/SETATR.md)). GRPPRT draws in FORCLR and leaves ATRBYT = FORCLR [M].
- **MAPXYC** places the position: in SCREEN 2 at GRPCGP + (Y AND $F8) x 32 + (X AND $F8) + (Y AND 7);
  in SCREEN 3 at MLTCGP + ((Y / 8) AND 7) x 256 + (X / 2) x 8 + (Y AND 7), in block coordinates [M].
  **SCALXY** clips a coordinate to the screen first, and outside SCREEN 2 divides it by 4 into blocks
  [M] ([SCALXY](../bios/SCALXY.md)).

### Moving the position

RIGHTC / LEFTC step the mask (rotating it, moving CLOC by 8 when it wraps), UPC / DOWNC step CLOC by
one line (by $F9 across a cell's edge), and none of them checks an edge [M]. TUPC / TDOWNC check:
they stop with the carry set at the top (CLOC below GRPCGP + $100) or the bottom (CLOC at GRPCGP +
$1700 or more), both unsigned comparisons; SCREEN 3's test ignores MLTCGP [M]
([TUPC](../bios/TUPC.md), [TDOWNC](../bios/TDOWNC.md)).

### Reading and setting pixels

- **The colour byte** of a SCREEN 2 pattern byte is at its address **XOR $2000** -- GRPCOL and
  GRPCGP are not used, whatever they hold [M] ([READC](../bios/READC.md)). With the published tables
  (patterns at $0000, colours at $2000) that is the colour table; with a pattern table moved to
  $2000 it is $0000.
- **Setting a pixel in SCREEN 2** changes two colours sharing one byte, so SETC chooses [M]
  ([SETC](../bios/SETC.md)): ATRBYT is the background colour -- clear the bit; it is the foreground --
  set it; every other bit of the byte is set -- clear the bit and make ATRBYT the background; else
  set the bit and make ATRBYT the foreground. NSETCX does the same for a run of pixels, a byte at a
  time, and writes a whole byte as pattern $00 with colour byte ATRBYT [M]
  ([NSETCX](../bios/NSETCX.md)). GRPPRT uses the same choice without the last two refinements [M]
  ([GRPPRT](../bios/GRPPRT.md)).
- **In SCREEN 3** a pixel is a nibble: ATRBYT goes into it, a low nibble taking the whole ATRBYT ORed
  in [M].

### Characters and PAINT

- **GRPPRT** draws the character in A at GRPACX / GRPACY ($FCB7 / $FCB9) from the font CGPNT points
  at, line by line, moving down as TDOWNC does; it moves GRPACX on 8 pixels (32 in SCREEN 3) and
  wraps; CR is a line feed [M] ([GRPPRT](../bios/GRPPRT.md)).
- **PAINT** stops at BDRATR ($FCB2). PNTINI sets it: in SCREEN 2 to ATRBYT (SCREEN 2 paints up to
  its own colour), in SCREEN 3 to A [M] ([PNTINI](../bios/PNTINI.md)). SCANR skips border pixels and
  counts the run to the right, painting it on request; SCANL counts to the left and paints from
  there [M] ([SCANR](../bios/SCANR.md), [SCANL](../bios/SCANL.md)).

### Interrupts

Every call that touches VRAM returns with interrupts **on**; the position calls (MAPXYC, the moves,
FETCHC / STOREC, SETATR, GTASPC, SCALXY) keep the interrupt state [M].

### What a probe may read

The probes set the work area and every VRAM byte by hand and read back registers, RAM and VRAM
through the VDP's ports ([docs/spec-method.md](../spec-method.md)). GRPPRT's probe points CGPNT at
a font of its own in RAM, so no ROM font byte is involved.

## Differences from the reference

Each call's differences are on its own page, never repeated here; the
[BIOS index](../bios/index.md) lists them per call.

## What we found, and how

Six probes (XGFX1-6) measured the nineteen calls on the VG-8020, alone and with a disk interface,
with VRAM filled so that every 1 KB block sums differently and every pixel has a computable colour.
The rules are checked against every case ([docs/spec-method.md](../spec-method.md)).

## How zerobas does it

The graphics calls are C-BIOS's, in the main ROM
([cbios-repack-provenance.md](../cbios-repack-provenance.md)).

## Related pages

- [The BIOS](bios.md): what every BIOS call has in common.
- [Screen modes](screen-modes.md): the VDP tables these calls draw into.
- The calls: [MAPXYC](../bios/MAPXYC.md), [FETCHC](../bios/FETCHC.md), [STOREC](../bios/STOREC.md),
  [SETATR](../bios/SETATR.md), [GTASPC](../bios/GTASPC.md), [SCALXY](../bios/SCALXY.md),
  [RIGHTC](../bios/RIGHTC.md), [LEFTC](../bios/LEFTC.md), [UPC](../bios/UPC.md), [TUPC](../bios/TUPC.md),
  [DOWNC](../bios/DOWNC.md), [TDOWNC](../bios/TDOWNC.md), [READC](../bios/READC.md),
  [SETC](../bios/SETC.md), [NSETCX](../bios/NSETCX.md), [GRPPRT](../bios/GRPPRT.md),
  [PNTINI](../bios/PNTINI.md), [SCANR](../bios/SCANR.md), [SCANL](../bios/SCANL.md).

## Tests that cover it

**`spec-live`** ([tools/spec_live.py](../../tools/spec_live.py), in every gate) re-runs every rule
of the nineteen call pages on zerobas.
