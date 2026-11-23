<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `PCMPLY` ($0186) — play a memory area through the PCM

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the Panasonic FS-A1GT and FS-A1ST (identical in every output but
> timing jitter). Probes and runs: [xpcmply.asm](../../../probes/bios/spec/xpcmply.asm),
> [scratchpad/AE_xpcmply_tr.out](../../../scratchpad/AE_xpcmply_tr.out) (decoded by
> [scratchpad/xpcmply_decode.py](../../../scratchpad/xpcmply_decode.py):
> [scratchpad/AE_xpcmply_tr_decoded.out](../../../scratchpad/AE_xpcmply_tr_decoded.out)); the `$00` code:
> [xpcmcmp.asm](../../../probes/bios/spec/xpcmcmp.asm), [scratchpad/AE_xpcmcmp_tr.out](../../../scratchpad/AE_xpcmcmp_tr.out)
> (decoded by [scratchpad/xpcmcmp_decode.py](../../../scratchpad/xpcmcmp_decode.py)); STOP held and the inputs that
> do not return: [xpcmstop.asm](../../../probes/bios/spec/xpcmstop.asm),
> [scratchpad/AE_xpcmstop_tr.out](../../../scratchpad/AE_xpcmstop_tr.out) (decoded by
> [scratchpad/xpcmrec_decode.py](../../../scratchpad/xpcmrec_decode.py):
> [scratchpad/AE_xpcmstop_tr_decoded.out](../../../scratchpad/AE_xpcmstop_tr_decoded.out)); CTRL+STOP pressed during the
> sound: [xpcmmid.asm](../../../probes/bios/spec/xpcmmid.asm), [scratchpad/AE_xpcmmid_tr.out](../../../scratchpad/AE_xpcmmid_tr.out);
> the goldfish pass's cases: [xpcmply2.asm](../../../probes/bios/spec/xpcmply2.asm),
> [scratchpad/AE_xpcmply2_tr.out](../../../scratchpad/AE_xpcmply2_tr.out)
> ([decoded](../../../scratchpad/AE_xpcmply2_tr_decoded.out), xpcmply's decoder), and STOP alone during a `$00` run:
> [xpcmmid2.asm](../../../probes/bios/spec/xpcmmid2.asm), [scratchpad/AE_xpcmmid2_tr.out](../../../scratchpad/AE_xpcmmid2_tr.out).
> All timing is openMSX's model.
> Goldfish pass 1 (test writer) 2026-11-23: 9 findings, 6 measured, 1 moved to open.

Main-ROM entry, turbo R only. Listed by MAP's "MSX turbo R BIOS Entries" ([index](../index.md)); C-BIOS has no
turbo R build.

## Summary

`PCMPLY` writes a block of bytes from RAM or VRAM to the PCM's D/A port $A4, one byte per sample, at the rate A bits
1-0 select: about 15.7, 7.85, 5.23 or 3.92 kHz. A data byte `$00` is a code: `$00 n` plays n samples of `$80`
(silence; n = 0 means 256). The sound is always played by the R800 — called from the Z80 it switches to R800 ROM
mode and back. STOP (with or without CTRL, held at entry or pressed during the sound) ends it with carry set and
A = 2, HL / E at the next data byte and D:BC the data bytes left; a normal end returns A = 0, carry clear. Every
register is changed, and it returns with interrupts enabled. With A = $08 and no key pressed the call never returns.

## The specification

**Interface** [P MAP]: input `A = v 0 0 0 0 0 x x` (v = the data is in VRAM; xx = "quality parameter (speed: 0 = fast)"), HL = start address in RAM or VRAM, BC = length, D bit 0 = bit 17 of the length and E bit 0 = bit 17 of the start address when in VRAM. Output: carry set when aborted with CTRL-STOP. Registers: all.

**Evidence.** `[XP n]` = case n of xpcmply (37 cases): per case CHGCPU to the start mode, every register loaded
(the inputs per case, the rest distinct garbage), the VDP interrupt off, CALL $0186; then every register, the
interrupt state, the S1990's register 6, GETCPU, ports $A4 / $A5 / $A7, $FCB1, the work-area cells that changed,
every OUT to $A4, $A5, $E4, $E5 and $A7 during the call (openMSX watchpoints), and the emulated time between two
breakpoints around the call. The data: P1 = $10, $11, ... (no $00) in RAM and VRAM; the rest of VRAM is $55.
`[XK n]` = xpcmcmp case n (short patterns with $00). `[XS n]` = xpcmstop case n (keys held from before the call to
after it, through `@keyset`). `[XM]` = xpcmmid (CTRL+STOP pressed while it plays, `@matrix`). `[XP2 n]` = case n of
xpcmply2 (16 cases, xpcmply's code and record; P4 = `10 00 05 20` at RAM $8300 and VRAM $08000; a $FCB1 override per
case). `[XM2]` = xpcmmid2 (STOP alone pressed while it plays 64 bytes of `$00`).

**What it plays** [M]:
- One OUT $A4 per sample, the data byte as it is, preceded by OUT $A4,$80 and followed by OUT $A4,$80: 64 bytes give
  66 OUTs, `80 10 11 ... 4F 80` [XP 0-7, 9-13, 19-30, 32-36]. Length 1: `80 10 80` [XP 16]; length 2: `80 10 11 80`
  [XP 14, 15].
- Port $A5: OUT $A5,$03 twice, at the start and at the end [XP, every logged case]. IN $A5 reads $83 before and after
  (bits 1-0 as written, bit 7 set) [XP]. What the $A5 bits mean is not from a source read here [A].
- **The `$00` code** [XK 0-17]: a `$00` byte and the byte after it are a pair: `$00 n` plays n samples of $80, and the
  pair counts 2 bytes of the length: `10 00 05 20` → `10 80 80 80 80 80 20` (inside the framing $80s). n = 1, 2, 3,
  $10, $7F, $80, $81, $FF give 1, 2, 3, 16, 127, 128, 129, 255 samples; **n = 0 gives 256** [XK 17]. It plays $80,
  not the previous sample [XK 0]. Two pairs both count [XK 8]; a leading `$00` works the same [XK 7]; a `$00` as the
  LAST byte of the length plays nothing (the byte after the block is not taken as its count) [XK 10, 11]. `$01`,
  `$80`, `$FF` are plain samples [XK 4-6]. `10 00 05 20` plays the same `80 10 80 80 80 80 80 20 80` from VRAM
  [XP2 0], from the Z80 [XP2 1], from R800 ROM mode [XP2 2], at rate code 3 [XP2 3], and from the Z80 at rate code 3
  from VRAM [XP2 4], so the code does not depend on the source, the CPU mode or the rate. Cross-check: xpcmply's P2 table, 64 bytes holding 17 such pairs, plays
  2938 samples (187.4 ms) [XP 8], exactly what the rule predicts. MAP's interface line does not mention this code.
- **RAM** (A bit 7 = 0): HL = the address, BC = the length (1-128 logged; 0 and > 128 not run in RAM); D and E are
  not used — D = E = $FE plays 64 bytes and returns DE = $FEFE [XP 30]. Sources in page 2 and page 3 play as written
  [XP 0, 13]. **Page 1 is not the caller's slot during the call:** a first run (not kept) played this cartridge's
  $6000 and a span crossing $7FFF / $8000, and the bytes sent to $A4 were not the cartridge's. What page 1 holds then
  is another slot's content (a ROM, by every indication), which the clean room does not read: that log was discarded
  and the cases removed. So "the cartridge's page 1 is not what is played" is [M]; what a page-0 / page-1 source
  plays is not specified here.
- **VRAM** (A bit 7 = 1): the address is E:HL — E = 0 plays $04000 [XP 9], E = 1 plays $14000 [XP 10]. The address
  runs on across $03FFF / $04000 [XP 32] and across $0FFFF / $10000 (17 bits: $A0... at $0FFE0, then $E0... at
  $10000) [XP 18]. E = $FE does NOT play $04000 (it played $55s), so E's bits above bit 0 are not ignored [XP 33];
  exactly how they count [A]. The length is D:BC — D = 1 plays 65600 samples (4.179 s) [XP 17], and **D = 2 plays
  131136 (8.353 s)** [XP 31], so D is more than "bit 0". D = $FF: with CTRL+STOP held it aborts at once [XS 13];
  without a key it did not return within about 115 s in a first run (not kept) — $FF0040 samples would take about
  18 minutes [A].
- Length 0 (VRAM): with CTRL+STOP held it aborts like any other [XS 12]; without a key not run in a kept run.

**The rate, A bits 1-0** [M]: the time per sample = (128 − 64 samples) / 64, both machines; R800 DRAM [XP 0-7],
from the Z80 [XP 21-25, 34-36]; R800 ROM rate code 0: 63.8-63.9 µs [XP 26, 28]:

| A bits 1-0 | µs per sample (R800 DRAM) | rate | from the Z80 |
|---|---|---|---|
| 0 | 63.6-63.9 | ≈ 15.7 kHz | 63.4 |
| 1 | 127.4 | ≈ 7.85 kHz | 126.5-127.6 |
| 2 | 191.1 | ≈ 5.23 kHz | 190.9 |
| 3 | 254.8 | ≈ 3.92 kHz | 254.0-254.9 |

So 1, 2, 3, 4 periods of one ≈ 63.6 µs clock; that this clock is the 15.75 kHz line rate is [A]. The fixed cost of a
call is 190-240 µs in the R800 and 850-960 µs from the Z80 [same cases]. Over 65600 samples: 63.70 µs per sample
[XP 17]. VRAM as the source: the same [XP 9, 12].

**A bits 6-2** [M]: bit 2 changes nothing (A = $04 plays exactly like A = $00) [XP 11]. **A = $08 never returns**: a
first run logged one OUT $A4,$80 — the leading $80 every play starts with, not a data byte — then nothing for 140 s; in the kept run the call is entered and does
not come back within 115 s [XS 14]. With CTRL+STOP held, A = $08, $10, $20, $40 and $7C all abort at once like A = $00
[XS 7-11]; whether $10, $20, $40, $7C also hang without a key was not run ($7C did, in a first run not kept).

**The CPU** [M]:
- In R800 ROM and DRAM mode the call stays in the mode: one OUT $E4,6 (selecting the S1990's register 6, read), no
  OUT to $E5 or $A7; GETCPU and R#6 unchanged after [XP 0-20, 26-28, 30-33].
- **Called from the Z80 it plays in R800 ROM mode:** OUT $E4,6 three times, OUT $E5 = $40, $60, $60 (R800 ROM, then
  the Z80 as [CHGCPU](CHGCPU.md) writes it), OUT $A7 = $00 then $02, and $FFFD / $FFFE (MAP: CHGCPU's stack pointer)
  changes from $E7E8 to $E7D8 [XP 21-25, 29, 34-36]. It returns in the Z80 (cpusnap, GETCPU 0, R#6 $60), $FCB1 back
  at $02. The Z80 never plays the sound [M].
- **$A7 follows $FCB1 as CHGCPU($01) then CHGCPU($00) would write it**: bit 1 cleared for the R800 and set again,
  bit 7 kept. With $FCB1 = $02 the OUTs are $00, $02 [XP 21-25]; with $FCB1 = $82 (the LED bit set, after
  CHGCPU($00)) they are $80, $82 and $FCB1 ends at $82 [XP2 5] [M].

**Return state** [M]:
- Played to the end: A = 0, carry clear; F = $44 (Z and P/V) plus **bits 5 and 3 of the entry F**: entry F $00,
  $40, $04, $44 → $44, entry F $28, $FF → $6C (R800 DRAM, `10 00 05 20`) [XP2 8-13]; $44 → $44 with 64 bytes and no
  `$00` [XP2 14]; from the Z80, $FF → $6C [XP2 6], $00 → $44 [XP2 1]; also [XP 0, 20] [M]. Bits 5 and 3 were only
  entered together; each alone was not run. xpcmcmp's cases all return $6C [XK 0-17]: there F came from `xor a`
  executed on the R800 just before the call, and on the R800 a flag result can keep the old bits 5 / 3 (as GETCPU's
  does, [GETCPU](GETCPU.md)), so that entry F is not known [A]. HL = the address after the last byte read (RAM: HL + BC; VRAM: the low 16 bits), BC = 0; VRAM:
  D = 0 and E = bits 16 and up of the end address (E = 1 after $0FFE0 + 64, E = 2 after $04000 + $20040)
  [XP 17, 18, 31]; RAM: DE kept [XP 30]. Every other register is changed, to the same values in every case on both
  machines: IX = $71DB, IY = $0054, AF' = $0044, BC' = $F400, DE' = $F300, HL' = $FCC5 [XP 0-36].
- **Interrupts enabled** on return, entered DI or EI [XP 0-36; 19 entered EI]; from the Z80 entered EI too [XP2 7].
- No work-area cell in $F380-$FFFE changes in the R800 modes (VDP interrupt off) [XP]; from the Z80 only $FFFD
  [XP 21-25, 29, 34-36]. Slots: $A8 and page 3's secondary register as on entry ($F4 / $00) [XP].

**STOP** [M]:
- STOP held at entry, with or without CTRL: nothing is played (OUT $A4 $80, $80 only), A = 2, F = $45 (carry set),
  HL, BC and DE as on entry, interrupts enabled — in the Z80, R800 ROM and DRAM, RAM and VRAM [XS 1, 2, 4-6]. CTRL
  alone changes nothing [XS 3].
- CTRL+STOP pressed during the sound (65600 samples at rate code 3 from VRAM $04000): the call returned 87.4 ms later
  with A = 2, carry set, HL = $4156 and E = 0 (the next address), D:BC = $00:$FEEA = 65600 − 342 left [XM]. That data
  has no `$00`, so bytes and samples are the same count there.
- **STOP alone** pressed during the sound ends it the same way, and **D:BC counts data bytes, not samples** [XM2]: 64
  bytes of `$00` from RAM $8000 at rate code 3 (32 pairs `$00 $00`, 8192 samples of $80); the call returned
  130.6 ms after it began with A = 2, F = $45, HL = $8004, BC = $003C (60), D = E = 0 — two pairs played (2 × 256 ×
  254.8 µs = 130.5 ms) and 60 bytes left. STOP was pressed at most 0.1 s into the call, so the key was acted on only at
  the end of the 256-sample run it fell in [M for this case; that STOP is checked per data byte, never inside a run, A].
  So an abort leaves HL / E at the next data byte and D:BC at the bytes left, and a second call with them would
  continue [M for the registers; the continuation A].

## Differences

**FS-A1GT vs FS-A1ST:** none in any output of any case — registers, flags, interrupt state, port writes, S1990,
$FCB1, $FFFD, work-area changes — beyond up to 100 µs of timing jitter per call (the start phase) [XP, XK, XS, XM,
XP2, XM2], and IN $A4 after the call: it reads $00, $01, $02 or $03, and differs between the models in [XP 8, 24, 35,
36], [XS 7, 8, 10, 11, 12] and [XP2 2]. Port $A4 is the D/A the call writes; what reading it returns is not known
[A], so it is not counted as an output of the call.

**C-BIOS / zerobas:** no turbo R build; nothing to compare.

## Open (not measured)

- A source in page 0 or page 1 (the clean room forbids reading what the call would play there).
- RAM lengths above 128 and length 0 in RAM; a RAM area crossing $BFFF / $C000 (the probe's capture sits there) or
  $FFFF (it would run into page 0); VRAM length 0 without a key.
- Exactly how E's bits above bit 0 and D's bits form the VRAM address and length (E = $FE, D = 2 measured only).
- Whether A = $10, $20, $40 hang without a key as $08 does (each needs a run of its own).
- What the sound is: openMSX's audio output was not recorded, only the OUTs; the meaning of the $A5 bits.
- What IN $A4 reads (it differs between the models and between cases with the same input, above).
- Return F with entry F bit 5 or bit 3 alone ($20, $08); whether STOP can end a play inside a `$00` run (one case
  [XM2] says no).
- Real-hardware timing; stack depth.
- The MSX Turbo-R Technical Handbook's text for PCMPLY (not read; the interface line is MAP's).

## Related pages

[turbo R index](../index.md); [PCMREC](PCMREC.md); [CHGCPU](CHGCPU.md); [GETCPU](GETCPU.md).

## Tests that cover it

None yet.
