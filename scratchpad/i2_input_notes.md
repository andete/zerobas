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

`PAD(0..7)` is **0 in every configuration measured**, including touchpad plugged
in either port, with and without the transform offset. `PAD(8)` → ERR 5.

That is the honest state: `PAD(0)` is the *touched?* status, being touched needs
a host mouse button, and §1 establishes there is no way to deliver one. The BIOS
therefore never latches x/y, so `PAD(1)`/`PAD(2)` cannot be moved off 0 either.

**Consequence for the gate — state it plainly rather than let it read as
coverage:** `PAD` can only ever be gated in its idle state, exactly as
`STICK(1..2)`/`STRIG(1..4)` were in I1. An implementation that returned a
constant 0 for `PAD` would pass every available case. `PDL` does *not* share this
limitation — the `128` and the two `0`s in §2 are genuine teeth that a constant
cannot fake, and they are reachable with nothing but a `plug` line.

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

## 5. Harness gap this implies

`omsx_repl` has no hook for **per-batch Tcl prologue**, which is what a `plug`
line is. I2's gate needs one (the characterization probe monkey-patched around
`_tcl` to get here, which is fine for scratch and not fine for a standing gate).
Small and clearly reusable — the interrupt-trap arc will want the same seam.
