# A graphics statement's error surface on an MSX1 — measurement notebook (2026-08-11)

Notebook for D-LINERR. The settled contract is
[`spec-basic-lineerr.md`](spec-basic-lineerr.md); this file is the provenance
trail — what was asked, on what, and what came back, including the readings that
refuted the question.

Sides: **Philips VG-8020** and **National CF-3300** (both black-box oracles) and
the zerobas repack. **210** rows, `make lineerr-characterize` (108 at D-LINERR;
§8 is D-PAINTSEED's 16, §9 is D-GIRDOM's 18, §10 is D-DRAWERR's 47 and §11 is
D-DSCALE's 21). `LINE`,
`PSET`, `CIRCLE`, `PAINT`, `DRAW`, `SCREEN`, `ON ERROR`, `ERR`, `RESUME`,
`STR$` and `PEEK` are core MSX-BASIC, present on every MSX1, so both references
are legitimate oracles for every row.

---

## 1. 🔴 The filed diagnosis was wrong, and reading the site was enough

D-STMTPEND (2026-08-09) deferred one row it could not close:

```
LINE (0,0)-((A$<5),1)        zerobas  ERR 5        both references  ERR 13
```

and both `TODO.md` and the probe's own DEFERRED dict recorded the reason as

> *"LINE raises its own `Illegal function call` **eagerly from inside its
> coordinate parse**, so it reaches NEITHER of this slice's two writers."*

**There is no ERR 5 anywhere in `parse_coord`.** `ex_line_gfx` opened with

    ld a,(SCRMOD) / cp 2 / jp nz,gfx_err5

— three instructions, before the first coordinate byte was looked at — and the
filed row runs in the boot default SCREEN 0 (its `CLS` does not change the mode).
So zerobas answered ERR 5 to a statement whose coordinates it never evaluated.
No emulator was needed to refute the diagnosis; the file was.

That matters beyond the bookkeeping, because the wrong diagnosis pointed at a
**per-driver** fix in LINE's coordinate walk. The right question — *where in the
statement does the mode refusal happen?* — is D-SCRERR's ordering shape one verb
over, and it is **not LINE's question at all** (§4).

---

## 2. Nobody had ever measured what a graphics statement REFUSES

`make graphics-acceptance` covers what LINE **draws**
([`spec-basic-graphics-g3.md`](spec-basic-graphics-g3.md)). Its error surface had
no denominator. One row is not a rule, so the probe sweeps

**(WHERE in the statement a fault happens) × (WHAT KIND of fault it is), crossed
with the SCREEN MODE.**

The position axis is structural rather than sampled: LINE's grammar is
`LINE [[STEP](x1,y1)] - [STEP](x2,y2) [,[c][,B|BF]]`, so every slot that reaches
a value is x1, y1, x2, y2 and c, and every slot that can *end* where a value was
required is swept as well. The fault axis is the four distinct pending codes
(11 / 6 / 5 / 13), each contributed by an expression evaluating to 0 so the row
says **which** fault survived, plus the coercion's own ERR 6 alone and together
with a pending code. The mode axis is complete for an MSX1: 0, 1, 2, 3.

---

## 3. The instrument: `[ E , X , Y ]`, because the screen cannot witness this

Every row changes the SCREEN mode, so a screen scrape is blind to its own
subject — the same wall that made D-STMTPEND defer `u.scr.dz` and made D-SCRERR
stop scraping. So the probe does not scrape, it **asks**:

```
10 ON ERROR GOTO 100
20 Q$="A":SCREEN 2:PSET(7,4):SCREEN 0
30 <the statement under test>
40 E=0:X=PEEK(&HFCB7)+256*PEEK(&HFCB8):Y=PEEK(&HFCB9)+256*PEEK(&HFCBA)
50 SCREEN 0:PRINT"[";E;",";X;",";Y;"]":END
100 E=ERR:X=PEEK(&HFCB7)+…:Y=PEEK(&HFCB9)+…:RESUME 50
```

`X`/`Y` are `GRPACX`/`GRPACY`, the **last-referenced point** — published MSX
system-variable addresses, and the identical read already ships in
`basic_probe_graphics.py` phases D/F, i.e. it is proven on both references.

**GRPAC is not decoration — it says how far the statement got.** Over the
`PSET(7,4)` seed, and with the LINE rows drawing `(11,12)-(20,21)`:

| reading | means |
|---|---|
| `(7,4)` | the statement moved nothing |
| `(11,12)` | the first endpoint was staged, and it then died |
| `(20,21)` | it ran to completion |

Staging p1 before parsing p2 is what makes `STEP` chain
([`spec-basic-graphics-g3.md`](spec-basic-graphics-g3.md) §3.3), so it is a side
effect **both** sides must have. It is the only window onto the statement's
interior that does not need a debugger, and it is what turns a one-bit answer
("which error code") into a two-bit one ("which error code, and how far did it
get before raising it").

---

## 4. What the references answer

### 4.1 The ordering, at LINE

| row | statement (SCREEN 0) | both references |
|---|---|---|
| `m.s0` | `LINE (11,12)-(20,21)` | ` 5 , 20 , 21 ` |
| `m.s0.tm1` | `LINE ((Q$<5),12)-(20,21)` | ` 13 , 7 , 4 ` |
| `m.s0.tm` | `LINE (11,12)-((Q$<5),21)` | ` 13 , 11 , 12 ` |
| `m.s0.dz` | `LINE (11,12)-(0*(1/0),21)` | ` 11 , 11 , 12 ` |
| `m.s0.ov` | `LINE (11,12)-(70000,21)` | ` 6 , 11 , 12 ` |
| `m.s0.syn` | `LINE (11,12)` | ` 2 , 11 , 12 ` |
| `m.s0.col` | `LINE (11,12)-(20,21),0*(1/0)` | ` 5 , 20 , 21 ` |
| `m.s0.box` | `LINE (11,12)-(20,21),,Z` | ` 5 , 20 , 21 ` |

Read down the third column and the rule states itself. **Every fault the two
MANDATORY endpoints can raise — a type fault, a deferred numeric one, an int16
overflow, a missing `-` — outranks the mode refusal. Not one fault in an
OPTIONAL argument does.** And the X,Y column sites it a second time,
independently of the error code: at `m.s0` the work area is already on (20,21)
when the mode is refused, so the refusal is *after* the work-area write, not
before it.

`m.s0.syn` is the sharpest of the eight: `LINE (11,12)` with the `-` missing is
`Syntax error` **in SCREEN 0**. A grammar fault after the first endpoint still
beats the mode.

### 4.2 It is the same rule at five verbs, and a NEGATIVE CONTROL said so

`n.pset0` (`PSET(20,21)` in SCREEN 0) was written as *"the wrong-mode rule at a
DIFFERENT verb, which this slice claims nothing about"*. It came back
` 5 , 20 , 21 ` on both references against ` 5 , 7 , 4 ` here — **the same
divergence as LINE's**. So the precheck is not LINE's; it belongs to
`gfx_err5`'s callers, and a fix that moved LINE alone would have shipped a
partial rule and left four verbs wrong with a green gate over them.

The control was reclassified into a new `v.*` class and the class was swept:

| row | statement (SCREEN 0) | both references | what it pins |
|---|---|---|---|
| `v.pset0.tm` | `PSET((Q$<5),21)` | ` 13 , 7 , 4 ` | PSET's coordinate outranks the mode |
| `v.pset0.col` | `PSET(20,21),0*(1/0)` | ` 5 , 20 , 21 ` | …its colour does not |
| `v.circ0.tm` | `CIRCLE((Q$<5),21),5` | ` 13 , 7 , 4 ` | CIRCLE's centre outranks it |
| `v.circ0.rt` | `CIRCLE(20,21),(Q$<5)` | ` 13 , 20 , 21 ` | **so does its RADIUS** |
| `v.circ0.c` | `CIRCLE(20,21),5,0*(1/0)` | ` 5 , 20 , 21 ` | …its colour does not |
| `v.paint0.tm` | `PAINT((Q$<5),21)` | ` 13 , 7 , 4 ` | PAINT's seed outranks it |
| `v.paint0.c` | `PAINT(20,21),0*(1/0)` | ` 5 , 20 , 21 ` | …its colour does not |
| `v.draw0` | `DRAW"U10"` | ` 5 , 7 , 4 ` | DRAW already agrees ⚠️ **and NOT for this reason — §10** |
| `v.point0` | `V=POINT(20,21)` | ` 0 , 7 , 4 ` | POINT has no precheck at all |

**`v.circ0.rt` is the row the design turns on.** CIRCLE has TWO mandatory
arguments, so "after the mandatory arguments" and "after the first one" are
different sites at that verb and only this row separates them. Without it the
cheaper one-site reading survives — and it is wrong.

`v.point0` is the control that keeps the whole `v.*` class honest: POINT works
in any mode by construction
([`spec-basic-graphics-g2.md`](spec-basic-graphics-g2.md) §11.8 / G2-e), so the
divergences above are about the **precheck** and not about "graphics in
SCREEN 0" generally. ⚠️ **And about the PRECHECK only** — §9.3 found a live
`POINT` defect this row is structurally blind to, because it reads `GRPAC` and
the defect was in `GXPOS`. A control is honest about the cell it reads.

### 4.3 Two corollaries that fell out of the sweep

**A LINE/PSET colour is a 0..15 RANGE CHECK (ERR 5), not a silent mask.**

| row | statement | both references | zerobas, before |
|---|---|---|---|
| `k.15` | `LINE (11,12)-(20,21),15` | ` 0 , 20 , 21 ` | agreed |
| `k.16` | `…,16` | ` 5 , 20 , 21 ` | ` 0 , 20 , 21 ` |
| `k.neg` | `…,-1` | ` 5 , 20 , 21 ` | ` 0 , 20 , 21 ` |
| `k.255` | `…,255` | ` 5 , 20 , 21 ` | ` 0 , 20 , 21 ` |
| `k.big` | `…,70000` | ` 6 , 20 , 21 ` | ` 6 , 11 , 12 ` |
| `k.pset16` | `PSET(20,21),16` | ` 5 , 20 , 21 ` | ` 0 , 20 , 21 ` |

`k.pset16` was written as the row that **keeps the colour fix honest** — if LINE
turned out to range-check, that row says whether the PSET/CIRCLE asymmetry is
the *reference's* or something this slice would be introducing by "fixing" LINE
into agreement with the wrong sibling. It answered ERR 5, so there is no
asymmetry: LINE, PSET, CIRCLE and PAINT all range-check, and zerobas's `and $0F`
at LINE **and** at PSET was the odd one out at both.

`k.big` is the useful ordering detail: `70000` is ERR 6 from the int16 coercion,
which happens *before* the range check, so an out-of-int16 colour reports
Overflow and not Illegal function call. Both references, both before and after.

**A list that ENDS where the colour was required is `Missing operand` (ERR 24).**

| row | statement | both references |
|---|---|---|
| `a.trailc` | `LINE (11,12)-(20,21),` | ` 24 , 20 , 21 ` |
| `a.trailcolon` | `LINE (11,12)-(20,21),:V=1` | ` 24 , 20 , 21 ` |
| `a.boxc` | `LINE (11,12)-(20,21),1,` | ` 2 , 20 , 21 ` |
| `a.boxcolon` | `LINE (11,12)-(20,21),1,:V=1` | ` 2 , 20 , 21 ` |

This is D-SCRERR's Missing-operand rule turning up at a second verb — and the
last two rows are why the `:` arm was **measured** here instead of copied from
`ex_screen`'s shape: the rule reaches the colour slot and stops. **One field
along, at the box keyword, the identical two shapes are ERR 2.** A guard written
by analogy would have made all four ERR 24 and been half wrong with no row to
say so.

### 4.4 The domain rows, which changed nothing and were worth running

`c.*` sweeps the int16 edges and the off-screen-but-legal range: `(300,21)` and
`(-1,21)` complete silently and still move GRPAC to the raw unclipped value
(`65535` for −1); `32768` / `-32769` / `70000` are ERR 6 with GRPAC left at the
staged p1; `20.6` truncates to 20. All agreed before and after. They are the
rows that say the coordinate rule is about **int16**, not about the screen —
i.e. that the ERR 5s elsewhere in the sweep really are the mode and not a
coordinate domain.

---

## 5. 🔴 Two rows read `<NO CAPTURE>` and were NOT defects

`c.32767` (`LINE (11,12)-(32767,21)`) and `c.m32768` came back `<NO CAPTURE>` on
zerobas in the first sweep, and would have been written up as two more
divergences.

They are not. At a longer window zerobas answers **exactly** what both
references answer (` 0 , 32767 , 21 ` and ` 0 , 32768 , 21 `). The cause is a
documented design choice: the tenant rasterises over the **true int16
endpoints** and masks per pixel, that per-pixel mask *being* the clip
([`spec-basic-graphics-g3.md`](spec-basic-graphics-g3.md) §3.4/§4.4), where the
references clip first and then walk ~250 pixels. A 32767-pixel span really is
walked pixel by pixel. Measured: **2.5 s no, 12 s yes, 40 s identical to 12 s.**

It is a speed difference, and this probe measures error surfaces, so the window
is widened for those two rows (`SLOW_ROWS`) rather than the finding being
mis-filed. Recorded here because the failure mode is general: **a probe's timing
budget is part of the apparatus, and a row that is merely slow reads exactly like
a row that is wrong.** The tell that separated them was that the two rows were
the only ones in the sweep whose *magnitude* was extreme rather than whose
*shape* was novel.

---

## 6. 🔴 The doc claim this slice set out to fix was never in a doc

The pre-slice code masked LINE's and PSET's colour with

    and $0F      ; use the low nibble (0..15); see G2 gate note

and the probe's own `k.pset16` comment restated that as *"PSET's colour is
documented as a SILENT `and $0F` MASK, **measured on the VG-8020**
(spec-basic-graphics-g2.md §11.9)"*.

**`spec-basic-graphics-g2.md` has no §11.9. It has no §11 at all** — its §11
references point into the *arc* spec, whose §11.9 is about token re-verification.
There is no "G2 gate note" either. And no doc in the tree states a domain for the
colour argument: [`spec-basic-graphics-g2.md`](spec-basic-graphics-g2.md) §3.4
covers only the *default* (`FORCLR` / `BAKCLR`) and §6 marshals `c` "already
resolved".

So the sequence was: an own-design mask shipped with a dangling pointer; the
pointer was later restated in a probe as a **measurement on a named machine**;
and the measurement never existed. Nothing in the tree could catch that — a
dangling `§11.9` is not a forbidden source, so `make audit-citations` is silent
on it, and no gate ever asked what `PSET(20,21),16` does.

The general shape, which is worth more than this instance: **a citation that
does not resolve gets *upgraded* on the way to its second reader.** The first
writer knew it was a note-to-self; the second read "measured on the VG-8020".

---

## 7. What was measured and left alone

* **SCREEN 3 draws on both references** (`m.s3`, `v.pset3`): ` 0 , 20 , 21 `
  there, ERR 5 here. zerobas has no SCREEN-3 pixel op at all, so its `cp 2`
  refuses the mode. That is a **whole-feature gap** — a second rasteriser and a
  second address/clash model — not an error-surface defect: this slice moved
  *where* the refusal happens, and the refusal itself is correct for every mode
  zerobas implements. Both rows are printed, marked `....`, excluded from the
  tally in both directions, and filed in `TODO.md`.
* **PAINT's off-screen-seed ERR 5 versus the mode ERR 5.** `ex_paint` tests the
  seed's range before the mode gate. Both faults raise ERR 5, so the error code
  cannot tell them apart and only the work area could — and the work area is
  written between them. Unmeasured; filed. ✅ **Measured 2026-08-11 — §8.**
* **DRAW.** `v.draw0` agrees already (` 5 , 7 , 4 ` on all three sides), so DRAW
  was left alone. Its argument is a string parsed by a tenant, so "the mandatory
  arguments" means something different there; naming it out of scope with a
  green row behind it is cheaper than guessing.
  ✅ **Measured 2026-08-11 — §10. The rule does NOT extend, and `v.draw0` could
  not have said so either way: its string is a LITERAL.**

---

## 8. D-PAINTSEED — §7's second bullet, measured (2026-08-11)

Contract: [`spec-basic-lineerr.md`](spec-basic-lineerr.md) §9. Same three sides,
same `[ ERR , X , Y ]` instrument over the same `PSET(7,4)` seed; 16 rows added,
the gate is now 124 rows.

### 8.1 The question, restated so it is answerable

`PAINT` answers ERR 5 to an off-screen seed **and** to a wrong SCREEN mode. Three
events are in play — the work-area write **A**, the mode gate **B**, the seed
test **C** — and D-LINERR had already pinned **A < B**.

🔴 **§7 asked for C versus B, and no row can answer that.** When a seed is both
off-screen and in the wrong mode, B and C raise the same code and leave the same
work area in either order. What a row *can* answer is **C versus A**: a seed that
never reaches A leaves GRPAC on (7,4), one that passes it leaves GRPAC on the raw
unclipped coordinate — the storage §4.4 already pinned at `LINE` (300 stays 300,
−1 reads back 65535). Since A and B are one call, C-below-A is C-below-the-gate,
and that is the whole of what was fixed.

### 8.2 What came back

Both references, identically, on all 16 rows:

```
p.off2    PAINT(300,100)      SCREEN 2     5 , 300 , 100        zb was  5 , 7 , 4
p.off0    PAINT(300,100)      SCREEN 0     5 , 300 , 100        zb was  5 , 7 , 4
p.neg2    PAINT(-1,100)       SCREEN 2     5 , 65535 , 100      zb was  5 , 7 , 4
p.oy2     PAINT(20,200)       SCREEN 2     5 , 20 , 200         zb was  5 , 7 , 4
p.step0   PAINT STEP(300,100) SCREEN 0     5 , 307 , 104        zb was  5 , 7 , 4
p.x256    PAINT(256,191)      SCREEN 2     5 , 256 , 191        zb was  5 , 7 , 4
p.y192    PAINT(255,192)      SCREEN 2     5 , 255 , 192        zb was  5 , 7 , 4
p.edge2   …,15,B:PAINT(255,191)            0 , 255 , 191        zb agreed
p.ov0     PAINT(70000,100)    SCREEN 0     6 , 7 , 4            zb agreed
```

**The work area moves first.** `p.off2` is the row that carries it: SCREEN 2 is
the mode where `PAINT` is legal, so the mode gate is out of the way and the only
thing that can raise there is the seed test — and it raises with GRPAC *and*
GXPOS already on (300,100). 13 of the 16 rows were red before the fix; every one
of the 16 readings was predicted exactly, value for value, before the run.

### 8.3 🔴 The row that was FILED could not have settled it

§7 named `PAINT(300,100)` in SCREEN 0. Knife **K-PS2** deletes the off-screen
test outright — and that row stays **green**, along with every other SCREEN-0/1
row in the class, because the mode gate above the hole answers with the same
code and the same work area. Only the seven SCREEN-2 rows move (all to
`<NO CAPTURE>`: an unchecked flood from an off-screen seed runs away).

So the named row measures "C is not above A" and nothing else; the row that keeps
the seed test alive is its SCREEN-2 twin, which nobody had named. **A filed row
is a guess about which reading carries the evidence** — the same class of claim
as a filed diagnosis (§1), and worth checking for the same reason.

### 8.4 🔴 A knife cut a different routine, and the tag is what caught it

The first K-PS1 runner replaced the first occurrence of

    call    gfx_point_gate      ; BC/DE/HL preserved

in `basic/graphics.asm`. That line occurs **three times**, and the first belongs
to `gfx_plot_stmt` — the path `PSET` takes. The knife aimed at `PAINT` removed
the work-area write from the probe's own **`PSET(7,4)` seed**.

§7.1's lesson, from a new cause: there the cut site was genuinely shared, here it
merely *looked* unique. The runner survived because it reads the **tag**, not the
values: `n.zork` failed, the probe exited 2 with every row marked `....`, and the
runner aborted with "the probe REFUSED TO SCORE" instead of reporting 29
movements. Every cut is now scoped to the routine's own region with its
occurrence count asserted — `replace(old, new, 1)` on a whole assembly file is a
guess, and a DRY'd file is exactly where that guess is wrong.

### 8.5 What K-PS3 could not separate, recorded as a MISS

K-PS3 (PAINT gates but never writes the work area) had its RED/GREEN sets exact,
but two per-row **value** predictions written with them were wrong: `p.ok2` and
`p.edge2` were predicted to fall back to the box's own last point and both came
back `<NO CAPTURE>`. `GXPOS/GYPOS` is not just this probe's instrument — it is
how the seed is **marshalled to the tenant** (`spec-basic-graphics-g5.md` §6), so
cutting the write cuts the argument passing too and the fill runs from stale
cells. At a verb whose ABI *is* the work area, "cut the instrument" and "cut the
subject" are the same cut.

---

## 9. D-GIRDOM — the same leaf at its SILENT callers (2026-08-11)

Contract: [`spec-basic-lineerr.md`](spec-basic-lineerr.md) §10. 18 rows added;
the gate is now 142 rows, 140 scored.

### 9.1 The question §8 left behind

§8 pinned `gfx_in_range`'s domain at `ex_paint`, the caller that **raises**. Two
callers decide a **silent** outcome from the identical leaf — `PSET`/`PRESET`
(off-screen → no plot) and `POINT` (off-screen → −1) — and nothing had asked
whether the references put the edge in the same place there.

`POINT`'s return value goes into the existing instrument as `PSET(V+1,V+1)`:
−1 → (0,0), a colour *c* → (*c*+1,*c*+1). The `+1` keeps it on the accepted
`PSET` path, so the encoding does not depend on the clip rule under test.

### 9.2 The domain agreed, and that answer is worth the rows

`0..255 × 0..191` at all three callers, with `(255,191)` accepted at each and
both off-by-ones refused, on both references. `PSET(-1,100)` leaves GRPAC on
`65535`, the same raw int16 storage §4.4 pinned at `LINE`. Sixteen of the
eighteen rows are a **confirmation**, and they were run because a shared leaf's
other callers are not covered by a measurement at one of them — the answer being
"the same" is a result, not a wasted sweep.

### 9.3 🔴 The two rows that diverged read a cell nobody had read

`ev_f_point`'s own comment says *"POINT is READ-ONLY: it resolves STEP against
the last point but does NOT move it"*, and three lines below it writes
`GXPOS/GYPOS` to marshal the target to the tenant.

```
w.pt.on     V=POINT(20,21)      GXPOS   refs  0 , 7 , 4    zb was  0 , 20 , 21
w.pt.step   V=POINT STEP(1,1)   GXPOS   refs  0 , 7 , 4    zb was  0 , 8 , 5
w.pt.off    V=POINT(300,100)    GXPOS   refs  0 , 7 , 4    zb      0 , 7 , 4
```

**`POINT` moves neither half of the work area on either reference.** The comment
was right and the code contradicted it in a cell the comment did not name.

⚠️ **`v.point0` cannot see this and never could.** It reads `GRPACX/GRPACY`,
which `POINT` does not touch on any of the three sides, so it is green under the
defect, under the fix, and under the knife that reinstates the defect. §4.2
promotes it as "the control that keeps the whole `v.*` class honest" — and it is,
about the **mode precheck**. A control is honest about the thing it reads.

### 9.4 🔴 My sharpest prediction was wrong, and wrong the other way

Written before the run: *"`w.pt.off` DIVERGES — if a reference's coordinate scan
writes GXPOS before the range test, which is exactly what §8 measured `PAINT`
doing, then an off-screen POINT leaves GXPOS on (300,100)."* Flagged in the same
file as "the row most likely to be wrong". It was: `w.pt.off` **agrees**, and the
two rows predicted to agree are the ones that diverged.

**15 of 18 exact; 3 wrong, including the one singled out.** The error was
extrapolating a rule measured at five **statements** to a **function**. The
work-area write is not something the coordinate scan does to everything it
parses — it is something the *statement* does with what the scan returned.
`POINT` parses the identical coordinate and writes nothing. **A rule's blast
radius is a claim too**, and this one was made by analogy rather than measured.

### 9.5 Two RED sets had to be corrected while being written

* **K-GD2** deletes the marshal write. The obvious RED set is "the `g.pt.*`
  rows" — but four of them are off-screen and the resident answers −1 *without
  calling the tenant*, so the cut cannot reach them. Only the two
  colour-returning controls move.
* **K-GD3** cuts the domain (`cp 192` → `cp 193`). The obvious row is
  `g.ps.y192` — but its reading is GRPAC, which moves to the raw coordinate
  whether the pixel plots or not, so the clip is *invisible* there. The rows
  that see it are `g.pt.y192` and `p.y192`, and `p.y192` had to be added to the
  knife's union to be scorable at all.

Both were caught by writing the prediction down before running. A runner that
scored first would have produced two MISSES and an explanation.

---

## 10. D-DRAWERR — the sixth verb, where the rule does NOT hold (2026-08-11)

Contract: [`spec-basic-lineerr.md`](spec-basic-lineerr.md) §11. 47 rows added
across six measured rounds; the gate is now 189 rows, 187 scored.

### 10.1 The question §7's third bullet left, and why one green row could not answer it

§7 recorded *"`v.draw0` agrees already (` 5 , 7 , 4 ` on all three sides), so
DRAW was left alone"*. `DRAW"U10"` is a string **literal**, and a literal's
evaluation can raise nothing — so that row reads ERR 5 whether the mode gate
sits above `str_eval` or below it. It is blind to the question it was cited for,
in exactly the way §8.3's `PAINT(300,100)` was.

Six rows can see it, and they only work by carrying a fault the string
expression can raise: `DRAW 5`, `DRAW (Q$<5)`, `DRAW (5<Q$)`,
`DRAW STR$(0*(1/0))`, `DRAW STR$(0*(1E38*1E38))` in the refusing modes, against
`DRAW 5` in SCREEN 2 as the control that the 13 exists at all.

### 10.2 The answer is NO, and a negative answer is a result

**`DRAW 5` in SCREEN 0 is ERR 5 on both references; in SCREEN 2 it is ERR 13.**
The mode is refused before the argument is evaluated. All six A-vs-B rows agree
across all three sides, `ex_draw`'s opening `cp 2` was right for the whole life
of G6, and D-LINERR's decline to touch it was right too.

⚠️ **Only ONE HALF of the rule was even askable here.** Its work-area half —
"moves the work area to the point its mandatory arguments resolve to" — is
vacuous at a verb whose mandatory argument is a string. `w.draw0` was added as
the GXPOS twin `v.draw0` never had (D-GIRDOM §9.3's lesson, applied before the
defect rather than after it) and reads ` 5 , 7 , 4 ` too.

### 10.3 🔴 The prediction that failed was mine, and the file refuted it

Written before the run: *"`ex_draw` still opens with the three instructions
D-LINERR deleted from `ex_line_gfx`; six rows predicted to diverge."* Zero did.
§9.4 had recorded *"a rule's blast radius is a claim too"* one slice earlier
after extrapolating from five statements to a function; this extrapolated to a
sixth **statement**, which felt like the safe direction and was not.

**15 of 26 exact in round 1.** The pattern is the useful part: every value
traced in the source was exact — the `B`/`N` prefix asymmetry, `gdrw_gxpos`'s
greater-y residue, `d.part2`'s incremental walk, the string domain — and every
value reached by analogy was wrong. Reading the artifact and reasoning from a
neighbouring measurement are not the same activity, and this slice priced the
difference at 11 rows.

### 10.4 What the controls found

**`DRAW A$` was `Type mismatch`.** `ex_draw` had no `skip_spaces`, so `str_eval`
was handed HL on the space after the token and returned "not a string operand".
DRAW took a literal and nothing else.

```
n.drawvar  A$="R10":DRAW A$            refs  0 , 17 , 4    zb  13 , 7 , 4
d.dz2      DRAW STR$(0*(1/0))          refs  11 , 7 , 4    zb  13 , 7 , 4
d.ov2      DRAW STR$(0*(1E38*1E38))    refs   6 , 7 , 4    zb  13 , 7 , 4
```

The route to it is worth recording because it was not a straight line. `d.dz2`
and `d.ov2` were written as GREEN CONTROLS and diverged; the obvious reading was
an ordering fault (`jp nc,gfx_typeerr` consulted before `check_expr_errors`), and
a fix for that was one edit away from being committed. Three rows stopped it:
`n.strdz`/`n.strov` (`A$=STR$(0*(1/0))`) **agree**, so the pending fault is
reported correctly everywhere else; `n.sprdz` **agrees**, so the byte-identical
sequence at `SPRITE$(n)=` does not have the defect; and `d.avar2` fitted neither
theory. `n.drawvar` was written only because of that misfit, and it is the row
that names the cause.

🔴 **`d.tm2` was green for the wrong reason**, and it is a row this slice had
just promoted as the control keeping §10.2's column honest. `DRAW 5` is 13 on
the references because the argument is numeric and was 13 here because the space
stopped the parse. A control is honest about the mechanism it exercises, not
about the answer it prints.

**Whitespace was ignorable only between commands.** The tenant header says
spaces and TABs are *"both measured to be ignorable anywhere"*; `gdrw_skipws`
had four call sites, all between commands.

```
d.spc2     DRAW"R 10"        refs  0 , 17 , 4    zb  5 , 8 , 4
d.sp.num   DRAW"R1 0"        refs  0 , 17 , 4    zb  5 , 8 , 4
d.sp.sgn   DRAW"R -5"        refs  0 ,  2 , 4    zb  5 , 8 , 4
d.sp.m1    DRAW"M 53,37"     refs  0 , 53 , 37   zb  5 , 7 , 4
d.sp.m2    DRAW"M53 ,37"     ALL THREE  0 , 53 , 37
```

`d.sp.num` says a space inside a NUMBER is ignored, so the rule is "skip before
every fetch" and the fix belongs in `gdrw_peek`. It was flagged in the
prediction file as the least-trusted row, on the grounds that its only support
was the same "anywhere" comment already caught being false — and it was exact.

### 10.5 The scale default, measured and filed

✅ **Answered in §11 (D-DSCALE, 2026-08-11).** The rule below holds; what this
section did not know is that `S4` is *also* wrong at one product, so the two
states coincide at `n = 8192` and the minimal discriminator is `8193`.

```
d.def32k   DRAW"BU32767"      refs  0 , 7 , 32773   zb  0 , 7 , 5
d.lit2     DRAW"BU40000"      refs  0 , 7 , 25540   zb  0 , 7 , 58308
d.s4.32k   DRAW"S4BU32767"    ALL THREE  0 , 7 , 5
d.s4.40k   DRAW"S4BU40000"    ALL THREE  0 , 7 , 58308
```

**`S4` and the boot default are different states on both references.** §3 of
`scratchpad/g6_draw_notes.md` fitted `distance = signed16((n×S) mod 65536) ÷ 4`
on five points and falsified it on seven more, and every one of those twelve set
`S` first. The model is right; the class it was fitted on never contained the
default, and the multiply is the identity everywhere except the wrap — so a
LARGE COUNT is the only observable that separates them. Filed, not fixed: it
changes what DRAW draws, and "never set" needs a sentinel `S4` cannot collide
with.

⚠️ `d.lit2` was written as a NEGATIVE CONTROL ("a 40000 count on the literal
path is accepted, so `d.sub2` is about the substitution path"). It is still true
as a control — `d.sub2` is ERR 6 on all three sides, so the two paths really do
have different domains on the references too — and it diverged on its *value*
while agreeing on its *verdict*. A control that pins one axis can be a witness on
another.

---

## 11. D-DSCALE — §10.5's residual, and the defect underneath it (2026-08-11)

**210 rows** (§10 left 189; this slice adds 21 in two rounds). The question:
*where does the never-set scale state live, and does `GFX_DANGLE` have the same
question?*

### 11.1 Round 1 — 10 of 11 exact, and the miss is the finding

Every value below was written down before the run
(`scratchpad/dscale_predictions.md`), traced through `sub/graphics.asm`'s
`gdo_dir → gdrw_arg_opt → gdrw_scale → gdrw_axis → gdrw_rotate → gdrw_move_rel`
chain over the probe's `PSET(7,4)` seed.

```
d.def10     DRAW"BU10"          all three   0 , 7 , 65530     ✓ predicted
d.def8k     DRAW"BU8192"        refs  0 , 7 , 57348   zb  0 , 7 , 8196    ✓
d.s4.8k     DRAW"S4BU8192"      refs  0 , 7 , 57348   zb  0 , 7 , 8196    🔴 MISS
d.defd40k   DRAW"BD40000"       refs  0 , 7 , 40004   zb  0 , 7 , 7236    ✓
d.defr40k   DRAW"BR40000"       refs  0 , 40007 , 4   zb  0 , 7239 , 4    ✓
d.a0.32k    DRAW"A0BU32767"     refs  0 , 7 , 32773   zb  0 , 7 , 5       ✓
d.c1.32k    DRAW"C1BU32767"     refs  0 , 7 , 32773   zb  0 , 7 , 5       ✓
d.post32k   DRAW"BU32767S4"     refs  0 , 7 , 32773   zb  0 , 7 , 5       ✓
d.prev32k   DRAW"S4":DRAW"BU32767"   all three   0 , 7 , 5                ✓
d.a0.10     DRAW"A0BU10"        all three   0 , 7 , 65530                 ✓
d.a1.10     DRAW"A1BU10"        all three   0 , 65533 , 4                 ✓
```

`d.s4.8k` was predicted ` 0 , 7 , 8196 ` **on all three sides** — a green
control. It is not green, and §12.2 of the spec is what came out of it.

### 11.2 The `GFX_DANGLE` fork, written down before the run

The brief asked for the angle question to be produced as a row *before* the
shape of the fix was chosen. The angle has no wrap of its own — its domain is a
checked `0..3`, and rotate-by-zero is the identity in any implementation — so
there is no way to ask it directly. `d.a0.32k` asks it **through the scale's
wrap** instead, and the two branches were priced in advance:

* full count ⇒ the cells are independent, the sentinel is `GFX_DSCALE = 0`, and
  `GFX_DANGLE` needs nothing;
* ` 0 , 7 , 5 ` ⇒ the boot state is a shared "no transform yet" flag any command
  arms, the sentinel must be written by `gdo_a` and `gdo_c` too, and the cheap
  edit is wrong.

Both references read the full count, and `d.c1.32k` says a `C` does not arm it
either. The cheap branch is the measured one. 🎯 **A fork with both branches
priced before the run is the cheapest form of "produce the row first"**: the
measurement chose the design instead of confirming it.

### 11.3 Round 2 — 10 of 10 exact, pinning `$8000` as a boundary

Round 1's miss gave exactly **one** data point ("`$8000` reads +32768"), and one
data point is not a rule. Round 2 reached the same product from five different
`(n,S)` pairs and put a green control one step to either side:

```
d.p8.s2    DRAW"S2BU16384"    $8000   refs 57348   zb 8196    DIFF
d.p8.s8    DRAW"S8BU4096"     $8000   refs 57348   zb 8196    DIFF
d.p8.s1    DRAW"S1BU32768"    $8000   refs 57348   zb 8196    DIFF
d.p8.s4b   DRAW"S4BU24576"    $8000   refs 57348   zb 8196    DIFF
d.p8.neg   DRAW"S4BU-8192"    $8000   refs 57348   zb 8196    DIFF
d.p7ffc    DRAW"S4BU8191"     $7FFC   all three 57349         ok
d.p8004    DRAW"S4BU8193"     $8004   all three  8195         ok
d.p0       DRAW"S4BU16384R5"  $0000   all three  0 , 12 , 4   ok
d.def8193  DRAW"BU8193"       —       refs 57347   zb 8195    DIFF
d.defneg   DRAW"BU-8192"      —       all three  8196         ok
```

All ten exact. The two neighbours are what turn "the references treat `$8000` as
positive" into a boundary claim rather than "the references do not wrap up
here".

### 11.4 🔴 `d.defneg` was measured GREEN on the UNFIXED tree

It is green after the fix too, and its agreement at HEAD is **two defects
cancelling**: the boot state wrongly multiplies by 4, and the resulting `$8000`
gets the wrong sign, and the two errors compose to the right answer. The row
carries no information about either defect on its own — only about their
product. It is in K-DS1's predicted-RED set and in neither of the other two
cuts', which is the only way the tree can state that.

### 11.5 What this slice cost in wrong predictions, as a number

**20 of 21 row predictions exact on the first attempt**, plus 4 of 4 on the
price and the walls. The single miss is `d.s4.8k`, and its two halves split the
way §10.8 predicted they would: **the zb column, traced through the source, was
exact; the reference column, extrapolated from a fitted model, was wrong.** The
model in question (`scratchpad/g6_draw_notes.md` §3) was fitted on five points
and falsified on seven fresh pairs — nineteen readings, not one of them at
`$8000`, because a fit-then-falsify method finds a single-value exception only
by landing on it exactly.
