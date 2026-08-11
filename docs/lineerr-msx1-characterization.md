# A graphics statement's error surface on an MSX1 — measurement notebook (2026-08-11)

Notebook for D-LINERR. The settled contract is
[`spec-basic-lineerr.md`](spec-basic-lineerr.md); this file is the provenance
trail — what was asked, on what, and what came back, including the readings that
refuted the question.

Sides: **Philips VG-8020** and **National CF-3300** (both black-box oracles) and
the zerobas repack. 108 rows, `make lineerr-characterize`. `LINE`, `PSET`,
`CIRCLE`, `PAINT`, `SCREEN`, `ON ERROR`, `ERR`, `RESUME` and `PEEK` are core
MSX-BASIC, present on every MSX1, so both references are legitimate oracles for
every row.

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
| `v.draw0` | `DRAW"U10"` | ` 5 , 7 , 4 ` | DRAW already agrees |
| `v.point0` | `V=POINT(20,21)` | ` 0 , 7 , 4 ` | POINT has no precheck at all |

**`v.circ0.rt` is the row the design turns on.** CIRCLE has TWO mandatory
arguments, so "after the mandatory arguments" and "after the first one" are
different sites at that verb and only this row separates them. Without it the
cheaper one-site reading survives — and it is wrong.

`v.point0` is the control that keeps the whole `v.*` class honest: POINT works
in any mode by construction
([`spec-basic-graphics-g2.md`](spec-basic-graphics-g2.md) §11.8 / G2-e), so the
divergences above are about the **precheck** and not about "graphics in
SCREEN 0" generally.

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
  written between them. Unmeasured; filed.
* **DRAW.** `v.draw0` agrees already (` 5 , 7 , 4 ` on all three sides), so DRAW
  was left alone. Its argument is a string parsed by a tenant, so "the mandatory
  arguments" means something different there; naming it out of scope with a
  green row behind it is cheaper than guessing.
