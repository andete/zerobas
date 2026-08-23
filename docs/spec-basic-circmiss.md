<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-CIRCMISS — CIRCLE's dangling comma draws the circle and reports nothing

Status: **✅ SHIPPED, 7 B of sub page 1.** 2026-08-23, from `81ae426`.
The second of the three mechanisms
[`docs/spec-basic-missop.md`](docs/spec-basic-missop.md) §11.1 separated:
*a verb's own grammar swallows the dangling comma before `eval` is ever
reached*, so D-MISSOPFIX's evaluator fix could not touch it and correctly
predicted that it would not move.

**`sub.rom` moves and the two main images do not** — the right signature for a
`sub/*.asm` edit, and the opposite of D-MISSOPFIX's.

---

## 1. The defect, in one line of BASIC

    10 SCREEN 2
    20 CIRCLE(50,50),20,

Both references stop at line 20 with **`Missing operand`** and leave the screen
blank. zerobas **drew the circle and carried on**, reporting nothing at all.
Four slots do it, on two terminators each — **eight rows**.

## 2. The site, and the count the filing got wrong

`sub/circleparse.asm` is a sub-ROM **page-1 tenant**: main page 1 is switched
out while it runs, so it walks the token stream itself and REQUESTS each value
from the resident `ex_circle` servicer over `GFX_DREQ`. `eval` is therefore
never called on an operand the tenant has already decided is absent.

The filing named *"`cpt_at_c`, `cpt_at_start` and `cpt_after_aspect`"*. 🔴 **The
real set is four labels and `cpt_after_aspect` is not one of them.** The
property that matters is *reached only after a comma has been consumed*, and
that is exactly:

| label | line | reached from |
|---|---|---|
| `cpt_at_c` | :99 | `cpt_after_r` consumed the `,` after the radius |
| `cpt_at_start` | :130 | `cpt_start_intro` consumed the `,` introducing start |
| `cpt_at_end` | :153 | `cpt_after_start` / `cpt_start_empty` consumed a `,` |
| `cpt_at_aspect` | :179 | `cpt_after_end` / `cpt_end_empty` consumed a `,` |

`cpt_after_aspect` carries no such pair at all; `cpt_at_end` and `cpt_at_aspect`
do. Each of the four carries

    or      a
    jp      z,cpt_finish        ; end of statement AFTER the comma -> DRAW
    cp      COLON
    jp      z,cpt_finish        ; ':' after the comma -> DRAW

**Eight jump instructions**, and they are 8 of the **14** that reach
`cpt_finish`. ⚠️ `cpt_finish` is a SHARED TAIL and the other six are the
LEGITIMATE *"no more optional fields, draw"* exits — so the fix could not go on
`cpt_finish`, exactly as D-MISSOPFIX's could not go on `ev_f_err`.

## 3. The measurement — 17 rows × 3 machines, boot-per-case

`scratchpad/circmiss_probe.py` → `circmiss_before.out` / `circmiss_after.out`.
Readout `[ERR R]`: `ERR` is `0` when the statement COMPLETED and the MSX code
when it aborted; **`R` is `POINT(30,50)`** — the left cardinal point of the
radius-20 circle, read BEFORE the exit line's `SCREEN0:CLS`. SCREEN 2
background is `BAKCLR` **4** and `FORCLR` is **15**, so `R` says whether the
machine DREW and in which colour, not merely whether it complained. Both arc
boundaries used (0.1 and 6.2 rad) sit near angle 0, so the point read is deep
inside every arc and never on a boundary.

| row | statement | refs | zb before | zb after |
|---|---|---|---|---|
| `c.colour` | `CIRCLE(50,50),20,` | `24 4` | `0 15` 🔴 | `24 4` ✅ |
| `c.start` | `CIRCLE(50,50),20,5,` | `24 4` | `0 5` 🔴 | `24 4` ✅ |
| `c.end` | `CIRCLE(50,50),20,5,0.1,` | `24 4` | `0 5` 🔴 | `24 4` ✅ |
| `c.aspect` | `CIRCLE(50,50),20,5,0.1,6.2,` | `24 4` | `0 5` 🔴 | `24 4` ✅ |
| `k.colour` | `CIRCLE(50,50),20,:A=1` | `24 4` | `0 15` 🔴 | `24 4` ✅ |
| `k.start` | `CIRCLE(50,50),20,5,:A=1` | `24 4` | `0 5` 🔴 | `24 4` ✅ |
| `k.end` | `CIRCLE(50,50),20,5,0.1,:A=1` | `24 4` | `0 5` 🔴 | `24 4` ✅ |
| `k.aspect` | `CIRCLE(50,50),20,5,0.1,6.2,:A=1` | `24 4` | `0 5` 🔴 | `24 4` ✅ |
| `o.none` | `CIRCLE(50,50),20` | `0 15` | `0 15` | `0 15` ✅ |
| `o.colour` | `CIRCLE(50,50),20,,0.1,6.2` | `0 15` | `0 15` | `0 15` ✅ |
| `o.start` | `CIRCLE(50,50),20,5,,6.2` | `0 5` | `0 5` | `0 5` ✅ |
| `o.end` | `CIRCLE(50,50),20,5,0.1,,1` | `0 5` | `0 5` | `0 5` ✅ |
| `x.extra` | `CIRCLE(50,50),20,5,0.1,6.2,,` | `2 4` | `2 4` | `2 4` ✅ |
| `x.extra2` | `CIRCLE(50,50),20,5,0.1,6.2,1,` | **`2 5`** | `2 4` 🔴 | `2 4` 🔴 |
| `r.miss` | `CIRCLE(50,50),` | `24 4` | `24 4` | `24 4` ✅ |
| `r.nocomma` | `CIRCLE(50,50)` | `2 4` | `2 4` | `2 4` ✅ |
| `c.ok` | `CIRCLE(50,50),20,5,0.1,6.2,1` | `0 5` | `0 5` | `0 5` ✅ |

**17 scored. 9 DIFF → 1 DIFF.** The eight target rows all close; the one that
remains is `x.extra2`, which was never this slice's subject (§6).

### 3.1 The four `k.*` rows were UNMEASURED before today

§16 measured only the end-of-line arm. The `cp COLON` arm is a separate
instruction at each of the four labels and could have had a separate answer —
D-LINERR measured LINE's colour slot as **24** and LINE's *box* slot, one field
along in the same statement, as **2** for the same two shapes, and D-MISSOP
measured `COLOR 15,` as COMPLETING. **Slots do not inherit each other's verdict.**
Measured: all four `k.*` rows are `24` on both references, identical to `c.*`.

### 3.2 🔴 THE TRAP, WHICH IS THE WHOLE DESIGN QUESTION

An omitted optional argument **between commas** is legal MSX BASIC and must
keep drawing. `c.ok` does not cover it and §16 said so. The four `o.*` rows do,
and they are unanimous `0` + a drawn pixel on all three machines **before and
after**. They are not decorative: K-CM3 and K-CM4 (§5) each point one
legitimate exit at the new raiser and redden exactly one of them.

## 4. ✅ AS BUILT — 7 B, and the estimate was exact

    cpt_err24:                          ; beside cpt_err5 / cpt_err2
                ld      a,24            ; +2 B
                ld      (GFX_RES),a     ; +3 B
                jr      cpt_finish      ; +2 B

    8 × `jp z,cpt_finish` -> `jp z,cpt_err24`        0 B (same instruction)

**Walls, `make basic-reloc` from clean: sub page 1 free 1624 → 1617 B.** Exactly
the 7 the arithmetic predicted — which this tree's own rule says not to expect.
Main page 1 is untouched at 4 B free, low region at 10 B.

`GFX_RES` already carries an arbitrary ERR code to the resident: `ex_circle`'s
`cp_done` does `ld a,(GFX_RES) / or a / jp nz,raise_error` **before** the
`GFX_OP=4` geometry draw, so a raising exit cannot draw. The references agree —
`R=4`, no pixel, on all eight rows on both machines.

⚠️ **A 6 B VERSION EXISTS AND WAS DECLINED.** Collapsing the three raisers onto
a shared `ld (GFX_RES),a` tail costs 1 B net instead of 7. It was not taken:
sub page 1 has ~1617 B free, so the 6 B buys nothing, and it would restructure
two shipping error paths to save bytes nobody needs — creating exactly the kind
of shared tail this session's other slice was bitten by. **The diff is one new
label and eight retargeted jumps, and that is the point.**

## 5. 🔬 Knives — 4 of 4 EXACT, and two of them are the trap

`scratchpad/circmiss_knives.py` → `circmiss_knives.out`. Each cut is
size-neutral, cuts a VALUE (never a call — a deleted call fails `make deadcode`
and builds no ROM), is preceded by `rm -rf build`, restores by WRITING THE
BYTES, and **asserts `sub.rom` moved while `basic-reloc.rom` and the merged
image did not**. All four score the whole 17-row set, because a knife that only
sees the rows the fix was aimed at cannot speak for the rows it was aimed past.

    baseline  roms=abfefa7f / 490ffc49 / a8173c25   (17 rows match circmiss_after.out)
    K-CM1     roms=abfefa7f / 5ad60bad / a8173c25
    K-CM2     roms=abfefa7f / eac21e13 / a8173c25
    K-CM3     roms=abfefa7f / 5f5ef3e2 / a8173c25
    K-CM4     roms=abfefa7f / 6d858809 / a8173c25
    restored  roms=abfefa7f / 490ffc49 / a8173c25
    4/4 knife rows EXACT

| knife | the cut | predicted | moved | |
|---|---|---|---|---|
| **K-CM1** | `cpt_err24` `ld a,24` → `ld a,0` (`GFX_RES`=0 is *no error*, so the resident draws) | the 8 rows back to their pre-fix faces | 8 | EXACT |
| **K-CM2** | `ld a,24` → `ld a,5` | the same 8, reading `5 4` | 8 | EXACT |
| **K-CM3** | `cpt_at_c`'s `jp z,cpt_start_intro` → `jp z,cpt_err24` | `o.colour` alone | 1 | EXACT |
| **K-CM4** | `cpt_after_r`'s `jp nz,cpt_finish` → `jp nz,cpt_err24` | `o.none` alone | 1 | EXACT |

### 5.1 What each one established

* **K-CM1 re-creates the defect** and is what makes *"`x.extra2` is
  pre-existing"* a READING rather than an argument: under a cut that
  neutralises the new raiser entirely, `x.extra2` did not move.
* **K-CM2 separates two properties that look like one.** Under it the eight
  rows answer `5` — the WRONG error — and `R` is still **4**. 🎯 **It is the
  ABORT that protects the picture, not the particular code**, and only a knife
  scoring a drawn-pixel column can say so. This is D-MISSOPFIX's K-MO2 finding
  (wrong code, byte still intact) reproduced on a different subject, which is
  what makes it a property of the design and not of that slice.
* **K-CM3 and K-CM4 ARE THE SLICE'S REAL CLAIM.** Each points ONE legitimate
  `cpt_finish` exit at the new raiser — K-CM3 the omitted-slot-between-commas
  arm, K-CM4 the no-optional-fields arm — and each reddens **exactly one `o.*`
  row and nothing else**. Without them the four green `o.*` rows would be
  decoration: green because the fix is narrow, or green because they cannot see
  the failure at all ([[a-case-that-agrees-can-agree-for-the-wrong-reason]]).
  They can see it.

⚠️ **NOT CLAIMED:** the other six `cpt_finish` jumps are unknifed as a set —
K-CM3 and K-CM4 cover two of them, chosen because a row exists that reaches
each. The four `cpt_err2`/`cpt_err5` raisers are untouched and unknifed here;
`graphics-acceptance` owns them.

## 6. 🔴 What the `R` column found that an `ERR` column cannot see

`x.extra2` — `CIRCLE(50,50),20,5,0.1,6.2,1,`, a comma after a **complete**
argument list — is **`2 5` on both references and `2 4` here.** Both sides say
Syntax error, so an ERR-only probe scores the row **green**. They do not agree:

* the references **DRAW THE CIRCLE and then raise** Syntax error;
* zerobas raises without drawing.

**PRE-EXISTING** (identical before and after the fix, and unmoved under K-CM1)
and **structurally hard**: the tenant reports through `GFX_RES` and the
resident's `cp_done` tests it *before* issuing `GFX_OP=4`, so "draw, then fail"
is not expressible without a second flag. FILED, not folded in.

🎯 The general shape: `x.extra` (`...,6.2,,`) is `2 4` on all three — no draw.
So the reference draws at the moment its argument list is SATISFIED and checks
the terminator afterwards; when a slot is itself empty it errors first. That is
one rule, and it explains both rows.

## 7. The sibling sweep — 🔴 PAINT HAS THE SAME DEFECT, MEASURED

A tree-wide scan of all **63** `cp COLON` sites (every file under `basic/` and
`sub/`) for a non-error jump target found three other statement-grammar
candidates with CIRCLE's shape. `scratchpad/circmiss_siblings.py`, 9 rows × 3
machines:

| row | statement | refs | zb | |
|---|---|---|---|---|
| `p.colour` | `PAINT(50,50),` | `24 4` | `0 15` | 🔴 **DIFF — the same defect** |
| `p.kcolour` | `PAINT(50,50),:A=1` | `24 4` | `0 15` | 🔴 **DIFF** |
| `p.omit` | `PAINT(50,50),,15` | `0 15` | `0 15` | ✅ the legitimate omission |
| `q.ok` | `CLEAR 200` | `0 0` | `0 0` | ✅ control |
| `p.b` / `p.kb` | `PAINT(50,50),5,` (+`:`) | `24 4` | `<NO OUTPUT>` | ⚠️ NOT MEASURED |
| `q.trail` / `q.kcolon` | `CLEAR 200,` (+`:`) | `24 0` | `<NO OUTPUT>` | ⚠️ NOT MEASURED |
| `p.ok` | `PAINT(50,50),5,15` | `<NO OUTPUT>` | `<NO OUTPUT>` | ⚠️ NOT MEASURED, all three |

**9 printed, 4 scored, 2 DIFF.** ⚠️ Five rows are **NOT MEASURED, which is not
green** — the zerobas run never reached its `PRINT`, and `p.ok` fails on all
three machines, so that case is the instrument's fault and not a finding.

🎯 **The deliverable is still a size, not a guess**: `basic/graphics.asm`'s
`ep_default_b` is reached from **two** slots (:708 the colour, :727 the B
field), each on two terminators — **4 more jumps**, of which 2 are measured
divergent and 2 are unmeasured. **And unlike CIRCLE this IS byte-blocked: PAINT's
grammar is main page 1, which is 4 B free.** ⚠️ `CLEAR 200,` is **24 on both
references** and zerobas is unmeasured. Both FILED, neither folded in.

⚠️ **SHAPE IS NOT A VERDICT, and the sweep is why the rows were run rather than
assumed.** D-LINERR measured LINE's colour slot as 24 and LINE's *box* slot —
one field along, same statement — as **2**; D-MISSOP measured `COLOR 15,` as
COMPLETING. `basic/screen.asm`'s three `clr_apply` sites are that third shape
and are correct as they stand.

## 8. Gates — 34 of 34 green

`scratchpad/circmiss_gates.out` + `circmiss_gates/*.log`, from `rm -rf build`.
ROMs `abfefa7f` / **`490ffc49`** / `a8173c25` throughout.

`basic-reloc`, `unit-test`, `deadcode`, `wall-assertion-check`,
`redundant-load-check`, `rowshape-check`, `injector-check`, `preflight-check`,
`latch-check` **16/16**, `diskdep-check`, `switch-build-check`, `kwsweep`,
`deffn-selftest`, `string-acceptance`, `str-domain-acceptance`,
`strparen-acceptance`, `penderr-acceptance`, `missing-acceptance`,
`error-acceptance`, `error-trap-acceptance`, `onerr0-acceptance`,
`math-acceptance`, `float-acceptance`, `intarg-acceptance`,
`logicops-acceptance`, **`lineerr-acceptance` 210/210**,
`screenerr-acceptance`, `tmfp-acceptance`, `stmtpend-acceptance`,
`array-acceptance`, `deffn-strict`, **`graphics-acceptance` PASS**,
`abort-acceptance`, `interval-trap-acceptance`.

⚠️ **`latch-check` WENT RED ON THE FIRST PASS AND THE TREE WAS NOT AT FAULT.**
It is the one gate in the battery with **no prerequisites at all** (`Makefile`
:2498) — my driver ran it straight after `rm -rf build`, before anything had
built the merged ROM, and it refused: *"a probe booted against this machine
would report the absence of the ROM as the absence of the FEATURE."* Re-run with
the ROMs present: **16/16**. 🎯 The gate did exactly the right thing, and the
lesson is about the DRIVER: `repack-machine` must be first in any hand-rolled
battery, because most acceptance targets self-heal via their prerequisites and
this one cannot.

**`lineerr-acceptance` is the gate that caught D-MISSOPFIX's regression**, and
it was run here for that reason rather than for coverage: a fix inside a
grammar walk is exactly the shape whose blast radius a purpose-built probe's
denominator does not describe. 210/210.
