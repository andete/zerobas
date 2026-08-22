# SPEC — D-PAINTS2SEED: the other half of PAINT's seed rule

Status: **✅ LANDED 2026-08-22.**
Filed by [`spec-basic-paintmc.md`](spec-basic-paintmc.md) §7 the same day, as one of
three divergences that slice measured and deliberately did not close.
Baseline `8e75629`: low **46 B** / main page 1 **10 B** / sub page 0 **3079 B** /
sub page 1 **1624 B**.

---

## 1. 🔴 A rule stated far more broadly than its evidence

`gfx_paint_flood`'s header has said this since G5:

> the seed pixel is **ALWAYS** painted and used as the flood origin,
> **UNCONDITIONALLY** — it is NOT skipped just because its own effective colour
> already happens to equal `GFX_B` *(or `GFX_C`)*.

It cites two measured cases, and both of them are gated rows that still pass:

| shipped row | seed sits on |
|---|---|
| `seed_on_border_still_floods` — `PAINT(100,100),7,1`, background 1 | **B** |
| `seed_on_wall_pixel` — a 15 wall, `PAINT(17,17),7,15` | **B** |

**Neither has a seed equal to `C`.** The parenthesis carried a claim no case had
ever tested, for a year, and it is false.

## 2. ✅ What the references actually do — three geometries, both machines

```
SCREEN 2 : PSET(10,10),9 : PAINT(10,10),9,7        →  POINT(10,0)
SCREEN 2 : LINE(20,20)-(60,60),15,B : PSET(30,30),9 : PAINT(30,30),9,15
                                                    →  POINT(50,50)
SCREEN 2 : LINE(20,20)-(60,60),15,B : PSET(35,30),9 : PAINT(30,30),4,15
                                                    →  POINT(35,30)
```

| row | what the seed is | vg8020 | cf3300 | zerobas before |
|---|---|---|---|---|
| `sc2.up` | drawn, colour == C, open screen | **4** | **4** | 9 |
| `su2.drawn` | drawn, colour == C, inside a box | **4** | **4** | 9 |
| `su2.row.cbg` | **undrawn**, C == the background | **9** | **9** | 4 |
| `su2.row.ctl` | undrawn, C != background (control) | 9 | 9 | 9 ✅ |

> 🎯 **In SCREEN 2, PAINT paints nothing at all when the seed's EFFECTIVE COLOUR
> already equals `C` — drawn or not.**

The third row is what makes the rule broad rather than "drawn and == C". An
undrawn pixel's effective colour **is** the background by construction
(`gfx_paint_read`'s own header), so the undrawn half can only arise when
`C == background` — and there, a flood repaints the region with `C == bg`, which
the PSET clash rule turns into *clear the bit*. A flood therefore **erases** any
drawn pixel it crosses, and a refusal leaves it alone: 4 versus 9.

### 2.1 ⚠️ That third row took two fixtures, and the first one separated nothing

Draft 1 put the witness pixel at **(40,40)** — a different row from the seed. All
three sides read 9 and it looked like a clean confirmation. It is not: reaching
another row needs a **PUSH**, a push goes through `gfx_paint_inside`, and that
stops at `== C` on both sides. With `C == background` *every* undrawn pixel reads
`== C`, so no span is ever pushed, the fill never leaves the seed's row, and
(40,40) survives **whether the seed was refused or not**.

🎯 **The fix is geometric: put the witness on the SEED'S OWN ROW**, where
`gfx_paint_extend_lr`'s looser `passable` walk reaches it with no push involved.
Then the two hypotheses give 9 and 4. `su2.row.ctl` — the same geometry with a
`C` that is not the background — is what excludes "the fill never ran".

## 3. 🎯 The two modes are MIRRORS, so this is not one shared rule

D-PAINTMC measured multicolour's seed rule the day before, and it is the opposite
comparison:

| seed's effective colour | SCREEN 2 | MULTICOLOUR |
|---|---|---|
| `== B` | **floods** (`seed_on_wall_pixel`, `sd2.wall.*`) | **paints nothing** (`sd3.wall.*`, `mb.b4.*`) |
| `== C` | **paints nothing** (this spec) | **floods** (`sc3.up`) |

Every cell of that table is measured on both references. There is no single
predicate that produces it, which is why the implementation is one comparison
selected by mode rather than a shared `gfx_paint_inside` call — and why K-S2S1
and K-S2S2 below, which swap the two arms, redden *different* row sets.

## 4. 💰 Price — measured

| wall | before | after | spent |
|---|---|---|---|
| sub page 0 | 3079 B | **3075 B** | **4** |
| main page 1 | 10 B | 10 B | 0 |
| main page-0 low | 46 B | 46 B | 0 |
| sub page 1 | 1624 B | 1624 B | 0 |

🔴 **I predicted 8 B and it is 4**, and the 4 B I did not spend are the whole
story of §5.1: draft 1 wrote the seed into `GFX_PTESTX/Y` (two `ld (nn),a`, 6 B)
when what `gfx_paint_read` actually wants is D and E (two `ld r,a`, 2 B). The
correct version is both smaller and the one that works. `basic-reloc.rom` is
**byte-identical** — this is a tenant-only edit, and only `sub.rom` moves,
exactly as the two-ROM rule says.

## 5. The implementation

`gfx_paint_flood` already had D-PAINTMC's multicolour seed gate. It becomes one
admission test whose *comparand* is chosen by mode:

```
                call    gfx_paint_read      ; A = the seed's EFFECTIVE colour
                ld      b,a
                call    gfx_is_mc           ; Zf=1 iff MULTICOLOUR (clobbers A only)
                ld      a,(GFX_B)           ; MC: the border colour
                jr      z,gpf_seed_cmp
                ld      a,(GFX_C)           ; SCREEN 2: the paint colour
gpf_seed_cmp:
                cp      b
                ret     z                   ; not admissible -> paint NOTHING at all
```

`ld a,(nn)` does not touch flags, which is what lets `gfx_is_mc`'s Zf survive
across the comparand load and makes one test serve both modes.

### 5.1 🔴 The first version read the seed's colour out of register garbage

`gfx_paint_read` takes **D=y, E=x in registers**. It does *not* read
`GFX_PTESTX/Y` — `gfx_paint_inside` and `gfx_paint_passable` are the routines
that load D/E *from* those cells, and D-PAINTMC's multicolour gate got the
loading for free by calling `gfx_paint_passable`. Inlining the read to get at a
second comparand dropped it, and draft 1 stored the seed into the two sysvars and
compared against whatever colour D/E happened to address.

⚠️ **It was DETERMINISTIC, so it mostly agreed.** The tenant dispatcher leaves the
same D/E every run, so of the ten shipped PAINT rows **eight passed** — including
`mc_border_is_bg`, whose entire job is this gate — and two failed:

```
FAIL seed_already_c_noop    ref=[1, 9, 1]  zb=[9, 9, 9]
FAIL mc_seed_on_border      ref=[15, 4]    zb=[9, 4]
```

🎯 **The second one is a row that was PASSING before this edit**, which is what
made the cause unambiguous: a new rule cannot break an old row unless the edit
touched something the old row depended on. The differential caught it the first
time it ran, and the eight green rows are the reminder that a passing row is
evidence about a reading, not about a mechanism.

## 6. 🔬 Falsification — `scratchpad/paints2seed_knives.py`

| knife | claim | predicted to redden |
|---|---|---|
| K-S2S1 | SCREEN 2 compares against **C** | `sc2.up su2.drawn su2.row.cbg sd2.wall.in sd2.wall.seed` |
| K-S2S2 | MULTICOLOUR compares against **B** | `sd3.wall.seed mb.b4.seed sc3.up` |

Each knife swaps one arm for the other mode's comparand, so the two predicted
sets are disjoint apart from `sc3.up`, and each carries the other mode's rows as
green controls. 🎯 **K-S2S2's set is the interesting one to derive**: making
multicolour compare against `C` un-refuses the two `== B` seeds — but only their
`.seed` rows redden, because in both of those geometries the seed's neighbours
are border-coloured, so the fill paints the seed cell and goes nowhere. The
`.in`/`.up` rows stay green, and a prediction of "all four" would have been
over-specified.

## 6.1 🔴 And this slice made one of D-PAINTMC's knives go BLIND

Re-running the predecessor's knives against the new build is not ceremony. Two of
the five did not survive contact:

* **K-PM2 aborted the runner.** It cut `call gfx_paint_passable` in the seed gate,
  and that call no longer exists. The runner printed `anchor matched 0x` and
  refused, rather than scoring the other four and reporting a tally. Retired; its
  claim is a strict subset of K-S2S2's.
* 🔴 **K-PM3 reddened NOTHING, with the ROM provably moved** — the exact shape
  this project treats as a finding about the *knife*. It makes a background cell
  report "undrawn", and its two rows were `mb.b4.*`, where `B ==` the background.
  This slice's gate reads the seed's **colour** and ignores `Zf`, where the gate
  it replaced went through `gfx_paint_passable`, which consulted it — so in those
  rows the seed is now refused by colour alone and the walk, the only place `Zf`
  still matters, never runs.

🎯 **The repair is a fixture, not a weaker claim.** `PSET(10,10),9 :
PAINT(10,10),1,4` **draws** the seed, so it is admitted (colour 9 ≠ B 4) and the
walk then meets background-coloured cells as borders — which is what `cp $FF`
decides. Both references: `POINT(10,10)`=1 (the seed was painted) and
`POINT(10,60)`=**4** (the fill did not escape). Under K-PM3 the second goes to 1.
It ships as `mc_bg_border_walk`, and it is a strictly better row than the two it
rescues, because it survives changes to the seed gate by construction.

## 7. What is NOT claimed

* **The two rows that carried the old wording are unchanged and still pass** —
  `seed_on_border_still_floods` and `seed_on_wall_pixel`. This spec narrows the
  claim they were cited for; it does not contradict them.
* ⚠️ **`border16_flood_ok` is a weak row and this makes it weaker.** Its
  `PAINT(5,5),1,16` has `C == 1 ==` the background under `LINIT`, so under the
  rule measured here the reference **refuses it outright** — the row's four
  sample points read 1 whether anything was painted or not. It still gates what
  its name's second half means (a border of 16 does not raise), and nothing else.
  Not restructured here: changing a pinned row is its own claim.
* **Nothing is claimed about `C == B == the background`**, nor about a seed whose
  colour equals C in a mode this project does not implement.
