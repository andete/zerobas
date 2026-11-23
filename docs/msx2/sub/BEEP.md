<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `BEEP` (sub-ROM $017D) — sound the beep set by SET BEEP

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

On the MSX2 the beep is a setting: `SET BEEP` chooses one of four sounds (high, low, two-tone,
three-tone) and one of four volumes, kept in the clock IC's battery-backed memory. The sub-ROM's `BEEP`
plays it; the main ROM's [BEEP ($00C0)](../../bios/BEEP.md) hands over to it. Where the setting lives is
on the [concept page](../concepts/clock-and-misc.md#block-2--the-basic-settings).

## The specification

Tags as on the [concept page](../concepts/clock-and-misc.md#references-subject-citation-tags).

**Interface.**
- Called through EXTROM / SUBROM with IX = $017D [P A1]. No input, no output; all registers may
  change [P A1].
- The main ROM's BEEP ($00C0) always calls the sub-ROM on the MSX2 [P A1 main (mark *3)]; that it
  calls this entry is [A], and the matrix asks only for equal results (BP-9).

**Behaviour.**
- The sound follows `SET BEEP`'s timbre: 1 the MSX1's high beep, 2 a low beep, 3 two tones, 4 three
  tones; and its volume, 1-4 [P 2§2.10]. The setting is kept in block 2, register 10 (tone bits 3-2,
  volume bits 1-0) [P 5§6.7].
- Whether the call reads the clock IC each time or a RAM copy made at reset [A].
- The PSG registers it uses, the pitches, the length of each tone and how the volume maps to the PSG's
  amplitude [A].
- Whether it ends with the MSX1 BEEP's reset of the PSG and the PLAY queues ([BEEP $00C0](../../bios/BEEP.md)) [A].
- The registers, flags, interrupt state and clock-IC MODE register it leaves [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

The measurement matrix. Fixtures as on the
[concept page](../concepts/clock-and-misc.md#shared-measurement-fixtures-for-the-call-pages-matrices).
**Sampler:** PSG R0-R13 and PPI port C are read through the debugger at fixed emulated-cycle steps
(not per frame, so 50 Hz and 60 Hz machines sample alike), from the call until R8-R10 have been 0 for
N = 30 frames' worth of cycles after the return — so a tone started by the call and ended by the timer
interrupt is caught. Every case records the registers, SP, the interrupt state on return, MODE, the
PLAY cells (QUEUEN, MUSICF, PLYCNT) and the cycles from call to return and to silence.

| case | inputs | desynced state | what it separates |
|---|---|---|---|
| BP-1 | block 2 reg 10 = each of the 16 values, written through the ports, then a **reset**, then the call | — | the 16 sounds (the sampled trace, durations); the code → timbre / volume mapping |
| BP-2 | `SET BEEP t, v` for t, v = 1-4, reset, then the call; block 2 reg 10 dumped | — | BASIC's encoding against BP-1's: which 2-bit code each timbre / volume is |
| BP-3 | BP-1's values written through the ports **after** reset, then the call (no reset) | a RAM copy, if one exists, still holds the reset-time value; to find it, diff RAM after resets with two different reg-10 values and preset the differing cell(s) to a third value | read at each call (follows the RTC) vs a copy made at reset (follows the cell) |
| BP-4 | one BP-1 value | MODE: each of the 4 banks × each of the 4 TE / AE combinations | MODE restored, left on block 2, or TE / AE changed |
| BP-5 | one BP-1 value | PLAY queues non-empty, MUSICF / PLYCNT set, PSG R0-R13 preset | the MSX1 BEEP's reset of the PSG and the queues applied or not |
| BP-6 | one BP-1 value | PPI port C bit 7 (1-bit sound) preset 1 | port C kept |
| BP-7 | one BP-1 value | register frame | the registers left (the MSX1 BEEP's are pinned on its page) |
| BP-8 | one BP-1 value | entered with DI, then EI | the interrupt state on return; whether the tone continues after return (the sampler's tail) |
| BP-9 | the BP-1 set through $00C0 and through SUBROM | — | equal results with EXTROM (equality only; no hand-over is claimed) |
| BP-10 | the timbre-1 code, sampled with the same sampler as the MSX1 BEEP's case on [BEEP $00C0](../../bios/BEEP.md) (run here on that page's VG-8020 too) | — | "timbre 1 is the MSX1's high beep" [P 2§2.10]: equal traces or not |
| BP-11 | a multi-tone code (timbre 3 / 4), CTRL+STOP pressed (keyboard matrix through the emulator) halfway through the trace | — | whether CTRL+STOP ends the tones, and the state then left |
| BP-12 | every row above | — | run on all three references (the fixture), so the FS-A1WSX is compared row by row, BP-3 / 4 / 5 / 7 included |

## Related pages
## Related pages

[BEEP $00C0](../../bios/BEEP.md) (the MSX1 call); [WRTCLK](WRTCLK.md), [REDCLK](REDCLK.md);
[the clock concept page](../concepts/clock-and-misc.md); [the sound concept page](../../concepts/sound-calls.md);
[the inventory](../index.md).

## Tests that cover it

none yet
