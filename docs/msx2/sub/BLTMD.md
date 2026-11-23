<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `BLTMD` (sub-ROM $01A5) — load a disk file into RAM

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubbltd.asm](../../../probes/bios/spec/xsubbltd.asm), [scratchpad/AE_xsubbltd_msx2.out](../../../scratchpad/AE_xsubbltd_msx2.out), decoded with the files read back from each machine's disk image by `scratchpad/xsubbltd.py` into [scratchpad/AE_xsubbltd_msx2_decoded.out](../../../scratchpad/AE_xsubbltd_msx2_decoded.out)). `[XD n]` = that run's case n.

## Summary

`BLTMD` copies the bytes of the file FNPTR names into RAM from SPTR, as they are in the file — a BSAVE header is
loaded as data, not obeyed — and stops at the end of the file or at EPTR (included), whichever comes first. A
missing file goes to BASIC's error handler through H.ERRO with error 53. It does not change the block.

## The specification

The block, the array and the recording: [block-transfer.md](../concepts/block-transfer.md).

**How it was called** [M]: from H.STKE (every ROM, the disk ROM included, initialised; BASIC's work area set
up), through EXTROM with IX = the entry, A $5A, F $01 (carry set), BC $BC0C, DE $DE0E, interrupts ON, block
fields the call does not name filled with garbage ($51 + offset), and H.ERRO hooked to record E and abandon the
case. Drive A held an image the probe's script made. Calls from MSX-DOS, or with interrupts off, were not made.

### Interface

- **In:** HL = $F562 [P A3 §3]; FNPTR at +0, a dummy at +2, SPTR (the start) at +4, EPTR (the end) at +6 [P A3
  §3; M XD 3]. FNPTR: a quoted name, then 0 [P A3 §3; M XD 3]. Whether HL or $F562 is read was measured for
  BLTDM only (HL is read there, [BLTDM](BLTDM.md)); for BLTMD it is [A].
- **Out, normal return:** carry reset [P A3 §3; M XD 3-6, 8, 18: entered with carry set, F $54 after]; A $00, BC
  $0300, DE $F2C4, HL $0300, IX $56D3 on all three references [M XD 3-6, 8, 18]. Interrupts ON after (entered
  on) [M].
- **Out, on an error:** a missing file calls H.ERRO with E = 53 (File not found), interrupts OFF, nothing loaded
  [M XD 7]; a call right after it works normally — no file left open [M XD 8].

### Behaviour

- **The file's bytes go to SPTR unchanged** [M]: DM1.BIN (64 bytes) to $9200 [M XD 3]; RAWDATA.BIN, a file with
  no header, to $9500 [M XD 6]; BSAVED.BIN, a BSAVE file ($FE, start $9420, end $942F, exec $9420, 16 bytes) to
  $9400 **with its 7-byte header** — $9400 = $FE, the data from $9407, nothing at $9420 [M XD 5].
- **The load stops at the file's end or at EPTR, EPTR included:** SPTR $9200, EPTR $9263 with a 64-byte file: 64
  bytes, $9240-$9257 (the window's end) left as they were [M XD 3]; SPTR $9300, EPTR $930F with the same file:
  16 bytes, $9310-$9357 left as they were [M XD 4]. EPTR < SPTR ($9700 / $96FF): nothing written in $96F8-$9757, no error [M XD 18].
- **The block is left as given** (all 15 bytes) [M XD 3-8, 18].
- The three references agree in every case [M].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (CBIOS2_CUR_*) have no disk ROM and their machines no drive; C-BIOS's sub-ROM entry
is a stub that returns at once, and calling it is safe. Measured there with no disk mounted (every case of [XD
0-21] on all three C-BIOS builds):

| what | reference | C-BIOS |
|---|---|---|
| the RAM from SPTR | the file's bytes | **left as it was** ($EE) |
| block | unchanged | unchanged |
| registers on return | A $00, F $54 (carry clear), BC / DE / HL / IX the call's own (Interface) | **every register as entered** (A $5A, **F $01: carry still set**, BC $BC0C, DE $DE0E, HL as entered, IX = the entry) |
| H.ERRO on a missing file | reached, E = 53 [XD 7] | **never reached**: no error of any kind |

These are "no disk BASIC at all" readings, not a C-BIOS implementation to fix piecemeal: the whole call is
missing. Whether a C-BIOS without a disk should raise an error (as a diskless reference would) is open: no
diskless MSX2 reference was run.

## Open (not measured)

| case | inputs | state | what it separates |
|---|---|---|---|
| MD-02b | a file written by BSAVE (BASIC) | — | the same as XD 5 for BASIC's own file |
| MD-06 | SPTR inside the block itself ($F562); FNPTR inside the block / BUF | — | the block and the name read before the load vs during |
| MD-07 | name unquoted / without terminator | — | the name syntax (BLTDM: unquoted gives error 13) |
| MD-08 | HL ≠ $F562, a block at HL differing in every byte | — | HL read vs fixed (BLTDM reads HL) |
| MD-10 | — | a diskless MSX2 reference | error / crash |
| MD-11 | — | called from MSX-DOS with H.ERRO hooked | the error path outside BASIC |
| MD-12 | — | interrupts off at entry; the control call | the call's interrupt state vs the path's |
| MD-13 | — | whole VRAM diffed | "does not touch VRAM" |

## Related pages

[BLTDM](BLTDM.md) (the inverse), [BLTVD](BLTVD.md); [block-transfer.md](../concepts/block-transfer.md).

## Tests that cover it

None yet.
