# D-TGTSPC — a SPACE between a variable reference and its `(`

*Slice of the lvalue arc. Subject: the `NEXT A (1)` residual D-NXARY filed and
DEFERRED — **not for space** — in `TODO.md` and
[`nxary-msx1-characterization.md`](nxary-msx1-characterization.md) §4.*

Based on `030f068` (D-NXARY). Measurement:
[`tgtspc-msx1-characterization.md`](tgtspc-msx1-characterization.md),
`make tgtspc-characterize`, `probes/basic/basic_probe_tgtspc.py`.

---

## 1. The rule — measured before it was designed

D-NXARY had **one** row (`a.spc`) and a mechanism read out of the source. One row
is not a rule ([[a-shared-engine-fix-must-measure-its-other-callers]]), and the
thing the fix touches is shared by **nine statement surfaces**. So all nine were
measured first, each with the CONTIGUOUS form of its own statement as its own
positive control, on its own fixture.

**28 rows, three sides, BOTH REFERENCES AGREEING ON ALL 28.** 12 of the 26
scored rows agree at `030f068`. The full table is in the characterization; the
rule it states:

> A variable REFERENCE's subscript `(` may be separated from the name by any run
> of spaces. The reference then parses the **whole** reference — the subscript is
> evaluated, the array **auto-DIMs**, and it is **range-checked** — exactly as if
> the `(` had been contiguous. This holds at **every** statement that takes a
> variable as a target.

Three clauses are readings no earlier row asked, and each one decides bytes:

* 🎯 **`t.spc` — THE SPACE SURVIVES THE CRUNCH, AND THAT IS WHAT SAYS WHICH FILE
  THE FIX BELONGS IN.** The first question is not *"does the reference skip the
  space"* but *"is the space still there when the parser runs"*. Read from the
  **stored line bytes** through `TXTTAB` — `basic_probe_crunch.py`'s own
  instrument — `1 NEXT A (1)` crunches to `83 20 41 **20** 28 12 29 00` on the
  VG-8020, on the CF-3300 and here, byte for byte. The `$20` before the `(` is
  stored on all three. Had the reference's tokeniser stripped it, every byte of
  a parser-side fix would have been spent in the wrong file — and a screen
  reading cannot tell the two apart, because both produce `NEXT without FOR`.
* 🎯 **`r.spcauto` — THE SPACED FORM AUTO-DIMS.** With no `DIM A` anywhere,
  `READ A (1)` then `PRINT A;A(1)` reads ` 0  7 ` on both references: the element
  took the value and the array was created. D-NXARY's `a.autodim` established
  auto-DIM for the contiguous form; this says the space does not change it, so
  the fix must stay on `ary_op0_resolve` op=0 and cannot be a tightened resolve.
* 🎯 **`n.spcoob` / `r.spcoob` — THE FULL RESOLVE, NOT A `(`-FINDER.** `NEXT A
  (99)` and `READ A (9)` on `DIM A(3)` are **Subscript out of range** on both
  references. A fix that merely learned to *reach* a `(` after a space, without
  evaluating and range-checking, would answer the wrong error — the same trap
  that priced D-NXLIST's decline.

And two rows are the BOUNDARY, measured rather than assumed — see §3.2.

---

## 2. What is wrong, in one sentence

`tgt_parse` (`basic/vars.asm:279`) tests for the subscript with a bare
`ld a,(hl)` immediately after `var_name_key`, so its `(` must be **lexically
contiguous**: `A (1)` resolves as the scalar `A`, and the ` (1)` then reaches
statement position as **Syntax error** — at all nine surfaces at once.

---

## 3. Scope

### 3.1 🔴 THE CALL-SITE COUNT WAS WRONG WHEN IT WAS FILED

`TODO.md`, `nxary-msx1-characterization.md` §4 and `ex_next`'s own code comment
all say `tgt_parse` has **seven** call sites. Walked
(`grep -n "call\s*tgt_parse\b" basic/`, and `tgt_parse_fld`'s own callers):

| # | site | file:line | statement |
|---|---|---|---|
| 1 | `ex_next` | `basic/program.asm:1665` | `NEXT` |
| 2 | `ex_read` | `basic/program.asm:1845` | `READ` |
| 3 | `inpc_vloop` | `basic/input.asm:102` | console `INPUT`, **numeric** arm |
| 4 | `inpc_vstr` | `basic/input.asm:127` | console `INPUT`, **string** arm |
| 5 | `inpc_line` | `basic/input.asm:200` | `LINE INPUT` |
| 6 | `ex_mid_stmt` | `basic/str-engine.asm:1014` | `MID$(<var>,n,m) =` |
| 7 | `inp_readvar` | `basic/files.asm:708` | `INPUT #n` / `LINE INPUT #n` |
| 8 | `tgt_parse_fld` | `basic/field.asm:201` | → `FIELD … AS` (`field.asm:288`) |
| | | | → `LSET` / `RSET` (`field.asm:384`) |

**EIGHT `call tgt_parse` instructions, NINE statement surfaces.** The filed list
("READ, console INPUT, LINE INPUT, `MID$(…)=`, FIELD, LSET/RSET and
`files.asm`") is seven *other* surfaces and forgot to count `ex_next`, the site
that filed it; it also folds the console `INPUT`'s two arms — two distinct
`call`s — into one ([[a-hand-listed-denominator-is-a-scope-claim]]). All nine are
measured here, each with its own control.

### 3.2 The boundary — the space positions this slice does NOT touch

Two rows exist to stop *"the fix works"* from quietly meaning *"some spaces
work"*, and both **DIVERGE**:

| row | program | both references | zerobas |
|---|---|---|---|
| `x.dollar` | `FOR A=1 TO 2` / `NEXT A $(1)` | **NEXT without FOR** | **Syntax error** |
| `x.name` | `FOR AB=1 TO 2` / `NEXT A B` / `PRINT"[OK]"` | **`OK`** | **NEXT without FOR** |

🔴 **`x.name` IS THE BIG ONE AND IT IS NOT THIS SLICE.** `NEXT A B` completing
the `FOR AB` loop means the reference treats a space **inside a variable name**
as insignificant — its name scan is CHRGET-based all the way down. That is
`var_name_key` / `var_str_type`, a cursor position *before* the one this slice
touches, and it reaches **every variable reference in every expression**, not
just the nine lvalue targets. The skip added here runs *after* `var_name_key`
has already stopped at the space, so it cannot reach either row.

Both are **DEFERRED**: measured, printed, never scored, and filed as one
residual with these two readings as its denominator. A deferred row that started
agreeing would itself be a finding.

`x.inner` (`NEXT A( 1 )`) is the third boundary row and it is **already green**
on all three sides — the array engine's own expression eval skips those spaces.
That is what scopes the defect to the `(` position itself rather than to
"spaces".

---

## 4. Design

### 4.1 🎯 ONE INSTRUCTION, IN THE ONE PLACE ALL NINE SURFACES SHARE

`basic/vars.asm`, inside `tgt_parse`:

```
                call    var_name_key        ; BC=key, HL past name+suffix
                ld      a,(hl)              ; ← 1 B, the whole defect
                cp      '('
                jr      z,tp_ary
```

becomes

```
                call    var_name_key        ; BC=key, HL past name+suffix
                call    skip_spaces         ; ← 3 B; A = first non-space, HL on it
                cp      '('
                jr      z,tp_ary
```

`skip_spaces` (`basic/interp.asm:674`) is `ld a,(hl)` / `cp ' '` / `ret nz` /
`inc hl` / `jr skip_spaces` — it returns **exactly what `ld a,(hl)` returned**
when there is no space, with `HL` on the byte in `A`. It is a drop-in.

**+2 B.** Not the 3 the residual filed: the instruction it replaces is one byte,
not zero.

### 4.2 Why here and not at the callers

Eight `call skip_spaces` insertions — one per site — would cost **≥ 16 B** into a
5-byte wall, would leave `tgt_parse` still wrong for the ninth caller anyone adds
next, and would not fix §4.3. The shared engine is where the rule lives; that is
the same reasoning that made `tgt_parse` exist at D-ARYLV.

### 4.3 🎯 THE SCALAR PATH CONSUMES A TRAILING SPACE TOO — AND THAT IS A SECOND FIX, NOT A SIDE EFFECT

`skip_spaces` advances `HL` whether or not a `(` follows, so a **scalar** target
now returns with the cursor past its trailing spaces. Eight of the nine callers
cannot see that: `ex_next` (`nx_end`), `ex_read` (`exr_after`), both console
`INPUT` arms (`inpc_after`), `LINE INPUT`, `inp_readvar`, `ex_field` and
`lrset_common` each do their **own** `call skip_spaces` before reading the next
delimiter.

`ex_mid_stmt` is the exception — `pop hl` / `ld a,(hl)` / `cp ','`, a bare read —
so it is the one place the change is visible on the scalar path. Measured rather
than argued:

| row | program | both references | zerobas at `030f068` |
|---|---|---|---|
| `m.trail` | `A$="HELLO"` / `MID$(A$ ,1,2)="XY"` / `PRINT A$` | **`XYLLO`** | **Syntax error** |

⇒ the trailing-space consumption is **required**, not tolerated. One instruction
closes two divergences at that site.

### 4.4 RAM

None. No new variable, no new stack word.

---

## 5. Forced constraints

### 5.1 The skip must be a LOOP, and `x.multi` is the only row that says so

`NEXT A   (1)` (three spaces) is **NEXT without FOR** on both references. A
one-byte step (`inc hl` / `ld a,(hl)`) would pass every other spaced row in this
battery and fail this one — and would break every contiguous control besides.
`skip_spaces` loops; the row pins that it must.

### 5.2 🔴 THE SKIP MUST NOT MOVE EARLIER THAN `var_name_key`

Putting it before the name scan would be a different and far wider rule — the one
`x.dollar` and `x.name` measure (§3.2). It is out of scope here, it is not
priced, and conflating them would leave no row able to separate the two
([[one-row-cannot-separate-two-rules]]).

### 5.3 `ex_for` must NOT gain the reach

`ex_for` parses its loop variable with `for_name`, not `tgt_parse`
(`spec-basic-nxary.md` §5.2), and both references answer **Syntax error** to
`FOR A (1)=1 TO 3`. `z.for` is the negative control that says a widened target
parse did not leak into the one site that must keep refusing
([[gate-whose-answer-is-an-error-passes-a-dead-subject]]).

### 5.4 Register contract — checked, not assumed

At the cut point `AF` is **pushed** (it carries `var_str_type`'s mode across
`var_name_key`), `BC` holds the key `var_name_key` just returned, and `DE` is
already documented as not preserved. `skip_spaces` touches **A and HL only** and
calls nothing. Nothing else in `tgt_parse`'s contract changes.

### 5.5 Region

`tgt_parse` is at `$473E` and `skip_spaces` at `$4255` — both **main page 1**, so
the call adds no region hop and no new escape class for either tenant closure.
`ary_op0_resolve` stays the same low-region call it already was.

---

## 6. The carve scout

Off `build/basic-reloc.sym` from a clean build at `030f068` (`rm -rf build &&
make basic-reloc`): low **11 B**, page 1 **5 B**, sub p0 **3604 B**, sub p1
**1483 B**; `basic-reloc.rom 62a461c1…`, `sub.rom accce5a1…`, `disk.rom
2c630d3d…`, `zerobas-main-eu.rom 80a57733…`.

### 6.1 Region — asked before anything is priced

| symbol | address | region |
|---|---|---|
| `tgt_parse` … `tp_set` | `$473E`–`$4759` | **page 1** — the only bytes this slice writes |
| `skip_spaces` | `$4255` | page 1 — reused, unchanged |
| `var_name_key` | `$46B2` | page 1 — reused, unchanged |
| `ary_op0_resolve` | `$3F96` | LOW — reached *through* `tgt_parse`, unchanged |

`carve_scout.py build/basic-reloc.sym --files basic/vars.asm`: 59 labels, all 59
in page 1, **731 B leaves page 1** if the file moves. No eviction is proposed —
recorded because the scout was run before the price, not after.

### 6.2 The estimator, calibrated before it is used

Hand-counted from source and checked against the `.sym` **first**
([[calibrate-a-hand-counter-before-quoting-it]]):

| span | counted | `.sym` Δ | |
|---|---|---|---|
| `tgt_parse` → `tp_ary` | 1+3+1+2+2+1+3+1+2 = **16** | `$474E−$473E` = **16** | ✅ |
| `tp_ary` → `tp_res` | 1+1+2+3 = **7** | `$4755−$474E` = **7** | ✅ |
| `tp_res` → `tp_set` | 3+1 = **4** | `$4759−$4755` = **4** | ✅ |
| `tp_set` → `tgt_store_num` | 4+1 = **5** | `$475E−$4759` = **5** | ✅ |

**4/4 exact.**

⚠️ **AND THE LAYOUT HAZARD THAT CAUGHT D-NXARY IS ABSENT HERE, WHICH IS A CLAIM
AND NOT A HOPE.** §10.2 of `spec-basic-nxary.md` was 2 B light because its
arithmetic assumed a fallthrough that a label sitting in between forbids
([[knife-prediction-inherits-the-drafts-layout-error]]). This slice adds **no
label, no branch and no fallthrough**: it substitutes one instruction for another
at a fixed position inside one span. The only way it can be wrong is if
`skip_spaces` is not 3 bytes to call, and `$4255` is a page-1 address, so it is.

### 6.3 The cost — a BOUND, with the twin named for every part

| body | region | before | after | Δ |
|---|---|---|---|---|
| `tgt_parse` — `ld a,(hl)` (1) → `call skip_spaces` (3) | p1 | 16 | **18** | **+2** |
| `tp_ary` / `tp_res` / `tp_set` — unchanged, shifted | p1 | 7/4/5 | 7/4/5 | **0** |
| every caller — unchanged | p1 / low | | | **0** |
| low / sub p0 / sub p1 / RAM | — | | | **0** |
| **main page-1 total** | | | | **+2** |

### 6.4 The bottom line

| region | free at `030f068` | slice | free after |
|---|---|---|---|
| **main page 1** | **5 B** | **+2** | **3 B** |
| main low | 11 B | 0 | **11 B** |
| sub page 0 / page 1 | 3604 / 1483 | 0 | **unchanged** |

⚠️ **PAGE 1 IS THE BINDING WALL AND THIS LEAVES IT AT 3 B.** Stated rather than
buried. The residual was declined at 5 B free *for want of evidence*, and the
evidence is now 28 measured rows; but the next slice has almost nothing, and
must carve-scout before assuming a budget
([[which-wall-binds-is-a-history-question]]).

⚠️ **Predicted ROM hashes:** `basic-reloc.rom` **MOVES**; `zerobas-main-eu.rom`
**MOVES**; 🎯 **`sub.rom` HOLDS at `accce5a1…`** and **`disk.rom` HOLDS at
`2c630d3d…`** — `basic/vars.asm` is page 1, and `sub/basic-resident-abi.inc`
(generated from `basic-reloc.sym`) contains **zero** addresses ≥ `$4000`
(checked, not assumed), so no page-1 shift can reach either image.

### 6.5 ✅ VERDICT: **GO, +2 into 5.** No eviction, no RAM, no sub-ROM byte, no new label.

---

## 7. Predicted GREEN

`make tgtspc-characterize` must read, on all three sides:

| rows | prediction | |
|---|---|---|
| `t.ctl` `t.spc` | `83204128122900` / `8320412028122900` | 🟢 green before **and** after — the crunch is not touched |
| `n.ctl` `n.spc` `x.multi` `x.inner` | `NEXT without FOR` | the element matches no frame |
| `n.spcoob` `r.spcoob` | `Subscript out of range` | the FULL resolve, through two different callers' abort paths |
| `r.ctl` `r.spc` `r.spcauto` `i.ctl` `i.spc` | ` 0  7 ` | the ELEMENT took the value, not the scalar |
| `i.spcstr` `l.ctl` `l.spc` `f.ctl` `f.spc` | `HI` | |
| `m.ctl` `m.spc` `m.trail` | `XYLLO` | 🎯 `m.trail` is §4.3 |
| `d.ctl` `d.spc` | `OK` | |
| `s.ctl` `s.spc` | `HI        ` | |
| `z.for` | `Syntax error` | 🔴 **NEGATIVE control** — green before **and** after |
| `x.dollar` `x.name` | **DEFERRED** | §3.2 — measured, printed, **not scored** |

⇒ **`make tgtspc-acceptance` scores 26/26**, from **12/26** at `030f068`
(28 cases, 2 deferred).

⇒ **`make nxary-acceptance` scores 22/22**, from 21/21 + 1 deferred:
`a.spc` leaves `DEFERRED` in `probes/basic/basic_probe_nxary.py` and becomes an
ordinary scored row ([[a-deferral-honoured-is-worth-more-than-one-filed]]).

⚠️ **THE REGRESSION SURFACE IS EVERY LVALUE GATE, NOT A BYSTANDER LIST.** One
instruction inside the shared target parse reaches all nine surfaces, so
`readvar-acceptance` 24/24, `arylv-acceptance` 18/18, `inputary-acceptance` 7/7,
`lvfix-acceptance`, `fldary-acceptance`, `lrvar-acceptance`,
`forvar-acceptance` 33/33 and `nxlist-acceptance` 25/25 must all hold.

Static counters, each predicted by reading its own check's definition
([[a-count-is-predicted-by-reading-its-definition]]): `audit-citations` swept
757 → **760** (the probe + two docs), basic provenance-bearing 198 → **199**
(`provenance_files("basic")` = the `basic/`+`sub/` globs + `PROVENANCE.md` +
`probes/basic/*.py`, so the probe counts and the docs do not);
`injector-check` 345 → **346**; `rowshape-check` 15 → **16** probes;
`preflight-check` **181/86/95/95/0 unchanged** (the probe spawns nothing
directly — `omsx_repl` does); `latch-check` **16/16 unchanged**; `deadcode`
**0/0 (+1) unchanged**; closures **585+43 / 733+15 / 122+4 unchanged**
(`skip_spaces` is main page 1 and already in every closure `tgt_parse` is in);
`unit-test` **59 unchanged**.

---

## 8. Knives — drafted before the row set was frozen

Read [`dev-workflow.md`](dev-workflow.md) §"Knives" first. Subject = the probe
invoked directly, `--sides vg8020,cf3300,zb`, except K-TS5. Every cut is
byte-neutral. Every cut is run **twice**.

| # | cut (byte-neutral) | predicted RED | predicted GREEN |
|---|---|---|---|
| **K-TS1** | `tgt_parse`: `call skip_spaces` → `ld a,(hl)` + 2 × `nop` — the slice, reverted | 🎯 the **14** spaced rows: `n.spc` `n.spcoob` `r.spc` `r.spcauto` `r.spcoob` `i.spc` `i.spcstr` `l.spc` `m.spc` `m.trail` `f.spc` `d.spc` `s.spc` `x.multi` | the other 12: the 9 contiguous controls, `t.ctl` `t.spc`, `x.inner`, `z.for` |
| **K-TS2** | `ex_next`: `jp nz,fp_runtime_error` → 3 × `nop` — the resolve's failure is ignored at ONE caller | 🎯 **`n.spcoob` ONLY** | the other 25 |
| **K-TS3** | `ex_read`: `jp nz,fp_runtime_error` → 3 × `nop` — the same failure at a DIFFERENT caller | 🎯 **`r.spcoob` ONLY** | the other 25 |
| **K-TS4** | `tgt_parse`: `ld de,0` → `ld de,$8000` — every SCALAR target now looks like an element | 🎯 **`m.trail` ONLY** — the one scored row whose target is a scalar | the other 25 |
| **K-TS5** | `CONTROL_WANT["m.ctl"]` unmatchable (probe-only), `--sides vg8020,zb` | rc **2**, `NOT MEASURED`, ROMs **NOT** moved | — |

All five red sets are **pairwise distinct**, and **three of them redden exactly
one row**. K-TS1 is a strict superset of K-TS2 ∪ K-TS3 ∪ K-TS4.

🎯 **K-TS2 AND K-TS3 ARE THE SAME CUT AT TWO CALLERS, AND THAT IS THE POINT OF A
SHARED-ENGINE SLICE.** `n.spcoob` and `r.spcoob` both read `Subscript out of
range`, and a battery that could not separate them would be treating one abort
path as evidence for eight.

🔴 **K-TS4 EXISTS BECAUSE `m.trail` IS THE ONLY ROW ABOUT THE SCALAR PATH.**
Without a cut of its own, §4.3's claim — that the trailing-space consumption is
the mechanism, not a coincidence — would rest on reading the source.

⚠️ **`t.ctl` / `t.spc` HAVE NO CUT, AND THAT IS NAMED RATHER THAN LEFT IMPLIED.**
Their subject is the tokeniser, which this slice does not touch; a cut that moved
them would be measuring `basic_probe_crunch.py`'s gate, not this one. They are
here to answer *which file*, and they answered it before the design was written.

⚠️ **`x.dollar` / `x.name` have no cut either** — they are DEFERRED rows about
code this slice does not write.

---

## 9. Denominator

**(the NINE statement surfaces that reach `tgt_parse`: `NEXT`, `READ`, console
`INPUT` numeric, console `INPUT` string, `LINE INPUT`, `MID$()=`, `INPUT #n`,
`FIELD`, `LSET`/`RSET`) × (CONTIGUOUS `A(1)` control / SPACED `A (1)`)**, plus
whether the space **survives the crunch** at all (read from the stored line
bytes, which is what says whether the fix belongs in the tokeniser or the
parser), plus whether the spaced form runs the **full** resolve (range check) and
**auto-DIMs**, plus the SCALAR-path side effect at the one caller that reads its
delimiter without its own `skip_spaces`, plus the other space positions this fix
does **not** touch (more than one space; inside the subscript; before the `$`
suffix; inside the NAME), plus the `FOR A (1)=` form both references REFUSE.

**Not covered, and named rather than implied:** a TAB or any other whitespace
byte; a space before the `(` of a FUNCTION call or of `DIM`; `RSET` measured
separately from `LSET` (they share one parse site, so one pair of rows covers
both verbs and that is a claim about the CODE, not about the reference); a space
before the `(` of a *subscript's own* array element (`NEXT A (B (1))`); and the
name-scan rule `x.dollar` / `x.name` measure, which is filed as its own residual.

---

## 10. As-built

Implemented 2026-08-08 on `main`, based on `030f068`.

### 10.1 What landed

| file | change |
|---|---|
| [`basic/vars.asm`](../basic/vars.asm) | `tgt_parse`'s subscript test becomes `call skip_spaces` instead of `ld a,(hl)` — **one instruction**. Its header's stale "FOUR call sites" is replaced by the walked table of eight `call`s / nine surfaces |
| [`probes/basic/basic_probe_tgtspc.py`](../probes/basic/basic_probe_tgtspc.py) | **new**, 28 rows, 9 positive + 1 negative control, 2 deferred, two reading modes (`[...]` after `RUN`, and the STORED LINE BYTES for `t.*`) |
| [`probes/basic/basic_probe_nxary.py`](../probes/basic/basic_probe_nxary.py) | `a.spc` leaves `DEFERRED`; that dict is now **empty** |
| [`Makefile`](../Makefile) | `tgtspc-characterize` + `tgtspc-acceptance`, both `.PHONY` |

### 10.2 The walls — **and §6.3's bound was EXACT**

| wall | at `030f068` | §6.4 predicted | as built | |
|---|---|---|---|---|
| **main page 1** | 5 B | 3 B (+2) | **3 B** | ✅ |
| main low / sub p0 / sub p1 / RAM | 11 / 3604 / 1483 | unchanged | **11 / 3604 / 1483** | ✅ |

The hand counter was 4/4 exact against the `.sym` before the price was quoted,
and §6.2's claim that the layout hazard which cost D-NXARY 2 B is *structurally
absent here* — no new label, no new branch, no assumed fallthrough — held.

### 10.3 The ROM hashes — all four predicted

| ROM | at `030f068` | predicted | as built |
|---|---|---|---|
| `basic-reloc.rom` | `62a461c1…` | MOVES | **`38022d44…`** ✅ |
| `sub.rom` | `accce5a1…` | **HOLDS** | **`accce5a1…`** ✅ |
| `disk.rom` | `2c630d3d…` | **HOLDS** | **`2c630d3d…`** ✅ |
| `zerobas-main-eu.rom` | `80a57733…` | MOVES | **`d6d36c7e…`** ✅ |

### 10.4 The gates

| gate | before | predicted | measured |
|---|---|---|---|
| **`tgtspc-acceptance`** | 12/26 | 26/26 | **26/26, 2 deferred** ✅ |
| **`nxary-acceptance`** | 21/21 + 1 deferred | 22/22 | **22/22, 0 deferred** ✅ |
| `forvar` / `nxlist` / `readvar` / `arylv` / `inputary` | 33 / 25 / 24 / 18 / 7 | unchanged | **33/33 · 25/25 · 24/24 · 18/18 · 7/7** ✅ |
| `lvfix` / `fldary` / `lrvar` | 18 / 13 / 21 | unchanged | **18/18 · 13/13 · 21/21** ✅ |
| `audit-citations` swept / basic | 757 / 198 | 760 / 199 | **760 / 199** ✅ |
| `injector-check` | 345 | 346 | **346** ✅ |
| `rowshape-check` | 15 | 16 probes | **16** ✅ |
| closures | 122+4 / 733+15 / 585+43 | unchanged | **unchanged** ✅ |
| `unit-test` · `preflight` · `latch` · `deadcode` | 59 · 181/86/95/95/0 · 16/16 · 0/0 | unchanged | **unchanged** ✅ |

### 10.5 🔴 Three things went differently

**(a) THE RESIDUAL'S PRICE WAS WRONG, AND IN THE CHEAP DIRECTION.** `TODO.md` and
`nxary-msx1-characterization.md` §4 both said *"the fix is **3 bytes**"*. It is
**2**: the instruction being replaced is one byte, not zero, and a filed cost
that forgets what it displaces is a cost for an insertion, not a substitution.
The error was harmless here only because the wall had room either way.

**(b) THE CALL-SITE COUNT WAS WRONG IN THREE DOCUMENTS AT ONCE.** `TODO.md`,
`nxary-msx1-characterization.md` §4 and `ex_next`'s own code comment all said
**seven**. Walked: **eight `call tgt_parse` instructions, nine statement
surfaces** — the hand list is seven *other* surfaces and forgot to count
`ex_next`, the site that filed the residual, and it folds the console `INPUT`'s
two arms (two distinct `call`s) into one
([[a-hand-listed-denominator-is-a-scope-claim]]). A denominator written as a
sentence rather than derived from a walk under-counted the surface a fix has to
be right about, and it did so in the same document that warned the fix was wide.

**(c) 🔴 K-TS4 REDDENED A SECOND ROW, AND THE PREDICTION HAD WRITTEN "SCORED"
INTO A CLAIM THE INSTRUMENT DOES NOT MAKE.** §8 predicted **`m.trail` ONLY** —
*"the one **scored** row whose target is a scalar"*. `x.dollar` (`NEXT A $(1)`)
has a scalar target here too, and a knife runner diffs every row the probe
**prints**: `probe_report.parse()` returns the deferred rows like any other and
nothing in the diff knows what *scored* means. The qualifier that made the
sentence true of the **gate** made it false of the **knife**.
🎯 **And the extra row is CORROBORATION, not noise.** `x.dollar` moving under a
cut that touches nothing but the SCALAR marker is independent evidence that
zerobas really does parse `NEXT A $(1)` as the scalar `A` — which is exactly the
mechanism §3.2 gives as the reason to defer it. The deferral's stated cause now
has a cut behind it instead of only a source reading.

### 10.6 Knives — 5 cuts × 2 rounds, **4 EXACT, both rounds identical**

| # | cut | predicted RED | measured | |
|---|---|---|---|---|
| **K-TS1** | `tgt_parse`: `call skip_spaces` → `ld a,(hl)` + 2 × `nop` | 🎯 the 14 spaced rows | **exactly those 14** | ✅ ×2 |
| **K-TS2** | `ex_next`: `jp nz,fp_runtime_error` → 3 × `nop` | 🎯 **`n.spcoob` ONLY** | **`n.spcoob` ONLY** | ✅ ×2 |
| **K-TS3** | `ex_read`: `jp nz,fp_runtime_error` → 3 × `nop` | 🎯 **`r.spcoob` ONLY** | **`r.spcoob` ONLY** | ✅ ×2 |
| **K-TS4** | `tgt_parse`: `ld de,0` → `ld de,$8000` | **`m.trail` ONLY** | **`m.trail` + `x.dollar`**, see (c) | ❌ ×2 |
| **K-TS5** | `CONTROL_WANT["m.ctl"]` unmatchable, `--sides vg8020,zb` | rc 2, ROMs unmoved | **rc 2 + `NOT MEASURED` banner, ROMs held** | ✅ ×2 |

§8 claimed three knives would redden exactly one row; **two did**. K-TS2 and
K-TS3 are the same cut at two different callers and separate cleanly, which is
the measurement a shared-engine slice owes: `n.spcoob` and `r.spcoob` read the
same `Subscript out of range` and are **not** one abort path.

⚠️ **`t.ctl` / `t.spc` have no cut** — their subject is the tokeniser, which this
slice does not touch; a cut that moved them would be measuring
`basic_probe_crunch.py`'s gate. Named rather than left implied, as are
`x.dollar` / `x.name`, which are DEFERRED rows about code this slice does not
write (and (c) is why one of them moved anyway).

### 10.7 Corpus

Sequentially from clean (`rm -rf build`, **bash** — `zsh` does not word-split
`make $t`), **31 targets, all rc=0, 16 min 27 s wall**: the 29 of
[`spec-basic-nxlist.md`](spec-basic-nxlist.md) §10.7 — `unit-test` 59 ·
`audit-citations` CLEAN (760 swept) · `preflight-check` 181/86/95/95/0 ·
`injector-check` 346 · `rowshape-check` 16 probes · `latch-check` 16/16 ·
`deadcode` 0/0 · `lnblank-acceptance REPEAT=2` · `lnblank-say-acceptance` ·
`logicops` · `float` · `linemax` · `dexp5-pin` · `editverb` · `lptverb` ·
`dskmsg` · `diskbasic` · `fat-error` · `runtail` · `castail` · `cassave` ·
`readvar-acceptance` 24/24 · `arylv-acceptance` 18/18 ·
`inputary-acceptance` 7/7 · `lvfix-acceptance` 18/18 ·
`fldary-acceptance` 13/13 · `lrvar-acceptance` 21/21 ·
`forvar-acceptance` 33/33 · `nxlist-acceptance` 25/25 — **plus
`nxary-acceptance` 22/22**, **plus `tgtspc-acceptance` 26/26**.

⚠️ `latch-check` still has **no `repack-machine` prerequisite**, so the script
builds explicitly before the loop; and `lnblank-acceptance` **defaults to
`REPEAT=1`**, so the `REPEAT=2` is passed by hand
([[pin-fired-inside-its-own-slice]]).

Copy *this* list forward, not the last one — the gate a slice ADDS is exactly the
one a runner rebuilt from the previous slice omits (D-NXARY §10.7).

### 10.8 The fix, as a program

Every cell below is a LITERAL screen row, read after `RUN` — the "before" column
from a rebuilt pre-fix ROM (`basic-reloc.rom 62a461c1…`, hash checked), not from
the battery's error-name reading.

```basic
10 FOR A=1 TO 2
20 NEXT A (1)
30 PRINT "[OK]"
```

| | screen after `RUN` |
|---|---|
| VG-8020 / CF-3300 | `NEXT without FOR in 20` |
| zerobas **before** → **after** | `Syntax error in 20` → **`NEXT without FOR in 20`** |
| under **K-TS1** (the skip reverted) | `Syntax error in 20` — the whole slice, in one instruction |

…and the same instruction at two sites nobody had connected to it:

```basic
10 DATA 7
20 READ A (1)
30 PRINT A;A(1)
```

| | screen after `RUN` |
|---|---|
| VG-8020 / zerobas **after** | ` 0  7 ` — the ELEMENT took it, and `A()` was AUTO-DIMmed by the reference too |
| zerobas **before** | `Syntax error in 20` |

```basic
10 A$="HELLO"
20 MID$(A$ ,1,2)="XY"
30 PRINT A$
```

| | screen after `RUN` |
|---|---|
| VG-8020 / zerobas **after** | `XYLLO` |
| zerobas **before** | `Syntax error in 20` |

🎯 **The third program has no subscript at all.** It is the SCALAR path, and it
is why §4.3's "side effect" is a second fix: `ex_mid_stmt` is the one caller that
reads its delimiter without its own `skip_spaces`.
