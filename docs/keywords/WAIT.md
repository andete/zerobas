<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `WAIT` — pause until an I/O port shows a bit pattern

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`WAIT port,mask[,xor]` reads an I/O port over and over until the byte it
reads, XORed with `xor` and ANDed with `mask`, is not zero. Then the program
carries on. It is how a BASIC program blocks on a hardware signal. zerobas
does the same test as the Philips VG-8020 and checks its arguments the same
way.

## Syntax

```
WAIT <port>,<mask>[,<xor>]
```

`xor` is optional and defaults to 0.

## Details

- **The rule:** continue as soon as `(INP(port) XOR xor) AND mask` is not
  zero; otherwise read the port again. With no `xor`, `WAIT` waits for any of
  the `mask` bits to be 1; an `xor` turns the test round for its bits, so they
  are waited for to be 0.
- **A mask of 0 never returns**, on the reference too. That is what the
  statement means, not a fault. Pick a mask the port can satisfy.
- **The canonical use** is waiting for the next video frame:
  `WAIT &H99,128` (bit 7 of the video chip's status port). It returns on the
  VG-8020 and on zerobas; the page's example does not use it, because reading
  that port also clears the flag the system's own interrupt reads.
- **The port goes through the address rule** (−32768 to 65535), as for
  [`OUT`](OUT.md); `WAIT 256*256,1` is `Overflow` (error 6).
- **The mask and the xor are bytes, 0 to 255:** `WAIT 1,256` and
  `WAIT 1,1,256` are `Illegal function call` (error 5).
- **A string anywhere** is `Type mismatch` (error 13).
- **A bare `WAIT`** is `Missing operand` (error 24); `WAIT 1` (no mask) is
  `Syntax error` (error 2).

| you write | you get |
|---|---|
| `WAIT P,V` where `V=INP(P)` and `V<>0` | returns at once |
| `WAIT P,255,V XOR 255` where `V=INP(P)` | returns at once, whatever `V` is |
| `WAIT P,0` | never returns |
| `WAIT 1,256`, `WAIT 1,1,256` | error 5, `Illegal function call` |
| `WAIT 256*256,1` | error 6, `Overflow` |
| `WAIT "A",1`, `WAIT 1,"A"`, `WAIT 1,1,"A"` | error 13, `Type mismatch` |
| `WAIT` | error 24, `Missing operand` |
| `WAIT 1` | error 2, `Syntax error` |

The whole set of errors `WAIT` can raise is {2, 5, 6, 13, 24}, the same on both
machines.

## Example

The example reads the slot register (port `&HA8`) first and builds masks it is
sure to satisfy, so it cannot hang on either machine.

```
10 P=&HA8:V=INP(P)
20 IF V=0 THEN PRINT "zero":END
30 WAIT P,V:PRINT "two"
40 WAIT P,255,V XOR 255:PRINT "three"
50 ON ERROR GOTO 90
60 WAIT P,256
70 WAIT P,1,"A"
80 END
90 PRINT "Error";ERR:RESUME NEXT
RUN
two
three
Error 5
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_wait.out`](../../scratchpad/kwdoc_wait.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: a `WAIT` uses the same amount of
free memory on both machines, but the VG-8020 writes a few work-area cells
along the way that zerobas does not.

## What we found, and how

- **`WAIT` was missing** (added 2026-09-07, D-WAIT). It was the last MSX1
  main-ROM statement zerobas did not have: `wait 0,0` was stored as a variable
  named `WAIT`. The test rows were built to finish, including the frame wait
  above, which is the one that proves `WAIT` really loops rather than falling
  straight through
  ([`wait_probe.py`](../../scratchpad/wait_probe.py)).
- **A mask over 255 hung the machine** (fixed 2026-09-28, D-WAITMASK). The
  mask was read with the address rule and cut to its low byte, so
  `WAIT 1,256` waited on a mask of 0 — for ever — where the VG-8020 stops with
  error 5. `WAIT 1,1,256` was likewise accepted. Both are byte arguments now,
  the same repair [`OUT`](OUT.md) had received three weeks earlier.
- **The third operand needed its own row.** A `WAIT` that read the `xor` and
  then ignored it would spin for ever on exactly the inputs the row uses
  (`WAIT &HA8,&H0F,&H0F`, against a port reading 240 on both machines), so the
  row only finishes if the `xor` is really applied.

## Where it lives

`ex_wait` in [basic/vdpio.asm](../../basic/vdpio.asm), beside `do_out`, whose
argument checks it shares. The wait itself is a six-byte loop.

## Tests that cover it

- `make intarg-acceptance` — the argument ranges; every row there stops in
  the parse, before any waiting.
- `make kwsweep` — a two-argument row, a three-argument row and the error rows
  for {2, 5, 6, 13, 24}.
- `make kwram` — the RAM-usage comparison.
