# D-LOCARG — a −29 B carve in `loc_next`, and the +7 B `DIRECTF` derive it funds

*Landed 2026-08-09. Measured in
[`locarg-msx1-characterization.md`](locarg-msx1-characterization.md), 45 rows,
three sides, both references agreeing on every one.*

Two filed residuals, one slice, because one pays for the other:

* [`spec-basic-evalchk.md`](spec-basic-evalchk.md) §6.6 priced a **−29 B** carve
  in `loc_next` ([`basic/missing.asm`](../basic/missing.asm)) and declined it
  for want of a denominator;
* [`spec-basic-onerr0.md`](spec-basic-onerr0.md) §7 priced a **+7 B** `DIRECTF`
  derive at **+7 B against a 0 B wall** and deferred two measured rows.

Main page 1 was at **0 B free**. −29 + 7 = **−22**, and it lands at **22 B**.

---

## 1. The two readings, taken before anything was designed

```basic
10 LOCATE 70000+0*(1/0),3
```

| side | before |
|---|---|
| VG-8020 · CF-3300 | `Division by zero in 10` |
| zerobas | `Overflow in 10` |

```basic
10 ON ERROR GOTO 30
20 END
30 ON ERROR GOTO 0
40 PRINT"[RANON]"
RUN
ERROR 7
```

| side | before |
|---|---|
| VG-8020 · CF-3300 | `Out of memory` |
| zerobas | `Out of memory in 0` |

## 2. What is wrong, in two sentences

`loc_next` writes its own two-stage domain check out in full, and `FPERR`'s
overflow store lands **on top of** a pending deferred fault, so the coercion's
complaint outranks the expression's — the clause D-EVALCHK fixed at three other
verbs and could not reach here.

`oe_reraise` restores the erroring statement's `CURLINE` and aborts through
`rerr_msg`, which never passes `rp_exec` — the only place that **derives**
`DIRECTF` — so the report carries the *re-raising* statement's mode.

## 3. Scope

### 3.1 The carve is the DOMAIN CHECK, not the apparatus

`loc_next` parks its return address in `LOC_RET` and runs `eval` /
`raise_error` at the statement handler's own stack depth. **That stays.** Only
the 29 bytes of hand-written coercion become `call eval_byte_checked`. The park
is what keeps `loc_more`, the apply-then-reject ordering and `loc_missing` at
handler depth; deleting it too is a separate ~9 B carve with a separate claim,
filed rather than ridden along.

### 3.2 🔴 The claim the carve rests on was already refuted, and the apparatus is still MEASURED

The block's header said `get_byte_arg` *"CANNOT BE CALLED here"* because the
abort chain "PRINTS AND RETURNS". `4d35b6d` (D-CUR-D) retired that:
`fre_abort_low` does `ld sp,(SAVSTK)` before it prints and `raise_error_hl`'s
trap arm always did, so aborts are **depth-independent**.

A refuted claim is not the same as an unmeasured one. The eleven `u.*` rows of
`make locarg-acceptance` run every abort class **untrapped** and read the whole
screen tail, so the exact failure the header warned about — `LOCATE "5",3`
printing `Type mismatch` and then `Missing operand` — is a red row. All eleven
are green on all three sides through the new `call`.

### 3.3 What the slice does NOT touch

* **`check_expr_errors`' internal order.** Its TMISMATCH-before-FPERR is
  D-EVALCHK §5.1's forced constraint. `t.tmfp` refutes it (§7), and it does not
  move here.
* **`LOCATE`'s positions, clamps and read-back.** `make missing-acceptance`,
  214 rows, unchanged before and after.
* **`RESUME` in any form.** §5.2 declines a cheaper design precisely because it
  would reach the RESUME path.

## 4. Design — the carve

```
                call    eval_byte_checked   ; A = E = 0..255, or aborts
                scf
                jr      loc_ret
```

`eval_byte_checked` (basic/interp.asm) is `eval` → `check_expr_errors` →
`get_int16_checked` → `gba_byte`: exactly the two-stage rule LOCATE wrote out,
with the deferred-error test **in front of** the coercion instead of behind it.
`get_byte_arg` already returns `A = E`, so the `ld a,e` the inline block ended
with is absorbed too, and `loc_illegal` is orphaned (`gb_illegal` raises the
same ERR 5 from inside the leaf).

## 5. Design — the derive

`rp_exec`'s six-instruction derive becomes a routine, called from both places:

```
derive_directf:
                ld      a,(CURLINE+1)
                cp      dir_line >> 8
                ld      a,0                 ; (xor a would clobber the flags)
                jr      nz,dd_mode
                inc     a
dd_mode:
                ld      (DIRECTF),a
                ret
```

🎯 **A CONSTANT IS REFUTED BEFORE IT IS WRITTEN.** The two deferred rows fail in
**opposite** directions — `d.instop` wants the suffix printed, `d.dirtrap` wants
it suppressed — so `DIRECTF := 0` fixes one and breaks the other. Knife K-LA3
falsifies the constant live by turning `inc a` into `nop`.

### 5.1 🔴 WHERE THE ROUTINE SITS IS A PRICE, NOT A TIDINESS QUESTION

The first placement — between `jr rp_exec` and `rp_resume:`, next to its main
caller — **did not assemble**: *`ERROR: Relative jump out of range on line 536`*.
Inserting 14 B inside the run loop pushed the backward `jr rp_lp` at the
fall-through-to-the-next-line tail past −128. That is the identical failure
D-CONTR recorded **two instructions below the same span**, whose remedy was
`jr` → `jp` at +1 B.

Moving the routine **out of the span** (below `rp_goto`'s `jp rp_lp`) costs
**0 B** and assembles. The D-CONTR remedy would have cost 1 of the 22 bytes this
slice is delivering. The assembler caught it, which is the same reason D-CONTR
gives for why nothing ever ran on a stale ROM.

### 5.2 💰 A CHEAPER DESIGN AT +3 B, DECLINED WITH NUMBERS

`res_ctx` (basic/interp.asm) ends `ld hl,(ERRRESUME+2)` / `ret`, and both of the
re-raise's needs are already met by it. Letting `res_ctx` **fall through** into
`derive_directf` would give `oe_reraise` the derive for **0 B at the site** and
delete `res_ctx`'s own `ret`:

| | +7 design (built) | +3 design (declined) |
|---|---|---|
| routine | +14 | +14 |
| `res_ctx`'s `ret` absorbed | — | −1 |
| `rp_exec` (−13 inline, +3 call) | −10 | −10 |
| `oe_reraise` | +3 | 0 |
| **total** | **+7** | **+3** |

**Declined for the 4 bytes it does not buy.** `res_ctx`'s other caller is
`res_same` (`RESUME` / `RESUME 0`), which **returns into the run loop** rather
than aborting. The extra derive would run there with `CURLINE` already swapped
to the erroring line, and whether any statement executes between that `ret` and
`rp_exec`'s own re-derive is **not measured by any row in this tree** —
`onerr0-acceptance` has three RESUME rows, which is a control set, not a
denominator. 4 B against a −22 B net does not buy a claim that cannot be scored.
Recorded so it is not re-derived.

## 6. The cost — measured, not estimated

| part | bytes |
|---|---|
| `loc_next`: `call eval` + the `TMISMATCH` test | −10 |
| `loc_next`: the inline two-stage coercion (incl. its `ld a,e`) | −17 |
| `loc_illegal`, orphaned | −5 |
| `loc_next`: `call eval_byte_checked` | +3 |
| **the carve** | **−29** |
| `rp_exec`: the inline derive | −13 |
| `rp_exec`: `call derive_directf` | +3 |
| `derive_directf` (13 B of derive + `ret`) | +14 |
| `oe_reraise`: `call derive_directf` | +3 |
| **the derive** | **+7** |
| **net, main page 1** | **−22** |

**Hand-counted before the build, and EXACT: page 1 free 0 B → 22 B.**
Low region 11 B, sub page 0 3604 B, sub page 1 1483 B — all unchanged.

## 7. 💰 DEFERRED with a price: `t.tmfp`

| row | zerobas | both references |
|---|---|---|
| `t.tmfp` — `LOCATE STR$(1/0),3` | ` 13  4  7 ` | ` 11  4  7 ` |

A numeric fault (`FPERR` = 11) and a type fault (`TMISMATCH`) are both pending
at the coercion; the references report the numeric one. Unmoved by the carve —
the order is the same before (`loc_next`'s own inline `ld a,(TMISMATCH)`) and
after (`check_expr_errors`).

💰 **The price is +7..+9 B and is NOT the reason.** `check_expr_errors` and
`check_fperr_only` are one routine with two entry points, the second a
**fall-in**, which is what makes the pair cost nothing extra; testing `FPERR`
first breaks the fall-in and needs that test written twice.

🔴 **The reason is the denominator.** `check_expr_errors` has four other callers
— `ex_if`, `exp_num` (print.asm), `ex_let`, and `eval_chan` since D-BADFNUM,
whose own header records that its ordering was **changed on a measurement** —
and the order may not move until each has a both-flags-pending row of its own.
D-EVALCHK §5.1 froze this order as a forced constraint on the strength of
`PRINT #A$,"X"`: a row with a type fault and **no** pending numeric one, which
cannot discriminate. **A constraint can be frozen by a row that does not test
it.** Filed in `TODO.md`.

## 8. Knives

Six cuts, each byte-neutral, each run **twice**, on `--sides zb` only (a cut in
zerobas can only move zerobas). Predictions were written before the runner was
started, and the misses below are **not** back-filled.

| # | cut | gate | predicted RED | measured | |
|---|---|---|---|---|---|
| **K-LA1** | `loc_next`: `eval_byte_checked` → `eval_byte_arg` | locarg + onerr0 | 6 | **11** — those 6 **plus** 5 type rows | ❌ ×2 |
| **K-LA2** | `loc_next`: `eval_byte_checked` → `eval_int16_checked` | locarg | 11 | **37** | ❌ ×2 |
| **K-LA3** | `derive_directf`: `inc a` → `nop` (force `DIRECTF := 0`) | onerr0 + locarg | 2 | 🎯 **exactly 1: `d.dirtrap`** | ❌ ×2 |
| **K-LA4** | `oe_reraise`: `call derive_directf` → `call res_ctx` | onerr0 + locarg | 2 | **exactly `d.instop` + `d.dirtrap`** | ✅ ×2 |
| **K-LA5** | `loc_next`: `scf` → `nop` (every accept reads as OMITTED) | locarg | 7 | **34**, and `t.zero` did **not** move | ❌ ×2 |
| **K-LA6** | `eval_int16_checked`: `check_expr_errors` → `check_fperr_only` | locarg | 5 | **exactly those 5** | ✅ ×2 |

**4/12 exact — and every one of the six knives gave byte-identical red sets in
both rounds**, which is the stability result D-FEVERB's K-FE1 exists to demand.
**No miss is the tree behaving unexpectedly; every one is a prediction that was
too narrow, and two of them are worth more than the exactness would have been.**

### 8.1 🎯 K-LA1'S MISS IS WHAT PRODUCED K-LA6, AND THE PAIR IS THE PROOF

K-LA1's prediction was written as *"drop the DEFERRED-error test only"*. That is
not what the cut does: `eval_byte_arg` differs from `eval_byte_checked` by the
**whole** of `check_expr_errors` — the `TMISMATCH` test *and* the `FPERR` test.
So it reddened the five type rows (`t.c.str`, `t.r.str`, `t.u.str`, `u.str`,
`t.tmfp`) as well, and could not say which half answers which row.

**K-LA6 was written to make that partition and did**, first time, both rounds:
dropping the type half **alone** reddens exactly those five and leaves all six
deferred-rank rows green.

🎯 **Read together, the two cuts say something no single row can.** LOCATE's
`Type mismatch` answers now arrive **through the shared leaf** — the carve
deleted `loc_next`'s own `ld a,(TMISMATCH)` and nothing local replaced it, which
K-LA6 demonstrates by reaching those rows from `basic/interp.asm`. And the six
deferred-rank rows survive K-LA6 intact while moving under K-LA1, so what fixed
them is the **order** of the two tests, not the presence of either
([[the-existing-split-is-cheaper-than-a-new-guard]]).

### 8.2 🎯 K-LA3 REDDENS EXACTLY ONE ROW, AND THAT ROW IS THE WHOLE OF §5

The prediction named `d.dirtrap` **and** `d.direrr`. Only `d.dirtrap` moved, and
the miss is instructive: `d.direrr`'s report (`No RESUME in 30`) is raised from
inside a handler on a **stored** line, where `DIRECTF` is 0 already — forcing 0
cannot change it. So the constant-`0` design is falsified by **one** row and
only one, which is precisely the claim §5 makes and exactly as small as it
should be.

### 8.3 🔴 K-LA5 IS A WEAK KNIFE, AND ITS OWN RED SET SAYS SO

34 rows moved against 7 predicted — but 28 of them moved because the **seed**
stopped applying, not because the subject did. Every `t.*` program opens with
`CLS:LOCATE 7,4`, and that `LOCATE` is cut too, so the cursor sits at CLS home
when the error fires and every ` 4  7 ` becomes ` 0  0 `. The cut does prove the
accept path is load-bearing for the reading; it proves almost nothing narrower.

🔴 **And `t.zero` is BLIND to it.** `CLS:LOCATE 7,4:LOCATE 0,0` reads ` 0  0  0 `
whether the two `LOCATE`s applied or neither did — the seed's fallback and the
row's target are the same cell. The probe's `SEED` comment claims the seed makes
"did not move" distinguishable from "moved to home"; that is true for every row
**except the one whose target is home**. The row is still sound in the shipped
tree (where the seed applies); it is unmeasurable by this particular cut, and
that is recorded rather than papered over.

⚠️ **The hang question was asked before any cut ran.** A dead machine scores
`<NO CAPTURE>` on every `t.*` row and `<NO ECHO>` on every `u.*` row — all 45
red. No cut here can hang (five swap one `call`/1-byte opcode for another into a
routine that terminates), and none produced an all-red set; K-LA2's 37 and
K-LA5's 34 both left a live green remainder.

## 9. Denominator

[`locarg-msx1-characterization.md`](locarg-msx1-characterization.md) §6, plus
`make missing-acceptance`'s 214 rows as the green control set and
`make onerr0-acceptance`'s 24 as the derive's.

## 10. As-built

### 10.1 What landed

* [`basic/missing.asm`](../basic/missing.asm) — `loc_next`'s 29 bytes of inline
  domain check become `call eval_byte_checked`; `loc_illegal` deleted. The
  refuted header is replaced by what is now true, **including a pointer at the
  `u.*` battery that keeps measuring the apparatus the claim was about**.
* [`basic/program.asm`](../basic/program.asm) — `derive_directf` extracted from
  `rp_exec` and called from `oe_reraise`.
* [`probes/basic/basic_probe_locarg.py`](../probes/basic/basic_probe_locarg.py)
  — new, 45 rows, 4 positive + 4 negative controls, `make locarg-acceptance`.
* [`probes/basic/basic_probe_onerr0.py`](../probes/basic/basic_probe_onerr0.py)
  — `DEFERRED` emptied **by fixing the rows**, not by rescoring them.

### 10.2 The walls — and §6's hand count was EXACT

| wall | before | after |
|---|---|---|
| main page 1 free | **0 B** | **22 B** |
| page-0 low region | 11 B | 11 B |
| sub page 0 / page 1 | 3604 / 1483 | 3604 / 1483 |

`main: 1586 spans, 0 dead (+0 allowlisted)` before and after — `loc_illegal` and
`rpe_mode` went, `derive_directf` and `dd_mode` arrived.

### 10.3 ROM hashes

`basic-reloc 830e5279` · `sub accce5a1` (unchanged) · `disk 2c630d3d`
(unchanged) · `zerobas-main-eu 18acd585`.

### 10.4 The gates

| gate | before | after |
|---|---|---|
| `locarg-acceptance` (new) | 38/45 | **44/45**, 1 deferred |
| `onerr0-acceptance` | 24 rows / 22 scored / **2 deferred** | 24 / **24 scored** / **0 deferred** |
| `missing-acceptance` | 214/214 as recorded | 214/214 as recorded |

### 10.5 🔴 Three things went differently

**(a) THE DECLINE'S STATED BLOCKER NAMED WORK THAT ALREADY EXISTED.** §6.6
declined for want of LOCATE's denominator — "row/column, omitted arguments, the
`CON_LASTROW` clamp, `CSRLIN`/`POS` read-back". All four were already in
`make missing-acceptance`, 214 recorded rows, and had been for weeks. The
genuinely missing axis was **one**: a deferred expression error as an argument.
The check that would have found this is `grep LOCATE probes/`, one command, not
run — because the person pricing a carve is reading the file the carve is in,
not the gate list ([[a-hand-listed-denominator-is-a-scope-claim]]).

**(b) 🔴 THE FIRST PLACEMENT OF THE NEW ROUTINE DID NOT ASSEMBLE, AND MOVING IT
WAS FREE WHILE THE OBVIOUS REMEDY WAS NOT.** See §5.1: 14 B dropped inside the
run loop pushed a backward `jr rp_lp` past −128, the identical failure D-CONTR
recorded two instructions below the same span. D-CONTR's remedy (`jr` → `jp`)
costs 1 B; siting the routine outside the span costs 0. **Where a routine goes
is a price, and a slice that reads a build error as "add a byte" pays it.**

**(c) 🔴 A NEW DIVERGENCE FOUND BY A ROW WRITTEN TO TEST AN ORDERING, AND THE
CONSTRAINT IT REFUTES WAS FROZEN BY A ROW THAT COULD NOT TEST IT.** `t.tmfp`
(§7): both references rank a pending numeric fault above `TMISMATCH`; zerobas
does the reverse, before and after alike. D-EVALCHK §5.1 froze that order as a
*forced constraint* on `PRINT #A$,"X"` — a row with a type fault and **no**
pending numeric one. Deferred here with its denominator named, because
`check_expr_errors` has four other callers.

### 10.6 Corpus

Sequentially from clean (`rm -rf build` + `make repack-machine`, **bash** —
`zsh` does not word-split `make $t`), **37 targets, all rc=0, 24 min 15 s wall**:
the 35 of [`spec-basic-evalchk.md`](spec-basic-evalchk.md) §10.7 plus the two
gates this slice moves — **`locarg-acceptance` (new)** and `missing-acceptance`,
the carve's green control set.

`unit-test` · `audit-citations` CLEAN (**775** swept, +3 on D-EVALCHK's 772: two
new docs and one new probe — **the sweep counts docs, not just code**) ·
`preflight-check` **181/86/95/95/0** · `injector-check` **350** files ·
`rowshape-check` **21** probes · `latch-check` **16/16** · `deadcode`
**0/0 (+1)** · `lnblank-acceptance REPEAT=2` **539/539** ·
`lnblank-say-acceptance` **204/204** · `logicops-acceptance` **193/193** ·
`float-acceptance` · `linemax-acceptance` **60/60** · `dexp5-pin` ·
`editverb-acceptance` **61/61** · `lptverb-acceptance` **44/44** ·
`dskmsg-acceptance` **5/5** · `diskbasic-acceptance` **34/34** verbs ·
`fat-error-acceptance` **10** scored · `runtail-acceptance` **9/9** ·
`castail-acceptance` **31/31** · `cassave-acceptance` **20/20** ·
`readvar-acceptance` **24/24** · `arylv-acceptance` **18/18** ·
`inputary-acceptance` **7/7** · `lvfix-acceptance` **18/18** ·
`fldary-acceptance` **13/13** · `lrvar-acceptance` **21/21** ·
`forvar-acceptance` **33/33** · `nxlist-acceptance` **25/25** ·
`nxary-acceptance` **22/22** · `tgtspc-acceptance` **28/28** ·
`namspc-acceptance` **58/58** · `fldwidth-acceptance` **40/40** ·
`clearpool-acceptance` **52/52** · `width-acceptance` **94/94** — **plus the
three gates this slice touches**: **`onerr0-acceptance` 24 printed / 24 SCORED /
24 agree** (was 22 scored + 2 deferred), **`missing-acceptance` 214/214 as
recorded** (the carve's green control set, unmoved) and **`locarg-acceptance`
44/45** (45 cases, 1 deferred).

⚠️ **`rowshape-check` reads 21, not D-EVALCHK's 19**, and both the new probe and
`basic_probe_locarg.py` are why: a probe that prints report rows on an exit-2
path *and* another path joins that contract automatically. It is a counter that
grows with the corpus, so quoting last slice's figure would have been a
prediction rather than a measurement.

### 10.7 The fix, as a program

Every cell is a **measured reading**, not a restatement: the "before" column
comes from the pre-slice ROM (`basic-reloc.rom d11dfd4a…`), the "after" from the
shipped one (`830e5279…`), and both reference columns were read off the machines
themselves.

**The carve — and it is a FIX, not a tidy-up:**

```basic
10 LOCATE 70000+0*(1/0),3
20 PRINT"[RANON]"
```

| | screen after `RUN` |
|---|---|
| VG-8020 · CF-3300 | `Division by zero in 10` |
| zerobas **before** → **after** | `Overflow in 10` → **`Division by zero in 10`** |

**The row that makes it a RULE and not "division by zero is special"** — a
different fault code through the identical shape, read as `[ ERR CSRLIN POS ]`:

```basic
10 ON ERROR GOTO 100
20 CLS:LOCATE 7,4:LOCATE 70000+0*SQR(-1),3
30 E=0:Y=CSRLIN:X=POS(0)
40 PRINT"[";E;Y;X;"]":END
100 E=ERR:Y=CSRLIN:X=POS(0):RESUME 40
```

| | reading |
|---|---|
| VG-8020 · CF-3300 | `[ 5  4  7 ]` |
| zerobas **before** → **after** | `[ 6  4  7 ]` → **`[ 5  4  7 ]`** |

…and the ` 4  7 ` in every column is the other half of the claim: the cursor is
still where `LOCATE 7,4` put it. The abort moved nothing.

**The +7 B it funded — and the two rows fail in OPPOSITE directions**, which is
why a constant cannot serve. `d.instop` types the disarm at the prompt while a
`STOP` holds the handler open:

```basic
10 ON ERROR GOTO 40
20 ERROR 7
30 PRINT"[NO]"
40 STOP
RUN
ON ERROR GOTO 0
```

| | screen |
|---|---|
| VG-8020 · CF-3300 | `Break in 40 >> Out of memory in 20 >> [OK]` |
| zerobas **before** → **after** | `… >> Out of memory >> [OK]` → **`… >> Out of memory in 20 >> [OK]`** |

`d.dirtrap` is the mirror — the erroring statement is the TYPED one, and the
suffix must go away:

```basic
10 ON ERROR GOTO 30
20 END
30 ON ERROR GOTO 0
40 PRINT"[RANON]"
RUN
ERROR 7
```

| | screen |
|---|---|
| VG-8020 · CF-3300 | ` >> Out of memory >> [AFTER]` |
| zerobas **before** → **after** | ` >> Out of memory in 0 >> [AFTER]` → **` >> Out of memory >> [AFTER]`** |

**And the one that did not move**, printed by the gate and not scored:

```basic
10 ON ERROR GOTO 100
20 CLS:LOCATE 7,4:LOCATE STR$(1/0),3
```

| | reading |
|---|---|
| VG-8020 · CF-3300 | `[ 11  4  7 ]` |
| zerobas **before** → **after** | `[ 13  4  7 ]` → `[ 13  4  7 ]` |

Against its discriminator `LOCATE "5",3`, which is ` 13 ` on all three sides —
so the claim is exactly "a pending numeric fault outranks the type test too",
and it belongs to `check_expr_errors` and its four other callers, not here (§7).
