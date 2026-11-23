<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `CLRTXT` (sub-ROM $0119) — clear the text screen (interface unpublished)

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubctx.asm](../../../probes/bios/spec/xsubctx.asm), [scratchpad/AE_xsubctx_msx2.out](../../../scratchpad/AE_xsubctx_msx2.out), decoded by `scratchpad/xsubctx_decode.py`).
>
> Goldfish pass 1 (test writer) 2026-11-23: 6 findings, 3 measured (cases 12-15 and the register copies before the
> call added), 3 corrected, 0 moved to open.

## Summary

An entry at sub-ROM $0119 named CLRTXT by other open implementations; the MSX2 Technical Handbook
does not list it. It is the text half of a screen clear: it writes spaces over 24 rows of the name
table, homes the cursor, resets LINTTB and redraws the function-key line when it is on. It does this
in EVERY mode, graphic ones included, where it writes spaces over the start of the current pattern-name
or bitmap area. Shared facts: [the screen-modes page](../concepts/screen-modes.md).

## The specification

Case numbers `[M xsubctx n]` are the probe's case table.

**Interface.**
- Not published: the handbook's sub-ROM listing goes from CLSSUB ($0115) to DSPFNK ($011D)
  [P App. 1, SUB-ROM]. An entry on all three references [M xsubctx 0-11].
- In: none. Z and A are not inputs: Z set / clear and A = $00 / $FF give the same result [M xsubctx 0, 2, 3].
- Out: none. AF, BC, HL, IX changed; with the key line off A $00, F $54, BC $0000, HL $FBCA (LINTTB + 24), IX $00C9 on
  all three; DE kept with the key line off and when it is on but not drawn (SCREEN 2), changed when it is drawn
  [M xsubctx 0-15].
- Interrupts on return, entered with DI: **kept (off) with the key line off** on all three [M xsubctx 0, 2, 3, 5, 6,
  8, 10, 11, 12]. **With the key line on (CNSDFG ≠ 0) the references disagree: on on the HB-F900 and NMS 8250, kept
  (off) on the FS-A1WSX** — also in SCREEN 2, where no key line is drawn [M xsubctx 4, 7, 9, 14, 15]. Entered with EI:
  on, key line off or on [M xsubctx 1, 13].

**Behaviour** (the same on all three references unless a machine is named).
- Writes $20 over 24 rows of the current name table (name-table rows 0-23, counted from 0), row length 40 in SCREEN 0
  (also at width 37), 80 in TEXT 2, 32 otherwise — 32 also when LINL32 is 29 (SCREEN 1 and SCREEN 2), so the row
  length is not LINL32; the rows after the 24th are left (name-table rows 24-26 still hold the probe's garbage)
  [M xsubctx 0, 5, 6, 8, 12].
  With CRTCNT 24 in every case, "24 rows" and "CRTCNT rows" are not separated, [A].
- The same in the graphic modes: in SCREEN 2 the 768 bytes from $1800 (the pattern-name table) := $20; in SCREEN 5
  the 768 bytes from VRAM $0000 (the first 6 lines of the bitmap) := $20 [M xsubctx 10, 11, 12]. The base is 0 in SCREEN 0
  and 5 and $1800 in SCREEN 1 and 2 — which work-area cell it is taken from is [A].
- Nothing else in the windows read changes: the pattern generator / blink table at $0800, the bytes just after the
  24 rows, $1000; SCREEN 1's colour table and patterns; SCREEN 2's colour table and patterns; SCREEN 5's lines past
  212 and the sprite tables [M xsubctx 0-11].
- CSRY := 1, CSRX := 1 [M xsubctx 0-11].
- LINTTB ($FBB2, 24 bytes) := 24, 23, ..., 1 (the entry for row r holds 25 − r) in every mode, graphic ones included
  [M xsubctx 0-11].
- In the text modes (SCREEN 0, 1), when CNSDFG ≠ 0 the function-key line is drawn on the last of the 24 rows
  (name-table row 23, screen line 24) as [DSPFNK](DSPFNK.md) draws it (7 characters a label at width 40, 15 at
  width 80, 5 in SCREEN 1), and CNSDFG := $FF — CNSDFG $01 gives the same key line and reads $FF after; when
  CNSDFG = 0 that row is left as spaces and CNSDFG stays 0 [M xsubctx 0, 4, 7, 9, 13, 14].
- In SCREEN 2 with CNSDFG $FF nothing is drawn: the 768 bytes are all spaces, as with the key line off, and CNSDFG
  stays $FF [M xsubctx 15].
- Mode, widths, CRTCNT and the register copies are not changed by the call: RG0SAV-RG7SAV read the same before and
  after the call in every case (RG7SAV differs between machines in SCREEN 1, 2 and 5: each machine's own border colour
  from the probe's CHGMOD) [M xsubctx 0-15].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject), [scratchpad/AE_xsubctx_msx2.out](../../../scratchpad/AE_xsubctx_msx2.out):
- text modes: the same clear, cursor home and LINTTB, but the key line is NOT redrawn (row 24 left as spaces with
  CNSDFG $FF), CNSDFG $01 is left $01 (the references set $FF), and interrupts are on on return also with the key line
  off; other registers (A $20, F $43, HL / IX kept) [M xsubctx 0-9, 13, 14];
- SCREEN 2 and 5: a graphic clear instead (SCREEN 2: patterns := $00, colour table := BAKCLR, the name table left;
  SCREEN 5: the bitmap := $44), with the cursor and LINTTB left as they were, also with the key line on
  [M xsubctx 10, 11, 12, 15].

## Open (not measured)

Recorded per case: A F BC DE HL IX IY, IFF (read twice), CSRY CSRX CNSDFG SCRMOD LINLEN CRTCNT LINL40 LINL32, LINTTB,
RG0SAV-RG7SAV after and before the call, per name-table row 0-26 the number of spaces and its first / last byte, rows 0 and 23 in full, three
16-byte windows per mode; the name table and the windows filled first with the address-dependent garbage
((a.lo + 3 a.hi) & $7F) | $80, LINTTB with $A0-$B7.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | — | DI and EI, key line off / on (also SCREEN 2, CNSDFG $01) | interrupt state on return | kept; ON with key line | kept; ON with key line | kept |
| CT-EX | — | SCREEN 0, all three machines | an entry at all | yes | yes | yes |
| CT-Z | Z set / clear, A $00 / $FF | SCREEN 0 | a Z gate like main-ROM CLS | none | none | none |
| CT-0 | — | SCREEN 0 (40, 37, 80), key line on / off, cursor (10, 12) | = CLS vs clear without home / key line / LINTTB | clear, home, LINTTB, key line | same | same |
| CT-1 | — | SCREEN 1, colour table garbage | colour table touched | no | no | no |
| CT-GR | — | SCREEN 2, 5 | does nothing vs clears vs switches to text | writes spaces over the name / bitmap start | same | same |
| CT-W32 | — | SCREEN 1, 2 with LINL32 29 | row length 32 vs LINL32 | 32 | 32 | 32 |
| CT-CNS | — | CNSDFG $01 | key line on any non-zero vs only $FF | drawn, CNSDFG := $FF | same | same |
| CT-KEYGR | — | SCREEN 2 key line on | key line drawn in a graphic mode | no; CNSDFG kept | same | same |
| CT-KEYG5 | — | SCREEN 5 (and 3, 4, 6-8) key line on | the same rule as SCREEN 2 vs drawn into the bitmap | ? | ? | ? |
| CT-GR8 | — | SCREEN 3, 4, 6, 7, 8 | the same rule | ? | ? | ? |
| CT-CRT | — | CRTCNT 13, 26 | 24 rows vs CRTCNT rows | ? | ? | ? |
| CT-BASE | — | TXTNAM / T32NAM / NAMBAS moved | which cell gives the base | ? | ? | ? |
| CT-REG | registers distinct | SCREEN 0 | registers kept | DE only (key line off) | same | same |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [CLS](CLS.md); [DSPFNK](DSPFNK.md).

## Tests that cover it

none yet
