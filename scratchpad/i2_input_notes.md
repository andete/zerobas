<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# I2 characterization record — `PDL(n)` / `PAD(n)`

Companion to [`i1_input_notes.md`](i1_input_notes.md) and
[`../docs/spec-basic-input-devices.md`](../docs/spec-basic-input-devices.md) §9.
Everything below is **black-box measured** on the Philips VG-8020 reference under
openMSX (probe `scratchpad/i2_char.py`), or read from openMSX's own Tcl surface.
No ROM disassembly. §§1–3 are the black-box half; §4 is the **protocol** half,
read from the MSX2 Technical Handbook (fetched once and cached, §5).

## 1. What openMSX can and cannot drive

| capability | verdict |
|---|---|
| `plug joyporta paddle` / `joyportb paddle` | ✅ works |
| `plug joyporta touchpad` / `joyportb touchpad` | ✅ works |
| `plug joyport{a,b} msxjoystick1` | ✅ works (I1 recorded `joystick1` failing — the pluggable is named `msxjoystick1`) |
| **drive a paddle / touchpad VALUE headlessly** | ❌ **impossible** — the full `info commands` list contains exactly two input-injection commands, `keymatrixdown` and `keymatrixup`. There is no mouse/absolute-pointer injection, and both devices are host-mouse-driven. |
| `touchpad_transform_matrix` as a back door | ❌ tried `{{256 0 200} {0 256 100}}` (a translation): **no effect**. It maps host mouse *events*; with no events there is nothing to transform, and `PAD(0)` stays 0 so the BIOS never latches x/y. |
| `debug write joystickports` as a pin-level back door | ❌ the write is accepted and then **ignored** — `debug read joystickports 0` returns 63 before and after writing 0 and 0xFF. The connector recomputes the pin state on every read. |

`joystickports` is however a useful **read-only** observable: 2 bytes (port A, port
B), idle `63`/`63`, and plugging a paddle into port A takes byte 0 to **62** — a
BIOS-free way to assert that a device is actually present.

## 2. Measured values — the whole `PDL` matrix, four configurations

`PDL(1..12)` on the reference, one boot-shared batch per configuration:

| n | nothing | paddle in A | paddle in B | touchpad in A | touchpad in B |
|---:|---:|---:|---:|---:|---:|
| 1 | 255 | **128** | 255 | 255 | 255 |
| 2 | 255 | 255 | **128** | 255 | 255 |
| 3 | 255 | 255 | 255 | **0** | 255 |
| 4 | 255 | 255 | 255 | 255 | **0** |
| 5 | 255 | 255 | 255 | **0** | 255 |
| 6 | 255 | 255 | 255 | 255 | **0** |
| 7..12 | 255 | 255 | 255 | 255 | 255 |

Domain edges re-confirmed: `PDL(0)` and `PDL(13)` → **ERR 5**, matching spec §5.

### The index→port mapping, settled empirically

The port-A and port-B columns are **exact mirrors under `n ↔ n+1`**. So

* **odd `n` = joystick port 1, even `n` = joystick port 2**;
* the paddle within the port is `(n+1) >> 1`, i.e. `n = 1,3,5,7,9,11` are port-1
  paddles 1..6 and `n = 2,4,6,8,10,12` are port-2 paddles 1..6.

This was *derived from the black box*, not taken from a doc — the two-port
symmetry is what makes it a proof rather than a guess. It also explains the
touchpad rows: the touchpad drives the port's data lines that paddles 2 and 3
(`n = 3` and `n = 5` on port 1) would otherwise read, pulling them to **0**
instead of the floating-high **255**.

* **Idle (nothing plugged) = 255**, i.e. the count runs to its cap — consistent
  with "no device ever pulls the line", and it is why 255 is *also* the idle
  value the spec already pinned.

## 3. Measured values — `PAD`

### 3.1 With `touchpad` — all zero (and why that misled me)

`PAD(0..7)` is **0** with `touchpad` plugged in either port, with and without the
transform offset. `PAD(8)` → ERR 5. `PAD(0)` is the *touched?* status, being
touched needs a host mouse button, and §1 says there is no way to deliver one, so
the BIOS never latches x/y and `PAD(1)`/`PAD(2)` stay 0 too.

**I concluded from this that `PAD` could never be gated above idle. That was
wrong, and the error was in the sampling, not the reasoning:** I tested only
`touchpad`, because that is the device the TH's table names for ids 0..3, and
never ran the *other* joyport pluggables against `PAD`. See §3.2.

### 3.2 With `arkanoidpad` — `PAD` HAS TEETH

| index | arkanoidpad in port A | arkanoidpad in port B | nothing plugged |
|---:|---:|---:|---:|
| `PAD(0)` sense 1 | **−1** | 0 | 0 |
| `PAD(1)` X 1 | **255** | 0 | 0 |
| `PAD(2)` Y 1 | **255** | 0 | 0 |
| `PAD(3)` button 1 | 0 | 0 | 0 |
| `PAD(4)` sense 2 | 0 | **−1** | 0 |
| `PAD(5)` X 2 | 255 | **255** | 0 |
| `PAD(6)` Y 2 | 255 | **255** | 0 |
| `PAD(7)` button 2 | 0 | 0 | 0 |

Reproduced across two runs. **Four distinct outcomes (−1, 255, 0, and the
port-mirroring of the sense index) — a constant-0 `PAD` fails this immediately.**
The sense index tracks which port holds the device, the same port-mirror proof
structure that settled `PDL`'s mapping in §2.

Two consequences beyond "the gate works":

* **The `$FF` → `-1` widening is now MEASURED, not inferred.** `PAD(0)` = **−1**
  while `PAD(1)`/`PAD(2)` = **255**. So the boolean sub-functions widen like
  `STRIG` and the coordinate sub-functions zero-extend — exactly the per-index
  asymmetry that was only an inference before, now pinned from the reference.
* **`mouse` and `trackball`** also plug, and drive `PDL(1,3,5)` to 0, but their
  `PAD` cases failed to capture cleanly and were not pursued (they are BIOS ids
  12..15, outside BASIC's 0..7 anyway).

**What this still does NOT give:** `PAD(1)` and `PAD(2)` both read **255**, so the
gate cannot tell the X channel from the Y channel — the µPD7001 *address phase*
(§4.6) remains undiscriminated. The teeth are real but they bite on the
sub-function dispatch and the widening, not on the channel selection.

`PDL` likewise gains a case: with `arkanoidpad` in port A, `PDL(1)` = **0**.

## 4. The protocol — published, and where it stops

Source: **MSX2 Technical Handbook ch. 5** (`docs/allowed-sources.md`: B / Scoped;
Konamiman's public English translation, raw cached at
`~/Documents/msx/docs-cache/TH-Chapter5a.md`,
sha256 `a07854dc…71071cce`). Fetched once, per [[be-gentle-on-services]].

### 4.1 The port wiring (TH figs. 5.21, 5.22 A/B) — fully published

| PSG reg | bits | meaning |
|---|---|---|
| **R14** (port A, input) | b0..b5 | terminals **1, 2, 3, 4, 6, 7** of the *selected* interface |
| | b7 | cassette data in (already cited by zerobas-tape) |
| **R15** (port B, output) | b4 | 8th terminal of interface **1** |
| | b5 | 8th terminal of interface **2** |
| | b6 | **selects** which interface R14 b0..b5 is connected to (0 = #1, 1 = #2) |
| | b7 | kana/Arabic lamp |

### 4.2 The paddle (TH §5.3, fig. 5.24) — fully published, and it *confirms §2*

Pulsing the 8th terminal triggers a one-shot multivibrator (LS123-compatible)
whose output appears on **terminal 1** — "for 2, 3, 4, 6, or 7 a similar circuit
would apply". The pulse lasts **10 µs to 3 ms**, set by a 150 kΩ variable
resistor; measuring its length gives the turning angle. `GTPDL` `$00DE` takes
A = 1..12 and returns A = 0..255.

Six terminals (1, 2, 3, 4, 6, 7) = six paddles per port = exactly R14 b0..b5. So
paddle *k* (1..6) of the selected port is **R14 bit (k−1)** — which is precisely
the mapping §2 derived black-box, now corroborated from the published circuit
*independently*. The touchpad rows in §2 fall out too: it holds terminals 2 and 3
(bits 1, 2) low, which are port-1 paddles 2 and 3 = `PDL(3)` and `PDL(5)`.

3 ms ÷ 255 ≈ **11.8 µs per count**, i.e. a ~43 T-state loop at 3.58 MHz, capping
at 255. Idle = the cap, which is the measured 255.

**This gives the gate sharper teeth than expected.** openMSX's paddle returned
**128** through the *reference* BIOS's counting loop. Reproducing 128 means our
loop must count at the same *rate*, so a timing error shows up as a wrong number
rather than as a pass. `PDL` is well-founded and well-gated.

### 4.3 The touch panel — the caller contract is published, the WIRE PROTOCOL IS NOT

The TH publishes `GTPAD` `$00DB`'s device-ID table (0..3 touch panel 1, 4..7
touch panel 2, 8..11 light pen, 12..15 mouse/trackball 1, 16..19 the mouse-2
mirror) with `$FF`/`$00` for touched and 0..255 for X/Y — and note that
**BASIC's `PAD(n)` domain 0..7 is the MSX1 subset** of that wider BIOS surface,
which is why the reference gives ERR 5 at `PAD(8)` (§3) while the BIOS accepts up
to 19. It also publishes the calling *sequence* (sense with A=0; X/Y are
meaningful only once that returned `$FF`) in List 5.8.

What it does **not** publish is how the panel puts X/Y on the wire. The TH gives
the paddle a circuit diagram and the touch panel none. And the community's own
account of it is titled *"MSX-Touchpad protocol reverse engineered"* — i.e. the
readily-available description is **RE'd, therefore ✗** under the firewall, and
openMSX's model is C / Conditional / corroboration-only with nothing to
corroborate *against*.

**But this is not a wall — see [[dont-prematurely-wall]].** The panel's interface
chip is a **NEC µPD7001**, a 4-channel 8-bit serial ADC, and *the chip is the
reference*: its NEC datasheet is an A / Clean source on exactly the footing the
AY-3-8910 already has in `tape/PROVENANCE.md`. Channel 0 = X, channel 3 = Y,
channels 1/2 always 0, MSB first. That covers the *serial protocol*. The only
genuinely unpublished residual is the **pin mapping** — which joyport terminal
carries CS / CLK / data / EOC — and that is reachable through **our own oracle**
(A / Clean): drive R15 b4 ourselves and watch R14 under openMSX's plugged
touchpad, which is a black-box characterization of the device, not of any ROM.
§1's finding that values can't be driven does not block this: the *handshake*
runs regardless of what coordinate comes back.

### 4.4 The µPD7001 datasheet — obtained, and what it says

Sourced from the **1982 NEC Microcomputer Catalog** (`µPD7001`, "8-BIT SERIAL
OUTPUT A/D CONVERTER", pp. 479–482, doc id `7001DS-REV 2-1-82-CAT`), via the
bitsavers scan on archive.org. A **manufacturer** data book ⇒ **A / Clean**, the
same footing as the AY-3-8910. Raw cached at `~/Documents/msx/docs-cache/`
(`nec1982.txt` sha256 `cb58ef72…b4be72d0`; the extracted chip section
`upd7001-extract.txt` sha256 `0d9ff383…303d9598`). The aggregator sites
(alldatasheet / datasheet4u / datasheetspdf) are all JS-gated or 403 and yielded
nothing — bitsavers is the route that works, and it is the better-provenance one
anyway.

Pin names, verbatim: `EOC` End of Conversion (open drain) · `DL` Analog Channel
Data Load · `SI` Serial Data Input · `SCK` Serial Data Clock · `SO` Serial Data
Output (open drain) · `CS` Chip Select · `CL0`/`CL1` Successive Approximation
Clock · `A0..A3` Analog Inputs · `VREF`, `AG`, `VSS`, `VDD`. 16-pin.

Protocol, verbatim in substance:

* the 4 analog inputs are selected by a **2-bit** address applied to `SI` and
  **latched with `DL`**; channel address (D0, D1) = A0 `L,L` · A1 `H,L` ·
  A2 `L,H` · A3 `H,H`;
* the internal sequence controller **initiates a conversion cycle at a RISE of
  `CS`**; at the final step the result is transferred to an 8-bit shift register
  and the next conversion begins immediately;
* **with `CS` low the data is exchanged** with the external circuit; **with `CS`
  high the chip converts and accepts no external digital signal**; 5 internal
  clock pulses are needed before data output;
* the 8 result bits leave on open-drain `SO`, **MSB first**, synchronised to an
  external clock on `SCK`;
* `EOC` is low during conversion; `t_CONV = 14 × 4 × 1/f_CK`, typ. 140 µs at
  f_CK = 400 kHz.

So the serial protocol is fully and admissibly specified. Only the **terminal
mapping** was left, which §4.5 now settles.

### 4.5 The pin mapping — recovered from our own oracle, method validated first

Probe `scratchpad/i2_pinmap.py`. We drive the one output line the port gives us
(R15 b4 = the 8th terminal of interface 1) from BASIC and sample R14 b0..b5 after
every edge. This characterizes the **device**, not any ROM.

**The paddle is the control, and it is a known-answer control** — its circuit
*is* published (§4.2, TH fig. 5.24: the one-shot answers on terminal 1). If the
method is sound it must recover that. Measured (R14 & `$3F`):

| config | toggle the 8th terminal ×16 | held low ×8 | held high ×8 |
|---|---|---|---|
| **nothing plugged** (control) | `3F` ×16 | `3F` ×8 | `3F` ×8 |
| **paddle in A** | `3E 3E 3F 3E 3E 3E …` | `3E 3E 3E 3E 3F 3F 3F 3F` | same |
| **touchpad in A** | `3B 3F 3B 3F 3B 3F …` | `3B 3B 3B 3B 3F 3F 3F 3F` | `3F` ×8 |

* Control is clean — all six terminals idle high, nothing moves. Any bit that
  moves below is the device answering.
* **Paddle ⇒ bit 0 = terminal 1.** Exactly where the published circuit puts the
  one-shot. **Method validated on a known answer**, so its verdict on the
  touchpad is evidence and not a guess.
* **Touchpad ⇒ bit 2 = terminal 3**, and it responds to the 8th terminal going
  **low**, not high (held high: nothing). That is the new, previously
  unpublished-to-us fact, recovered admissibly.

**Two things this round did NOT settle, stated so they don't read as done:**

1. §2 has the touchpad pulling *both* `PDL(3)` and `PDL(5)` (terminals 2 **and**
   3) to 0 under `GTPDL`'s own pulsing, whereas this slow toggle moves only
   terminal 3. So **terminal 2 carries a second signal** that is only asserted
   transiently or at speed — the obvious candidates being the `SO`/`EOC` pair.
   Unresolved.
2. **BASIC is far too slow to clock a µPD7001 frame.** `SCK` wants a ~400 kHz
   clock; an `OUT`-in-a-`FOR`-loop manages ~kHz, so we see the envelope of the
   response, never the 8 MSB-first bits. Recovering an actual frame needs a
   **Z80-speed harness** — a small routine injected into RAM that bit-bangs the
   line and logs R14 into a buffer we then read out with `debug read_block`.
   That is the concrete next step for the `PAD` half, and it is a real piece of
   work rather than a tweak.

### 4.6 The Z80-speed round — terminal 2 identified as `EOC`, quantitatively

Probe `scratchpad/i2_frame.py`, the harness §4.5 said was needed: a ~40-byte Z80
routine poked into `$C000` (behind a `CLEAR 200,&HBFFF` so nothing BASIC does can
land on it), fired with `DEFUSR`/`USR`, logging R14 into `$C100` and read back
with `debug read_block`. Sample period is `in a,(n)` 11 + `ld (hl),a` 7 +
`inc hl` 6 + `djnz` 13 = **37 T ≈ 10.34 µs** at 3.579545 MHz — ~50× what BASIC
managed. The paddle is again the known-answer control, and again lands on
terminal 1; nothing-plugged is `3F` throughout in every experiment.

**Speed alone changed the answer, exactly where §4.5 predicted it would.** The
touchpad, square-waved at Z80 speed:

```
toggle    3B 3D 39 3D 39 3D 39 ...     (3F=idle · 3B=t3 low · 3D=t2 low · 39=both)
```

so **terminal 3 follows the driven line** (low in our low phase, high in our high
phase) while **terminal 2 latches low from the first full cycle onward**. The
BASIC-speed probe saw only terminal 3 — residual 1 of §4.5 is resolved, and it
was a sampling-rate artifact, not a second device state.

**Which of the two is `EOC` is then settled by a prediction the datasheet makes
and we can check.** `EOC` is specified low *only during conversion*, with
`t_CONV = 14 × 4 / f_CK` (typ. 140 µs at f_CK = 400 kHz). So clock a burst, stop,
leave the line idle high, and keep sampling: `EOC` must rise again after a
**bounded** interval that does **not** depend on how long we clocked. A data line
would not behave that way.

| experiment | result |
|---|---|
| clock ×8, then sample 64 | terminal 2 low for **12 samples**, then high |
| clock ×32, then sample 64 | terminal 2 low for **12 samples**, then high |
| same, paddle / nothing plugged | terminal 2 never low (controls clean) |

12 × 10.34 µs ≈ **124 µs**, against the datasheet's 140 µs typ — and **identical
for 8 and 32 clocks**, i.e. fixed-duration and clock-count-independent, which is
the signature asked for. (Inverting `t_CONV` on the measurement gives
f_CK ≈ 56/124 µs ≈ 450 kHz, comfortably around the 400 kHz nominal.)

**⇒ terminal 2 = `EOC`, terminal 3 = `SO`.** The first is a quantitative match to
an independently published number, not an argument from elimination.

Recovered mapping, then:

| joyport terminal | R14/R15 bit | µPD7001 signal | how established |
|---|---|---|---|
| 8th | R15 b4 (out) | the driven line — `CS`/`SCK` | the only output the port has (TH fig. 5.22 B) |
| 3 | R14 b2 | **`SO`** | follows the driven line; the non-`EOC` of the pair |
| 2 | R14 b1 | **`EOC`** | fixed ~124 µs low, clock-count-independent ≈ `t_CONV` |

**A hard limit to state before this reads as a finished protocol.** The untouched
touchpad converts to **0**, so every `SO` bit is 0 and the line is
indistinguishable from an echo of the clock *by bit value*; §1 establishes we
cannot produce a non-zero coordinate. So this method can recover the **handshake
and its timing** — which it now has — but **cannot validate the data path's bit
values** end to end. Also still open: how the two address bits (`SI`, latched by
`DL`) are delivered at all, given the port offers exactly **one** output line;
the encoding has to be temporal, and nothing measured so far pins it.

## 5. Harness gap this implies

`omsx_repl` has no hook for **per-batch Tcl prologue**, which is what a `plug`
line is. I2's gate needs one (the characterization probe monkey-patched around
`_tcl` to get here, which is fine for scratch and not fine for a standing gate).
Small and clearly reusable — the interrupt-trap arc will want the same seam.
