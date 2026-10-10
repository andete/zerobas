<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no wait=15 -->

# Interrupts and traps — what runs between statements

> **Status (2026-10-10):** the five `ON … GOSUB` traps, Ctrl-STOP, `TIME` and
> background `PLAY` match the VG-8020 in every case measured. Open: keys typed
> during long disk work are lost more often than on the CF-3300 (D-FDCDI,
> TIER 3); traps are not dispatched at the prompt, where the reference has not
> been measured (D-DIR-3); `PLAY(n)` on the statement right after a `PLAY`
> (declined by ruling).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

Fifty times a second (on the VG-8020, a European machine) the video chip
interrupts whatever the computer is doing. In that moment the machine counts
`TIME`, scans the keyboard, feeds the next notes of a `PLAY` to the sound chip
— so music plays on while the program runs — and notices the events a program
has asked to hear about.

A program asks with a **trap**: `ON KEY`, `ON STRIG`, `ON SPRITE`, `ON STOP`
or `ON INTERVAL` followed by `GOSUB <line>`. When the event happens, BASIC
finishes the current statement and calls the handler as if the program had
written `GOSUB` there; its `RETURN` carries on where the program was. Errors
have their own trap, `ON ERROR GOTO` ([errors.md](errors.md)). zerobas
follows the VG-8020's rules for all of this.

## How it works

### The five traps

| trap | arm | switch | the event | handlers |
|---|---|---|---|---|
| `KEY` | `ON KEY GOSUB l1,…,l10` | `KEY(n) ON`/`OFF`/`STOP`, n 1–10 | a function key types (press and each auto-repeat) | one per key, F1–F10 |
| `STRIG` | `ON STRIG GOSUB l0,…,l4` | `STRIG(n) ON`/`OFF`/`STOP`, n 0–4 | the space bar or a fire button goes down | one per trigger |
| `SPRITE` | `ON SPRITE GOSUB l` | `SPRITE ON`/`OFF`/`STOP` | two sprites overlap | one |
| `STOP` | `ON STOP GOSUB l` | `STOP ON`/`OFF`/`STOP` | Ctrl-STOP is pressed | one |
| `INTERVAL` | `ON INTERVAL=n GOSUB l` | `INTERVAL ON`/`OFF`/`STOP` | n frames have passed | one |

The handler lists are positional: in `ON KEY GOSUB 100,,300`, F1 calls 100, F2
nothing, F3 300. `INTERVAL` is not a keyword on MSX1 — it is typed as `INT`,
`ER`, `VAL`, and both machines recognise the combination
([`ON`](../keywords/ON.md) has the details).

### The model they share

- **Arming is not enabling.** `ON … GOSUB` names the handler; nothing fires
  until the matching `… ON`. `ON … GOSUB` with no line number removes the
  handler.
- **`… OFF` forgets.** An event while the trap is off is lost.
- **`… STOP` differs per trap.** For `INTERVAL` it holds back one missed period,
  which fires as soon as `INTERVAL ON` runs. For `KEY`, `STRIG` and `SPRITE`
  it behaves exactly like `OFF`, measured on the VG-8020: a function key is
  typed normally, a press or collision is not remembered.
- **A trap is suspended while its own handler runs**, and switched back on by
  the handler's `RETURN`. A key or button pressed during the handler is
  remembered and calls it once more after the `RETURN`.
- **A handler left without `RETURN`** — by `GOTO`, or an error handled with
  `RESUME <line>` — leaves its trap suspended for good, until the program
  switches it on again. Measured with `ON INTERVAL` on both references; zerobas
  matches, and its other traps share the same code.
- **Traps are cleared** by `RUN`, `NEW` and `CLEAR`.
- **zerobas serves one trap per check**, the next one at the next check.
  Function keys struck in the same frame are served highest number first, as
  on the VG-8020.

### Each trap's own rules

- **`KEY`** fires once when the key goes down and again at every auto-repeat
  while it is held. While `KEY(n)` is on, the key's text is
  *not* typed — even when no handler line is set. F6–F10 are SHIFT with F1–F5.
  An 11th line in `ON KEY GOSUB` is `Syntax error`; `KEY(0) ON` and
  `KEY(11) ON` are `Illegal function call`.
- **`STRIG`** fires once per press; holding the button does not repeat, and a
  button already held when `STRIG(n) ON` runs does not fire.
  `STRIG(5) ON` is `Illegal function call`.
- **`SPRITE`** fires once per frame for as long as two sprites overlap. The
  collision flag is not used up: `VDP(8)` still shows it.
- **`STOP`**: while `STOP ON`, Ctrl-STOP no longer breaks the program — it calls
  the handler instead, and a held Ctrl-STOP calls it again at the keyboard's
  repeat rhythm. After `STOP OFF`, or with the handler removed, Ctrl-STOP breaks
  as usual.
- **`INTERVAL`** fires every n frames (`n=1` every frame); n is converted like
  an address, so 0 is error 5 and 65536 error 6. The count runs from the
  moment the trap fires, so a handler that takes longer than n frames runs
  again as soon as it returns, and the main program never gets another turn —
  on both machines.

### When traps are checked

Traps fire **between statements**, never in the middle of one. zerobas checks
at the start of every program line and wherever the program jumps — `GOTO`,
`GOSUB`, `RETURN`, a `NEXT` that loops — but not between statements joined with
`:` when execution simply flows on; whether the reference checks there has not
been measured. No handler runs while the program waits inside `INPUT`
(measured with `ON KEY` on the VG-8020), nor after the program has ended
(measured with `ON STRIG`).

### Ctrl-STOP and `STOP`

Without a `STOP` trap, Ctrl-STOP ends the program at the next check with
`Break in <line>`, and [`CONT`](../keywords/CONT.md) carries on with the next
statement. The [`STOP`](../keywords/STOP.md) statement does the same on
purpose; it also silences the music and, in a graphics mode, returns to the
text screen first. In zerobas Ctrl-STOP takes the same path (`do_break`).
Typed at the prompt, `STOP` prints a bare `Break`.

### The frame counter and the music

- **`TIME`** is the documented `JIFFY` cell (`&HFC9E`), counted up by the frame
  interrupt; it stops if a program switches that interrupt off in video
  register 1. It also pauses while the disk moves a sector, on both machines;
  until 2026-10-10 it stopped for the whole of every long disk command here
  (D-LOADDI, D-HOOKDI, D-BLDI, [disk](disk.md)). See [`TIME`](../keywords/TIME.md).
- **`PLAY`** puts the notes in queues and returns; the interrupt plays them.
  `PLAY(0)` is −1 while any voice is playing, `PLAY(1)`–`PLAY(3)` ask about one
  voice. The music outlives `END`, `NEW` and a trapped error; an untrapped
  error, `STOP` and `BEEP` silence it. See [`PLAY`](../keywords/PLAY.md).
- **During long disk work** typed keys can be lost, on the CF-3300 too;
  zerobas loses more of them (D-FDCDI, below; [disk.md](disk.md)).

## Example

```
10 ON INTERVAL=50 GOSUB 200
20 INTERVAL ON
30 INTERVAL STOP:T=TIME
40 IF TIME-T<120 THEN 40
50 PRINT "stopped";C
60 INTERVAL ON:T=TIME
65 IF TIME-T<5 THEN 65
70 PRINT "on again";C
80 INTERVAL OFF:T=TIME
90 IF TIME-T<120 THEN 90
100 INTERVAL ON
110 PRINT "after off";C
120 END
200 C=C+1:RETURN
RUN
stopped 0
on again 1
after off 1
```

Stopped for two whole periods, the timer fires nothing but holds one period
back, which fires soon after line 60 switches it on. Switched off for as long,
it forgets; switching it on again fires nothing. The period is long enough
that no new one ends between a switch and the `PRINT`.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_interrupts-and-traps.out`](../../scratchpad/kwdoc_interrupts-and-traps.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

- **How soon a held-back event fires** (D-TRAPLATCHWHEN, found 2026-10-09,
  open, TIER 6). After `INTERVAL STOP` has held a period back, `INTERVAL ON`
  releases it on both machines, but not at the same moment: in this page's
  example without line 65's short wait, the `PRINT` on the very next line
  read 1 on zerobas and still 0 on the VG-8020, which had not yet run the
  handler ([`traplatch_run.out`](../../scratchpad/traplatch_run.out)). zerobas
  raises the event at
  the next statement boundary; when the reference does is not yet pinned.
- **Keys typed during long disk work** are lost more often than on the
  CF-3300 (D-FDCDI, TIER 3): zerobas's disk driver keeps the interrupt off for
  each whole sector operation, seek included. The CF-3300 loses some too, so
  the target is a rate, not zero.
- **Traps at the prompt** (D-DIR-3). After a program with an enabled trap
  stops, zerobas runs no handler for commands typed at the prompt. What the
  reference does there has not been measured.
- **`PLAY(n)` on the very next statement after a `PLAY`** can differ for a
  voice the `PLAY` did not name. Joost ruled on 2026-09-27 to leave it.
- **A sixth line in `ON STRIG GOSUB`** takes the VG-8020 down; zerobas raises
  `Syntax error` instead, deliberately.

## What we found, and how

- **Keys typed in the first seconds after power-on were lost** (fixed
  2026-10-09, D-BOOTSCAN, reported by Joost). The interrupt scans the keyboard
  only when a countdown cell (`SCNCNT`, `&HF3F6`) reaches 0; the VG-8020's
  start-up clears it, C-BIOS leaves it at its power-on `&HFF`, so zerobas
  showed `ZB` about 2.5 seconds before it took the first key. zerobas now sets
  it at start-up, and the first key is taken as soon as the prompt shows, as
  on the reference.
- **`INTERVAL` was first written off as an MSX2 feature** (2026-07-24) because
  it is not in the keyword table; running it showed it works on the VG-8020,
  built from `INT` and `VAL`. It shipped on 2026-07-26 with a 149-case gate.
- **The `STOP` handler was broken by its own key** (fixed 2026-07-25): the
  Ctrl-STOP that fired the handler was still down at the handler's first
  statement, and zerobas treated it as a second press and broke.
- **The reference was misread twice by too short a capture window**: "a press
  during the handler is lost" and "a held Ctrl-STOP aborts the handler" were
  both the handler not having finished yet
  ([spec-traps-t2-strig.md](../spec-traps-t2-strig.md) §10.1,
  [spec-traps-t1-stop-reslice.md](../spec-traps-t1-stop-reslice.md) §12.3).
- **A held Ctrl-STOP fired the handler once** where the reference keeps firing
  (fixed 2026-09-20, D-STOPRELATCH), and then fired it too often for a short
  tap until it followed the keyboard's repeat rhythm (2026-09-25, D-STOPTAP).
- **Leaving a handler without `RETURN` kills its trap — on every machine**
  (2026-08-23, D-TRAPSVC, [spec-basic-trapsvc.md](../spec-basic-trapsvc.md)):
  faithful, not a defect. zerobas alone stopped with `Out of memory` after six
  such handlers; that limit went when traps moved onto the shared control
  stack (D-CTLPOOL).
- **`CLEAR` did not switch traps off** (fixed 2026-08-30, D-CLRTRAP,
  [spec-basic-clrtrap.md](../spec-basic-clrtrap.md)): an armed `ON INTERVAL`
  kept firing, and a killed trap could come back to life.
- **A stopped program kept playing music** (fixed 2026-09-03, D-GICINI).

## How zerobas does it

The interrupt is C-BIOS's: its routine at `&H0038` counts `JIFFY`, scans the
keyboard and calls the documented hook `H.TIMI` (`&HFD9F`). zerobas points the
hook (`play_install` in [basic/playsvc.asm](../../basic/playsvc.asm)) at
`htimi_guard` in [basic/subromcall.asm](../../basic/subromcall.asm). The guard
first samples the sprite collision flag
([basic/sprtrap-body.inc](../../basic/sprtrap-body.inc)); then, if the main ROM
is mapped in, it runs `htimi_service` in [basic/traps.asm](../../basic/traps.asm):
`event_poll` (the Ctrl-STOP hold count, the `INTERVAL` counter, the `STRIG`
buttons through the BIOS `GTTRIG`), then `play_service`, which plays one frame
of music. When a sub-ROM routine holds that part of memory, both are skipped
for the frame; the sprite sample is not. The `KEY` trap needs to see a key
*before* it is typed, which no documented hook allows, so the repacked C-BIOS
calls `zkey_hook` in [basic/keytrap.asm](../../basic/keytrap.asm) from inside
its keyboard scan
([cbios-repack/key-trap-hook.patch](../../cbios-repack/key-trap-hook.patch)).
Ctrl-STOP is read with the BIOS `BREAKX` by the run loop (`rp_exec` and
`rp_break` in [basic/program.asm](../../basic/program.asm)).

The trap table is zerobas's own design, not the reference's layout: `ZTRAP`
in [basic/sysvars.inc](../../basic/sysvars.inc), 18 entries of a state byte
(off, on, stopped, in service; an event-waiting bit; an edge bit for buttons
and Ctrl-STOP) and the handler's line. The interrupt side only sets bits and a `TRAPPEND` flag. The
run loop reads that flag at `rp_trapchk`, and `check_traps` in
[basic/traps.asm](../../basic/traps.asm) pushes an ordinary `GOSUB` frame plus
a small service record, marks the trap in service and jumps to the handler.
`RETURN` recognises its own trap's record (`trap_return_check`) and switches
the trap back on. `trap_init` empties the table at power-on, `RUN`, `NEW` and
`CLEAR` (`clear_vars` in [basic/vars.asm](../../basic/vars.asm)).

## Related pages

- Keywords: [`ON`](../keywords/ON.md) (and `ON INTERVAL`), [`KEY`](../keywords/KEY.md),
  [`STRIG`](../keywords/STRIG.md), [`SPRITE`](../keywords/SPRITE.md),
  [`STOP`](../keywords/STOP.md), [`CONT`](../keywords/CONT.md),
  [`RETURN`](../keywords/RETURN.md), [`TIME`](../keywords/TIME.md),
  [`PLAY`](../keywords/PLAY.md), [`BEEP`](../keywords/BEEP.md).
- Concepts: [errors.md](errors.md) (`ON ERROR GOTO`),
  [screen-editor.md](screen-editor.md), [screen-modes.md](screen-modes.md),
  [disk.md](disk.md), [memory-map.md](memory-map.md).
- Design notes: [spec-basic-interrupt-traps.md](../spec-basic-interrupt-traps.md),
  [T1](../spec-traps-t1-stop-reslice.md), [T2](../spec-traps-t2-strig.md),
  [T3](../spec-traps-t3-key.md), [T4](../spec-traps-t4-sprite.md),
  [T5](../spec-traps-t5-interval.md); where they disagree, this page is current.
- More keywords: [`GOSUB`](../keywords/GOSUB.md).

## Tests that cover it

- `make stop-trap-acceptance`, `strig-trap-acceptance`, `key-trap-acceptance`,
  `sprite-trap-acceptance`, `interval-trap-acceptance` — each trap vs the VG-8020.
- `make trapsvc-acceptance` — handlers left without `RETURN`.
- `make bootkey-acceptance` — the first key after power-on is taken as soon
  as the prompt shows, on zerobas with and without its disk ROM; the VG-8020
  is the control.
- `make time-acceptance`; `make play-acceptance`, `make play-trace-acceptance`
  and `make gicini-acceptance` — `TIME`, `PLAY`, `PLAY(n)`, what stops music.
- `make direct-ctrl-acceptance` — Ctrl-STOP and `STOP` at the prompt.
- `make unit-test` — the trap state machine (`tests/test_traps.py`).
