<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `VDPSTA` (sub-ROM $0131) — read a VDP status register

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xwv.asm](../../../probes/bios/spec/xwv.asm), [scratchpad/AE_xwv_msx2.out](../../../scratchpad/AE_xwv_msx2.out), decoded by [xwv_decode.py](../../../scratchpad/xwv_decode.py) into [scratchpad/AE_xwv_msx2_decoded.out](../../../scratchpad/AE_xwv_msx2_decoded.out)). The ten "VDPSTA" records (A 0-9) and the three "phase 4" records (added 2026-11-23: STATFL preset, port $99 logged, S#0's F flag left pending by a DI wait).
>
> Goldfish pass 1 (test writer) 2026-11-23: 1 finding, 1 measured, 0 moved to open.

## Summary

`VDPSTA` returns status register S#A (0-9) in A. Reading some status registers changes the VDP:
S#5 resets S#3-S#6, and S#0 is what the interrupt handler reads. The handbook calls it "reads the
VDP register", but its range 0-9 is the status registers'.

## The specification

Shared facts — S#0-S#9, R#15, STATFL, the recording: [vdp-and-palette.md](../concepts/vdp-and-palette.md).

### Interface

- **In:** A, the register number, 0 to 9 [P A1 VDPSTA].
- **Out:** A, the data. Only F changes besides [P A1 VDPSTA].

### Behaviour

- A := S#A, read by selecting it in R#15 [P 4§2.1.3; that the call does so is A].
- R#15 back to 0 afterwards, and interrupts off during the read, are what the handbook asks of a
  program [P 4§2.1.3]; that the call does both, and the interrupt state on return, are [A].
- The side effects are the VDP's: reading S#5 resets S#3-S#6 [P 4§5.3.3]; reading S#0 clears its
  flags [A]; reading S#7 affects TR [P 4§6.5.6]. Whether reading S#0 also stores it in STATFL
  [P A4 STATFL] is [A].
- A from 10 to 15, and above 15, is [A]. S#1 carries a VDP identification that differs between the
  MSX2 and MSX2+ VDPs [A].

**Measured** [M] (the same on all three references): A 0-9 returns S#0-S#9, equal to the status the debugger
held just before the call (S#2's live bits aside); the FS-A1WSX's S#1 reads $04, the V9958's ID (2) in bits 5-1,
where the V9938s read $00. F after: $44 for A 0 (both runs), $9B for A 1-9 in the VDPSTA loop but $40 / $60 for A 1 in phase 4 -- F for
A >= 1 is not a constant of the call.

**A 0 reads the port, selected like the others** (phase 4): the port $99 log is `00 8F`, the read, `00 8F` for A 0
and `01 8F`, the read, `00 8F` for A 1 -- S#A selected through R#15, R#15 set back to 0 afterwards; A 0 is not
"port $99 read with no selection". The call does NOT write STATFL ($F3E7): with STATFL preset $A5 and A 0 read at
once, STATFL is still $A5 and A = $1F. With S#0's F flag pending (S#0 $9F before), A came back $1F and STATFL held
$9F: the timer interrupt ran during the call (the probe enters with DI) and its handler read S#0 (and cleared F)
first. IFF = 0 on return in all three.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds return the same status registers, with the same R#15 port sequence and STATFL left
alone, but return with interrupts ON (IFF = 1; the references 0) ([scratchpad/AE_xwv_msx2.out](../../../scratchpad/AE_xwv_msx2.out)).

## Open (not measured)

Recording as in [vdp-and-palette.md](../concepts/vdp-and-palette.md#how-every-case-is-recorded);
STATFL is preset to garbage and recorded in every case; R#15 by snapshot.

| case | inputs | state | what it separates |
|---|---|---|---|
| VS-01 | A 0 | a frame interrupt pending (R#1 IE0 clear) | **STATFL half decided** (phase 4: not written by the call); bit 7 seen by the call still open -- with IE0 set the handler read it first, so IE0 clear is the case |
| VS-02 | A 1, 2 | DI throughout | the value (S#1 per machine); R#15 left at A vs reset to 0 by the call (no ISR) |
| VS-03 | A 3, then A 5, then A 3 | sprite collision in mode 2 set up | S#5 resets S#3-S#6, S#3 does not; STATFL untouched |
| VS-04 | A 7 | an LMCM command running (CE = 1) | TR / S#7 interplay through the call |
| VS-05 | A 8, 9 | a SRCH command done | the found X |
| VS-06 | A 10, 15, $10, $FF | port log | masked to 4 bits by the call (the R#15 byte sent) vs passed and dropped by the VDP; R#15 left |
| VS-07 | A 2 | interrupts on, IE0 set, a frame interrupt due at the port read | DI during the read (IFF1 at the port $99 access in the log; the ISR not run between select and read) |
| VS-08 | — | interrupts on / off; the control call | the call's interrupt state vs the path's |
| VS-09 | — | entry F $00 / $FF; all registers incl. AF' BC' DE' HL' IX IY garbage | F's value; registers kept |

## Related pages

[WRTVDP](WRTVDP.md); the MSX1 call [RDVDP $013E](../../bios/RDVDP.md);
[vdp-and-palette.md](../concepts/vdp-and-palette.md).

## Tests that cover it

None yet.
