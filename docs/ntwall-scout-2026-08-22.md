# SCOUT — the `nt2.wall` divergence is not the one that was filed

Status: **MEASUREMENT ONLY. No code changed.** 2026-08-22, from `f80cc69`.
Subject: `TODO.md`'s *"A `,B` WALL SHARING A COLOUR GROUP WITH THE FILL IS
'EATEN' ON THE REFERENCES AND NOT HERE"*, filed by
[`spec-basic-paintmc.md`](spec-basic-paintmc.md) §7.
Probe: [`scratchpad/ntwall_probe.py`](../scratchpad/ntwall_probe.py), five rounds,
VG-8020 + CF-3300 + zerobas, boot-per-case. The references agree on **every row**.

---

## 1. What was filed, and the question it told the next reader to ask first

    SCREEN 2 : LINE(0,20)-(103,20),7 : LINE(108,20)-(255,20),7 : PAINT(128,8),9,7
    then POINT(50,20) reads 9 on both references and 7 here.

> ⚠️ *Ask FIRST whether the fill even paints the pixels in that group here,
> before touching `gfx_color_rmw`: a fill that never entered the group is a
> different defect from a clash resolved differently.*

**It did.** Sampling the whole wall row instead of one point of it:

| x at y=20 | 0 | 50 | 100 | 103 | **104** | **106** | **108** | **111** | 112 | 150 | 255 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| both refs | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 |
| zerobas | 7 | 7 | 7 | 7 | **9** | **9** | **9** | **9** | 7 | 7 | 7 |

🎯 zerobas ate **exactly the one colour group the fill entered** — `x=104..111`,
the group holding the gap — and no other, in either direction. That is not a
defect in `gfx_color_rmw`; it is the ceiling of the mechanism. Eating a group
needs the fill to PAINT a pixel in it, painting needs to REACH it, and every
pixel of the next group along the wall is a border until that group is eaten.
**The cascade cannot propagate, by construction.**

---

## 2. 🔴 And the control said something larger than the filed item

Take the gap away entirely — `LINE(0,20)-(255,20),7 : PAINT(128,8),9,7`:

| | (50,19) above | (50,20) the wall | (50,21) **below** | (10,100) far below |
|---|---|---|---|---|
| both refs | 9 | 9 | **9** | 9 |
| zerobas | 9 | **7** | **4** | **4** |

**With no gap at all, the references' fill gets past a solid full-width wall.**
The filed framing — a clash inside a shared colour group — cannot describe that:
there is no shared group, and nothing to cascade from.

---

## 3. 🎯 The instrument had to change: `POINT` cannot see this

`POINT` collapses the pattern bit and the two colour nibbles into one number, so
*"the wall reads 9"* cannot distinguish *painted over* from *recoloured under*.
`VPEEK` reads the bytes. SCREEN 2 keeps **one colour byte per 8 pixels per
scanline**, fg in the high nibble, bg in the low:

    off = ((y\8)*32 + (x\8))*8 + (y AND 7)     pattern = off     colour = $2000+off

| state, at x=50 | pattern | colour |
|---|---|---|
| fresh `SCREEN 2` | 0 | `$04` — fg 0, **bg 4** |
| after `PSET(50,20),7` | `$20` | `$74` — fg 7, bg 4 |
| after `LINE(0,20)-(255,20),7` | `$FF` | `$74` — fg 7, bg 4 |
| after `LINE(0,20)-(255,20),7,BF` | **0** | `$07` — fg 0, **bg 7** |

**All four rows are identical on all three machines.** Two consequences:

🔴 **A plain `LINE` wall is a genuinely DRAWN border on the reference too.** The
tempting explanation — that the reference walks through a wall that was never
really there — is dead. Its fill crosses a real border.

🔴 **`,BF` DOES NOT SET THE PATTERN BITS AT ALL.** A fully covered group is
written as *"background = 7"*, bits clear, on every machine. An undrawn pixel is
never a border, so a `,BF` wall is not a border on **any** of the three — which
dissolves three rows of this scout (`v.group8`, `h2b`, `h4b`) that agreed on all
three sides. They agreed for a reason that has nothing to do with the subject.
`POINT` reports the bg nibble for a clear bit, so they read as walls throughout.

---

## 4. 🔴 The actual divergence: the two engines write different bytes

After `LINE(0,20)-(255,20),7 : PAINT(128,8),9,7`, at x=50:

| row | both refs | zerobas |
|---|---|---|
| y=19 (above, filled on both) | `0` / `$09` — bits **clear**, **bg** 9 | `$FF` / `$94` — bits **set**, **fg** 9 |
| y=20 (the wall) | `0` / `$09` | `$FF` / `$74` — untouched |
| y=21 (below) | `0` / `$09` | `0` / `$04` — untouched |

> **The reference's PAINT writes a filled group as `pattern := 0, bg := C`.
> zerobas writes it as `pattern := $FF, fg := C`. Both `POINT`-read as C.**

⚠️ **THAT IS A DIVERGENCE THE SHIPPED GATE IS STRUCTURALLY BLIND TO**, and one
row of this scout proves it: with the group-aligned `,BF` wall, all three sides
read 9 at every sampled x — while the bytes behind those 9s are `0`/`$09` on the
references and `$FF`/`$94` here. **A row that agrees through the instrument it
was written for, and diverges underneath it.** Every PAINT row in
`basic_probe_graphics.py` PHASE H is `POINT`-sampled.

---

## 5. What bounds the reference at all — the control that stops this being unfalsifiable

Something must still stop the fill, or *"the references flood everything"* is not
a claim. `C == B` is what does it, and it is the SAME wall:

| `LINE(0,20)-(255,20),7` then… | (50,19) | (50,20) | (50,21) | (10,100) |
|---|---|---|---|---|
| `PAINT(128,8),7,7` — **C == B**, all three sides | 7 | 7 | **4** | **4** |
| `PAINT(128,8),9,7` — C != B, refs | 9 | 9 | 9 | 9 |
| `PAINT(128,8),9,7` — C != B, zerobas | 9 | 7 | 4 | 4 |

🎯 **So the wall's GEOMETRY decides nothing, and the filed item's "clash policy"
framing is the wrong frame.** This is
[`spec-basic-graphics-g5.md`](spec-basic-graphics-g5.md) §5's own dichotomy —
`C == B` bounded, `C != B` **floods the entire screen** — which was measured on a
BOX and holds here for walls too:

* a **1-row** plain-LINE wall: refs cross, zerobas stops;
* a **3-row** wall (three stacked plain LINEs): refs cross **all three rows**,
  zerobas stops at the first — so it is not a one-group effect with a bigger
  radius, it is unbounded;
* a **vertical** 1-px plain-LINE wall: **all three cross**, because there the
  8-pixel group straddles the wall and zerobas's eating mechanism does reach it.

> **zerobas reproduces `C != B` → floods everything only when a border pixel
> happens to SHARE a colour group with a pixel the fill can reach.** True for a
> vertical wall, false for a horizontal one, and half-true for the notch — which
> is the whole of the filed table.

---

## 6. 🔬 Apparatus faults found in this scout, and what they cost

* 🔴 **A ROW SCORED `zb=DIFF` TWICE ON A VALUE THAT WAS NOT ONE.** `v.thin` read
  `<NO OUTPUT>` on zb in rounds 2 and 4 and the summary printed `zb=DIFF` both
  times, because the readout compares faces and a missing capture is not equal to
  `9`. It is a **missing measurement** — the capture firing before the fill ends.
  At `NTW_STEP=240` all three sides read 9 and the row **agrees**. Had it been
  believed, this scout would have reported a vertical-wall divergence that does
  not exist.
  ⚠️ And round 4 *said* it would re-run it at a bigger step and then re-ran it at
  the same one, because the step was a module constant with no override. Saying
  what the fix is does not apply it.
* ⚠️ **A FIXTURE THAT WAS NOT WHAT ITS NAME SAID.** `h2`/`h4` were written as
  *"a wall 2 / 4 rows thick"* and `LINE(0,20)-(255,21),7` is a shallow **diagonal**,
  not a bar. The zb reading is what exposed it: `(50,20)=9` and `(50,21)=7` says
  the wall at x=50 is on row 21, which a bar starting at row 20 cannot produce.
  Re-asked with `,BF` — and `,BF` then turned out not to draw a border at all,
  which is §3.

---

## 7. What this replaces, and what it does not claim

The filed item is **retracted and replaced** by §5's statement. It was not wrong
about its row; it was wrong about the mechanism, and it pointed the next reader at
`gfx_color_rmw`, which is not where this lives.

**Not claimed here:**

* **No price, and no design.** Matching the reference means changing what a
  filled span WRITES (bits cleared, bg := C) — which is `gfx_plot_cur`'s contract,
  shared with PSET/LINE/CIRCLE/DRAW, all of which measurably agree today and must
  keep agreeing. That is its own slice with its own knives, not a fold-in.
* **Nothing about MULTICOLOUR.** SCREEN 3 has no colour table and therefore no
  clash; `nt3.wall` agrees and PHASE H-MC gates it.
* **Nothing about *why* the reference's walk crosses a border it can still see.**
  §4 says what it WRITES; it does not explain how the walk gets to the wall row in
  the first place, and no row here separates the candidate rules. That is the
  first thing the slice has to measure.
