# Spec — the `BEEP` statement (audio arc, close-out slice)

Status: **LANDED 2026-07-21** (signed off: direct-PSG, EI delay). Closes the audio arc.
Owner: zerobas-BASIC. Repack-build only (page-1 resident, like `SOUND`/`PLAY`).
Sibling specs: [`spec-basic-audio-play.md`](spec-basic-audio-play.md) (SOUND, Slice 1),
[`spec-basic-audio-play-slice2a.md`](spec-basic-audio-play-slice2a.md) (PLAY parser),
[`audio-slice3-characterization.md`](audio-slice3-characterization.md) (live servicer).

This closes the "Sound" line of Phase 3 ([`TODO.md`](../TODO.md) §Phase-3): `SOUND`
and `PLAY` landed 2026-07-21; `BEEP` is the last unbuilt audio verb.

---

## 1. Surface

```
BEEP
```

No arguments. Emits one short fixed tone (a "beep") on PSG channel A, synchronously,
then returns. It is the simplest audio verb — a discrete, fire-once event with no
queue, no ISR involvement, no sub-ROM tenant.

### 1.1 Token — black-box pinned

`BEEP` crunches to a **single-byte STATEMENT token `$C0`** (VG-8020 crunch capture,
`scratchpad/spike_beep_token.py`, 2026-07-21):

| typed | stored body bytes |
|---|---|
| `beep` | `c0 00` |
| `beep:beep` | `c0 3a c0 00` |
| `sound 1,2:beep` | `c4 20 12 2c 13 3a c0 00` |

So `$C0`, no arguments, no prefix collision (no keyword shares the "BEEP" prefix;
`match_kw` compares the full keyword). `$C0` is otherwise unused in
[`kwtable.inc`](../basic/kwtable.inc). Cross-checked against MSX2 TH Table 2.20.

---

## 2. Behaviour — black-box pinned (VG-8020 PSG trace)

The reference contract was captured with the arc's per-VBLANK PSG trace harness
(`probes/lib/psgtrace.py`) running `beep` on `Philips_VG_8020`, 2026-07-21:

```
baseline  R0=00 R1=00 ... R7=b8 R8=00 R9=00 R10=00 R11=0b R12=00 R13=00   (silent)
BEEP on   R0=55 R1=00 ... R7=be R8=07 ...                                  (tone A, vol 7)
~2 frames later
BEEP off  R0=55 R1=00 ... R7=b8 R8=00 ...                                  (silent again)
```

Decoded, `BEEP` performs exactly this sequence:

1. **Tone A period** ← `$0055` (85): write `R0=$55` (fine), `R1=$00` (coarse).
   ≈ 1316 Hz (1789772.5 / (16·85)).
2. **Mixer** ← mute everything but tone A, preserving the two PSG I/O-direction bits:
   `R7' = (R7 & $C0) | $3E`.
   `$3E = 0011 1110` = tone A **on** (bit0=0), tones B/C **off** (bits 1,2=1),
   all three noise channels **off** (bits 3,4,5=1). From the baseline `$b8` this
   yields `$be`, matching the trace.
3. **Channel-A amplitude** ← `$07` — a **fixed** volume 7 (bit 4 = 0, i.e. NOT
   hardware-envelope mode). The envelope registers R11/R12/R13 are **left
   untouched** (trace: unchanged throughout).
4. **Delay** — a short fixed duration, ≈ 2 VBLANK frames (≈ 33 ms) in the trace.
5. **Silence** — write `R8=$00`.
6. **Restore mixer** — write `R7` back to its saved pre-beep value.

Notes carried from the trace, all faithful-repro requirements:
- The tone period (R0/R1) is **not** restored — it is left at `$0055` after the
  beep (trace: post-beep R0 still `$55`). Only R8 and R7 are reverted.
- Volume is **fixed** (R8=$07), **not** the hardware envelope. A self-decaying
  envelope beep (R8=$10, R13=one-shot) would sound similar but would NOT match the
  VG-8020 PSG trace, so it is rejected — the gate requires byte-fidelity.
- No `MUSICF` / PLAY-queue interaction: `BEEP` is a direct, self-contained event.

---

## 3. Why direct-PSG, not `CALL $00C0` (design fork — resolved)

Real MSX BASIC's `BEEP` is `CALL BEEP ($00C0)` — a BIOS delegation. Two facts
resolve the fork **against** delegating, in favour of reproducing the PSG sequence
directly (consistent with how Slice 1 built `SOUND`):

1. **Consistency + gate-ability.** `SOUND`/`PLAY` own the PSG protocol directly
   (direct port I/O, VG-8020-pinned) precisely so they are slot/BIOS-independent
   and differentially gate-able against the VG-8020. `BEEP` is the sibling; a
   `CALL $00C0` beep could not be VG-8020-sound-differentiated.
2. **C-BIOS's `$00C0` does not produce our beep.** On the runtime BIOS (C-BIOS),
   `$00C0` is `JP $1656` (a real routine, not a bare `RET` stub), yet a PSG trace
   of it via `USR(&HC0)` on the repack build showed **zero PSG activity across 700
   frames** — C-BIOS's BEEP is silent or divergent on this path (another C-BIOS
   BIOS gap, cf. the LPTOUT gap we filled — memory `cbios-lptout-followup`).
   `CALL $00C0` would therefore give a **broken/silent** BEEP on zerobas.

⇒ Reproduce the VG-8020 PSG sequence directly in zerobas-BASIC. Slot/BIOS-
independent, deterministic, and VG-8020-byte-faithful.

---

## 4. Implementation sketch

Add `ex_beep` as a sibling of `ex_sound` in [`basic/sound.asm`](../basic/sound.asm)
(shares the `PSG_ADDR`/`PSG_DATW`/`PSG_DATR` equates; no new file, no Makefile
`SUB_PARTS`/include churn). Wire the dispatch in
[`interp.asm`](../basic/interp.asm) next to `SOUND_TOKEN`/`PLAY_TOKEN`
(`cp BEEP_TOKEN : jp z,ex_beep`, inside the existing `IF ROM_BASE < $4000`).
Define `BEEP_TOKEN equ $C0` in [`sysvars.inc`](../basic/sysvars.inc). Add
`db 4,"BEEP",1,BEEP_TOKEN` to the audio block of
[`kwtable.inc`](../basic/kwtable.inc).

`ex_beep` (no arg parse):
```
ex_beep:
        inc     hl                  ; past the BEEP token
        ; --- save current R7 (mixer), atomic vs play_service ---
        di
        ld      a,7 : out (PSG_ADDR),a : in a,(PSG_DATR)   ; A = cur R7
        ld      c,a                 ; C = saved R7
        and     $C0 : or  $3E : ld  b,a                     ; B = beep-mixer byte
        ; --- program tone A period 85, mute-all-but-A, vol 7 ---
        ld a,0 : out (PSG_ADDR),a : ld a,$55 : out (PSG_DATW),a   ; R0 = $55
        ld a,1 : out (PSG_ADDR),a : xor a     : out (PSG_DATW),a   ; R1 = $00
        ld a,7 : out (PSG_ADDR),a : ld a,b    : out (PSG_DATW),a   ; R7 = beep mixer
        ld a,8 : out (PSG_ADDR),a : ld a,7    : out (PSG_DATW),a   ; R8 = 7
        ei                          ; delay runs with interrupts on (see §4.1)
        ; --- fixed delay ~33 ms ---
        call    beep_delay
        ; --- silence A, restore R7 ---
        di
        ld a,8 : out (PSG_ADDR),a : xor a  : out (PSG_DATW),a      ; R8 = 0
        ld a,7 : out (PSG_ADDR),a : ld a,c : out (PSG_DATW),a      ; R7 = saved
        ei
        jp      exec_stmt           ; chain the next `:`-separated statement
```
(`beep_delay` = a plain counted loop calibrated to ≈ 2 VBLANK frames. Exact value
tuned so the psgtrace gate sees the beep span ≥1 sampled frame; duration is not
black-box-pinnable finer than ~1 frame.)

### 4.1 Interrupt discipline
Each PSG latch+access pair is `di`-guarded (atomic against `play_service`, which
programs the PSG from the `$0038` ISR — same rule Slice 1 adopted for `SOUND`).
The delay loop runs **`ei`** (matches the reference: BEEP's duration is a software
delay with interrupts live, so VBLANK/VDP servicing continues). Accepted edge,
matching real-hardware behaviour: a `BEEP` issued **while a `PLAY` is actively
draining** will be fought by `play_service` during the delay window (both write the
PSG). With no active PLAY (`MUSICF=0`), `play_service` is a no-op and the beep is
clean. Documented, not specially handled.

---

## 5. Acceptance

- **Standing gate** `make beep-acceptance` (new; `probes/basic/basic_probe_beep.py`),
  repack-only + oracle-dependent. Per-VBLANK PSG trace differential vs the VG-8020
  (reuse `psgtrace.py`): after `beep`, assert the transient shows
  **R0=$55, R1=$00, R7=(prevR7 & $C0)|$3E, R8=$07** for ≥1 sampled frame, then
  returns to **R8=$00** with R7 restored. Duration-tolerant (±1 frame). Include a
  `beep:beep` chain case (two blips) and a `sound 7,190:beep` case (R7 restored to
  the SOUND-set value, proving the save/restore is dynamic not hardcoded).
- **Crunch**: add `beep` to the crunch corpus (`beep`→`c0`, `beep:beep`→`c0 3a c0`)
  so the token is locked byte-for-byte vs the VG-8020.
- **Host unit test** `tests/test_beep.py` under `make unit-test`: the emulator-free
  fast layer — exercise `ex_beep`'s R7 read-modify-write mask
  (`(R7 & $C0)|$3E`) and the PSG write ordering against a mock PSG.
- **Regression**: lean `basic.rom` stays byte-identical (all under `IF ROM_BASE <
  $4000`); `sound-acceptance`, `play-acceptance`, `play-trace-acceptance` still green.

### 5.1 Adversarial / empirical pass (RECURRING ARC LESSON)
Per the standing trap (green build ≠ run): after implementing, **boot the repack
build and actually run `beep` under psgtrace** — do not trust a green assemble.
Verify the transient is non-vacuous (the beep genuinely appears then clears), and
that `sound 7,190:beep` restores R7 to `$be`-style value not a hardcoded `$b8`.

---

## 5.2 What the adversarial pass actually caught (recurring arc lesson, again)
The first working build had `ex_beep` hold the preserved I/O bits in `C` across the
`call beep_delay`. But `beep_delay` is a `ld bc,N` / `dec bc` busy loop — it zeroes
`C`. So the restore computed `0 | $38 = $38` instead of `ioBits | $38 = $b8`. **The
per-VBLANK PSG-trace differential was BLIND to this**: openMSX's `PSG regs` read-back
reports R7 as `$b8` whether `$38` or `$b8` was written (R7's bits 6-7 are the I/O-port
direction, which the debuggable normalises), so the trace showed the correct `$b8`
*before and after* the fix. Only **`tests/test_beep.py`**, which captures the literal
OUT bytes, saw the wrong `$38` and failed. Fix: hold the I/O bits in `E` (which
`beep_delay` preserves). Lesson re-confirmed: the emulator-free host layer capturing
raw writes is load-bearing; a green differential is not proof. (memory:
`error-handling-arc` recurring lesson; `gate-during-implementation`.)

## 6. Divergences / out of scope
- Runtime beep is VG-8020's beep (period 85, vol 7), frozen into the interpreter —
  a documented deviation from "BEEP = whatever the runtime BIOS produces" (§3).
- `Ctrl-G` (`PRINT CHR$(7)`) console-bell is a **separate** path (the print layer),
  not this item.
