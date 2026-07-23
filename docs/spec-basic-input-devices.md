# zerobas BASIC — input devices: `STICK` / `STRIG` / `PAD` / `PDL`

Status: **DRAFT — awaiting sign-off.** Opened 2026-07-23, the first slice after the
graphics arc concluded. Corresponds to the `Input devices` checkbox in
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

I1 is specified in full below. I2 is scoped in §9 and gets its own spec addendum
after its characterization round — writing it now would be speculation about
hardware behaviour we have not yet measured.

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

Estimated I1 cost:

| item | region | est. |
|---|---|---|
| `kwtable` rows `STICK` + `STRIG` (`[len][chars][tlen][$FF][tok]`) | low region | 18 B |
| 2 × `cp TOK / jr z,ev_ff_arg` dispatch rows | page 1 | 8 B |
| domain check (selector → max, then the existing `gb_illegal`) | page 1 | ~15 B |
| `STICK` body (`ld a,e` / `call GTSTCK` / `ld e,a` / `ld d,0` / `ret`) | page 1 | ~9 B |
| `STRIG` body (A into both halves) | page 1 | ~7 B |
| read-dispatch rows | page 1 | ~8 B |
| **total** | | **~18 B low + ~47 B page 1** |

The low-region rows fit in the 19 B available with 1 B to spare; the **page-1 side
needs ≈45 B of relief it does not have**. This is a small deficit by this project's
standards (G6 closed 239 B, G7 closed 388 B), and the coercion machinery it leans
on already exists — `get_int16_checked` / `get_byte_arg` / `gb_illegal`
([`../basic/interp.asm:1248`](../basic/interp.asm:1248)), shipped by the D-F2-2
int-arg arc — so the estimate above is mostly dispatch rows, not new logic.

Funding options, in the order I would try them (decision **D-I-4**):

1. **Golf / DRY inside the `ev_f_ff` block.** The dispatch is nine sequential
   `cp`/`jr z` pairs plus a second nine-way read dispatch on the same selector;
   collapsing the two into one table-driven walk plausibly *frees* more than I1
   spends. This is the self-funding path and it is the one the arc should try
   first — G8 funded itself the same way.
2. **A scouted carve.** `scratchpad/g7_carve_scout.py 120` shortlists two clean
   single-entry page-0-tenant carves at 130 B: `psv_fetch` and `psv_env` (the PLAY
   servicer's fetch/envelope halves). Both are **interrupt-context** code — the
   servicer runs from `H.TIMI` — so evicting them puts a `CALSLT` inside the
   VBLANK handler. That is a real risk to the audio arc's timing and should not be
   taken for a 47 B need if option 1 works.
3. **A page-1 sub-ROM tenant for the two bodies.** Reach is correct — a *page-1*
   tenant sees the BIOS, so it may call `GTSTCK` — but a `subrom_call` stub costs
   about as much as the ~16 B of body it would move. Not worth it for I1 alone;
   revisit for I2, whose direct-PSG bodies are genuinely larger.

**Measure before committing** ([memory: dont-prematurely-wall]) — option 1's actual
yield gets measured empirically as step 1 of implementation, before any carve is
cut.

## 8. Gate

New standing gate `make input-devices-acceptance`
(`probes/basic/basic_probe_input_devices.py`), differential VG-8020 vs
`C-BIOS_MSX1_EU_REPACK_DISK`, in four phases:

* **Phase A — grammar and errors.** The §3 table plus the §4 coercion
  discriminators, each as a trapped `ON ERROR` case comparing the error number.
  ~25 cases, batched.
* **Phase B — idle values.** Every legal index of both functions with nothing
  plugged; asserts the exact idle values of §4 (this is where `PDL`'s 255 and
  domain-from-1 land in I2).
* **Phase C — LIVE key matrix (the teeth).** The load-bearing phase. Holds each
  row-8 bit down across a sampling RUN and compares `STICK(0)` / `STRIG(0)`
  between the machines — the only phase that proves anything is actually being
  *read*. Proven feasible: openMSX `keymatrixdown` / `keymatrixup` reach the
  matrix, which KEYBUF injection does not. Requires a **harness addition** —
  `omsx_repl` gains scheduled key-matrix hold/release actions (decision
  **D-I-3**); that capability is reusable by the interrupt-trap arc's `ON KEY`.
* **Phase D — plugged devices (I2).** `plug joyporta paddle` / `touchpad`. Both
  pluggables exist in this openMSX build; there is **no** headless joystick
  pluggable, so `STICK(1..2)` / `STRIG(1..4)` are gated idle-only and device 0
  carries the live teeth. This limit is a documented gate boundary, not a silent
  gap.

Plus a host unit test (`tests/test_input_devices.py`) for the domain/coercion
decision table, per the usual two-layer discipline.

## 9. I2 sketch (not yet specified)

Placement is now settled (§6.2): the routines go in the zerobas-tape page-0 patch
behind the real `$00DB`/`$00DE` vectors, and `basic.rom` gains only two more
dispatch rows plus two `kwtable` rows (~14 B low region + ~20 B page 1 — the
low-region rows are the tighter half and may need a few bytes of relief there).

To be characterized before I2 is written: the `paddle`/`touchpad` pluggables'
behaviour, whether a paddle value can be *driven* headlessly or only plugged, the
PSG R14/R15 pulse-and-count protocol from the AY-3-8910 datasheet + MSX Technical
Data Book, and the `PAD(n)` sub-function meaning per index (0 = connected status,
1/2 = x/y, 3 = touch, for port 1; 4..7 the port-2 mirror). The differential then
has a second axis the other slices lack: the routine under test is in the *BIOS*,
so it can also be exercised without BASIC at all.

## 10. Decisions — FOR SIGN-OFF

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
