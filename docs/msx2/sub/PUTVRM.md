<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `PUTVRM` (sub-ROM $0129) — put a byte at a text position (column H, row L) in the name table

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubpvr.asm](../../../probes/bios/spec/xsubpvr.asm), [scratchpad/AE_xsubpvr_msx2.out](../../../scratchpad/AE_xsubpvr_msx2.out); round 2 [xsubpvr2.asm](../../../probes/bios/spec/xsubpvr2.asm), [scratchpad/AE_xsubpvr2_msx2.out](../../../scratchpad/AE_xsubpvr2_msx2.out); round 3 [xsubpvr3.asm](../../../probes/bios/spec/xsubpvr3.asm), [scratchpad/AE_xsubpvr3_msx2.out](../../../scratchpad/AE_xsubpvr3_msx2.out); decoded by [scratchpad/xsubpvr_decode.py](../../../scratchpad/xsubpvr_decode.py)).
>
> Goldfish pass 1 (test writer) 2026-11-23: 5 findings, 4 measured, 0 moved to open.

## Summary

A sub-ROM entry of the MSX2 (standard: MSX2; listed in MAP only — the Technical Handbook does not
list it, so no published interface exists). By measurement it writes the byte in **C** to the name
table at the text position **column H, row L** (both counted from 1): VRAM address NAMBAS +
(L − 1) × the row width + (H − 1) + the left margin LINLEN leaves; the row width is 32 outside
SCREEN 0, and in SCREEN 0 follows LINLEN (80 above 40, else 40), not the VDP's 40 / 80-column mode. The cursor, the work
area and every other VRAM byte are left alone. The three references agree on every measured
output. C-BIOS has no entry here (its sub-ROM holds a bare `RET` at $0129).

Shared facts — the screen state and NAMBAS / LINLEN: [the screen-modes page](../concepts/screen-modes.md);
VRAM and R#14: [vdp-and-palette.md](../concepts/vdp-and-palette.md).

## The specification

Evidence tags: **[PV1 k]** = case k of round 1 (xsubpvr.asm: SCREEN 0 at width 40 = cases 0-2, width
80 = 3-5, SCREEN 1 = 6-8, SCREEN 5 = 9-11; LINLEN = LINL40 = LINL32 = the width, NAMBAS as CHGMOD set
it); **[PV2 k]** = case k of round 2 (xsubpvr2.asm: cases 0-3 SCREEN 0/40, 0/80, 1, 5 with LINLEN,
LINL40, LINL32, NAMBAS, TXTNAM and T32NAM each set to a value no other source holds; cases 4-7 the
edges of H / L); **[PV3 k]** = case k of round 3 (xsubpvr3.asm, which also records LINLEN, LINL40, LINL32,
NAMBAS, TXTNAM, T32NAM, SCRMOD, RG0SAV and RG1SAV just before the call: case 0 the 80-column mode with LINLEN
40, case 1 the 40-column mode with LINLEN 60, cases 2-4 round 2's edges H 41 / H 0 / L 0 with NAMBAS $0400,
cases 5-7 the edges H 41 L 1 / H 0 L 3 / H 5 L 0 at LINLEN 37, case 8 SCREEN 1 and case 9 SCREEN 5 as CHGMOD
leaves them, case 10 SCREEN 0 (40 columns) with LINLEN 29, case 11 SCREEN 1 with LINLEN 40). Every case enters with interrupts off, every register distinct, CSRX / CSRY set to
values unlike H / L, VRAM $0000-$7FFF filled with an address-dependent pattern, and records every
register, the interrupt state (read twice), every changed work-area byte ($F380-$FFFE), every changed
VRAM byte in $0000-$7FFF, sums of VRAM $8000-$1FFFF, and the whole VDP state before / after (@vdpfull).
The three references give the same values in every case (only the VDP status registers, read at
different moments, and the interrupt-counter cells differ) [PV1 0-11] [PV2 0-7] [PV3 0-11].

### Interface

- **In:** C = the byte; H = the column, L = the row, both from 1 [M PV1 0-11]. A, B, DE and the cursor
  (CSRX / CSRY) are not inputs: the written byte is C in every case where A ≠ C, and the address does
  not follow CSRX / CSRY or DE [M PV1 0-11].
- **Out:** A := C [M PV1 0-11, PV2 0-7, PV3 0-11]; DE := the offset (L − 1) × width + (H − 1) + margin, without
  NAMBAS (e.g. $0054 for H 5, L 3 at width 40; $00A8 at LINLEN 72 in the 80-column mode) [M PV1 0-11,
  PV2 0-7, PV3 0-11]. BC, HL, IX, IY and SP are kept (IY still held the probe's own previous pointer) [M PV1 0-11].
  **F** = the flags of an `OR` that gives ((address of the byte) high byte AND $3F) OR $40 — the VDP's
  write-setup byte: S, Z and bits 5 / 3 from it, P/V = its parity, H = N = C = 0. It read $00, $04, $08, $0C,
  $28 and $2C, and all 32 measured values fit (e.g. $2BD8 → $6B → $28, $1844 → $58 → $08, $0456 → $44 → $04)
  [M PV1 0-11, PV2 0-7, PV3 0-11]. Every address was below $4000, so the AND $3F is [A]; a test that does not
  set up such an address leaves F to this rule or leaves it out.
- **Interrupts:** entered with interrupts off, the call returns with them **on** (IFF = 1, and one
  timer interrupt ran inside the call: JIFFY +1, INTCNT −1, SCNCNT −1) [M PV1 0-11, PV2 0-7, PV3 0-11]. Entry
  with interrupts on: [A].

### Behaviour

- **The address** is NAMBAS ($F922) + (L − 1) × W + (H − 1) + M, where
  - **NAMBAS**, not TXTNAM / T32NAM / R#2, is the base: with NAMBAS $0400, TXTNAM $0800, T32NAM
    $0C00 the byte went to $0456 / $04A8 / $0447 / $0447 in SCREEN 0/40, 0/80, 1 and 5 [M PV2 0-3];
    with CHGMOD's own NAMBAS ($0000 in SCREEN 0 and 5, $1800 in SCREEN 1) to $0054 / $00A4 / $1844 /
    $0044 for H 5, L 3 [M PV1 0, 3, 6, 9];
  - **W**, the row width: **32 when SCRMOD ≠ 0** (SCREEN 1 and 5, also SCREEN 1 with LINLEN 40)
    [M PV1 6-11, PV2 2-3, PV3 8, 9, 11]; in SCREEN 0 **80 when LINLEN > 40, else 40 — whatever the VDP's
    mode**: the 80-column mode with LINLEN 40 used W = 40 (offset $0054 for H 5, L 3), the 40-column mode with
    LINLEN 60 used W = 80 ($00AE = 2 × 80 + 4 + 10), and LINLEN 29 in SCREEN 0 used W = 40, not 32
    ($005A = 2 × 40 + 4 + 6) [M PV1 0-5, PV2 0-1, PV3 0, 1, 10];
  - **M**, the left margin, is (W − LINLEN + 1) / 2 rounded down, from **LINLEN** ($F3B0), not LINL40 /
    LINL32: LINLEN 37 / 72 / 27 / 27 gave M = 2 / 4 / 3 / 3 with LINL40 33 / 75, LINL32 29 (which
    would give 4 / 3 / 2 / 2) [M PV2 0-3]; M = 0 with LINLEN = W (recorded: LINLEN 40 at W 40, 32 in SCREEN 1
    and in SCREEN 5, the 32 SCREEN 1's CHGMOD left) [M PV3 2-4, 8, 9] — round 1 did not record LINLEN, its
    M = 0 rests on CHGMOD having set LINLEN := the width (SCREEN 0 / 1) or left SCREEN 1's 32 (SCREEN 5)
    [M PV1 0-11, inferred]. With LINLEN > W the difference is taken as a byte and halved unsigned: SCREEN 1
    with LINLEN 40 gave M = ($F9) / 2 = $7C = 124 (offset $00C0 = 2 × 32 + 4 + 124) [M PV3 11].
- **No clamping, 8-bit position arithmetic:** H 41 at width 40 writes row 2, column 1 (offset 40)
  [M PV2 4, PV3 2]; L 25 writes offset 960 [M PV2 5]; H 0 gives offset $00FF ((H − 1) taken as the byte $FF)
  [M PV2 6, PV3 3]; L 0 gives offset $27D8 = 255 × 40 [M PV2 7, PV3 4]. In round 2 these bytes landed at $0800
  + the offset — NAMBAS was not recorded there, $0800 being the TXTNAM case 3 left, copied by CHGMOD; round 3
  repeated H 41, H 0 and L 0 with NAMBAS $0400 recorded and they landed at $0400 + the offset [M PV3 2-4].
  **With a margin** (LINLEN 37, M 2) the margin is added after, as 16 bits: H 41 L 1 → 42, H 0 L 3 → 2 × 40 +
  255 + 2 = 337 ($0151, not the 8-bit 81), H 5 L 0 → $27D8 + 4 + 2 = $27DE [M PV3 5-7].
- **SCREEN 5 is not drawn as a character:** the byte C itself lands in the bitmap at NAMBAS + offset
  with W = 32 (one byte = two pixels), nothing else changes [M PV1 9-11, PV2 3].
- **Nothing else changes:** exactly one VRAM byte in $0000-$7FFF differs from its pattern, the sums of
  $8000-$1FFFF are unchanged, the work area changes only by the timer interrupt (SCNCNT, JIFFY,
  INTCNT, STATFL), CSRX / CSRY are kept [M PV1 0-11, PV2 0-7].
- **The VDP after the call:** R#14 = 0 [M PV1 0-11, PV3 0-11] (the byte's address was below $4000 in every case;
  an address at or above $4000: [A]); the VDP address counter = the written address + 1 (its 14 bits)
  [M PV1 0-11]; no other VDP register changes [M PV1 0-11].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) have no PUTVRM: the sub-ROM's $0129 holds `RET` ($C9), so
calling it returns at once — nothing written to VRAM, A / DE unchanged (A = $41 and DE = $090B where
the references give C and the offset), interrupts left off ([scratchpad/AE_xsubpvr_msx2.out](../../../scratchpad/AE_xsubpvr_msx2.out),
[scratchpad/AE_xsubpvr2_msx2.out](../../../scratchpad/AE_xsubpvr2_msx2.out),
[scratchpad/AE_xsubpvr3_msx2.out](../../../scratchpad/AE_xsubpvr3_msx2.out), every case on all three rows).

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: every case gives the same bytes as on the FS-A1WSX, on both models except the VRAM-sum / counter pairs that move with JIFFY (one count apart), R#36 = $80 (the boot's last VDP command) and VDP S#2 (read at a random moment) -- timing [M] ([AE_trall/xsubpvr.out](../../../scratchpad/AE_trall/xsubpvr.out), [AE_trall/xsubpvr2.out](../../../scratchpad/AE_trall/xsubpvr2.out), [AE_trall/xsubpvr3.out](../../../scratchpad/AE_trall/xsubpvr3.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

- SCREEN 2, 3, 4 and 6, 7, 8; MODE's address-mask bit ($FAFC bit 3) and ACPAGE ≠ 0 (both change the
  sub-ROM's [NWRVRM](NWRVRM.md) addressing); a target address at or above $4000.
- Entry with interrupts on; F for an address at or above $4000 (the AND $3F of the rule).
- Whether the purpose is the screen editor's "put a character" step: what the entry is for cannot be
  pinned down from its effects beyond the rule above.

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [NWRVRM](NWRVRM.md); [INITXT](INITXT.md);
MSX1 [WRTVRM](../../bios/WRTVRM.md), [CHPUT](../../bios/CHPUT.md).

## Tests that cover it

none yet
