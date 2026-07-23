# zerobas BASIC — input devices: `STICK` / `STRIG` / `PAD` / `PDL`

Status: **I1 LANDED 2026-07-23** (commit b8a6a5b). **I2 CHARACTERIZED and
SPECIFIED (§9), awaiting sign-off on D-I-7..D-I-10 (§10a); not implemented.**
Opened 2026-07-23, the first slice after the graphics arc concluded. Decisions in
§10 were taken as recommended, with **D-I-6** (complete the stubbed BIOS entries
rather than working around them) added on the user's call; §7 and §8 below are
rewritten **as built**. Corresponds to the `Input devices` checkbox in
[`../TODO.md`](../TODO.md) (Phase 3+).

Every `[PIN]` below is a measured black-box fact from the Philips VG-8020, with the
raw record in [`../scratchpad/i1_input_notes.md`](../scratchpad/i1_input_notes.md)
and the scripts in [`../scratchpad/i1_input_char1.py`](../scratchpad/i1_input_char1.py)
(tokens / values / coercion / grammar) and
[`../scratchpad/i1_input_char2.py`](../scratchpad/i1_input_char2.py) (live key
matrix). No reference-ROM disassembly ([memory: no-reference-rom-disasm]). The one
non-oracle source read is the **C-BIOS source** — our own runtime target, open
source, not the artifact zerobas reimplements.

---

## 1. Scope

**In:** the four device-reading functions, as *functions* only.

| surface | today |
|---|---|
| `STICK(n)` | not a keyword — `syntax error` |
| `STRIG(n)` | not a keyword — `syntax error` |
| `PDL(n)` | not a keyword — `syntax error` |
| `PAD(n)` | not a keyword — `syntax error` |

**Out, deliberately:**

* `STRIG(n) ON/OFF/STOP` and `KEY(n) ON/OFF/STOP` — the *statement* forms. The
  reference **accepts** `STRIG(1)ON` (measured, §3), so this is a real surface, but
  it is an interrupt-trap surface: it arms a trap serviced from `H.TIMI` and
  branches through `ON STRIG GOSUB`. It belongs to the **interrupt-trap** TODO item
  together with `ON SPRITE GOSUB` (which the graphics arc deferred to the same
  place). This arc must leave the grammar in a state that does not fight that one:
  see decision **D-I-5**.
* Any *writing* to these devices. They are read-only surfaces.

## 2. Slices

The arc splits in two, and the split is forced from two independent directions —
the runtime and the byte budget:

| slice | surface | carrier | why separate |
|---|---|---|---|
| **I1** | `STICK(n)`, `STRIG(n)` | C-BIOS `GTSTCK` / `GTTRIG`, as shipped | both BIOS entries are **real** in C-BIOS and their behaviour already matches the reference (§6) — small, cheap, gate-able live |
| **I2** | `PDL(n)`, `PAD(n)` | `GTPDL` / `GTPAD`, **which we supply** as new BIOS completions in the zerobas-tape page-0 patch (§6.2) | C-BIOS ships these two as debug-printing stubs, so the *BIOS* is what has to be fixed; and the fix needs its own hardware characterization against the openMSX `paddle` / `touchpad` pluggables |

Both slices therefore end up with the **same** BASIC-side shape — a thin
`call <BIOS entry>` — and the split is about *where the missing work is*, not
about two different implementation strategies.

I1 is specified in full below; **I2 in §9**, written after its characterization
round (2026-07-23) rather than ahead of it.

## 3. Tokens and grammar `[PIN]`

All four are two-byte `$FF`-prefixed **function** tokens — structurally the same
shape as `PEEK` (`$FF $97`), so they land on the existing `ev_f_ff` dispatch and
need **no** new statement token:

| keyword | token |
|---|---|
| `STICK` | `$FF $A2` |
| `STRIG` | `$FF $A3` |
| `PDL` | `$FF $A4` |
| `PAD` | `$FF $A5` |

```
A=STICK(0)          41 EF FF A2 28 11 29
A=STICK(0)+STRIG(1) 41 EF FF A2 28 11 29 F1 FF A3 28 12 29
```

Grammar — exactly one parenthesised numeric expression, nothing else:

```
    STICK ( <numeric-expr> )
    STRIG ( <numeric-expr> )
```

| form | reference |
|---|---|
| `STICK(0` (unclosed) | ERR 2 |
| `STICK()` | ERR 2 |
| `STICK(0,1)` | ERR 2 |
| `A=STICK` (no parens) | ERR 2 |
| `STICK 0` | ERR 2 |
| `STICK(0)` in statement position | ERR 2 |
| `STICK(STRIG(0)+1)` | nests normally |
| `STICK("X")` | ERR 13 (type mismatch) |
| `STRIG(1)ON` | **accepted** — the trap statement, out of scope (D-I-5) |

Every one of these ERR-2 shapes is what `ev_f_err` already produces for the
existing `$FF` functions, so the grammar costs nothing beyond the dispatch rows.

## 4. Argument coercion `[PIN]`

Two stages, in this order:

1. **Truncate toward zero to a signed int16.** Outside −32768..32767 → **ERR 6**
   (`Overflow`). Measured: `STICK(32768)` → ERR 6, `STICK(40000)` → ERR 6, while
   `STICK(32767)` and `STICK(-32768)` reach stage 2.
2. **Range-check the device index.** Outside the per-function domain → **ERR 5**
   (`Illegal function call`).

The truncation direction was pinned with discriminators chosen so that
round-half-up and truncate-toward-zero give *different verdicts*:

| source | round would give | truncate would give | measured |
|---|---|---|---|
| `PDL(0.6)` | 1 → 255 | 0 → ERR 5 | **ERR 5** |
| `PDL(12.6)` | 13 → ERR 5 | 12 → 255 | **255** |
| `STRIG(4.9)` | 5 → ERR 5 | 4 → 0 | **0** |
| `STICK(-0.6)` | −1 → ERR 5 | 0 → 0 | **0** |
| `PAD(7.5)` | 8 → ERR 5 | 7 → 0 | **0** |

⇒ **truncate toward zero, both signs** — consistent with the float arc's F2
finding that float→int conversion truncates, and with the D-F2-2 `get_byte_arg`
template already shipped.

Domains and idle values `[PIN]`:

| function | domain | ERR 5 outside | idle (nothing plugged) |
|---|---|---|---|
| `STICK` | 0..2 | `-1`, `3`, `32767`, `-32768` | 0 |
| `STRIG` | 0..4 | `-1`, `5` | 0 |
| `PDL` | 1..12 | `0`, `13` | **255** |
| `PAD` | 0..7 | `-1`, `8` | 0 |

Note `PDL`'s domain **starts at 1**, and its idle value is 255, not 0 — the two
places this family is least guessable, and both are gated.

## 5. Semantics `[PIN]`

### 5.1 `STICK(n)` — eight-way direction, 0 = centred

`n` = 0 keyboard cursor keys, 1 = joystick port 1, 2 = joystick port 2. The result
is an integer 0..8: 0 = centred, then 1..8 clockwise from up. Measured live against
the key matrix (row 8 held down across the RUN):

| held (row 8) | `STICK(0)` |
|---|---|
| nothing | 0 |
| bit 4 (left) | 7 |
| bit 5 (up) | 1 |
| bit 6 (down) | 5 |
| bit 7 (right) | 3 |
| bits 5+6 (up+down) | **0** — an opposing pair cancels |

### 5.2 `STRIG(n)` — boolean trigger, 0 or −1

`n` = 0 the space bar, 1/2 = button A of port 1/2, 3/4 = button B of port 1/2.
Result is **0** (not pressed) or **−1** (pressed) — the BASIC truth convention, not
the BIOS's `$00`/`$FF` byte. Measured: holding row 8 bit 0 (space) gives
`STRIG(0)` = −1 while `STICK(0)` stays 0.

The `$FF`→`-1` widening is free in the implementation: `GTTRIG` returns `$00`/`$FF`
in A, and copying A into **both** halves of the int16 result yields exactly
`$0000` / `$FFFF`.

## 6. Runtime carrier — the BIOS, for all four

### 6.1 What C-BIOS actually ships

Read from the C-BIOS **source** (`~/projects/cbios/src/main.asm`):

| entry | C-BIOS state |
|---|---|
| `GTSTCK` `$00D5` | **real** — device 0 reads matrix row 8 via `SNSMAT` and maps it through a 16-entry table; devices 1/2 read the PSG |
| `GTTRIG` `$00D8` | **real** — space via row 8 bit 0, joystick triggers via the PSG |
| `GTPAD` `$00DB` | **STUB** — prints the debug string `"GTPAD"`, returns 0 |
| `GTPDL` `$00DE` | **STUB** — prints the debug string `"GTPDL"`, returns its own input |

C-BIOS's keyboard direction table reproduces the reference mapping measured in
§5.1 *exactly* (left→7, up→1, down→5, right→3, opposing pair→0), and its
joystick-port path is fully implemented too (PSG R15 port select → R14 read →
table map). So `GTSTCK`/`GTTRIG` are faithful carriers and I1 is a thin wrapper.

`GTPAD`/`GTPDL` are not merely inaccurate, they are **actively harmful**: they
`CHPUT` debug text onto the user's screen.

Unlike the graphics tenant, this code runs in **ordinary resident context** with
page 0 = BIOS, so a plain `call GTSTCK` is available (the same footing as
`INKEY$`'s `CHSNS`/`CHGET`). No trampoline, no direct-port workaround.

### 6.2 `GTPAD`/`GTPDL` — fix them in the BIOS, not in BASIC

The first draft of this spec had `PAD`/`PDL` read the PSG *from inside
`basic.rom`*, working around the stubs. That is the wrong placement. The right
fix is to **complete the two stubbed BIOS entries** in the zerobas-tape page-0
patch, which is exactly the component that exists for this
([`../tape/DESIGN.md`](../tape/DESIGN.md) "Scope"). All three admission criteria
hold, and not marginally:

| criterion | `GTPAD` `$00DB` / `GTPDL` `$00DE` |
|---|---|
| 1. a missing/stubbed C-BIOS page-0 BIOS entry, so filling it in serves *any* caller | ✅ literal stubs at standard `$00xx` jump-table vectors — a real MSX BASIC or a DOS program on our runtime is just as broken by them as we are |
| 2. small — too small for its own component | ✅ ~50–70 B each: a PSG register select plus a read/count loop |
| 3. fits the spare page-0 fill the patch already owns | ✅ **322 B free**, measured (below) |

Measured spare fill, all four C-BIOS MSX1 main variants (`msx1`, `_br`, `_eu`,
`_jp`) identically:

```
zero-fill region   $09EE .. $0D00   = 787 B
used by zerobas-tape ($09EE..tape_end $0BBF) = 465 B
FREE                                          = 322 B
```

Three further arguments for this placement, beyond it being the documented home:

1. **Faithfulness.** On a real MSX, `PDL`/`PAD` *are* BIOS routines that BASIC
   calls; the platform split puts the device read in the BIOS. Reading the PSG
   from inside `basic.rom` would reproduce the *behaviour* while diverging on the
   *placement* — the same mistake Phase 1.5 was written to correct on the disk
   side, where zerobas had copied the placement but swapped the protocol.
2. **Provenance fit.** zerobas-tape already reads the PSG through ports
   `$A0`/`$A2` from the AY-3-8910 datasheet (`; CAS-in is PSG R14 bit 7`), so the
   paddle read lands in a component whose allowed-source set and provenance log
   already cover exactly this hardware.
3. **Space.** 322 B of patch fill against 6 B of page-1 `basic.rom` — the whole I2
   body cost moves off the constrained budget onto an unconstrained one.

This was in fact anticipated by the project's own space strategy:
[`decision-phase3-space-strategy.md:107`](decision-phase3-space-strategy.md:107)
sizes input devices as "thin wrappers **(+ possible tape-component BIOS
completions)**". This spec now takes that option.

The cost of the choice, stated plainly: I2 becomes a **two-component** slice
(`tape/` for the routines + their provenance rows and scope entry, `basic/` for
the wrapper), so it carries the tape component's build/verify wiring — the IPS
must be re-forged and the `$00DB`/`$00DE` vector rewrites added to the three
patched regions, which `tools/build_patches.py` verifies across all C-BIOS main
ROMs. That is real extra work; it is worth it for a fix that is correct rather
than merely local. *(Offering the routines upstream to C-BIOS is a separate,
later question — the patch stays the shipping mechanism either way, since
[`../tape/DESIGN.md`](../tape/DESIGN.md) keeps our code out of the C-BIOS source
tree deliberately, as a legal firewall.)*

## 7. Space — the binding constraint

Measured on the current build (`tools/check_reloc.py`, at 45090f5):

```
page-0 low region free = 19 B   ($2812-$3FFF, __MEAS_LOW_END @ $3FED)
page-1 free            =  6 B   ($4000-$7FFF, __MEAS_PAGE1_END @ $7FFA)
```

As-built I1 cost and the funding, measured:

| item | region | as built |
|---|---|---|
| `kwtable` rows `STICK` + `STRIG` | — | **0 B resident**: the repack build's keyword table is wholly SUB-side since the wave-3 detokeniser eviction, so keyword rows cost sub-ROM bytes, not page-1 or low-region ones. (The draft budgeted 18 B of low region for these; that was wrong, and the low region is untouched at 19 B free.) |
| dispatch rows, domain check, the two bodies | page 1 | **56 B** |
| **deficit against the 6 B free** | page 1 | **50 B** (58 B before the golf) |

Funding, in the order §7 predicted:

1. **The `ev_f_ff` dispatch golf paid first, as expected** — the per-token
   `cp`/`jr z` chain became a `cpir` set test over a selector table, taking a
   function's dispatch cost from 4 B to 1 B. Measured yield **+8 B** with I1's own
   two rows already in it (`__MEAS_PAGE1_END` $803A → $802C). It had to be gated
   repack-only: the first cut changed the **lean** `basic.rom`, which is
   byte-frozen, and `check_reloc.py` caught that immediately.
2. **A scouted carve closed the rest** — `ex_beep` + `beep_delay` (71 B) →
   `sub/beep.asm`, a new page-0 tenant (`SUBROM_IDX_BEEP` = 11), stub cost ~12 B.
   Taken over the two 130 B candidates (`psv_fetch`/`psv_env`) exactly as §7
   argued: those are PLAY-servicer halves running from `H.TIMI`, and a CALSLT
   inside the VBLANK handler is not a trade worth making for a 50 B need.
   BEEP qualifies on every count — cold (one CALSLT against a ~33 ms tone),
   transitively page-0 clean (PSG ports + a busy-wait; the automated closure
   checker now verifies this), and its reference-faithful `ei` across the delay is
   safe *because* the sub-ROM owns its own page-0 `$0038` trampoline.

One structural consequence: with index 11 the page-0 entry table reached the
`$0038` interrupt vector, so `sub_p0_ping`'s body moved below it (it is reached
only through its own `jp` row, so its address is immaterial). **The page-0 table
is now within 4 bytes of that ceiling — the next page-0 tenant will have to
restructure the $0010..$0037 window, and that is a real constraint on the next
eviction, not a detail.**

Final: **page-1 free 6 B → 17 B**, low region unchanged at 19 B, lean
`basic.rom` byte-identical.

## 8. Gate — as built

`make input-devices-acceptance`
([`../probes/basic/basic_probe_input_devices.py`](../probes/basic/basic_probe_input_devices.py)),
differential VG-8020 vs `C-BIOS_MSX1_EU_REPACK_DISK`, **31/31 PASS**:

* **Phase A — grammar, errors, coercion (22 cases).** The §3 table plus the §4
  discriminators, each trapped by `ON ERROR` and compared on the error NUMBER.
  The discriminator rows are the ones with teeth: `STRIG(4.9)` is legal only
  under truncation, so a regression to round-half-up fails the phase.
* **Phase B — idle values (2 cases).**
* **Phase C — LIVE key matrix (7 cases): the teeth.** Phases A and B pass just as
  well against a function returning a constant 0, because with nothing plugged
  idle *is* 0. Phase C holds a row-8 bit down across a sampling RUN and compares
  what the functions actually read; both machines reproduce the §5.1 mapping
  (space → −1, left 7, up 1, down 5, right 3, up+down 0).

**Harness addition (D-I-3), as built:** `omsx_repl` gained per-case
`holds=[(row, mask) | None]` + `hold_secs`, scheduling `keymatrixdown` at the RUN
slot and `keymatrixup` before the capture. Reusable by the interrupt-trap arc's
`ON KEY`/`ON STRIG`.

**Two false-green probe bugs were found and fixed while building this gate**, both
of the arc's recurring class:

1. The outcome regex matched the tag inside the **echoed source line**, so all 31
   cases "passed" while extracting no output at all. The extractor now anchors
   after the last `RUN` and takes the last non-bare match (an aborting case prints
   its tag twice — once from the failing statement, once from the handler).
2. Phase C's first timing let the sampling loop finish **before** the key went
   down. Sizing that loop is genuinely two-sided: it must still be running 0.3 s
   after RUN on the fast machine and must finish before the capture on the slow
   one, and a STICK/STRIG iteration is expensive (~10 iterations per emulated
   second, two matrix-scanning BIOS calls each), so 60 iterations is the window
   that holds on both. Phase C also runs boot-per-case: a held matrix bit is
   exactly the state that could leak into the next case's line entry, and this is
   the one phase whose result must not be explainable by contamination.

The **crunch corpus** gained `STICK`/`STRIG` rows plus `STEP`/`STOP`/`STR$` rows
that would catch a keyword-prefix collision (all byte-identical to the reference).
Host layer: `tests/test_beep.py` retargeted at `beep_tenant`, and `tests/z80.py`
gained `CPI`/`CPIR` — the golf's `cpir` was an unimplemented opcode, which the
host core reported loudly with the exact PC and byte, as it is designed to.

**Residual fixed in passing (not input-devices).** The Phase-A differential caught
that a **missing argument list** evaluated silently to 0 where the reference
raises ERR 2 — `PRINT PEEK`, `PEEK 100`, and likewise `VPEEK`/`INP`/`EOF`/`LOF`.
A pre-existing divergence across the whole `ev_ff_arg` family, not something the
new functions introduced; both paren checks now defer through `ev_f_empty` (the
cure `CVI` already carried). Byte-neutral, repack-only.

## 9. I2 — `PDL(n)` / `PAD(n)`, specified

**Status: characterization round COMPLETE (2026-07-23, commits 1fe02d2 → 559e15d);
this section is the spec, FOR SIGN-OFF. Nothing is implemented.** The raw record
is [`../scratchpad/i2_input_notes.md`](../scratchpad/i2_input_notes.md), with
probes [`i2_char.py`](../scratchpad/i2_char.py) (the value matrix),
[`i2_pinmap.py`](../scratchpad/i2_pinmap.py) (BASIC-speed terminal identity) and
[`i2_frame.py`](../scratchpad/i2_frame.py) (the Z80-speed bit-bang harness).

Grammar (§3), coercion (§4) and the domains/idle values (§4, `PDL` 1..12 idle
255; `PAD` 0..7 idle 0) were already pinned during I1 and are **unchanged** — I2
adds no new BASIC-visible surface beyond the two functions themselves.

### 9.1 What the characterization established

1. **`PDL`'s index→port mapping**, settled twice and independently: black-box
   (the port-A and port-B value columns mirror exactly under `n ↔ n+1`) and from
   the TH's published circuit (R14 b0..b5 = terminals 1,2,3,4,6,7 of the port
   selected by R15 b6 ⇒ six paddles per port). ⇒ **odd `n` = joystick port 1,
   even `n` = port 2; the paddle within the port is `(n+1) >> 1`, read on
   R14 bit `((n+1) >> 1) − 1`.**
2. **The paddle protocol** (TH §5.3, fig. 5.24): pulse the 8th terminal, an
   LS123-compatible one-shot answers on the data terminal for **10 µs..3 ms**;
   measure the length. 3 ms ÷ 255 ≈ **11.8 µs per count**, capping at 255.
3. **The touch-panel protocol** is the **NEC µPD7001** serial ADC's, from the
   manufacturer data book (§4.4 of the record): 2 address bits in on `SI` latched
   by `DL`, conversion starts on the **rise of `CS`**, data exchanged while `CS`
   is **low**, 8 result bits out MSB-first on open-drain `SO` clocked by `SCK`,
   `EOC` low during conversion, `t_CONV = 14 × 4 / f_CK`.
4. **The terminal mapping**, recovered from our own oracle with the paddle run
   first as a known-answer control:

   | terminal | bit | µPD7001 signal | basis |
   |---|---|---|---|
   | 8th | R15 b4 (port 1) / b5 (port 2), **output** | `CS`/`SCK` | the only output the port has |
   | 3 | R14 b2 | `SO` | follows the driven line |
   | 2 | R14 b1 | `EOC` | low for a fixed ~124 µs after clocking stops, independent of clock count, against `t_CONV` 140 µs typ |

### 9.2 BIOS side — the two routines, in the zerobas-tape page-0 patch

Per **D-I-6** (already signed off). Both are ordinary page-0 code; the patch has
**322 B free** and these are ~60–80 B each.

**`GTPDL` `$00DE`** — in A = 1..12, out A = 0..255:

```
    port   = 1 + ((n - 1) & 1)          ; odd n -> port 1, even n -> port 2
    paddle = (n + 1) >> 1               ; 1..6
    mask   = 1 << (paddle - 1)          ; the R14 bit to watch
    select port via R15 b6; pulse that port's 8th terminal (R15 b4 / b5)
    count = 0
    repeat: if (R14 & mask) is inactive -> return count
            count += 1; if count = 255 -> return 255
```

The **count loop must be paced at ≈11.8 µs per iteration** (~42 T at 3.58 MHz) so
that the 10 µs..3 ms one-shot maps onto 0..255. Polarity and the exact pacing are
*pinned by the gate*, not asserted here: nothing-plugged must yield **255** and a
plugged openMSX paddle must yield **128** (§9.4). That is deliberate — those two
numbers are a sharper specification of the loop than prose about which edge is
active, and a timing error fails them.

**`GTPAD` `$00DB`** — in A = 0..19, out A = the TH's table. MSX1 BASIC only ever
passes 0..7 (§4); the wider BIOS surface is real but out of this arc's scope, and
ids 8..19 (light pen, mouse/trackball) return 0.

```
    device = A >> 2                     ; 0 = touch panel 1, 1 = touch panel 2
    sub    = A & 3                      ; 0 sense, 1 X, 2 Y, 3 button
    sub 0: run a conversion; latch X and Y; return $FF if touched else $00
    sub 1: return the latched X    (uPD7001 channel 0)
    sub 2: return the latched Y    (uPD7001 channel 3)
    sub 3: return $FF if the button is pressed else $00
```

The sense call is the one that talks to the chip; 1/2/3 read what it latched.
That is the TH's own published calling sequence (List 5.8: sense with A=0, and
the coordinates are meaningful only once it returned `$FF`), so the latch is
required behaviour, not an optimisation.

### 9.3 BASIC side — two thin wrappers

Same shape as I1: two `ev_f_ff` dispatch rows, the shared `get_byte_arg` coercion
(§4), the domain check (`PDL` 1..12, `PAD` 0..7 ⇒ ERR 5), then `call $00DE` /
`call $00DB`. Keyword rows cost **sub-ROM** bytes, not resident ones (the §7
as-built correction).

One asymmetry: **`PDL` always zero-extends** its 0..255 result, but **`PAD`'s
result width depends on the index** — ids 0 and 3 (and their port-2 mirrors 4 and
7) are booleans that the BIOS returns as `$00`/`$FF`, so BASIC widens them to
`0`/`-1` exactly as `STRIG` does (§5.2), while ids 1/2/5/6 are coordinates that
zero-extend. **Measured `[PIN]`**, with `arkanoidpad` plugged: `PAD(0)` = **−1**
while `PAD(1)`/`PAD(2)` = **255** (record §3.2). An earlier draft carried this as
an inference needing a doc lookup; it is now a reference measurement, and D-I-8
is closed.

### 9.4 Gate

Extends `make input-devices-acceptance` with two phases, both differential
against the VG-8020:

* **Phase D — `PDL` values, with devices plugged. THE TEETH.** The whole 1..12
  matrix under four configurations (paddle in A / in B, touchpad in A / in B),
  asserting the §9.1 table: `128` for the plugged paddle's index, `0` for the two
  touchpad-shadowed indices, `255` elsewhere. A constant cannot fake this, and
  the `128` additionally pins the count *rate*.
* **Phase E — `PAD` values, with devices plugged. ALSO TEETH.** The 0..7 matrix
  under `arkanoidpad` in port A and in port B, asserting the record's §3.2 table:
  sense = **−1** on the populated port's index, X/Y = **255**, button = 0, and the
  whole thing mirroring between indices 0..3 and 4..7. A constant-0 `PAD` fails
  this immediately. Plus the ERR 5 / ERR 6 edges.

  *Corrects an earlier draft of this spec*, which said Phase E could only ever be
  gated idle. That was measured against `touchpad` alone — the device the TH's
  table names for ids 0..3 — and the other joyport pluggables were never tried
  against `PAD`. `arkanoidpad` drives the surface without needing any host input,
  so no `PAD` limitation on the user's decision to keep it in I2 survives.

**What Phase E still cannot do** is tell the X channel from the Y channel:
`PAD(1)` and `PAD(2)` both read 255, so the µPD7001 **address phase** is
undiscriminated. The teeth bite on the sub-function dispatch and on the
`$FF`→`-1` widening, not on channel selection — which is what keeps D-I-7 open,
in a narrower form than before.

Harness prerequisite: `omsx_repl` needs a **per-batch Tcl prologue** hook so a
gate can `plug` a device. The characterization probes monkey-patched `_tcl`, which
is fine for scratch and not for a standing gate. The interrupt-trap arc will want
the same seam.

### 9.5 Space — MEASURED, not estimated

Baseline (`tools/check_reloc.py`): **page-1 free = 17 B**, low region free = 19 B.

The draft of this section estimated the BASIC-side cost at ~60 B ⇒ a ~43 B
deficit. **That estimate was low.** The wrappers were written, built and measured,
then reverted (nothing is implemented — the measurement is the deliverable):

```
__MEAS_PAGE1_END   $7FEF  baseline        (17 B free under the $8000 ceiling)
                   $8037  with I2         (overran the ceiling by $37)
                   -----
I2 resident cost    $48 = 72 B      ⇒ DEFICIT = 55 B
```

So **72 B, and a 55 B deficit** — the estimate was ~12 B light, which is exactly
why the arc's standing lesson is to measure a byte budget rather than reason about
one. The BIOS bodies themselves still cost nothing here; they live in the tape
patch's 322 B of free fill.

Three of those bytes are landmine tax, and the landmine is the one I1 already
recorded: **a mid-file insert splits page-1 forward `jr`s**. Adding I2's dispatch
and domain rows pushed `ev_ff_dskf` out of its `jr`'s reach, and moving the two
new bodies to the dispatch *tail* (the documented cure) then put them out of reach
of their own `jr`s. The shape that assembles is: bodies at the tail, `jp` to
reach them, and a `ROM_BASE`-conditional `jp` for `DSKF` so the frozen lean
`basic.rom` keeps its `jr` and stays byte-identical. Worth knowing before the
implementation session rediscovers it.

**A carve is therefore required, and it is a bigger one than I1's.** I1 funded
56 B from a dispatch golf (+8 B) plus evicting `BEEP` (~59 B net). 55 B is the
same order, so the `g6_carve_scout.py` tenancy rule should find a candidate — but
this is now a known cost to plan against, not a surprise to hit mid-slice.

### 9.6 Implementation order (after sign-off)

1. ~~`omsx_repl` prologue hook~~ — **✅ DONE (1bce384)**, validated by reproducing
   three known results through it (including a nothing-plugged negative control,
   which is what proves the prologue takes effect rather than being ignored).
2. ~~Measure the real BASIC-side cost~~ — **✅ DONE: 72 B, 55 B deficit (§9.5).**
   Next actual step: **scout the carve** (`g6_carve_scout.py`).
3. The two `tape/` routines + `tape/PROVENANCE.md` rows + `tape/DESIGN.md` scope
   entry; re-forge the IPS/BPS with the `$00DB`/`$00DE` vector rewrites; verify
   across all four C-BIOS MSX1 main ROMs (`tools/build_patches.py`).
4. The BASIC-side wrappers; host unit tests.
5. Phases D and E; then the full standing-gate battery (lean `basic.rom` must
   stay byte-identical).
6. Provenance, TODO, and this section rewritten as-built.

## 10. Decisions — FOR SIGN-OFF

### 10a. I2 decisions (new, 2026-07-23)

* **D-I-7 — how far to reconstruct `GTPAD`.** The µPD7001 datasheet plus the
  recovered terminal mapping specify the *handshake*; what is **not** pinned is
  how the two channel-address bits (`SI`, latched by `DL`) reach the chip through
  a port that offers exactly **one** output line. The encoding must be temporal,
  and nothing measured so far constrains it. Three ways forward:
  1. **Another characterization round** aimed at the address phase — vary the
     pulse widths and inter-pulse gaps on the 8th terminal and look for the
     pattern that selects a different channel.
  2. **Implement channel 0 (X) only** and return the Y sub-function as 0,
     documented.
  3. **Implement the handshake and accept an unvalidated address phase.**

  *Recommend: (3), with (1) only if it falls out cheaply.* **This reverses an
  earlier recommendation of (1)**, on two grounds that emerged after it was
  written. First, (1) has no observable to work with: distinguishing channels
  requires the channels to *differ*, and every reachable channel reads the same —
  0 on an untouched panel, 255 on both `PAD(1)` and `PAD(2)` with `arkanoidpad`.
  `EOC` firing tells us a conversion happened, never which channel it converted.
  So the experiment cannot answer the question, and pursuing it would be exactly
  the probe-loop grind [memory: harness-first-investigation-mo] warns against.
  Second, the risk (3) carries is now much smaller than it was: Phase E gives the
  whole `GTPAD` surface a real differential (§9.4), so any divergence outside the
  channel address is caught. The residual is narrow and should be **recorded as a
  documented deviation** rather than chased.
* **D-I-8 — `PAD`'s boolean widening. ✅ CLOSED 2026-07-23, no decision needed.**
  It was raised as an inference the differential could not check. Plugging
  `arkanoidpad` measures it directly: `PAD(0)` = **−1**, `PAD(1)`/`PAD(2)` =
  **255** (record §3.2). The widening is a `[PIN]` and the doc lookup is moot.
* **D-I-9 — `PDL`'s count loop is specified by its GATE, not by prose.** §9.2
  gives the algorithm structurally and pins the timing with two measured numbers
  (idle → 255, plugged paddle → 128) rather than asserting an active polarity or
  a T-state count. *Recommend: accept* — the numbers are strictly stronger than
  the prose would be, they came from the reference, and a pacing error fails them
  loudly. The cost is that the implementer must iterate against the gate rather
  than code straight from the spec.
* **D-I-10 — keep `PAD` in I2. ✅ Its objection has evaporated.** The decision was
  taken (user, 2026-07-23) when `PAD` looked un-gateable, and was then re-examined
  on the question of whether openMSX supports the pad well enough to bother. The
  answer is that it does — via `arkanoidpad`, not `touchpad` — so `PAD` ships with
  a differential that has teeth, and the "green gate ≠ validated behaviour"
  caveat now applies only to the channel address (D-I-7), not to the verb.
  *Recommend: accept, with the narrow D-I-7 deviation documented in
  `tape/PROVENANCE.md`.*

### 10b. I1 decisions (settled, 2026-07-23)

* **D-I-6 — complete the stubbed BIOS entries rather than working around them.**
  `GTPAD` `$00DB` / `GTPDL` `$00DE` get real implementations in the zerobas-tape
  page-0 patch; `PDL`/`PAD` in BASIC then become thin `call` wrappers like
  `STICK`/`STRIG`. *Recommend: accept* — it meets all three of the component's
  admission criteria with 322 B of measured room, it is the faithful placement
  (on a real MSX these *are* BIOS routines), it serves every caller on our runtime
  rather than only our interpreter, and it moves I2's body cost off the 6-byte
  page-1 budget entirely. Cost: I2 becomes a two-component slice with the tape
  patch's re-forge/verify wiring (§6.2). **This supersedes the first draft's
  direct-PSG-inside-basic.rom plan** (user's call, 2026-07-23).
* **D-I-1 — slice split.** I1 = `STICK`/`STRIG`; I2 = `PDL`/`PAD`, separately
  characterized and specified. *Recommend: accept* — note that under D-I-6 the
  split is no longer *forced* by the runtime (both slices are BIOS-backed now); it
  survives on the two remaining grounds: I2 needs its own hardware
  characterization round, and it spans a second component.
* **D-I-2 — BIOS carrier for I1.** Use `GTSTCK`/`GTTRIG` as C-BIOS ships them,
  rather than reading the matrix/PSG ourselves. *Recommend: accept* — measured
  faithful (§6.1), including the joystick-port path, and ~10× cheaper
  in bytes than an own-design read at a moment when page 1 has 6 B free. The
  counter-argument is the project's usual preference for not depending on BIOS
  behaviour; it is weaker here because the entries are published MSX contracts and
  C-BIOS implements them correctly, and because the differential gate would catch
  any drift.
* **D-I-3 — harness addition.** Add scheduled key-matrix hold/release to
  `probes/lib/omsx_repl.py`. *Recommend: accept* — without it the gate has no
  teeth (it can only prove idle values), and the interrupt-trap arc needs the same
  capability for `ON KEY`.
* **D-I-4 — funding order.** Try the `ev_f_ff` dispatch golf first; fall back to a
  scouted carve only if it under-delivers; do not evict interrupt-context PLAY
  servicer code for a ~47 B need. *Recommend: accept.*
* **D-I-5 — trap-statement boundary.** `STRIG(n) ON/OFF/STOP` stays out of this
  arc. The reference accepts it; after I1, zerobas will raise ERR 2 for it —
  a **new documented divergence**, closed by the interrupt-trap arc.
  *Alternative:* accept-and-ignore it as a no-op now (the G7 precedent for
  `SPRITE ON|OFF|STOP`), which removes the divergence at the cost of silently
  accepting a statement that does nothing. *Recommend: the divergence* — a trap
  that silently never fires is worse than a clean syntax error, and G7's no-op was
  justified by sprites having no trap semantics to fake. **This one is a genuine
  judgment call and the one I would most like a second opinion on.**

## 11. Implementation order (I1, after sign-off)

1. Measure option 1 of §7 (dispatch golf) — the real number, before any carve.
2. Harness: key-matrix actions in `omsx_repl` (D-I-3), self-tested against the
   reference by reproducing the §5.1 table.
3. `kwtable` rows + `ev_f_ff` dispatch + domain check + the two bodies.
4. Host unit test; then the four-phase gate; then `make` the full standing-gate
   battery (lean `basic.rom` must stay byte-identical).
5. Provenance (`basic/PROVENANCE.md` → "Phase 3: input devices"), TODO, and this
   spec's §7 rewritten as-built.

I2 additionally: characterize the pluggables → write the `tape/` routines with
their `tape/PROVENANCE.md` rows and `tape/DESIGN.md` scope entry → re-forge the
IPS/BPS with the two new vector regions → verify across all C-BIOS main ROMs →
then the BASIC-side wrapper.
