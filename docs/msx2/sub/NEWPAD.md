<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `NEWPAD` (sub-ROM $01AD) — read the light pen, mouse or track ball

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`NEWPAD` is the MSX2's handler for the pointing devices: a light pen, and a mouse or track ball in
either joystick port. Like BASIC's `PAD()`, it works in pairs: one call fetches a device's data, the
next calls return the parts (X, Y, a switch). Its function numbers are the device numbers 8 and up of the main ROM's
[GTPAD](../../bios/GTPAD.md); whether GTPAD hands them over is not yet measured. The devices' ports are on the
[concept page](../concepts/clock-and-misc.md#other-devices-the-calls-in-this-region-reach).

## The specification

Tags as on the [concept page](../concepts/clock-and-misc.md#references-subject-citation-tags).

**Interface.**
- Called through EXTROM / SUBROM with IX = $01AD [P A1]. In: A = the function number; out: A; all
  registers may change [P A1].

**Behaviour.**
- **8:** fetch the light pen; $FF when the data is valid [P A1]. **9 / 10:** its X / Y [P A1].
  **11:** its switch, $FF when pressed [P A1]. 9-11 mean something only after 8 returned $FF
  [P 5§5.4 note 1].
- **12 / 16:** fetch the mouse or track ball in port 1 / port 2 [P A1]. The handbook's two descriptions
  differ: $FF "when connected" [P A1] against "always $FF" [P 5§5.4 Table 5.5].
- **13, 14 / 17, 18:** X / Y for port 1 / port 2 [P A1]: "offsets" [P A1] against "coordinates 0 to
  255" [P 5§5.4]. They are valid only right after 12 / 16; a long gap makes them unreliable
  [P 5§5.4 note 3]. **15 / 19:** always 0 [P A1].
- A mouse and a track ball are told apart without the caller's help [P 5§5.4 note 2]; their buttons are
  read with GTTRIG, not here [P 5§5.4 note 4].
- 20-23 (a second light pen, as 8-11) are listed only by [P MAP]: [A] until measured.
- GTPAD hands numbers 8 and up to this call [P MAP]; the handbook marks GTPAD "same as MSX1"
  [P A1 main], so the hand-over is [A]; the matrix asks only that the two give equal results (NP-9).
- Whether X / Y are signed offsets since the last fetch, and their sign convention [A]. What A < 8 or
  A > 19 (or 23) returns [A]. The PSG R15 (port select) left [A]. Flags, registers kept,
  interrupt state [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

The measurement matrix. Fixtures as on the
[concept page](../concepts/clock-and-misc.md#shared-measurement-fixtures-for-the-call-pages-matrices).
openMSX's mouse and track-ball plug-ins drive the devices; motion is scripted so the expected values
are known. **openMSX is not known to model a light pen** [A]: unless one is found, the light-pen rules
(8-11, 20-23) are measured only as the no-pen behaviour (NP-8), and the rest of them stay [P] / [A].
Every case records A, F, the register frame, PSG R15, the interrupt state and the emulated cycles.

| case | inputs | desynced state | what it separates |
|---|---|---|---|
| NP-1 | A = 0-255, nothing in either port; one boot (or savestate restore) per A value | PSG R15 preset to a non-default value | the "no device" answers and the A < 8 / > 19 range; "hung" (no return within 1 s of emulated time) is a recorded outcome |
| NP-2 | A = 12 then 16 | mouse in port 1 only; then a joystick in port 2 | "$FF when connected" vs "always $FF" |
| NP-3 | 12, 13, 14 with scripted motion (+5, -3); none; +100 twice without a fetch between; +200 / -200 in one step; a position walked across 0 and 255 | — | offset since the last fetch vs absolute position 0-255; sign; clamp vs wrap beyond ±128 and across 0 / 255; R15 after |
| NP-4 | 13 / 14 without a 12 before; 12, 14, 13; 12, 13, 13 | — | which call fetches, which reads; a second read repeats or re-fetches |
| NP-5 | 12 then 13 with a gap of 0, 1 000, 10 000, 100 000 cycles | mouse moving | what "a long gap" does |
| NP-6 | 16, 17, 18 | mouse in port 2, port 1 empty; then both ports | port selection, no crosstalk; R15 after |
| NP-7 | NP-3 with a track ball | — | the track ball's encoding vs the mouse's |
| NP-8 | 8-11, 20-23 | no light pen (or one, if openMSX offers it) | the no-pen answers; whether 20-23 exist as functions at all |
| NP-9 | the NP-3 / NP-6 sequences through GTPAD ($00DB) and through SUBROM | — | equal results with EXTROM (equality only; no hand-over is claimed) |
| NP-10 | A = 15, 19 | mouse in the port, each button held, then released | "always 0" vs a button state |
| NP-11 | any case | register frame; DI / EI on entry | registers, flags and the interrupt state left; the time each function takes |

## Related pages
## Related pages

[GTPAD $00DB](../../bios/GTPAD.md) (the main-ROM entry); [the concept page](../concepts/clock-and-misc.md);
[the inventory](../index.md).

## Tests that cover it

none yet
