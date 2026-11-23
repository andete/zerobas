<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `KNJPRT` (sub-ROM $01BD) — draw a kanji on a bitmap screen

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`KNJPRT` draws one kanji, read from the kanji ROM by its JIS code, on a bitmap screen (SCREEN 5-8) —
the machine-code side of BASIC's `PUT KANJI`. It draws the full 16 x 16 character, or only its even or
odd dots. The kanji ROM and the cells it is assumed to use are on the
[concept page](../concepts/clock-and-misc.md#other-devices-the-calls-in-this-region-reach).

## The specification

Tags as on the [concept page](../concepts/clock-and-misc.md#references-subject-citation-tags).

**Interface.**
- Called through EXTROM / SUBROM with IX = $01BD [P A1].
- In: BC = the JIS kanji code; A = the display mode: 0 all 16 x 16 dots, 1 the even dots, 2 the odd
  dots [P A1]. Out: nothing listed [P A1].
- The registers it changes are not listed [P A1]; [P MAP] gives AF — [A].

**Behaviour.**
- It works on SCREEN 5-8 [P A1]. What it does on SCREEN 0-4 (and on the MSX2+'s 10-12) [A].
- `PUT KANJI` takes a position, a colour, a logical operation and the same mode, and needs a kanji ROM
  [P 2 (statement table)]. That the call takes the position from GRPACX / GRPACY, the colour from
  FORCLR or ATRBYT and the operation from LOGOPR is [A].
- Which dots "even" and "odd" are — rows, columns, or interlace fields [A].
- Whether the position moves after the call [A]; what happens at the screen's right / bottom edge [A];
  which page it draws on (ACPAGE) [A].
- What it does with a code outside the JIS kanji range, and without a kanji ROM [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

The measurement matrix. Fixtures as on the
[concept page](../concepts/clock-and-misc.md#shared-measurement-fixtures-for-the-call-pages-matrices).

**Kanji ROM.** Each reference's kanji ROM (level 1 at $D8 / $D9, level 2 if present) is recorded
before the matrix is read [A: which has which]. The subject machines (openMSX's C-BIOS MSX2 / MSX2+
configs, `tools/install_cbios_msx2.py`) carry NO kanji ROM: for a comparison they are given the SAME
kanji ROM image as the reference they are compared with, so the cases compare the call's code (which
dots go where, in which colour and operation) and never two fonts. The no-ROM case (KJ-10) runs on the
subject as shipped and on a reference with its kanji ROM removed.

Every case records: VRAM of the 16 x 16 cell plus a 4-dot margin on every side, on ALL pages the mode
has (four in SCREEN 5 / 6, two in 7 / 8); GRPACX / GRPACY, CLOC / CMASK, ATRBYT, LOGOPR after; the
VDP command registers R32-R46 and the status CE bit after return (whether a command is still running);
the register frame; the interrupt state; the emulated cycles.

| case | inputs | desynced state | what it separates |
|---|---|---|---|
| KJ-1 | SCREEN 5, 6, 7, 8 × A = 0, 1, 2 × BC = $2121, $3021, $4F53 (level 1) | GRPACX / GRPACY ≠ GXPOS / GYPOS ≠ CLOC / CMASK | the position's source; the dots drawn per mode |
| KJ-2 | KJ-1, mode 1 / 2 | interlaced and non-interlaced display | rows, columns or fields for "even" / "odd" |
| KJ-3 | KJ-1, one code | FORCLR ≠ ATRBYT ≠ BAKCLR | the colour's source; whether background dots are written |
| KJ-4 | KJ-1, one code | LOGOPR = 0-4, 8-12; VRAM under the cell patterned | the logical operation applied, transparency |
| KJ-5 | one code | ACPAGE ≠ DPPAGE, each page | the page it draws on (all pages read back) |
| KJ-6 | one code at the right edge (X = 248 in SCREEN 5 / 8, 504 in SCREEN 6 / 7) and the bottom edge (Y = 196 and 204 with 212 lines; 180 / 188 with 192), and at the last dot | — | clip, wrap or overrun |
| KJ-7 | BC = $0000, $2120, $7F7F, $FFFF, a code in a gap of the JIS table | — | range check, blank, or garbage |
| KJ-8 | BC = $5021, $7E7E (JIS level 2) | with and without a level-2 ROM | level-2 codes drawn, refused or blank |
| KJ-9 | A = 3, $FF | — | other modes |
| KJ-10 | KJ-1 without a kanji ROM | — | the no-ROM behaviour |
| KJ-11 | SCREEN 0-4; on the FS-A1WSX also 10-12 | — | no-op, fallback or VRAM damage |
| KJ-12 | any case | register frame; DI / EI on entry | the cursor advance; registers, flags, interrupt state; the time it takes |
| KJ-13 | the KJ-1 set through SUBROM | — | equal to EXTROM's results |

## Related pages
## Related pages

[the concept page](../concepts/clock-and-misc.md); the bitmap screens:
[screen-modes concept page](../concepts/screen-modes.md); [the inventory](../index.md).

## Tests that cover it

none yet
