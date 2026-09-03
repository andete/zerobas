# D-GICINI — the abort seam does not stop the music

**Status:** measured, defect confirmed on six rows; fix pending.
**Probes:** `scratchpad/gicini_probe.py` (BASIC-visible), `scratchpad/gicini_psg.py`
(PSG register trace).
**Found by:** `scratchpad/deferral_sweep.py` — the instrument built by D-DEFERSWEEP
for exactly this class.

## 0. How this was found, and why that matters

`basic/sound.asm` deferred a GICINI-equivalent init to "Slice 2", and justified
the deferral in a parenthesis:

> "(there are no PLAY queues / MUSICF to zero yet, and C-BIOS's own boot GICINI
> already leaves the PSG quiet — amplitudes 0 — so a fresh SOUND works with no
> init of ours)"

The first clause stopped being true when `basic/play.asm` and `basic/playsvc.asm`
shipped. Nothing in this tree watched that trigger; the deferral sat there
reading as current. This is the third time the same class has produced a real
defect (`printusing` "arrive with Phase-3 floats" → D-PUSING; `play.asm` "NO live
drain" → D-PLAYFN), and the first time the sweep found one **on purpose** rather
than by accident.

⚠️ **The conclusion the parenthesis supported was still wrong for a second
reason.** Even granting "no queues yet", the deferral named an *init*; what is
actually missing is a *teardown*. Reading the file would never have said so.

## 1. What diverges

`PEEK(&HFB3F)` is MUSICF, a published MSX work-area address that zerobas places
deliberately (`basic/sysvars.inc` names "a program that PEEKs MUSICF" as the
faithfulness reason), so the same expression names the same thing on all three
machines.

Six of 34 rows diverge; both references agree with each other on every one.

| row | stimulus | vg8020 | cf3300 | zb |
|---|---|---|---|---|
| `e.untrap` | program raises `ERROR 5`, untrapped | 0 | 0 | **1** |
| `e.errnat` | program raises `Undefined line number` | 0 | 0 | **1** |
| `e.errdir` | the same error typed in **direct mode** | 0 | 0 | **1** |
| `e.stop`   | program hits `STOP` (`Break in 20`) | 0 | 0 | **1** |
| `e.cont`   | …and `CONT` afterwards does not bring it back | 0 | 0 | **1** |
| `m.beep`   | `BEEP` during an active drain | 0 | 0 | **1** |

`e.cont` is a consequence of `e.stop`, not a separate site: the break **destroys**
the queue rather than pausing it, and resuming the program does not resurrect it.

## 2. What does NOT diverge — the rows that make the rule precise

* `e.end` — a **clean `END`** leaves MUSICF set on **all three**. So the trigger
  is not "returned to the `Ok` prompt"; it is **abort**. Music surviving the end
  of a program is correct MSX behaviour and zerobas already has it.
* `e.new` — **`NEW` does not clear it either**, on any of the three. Round 4 said
  the opposite; see §4.
* `e.runagain` — a second `RUN` does not clear it (the new `PLAY` refills it).
* `m.err` — a **trapped** error (`ON ERROR` + `RESUME`) leaves it set on all
  three. So it is not error-*raising* either.
* `m.sound2`, `m.sound7` — `SOUND` writes, including to the mixer R7, do not
  touch the queue anywhere. So `BEEP` is not clearing it merely by being a PSG
  writer; `BEEP` does something `SOUND` does not.
* `m.cls`, `m.keyoff`, `m.width`, `m.screen`, `m.clear` — all leave it set on all
  three, which bounds the fix away from the display and `CLEAR` paths.

## 3. Whether the fix must SILENCE, or only zero MUSICF

If the reference merely zeroed MUSICF the servicer would stop writing and the
last amplitude would **sustain** — a note that never ends. That is physically
absurd, which is exactly why it was measured rather than argued: an obvious
inference is the shape of the justification parenthesis that produced this slice.

`scratchpad/gicini_psg.py` samples the 14 PSG registers every VBLANK
(`probes/lib/psgtrace.py`, the Slice-3 drain instrument). Two stimuli per side:
a control that never aborts, and the `e.stop` program.

| side | control (no abort) | after `STOP` |
|---|---|---|
| vg8020 | R8 = 136, sustained | **0** |
| cf3300 | R8 = 8, sustained | **0** |
| zb     | R8 = 8, sustained | **8, sustained** |

Both references **silence the amplitudes**. zerobas holds the note at volume 8
indefinitely. So the fix is a real GICINI-equivalent (silence + clear), not a
one-byte `ld (MUSICF),a`.

🟢 The control column is load-bearing and was added because it had to be: three
earlier rounds of this trace read amplitude 0 on **every** side including the
control, which is what "the abort silenced it" and "the machine never booted"
look like alike. Two separate apparatus faults (typing before boot; a raw `0x0D`
where Tcl needed the two-character `\r`) were caught only by the control.

## 4. An apparatus fault that would have produced four false findings

Round 4 of `gicini_probe.py` reported `e.errdir` (direct-mode error), `e.new`
(`NEW`), `e.cont` and `e.nop` as **agreeing** — 0 on all three — and the obvious
reading was "zerobas already clears the queue on those paths".

That reading was wrong. `omsx_repl` types one line per **8 s slot**, and the
original `L1CDEFGAB` runs ~16 s: any row with two typed lines after the `PLAY`
outlives its own queue. The rows were not measuring `NEW` at all.

⚠️ **THIS IS A PROPERTY OF `DIRECT` ROWS ONLY, AND THE DISTINCTION MATTERS.** A
`CASES` row is a single stored program — its setup lines and its `PRINT` run
back-to-back inside one `RUN`, microseconds apart — so no `m.*` row here was ever
exposed to it, and neither is the pre-existing `scratchpad/musicf_probe.py`,
whose `r.drop` is program-form. Only the `e.*` rows, which exist precisely to
reach the `Ok` prompt, pay the typing latency.

This was caught by `e.nop`/`e.nop2` — a **harmless** direct statement in the same
position as the subject's event, which must read 1 and did not. The measurement
was redone at `T32` (the slowest MSX tempo: a whole note is 7.5 s, so the same
eight notes run ~60 s and outlive every fixture). Note count was deliberately
left alone — a longer MML string fills the 128-byte ring and makes `PLAY` block,
which is a different fixture again.

⚠️ Without those two control rows this document would have contained four
"zerobas already matches" claims, **every one of them false** — and it would have
under-reported the defect by a third: at `T32`, `e.errdir` and `e.cont` are
**divergences**, and `NEW`'s real answer is the opposite of the one round 4 gave.
A row that agrees can agree for the wrong reason, and the only thing that
separates the two is a control written to fail when it does.

## 5. Provenance

MUSICF's address and meaning are published MSX work-area documentation; the
divergence and every value in the tables above are black-box readings from the
Philips VG-8020 and National CF-3300 through BASIC and through openMSX's `PSG
regs` debuggable. No reference ROM was disassembled or byte-copied.

## 6. The fix

`psg_silence` (`basic/sound.asm`, low region) — 21 B:

```
psg_silence:    di
                xor     a
                ld      (MUSICF),a          ; play_service's fast-out: no more PSG writes
                ld      b,8                 ; R8/R9/R10 = the three tone amplitudes
psgs_lp:        ld      a,b
                out     (PSG_ADDR),a
                xor     a
                out     (PSG_DATW),a
                inc     b
                ld      a,b
                cp      11
                jr      c,psgs_lp
                ei
                ret
```

Three call sites, 3 B each:

| site | file | region | rows it answers |
|---|---|---|---|
| `fre_abort_low` | `basic/arrays.asm` | low | `e.untrap`, `e.errnat`, `e.errdir` |
| `do_break` | `basic/program.asm` | page 1 | `e.stop`, `e.cont` |
| `ex_beep` | `basic/sound.asm` | low | `m.beep` |

**Why the funnel and not three mode-specific sites.** `fre_abort_low` is the
single untrapped-abort funnel (its own header says so, and only two instructions
in the tree reach it: `ra_abort` and the ERR 21 `No RESUME` site). The **trapped**
branch left at `raise_error_hl` several instructions earlier, so the funnel is
already on the right side of the fork that `m.err` measures. ⚠️ A shared tail is a
label and not a decision — both of its entries were checked to be aborts, rather
than assuming the name meant what it says.

**Why `MUSICF` first, and why `di`.** Clearing MUSICF makes `play_service`'s own
fast-out skip the PSG entirely, so the amplitude writes cannot be fought. The
`di` closes the one remaining window: an ISR that fired just *before* the MUSICF
store is already past its fast-out and would write one more frame of amplitude
after ours. One leaked frame is invisible to a ±1-frame PSG trace, so it is
closed by construction rather than measured away.

**Cost.** Page-0 low region 106 → **79 B** free; page 1 272 → **269 B**. Read from
`make basic-reloc`, before and after.

## 7. Result

`scratchpad/gicini_probe.py`: **0 DIFF / 36 rows**, three machines.
`scratchpad/gicini_psg.py`: zb `stop` now reads amplitude **0 sustained**,
matching both references, while its control still reads 8 sustained.

🎯 **`e.replay` / `e.replayfn` are the rows that say the fix did not merely paper
over.** Silencing the PSG says nothing about whether a *later* `PLAY` can still
use the queue. Both read as playing (`1`, `-1`) on all three after an abort.

⚠️ **And they were vacuous when first written**, for the third time in this
slice: `PLAY"T32L1C"` is one 7.5 s note, which drains inside the fixture's own
8 s typing slot. Written up unchecked, they would have said "the replay behaves
identically" while measuring nothing. The same artefact, caught the second and
third time only because §4's control row had already made the failure mode
nameable.

## 8. Not covered

* **Voice A only is ever exercised.** Every stimulus here plays one voice, so
  `psg_silence`'s R9/R10 writes are argued from the register map, not measured.
  `m.two`/`m.three` show MUSICF's bitmask is right for 2 and 3 voices, but no row
  aborts a multi-voice drain.
* **The envelope registers (R11–R13) are left alone**, matching `BEEP`'s existing
  contract. Whether the reference's GICINI-equivalent resets them is unmeasured:
  the VG-8020 control trace reads R8 = 136 (envelope bit set) where the CF-3300
  and zerobas read 8, so the two references already disagree about envelope use
  during a drain — a NO-ORACLE row, and not this slice's subject.

## 9. Knives — predictions, recorded before the run

`scratchpad/gicini_knives.py`. Four arms, each a source edit + rebuild +
re-measure, every one hashing the ROM so an arm that did not build is reported
INERT rather than believed green.

| arm | plant | predicted to move |
|---|---|---|
| K-GI1 | drop the call from `fre_abort_low` | `e.untrap`, `e.errnat`, `e.errdir` |
| K-GI2 | drop the call from `do_break` | `e.stop`, `e.cont` |
| K-GI3 | drop the call from `ex_beep` | `m.beep` |
| K-GI4 | keep `ld (MUSICF),a`, delete the amplitude loop | **nothing** |

🎯 **K-GI4 is the point of the set, and its prediction is that it comes back
empty.** Every row in `gicini_probe.py` reads MUSICF, so an arm that still clears
MUSICF is invisible to all 36 of them — while the machine holds the note forever,
which is the actual user-visible symptom. If K-GI4 moves nothing, that is not the
row set passing; it is the row set admitting the PSG trace is the only cover for
half the fix.

### 9.1 Result — 4/4, and all four predictions correct

```
base ROM 996e345401a0     base DIFF rows: []
K-GI1: rom=7b00b645d26d  moved=[e.errdir, e.errnat, e.untrap]  PASS
K-GI2: rom=08d3de3e9175  moved=[e.cont, e.stop]                PASS
K-GI3: rom=d05eab826bf5  moved=[m.beep]                        PASS
K-GI4: rom=52cfe774be54  moved=<none>                          PASS
restored ROM 996e345401a0 (base was 996e345401a0) OK
```

Every arm's ROM hash differs from the base, so no arm was inert; the restore hash
is byte-identical to the base.

🔴 **K-GI4 CAME BACK EMPTY AS PREDICTED, AND THAT IS A FINDING ABOUT THE GATE,
NOT A PASS.** With the amplitude loop deleted the machine holds the note at
volume 8 forever — the exact user-visible symptom this whole slice is about — and
**all 36 rows stay green**, because all 36 read MUSICF. Half of `psg_silence` is
covered by nothing a row can see. §10 closes that.

## 10. The gate

`make gicini-acceptance` (`probes/basic/basic_probe_gicini.py`) scores **both**
halves:

* the 36 BASIC-visible rows, three machines, expected 0 DIFF;
* the PSG amplitude trace, with the control that K-GI4 proved is load-bearing —
  `zb/stop` must read peak amplitude **0** *and* `zb/ctl` must read **non-zero**.
  Without the control, a trace that never booted scores green.


## 11. An apparatus near-miss worth recording

This slice's row probe was first written to `scratchpad/musicf_probe.py` with a
`cat >` heredoc. **That file already existed** — commit `3764e23`, a different
investigation ("does a `PLAY` naming fewer voices stop a still-playing voice?")
— and was destroyed without being read. It was restored byte-identical from git
(`2b22f7b4…`), and this slice's probe now lives in `scratchpad/gicini_probe.py`.

Two things made it survivable and one made it visible: the file was **tracked**,
so `git status` showed `M` where a new file shows `A`, and the staged copy of the
overwriting version was still recoverable as a dangling blob. Nothing in the
tooling objected; the only signal was one character in a status listing.

The slice was also briefly named **D-MUSICF**, which is the name `3764e23`
already carries. Both the file name and the slice name were taken, and neither
collision was checked before writing.
