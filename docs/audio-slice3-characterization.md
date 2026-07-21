# Audio Slice 3 — reference drain characterization (the `play_service` contract)

Status: **IMPLEMENTED + GATED (2026-07-21).** Characterization was reviewed and signed
off, then `play_service` was built to this contract. All gates green: `make
play-trace-acceptance` (per-VBLANK PSG trace differential vs VG-8020 — byte-faithful
across scale/rest/dots/octaves/multi-voice/envelope/R7/DI-safety), `make
sound-acceptance` + `make play-acceptance` regression-clean, 49/49 `unit-test` (incl the
new `tests/test_play_frame_sim.py` host drain simulator), lean ROM byte-identical. This
doc pins the black-box unknowns the [Slice-3 spec](spec-basic-audio-play.md) §3.B/§4
deferred to "the empirical differential"; the servicer implements them exactly.
Implementation: [`basic/playsvc.asm`](../basic/playsvc.asm) (`play_service` +
`play_install`), seam in [`initext.asm`](../basic/initext.asm), corrected formula +
measured period table in [`sub/playparse.asm`](../sub/playparse.asm) /
[`tests/mml_ref.py`](../tests/mml_ref.py).

Method: per-VBLANK PSG-register trace of the **Philips VG-8020** (PAL) draining live
`PLAY` music. Harness = [`probes/lib/psgtrace.py`](../probes/lib/psgtrace.py): hooks the
`VDP.IRQvertical` probe (raised edge → one sample per frame), reads the openMSX
`PSG regs:0:14` debuggable each VBLANK while the reference's `$0038` ISR drains the
queue. Black-box only — no stock-ROM disassembly ([memory: no-reference-rom-disasm]).
Provenance clean: we observe register *effects*, never ROM bytes.

---

## 1. Frame timing — PINNED (corrects the current guess)

**`frames = max(1, 12000 // (T * L))` — floor division, constant 12000.**

Verified exact across 8 (tempo, length) points:

| T | L | T·L | measured frames | `12000//tl` | old guess `(14400+tl/2)//tl` |
|---|---|-----|-----------------|-------------|------------------------------|
|120|4|480|**25**|25|30|
|120|8|960|**12**|12|15|
|120|2|240|**50**|50|60|
|100|4|400|**30**|30|36|
|150|4|600|**20**|20|24|
|144|4|576|**20**|20|25|
|180|4|720|**16**|16|20|
|240|4|960|**12**|12|15|

Two corrections to [`tests/mml_ref.py`](../tests/mml_ref.py) (the single source of truth
that generates the asm table + the host decoder's expectations):

1. `FRAME_BASE` **14400 → 12000**.
2. Rounding **half-up → floor**: `(FRAME_BASE + tl//2)//tl` → `FRAME_BASE // tl`.
   The half-up form was wrong for non-integer quotients (t144l4: 20.83 → ref **20**,
   half-up gives 21; t120l8: 12.5 → ref **12**, half-up gives 13).

Why 12000: `12000 = 240 × 50`. On PAL/50 Hz this makes tempo `T` ≈ BPM exactly
(quarter @ T120 = 25 frames = 0.5 s = 120 BPM). The **frame count is Hz-independent**
(the ISR counts VBLANKs), so no NTSC/PAL branch is needed — the same count plays
faster on a 60 Hz machine, exactly as the reference does. (Measured on PAL only; the
count model is Hz-agnostic by construction — a small residual to sanity-check if a
60 Hz oracle ever becomes available.)

### Dots
- **Single dot adds `ceil(base/2) = (base+1)//2`.** Verified: L4·=38 (25+13), L8·=18
  (12+6), L2·=75 (50+25).
- Double dot: L4·· = **44** = 25 + 13 + 6 → "ceil for the first dot, floor of the
  running addend thereafter". Parser-side and rare; logged as a **low-priority
  residual** to fully pin if we decide double-dots need byte-faithfulness.

The current `mml_ref.note_frames` dot loop (`add //= 2; fr += add`) is wrong on the
first dot for odd `base` (uses floor, ref uses ceil).

---

## 2. Per-voice drain model — the `play_service` behavioral contract

Each VBLANK, for each voice `v` whose `MUSICF` bit is set:

- **Independent down-counter per voice**, decremented once per frame. A note occupies
  exactly `dur` consecutive VBLANKs; the next note programs on the frame immediately
  after — **no gap** (measured: consecutive notes change on back-to-back-by-`dur`
  frames, e.g. C@f315 → D@f340 → E@f365, Δ25 each). Implementation: on programming a
  note set `counter = dur`; each frame `counter--`; when it reaches 0, fetch the next
  packet and program it **that same frame**.
- Voice `v` → PSG **channel A/B/C** = registers: tone period `R(2v)/R(2v+1)`,
  amplitude `R(8+v)`. Confirmed independent per-voice accounting with a 3-voice tune
  (quarters/halves/whole each ended at their own `start+dur`).

**Programming a NOTE packet** (`OP_NOTE [period_lo, period_hi, amp, dur_lo, dur_hi]`):
- Write tone period → `R(2v), R(2v+1)`.
- Write amplitude → `R(8+v)`: volume `0..15` (bit4=0) in V-mode, or **`$10`**
  (bit4=1, "follow envelope") in S-mode. (Verified: V15→`0x0f`, V4→`0x04`, V8→`0x08`;
  S-mode amp reg bit4 set.)

**REST** — the one place the naive encoding diverges from the reference, and it
**matters for the trace gate**:
- The reference writes **amplitude 0 only** and **leaves the tone period untouched**
  (measured: during an `R`, `R0/R1` retain the previous note's period `428`, not 0).
- Our parser currently emits a rest as `OP_NOTE` with `period = 0x0000, amp = 0`.
  Since a real tone period is always `1..4095`, **period == 0 is a safe sentinel**:
  → **Recommendation: `play_service` treats `period == 0x0000` as a rest — writes the
  amplitude byte only, skips the tone-period write.** This makes `R0/R1` retain the
  prior value (matches the reference trace) with **zero parser change**.

**ENVELOPE note** (`OP_ENV [shape, per_lo, per_hi]` precedes the affected notes):
- Set envelope period → `R11 (fine), R12 (coarse)` from `M`; set envelope shape →
  `R13` from `S` (low nibble). Amp reg for the note = `$10`.
- Envelope period is set once (persists across notes); tone still reprogrammed per
  note. **Residual (minor):** whether `R13` is *re-written per note* to re-trigger the
  envelope, or only when `S` changes — the raw read's upper bits shifted per note,
  hinting at a per-note rewrite, but the semantic nibble was constant. Re-triggering
  per note is the standard MSX behavior and the safe default; confirm on the gate.

**R7 (mixer) — NEVER touched.** R7 stayed constant `0xB8` (all three tones enabled,
noise off) across every trace, single- and multi-voice. **`play_service` must not
write R7.** zerobas already boots `R7 = 0xB8` (C-BIOS GICINI), byte-identical to the
reference idle state — so the mixer trace matches for free, no init write needed.
(Corollary: silence is *always* amplitude 0, never a mixer-disable bit.)

**End of a voice's queue (`OP_END`):** clear that voice's `MUSICF` bit; leave the
channel's amplitude at 0 (music ends silent; the tone period keeps its last value).

---

## 3. MUSICF (`$FB3F`) — "music finished" detection

- Bit `v` = voice `v` queue active. `MUSICF == 0` ⟺ all music done (the flag a program
  `PEEK`s to wait for completion).
- The parser sets the present-voice mask **last** (already done in Slice 2a, so a
  mid-parse VBLANK never drains a half-built queue). **`play_service` clears bit `v`
  at that voice's `OP_END`.** Measured on a 2-voice unequal-length tune: `0x03` while
  both play → `0x01` when the half-note voice ended → `0x00` when the last voice ended.
- Benign transient: the reference momentarily shows `0x07` (all 3 bits) for one frame
  at PLAY start, then clears the empty voices' bits on the first drain. Our parser
  sets the exact present-mask directly, so zerobas skips that 1-frame `0x07` — a
  one-frame `MUSICF` difference only, not a PSG-audible one.

---

## 4. Slice-3 gate (proposed)

Boot-per-case, per-VBLANK **PSG register trace differential vs the VG-8020**, driven by
[`probes/lib/psgtrace.py`](../probes/lib/psgtrace.py):
- Compare tone `R0–R5`, amplitude `R8–R10` every frame; `R11–R13` for envelope cases;
  assert `R7` stays `0xB8`. Optional secondary: `MUSICF` at `$FB3F`.
- Tune set already exercised (reusable as gate cases): tempo/length battery, dots,
  rests, volume, envelope (S/M), 3-voice interleave, MUSICF completion.
- Emulator-free fast layer: extend [`tests/test_play_parse.py`](../tests/test_play_parse.py)'s
  host decoder with a frame-by-frame drain simulator asserting the same per-frame
  register sequence (locks the model without booting openMSX).

---

## 4a. Placement resolution — page-1 resident, NOT page-0 (deviation from spec §3.B)

Measured free space (from `build/basic-reloc.sym`): **page-0 low region = 19 B**
(`__MEAS_LOW_END=$3FED`), **page-1 = 932 B** (`__MEAS_PAGE1_END=$7C5C`).
`play_service` (~100–200 B) cannot fit page 0.

The spec (§3.B) required page-0 residence to avoid the §4.3 hazard: "a VBLANK fires
while the CPU is inside a page-1 tenant CALSLT (e.g. `SIN(x)`) — main page 1 is
switched out, so a page-1-resident servicer would be unmapped when the ISR reaches
it." **That scenario is impossible here:** `subrom_call` wraps every page-1 tenant
CALSLT in `di … call CALSLT … ei` ([subromcall.asm:67-69](../basic/subromcall.asm)) —
tenants run **fully under DI**, and a grep confirms **no page-1 tenant opts into EI**.
So a VBLANK never fires while main page 1 is switched out. In every case where the
ISR's `H.TIMI` actually runs:

1. Normal EI main-ROM execution → main page 1 mapped. ✓
2. Page-1 tenant CALSLT → DI, no IRQ serviced until `ei` (page 1 already restored). ✓
3. Page-0 tenant running EI → CALSLT switched page 0 only; main page 1 still mapped. ✓

**Decision: `play_service` is page-1 main-ROM resident** (repack-only, alongside
`ex_sound`/`ex_play`), reached from `H.TIMI` by a near `JP`. No page-0 window needed;
the §4.3 hazard is void under the DI discipline. This is *safer* than the spec's stated
page-1-**tenant** fallback (which re-accepted §4.3 and would have added an ISR-path
CALSLT). Empirical guard added to the gate: PLAY a tune, then spin a tight `SIN` loop,
assert the music keeps draining and the machine never derails.

## 5. Summary of changes this pins (for the implementation phase, post-review)

| Where | Change |
|-------|--------|
| `tests/mml_ref.py` | `FRAME_BASE` 14400→**12000**; base rounding half-up→**floor**; dot first-step **ceil** |
| `sub/playparse.asm` | regen the note→frames path from `mml_ref` (table + dot); rest already emits period 0 (kept) |
| `tests/test_play_parse.py` | expected durations follow the corrected `mml_ref` |
| **`play_service` (NEW, resident page-0)** | per-voice down-counter drain per §2; `period==0`⇒rest (amp-only); env R11/12/13; **never touch R7**; clear `MUSICF` bit at `OP_END` |
| **`H.TIMI` seam (NEW)** | install `JP play_service` at `$FD9F` at boot; `MUSICF==0 → ret` fast-out |
| gate | `make play-trace-acceptance` (new) using `psgtrace.py`; host frame-sim in `test_play_parse.py` |
