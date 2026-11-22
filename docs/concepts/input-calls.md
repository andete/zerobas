<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# The input calls — the key matrix, joysticks and CTRL+STOP in the BIOS

> **Status (2026-11-19):** the shared facts of the input region's ten BIOS calls (SNSMAT, KILBUF,
> CHGCAP, GTSTCK, GTTRIG, BREAKX, ISCNTC, CKCNTC, GTPAD, GTPDL). Each call's state, and the
> differences its page names, are in the generated [BIOS index](../bios/index.md), never repeated
> here. Speed is deliberately left out of these docs until on-par speed is established.

## Summary

The keyboard is an 11-row matrix the PPI reads one row at a time: port C's low nibble selects the
row, port B ($A9) returns it, a bit 0 for each key held. The timer interrupt scans it into NEWKEY /
OLDKEY and the key buffer; [CHGET](../bios/CHGET.md) reads that buffer. The joysticks, touch pads and
paddles sit on the PSG's port A (R14), the port chosen with R15. The input calls read these directly:
SNSMAT a matrix row, GTSTCK / GTTRIG a direction or a trigger (the cursor keys and the space bar
standing in for joystick 0), GTPAD / GTPDL the pads and paddles; BREAKX checks CTRL+STOP itself,
ISCNTC / CKCNTC the flag the timer interrupt sets; KILBUF empties the key buffer and CHGCAP switches
the CAPS lamp.

zerobas reads the keys the same. SNSMAT, KILBUF, CHGCAP, GTSTCK, GTTRIG, BREAKX, ISCNTC and CKCNTC
match the VG-8020 in every measured case since 2026-11-19 (cbios-repack/input-calls.patch and
basic/biosfnk.asm); what is left is GTPDL's
port bits (D-GTPDLPORT).

## How it works

Every statement below carries its source:
- **[P]** the published interface, the MSX2 Technical Handbook (rated in
  [allowed-sources.md](../allowed-sources.md));
- **[M]** measured by this project (the per-call pages);
- **[A]** not yet established.

### The key matrix

- SNSMAT returns row A AND $0F (rows 11-15 read $FF), selecting it with port C := (port C AND $F0) +
  A -- an add of the whole A, so a row number of $10 and up carries into the CAPS lamp and click bits
  [M] ([SNSMAT](../bios/SNSMAT.md)).
- GTSTCK with A = 0 turns the cursor keys (row 8, bits 4-7) into a direction 0-8, opposite keys
  cancelling; GTTRIG with A = 0 returns $FF while the space bar (row 8 bit 0, and only it) is held
  [M] ([GTSTCK](../bios/GTSTCK.md), [GTTRIG](../bios/GTTRIG.md)). Both leave row 8 selected.

### The joystick ports

- The PSG's R15 bit 6 selects which port its port A reads: GTSTCK, GTTRIG and GTPDL clear it for an
  odd port number and set it for an even one [M]. With nothing plugged in the directions and
  triggers read 0 and the paddles $FF [M] ([GTPDL](../bios/GTPDL.md)); GTPAD's protocol drives R15
  bit by bit [M] ([GTPAD](../bios/GTPAD.md)).

### CTRL+STOP and the key buffer

- **BREAKX** reads the matrix itself: the carry is set while CTRL and STOP are both held, and then it
  empties the key buffer and marks STOP in OLDKEY [M] ([BREAKX](../bios/BREAKX.md)).
- **ISCNTC / CKCNTC** look at INTFLG ($FC9B), which the timer interrupt sets, not at the keys: with no
  break pending they return A = 0 and turn interrupts on [M] ([ISCNTC](../bios/ISCNTC.md),
  [CKCNTC](../bios/CKCNTC.md)). With a break pending they leave for BASIC's break handling [P] --
  [A] here.
- **KILBUF** empties the key buffer by moving the get pointer to the put pointer [M]
  ([KILBUF](../bios/KILBUF.md)).
- **CHGCAP** lights the CAPS lamp (port C bit 6 := 0) for A = 0 and puts it out otherwise; CAPST, the
  shift state, is not touched [M] ([CHGCAP](../bios/CHGCAP.md)).

### How the probe presses keys

The harness sets the emulator's key matrix through the debugger before each case (`@keyset`,
[probes/bios/biosl_run.py](../../probes/bios/biosl_run.py)) -- input, as a person pressing keys --
and the probe turns the VDP's frame interrupt off, so no timer interrupt scans the keys behind a call
([docs/spec-method.md](../spec-method.md)).

## Differences from the reference

Each call's differences are on its own page, never repeated here; the
[BIOS index](../bios/index.md) lists them per call.

## What we found, and how

One probe (XINP1, 95 cases over three runs) measured the ten calls on the VG-8020, alone and with a
disk interface. The rules are checked against every case ([docs/spec-method.md](../spec-method.md)).

## How zerobas does it

The input calls are C-BIOS's, in the main ROM
([cbios-repack-provenance.md](../cbios-repack-provenance.md)); SNSMAT, KILBUF, CHGCAP, GTSTCK and GTTRIG carry
zerobas's repack patch for their measured contracts (`cbios-repack/input-calls.patch`).

## Related pages

- [The BIOS](bios.md): what every BIOS call has in common.
- [The screen editor](screen-editor.md): CHGET and the key buffer as BASIC sees them.
- [Interrupts and traps](interrupts-and-traps.md): the timer interrupt that scans the keys.
- The calls: [SNSMAT](../bios/SNSMAT.md), [KILBUF](../bios/KILBUF.md), [CHGCAP](../bios/CHGCAP.md),
  [GTSTCK](../bios/GTSTCK.md), [GTTRIG](../bios/GTTRIG.md), [BREAKX](../bios/BREAKX.md),
  [ISCNTC](../bios/ISCNTC.md), [CKCNTC](../bios/CKCNTC.md), [GTPAD](../bios/GTPAD.md),
  [GTPDL](../bios/GTPDL.md).

## Tests that cover it

**`spec-live`** ([tools/spec_live.py](../../tools/spec_live.py), in every gate) re-runs every rule
of the ten call pages on zerobas.
