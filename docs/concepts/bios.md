<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# The BIOS — calling the machine's own routines

> **Status (2026-11-17):** the base page for the per-call BIOS pages. Each call's state, and the
> differences its page names, are in the generated [BIOS index](../bios/index.md), never repeated
> here. Speed is deliberately left out of these docs until on-par speed is established.

## Summary

The BIOS is the set of routines in the main ROM that every MSX program can call: write a
character, read a key, set up the screen, play a sound, reach another slot. zerobas's BIOS is
the C-BIOS repack, C-BIOS with this project's patches, and each call is compared with the Philips
VG-8020 (the reference). This page says what all calls have in common. Each call's own page says
what it does, as measured against the reference, and where zerobas differs.

## How it works

Every statement below carries its source:
- **[P]** the published interface, the MSX2 Technical Handbook (rated in
  [allowed-sources.md](../allowed-sources.md));
- **[M]** measured by this project (the per-call pages);
- **[A]** not yet established.

### Where the BIOS lives

The BIOS is in the main ROM, mapped at the bottom 16 KB of the address space (page 0,
$0000–$3FFF) in the main ROM's slot [P]. Its calls are entered through a table of fixed
addresses at the start of the ROM, one jump per call, so a program calls an address and not a
routine's location [P]. The 108 MSX1 addresses are listed in [docs/bios/index.md](../bios/index.md).

### Calling it

- **From BASIC, or a cartridge whose page 0 is the main ROM:** a plain `CALL` to the address [P].
- **When page 0 is not the main ROM** (MSX-DOS runs with RAM there): through the inter-slot call
  CALSLT, or CALLF / `RST 30h`, naming the main ROM's slot and the address [P].
- **Each call's registers on entry and return** are its own contract. The per-call page states
  what was measured, for example CHPUT returns A unchanged for every byte [M]. **[A]** Which
  other registers each call preserves: per page, as measured.

### Hooks

Many calls first call a HOOK, a 5-byte slot in the work area that an extension (a disk ROM, a
cartridge) can redirect to take the call over [P]. **[A]** Which calls go through which hook, and
whether zerobas's do the same: per page (CHPUT's hook is open on its page).

### The work area

The BIOS keeps its state in RAM at the top of the address space, in published cells: the cursor
(CSRX $F3DD, CSRY $F3DC), the screen width (LINLEN $F3B0), the row count (CRTCNT $F3B1), the
function-key line switch (CNSDFG $F3DE), the line-continuation table (LINTTB $FBB2) and many
more [P]. Several calls read and write the same cells. Which call touches which cell is the
[shared-state map](../bios/shared-state.md). It shows where one region's calls meet another's, so
a fix in one cannot silently break another.

## Differences from the reference

Each call's differences are on its own page, never repeated here. The
[BIOS index](../bios/index.md) lists, per call, the TODO items its page names.

## What we found, and how

Each call's page is made by measuring the call on the reference and on zerobas with a probe that
calls it directly. The behaviour is stated as EXECUTABLE RULES, checked against every measured
case, then reviewed by fresh readers who see only the page
([docs/spec-method.md](../spec-method.md)). The reference for the main BIOS is the VG-8020; the
Panasonic CF-3300 is a second reading.

## How zerobas does it

zerobas runs C-BIOS, repacked and patched for this project. The patches are in `cbios-repack/`,
and their provenance is in [cbios-repack-provenance.md](../cbios-repack-provenance.md). A difference a
call's page finds becomes a TODO item, fixed as a patch and then pinned by the page's own rules.

## Related pages

- [docs/bios/index.md](../bios/index.md): every call, its region, its page.
- [The screen editor](screen-editor.md): the text region's shared facts.
- [The graphics calls](graphics-calls.md): the graphics region's shared facts.
- [Slots](slots.md): the slots region's shared facts; [the interpreter entries](interpreter-entries.md): the
  interpreter region's.
- [Interrupts and traps](interrupts-and-traps.md), [Screen modes](screen-modes.md),
  [Files and devices](files-and-devices.md).

## Tests that cover it

`biosl-acceptance` (the BIOS ladder: our own cartridges, VG-8020 against zerobas) and the
per-call gates named in [docs/tier-status.md](../tier-status.md). The per-call pages' rules become
gate cases through the test audit ([docs/spec-method.md](../spec-method.md) §8).
