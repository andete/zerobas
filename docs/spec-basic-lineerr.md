# D-LINERR — a graphics statement gates the SCREEN mode after its mandatory arguments, not before them

Measurement notebook:
[`lineerr-msx1-characterization.md`](lineerr-msx1-characterization.md).
Gate: `make lineerr-acceptance` (108 rows × 3 sides). Landed 2026-08-11.
Clean-room: observed screen output and published MSX system-variable reads only;
both reference ROMs are black boxes.

---

## 1. The rule

> **A graphics statement moves the WORK AREA to the point its MANDATORY
> arguments resolve to, and refuses a wrong SCREEN mode IMMEDIATELY AFTER
> THAT — after every fault the mandatory arguments can raise, and BEFORE the
> first OPTIONAL argument is looked at.**

Two corollaries, measured in the same sweep:

* **A `LINE`/`PSET` colour is a 0..15 RANGE CHECK (ERR 5)**, the same one
  `CIRCLE` and `PAINT` already used — not a silent `and $0F` nibble mask.
  An out-of-int16 colour is ERR 6 from the coercion first (`,70000` → 6).
* **A `LINE` argument list that ENDS where the COLOUR was required is
  `Missing operand` (ERR 24)** — both at end-of-line and at a `:`. It does
  **not** extend one field along to the box slot, which is ERR 2 for both
  shapes.

It is **one rule at five verbs** (`PSET`, `PRESET`, `LINE`, `CIRCLE`, `PAINT`),
which is why it is one shared routine and not five edits. `DRAW` already agreed;
`POINT` has no mode gate at all, by construction.

---

## 2. Where the rule comes from, and how the site is pinned from both directions

Neither half of the ordering is inferred. Each is fixed by a **pair** of rows
that bracket it, at every verb that has a gate (SCREEN 0 throughout):

| the gate is AFTER this | …and BEFORE this |
|---|---|
| `PSET((Q$<5),21)` → ERR **13** | `PSET(20,21),0*(1/0)` → ERR **5** |
| `LINE (11,12)-((Q$<5),21)` → ERR **13** | `LINE (11,12)-(20,21),0*(1/0)` → ERR **5** |
| `CIRCLE(20,21),(Q$<5)` → ERR **13** | `CIRCLE(20,21),5,0*(1/0)` → ERR **5** |
| `PAINT((Q$<5),21)` → ERR **13** | `PAINT(20,21),0*(1/0)` → ERR **5** |

The left column says a mandatory argument's fault outranks the mode; the right
says an optional argument's does not. Neither column alone sites the gate.

And the **work-area** half is pinned independently of the error code, by the
`X,Y` reading over a `PSET(7,4)` seed: `LINE (11,12)-(20,21)` in SCREEN 0 raises
ERR 5 with GRPAC **already on (20,21)** on both references. So the work-area
write is before the gate, not after it.

### 2.1 The row the design turns on

`CIRCLE` has **two** mandatory arguments, so "after the mandatory arguments" and
"after the first one" are different sites at that verb — and exactly one row
separates them:

```
v.circ0.rt    CIRCLE(20,21),(Q$<5)     both references:  13 , 20 , 21
```

The radius's type fault outranks the mode. A one-site reading of the rule puts
CIRCLE's gate at the centre and answers ERR 5 here. Knife **K-LE7** builds that
cheaper design and reddens this row and `v.circ0.r`, and nothing else (§7).

### 2.2 🔴 It was a negative control that made this a five-verb rule

`n.pset0` was written as *"the wrong-mode rule at a DIFFERENT verb, which this
slice claims nothing about"* — a control chosen to agree for a reason
independent of the claim. It diverged **identically** to LINE's filed row. So
the gate is not `ex_line_gfx`'s; it is `gfx_err5`'s callers', and a fix at LINE
alone would have shipped a partial rule under a green gate. The control was
reclassified into the new `v.*` class, the class was swept, and the fix became
one leaf.

---

## 3. 🔴 The filed diagnosis was wrong, and the file refuted it

`TODO.md` and the deferring probe both recorded:

> *"LINE raises its own `Illegal function call` **eagerly from inside its
> coordinate parse**."*

There is no ERR 5 anywhere in `parse_coord`. The refusal was `ex_line_gfx`'s own
opening `cp 2`, three instructions in, before any coordinate was looked at, and
the row runs in the boot default SCREEN 0. **Reading the site was enough** — no
emulator, no reference. The wrong diagnosis pointed at a per-driver fix in a
coordinate walk; the right question pointed at a shared ordering rule at five
verbs.

The generalisation is the one D-TMFP already paid for once: *a filed diagnosis is
a claim about code, and it is the cheapest claim in the whole slice to check.*

---

## 4. The design, and its price

Three entry points, 29 bytes, in `basic/graphics.asm` beside `gfx_err5`:

```
gfx_point_gate:   work area := (BC,DE), then the gate     ; the common case
gfx_mode_gate:    the gate alone                          ; CIRCLE's radius
gfx_work_area:    the work area alone                     ; CIRCLE's centre
```

They **nest** — `gfx_point_gate` falls into `gfx_mode_gate`, which is followed
by `gfx_work_area` — so the two extra entry points cost 4 bytes between them.
`BC`, `DE` and `HL` are all preserved (every caller still holds the cursor in
`HL`; PSET's caller still needs the point in `BC`/`DE` for its own range test);
`A` is the only clobber.

⚠️ **CIRCLE gates on EVERY int request, not only the radius.** Gating twice is
the same as gating once — the second test can only pass — and that is cheaper
than a "which argument am I on" flag in the coroutine's resume state.

### 4.1 The walls — a −26 B CARVE, hand count EXACT at both stages

| site | Δ |
|---|---:|
| the three new shared leaves | **+29** |
| `gfx_plot_stmt` (PSET/PRESET) | **−24** |
| `ex_line_gfx` | **+1** |
| `ex_paint` | **−25** |
| `ex_circle` | **−2** |
| LINE's `p1` staging | **−5** |
| **net** | **−26** |

Page 1 free **48 → 74 B**; the low region stays at **14 B**; sub p0 3604 and
sub p1 1483 unchanged. The hand count was exact at both stages (−21, then −5).

**The fix pays for itself because the old code said the same thing five times.**
`ex_paint` alone gives back 25 bytes: its work-area write sat after every field
and needed a `push bc`/`push de` pair to guard the seed across the colour and
border parses — moving the write *up* retires the guard along with it.

ROMs after: `basic-reloc 6db65a59`, `sub 5d7c837a`, `disk 2c630d3d`,
`zerobas-main-eu 819cb9de` (base `372221e` was `789c89bf / 5d7c837a / 2c630d3d /
bbd8e64d` — the sub and disk ROMs are untouched, as expected for a
resident-only change).

---

## 5. Two shipped doc claims this refutes

Both are corrected in place with a **SUPERSEDED pointer**, not deleted: a
retired claim that simply vanishes is invisible on the next grep (`bf0dab5`).

1. [`spec-basic-graphics-g5.md`](spec-basic-graphics-g5.md) §6 —
   *"Resident `ex_paint`: **SCREEN-2 precheck** → `parse_coord` … → set
   GRPAC/GXPOS = seed → marshal"*. **Both ends are wrong.** The gate is not
   first (`v.paint0.tm` is ERR 13), and the work-area write is not last
   (`v.paint2.c` leaves GRPAC on the seed). It was a design choice never
   measured against a reference.
2. The `and $0F` colour mask at `PSET`/`LINE`. 🔴 **And this one was never in a
   doc at all** — see §5.1.

### 5.1 🔴 The claim I set out to correct did not exist

The pre-slice code read

    and $0F      ; use the low nibble (0..15); see G2 gate note

and the probe restated it as *"documented as a SILENT `and $0F` MASK, **measured
on the VG-8020** (spec-basic-graphics-g2.md §11.9)"*.

**`spec-basic-graphics-g2.md` has no §11.9 — it has no §11 at all**, and there is
no "G2 gate note". No doc in the tree ever stated a domain for the colour
argument. So an own-design mask shipped with a dangling pointer, and the pointer
was later re-read as a measurement on a named machine.

Nothing mechanical could catch it: a dangling `§11.9` is not a forbidden source,
so `make audit-citations` is silent, and no gate ever asked what `PSET(20,21),16`
does. The lesson is not "check citations" but the direction of the drift:
**a citation that does not resolve gets UPGRADED on the way to its second
reader.** The first writer knew it was a note-to-self; the second read
"measured".

Both bad citations are corrected in this slice's own source and probe.

---

## 6. As-built

### 6.1 The gate

`make lineerr-acceptance` — 108 rows × 3 sides, **106 scored, 2 deferred**.

* **before: 55 agree / 53 diverge** — taken over **108** scored rows, because
  the DEFERRED dict did not exist yet; the SCREEN-3 gap was not known to be one
  until the sweep found it.
* **after: 106 agree / 0 diverge**, 2 deferred and printed.

⚠️ **The two columns are not scored over the same denominator, so the headline
is stated both ways rather than as one flattering fraction.** Of the 53 that
diverged, 51 are now green and 2 (`m.s3`, `v.pset3`) moved but remain deferred.
Rebased onto the after convention, the before column is **55/106**; taken as it
was actually printed, it is **55/108**. Nothing was re-scored to improve it:
recategorising a red row as deferred and then quoting the improvement against
the new denominator is how a fix flatters itself.

The before column was measured on a rebuilt base tree with the base hashes
reproduced (`789c89bf / 5d7c837a / 2c630d3d / bbd8e64d`), not copied from the
design's predictions.

`make stmtpend-acceptance` closes with it: `c.line.tm` is **un-deferred**, and
that probe's DEFERRED dict is now **EMPTY** (58 scored).

### 6.2 The instrument

Trapped rows read `[ ERR , X , Y ]` — the code **and** how far the statement got,
over a `PSET(7,4)` seed. Every row changes the SCREEN mode, so a screen scrape
is blind to its own subject (the wall that made D-STMTPEND defer `u.scr.dz`).
The `w.*` rows read `GXPOS/GYPOS` instead of `GRPACX/GRPACY`.

🔴 **The `w.*` class earned its place mid-slice.** After the first fix `m.s0.tm`
was GREEN while its GXPOS twin `w.s0.tm` was still RED **on the identical
statement** — LINE's `p1` staging wrote only the last-referenced point. A
GRPAC-only reading would have scored a live defect green. Knife **K-LE3** is the
falsification of that half specifically.

### 6.3 Corpus

Sequentially from clean (`rm -rf build`, then `repack-machine` **first** —
`latch-check` has no such prerequisite and would otherwise boot a machine config
pointing at ROMs that do not exist; **bash**, since `zsh` does not word-split
`make $t`). The corpus of record is D-SCRERR's lineage plus
`lineerr-acceptance`, and this slice adds an **adjacent sweep** of seven gates
pulled in by what the diff actually touches (the graphics floor, the sub-ROM
tenant ABI the LINE tenant is called across, and the shared error raisers).

**52 targets, every one rc=0** — the 45 of record plus the 7 adjacent. **2014 s
(34 min) of measured gate time**, plus the clean rebuild; real host wall time
per target (`$SECONDS` around each `make`), not emulated MSX time — the probes
run `set throttle off`, so the two are nowhere near each other.

`unit-test` **59/59** · `audit-citations` CLEAN (**790** files swept) ·
`preflight-check` **95 guarded / 0 unguarded** · `injector-check` **355** files
(+1) · `rowshape-check` **26** probes (+1) · `deadcode` **0/0 (+1 allowlisted)** ·
`latch-check` **16/16** · `lineerr-acceptance` **106/106 + 2 deferred (new,
168 s)** · `stmtpend-acceptance` **58/58, its DEFERRED dict now EMPTY** ·
`screenerr-acceptance` **61/61** · `penderr-acceptance` **61/61** ·
`tmfp-acceptance` **50/50** · `width-acceptance` **94/94** · `locarg-acceptance`
**45/45** · `namspc-acceptance` **58/58** · `fldwidth-acceptance` **40/40 (+2
deferred)** · `onerr0-acceptance` **24/24** · `missing-acceptance` **214/214** ·
`graphics-acceptance` PASS · `badfnum-acceptance` **93 cases, 0 mangled, 0
oracle drift** · `diskbasic-acceptance` **34/34 verbs** · `lnblank-acceptance`
**539/539** · `lnblank-say-acceptance` **204/204** · `logicops-acceptance`
**193/193** · `clearpool-acceptance` **52/52** · `forvar` **33/33** · `nxlist`
**25/25** · `nxary` **22/22** · `tgtspc` **28/28** · `arylv` **18/18** ·
`readvar` **24/24** · `inputary` **7/7** · `linemax` **60/60** · `editverb`
**61/61** · `lptverb` **44/44** · `dskmsg` **5/5** · `runtail` **9/9** ·
`cassave` **20/20** · `dexp5-pin` **16 rows**, plus the remaining gates.

The **adjacent sweep**, all PASS: `graphics-floor-acceptance` ·
`subrom-abi-check` (12 resident-ABI addresses, `sub.rom` not stale) ·
`subrom-closure-check` (**733** page-0 and **586** page-1 tenant routines, no
escape) · `subrom-acceptance` · `error-acceptance` · `error-trap-acceptance` ·
`intarg-acceptance`. Seven targets for **56 s** between them — the sweep is
cheap, which is the argument for widening it rather than reasoning about which
gates a diff "could" reach.

⚠️ `rowshape-check`, `injector-check` and `audit-citations` all GROW with the
corpus, so the previous slice's figures are **predictions**, not baselines.
Scored, not assumed.

### 6.3.2 🔴 The run DIED at target 43 and the waiter could not tell

The first driver took **SIGTERM** during `graphics-acceptance`
(`make: *** [graphics-acceptance] Terminated: 15`) after 42 targets, because it
had been launched from a session background shell that was reaped. Recorded
because the interesting half is the **instrument**, not the accident:

🔴 **The waiter was `until grep -q '=== done ==='; do sleep 30; done` — it
matches only the happy path.** A run that dies never prints the sentinel, so the
waiter blocks forever and the death reads as slowness. That is this project's own
recurring lesson at the harness level: *a check whose negative answer is
indistinguishable from a dead subject is not a check.* The remedy is not a
shorter poll but no poll — hand the driver to the harness, which reports process
**exit** whatever its cause, make the driver `exit` non-zero on any failed target
so the notification carries the verdict, and give it a signal trap that names the
target it died on.

The remaining 10 targets were **resumed, not re-run from clean**, and that is a
measurement claim which was checked rather than assumed: all four ROMs still
hashed to this slice's `after` values (`6db65a59 / 5d7c837a / 2c630d3d /
819cb9de`, `sha256[:8]`) and the four walls still printed 14 / 74 / 3604 / 1483,
so targets 43–52 measured the byte-identical artifact targets 1–42 did.
⚠️ And the clean-start guarantee had already discharged its only purpose:
`rm -rf build` + repack-first exists **for `latch-check`**, which has no repack
prerequisite — and `latch-check` ran at position 7, scoring 16/16.

### 6.3.1 The PROVENANCE staleness grep came back EMPTY, and that is the finding

`bf0dab5` established the habit: after a slice, grep `PROVENANCE.md` for rows
naming the routines it touched, because a row naming a *retired* cell is visible
on the next grep while one naming a *moved* cell is not. Done here for
`ex_line_gfx`, `gfx_plot_stmt`, `parse_coord`, `ex_paint`, `ex_circle` and
`gfx_err5`, across all five `PROVENANCE.md` files.

**Not one row mentions any of them.** No row went stale because none existed:
the graphics arc recorded provenance for G6 (`DRAW`) and for the retired `BASE`
descope, and G2–G5 — every routine this slice rewrote — never got a section. So
the SCREEN-mode gate, the coordinate walk and the colour handling had their
contracts only in the `docs/spec-basic-graphics-g*.md` design specs, which is
exactly where §5.1's dangling citation could sit unchallenged. The section
appended for this slice is the first provenance row any of these five routines
has ever had.

### 6.4 SCREEN 3 is measured and deferred, not silently red

`m.s3` and `v.pset3` show both references **drawing** in SCREEN 3 where zerobas
raises ERR 5. That is a whole-feature gap — a second rasteriser and a second
address/clash model — not an error-surface defect: this slice moved *where* the
refusal happens, and the refusal is correct for every mode zerobas implements.
Both rows are printed, marked `....`, and excluded from the tally in **both**
directions. A row that can only ever be red is doc debt, not a gate.

---

## 7. Knives

Nine cuts, each run **twice**, all four ROMs hashed after every cut build,
byte-neutral sites except K-LE2 (deliberately an insertion — it is the one that
reinstates the shipped defect), restored from a scratchpad snapshot in a
`finally`, parsed with `probe_report.parse()`, baseline computed once over the
union of all labels, and a predicted **GREEN** set scored alongside the RED one.

| | cut | RED / predicted | GREEN moved | r1 | r2 |
|---|---|---|---|---|---|
| **K-LE1** | `gfx_mode_gate`: `ret z` → `ret` — one bit, and the gate never refuses, at all five verbs | 12/12 | 0/11 | EXACT | EXACT |
| **K-LE2** | the gate reinstated at the TOP of `ex_line_gfx` — the shipped defect, rebuilt | 15/15 | 0/12 | EXACT | EXACT |
| **K-LE3** | `gfx_work_area`'s `GXPOS` write → a second `GRPACX` write | 3/3 | 0/9 | EXACT | EXACT |
| **K-LE4** | its mirror: the `GRPACX` write → a second `GXPOS` write | — | — | *DID-NOT-MEASURE* | *DID-NOT-MEASURE* |
| **K-LE4a** | K-LE4 re-sited: `ex_paint` gates but no longer moves the work area | 3/3 | 0/8 | EXACT | EXACT |
| **K-LE4b** | K-LE4 re-sited: LINE's `p2` likewise | 5/5 | 0/8 | EXACT | EXACT |
| **K-LE5** | the ERR-24 guard re-pointed at the `elg_syntax` raise it displaced | 2/2 | 0/9 | EXACT | EXACT |
| **K-LE6** | the 0..15 check → the silent `and $0F` mask, byte for byte | 5/5 | 0/7 | EXACT | EXACT |
| **K-LE7** | CIRCLE gates at the CENTRE instead of after the radius | 2/2 | 0/7 | EXACT | EXACT |
| **K-LE8** | *probe-side*: the `PSET(7,4)` seed cut, on the REVERTED tree | — | — | **predicted MISS** | — |

**16 of 16 scoreable predictions EXACT, in both rounds**, with the predicted
GREEN set empty every time.

### 7.1 🔴 K-LE4 cut the INSTRUMENT, and the probe's own control caught it

K-LE4 removed the `GRPACX`/`GRPACY` write from the shared leaf. But the probe's
seed **is** `PSET(7,4)` — it reaches `GRPAC` through that same leaf — so the cut
destroyed the measuring apparatus along with the subject. `n.zork`, a positive
control chosen to hold for reasons independent of this slice's claim, read
` 2 , 0 , 4 ` instead of ` 2 , 7 , 4 `, and the probe **refused to score**.

🔴 **And the first runner turned that refusal into a number.** The exit-2 report
is complete, has a correct `ROWS:` terminator, parses cleanly, and carries real
values — every row simply carries the tag `....`. Diffing values against the
baseline therefore reported *"9 of 9 predicted-RED rows moved, and 9 of 9
predicted-GREEN rows moved too"*: a spectacular, entirely fictional MISS.

`docs/dev-workflow.md` §Knives has four bullets about a runner defeated by a
report's shape, and every one of them is about a report that is a **prefix** or
is **formatted differently**. This is a fifth: **a report that is whole,
well-formed and parseable, and still says nothing was measured.** The only thing
that carries that fact is the TAG. Read it; `probe_report.parse()` hands it to
you and the first runner threw it away.

The claim itself is testable — just not there. **K-LE4a** and **K-LE4b** re-site
it at two call sites the seed does not pass through (`ex_paint` and LINE's `p2`,
each a byte-neutral `gfx_point_gate` → `gfx_mode_gate` swap, so the verb still
gates and no longer moves the work area). Both are EXACT in both rounds.

### 7.2 🔴 K-LE8 was a PREDICTED MISS, and it holds

K-LE8 cuts the `PSET(7,4)` seed out of the probe and runs it against the
**reverted** tree — the D-SCRERR K-SE6 shape, since a seed can only hide a
divergence that exists. The prediction, written before the run, was **MISS**:
the seed makes "the statement moved nothing" distinguishable from "(0,0)", but
every row this slice moved differs from the references in the error code, the
coordinate, or both, so a `(0,0)` reading against a `(20,21)` one is still a
divergence.

Measured, 14 rows × 3 sides: **7 diverge with the seed, 7 without.** No row's
verdict flips. **The seed is DEFENSIVE, not load-bearing, for this row set** —
the D-PENDERR K-PE3 shape — and it is kept, with the reason written down, rather
than justified by a claim nobody had tested.

(Its verdict also had to be computed from the three side values by hand, for the
§7.1 reason: cutting the seed necessarily fails `n.zork`, so the probe declines
to score the very run the knife needs.)

### 7.3 What the strongest cuts actually printed

K-LE1's two loudest rows are worth quoting, because they are the gate's absence
being visible rather than merely different: `u.s0` (an untrapped
`LINE (11,12)-(20,21)` in SCREEN 0) goes from `Illegal function call in 20` to
**`[RANON]`** — the statement completes and the next line runs — and `v.paint0`
goes to `<NO CAPTURE>`, because a `PAINT` let loose in SCREEN 0 flood-fills
against garbage and outruns the window.

---

## 8. Filed, not folded in

1. **SCREEN 3 draws on both references** (`m.s3`, `v.pset3`) — a whole-feature
   gap, priced at nothing here (§6.4).
2. **PAINT's off-screen-seed ERR 5 versus the mode ERR 5 is unordered.** Both
   raise ERR 5, so the code cannot separate them and only the work area could —
   and it is written between them. `ex_paint` keeps the seed test above the
   gate, which is where it already was; nothing measured says that is right.
3. **DRAW was left alone.** `v.draw0` agrees on all three sides already. Its
   argument is a string parsed by a tenant, so "the mandatory arguments" means
   something different there; naming it out of scope with a green row behind it
   beats guessing.
4. **`ex_line_gfx`'s p2 work-area write is duplicated in the tenant**
   (`sub/graphics.asm` `gfx_line_op` writes `GXPOS`/`GRPAC` = p2 again on the
   drawn path). Deliberate, not dead: the CIRCLE spokes call that op internally
   and rely on it. K-LE3's green `w.s2` is the row that shows the duplicate is
   load-bearing — a LINE that *draws* gets its work area from the tenant, which
   is exactly why only the rows that never reach the draw can see K-LE3's cut.
