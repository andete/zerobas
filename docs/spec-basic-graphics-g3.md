# Spec — graphics Slice G3: `LINE` (+ `,B` / `,BF`) — the first long, EI-during-draw op

**Status: DRAFT — SIGN-OFF NEEDED (2026-07-21).** Slice-design addendum to the arc
spec [`spec-basic-graphics.md`](spec-basic-graphics.md) (crux D1/D2/D3/D4 approved)
and the landed [`spec-basic-graphics-g1.md`](spec-basic-graphics-g1.md) /
[`spec-basic-graphics-g2.md`](spec-basic-graphics-g2.md). No asm is written until the
decisions in §9 are approved. The **VG-8020 characterization pass is complete** (§11);
every faithfulness fact below is a measured black-box pin, and the exact rasteriser
variant is **host-fit against the captured pixels** (§4/§11.3) — the recurring arc
lesson ([memory: error-handling-arc]) applied up front, because a green build hides a
wrong pixel as easily as a dead trap branch.

G1 built the VDP floor; G2 delivered the atomic pixel RMW + the color clash. **G3 is
the first genuinely long, looping op** and therefore the arc's first real exercise of
the interrupt discipline (D1): a large `LINE` — and especially a `,BF` filled box —
must run **interrupts-on so `PLAY` keeps sounding**, dropping to DI only around each
pixel's VDP access. G3 is where §2 of the arc spec is validated under load.

> **Two crux surfaces, both measured, not reasoned:**
> 1. **Pixel-exactness.** `LINE`'s own-design Bresenham must reproduce the reference
>    pixel set **byte-for-byte**, including tie-breaking and the measured
>    **direction-independence** (`LINE(a)-(b)` ≡ `LINE(b)-(a)`). The variant is pinned
>    by fitting against captured VG-8020 bitmaps (§11.3): **err init 0, minor step when
>    `2·err ≥ dx`, endpoints sorted so the major axis ascends.** All four probe lines
>    (shallow/steep/diagonal/negative) match exactly.
> 2. **EI-during-draw under the VDP races.** The loop runs `EI` between pixels and
>    `DI` around each pixel's read-modify-write, whose reads carry the G2
>    **fetch-window** settle ([memory: vdp-direct-port-read-fetch-window]). Both the
>    latch-reset race (ISR reads `$99`) and the read-ahead race apply per pixel now,
>    inside an interrupt-live loop.

---

## 1. What lands in G3 vs. what defers

| Piece | G3 | Notes |
|---|---|---|
| `LINE (x1,y1)-(x2,y2)[,c]` | ✅ | the base segment; own-design Bresenham (§4) |
| `LINE -(x2,y2)[,c]` continuation | ✅ | `p1 = GRPAC` (last point); §3.2, §11.5 |
| `LINE [STEP](x1,y1)-[STEP](x2,y2)` | ✅ | STEP **chains** — 2nd STEP relative to the 1st endpoint (§3.3, §11.6) |
| `LINE …,c,B` rectangle outline | ✅ | 4 edges, inclusive corners (§5, §11.4) |
| `LINE …,c,BF` filled rectangle | ✅ | scanline fill of the box (§5, §11.4) |
| Off-screen **clipping** (draw the on-screen portion) | ✅ | LINE **clips**, unlike PSET's no-op — measured (§3.4, §11.7) |
| Per-pixel color clash along the line/box | ✅ | identical to G2's rule; reuses `gfx_color_rmw` (§4.3, §11.3) |
| EI-during-draw + DI-per-pixel primitive | ✅ | the D1 exercise (§2) |
| `CIRCLE` / `PAINT` / `DRAW` / sprites | ❌ G4+ | — |
| Fast-forwarding the Bresenham error across a huge off-screen span | ❌ | correctness first; masking iterates every step (§4.4 perf note) |

**No new token, no new kwtable row.** `LINE=$AF` already tokenizes on both builds
(it exists for `LINE INPUT`, [basic/kwtable.inc:43](basic/kwtable.inc)); graphics
`LINE` is disambiguated **purely at runtime** in `ex_line` (§6/§7). G3 is otherwise
repack-only (the page-0 tenant op), so the lean cart is byte-identical.

---

## 2. Placement + the EI-during-draw discipline (the D1 exercise) — crux 2

`LINE` runs in the **page-0 graphics tenant** ([sub/graphics.asm](sub/graphics.asm)),
a new selector op **`GFX_OP=3`** beside G1's self-test (0) and G2's plot/point (1/2).
This is the first op long enough that holding DI for its duration would starve
H.TIMI/JIFFY — a full-width line is ~7 ms (≈0.4 frame) and a large `,BF` fill is many
frames. Faithfulness demands interrupts stay live (arc §11.8 measured JIFFY advancing
mid-`CIRCLE`); **music must keep playing while a line draws.**

**The loop discipline (own-design, mirrors `graphics_selftest`):**
- The tenant is entered under DI by `CALSLT`. The `LINE` op does **`ei`** at the top,
  runs the Bresenham/box loop with interrupts live, and **`di`** before `ret` — the
  exact bracket G1's self-test already proved ([sub/graphics.asm:78](sub/graphics.asm)).
- **Each pixel's read-modify-write is one brief DI unit.** Between pixels the loop is
  interruptible; around a pixel we `di`, do calc-addr → read pattern → read color →
  clash → write pattern → write color, then `ei`. This is arc §2/§3 to the letter:
  "drop to a brief DI only around the VDP access."
- **The per-pixel reads carry the G2 fetch-window settle.** With interrupts live, both
  VDP races apply *per pixel*: the ISR's `$99` status read resets the address latch
  (closed by the DI bracket), and the read-ahead fetch window means a bare
  `out $99/out $99/in $98` returns a stale byte (closed by the 8-NOP settle in
  `gfx_rd_raw`, [memory: vdp-direct-port-read-fetch-window]). **G3-x:** the LINE
  per-pixel primitive reuses **`gfx_rd_raw`** (which has the settle) *inside* the DI
  bracket — NOT G1's `gfx_vram_rd` (which is DI-guarded but has **no** fetch window and
  is used only by the write-then-read-back self-test). See §9 G3-x.

**What stays resident** (like G2): token dispatch + the `LINE INPUT` disambiguation
(§7), the coordinate/color **eval**, the `STEP`/`(`/`,`/`)`/`-`/`,B`/`,BF` syntax walk,
the `SCREEN 2` precheck and the ERR raises, the work-area writes (§6 GRPAC=p2), and
marshalling one param block + one `subrom_call`. The tenant owns only the rasteriser
and the per-pixel VDP RMW.

**BIOS-agnostic (inherited):** touches only `$98`/`$99`, never a VDP mode register.

---

## 3. `LINE` grammar + semantics (measured §11)

**Grammar (VG-8020 crunch, §11.1):**
```
LINE  [ [STEP] '(' x1 ',' y1 ')' ]  '-'  [STEP] '(' x2 ',' y2 ')'
      [ ',' [ c ] [ ',' ('B' | 'BF') ] ]
```
- The **`-` is mandatory** and is `MINUS_TOKEN $F2`; the **second coordinate is
  mandatory**. The **first coordinate is optional** (`LINE-(x2,y2)`).
- `STEP` = `$DC` prefix on either coordinate. `,B` = verbatim ASCII `2C 42`; `,BF` =
  `2C 42 46` (§11.1). Color may be omitted with a placeholder comma: `LINE(a)-(b),,B`.
- **Errors (§11.5):** a missing `-`/second coord (`LINE(5,5)`), a bare `LINE`, or a bad
  suffix (`…,X`) → **Syntax error (ERR 2)**. A coordinate outside int16 → **Overflow
  (ERR 6)**. `LINE` in SCREEN 0/1 (incl. the `,BF` form) → **Illegal function call
  (ERR 5)**.

**3.1 Draw.** Plot every pixel of the segment `p1→p2` inclusive with color `c`
(default `FORCLR` when omitted, §11.3), using the per-pixel color-clash RMW (§4.3).
A degenerate `LINE(x,y)-(x,y)` lights the single pixel `(x,y)` (§11.6).

**3.2 Continuation.** `LINE-(x2,y2)` sets `p1 = (GRPACX,GRPACY)`, the last-referenced
point (§11.5: `PSET(3,3):LINE-(3,12)` draws the vertical run `x=3, y=3..12`).

**3.3 STEP chains (measured, §11.6).** In `LINE STEP(a,b)-STEP(c,d)` the **first**
STEP is relative to `GRPAC`; the **second** STEP is relative to the **first resolved
endpoint**, not to `GRPAC`. Measured: `PSET(10,10):LINE STEP(2,2)-STEP(3,3)` draws
`(12,12)-(15,15)` (the `(3,3)` added to `(12,12)`, not `(10,10)`). Implementation: the
running reference point advances to `p1` before `p2` is parsed (§6).

**3.4 Off-screen ⇒ CLIP, not no-op (measured, §11.7).** Unlike `PSET` (silent no-op),
`LINE` **draws the on-screen portion** of a partly-off-screen segment and raises no
error; a fully-off-screen segment draws nothing (still no error):
- `LINE(-100,-100)-(50,50)` → the on-screen pixels are exactly the ideal `y=x` for
  `x∈[0,50]`; `LINE(0,0)-(510,190)` → the on-screen Bresenham run to the right edge;
  `LINE(300,300)-(400,400)` → blank. `LINE(0,0)-(300,300)` → no error.
- **Model:** the measured on-screen pixels equal the **masked ideal Bresenham** — run
  the rasteriser over the true (possibly off-screen, int16) endpoints and plot only
  the pixels with `0≤x≤255 ∧ 0≤y≤191`. See §4.4 and the §9 G3-clip residual.

---

## 4. The rasteriser (own-design, host-fit to the reference) — crux 1

**4.1 Exact variant (pinned by fitting, §11.3).** Integer Bresenham with:
- **Sort endpoints so the major axis is ascending** (this is what makes drawing
  direction-independent — §11.3 measured `LINE(20,7)-(0,0)` ≡ `LINE(0,0)-(20,7)`).
- Major axis = the larger of `|dx|`,`|dy|`; transpose to the steep case when `|dy|>|dx|`.
- **error init = 0**; per major step: plot, `err += dmin`, and **if `2·err ≥ dmaj`**
  then step the minor axis (`err -= dmaj`). Minor-axis sign = `sgn` of its delta.

This variant reproduces **all four** captured VG-8020 bitmaps exactly (§11.3):
shallow `(0,0)-(20,7)`, steep `(0,0)-(7,20)`, diagonal `(0,0)-(15,15)`, negative
`(0,15)-(15,0)`. The fit is scripted
([scratchpad/g3_bresenham_fit.py](../scratchpad/g3_bresenham_fit.py)); the captured
sets become the host-unit-test oracle (§8).

**4.2 16-bit signed coordinates.** Because clipping is masking (§3.4/§4.4), the
rasteriser runs over the **true int16 endpoints** and range-tests each pixel; deltas
are up to 16-bit. The per-pixel in-range gate (`0≤x≤255 ∧ 0≤y≤191`) is what implements
the clip and also guarantees `gfx_calc_addr`'s `x≤255,y≤191` preconditions
([sub/graphics.asm:177](sub/graphics.asm)) for every pixel actually plotted.

**4.3 Per-pixel color.** Each plotted pixel takes the **same clash RMW as `PSET`**
(§11.3: `LINE(0,0)-(15,0),6` → color bytes `$61` = fg 6 | bg 1). The tenant reuses
`gfx_color_rmw` / `gfx_calc_addr` verbatim; the only new tenant code is the
Bresenham/box loop and the DI-per-pixel bracket (§2).

**4.4 Clip = masking; perf note.** Masking iterates every major step even when
off-screen, so `LINE(-32768,0)-(32767,0)` walks 64 K steps (~1 s, but EI so music
plays). Acceptable for G3 (extreme edge); a future optimization may fast-forward the
error term across an off-screen span **without changing the plotted pixels** — deferred
(§9 G3-perf), correctness before speed.

---

## 5. Box forms `,B` / `,BF` (measured, §11.4)

Corners `(x1,y1)`,`(x2,y2)`. `,B` draws the **four edges** inclusive
(`LINE(1,1)-(14,10),15,B` → top/bottom rows `y=1,10` over `x=1..14` and left/right
cols `x=1,14` over `y=1..10`). `,BF` **fills** the rectangle (all `x∈[x1,x2],
y∈[y1,y2]`). Implementation: `,B` = four axis-aligned segments through the pixel op;
`,BF` = a run of horizontal segments (`min(y1,y2)..max(y1,y2)`). Corners are
normalized (`min`/`max`) so reversed corners draw the same box — **G3-box residual**:
verified for sorted corners; the gate adds one reversed-corner case (§8). Box pixels
clip by the same per-pixel mask (§4.2) and take the clash color (§4.3). `GRPAC` after a
box = `p2` (the second corner) — measured `LINE(10,10)-(30,20),B` → `GRPAC=(30,20)`
(§11.5).

---

## 6. Work-area contract + marshalling ABI

**Work area (resident writes, §11.5).** After a `LINE`/box, `GXPOS/GYPOS` **and**
`GRPACX/GRPACY` = `p2` (the endpoint / second corner) — the standard MSX behavior
(arc §11.5, and G3 `grpac_line`/`grpac_box`). `CLOC/CMASK` = the last drawn pixel's
address+mask (tenant-written, as G2). The STEP-chain (§3.3) needs the **first**
endpoint as the reference while parsing the second: the resident stub resolves `p1`
(STEP rel `GRPAC`), stages it as the running reference (write `GRPACX/GRPACY=p1`
before parsing `p2`, then overwrite with `p2` at the end — reuses `parse_coord`
verbatim), resolves `p2` (STEP rel `p1`), then draws and sets `GRPAC=p2`.

**Tenant ABI (append-only param cells).** New op `GFX_OP=3` (line/box). Marshal the
**two int16 endpoints + color + mode** in own-design cells appended after `GFX_REL`
([basic/sysvars.inc:392](basic/sysvars.inc), `$E033`; allocate `$E034+` after a
live-map check, the G2 discipline): `GFX_X1/GFX_Y1/GFX_X2/GFX_Y2` (2 B each, int16 LE),
`GFX_C` (reuse, resolved color 0..15), `GFX_MODE` (0=line, 1=box outline, 2=box fill).
The resident stub sets these, `push hl` (guard the token cursor — the `ex_play`
lesson), `subrom_call IX=SUBROM_ENTRY_BASE_P0+3*8`, `pop hl`. The reference-faithful
`GXPOS/GYPOS/GRPAC` cells are written **resident** (the stub holds the coords); the
tenant reads its own `GFX_*` block for the geometry.

---

## 7. Token dispatch + the `LINE INPUT` disambiguation (measured, §11.1)

`LINE=$AF` reaches `ex_line` already ([basic/interp.asm:170](basic/interp.asm),
[basic/files.asm:722](basic/files.asm)). Today `ex_line` requires `INPUT` next, else
`stmt_error` ("graphics LINE = Phase 3"). G3 flips that fall-through:

```
ex_line: inc hl ; skip_spaces
         a=(hl); cp INPUT_TOKEN ($85) -> z: LINE INPUT#/console  (existing path)
         else -> ex_line_gfx           (graphics LINE; repack-only, IF ROM_BASE<$4000)
```

Disambiguation is total and measured (§11.1): `LINE INPUT` crunches `AF 20 85 …`
(INPUT token follows); graphics `LINE` begins with `(`=$28, `-`=$F2, or `STEP`=$DC —
none of which is `$85`. On the **lean** build (`ROM_BASE≥$4000`) the else-branch stays
`stmt_error` (no graphics), so the lean cart is byte-identical. The `-` between the two
coordinate parens is the ordinary minus token `$F2`, so the resident walk consumes a
`$F2` between `parse_coord` calls (not a fresh eval).

---

## 8. Gates (Definition of Done, G3)

- **`make graphics-acceptance` extended** — add a `LINE` phase to
  [basic_probe_graphics.py](probes/basic/basic_probe_graphics.py): a **VG-8020
  differential** that draws each case on both machines, reads the **pattern AND color**
  planes of the covered band back (`vram_segs`, the G2 method), and asserts
  byte-identical. Battery (each a pinned §11 fact ⇒ known oracle):
  - the four rasteriser shapes (shallow/steep/diag/neg) — exact pixel set.
  - **direction-independence**: `LINE(20,7)-(0,0)` ≡ `LINE(0,0)-(20,7)`.
  - **clip**: `LINE(-100,-100)-(50,50)` on-screen band = `y=x`; `LINE(0,0)-(300,300)`
    no error; fully-off = blank. Plus a **fractional-slope, off-screen-start** case to
    settle the masking-vs-reseed residual (§9 G3-clip).
  - **continuation** `PSET(3,3):LINE-(3,12)`; **STEP chain**
    `PSET(10,10):LINE STEP(2,2)-STEP(3,3)` → `(12,12)-(15,15)`.
  - **box** `,B` (4 edges) + reversed-corner case; **`,BF`** fill; color plane of a
    clash line (`…,6` → `$61`).
  - **errors**: ERR 6 (`(32768,0)`), ERR 5 (SCREEN 0/1, incl. `,BF`), ERR 2
    (`LINE(5,5)`, bare `LINE`, bad suffix). `(-32768,0)` = no error (valid int16).
- **Host unit tests** (`make unit-test`) for the pure rasteriser: the §11.3 captured
  bitmaps as the oracle for the Bresenham point-set (both directions), the box edge/fill
  point-sets, and the STEP-chain arithmetic. Locks the math emulator-free — the crux-1
  de-risker, already prototyped in
  [scratchpad/g3_bresenham_fit.py](../scratchpad/g3_bresenham_fit.py).
- **Teeth / anti-green-build:** confirm during bring-up that (a) perturbing the
  `2·err ≥ dx` threshold makes the shape cases fail, and (b) dropping the fetch-window
  settle in the LINE read path regresses the differential (the §2 G3-x race, the G2
  Heisenbug's home) — the [memory: error-handling-arc] discipline.
- **G1 floor + G2 gates still green** (`graphics-floor-acceptance`, the G2 phases,
  `unit-test`): `GFX_OP=0/1/2` unchanged; the new selector arm must not regress them.
- **Build wiring:** `sub/graphics.asm` already in `SUB_PARTS` — force-rebuild the
  sub-ROM (selector grows an arm), add the resident `ex_line_gfx` under the repack
  guard, **rebuild+reinstall the IPS** before the machine probe
  ([memory: makefile-subparts-stale-tenant], [memory: ips-rebuild-after-basic-change]).
- **Lean build byte-identical** — G3 is repack-only (runtime disambiguation keeps the
  lean `ex_line` fall-through = `stmt_error`).

---

## 9. Decisions — SIGN-OFF NEEDED

| # | Decision | Recommendation |
|---|---|---|
| **G3-a** | `LINE` runs in the page-0 tenant as `GFX_OP=3` (line+box), **EI between pixels, DI per-pixel RMW** — the D1 exercise (§2) | **Yes** — arc D1/D2/D5; first faithful EI-during-draw op |
| **G3-x** | The LINE per-pixel read uses **`gfx_rd_raw` (fetch-window settle) inside the DI bracket**, not G1's `gfx_vram_rd` (no settle) | **Yes** — both VDP races apply per pixel under EI ([memory: vdp-direct-port-read-fetch-window]); flag G1 `gfx_vram_rd` as latent-untested (self-test only writes-then-reads) |
| **G3-b** | Rasteriser = own-design integer Bresenham, **err0 / `2·err≥dx` / sort-major-ascending**; host-fit reproduces all four captured shapes + direction-independence | **Yes** — measured (§4.1/§11.3); captured bitmaps are the host-test oracle |
| **G3-c** | Off-screen ⇒ **clip by masking** (run true-endpoint Bresenham, plot in-range pixels), no error; fully-off = blank | **Yes** — measured (§3.4/§11.7); simplest model that matches |
| **G3-clip** | Masking-vs-Cohen-Sutherland-reseed is **indistinguishable** on the tested lines (both give the measured pixels) | Implement **masking**; the gate adds a fractional-slope off-screen-start case to catch a mismatch (§8) |
| **G3-d** | `STEP` **chains** — 2nd STEP relative to the 1st resolved endpoint; stage `GRPAC=p1` before parsing `p2` | **Yes** — measured (§3.3/§11.6) |
| **G3-e** | Box `,B` = 4 inclusive edges, `,BF` = scanline fill; corners normalized (min/max); `GRPAC=p2` | **Yes** — measured (§5/§11.4); gate adds a reversed-corner case |
| **G3-f** | Disambiguate graphics `LINE` from `LINE INPUT` at runtime in `ex_line` (INPUT-next ⇒ input; else ⇒ gfx); no new token | **Yes** — measured total (§7/§11.1); lean stays `stmt_error` |
| **G3-perf** | Masking walks every major step (huge off-screen spans slow but EI); error-term fast-forward | **Defer** — correctness before speed (§4.4) |

Implementation order (capture pass ✅ done, §11): resident `ex_line` disambiguation +
`ex_line_gfx` grammar walk (`-`, `,B`/`,BF`, STEP-chain) → host unit tests for the
Bresenham + box point-sets (fast, emulator-free, from the captured oracle) → tenant
`GFX_OP=3` (16-bit Bresenham + box + DI-per-pixel RMW reusing `gfx_color_rmw`/
`gfx_rd_raw`) → the `graphics-acceptance` LINE phase (pattern+color differential, incl.
the clip/teeth cases) → verify G1/G2 gates + `unit-test` still green → commit.

---

## 11. Pinned VG-8020 characterization (black-box, 2026-07-21)

Method as arc §11 (KEYBUF-injection via [omsx_repl.py](probes/lib/omsx_repl.py) on
`Philips_VG_8020`; VRAM read back mid-`GOTO`-self with `vram_segs`; behavior via
SCREEN-0-funnelled tags). Scripts:
[g3_line_characterize.py](../scratchpad/g3_line_characterize.py),
[g3_line_char2.py](../scratchpad/g3_line_char2.py),
[g3_line_char4.py](../scratchpad/g3_line_char4.py),
[g3_bresenham_fit.py](../scratchpad/g3_bresenham_fit.py). No ROM disassembly.

**11.1 Tokens / grammar** (stored-line crunch):
- `LINE(0,0)-(10,10)` → `AF (28 …) F2 (28 …) 00` — `LINE`=`$AF`, `-`=`$F2`(minus).
- `LINE-(10,10)` → `AF F2 (…)` — continuation (no first coord).
- `LINE(a)-(b),15,B` → `… 2C 0F 0F 2C 42`; `,BF` → `… 2C 42 46`; `,,B` → `… 29 2C 2C 42`.
- `LINE STEP(1,1)-STEP(2,2)` → `AF 20 DC (…) F2 DC (…)` — `STEP`=`$DC` per coord.
- `LINE INPUT A$` → `AF 20 85 …` — disambiguator: `INPUT`=`$85` follows ⇒ LINE INPUT.

**11.2 Rasteriser is direction-independent.** `LINE(20,7)-(0,0),15` renders the
**identical** bitmap to `LINE(0,0)-(20,7),15` (both = the shallow shape below).

**11.3 Exact pixel sets (pattern plane) + clash (color plane).** Captured bitmaps
(fg 15 on bg 1); the fitted variant (§4.1) reproduces each exactly:
- shallow `(0,0)-(20,7)` run-lengths per `y`: `2,3,3,2,3,3,3,2`.
- steep `(0,0)-(7,20)`: the transpose.
- diagonal `(0,0)-(15,15)`: `x==y`. negative `(0,15)-(15,0)`: `x+y==15`.
- degenerate `(5,5)-(5,5)`: single pixel. Clash: `LINE(0,0)-(15,0),6` → color bytes
  `$61` (fg 6 | bg 1), i.e. per-pixel `PSET`-identical clash.

**11.4 Box.** `LINE(1,1)-(14,10),15,B` = 4 inclusive edges (rows `y=1,10` ×`x=1..14`;
cols `x=1,14` ×`y=1..10`). `…,BF` = filled `x∈[1,14],y∈[1,10]`.

**11.5 Work area.** `PSET(5,5):LINE(10,20)-(30,40)` → `GRPACX/GRPACY=(30,40)`;
`LINE(10,10)-(30,20),B` → `GRPAC=(30,20)`. (Arc §11.5 also pins `GXPOS/GYPOS` = p2 and
`LINE-(30,40)` setting all four to the endpoint.)

**11.6 Continuation / STEP chain.** `PSET(3,3):LINE-(3,12)` → vertical run `x=3,
y=3..12`. `PSET(10,10):LINE STEP(2,2)-STEP(3,3)` → segment `(12,12)-(15,15)` (2nd STEP
relative to the 1st endpoint `(12,12)`, not to `GRPAC (10,10)`).

**11.7 Clip.** `LINE(-100,-100)-(50,50),15` → on-screen band is exactly `y=x`,
`x∈[0,50]`; `LINE(0,0)-(510,190),15` → the on-screen Bresenham run; `LINE(300,300)-
(400,400)` → blank; `LINE(0,0)-(300,300)` → no error. On-screen pixels = masked ideal
Bresenham (masking-vs-reseed indistinguishable on these — §9 G3-clip).

**11.8 Errors** (ON-ERROR funnelled): `(0,0)-(32768,0)` → **ERR 6**; `(-32769,0)-(5,5)`
→ **ERR 6**; `(0,0)-(-32768,0)` → **no error** (valid int16); SCREEN 0/1 (incl. `,BF`)
→ **ERR 5**; `LINE(5,5)` (no `-`) / bare `LINE` / bad suffix `,X` → **ERR 2**.

---

## Appendix — sources

Inherited from the arc spec §0/§Appendix, G1 and G2: TMS9918A datasheet (GRAPHIC-2
planes, VDP ports), MSX2 TH (work-area `GRPAC*`/`GXPOS`/`CLOC`/`CMASK`/`SCRMOD`),
public MSX-BASIC language reference (`LINE` semantics, `STEP`, `,B`/`,BF`), the arc §11
pins, and the G3 capture pass (tokens/grammar, direction-independence, exact pixel
sets, box, clip, STEP chain, errors). **Own-design:** the coordinate/box grammar walk,
the Bresenham variant (host-fit, not lifted), the box scanline fill, the DI-per-pixel
EI-loop. No reference-ROM disassembly ([memory: no-reference-rom-disasm]).
