# D-LINERR — a graphics statement gates the SCREEN mode after its mandatory arguments, not before them

Measurement notebook:
[`lineerr-msx1-characterization.md`](lineerr-msx1-characterization.md).
Gate: `make lineerr-acceptance` (**124** rows × 3 sides). Landed 2026-08-11.
Clean-room: observed screen output and published MSX system-variable reads only;
both reference ROMs are black boxes.

**§9 is a second landing on the same rule** — D-PAINTSEED, 2026-08-11, which
measured the residual §8.2 filed and moved `PAINT`'s off-screen-seed test below
the gate. §§1–8 are as they were the day D-LINERR landed, except for §8.2's
closure marker; the row counts and gate timings in §6 are that day's and are
superseded by §9's.

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
2. ✅ **CLOSED 2026-08-11 by D-PAINTSEED — see §9.** *(as filed: "PAINT's
   off-screen-seed ERR 5 versus the mode ERR 5 is unordered. Both raise ERR 5,
   so the code cannot separate them and only the work area could — and it is
   written between them. `ex_paint` keeps the seed test above the gate, which is
   where it already was; nothing measured says that is right.")* The work area
   answered: it moves **before** the refusal, so the seed test moved below the
   gate. The residual's own framing was half wrong, and §9.2 says how.
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

---

## 9. D-PAINTSEED — §8.2 measured, 2026-08-11

Same probe, same notebook, same gate. `make lineerr-acceptance` is now **124
rows × 3 sides, 122 scored + 2 deferred, 205 s**.

### 9.1 The rule

> **A `PAINT` whose seed is off the screen still moves the WORK AREA to that
> seed — the RAW, UNCLIPPED, STEP-resolved point — and only then refuses it.**

`GRPACX/GRPACY` *and* `GXPOS/GYPOS`, both halves, on both references, in the
mode where `PAINT` is legal as well as in the modes where it is not. So the
off-screen-seed test belongs **below** `gfx_point_gate`, not above it, and
`ex_paint` was wrong for the whole life of G5.

### 9.2 🔴 What is observable here, and the residual asked for the half that is not

Name the three events:

    A = the WORK-AREA write        B = the MODE gate        C = the SEED test

§8.2 asked for **C versus B**, and that pair is **not observable through this
instrument at all** — when a seed is both off-screen and in the wrong mode, B
and C raise the same code and leave the same work area whichever runs first. It
is not that no row was run; it is that no row *can* be. What is observable is
**C versus A**, and that is what the fix rests on: A and B are one
`call gfx_point_gate`, so putting C below A puts it below the gate.

🔴 **And the row §8.2 named — `PAINT(300,100)` in SCREEN 0 — cannot see the seed
test at all.** Knife **K-PS2** deletes the test outright and that row stays
**GREEN**, because the mode gate sits above the hole and answers with the same
code and the same work area. The row that carries the measurement is its
**SCREEN-2 twin** `p.off2`, where the statement is legal and only C can fire.
The residual named the row it could think of; the class is what found the one
that works.

The generalisation is the one the `n.pset0` control already paid for once in
§2.2, pointed the other way: **a filed row is a guess about which reading
carries the evidence, and it is as checkable as a filed diagnosis.** Sweeping
the class costs 16 rows and settles which row was load-bearing; running the one
named row would have produced the right answer for a reason that does not hold.

### 9.3 The measurement — 16 rows × 3 sides, all 16 predictions EXACT

The before column is the shipped `c0fc46b` tree (`basic-reloc 6db65a59`), and
the knife that reinstates the order rebuilds **that same hash byte for byte**
(§9.5), so "before" here is the artifact and not a memory of it.

| row | statement | mode | both references | zerobas BEFORE |
|---|---|---|---:|---:|
| `p.off0` | `PAINT(300,100)` | 0 | ` 5 , 300 , 100 ` | ` 5 , 7 , 4 ` |
| `p.off1` | `PAINT(300,100)` | 1 | ` 5 , 300 , 100 ` | ` 5 , 7 , 4 ` |
| `p.off2` | `PAINT(300,100)` | **2** | ` 5 , 300 , 100 ` | ` 5 , 7 , 4 ` |
| `p.oy0` / `p.oy2` | `PAINT(20,200)` | 0 / 2 | ` 5 , 20 , 200 ` | ` 5 , 7 , 4 ` |
| `p.neg0` / `p.neg2` | `PAINT(-1,100)` | 0 / 2 | ` 5 , 65535 , 100 ` | ` 5 , 7 , 4 ` |
| `p.negy2` | `PAINT(20,-1)` | 2 | ` 5 , 20 , 65535 ` | ` 5 , 7 , 4 ` |
| `p.x256` | `PAINT(256,191)` | 2 | ` 5 , 256 , 191 ` | ` 5 , 7 , 4 ` |
| `p.y192` | `PAINT(255,192)` | 2 | ` 5 , 255 , 192 ` | ` 5 , 7 , 4 ` |
| `p.step0` | `PAINT STEP(300,100)` | 0 | ` 5 , 307 , 104 ` | ` 5 , 7 , 4 ` |
| `w.paint0.off` / `w.paint2.off` | the same, read through **GXPOS** | 0 / 2 | ` 5 , 300 , 100 ` | ` 5 , 7 , 4 ` |
| `p.ov0` | `PAINT(70000,100)` | 0 | ` 6 , 7 , 4 ` | ` 6 , 7 , 4 ` |
| 🟢 `p.ok2` | box, then `PAINT(20,20)` | 2 | ` 0 , 20 , 20 ` | ` 0 , 20 , 20 ` |
| 🟢 `p.edge2` | box, then `PAINT(255,191)` | 2 | ` 0 , 255 , 191 ` | ` 0 , 255 , 191 ` |

**13 diverge, 3 agree — exactly as predicted, value for value, before the run.**

Four things the class buys that the one named row does not:

* the **domain** is swept, not sampled: `x>255`, `192≤y≤255` (a legal byte that
  is still off-screen), and both negatives, which read back as `65535` — the
  same raw-int16 storage §4.4 measured at `LINE`;
* the **edge is pinned from both sides**. `p.edge2` proves `(255,191)` is
  *accepted*, so `p.x256`/`p.y192` are an off-by-one and not "everything
  refuses";
* `p.step0` says the work area takes the **resolved** point (307,104), not the
  literal — so the write is downstream of `parse_coord`'s STEP arithmetic;
* `p.ov0` says the int16 **coercion still outranks both**, unchanged.

🔴 **The SCREEN-3 face was deliberately NOT added.** Both references draw in
SCREEN 3 (§6.4) but refuse an off-screen seed there too, so `PAINT(300,100)` in
SCREEN 3 would be ERR 5 on all three sides — zerobas's `cp 2` agreeing with the
references' seed test. A row that agrees for the wrong reason is worse than no
row.

### 9.4 The price — NET ZERO, and the header that outlived two edits

Two instructions moved down. No byte changed anywhere: low **14 B**, page 1
**74 B**, sub p0 **3604**, sub p1 **1483**, all four identical to `c0fc46b`.
`sub.rom` and `disk.rom` hash unchanged (`5d7c837a` / `2c630d3d`), as a
resident-only reorder must.

🔴 **`ex_paint`'s header comment still described the code from before
D-LINERR** — *"unlike PSET/LINE/CIRCLE, the work-area write is deferred to
AFTER every field is parsed"* — with the body three lines below it already
saying the opposite, in D-LINERR's own words. A header that survives the edit it
describes is the `and $0F` shape of §5.1 in miniature: the next reader has two
statements and no way to tell which is the measurement. Corrected here. And the
"unlike" was doubly wrong: after both edits `PAINT` is `gfx_point_gate` at
exactly the site the other four verbs use, and the only thing that distinguishes
it is the extra reject underneath.

### 9.5 Knives — 3 cuts, each run twice, 6 of 6 EXACT

Union of 29 labels (every PAINT row, plus five non-PAINT witnesses and all four
positive controls); baseline through `probe_report.parse()`; restore from a
scratchpad snapshot in a `finally`; rebuild inside the loop.

| | cut | RED / predicted | GREEN moved | r1 | r2 |
|---|---|---|---|---|---|
| **K-PS1** | the shipped order reinstated — the seed test back above the gate | 13/13 | 0/16 | EXACT | EXACT |
| **K-PS2** | the off-screen test **deleted** (`call`+`jp` → 6 × `nop`) | 7/7 | 0/22 | EXACT | EXACT |
| **K-PS3** | `gfx_point_gate` → `gfx_mode_gate`: PAINT gates, never moves the work area | 18/18 | 0/11 | EXACT | EXACT |

**K-PS1 rebuilds `basic-reloc` to `6db65a59` — the shipped `c0fc46b` ROM, byte
for byte.** That is the strongest single fact in this slice: it says the change
is a pure reorder *and* that the knife reinstates the real defect rather than an
approximation of it.

**K-PS2 is the one worth reading.** Deleting the code under test reddens only
the **seven SCREEN-2 rows**; the six SCREEN-0/1 rows — `p.off0` among them —
stay green, because the mode gate above the hole answers identically. All seven
go to `<NO CAPTURE>`: a `PAINT` let loose from an off-screen seed floods against
garbage and outruns the window, the same way §7.3's `v.paint0` does under K-LE1.

### 9.6 🔴 A knife cut a DIFFERENT ROUTINE, and the cut site LOOKED unique

K-PS1's first runner did `src.replace("call gfx_point_gate ; BC/DE/HL preserved",
…, 1)`. That exact line, comment and all, occurs **three times** in
`basic/graphics.asm`, and the first is `gfx_plot_stmt`'s — the line **`PSET`**
goes through. So the knife aimed at `ex_paint` silently removed the work-area
write from the probe's own **`PSET(7,4)` seed**.

This is §7.1's failure with a new cause. There, K-LE4 cut a leaf the seed
genuinely shared; here nothing was shared — the cut site merely *looked* unique
because it was distinctive-looking text. The tag guard is what caught it: the
probe failed `n.zork`, exited 2, and the runner **read the tag** instead of
diffing the values, so it aborted with *"the probe REFUSED TO SCORE"* rather
than reporting 29 spectacular movements.

The remedy is mechanical and belongs in the next runner: **scope every cut to
the routine's own region and assert the occurrence count is exactly 1.**
A `replace(old, new, 1)` on a whole file is a *guess* that the first match is
the intended one, and an assembly file is precisely where that guess is wrong —
shared idiom is what a DRY pass leaves behind, so the better the file, the more
duplicate call lines it has.

### 9.7 🔴 What K-PS3 cannot separate — recorded because the prediction MISSED

K-PS3's RED/GREEN sets were exact, but two **per-row value** predictions written
alongside them were wrong: `p.ok2` and `p.edge2` were predicted to read the
box's own last point (` 0 , 10 , 10 ` and ` 0 , 250 , 186 `) and both came back
`<NO CAPTURE>`.

The reason is a fact about the ABI that the knife's framing ignored:
`GXPOS/GYPOS` is not only *this probe's instrument*, it is **how the seed
reaches the tenant** (`spec-basic-graphics-g5.md` §6). So cutting PAINT's
work-area write does not cut the reading alone — it cuts the argument passing,
and the fill runs from whatever those cells last held. **K-PS3 is therefore not
a clean instrument-only knife at this verb**, and it cannot distinguish "the
rows depend on the work-area write" from "the rows depend on PAINT being handed
its seed". It is kept because that weaker statement is still worth having, and
because the miss is the useful part: at a verb whose marshalling *is* the work
area, "cut the instrument" and "cut the subject" are the same cut. K-PS1 and
K-PS2 carry the falsification.
