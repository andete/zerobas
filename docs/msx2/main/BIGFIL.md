<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `BIGFIL` ($016B) — fill VRAM with a byte, without the 16 KB limit

> **Spec:** DRAFT 1 (2026-11-23): BF-1 - BF-6 and five VA states MEASURED on the HB-F900, NMS 8250 and FS-A1WSX
> (identical on all three; [xbf.asm](../../../probes/bios/spec/xbf.asm), [scratchpad/AE_xbf_msx2.out](../../../scratchpad/AE_xbf_msx2.out), decoded by [xbf_decode.py](../../../scratchpad/xbf_decode.py));
> VA-13, VA-14 (FS-A1WSX only) and VA-16 with the other four calls ([README.md](README.md#the-shared-vram-address-matrix) "Measured");
> entry A / F, the alternate registers, ports, save cells and VRAM sums with BC 1 in [xva3.asm](../../../probes/bios/spec/xva3.asm), [scratchpad/AE_xva3_msx2.out](../../../scratchpad/AE_xva3_msx2.out).
> Goldfish pass 1 (test writer) 2026-11-23: 5 findings, 2 measured, 0 moved to open.

## Summary

`BIGFIL` fills BC bytes of VRAM, from the address in HL, with A — as [FILVRM](../../bios/FILVRM.md),
but without FILVRM's MSX2 test of the screen mode: FILVRM treats VRAM as 16 KB in SCREEN 0-3, BIGFIL
takes its parameters as given in every mode. Where A16 comes from is not published.

## The specification

**Interface.**
- In: HL = the first VRAM address, BC = the length, A = the byte [P A1]. Out: none [P A1]. Changes:
  AF, BC [P A1].
- It does not test the screen mode; FILVRM does, and treats VRAM as 16 KB in SCREEN 0-3 [P A1].
  So AR-16K is not its rule in SCREEN 0-3 [P A1]; the rest of the rival rules of the
  [shared VRAM address matrix](README.md#the-shared-vram-address-matrix) stay open [A].
- **Measured** [M], the same on all three references:
  - The start address follows the [shared matrix's measured rule](README.md#the-shared-vram-address-matrix)
    exactly as NSETWR's: ACPAGE 2 + $C120 fills $1C120 (VA-3), ACPAGE 3 + $C120 fills $14120 (VA-5), SCREEN 1
    fills $0C120 -- no 16 KB mask (VA-8) -- and SCREEN 1 with ACPAGE 1 fills ACPAGE x $100 + E, $0015A (VA-11); with
    BC 1 in xva3, SCREEN 6, ACPAGE above 3 and SCREEN 7 / 8 with ACPAGE 2 / 3 too (the matrix's rules).
  - Its only port $99 writes are R#14 and the address (four writes); the bytes go out through the VDP's
    auto-increment: in SCREEN 5 a fill crosses $0FFFF into $10000 (BF-1) and a 16 KB bank into $04000 (BF-2), and
    R#14 is left at the bank of the address AFTER the last byte -- the VDP's carry: BF-4's last byte is $17FFF (bank
    5) and R#14 is $06; BF-1 and BF-2 ($04, $01) fit that and "the last byte's bank" alike. In SCREEN 1 it wraps from
    $03FFF to $00000 (BF-3), the VDP's 14-bit counter in that mode.
  - The length is exact: BC 1 fills one byte, $100 fills $08000-$080FF; **BC 0 fills 64 KB** ($08000-$17FFF, BF-4).
  - On return: **A kept** ($C7; $00 and $FF in xva3), **F = $42 OR the entry carry** ($42 from entry F $44 / $00,
    $43 from $FF), **BC $0000**, DE / HL / IX / IY kept (and BC' / DE' / HL' / AF' in xva3); **interrupts ON**,
    entered with them off or on (BF-6). With BC 1 (xva3): one port $98 write, no port $9A / $9B write, no save cell
    $FFE7-$FFF6 changed, and the 128 KB VRAM sum changes by the one byte only.
  - An interrupt during the call (VA-16, BC 1; [xva16.asm](../../../probes/bios/spec/xva16.asm), [scratchpad/AE_xva16_msx2.out](../../../scratchpad/AE_xva16_msx2.out)): never taken between its first and fourth port
    $99 write -- held until after the fourth -- and the address right at every step; interrupts on at the return.
    It re-enables interrupts inside the call after the fourth write and BEFORE its port $98 write (the rerun's stack
    depth and port $98 log), so the fill's bytes are outside the protected window.
  - SCREEN 10-12 (VA-14, the FS-A1WSX; [xva14.asm](../../../probes/bios/spec/xva14.asm), [scratchpad/AE_xva14_msx2.out](../../../scratchpad/AE_xva14_msx2.out)) and 64 KB of VRAM (VA-13): the start address follows
    the shared matrix exactly as NSETWR's -- SCRMOD 10 a 32 KB page, SCRMOD 8 / 11 / 12 a 64 KB one.
- Still open [A]: the stack depth and time (BF-9), a long fill across a frame with VDP interrupts enabled (BF-8), BF-7's
  other save cells, the display off.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) give every measured case but these: with ACPAGE not 0 in SCREEN 0-4 they
fill from HL AND $3FFF ($00120 for VA-11), where the references fill from ACPAGE x $100 + E, with five port $99
writes there instead of four (the fifth, $41, left in the latch until the port $98 writes); with ACPAGE above 3 in
SCREEN 5 / 6 or above 1 in SCREEN 7 / 8 they mask ACPAGE where the references add its high bits (xva3, the
[shared matrix](README.md#the-shared-vram-address-matrix)); and with SCRMOD 10 (VA-14, the MSX2+ build) they start in SCREEN 8's 64 KB page
($11235 after one byte from ACPAGE 1 + $1234) where the FS-A1WSX starts in SCREEN 5's 32 KB page ($09235) -- the
shared matrix's two differences.

## Open (not measured)

The [shared VA cases](README.md#the-shared-vram-address-matrix) VA-1 to VA-16 with HL lowered by 3,
BC $0008 and A $C7: S-MARK marks each rival's 8-byte span and the byte beyond each end, so no marked
byte is $C7 before the call; after it, the spans that read $C7 name the rule, the end bytes that
the length is exact, the block sums that nothing else changed. VA-8 to VA-11 check the
[P A1] statement that BIGFIL does not mask. Plus:

| case | inputs | state | separates | F900 | 8250 | WSX |
|---|---|---|---|---|---|---|
| BF-1 | HL $FFF8, BC $10, A $C7 | S-BASE, every rival's span marked (among them $0FFF8-$1000F and $00000-$00007) | crosses into $10000 vs wraps to $00000 (VDP carry vs a BIOS bank rule: the port log tells which wrote R#14) | crosses into $10000; R#14 $04 [M] | crosses into $10000; R#14 $04 [M] | crosses into $10000; R#14 $04 [M] |
| BF-2 | HL $3FF8, BC $10, A $C7 | S-BASE (entry R#14 $06, a bank neither $0xxxx span uses) | across a 16 KB bank: R#14 after = $06 (put back), $01 (left at the last byte's bank, or the next address's: the same here), or the first byte's $00 | into $04000; R#14 $01 [M] | into $04000; R#14 $01 [M] | into $04000; R#14 $01 [M] |
| BF-3 | HL $3FF8, BC $10 | SCREEN 1, R14 $00 | in a 16 KB mode: a wrap to $00000 vs straight on to $04000 | wraps to $00000 [M] | wraps to $00000 [M] | wraps to $00000 [M] |
| BF-4 | HL $8000, BC $0000, A $C7 | S-BASE | BC 0: nothing, or 64 KB (four windows: 8 bytes at $07FFC, $0FFFC, $17FFC, 4 at $18000 -- not block sums); and R#14 after: the last byte's bank (5) or the next address's (6) | 64 KB, $08000-$17FFF; R#14 $06 (the next address's) [M] | the same [M] | the same [M] |
| BF-5 | HL $8000, BC $0001 and $0100, A $C7 | S-BASE, $07FFF and $08001 / $08100 marked | the length is exact | exact ($08000; $08000-$080FF) [M] | exact ($08000; $08000-$080FF) [M] | exact ($08000; $08000-$080FF) [M] |
| BF-6 | xbf: HL $1231, BC 8, A $C7, DE $A55A, IX $4321, IY $8765 (their low bytes recorded), entry F $44 (interrupts off) / $00 (on); xva3: HL $1234, BC 1, A $C7 / $00 / $FF, F $00 / $FF, S-REGS | interrupts off, then on (xbf); off (xva3) | AF and BC on return (BC 0? A kept?); DE / HL / IX / IY / alternates kept; the interrupt state | A kept, F $42 OR entry carry, BC 0, the rest kept, IFF 1 either way [M] | the same [M] | the same [M] |
| BF-7 | HL $1234, BC $10 | as NSETRD's SR-3 | no other VDP register or save cell written | with BC 1 (xva3): four port $99 writes, no $9A / $9B, no save cell [M]; BC $10 not run | the same [M] | the same [M] |
| BF-8 | HL $8000, BC $4000 | S-BASE, interrupts on, VDP interrupts enabled | a fill that spans a frame: interrupts taken during it (the H.TIMI handler's count), the fill still exact | ? | ? | ? |
| BF-9 | HL $8000, BC $0100 | S-BASE | stack depth and time (README methods) | ? | ? | ? |

Also open: the display off.

## Related pages

[region page](README.md), [NSETWR](NSETWR.md), [NWRVRM](NWRVRM.md); MSX1 [FILVRM](../../bios/FILVRM.md).

## Tests that cover it

None yet.
