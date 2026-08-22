# SCOUT — SCREEN 3, priced for the first time (2026-08-22)

Status: **SCOUT ONLY — nothing implemented.** Baseline `98c0d14`, clean build,
low **46 B** / main page 1 **8 B** / sub page 0 **3299 B** / sub page 1 **1624 B**.
Instrument: `scratchpad/s3_scout_probe.py`, boot-per-case on **both** references.

`TODO.md` has carried SCREEN 3 as *"unpriced and never scouted — the largest
unknown on the list"* since the 2026-08-21 gap sweep. This prices it, and three of
the filed characterisations turn out to be wrong in the **cheap** direction.

---

## 1. What already works — SCREEN 3 is not the whole-feature gap it is filed as

| part | state today | evidence |
|---|---|---|
| the **mode switch** | ✅ works | `ex_screen` accepts 0..3 (`cp 4 / jp nc,gb_illegal`) and calls `CHGMOD` |
| **sprites** | ✅ work | `spr_assign` / `ex_put_sprite` gate on `or a` (any non-zero mode), not `cp 2` |
| the **VDP register layer** | ✅ present | `sub/graphics.asm`'s reprogram path already encodes *"group 3 (multicolor) -> M2"* |
| the **drawing algorithms** | ✅ reusable | Bresenham/line/box are mode-free — **464 B** already written |
| **pixel ops** | ❌ refused | two `cp 2` gates in `basic/graphics.asm` (`gfx_mode_gate`, and DRAW's own) |

So the gap is the **address model and the pixel primitives**, not the feature.

## 2. The coordinate model — MEASURED, and it is the big one

Round 1 showed `PSET(255,191)` "works" in SCREEN 3 on both references. ⚠️ **That
agrees for the wrong reason if a wrapped PSET and a wrapped POINT alias to the
same cell** — so round 2 asked a discriminating question. Both references agree
on every row:

| case | vg8020 | cf3300 | establishes |
|---|---|---|---|
| `PSET(0,0),7` → `POINT(3,3)` | `7` | `7` | (0,0) and (3,3) are **one cell** |
| `PSET(0,0),7` → `POINT(4,4)` | `4` | `4` | (4,4) is a **different** cell |
| `PSET(255,191),7` → `POINT(252,188)` | `7` | `7` | same aliasing at the far corner |
| `PSET(256,192),7` → `POINT(255,191)` | `4`, E=0 | `4`, E=0 | off-screen = **silent no-op** |
| `PSET(10,10),7` → `POINT(10,10)` | `7` | `7` | 16 colours per cell |
| `POINT(30,30)` untouched | `4` | `4` | background reads back; no clash |

> 🎯 **The SCREEN 3 logical coordinate space is 0..255 × 0..191 — IDENTICAL to
> SCREEN 2.** The 64×48 multicolour grid is a **hardware cell size**, not the
> BASIC surface: logical `(x,y)` addresses cell `(x>>2, y>>2)`. Off-screen is the
> same silent no-op SCREEN 2 has, with `ERR 0`.

**Three filed claims are corrected by this:**

1. 🔴 *"SCREEN 3 is 64×48, not a bitmap"* — true of the hardware, **false of the
   BASIC coordinate space**. Every filing that priced a second domain was pricing
   something that does not exist.
2. 🔴 *"needs a second address AND CLASH model"* — **the clash model disappears.**
   Multicolour has no colour table; each cell carries its own colour, so
   `gfx_color_rmw` (and the two-read back-to-back dance around it) has **no
   counterpart**. The twin is cheaper than the original.
3. ✅ **`gfx_in_range` needs no change at all** — the domain is identical. That was
   the one part of the cost sitting on main page 1, which has 8 B.

## 3. Measured sizes — the anchor for the price

From `build/sub.sym`, by **address range** (span sums undercount: the model splits
at every internal label).

| region | bytes | reusable in SCREEN 3? |
|---|---|---|
| `gfx_calc_addr` — bitmap address + bit mask | 33 | ✗ needs an MC twin |
| raw VRAM r/w + the VDP fetch window | 29 | ✅ mode-free |
| `gfx_plot` — PSET with the clash RMW | 67 | ✗ (and the clash half vanishes) |
| `gfx_point` + `gfx_color_rmw` + extract | 62 | ✗ |
| `gfx_plot_cur` / `gfx_rmw_at` — clip + RMW | 89 | ✗ (but the **clip bounds are identical**) |
| **address-model-dependent** | **280** | |
| line op + `gfx_draw_seg` | 70 | ✅ |
| Bresenham + `gfx_abs16` | 289 | ✅ |
| box outline | 105 | ✅ mostly |
| **algorithm, mode-free** | **464** | |

`sub/graphics.asm` occupies `$19FF–$2BD9` = **4570 B in sub PAGE 0**, which has
**3299 B free**. The rasteriser twin lands there, not on main page 1.

## 4. 💰 The price

| where | what | estimate |
|---|---|---|
| **main page 1** (8 B free) | widen two `cp 2` gates to accept mode 3 | **~6 B** |
| **sub page 0** (3299 B free) | MC address model + nibble RMW + point extract | ~80–110 B |
| | mode dispatch at `gfx_calc_addr`'s 6 call sites | ~20–30 B |
| | box-fill fast path variant (an MC byte is 2 cells, not 8 px) | ~30–60 B |
| | PAINT's run-scan variant | ~40–80 B |
| | **sub page 0 total** | **~170–280 B** |

**It fits in both walls as they stand today.** That is the headline: SCREEN 3 was
filed as blocked on a page-1 carve, and it is not — the ~6 B it needs on page 1
fits in the 8 B available, and the bulk lands in a page with 3299 B free.

⚠️ **Estimate, not measurement.** The MC VRAM layout has not been derived yet
(§6), and the project's rule is that a size from arithmetic is not a measurement.

## 5. 🔴 A DEFECT FOUND BY THE SCOUT — `POINT` in SCREEN 3 is a SILENT WRONG ANSWER

| case | vg8020 | cf3300 | zerobas |
|---|---|---|---|
| `SCREEN 3` + `POINT(30,30)`, nothing plotted | `0 , 4` | `0 , 4` | **`0 , 1`** |

**`POINT` does not gate the mode** — only the plotting ops do (`gfx_point_gate` is
called by PSET/LINE/…, but `gfx_point` is reached without it). So in SCREEN 3
zerobas reads the SCREEN-2 address model against multicolour VRAM and returns a
**wrong colour with no error**. Every plotting op honestly raises ERR 5; `POINT`
alone answers, and answers wrongly.

That is the silent-wrong-answer class — worse than the refusal it sits next to,
and **independent of implementing SCREEN 3 at all**: gating `POINT` the way its
siblings are gated would make it ERR 5 today. Filed in `TODO.md` as its own item;
it needs its own reference measurement of what `POINT` should do in SCREEN 3 (both
references answer `4`, i.e. they read the real cell — so the *fix* is the MC read
path, but the *stop-the-bleeding* option is the gate).

## 6. ✅ The MC VRAM layout — DERIVED 2026-08-22, both references

`scratchpad/mc_layout_probe.py`. Black-box throughout: the machine is asked with
`BASE()` and `VPEEK`, and no reference ROM is decoded.

### 6.1 The tables, from `BASE()` — asked, not guessed

| table | SCREEN 3 | SCREEN 2 (control) | SCREEN 0 (control) |
|---|---|---|---|
| name | **$0800** (2048) | $1800 | $0000 |
| colour | unused (0) | $2000 | — |
| pattern generator | **$0000** | $0000 | $0800 |
| sprite attr / pattern | $1B00 / $3800 | same | — |

🔴 **The first attempt read the wrong group and its CONTROL AGREED WITH IT.**
`BASE()`'s groups are 0–4 SCREEN 0, 5–9 SCREEN 1, 10–14 SCREEN 2, 15–19 SCREEN 3
— so `BASE(10..12)` read SCREEN 2 while the "control" `BASE(5..7)` read SCREEN 1,
**whose nominal bases are identical** ($1800/$2000/$0000). Two readings agreeing
said the *indices* were wrong, not that the answer was right. The control is now
the SCREEN-0 group, whose layout genuinely differs. And the `$1800` this replaced
was a **guess** that read a meaningless 32.

### 6.2 The fill byte, and the address model

After `SCREEN 3` the generator is filled with **$44** — both nibbles = colour 4,
the default background (measured, both references).

Plot one cell in colour 7, find the byte that stopped being $44:

| logical (x,y) | cell (x»2, y»2) | address | value | nibble |
|---|---|---|---|---|
| (0,0) | (0,0) | 0 | $74 | high |
| (4,0) | (1,0) | 0 | $47 | **low — shares the byte** |
| (8,0) | (2,0) | 8 | $74 | high |
| (0,4) | (0,1) | 1 | $74 | high |
| (0,8) | (0,2) | 2 | $74 | high |
| (0,32) | (0,8) | 256 | $74 | high |

> 🎯 **`addr = (cy>>3)*256 + (cx>>1)*8 + (cy&7)`, where `cx = x>>2`, `cy = y>>2`;
> the high nibble is the pixel with `cx` EVEN, the low nibble `cx` ODD.**

### 6.3 Verified against predictions written before the run

| case | predicted | vg8020 | cf3300 |
|---|---|---|---|
| `PSET(252,188)` → `VPEEK(1535)` | 71 (`$47`, low) | **71** | **71** |
| `PSET(128,64)` → `VPEEK(640)` | 116 (`$74`, high) | **116** | **116** |
| `PSET(5,5)` → `VPEEK(1)` | 71 (`$47`, low) | **71** | **71** |

⚠️ **One row of the sweep is NOT a reading:** `p.252.188`'s *scan* returned
`<NO OUTPUT>` on both references. Cell (63,47) lands at 1535 — the **last** byte —
so that scan ran all 1536 iterations where every other case exited within a few.
An **apparatus timeout**, and it is recorded as one rather than as a machine fact;
§6.3's direct `VPEEK` at the predicted address is what replaced it, and it is a
stronger row than the scan would have been.

### 6.4 What this does to the price

The address model is now **arithmetic on `x` and `y` with shifts only** — no
table, no multiply. Compare `gfx_calc_addr`'s SCREEN-2 body (33 B: a mask loop
plus three masks and a shift): the MC twin needs `(cy>>3)*256` (a high-byte
store), `(cx>>1)*8`, `(cy&7)`, and a nibble select. **It is the same shape and
about the same size**, and it replaces *both* `gfx_calc_addr` and the clash RMW,
since a nibble write needs no colour byte. §4's ~170–280 B stands, and its
largest single unknown is now closed.

## 7. What is still unmeasured — the named next experiments

1. **`PAINT` in SCREEN 3** — the flood fill's run scan is byte-oriented (8 px/byte
   in SCREEN 2, 2 cells/byte in MC).
2. **`DRAW` in SCREEN 3** — has its own `cp 2` gate; its scale/step rules are
   measured only for SCREEN 2.
3. **`CIRCLE` aspect** in a 4×4-cell surface.
4. **Whether `LINE ... ,B/BF` uses the same fast path** once a byte is 2 cells.
5. **What the NAME TABLE at $0800 must contain.** `BASE()` gives its address;
   nothing here measured its *contents*, and `CHGMOD` writes them — so an
   implementation that only touches the generator inherits whatever the BIOS
   laid down. Worth one `VPEEK` row before relying on it.

## 8. Provenance

Clean-room: every reading above is **black-box observation of screen output**
through this project's own probe harness. No reference ROM was disassembled. The
MSX-BASIC *language* (that SCREEN 3 exists and takes the same graphics statements)
is the public language reference; every behavioural rule here is our own
measurement. Same standing as `basic/PROVENANCE.md` §graphics.

## 9. ⚠️ The instrument, because it failed first

Draft 1 of the probe read **`<NO OUTPUT>` on all 21 rows, including the SCREEN-2
control**, and printed *"refs agree"* on every one. **A screen scrape cannot read
`PRINT` output while the VDP is in a graphics mode** — "the screen was blank" and
"the machine is still in SCREEN 3" are the same reading.

The **control is what caught it**: `ctl.s2` must read a POINT value on all three
sides, and it did not. The fix is `basic_probe_lineerr.py`'s `TRAP_PROG` shape —
capture into variables, force `SCREEN 0`, *then* print, with `ON ERROR` so a
refusal is a readable value (`E=5,V=-1`) instead of silence. It was re-calibrated
on that known positive (`0 , 15` on all three) **before** any SCREEN-3 row was
believed.
