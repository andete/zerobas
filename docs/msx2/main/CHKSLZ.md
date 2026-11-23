<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `CHKSLZ` ($0162) — find the sub-ROM's slot

> **Spec:** DRAFT 1 (2026-11-23): observable effects MEASURED on the HB-F900, NMS 8250 and FS-A1WSX -- the three
> DISAGREE, and on two of them the call does not come back as a subroutine
> ([xchkslzd.asm](../../../probes/bios/spec/xchkslzd.asm), runs [scratchpad/AE_xchkslzd_msx2.out](../../../scratchpad/AE_xchkslzd_msx2.out)
> and the repeat [scratchpad/AE_xchkslzd_msx2b.out](../../../scratchpad/AE_xchkslzd_msx2b.out), identical).

## Summary

`CHKSLZ` is an MSX2 jump-table entry the handbook does not list; C-BIOS names it "search slots for the
subrom". On the references it is **not a callable service**: called from a cartridge it runs for many
seconds with interrupts enabled, leaves EXBRSA alone, and on the NMS 8250 and FS-A1WSX it does not
return to the caller as a subroutine (the FS-A1WSX calls the cartridges' INIT again and goes on into
its start-up). Only the observable effects are recorded here; what the routine is for is not
measured.

## The specification

**Interface.** None published (absent from App. 1's MSX2 entries) [A]. That a header's ID "CD" marks a
sub-ROM is [P 5§7.3.1].

**Measured** [M] (the probe: stack and variables in page 2 RAM, EXBRSA := $A5, A $A7, BC $B1C2, DE $4E5F, HL $9876,
DI, the VDP interrupt enabled as booted; progress written to VRAM $3F00, which no slot switch hides; the two runs give
the same bytes):
- **HB-F900:** returns to the caller after about 18.6 s (JIFFY $008A -> $04E4, 60 Hz) with SP balanced, page 3's slot as
  before, **interrupts ON**, EXBRSA still $A5 (not written), A $FC, F $A8, BC $FC04, DE $FCFC, HL $FD09 [M].
- **NMS 8250:** the code after the CALL is reached in a broken state -- SP $00FF, port $A8 $F5 (page 0 in slot 1),
  JIFFY unchanged, A $A9 -- not a return to the caller; EXBRSA still $A5 [M].
- **FS-A1WSX:** never comes back. Our cartridge's INIT is called again, twice, from a stack at $F08E with port $A8 $F4,
  and the VRAM the probe wrote is cleared afterwards -- the machine goes on with its start-up; no reading of the
  return [M].
- EXBRSA reads $A5 (the probe's preset) after the call on the HB-F900 and NMS 8250: not written; on the FS-A1WSX there
  is no reading [M].

## Differences from the reference

The references do not agree with each other, so there is no single reference behaviour. C-BIOS's MSX2 / MSX2+ builds
(the subject) return at once (JIFFY unchanged), SP balanced, interrupts left off, with **A = the sub-ROM's slot ($83)
and EXBRSA written with it**, F $41, BC $0103, DE $F444, HL $FCC4 [M] -- a "find the sub-ROM" service none of the three
references provides through this entry.

## Open (not measured)

- What the routine is for; it reads as part of the start-up sequence. Its behaviour with the VDP interrupt DISABLED was
  tried during development (the NMS 8250 did not return) but that run is not on file.
- The DRAFT 0 matrix CZ-1 .. CZ-11 (EXBRSA presets, a planted "CD" header, EXPTBL, configured machines): retired --
  every case needs the call to return, which it does not on two of the three references. A first full-matrix probe
  (stack in page 3, then in page 2, our INIT returning at once on re-entry) gave no reading on any reference within
  400 s and was dropped.

## Related pages

[region page](README.md), [EXTROM](EXTROM.md), [SUBROM](SUBROM.md); [slots](../../concepts/slots.md).

## Tests that cover it

None yet.
