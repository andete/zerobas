<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# The sound calls — the PSG, PLAY's queues and the 1-bit port in the BIOS

> **Status (2026-11-19):** the shared facts of the sound region's ten BIOS calls (GICINI, WRTPSG,
> RDPSG, STRTMS, BEEP, CHGSND, LFTQ, PUTQ, GETVCP, GETVC2). Each call's state, and the differences its
> page names, are in the generated [BIOS index](../bios/index.md), never repeated here. Speed is
> deliberately left out of these docs until on-par speed is established.

## Summary

MSX1 makes sound with a PSG (three tone channels, noise, envelope), reached through I/O ports $A0
(register select), $A1 (write) and $A2 (read), and with a 1-bit output, bit 7 of the PPI's port C
($AA). BASIC's SOUND writes PSG registers; PLAY parses its strings into three queues, one per voice,
which the timer interrupt plays from. The BIOS calls give the pieces: WRTPSG / RDPSG for registers,
CHGSND for the 1-bit port, GICINI to reset everything, PUTQ / LFTQ for the queues, GETVCP / GETVC2
to address the voice buffers, STRTMS to start the play, and BEEP.

zerobas does the register and queue work the same in the cases BASIC uses; its differences are in
the reset of the voice buffers, BEEP's ending, STRTMS's start, and flags and working registers.

## How it works

Every statement below carries its source:
- **[P]** the published interface, the MSX2 Technical Handbook (rated in
  [allowed-sources.md](../allowed-sources.md));
- **[M]** measured by this project (the per-call pages);
- **[A]** not yet established.

### The PSG

- WRTPSG writes E into register A (R0-R13; R7 written whole) and returns with interrupts **on**;
  RDPSG returns register A, $FF past 15 [M] ([WRTPSG](../bios/WRTPSG.md), [RDPSG](../bios/RDPSG.md)).
- R14 is port A, an input; R15 is port B [P]. R15 changes while interrupts are on -- the timer
  interrupt writes it -- so the pages compare it only with interrupts off [M].
- GICINI sets R7 := $B8 (tones on, noise off, port A in, port B out) and the volumes R8-R10 := 0 [M]
  ([GICINI](../bios/GICINI.md)).

### PLAY's queues and voices

- **QUETAB** ($F959) has a 6-byte entry per queue: put, get, a back flag, size, address [P]. Queues
  0-2 are the three voices' (VOICAQ / VOICBQ / VOICCQ, $F975 / $F9F5 / $FA75, 128 bytes each); queue 3
  is RS2IQ's [P].
- PUTQ advances put to (put + 1) AND
  size and stores there unless that meets get (full: Z set); LFTQ returns (get - ((put + 1) AND
  size)) AND size [M] ([PUTQ](../bios/PUTQ.md), [LFTQ](../bios/LFTQ.md)).
- **The voice buffers** VCBA / VCBB / VCBC are 37 bytes each from $FB41 [P]; GETVCP and GETVC2 return
  addresses in them (VCBA + 37 x voice + offset) [M] ([GETVCP](../bios/GETVCP.md),
  [GETVC2](../bios/GETVC2.md)). GICINI clears them and sets bytes 15-19 of each to $04 $04 $78 $88
  $FF [M]; what each default means is [A] here.
- **MUSICF** ($FB3F) flags the voices playing, **PLYCNT** ($FB40) counts the PLAY strings queued [P].
  STRTMS starts the play when nothing plays and PLYCNT is not 0: PLYCNT - 1, MUSICF := 7, each voice's
  first word := 1 [M] ([STRTMS](../bios/STRTMS.md)).

### The 1-bit port and BEEP

- CHGSND sets port C bit 7 for any A but 0 [M] ([CHGSND](../bios/CHGSND.md)).
- BEEP sounds a tone on channel A and ends with GICINI's reset [M] ([BEEP](../bios/BEEP.md)).

### What a probe may read, and where it must not write

The probes preset the PSG through its ports, the work area and the buffers, and read them back
([docs/spec-method.md](../spec-method.md)). On the VG-8020 with the NMS 1200 disk interface, RS2IQ
($FAF5-$FB34) holds something of that machine's own: overwriting it stopped it, so the probes leave
it alone and give queue 3 a buffer elsewhere [M].

## Differences from the reference

Each call's differences are on its own page, never repeated here; the
[BIOS index](../bios/index.md) lists them per call.

## What we found, and how

Two probe files (XSND1, XSND1B) measured the ten calls on the VG-8020, alone and with a disk
interface: 135 cases over the PSG, port C, the queue table and cells, and windows over the buffers.
The rules are checked against every case ([docs/spec-method.md](../spec-method.md)).

## How zerobas does it

The sound calls are C-BIOS's, in the main ROM
([cbios-repack-provenance.md](../cbios-repack-provenance.md)).

## Related pages

- [The BIOS](bios.md): what every BIOS call has in common.
- [Interrupts and traps](interrupts-and-traps.md): the timer interrupt that plays the queues.
- The calls: [GICINI](../bios/GICINI.md), [WRTPSG](../bios/WRTPSG.md), [RDPSG](../bios/RDPSG.md),
  [STRTMS](../bios/STRTMS.md), [BEEP](../bios/BEEP.md), [CHGSND](../bios/CHGSND.md),
  [LFTQ](../bios/LFTQ.md), [PUTQ](../bios/PUTQ.md), [GETVCP](../bios/GETVCP.md),
  [GETVC2](../bios/GETVC2.md).

## Tests that cover it

**`spec-live`** ([tools/spec_live.py](../../tools/spec_live.py), in every gate) re-runs every rule
of the ten call pages on zerobas.
