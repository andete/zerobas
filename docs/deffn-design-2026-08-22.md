# DESIGN — `DEF FN` / `FN`: what the reference DOES, measured

Status: **MEASUREMENT ONLY. No ROM byte changed.** 2026-08-22, from `84e080c`.
Probe: [`scratchpad/deffn_scout.py`](../scratchpad/deffn_scout.py), rounds 5–10,
logs `scratchpad/deffn_round5.out` … `deffn_round10.out`. Boot-per-case, Philips
VG-8020 + National CF-3300. **Both references agree on every scored row.**

The gated row set is **82**: 71 measured here, plus the scout's own 11 round-3
behaviour rows (`scratchpad/deffn_scout.out`), which this round re-uses
unchanged. 🔴 **The `WANT` column was GENERATED from those logs, not
transcribed** — and the generator refused any row the two references did not
agree on, so nothing unscored reached the table.

Companion: [`deffn-scout-2026-08-22.md`](deffn-scout-2026-08-22.md) measured what
the reference **stores**. This one measures what it **does**, and its §6 list of
"what is NOT claimed" is what this file closes.

---

## 1. 🔴 The headline of the scout is REFUTED

The scout's own summary reads:

> **AND THE BINDING IS DEARER THAN FILED.** `X=5:DEF FNA(X)=X+1:Y=FNA(2)` leaves
> **X = 5** on both references: the formal is **SAVED AND RESTORED**, not bound
> through the variable table the way classic MS BASIC does. […] that is the fact
> the design turns on.

The observation is right and the mechanism drawn from it is wrong. **There is no
save and no restore, because the variable is never written.** Three rows say so,
and only the third of them can be argued with:

| row | program | both refs |
|---|---|---|
| `o.realcell` | `X=5 : P=VARPTR(X) : DEF FNA(X)=PEEK(P)` → `FNA(2)` | **`5`** |
| `o.realcell.ctl` 🟢 | the same `PEEK(P)`, no FN in the way | `5` |
| `o.sameaddr` | `DEF FNA(X)=VARPTR(X)-P` → `FNA(2)` | **`30327`**, not `0` |
| `o.dynself` | `X=5 : DEF FNB(Y)=X : DEF FNA(X)=FNB(0)+X*100` → `FNA(2)` | **`205`** |

`o.realcell` takes the variable's address **outside** the body and reads it
**inside**: the cell still holds 5 while the body is running. `o.sameaddr` says
the name resolves to a **different address** inside the body. And `o.dynself`
shows FNA's own body reading `X` as 2 (the `*100` term) in the same call in
which FNB's body reads `X` as 5 — which one shared cell cannot do.

> 🎯 **THE FORMAL IS A SHADOW CELL THAT ONLY THE DEFINING FUNCTION'S OWN BODY
> SEES.** Nothing is saved, nothing is restored, and nothing has to be unwound.

> 🔴 **CORRECTION, 2026-08-22 (the RAM-hunt round): THAT LAST SENTENCE IS TRUE OF
> THE VARIABLE TABLE AND FALSE OF THE SHADOW BLOCK, AND IT IS WRITTEN AS IF IT
> WERE UNQUALIFIED.** It is also the form that reached the memory index. §2 states
> the opposite mechanism eight lines further down — *"the reference copies the
> outer frame away and reuses one block"* — and §2 is right.
>
> The rows decide it. `z.addr2` (`DEF FNB(X)=FNA(0)*0+VARPTR(X)`) and `z.addr2i`
> (`DEF FNB(X)=FNA(0)`) both read **`$F6EB`**, so FNA's shadow and FNB's shadow
> are **the same cell**. Then `o.nestsame` — `DEF FNA(X)=X : DEF FNB(X)=FNA(X+1)+X`
> → `FNB(3)` — requires FNB's `X` to still be **3** after FNA's call wrote **4**
> to that same cell: 4+3 = **7**, which is what both references answer. With no
> restore it is 4+4 = 8. `o.outerafter` is the second witness: 0+2 = **2**
> restored, 0+0 = 0 not.
>
> **So a nested call MUST save the outer frame and restore it on return.** What
> §1 establishes is narrower and still valuable: the *variable table* is never
> written, so no user-visible cell needs unwinding and the ERROR path needs no
> work — `raise_error` resets SP and the abandoned saved copy is nobody's
> business. **The claim survives; its scope does not.**
>
> ⚠️ **And the gate could not have caught the mistake.** The mutation battery in
> §8b had eight mutants and none of them was *"the shadow is not restored"* —
> the implementation an unqualified §1 invites. Build the obvious single fixed
> block with no save/restore and the address rows still agree, the binding rows
> still agree, and the ceiling still agrees; only `o.nestsame` and `o.outerafter`
> move. That mutant now ships (`make deffn-selftest`, **18/18**, was 17).

That is *cheaper* than the filed design in code and in risk **on the variable-table
axis only**: the error path needs no work at all, which is exactly why `X` is
still 5 after a body that raised.

### 1.1 🔴 And the row that was going to prove the opposite agreed for the wrong reason

Round 8 asked the same question as `DEF FNA(X)=PEEK(VARPTR(X))` and got **`2`**
with its no-FN control at `5` — read as "the real cell holds the actual". It is
not: **`VARPTR(X)` inside the body resolves `X` exactly the way the body does**,
so it reports the shadow's address just as happily as the entry's. The case
could not separate the two hypotheses it was built to separate
[[a-case-that-agrees-can-agree-for-the-wrong-reason]]. `o.realcell` takes the
address from **outside**, where the name cannot be captured, and that is the
whole difference between the two rows.

---

## 2. Where the shadow lives, and why the parameter ceiling is 9

| row | program | both refs |
|---|---|---|
| `z.addr` | `DEFINT A-Z : DEF FNA(X)=VARPTR(X)` → `FNA(2)` | `-2325` = **`$F6EB`** |
| `z.addr2` | the same address read one nesting level deeper | `-2325` |
| `z.addr2i` | …and at the inner level | `-2325` |
| `z.addr.ctl` 🟢 | an ordinary variable's `VARPTR` | `-32679` = `$8059` |
| `o.p9` | 9 formals | `1` |
| `o.p10` | 10 formals | **ERR 5** *at the call* |

The shadow is at a **fixed address**, and it does **not move with nesting** —
so the reference copies the outer frame away and reuses one block, rather than
building a frame per call.

> 🎯 **AND THE CEILING IS NOT A RULE, IT IS A DIVISION.** `$F6EB` is 3 bytes into
> a **100-byte** block at `$F6E8`; a slot shaped like a variable entry is
> `[name0][name1][type][value:8]` = **11 B**; `100 / 11 = 9`. The measured
> ceiling of 9 formals is *predicted* by the area size, which is a much better
> reason to size zerobas's own area the same way than "the manual says 9".

`o.p10`'s ERR 5 is raised **at the call** (`AT 60`), not at the `DEF`
(`z.p10def` → `OK`), which is consistent with everything in §3.

---

## 3. `DEF FN` does not parse its body

| row | program | both refs |
|---|---|---|
| `o.lazybody` | `DEF FNA(X)=X+*2`, never called | **`OK`** |
| `o.lazydiv` | `DEF FNA(X)=X/0`, never called | **`OK`** |
| `o.noeq` | `DEF FNA(X) X+1` — **no `=` at all** | **`OK`** |
| `o.aryformal` | `DIM B(5) : DEF FNA(B(1))=B(1)+1` | `OK` at DEF, **ERR 2 at the call** |
| `o.twofault` | `DEF FN(X` — no name **and** unclosed | **ERR 2 at the DEF** |
| `o.badname` | `DEF FN1(X)` — leading digit | **ERR 2 at the DEF** |
| `o.quotedcolon` | `DEF FNA$(X$)=X$+":Q"` → `FNA$("a")` | **`a:Q`** |
| `o.stmtcolon` | `DEF FNA(X)=X+1:B=9` → `FNA(2);B` | `3 9` |

> 🎯 **`DEF FN` VALIDATES EXACTLY ONE THING: THAT A LETTER FOLLOWS `FN`.**
> Everything else — the parameter list, the `=`, the body — is untouched until
> the function is called. So the statement is a **scan**, not a parse:
> `is_letter` → `var_name_key` → record → skip to the end of the statement.

⚠️ **The skip is token-aware.** `o.quotedcolon` returns `a:Q`, so a `:` inside a
string literal does not end the definition, while `o.stmtcolon` shows a real
statement separator does. That is `if_skip_to_else`'s shape with `COLON` for
`ELSE_TOKEN`, i.e. `tok_skip` in a five-instruction loop — not a byte scan.

---

## 4. Error ordering — D-LINERR's rule applied, and it is simple

| row | program | both refs |
|---|---|---|
| `o.undefarg` | `FNZ(1,2)` — undefined **and** unmatched | **ERR 18** |
| `o.toomany` | `DEF FNA(X)=X+1` → `FNA(1,2)` | ERR 2 |
| `o.toofew` | `DEF FNA(X,Y)=X+Y` → `FNA(1)` | ERR 2 |
| `o.barecall` | `DEF FNA(X)=X+1` → `FNA` | ERR 2 |
| `o.argnoarg` | `DEF FNA=7` → `FNA(1)` | **`7 1`** |
| `o.strnum` | `DEF FNA(X)=X+1` → `FNA("hi")` | ERR 13 |
| `o.strnumx` | …and `X` afterwards | **`5 13`** |
| `o.errrestore` | body raises (`X/0`), then read `X` | **`5 11`** |

> **THE NAME IS LOOKED UP FIRST.** An undefined name beats every other fault
> (ERR 18), and only once the definition is in hand does an argument-count
> mismatch become ERR 2. So the call path is: name → **ERR 18** → walk the two
> lists together → **ERR 2** on a shape mismatch → **ERR 5** past 9 → bind →
> evaluate.

🎯 **`o.argnoarg` = `7 1` is not a two-value error.** A zero-parameter function
consumes **no parentheses at all**: `PRINT"[";FNA(1);"]"` evaluates `FNA` to 7
and then prints `(1)` as the next PRINT item. The `(` is left for the caller.

🎯 **AND NOTHING NEEDS UNDOING ON THE ERROR PATH.** `o.strnumx` and
`o.errrestore` both read `X` = 5 after a fault inside the call, which §1 already
explains: the variable was never written.

---

## 5. Types, scope and lifetime

| row | program | both refs |
|---|---|---|
| `o.global` | `Y=3 : DEF FNA(X)=X+Y` → `FNA(2)` | `5` — globals are visible |
| `o.dynscope` | `DEF FNB(Y)=X`, `DEF FNA(X)=FNB(0)` | **`5`** — the shadow is not dynamic |
| `o.outerafter` | `DEF FNA(X)=FNB(0)+X` | `2` — and it survives a nested call |
| `o.nestsame` | `DEF FNA(X)=X`, `DEF FNB(X)=FNA(X+1)+X` → `FNB(3)` | `7` |
| `o.actualfirst` | `X=5 : DEF FNA(X)=X*10` → `FNA(X+1)` | `60` — actuals bind in the CALLER |
| `o.fnpct` / `o.fnbang` 🟢 | `DEF FNA%(X)=X/2` vs `FNA!` | **`2`** vs `2.5` |
| `o.defint` / `o.defint.ctl` 🟢 | `DEFINT A-Z` then `DEF FNA(X)=X/2` | `2` vs `2.5` |
| `o.defintbang` 🟢 | `DEFINT A-Z` + an explicit `!` | `2.5` |
| `o.defstr` | `DEFSTR A-Z : DEF FNA(X)=X+"!"` | `hi!` |
| `o.namespace` | `A=9 : DEF FNA(X)=X+1` → `A;Y` | **`9 3`** |
| `o.clearwipe3` | `DEF FNA(X)=X+1 : CLEAR` → `FNA(2)` | **ERR 18** |
| `o.ifthen` / `o.ifnot` | `IF 1 THEN DEF …` / `IF 0 THEN DEF …` | `3` / ERR 18 |

Three of these decide where the definition lives:

* 🎯 **`o.clearwipe3` — `CLEAR` ERASES THE DEFINITION.** It behaves like a
  variable, because it *is* one.
* 🎯 **`o.namespace` — `A` and `FNA` coexist.** So the FN key is in a namespace
  of its own. Setting bit 7 of `name0` (`'A'`=`$41` → `$C1`) is a key no
  ordinary variable can produce, and it needs **no new table at all**:
  `var_alloc_or_find(BC=key, A=2)` already allocates a typed 2-byte entry
  through the ARY tenant, and 2 bytes is exactly a text pointer.
* **`o.ifnot`** — the definition is recorded when the statement **executes**,
  not when the line is scanned.

The **result** is coerced to the *function's own* type (`o.fnpct` vs its `!`
control), and that type comes from the name through the DEFtbl exactly like a
variable's (`o.defint` vs its two controls).

---

## 6. 🎯 `DEF FN` in DIRECT mode is `Illegal direct` — ERR 12

| row | typed at the prompt | both refs |
|---|---|---|
| `d.defonly` | `CLS:DEF FNA(X)=X+1:PRINT"[OK]"` | **`Illegal direct`** |
| `d.sameline` | …and using it on the same line | **`Illegal direct`** |
| `d.def` / `d.defrun` | define in direct mode, then call | `Undefined user function` |
| `d.defusr` 🟢 | `CLS:DEF USR=&HC000:PRINT"[OK]"` | `OK` |
| `d.let` 🟢 | `CLS:A=1:PRINT"[OK]"` | `OK` |

Two controls pin the refusal to `DEF FN` and not to `DEF`, nor to direct mode in
general. ✅ **ERR 12's message already ships** (`err_msgtab` entry 12,
sub-hosted) and is currently reachable only through `ERROR 12`.

🎯 This is also the rule that makes a **text pointer** safe as the stored
definition: a direct-mode definition would point into the line buffer, which the
next command overwrites. The reference does not have that problem because it
refuses to make one.

---

## 7. What this costs, and why it is not landed today

> ✅ **OBSTACLE (3) IS CLOSED — 2026-08-22, LATER THE SAME DAY.**
> [D-DUPSPAN](spec-basic-dupspan.md) spent the §8 survey: main page 1 went
> **4 B → 54 B (+50 B)**, `sub.rom` byte-identical. §8's own estimate for the
> two error-tail families was *"~45–55 B net"* and the measurement is **50**.
> **The reading below is left standing as the reading that was true when it was
> taken** — the conclusion it supports (*"even the statement side alone does not
> fit"*) is the part that is now false. Obstacle (2), the RAM window, is
> **still open** and is the live blocker: see
> [`basic/sysvars.inc`](../basic/sysvars.inc) and §7(2).

**Walls, read from `make basic-reloc` at `84e080c` on a clean tree, 2026-08-22:**

| region | free |
|---|---|
| main page 1 | **4 B** |
| main page-0 low | **46 B** |
| sub page 0 | 3075 B |
| sub page 1 | 1624 B |

⚠️ **It is resident wherever it lands.** `FN` evaluation calls `eval`, which is
main page 1, and no sub-ROM tenant can reach main page 1 — `check_sub_walls`'
own closure gate proves it both ways. The `DEF FN` **statement** could be a
page-0 tenant sharing `ex_deftype`'s existing glue (it needs no `eval` at all);
the **call** cannot.

**Three obstacles were measured rather than estimated, and the third is the one
that stopped this becoming a fix today:**

1. **The main ROM has 50 free bytes in total.** The three resident pieces are
   the `ev_f` dispatch arm, `ev_fn` (name → ERR 18 → list walk → bind → body →
   result coercion) and the `fn_shadow` hook that `var_find_typed` and
   `var_alloc_or_find` must both go through. Even the statement side alone,
   drafted against the measured rules in §3, does not fit.
2. 🔴 **THE RAM WINDOW THE PARAMETER AREA NEEDED IS NOT FREE, AND THE SYSVAR MAP
   SAYS IT IS.** [`basic/sysvars.inc`](../basic/sysvars.inc) records
   *"-> top `$E3E8`, well below the disk WBUF wall at `$E560` (376 B spare)"*
   — and `GFX_PSTK`/`GFX_DBUF` have since been homed at **`$E3F2`**, 256 B of
   it, leaving **10 bytes**. This was found by the assembler, not by reading:
   the draft's own page-crossing assert fired
   (`FNPAREA_CROSSES_A_PAGE__8BIT_SLOT_WALK_WOULD_CARRY`), and only then did the
   window turn out to be occupied as well. **That comment is a live defect and
   is filed as one** — a later slice reading "376 B spare" would place a cell
   inside the PLAY parser's stack.
3. **The carve has to come from somewhere, and it is bigger than any single
   candidate.** §8.

**No total is claimed.** The draft was written and assembled far enough to hit
(2) and was then **reverted**; the tree at the end of this work is byte-identical
to `84e080c` and its four walls read exactly as above. A size derived from
counting the remaining instructions in my head is not a measurement and is not
recorded here.

---

## 8. The funding survey — measured, and it is a real supply

[`scratchpad/dupspan_sweep.py`](../scratchpad/dupspan_sweep.py) asks the whole
main image the question D-PAINTBORD answered by eye for one pair: **which spans
between consecutive labels are byte-identical?** That carve — `gfx_absent` was
identical to `gfx_err5` and became `equ` it, −5 B — is the precedent, and
`interp.asm`'s own `err_illegal_fn` is the precedent for *that*.

⚠️ **The tool is calibrated**: `--selftest` plants two synthetic identical spans
and asserts the walk finds that pair, so "0 candidates" would be a statement
about the ROM rather than about a walk that finds nothing by construction. It
prints its denominator (1480 labels, 1467 non-empty spans).

The largest groups, from the run at `84e080c`:

| bytes | ×  | recoverable | what it is |
|---|---|---|---|
| 5 | 8 | 35 B | `ld a,5` / `jp raise_error` — `gb_illegal`, `snd_illegal`, `pl_absent`, `gfx_err5` (already collapsed), `fchk_ifc`, `eoi_err5`, `strig_illegal`, `sw_illegal` |
| 5 | 6 | 25 B | `ld a,2` / `jp raise_error` — `pl_syntax`, `elg_syntax`, `pc_syntax`, `ep_syntax`, `gfx_syntax`, `trap_syntax` |
| 20 | 2 | 20 B | `sav_ascii_flag` / `sav_cas_flag` |
| 20 | 2 | 20 B | `esn_p2` / `esn_scan_lp` |
| 16 | 2 | 16 B | `ems_print` / `exps_print` |
| 14 | 2 | 14 B | `ai14_lp` / `ai6_lp` |
| 13 | 2 | 13 B | `raf_zero_ok` / `cpow_x0_pos` |
| 13 | 2 | 13 B | `eostr_lp` / `eokey_lp` |
| 12 | 2 | 12 B | `sst_overflow` / `shxf_overflow` |
| 12 | 2 | 12 B | `ex_on_strig` / `ex_on_key` |
| 11 | 2 | 11 B | `asw_single` / `vsf_single` |

🔴 **EVERY ROW IS A CANDIDATE, NOT A VERDICT, AND THE TOOL SAYS SO.** Two things
it cannot decide were checked by hand on the ERR-5 family and both bite:

* **Some sites are FALLTHROUGH targets.** `sw_illegal` ([`basic/missing.asm:483`](../basic/missing.asm:483))
  is entered by falling off a `pop hl` above it; aliasing it away needs a `jp`
  in its place, so it recovers 2 B, not 5.
* **Some callers use `jr`.** `gb_illegal`, `snd_illegal`, `pl_absent`,
  `fchk_ifc`, `eoi_err5`, `pl_syntax` and `pc_syntax` are all reached by `jr`
  from nearby, and a collapse moves the target out of range; each such caller
  costs 1 B to widen to `jp`.

✅ **BOTH ERR FAMILIES SPENT 2026-08-22 by [D-DUPSPAN](spec-basic-dupspan.md):
13 tails collapsed to two `equ` canonicals, `+50 B` — against the estimate below
of ~45–55 B.** 🔴 **And the estimate for the REST of this table is worse than it
reads**: the `3 B ×6` bare-`jp raise_error` group is worth **~2 B, not 15**,
because five of its six members are entered by fallthrough from a *different*
`ld a,N`. The remainder are loop bodies, not tails, and a loop body containing a
relative jump out of itself is not position-independent at all. Re-run the tool.

Realistically the ERR-5 and ERR-2 families together are worth ~45–55 B net, and
the whole list ~150–190 B — enough, but it is **a funding slice of its own**,
across seven files, and each collapse also erases a distinct error *identity*
that this tree's own comments treat as meaningful (`gfx_absent`'s note: *"the
NAME survives because the two are different CLAIMS"*).

---

## 8a. What the row set says about zerobas TODAY

`make deffn-acceptance` at `84e080c` (clean → `make repack-machine` → probe),
82 rows + 3 claim rows:

    ROWS: 85 printed, 80 scored — 67 of 69 DEF FN rows still divergent;
                                  0 of 8 controls failed

🟢 **All eight positive controls PASS**, so the reds below are about the verb.

🔴 **SIX ROWS ARE A SILENT WRONG ANSWER, NOT TWO.** The scout found `FNZ(1)` and
a forward `DEF`; the wider row set finds four more, all the same mechanism —
an undefined `FN<name>(…)` parses as an ordinary subscripted array reference and
reads **`0`**:

| row | reference | zerobas |
|---|---|---|
| `b.undef` `FNZ(1)` | ERR 18 | **`0`** |
| `b.forward` `DEF` on a later line | ERR 18 | **`0`** |
| `o.undefarg` `FNZ(1,2)` | ERR 18 | **`0`** |
| `o.ifnot` `IF 0 THEN DEF …` | ERR 18 | **`0`** |
| `d.def` direct-mode define, then call | `Undefined user function` | **`0`** |
| `d.defrun` …then `RUN` | `Undefined user function` | **`0`** |

🔴 **AND TWO OF THE THREE GREENS ARE WORTHLESS, WHICH THE PROBE NOW SAYS OUT
LOUD.** `o.twofault` (`DEF FN(X`) and `o.badname` (`DEF FN1(X)`) both want
`ERR 2 AT 20` and both get it — but so do **44 of the 69** subject rows, because
this tree answers `Syntax error` to *every* `DEF FN` line. Those two agree with
a **blanket**, not with the name rule they were built to test, and they would
keep agreeing through an implementation that got that rule wrong
[[a-case-that-agrees-can-agree-for-the-wrong-reason]]. The probe detects the
blanket (a zb face shared by ≥5 rows that diverge) and prints
`GREEN BUT VACUOUS` beside them rather than leaving it to the reader.

🔴 **A THIRD INSTANCE, IN THE PROBE'S OWN GATE.** The first version of the three
address `claim:` rows scored the predicate over whatever faces came back, and on
today's tree two of them came out **PASS**: `'ERR 2 AT 30' == 'ERR 2 AT 30'`
satisfies *"the shadow does not move with nesting"*, and `!=` satisfies *"the
shadow is not the variable's own cell"*. **The two sharpest claims in this whole
document were being signed off by a machine that cannot express either of
them.** A predicate now names the rows it reads and scores `....` unless every
one of them is a number; the fix is calibrated on a reference-like set (PASS), a
planted-wrong set (FAIL) and today's error faces (NOT MEASURED).

---

## 8b. 🔬 Falsifying the gate, because the subject is missing

There is no fix to knife. What there IS is an instrument that will be believed
the day the verb lands — and **a real run of it cannot demonstrate that it would
detect anything**, because 67 of 69 rows are red whatever the classifiers do.
So the classifiers are mutation-tested against **planted face tables** instead:
`make deffn-selftest` (no emulator, `--selftest`).

| planted case | must produce |
|---|---|
| a correct implementation (`zb` = `WANT`) | 0 divergent, 0 vacuous, 0 silent |
| today's tree (the real measured faces) | 6 silent, exactly `o.twofault`+`o.badname` vacuous |
| MUTANT: binds through the variable table | catches `o.realcell`/`o.dynself`/`o.dynscope`/`o.dynaddr` |
| MUTANT: 10 formals accepted | catches `o.p10` |
| MUTANT: `DEF FN` parses its body | catches `o.lazybody` |
| MUTANT: direct mode allowed | catches `d.defonly`/`d.sameline` |
| MUTANT: `CLEAR` does not erase | catches `o.clearwipe3` |
| MUTANT: undefined name reads 0 | catches `b.undef` |
| MUTANT: result not coerced to the FN's type | catches `o.fnpct` |
| MUTANT: the shadow moves with nesting | catches `z.addr2` |
| one wrong row on an otherwise correct tree | exactly 1 divergent, **0 vacuous** |
| a blank reading | scored `blank`, never `DIFF` |
| a broken positive control | caught as a control failure |
| the address claims, three ways | PASS / FAIL / NOT MEASURED |

**17 of 17 hold**, the seventeenth being an integrity check on the `WANT` table
itself — and it exists because the generator nearly banked garbage.

🔴 **"BOTH REFERENCES AGREE" DOES NOT MEAN "THE READING IS RIGHT".** The rule
that built `WANT` was *"take the last round in which both references agreed"*,
and **the scout's round 2 agreed on eleven rows while reading the program's own
source text** — the fixture's echo carried the `[...]` fence, so `b.param`
returned `'";Y;X;"'` on all three sides and scored `refs-agree`. Both readings
are indistinguishable in the log. The banked table is clean (checked, not
assumed: the last occurrence of each row happened to be the corrected one), and
what now keeps it clean is that a captured source fragment carries the fixture's
own quotes and semicolons, which no value in this row set does. Calibrated both
ways — silent on the real table, firing on the planted round-2 face.

🔴 **AND THE BATTERY FOUND A DEFECT IN THE CLASSIFIER IT WAS BUILT TO CONFIRM.**
The blanket rule was *"≥5 rows share this `zb` face and at least one of them
diverges"*. That is correct for today's tree and wrong for a nearly-working one:
five rows may legitimately share `ERR 2 AT 60`, and one of them going red then
branded the other four **vacuous**. Every mutant reported 4–11 bogus vacuous rows
— visible only because each case states what it must produce. The rule now counts
the **diverging** rows (`≥5`), and `one wrong row, nothing vacuous` is the case
that pins it. That case did not exist until the defect did.

---

## 8c. The predecessor knives, re-run as a regression on this work

The only source this round changed outside `docs/`, `probes/` and `scratchpad/`
is **two comments** (`basic/sysvars.inc`, `basic/vars.asm`). Both ROM images are
`sha256[:8]` **`815bb553`** / **`b91622a9`** before and after, i.e. byte-identical
to `84e080c` — so nothing that reads ROM behaviour can have moved.

That is an argument, and the knives are the measurement. All three predecessor
suites were re-run on this tree. Each calibrated its parser on a clean, a planted
and a row-deleted log first; each read a baseline of
`roms=('815bb553','b91622a9') divergent=[]` — **the same two hashes** — and each
restored to a byte-identical source and those same hashes afterwards.

| suite | patches | knives |
|---|---|---|
| `paintbord_knives.py` | `basic/graphics.asm` | **4/4 EXACT** |
| `paintmc_knives.py` | `sub/graphics.asm` | **4/4 EXACT** |
| `paints2seed_knives.py` | `sub/graphics.asm` | **2/2 EXACT** |

**10 of 10, no knife going blind, no predicted set moving.** 🎯 And the two-ROM
guard earned its place in passing: `paintmc`'s K-PM1 reports
`roms=('815bb553','ef386d67')`, i.e. **only `sub.rom` moved** — a runner watching
the main image alone would have aborted with *"make skipped the build"* when make
had done nothing wrong.

⚠️ **The disjointness is worth stating because it is checkable, not assumed**:
`paintbord` patches `basic/graphics.asm`, the other two patch `sub/graphics.asm`,
and this round touched neither.

---

## 9. What is NOT claimed

* **No implementation and no total.** §7 says why, with the walls that say it.
* **Nothing about the reference's actual addresses being reproducible.** `$F6EB`
  and `$8059` are the reference's RAM map; zerobas's is its own
  (PROVENANCE.md — the same disposition `basic/usr.asm` records for USR's
  calling convention). The probe therefore gates the layout-INDEPENDENT claims
  (`VARPTR(formal) ≠ VARPTR(variable)`; the shadow does not move with nesting)
  and prints the addresses as characterization.
* **Nothing about `DEF FN` interacting with `RESUME`, `CONT`, `TRON`, arrays as
  actuals, or a definition whose program line is later edited.**
* **Nothing about what the shadow does to `FRE`.**
