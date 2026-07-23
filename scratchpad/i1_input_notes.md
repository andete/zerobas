# Input-devices arc — characterization record (Philips VG-8020)

Raw black-box measurements behind [`../docs/spec-basic-input-devices.md`](../docs/spec-basic-input-devices.md).
Scripts: [`i1_input_char1.py`](i1_input_char1.py) (tokens / values / coercion +
grammar), [`i1_input_char2.py`](i1_input_char2.py) (live key-matrix).
No ROM disassembly — every line here is an observed input→output pair.

Machine: `Philips_VG_8020` under openMSX, `-command "set renderer none"`,
KEYBUF injection via `probes/lib/omsx_repl.py`. Date: 2026-07-23.

---

## Round 1 — crunch tokens (`stored_line` capture of TXTTAB)

```
10 A=STICK(0)            0d800a0041 efffa2 2811 29 00
10 A=STRIG(0)            0d800a0041 efffa3 2811 29 00
10 A=PDL(1)              0d800a0041 efffa4 2812 29 00
10 A=PAD(0)              0d800a0041 efffa5 2811 29 00
10 A=STICK(0)+STRIG(1)   13800a0041 efffa2 281129 f1 ffa3 2812 29 00
```

| keyword | token |
|---|---|
| `STICK` | `$FF $A2` |
| `STRIG` | `$FF $A3` |
| `PDL`   | `$FF $A4` |
| `PAD`   | `$FF $A5` |

All four are two-byte `$FF`-prefixed **function** tokens — the same shape as
`PEEK` (`$FF $97`) / `VPEEK` / `INP`, i.e. they land on the existing `ev_f_ff`
dispatch, not on a new statement token.

## Round 2 — values and the error domain, NOTHING plugged

Each case ran as a stored program with `ON ERROR GOTO 40`; `nnE <err>` = trapped
error number, otherwise the printed values.

| case | source | result |
|---|---|---|
| stick_0_2 | `PRINT STICK(0);STICK(1);STICK(2)` | ` 0  0  0` |
| stick_neg | `STICK(-1)` | **ERR 5** |
| stick_3 | `STICK(3)` | **ERR 5** |
| stick_frac | `STICK(.9);STICK(1.4);STICK(2.6)` | ` 0  0  0` (all accepted) |
| strig_all | `STRIG(0)…STRIG(4)` | ` 0  0  0  0  0` |
| strig_5 | `STRIG(5)` | **ERR 5** |
| strig_neg | `STRIG(-1)` | **ERR 5** |
| pdl_1_4 | `PDL(1);PDL(2);PDL(3);PDL(4)` | ` 255  255  255  255` |
| pdl_0 | `PDL(0)` | **ERR 5** |
| pdl_12 | `PDL(12)` | ` 255` |
| pdl_13 | `PDL(13)` | **ERR 5** |
| pad_0_3 | `PAD(0)…PAD(3)` | ` 0  0  0  0` |
| pad_4_7 | `PAD(4)…PAD(7)` | ` 0  0  0  0` |
| pad_8 | `PAD(8)` | **ERR 5** |
| pad_neg | `PAD(-1)` | **ERR 5** |
| bare_stick | `PRINT STICK` | **ERR 2** |
| stick_noparen | `PRINT STICK 0` | **ERR 2** |
| stick_str | `STICK("X")` | **ERR 13** |
| stick_expr | `A=1:PRINT STICK(A*2)` | ` 0` (arbitrary expression accepted) |
| stick_big | `STICK(40000)` | **ERR 6** |

Unplugged resting values: `STICK`→0, `STRIG`→0, `PDL`→**255**, `PAD`→0.

## Round 3 — argument coercion and grammar

The discriminators were chosen so that *round-half-up* and *truncate-toward-zero*
give **different** verdicts (one lands in the legal domain, the other outside it):

| source | round-half-up would give | truncate would give | **measured** |
|---|---|---|---|
| `PDL(0.6)` | 1 → 255 | 0 → ERR 5 | **ERR 5** |
| `PDL(12.6)` | 13 → ERR 5 | 12 → 255 | **255** |
| `STRIG(4.9)` | 5 → ERR 5 | 4 → 0 | **0** |
| `STICK(-0.6)` | −1 → ERR 5 | 0 → 0 | **0** |
| `STICK(-0.4)` | 0 → 0 | 0 → 0 | 0 (agrees, control) |
| `PAD(7.5)` | 8 → ERR 5 | 7 → 0 | **0** |

⇒ **truncate toward zero**, unambiguously, on both signs. (Consistent with the
float arc's F2 finding that float→int conversion truncates.)

Integer boundary:

| source | result |
|---|---|
| `STICK(32767)` | ERR 5 (in int16, out of the 0..2 domain) |
| `STICK(-32768)` | ERR 5 (idem) |
| `STICK(32768)` | **ERR 6** |
| `STICK(40000)` | **ERR 6** |

⇒ two-stage: coerce to signed int16 (outside → **Overflow, ERR 6**), then range-check
the device index (outside → **Illegal function call, ERR 5**).

Grammar:

| source | result |
|---|---|
| `STICK(0` (unclosed) | ERR 2 |
| `STICK()` | ERR 2 |
| `STICK(0)` as a statement | ERR 2 |
| `A=STICK` | ERR 2 |
| `STICK(0,1)` | ERR 2 |
| `STICK(STRIG(0)+1)` | 0 — nests normally |
| `STRIG(1)ON` | **accepted, no error** — the interrupt-trap statement form |

The last row is the arc boundary marker: `STRIG(n) ON/OFF/STOP` parses on the
reference and belongs to the **interrupt-trap** item, not here.

## Round 4 — LIVE key matrix (the gate's teeth)

KEYBUF injection bypasses the key **matrix**, so `STICK(0)`/`STRIG(0)` — which
scan the matrix — read as idle under the normal REPL driver. openMSX's
`keymatrixdown <row> <mask>` / `keymatrixup` drives the matrix directly and
**does** reach them. Program: a 600-iteration sampling loop latching any nonzero,
with the bit held down across the whole RUN window.

| held (row 8) | `STICK(0)` | `STRIG(0)` |
|---|---|---|
| nothing | 0 | 0 |
| bit 0 | 0 | **−1** |
| bit 4 | **7** | 0 |
| bit 5 | **1** | 0 |
| bit 6 | **5** | 0 |
| bit 7 | **3** | 0 |
| bits 5+6 | **0** | 0 |

⇒ row 8 = { bit0 space, bit4 left, bit5 up, bit6 down, bit7 right }; the eight-way
code is 1=up, 3=right, 5=down, 7=left, and an **opposing pair cancels to 0**.
`STRIG` is a boolean: 0 / −1.

## Round 5 — openMSX connector inventory (what the gate can plug)

```
connectors: cassetteport  joyporta  joyportb  printerport   (all empty at boot)
plug joyporta <p>:  mouse OK   trackball OK   arkanoidpad OK
                    touchpad OK   paddle OK   ninjatap OK   magic-key OK
                    joystick1 / keyjoystick1 -> "No such pluggable"
```

⇒ **`paddle` and `touchpad` exist** — `PDL`/`PAD` can be exercised against a real
plugged device. There is **no headless joystick** pluggable, so `STICK(1..2)` /
`STRIG(1..4)` can only be gated in their unplugged state (both machines idle),
with the keyboard device 0 carrying the live teeth.

## Runtime-side finding — C-BIOS (our target, not the reference)

Read from the C-BIOS **source** (`~/projects/cbios/src/main.asm`, open source, not
a reference-ROM disassembly):

| entry | C-BIOS state |
|---|---|
| `GTSTCK` `$00D5` | **real** — device 0 reads matrix row 8 through `SNSMAT` and maps it via a 16-entry table; devices 1/2 read the PSG |
| `GTTRIG` `$00D8` | **real** — space via row 8 bit 0, joystick triggers via the PSG |
| `GTPAD` `$00DB` | **STUB** — prints the debug string `"GTPAD"` and returns 0 |
| `GTPDL` `$00DE` | **STUB** — prints the debug string `"GTPDL"`, returns its own input |

The C-BIOS keyboard table reproduces the reference mapping measured in round 4
exactly (left→7, up→1, down→5, right→3, up+down→0), so `GTSTCK`/`GTTRIG` are
faithful carriers. `GTPAD`/`GTPDL` are **not usable** — they would print debug
text onto the user's screen — so `PAD`/`PDL` must read the hardware themselves.
This is what splits the arc into I1 (BIOS-backed) and I2 (direct PSG).
