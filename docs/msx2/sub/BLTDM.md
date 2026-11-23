<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `BLTDM` (sub-ROM $01A9) — save RAM to a disk file

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubbltd.asm](../../../probes/bios/spec/xsubbltd.asm), [scratchpad/AE_xsubbltd_msx2.out](../../../scratchpad/AE_xsubbltd_msx2.out), decoded with the files read back from each machine's disk image by `scratchpad/xsubbltd.py` into [scratchpad/AE_xsubbltd_msx2_decoded.out](../../../scratchpad/AE_xsubbltd_msx2_decoded.out)). `[XD n]` = that run's case n.

## Summary

`BLTDM` writes the RAM from SPTR to EPTR, both ends included, to the file FNPTR names, as raw bytes: no header
of any kind. An existing file of that name is replaced. HL, not the fixed $F562, locates the block. A bad file
name or a disk error goes to BASIC's error handler through H.ERRO. It does not change the block.

## The specification

The block, the array and the recording: [block-transfer.md](../concepts/block-transfer.md).

**How it was called** [M]: from H.STKE (every ROM, the disk ROM included, initialised; BASIC's work area set
up), through EXTROM with IX = the entry, A $5A, F $01 (carry set), BC $BC0C, DE $DE0E, interrupts ON, block
fields the call does not name filled with garbage ($51 + offset), and H.ERRO hooked to record E and abandon the
case. Drive A held an image the probe's script made. Calls from MSX-DOS, or with interrupts off, were not made.

### Interface

- **In:** HL = the block (normally $F562) [P A3 §3]: SPTR (the start) at +0, EPTR (the end) at +2, FNPTR at +4
  [P A3 §3]. HL is READ: with HL = $9F00 holding SPTR $9000, EPTR $9009, "HLB.BIN" and $F562 holding
  $9000-$903F, "FIX.BIN", the disk got HLB.BIN (10 bytes) and no FIX.BIN [M XD 16].
- **FNPTR** points at the name as BASIC writes it: a quoted string, then 0 (`"DM1.BIN"`, 0) [P A3 §3; M XD 0].
  The name unquoted (`DM3.BIN`, 0) is evaluated as a numeric expression: error 13 (Type mismatch) through
  H.ERRO, no file written [M XD 2].
- **Out, normal return:** carry reset [P A3 §3; M XD 0, 1, 16, 17: entered with carry set, F $54 after]; A $00,
  BC $0301, DE $0007, HL $0300 on all three references [M XD 0, 1, 16, 17]. IX ($F197 NMS 8250, $F196 HB-F900,
  $F185 FS-A1WSX) and IY differ by machine and are no contract [M]. Interrupts ON after [M XD 0, 1, 16, 17];
  entered with them on, so whether the call enables them is not separated [A].
- **Out, on an error:** H.ERRO ($FFB1) is called with E = the BASIC error number (13 for the unquoted name) and
  interrupts OFF [M XD 2]; a caller that hooks it and abandons the call can call again at once (the next BLTMD,
  XD 3, read the file normally) [M XD 2, 3].

### Behaviour

- **The file is the bytes SPTR..EPTR, EPTR included, and nothing else** [M]: $9000-$903F gave a 64-byte DM1.BIN
  equal to that RAM [M XD 0]; $9010-$9010 a 1-byte DM2.BIN ($81, the byte at $9010) [M XD 1]. No $FE / BSAVE
  header, no length or address in the file [M XD 0, 1].
- **An existing file is replaced, not overwritten in place:** 16 bytes saved over the 300-byte LONG.BIN left a
  16-byte LONG.BIN [M XD 17].
- **The block is left as given** (all 15 bytes $F562-$F570, the garbage included) [M XD 0, 1, 16, 17]; the
  source RAM is unchanged [M XD 0, 1, 16, 17: the 96-byte window at $9000].
- The three references agree in every case; only IX and the VDP status S#2 (timing bits) differ [M].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (CBIOS2_CUR_*) have no disk ROM and their machines no drive; C-BIOS's sub-ROM entry
is a stub that returns at once, and calling it is safe. Measured there with no disk mounted (every case of [XD
0-21] on all three C-BIOS builds):

| what | reference | C-BIOS |
|---|---|---|
| the file | DM1.BIN 64 B, DM2.BIN 1 B, HLB.BIN, LONG.BIN replaced | **nothing written** (no drive) |
| block, source RAM | unchanged | unchanged |
| registers on return | A $00, F $54 (carry clear), BC / DE / HL / IX the call's own (Interface) | **every register as entered** (A $5A, **F $01: carry still set**, BC $BC0C, DE $DE0E, HL as entered, IX = the entry) |
| H.ERRO on an unquoted name | reached, E = 13 [XD 2] | **never reached**: no error of any kind |

These are "no disk BASIC at all" readings, not a C-BIOS implementation to fix piecemeal: the whole call is
missing. Whether a C-BIOS without a disk should raise an error (as a diskless reference would) is open: no
diskless MSX2 reference was run.

## Open (not measured)

| case | inputs | state | what it separates |
|---|---|---|---|
| DM-03 | EPTR < SPTR | — | empty file / error / a 64 KB wrap (EPTR = SPTR is measured: one byte, XD 1) |
| DM-05 | a full / write-protected disk, then a valid call | — | the error number; the directory left |
| DM-06 | SPTR range covering $F562-$F570; FNPTR inside the block / BUF | — | the block saved as at entry vs as the call changed it |
| DM-07b | `"A:X.BIN"`, a name with no terminator, a string expression | — | the name is a BASIC expression (XD 2 suggests it) |
| DM-10 | — | a diskless MSX2 reference | error, carry, or crash |
| DM-11 | — | called from MSX-DOS with H.ERRO hooked | the error path outside BASIC |
| DM-12 | — | interrupts off at entry; the control call (GSPSIZ) | the call's interrupt state vs the path's |
| DM-13 | — | whole VRAM diffed | "does not touch VRAM" (only BLTDM's RAM effects were read) |

## Related pages

[BLTMD](BLTMD.md) (the inverse), [BLTDV](BLTDV.md); [block-transfer.md](../concepts/block-transfer.md).

## Tests that cover it

None yet.
