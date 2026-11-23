<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `PCMPLY` ($0186) — play a memory area through the PCM

> **Spec:** DRAFT 0 (2026-11-23): not measured. References: Panasonic FS-A1GT and FS-A1ST
> ([`--row turbor`](../../../probes/bios/biosl_run.py)). Only the published interface below.

Main-ROM entry, turbo R only. Listed by MAP's "MSX turbo R BIOS Entries" ([index](../index.md)); C-BIOS has no
turbo R build.

## Summary

Not measured yet.

## The specification

**Interface** [P MAP]: input `A = v 0 0 0 0 0 x x` (v = the data is in VRAM; xx = "quality parameter (speed: 0 = fast)"), HL = start address in RAM or VRAM, BC = length, D bit 0 = bit 17 of the length and E bit 0 = bit 17 of the start address when in VRAM. Output: carry set when aborted with CTRL-STOP. Registers: all.

Everything else is [A] until measured.

## Cases to measure (a later unit)

- Every A bit separately and together, in each CPU mode (Z80, R800 ROM, R800 DRAM: the call may switch the CPU or
  depend on it -- record GETCPU and the S1990's register 6 before and after, as
  [CHGCPU](CHGCPU.md)'s probe does).
- The quality / speed values 0-3: the time per sample (the S1990 timer, ports $E6 / $E7) and the number of PCM port
  writes (an `@portlog` on the PCM ports; which ports, from a published I/O map, to be named first).
- RAM vs VRAM (bit 7), the 17-bit VRAM address and length in D / E, a length of 0, an area that crosses $8000 / $C000
  or the end of VRAM.
- CTRL-STOP during the call (`@matrix`): carry, A, where it stopped; and a run to the end: carry clear?
- Every register, flag and the interrupt state on return (the registers loaded with distinct garbage); the work-area
  cells that change; the slot registers.

- FS-A1GT vs FS-A1ST, per case.

## Differences

Not measured.

## Open (not measured)

Everything above.

## Related pages

[turbo R index](../index.md); [CHGCPU](CHGCPU.md); [GETCPU](GETCPU.md).

## Tests that cover it

None yet.
