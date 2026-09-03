# Spec — MSX1 graphics arc (`SCREEN 2` geometry engine + sprites)

**Status: DRAFT — SIGN-OFF NEEDED (2026-07-21).** This is the *arc* spec; each
slice lands as a signed-off addendum (the pattern
[`spec-basic-audio-play.md`](spec-basic-audio-play.md) →
[`spec-basic-audio-play-slice2a.md`](spec-basic-audio-play-slice2a.md) used). No
asm is written until the crux decisions in §2–§4 and the sign-off table in §10 are
approved. Every faithfulness fact marked **[PIN]** is characterised black-box
against the Philips VG-8020 before it is asserted in code — the recurring arc
lesson ([memory: error-handling-arc]) applies with force here, because a green
build can hide a wrong pixel just as easily as a dead trap branch.

**Crux decisions D1/D2/D4 SIGNED OFF (2026-07-21).** The §11 VG-8020 characterization
is complete — every arc-level `[PIN]` is now a measured fact (tokens, base tables,
color-clash rule, clip/error, work-area addresses, interrupts-live-during-draw). Two
corrections it forced are folded in: the §4 pixel-address formula, and the removal of
graphics `GET`/`PUT` (Syntax error on MSX1). Next artifact: the **G1 slice spec**.

Reconnaissance basis (2026-07-21): nothing beyond `SCREEN`/`COLOR`/`CLS`/`WIDTH`/
`VPOKE`/`VPEEK`/`OUT`/`INP`/`BASE` exists ([basic/screen.asm](basic/screen.asm),
[basic/vdpio.asm](basic/vdpio.asm)); resident main ROM is effectively full (0–3 B
free on page 1); sub-ROM has ~9.5 KB free on page 0 and ~7 KB on page 1; VRAM
access today is stateless per-byte BIOS `WRTVRM`/`RDVRM` with **no shared cursor**
to straddle.

---

## 0. Why this needs its own spec + provenance boundary

Graphics is the largest remaining Phase-3 charter item ([../TODO.md:3059 (T-BDB99C)](TODO.md))
and the first arc whose runtime is **compute-heavy and long-running** (a full-screen
`PAINT` is milliseconds-to-seconds of work), which collides directly with the live
`PLAY` servicer we just landed ([basic/playsvc.asm:67](basic/playsvc.asm)). The
interrupt-discipline decision (§2) is unlike any prior tenant and must be pinned
before code.

**Provenance (allowed sources only, [memory: no-reference-rom-disasm]):**
- Statement *semantics* (what `LINE`/`CIRCLE`/`PAINT`/`DRAW` do) — public MSX-BASIC
  language reference.
- VDP register/port contract, `SCREEN 2` VRAM table layout, direct port I/O
  ($98 data / $99 addr-reg) — **TMS9918A datasheet** + MSX2 Technical Handbook VDP
  chapter (published hardware contract; already the basis for `OUT`/`INP` and cited
  clean for the V9990 idea [memory: v9990-basic-extension-idea]).
- Graphics work-area addresses (last-referenced point, `ATRBAS`/`PATBAS`, `CLOC`/
  `CMASK`, …) — MSX2 TH work-area appendix / MSX Assembly Page, **cross-checked
  black-box** against VG-8020 work-area RAM (same discipline as `FORCLR` et al.,
  [basic/sysvars.inc:99](basic/sysvars.inc:99)).
- Bresenham, the circle midpoint rasteriser, the flood-fill, and the `DRAW` packet
  encoding — **own-design, host-validated**; never lifted from a stock ROM.
- Every token value — black-box VG-8020 crunch capture (§8), never asserted from
  memory (the `SOUND`-token `$C2`-guess-was-wrong lesson,
  [basic/sysvars.inc:362](basic/sysvars.inc)).

---

## 1. Scope + slice plan

**In arc:** the `SCREEN 2` (256×192, TMS9918 GRAPHIC-2) drawing surface and the
statements that write it: `PSET`, `PRESET`, `POINT` (fn), `LINE` (incl. `,B`/`,BF`
box forms), `CIRCLE`, `PAINT`, `DRAW`, and sprites (`SPRITE$`, `PUT SPRITE`).
**Graphics `GET`/`PUT` do NOT exist on MSX1** — the VG-8020 raises Syntax error
(ERR 2) for `GET (x,y)-(x,y),A` (§11.7); they are an MSX2 addition, out of charter.
`SCREEN`/`COLOR`/`CLS`/`WIDTH` already exist and stay
resident; this arc extends them only where a graphics mode needs extra setup.

**Deferred / flagged (see §10):** `SCREEN 3` (multicolor, a wholly different pixel
layout) — **recommend defer** to a follow-up slice; the charter wants it eventually
but SCREEN 2 carries ~all real programs and de-risks the engine first.

| Slice | Delivers | Placement | Risk |
|---|---|---|---|
| **G1** | VDP port I/O foundation + `SCREEN 2` bring-up: base-table equates, work-area contract (§5), the pixel-address+mask function, the DI-guarded VDP addr-latch primitive (§2/§3) | tenant scaffold | med — the interrupt-race primitive is the whole arc's floor |
| **G2** | `PSET` / `PRESET` / `POINT` — the atomic read-modify-write pixel op; SCREEN-2 **color-clash** falls out here (§4) | same tenant | med — color-attribute faithfulness **[PIN]** |
| **G3** | `LINE` (+ `,B` / `,BF`) — Bresenham over the G2 primitive; first genuinely long op → first EI exercise | same tenant | high — validates §2 under load |
| **G4** | `CIRCLE` (+ aspect ratio) | same tenant | med |
| **G5** | `PAINT` — scanline flood fill (RAM stack/queue), boundary-color logic | same tenant | high — unbounded runtime; EI + Ctrl-STOP |
| **G6** | `DRAW` — MML-style macro interpreter; structurally the twin of `IDX_PLAY_PARSE` ([sub/playparse.asm](sub/playparse.asm)) — reuse that parser shape | same tenant | med |
| **G7** | Sprites — `SPRITE$` / `PUT SPRITE` / attribute+pattern tables (NO graphics `GET`/`PUT` — §1) | **sub-decision** (§10 D6) — short writes, orthogonal to the pixel primitive | med |

---

## 2. THE CRUX — placement + interrupt discipline (DECISION D1)

Two hard constraints collide:

1. **New code must live in the sub-ROM.** Resident page 1 has 0–3 B free; the
   geometry engine (est. 1.5–3 KB) has nowhere else to go. Sub-ROM has the room.
2. **A long op must NOT hold DI.** `subrom_call` wraps the whole tenant in
   `di … call CALSLT … ei` ([basic/subromcall.asm:51](basic/subromcall.asm)). A
   full-screen `PAINT` run that way starves H.TIMI (the `PLAY` servicer) and JIFFY
   for its entire duration. And faithfulness demands it: **on a real MSX, music
   keeps playing while graphics draw**, precisely because graphics run interrupts-on.

The only mechanism that lets a tenant run `EI` is the **page-0 interrupt
trampoline** ([basic/subromcall.asm:89](basic/subromcall.asm)) — already built and
proven (the interrupt self-test tenant `SUBROM_IDX_INTTEST`, and the math pack's
`RND_SEED` even lives in its RAM reservation tail). A page-0 tenant carries its own
`$0038` that maps the BIOS back for the real ISR, so it may `EI` after entry / `DI`
before `ret`.

But page-0 residence has a consequence the recon surfaced
([sub/equates.inc:17](sub/equates.inc)): **a page-0 tenant has the BIOS switched
out** — it *cannot* `CALSLT WRTVRM`. That is not a problem; it is the forcing
function toward the correct design (§3): a pixel engine must not pay CALSLT-per-byte
anyway.

> **Recommended D1:** ONE **page-0 EI-trampoline graphics tenant**, direct VDP port
> I/O throughout (§3), holding a shared pixel primitive that all of G2–G6 call
> in-page (no CALSLT between verbs). It runs `EI` during compute loops (Bresenham
> stepping, fill scanning) so H.TIMI/JIFFY keep firing, and drops to a **brief DI
> only around the 2-byte VDP address-latch write** (§3) to close the
> interrupt-vs-VDP-status-read race. Short ops (`PSET`) simply never spin long
> enough to matter but cost nothing by living in the same island.

Alternative considered — a page-1 DI tenant (like `format`/`playparse`): rejected
for G3–G6 because it holds DI for the whole op. Viable *only* if every op is proven
short, which `PAINT`/big `CIRCLE` are not. Keeping a split (short verbs page-1/BIOS,
long verbs page-0/ports) was rejected as two VRAM-access methods in one arc.

**[PIN] D1 empirical floor (G1 gate):** extend the `subrom-inttest` pattern — a
graphics-shaped tenant that EI-spins ~N frames while direct-writing VRAM, asserting
JIFFY advanced (interrupts serviced) AND the VRAM writes are intact (no latch
corruption). This proves §2+§3 before any real geometry rides on it.

---

## 3. VRAM access model — direct VDP port I/O (DECISION D2)

The tenant talks to the TMS9918 directly, not through the BIOS:
- **Write setup:** to write VRAM address `addr`, output `addr & $FF` to port $99,
  then `(addr >> 8) | $40` to port $99 (write-enable bit). Autoincrement then lets
  a run of `out ($98),a` stream bytes.
- **Read setup:** low byte to $99, `(addr>>8)` (no $40) to $99, then `in a,($98)`.
- The **address-latch write is the one racy 2-byte sequence.** The frame ISR reads
  VDP status (`in a,($99)`), which shares the latch; an interrupt landing between
  our two $99 writes corrupts the address. Standard MSX discipline: wrap **only**
  those two `out ($99)` instructions in `di`/`ei` (microseconds), leaving the
  surrounding compute interruptible. **[PIN]** — confirm the race is real on VG-8020
  and that the brief-DI window matches reference behaviour (no visible glitch).

This mirrors the resident code's existing willingness to do raw port I/O
([basic/vdpio.asm:68](basic/vdpio.asm) `out (c),a` for `OUT`) and needs no BIOS,
which is exactly what page-0 residence (§2) requires.

G1 adds the port equates (VDP_DATA=$98, VDP_ADDR=$99) and the `SCREEN 2` base-table
equates (pattern generator, name table, color table, sprite attr/pattern — the
standard GRAPHIC-2 layout, values from the published VDP/`BASE` table, cross-checked
via `BASE(n)` black-box).

---

## 4. `SCREEN 2` pixel + color-clash model (DECISION D3)

In GRAPHIC-2, VRAM holds a **pattern** plane (1 bit/pixel: on=fg, off=bg) and a
**color** plane (one fg/bg *byte* per 8×1 pixel group). **Pinned VG-8020 layout**
(pattern generator @ $0000, color table @ $2000; §11):
- pattern/color byte addr = `(y>>3)*256 + (x>>3)*8 + (y&7)` (color at `+ $2000`).
- bit within the byte is **MSB-first**: mask = `$80 >> (x & 7)`.

**Color-attribute rule (D3 — PINNED, §11.3).** The color byte is `hi=fg | lo=bg`.
`PSET (x,y),c`:
- if `c` **equals the group color byte's current low (bg) nibble** → **clear** the
  pixel bit, color byte untouched;
- else → **set** the bit, write the color byte's **high** nibble = `c`, **preserve**
  the low nibble. So a second pixel plotted in the same 8-group with a different
  color rewrites the high nibble → every set pixel in the group takes the new color:
  the **8-pixel color clash**, bug-for-bug faithful
  ([memory: bug-for-bug-compat-over-accuracy]).
- `c` omitted → `FORCLR`. `PRESET` = `PSET` whose default color is `BAKCLR`;
  `PRESET (x,y),c` behaves exactly like `PSET (x,y),c`.

**Coordinates / clip / errors (PINNED, §11.4):** valid 0..255 × 0..191; off-screen
(256+, 192+, negative) within int16 is a **silent no-op — NOT clipped to the edge**;
a coordinate outside int16 → **ERR 6 (Overflow)** (raised by the eval domain, before
clip); `PSET` in `SCREEN 0/1` → **ERR 5 (Illegal function call)**.

---

## 5. Graphics work-area RAM contract

The engine's persistent state lives in the **system work area RAM** (page 2/3,
always mapped from both the tenant and main BASIC — the same visibility the
`ARY_*`/`SH_*`/`PLAY` blocks rely on). Two categories:

- **Reference-faithful cells** (program-visible, must land at their real MSX
  addresses — **PINNED** by RAM-scan diff, §11.5, matching the published MSX2-TH
  addresses): `GXPOS`=`$FCB3` / `GYPOS`=`$FCB5` (int16 LE, the pending pixel target),
  `GRPACX`=`$FCB7` / `GRPACY`=`$FCB9` (int16 LE, the **last-referenced point** for
  `LINE -(x,y)` / STEP — `LINE` updates it to the endpoint), `CLOC`=`$F92A` (the
  computed VRAM byte address), `CMASK`=`$F92C` (the MSB-first bit mask). Mirrors the
  `spec-basic-audio-play.md §5` "full standard work area" faithfulness choice.
- **Own-design scratch** (marshalling + `PAINT` stack + `DRAW` state) — homed in the
  repack-only free RAM window like every prior tenant's param block
  ([basic/sysvars.inc](basic/sysvars.inc) `GXX_*`, to be allocated), never aliasing
  a live cell.

---

## 6. Tenant / marshalling ABI

New page-0 index appended (never renumber): `SUBROM_IDX_GRAPHICS` (next free after
7; page-0 indices currently top out at PU_TAIL=7). A **selector-dispatched** single
entry (the `fatprim`/`dirverb` pattern — [sub/equates.inc:98](sub/equates.inc)):
resident stubs set a `GFX_OP` selector + args in a RAM param block, then
`subrom_call IX = SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_GRAPHICS`. Args/results
marshalled in RAM (coords are >8-bit; CALSLT clobbers all registers and CF cannot
ride back — [basic/subromcall.asm:54](basic/subromcall.asm)). Resident stubs
(repack-only, one per verb in a new `basic/graphics.asm`) do the eval of the
coordinate/color expressions (eval stays resident) and the token-cursor guard
(`push`/`pop hl` around the CALSLT — the exact bug that bit `ex_play`).

---

## 7. Tokens (capture discipline, §8 gate)

**PINNED** (VG-8020 stored-line crunch, §11.1). All single-byte tokens (no `$FF`
prefix); repack-only kwtable entries (the lean build keeps emitting verbatim, as
today). The `-` between coordinate pairs is the ordinary minus token `$F2`; `,B`/
`,BF` box suffixes stay **verbatim ASCII** (`2C 42` / `2C 42 46`).

| Keyword | Token | Kind |
|---|---|---|
| `PSET` | `$C2` | statement (this is the value the wrong `SOUND` guess used — [basic/sysvars.inc:362](basic/sysvars.inc)) |
| `PRESET` | `$C3` | statement |
| `CIRCLE` | `$BC` | statement |
| `PAINT` | `$BF` | statement |
| `DRAW` | `$BE` | statement |
| `POINT` | `$ED` | function (single-byte, like `BASE`/`VARPTR`) |
| `SPRITE` | `$C7` | the `$` is separate ASCII `$24`; `SPRITE$(n)` on both L/R of `=` |
| `STEP` | `$DC` | reserved word (relative-coord prefix) |
| `PUT SPRITE` | `$B3 20 $C7 20` | `PUT`($B3) + `SPRITE`($C7) — two reserved words |
| `LINE` (gfx) | `$AF` | **confirmed same token as `LINE INPUT`**; disambiguated on argument context (the `OUT`/`PUT` dual-token precedent) |

None collide with existing statement tokens ([basic/sysvars.inc](basic/sysvars.inc):
`FILES`$B7 `PUT`$B3 `SAVE`$BA `PLAY`$C1 `BEEP`$C0 `SOUND`$C4 `VPOKE`$C6 `BASE`$C9 …).

---

## 8. Gates (Definition of Done, per slice)

- `make graphics-acceptance` — new VG-8020 **differential** probe
  (`probes/basic/basic_probe_graphics.py`): draw on both zerobas and the reference,
  read the pattern+color VRAM back (`VPEEK` / openMSX `read_mem`), assert
  byte-identical pixel/attribute results. This is the load-bearing pass (§0).
- Host unit tests (`make unit-test`, [memory: host-unit-test-harness]) for the pure
  math: pixel-address+mask, Bresenham point sets, circle octant points, fill spans —
  locks the logic the probe proves.
- G1's `subrom-inttest`-style interrupt-under-draw gate (§2 [PIN]).
- Build wiring: add the new `sub/graphics.asm` to Makefile `SUB_PARTS` and
  force-rebuild — the stale-tenant trap ([memory: makefile-subparts-stale-tenant]).
  Rebuild+reinstall the IPS for machine probes ([memory: ips-rebuild-after-basic-change]).

## 9. Clean-room

Own code throughout; VDP/port/work-area/token contracts are called or captured,
never disassembled ([memory: no-reference-rom-disasm]). Log the direct-port-I/O and
own-design-rasteriser decisions in `sub/PROVENANCE.md`, mirroring the audio arc's
own-design-packet note.

## 10. Open decisions — SIGN-OFF NEEDED

| # | Decision | Recommendation |
|---|---|---|
| **D1** | Placement + interrupt discipline | **Page-0 EI-trampoline tenant, direct ports, brief-DI latch** (§2) |
| **D2** | VRAM access method | **Direct VDP port I/O** (§3), not BIOS CALSLT |
| **D3** | Color-clash / attribute rule | RESOLVED — pinned (§4/§11.3): compare `c` vs the byte's own low nibble; set→hi-nibble, preserve lo |
| **D4** | SCREEN 3 (multicolor) | **Defer** to a post-arc slice; SCREEN 2 only now (§1). NOTE: G8 nevertheless had to model SCREEN 3's *register* layout, because the reference's `BASE(n)=` in SCREEN 2 programs the chip from the multicolor group (spec-basic-graphics-g8.md §4.4) |
| **D5** | Engine granularity | **One selector-dispatched page-0 tenant** for G2–G6 (§6) |
| **D6** | Sprites (G7) placement | SETTLED 2026-07-22 — join the graphics tenant (`GFX_OP` 7–12), spec-basic-graphics-g7.md §2 |
| **D7** | Slice ordering / first cut | G1→G2→G3 as the de-risking core, then G4–G7 |
| **D8** | `VDP(n)` / `BASE(n)` (G8) | SETTLED 2026-07-22 — tenant ops 13/14 for the writes, resident work-area fetches for the reads, the SCREEN-1/2 off-by-one REPRODUCED, and the old `BASE` descope retired: spec-basic-graphics-g8.md |

---

## 11. Pinned VG-8020 characterization (black-box, 2026-07-21)

Method: KEYBUF-injection via [omsx_repl.py](probes/lib/omsx_repl.py) on
`Philips_VG_8020`; VRAM read back *inside* each case line (`VPEEK`→`POKE` into
$D1xx, then a planted-pointer `mem_indirect` capture) because returning to the text
prompt rewrites VRAM. Raw captures cached in scratchpad. Behavior only — no ROM
disassembly. These pins are the acceptance oracle the G-slices differential against.

**11.1 Tokens** — table in §7 (stored-line `1 <body>` crunch; nothing executed).

**11.2 SCREEN 2 base tables** (`BASE(10..14)`, identical read from SCREEN 0 or 2):
name `$1800`, color `$2000`, pattern generator `$0000`, sprite attribute `$1B00`,
sprite pattern generator `$3800`. Landing checks confirm `addr = (y>>3)*256 +
(x>>3)*8 + (y&7)`, bit = MSB-first `$80 >> (x&7)`.

**11.3 Color-attribute rule** — §4. Evidence: after `COLOR 15,4,7:SCREEN2` every
color byte = `$04` (fg 0 | bg 4=BAKCLR@CLS). `PSET(0,0),15`→ pattern `$80` / color
`$F4`. `PSET(0,0),15:PSET(1,0),6` → `$C0`/`$64` (both pixels become 6 — clash).
`…:PSET(1,0),4` (c == the byte's bg nibble) → `$80`/`$F4`: the 2nd bit is **not**
set. Disambiguation run (byte bg=4 while BAKCLR=1): `PSET(0,0),4`→clear,
`PSET(0,0),1`→set `$14` ⇒ the **byte's own low nibble** decides, not `BAKCLR`, and
`PSET` never writes the bg nibble. `c` omitted → `FORCLR` (13 → `$D4`). `PRESET`
after a `PSET` clears the bit (color untouched); `PRESET(0,0),6` → `$80`/`$64`
(= `PSET,c`). **Unmeasured edge (flagged):** a group whose fg nibble already equals
its bg nibble, with `c` equal to both — which branch wins is unobservable; handle
conservatively and note in the G2 gate.

**11.4 Coordinates / clip / errors** — §4. `PSET(255,191)` ok; `(256,0)`/`(0,192)`/
`(-1,0)`/`(300,100)`/`(32767,0)` → silent no-op, **not** edge-clipped;
`(32768,0)`/`(-32769,0)` → **ERR 6**; `PSET …` in SCREEN 0/1 → **ERR 5**.

**11.5 Last point / STEP / work area** — §5. `PSET(10,20):LINE-(30,40)` draws from
(10,20); `LINE` then sets all of GXPOS/GYPOS/GRPACX/GRPACY to the endpoint (30,40).
`PSET STEP(5,5)` after `PSET(10,20)` → (15,25); negative STEP verified. Work-area
diff pinned `GXPOS=$FCB3 GYPOS=$FCB5 GRPACX=$FCB7 GRPACY=$FCB9 CLOC=$F92A
CMASK=$F92C`. **G2 addendum (2026-07-21):** a drawn `PSET(10,20)` writes BOTH
GXPOS/GYPOS AND GRPACX/GRPACY = (10,20); and an **off-screen no-op** `PSET(300,100)`
still moves GRPACX/GRPACY to the **raw unclipped** (300,100) — the work-area update is
unconditional, only the pixel plot is range-gated (G2 spec §4/§6, G2-d).

**11.6 Interrupts live during a draw** — JIFFY (`$FC9E`) advanced `$0584→$0599`
(21 frames ≈ 0.42 s) across `CIRCLE(128,96),80,15`. Confirms the reference services
interrupts mid-draw → validates the §2 EI-during-draw intent (music keeps playing).

**11.7 Graphics GET/PUT absent** — `GET (0,0)-(8,8),A` / `PUT (0,0)-(8,8),A` crunch
(tokens `$B2`/`$B3`) but raise **ERR 2 (Syntax error)** at runtime. Faithful MSX1
behavior is Syntax error; §1 scope corrected.

**11.8 POINT** — returns the pixel's color (bonus): a `c=13` pixel → 13, its neighbor
→ 4 (bg); **off-screen `POINT` → -1**; `POINT` in SCREEN 0 does **not** error (value
is screen-content dependent — only "no error" is pinned). **G2 addendum:** re-confirmed
(`POINT(50,50)` of a color-9 pixel → 9, neighbor → 4, `POINT(300,300)` → -1); and
**`POINT STEP(dx,dy)` is accepted** — STEP resolved against the last point (GRPAC),
`POINT STEP(0,0)` after `PSET(50,50),9` → 9 (G2 spec §5, G2-g).

**11.9 Tokens re-verified (G2, 2026-07-21):** stored-line crunch on VG-8020 —
`PSET(0,0)`→`C2 28 11 2C 11 29 00`, `PRESET(0,0)`→`C3 …`, `X=POINT(0,0)`→`58 EF ED …`,
`PSET STEP(1,2)`→`C2 20 DC 28 …`. Confirms **PSET=$C2 PRESET=$C3 POINT=$ED STEP=$DC**
(the §7 table; `$C2` — the value the wrong `SOUND` guess used — is genuinely PSET).

---

## Appendix — sources

TMS9918A datasheet (VDP ports/registers/GRAPHIC-2 layout); MSX2 Technical Handbook
VDP chapter + work-area appendix; public MSX-BASIC language reference (statement
semantics); VG-8020 black-box captures (tokens, color-attribute rule, work-area
addresses, clipping/error behaviour). No reference-ROM disassembly.
