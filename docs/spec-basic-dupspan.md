# SPEC — D-DUPSPAN: the byte-identical error tails, collapsed onto two names

Status: **✅ LANDED 2026-08-22.** A pure **funding** slice: no BASIC behaviour
changes, and that is the whole claim.

Filed by [`deffn-design-2026-08-22.md`](deffn-design-2026-08-22.md) §8 as the
survey that would pay for `DEF FN`. Baseline `d4e3037`, clean:
low **46 B** / main page 1 **4 B** / sub page 0 **3075 B** / sub page 1 **1624 B**.

---

## 1. What was carved

`ld a,N / jp raise_error` — five bytes — appeared **fourteen times** in the main
image under fourteen different names, in seven files. Eight raise ERR 5, six
raise ERR 2. Thirteen of them are now `equ` aliases of the other one.

The precedent is this tree's own, twice: `basic/interp.asm`'s
`err_illegal_fn equ err_illegal_fn_arr`, and then D-PAINTBORD's
`gfx_absent equ gfx_err5` (−5 B), whose comment states the rule this slice
applies thirteen times over:

> *the NAME survives because the two are different CLAIMS: if a later slice wants
> a distinct face for an absent tenant, un-alias it here and no call site moves.*

**Every name survives as an `equ`, and no call site was retargeted.** The only
edits at call sites are `jr` → `jp` widenings forced by distance.

| region | before | after | delta |
|---|---|---|---|
| main page 1 | **4 B** | **54 B** | **+50 B** |
| main page-0 low | 46 B | 46 B | 0 |
| sub page 0 | 3075 B | 3075 B | 0 |
| sub page 1 | 1624 B | 1624 B | 0 |

`build/sub.rom` is **byte-identical** across the whole slice (`b91622a9`), which
is the right answer: every edit is main-only and none of these files is shared
into a tenant.

---

## 2. The supply, and why the sweep's table is not the answer

[`scratchpad/dupspan_sweep.py`](../scratchpad/dupspan_sweep.py) walks the main
image's 1467 non-empty label-to-label spans and groups the byte-identical ones.
At `d4e3037` it reported **55 groups, 463 B "recoverable"**. That number is not a
price and the tool says so: it cannot see **fallthrough entries** or **`jr`
reach**, and both bite.

### 2.1 Fallthrough — the tool's blind spot, twice over

A span is byte-identical without being *entered* the same way.

* **`sw_illegal`** ([`basic/missing.asm`](../basic/missing.asm)) is entered by
  falling off `sw_absent`'s `pop hl`. Aliasing it away needs a `jp` in its place:
  **2 B recovered, not 5.**
* 🔴 **And the family the survey table ranked fourth is worth almost nothing for
  exactly this reason.** The sweep's `3 B ×6` group — six copies of a bare
  `jp raise_error`, 15 B nominal — has **five of its six members entered by
  fallthrough from a *different* `ld a,N` directly above**:

  | label | file | the `ld a,N` it falls in from |
  |---|---|---|
  | `ee_raise` | `interp.asm` | `ee_illegal: ld a,5` |
  | `sid_raise` | `strvar.asm` | `ld a,61` |
  | `tm_raise` | `time.asm` | `ld a,24` |
  | `exf_raise` | `field.asm` | `ld a,61` |
  | `gp_raise` | `field.asm` | `ld a,61` |

  Each would need a 3-byte `jp` to replace the 3 bytes removed. **Net zero.**
  Only `pl_parse_err` is not a fallthrough target, and its single caller is a
  `jr` that would have to widen — **net 2 B for the whole family.** It is
  DECLINED, and the reason is filed rather than the number.

🔴 The naive predecessor test — a regex like `^\s*(ret|jp|jr)` — gets this
wrong in both directions. `ret nz` and `jp nc,x` match it and are **not**
terminators. This slice used
[`tools/check_tenant_closure.py`](../tools/check_tenant_closure.py)'s
`_is_terminator`, the tree's own oracle, for exactly that reason.

⚠️ **And that oracle has its own blind spot, found here.** Walking back over
blank and comment lines to the previous instruction reports `ENDIF` as the
predecessor of `gfx_syntax`, and `ENDIF` is not a terminator — so the survey
called `gfx_syntax` a fallthrough target and it is not. Both arms of its
`IF G6_RESIDENT` end in `jp exec_stmt`. **A conditional-assembly directive is
not an instruction, and a linear walk that stops at one has stopped in the wrong
place.** The +22 B measurement is what settled it.

### 2.2 `jr` reach — the canonical is chosen by counting callers

A collapse moves the tail far away, so every caller reaching it with `jr` costs
1 B to widen to `jp`. Which member stays put is therefore not arbitrary:

* **ERR 5 → `gb_illegal`** (`interp.asm`), because it is the only member with
  `jr` callers that do *not* have to widen — three of its own local entries
  (`get_vram_arg`'s `jr`, `eval_pos_arg`'s `jp`, `gba_byte`'s `jr nz`). Picking
  `gfx_err5` instead would have cost 2 B more.
* **ERR 2 → `pl_syntax`** (`play.asm`), which has four local `jr` callers against
  `pc_syntax`'s three. Picking `pc_syntax` would have cost 1 B more; leaving
  *both* uncollapsed would have cost 2 B more than that.

### 2.3 The measured ledger

Predicted before the build, then assembled:

| family | site | file | entry | cost | net |
|---|---|---|---|---|---|
| ERR 5 | `gb_illegal` | `interp.asm` | — | **canonical** | 0 |
| | `snd_illegal` | `sound.asm` | `jr nc` | +1 | **4** |
| | `pl_absent` | `play.asm` | `jr c` | +1 | **4** |
| | `gfx_err5` | `graphics.asm` | 6× `jp` | 0 | **5** |
| | `fchk_ifc` | `files.asm` | `jr nz` | +1 | **4** |
| | `eoi_err5` | `program.asm` | `jr z` | +1 | **4** |
| | `strig_illegal` | `program.asm` | 2× `jp` | 0 | **5** |
| | `sw_illegal` | `missing.asm` | **fallthrough** | +3 | **2** |
| ERR 2 | `pl_syntax` | `play.asm` | — | **canonical** | 0 |
| | `elg_syntax` | `graphics.asm` | 2× `jp` | 0 | **5** |
| | `pc_syntax` | `graphics.asm` | 3× `jr nz` | +3 | **2** |
| | `ep_syntax` | `graphics.asm` | 2× `jp` | 0 | **5** |
| | `gfx_syntax` | `graphics.asm` | 11× `jp` | 0 | **5** |
| | `trap_syntax` | `program.asm` | 15× `jp` | 0 | **5** |

**Predicted 28 + 22 = 50 B. Measured 28 + 22 = 50 B**, in two separate builds
(`815bb553` → `7dd4a8f4` → `834c45b5`). The sweep's 463 B headline shrinks to
50 B for these two families once the two things it cannot see are read by hand.

---

## 3. Why the collapse is observable-free — proved, not assumed

The prompt for this work put the right objection: **D-LINERR's whole finding is
that *where* a check sits is itself a claim.** Eight sites raising ERR 5 are
eight different claims about *when* ERR 5 happens — so does merging their tails
merge the claims?

**No, and the reason is structural.** The collapse does not move a single check.
It removes the last two instructions each check `jp`s to, and those two
instructions are a pure function of `A`:

* `raise_error` reads **`A`** (into `ERRFLG`), then `record_errline` reads
  **`DIRECTF`** and **`CURLINE`** — sysvars, not registers, not the stack.
* `raise_error_hl` reads **`ONEFLG`** / **`ONELIN`**, then does
  `ld sp,(SAVSTK)` — **the stack is discarded**, so no site's pushes survive
  into it either way.
* The resume context comes from **`CURLINE`** and **`SAVTXT`**, both sysvars.
* `raise_error` is **never `call`ed** (checked: zero `call raise_error` in the
  tree). Every entry is a `jp`, so **no return address is pushed** and the entry
  site leaves no trace at all.

There is therefore nothing for a tail to carry except `A`, and `A` is what the
`ld a,N` sets. `sw_absent`'s `push ix / pop hl` — the one site whose comment says
it restores something "for the abort" — happens **before** the tail in both the
old and the new code, and `gb_illegal` does not touch `HL`, so its register state
at `raise_error` is byte-for-byte what it was.

---

## 4. 🎯 The knife the batteries cannot replace

**A green battery says the collapse broke nothing. It cannot say the collapse
was observable at all.** A tail that no row reaches would survive any mistake
made to it, and thirteen aliases are thirteen chances for a row set to have been
blind all along. So the falsification here is not "does it still work" but
**"can each collapsed site still be told apart from the others?"**

[`scratchpad/dupspan_probe.py`](../scratchpad/dupspan_probe.py) is one row per
site (18 rows, 13 named sites), read through `ON ERROR GOTO 900` +
`PRINT ERR` — which is not decoration: `raise_error` is **trappable** and
`stmt_error` is not, so a row that reached ERR 2 by the wrong mechanism would
abort the RUN and read `<NO OUTPUT>` rather than agreeing.

⚠️ **`pl_absent` has no row and cannot have one.** It is the defensive
"`subrom_call` reported the tenant missing" tail, unreachable on the merged
build — the same class as `gfx_absent`, D-PAINTBORD's own subject. Its collapse
is claimed on the assembler alone. **8 ERR-5 sites, 7 of them reachable.**

### 4.1 The gates, at this commit

Clean → `make repack-machine` → probe. All thirteen emulator batteries and every
static gate green, none of them moved by the carve:

| gate | result |
|---|---|
| `graphics-acceptance` | **383 PASS / 0 FAIL** |
| `lineerr-acceptance` | **210/210, 0 DEFERRED** — the gate most exposed here |
| `namspc-acceptance` | 102/102 |
| `fldwidth-acceptance` | 47/47 |
| `strparen-acceptance` | 16/16 |
| `cassave` / `castail` / `dskmsg` | 20/20 · agree · 15/15 |
| `diskbasic` / `fat-error` | 34/34 verbs · 11 scored, ALL PASS |
| `deffn-acceptance` | **0 of 8 controls failed**, 67/69 divergent (unchanged) |
| `deffn-selftest` / `latch-check` | 17/17 · 16/16 |
| `deadcode` | 1585 main spans, **0 dead** |
| `kwsweep` | MISSING=1 (`deffn`), unchanged |

⚠️ **`make` exits 2 for ANY failed recipe and the battery driver's
`&& … || …` list swallows a per-target failure**, so the driver's own exit 0
proves nothing. Every one of the thirteen `rc=` lines was read, and every log
checked non-empty.

[`scratchpad/dupspan_knives.py`](../scratchpad/dupspan_knives.py) — §5.


---

## 5. The knives — 5/5 EXACT

Baseline `('834c45b5','b91622a9')`. Every knife moved `basic-reloc.rom` and left
`sub.rom` at `b91622a9`, which is the right answer for a main-only edit; the
runner prints WHICH image moved, because a guard watching the wrong one halts
with the right verdict and the wrong reason. Restored to `834c45b5` with all
five sources byte-identical.

| knife | cut | predicted | got |
|---|---|---|---|
| **K-DS1** | `gb_illegal` `ld a,5` → `ld a,9` | **all 11 ERR-5 rows** | ✅ exact |
| **K-DS2** | `pl_syntax` `ld a,2` → `ld a,9` | **all 7 ERR-2 rows** | ✅ exact |
| **K-DS3** | `sw_absent`'s new `jp gb_illegal` → `jp gfx_typeerr` | `e5.swapnew` **only** | ✅ exact |
| **K-DS4** | `gfx_err5 equ gb_illegal` → `equ gfx_typeerr` | `e5.pset0` **only** | ✅ exact |
| **K-DS5** | `trap_syntax equ pl_syntax` → `equ gfx_typeerr` | `e2.oninterv` **only** | ✅ exact |

**What each one bought:**

🟢 **K-DS1 and K-DS2 have disjoint predicted sets and each is the other's green
control.** Eleven ERR-5 rows moved to ERR 9 and seven ERR-2 rows did not; then
the mirror. A knife that reddened both would have been a statement about the
apparatus — an address shift, a machine rebuilt wrong — and not about the tails.
**Every one of the thirteen reachable sites is genuinely exercised by a row**:
none stayed green, so none of these collapses was made blind.

🎯 **K-DS3 is the only knife aimed at code this slice WROTE**, and it separates
the two SWAP faults that used to be one span. `e5.swapnew` (`A=1:SWAP A,B`,
reaching the tail by falling off `sw_absent`'s `pop hl` into the new `jp`)
reddened; `e5.swap3` (`SWAP A,B,C`, reaching it by the surviving
`jp sw_illegal`) stayed green. The fallthrough repair carries exactly one of
them, which is what says the repair is load-bearing and correctly scoped.

🎯 **K-DS4 and K-DS5 prove the promise this carve inherits thirteen times over.**
`gfx_absent`'s comment says *un-alias here and no call site moves*. Retargeting
one `equ` gave that one name a distinct face (`gfx_err5`'s six call sites,
`trap_syntax`'s fifteen) and left its whole family untouched. **A collapse whose
knife reddens the whole family is a collapse that lost the distinction; these
say the distinction is one line away from coming back.**

⚠️ The parser was calibrated on a clean log, a planted one and a row-deleted one
**before** the baseline ran — the `APPARATUS: probe printed 17 of 18 rows` line
at the top of the log is the deleted-row calibration firing as designed, not a
failure.

### 5.1 The predecessor knives, re-run as a regression

This slice edits `basic/graphics.asm` (`gfx_err5`, `gfx_syntax`, `elg_syntax`,
`pc_syntax`, `ep_syntax`), which is `paintbord_knives.py`'s own subject — so
those four are a real regression test here, not a formality.

**All ten re-run, 10/10 EXACT** against the moved baseline
`('834c45b5','b91622a9')`, every suite restoring both images and its source
byte-identical:

| suite | cuts | rows |
|---|---|---|
| `paintbord_knives.py` | `basic/graphics.asm` — **this slice's own file** | **4/4 EXACT** |
| `paintmc_knives.py` | `sub/graphics.asm` | **4/4 EXACT** |
| `paints2seed_knives.py` | `sub/graphics.asm` | **2/2 EXACT** |

⚠️ **And the two-image guard earned its keep in both directions.** `paintbord`'s
knives move `basic-reloc.rom` and leave `sub.rom` at `b91622a9`; `paintmc`'s and
`paints2seed`'s move `sub.rom` and leave `basic-reloc.rom` at `834c45b5`. A
runner watching only one image would halt on half of these with the right
verdict and the wrong reason.

**15/15 knife rows EXACT across the four suites.**

---

## 6. 🔴 Three divergences the row set turned up — none of them this carve's

A probe built to prove a carve changed nothing found three places where zerobas
disagrees with **both** references. **All three predate this slice**: every one
of these dispositions is decided upstream of the tail, in code the collapse did
not touch, and the `zb` face of all eighteen rows is what it was before. They
are recorded here and filed in `TODO.md` because a new row set that finds
something and folds it into the commit that found it is how a finding gets lost.

⚠️ **Two of the three needed a SECOND fixture before they could be believed**,
and one of those turned out to be my own instrument.

### 6.1 It was the capture window, and then it wasn't

`e2.paint4` — `SCREEN 2 : PAINT(10,10),9,15,` — read `<NO OUTPUT>` on both
references and `ERR 2` on zerobas at `step=4`. 🔴 **A `<NO OUTPUT>` IS NOT A
DIVERGENCE, IT IS A MISSING MEASUREMENT.** At `step=90` (paintmc's proven
SCREEN-2 flood value) all three read `ERR 2` and the row agrees.

🎯 **But the ASYMMETRY is a measurement.** Same fixture, same boot, same step:
zerobas answered inside four seconds and neither reference did. The only
plausible consumer of those seconds is the fill — so the reference **paints
first and raises the 4th-argument Syntax error afterwards**, and zerobas raises
it before painting.

🔴 **A timing inference is not a measurement either, and the row written to
settle it could not reach its own case.** `x.paint4pt` put the `POINT` read on a
line *after* the `PAINT` — but a **trapped** error jumps straight to the
handler, so that line never runs and all three sides printed the trapped `ERR`.
The read has to happen **in the handler**, which is exactly how
`basic_probe_lineerr.py` captures `GRPACX`/`GRPACY`. With the handler moved:

| row | vg8020 | cf3300 | zerobas |
|---|---|---|---|
| `x.pt4.ord` — `PAINT(10,10),9,15,` then `POINT(10,0)` in the handler | **`2 9`** | **`2 9`** | **`2 4`** |
| `x.pt4.ctl` — `PUT SPRITE 0`, an ERR 2 from a statement that paints nothing | `2 4` | `2 4` | `2 4` |

> **Both references PAINT and then raise ERR 2. zerobas raises ERR 2 and paints
> nothing.** The control says the `9` is the fill and not an artifact of reading
> `POINT` from a handler: the same handler on a statement that paints nothing
> reads `4` on every side.

🎯 **D-PAINTBORD's `od2.b16c` row cannot see this**, and it is the row that owns
this exact statement shape. It scores the ERROR FACE, and both orderings produce
`ERR 2`. **No row scored the SIDE EFFECT, so a fix and a no-op read the same** —
D-FILESIDE's finding, in a different verb.

### 6.2 🔴 A characterization row that agreed for the wrong reason

[`docs/missing-vg8020-characterization.md`](missing-vg8020-characterization.md)
§4.5 records `SWAP A,B,C` → **`Illegal function call`**, and singles it out:

> *`SWAP A,B,C` raising `Illegal function call` where every other malformed
> shape raises `Syntax error` is the kind of detail that only a measurement
> produces.*

[`basic/missing.asm`](../basic/missing.asm) implements it as
`jp sw_illegal ; SWAP A,B,C -> Illegal function call`. **The row is true and its
generalisation is false**, and one axis the fixture never varied decides it:

| fixture | vg8020 | cf3300 | zerobas | |
|---|---|---|---|---|
| `SWAP A,B,C` — all undefined (**the doc's shape**) | ERR 5 | ERR 5 | ERR 5 | ✅ |
| `A=1:C=3` then `SWAP A,B,C` — **B undefined** | ERR 5 | ERR 5 | ERR 5 | ✅ |
| `A=1:B=2` then `SWAP A,B,C` — **C undefined** | **ERR 2** | **ERR 2** | ERR 5 | 🔴 |
| `A=1:B=2:C=3` then `SWAP A,B,C` — all defined | **ERR 2** | **ERR 2** | ERR 5 | 🔴 |

> **The ERR 5 is the SECOND operand's rule, not the third operand's.** It is the
> already-measured `sw_absent` rule — *`A=1:SWAP A,B` is Illegal function call,
> NOT an auto-created B* — firing before the parse ever reaches the `,C`. Give
> `B` a value and a third operand is a plain **trappable Syntax error, ERR 2**.

The doc's fixture had `B` undefined, so it recorded the second-operand rule and
called it a third-operand rule. **Invert the conclusion, do not delete the
analysis**: the row stays, its scope narrows.

💰 **The fix this implies is 0 B and this carve is what makes it so**:
`jp sw_illegal` → `jp pl_syntax`, three bytes for three bytes, into the ERR-2
canonical tail that did not exist before today. It is **filed, not folded in** —
a semantic change has no business in a commit whose whole claim is that no
observable moved, and it needs its own row set (`SWAP A,B,` and the trappability
of each shape are unmeasured).

### 6.3 `PLAY` is a missed member of an established class

| fixture | vg8020 | cf3300 | zerobas | |
|---|---|---|---|---|
| `PLAY` — end of line | **ERR 24** | **ERR 24** | ERR 2 | 🔴 |
| `PLAY:PRINT 1` — end of statement | **ERR 24** | **ERR 24** | ERR 2 | 🔴 |
| `PLAY ,"E"` — a bare comma | ERR 2 | ERR 2 | ERR 2 | ✅ |
| `PLAY "E"` — the control | *(no error)* | *(no error)* | *(no error)* | ✅ |

**ERR 24 is `Missing operand`, and this tree already implements that rule three
times over** — `LINE` ([`basic/graphics.asm:215`](../basic/graphics.asm:215)),
`SCREEN` (*"an argument list that ends where a value was required is Missing
operand at all four such slots"*, `PROVENANCE.md`) and `TIME=`
([`basic/time.asm:62`](../basic/time.asm:62)). **`PLAY` is the same class and
does not.**

🎯 **The divergence is TWO of `pl_syntax`'s four call sites, not four.** The
reference splits *the operand is MISSING* (end of statement → ERR 24) from *the
operand is MALFORMED* (a bare comma → ERR 2); zerobas answers ERR 2 to all of
them. `play.asm`'s `jr z,pl_syntax` at the `or a` and `COLON` tests are the two
that move; the `','` test is already right. The fourth site (a 4th voice string)
is **unmeasured** and must not be assumed into either half.

⚠️ `pl_syntax`'s own header cites the VG-8020 for the ERR-2 claim. **That
citation is correct for the comma site and wrong for the two it also covers** —
the same shape as §6.2, a measurement generalised past its fixture.
