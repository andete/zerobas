<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# I2 characterization record — `PDL(n)` / `PAD(n)`

Companion to [`i1_input_notes.md`](i1_input_notes.md) and
[`../docs/spec-basic-input-devices.md`](../docs/spec-basic-input-devices.md) §9.
Everything below is **black-box measured** on the Philips VG-8020 reference under
openMSX (probe `scratchpad/i2_char.py`), or read from openMSX's own Tcl surface.
No ROM disassembly. The *protocol* half (how the BIOS pulses and counts) is NOT
in here — it needs the MSX Technical Data Book and is still open.

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

## 4. Harness gap this implies

`omsx_repl` has no hook for **per-batch Tcl prologue**, which is what a `plug`
line is. I2's gate needs one (the characterization probe monkey-patched around
`_tcl` to get here, which is fine for scratch and not fine for a standing gate).
Small and clearly reusable — the interrupt-trap arc will want the same seam.

## 5. Still open before I2 can be written

The **protocol**: how `GTPDL` selects a paddle and counts, and how `GTPAD`
strobes/latches — PSG R15 (port B, output) pin-8 pulse plus the R14 (port A,
input) read, and the timeout that yields 255. That is a published-interface
question for the **MSX Technical Data Book** (`docs/allowed-sources.md`: B /
Scoped / gen 1) plus the AY-3-8910 datasheet (A / Clean), which zerobas-tape
already cites for `$A0`/`$A2`. Not yet fetched.
