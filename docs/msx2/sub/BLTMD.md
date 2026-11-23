<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `BLTMD` (sub-ROM $01A5) — load a disk file into RAM

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubbltd.asm](../../../probes/bios/spec/xsubbltd.asm), [scratchpad/AE_xsubbltd_msx2.out](../../../scratchpad/AE_xsubbltd_msx2.out), decoded with the files read back from each machine's disk image by `scratchpad/xsubbltd.py` into [scratchpad/AE_xsubbltd_msx2_decoded.out](../../../scratchpad/AE_xsubbltd_msx2_decoded.out)). `[XD n]` = that run's case n.
>
> Goldfish pass 1 (test writer) 2026-11-23: 5 findings, 2 measured, 2 moved to open, 1 corrected in wording (cases XD 33, 34 added for it).

## Summary

`BLTMD` copies the bytes of the file FNPTR names into RAM from SPTR, as they are in the file — a BSAVE header is
loaded as data, not obeyed — and stops at the end of the file or after EPTR − SPTR + 1 bytes (mod 64 K),
whichever comes first. A missing file goes to BASIC's error handler through H.ERRO with error 53, an unquoted
name with error 13. It does not change the block; it writes SPTR to the two bytes after it.

## The specification

The block, the array and the recording: [block-transfer.md](../concepts/block-transfer.md).

**How it was called** [M]: from H.STKE (every ROM, the disk ROM included, initialised; BASIC's work area set
up), through EXTROM with IX = the entry, A $5A, F $01 (carry set), BC $BC0C, DE $DE0E, interrupts ON, block
fields the call does not name filled with garbage ($51 + offset), and H.ERRO hooked to record E and abandon the
case. Drive A held an image the probe's script made. Calls from MSX-DOS, or with interrupts off, were not made.
What each case records, and what it does not, is in [block-transfer.md](../concepts/block-transfer.md#how-the-disk-cases-are-recorded):
the block and the two bytes either side of it, LOGOPR and a 96-byte RAM window round SPTR — not VRAM or the time
taken.

### Interface

- **In:** HL = $F562 [P A3 §3]; FNPTR at +0, a dummy at +2, SPTR (the start) at +4, EPTR (the end) at +6 [P A3
  §3; M XD 3]. FNPTR: a quoted name, then 0 [P A3 §3; M XD 3]. Whether HL or $F562 is read was measured for
  BLTDM only (HL is read there, [BLTDM](BLTDM.md)); for BLTMD it is [A] (MD-08).
- **Out, normal return:** carry reset [P A3 §3; M XD 3-6, 8, 18, 34: entered with carry set, F $54 after].
  Interrupts ON after (entered on) [M].
- **Registers on return (not a contract):** A $00, BC $0300, DE $F2C4, HL $0300, IX $56D3 on all three
  references [M XD 3-6, 8, 18, 34], from one entry state (A $5A, BC $BC0C, DE $DE0E). A caller should treat every
  register but F's carry as destroyed [A].
- **Out, on an error:** a missing file calls H.ERRO with E = 53 (File not found) [M XD 7], the name unquoted
  (`DM3.BIN`, 0) with E = 13 (Type mismatch) [M XD 33]; interrupts OFF, nothing loaded, $F571-$F572 not written
  [M XD 7, 33]; a call right after the missing file works normally — no file left open [M XD 8].

### Behaviour

- **The file's bytes go to SPTR unchanged** [M]: DM1.BIN (64 bytes) to $9200 [M XD 3]; RAWDATA.BIN, a file with
  no header, to $9500 [M XD 6]; BSAVED.BIN, a BSAVE file ($FE, start $9420, end $942F, exec $9420, 16 bytes) to
  $9400 **with its 7-byte header** — $9400 = $FE, the data from $9407, nothing at $9420 [M XD 5].
- **The load stops at the file's end or after EPTR − SPTR + 1 bytes (16-bit, so EPTR is included), whichever
  comes first:** SPTR $9200, EPTR $9263 with a 64-byte file: 64 bytes, $9240-$9257 (the window's end) left as
  they were [M XD 3]; SPTR $9300, EPTR $930F with the same file: 16 bytes, $9310-$9357 left as they were [M XD
  4]. EPTR = SPTR − 1 ($9700 / $96FF, a count of 0): nothing written in $96F8-$9757, no error [M XD 18].
  **EPTR = SPTR − 2** ($9702 / $9700, a count of $FFFF): the whole 64-byte file loaded at $9702-$9741, no error
  [M XD 34] — so EPTR below SPTR is not refused: the count wraps, and only a count of 0 loads nothing.
- **The block is left as given** (all 15 bytes) [M XD 3-8, 18, 33, 34].
- **Past the block:** $F571-$F572 (in BUF, right after the block) := SPTR after a load [M XD 3-6, 8, 34: preset
  $A4 $A5], := $8003 after the load of nothing [M XD 18]; $F55E-$F561 and LOGOPR ($FB02) are left [M].
- The three references agree in every case [M].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (CBIOS2_CUR_*) have no disk ROM and their machines no drive; C-BIOS's sub-ROM entry
is a stub that returns at once, and calling it is safe. Measured there with no disk mounted (every case of [XD
0-34] on all three C-BIOS builds):

| what | reference | C-BIOS |
|---|---|---|
| the RAM from SPTR | the file's bytes | **left as it was** ($EE) |
| block | unchanged | unchanged |
| $F571-$F572 | := SPTR ($8003 when nothing loaded) | **unchanged** |
| registers on return | A $00, F $54 (carry clear), BC / DE / HL / IX the call's own (Interface) | **every register as entered** (A $5A, **F $01: carry still set**, BC $BC0C, DE $DE0E, HL as entered, IX = the entry) |
| H.ERRO on a missing file / an unquoted name | reached, E = 53 [XD 7] / E = 13 [XD 33] | **never reached**: no error of any kind |

These are "no disk BASIC at all" readings, not a C-BIOS implementation to fix piecemeal: the whole call is
missing. Whether a C-BIOS without a disk should raise an error (as a diskless reference would) is open: no
diskless MSX2 reference was run.

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: A, F, the block and the files are the FS-A1WSX's, on both models; what differs is IX's low byte after the call (ROM-internal: it differs between every machine, the A1GT and A1ST included), VDP S#2 (read at a random moment) and case 16's unwritten window (power-on RAM) [M] ([AE_trall/xsubbltd.out](../../../scratchpad/AE_trall/xsubbltd.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

| case | inputs | state | what it separates |
|---|---|---|---|
| MD-02b | a file written by BSAVE (BASIC) | — | the same as XD 5 for BASIC's own file |
| MD-06 | SPTR inside the block itself ($F562); FNPTR inside the block / BUF | — | the block and the name read before the load vs during |
| MD-05 | EPTR = SPTR; a 0-byte file | — | one byte loaded (the count rule says so); an empty file: nothing loaded vs an error |
| MD-05b | SPTR $FFE0 with a 64-byte file, EPTR $FFFF / $001F | — | the load stopped at $FFFF vs wrapped to $0000 (page 0 is the BIOS during the call) |
| MD-05c | a load over the stack or the work area ($F380-) | — | refused vs loaded (and what then breaks) |
| MD-07 | name without terminator, a string expression | — | the name syntax (unquoted: error 13, XD 33) |
| MD-08 | HL ≠ $F562, a block at HL differing in every byte | — | HL read vs fixed (BLTDM reads HL) |
| MD-10 | — | a diskless MSX2 reference | error / crash |
| MD-11 | — | called from MSX-DOS with H.ERRO hooked | the error path outside BASIC |
| MD-12 | — | interrupts off at entry; the control call | the call's interrupt state vs the path's |
| MD-14 | — | the emulated time from just before to just after the call | the cost of the call (speed parity) |
| MD-13 | — | whole VRAM diffed | "does not touch VRAM" |

## Related pages

[BLTDM](BLTDM.md) (the inverse), [BLTVD](BLTVD.md); [block-transfer.md](../concepts/block-transfer.md).

## Tests that cover it

None yet.
