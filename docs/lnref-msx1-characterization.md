<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-LNREF — the line-number REFERENCE, measured: which verbs arm it, and how big it may be

Instrument: [`probes/basic/basic_probe_lnblank.py`](../probes/basic/basic_probe_lnblank.py),
batteries `lnr` (137 rows), `lnrx` (25), `lnr2` (4), `lnv` (26), `lnv2` (5),
`lna` (13), `lnrd` (7, say-mode).

Two oracles, **Philips VG-8020** and **National CF-3300**, `--repeat 2`, every
payload past the echo guard on all three sides. **The two references agree on
every one of the 217 rows below, byte for byte.** No row read `UNSTABLE`,
`NOCAPTURE` or `REFUSED`.

---

## 0. The headline

`TODO.md` files this as **two** items. It is **one mechanism** — line-number
mode, `branch_lineno` in
[`basic/tokenise.inc`](../basic/tokenise.inc) — with **two rules**, and the filed
description of each was wrong.

1. 🔴 **The filed verb list is wrong in BOTH directions.** It names five verbs
   zerobas lacks the `$0E` arm for (`LIST`/`DELETE`/`AUTO`/`RENUM`/`ELSE`).
   Measured over all 162 reserved words, the reference arms on **fourteen**.
   **Three of the filed five (`DELETE`/`AUTO`/`RENUM`) are not this defect at
   all** — zerobas has no token for them, so their rows diverge for a second
   reason and can attribute nothing. And **three verbs the item never mentions
   arm**: `RETURN`, `ERL` and `LLIST`. Two of those three — `RETURN` and `ERL` —
   are verbs zerobas *has tokens for*, so they are this defect, and nobody had
   looked at them.
2. 🔴 **"`20 GOTO 99999` tokenises 3 bytes shorter" is not a length, a wrap or a
   refusal — the reference SPLITS the digit run.** A line-number reference
   accumulates only while the value stays **≤ 65529**; the first digit that
   would carry it past that **ends the reference and begins a new one**, because
   the mode is still armed (D-LNLIST R-L2). `GOTO 99999` stores
   `$0E,9999` `$0E,9` — six bytes where zerobas stores three. The filed
   measurement read the ONELIN/ARYTAB pointers and could only ever have seen the
   three.
3. 🔴 **And one of the missing arms is a LIVE RUNTIME DEFECT, not a byte-level
   nicety.** `if_false` ([`basic/interp.asm:1347`](../basic/interp.asm:1347))
   already tests `cp LINENO_TOKEN` after the `$A1` and jumps to `ex_goto_at`.
   The feature is written and reachable and has never fired, because the crunch
   never produces the `$0E` it waits for:

   ```
   10 IF 0 THEN 20 ELSE 30 : 20 A=20:END : 30 A=30:END
       both references -> A = 30, ERR 0
       zerobas         -> A =  0, ERR 2   (Syntax error)
   ```

---

## 1. R-R — WHICH reserved words arm line-number mode

The whole 162-word denominator
([`kwsweep-msx1-coverage.md`](kwsweep-msx1-coverage.md)), each asked the same
question in the same shape — `20 <WORD> 10`, does the `10` become
`<0E><0A><00>` or the ordinary constant `<0F><0A>`?

⚠️ **The payload carries no blank inside the number, on purpose.** The standing
`ref-*` rows type `1 0`, which diverges for two reasons on a machine that has
neither the arm nor D-LNBLANK's blank rule. This is the same trap D-EXPKW's
`expk-else` fell into (`expkw-msx1-characterization.md` §1.1a) — **the
terminator changed, not the subject.**

### The fourteen that ARM (both references, identical)

| word | token | reading | zerobas today |
|---|---|---|---|
| `GOTO` | `$89` | `<89> <0E><0A><00>` | arms ✓ |
| `RUN` | `$8A` | `<8A> <0E><0A><00>` | arms ✓ |
| `RESTORE` | `$8C` | `<8C> <0E><0A><00>` | arms ✓ |
| `GOSUB` | `$8D` | `<8D> <0E><0A><00>` | arms ✓ |
| **`RETURN`** | `$8E` | `<8E> <0E><0A><00>` | 🔴 `<8E> <0F><0A>` |
| **`LIST`** | `$93` | `<93> <0E><0A><00>` | 🔴 `<93> <0F><0A>` |
| `LLIST` | `$9E` | `<9E> <0E><0A><00>` | no token (`L<93> <0F><0A>`) |
| **`ELSE`** | `:`+`$A1` | `:<A1> <0E><0A><00>` | 🔴 `:<A1> <0F><0A>` |
| `RESUME` | `$A7` | `<A7> <0E><0A><00>` | arms ✓ |
| `DELETE` | `$A8` | `<A8> <0E><0A><00>` | no token (`DE<88>E 10`) |
| `AUTO` | `$A9` | `<A9> <0E><0A><00>` | no token (`AU<D9> <0F><0A>`) |
| `RENUM` | `$AA` | `<AA> <0E><0A><00>` | no token (`RENUM 10`) |
| `THEN` | `$DA` | `<DA> <0E><0A><00>` | arms ✓ |
| **`ERL`** | `$E1` | `<E1> <0E><0A><00>` | 🔴 `<E1> <0F><0A>` |

The other **148** words store the ordinary constant on both references.

### 1.1 🔴 It is a LIST, and it CANNOT be a range or a threshold

D-CNAME found an apparent operator rule that was really an **ASCII range**, and
D-LNLIST found an apparent token-value rule that was really *alphabetic vs
symbolic*. Here the walk says the opposite, and says it with **adjacent token
bytes on both sides of every boundary**:

| token | word | arms? |
|---|---|---|
| `$8B` | `IF` | **no** — and it sits *inside* the `$89`…`$8E` run |
| `$8F` | `REM` | unobservable (§1.2) |
| `$90` `$91` `$92` `$94` `$95` | `STOP` `PRINT` `CLEAR` `NEW` `ON` | **no** — `$93` `LIST` is alone between them |
| `$96` | `WAIT` | **no** |
| `$A6` | `ERROR` | **no** — immediately before `$A7` `RESUME` |
| `$AB` | `DEFSTR` | **no** — immediately after `$AA` `RENUM` |
| `$D9` | `TO` | **no** — immediately before `$DA` `THEN` |
| `$E2` | `ERR` | **no** — immediately after `$E1` `ERL` |

Every arming token has a non-arming neighbour on at least one side, and `IF`
sits *between* four arming tokens. No threshold, no mask and no range separates
the classes. **The faithful implementation is the list itself.** Only a walk
could say so: any six of these rows agree with half a dozen wrong rules.

### 1.2 Three rows CANNOT ANSWER, and they are not negatives

`REM` (`<8F> 10`), `DATA` (`<84> 10`) and `CALL` (`<CA> 10`) swallow or
re-scan the rest of the statement, so no observable line number can follow any
of them on any machine. They stay in the walk — dropping them turns a
denominator back into a sample, the trap D-NOTOPEN2 hit — and are read as
**unobservable**, never as "does not arm". All three agree on all three sides.

### 1.3 The walk's readings survive a REAL program shape (`lnr2`)

`20 ERL 10` and `20 RETURN 10` are not programs anyone writes. The crunch never
parses, so the readings should transfer unchanged; these rows are what say they
do.

| row | typed | both references | zerobas |
|---|---|---|---|
| `lnr2-goto`^ | `20 A=1:GOTO 10` | `A<EF><12>:<89> <0E><0A><00>` | agrees |
| `lnr2-nokw`^ | `20 A=1:B=10` | `A<EF><12>:B<EF><0F><0A>` | agrees |
| `lnr2-return` | `20 A=1:RETURN 10` | `A<EF><12>:<8E> <0E><0A><00>` | `<8E> <0F><0A>` |
| `lnr2-erl` | `20 IF ERL=100 THEN 1` | `<8B> <E1><EF><0E>d<00> <DA> <0E><01><00>` | `<E1><EF><0F>d …` |

🔴 **`lnr2-erl` is the row that makes this more than a tokeniser change.** The
`$0E` lands **inside an expression**, and `ev_f`
([`basic/expr.asm:505`](../basic/expr.asm:505)) has arms for `$0B` `$0C` `$1C`
`$0F` and **none for `$0E`**. Arming `ERL` without teaching the evaluator would
break a shape that works today.

### 1.4 The mode reaches the whole statement for the new verbs too (`lna`)

D-LNLIST R-L2/R-L3 were measured on branch keywords only. They hold unchanged:

| row | typed | both references |
|---|---|---|
| `lna-listrng` | `20 LIST 10-20` | `<93> <0E><0A><00><F2><0E><14><00>` |
| `lna-listopen` | `20 LIST -20` | `<93> <F2><0E><14><00>` |
| `lna-listplus` | `20 LIST 10+20` | `<93> <0E><0A><00><F1><0E><14><00>` |
| `lna-listkw` | `20 LIST 10 AND 20` | `<93> <0E><0A><00> <F6> <0F><14>` — the WORD disarms |
| `lna-listcol` | `20 LIST 10:20` | `<93> <0E><0A><00>:<0F><14>` — `:` disarms |
| `lna-elseb` | `20 IF A THEN B=1 ELSE 20` | `… B<EF><12> :<A1> <0E><14><00>` — `ELSE` RE-arms after a name disarmed it |
| `lna-elseplus` | `20 IF A THEN 1 ELSE 20+30` | `… :<A1> <0E><14><00><F1><0E><1E><00>` |
| `lna-elsecol` | `20 IF A THEN 1 ELSE 20:30` | `… :<A1> <0E><14><00>:<0F><1E>` |
| `lna-renum3` | `20 RENUM 10,20,30` | `<AA> <0E><0A><00>,<0E><14><00>,<0E><1E><00>` |
| `lna-auto2` | `20 AUTO 10,5` | `<A9> <0E><0A><00>,<0E><05><00>` |
| `lna-delrng` | `20 DELETE 10-20` | `<A8> <0E><0A><00><F2><0E><14><00>` |

🔴 **`lna-auto2` says "line-number verb" is the wrong name for the mechanism.**
`AUTO 10,5`'s second argument is an **increment**, not a line number, and it is
stored as `$0E,5` anyway. Nothing here knows what the argument *means*; it is a
MODE over digit runs, exactly as D-LNLIST measured.

---

## 2. R-V — how big a single line-number reference may be

The second filed item. `lnv` walks the digit ladder and the 65528…65537
boundary **contiguously**; D-LNBLANK's `num-max`/`num-over`/`num-huge` sampled
three values and could not have located a cut.

| row | typed | both references | zerobas |
|---|---|---|---|
| `lnv-d1`…`d5` | `GOTO 1` … `GOTO 12345` | one reference, exact | agrees |
| `lnv-d6` | `20 GOTO 123456` | `<0E>90` `<0E><06><00>` = **12345 ∥ 6** | `<0E>@<E2>` = 57920 |
| `lnv-d7` | `20 GOTO 1234567` | **12345 ∥ 67** | 54919 |
| `lnv-d8` | `20 GOTO 12345678` | **12345 ∥ 678** | 24910 |
| `lnv-b28` | `20 GOTO 65528` | `<0E><F8><FF>` = 65528 | agrees |
| `lnv-b29` | `20 GOTO 65529` | `<0E><F9><FF>` = 65529 | agrees |
| `lnv-b30` | `20 GOTO 65530` | `<0E><99><19>` `<0E><00><00>` = **6553 ∥ 0** | 65530 |
| `lnv-b31`…`b35` | `65531` … `65535` | **6553 ∥ 1** … **6553 ∥ 5** | 65531 … 65535 |
| `lnv-b36` | `20 GOTO 65536` | **6553 ∥ 6** | 0 |
| `lnv-b37` | `20 GOTO 65537` | **6553 ∥ 7** | 1 |
| `lnv-huge` | `20 GOTO 99999` | **9999 ∥ 9** | 34463 |
| `lnv-huge2` | `20 GOTO 100000` | **10000 ∥ 0** | 34464 |
| `lnv-mega` | `20 GOTO 655290` | **65529 ∥ 0** | 65466 |
| `lnv-zero`^ | `20 GOTO 0` | `<0E><00><00>` | agrees |
| `lnv-lead0`^ | `20 GOTO 0010` | `<0E><0A><00>` | agrees |
| `lnv-lead00`^ | `20 GOTO 00000010` | `<0E><0A><00>` | agrees |

**R-V.** A line-number reference takes another digit only while the resulting
value would stay **≤ 65529**. The first digit that would exceed it terminates the
reference *without consuming it*; the mode is still armed, so that digit begins a
**new** reference.

Equivalently, and this is how it is implemented: **stop when the accumulator has
already reached 6553**, because `v*10 + d > 65529 ⟺ v ≥ 6553` for `d ≤ 9`.

* `lnv-lead00` is the row that says the rule is the **VALUE and not the digit
  count**: eight digits, no split, because the value never leaves 10.
* **65529 is the same constant as the LEADING line number's ceiling**
  (D-LNBLANK R4). The *response* differs: a leading number past 65529 is
  **refused** with `Syntax error`; a reference past it is **split**.
* No refusal, no saturation, no 16-bit wrap. zerobas does the wrap, and it is
  the only one of the four behaviours that is silent.

### 2.1 R-V meets its neighbours (`lnv2`)

| row | typed | both references | zerobas |
|---|---|---|---|
| `lnv2-blk29`^ | `20 GOTO 6 5 5 2 9` | `<0E><F9><FF>` — R5 reaches 65529, no split | agrees |
| `lnv2-blk30` | `20 GOTO 6 5 5 3 0` | `<0E><99><19>`␣`<0E><00><00>` | `<0E><FA><FF>` |
| `lnv2-listbig` | `20 LIST 99999` | `<93> <0E><0F>'<0E><09><00>` | `<93> <1D>E<99><99><90>` |
| `lnv2-onbig` | `20 ON A GOTO 99999,1` | `<95> A <89> <0E><0F>'<0E><09><00>,<0E><01><00>` | one `$0E` |
| `lnv2-erlbig` | `20 IF ERL=99999 THEN 1` | `<8B> <E1><EF><0E><0F>'<0E><09><00> <DA> …` | a float literal |

🔴 **`lnv2-blk30` pins where the split happens relative to the blank, and a
naive implementation gets it wrong.** The reference keeps the **space** between
the two references. D-LNBLANK R5's blank lookahead commits to the whole run once
it sees a digit past it — so a ceiling tested *on the digit* would already have
swallowed the blank and stored `<0E><99><19><0E><00><00>` with no space. **The
ceiling has to be tested before the character is fetched at all**, which is the
one placement that reproduces every row in §2 and this one.

* `lnv2-listbig` is the cross-product row: a **split under a newly-armed verb**.
  It cannot go green unless *both* rules land.
* `lnv2-onbig` is the trap-parser row: the reference genuinely gives
  `ON A GOTO` **three** `$0E` slots where the user wrote two.

---

## 3. What it costs at run time (`lnrd`, say mode)

| row | program | both references | zerobas |
|---|---|---|---|
| `lnrd-ctl`^ | `IF 0 THEN A=1 ELSE A=2` | `2 0` | agrees |
| `lnrd-then`^ | `IF 1 THEN 20 ELSE 30` | `20 0` | agrees |
| **`lnrd-else`** | `IF 0 THEN 20 ELSE 30` | `30 0` | 🔴 **`0 2` — Syntax error** |
| `lnrd-erlctl`^ | handler, no `ERL` compare | `9 21` | agrees |
| **`lnrd-erl`**^ | `40 IF ERL=20 THEN A=1` | `1 21` | **agrees — MUST NOT BREAK** |
| `lnrd-list`^ | `10 A=1:LIST 20:A=2` | `1 0` | agrees |
| `lnrd-return` | `40 RETURN 30` | `30 0` | `20 0` |

* 🔴 `lnrd-else` is the live defect. `IF … ELSE <line>` raises **`Syntax
  error`** on zerobas today, on a program shape the interpreter already has code
  for.
* `lnrd-erl` is the **guard**, and it is green *before* the change. Arming `ERL`
  puts a `$0E` where `ev_f` has no arm; if the evaluator is not taught, this row
  is what goes red.
* `lnrd-return` is a **different, separate gap**: `ex_return`
  ([`basic/program.asm:1089`](../basic/program.asm:1089)) pops the frame and
  never looks at its argument, so `RETURN <line>` returns to the caller. The
  crunch fix does not close it and **this row is expected to stay divergent** —
  measured so the claim is a measurement rather than a guess.

⚠️ **Apparatus: the `lnrd` rows are not covered by `make lnblank-echo`.** The
probe drops `SAY_ONLY` rows from the echo pass by construction
([`basic_probe_lnblank.py`](../probes/basic/basic_probe_lnblank.py), `sel = [c
for c in sel if args.say or c[0] not in SAY_ONLY]`). All seven were guarded by
calling the probe's own `run_side(..., echo=True)` on exactly those rows —
**`ECHOED` on all three sides** — and the standing weaker guard is the say
reader's own anchor, which returns `<none>` when the last typed line's echo is
missing. This is the same un-gated `--say` surface `TODO.md` already files under
`dir-name`.

---

## 3.1 🎯 The sweep that FILED the defect confirms it closed

`make sysvarsweep` after the change, reading the very cells D-REHOME filed the
`GOTO 99999` item from:

```
ONELIN  s7-fired   SAME-VAR   refs=0000->1c80   zb@pub=0000->1c80
ARYTAB  s7-fired   SAME-VAR   refs=0380->2480   zb@priv=0380->2480
```

Both sides now agree exactly, where D-REHOME measured `$801C` vs `$8019` and
`$8024` vs `$8021` — a 3-byte gap on both pointers. **Neither variable was ever
at fault**, exactly as that item said; the text they point into is the right
length now. This is an *independent* confirmation: the sweep was not told what
changed, and it is the same instrument that produced the original reading.

---

## 4. Byproducts of the walk — measured, filed, NOT fixed here

* **`DEFINT` stores different bytes from the reference.** `20 DEFINT 10` reads
  `<AC> <0F><0A>` on both references and `<97>INT <0F><0A>` on zerobas. This is
  a *deliberate* zerobas design — [`basic/kwtable.inc:140`](../basic/kwtable.inc:140)
  emits `DEF_TOKEN` + literal `"INT"` so `ex_def_type` sees the ASCII mnemonic —
  and the same shape as `DEFSNG`/`DEFDBL`/`DEFSTR`, which have no entry at all.
  Neither side arms line-number mode, so it is not this defect. The walk newly
  pins the reference's own bytes: `DEFSTR $AB`, `DEFINT $AC`, `DEFSNG $AD`,
  `DEFDBL $AE`.
* **Twenty-five reference token bytes are now oracle-locked** for the words
  zerobas has no entry for — `RENUM $AA`, `DELETE $A8`, `AUTO $A9`, `LLIST $9E`,
  `LPRINT $9D`, `WAIT $96`, `FN $DE`, `COPY $D6`, `SET $D2`, `IPL $D5`,
  `CMD $D7`, `LFILES $BB`, `DSKI$ $EA`, `DSKO$ $D1`, `ATTR$ $E9`,
  `LPOS $FF,$9C`, `MKS$ $FF,$AF`, `MKD$ $FF,$B0`, `CVS $FF,$A9`, `CVD $FF,$AA`,
  `LOC $FF,$AC`. The keyword-gap item inherits these.
* **`INPUT$` is not absent at all.** `20 INPUT$ 10` reads `<85>$ <0F><0A>` on
  **all three sides**: the reference has no distinct `INPUT$` token either, so
  zerobas' `INPUT` + literal `$` is already byte-exact. One of the 25 words the
  coverage sweep counts as absent is absent only from the *table* — the same
  shape as the `INTERVAL` retraction, found here by the walk.
* 🔴 **The keyword gap and this defect are coupled, and the coupling is a
  trip-wire.** `DELETE`/`AUTO`/`RENUM`/`LLIST` arm on the reference. Whoever
  adds those keywords must also add the arming byte, or this defect comes back
  for four verbs. `lnrx-delete`/`-auto`/`-renum`/`-llist` and
  `ref-delete`/`-auto`/`-renum` are pinned as `KNOWN_DIVERGE` to zerobas' exact
  current bytes for exactly that reason: the moment a token lands, the pin stops
  matching and the gate goes red.
