<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `NEWPAD` (sub-ROM $01AD) — read the light pen, mouse or track ball

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX with nothing, and with openMSX's (still) mouse / track ball, in the joystick ports ([xsubpad_body.inc](../../../probes/bios/spec/xsubpad_body.inc); runs [AE_xsubpad](../../../scratchpad/AE_xsubpad_msx2.out), [AE_xsubpadm](../../../scratchpad/AE_xsubpadm_msx2.out), [AE_xsubpadb](../../../scratchpad/AE_xsubpadb_msx2.out), [AE_xsubpadx](../../../scratchpad/AE_xsubpadx_msx2.out); decoded by [xsubpad_decode.py](../../../scratchpad/xsubpad_decode.py)). No movement and no light pen could be measured (below).

## Summary

`NEWPAD` is the MSX2's handler for the pointing devices: a light pen, and a mouse or track ball in
either joystick port. Like BASIC's `PAD()`, it works in pairs: one call fetches a device's data, the
next calls return the parts (X, Y, a switch). Its function numbers are the device numbers 8 and up of the main ROM's
[GTPAD](../../bios/GTPAD.md), which gives the same results for 8-19 on all three references. The devices' ports are on
the [concept page](../concepts/clock-and-misc.md#other-devices-the-calls-in-this-region-reach).

Measured: the three references agree on every call. The fetch (12 / 16) returns $FF whether or not anything is
connected. The reads return the values of the LAST fetch, from either port; only functions 8, 11, 12 and 16 are
special, and every other number -- 9, 10, 20-23 and the out-of-range 0-7, 24, 31, $80, $FF -- is a read chosen by
its two low bits. C-BIOS's MSX2 builds fetch on 4, 20 and 24 as well, and return with interrupts off after a fetch.

## The specification

Tags as on the [concept page](../concepts/clock-and-misc.md#references-subject-citation-tags).
**[M PAD n]**, **[M PADM n]**, **[M PADB n]**, **[M PADX n]**: call n of the runs of
[xsubpad.asm](../../../probes/bios/spec/xsubpad.asm) (nothing plugged), [xsubpadm.asm](../../../probes/bios/spec/xsubpadm.asm)
(mouse in port 1, track ball in port 2), [xsubpadb.asm](../../../probes/bios/spec/xsubpadb.asm) (port 1 empty, mouse in
port 2) and [xsubpadx.asm](../../../probes/bios/spec/xsubpadx.asm) (out-of-range numbers, nothing plugged), 2026-11-23,
`--fresh`. Each call: interrupts off, PSG R15 := $8F, BC $1357, DE $2468, HL $369C, A = the function; the calls
follow each other with no wait. The devices are openMSX's `mouse` / `trackball`, plugged before boot (`@plug`); no
host input reaches a run, so they never move. "Empty" means nothing plugged: every input pin reads 1.

**Interface.**
- Called through EXTROM / SUBROM with IX = $01AD [P A1]. In: A = the function number; out: A; all
  registers may change [P A1].
- Interrupts are **on** on return from every function, entered with DI, on all three references [M PAD 0-25].
- Registers [M PAD], [M PADM]: a read (X / Y) returns BC $40FF, DE $240F, HL $20DF; a fetch returns BC = DE = HL =
  $0F1C (port empty), $0054 (mouse), $0818 (track ball); function 8 keeps BC / DE and returns HL $FAFF; function
  11 keeps BC, DE and HL. F: $BB after an X read (functions with low bits 00 / 01), $42 after a Y read (10), $44
  after the "always 0" read (11), $13 after a fetch from an empty port, $42 from a mouse, $54 from a track ball, $74
  after 8, $54 after 11 [M PAD], [M PADM], [M PADB], [M PADX].
- PSG R15 on return [A]: it read $CF after every fetch of port 2 and mostly $8F otherwise, but interrupts are on
  on return and the timer interrupt writes R15 ($8F / $CF) every frame, so the call's own value cannot be told from
  the interrupt's [M PAD].

**Behaviour.**
- **12 / 16** fetch port 1 / port 2 and return **$FF**, with the port empty, a mouse or a track ball alike
  [M PAD 4, 8], [M PADM 4, 8], [M PADB 0, 3] -- the handbook's "always $FF" [P 5§5.4 Table 5.5], not "$FF when
  connected" [P A1].
- A fetch's X and Y: **$01 / $01 from an empty port**, 0 / 0 from a still mouse or track ball
  [M PAD 5-6], [M PADM 5-6, 9-10], [M PADB 1-2, 4-5]. Whether they are offsets since the previous fetch or
  positions, and their sign [A] (no movement could be scripted).
- **The reads return the last fetch's values, whatever port they name:** after a fetch of port 2 (a mouse, 0),
  13 / 14 return 0; after a fetch of port 1 (empty, $01), 17 / 18 return $01 [M PADB 3-10]. A read repeats
  without fetching again: 13, 14 called twice give the same values [M PAD 5-6, 16-17].
- Before any fetch since boot, the reads return 0 [M PAD 1-2], [M PADX 0-11].
- **Which read a function is:** for every function number except 8, 11, 12 and 16, its two low bits: 00 / 01 →
  X, 10 → Y, 11 → 0 [M PAD 1-2, 5-7, 9-15], [M PADB 11-14, 16-18], [M PADX 0-11]. So 9 / 10 (the light pen's X / Y)
  return the last mouse / track-ball fetch's X / Y when no pen is present [M PADB 11-12, 16]; 20-22 return X, X,
  Y and 23 returns 0 [M PAD 12-15], [M PADB 13, 17-18]: there is no second light pen. Out of range: 0, 1, 4, 5,
  24, $80 → X; 2, 6 → Y; 3, 7, 31, $FF → 0; none fetches [M PADX 0-11], [M PADB 14].
- **Caveat on X against Y:** every fetch measured gave X = Y, so the values cannot tell an X read from a Y read.
  The X / Y split above rests on the flags: each such function returns 13's registers and F ($BB) or 14's ($42).
  The "0" class (low bits 11) is separated by value: it returns 0 where the X / Y reads return $01 [M PAD 7, 11,
  15]. A fetch with X ≠ Y (needs motion) would pin it [A].
- **15 / 19** return 0 [M PAD 7, 11], [M PADM 7, 11] (no button state could be applied: open).
- **8** (light pen fetch) returns 0 with no pen; **11** (its switch) returns 0 [M PAD 0, 3]. openMSX models no light
  pen, so 8 returning $FF and 9-11 after it are [P] only.
- GTPAD ($00DB) with A = 8-19 gives the same A, F and registers as NEWPAD with the same history
  [M PAD 26-37], [M PADM 26-37]; that it calls this entry is [A].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject), all three rows:
- **20 fetches port 2** (A $FF) instead of reading X [M PAD 12], [M PADB 13]; out of range, **4 fetches port 1
  and 24 fetches port 2** instead of reading X [M PADX 4, 8]; **0 returns 0** instead of the last X
  [M PADB 14]; 5 / 6 return the X / Y as the references do. Its reads otherwise select by the low bits as the
  references do.
- **After a fetch (12 / 16 and the above) interrupts are left OFF**; the references leave them on [M PAD 4, 8].
- Registers and flags differ throughout (e.g. the reads return F $42, BC = function << 8 | $57, DE kept); A
  agrees for 8-19 [M PAD], [M PADM], [M PADB].

## Open (not measured)

openMSX's mouse and track ball take their motion and buttons from the host's mouse only: no console command moves
them, so with the current harness every device is still. Measured: NP-1 (8-23, 0-7, 24, 31, $80, $FF -- one boot
per run, not per value), NP-2, NP-4, NP-6 (no crosstalk tested only as "reads return the last fetch"), NP-8
(no pen), NP-9, NP-11 (interrupts, registers). Still open:

| case | inputs | desynced state | what it separates |
|---|---|---|---|
| NP-3 | 12, 13, 14 with scripted motion (+5, -3); +100 twice without a fetch; +200 / -200; across 0 / 255 | — | offset vs position; sign; clamp vs wrap -- needs a way to move openMSX's mouse from a script |
| NP-5 | 12 then 13 with a gap of 0 - 100 000 cycles | mouse moving | what "a long gap" does (needs motion) |
| NP-7 | NP-3 with a track ball | — | the track ball's encoding (needs motion) |
| NP-8b | 8-11 with a light pen | — | openMSX has no light pen |
| NP-10 | A = 15, 19 | a mouse button held | "always 0" vs a button state (needs the host button) |
| NP-1b | A = 32-127, 129-254 | — | the low-bits rule over the rest of the range (12 of 233 values measured) |
| NP-12 | each function entered with EI | — | the interrupt state when entered with EI (measured with DI only) |

## Related pages

[GTPAD $00DB](../../bios/GTPAD.md) (the main-ROM entry); [the concept page](../concepts/clock-and-misc.md);
[the inventory](../index.md).

## Tests that cover it

none yet
