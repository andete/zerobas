# D-EVALCHK — a DEFERRED expression error outranks the coercion's own overflow

Slug **D-EVALCHK**. Based on `65171d6` (D-FLDWIDTH) on `main`, 2026-08-09.

Subject: the residual [`TODO.md`](../TODO.md) §"Open — standing residuals" filed
by D-FLDWIDTH — *"a −10 B funding carve exists in `ex_width` and is DECLINED on
a missing reading"*. The reading has now been taken, on **two** references, and
it does not say what the decline assumed.

Instrument: [`basic_probe_width.py`](../probes/basic/basic_probe_width.py),
extended from D-WID's 57 VG-8020 rows to **94 rows on three sides**.

---

## 1. The reading, taken before anything was designed

The residual said the carve was blocked because folding `ex_width` onto
`check_expr_errors` *"changes `WIDTH 1/0`'s answer, and nobody has measured what
a reference says to it"*. Both halves of that turn out to be wrong, and the
second one is wrong in the more interesting direction.

| row | subject | VG-8020 | CF-3300 | zerobas at `65171d6` | |
|---|---|---|---|---|---|
| `dfe-div0` | `WIDTH 1/0` | ` 11 ` | ` 11 ` | ` 11 ` | 🟢 **already agrees** |
| `dfe-defer` | `WIDTH 1+0*(1/0)` | ` 11 ` | ` 11 ` | ` 11 ` | 🟢 already agrees |
| `dfe-sqr` | `WIDTH SQR(-1)` | ` 5 ` | ` 5 ` | ` 5 ` | 🟢 already agrees |
| `dfe-70000` | `WIDTH 70000` | ` 6 ` | ` 6 ` | ` 6 ` | 🟢 already agrees |
| `dfe-plus0` | `WIDTH 30+0*1` | ` 0 30 ` | ` 0 30 ` | ` 0 30 ` | 🟢 already agrees |
| `dfe-tmfp` | `A$="X":WIDTH (A$<5)+0*(1/0)` | ` 13 ` | ` 13 ` | ` 13 ` | 🟢 already agrees |
| **`dfe-ovfdiv`** | **`WIDTH 70000+0*(1/0)`** | **` 11 `** | **` 11 `** | **` 6 `** | 🔴 |
| **`dfe-ovfsqr`** | **`WIDTH 70000+0*SQR(-1)`** | **` 5 `** | **` 5 `** | **` 6 `** | 🔴 |
| **`cl-ovfdiv`** | **`CLEAR 70000+0*(1/0)`** | **` 11 `** | **` 11 `** | **` 6 `** | 🔴 |

(Readout = the trapped `ERR` code; ERR 5 `Illegal function call`, 6 `Overflow`,
11 `Division by zero`, 13 `Type mismatch`. Full matrix in
[`evalchk-msx1-characterization.md`](evalchk-msx1-characterization.md).)

**THE RULE, in one sentence:** *when the argument expression has ALREADY faulted
and the value it nevertheless leaves in FAC is ALSO out of int16, the reference
reports the **expression's** error, not the **coercion's**.* One clause, two
fault classes (`1/0` → ERR 11, `SQR(-1)` → ERR 5), three verbs, two references.

🔴 **THE BLOCKER ROW WAS ALREADY GREEN, AND THE SOURCE SAYS WHY.**
`get_byte_arg` → `get_int16_checked` ends `jp check_fperr_only`
([`basic/interp.asm:1520`](../basic/interp.asm:1520)), and `fac_to_int_strict`
does **not** clear `FPERR` on its way through. So a deferred FPERR left by
`eval` is *already* surfaced by the coercion, one step later than
`check_expr_errors` would surface it — with the **same** code, for every value
that does not also overflow. `WIDTH 1/0` never needed the fold, and no reading
had to be taken to keep it working. The decline was priced against a hazard the
call graph had already closed.

🎯 **AND THE ROW THE DECLINE COULD NOT IMAGINE IS THE ONE THAT PAYS FOR THE
SLICE.** `fac_to_int_strict` *sets* `FPERR=1` on an out-of-int16 magnitude —
**overwriting** the `FPERR=2`/`FPERR=3` the expression already left there. So the
error zerobas reports is whichever of the two was written **last**, and the
references report whichever happened **first**. Three rows say so, at three
different verbs, in two fault classes. **The carve is not free; it is a fix that
also returns 13 bytes.**

---

## 2. What is wrong, in one sentence

Three statement handlers evaluate an argument, test `TMISMATCH` inline, and then
run a checked coercion whose own `FPERR` write **clobbers** the expression's
pending one — so `WIDTH`/`CLEAR`/`LOCATE` answer `Overflow` where both references
answer the fault the expression actually raised.

---

## 3. Scope

### 3.1 The site walk, done rather than restated

`grep -rn "TMISMATCH" basic/*.asm` returns 12 read sites. Only the ones matching
*`call eval` → post-eval check → CHECKED COERCION* are candidates; the rest are
listed here so the walk is auditable rather than asserted.

| site | shape | in this slice? |
|---|---|---|
| [`basic/field.asm:298`](../basic/field.asm:298) `exf_item` | `call eval` / `call check_expr_errors` / `call get_byte_arg` | ✅ **folded** — 9 B → 3 B, **behaviour-identical** (it already had the right order; D-FLDWIDTH put it there) |
| [`basic/screen.asm:161`](../basic/screen.asm:161) `ex_width` | `call eval` / inline `TMISMATCH` / `call get_byte_arg` | ✅ **folded** — 13 B → 3 B, and `dfe-ovfdiv`/`dfe-ovfsqr` change |
| [`basic/clear.asm:64`](../basic/clear.asm:64) `ex_clear` | `call eval` / inline `TMISMATCH` / `call get_int16_checked` | ✅ **folded** — 13 B → 3 B, and `cl-ovfdiv` changes. **A DIFFERENT COERCION**, which is why the helper has two entry points |
| [`basic/missing.asm:237`](../basic/missing.asm:237) `loc_next` | `call eval` / inline `TMISMATCH` / the whole two-stage check **written out** | ❌ **DECLINED, WITH ITS READING TAKEN** — §6.6 |
| [`basic/float-arith.asm:1289`](../basic/float-arith.asm:1289) `eval_chan` | `call eval` / `TMISMATCH` / **conditional** coercion / `jp check_expr_errors` | ❌ different shape: the coercion is SKIPPED on a mismatch by design (D-BADFNUM §6) |
| [`basic/arrays.asm:808`](../basic/arrays.asm:808) `ex_let_arr` | `TMISMATCH` then `FPERR`, both with **stack unwinding** arms (`ela_abort_tm`) | ❌ needs `check_expr_errors_popbc`'s shape, no coercion |
| [`basic/files.asm:1108`](../basic/files.asm:1108) `fch_check_d` | a channel-number test, no `eval`, no coercion | ❌ |
| [`basic/str-engine.asm:1112`](../basic/str-engine.asm:1112) | promotes `TMISMATCH` **into** `FPERR`, first-error-wins | ❌ |
| [`basic/expr.asm:884`](../basic/expr.asm:884) `ev_ff_ckpdl` | suppresses PDL's ERR 5 so a deferred `TMISMATCH` can surface | ❌ |
| [`basic/interp.asm:151`](../basic/interp.asm:151) | the per-statement **clear** of both flags | ❌ |
| `sysvars.inc`, `print.asm:242`, `str-engine.asm:1544` | the address, the SETTER, the comparator | ❌ |

### 3.2 🔴 THE CONSTRAINT — the interposed frame must not break the abort

Every fold replaces *N* instructions **at the handler's own depth** with a
`call`, so every abort inside the check now fires **one frame deeper**. That is
exactly the hazard `basic/missing.asm`'s header describes as a live bug.

**It is closed, and the closure is in the tree, not in this argument.** Both
abort arms reset SP from `SAVSTK` before they print:

* trap armed → [`raise_error_hl`](../basic/interp.asm:873) `ld sp,(SAVSTK)`;
* no trap → [`fre_abort_low`](../basic/arrays.asm:118) `ld sp,(SAVSTK)`, added
  by `4d35b6d` (D-CUR-D, [`spec-basic-abort-depth.md`](spec-basic-abort-depth.md)
  §4) **precisely because** `get_byte_arg`'s reject used to return into
  `ex_width` with `A` = the error code.

`type_mismatch_error` and `fp_runtime_error` both funnel through `raise_error`,
so both are covered. The standing detectors are already in this probe:
`s0-300` / `s0-256` / `s0-neg1` read *"ERR 5 raised **and** `LINLEN` was not
scribbled"*, and `unt-300` reads the untrapped screen. If the depth claim were
false those rows would be the first to fall.

⚠️ **`basic/missing.asm`'s header is therefore STALE**, and it is stale in the
file that carries the fourth site. It is corrected in this commit even though
the code beneath it is not — §6.6.

### 3.3 The boundary — what this slice does NOT touch

* **`loc_next` (LOCATE).** Measured (§6.6), priced at **−29 B**, declined: its
  fix is *deleting a defensive apparatus* justified by the stale comment above,
  which is a claim needing its own falsification and LOCATE's own denominator.
  Filed in `TODO.md` **with its four readings already taken**.
* **`CLEAR`'s own domain** — D-CLP's surface
  (`basic_probe_clearpool.py`). Only the deferred-error ORDER moves here; the
  `cl-ok` / `cl-neg` / `cl-500` / `cl-70000` rows exist to prove the rest does not.
* **`FIELD overflow` (ERR 50)** — re-priced in §6.5, still declined.
* **The UNWIND** — `make abort-acceptance` owns it; §3.2 only *rests* on it.
* **Message WORDING** — D-MSGEXACT's surface.

---

## 4. Design

### 4.1 🎯 ONE ROUTINE, TWO ENTRY POINTS, BECAUSE THERE ARE TWO COERCIONS

`WIDTH`/`FIELD` want a **byte**; `CLEAR` wants an **int16 with a sign test**.
`get_byte_arg` is already `get_int16_checked` plus a two-instruction byte stage,
so the helpers nest the same way and the byte one costs 5 B rather than 8:

```
eval_int16_checked:                     ; the shared head: eval, then the
                call    eval            ; DEFERRED-ERROR CHECK, then coerce
                call    check_expr_errors
                jr      get_int16_checked
eval_byte_checked:
                call    eval_int16_checked
                jr      gba_byte        ; get_byte_arg's byte stage alone
```

`gba_byte` is a new **label only** (0 B) inside `get_byte_arg`, at the point its
own `call get_int16_checked` returns. Sited immediately above `eval_pos_arg` in
[`basic/interp.asm`](../basic/interp.asm), where `get_int16_checked`,
`get_byte_arg` and their two existing `eval`-folding leaves already live.

**THE ORDER IS THE FIX, AND IT IS ONE INSTRUCTION'S WORTH OF MOVEMENT.** The
check runs **before** the coercion instead of after, so the expression's pending
`FPERR` is read before `fac_to_int_strict` can overwrite it.

### 4.2 Register contract — checked, not assumed

| | |
|---|---|
| `HL` (token cursor) | `eval` advances it; `check_expr_errors` reads two RAM bytes and `ret`s; `get_int16_checked` `push`/`pop`s it across `fac_to_int_strict`. **Preserved.** |
| `DE` | `get_int16_checked` returns the int16; `check_fperr_only`'s clean path does not touch it. `ex_clear`'s `bit 7,d` and `ld (POOLSIZE),de` read it. **Preserved.** |
| `A` / `E` | `get_byte_arg` returns `A = E = byte`, `D = 0`. `ex_width`'s `ld b,a` and `exf_item`'s `push de` read them. **Unchanged.** |
| `SP` | one extra frame; §3.2. |

### 4.3 The three call sites

```
exf_item:   call eval / call check_expr_errors / call get_byte_arg
         -> call eval_byte_checked                          ; 9 -> 3, NO behaviour change
ex_width:   call eval / ld a,(TMISMATCH) / or a / jp nz,type_mismatch_error / call get_byte_arg
         -> call eval_byte_checked                          ; 13 -> 3
ex_clear:   call eval / ld a,(TMISMATCH) / or a / jp nz,type_mismatch_error / call get_int16_checked
         -> call eval_int16_checked                         ; 13 -> 3
```

### 4.4 RAM

None. No new sysvar, no new scratch byte.

---

## 5. Forced constraints

### 5.1 The `TMISMATCH` test must stay AHEAD of the FPERR test
`dfe-tmfp` (`WIDTH (A$<5)+0*(1/0)`) has **both** flags set and reads ` 13 ` on
both references. `check_expr_errors` tests `TMISMATCH` first; `check_fperr_only`
is the same routine minus that test. This is what K-EV1 cuts.

### 5.2 The check must stay AHEAD of the coercion
That is the whole rule (§1). `dfe-ovfdiv`/`dfe-ovfsqr`/`cl-ovfdiv`.

### 5.3 `CLEAR` must keep the int16 coercion, not acquire a byte one
`cl-500` (`CLEAR 500`) is accepted on both references. Routing `ex_clear` through
the **byte** entry would make it ERR 5 — which is exactly K-EV3.

### 5.4 `FIELD` must not move at all
`exf_item`'s fold is a pure 6-byte collapse of three calls into one; the shipped
`fldwidth-acceptance` **41/41** is the guard, and K-EV4 is the knife.

### 5.5 Region
Every byte is main page 1. `basic/screen.asm` (15 labels), `basic/clear.asm` (3),
`basic/field.asm` (46) and `basic/interp.asm` (79) are **100 % page 1** by
`carve_scout.py`. No low-region byte, no sub-ROM byte, no RAM.

---

## 6. The carve scout

Off `build/basic-reloc.sym` from a clean build at `65171d6` (`rm -rf build &&
make basic-reloc`): low **11 B**, page 1 **3 B**, sub p0 **3604 B**, sub p1
**1483 B**; `basic-reloc.rom f9d427e0…`, `sub.rom accce5a1…`, `disk.rom
2c630d3d…`, `zerobas-main-eu.rom 19e0ee37…`.

### 6.1 Region — asked before anything is priced

| symbol | address | region |
|---|---|---|
| `ex_width` … `wid_missing` | `$590E`–`$594E` | **page 1** |
| `ex_clear` … `clr_himem` | `$52F9`–`$5325` | **page 1** |
| `exf_item` … `exf_comma` | `$7299`–`$72DC` | **page 1** |
| `get_int16_checked` / `get_vram_arg` | `$44DE` / `$44E6` | page 1 — the insertion neighbourhood |
| `eval_pos_arg` / `eval_byte_arg` / `get_byte_arg` / `gb_illegal` | `$44EF` / `$44F7` / `$44FD` / `$4506` | page 1 — each moves **+13** |
| `check_expr_errors` / `check_fperr_only` | `$43B2` / `$43B8` | page 1 — **unchanged**, reused |
| `eval` | `$4A9E` | page 1 — reused |

`carve_scout.py`: `screen.asm` 293 B, `clear.asm` 66 B, `field.asm` 571 B,
`interp.asm` 1186 B — **all of it page 1**, nothing leaves it, no eviction is
proposed. Recorded because the scout was run **before** the price.

### 6.2 The estimator, calibrated before it is used

Hand-counted from source and checked against the `.sym` **first**
([[calibrate-a-hand-counter-before-quoting-it]]):

| span | counted | `.sym` Δ | |
|---|---|---|---|
| `ex_width` → `wid_bound` | 1+3+1+2+2+2+3+3+1+3+3+1+3+3+1+2+2+1+2 = **39** | `$5935−$590E` = **39** | ✅ |
| `wid_bound` → `wid_apply` | 1+2+1+1+2+3+1 = **11** | `$5940−$5935` = **11** | ✅ |
| `wid_apply` → `wid_illegal` | 3+1+3+1+3 = **11** | `$594B−$5940` = **11** | ✅ |
| `wid_illegal` → `wid_missing` | **3** | `$594E−$594B` = **3** | ✅ |
| `wid_missing` → `ex_key` | **3** | `$5951−$594E` = **3** | ✅ |
| `ex_clear` → `clr_himem` | 1+3+1+2+2+2+2+2+3+3+1+3+3+2+3+4+3+2+2 = **44** | `$5325−$52F9` = **44** | ✅ |
| `exf_item` → `exf_comma` | **67** | `$72DC−$7299` = **67** | ✅ |
| `loc_next` → `loc_illegal` | 1+4+3+1+2+2+2+2+2+3+3+1+3+1+3+1+3+1+3+1+1+2+1+1+2 = **49** | `$7ED1−$7EA0` = **49** | ✅ |
| `loc_illegal` → `loc_omit` | 2+3 = **5** | `$7ED6−$7ED1` = **5** | ✅ |

**9/9 exact.** (`ld (nn),de` is 4 B, `ED 53`-prefixed — the one width a hand
count gets wrong, and it is in two of these spans.)

⚠️ **THE LAYOUT HAZARD IS NAMED RATHER THAN HOPED AWAY** ([[knife-prediction-inherits-the-drafts-layout-error]]).
The design adds **two labels and one label-only split**, deletes none, and both
new `jr`s are computed against the post-move layout, not the current one:

| `jr` | from | to | displacement |
|---|---|---|---|
| `eval_int16_checked`'s `jr get_int16_checked` | `$44F5` (next `$44F7`) | `$44DE` | **−25** ✅ |
| `eval_byte_checked`'s `jr gba_byte` | `$44FA` (next `$44FC`) | `$450D` | **+17** ✅ |

Both are inside −128..127 by a factor of five. Nothing else changes branch
distance: the three call sites each replace *N* bytes with a `call`, so every
`jr` inside them spans **less** than before.

### 6.3 The cost — a BOUND, with the twin named for every part

| body | region | before | after | Δ |
|---|---|---|---|---|
| `eval_int16_checked` — **new** (`call eval` 3 + `call check_expr_errors` 3 + `jr` 2) | p1 | 0 | 8 | **+8** |
| `eval_byte_checked` — **new** (`call eval_int16_checked` 3 + `jr` 2) | p1 | 0 | 5 | **+5** |
| `gba_byte` — a LABEL inside `get_byte_arg` | p1 | 6 | 6 | **0** |
| `exf_item` — three calls become one | p1 | 67 | 61 | **−6** |
| `ex_width` → `wid_bound` — 13 B inline becomes a 3 B call | p1 | 39 | 29 | **−10** |
| `ex_clear` → `clr_himem` — 13 B inline becomes a 3 B call | p1 | 44 | 34 | **−10** |
| every other body / low / sub p0 / sub p1 / RAM | — | | | **0** |
| **main page-1 total** | | | | **−13** |

### 6.4 The bottom line

| region | free at `65171d6` | slice | free after |
|---|---|---|---|
| **main page 1** | **3 B** | **−13** | **16 B** |
| main low | 11 B | 0 | **11 B** |
| sub page 0 / page 1 | 3604 / 1483 | 0 | **unchanged** |

🎯 **THE FILED PRICE WAS "≈ −2 B NET" AND THE REAL ONE IS −13, BECAUSE THE FILED
ONE PRICED ONE HELPER AND TWO SITES.** Walking the site found a third caller of
the same shape (`ex_clear`), and walking `get_byte_arg` found that the two
coercions **nest** — so the second entry point costs 5 B, not 8, and pays for
itself four times over. This is D-NAMSPC's result again, one slice on
([[the-existing-split-is-cheaper-than-a-new-guard]]).

### 6.5 💰 `FIELD overflow` (ERR 50) — RE-PRICED, STILL DECLINED

D-FLDWIDTH §6.5 priced it at **≈27 B** against a 6 B wall. Page 1 is now **16 B**
— so the byte half of that decline is **narrower but still short by 11 B**, and
nothing in this slice changes the other two blockers:

* the check needs `FCH_RECLENS[ch]`, whose only accessor `load_reclen` is
  **sub-ROM** and not callable from `ex_field`; `GP_RECLEN` is loaded at GET/PUT
  time, so reading it here reads a stale cell;
* 🔴 **its denominator is still unbuilt.** Every measured row uses the DEFAULT
  256-byte record, so nothing separates *"checked against the record length"*
  from *"checked against a constant 256"*. That needs `OPEN … LEN=r` rows.

**Bytes alone were never the whole blocker and are still not.** Re-stated in
`TODO.md` with the new wall.

### 6.6 💰 `loc_next` (LOCATE) — DECLINED AT **−29 B**, WITH ITS READING TAKEN

> ✅ **TAKEN 2026-08-09 BY D-LOCARG** ([`spec-basic-locarg.md`](spec-basic-locarg.md)),
> at exactly −29 B, and it funded the +7 B `DIRECTF` derive
> [`spec-basic-onerr0.md`](spec-basic-onerr0.md) §7 had deferred: main page 1
> **0 B → 22 B**.
> 🔴 **AND THE DENOMINATOR THIS SECTION ASKED FOR WAS ALREADY BUILT.** Every axis
> named below as missing — row/column, omitted arguments, the `CON_LASTROW`
> clamp, `CSRLIN`/`POS` read-back — was already in `make missing-acceptance`,
> 214 recorded rows. The one axis that genuinely did not exist was the deferred
> expression error itself. The decline was right on the arithmetic (four rows are
> not a denominator) and wrong on the inventory, and `grep LOCATE probes/` is the
> command that would have said so.

The fourth site, and the largest carve in this walk. Measured on the same three
sides (`plain()` fixture, scratch run 2026-08-09):

| subject | VG-8020 | CF-3300 | zerobas | |
|---|---|---|---|---|
| `LOCATE 1/0,1` | ` 11 ` | ` 11 ` | ` 11 ` | 🟢 |
| `LOCATE 70000,1` | ` 6 ` | ` 6 ` | ` 6 ` | 🟢 |
| `LOCATE "5",3` | ` 13 ` | ` 13 ` | ` 13 ` | 🟢 |
| **`LOCATE 70000+0*(1/0),1`** | **` 11 `** | **` 11 `** | **` 6 `** | 🔴 the same divergence |

| part | bytes |
|---|---|
| `call eval` / `ld a,(TMISMATCH)` / `or a` / `jp nz,type_mismatch_error` | 3+3+1+3 = **10** |
| `push hl` / `call fac_to_int_strict` / `pop hl` / `ld a,(FPERR)` / `or a` / `jp nz,fp_runtime_error` / `ld a,d` / `or a` / `jr nz,loc_illegal` / `ld a,e` | 1+3+1+3+1+3+1+1+2+1 = **17** |
| → `call eval_byte_checked` | **3** |
| `loc_illegal` (`ld a,5` / `jp raise_error`), orphaned | **−5** |
| **total, main page 1** | **−29** |

**DECLINED, and not for bytes.** The 17-byte inline block exists because
`basic/missing.asm`'s header claims `get_byte_arg` *"CANNOT BE CALLED here"* —
a claim `4d35b6d` retired and nobody went back to. Acting on that means
**deleting a defensive apparatus** (`LOC_RET`, the parked frame, `loc_illegal`)
on the strength of a refutation, which needs its own knife — put the frame back
and show the aborts still land — and LOCATE's own denominator (row/column,
omitted arguments, the `CON_LASTROW` clamp, `CSRLIN`/`POS` read-back), none of
which this probe has. A −29 B carve is exactly the size that should not ride
along in someone else's slice. Filed in `TODO.md` with the four readings above,
and the stale header is corrected **in this commit** so the next reader is not
blocked by a comment this slice already refuted
([[a-source-comment-about-the-emulator-is-a-claim]]).

### 6.7 💰 `eval_byte_arg`'s redundant `jp` — DECLINED at −3 B

`eval_byte_arg` (`$44F7`) is `call eval` / `jp get_byte_arg`, and
`get_byte_arg` is at `$44FD` — **the very next instruction**. The `jp` is a 3-byte
no-op that a fallthrough would replace. Declined: it buys 3 B this slice does not
need, its only guard is layout adjacency (nothing would fail if a future edit
inserted a routine between them — it would just silently cost 3 B again), and it
is a tidy-up **no row can see**. Recorded so it is not re-derived.

### 6.8 ✅ VERDICT: **GO, −13 into 3.** No eviction, no RAM, no sub-ROM byte, one label-only split.

---

## 7. Predicted GREEN

`make width-characterize` must read, on all three sides:

| rows | prediction | |
|---|---|---|
| `dfe-ovfdiv` | ` 6 ` → **` 11 `** | 🔴 **THE SUBJECT** — the deferred `1/0` now outranks the coercion's overflow |
| `dfe-ovfsqr` | ` 6 ` → **` 5 `** | 🔴 **THE SUBJECT, second fault class** — and a *different* code, which is what says the rule is "the expression's error" and not "division by zero is special" |
| `cl-ovfdiv` | ` 6 ` → **` 11 `** | 🔴 the same rule at the second site |
| the other **91** rows | unchanged | 🟢 green before **and** after |
| `dfe-div0` `dfe-defer` `dfe-sqr` `dfe-70000` | ` 11 ` ` 11 ` ` 5 ` ` 6 ` | 🟢 the blocker row and its three neighbours — **already green**, §1 |
| `co-str` `co-strvar` `dfe-tmonly` `dfe-tmfp` `cl-str` | ` 13 ` | 🟢 the `TMISMATCH` clause must survive the move into a shared routine |
| `cl-ok` `cl-500` `cl-neg` `cl-70000` | ` 0 ` ` 0 ` ` 5 ` ` 6 ` | 🟢 `CLEAR`'s int16 stages, unchanged — §5.3 |
| all 15 `s0-*`, 9 `s1-*`, 11 `s2-*` | unchanged | 🟢 the DOMAIN is not this slice's surface |
| all 7 `unt-*` | unchanged | 🟢 the untrapped seam — the §3.2 depth detector |

**Gate: `width-acceptance` 91/94 → 94/94.**
**Gate: `fldwidth-acceptance` 40/40 (2 deferred, 42 cases) — unchanged**, and
that is a prediction, not a hope: `exf_item`'s fold is behaviour-identical
(§5.4).
**Gate: `clearpool-acceptance` — unchanged**; none of its rows puts a deferred
fault and an int16 overflow in one expression. ⚠️ **The count is stated as
"unchanged" rather than as a number on purpose** — see §10.5(c).

### 7.1 Predicted ROM hashes

| ROM | at `65171d6` | predicted |
|---|---|---|
| `basic-reloc.rom` | `f9d427e0…` | **MOVES** |
| `zerobas-main-eu.rom` | `19e0ee37…` | **MOVES** (it embeds the relocated image) |
| `sub.rom` | `accce5a1…` | **HOLDS** |
| `disk.rom` | `2c630d3d…` | **HOLDS** |

⚠️ **The hold was worked out, not assumed.** The sub build's ONLY dependency on
main addresses is [`sub/basic-resident-abi.inc`](../sub/basic-resident-abi.inc),
generated from `$(RELOC_SYM)` by `tools/gen_resident_abi.py`. It contains
**11 equates and every one is below `$4000`** (`fp_add $34B7` … `vars_reset
$3DAD`) — the low region, which this slice does not touch. A page-1-only change
therefore regenerates the identical `.inc` and the identical `sub.rom`. Had any
byte landed in the low region, or had the ABI exported a page-1 symbol, the
prediction would invert.

---

## 8. Knives — drafted before the row set was frozen

Read [`dev-workflow.md`](dev-workflow.md) §"Knives" first. Subject = the probe
invoked **directly** at `--sides vg8020,zb` (a REFERENCE plus zb — never a lone
`zb`; the diff is over zb's values and the reference is a constant), except
K-EV4, which needs a second instrument, and K-EV5, which is probe-only. Every
cut is byte-neutral. Every cut is run **twice**.

🔴 **THE PREDICTIONS ARE QUANTIFIED OVER ALL 94 ROWS THE PROBE PRINTS.** At
`--sides vg8020,zb` there are no DEFERRED rows and no `noref` rows, so printed
= scored = 94; the D-TGTSPC lesson (a runner diffs what the probe **prints**)
still governs and is stated rather than assumed.

⚠️ **WHAT DOES A HUNG MACHINE SCORE HERE?** Every trapped row would read
`<none>` and every `unt` row `<no echo>` — i.e. **all 94 red**. No cut below can
hang (each swaps one `call` operand for another into a routine that terminates;
none touches a loop condition — D-FLDWIDTH's K-FW4 `cp $00` trap has no analogue
here). The runner therefore **aborts** on a 94-row red set instead of scoring it.

| # | cut (byte-neutral) | instrument | predicted RED | predicted GREEN |
|---|---|---|---|---|
| **K-EV1** | `eval_int16_checked`: `call check_expr_errors` → `call check_fperr_only` (`$43B8`, its documented fall-in entry point) — the **TYPE clause reverted, the FPERR clause kept**, at BOTH entry points | width | **6**: `co-str` `co-strvar` `dfe-tmonly` `dfe-tmfp` `unt-str` `cl-str` | the other **88**, and in particular `dfe-ovfdiv` `dfe-ovfsqr` `cl-ovfdiv` — **the FPERR half survives**, so the two clauses are demonstrably separate |
| **K-EV2** | `ex_width`: `call eval_byte_checked` → `call eval_byte_arg` — the **UNCHECKED twin that already ships** for `CHR$`/`LEFT$`/`RIGHT$`/`MID$`; the WIDTH site reverted, `CLEAR`'s left alone | width | **7**: `co-str` `co-strvar` `dfe-tmonly` `dfe-tmfp` `unt-str` `dfe-ovfdiv` `dfe-ovfsqr` | the other **87**, and in particular **all seven `cl-*`** — the two entry points are independent |
| **K-EV3** | `ex_clear`: `call eval_int16_checked` → `call eval_byte_checked` — the int16 stage **narrowed to a byte**, one clause of §5.3 removed | width | 🎯 **`cl-500` ONLY** (1) | the other **93**, `cl-ok` `cl-neg` `cl-70000` `cl-div0` `cl-ovfdiv` included — a byte coercion answers all five identically |
| **K-EV4** | `exf_item`: `call eval_byte_checked` → `call eval_byte_arg` — the FIELD site reverted | **both** width **and** `basic_probe_fldwidth.py --sides cf3300,zb` | width: **0, by construction** (no `FIELD` row exists here); fldwidth: the **7** string rows `s.var` `s.lit` `s.ary` `s.fn` `s.join` `m.str2` `m.trap` | width: all **94**; fldwidth: the other **36**, and in particular `d.div` (`get_byte_arg`'s own FPERR tail survives) and `o.wt` (D-FLDWIDTH §10.6's computed green) |
| **K-EV5** | `CONTROL_WANT["ctl-div0"]` made unmatchable (probe-only) | width | rc **2**, `NOT MEASURED` banner, ROMs **NOT** moved | — |

🎯 **K-EV1 AND K-EV2 ARE PARTIAL REVERTS AND THEIR RED SETS ARE NOT DISJOINT —
THE DIFFERENCE IS THE MEASUREMENT.** They share five rows (the `TMISMATCH`
family, which either cut removes). **K-EV1 uniquely reddens `cl-str`** — proof
that the shared clause really does reach `CLEAR` through the new helper.
**K-EV2 uniquely reddens `dfe-ovfdiv`/`dfe-ovfsqr`** — proof that the ORDER, not
the presence of a check, is what fixed them. Claiming disjointness here would be
claiming something false; the pair is designed as a difference, not a partition.
K-EV3 and K-EV4 are disjoint from both and from each other.

🎯 **K-EV3 IS THE ONE-ROW KNIFE, AND ITS TARGET ROW EXISTS FOR IT.** `cl-500`
(`CLEAR 500` → accepted) was added to the matrix *while drafting this table*,
because without it every `cl` row happens to answer identically through either
coercion and the byte/int16 distinction — the entire reason the helper has two
entry points — would have had **no row behind it**
([[knife-that-reddens-nothing-is-the-finding]]).

⚠️ **K-EV4's width column is a PREDICTED ZERO, not a hoped-for one.** The width
probe contains no `FIELD` statement, so a cut confined to `exf_item` cannot move
it; the hash guard separates that from "the cut never reached the artifact"
([[a-shadowed-guard-has-no-knife]]). The measurement is the **pair**.

⚠️ **The 9 positive controls have no cut**, named rather than left implied:
their subject is the trapped-readout apparatus, which this slice does not touch.

---

## 9. Denominator

See [`evalchk-msx1-characterization.md`](evalchk-msx1-characterization.md) §5.
In one line: **(WHICH deferred fault: a `1/0` → ERR 11, a `SQR(-1)` → ERR 5, a
string comparison → ERR 13, and each in an expression that is `0*`-multiplied to
contribute the fault WITHOUT contributing to the value) × (AGAINST WHAT: nothing,
an int16 overflow, another deferred fault) × (AT WHICH SITE: `WIDTH`'s
`get_byte_arg`, `CLEAR`'s `get_int16_checked`, and — measured, declined —
`LOCATE`'s written-out copy) × (WITH WHICH CONTROL: the same value with the fault
removed, the same expression shape with the fault removed, and each coercion's
two stages)**, inside D-WID's existing 79-row domain matrix so that a fix that
moved the DOMAIN while fixing the ORDER cannot pass.

**Not covered, and named rather than implied:** `WIDTH LPRINT n` (the printer
channel); the UNWIND (`abort-acceptance`); `CLEAR`'s pool semantics (D-CLP); a
`LEN=` record length (D-FLDWIDTH §6.5's residual); message WORDING; and
`LOCATE`'s own argument surface, which is why §6.6 is a decline and not a fix.

---

## 10. As-built

Implemented 2026-08-09 on `main`, based on `65171d6`.

### 10.1 What landed

* **`basic/interp.asm`** — `eval_int16_checked` (8 B) and `eval_byte_checked`
  (5 B), plus `gba_byte`, a **label only**, at the point `get_byte_arg`'s own
  `call get_int16_checked` returns.
* **`basic/screen.asm`** `ex_width` — 13 B of inline `eval` / `TMISMATCH` test /
  `get_byte_arg` → `call eval_byte_checked`.
* **`basic/clear.asm`** `ex_clear` — the same 13 B → `call eval_int16_checked`.
  (The `IF CLEARPOOL` block gained an `ELSE` arm so the never-built
  `CLEARPOOL = 0` path still evaluates its argument.)
* **`basic/field.asm`** `exf_item` — three calls → one, **behaviour-identical**.
* **`basic/missing.asm`** `loc_next` — the **comment only**: the claim that
  `get_byte_arg` "CANNOT BE CALLED here" is refuted, the −29 B carve and its
  four readings are recorded, and the decline is stated. **No code moved.**
* **`probes/basic/basic_probe_width.py`** — D-WID's 57 rows restructured from a
  two-side `run_differential` to the three-side `probe_report` shape, plus the
  `dfe` (9) and `cl` (7) batteries and two new apparatus rows. **94 rows.**

### 10.2 The walls — **and §6.3's bound was EXACT**

| region | at `65171d6` | predicted | as built |
|---|---|---|---|
| **main page 1** | 3 B | **16 B** (−13) | **16 B** ✅ |
| main low | 11 B | 11 B | **11 B** ✅ |
| sub page 0 / page 1 | 3604 / 1483 | unchanged | **3604 / 1483** ✅ |

Every one of the six cost-table rows landed on its number, and so did every
address in §6.2's layout arithmetic:

| span | predicted | `.sym` as built | |
|---|---|---|---|
| `eval_int16_checked` | `$44EF`, 8 B | `$44EF` → `$44F7` = **8** | ✅ |
| `eval_byte_checked` | `$44F7`, 5 B | `$44F7` → `$44FC` = **5** | ✅ |
| `eval_pos_arg` / `eval_byte_arg` / `get_byte_arg` / `gb_illegal` | each **+13** | `$44FC` / `$4504` / `$450A` / `$4513` | ✅ |
| `gba_byte` | `$450D` | `$450D` | ✅ |
| `ex_width` → `wid_bound` | 39 → **29** | `$592E−$5911` = **29** | ✅ |
| `ex_clear` → `clr_himem` | 44 → **34** | `$5328−$5306` = **34** | ✅ |
| `exf_item` → `exf_comma` | 67 → **61** | `$72CF−$7292` = **61** | ✅ |

Both new `jr`s landed where §6.2 computed them (−25 and +17); no branch went out
of range and the assembler was never given the chance to find one.

### 10.3 The ROM hashes — all four predicted

| ROM | at `65171d6` | predicted | as built |
|---|---|---|---|
| `basic-reloc.rom` | `f9d427e0…` | MOVES | **`06a235e1…`** ✅ |
| `sub.rom` | `accce5a1…` | **HOLDS** | **`accce5a1…`** ✅ |
| `disk.rom` | `2c630d3d…` | **HOLDS** | **`2c630d3d…`** ✅ |
| `zerobas-main-eu.rom` | `19e0ee37…` | MOVES | **`a7ede5ed…`** ✅ |

The two holds were derived rather than hoped for (§7.1): the sub build's only
dependency on main addresses is the generated
`sub/basic-resident-abi.inc`, whose 11 equates are **all below `$4000`**.

### 10.4 The gates

| gate | before | predicted | measured |
|---|---|---|---|
| **`width-acceptance`** | 91/94 | **94/94** | **94/94** ✅ |
| **`fldwidth-acceptance`** | 40/40 (2 deferred, 42 cases) | unchanged | **40/40, 2 deferred** ✅ |
| **`clearpool-acceptance`** | — | unchanged | **52/52 gated (5 never gated)** ✅ *(§10.5(c))* |
| `rowshape-check` | 18 probes | **19** (the width probe joins the contract) | **19** ✅ |
| `audit-citations` swept / basic | 766 / 201 | **768** / 201 | **768 / 201** ✅ |
| `preflight-check` | 181/86/95/95/0 | unchanged | **181/86/95/95/0** ✅ |
| `injector-check` | 348 | unchanged | **348** ✅ |
| `unit-test` · `latch-check` · `deadcode` | 59 · 16/16 · 0/0 (+1) | unchanged | **unchanged** ✅ |

`audit-citations` swept **768** exactly as the counting rule predicts — 766 plus
**two documents**; the per-language `basic` counter does not move, because the
probe this slice rewrote already existed
([[a-count-is-predicted-by-reading-its-definition]]).

### 10.5 🔴 Three things went differently

**(a) THE BLOCKER ROW WAS ALREADY GREEN, AND THE CARVE WAS A FIX.** The residual
declined this carve because folding `ex_width` onto `check_expr_errors` would
*"change `WIDTH 1/0`'s answer"*. It does not: `get_int16_checked` ends
`jp check_fperr_only`, so a deferred FPERR was **already** surfaced one step
later with the same code, and `WIDTH 1/0` read ERR 11 on both references and on
zerobas before a byte moved. 🎯 **But the row nobody had thought to write —
`WIDTH 70000+0*(1/0)`, a deferred fault AND an int16 overflow in one
expression — was a live divergence at THREE verbs**, because `fac_to_int_strict`
writes `FPERR=1` over the pending one. The decline was priced against a hazard
that did not exist while standing next to a defect that did.
**A decline is a claim about a design, and this one was measurable in nine rows.**

**(b) 🔴 THE WALK FOUND A THIRD SITE AND A FOURTH, AND THE FOURTH CARRIES A
COMMENT THAT REFUTES THIS SLICE'S OWN DESIGN.** The residual named two sites.
`grep TMISMATCH` found `ex_clear` (folded, −10 B, same divergence) and
`loc_next` — whose header states, in the file, that `get_byte_arg` **cannot** be
called from a statement handler because the abort chain "PRINTS AND RETURNS".
That was true until `4d35b6d` made `fre_abort_low` reset SP from `SAVSTK`, and
had it still been true this whole slice would have been unbuildable. **The
design's load-bearing assumption was written down as an obstacle in a file the
walk only reached by accident** ([[a-source-comment-about-the-emulator-is-a-claim]]).
The comment is corrected here; the −29 B carve underneath it is declined with
its readings taken (§6.6).

**(c) 🔴 A PREDICTED "UNCHANGED" WAS QUOTED FROM A COMMENT INSTEAD OF A GATE, AND
IT WAS STALE.** §7 first predicted `clearpool-acceptance` **51/51**, copied from
the Makefile's own header. The gate reads **52/52 (5 never gated)** — and it read
that *before* this slice too: `9a9a4c7` (D-ARRDIM) graduated `oos-dim-huge` out
of the never-gated `arr` battery months ago, exactly as that probe's comment
said it would, and the Makefile header was never updated. Nothing regressed and
nothing improved; a number was carried forward instead of measured
([[a-prediction-copied-into-the-result-column]]). The prediction is now stated as
*"unchanged"* rather than as a figure, which is the claim the slice can actually
make. **The same mistake nearly reached `fldwidth-acceptance`**, where §7's first
draft said 41/41 on the strength of a row this slice considered adding and did
not.

### 10.6 Knives — 5 cuts × 2 rounds, **ALL TWELVE EXACT, both rounds identical**

| # | cut | instrument | predicted RED | measured | |
|---|---|---|---|---|---|
| **K-EV1** | `eval_int16_checked`: `check_expr_errors` → `check_fperr_only` | width | 6 | **exactly those 6** | ✅ ×2 |
| **K-EV2** | `ex_width`: `eval_byte_checked` → `eval_byte_arg` | width | 7 | **exactly those 7** | ✅ ×2 |
| **K-EV3** | `ex_clear`: `eval_int16_checked` → `eval_byte_checked` | width | 🎯 **`cl-500` ONLY** | **exactly that 1** | ✅ ×2 |
| **K-EV4** | `exf_item`: `eval_byte_checked` → `eval_byte_arg` | width **and** fldwidth | **0** / **7** | **0 of 94** and **exactly those 7 of 42** | ✅ ×2 |
| **K-EV5** | `CONTROL_WANT["ctl-div0"]` unmatchable, probe-only | width | rc 2, ROMs unmoved | **rc 2 + `NOT MEASURED`, ROMs held** | ✅ ×2 |

🎯 **THE TWO PARTIAL REVERTS ARE WHERE THE PROOF IS, AND IT IS IN THEIR
DIFFERENCE RATHER THAN IN A PARTITION.** K-EV1 and K-EV2 share five rows — the
`TMISMATCH` family, which either cut removes — and §8 said so instead of
claiming disjointness:

* **K-EV1 uniquely reddens `cl-str`**, and nothing else does. That is the shared
  clause demonstrably reaching `CLEAR` *through the new helper*: `ex_clear` has
  no `TMISMATCH` test of its own any more.
* **K-EV2 uniquely reddens `dfe-ovfdiv`/`dfe-ovfsqr`**, and K-EV1 leaves them
  green. So what fixed them is the **order**, not the presence of a check — the
  FPERR half of `check_expr_errors` survives K-EV1 intact and the rows still
  move under K-EV2. No single row can say that; the pair can.
* **K-EV3 reddens exactly one row**, and that row exists *because the knife was
  drafted first*: without `cl-500`, every `cl` row answers identically through
  either coercion, and "the helper needs two entry points" — §5.3, the reason
  `ex_clear` is not simply routed through the byte leaf — would have had **no
  row behind it** ([[knife-that-reddens-nothing-is-the-finding]]).
* **K-EV4 is a PREDICTED ZERO on one instrument and exactly 7 on another.** The
  width probe contains no `FIELD` statement, so a cut confined to `exf_item`
  cannot move it; the four-ROM hash guard is what separates that from "the cut
  never reached the artifact". Its fldwidth red set is D-FLDWIDTH's own K-FW1
  set, reproduced through a different call graph — and `d.div` and `o.wt` stayed
  green there, as that slice computed.

⚠️ **The hang question was asked of every cut before any of them ran.** A dead
machine scores `<none>` on every trapped row and `<no echo>` on every `unt` row,
i.e. **all 94 red** — indistinguishable from a spectacular cut. No cut here can
hang (each swaps one `call` operand for another into a routine that terminates;
D-FLDWIDTH's `cp $00` line-terminator trap has no analogue), so the runner
**aborts** on an all-red set rather than scoring it. It never fired.

⚠️ **The 9 positive controls have no cut**, named rather than left implied:
their subject is the trapped-readout apparatus, which this slice does not touch.

### 10.7 Corpus

Sequentially from clean (`rm -rf build` + `make repack-machine`, **bash** —
`zsh` does not word-split `make $t`), **35 targets, all rc=0, 20 min 55 s wall**
(1255 s): the 33 of [`spec-basic-fldwidth.md`](spec-basic-fldwidth.md) §10.7 —
`unit-test` **59** · `audit-citations` CLEAN (**768** swept, basic **201**) ·
`preflight-check` **181/86/95/95/0** · `injector-check` **348** ·
`rowshape-check` **19** probes · `latch-check` **16/16** · `deadcode`
**0/0 (+1)** · `lnblank-acceptance REPEAT=2` · `lnblank-say-acceptance`
**204/204** · `logicops-acceptance` **193/193** · `float-acceptance` ·
`linemax-acceptance` **60/60** · `dexp5-pin` **16** · `editverb-acceptance`
**61/61** · `lptverb-acceptance` **44/44** · `dskmsg-acceptance` **5/5** ·
`diskbasic-acceptance` **34/34** verbs · `fat-error-acceptance` ·
`runtail-acceptance` **9/9** · `castail-acceptance` **31/31** ·
`cassave-acceptance` **20/20** · `readvar-acceptance` **24/24** ·
`arylv-acceptance` **18/18** · `inputary-acceptance` **7/7** ·
`lvfix-acceptance` **18/18** · `fldary-acceptance` **13/13** ·
`lrvar-acceptance` **21/21** · `forvar-acceptance` **33/33** ·
`nxlist-acceptance` **25/25** · `nxary-acceptance` **22/22** ·
`tgtspc-acceptance` **28/28** · `namspc-acceptance` **58/58** ·
`fldwidth-acceptance` **40/40** (2 deferred, 42 cases) — **plus the two gates
this slice touches**: `clearpool-acceptance` **52/52** gated (5 never gated) and
**`width-acceptance` 94/94** (94 cases, 9 positive controls, 7 rows with one
reference only, **0 rows where the references disagree**).

⚠️ **THE TWO ADDED TARGETS ARE THE POINT OF COPYING THIS LIST FORWARD RATHER
THAN THE LAST ONE.** A runner rebuilt from D-FLDWIDTH's 33 omits
`width-acceptance` — the gate this slice moves — and `clearpool-acceptance`,
whose verb this slice edits. That is the standing warning applied, not restated.

⚠️ `latch-check` still has **no `repack-machine` prerequisite**, so the script
builds explicitly before the loop; and `lnblank-acceptance` **defaults to
`REPEAT=1`**, so the `REPEAT=2` is passed by hand.

### 10.8 The fix, as a program

Every cell below is a **LITERAL screen row** read after `RUN` — not the
battery's canonicalised `ERR` code, which is a different reading. The zerobas
"before" column comes from a **rebuilt pre-fix ROM** (`basic-reloc.rom
f9d427e0…`, hash checked), the "after" from the shipped one (`06a235e1…`), and
both reference columns were measured on the machines themselves.

**The row the decline was written about — and it never moved:**

```basic
10 WIDTH 1/0
```

| | screen after `RUN` |
|---|---|
| VG-8020 · CF-3300 | `Division by zero in 10` |
| zerobas **before** → **after** | `Division by zero in 10` → **`Division by zero in 10`** |

🎯 **This is the whole residual, and it was already right.** `get_int16_checked`
tails into `check_fperr_only`, so the deferred fault was surfaced by the
coercion. Nothing had to be measured to keep it working — but measuring it is
what made the next two programs findable.

**The row nobody had written:**

```basic
10 WIDTH 70000+0*(1/0)
```

| | screen after `RUN` |
|---|---|
| VG-8020 · CF-3300 | `Division by zero in 10` |
| zerobas **before** → **after** | `Overflow in 10` → **`Division by zero in 10`** |

**…and its twin, because a second fault class gives a DIFFERENT code:**

```basic
10 WIDTH 70000+0*SQR(-1)
```

| | screen after `RUN` |
|---|---|
| VG-8020 · CF-3300 | `Illegal function call in 10` |
| zerobas **before** → **after** | `Overflow in 10` → **`Illegal function call in 10`** |

🎯 **One `Overflow` becoming two different messages is the rule.** Had only the
first program been measured, *"division by zero is special"* would fit the
evidence exactly as well ([[one-row-cannot-separate-two-rules]]). The control
that says where the `Overflow` legitimately comes from is the same value with
the fault taken out — `10 WIDTH 70000` reads `Overflow in 10` on all three
machines, before and after.

**…and the same rule at the second site, which is a different verb entirely:**

```basic
10 CLEAR 70000+0*(1/0)
```

| | screen after `RUN` |
|---|---|
| VG-8020 · CF-3300 | `Division by zero in 10` |
| zerobas **before** → **after** | `Overflow in 10` → **`Division by zero in 10`** |

`WIDTH` coerces to a byte and `CLEAR` to an int16, which is why the helper has
two entry points — and why `10 CLEAR 500` must stay silent on all three machines
(it does, and knife K-EV3 is the one-row proof).
