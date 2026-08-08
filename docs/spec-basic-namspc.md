# D-NAMSPC — a SPACE *inside* a variable reference's NAME

*Subject: the residual D-TGTSPC filed and DEFERRED in `TODO.md` — a space inside
a variable reference's name, or before its type suffix.*

Based on `36a107e` (D-TGTSPC). Measurement:
[`namspc-msx1-characterization.md`](namspc-msx1-characterization.md),
`make namspc-characterize`, `probes/basic/basic_probe_namspc.py`.

---

## 1. The rule — measured before it was designed

D-TGTSPC had **two** rows (`x.dollar`, `x.name`) and a mechanism read out of the
source. Two rows are not a rule, and the routines the fix touches are shared by
**every variable reference in the interpreter** — 11 `var_name_key` call sites
and 16 `var_str_type` call sites, against `tgt_parse`'s nine lvalue surfaces. So
the denominator was built first, and it is **not** the lvalue one.

**58 rows, three sides, BOTH REFERENCES AGREEING ON ALL 56 THEY CAN BOTH
EXPRESS.** 29 of the 56 scored rows agree at `36a107e`. ⚠️ The set was frozen at
**55** when §4–§9 below were written and grew by three during implementation —
see §10.5(b), and see §8 for why that invalidated every knife prediction written
against it. The full table is in the characterization; the rule it states:

> A variable REFERENCE's NAME may contain any run of spaces, at any position
> inside it, and any run of spaces may separate it from its type suffix. The
> reference then resolves to **exactly the variable the contiguous spelling
> names** — the same two significant characters, the same suffix type, the same
> key. This is the NAME SCAN's rule, not any statement's: it holds in an r-value
> expression, a LET target, an `IF` condition, `FOR`, `NEXT`, `DIM`, an array
> element lvalue, `READ` and `SWAP` alike.

Four clauses are readings no earlier row asked, and each one decides bytes:

* 🎯 **`r.name` — IT IS UNIVERSAL, NOT AN LVALUE RULE, AND THAT IS THE READING
  THAT SIZED THE SLICE.** `AB=7` / `PRINT A B` reads ` 7 ` — **one** value, the
  variable `AB` — on both references, against ` 0  0 ` (two values) here.
  `PRINT` never touches `tgt_parse`. Had this come back ` 0  0 ` on the
  references, the fix would have been a second D-TGTSPC-shaped patch at a
  handful of target sites; it did not, so the fix belongs in the one place every
  reference passes through.
* 🎯 **`t.*` — THE SPACE SURVIVES THE CRUNCH IN EVERY POSITION, AND THAT IS WHAT
  SAYS WHICH FILE.** Twelve tokeniser rows, read from the **stored line bytes**
  through `TXTTAB`, are green on all three sides *before* the fix. `1 A B=1`
  stores `41 20 42 EF 12 00`; `1 AB $="X"` stores `41 42 20 24 …`; and 🔴 **`1 A
  1=1` stores `41 20 31 …` — the digit stays VERBATIM after the space.** That
  last one was the hazard that could have moved the whole slice into the
  tokeniser: a digit is copied verbatim only while the in-name flag `TKNAME`
  ($E028) is set, and had a space cleared it, `A 1` would store a numeric
  constant that no parser-side scan could ever rejoin. It does not. ⇒ **parser
  fix, and zerobas's crunch already agrees with both references byte for byte.**
* 🎯 **`r.three` / `r.run` / `a.sig` — THE TWO-CHARACTER KEY IS UNCHANGED.**
  `A B C`, `AB CD` and `A B C=7` all resolve to the key `(A,B)` on both
  references: the 3rd+ characters are consumed and ignored across a space
  exactly as they are without one. So a spaced name still **collides** with its
  contiguous spelling, and no new key shape is needed.
* 🎯 **`z.miss` — THE JOINED NAME IS A DIFFERENT VARIABLE, NOT TOLERATED JUNK.**
  `FOR A=1 TO 2` / `NEXT A B` is **NEXT without FOR** on both references. A fix
  that merely learned to *ignore* the space and its tail would answer `OK` here
  and pass every other row in the battery.

And two rows are the CONSTRAINT, measured rather than assumed — see §3.2 and
§3.3.

---

## 2. What is wrong, in one sentence

`is_ident_cont` (`basic/vars.asm:48`) tests the byte its caller loaded with a
bare `ld a,(hl)`, so all three name-scan read points — `var_name_key`'s second
character, its 3rd+ loop, and `var_str_type`'s suffix walk — stop dead at a
space, and every variable reference in the interpreter is lexically contiguous.

---

## 3. Scope

### 3.1 The call-site walk, done rather than restated

`grep -n "call\s*is_ident_cont" basic/ sub/`:

| # | site | file:line | what it reads |
|---|---|---|---|
| 1 | `var_name_key` | `basic/vars.asm:74` | the **second** name character |
| 2 | `vnk_more` | `basic/vars.asm:84` | every **3rd+** name character |
| 3 | `vst_walk` | `basic/vars.asm:167` | `var_str_type`'s walk to the suffix |

**THREE call sites, all in `basic/vars.asm`, and they are exactly the three read
points the rule needs.** That is not a coincidence to be relied on quietly — it
is the reason §4.1's fix is one instruction rather than three: `is_ident_cont`
has no caller that wants the old, cursor-preserving contract. D-CNAME already
deleted the only other copy (a sub-local clone, `sub/PROVENANCE.md`), so the walk
is complete and small.

⚠️ **AND THE LAST TIME A DOCUMENT PRESCRIBED A CHANGE TO `is_ident_cont`, THE
PRESCRIPTION WAS REFUTED.** D-NAMDOT's knife K4 (`basic/PROVENANCE.md`, ~4317)
made the filed *"accept `.` too"* change and drove `B.5=7` from ERR 2 to ERR 0 —
shipping a divergence in the exact place the item pointed at, because MSX1's
tokeniser charset and its executor charset are **different charsets**. This
slice changes a different axis: it does **not** widen the character set, it
skips `$20` *before* the unchanged test. `B .5` stays `Syntax error` because `.`
is still not an identifier character. The difference from K4 is not an argument,
it is 58 measured rows.

### 3.2 🔴 THE KEYWORD CONSTRAINT — a spaced name can be a TOKEN before any parser sees it

This tree's tokeniser matches keywords at **every** position mid-identifier,
exactly like MS-BASIC (`dev-workflow.md` §"Tokeniser quirks"). Three rows fix
what that means for a space-skipping name scan, and they point in **both**
directions:

| row | line | stored bytes (all three sides) |
|---|---|---|
| `t.kwctl` | `1 SCORE=1` | `53 43 **F7** 45 EF 12 00` — `SC` + `OR` + `E` |
| `t.kw` | `1 SC ORE=1` | `53 43 20 **F7** 45 EF 12 00` — the space is stored **and the `OR` token is still there** |
| `t.absctl` | `1 ABS=1` | `**FF 86** EF 12 00` — one token |
| `t.abs` | `1 A BS=1` | `41 20 42 53 EF 12 00` — `A`,` `,`B`,`S`: **no token at all** |

⇒ the match is **positional**: a space blocks it at the position it occupies,
and does not prevent one at the next. So a spaced name may or may not survive to
the parser, and **the name scan must not try to be cleverer than the tokeniser
that already ran.** `z.kw` is the negative control that pins it: `SC ORE=7` is
`Syntax error` on both references *and here*, before and after, because the
scan stops at the `$F7` byte like any other non-identifier.

`k.and` and `k.abs` are the same constraint from the green side: `AN=7` /
`PRINT A ND` reads ` 7 ` and `AB=7` / `PRINT A BS` reads ` 7 ` on both
references — the spaced forms are ordinary names precisely because the crunch
found no keyword in them.

### 3.3 🔴 WHAT THE RULE COSTS — `FIELD #1,N AS A$` STOPS WORKING, ON BOTH MACHINES

`AS` is **not** in `basic/kwtable.inc` and is not a token: `ex_field`
(`basic/field.asm:272`) `eval`s the field width and then reads the two literal
characters `'A'`,`'S'`. So a *variable* width is followed by bare letters, and a
name scan that skips spaces must swallow them.

| row | program | CF-3300 | zerobas at `36a107e` |
|---|---|---|---|
| `z.fldctl` | `FIELD#1,10 AS A$(1)` | `OK` | `OK` 🟢 control |
| `z.fldvar` | `FIELD#1,N AS A$(1)` | **Type mismatch** | **`OK`** 🔴 |

🎯 **THE REFERENCE REFUSES IT, AND THE MECHANISM PREDICTS THE EXACT ERROR.**
With the fix, `N AS A$` is scanned as ONE reference: `N` + skip + `A` (name1) +
`S` (ignored) + skip + `A` (ignored) + `$` (suffix) — a **string** name in a
numeric factor, which `ev_f_var`'s `check_vartype_num` answers as **Type
mismatch**, not `Syntax error`. That is §7's sharpest prediction: this row is
red today and must go **GREEN**, on a value nobody chose for it.

This is the honest price of the rule and it is stated rather than discovered
later: a construct that works in zerobas today stops working — because it does
not work on the reference either, which is the charter
([[bug-for-bug-compat-over-accuracy]]).

### 3.4 The boundary — what this slice does NOT touch

* **Direct mode.** `TODO.md`'s `dir-name` residual (`B1 1=7 : PRINT B11`) is the
  same rule typed at the prompt. `a.dig` is its program-mode twin and *is* in
  this battery, so the fix very probably closes it — but that row lives in the
  un-gated `--say` surface of a different probe and closing it is that
  residual's job, not this one's ([[say-only-rows-are-ungated]]).
* **A TAB or any other whitespace byte.** `skip_spaces` skips `$20` only, before
  and after.
* **`OPEN A$ AS #1`** — measured in passing on the CF-3300 as `OK` against
  `Syntax error` here. Nothing to do with spaces (the `$` suffix terminates the
  scan before the ` AS`), unaffected by this fix, and filed as its own residual.

---

## 4. Design

### 4.1 🎯 ONE INSTRUCTION, IN THE ONE PLACE ALL THREE READ POINTS SHARE

`basic/vars.asm`:

```
is_ident_cont:
                call    is_letter           ; letter -> CF set, A preserved
                ret     c
```

becomes

```
is_ident_cont:
                call    skip_spaces         ; ← 3 B; A = first non-space, HL on it
                call    is_letter
                ret     c
```

…and the `ld a,(hl)` that **every one of its three callers** performs
immediately before the call becomes dead and is deleted:

```
                ld      a,(hl)              ; ← deleted at vars.asm:73, :83, :166
                call    is_ident_cont
```

`skip_spaces` (`basic/interp.asm:620`) is `ld a,(hl)` / `cp ' '` / `ret nz` /
`inc hl` / `jr skip_spaces` — with no space it returns **exactly what
`ld a,(hl)` returned**, with `HL` on the byte in `A`. So the substitution is
value-for-value at all three sites.

**+3 B in the callee, −1 B × 3 at the callers: the rule itself is NET ZERO.**

### 4.2 Why in the callee and not at the three callers

Three `call skip_spaces` insertions would cost **+6 B** and leave
`is_ident_cont` still wrong for the next caller anyone adds. Putting it in the
callee costs nothing because it *removes* the load each caller was doing
anyway. The contract change is real and is documented in capitals at the routine:
`is_ident_cont` is no longer a pure predicate on `A`, it is a cursor scan —
`A` and `HL` are outputs, not inputs.

### 4.3 The carve that comes with it — `vnk_dig2` is a dead reload

```
                call    is_letter
                jr      nc,vnk_dig2
                call    upcase
vnk_set2:       ld      c,a
...
vnk_dig2:       ld      a,(hl)              ; ← re-reads what A already holds
                jr      vnk_set2
```

`is_letter` (`basic/interp.asm:122`) is `push af` … `pop af` on **both** exits,
and `is_ident_cont` only `cp`s — so at `vnk_dig2` **`A` already holds the
digit**. The reload is dead, and `jr nc,vnk_dig2` can point straight at
`vnk_set2`.

**−3 B**, and it is not an unmeasured tidy-up: `r.digctl` / `r.dig` / `a.dig`
are the rows that fail if the register reading is wrong, and **K-NS2 is the
knife that proves they can see it** (§8).

### 4.4 The cursor contract widens, and `w.*` is what catches it

With the skip in the callee, `vnk_more` now consumes a name's **trailing**
spaces on its way to look for a suffix, so `var_name_key` returns with `HL` past
them on the no-suffix path — the same widening D-TGTSPC made one cursor position
later, now at all 11 call sites. `w.let` (`AB =7`), `w.print` (`PRINT AB ;`),
`w.for` (`FOR AB =1 TO 2`) and `w.comma` (`SWAP AB ,CD`) are **green on all
three sides before the fix** and must stay green; they are the only rows able to
catch a scan that eats one delimiter too many.

⚠️ The `vnk_eat` path (a suffix **was** found) does **not** skip, so
`tgt_parse`'s own `call skip_spaces` — D-TGTSPC's whole slice — is still
load-bearing for `A$ (1)` and is untouched. Checked, not assumed.

### 4.5 RAM

None. No new variable, no new stack word, no new label.

---

## 5. Forced constraints

### 5.1 The skip must be a LOOP — `r.multi` is the only row that says so

`AB=7` / `PRINT A  B` (two spaces) reads ` 7 ` on both references. A one-byte
step would pass every other spaced row here and fail this one.

### 5.2 It must be INSIDE `is_ident_cont`, not before `var_name_key`

Skipping at entry would skip leading spaces the callers have already handled and
would not reach the 3rd+ loop or `var_str_type`'s walk at all — `r.run`,
`r.three` and `r.instr` are the rows that separate the two.

### 5.3 `z.kw` must STAY refused

`SC ORE=7` carries the `OR` token; the scan must stop at it. This is automatic
(a token byte is not an identifier character) and is stated so that a future
"improvement" that special-cases tokens has a row in its way
([[gate-whose-answer-is-an-error-passes-a-dead-subject]]).

### 5.4 Register contract — checked, not assumed

At all three call sites `A` is dead on entry (each was about to be overwritten by
`ld a,(hl)`), `BC` holds the key under construction, and `HL` is the cursor.
`skip_spaces` touches **A and HL only** and calls nothing. `var_str_type`'s `HL`
is `push`/`pop`-scratch, so its walk advancing is invisible to its callers.

### 5.5 Region

`is_ident_cont` is at `$46A2` and `skip_spaces` at `$4255` — both **main page 1**,
so the call adds no region hop and no new escape class for any tenant closure.

---

## 6. The carve scout

Off `build/basic-reloc.sym` from a clean build at `36a107e` (`rm -rf build &&
make basic-reloc`): low **11 B**, page 1 **3 B**, sub p0 **3604 B**, sub p1
**1483 B**; `basic-reloc.rom 38022d44…`, `sub.rom accce5a1…`, `disk.rom
2c630d3d…`, `zerobas-main-eu.rom d6d36c7e…`.

### 6.1 Region — asked before anything is priced

| symbol | address | region |
|---|---|---|
| `is_ident_cont` … `iic_no` | `$46A2`–`$46B2` | **page 1** — where the instruction lands |
| `var_name_key` … `vnk_suffix` | `$46B2`–`$46D6` | **page 1** — the three deletions + the carve |
| `var_str_type` … `vst_suffix` | `$470A`–`$4719` | **page 1** |
| `skip_spaces` | `$4255` | page 1 — reused, unchanged |
| `tgt_parse` | `$473E` | page 1 — **unchanged**, §4.4 |

`carve_scout.py build/basic-reloc.sym --files basic/vars.asm`: 59 labels, all 59
in page 1, **733 B leaves page 1** if the file moves. No eviction is proposed —
recorded because the scout was run before the price, not after.

### 6.2 The estimator, calibrated before it is used

Hand-counted from source and checked against the `.sym` **first**
([[calibrate-a-hand-counter-before-quoting-it]]):

| span | counted | `.sym` Δ | |
|---|---|---|---|
| `is_ident_cont` → `iic_no` | 3+1+2+2+2+2+1+1 = **14** | `$46B0−$46A2` = **14** | ✅ |
| `iic_no` → `var_name_key` | 1+1 = **2** | `$46B2−$46B0` = **2** | ✅ |
| `var_name_key` → `vnk_set2` | 1+3+1+1+2+1+3+2+3+2+3 = **22** | `$46C8−$46B2` = **22** | ✅ |
| `vnk_set2` → `vnk_more` | 1+1 = **2** | `$46CA−$46C8` = **2** | ✅ |
| `vnk_more` → `vnk_dig2` | 1+3+2+1+2 = **9** | `$46D3−$46CA` = **9** | ✅ |
| `vnk_dig2` → `vnk_suffix` | 1+2 = **3** | `$46D6−$46D3` = **3** | ✅ |
| `var_str_type` → `vst_walk` | 1+3+1+1 = **6** | `$4710−$470A` = **6** | ✅ |
| `vst_walk` → `vst_suffix` | 1+3+2+1+2 = **9** | `$4719−$4710` = **9** | ✅ |

**8/8 exact.**

⚠️ **AND THE LAYOUT HAZARD IS NAMED RATHER THAN HOPED AWAY.** D-NXARY was 2 B
light because its arithmetic assumed a fallthrough a label forbids
([[knife-prediction-inherits-the-drafts-layout-error]]). This slice **deletes** a
label (`vnk_dig2`) and re-points one `jr` at an existing one; it adds no label,
no branch and no new fallthrough. The only arithmetic risk is the `jr` range, and
`vnk_set2` sits **4 bytes** before the re-pointed instruction.

### 6.3 The cost — a BOUND, with the twin named for every part

| body | region | before | after | Δ |
|---|---|---|---|---|
| `is_ident_cont` — `call skip_spaces` prepended | p1 | 14 | **17** | **+3** |
| `var_name_key` head — `ld a,(hl)` deleted | p1 | 22 | **21** | **−1** |
| `vnk_more` — `ld a,(hl)` deleted | p1 | 9 | **8** | **−1** |
| `vst_walk` — `ld a,(hl)` deleted | p1 | 9 | **8** | **−1** |
| — the RULE's own cost — | | | | **0** |
| `vnk_dig2` — deleted, `jr nc,vnk_dig2` → `jr nc,vnk_set2` (§4.3 carve) | p1 | 3 | **0** | **−3** |
| every caller / `tgt_parse` / low / sub p0 / sub p1 / RAM | — | | | **0** |
| **main page-1 total** | | | | **−3** |

### 6.4 The bottom line

| region | free at `36a107e` | slice | free after |
|---|---|---|---|
| **main page 1** | **3 B** | **−3** | **6 B** |
| main low | 11 B | 0 | **11 B** |
| sub page 0 / page 1 | 3604 / 1483 | 0 | **unchanged** |

🎯 **THE RULE IS FREE AND THE SLICE GIVES THE BINDING WALL 3 B BACK.** The
residual was filed *"not scouted and not priced, and page 1 is at 3 B"* with a
carve expected to be most of the work. It is not: the fix is cheaper than the
code it replaces because all three read points were already loading the byte the
callee now loads itself. Page 1 goes **3 → 6 B**, which is still nearly empty —
the next slice must carve-scout before assuming a budget
([[which-wall-binds-is-a-history-question]]).

⚠️ **Predicted ROM hashes:** `basic-reloc.rom` **MOVES**; `zerobas-main-eu.rom`
**MOVES**; 🎯 **`sub.rom` HOLDS at `accce5a1…`** and **`disk.rom` HOLDS at
`2c630d3d…`** — `basic/vars.asm` is page 1, and `make basic-reloc`'s own
resident-closure gate states it: *"122 routines in the resident closure of 11 ABI
seeds, + 4 data-referenced label(s), **all page-0 (< $4000). No page-1
escapes**"*. Checked from the gate, not assumed.

### 6.5 ✅ VERDICT: **GO, −3 into 3.** No eviction, no RAM, no sub-ROM byte, one label deleted.

---

## 7. Predicted GREEN

`make namspc-characterize` must read, on all three sides:

| rows | prediction | |
|---|---|---|
| the 12 `t.*` rows | unchanged hex | 🟢 green before **and** after — the tokeniser is not touched |
| `r.name` `r.multi` `r.three` `r.run` `k.and` `k.abs` | ` 7 ` | the r-value scan — **the universality claim** |
| `r.dig` | ` 7 ` | 🔴 from `<RUN SCROLLED OFF>` — a **hang** becomes a value |
| `r.instr` `r.dollar` | `HI` | `var_str_type`'s walk crosses the space |
| `r.pct` `r.bang` `r.hash` | ` 7 ` | 🔴 three more hangs become values |
| `a.name` `a.dig` `a.sig` | ` 7 ` | the LET store keys the same cell |
| `a.str` `a.dollar` | `HI` | |
| `s.if` `s.for` `s.next` | `OK` | `s.next` **is** D-TGTSPC's deferred `x.name` |
| `s.dim` `s.ary` `s.read` | ` 7 ` | |
| `s.swap` | ` 9  7 ` | |
| `z.miss` | `NEXT without FOR` | 🔴 **NEGATIVE control** — the joined name is a DIFFERENT variable |
| `z.kw` | `Syntax error` | 🔴 **NEGATIVE control** — green before **and** after |
| `w.let` `w.print` `w.for` `w.comma` | unchanged | 🟢 green before **and** after — §4.4 |
| **`z.fldvar`** | **`Type mismatch`** | 🎯 **the sharpest prediction in this document** — §3.3 |
| the 18 positive controls | unchanged | |

⇒ **`make namspc-acceptance` scores 55/55**, from **29/55** at `36a107e`.
⚠️ As built this is **56/56 with 2 deferred**, over 58 cases — §10.5(b).

⇒ **`make tgtspc-acceptance` scores 28/28**, from 26/26 + 2 deferred: `x.dollar`
and `x.name` leave `DEFERRED` in `probes/basic/basic_probe_tgtspc.py` and become
ordinary scored rows, and that dict becomes **empty**
([[a-deferral-honoured-is-worth-more-than-one-filed]]).

⚠️ **THE REGRESSION SURFACE IS EVERY VARIABLE REFERENCE, WHICH IS NOT A BYSTANDER
LIST — IT IS THE WHOLE INTERPRETER.** One instruction inside the shared name scan
reaches all 11 `var_name_key` and all 16 `var_str_type` call sites, so the entire
corpus is the regression gate, and in particular `crunch` (the tokeniser is
untouched — assert it), `forvar` 33/33, `nxlist` 25/25, `nxary` 22/22,
`readvar` 24/24, `arylv` 18/18, `inputary` 7/7, `lvfix` 18/18, `fldary` 13/13,
`lrvar` 21/21 and `lnblank` (which carries D-NAMDOT's `.` rows — §3.1).

Static counters, each predicted by reading its own check's definition
([[a-count-is-predicted-by-reading-its-definition]]) and **already realised by
the probe file itself**: `audit-citations` swept 760 → **761**, basic
provenance-bearing 199 → **200**; `injector-check` 346 → **347**;
`rowshape-check` 16 → **17** probes; `preflight-check` **181/86/95/95/0
unchanged**; `latch-check` **16/16 unchanged**; `deadcode` **0/0 (+1)
unchanged** — ⚠️ *unless the `vnk_dig2` deletion is done wrong, in which case the
dead-code gate fails the BUILD, which is the outcome to want*; closures
**122+4 / 733+15 / 585+43 unchanged** (`skip_spaces` is main page 1 and already
in every closure `is_ident_cont` is in); `unit-test` **59 unchanged**.

---

## 8. Knives — drafted before the row set was frozen

Read [`dev-workflow.md`](dev-workflow.md) §"Knives" first. Subject = the probe
invoked directly, `--sides vg8020,cf3300,zb`, except K-NS5. Every cut is
byte-neutral. Every cut is run **twice**.

🔴 **AND THE PREDICTIONS ARE QUANTIFIED OVER THE ROWS THE KNIFE CAN SEE, NOT THE
ROWS THE GATE SCORES.** D-TGTSPC's K-TS4 missed for exactly that: a runner diffs
what the probe **prints**, and `probe_report.parse()` returns every printed row
(`spec-basic-tgtspc.md` §10.5(c)). This probe has no deferred rows, and the sets
below are stated over all **55** printed rows.

Subject run at `--sides vg8020,zb` (a REFERENCE plus zb, never a lone zb —
the diff is over zb's values, and vg8020 is the cheaper of the two references).

| # | cut (byte-neutral) | predicted RED | predicted GREEN |
|---|---|---|---|
| **K-NS1** | `is_ident_cont`: `call skip_spaces` → `ld a,(hl)` + 2 × `nop` — the rule, reverted to exactly its pre-slice semantics | 🎯 the **28** rows the rule moves: the 26 red at `36a107e` (`r.name` `r.multi` `r.three` `r.run` `r.dig` `r.instr` `r.dollar` `r.pct` `r.bang` `r.hash` `a.name` `a.dig` `a.str` `a.dollar` `a.sig` `s.if` `s.for` `s.next` `s.dim` `s.ary` `s.read` `s.swap` `k.and` `k.abs` `z.miss` `z.fldvar`) **plus `z.join` `z.joinnum`** | the other 30: all 18 controls, the 12 `t.*`, `z.kw`, `w.*`, `z.fldstr` |
| **K-NS2** | `var_name_key`: `jr nc,vnk_set2` → `jr nc,vnk_more` — a digit second character folds into the ignored 3rd+ tail, so `A1` and `A` collide | 🎯 **`r.digctl` `r.dig` `a.dig` ONLY** (3) | the other 55 |
| **K-NS3** | `vst_suffix`: `cp '$'` → `cp '@'` — `var_str_type` never calls a name a string | `r.strctl` `r.instr` `r.dollar` `a.str` `a.dollar` `z.fldctl` `z.fldstr` `z.join` (8) | the other 50 |
| **K-NS4** | `vnk_more`: `jr vnk_more` → `jr vnk_suffix` — the 3rd+ loop consumes at most ONE character | `r.run` `z.join` `z.joinnum` (3) | the other 55 |
| **K-NS5** | `CONTROL_WANT["c.let"]` unmatchable (probe-only), `--sides vg8020,zb` | rc **2**, `NOT MEASURED`, ROMs **NOT** moved | — |

All five red sets are **pairwise distinct**; K-NS2 and K-NS3 each contain a
POSITIVE CONTROL that K-NS1 cannot touch, and K-NS2 / K-NS4 redden three rows
each.

🔴 **AND THIS TABLE WAS RECOMPUTED, WHICH IS THE POINT OF DRAFTING KNIVES
BEFORE FREEZING A ROW SET RATHER THAN AFTER.** The first draft predicted
*"`r.run` ONLY"* for K-NS4 and omitted `z.join` / `z.joinnum` everywhere,
because those three rows did not exist yet — they were added when the `z.fldvar`
measurement in §3.3 turned out to need isolating (§10.5(b)). A prediction is
quantified over a row set, so a row set that grows **invalidates every
prediction written against it**; the sets above are the recomputed ones, and
they were recomputed *before* the battery ran.

🎯 **K-NS2 IS THE KNIFE FOR THE CARVE, AND DRAFTING IT FOUND A MISSING ROW.** The
first row set had `r.digctl` = `A1=7` / `PRINT A1` and `r.dig` = `A1=7` /
`PRINT A 1`. Under this cut the key corruption is **symmetric** — the store and
the read-back both land in the same wrong cell — so every digit row would have
stayed green and the knife would have reddened nothing
([[knife-that-reddens-nothing-is-the-finding]]). The `A=3` line was added to all
three digit rows **before** the baseline was frozen, precisely so the carve in
§4.3 has a cut behind it instead of only a register reading.

⚠️ **The 12 `t.*` rows have no cut, and that is named rather than left implied.**
Their subject is the tokeniser, which this slice does not touch; a cut that moved
them would be measuring `basic_probe_crunch.py`'s gate. They are here to answer
*which file*, and they answered it before the design was written.

---

## 9. Denominator

**(WHERE the space falls inside a reference: before the 2nd LETTER, before a
DIGIT, before each of the four type suffixes `% ! # $`, MORE THAN ONCE, and
between two names run together) × (the POSITION the reference stands in: r-value
expression, LET target, `IF` condition, `FOR`, `NEXT`, `DIM`, an array element
lvalue, `READ`, `SWAP` — of which only `NEXT` and `READ` reach `tgt_parse` at
all)**, plus whether the space **survives the crunch** in each of those positions
(read from the stored line bytes, which is what says whether the fix belongs in
the tokeniser or the parser), plus what the **two-character key** does with a
space in the middle, plus the **keyword constraint** in both directions (a
contiguous name that becomes a token, and a spaced one that does not) with its
runtime negative control, plus the converse row that says the joined name is a
DIFFERENT variable, plus the TRAILING-space set that is green before and must
stay green, plus the one construct the rule **takes away** (`FIELD #n,<var> AS`).
Every spaced row carries the CONTIGUOUS form of its own fixture as its positive
control.

**Not covered, and named rather than implied:** a TAB or any other whitespace
byte; DIRECT mode (`TODO.md`'s `dir-name` residual, whose program-mode twin
`a.dig` *is* here); a space inside a `DEF FN` name or inside a line-number list;
`RSET` and the rest of the `FIELD` family (D-TGTSPC's nine lvalue surfaces share
one parse site and already carry the `(` position); and `OPEN A$ AS #1`, measured
in passing as a divergence with a different cause and filed separately.

---

## 10. As-built

Implemented 2026-08-08 on `main`, based on `36a107e`.

### 10.1 What landed

| file | change |
|---|---|
| [`basic/vars.asm`](../basic/vars.asm) | `is_ident_cont` gains `call skip_spaces` and becomes a **cursor scan**; the `ld a,(hl)` at each of its three callers is deleted; `vnk_dig2` (a dead reload) is deleted and its `jr` re-pointed at `vnk_set2` |
| [`probes/basic/basic_probe_namspc.py`](../probes/basic/basic_probe_namspc.py) | **new**, 58 rows, 18 positive + 2 negative controls, 2 deferred, two reading modes (`[...]` after `RUN`, and the STORED LINE BYTES for `t.*`) |
| [`probes/basic/basic_probe_tgtspc.py`](../probes/basic/basic_probe_tgtspc.py) | `x.dollar` and `x.name` leave `DEFERRED`; that dict is now **empty** |
| [`Makefile`](../Makefile) | `namspc-characterize` + `namspc-acceptance`, both `.PHONY` |

### 10.2 The walls — **and §6.3's bound was EXACT**

| wall | at `36a107e` | §6.4 predicted | as built | |
|---|---|---|---|---|
| **main page 1** | 3 B | 6 B (−3) | **6 B** | ✅ |
| main low / sub p0 / sub p1 / RAM | 11 / 3604 / 1483 | unchanged | **11 / 3604 / 1483** | ✅ |

The hand counter was **8/8 exact** against the `.sym` before the price was
quoted, and §6.2's claim that the layout hazard which cost D-NXARY 2 B is
structurally absent — no label ADDED, no new branch, no assumed fallthrough —
held; the one label this slice *deletes* took its `jr` with it.

🎯 **THE SLICE FUNDS THE BINDING WALL RATHER THAN SPENDING IT.** The residual was
filed *"not scouted and not priced, and page 1 is at 3 B"*, expecting a carve to
be most of the work. The rule itself costs **zero** — all three read points were
already loading the byte the callee now loads — and the `vnk_dig2` carve gives
**3 B back**.

### 10.3 The ROM hashes — all four predicted

| ROM | at `36a107e` | predicted | as built |
|---|---|---|---|
| `basic-reloc.rom` | `38022d44…` | MOVES | **`f04e402d…`** ✅ |
| `sub.rom` | `accce5a1…` | **HOLDS** | **`accce5a1…`** ✅ |
| `disk.rom` | `2c630d3d…` | **HOLDS** | **`2c630d3d…`** ✅ |
| `zerobas-main-eu.rom` | `d6d36c7e…` | MOVES | **`c66ab7e0…`** ✅ |

### 10.4 The gates

| gate | before | predicted | measured |
|---|---|---|---|
| **`namspc-acceptance`** | 29/55 | 55/55 | **56/56, 2 deferred** ✅ (58 cases — §10.5(b)) |
| **`tgtspc-acceptance`** | 26/26 + 2 deferred | 28/28 | **28/28, 0 deferred** ✅ |
| `nxary` / `nxlist` / `forvar` / `readvar` / `arylv` / `inputary` | 22 / 25 / 33 / 24 / 18 / 7 | unchanged | **all rc 0** ✅ |
| `lvfix` / `fldary` / `lrvar` | 18 / 13 / 21 | unchanged | **18/18 · 13/13 · 21/21** ✅ |
| `audit-citations` swept / basic | 760 / 199 | 761 / 200 | **763 / 200** — swept ❌, basic ✅ (§10.7) |
| `injector-check` | 346 | 347 | **347** ✅ |
| `rowshape-check` | 16 | 17 probes | **17** ✅ |
| closures | 122+4 / 733+15 / 585+43 | unchanged | **unchanged** ✅ |
| `unit-test` · `preflight` · `latch` · `deadcode` | 59 · 181/86/95/95/0 · 16/16 · 0/0 | unchanged | **unchanged** ✅ |

### 10.5 🔴 Three things went differently

**(a) THE RESIDUAL EXPECTED A CARVE AND THE RULE TURNED OUT TO BE FREE.**
`TODO.md` filed it *"NOT SCOUTED AND NOT PRICED, and page 1 is at 3 B — carve
before assuming a budget"*, and the brief expected the carve to be most of the
work. It is not, and the reason is structural rather than lucky: **all three
name-scan read points already did `ld a,(hl)` immediately before calling
`is_ident_cont`**, so moving the load into the callee pays for the space skip
exactly, three deletions for one insertion. A cost estimate that had priced this
as *"three `call skip_spaces` insertions, +6 B"* — the obvious shape — would have
declined a slice that in fact **gives the wall 3 B back**. What made the
difference was walking the callers before pricing, not after.

**(b) 🔴 THE ROW SET GREW AFTER THE KNIVES WERE DRAFTED, AND EVERY PREDICTION
WRITTEN AGAINST IT DIED WITH IT.** §3.3 predicted `z.fldvar` would go GREEN on
`Type mismatch`, derived by tracing the mechanism. It came back **`Syntax
error`** — 54/55, one row short. The trace was right about the SCAN and wrong
about what happens downstream, and separating those needed rows that did not
exist: `z.fldstr` (`FIELD#1,B$ AS A$(1)`, **no space anywhere**) reads `OK` here
against `Type mismatch` on the CF-3300, so **`ex_field` never type-checks its
width** — a shipped defect this slice only made visible; and `z.join` /
`z.joinnum` take FIELD out of the picture entirely and agree on all three sides,
which is what proves the join itself is exact. Two rows deferred, two added, and
§8's whole prediction table recomputed before the battery ran.
🎯 **The prediction was wrong in the direction that produced a finding.** Had
`z.fldvar` simply gone green as predicted, the `ex_field` defect would have
stayed invisible behind it.

**(c) 🔴 THE `<NO OUTPUT>` SENTINEL WAS RECORDING A HANG AS A SILENCE.** Five
rows (`r.dig` `r.dollar` `r.pct` `r.bang` `r.hash`) read `<NO OUTPUT>` in the
first draft. They are the opposite: `PRINT A 1` / `PRINT AB %` / `!` / `#` / `$`
fill a SCREEN 0 page with ` 0 ` **forever**, and `RUN` had scrolled off the top
so `screen_tail()` returned `None`. A reader that maps "I could not find my
anchor" onto "nothing was printed" understates a runaway by a whole category
([[readout-blind-to-its-own-subject]]). Renamed `<RUN SCROLLED OFF>` and
documented at the function.

### 10.6 Knives — 5 cuts × 2 rounds, **3 EXACT, both rounds identical**

| # | cut | predicted RED | measured | |
|---|---|---|---|---|
| **K-NS1** | `is_ident_cont`: `call skip_spaces` → `ld a,(hl)` + 2 × `nop` | 🎯 the 28 rows the rule moves | **exactly those 28** | ✅ ×2 |
| **K-NS2** | `jr nc,vnk_set2` → `jr nc,vnk_more` | 🎯 **`r.digctl` `r.dig` `a.dig` ONLY** | **exactly those 3** | ✅ ×2 |
| **K-NS3** | `vst_suffix`: `cp '$'` → `cp '@'` | 8 string rows incl. `z.join` | **8 rows: `z.fldvar` instead of `z.join`** | ❌ ×2 |
| **K-NS4** | `vnk_more`: `jr vnk_more` → `jr vnk_suffix` | `r.run` `z.join` `z.joinnum` | **`r.run` `z.joinnum` only** | ❌ ×2 |
| **K-NS5** | `CONTROL_WANT["c.let"]` unmatchable, `--sides vg8020,zb` | rc 2, ROMs unmoved | **rc 2 + `NOT MEASURED` banner, ROMs held** | ✅ ×2 |

🎯 **K-NS2 IS THE KNIFE FOR THE §4.3 CARVE, AND DRAFTING IT FOUND A MISSING
ROW.** With `r.digctl` = `A1=7` / `PRINT A1`, the cut corrupts the key
**symmetrically** — store and read-back land in the same wrong cell — so every
digit row would have stayed green and the knife would have reddened nothing
([[knife-that-reddens-nothing-is-the-finding]]). The `A=3` line was added to all
three digit rows *before* the baseline was frozen. The carve now rests on a cut
rather than on a register reading.

🔴 **BOTH MISSES ARE THE SAME ROW AND THE SAME MISTAKE: I TRACED `z.join`
THROUGH `var_name_key` WHEN IT IS DECIDED BY `var_str_type`.** `X=N AS A$(1)`
answers `Type mismatch` because `var_str_type` walks the whole joined name and
returns STRING *before* `var_name_key` runs at all. So K-NS4, which cuts only
`var_name_key`'s 3rd+ loop, cannot reach it; and K-NS3, which cuts only
`var_str_type`'s `$` test, cannot reach it either — because `vnk_suffix` has its
**own, independent** `cp '$'`, so the resolved type is still string and the
`Type mismatch` still fires. 🎯 **The `$` is tested in two places, and no single
byte-neutral cut separates them.** That is a fact about the code the battery
established and the source reading did not.

### 10.7 Corpus

Sequentially from clean (`rm -rf build` + `make repack-machine`, **bash** —
`zsh` does not word-split `make $t`), **32 targets, all rc=0, 19 min 12 s wall**
(276 s + 876 s; the run was split across two invocations because the shell
harness caps a single foreground command at 10 min — same build, no rebuild
between them): the 31 of [`spec-basic-tgtspc.md`](spec-basic-tgtspc.md) §10.7 —
`unit-test` **59** · `audit-citations` CLEAN (**763** swept, basic **200**) ·
`preflight-check` **181/86/95/95/0** · `injector-check` **347** ·
`rowshape-check` **17** probes · `latch-check` **16/16** · `deadcode`
**0/0 (+1)** · `lnblank-acceptance REPEAT=2` · `lnblank-say-acceptance`
**204/204** · `logicops-acceptance` · `float-acceptance` ·
`linemax-acceptance` **60/60** · `dexp5-pin` · `editverb-acceptance` **61/61** ·
`lptverb-acceptance` **44/44** · `dskmsg-acceptance` **5/5** ·
`diskbasic-acceptance` **34/34** verbs · `fat-error-acceptance` ·
`runtail-acceptance` **9/9** · `castail-acceptance` · `cassave-acceptance`
**20/20** · `readvar-acceptance` **24/24** · `arylv-acceptance` **18/18** ·
`inputary-acceptance` **7/7** · `lvfix-acceptance` **18/18** ·
`fldary-acceptance` **13/13** · `lrvar-acceptance` **21/21** ·
`forvar-acceptance` **33/33** · `nxlist-acceptance` **25/25** ·
`nxary-acceptance` **22/22** · **`tgtspc-acceptance` 28/28** — **plus
`namspc-acceptance` 56/56**.

⚠️ `latch-check` still has **no `repack-machine` prerequisite**, so the script
builds explicitly before the loop; and `lnblank-acceptance` **defaults to
`REPEAT=1`**, so the `REPEAT=2` is passed by hand
([[pin-fired-inside-its-own-slice]]).

⚠️ `audit-citations` swept **763**, not the 761 §7 predicted: the prediction
counted the probe file and forgot that this slice writes **two documents**, and
the listing/hex-dump sweep counts every file in the tree. The per-language
`basic` count is **200** exactly as predicted, because `provenance_files("basic")`
globs `basic/`+`sub/`+`probes/basic/*.py` and not `docs/`
([[a-count-is-predicted-by-reading-its-definition]] — the definition was read for
one of the two counters and assumed for the other).

Copy *this* list forward, not the last one — the gate a slice ADDS is exactly the
one a runner rebuilt from the previous slice omits.

### 10.8 The fix, as a program

Every cell below is a LITERAL screen row read after `RUN` — the "before" column
from a rebuilt pre-fix ROM (`basic-reloc.rom 38022d44…`, hash checked), not from
the battery's error-name reading.

```basic
10 FOR AB=1 TO 2
20 NEXT A B
30 PRINT "OK"
```

| | screen after `RUN` |
|---|---|
| VG-8020 / CF-3300 | `OK` |
| zerobas **before** → **after** | `NEXT without FOR in 20` → **`OK`** |

…and the row that says it is not an lvalue rule — `PRINT` never touches
`tgt_parse`:

```basic
10 AB=7
20 PRINT A B
```

| | screen after `RUN` |
|---|---|
| VG-8020 / zerobas **after** | `7` — ONE value, the variable `AB` |
| zerobas **before** | `0  0` — two variables, `A` and `B` |

…and a type suffix behind a space, which was not an error but a **hang**:

```basic
10 AB%=7
20 PRINT AB %
```

| | screen after `RUN` |
|---|---|
| VG-8020 / zerobas **after** | `7` |
| zerobas **before** | the screen fills with ` 0 ` and never stops — `RUN` scrolls off the top |

🎯 **The third program is why §10.5(c) matters.** Read through a sentinel called
`<NO OUTPUT>`, a program that never stops looks exactly like a program that
printed nothing.
