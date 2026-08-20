# D-FLDWIDTH — a `FIELD` width is a BYTE ARGUMENT

*Subject: the residual D-NAMSPC filed and DEFERRED in `TODO.md` — `ex_field`
never type-checks its field width, and the row that says so has no space in it.*

Based on `f0b688d` (D-NAMSPC). Measurement:
[`fldwidth-msx1-characterization.md`](fldwidth-msx1-characterization.md),
`make fldwidth-characterize`, `probes/basic/basic_probe_fldwidth.py`.

---

## 1. The rule — measured before it was designed

The residual arrived with **two rows** and one clause: *"a STRING is accepted as
a field width"*. Two rows are not a rule, and `ex_field` runs **two** `call
eval`s, a `var_str_type` check and the whole `AS` item parse **in a loop** — so
the denominator was built first, over four axes (type × domain × surface ×
order).

**42 rows, CF-3300 + zerobas, 24 agreeing at `f0b688d`.** The full table is in
the characterization; the rule it states:

> A `FIELD` width is a **BYTE ARGUMENT**, and it is the ordinary two-stage one
> this tree already implements for every other numeric argument: a **STRING is
> `Type mismatch`**, a deferred arithmetic fault is **`Division by zero`**, the
> value coerces to int16 (**`Overflow`** beyond it) and must lie in **0..255**
> (**`Illegal function call`** outside; **0 is inside**), a fraction
> **TRUNCATES**. It is then checked against the channel's record length as a
> **RUNNING TOTAL** (**`FIELD overflow`**). Every check is **PER ITEM**, in list
> order, and **does not roll back** the items already placed. The CHANNEL is
> checked before all of it; the WIDTH before the TARGET's type.

Four readings decide bytes, and no earlier row asked any of them:

* 🎯 **`d.big` vs `d.neg`/`d.256`/`d.257` — TWO DIFFERENT ERRORS, AND THAT IS
  WHAT MAKES THE FIX A CALL RATHER THAN A BOUND.** 70000 → `Overflow` (ERR 6),
  −1/256/257 → `Illegal function call` (ERR 5), 0 → accepted. That is
  **exactly** `get_byte_arg`'s two stages (`basic/interp.asm:1715` —
  `get_int16_checked`, then `ld a,d / or a / jr nz,gb_illegal`), the routine
  `CHR$`, `STRING$`, `SPACE$`, `ON n` and `WIDTH n` already share. Had the
  reference answered one error for all four, the fix would have been a
  hand-rolled comparison; it did not, so **the whole domain rule is 3 bytes of
  `call`**.
* 🎯 **`d.zero` — 0 IS LEGAL, AND `basic/field.asm`'s OWN HEADER SAYS IT IS
  NOT.** That header reads *"field widths are 1..255"*. The CF-3300 accepts
  `FIELD#1,0 AS A$` and reports `LEN(A$)` = 0. A design built on the source
  comment would have shipped a divergence the comment invented — the same shape
  as [[a-source-comment-about-the-emulator-is-a-claim]]. The header is corrected
  by this slice.
* 🎯 **`m.trap` — PER ITEM, NO ROLLBACK, SO THE CHECK GOES INSIDE THE LOOP.**
  Trapped, `FIELD#1,5 AS A$,N$ AS B$` reads **` 13  5 `** on the reference: ERR
  13, and `A$` is still 5 bytes wide. No entry-time validation pass, no undo.
* 🎯 **`o.dt` — THE WIDTH IS CHECKED BEFORE THE TARGET.** `FIELD#1,-1 AS A` has
  two faults and answers `Illegal function call`, not `Type mismatch`.
  ⚠️ `o.wt` **cannot** say this (both faults are ERR 13); it was the natural
  first draft of the ordering row and it would have agreed either way
  ([[one-row-cannot-separate-two-rules]]).

And one row set is the **CONSTRAINT** rather than the rule — see §3.2.

---

## 2. What is wrong, in one sentence

`ex_field`'s width `call eval` (`basic/field.asm:282`) is followed by nothing at
all — no type check, no coercion, no domain test — so its `pop de` takes
whatever `eval` left in `E`, which is `type_mismatch_set`'s hard **0** for a
string and the **low byte** of anything out of range; and its target
`var_str_type` miss answers `exf_syn` (ERR 2) where the same test in the same
file answers ERR 13.

---

## 3. Scope

### 3.1 The site walk, done rather than restated

`ex_field` has **four** `eval`/check surfaces, and the walk says which are in:

| # | surface | `field.asm` | in scope? |
|---|---|---|---|
| 1 | the CHANNEL's `call eval` at `exf_havech` | :246 | **NO** — `ch.str` and `o.chan` are already green on both sides |
| 2 | the WIDTH's `call eval` at `exf_item` | :270 | **YES** — the subject |
| 3 | the TARGET's `var_str_type` miss | :286 | **YES** — `t.num`, 0 B (§4.3) |
| 4 | the running total in `fld_add` | :310 | **NO** — priced and DECLINED, §6.5 |

⚠️ Surface 1 is **not** left alone on faith: `ch.str` (`FIELD#N$,10 AS A$`)
reads `Type mismatch` on **both** sides and `o.chan` (`FIELD#2,N$ AS A$`) reads
`Bad file number` on both, so the channel already type-checks and already runs
first. Measured, not assumed.

⚠️ `LSET`/`RSET` share `tgt_parse_fld` with `ex_field`, and the brief asked
whether they inherit this. **They cannot: they have no width expression.** The
shared routine is the TARGET parse, and this slice does not touch it — surface 3
changes only the `jp` that `ex_field` takes when `var_str_type` has *already*
returned. `t.numctl` (`LSET A=2` → `Type mismatch`) is green before and after
and is this group's control.

### 3.2 🔴 THE CONSTRAINT — three of the four `exf_syn` arms must NOT become ERR 13

`ex_field` answers **four** different faults with the same `jp ..,exf_syn`:
the `AS` first letter, the `AS` second letter, a target that is not a letter,
and a target whose resolved type is not a string. **Only the last becomes ERR
13.** Two negative controls pin the other side:

| row | program | both sides, before **and** after |
|---|---|---|
| `t.noas` | `FIELD#1,10 A$` — no `AS` | `Syntax error` |
| `t.nonm` | `FIELD#1,10 AS 5` — target is not a NAME | `Syntax error` |

Without `t.nonm` the fix would be indistinguishable from *"answer ERR 13 to any
target `ex_field` dislikes"*, which is a wider rule than the evidence supports
([[a-rule-can-claim-more-than-its-evidence]]).

### 3.3 🔴 WHAT THE CARVE RESTS ON — `exf_item`'s `call skip_spaces` is DEAD

```
exf_item:
                call    skip_spaces         ; <- 3 B, dead
                call    eval                ; DE = field width
```

`eval` → `ev_logic` → … → `ev_f` (`basic/expr.asm:460`), whose **first
instruction is `call ev_sp`** — the identical `$20`-skipping loop. The
neighbouring `exf_havech` already proves the pattern from the other side: it
does `call eval` with **no** preceding skip and `FIELD # 1,…` works.

So the deletion is value-for-value, and it is **not** an unmeasured tidy-up:
`c.wsp` (`FIELD#1, 10 AS A$`) and `c.wsp2` (`FIELD#1,5 AS A$, 7 AS B$` — the
second item, reached by the `jr` from `exf_comma`) are **green before the fix**
and must stay green, and **K-FW4 is the knife that proves they can see it**
(§8). D-NAMSPC's §4.3 carve landed on exactly this rule: a carve with no row
behind it is a register reading, not a measurement.

### 3.4 The boundary — what this slice does NOT touch

* **`FIELD overflow` (ERR 50) against the record length.** `d.sum`/`d.sum1`
  measured, priced at ≈27 B against a 6 B wall, DECLINED WITH NUMBERS (§6.5),
  DEFERRED in the probe and filed in `TODO.md`.
* **`ex_width`'s identical inline sequence.** `basic/screen.asm:160` is `call
  eval / ld a,(TMISMATCH) / or a / jp nz,type_mismatch_error / call
  get_byte_arg` — 13 B that a shared `eval_byte_checked` helper would collapse
  to 3, funding this slice **and** returning ~10 B (§6.4). It is declined
  deliberately: `check_expr_errors` also raises on **FPERR**, so folding
  `ex_width` in would change `WIDTH 1/0`'s answer, and that reading has not been
  taken. A byte saving is not a licence to move another verb's error face
  ([[a-priced-decline-is-a-claim-about-a-design]]).
* **Message WORDING** (D-MSGEXACT's surface — the probe matches error names
  case-insensitively and says so).

---

## 4. Design

### 4.1 🎯 THE WIDTH BECOMES A BYTE ARGUMENT — two calls, and both routines already ship

`basic/field.asm`, `exf_item`:

```
exf_item:
                call    skip_spaces         ; deleted -- §3.3, ev_f does it
                call    eval                ; DE = field width; HL advanced
                call    check_expr_errors   ; + 3 B  -- TMISMATCH / FPERR
                call    get_byte_arg        ; + 3 B  -- ERR 6 / ERR 5 / 0..255
                push    de                  ; DE = D0,E=width
```

* `check_expr_errors` (`basic/interp.asm:1298`) is the statement-boundary check
  `ex_if`, `exp_num` and `eval_chan` already use: `TMISMATCH` → ERR 13,
  `FPERR` → `fp_runtime_error` (which maps FPERR 2 → **ERR 11, Division by
  zero** via `fperr_to_err`). One 3-byte call answers `s.*` **and** `d.div`.
* `get_byte_arg` (`basic/interp.asm:1725`) is the two-stage rule §1 measured:
  `get_int16_checked` (ERR 6 past int16) then `ld a,d / or a / jr nz,gb_illegal`
  (ERR 5 outside 0..255, 0 accepted). It returns `D=0, E=byte` — which is
  precisely what the existing `pop de` / `fld_add` pair wants, and what the
  current comment already *claims* (`"E = width, D = 0 for w<=255"`) without
  anything enforcing it.

**ORDER IS FORCED, NOT CHOSEN.** `check_expr_errors` must precede
`get_byte_arg`: on a `TMISMATCH` state `type_mismatch_set` has hard-zeroed `DE`
and left `FAC` untouched, so coercing first would fault (or succeed) on a value
that means nothing. `eval_chan` (`basic/float-arith.asm:1287`) documents the
identical constraint at the identical join, and D-BADFNUM measured it.

### 4.2 Register contract — checked, not assumed

At the insertion point `HL` is the text cursor and must survive.
`check_expr_errors` reads two RAM bytes and `ret`s — `HL` untouched; on its
abort arms it never returns. `get_byte_arg` → `get_int16_checked`, which is
`push hl / call fac_to_int_strict / pop hl` — `HL` preserved by construction, and
its own header says "DE preserved (D=0, E=byte) … Clobbers A". `BC` is not live
here (the key is built later, by `tgt_parse_fld`). Nothing is on the stack at
`exf_item`: the `push de` is *after* the width is final, and the second item
re-enters through `exf_comma`'s `jr` at the same clean depth — so
`check_expr_errors` is the right entry point and `check_expr_errors_popbc` is
not.

### 4.3 The target's type — ERR 13, and it is BYTE-NEUTRAL

```
                call    var_str_type        ; A=1 if `$` suffix
                or      a
                jp      z,exf_syn           ; -> jp z,type_mismatch_error
```

Same `jp cc,nn`, 3 B for 3 B. This is D-LRVAR's move, one statement over:
`lrset_common` in this same file already does `jp z,type_mismatch_error` for the
identical test, measured against the CF-3300, and `t.numctl` is that row.

⚠️ **`exf_syn`'s `pop de` is NOT lost by this.** The other three arms keep it,
and it is in any case a no-op for correctness: `stmt_error` → `raise_error`
resets `SP` from `SAVSTK` on **both** its arms (`ld sp,(SAVSTK)` at
`raise_error_hl`'s trap branch and at `fre_abort_low`), which is what
`exf_raise`'s own shipped comment three lines below already states.

### 4.4 RAM

None. No new variable, no new stack word, no new label, no label deleted.

---

## 5. Forced constraints

### 5.1 The check must be INSIDE the item loop — `m.trap` is the row that says so

`m.trap` reads ` 13  5 `: the error fires at the **second** item and the first
one stays placed. A once-at-entry validation would need to look ahead over a
comma list it has not parsed, and a rollback would have to un-place `A$`. Both
are refuted by one row.

### 5.2 It must run BEFORE the `AS` scan, not after

`s.join` (`FIELD#1,N AS A$(1)`) is the row: D-NAMSPC's name scan swallows the
`AS` into the reference `NA$(1)`, so by the time the parse looks for a literal
`'A'` the cursor is past it and the answer is `Syntax error`. The reference
refuses the **width** first, which is why its answer is `Type mismatch`. A check
placed after the `AS` match would never see this row at all.

### 5.3 `t.noas` and `t.nonm` must STAY `Syntax error`

§3.2. Three of the four `exf_syn` arms are untouched, and the two rows are in
the battery so a future "improvement" that generalises the ERR 13 has something
in its way ([[gate-whose-answer-is-an-error-passes-a-dead-subject]]).

### 5.4 `d.frac` must stay ` 10 ` — the coercion CHANGES, and this is the row that catches it

Today a float width reaches `DE` through `ev_f_float`'s `flt_to_int16`
(`CVT_MODE=1`); after the fix it goes through `get_byte_arg`'s
`fac_to_int_strict` (`CVT_MODE=0`). Those are **two entry points into one body**
(`domain_convert_core`, `basic/float-arith.asm:1152`) and `CVT_MODE` selects
only the `dexp==5` bound (32767 strict vs 65535 wrapping) — truncation is
`dig_to_word` in both. So 10.7 truncates to 10 either way, **and 70000
(`dexp==5`, positive) is exactly where the two modes differ**: strict bounds at
32767 and raises `Overflow`, which is the reference's answer. `d.frac` is green
before and after; `d.big` moves *because* of the mode.

### 5.5 Region

`ex_field` is at `$7263`, `check_expr_errors` at `$43B2`, `get_byte_arg` at
`$44FD`, `type_mismatch_error` at `$426A` — **all main page 1**. No region hop,
no new escape class for any tenant closure.

---

## 6. The carve scout

Off `build/basic-reloc.sym` from a clean build at `f0b688d` (`rm -rf build &&
make basic-reloc`): low **11 B**, page 1 **6 B**, sub p0 **3604 B**, sub p1
**1483 B**; `basic-reloc.rom f04e402d…`, `sub.rom accce5a1…`, `disk.rom
2c630d3d…`, `zerobas-main-eu.rom c66ab7e0…`.

### 6.1 Region — asked before anything is priced

| symbol | address | region |
|---|---|---|
| `ex_field` … `fld_add` | `$7263`–`$72E9` | **page 1** — where every byte lands |
| `check_expr_errors` | `$43B2` | page 1 — reused, unchanged |
| `get_byte_arg` | `$44FD` | page 1 — reused, unchanged |
| `type_mismatch_error` | `$426A` | page 1 — reused, unchanged |
| `skip_spaces` | `$4255` | page 1 — one caller fewer |
| `tgt_parse_fld` | `$7247` | page 1 — **unchanged**, §3.1 |

`carve_scout.py build/basic-reloc.sym --files basic/field.asm`: 46 labels, all
46 in page 1, **568 B leaves page 1** if the file moves. No eviction is
proposed — recorded because the scout was run **before** the price, not after.

### 6.2 The estimator, calibrated before it is used

Hand-counted from source and checked against the `.sym` **first**
([[calibrate-a-hand-counter-before-quoting-it]]):

| span | counted | `.sym` Δ | |
|---|---|---|---|
| `ex_field` → `exf_havech` | 1+3+2+2+1 = **9** | `$726C−$7263` = **9** | ✅ |
| `exf_havech` → `exf_item` | 3+3+1+3+1+3+1+2+2+2+1+3+3+1+1+3+3+3+2+3+1 = **45** | `$7299−$726C` = **45** | ✅ |
| `exf_item` → `exf_comma` | 3+3+1+3+3+2+3+1+1+3+2+3+1+3+3+3+3+1+3+3+1+1+3+1+3+2+2+3 = **64** | `$72D9−$7299` = **64** | ✅ |
| `exf_comma` → `exf_syn` | 1+2 = **3** | `$72DC−$72D9` = **3** | ✅ |
| `exf_syn` → `exf_dev` | 1+3 = **4** | `$72E0−$72DC` = **4** | ✅ |
| `exf_dev` → `exf_bfm` | 2+2 = **4** | `$72E4−$72E0` = **4** | ✅ |
| `exf_bfm` → `exf_raise` | **2** | `$72E6−$72E4` = **2** | ✅ |
| `exf_raise` → `fld_add` | **3** | `$72E9−$72E6` = **3** | ✅ |

**8/8 exact.**

⚠️ **AND THE LAYOUT HAZARD IS NAMED RATHER THAN HOPED AWAY.** D-NXARY was 2 B
light because its arithmetic assumed a fallthrough a label forbids
([[knife-prediction-inherits-the-drafts-layout-error]]). This slice adds **no
label, deletes no label, and adds no branch**: two `call`s in, one `call` out,
one `jp` operand changed. The only arithmetic risk is a `jr` going out of range,
and the net movement inside `ex_field` is **+3 B**, all of it *below* `exf_item`
— so `exf_comma`'s `jr exf_item` (backwards, 64→67 B) and `exf_item`'s
`jr z,exf_comma` (forwards, unchanged) both stay inside −128..127 by a factor
of nearly two.

### 6.3 The cost — a BOUND, with the twin named for every part

| body | region | before | after | Δ |
|---|---|---|---|---|
| `exf_item` — `call check_expr_errors` inserted (§4.1) | p1 | | | **+3** |
| `exf_item` — `call get_byte_arg` inserted (§4.1) | p1 | | | **+3** |
| `exf_item` — `call skip_spaces` deleted (§3.3 carve, dead: `ev_f` opens with `call ev_sp`) | p1 | | | **−3** |
| `exf_item` total | p1 | 64 | **67** | **+3** |
| target `jp z,exf_syn` → `jp z,type_mismatch_error` (§4.3) | p1 | 3 | **3** | **0** |
| every other body / `tgt_parse_fld` / low / sub p0 / sub p1 / RAM | — | | | **0** |
| **main page-1 total** | | | | **+3** |

### 6.4 The bottom line

| region | free at `f0b688d` | slice | free after |
|---|---|---|---|
| **main page 1** | **6 B** | **+3** | **3 B** |
| main low | 11 B | 0 | **11 B** |
| sub page 0 / page 1 | 3604 / 1483 | 0 | **unchanged** |

🎯 **THE OBVIOUS PRICE WAS +6 AND THE REAL ONE IS +3, BECAUSE THE SITE WAS
WALKED BEFORE IT WAS PRICED.** Two inserted calls, one deleted — the deleted one
being a `skip_spaces` that `eval`'s own first instruction has been redoing since
`ev_f` was written. Page 1 goes **6 → 3 B**, exactly where D-TGTSPC left it, and
the next slice must carve-scout before assuming a budget
([[which-wall-binds-is-a-history-question]]).

⚠️ **A −10 B FUNDING CARVE EXISTS AND IS DECLINED.** `ex_width`
(`basic/screen.asm:160`) is the same sequence written out inline — 13 B that a
shared `eval_byte_checked` (`call eval / call check_expr_errors / jp
get_byte_arg`, 9 B) would collapse to 3, netting **−1 B here and −10 B there**.
It is declined because `check_expr_errors` raises on **FPERR** as well, so it
would change `WIDTH 1/0`'s answer on a reading nobody has taken. Recorded with
its number so the next slice can take that reading and claim the bytes.

### 6.5 💰 `FIELD overflow` (ERR 50) — DECLINED WITH NUMBERS

`d.sum1` (200+57 into a 256-byte record) is `FIELD overflow` on the CF-3300 and
` 200  57 ` here; `d.sumok` (200+56) is accepted on both. Real, measured, and
**not affordable**:

| part | bytes |
|---|---|
| `ld a,(FLD_CHAN)` / `add a,a` / `ld e,a` / `ld d,0` / `ld hl,FCH_RECLENS` / `add hl,de` / `ld e,(hl)` / `inc hl` / `ld d,(hl)` | 3+1+1+2+3+1+1+1+1 = **14** |
| `ld hl,(FLD_CUROFF)` / `or a` / `sbc hl,de` / `jr c,…` / `jr z,…` | 3+1+2+2+2 = **10** |
| `ld a,50` / `jr exf_raise` | 2+2 = **4** |
| **total, main page 1** | **≈27 B** |

against a **6 B** wall of which this slice already spends 3. There is no
main-side accessor to borrow: `load_reclen` (`basic/randio-body.inc:270`) is
**sub-ROM** (`sub/randio.asm:47`) and `GP_RECLEN` is only loaded at GET/PUT
time, so reading it here would read a stale cell.

🔴 **AND ITS DENOMINATOR IS NOT BUILT.** Every row in this battery uses the
**default** 256-byte record, so nothing measured separates *"checked against the
record length"* from *"checked against a constant 256"*. That needs
`OPEN … LEN=r` rows — the disk-BASIC option surface, not this one. Deferred in
the probe, filed in `TODO.md` with these three readings as its starting point.

---

✅ **ADDENDUM 2026-08-19 (D-RECLEN) — THE DENOMINATOR IS NOW BUILT, AND THE RULE
IS THE RECORD LENGTH.** Everything above stands as written for its date; only its
status changes. Five `r.*` rows were added to this battery, opening a
**non-default** record so that the two candidate rules disagree:

| row | record | field(s) | CF-3300 | zerobas |
|---|---|---|---|---|
| `r.ok` 🟢 | 64 | 64 | ` 64 ` | ` 64 ` |
| `r.over` | 64 | 65 | **FIELD overflow** | ` 65 ` |
| `r.mid` | 64 | 200 | **FIELD overflow** | ` 200 ` |
| `r.sum128` | 128 | 100 + 50 | **FIELD overflow** | ` 100  50 ` |

🎯 **`r.mid` IS THE DECISIVE ONE: 200 IS UNDER 256.** A constant-256
implementation accepts it; the CF-3300 refuses it. The check is against
`FCH_RECLENS[ch]`, and the ≈27 B hand-count above — which already prices the
inline `FCH_RECLENS` read at 14 B — is a count of the *right* code. **The "no
main-side accessor" note was never a blocker in its own right**: the price
assumes no accessor and reads the table inline, exactly as
`oo_parse_reclen` writes it inline at [`basic/files.asm:283`](../basic/files.asm).

💰 **RE-PRICED: the wall is 50 B page 1** (D-LOADSWEEP, 2026-08-19) against the
same ≈27 B, so **the byte half and the measurement half are both now clear.**
See [`repricing-page1-2026-08-19.md`](repricing-page1-2026-08-19.md) §3.2, which
identified this as the only open item whose byte blocker the carve had lifted.

🔴 **AND THE ROW THAT MISSED FOUND A SECOND DIVERGENCE.** `r.sum` was drafted
with `LEN=100` and predicted ` 60  50 ` here; it read **`Syntax error`**, because
`oo_parse_reclen` restricts the record length to a **power of two** in 1..256.
Split into `r.len100` (the `LEN=` parse alone: CF-3300 `OK`, zerobas **`Syntax
error`**) and `r.sum128` (the running total on a record zerobas accepts). The
first is a separate defect and is filed; it is **not** part of the ERR-50 rule
and must not be folded into it.

### 6.6 ✅ VERDICT: **GO, +3 into 6.** No eviction, no RAM, no sub-ROM byte, no new label.

---

## 7. Predicted GREEN

`make fldwidth-characterize` must read, on both sides:

| rows | prediction | |
|---|---|---|
| the 9 `n.*` rows | ` 10 ` | 🟢 green before **and** after — the numeric family must not move |
| `c.wsp` `c.wsp2` | ` 10 ` / ` 5  7 ` | 🟢 green before **and** after — §3.3, the carve's own rows |
| `s.var` `s.lit` `s.ary` `s.fn` | **`Type mismatch`** | 🔴 from ` 0 ` — the SUBJECT, four roads |
| `s.join` | **`Type mismatch`** | 🔴 from `Syntax error` — D-NAMSPC's `z.fldvar`, §5.2 |
| `d.neg` `d.256` `d.257` | **`Illegal function call`** | 🔴 from ` 255 ` / ` 0 ` / ` 1 ` |
| `d.big` | **`Overflow`** | 🔴 from ` 0 ` — a DIFFERENT error, §5.4 |
| `d.div` | **`Division by zero`** | 🔴 from ` 0 ` — the FPERR arm of `check_expr_errors` |
| `d.zero` `d.frac` | ` 0 ` / ` 10 ` | 🟢 green before **and** after — 0 is legal, 10.7 truncates |
| `m.str2` | **`Type mismatch`** | 🔴 the second item |
| `m.trap` | **` 13  5 `** | 🔴 from `<NO OUTPUT>` — ERR 13 **and the first field survives** |
| `m.neg2` | **`Illegal function call`** | 🔴 the second item's domain |
| `t.num` | **`Type mismatch`** | 🔴 from `Syntax error` — §4.3, 0 B |
| `o.wt` | **`Type mismatch`** | 🔴 — the width check now fires first |
| `o.dt` | **`Illegal function call`** | 🔴 🎯 **the sharpest prediction here** — not ERR 13; the width is checked before the target |
| `t.noas` `t.nonm` | `Syntax error` | 🔴 **NEGATIVE controls** — green before **and** after, §3.2 |
| `ch.str` `ch.expr` `o.chan` | unchanged | 🟢 the channel surface is not touched |
| `d.sum` `d.sum1` | unchanged | ⏸ **DEFERRED** — §6.5, measured and printed, never scored |
| the 7 positive controls | unchanged | |

⇒ **`make fldwidth-acceptance` scores 40/40 with 2 deferred**, over 42 cases,
from **24/42** at `f0b688d`. **16 rows move.**

⚠️ **THE REGRESSION SURFACE IS EVERY `FIELD` STATEMENT IN THE CORPUS**, so
`fldary-acceptance` (13/13), `lrvar-acceptance` (21/21), `lvfix`, `lvsites` and
`diskbasic-acceptance` are the gates that matter — every one of them FIELDs at
widths 4, 6 and 10, all of which are inside the new domain and unaffected by the
new type check. `namspc-acceptance` is the other one: its two DEFERRED rows
(`z.fldvar` / `z.fldstr`) are this slice's subject and are **un-deferred** by it,
taking that gate 56/56 → **58/58** and emptying its `DEFERRED` dict
([[a-deferral-honoured-is-worth-more-than-one-filed]]).

Static counters, each predicted by reading its own check's definition
([[a-count-is-predicted-by-reading-its-definition]]) and **already measured with
the probe file present**: `audit-citations` swept 763 → **766** (⚠️ the sweep
counts DOCS: one probe **plus two documents**, which is the count D-NAMSPC's own
prediction got wrong by forgetting), basic provenance-bearing 200 → **201**;
`injector-check` 347 → **348**; `rowshape-check` 17 → **18** probes;
`preflight-check` **181/86/95/95/0 unchanged** (the probe adds no spawn site the
checker cannot already prove harmless — measured, not predicted);
`latch-check` **16/16 unchanged**; `deadcode` **0/0 (+1) unchanged** (the
deleted `call skip_spaces` orphans nothing — `skip_spaces` keeps dozens of
callers); closures **122+4 / 733+15 / 585+43 unchanged** (every routine the fix
calls is main page 1 and already inside every closure `ex_field` is in);
`unit-test` **59 unchanged** — ⚠️ and it *cannot* cover this, for the reason
`eval_byte_arg`'s own header gives: `get_byte_arg` aborts through `raise_error`,
which needs `SAVSTK`, which `tests/msxtest.py` never sets.

---

## 8. Knives — drafted before the row set was frozen

Read [`dev-workflow.md`](dev-workflow.md) §"Knives" first. Subject = the probe
invoked directly at `--sides cf3300,zb` (a REFERENCE plus zb — never a lone
`zb`; the diff is over zb's values and the reference is a constant), except
K-FW5. Every cut is byte-neutral. Every cut is run **twice**.

🔴 **THE PREDICTIONS ARE QUANTIFIED OVER ALL 42 ROWS THE PROBE PRINTS, NOT THE
40 THE GATE SCORES.** D-TGTSPC's K-TS4 missed for exactly that: a runner diffs
what the probe **prints**, and `probe_report.parse()` returns DEFERRED rows like
any other. `d.sum` and `d.sum1` are printed, are in **every** GREEN set below,
and are touched by no cut.

| # | cut (byte-neutral) | predicted RED | predicted GREEN |
|---|---|---|---|
| **K-FW1** | `exf_item`: `call check_expr_errors` → `call check_fperr_only` — the **same routine minus its `TMISMATCH` test** (`$43B8`, its documented fall-in entry point), i.e. the TYPE half reverted and the FPERR half kept | 🎯 the **7** string rows: `s.var` `s.lit` `s.ary` `s.fn` `s.join` `m.str2` `m.trap` | the other **35**, and in particular `d.div` (the FPERR half survives), `o.wt` and `o.dt` |
| **K-FW2** | `exf_item`: `call get_byte_arg` → `call get_int16_checked` (`$44DE`) — the **int16 stage only**, the 0..255 test dropped | 🎯 `d.neg` `d.256` `d.257` `m.neg2` `o.dt` (**5**) | the other **37**, and in particular **`d.big`** — `Overflow` comes from the stage this cut KEEPS |
| **K-FW3** | the target test: `jp z,type_mismatch_error` → `jp z,exf_syn` (the pre-slice operand) | 🎯 **`t.num` ONLY** (1) | the other **41**, `o.wt` and `o.dt` included — the width check now fires first |
| **K-FW4** | `ev_sp` (`basic/expr.asm:319`): `cp ' '` → `cp $00` — the loop the §3.3 carve rests on never skips | 🎯 `c.wsp` `c.wsp2` (**2**) | the other **40** — no other fixture here has a space before an expression |
| **K-FW5** | `CONTROL_WANT["c.lit"]` unmatchable (probe-only), `--sides cf3300,zb` | rc **2**, `NOT MEASURED` banner, ROMs **NOT** moved | — |

All four code red sets are **pairwise disjoint**, and they partition the fix by
part: K-FW1 the type check, K-FW2 the domain check, K-FW3 the target's error
class, K-FW4 the carve. **K-FW3 reddens exactly ONE row.** K-FW2 contains no
control, K-FW1 and K-FW4 each redden a row that is green in the shipped tree for
a *different* reason than the rest of their set (`m.trap`'s reading is a trapped
`ERR`; `c.wsp2`'s is the second item).

🎯 **K-FW1 AND K-FW2 ARE PARTIAL REVERTS, NOT NO-OPS, AND THAT IS WHY THEY ARE
SHARP.** Both cut sites swap one 3-byte `call` for another 3-byte `call` into a
routine that *already exists and does part of the job*:
`check_expr_errors`/`check_fperr_only` are literally one routine with two entry
points (`basic/interp.asm:1302`), and `get_byte_arg` is `get_int16_checked` plus
a two-instruction byte test. So each knife removes **exactly one clause** of §1's
rule and leaves the rest standing — which is what makes `d.div` surviving K-FW1
and `d.big` surviving K-FW2 predictions rather than hopes.

🎯 **K-FW1's GREEN SET IS THE INTERESTING HALF, AND IT WAS COMPUTED, NOT
ASSUMED.** With the `TMISMATCH` test gone, `fac_to_int_strict` returns
immediately (`FACTYP` is still **2**, the value `eval` set on entry and
`type_mismatch_set` never changes) with `DE` = `type_mismatch_set`'s hard **0** —
so a string width is accepted as **width 0**, exactly the pre-slice reading. That
is why `o.wt` (`FIELD#1,N$ AS A`) stays **GREEN** under this cut: the width sails
through as 0, the `AS` matches, and the *target* test — which K-FW1 does not
touch — raises the same ERR 13 the reference gives. A knife whose green set
contains the row you would naively expect to redden is worth more than one whose
sets are tidy.

⚠️ **The 7 positive controls have no cut, and that is named rather than left
implied.** Their subject is the working `FIELD` path, which this slice does not
touch; a cut that moved them would be measuring `basic_probe_fldary.py`'s gate.
They are here to say a red row is about the WIDTH and not about the fixture.

---

## 9. Denominator

See [`fldwidth-msx1-characterization.md`](fldwidth-msx1-characterization.md) §5.
In one line: **(what TYPE the width is: nine numeric spellings against four
string ones plus the `AS`-joined name) × (what DOMAIN: 0, negative, past the
byte, past int16, a deferred `1/0`, a fraction, and a running total one byte
either side of the record) × (which SURFACE: width, channel, target, second
item) × (which ERROR and in what ORDER, with two faults in one statement and two
different error codes so the order is observable)**, every group carrying the
working form of its own fixture as a positive control, two negative controls
bounding the ERR-13 change, and every accepting row reading the WIDTH BACK
rather than printing `OK`.

**Not covered, and named rather than implied:** `GET`/`PUT` record I-O through a
bad field; a `LEN=` record length other than the default (which is what §6.5's
residual needs); `FIELD` on a `CAS:` channel; `RSET` (it shares `lrset_common`
with `LSET` and is not a second site); and message WORDING.

---

## 10. As-built

Implemented 2026-08-08 on `main`, based on `f0b688d`.

### 10.1 What landed

| file | change |
|---|---|
| [`basic/field.asm`](../basic/field.asm) | `exf_item` gains `call check_expr_errors` + `call get_byte_arg` and **loses** its dead `call skip_spaces`; the target's `var_str_type` miss becomes `jp z,type_mismatch_error`; the file header's *"field widths are 1..255"* claim is **corrected to 0..255** and its FIELD-overflow line now carries the price |
| [`probes/basic/basic_probe_fldwidth.py`](../probes/basic/basic_probe_fldwidth.py) | **new**, 42 rows, 7 positive + 2 negative controls, 2 deferred |
| [`probes/basic/basic_probe_namspc.py`](../probes/basic/basic_probe_namspc.py) | `z.fldvar` and `z.fldstr` leave `DEFERRED`; that dict is now **empty** |
| [`Makefile`](../Makefile) | `fldwidth-characterize` + `fldwidth-acceptance`, both `.PHONY` |

### 10.2 The walls — **and §6.3's bound was EXACT**

| wall | at `f0b688d` | §6.4 predicted | as built | |
|---|---|---|---|---|
| **main page 1** | 6 B | 3 B (+3) | **3 B** | ✅ |
| main low / sub p0 / sub p1 / RAM | 11 / 3604 / 1483 | unchanged | **11 / 3604 / 1483** | ✅ |

The hand counter was **8/8 exact** against the `.sym` before the price was
quoted, and §6.2's layout claim held to the byte: `exf_item` → `exf_comma`
measured `$72DC−$7299` = **67 B**, exactly the predicted 64 + 3.

🎯 **THE OBVIOUS PRICE WAS +6 AND THE SITE WALK MADE IT +3.** Two 3-byte calls
inserted, one 3-byte call deleted — the deleted one being a `skip_spaces` that
`eval`'s own first instruction (`ev_f` → `call ev_sp`) has been redoing since
`ev_f` was written. The same shape as D-NAMSPC's result and for the same reason:
**walk the callers/callees before pricing, not after.**

### 10.3 The ROM hashes — all four predicted

| ROM | at `f0b688d` | predicted | as built |
|---|---|---|---|
| `basic-reloc.rom` | `f04e402d…` | MOVES | **`f9d427e0…`** ✅ |
| `sub.rom` | `accce5a1…` | **HOLDS** | **`accce5a1…`** ✅ |
| `disk.rom` | `2c630d3d…` | **HOLDS** | **`2c630d3d…`** ✅ |
| `zerobas-main-eu.rom` | `c66ab7e0…` | MOVES | **`19e0ee37…`** ✅ |

⚠️ `FIELD`/`LSET` **do** have sub-ROM tenants (`fld_lookup_tenant`,
`lrset_store_tenant`), so the hold was worked out rather than assumed: every
byte this slice moves is in `ex_field`, which is main page 1, and every routine
it calls (`check_expr_errors` `$43B2`, `get_byte_arg` `$44FD`,
`type_mismatch_error` `$426A`) is main page 1 too. Had the fix landed in either
tenant the prediction would have inverted.

### 10.4 The gates

| gate | before | predicted | measured |
|---|---|---|---|
| **`fldwidth-acceptance`** | 24/42 | 40/40 + 2 deferred | **40/40, 2 deferred (42 cases)** ✅ |
| **`namspc-acceptance`** | 56/56 + 2 deferred | 58/58 | **58/58, 0 deferred** ✅ |
| `audit-citations` swept / basic | 763 / 200 | 766 / 201 | *(§10.7)* |
| `injector-check` | 347 | 348 | **348** ✅ |
| `rowshape-check` | 16 → 17 | 18 probes | **18** ✅ |
| `preflight-check` | 181/86/95/95/0 | unchanged | **181/86/95/95/0** ✅ |
| `unit-test` · `latch-check` · `deadcode` | 59 · 16/16 · 0/0 (+1) | unchanged | **unchanged** ✅ |

### 10.5 🔴 Three things went differently

**(a) THE RESIDUAL NAMED ONE CLAUSE AND THE RULE HAS SIX.** It was filed as
*"`ex_field` never type-checks its field width"*, with two rows. The type check
is **3 of the 6 bytes**; the other three buy a DOMAIN rule nobody had asked
about, and the domain rule is the interesting half. 🎯 **`d.big` (70000 →
`Overflow`) against `d.neg`/`d.256`/`d.257` (→ `Illegal function call`) is
`get_byte_arg`'s two stages, exactly**, and `d.zero` says **0 is legal**. Had
the reference answered one error for all four, the fix would have been a
hand-rolled comparison against a bound this slice would have had to invent. It
did not — so the fix is a `call` into code that already ships, is already the
reference's rule, and is already shared by `CHR$`/`STRING$`/`SPACE$`/`ON`/
`WIDTH`. **A denominator built only around the filed clause would have cost more
bytes and delivered less.**

**(b) 🔴 `basic/field.asm`'s OWN HEADER WAS THE WRONG ORACLE, AND IT SAID SO IN
THE FILE UNDER TEST.** *"field widths are 1..255"* — invented by this file,
carried since Phase 2c, and refuted by `d.zero` (`FIELD#1,0 AS A$` → `LEN(A$)`
= 0 on the CF-3300). A design that had trusted it would have shipped `0` →
`Illegal function call`, a divergence created by the comment rather than by the
code ([[a-source-comment-about-the-emulator-is-a-claim]] — same shape, different
file). The line is corrected in the same commit as the code that enforces the
real domain.

**(c) 🔴 THE PROBE'S READER WAS BLIND TO ITS OWN SUBJECT, AND IT FAILED BY
AGREEING.** `bracket()` returns the first error name it finds in the screen
tail; `Overflow` is a **substring of `FIELD overflow`** and was listed earlier,
so `FIELD overflow in 30` scored as `<Overflow>`. Nothing looked wrong: *"300 is
too big → Overflow"* is exactly what a plausible reading predicts, so the row
agreed with a wrong answer ([[readout-blind-to-its-own-subject]]). What exposed
it was **`d.big`** — 70000, a genuinely different fault — returning the *same*
string. Two rows that must differ, reading identically, is the signal; a single
row could not have produced it. Needles are now sorted longest-first, and the
two separate into `<FIELD overflow>` and `<Overflow>` — which is also what made
§6.5's decline a *measured* decline rather than a mis-read one.

### 10.6 Knives — 5 cuts × 2 rounds, **ALL TEN EXACT, both rounds identical**

| # | cut | predicted RED | measured | |
|---|---|---|---|---|
| **K-FW1** | `call check_expr_errors` → `call check_fperr_only` | the 7 string rows | **exactly those 7** | ✅ ×2 |
| **K-FW2** | `call get_byte_arg` → `call get_int16_checked` | `d.neg` `d.256` `d.257` `m.neg2` `o.dt` | **exactly those 5** | ✅ ×2 |
| **K-FW3** | `jp z,type_mismatch_error` → `jp z,exf_syn` | 🎯 **`t.num` ONLY** | **exactly that 1** | ✅ ×2 |
| **K-FW4** | `ev_sp`: `cp ' '` → `cp $7F` | `c.wsp` `c.wsp2` | **exactly those 2** | ✅ ×2 |
| **K-FW5** | `CONTROL_WANT["c.lit"]` unmatchable, probe-only | rc 2, ROMs unmoved | **rc 2 + `NOT MEASURED`, ROMs held** | ✅ ×2 |

🎯 **K-FW1 AND K-FW2 ARE PARTIAL REVERTS, AND THAT IS WHY THE GREEN SETS CARRY
THE WEIGHT.** Each swaps one 3-byte `call` for another into a routine that
already does *part* of the job, so each removes exactly one clause of §1's rule:

* **`d.div` survives K-FW1** — the FPERR half of `check_expr_errors` is what
  `check_fperr_only` *is*, so `Division by zero` still fires.
* **`d.big` survives K-FW2** — `Overflow` comes from `get_int16_checked`, the
  stage the cut keeps. So the ERR 6 and the ERR 5 are demonstrably from
  different stages, which no single row can say.
* **`o.wt` survives K-FW1**, and this one was *computed*: with the `TMISMATCH`
  test gone, `FACTYP` is still 2 (the value `eval` set on entry;
  `type_mismatch_set` never changes it), so `fac_to_int_strict` returns
  immediately with `DE` = its hard 0 — the string is accepted as **width 0**,
  the `AS` matches, and the *target* test raises the same ERR 13 the reference
  gives. A knife whose green set contains the row you would naively expect to
  redden is worth more than one whose sets are tidy.

⚠️ **K-FW4's first draft would have measured nothing.** The obvious byte-neutral
cut of `ev_sp`'s `cp ' '` is `cp $00` — and `$00` is the **line terminator**, so
the loop would `inc ix` past the end of every line and **hang the machine**.
Every row would have read `<RUN SCROLLED OFF>` and the knife would have
"reddened" 42 rows while measuring nothing at all. Caught while writing the
runner, not while reading the result; the cut is `cp $7F`.

⚠️ **The 7 positive controls have no cut**, named rather than left implied:
their subject is the working `FIELD` path this slice does not touch, and a cut
that moved them would be measuring `basic_probe_fldary.py`'s gate.

⚠️ Predicted sets were quantified over all **42 printed** rows, not the 40 the
gate scores — `d.sum` and `d.sum1` are DEFERRED, are returned by
`probe_report.parse()` like any other row, and are in every GREEN set. That is
D-TGTSPC's K-TS4 lesson applied rather than restated.

### 10.7 Corpus

Sequentially from clean (`rm -rf build` + `make repack-machine`, **bash** —
`zsh` does not word-split `make $t`), **33 targets, all rc=0, 17 min 06 s wall**
(1026 s): the 32 of [`spec-basic-namspc.md`](spec-basic-namspc.md) §10.7 —
`unit-test` **59** · `audit-citations` CLEAN (**766** swept, basic **201**) ·
`preflight-check` **181/86/95/95/0** · `injector-check` **348** ·
`rowshape-check` **18** probes · `latch-check` **16/16** · `deadcode`
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
`nxary-acceptance` **22/22** · `tgtspc-acceptance` **28/28** ·
**`namspc-acceptance` 58/58 (0 deferred)** — **plus `fldwidth-acceptance`
40/40 (2 deferred, 42 cases)**.

⚠️ `latch-check` still has **no `repack-machine` prerequisite**, so the script
builds explicitly before the loop; and `lnblank-acceptance` **defaults to
`REPEAT=1`**, so the `REPEAT=2` is passed by hand
([[pin-fired-inside-its-own-slice]]).

✅ `audit-citations` swept **766** exactly as §7 predicted — 763 + one probe +
**two documents**. That is D-NAMSPC's own §10.7 miss corrected: the listing and
hex-dump sweeps count every file in the tree, docs included, while the
per-language `basic` count (200 → **201**) globs only
`basic/`+`sub/`+`probes/basic/*.py`
([[a-count-is-predicted-by-reading-its-definition]] — this time the definition
was read for *both* counters).

Copy *this* list forward, not the last one — the gate a slice ADDS is exactly
the one a runner rebuilt from the previous slice omits.

### 10.8 The fix, as a program

Every cell below is a **LITERAL screen row** read after `RUN`: the zerobas
"before" column from a rebuilt pre-fix ROM (`basic-reloc.rom f04e402d…`, hash
checked), the "after" from the shipped one (`f9d427e0…`), and the CF-3300
column measured on the reference itself — **not** the battery's canonicalised
error name, which is a different reading and would have quietly merged
`FIELD overflow` into `Overflow` (§10.5(c)).

**The residual's own program — and there is no space anywhere in it:**

```basic
10 OPEN"TS.DAT"AS #1
20 B$="X"
30 FIELD#1,B$ AS A$
40 PRINT LEN(A$)
```

| | screen after `RUN` |
|---|---|
| CF-3300 | `Type mismatch in 30` |
| zerobas **before** → **after** | `0` → **`Type mismatch in 30`** |

🎯 **`0`, not `OK`.** The field really was created, at width zero — which is
what `type_mismatch_set` leaves in `DE` — and only a fixture that reads
`LEN(A$)` back can see it.

**…and the row that named the rule, because it is a DIFFERENT error:**

```basic
10 OPEN"TS.DAT"AS #1
20 FIELD#1,70000 AS A$
30 PRINT LEN(A$)
```

| | screen after `RUN` |
|---|---|
| CF-3300 | `Overflow in 20` |
| zerobas **before** → **after** | `0` → **`Overflow in 20`** |

Past int16 is `Overflow`; outside 0..255 but inside int16 is `Illegal function
call`; 0 is accepted. Two codes, three outcomes — `get_byte_arg`'s two stages
exactly, which is why the whole domain rule cost 3 bytes.

**…and the row that ORDERS the checks, where two faults compete:**

```basic
10 OPEN"TS.DAT"AS #1
20 FIELD#1,-1 AS A
30 PRINT"OK"
```

| | screen after `RUN` |
|---|---|
| CF-3300 | `Illegal function call in 20` |
| zerobas **before** → **after** | `Syntax error in 20` → **`Illegal function call in 20`** |

🎯 **The width is checked before the target, and this is the only program that
can say so.** Its twin `o.wt` (a *string* width with the same numeric target)
raises ERR 13 for either reason and agrees whichever fires first
([[one-row-cannot-separate-two-rules]]).
