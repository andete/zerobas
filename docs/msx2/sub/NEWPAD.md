<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `NEWPAD` (sub-ROM $01AD) — read the light pen, mouse or track ball

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX with nothing, and with openMSX's (still) mouse / track ball, in the joystick ports ([xsubpad_body.inc](../../../probes/bios/spec/xsubpad_body.inc); runs [AE_xsubpad](../../../scratchpad/AE_xsubpad_msx2.out), [AE_xsubpadm](../../../scratchpad/AE_xsubpadm_msx2.out), [AE_xsubpadb](../../../scratchpad/AE_xsubpadb_msx2.out), [AE_xsubpadx](../../../scratchpad/AE_xsubpadx_msx2.out), [AE_xsubpads](../../../scratchpad/AE_xsubpads_msx2.out), [AE_xsubpadg](../../../scratchpad/AE_xsubpadg_msx2.out); decoded by [xsubpad_decode.py](../../../scratchpad/xsubpad_decode.py)). No movement and no light pen could be measured (below).
>
> Goldfish pass 1 (test writer) 2026-11-23: 7 findings, 3 measured (two new runs: every number 0-255, and GTPAD 20-23 / out of range, each after a fetch), 3 citations or wordings corrected, 2 moved to open (the X / Y split, NP-13; a plain joystick, NP-14).

## Summary

`NEWPAD` is the MSX2's handler for the pointing devices: a light pen, and a mouse or track ball in
either joystick port. Like BASIC's `PAD()`, it works in pairs: one call fetches a device's data, the
next calls return the parts (X, Y, a switch). Its function numbers are the device numbers 8 and up of the main ROM's
[GTPAD](../../bios/GTPAD.md), which gives the same results for 8-19 on all three references. The devices' ports are on
the [concept page](../concepts/clock-and-misc.md#other-devices-the-calls-in-this-region-reach).

Measured: the three references agree on every call. The fetch (12 / 16) returns $FF whether or not anything is
connected. The reads return the values of the LAST fetch, from either port; only functions 8, 11, 12 and 16 are
special, and every other number 0-255 -- 9, 10, 20-23 and the out-of-range ones -- is a read chosen by its two low
bits. C-BIOS's MSX2 builds select by the low five bits instead (fetching on 4, 20 and 24 and their aliases), and
return with interrupts off after a fetch.

## The specification

Tags as on the [concept page](../concepts/clock-and-misc.md#references-subject-citation-tags).
**[M PAD n]**, **[M PADM n]**, **[M PADB n]**, **[M PADX n]**: call n of the runs of
[xsubpad.asm](../../../probes/bios/spec/xsubpad.asm) (nothing plugged), [xsubpadm.asm](../../../probes/bios/spec/xsubpadm.asm)
(mouse in port 1, track ball in port 2), [xsubpadb.asm](../../../probes/bios/spec/xsubpadb.asm) (port 1 empty, mouse in
port 2) and [xsubpadx.asm](../../../probes/bios/spec/xsubpadx.asm) (out-of-range numbers, nothing plugged), 2026-11-23,
`--fresh`. **[M PADS n]**, **[M PADG n]** (added by the goldfish pass, the same day): call n of
[xsubpads.asm](../../../probes/bios/spec/xsubpads.asm) -- call 0 a fetch of the empty port 1 ($01 / $01), then call
f + 1 = function f for every f = 0-255 -- and of [xsubpadg.asm](../../../probes/bios/spec/xsubpadg.asm) -- GTPAD 12,
then GTPAD 20, 21, 22, 23, 24, 31, $80, $FF -- nothing plugged in either. `xsubpad_decode.py --classes` groups their
calls by result. Each call: interrupts off, PSG R15 := $8F, BC $1357, DE $2468, HL $369C, A = the function; the calls
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
  without fetching again: 17, 18 called twice, with only reads (19-23, 13, 14) between, give the same values
  [M PAD 9-10, 18-19].
- Before any fetch since boot, the reads return 0 [M PAD 1-2], [M PADX 0-11].
- **Which read a function is:** for every function number 0-255 except 8, 11, 12 and 16, its two low bits pick
  one of three results: low bits 00 / 01 give 13's result, 10 gives 14's, 11 gives 0 -- after a fetch of $01 / $01,
  the 125 numbers with low bits 00 / 01 return $01 with F $BB, the 64 with 10 return $01 with F $42, and the 63
  with 11 return 0 with F $44, all with the read's registers; no other number fetches or acts as 8 or 11
  [M PADS 1-256], the same on all three references. So 9 / 10 (the light pen's X / Y) return the last fetch's X / Y
  when no pen is present -- an empty port's $01 [M PADB 11-12], a mouse's 0 [M PADB 16]; 20-22 read as 13, 13, 14
  and 23 returns 0 [M PAD 12-15], [M PADB 13, 17-18]: there is no second light pen. Before any fetch the same
  split shows in the flags alone (every read 0) [M PADX 0-11]. That 13's result is X and 14's is Y is [P A1]
  (below).
- **Caveat on X against Y [A]:** every fetch measured gave X = Y, so the values cannot tell an X read from a Y read.
  Two rules fit every case: (A) low bits 00 / 01 read the stored X and 10 the stored Y; (B) both read the same cell
  and differ only in F. The split above is by result (flags and registers) [M]; that it is X against Y is [A]
  until a fetch with X ≠ Y (needs motion, NP-13). The "0" class (low bits 11) is separated by value: it returns 0
  where the X / Y reads return $01, for 15 / 19 / 23 [M PAD 7, 11, 15] and for every other number with low bits 11
  (3, 7, 31, $FF, ...) [M PADS 4, 8, 32, 256].
- **8** after a fetch returns 0 and does not clear the stored values: the next read (9) still returns $01
  [M PADS 9-10], and GTPAD 9 after GTPAD 8 likewise [M PAD 26-27].
- **15 / 19** return 0 [M PAD 7, 11], [M PADM 7, 11] (no button state could be applied: open).
- **8** (light pen fetch) returns 0 with no pen; **11** (its switch) returns 0 [M PAD 0, 3]. openMSX models no light
  pen, so 8 returning $FF and 9-11 after it are [P] only.
- GTPAD ($00DB) with A = 8-19 gives the same A, F and registers as NEWPAD with the same history
  [M PAD 26-37], [M PADM 26-37]; with A = 20-23, 24, 31, $80 and $FF too, after a GTPAD 12: 20, 21, 24, $80 read
  as 13, 22 as 14, 23, 31, $FF return 0 [M PADG 0-8]. That it calls this entry is [A].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject), all three rows:
- **It selects by the low five bits, not two:** numbers whose low five bits are 4 or 12 fetch port 1 and 16,
  20, 24 or 28 fetch port 2 (A $FF) -- so 4, 20, 24 and e.g. 36, 44, 48, $84 fetch where the references
  read X; low five bits 0 or 8 return 0 (as 8) where the references read X (except 8 itself) [M PADS 1-256],
  [M PAD 12], [M PADB 13-14], [M PADX 4, 8]. The other numbers read by their two low bits as the references do
  (00 / 01 → 13's value, 10 → 14's, 11 → 0) [M PADS]. Its GTPAD 20-23 / 24 / 31 / $80 / $FF act as its NEWPAD
  [M PADG].
- **After a fetch (12 / 16 and the above) interrupts are left OFF**; the references leave them on [M PAD 4, 8],
  [M PADS].
- Registers and flags differ throughout (e.g. the reads return F $42, BC = function << 8 | $57, DE kept); A
  agrees for 8-19 [M PAD], [M PADM], [M PADB].

## Open (not measured)

openMSX's mouse and track ball take their motion and buttons from the host's mouse only: no console command moves
them, so with the current harness every device is still. Measured: NP-1 (8-23, 0-7, 24, 31, $80, $FF -- one boot
per run, not per value), NP-1b (every number 0-255 after a fetch, one boot), NP-2, NP-4, NP-6 (no crosstalk tested only as "reads return the last fetch"), NP-8
(no pen), NP-9, NP-11 (interrupts, registers). Still open:

| case | inputs | desynced state | what it separates |
|---|---|---|---|
| NP-3 | 12, 13, 14 with scripted motion (+5, -3); +100 twice without a fetch; +200 / -200; across 0 / 255 | — | offset vs position; sign; clamp vs wrap -- needs a way to move openMSX's mouse from a script |
| NP-5 | 12 then 13 with a gap of 0 - 100 000 cycles | mouse moving | what "a long gap" does (needs motion) |
| NP-7 | NP-3 with a track ball | — | the track ball's encoding (needs motion) |
| NP-8b | 8-11 with a light pen | — | openMSX has no light pen |
| NP-10 | A = 15, 19 | a mouse button held | "always 0" vs a button state (needs the host button) |
| NP-12 | each function entered with EI | — | the interrupt state when entered with EI (measured with DI only) |
| NP-13 | 12 with scripted motion giving X ≠ Y, then 13, 14, 9, 10, 0, 1, 2, 20-22 | — | (A) low bits 00 / 01 read X and 10 read Y, against (B) one cell read by both, only F differing -- every fetch so far gave X = Y; needs motion as NP-3 |
| NP-14 | 12 / 16 then 13 / 14 with a plain joystick plugged, a direction / trigger held | — | what a fetch reads from a non-mouse device (a still joystick's pins read as an empty port's, so it needs a held input) |

## Related pages

[GTPAD $00DB](../../bios/GTPAD.md) (the main-ROM entry); [the concept page](../concepts/clock-and-misc.md);
[the inventory](../index.md).

## Tests that cover it

none yet
