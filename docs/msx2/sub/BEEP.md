<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `BEEP` (sub-ROM $017D) — sound the beep set by SET BEEP

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubbeep.asm](../../../probes/bios/spec/xsubbeep.asm), [scratchpad/AE_xsubbeep_msx2.out](../../../scratchpad/AE_xsubbeep_msx2.out), decoded by [xsubbeep_decode.py](../../../scratchpad/xsubbeep_decode.py)).

## Summary

On the MSX2 the beep is a setting: `SET BEEP` chooses one of four sounds (high, low, two-tone,
three-tone) and one of four volumes, kept in the clock IC's battery-backed memory. The sub-ROM's `BEEP`
plays it; the main ROM's [BEEP ($00C0)](../../bios/BEEP.md) gives the same writes on all three references.
Where the setting lives is on the [concept page](../concepts/clock-and-misc.md#block-2--the-basic-settings).

Measured: the call reads block 2 register 10 from the clock IC at every call, plays the sound to the end
before it returns (36-733 ms), and leaves R8-R10 at 0 and R7 at $B8. The three references write the same
PSG sequence for each of the 16 settings. C-BIOS's MSX2 / MSX2+ sub-ROM BEEP writes nothing to the PSG.

## The specification

Tags as on the [concept page](../concepts/clock-and-misc.md#references-subject-citation-tags).
**[M XB n]**: case n of [xsubbeep.asm](../../../probes/bios/spec/xsubbeep.asm), run 2026-11-23 on all three
references with `--fresh` (empty clock-chip state), [scratchpad/AE_xsubbeep_msx2.out](../../../scratchpad/AE_xsubbeep_msx2.out).
Before each case: PSG R0-R13 := $A1 $02 $B3 $04 $C5 $06 $17 $B8 $09 $0A $0B $5C $1D $0E, block 2 register 10 := V
through the clock IC's ports (no reset in between), BC $1357, DE $2468, HL $369C, IY $8765, A $C3. Cases 0-15:
V = 0-15 through EXTROM, entered with DI; 16: V = $F through the main ROM's $00C0; 17: V = 6, entered with EI,
MODE := $07 (block 3, TE 0, AE 1) just before the call. Every OUT to $A1 except R15's is timed (`@psglog`;
the timer interrupt writes R15 $8F / $CF every frame and nothing else, seen in an unfiltered first run).
`xsubbeep_decode.py --cmp` compares the three references' write sequences.

**Interface.**
- Called through EXTROM / SUBROM with IX = $017D [P A1]. No input, no output; all registers may
  change [P A1].
- Registers on return, all three references [M XB 0-17]: A = the clock IC's MODE register as it was on
  entry ($0B; $07 in case 17), F $18 ($10 in case 17); B $0E; C $D0 for tone codes 0, else the volume code
  (V AND 3); D $24; E the R8 level for tone code 0 ($04 / $07 / $0A / $0F), else 0; HL and IY kept;
  IX $0090 through EXTROM.
- Interrupts on return [M XB 0-17]: **on** on the HB-F900 and NMS 8250 whether entered with DI or EI; on the
  **FS-A1WSX as entered** (off in cases 0-16, entered with DI; on in case 17, entered with EI) -- the
  references differ.
- The clock IC's MODE is left as found (block bits and TE / AE), also when it pointed at block 3 with
  TE 0 [M XB 17]: the call selects block 2 itself.
- The main ROM's BEEP ($00C0) with the same setting writes the same PSG sequence, with the same timing, on
  all three references, and leaves the same registers except IX (kept there) [M XB 16 vs 15]; that it calls
  this entry is [A].

**Behaviour.**
- The setting is read from the clock IC (block 2, register 10) at **each call**: cases 0-15 changed it
  through the ports between calls, with no reset, and each call followed its own value [M XB 0-15]. Bits 3-2
  pick the sound, bits 1-0 the volume [M XB 0-15], as [P 5§6.7] says.
- The volume code 0 / 1 / 2 / 3 is the starting PSG amplitude **4 / 7 / 10 / 15** [M XB 0-15].
- The sounds (periods are R0/R1 = tone A, R2/R3 = B, R4/R5 = C; "decay" = the amplitude written to the
  channels steps down by 1 from the start level to 1, at equal intervals, the whole decay lasting the
  segment's length) [M XB 0-15]:

| bits 3-2 | sound | PSG writes, in order |
|---|---|---|
| 00 | one tone, A only | R0 $55, R1 $00, R7 $BE, R8 := level; held ~43 ms (all volumes); then R8, R9, R10 := 0, R7 := $B8 |
| 01 | a chord on A, B, C | R7 $B8, R2/R3 $00A7, R4/R5 $00A8, R0/R1 $00A6, R8-R10 := level, decaying over ~365 ms; then R8, R9, R10 := 0, R7 := $B8 |
| 10 | two tones on A | R7 $BE; tone $002A, R8-R10 := level, decay over ~365 ms; tone $0035, the same; then R8, R9, R10 := 0, R7 := $B8 |
| 11 | three tones on A | R7 $BE; tones $006B, $0047, $0055, each R8-R10 := level and a decay over ~122 ms; then R8, R9, R10 := 0, R7 := $B8 |

- The decay writes R8, R9 and R10 together, also for the sounds that enable tone A only (R7 $BE)
  [M XB 4-15]. Sound 00 writes R8 only before its end; R9 / R10 keep what they held (the probe's $0A / $0B)
  until the final writes [M XB 0-3].
- The call is synchronous: the whole sound is played before it returns, ~44 ms (sound 00), ~365 ms (01, 11)
  or ~730 ms (10) after entry; nothing is written in the 10 frames after the return with interrupts on
  [M XB 0-17]. The three references agree within ~1.5 % on these times (the NMS 8250 the slowest) [M XB].
- PSG left on return [M XB 0-17]: R0-R5 as the sound last set them (sound 00 leaves R2-R5 as found), R6 and
  R11-R13 as found, R7 $B8, R8-R10 0.
- PPI port C is left as found (bit 7 not exercised) [M XB 0-17].
- Whether it also resets the PLAY queues, MUSICF and PLYCNT, as the MSX1 BEEP's GICINI does [A] (BP-5).

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject), all three rows [M XB]:
- **The sub-ROM BEEP is a no-op:** no PSG write, returns after ~0.6 ms with every register kept (A $C3,
  F $93 as entered), the PSG garbage untouched.
- **The main ROM's BEEP ($00C0) ignores the setting:** it plays the MSX1 beep (R0/R1 $0055, R7 $BE, R8 $07,
  ~44 ms, then R8-R10 := 0, R7 := $B8) for every setting, and returns A $00, F $44, BC $0000, E $07
  [M XB 16]; the references play the setting (case 16 = case 15).
- Interrupts: on on return in every case (as the HB-F900 / NMS 8250; the FS-A1WSX keeps DI).

## Open (not measured)

Measured so far: BP-1 (through the ports, without a reset: BP-3's question answered by it), BP-4 (one
MODE value), BP-7, BP-8 (entry DI and EI; the tail), BP-9 (EXTROM and $00C0 only), BP-12. Still open:

| case | inputs | desynced state | what it separates |
|---|---|---|---|
| BP-2 | `SET BEEP t, v` for t, v = 1-4, reset, then the call; block 2 reg 10 dumped | — | BASIC's encoding against BP-1's (the page assumes BASIC's `SET BEEP t, v` writes (t-1)*4 + (v-1)) [A] |
| BP-4b | one BP-1 value | MODE: the other banks × TE / AE combinations | MODE restored in every combination (one measured) |
| BP-5 | one BP-1 value | PLAY queues non-empty, MUSICF / PLYCNT set | the MSX1 BEEP's reset of the queues applied or not |
| BP-6 | one BP-1 value | PPI port C bit 7 (1-bit sound) preset 1 | port C kept |
| BP-9b | the BP-1 set through SUBROM ($015C) | — | equal results with EXTROM |
| BP-10 | the sound-00 code, sampled against the VG-8020's MSX1 BEEP ([BEEP $00C0](../../bios/BEEP.md)) | — | "sound 1 is the MSX1's high beep" [P 2§2.10]: both use $0055 on tone A (the MSX1 page); the level and the length are not compared |
| BP-11 | a multi-tone code, CTRL+STOP pressed during the sound | — | whether CTRL+STOP ends the tones |
| BP-13 | block 2 register 0 (the ID) other than $A | — | whether the call checks the block's ID before using register 10 |

## Related pages

[BEEP $00C0](../../bios/BEEP.md) (the MSX1 call); [WRTCLK](WRTCLK.md), [REDCLK](REDCLK.md);
[the clock concept page](../concepts/clock-and-misc.md); [the sound concept page](../../concepts/sound-calls.md);
[the inventory](../index.md).

## Tests that cover it

none yet
