# SPEC — D-PAINTMC: PAINT joins SCREEN 3, and the own-design stop turns out to be faithful

Status: **✅ LANDED 2026-08-22.**
Predecessors: [`spec-basic-screen3.md`](spec-basic-screen3.md) §5 (which excluded
PAINT and named the reason) and [`screen3-scout-2026-08-22.md`](screen3-scout-2026-08-22.md)
§6 (the multicolour address model). Read §5 first — this spec is the sentence that
inverts it.
Baseline `abeccc2`: low **46 B** / main page 1 **4 B** / sub page 0 **3156 B** /
sub page 1 **1624 B**.

---

## 1. What shipped

`PAINT` is the last graphics statement that refused `SCREEN 3`. It no longer does,
and it takes the shared mode gate with its four siblings again.

| statement | SCREEN 3 before | after |
|---|---|---|
| `PSET` / `PRESET` / `POINT` / `LINE` / `LINE ,B/BF` / `CIRCLE` / `DRAW` | ✅ (D-SCREEN3) | unchanged |
| `PAINT` | **ERR 5** | ✅ |

## 2. 💰 Price — measured

| wall | before | after | spent |
|---|---|---|---|
| main page 1 | 4 B | **10 B** | **−6 (RECOVERED)** |
| main page-0 low | 46 B | 46 B | 0 |
| sub page 0 | 3156 B | **3079 B** | **77** |
| sub page 1 | 1624 B | 1624 B | 0 |

🎯 **THE MAIN-ROM WALL WENT UP, NOT DOWN.** D-SCREEN3 had to take
`gfx_point_gate` apart for PAINT alone — `call gfx_work_area` + `ld a,(SCRMOD)` +
`call gfx_mode_gate_s2`, 9 B, because PAINT was the one verb that still had to
refuse mode 3. One `call gfx_point_gate` is 3 B and does both halves. The narrow
entry point `gfx_mode_gate_s2` is retired with it. **I predicted 3 B and it was
6**: the prediction counted the `ld a,(SCRMOD)` and forgot that the split had
also cost a separate `gfx_work_area` call.

## 3. 🔴 What was actually wrong — and what was NOT

D-SCREEN3 §5's diagnosis was right and its remedy was wrong.

> **Right:** adjacent LOGICAL pixels share one 4×4 cell, so with the default
> border `B = C` the first cell painted to `C` instantly reads as a **border** to
> its own neighbours, and the span walk stops dead.

> **Wrong:** *"the fix is a flood engine that does not re-test painted cells"*.

The engine's own-design `== C` stop was the suspect, and it was named as such in
three places: `gfx_paint_inside`'s `; == C already -> CF=0 (own-design stop)`,
`gfx_paint_op`'s header (*"NOT measured by the pinned battery either way"*), and
`basic/sysvars.inc`'s `GFX_PSTK` block. **It is faithful.** §4 is the measurement.

What was actually wrong was the walk's **PITCH**, and nothing else: at pitch 1 the
next coordinate is inside the cell just painted, so the walk tests its own work.
At pitch 4 every step lands on a cell the fill has not touched.

## 4. ✅ The measurement — `scratchpad/paintmc_probe.py`, both references

### 4.1 The decisive fixture

Put a barrier **already coloured C** inside an otherwise open area, with a border
colour `B` that appears **nowhere** on the screen. Then the only thing that can
stop the fill is the `== C` rule.

```
SCREEN m : LINE(0,40)-(255,40),9 : PAINT(10,10),9,15
```

| row | reads | vg8020 | cf3300 | zerobas |
|---|---|---|---|---|
| `ac2.spread` | `POINT(10,0)` | 9 | 9 | 9 |
| `ac2.stop` | `POINT(10,60)` | **4** | **4** | 4 |
| `ac3.spread` | `POINT(10,0)` | 9 | 9 | ERR 5 → **9** |
| `ac3.stop` | `POINT(10,60)` | **4** | **4** | ERR 5 → **4** |

⚠️ **The `.spread` half is not decoration.** A 4 beyond the barrier agrees for a
second reason — a fill that never left the seed. Every `.stop` row is paired with
a row on the SAME program reading a point the fill must have reached.

🎯 **The `== C` stop is real, in SCREEN 2 AND in multicolour.** It also settles
the only termination argument multicolour has: with `C != B` a painted cell is
still `!= B`, so nothing but the `already C` rule can ever end the walk.

### 4.2 The border rule in multicolour is the OPPOSITE of SCREEN 2's

SCREEN 2's measured rule (the VG-8020 PAINT differential that shipped with G5) is
that a border is a **DRAWN** pixel whose colour is `B`; an **undrawn** pixel is
never a border whatever its colour. Multicolour has no pattern bit, and the
references say so:

| row | program | reads | both refs |
|---|---|---|---|
| `mb.b4.up` | `PAINT(10,10),9,4` (background is 4) | `POINT(10,0)` | **4** |
| `mb.b4.seed` | ″ | `POINT(10,10)` | **4** |
| `mb.b7.up` | `PAINT(10,10),9,7`, a 7 line at y=40 | `POINT(10,0)` | 9 |
| `mb.b7.far` | ″ | `POINT(10,60)` | 4 |
| `mb.dflt.far` | `PAINT(10,10),9` (B defaults to C) | `POINT(10,60)` | 9 |

So in MC: **border = colour == B**, full stop. `gfx_paint_read`'s MC arm returns
`Zf=0` unconditionally, which makes both callers correct without touching either.

### 4.3 🔴 And the SEED rule differs by mode — a prediction this slice got wrong

`mb.b4.seed` = **4** was not what I expected. The shipped SCREEN-2 rule, gated by
`basic_probe_graphics.py`'s `seed_on_wall_pixel`, is that the seed is painted
**unconditionally** — a seed placed exactly on a drawn pixel whose colour equals
`B` still floods past it. I predicted 9 and the references said 4. The twin pair
that settles it runs the SAME geometry in both modes:

```
SCREEN m : LINE(20,20)-(60,60),15,B : PAINT(20,20),9,15
```

| row | reads | vg8020 | cf3300 |
|---|---|---|---|
| `sd2.wall.seed` | `POINT(20,20)` | 9 | 9 |
| `sd2.wall.in` | `POINT(40,40)` | 9 | 9 |
| `sd3.wall.seed` | `POINT(20,20)` | **15 — still the wall** | **15** |
| `sd3.wall.in` | `POINT(40,40)` | **4 — never entered** | **4** |

⚠️ **It is the `== B` half ONLY, not "not inside".** A seed already coloured `C`
floods normally in multicolour — and, astonishingly, does *not* in SCREEN 2:

| row | program | reads | vg8020 | cf3300 |
|---|---|---|---|---|
| `sc3.up` | `SCREEN 3:PSET(10,10),9 : PAINT(10,10),9,7` | `POINT(10,0)` | **9** | **9** |
| `sc2.up` | the same in `SCREEN 2` | `POINT(10,0)` | **4** | **4** |

`sc2.up` is a **SCREEN-2 divergence this slice did not close** — see §7.

### 4.4 Shape rows — a concave notch through a ONE-CELL gap

```
SCREEN m : LINE(0,20)-(103,20),7 : LINE(108,20)-(255,20),7 : PAINT(128,8),9,7
```

The gap is x=104..107 — exactly one 4-wide MC cell. The seed is above the wall;
everything below is reachable only through that gap, and only by a walk that
re-extends a pushed span to its true width (`gfx_paint_extend_lr`'s own header).
Both references: `POINT(10,100)`=9, `POINT(128,60)`=9, `POINT(10,4)`=9, and the
wall itself `POINT(50,20)`=**7**, unpainted.

### 4.5 ⚠️ The apparatus failed first, and its own control caught it

Round 1 ran at `omsx_repl`'s default `step=2.5` and read `<NO OUTPUT>` on **every
SCREEN-2 row of all three sides — including its own known positive**. The raw
scrape is a blank *graphics* screen: the capture fired mid-fill.
`basic_probe_graphics.py`'s PAINT phase already carries the answer in a comment
("PAINT is genuinely SLOW in EMULATED time", `PAINT_STEP = 90.0`) and the reading
was only trustworthy once the probe used it. The `box*` rows — the smallest fill
that can exist — are now the first thing it runs.

## 5. The implementation

`sub/graphics.asm`, all of it inside the existing engine:

| piece | what |
|---|---|
| `gfx_paint_pitch` | writes `GFX_PPITCH` = 1 (SCREEN 2) / 4 (MC), once per statement |
| `gfx_paint_flood` | snaps the seed onto the lattice (`or 3` in MC) **and** gates it on `gfx_paint_passable` |
| 7 step sites | `ld hl,GFX_PPITCH` + `add a,(hl)` / `sub (hl)` / `cp (hl)` |
| `gfx_paint_read` | MC arm: `gfx_point_mc` + `cp $FF` (A preserved, Zf=0 always) |

🎯 **THE LATTICE CORNER IS LOAD-BEARING.** The seed snaps to `(x|3, y|3)` — the
**bottom-right** pixel of its cell — so every coordinate the flood holds is
`≡ 3 (mod 4)`. That is what keeps the two UPPER bounds exactly as they were:
**255 and 191 are lattice points in both modes**, so `cp 255` and `cp 191` are
still the right tests, and only the two LOWER edge tests had to become
"< pitch" — which is what `or a` already was, at pitch 1. An `(x|0, y|0)` lattice
would have needed 252 and 188, i.e. two more mode-dependent constants.

### 5.1 💰 One byte of RAM, and the number that bought it

The pitch was first read by CALLING a 4-instruction helper that asked `SCRMOD`, at
each of the seven sites. Measured on `tests/test_graphics.py`'s full-screen case C
(a 256×192 fill, the largest this project runs):

| build | Z80 steps |
|---|---|
| `abeccc2`, before the slice | **3,205,330** |
| pitch asked at every step | **4,339,041** — **+35 %** |
| pitch cached in `GFX_PPITCH` | **3,352,745** — **+4.6 %** |

+35 % on every SCREEN-2 PAINT, paid so that SCREEN 3 works, was too much — and it
blew that test's 4,000,000-step runaway guard, which would have meant *raising a
runaway guard to make a test pass*. `GFX_PPITCH` aliases G8's `VDP(n)=` index
cell, on the one-statement-at-a-time argument `DEFT_PTR` / `RDV_*` / `TGT_ADDR` /
`GFX_DBUF` / `GFX_CS_M1` / `GFX_VBUF` all rest on in that window, so it costs
**0 B of RAM** and the guard is untouched.

## 6. 🔬 Falsification — `scratchpad/paintmc_knives.py`

Five knives, five distinct predicted row sets, each MC knife carrying the two
SCREEN-2 rows as green controls and K-PM5 the reverse. The parser is calibrated
on three synthetic logs (clean / one planted divergence / one row deleted) before
any knife runs — two runners in this project have reported confident zeros
because their regex matched nothing.

| knife | claim | predicted to redden |
|---|---|---|
| K-PM1 | the MC pitch is 4 | `box3.in ac3.spread mb.dflt.far mb.b7.up sc3.up nt3.thru tm3.far` |
| ~~K-PM2~~ | ~~the seed gate is `!= B` **only**~~ | 🗑️ **retired** — see below |
| K-PM3 | MC never reports "background" | `mb.b4.up mb.b4.seed` |
| K-PM4 | the pitch applies UPWARD too | `ac3.spread mb.b7.up nt3.above sc3.up` |
| K-PM5 | SCREEN 2's pitch is 1 | `box2.in ac2.spread` |

🗑️ **K-PM2 WAS RETIRED THE SAME DAY, AND THE RUNNER IS WHAT NOTICED.** It cut
`call gfx_paint_passable` → `call gfx_paint_inside` in the seed gate.
[D-PAINTS2SEED](spec-basic-paints2seed.md) replaced that gate with one comparison
whose comparand is chosen by mode, the anchor stopped existing, and the runner
**aborted with `anchor matched 0x`** rather than scoring the other four and
printing a tally. The claim is not lost: `paints2seed_knives.py`'s K-S2S2 swaps
that comparand and predicts a **superset** of K-PM2's single row. The four
survivors re-ran EXACT against the new build.

**Result (at `8e75629`): 5/5 EXACT**, five distinct knife ROM hashes, source restored
byte-identical and both ROMs back to the baseline pair. ⚠️ **Five first-time
exacts is the shape this project distrusts** — so what carries it is not the
tally: the parser was calibrated on a planted log before the baseline ran, the
baseline read 0 divergent across all 15 rows, every knife's `sub.rom` hash is
distinct from the baseline's and from each other's, and the five predicted sets
are five DIFFERENT sets, each with the other mode's rows standing as green
controls. A knife that reddened everything would have proved nothing.

K-PM1's prediction is **not** "everything reddens", and deriving why is the point:
a pitch-1 walk still crosses cells sideways (`gfx_paint_passable` lets it through
its own paint whenever `C != B`) and still reaches the row above whenever `y-1`
happens to fall in the next cell row. What it can never do is leave the seed's own
cell row when the seed is not at a cell-row edge.

## 7. What is NOT claimed, and what is filed

* 🔴 **`sc2.up` — a SHIPPED SCREEN-2 divergence, filed not fixed.**
  `SCREEN 2 : PSET(10,10),9 : PAINT(10,10),9,7` then `POINT(10,0)` reads **4** on
  both references and **9** here: the references refuse a seed whose effective
  colour already equals `C`, and this engine paints it and floods. It is the
  mirror image of the rule §4.3 measures for multicolour, it is out of this
  slice's scope, and folding it in would mix a SCREEN-3 measurement with a
  SCREEN-2 behaviour change. `TODO.md`.
* 🔴 **`nt2.wall` — a second SCREEN-2 divergence, same status.** With the fill
  above a `,7` wall in the same 8-pixel colour group, both references recolour the
  wall pixel to 9 ("border eaten") and this engine leaves it 7. Filed.
* 🔴 **PAINT's BORDER DOMAIN — a rule this slice MEASURED and did not implement,
  and the one place D-PAINTMC makes an existing defect newly VISIBLE.** The
  references range-check `B`, and the bound depends on the mode:

  | `B` | SCREEN 2 (both refs) | SCREEN 3 (both refs) | zerobas, both modes |
  |---|---|---|---|
  | 15 | floods | floods | floods ✅ |
  | 16 / 255 | floods | **ERR 5** | floods |
  | 256 / −1 | **ERR 5** | **ERR 5** | floods |

  > **`B` is 0..255 in SCREEN 2 and 0..15 in MULTICOLOUR; outside that, ERR 5.**

  ⚠️ **The SCREEN-2 half is PRE-EXISTING and has nothing to do with this slice** —
  `ep_parse_b` does `ld a,e / ld (GFX_B),a` with no check at all, and the shipped
  row that covers this argument (`border16_flood_ok`, B=16) could never see it,
  because 16 is *inside* the SCREEN-2 domain. What D-PAINTMC changed is that the
  SCREEN-3 rows stopped agreeing by accident: before it, every SCREEN-3 PAINT was
  ERR 5, so `PAINT(10,10),9,16` gave the right answer for the wrong reason —
  [[a-case-that-agrees-can-agree-for-the-wrong-reason]] in its purest form.
  💰 **Priced and DECLINED here: ~21 B of MAIN PAGE 1, which has 10 B.** It needs
  a carve. And it needs one more measurement first: D-LINERR's ordering rule says
  *where* in the parse a check sits is itself a claim, and `PAINT(10,10),9,16,`
  (a 4th argument after an out-of-domain border) would separate ERR 5 from ERR 2.
  Filed in `TODO.md` as one item covering both modes.
* **Nothing is claimed about PAINT's SPEED in multicolour** beyond the step counts
  in §5.1, which are SCREEN-2 figures. No gate in this project measures time.
* **The span-stack capacity is unchanged** (120 entries). A 64×48 surface needs
  far fewer spans than 256×192, so multicolour cannot be the case that overflows
  it; the `ERR 7` path is untested in MC and stays so.

## 8. Gates

`unit-test` 59/59 · `deadcode` 0 dead both builds (+2 allowlisted) · `latch-check`
16/16 · `injector-check` · `diskdep-check` + `diskdep-selftest` 6/6 ·
`audit-citations` · `wall-assertion-check` · `redundant-load-check` ·
`rowshape-check` · `preflight-check`, plus the eleven emulator batteries — the two
graphics ones load-bearing, since this slice edits the graphics tenant.
