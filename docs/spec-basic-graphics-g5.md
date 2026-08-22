# Spec — graphics Slice G5: `PAINT` (SCREEN-2 flood fill)

Status: **SIGNED OFF (2026-07-21) — ready for impl (Sonnet-5).** D1/D2/D4/D5 as
written; D3 overflow = ERR 7 (measured). Part of the graphics arc
([docs/spec-basic-graphics.md](spec-basic-graphics.md), slice G5). All pins are
MEASURED black-box on the Philips VG-8020 (no ROM disassembly); the raw
characterization + probes are in `scratchpad/g5_paint_*` and
`scratchpad/g5_paint_notes.md`. Clean-room: the flood algorithm, the parser and
the marshalling are zerobas's own; only the *observable language behaviour* is
pinned from the reference.

---

## 1. What lands in G5 vs. what defers

**Lands:** `PAINT [STEP](x,y)[,C[,B]]` — SCREEN-2 flood fill from a seed, painting
the 4-connected region with colour `C`, bounded by pixels of colour `B`.

**Defers / rejected (measured, §8):**
- MSX2 tile form `PAINT(x,y),tile$,B` → **ERR 13** (Type mismatch) at runtime.
- 4th argument `PAINT(x,y),C,B,n` → **ERR 2** (Syntax error) at runtime.
- SCREEN 3 (multicolor) — whole arc defers it (D4).

---

## 2. Placement + EI-during-draw discipline (inherited from G3/G4)

Same as LINE/CIRCLE: the fill runs in the **page-0 EI-trampoline graphics
tenant** ([sub/graphics.asm](../sub/graphics.asm)), a new arm `GFX_OP=5`. It uses
**direct VDP port I/O** and reuses the landed pixel primitives verbatim:
- `gfx_plot_cur` — the G2/G3 colour-clash read-modify-write (paints one pixel).
- `gfx_point` (effective-colour read) — the border test (reads the *current*,
  post-clash colour of a pixel).

Interrupt discipline: **EI between fill units, DI only around each pixel's VDP
RMW** (the fetch-window settle in `gfx_rd_raw` stays inside the DI bracket, per
[vdp-direct-port-read-fetch-window]). A long PAINT keeps music playing; Ctrl-STOP
interrupts it exactly like a long LINE. PAINT is genuinely SLOW (a full-screen
flood is seconds of emulated time) — this is faithful.

---

## 3. `PAINT` grammar + semantics (measured §11)

```
PAINT [STEP] (x,y) [, [C] [, B]]
```
- **Coordinate** (seed): STEP-relative vs absolute, resolved by the existing
  `parse_coord` (STEP vs GRPAC, `>int16 → ERR 6`). Same as PSET.
- **`C` (paint colour):** omitted → `FORCLR`. Evaluated int16; **`C<0` or `C>15`
  → ERR 5** (Illegal function call). Used as a 0..15 nibble.
- **`B` (border colour):** omitted → **`= C`**. Evaluated int16, then
  **RANGE-CHECKED AGAINST THE MODE'S DOMAIN** — `0..255` in SCREEN 2 and
  `0..15` in MULTICOLOUR; outside → **ERR 5**
  ([`spec-basic-paintbord.md`](spec-basic-paintbord.md)). The `,,B` form
  (colour omitted, border given) is legal.
  ⚠️ **THE SENTENCE THAT USED TO STAND HERE IS INVERTED, NOT DELETED.** It read
  *"NOT range-checked (`B=16` raises no error — it is only a comparison value
  that no 0..15 pixel matches)"*. The parenthesis is **true** — 16 raises no
  error in SCREEN 2 and is a comparison value nothing matches — and the
  conclusion drawn from it is **false**: 16 is merely INSIDE the SCREEN-2 domain,
  and the argument that a border no pixel can equal must therefore be legal fails
  at 256 (ERR 5 in SCREEN 2) and at 16 itself (ERR 5 in MULTICOLOUR). One
  measured case was generalised into a domain. The check is on the full int16,
  not the stored byte: 256 is `$0100` and its low byte is `$00`.

**The fill (measured, POINT-verified — the crux):** flood the 4-connected region
of the seed, painting each pixel with the colour-clash RMW (`gfx_plot_cur`), and
stopping a walk when the *current effective colour* of the next pixel `== B`.

Because SCREEN 2 shares one foreground per 8-pixel group-row, painting a pixel
recolours its whole group-row's foreground to `C`. The measured consequence,
robust across a 1-px box AND a proven-enclosing 8-px-thick group-aligned arena:

| case | result |
|---|---|
| **`C == B`** | **BOUNDED** — the connected region only. Painted pixels read back as `B` and self-limit the walk. |
| **`C != B`** | **FLOODS THE ENTIRE SCREEN** with `C`, clipped to 0..255 × 0..191. Border pixels sharing a group-row with the fill get their foreground overwritten to `C` → the border is "eaten" → the fill escapes and reaches every screen pixel (far corner (200,150) verified = `C`). No wrap, no error. |

**KEY SIMPLIFICATION:** the final bitmap is **traversal-order-independent** — a
bounded fill converges to the connected set; a `C!=B` fill converges to the whole
clipped screen. So G5 may use **any correct flood algorithm** and still be
byte-faithful (unlike G3/G4, where the exact Bresenham/midpoint order was
load-bearing). Order only matters for a Ctrl-STOP-interrupted fill (impl-defined,
like an interrupted LINE) and for pathological *partial* `C!=B` fills (excluded
from the differential gate).

**DOCUMENTED DEVIATION — G5-align (`C!=B` flooding of byte-aligned enclosures).**
The `C!=B` flood works via the clash: the fill escapes an enclosure because a
border pixel *shares a VRAM 8-pixel colour-group* with a to-be-painted interior
pixel, so painting recolours (eats) the border. When an enclosure's walls are
**byte-aligned to the 8-pixel colour groups in BOTH axes** (e.g. a `,B` box at
exactly `(16,16)-(40,40)`, or the 8-px arena used in characterization), the
interior shares NO group with anything outside → clash-escape is topologically
impossible under our (or *any* apparent) pixel-accurate model. **Yet the VG-8020
still escapes such enclosures by some other mechanism we could not identify
without disassembly** (barred by the no-reference-ROM-disasm principle). So for
this narrow case our PAINT stays BOUNDED where the reference floods. Programs
essentially never draw walls at exact multiples of 8, so real fills match; the
differential gate uses deliberately non-aligned coordinates. (Same
documented-deviation class as G4-rneg; [bug-for-bug-compat-over-accuracy].)

**Off-screen seed (DISTINCT from PSET/LINE):** a seed that is in-int16 but
`x∉0..255` or `y∉0..191` (incl. negative) → **ERR 5** (NOT a silent no-op / clip).
`|coord|>int16` still → ERR 6 first (in `parse_coord`).

**Work area:** after PAINT, `GRPACX/GRPACY = GXPOS/GYPOS = the seed (x,y)`.

**SCREEN 0/1 → ERR 5.**

---

## 4. The fill engine (own-design) — recommended shape

A **scanline span flood-fill** (Smith-style), chosen to bound the stack (a naive
per-pixel stack is O(area)):

1. Seed span: from the seed, walk left/right painting until the next pixel's
   effective colour `== B` (or the screen edge x=0/255). This yields one filled
   horizontal span `[xL..xR]` at row `y`.
2. For the rows `y-1` and `y+1` (clipped to 0..191), scan across `[xL..xR]` for
   maximal sub-spans of not-yet-`B` pixels and push each as a new seed span.
3. Pop and repeat until the stack is empty.

- Paint = `gfx_plot_cur`; border test = `gfx_point` (live effective colour).
- **EI between spans; DI per pixel** (VDP-race + fetch-window inside the DI).
- The `C==B` self-limit and the `C!=B` whole-screen flood both emerge from this
  with no special-casing (a painted pixel reads back `C`; the "already filled"
  test is exactly "effective colour == B").

**Span stack (D3 — SIGNED OFF, overflow measured):** fixed-capacity span stack in
a repack-only RAM window (each entry ~5 B: `y`, `xL`, `xR`, parent-direction).
**Overflow → ERR 7 (Out of memory)** — MEASURED on the reference: its stack grows
down from STKTOP and only overflows under pathologically tight memory (box + ~73
full-height parallel channels completes at normal HIMEM and down to himem=$8800;
only himem=$8500 forces "Out of memory in 60"). Realistic fills NEVER overflow, so
**size the stack generously (target ≥128 spans)** and raise ERR 7 on the rare
overflow to match. Exact RAM home + capacity finalized during impl (must NOT alias
live interpreter/PLAY state — the recurring aliasing bug class; the LINEBUF-region
discipline of G3/G4 is too small for a big stack, so pick a documented
dead-during-graphics window and measure).

---

## 5. Errors (all measured, §8)

| condition | error |
|---|---|
| SCREEN 0 / 1 | ERR 5 (Illegal function call) |
| paint colour `C < 0` or `C > 15` | ERR 5 |
| seed off-screen (in-int16, `x∉0..255`/`y∉0..191`, incl. negative) | ERR 5 — **and the work area is moved to the raw seed first** (D-PAINTSEED; `(255,191)` is the last accepted point, `(256,191)` and `(255,192)` are not) |
| any coordinate `> int16` | ERR 6 (Overflow) |
| `PAINT(x,y),tile$,B` (string paint colour) | ERR 13 (Type mismatch) |
| `PAINT(x,y),C,B,n` (4th arg) | ERR 2 (Syntax error) |
| border `B` outside `0..255` (SCREEN 2) / `0..15` (MULTICOLOUR) | **ERR 5**, raised as `B` is parsed — ABOVE the 4th-arg grammar test (D-PAINTBORD; `PAINT(10,10),9,16,` in SCREEN 3 is ERR 5, not ERR 2). ⚠️ This row used to read *"no error (comparison value only)"* |
| border `B` = 16..255 in SCREEN 2 | no error — a comparison value no 0..15 pixel matches (unchanged; this is the case the retracted row was generalised from) |

---

## 6. Work-area contract + marshalling ABI

Reuse the shared tenant block. New/used cells:
- `GFX_OP=$E030` = **5** (PAINT arm).
- `GFX_C=$E031` = paint colour `C` (0..15).
- **`GFX_B` (new, 1 B, append after G4's cells ~`$E14B` in the LINEBUF region)** =
  border colour `B` (the raw comparison value).
- Seed marshalled via `GXPOS/GYPOS` (`$FCB3/$FCB5`).
- The span-stack RAM window (D3).

⚠️ **SUPERSEDED 2026-08-11 by D-LINERR**
([`spec-basic-lineerr.md`](spec-basic-lineerr.md) §5). The order below was a
design choice, never measured against a reference, and **both of its ends are
wrong**. Kept rather than deleted, because a retired claim that simply vanishes
is invisible on the next grep (`bf0dab5`):

> ~~Resident `ex_paint`: **SCREEN-2 precheck** → `parse_coord` (seed) →
> off-screen-seed → ERR 5 → parse optional `C` (default FORCLR, range 0..15 →
> ERR 5) → parse optional `B` (default = C) → 4th-arg → ERR 2 → **set
> GRPAC/GXPOS = seed** → marshal → `subrom_call IX=$0028` → chain.~~

The gate is **not** a precheck: `PAINT((Q$<5),21)` in SCREEN 0 is `Type
mismatch` on both references, so the seed's own fault outranks the mode. And the
work-area write is **not** deferred past every field: `PAINT(20,21),0*(1/0)`
leaves `GRPAC`/`GXPOS` on (20,21) on both references. The measured order is

    ex_paint: parse_coord (seed) → work area := seed → SCREEN-2 gate
              → off-screen-seed → ERR 5 → optional C (0..15 → ERR 5)
              → optional B (default = C) → 4th-arg → ERR 2 → marshal
              → `subrom_call IX=$0028` (`SUBROM_IDX_GRAPHICS`) → chain.

Both moves are one `call gfx_point_gate` (`basic/graphics.asm`), and hoisting the
write **retires the `push bc`/`push de` pair** that existed only to guard the
seed across the `C`/`B` parses — which is why the change gives 25 bytes back at
this verb. Rows `v.paint0.tm` / `v.paint0.c` / `v.paint2.c`; knife **K-LE4a**.

⚠️ **SUPERSEDED 2026-08-11 by D-PAINTSEED**
([`spec-basic-lineerr.md`](spec-basic-lineerr.md) §9), hours after the paragraph
above was written. Kept rather than deleted, per the same rule:

> ~~The off-screen-seed ERR 5 stays **above** the gate and is untouched. Both
> faults raise ERR 5, so no row in the sweep can order those two against each
> other — only the work area could, and it is written between them. Filed
> unmeasured in `TODO.md`.~~

The last sentence is right and the first is wrong, and the second is the reason:
*"no row can order those two"* is true of the **gate**, and the paragraph then
used it to leave the **work-area write** unmeasured as well. Those are different
comparisons. `PAINT(300,100)` in SCREEN **2** — where the gate cannot fire at all
— raises ERR 5 with `GRPACX/GRPACY` **and** `GXPOS/GYPOS` already on the raw,
unclipped `(300,100)` on both references. So the seed test is **below** the
work-area write, hence below `gfx_point_gate`, and the order above is corrected
to match. Measured across the whole seed domain, both axes, both signs, both
off-by-one edges and through `STEP`: rows `p.*` / `w.paint*.off`, knives
K-PS1..K-PS3, net zero bytes.

⚠️ The seed test versus the **gate** remains genuinely unordered, and nothing
now claims otherwise: when a seed is off-screen *and* the mode is wrong, both
raise ERR 5 with the same work area whichever runs first.

---

## 7. Token dispatch

`PAINT=$BF` (pinned G1). The tokeniser is already permissive (measured: every
form crunches; runtime enforces §5). Route the `$BF` statement token to `ex_paint`
in the interpreter dispatch (repack-only, PSET/CIRCLE pattern). No kwtable/runtime
disambiguation needed.

---

## 8. Space (measured — §3 of the notes)

Page-1 tail = **80 B free** (`__MEAS_PAGE1_END=$7FB0`). The flood engine is
sub-ROM (~7 KB free) — only `ex_paint` (~130–150 B est.) hits page 1 → overrun
~50–70 B. **DRY-first:** factor the duplicated optional-`,c` colour parse (in
`ex_pset` l.50–64 AND `ex_circle`/`circ_c` l.396–409, incl. the `,,` empty-field
handling) into a shared leaf → shrinks `ex_pset` + `ex_circle` and serves
`ex_paint`; likely frees the overrun with no eviction. **Fallback:** a small
self-contained eviction (G4 precedent). Measure `ex_paint` empirically before
declaring an eviction need (recurring lesson).

---

## 9. Decisions — SIGN-OFF NEEDED

- **D1 (algorithm & faithfulness model):** flood via the shared `gfx_plot_cur`
  clash RMW + live `gfx_point` border test; rely on **traversal-order-independence**
  for byte-faithfulness (bounded set for `C==B`; whole clipped screen for `C!=B`).
  Differential gate uses bounded + full-flood + error cases only. **OK?**
- **D2 (off-screen seed → ERR 5):** adopt the measured PAINT-specific rule (NOT
  PSET/LINE clip). **OK?**
- **D3 (span-stack home + overflow):** ✅ SIGNED OFF — overflow → **ERR 7 (Out of
  memory)**, MEASURED on the reference (himem=$8500 forces it; realistic fills never
  do). Fixed-capacity span stack in a repack-only RAM window, sized generously
  (≥128 spans); RAM home finalized during impl (no aliasing live state).
- **D4 (space):** DRY-first (shared colour-parse leaf), evict only if measured
  `ex_paint` still overruns. **OK?**
- **D5 (model split):** per [opus-vs-sonnet-model-split], hand the signed-off spec
  to Sonnet-5 for impl. **OK?**

---

## 10. Gates (Definition of Done, G5)

- Host unit tests for the pure fill leaves (span-walk / border-test), teeth-proven.
- `make graphics-acceptance` + a **PAINT phase**: VG-8020 **effective-colour
  (POINT) differential** with a large emulated budget (`step>=30`), covering:
  bounded `C==B` closed region (exact bitmap), `C!=B` whole-screen flood (sample
  points == C), STEP form, defaults (`PAINT(x,y)`, `,,B`), and every §5 error.
- Lean cart byte-identical (repack-only feature).

---

## 11. Pinned VG-8020 characterization (black-box, 2026-07-21)

See `scratchpad/g5_paint_notes.md` for the full log. Summary: grammar/tokens
(C1), work-area = seed (C5), errors (C6: off-screen seed → ERR5, C-range → ERR5,
coord ovf → ERR6, tile$ → ERR13, 4th-arg → ERR2, *"border unchecked"* —
⚠️ **that last one is RETRACTED**, see §3/§5 and
[`spec-basic-paintbord.md`](spec-basic-paintbord.md): the characterization only
ever exercised `B=16`, which is inside the SCREEN-2 domain), the
harness-budget trap (PAINT slow in emulated time — not a hang), and the
`C==B`-bounded / `C!=B`-flood dichotomy (POINT-verified across thin box + thick
arena, with a fill=15 control proving the arena encloses).

⚠️ **C6's off-screen pin was the ERROR CODE, on ONE machine.** It never asked
where the work area stood, and that gap is what let §6 ship the seed test above
the write for the whole life of G5. D-PAINTSEED (2026-08-11) re-measured the seed
domain on **both** references through `GRPACX/GRPACY` *and* `GXPOS/GYPOS`, added
the accepted edge `(255,191)` that C6 had no row for, and moved the test — 16
rows in `make lineerr-acceptance`, [`spec-basic-lineerr.md`](spec-basic-lineerr.md)
§9. The code C6 pinned is unchanged; what it did not pin is what moved.

## Appendix — sources
Public MSX-BASIC language reference for `PAINT` grammar/semantics; all
mode/colour/clash/flood/error specifics are VG-8020 black-box pins. No
disassembly. See [basic/PROVENANCE.md](../basic/PROVENANCE.md).
