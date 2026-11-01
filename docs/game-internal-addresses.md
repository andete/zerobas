<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: verify=no reason="no example" -->

# Game programs that call undocumented ROM addresses

> **Status (2026-11-01):** a catalogue, not a plan. Joost, 2026-11-01:
> *"record these expected internal addresses (game + which address, no
> further investigation needed now) but we can't already be compatible with
> all of them yet. We still have completeness and correctness and size
> constraints already as big challenges."*

Some games on tape call into the MSX BIOS or the BASIC ROM at addresses
that are not published entry points. The addresses are interpreter or BIOS
internals that only disassemblies describe, which this project does not use
(see [allowed-sources.md](allowed-sources.md)). zerobas's code is laid out
differently, so a call to such an address lands in unrelated code. The
game typically resets or stops with an error.

Each address below was found black-box: we ran the game on the Philips
VG-8020 and on zerobas and logged where the program counter went from RAM
into ROM (PC values only, never a ROM or game byte).

## Supported: an entry at the same address

Each was characterised black-box on the VG-8020 (registers and published
work-area cells in, the same out) and given its own entry at that address
(D-BASICINT, D-BASICINT2, D-BIOSINT, D-AVTAK).

| Title | Address | Where | Note |
|---|---|---|---|
| Punch & Judy | $73AC, $3297 | BASIC ROM | runs a stored BASIC program after a BLOAD,R |
| Loopy Laundry | $73AC | BASIC ROM | as Punch & Judy (the rest of its calls: below) |
| Harry Fox | $6CF3, $3297 | BASIC ROM | |
| Demonia | $72E9, $72D4 | BASIC ROM | reads its tape through them, per block and per byte |
| A View to a Kill | $73E5 | BASIC ROM | the PLAY statement's body |
| Head over Heels | $4EF8 | BASIC ROM | reached by a `ret` from the game's own code |
| Buzz Off, Shark Hunter | $0D12 | BIOS | the reference's keyboard scan |

## Recorded, not supported

| Title | Addresses | Where |
|---|---|---|
| Buzz Off, Shark Hunter | about 90 addresses in $0748–$0820 and $0D12–$126B, plus $0468, $046B, $046E (only the ranges were recorded) | BIOS |
| Loopy Laundry | $4604 $4649 $4669 $4B02 $4C70 $4CA9 $4DDC $593F $5EAC $629D $62A4 $62B2 $62F3 $6686 $67F1 $6AB6 $6AF9 $6B12 $6C48 $6F18 $6F92 $732B $732E $7331 $79CF, and $3002 | BASIC ROM |
| Loopy Laundry | $01C4, $1462, $1B49, $18E8 | BIOS |
| Loopy Laundry | $2010 | the font |

**$2010 is a special case.** The font is already where the VG-8020 has it
(CGPNT is slot 0, $1BBF, on both), so $2010 is character 138's glyph on both
machines. The game's loader does not read the glyph: it returns into it and
runs its bytes as code. zerobas's font has its own glyphs, so other bytes
run there. Matching it would mean copying the reference's glyph bytes, which
is ROM content and would change how that character looks. Joost parked that
question on 2026-10-17, and it stays parked.

## Other MSX models

Measured 2026-11-01 (the tape run on another machine in the reference's
place, `scratchpad/tapecorpus_run.py --ref`):

| Machine | Buzz Off, Shark Hunter, Harry Fox, Punch & Judy |
|---|---|
| Toshiba HX-10 (MSX1) | run, ending in the same states as on the VG-8020 |
| Canon V-20 (MSX1) | run, ending in the same states as on the VG-8020 |
| Philips NMS 8250 (MSX2) | the first three reset after loading; Punch & Judy stops at `Disk offline`, caused by the machine's disk drive |
| Sony HB-75P (MSX1) | no reading: the machine started its built-in firmware, not BASIC |

So these addresses are the same across the European MSX1 BASIC 1.0 machines
tried, and they changed with MSX2. Loopy Laundry and the other titles were
not run on other models.

## Where the records are

- `TODO.md`: D-TAPELOAD's (A1) / (A2) blocks, D-BIOSINT, D-BASICPUB.
- `docs/TODO-done.md`: D-BASICINT, D-BASICINT2.
- The pins themselves: `ds $XXXX - $` lines in `basic/field.asm`,
  `basic/files.asm`, `basic/expr.asm` and `basic/float-arith.asm`, and the
  repacked BIOS patch for $0D12.
