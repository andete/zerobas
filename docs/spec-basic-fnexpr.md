<!-- Copyright (c) 2026 Joost Yervante Damad — SPDX-License-Identifier: 0BSD -->

# A filename argument is a string EXPRESSION — the raising half

**D-FNEXPR, 2026-08-21**, on `main`, based on `3704e24` (D-FNFUND, the carve that
funded it). Closes the RAISING half of the `TODO.md` residual ranked **first** by
the 2026-08-21 gap sweep as real BASIC surface: `OPEN` / `KILL` / `NAME` now take
any string expression where the filename goes, exactly as both references do.

Characterization this implements:
[`fnarg-msx1-characterization.md`](fnarg-msx1-characterization.md) (D-FNARG,
14 rows) and [`fnarg2-msx1-characterization.md`](fnarg2-msx1-characterization.md)
(D-FNARG2, the four remaining verbs).

⚠️ **ONE REFERENCE.** Every row is Disk BASIC; a diskless Philips VG-8020 cannot
express the question and reads `<NO DISK ON THIS SIDE>` rather than a value.
Every reading rests on the National CF-3300.

---

## 1. The rule, and what this slice closes

> **Wherever the reference accepts a filename it accepts a string EXPRESSION.
> zerobas accepted a STRING LITERAL and nothing else.**

Seven verbs diverged. This slice closes the three that **RAISE** — `OPEN`,
`KILL`, `NAME` — and deliberately leaves the `load error` family
(`SAVE`/`LOAD`/`BLOAD`) and `FILES` open, because those are a **different
mechanism**, not leftover scope: `load_error` prints and *returns*, so there is
no error to raise and the program runs on (D-FNARG2 §4.2).

> ✅ **CLOSED THE SAME DAY BY D-FNEXPR2**,
> [`spec-basic-fnexpr2.md`](spec-basic-fnexpr2.md) — and 🔴 **the "different
> mechanism" reason above was already out of date when it was written.**
> D-LOADERR-FIX and D-BLNF had retired the printed `load error` at `LOAD` and
> `BLOAD` on 08-20/08-21; re-read from clean, `f.loadlit` and `f.bloadlit`
> already agreed. What remained at all four verbs was the ARGUMENT SHAPE — this
> slice's own rule — and the fix RECOVERED 36 B rather than spending any.

**Thirteen deferred rows graduated to ordinary scored rows.** `namspc-acceptance`
deferred count 23 → 10.

| row | statement | cf3300 | zb before | zb after |
|---|---|---|---|---|
| `f.lit` 🟢 | `OPEN"FA1.DAT"AS #1` | `OK` | `OK` | `OK` |
| `f.var` | `OPEN A$ AS #1` | `OK` | **Syntax error** | **`OK`** ✅ |
| `f.expr` | `OPEN A$+".DAT" AS #1` | `OK` | **Syntax error** | **`OK`** ✅ |
| `f.inlit` 🟢 | `OPEN"FA5.DAT"FOR INPUT AS #1` | `OK` | `OK` | `OK` |
| `f.invar` | `OPEN A$ FOR INPUT AS #1` | `OK` | **Syntax error** | **`OK`** ✅ |
| `f.outvar` | `OPEN A$ FOR OUTPUT AS #1` | `OK` | **Syntax error** | **`OK`** ✅ |
| `f.appvar` | `OPEN A$ FOR APPEND AS #1` (missing) | `File not found` | **Syntax error** | **`File not found`** ✅ |
| `f.applit` 🟢 | `OPEN"FB1.DAT"FOR APPEND AS #1` | `File not found` | `File not found` | `File not found` |
| `f.appvarx` | `OPEN A$ FOR APPEND AS #1` (exists) | `OK` | **Syntax error** | **`OK`** ✅ |
| `f.killlit` 🟢 | `KILL"FA9.DAT"` | `OK` | `OK` | `OK` |
| `f.killvar` | `KILL A$` | `OK` | **Syntax error** | **`OK`** ✅ |
| `f.namelit` 🟢 | `NAME"FAB.DAT"AS"FAC.DAT"` | `OK` | `OK` | `OK` |
| `f.namevar` | `NAME A$ AS B$` | `OK` | **Syntax error** | **`OK`** ✅ |

The five 🟢 literal controls are load-bearing in both directions: without them
"zerobas cannot do disk I-O at all" reads the after-column just as well.

---

## 2. 🔴 The filed price named the wrong unit, and this was WALKED

`TODO.md` priced the fix as *"one mechanism at **11 `parse_disk_fcb` call
sites**"*, needing *"a SECOND SOURCE for a shared parser plus a staging
buffer — a design question, not an edit."*

**The 11 sites are real and are not the change surface.** The sites that refuse
an expression are the **quote gates**, and walking them found ~13 opening and
~5 closing gates across five files with **six different error faces**
(`stmt_error`, `load_error`, `oo_synerr`, `bl_load_error`, `df_nofilespec`, and
`RUN`'s bare-`RUN` fallthrough, which is genuinely ambiguous with `RUN <lineno>`).

> 🔴 **"GENUINELY AMBIGUOUS" IS REFUTED — D-FNEXPR2 §1.2.** That is a claim about
> the token stream, and the `t.*` instrument reads the stored line bytes:
> `1 RUN 30` stores `8a 20 0e 1e 00 00` and `1 RUN A$` stores `8a 20 41 24 00`,
> byte-identical on vg8020, cf3300 and zb. `$0E` is `LINENO_TOKEN` and the
> tokeniser emits it for the line-number form and nothing else, so a parser that
> tests for `$0E` first is not guessing. The decline stands for now — RUN is a
> separate edit with its own knife — but it is **priced at ~+17 B against a
> 50 B wall**, not blocked.

🎯 **AND `parse_disk_fcb` NEEDS NO SECOND SOURCE.** It walks `(HL)` until a `"`
and is already source-agnostic, so pointing it at a staged buffer instead of the
token stream costs **zero bytes and zero edits**. That matters more than the
byte count: [`basic/pdfcb-body.inc`](../basic/pdfcb-body.inc) is included in
**three** places byte-identically, one of them the sub-ROM tenant, so a second
source would have been the expensive part of the filed design and it was never
needed.

🎯 **A STRING LITERAL IS ITSELF A STRING EXPRESSION**, so `str_eval` serves both
and there is no dual path: `OPEN"X.DAT"` and `OPEN A$` now take one route.

---

## 3. The change

**`fname_expr`** ([`basic/files.asm`](../basic/files.asm)), **34 B**, plus **8 B
recovered** at the six sites it replaces — the gates it removes are longer than
the calls that replace them.

```
fname_expr:     call    str_eval        ; STRPTR -> [len][ptr]; HL past the expr
                jp      nc,stmt_error   ; not a string operand
                ld      (FN_RESUME),hl  ; where the statement resumes
                ... copy the body to STRSCR+1, append '"', return HL = STRSCR+1
```

**`FN_RESUME` = `$E227`** — the two bytes `LOC_RET` occupied, freed by D-LOCPARK
**one day earlier** and deliberately left NAMED rather than silently reused
*"because the next cell that wants them should know what was here."* That is
exactly how they were re-let. ⚠️ It is **not** a saved return address: nothing
`ret`s through it and no stack depth depends on it.

### 3.1 The six sites

| # | site | before | after |
|---|---|---|---|
| 1 | `do_open` gate | `cp '"'` / `jr nz,oo_synerr` / `inc hl` | `call fname_expr` |
| 2 | `do_open` disk resume | `inc hl` | `ld hl,(FN_RESUME)` |
| 3 | `oodv_fn` exit (LPT:/CRT:) | falls through | `ld hl,(FN_RESUME)` |
| 4 | `oo_dev_cas` resume | quote check + `inc hl` | `ld hl,(FN_RESUME)` |
| 5 | `do_kill` gate + resume | `cp '"'` / `jp nz` / `inc hl` … `inc hl` | `call fname_expr` … `ld hl,(FN_RESUME)` |
| 6 | `do_name` both operands | two gates, two `push`/`pop` cursor guards | two `call fname_expr`, **no guards** |

`do_name` gets *cheaper* than the others because the cursor now lives in
`FN_RESUME`, so three exits (`nm_fail`, `nm_fail2`, `nm_notfound`) each shed a
`pop hl` that existed only to balance a guard.

### 3.2 ⚠️ The device dispatch now runs on the STAGED copy

`dev_cmp` against `LPT:`/`CRT:`/`CAS:` reads `STRSCR+1`, not program text. This
is the faithful behaviour — `OPEN A$ AS #1` with `A$="CAS:X"` should reach the
tape arm exactly as the literal does — but it is a **behaviour claim**, so it is
measured (`d.opendev`, `d.savedev`, `f.var`, plus `cassave`/`castail` unmoved),
not asserted.

### 3.3 ⚠️ The non-string face is UNCHANGED and is a FILED QUESTION

`OPEN 5 AS #1` was `Syntax error` because a non-quote failed `cp '"'`. It is
`Syntax error` still: `str_eval` returns CF clear on a numeric operand and
`fname_expr` jumps to the same `stmt_error` that `oo_synerr` trampolines to. The
reference may answer `Type mismatch` — `PLAY`'s own string operand does — but
**that is unmeasured**, so today's face is preserved rather than guessed at.

> ✅ **MEASURED 2026-08-21 (D-FNEXPR2 §2), AND THE GUESS THIS DECLINED TO MAKE
> WAS THE RIGHT ONE.** `OPEN 5 AS #1` / `KILL 5` / `SAVE 5` / `LOAD 5` /
> `BLOAD 5` / `FILES 5` are **`Type mismatch`** on the CF-3300 — one face at all
> six verbs. 🔴 **But it is not the whole rule, which is why declining to guess
> was still correct:** `SAVE 1/0` and `OPEN 1/0 AS #1` are **`Division by
> zero`** — the reference EVALUATES the operand and the operand's own fault
> wins. A blanket "non-string → ERR 13" would have matched the six rows this
> paragraph anticipated and been wrong on the two it did not. The exit is
> `els_tc_common` now (D-MISS-1's tail), at **zero bytes**.

### 3.4 ⚠️ STRSCR is a shared scratch, and the second-tenant argument is stated

Its other tenant is `read_into_strscr` (`INPUT#` / `LINE INPUT#`). A filename
parse happens at a **statement head**; `read_into_strscr` runs **inside** an
already-open `INPUT#`. They cannot nest.

🔴 **`do_name`'s SECOND operand is the one place the staged copy must survive a
disk primitive**, and it holds **by address, not by luck.** The only writer into
STRSCR's span during a disk primitive is DSKIO's FDC work area `$E29A..$E29F`
(`basic/sysvars.inc`'s cross-component overlap invariant) — that is
**STRSCR+45..+50**, and a name long enough to reach it is 45+ characters, which
`build_83_name`'s 8.3 rule refuses. The bytes that can ever be read back are the
first 14 at most: **30 bytes of margin.**

🎯 And the self-overlap is benign rather than unconsidered: `OPEN INPUT$(2,#1)`
has `str_eval` fill STRSCR itself, so `RVDESC.ptr` **is** `STRSCR+1` and the
`ldir` runs with `HL == DE`, copying each byte onto itself.

---

## 4. 🔴 `f.paren` did NOT close, and it is not this rule

`OPEN(A$)AS #1` is still `Syntax error` here and `OK` on the CF-3300 — the one
row of fourteen the fix left red, **predicted before the run** from reading
`str_eval_one`, which dispatches on `"`, on the string-function tokens and on a
letter, and has **no parenthesised-subexpression case**.

Measured afterwards, with two green controls, and it is not a filename question
at all:

| statement | cf3300 | zb |
|---|---|---|
| `B$=(A$)` | `Q` | **`Type mismatch`** |
| `PRINT (A$)` | `Q` | **`Type mismatch`** |
| `B$=A$` 🟢 | `Q` | `Q` |
| `B=(A)` 🟢 **numeric** | ` 5 ` | ` 5 ` |

🎯 **Parentheses work for numbers; it is the STRING evaluator that has no `(`
case.** `(A$)` is refused in *every* string context. Charging that to the
filename gate would price a string-evaluator hole against the wrong verb, so
`f.paren` stays deferred with a corrected reason and is filed as its own
residual. ⚠️ Its face is context-dependent too (`Type mismatch` in LET/PRINT,
`Syntax error` through `fname_expr`), so it cannot even be scored on the face
until the evaluator is the subject.

---

## 5. Cost

Measured from clean, never counted:

| wall | at `3704e24` | after | delta |
|---|---|---|---|
| main page 1 | 40 B | **14 B** | **+26 B** |
| page-0 low | 22 B | 22 B | 0 |
| sub page 0 | 3299 B | 3299 B | 0 |
| sub page 1 | 1615 B | 1615 B | 0 |

`sub.rom` is byte-identical (`d4427e18`) — a page-1 main edit leaves the
generated resident ABI alone. The hand count was 34 B of helper less 8 B
recovered at the sites, i.e. +26 B: **exact**, and checked against the wall
rather than believed.

---

## 6. The knives, and the two things they found that the gate could not

Three claims, three narrow predictions written before the runs. **One was exact,
one missed on the denominator, and one exposed a blindness in the rows this slice
had just shipped.**

| knife | cut | predicted | measured |
|---|---|---|---|
| **K-FE1** | the `'"'` `fname_expr` appends → `$01` | all 15 red | **12 red** — §6.1 |
| **K-FE2** | `do_kill`'s `ld hl,(FN_RESUME)` → `ld hl,(STRPTR)` | `f.killlit` + `f.killvar` | **those two AND `d.opendev`** — §6.2 |
| **K-FE3** | `call str_eval` → `call str_eval_one` (drops the concat tail) | exactly `f.expr` | **exactly `f.expr`** ✅ EXACT |

**K-FE3 is the clean one and it is the load-bearing one:** dropping
`str_concat_tail` reddens `A$+".DAT"` and *nothing else* — so `f.expr`, the row
that rules out the cheap "accept a bare string variable" fix, is pinned by
exactly the code that makes it pass.

### 6.1 🔴 K-FE1 reddened ONE row of fifteen, and the readout was why

First run: `f.lit` scored **green** with the terminator destroyed. The screen:

```
ZBRUN
load error
[OK]
```

`parse_disk_fcb`'s reject reaches `bl_load_error`, which **prints and RETURNS** —
no ERR code, no line number, no `ON ERROR`, and the program runs on to print its
`[OK]` **underneath** the message. `bracket()` looks for `[` before it looks for
an error, so **thirteen rows scored green while the machine was refusing every
filename** [[readout-blind-to-its-own-subject]].

🎯 **D-FNARG2 FOUND THIS EXACT CLASS AND FIXED IT — FOR THE OTHER FOUR VERBS.**
`errface()` exists *because* of it. Fixing `SAVE`/`LOAD`/`BLOAD`/`FILES` and
leaving `OPEN`/`KILL`/`NAME` on `bracket()` is guarding one instance of a class
and calling the class guarded. All fourteen `f.*` rows are `dskerr`/`errface`
rows now; **the healthy readings are unchanged** (`errface` returns the `[...]`
span when there is no error), so this is a coverage fix, not a rescoring —
`namspc-acceptance` is 75/75 before and after.

**Re-run with the error-first readout: 12 of 15 red.** The three that stayed
green stayed green for three *different* reasons, and only one of them is an
apparatus fault:

* 🔴 **`f.appvar` and `f.applit` AGREE FOR THE WRONG REASON.** Both expect
  `File not found` (an `APPEND` on a file that does not exist) — and a rejected
  filename raises `File not found` too. The knife's face and the row's expected
  face **coincide**, so the row cannot tell a refused parse from a missing file.
  *A case that agrees can agree for the wrong reason*, live.
* ✅ **`d.savedev` is correctly green**: `SAVE` goes through `do_save`, which
  this slice does **not** convert. It is a row about the other half, and a knife
  in `fname_expr` must not touch it.

### 6.2 K-FE2 reddened three, not two — a miss in the DENOMINATOR

Predicted `f.killlit` + `f.killvar`; measured those two **and `d.opendev`**,
whose third line is `KILL"CRT.DAT"`. The row built to *read around* the device
dispatch necessarily reads *through* `do_kill`. The mechanism was predicted
correctly; the row list was not.

### 6.3 🔴 K-FE3's FIRST RUN NEVER CUT, and the guard is what said so

`call str_eval` → `call str_eval_one` produced a ROM **byte-identical to the
baseline** (`257af791`), though the symbols plainly differ (`$4988` vs `$498F`).
`make` had judged the tree up to date: the source write landed in the same mtime
tick as the previous restore's artifacts, so the knife was scored **on the
previous machine** — and it would have read as "reddens nothing", i.e. as a
shadowed guard. The runner's `assert h != BASE` caught it.

Same family as the `shutil.copy2` trap the operating rules already carry, one
step further out: it is not enough to restore by *writing* the bytes if `make`
can still decide nothing changed. The runner now does `rm -rf build` before every
build, and K-FE3 then cut (`686b2490`) and scored exactly as predicted.

**Before believing a knife that reddens nothing, check that it CUT.**
