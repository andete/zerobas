<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-EVFERR — splitting `ev_f_err` by MEANING: five sites, ZERO bytes

Status: **✅ SHIPPED.** 2026-08-26, on `423d298`. The open half of THE GENERIC
ERROR-LAYER SEAM (`TODO.md`:1447) and the slice `TODO.md`:1069 asked for by
name: *"`ev_f_err` IS NOW A NAME FOR TWO THINGS ... splitting the label by
MEANING is the shape of the next slice, and each site needs its own reference
reading before it is priced."*

**26 rows × 3 machines, references unanimous on all 26. 11 DIFF → 1.**
`scratchpad/evferr_probe.py`, `evferr_base.out` / `evferr_base2.out` (before),
`evferr_after.out` (after).

---

## 1. The filing was priced off a source reading that had rotted twice

`TODO.md`:1069 says `ev_f_err` is reached by **EIGHT** `jp`/`jr` instructions
and that D-MISSOPFIX served one. Grepping the INSTRUCTIONS on today's tree finds
**SEVEN**, and **two of those are not assembled**:

```
grep -rnE '^\s+(jp|jr|call)\s+(z,|nz,|c,|nc,)?ev_f_err\b' --include='*.asm' --include='*.inc' .
```

`expr.asm:2032`/`:2037` sit inside `IF !G8_RESIDENT`, and
`basic/sysvars.inc:475` is `G8_RESIDENT equ 1`. **The live set is FIVE.**

🔴 **AND THE FILED REASON FOR THAT PAIR IS DEAD, THOUGH ITS CONCLUSION HOLDS.**
`TODO.md` and `spec-basic-missop.md` §14.1 both say *"those two sites are never
reached: BASE is descoped and carries its own inline `ERRMARK` body."* BASE has
not been descoped since graphics slice G8 — the shipping `ev_f_base` is
`basic/graphics.asm:1292` and raises `gfx_syntax`, and the stub the filing
describes **is not in the ROM at all**. The rows still agree; the sentence that
said why does not survive contact with `grep`. Same family as
[[a-justification-parenthesis-is-an-unrun-claim]]: nobody re-runs a parenthesis,
and nobody re-greps a reason.

| site | reached by | reference answer | after |
|---|---|---|---|
| `expr.asm:835` | `ev_f_paren`: `(expr` not closed by `)` | **2** | `ev_f_empty` |
| `expr.asm:1135` | `EOF(n)`, n an OPEN length-less channel | **5** | `ev_f_ifc` |
| `expr.asm:1157` | `LOF(n)`, same | **5** | `ev_f_ifc` |
| `expr.asm:1928` | `VARPTR` with no `(` | **2** | `ev_f_empty` |
| `expr.asm:1932` | `VARPTR(<not a name>)` | **2** | `ev_f_empty` |

---

## 2. 🔴 EVERY "AGREES" ROW IN THE FILING AGREED FOR A REASON OTHER THAN THE SITE

This is the whole method of the slice. The filing recorded five agreeing rows as
evidence about five sites. **Not one of them was a reading about its site**, and
the separator that shows it is one character away in each case
([[a-case-that-agrees-can-agree-for-the-wrong-reason]]).

| filed as "agrees" | its SECOND cause of green | separator | separator's reading |
|---|---|---|---|
| `A=VARPTR 5` → 2 | `ev_f_err` leaves the cursor **UNADVANCED**, so `5` is a leftover token and **`es_noentry`** raises the 2 — the trailing-token layer, not the expression layer | `A=VARPTR` | zb **0**, refs 2 🔴 |
| `A=VARPTR(5)` → 2 | same: `5)` is left over | `A=VARPTR(` | zb **0**, refs 2 🔴 |
| `A=EOF(0)` → 59 | channel 0 goes to `err_notopen_raise` inside **`fch_check`**, one call BEFORE `fch_mode_class`; the site below is never reached | `OPEN"CRT:"FOR OUTPUT AS#1:A=EOF(1)` | zb **0**, refs **5** 🔴 |
| `A=LOF(0)` → 59 | same | `…:A=LOF(1)` | zb **0**, refs **5** 🔴 |
| `A=BASE 5` / `A=BASE(0` → 2 | answered by `gfx_syntax` in the RESIDENT `ev_f_base`; the expr.asm sites are not assembled | `A=BASE` | zb 2, refs 2 ✅ (genuinely correct) |

🎯 **FOUR OF THE FIVE "AGREEING" SITES WERE LIVE DIVERGENCES WEARING A GREEN
ROW.** The agreement was produced by a DIFFERENT LAYER each time — `es_noentry`
for VARPTR, `fch_check` for EOF/LOF, `gfx_syntax` for BASE — which is exactly
what a *neutral* shared tail invites: it returns a defined value and no error, so
whatever is downstream of it gets to answer instead, and the answer is often
right for the rows anyone thinks to type.

---

## 3. The instrument

`scratchpad/evferr_probe.py` — D-TRAPSVC's shape (whole programs,
**boot-per-case**, both references and zerobas, one fenced value per row, a
non-numeric fence rejected as the source echo, [[trapsvc-echo-fence]]), plus
D-SNCAP capture-on-signal: **78 of 78 captures on the program's own signal, 0
fallbacks.** The mark is legal here because the readout is an **error code**, not
an address (`probe_signal` rule 3).

Readout is `[ERR]`: **0 means the statement COMPLETED**, otherwise the MSX error
code. Predictions were pinned in `scratchpad/evferr_predictions.md` before the
probe ran once.

---

## 4. The measurement — 26 rows, 11 DIFF → 1

| row | statement | refs | before | after |
|---|---|---|---|---|
| `p.noclose` | `A=(1+2` | 2 | **0** | 2 ✅ |
| `p.colon` | `A=(1+2:B=3` | 2 | **0** | 2 ✅ |
| `p.nested` | `A=((1+2)` | 2 | **0** | 2 ✅ |
| `p.print` | `PRINT(1+2` | 2 | **0** | 2 ✅ |
| `p.if` | `IF(1 THEN A=2` | 2 | **0** | 2 ✅ |
| `p.for` | `FOR I=(1 TO 3:NEXT` | 2 | **0** | 2 ✅ |
| `p.ok` | `A=(1+2)` | 0 | 0 | 0 ✅ |
| `v.nopar` | `A=VARPTR 5` | 2 | 2 | 2 ✅ |
| `v.nopareol` | `A=VARPTR` | 2 | **0** | 2 ✅ |
| `v.badarg` | `A=VARPTR(5)` | 2 | 2 | 2 ✅ |
| `v.badargeol` | `A=VARPTR(` | 2 | **0** | 2 ✅ |
| `v.noclose` | `A=VARPTR(B` (B unset) | 2 | **5** | **5** 🔴 |
| `v.nocloseset` | `B=1:A=VARPTR(B` | 2 | 2 | 2 ✅ |
| `v.aryunset` | `A=VARPTR(Z(1)` | 2 | 2 | 2 ✅ |
| `v.ok` | `B=1:A=VARPTR(B)` | 0 | 0 | 0 ✅ |
| `e.eofdev` | `A=EOF(0)` | 59 | 59 | 59 ✅ |
| `e.eofcrt` | `OPEN"CRT:"…:A=EOF(1)` | **5** | **0** | 5 ✅ |
| `e.lofcrt` | `OPEN"CRT:"…:A=LOF(1)` | **5** | **0** | 5 ✅ |
| `e.crtok` | `OPEN"CRT:"…:PRINT#1,"X"` | 0 | 0 | 0 ✅ |
| `s.strparen` | `A$=(1+2` | 2 | 2 | 2 ✅ |
| `s.strvp` | `A$=VARPTR 5` | 2 | 2 | 2 ✅ |
| `s.strok` | `A$=(1+2)` | 13 | 13 | 13 ✅ |
| `b.nopar` | `A=BASE 5` | 2 | 2 | 2 ✅ |
| `b.nopareol` | `A=BASE` | 2 | 2 | 2 ✅ |
| `b.openeol` | `A=BASE(` | **24** | 24 | 24 ✅ |
| `b.ok` | `A=BASE(0)` | 0 | 0 | 0 ✅ |

---

## 5. 💰 The price: ZERO BYTES, because every fix was a `jp` already there

All four walls **identical** before and after, read from clean:

```
page-0 low region free = 45 B    page-1 free = 107 B
sub page 0 free = 2464 B         sub page 1 free = 1622 B
```

and `basic-reloc.rom` **moved** (`41b8c4ed` → `6db7c1f0`) with `sub.rom`
unchanged (`ae796ccb`), which is the pair of checks a 0 B claim needs: the wall
says it cost nothing, the hash says it happened
([[apparatus-is-part-of-the-measurement]] — *"a 5 B edit that costs 0 B has not
happened"*, inverted).

`vptr_close` (`expr.asm:1993`) had carried the cure and the price in its own
comment since the arrays slice — *"the CHECKED deferred FPERR=4 syntax error,
not the bare `ERRMARK` `ev_f_err` … **Byte-neutral vs `ev_f_err`**"*. Every site
whose reference answer is a syntax error is that same one-word retarget; the two
whose reference answer is a **value-domain** error take `ev_f_ifc` (FPERR=3 →
ERR 5) instead, which is the idiom's other arm.

The ~6 B that `TODO.md` priced, the page-1 carve it was blocked on, and the
`ev_f_err`-promotion alternative were all **answers to the wrong question**: the
cost was never in the code, it was in not knowing which of five meanings each
site had.

---

## 6. 🎯 `ev_f_err` IS NO LONGER A SHARED TAIL

```
grep -cE '^\s+(jp|jr|call)\s+(z,|nz,|c,|nc,)?ev_f_err\b' basic/expr.asm   ->   0
```

Nothing jumps to it. It is reached **only by fall-through from `ev_f_defer`**,
whose job is to stamp the `$DD` landmark once a code has been deferred — which
is the only thing it was ever *for*. The seven meanings that had accumulated on
it are now seven jumps to three labels that each say one thing:

| label | meaning | sites |
|---|---|---|
| `ev_f_missop` | a factor was REQUIRED and this cannot start one → 24 | 1 (D-MISSOPFIX) |
| `ev_f_empty` | this expression is malformed → 2 | 3 + 2 unassembled |
| `ev_f_ifc` | the operand parsed and its VALUE is out of domain → 5 | 2 |

🔴 **AND THAT IS THE STANDING RULE THE COMMENT NOW CARRIES**: a new
`jp ev_f_err` is a factor choosing to fail with **no error code at all**, which
measured wrong at every one of the seven sites that had made that choice.

---

## 7. The last DIFF was an ORDERING one — and the rule is NARROWER than it looks

After the five retargets: **26 scored, 1 DIFF.** `A=VARPTR(B` with `B` unset was
ERR **5** where both references say **2**, while `B=1:A=VARPTR(B` — the same
missing `)` with the lookup satisfied — was already 2 on all three. So zerobas
answers the operand's DOMAIN error and the references answer the form's SYNTAX
error, and nothing else separates them.

🔴 **BEFORE PRICING A FIX AT `vptr_unset`, THE RULE IT IMPLIES NEEDED ITS OWN
DENOMINATOR** — *out of scope for the FIX is not out of scope for the
BOOKKEEPING* ([[a-row-written-off-as-out-of-scope-leaves-the-bookkeeping]]). Two
candidates: one TYPE over, and one ARM over.

| row | statement | refs | zb | |
|---|---|---|---|---|
| `d.strunset` | `A=VARPTR(B$` | 2 | **5** | 🔴 a SECOND member — same class, string scalar |
| `d.strunsetok` | `A=VARPTR(B$)` | 5 | 5 | ✅ control (D-VPTRDOM: an unset scalar is IFC) |
| `d.arybadsub` | `DIM Z(2):A=VARPTR(Z(9)` | **9** | **9** | ✅ **the rule does NOT extend here** |
| `d.arybadsubok` | `DIM Z(2):A=VARPTR(Z(9))` | 9 | 9 | ✅ control |

🎯 **`d.arybadsub` IS THE ROW THAT SEPARATED TWO RULES THAT COINCIDE ON EVERY
SCALAR CASE** ([[two-rules-that-coincide-on-every-row-you-have]]). I had the
general rule written down — *"syntax outranks domain"* — and it is **wrong**:
the array arm's out-of-range subscript beats the missing `)` on BOTH references,
because an array reference's subscripts are evaluated *while the form is being
parsed*, whereas a scalar is looked up only once the form is known to be well
formed. The narrow rule is the true one:

> **A SCALAR LOOKUP HAPPENS AFTER THE CLOSING `)`, NOT BEFORE IT.**

⚠️ **AND THAT VINDICATED AN UNTESTED JUSTIFICATION RATHER THAN FALSIFYING ONE.**
`vptr_none` declines the very check at issue, in prose, with a reason nobody had
run: *"no `')'` check (it could only raise a masking second error)"*. It is
**correct**, and `d.arybadsub` is the row that says so — the first time that
sentence has been evidence rather than an argument. This is the mirror of
[[a-justification-parenthesis-is-an-unrun-claim]]: running one can confirm it,
and the outcome is not knowable in advance, which is the entire reason to run it.

### 7.1 The fix, and why it is 8 B rather than 3

```
vptr_unset:     call    ev_sp
                cp      ')'
                jp      nz,ev_f_empty       ; malformed close -> Syntax error (2)
                ld      e,3                 ; (unchanged)
                jp      ev_f_defer          ; (unchanged)
```

**+8 B of main page 1: 107 → 99 B**, measured from clean, exactly as priced.

⚠️ **`call vptr_close` WOULD HAVE BEEN 5 B CHEAPER AND WAS DECLINED.** Every
factor error path ends in `ret` **to the factor's caller**, so a `call` here puts
one frame between `ev_f_err`'s `ret` and the address it means to land on. It
*does* unwind correctly — the extra frame is consumed by the first pass through
the tail and re-supplied by the second — and that is precisely the accident
[[abort-chain-returns-into-caller]] records **twice** as a measured failure
(`LOCATE` erroring twice; `WIDTH 300` continuing with the error code as data).
8 B is the price of not repeating it, and 99 B of page 1 can pay it.

**Final: 30 rows × 3 machines, references unanimous, 0 DIFF.**

---

## 8. 🔬 Knives — 5 of 6 EXACT

`scratchpad/evferr_knives.py` / `evferr_knives.out`. Predictions pinned in
`evferr_predictions.md` before the runner ran.

| knife | cut | predicted | moved | |
|---|---|---|---|---|
| K-EV1 | `ev_f_paren` → `ev_f_err` | 6 `p.*` rows → 0 | the same 6 | ✅ EXACT |
| K-EV2 | `ev_f_paren` → `ev_f_missop` | 6 `p.*` rows → 24 | **7** — plus `s.strparen` | 🔴 NOT EXACT |
| K-EV3 | VARPTR missing-`(` → `ev_f_err` | `v.nopareol` only | 1 | ✅ EXACT |
| K-EV4 | VARPTR not-a-name → `ev_f_err` | `v.badargeol` only | 1 | ✅ EXACT |
| K-EV5 | EOF `ev_f_ifc` → `ev_f_empty` | `e.eofcrt` → 2 only | 1 | ✅ EXACT |
| K-EV6 | delete `vptr_unset`'s close check | `v.noclose` + `d.strunset` → 5 | 2 | ✅ EXACT |

**5 of 6 EXACT**, restore byte-exact (`fa720d6a`), `sub.rom` unmoved throughout.

🎯 **K-EV3 AND K-EV4 ARE WHAT THIS ITEM EXISTS FOR.** Each moved exactly ONE
row, and neither moved `v.nopar` or `v.badarg` — the rows the filing cited as
evidence. That is the §2 finding, measured: those two answer 2 through
`es_noentry` whatever the expression layer does, so a knife at their own site
cannot touch them. Had either reddened, the separators were not separating.

🔴 **K-EV6'S ROM IS `6db7c1f0` — BYTE-IDENTICAL TO THE PREVIOUS COMMIT'S IMAGE.**
Deleting the ordering fix reproduces the retarget-only tree exactly, which is an
independent confirmation that §7.1 is those 8 bytes and nothing else.

### 8.1 🔴 K-EV2 FOUND A ROW THE PREDICTION MISSED, AND IT IS THE ONE §6.1 WARNED ABOUT

`s.strparen` (`A$=(1+2`) moved to **24** under K-EV2 and I had predicted it would
not move at all. `missing.asm`'s `els_tc_common` clears `ERRMARK`, evaluates the
RHS numerically and calls `check_expr_errors` — so it reads the **deferred code**,
and the code chosen at `:835` propagates straight through to the string-LET
answer. `spec-basic-missop.md` §6.1 named this path as *"the one that can sink
the design"*; the knife shows it would have sunk a **different** choice than the
one considered. `ev_f_empty` is right there for two independent reasons — the
references say 2, and `A$=(1+2` says 2 — and only the knife separates them.

⚠️ **So `s.strparen` is a LIVE DETECTOR for the code at `:835`, not a control**,
and the shipping row's green is load-bearing rather than incidental
([[a-pinned-divergence-is-a-live-detector]]).


---

## 9. Predictions scored

**Round 1 — 19 of 20 exact. Round 2 — 3 of 4. Knives — 5 of 6.**

**Round 1 — 19 of 20 exact.** The one miss is `b.openeol` (`A=BASE(`): I
predicted `gfx_syntax`'s ERR 2 would beat the deferred missing-operand and
called it 2/2; it is **24 on all three machines**. An AGREEING row, mispredicted
— the deferred FPERR reaches the statement boundary and wins, and both
references agree that an empty `BASE(` slot is *Missing operand*. ⚠️ The
prediction doc's own **tally** said "8 DIFF" while its row table listed **nine**;
the rows were right and the arithmetic beneath them was not. A summary line is
not a prediction, and it is not covered by one either.

**Round 2 — 3 of 4 exact.** The miss is the important one: I predicted
`d.arybadsub` would read **2** on the references (the wide rule) and it reads
**9**. Had that row not been in the set, the fix would have shipped with a
justification stating a rule the tree measurably does not follow — the fix
itself would still have been correct, because it is sited where the narrow rule
lives.

🎯 **BOTH MISSES ARE THE SAME SHAPE: A CLAIM ABOUT WHICH LAYER ANSWERS FIRST,
MADE BY READING CODE.** That is the shape this whole slice is about, and I made
it twice more while writing the slice about it.

---

## 10. Gates

`make gates`, from clean.

---

## 11. What this does NOT establish

* The 26-row set is a **hand-listed sample around five named sites**, which is a
  scope claim and not a coverage one ([[a-hand-listed-denominator-is-a-scope-claim]]).
  Every `ev_f_err` jump instruction in the tree is covered; every *row* that can
  reach one is not.
* **`e.eofcrt`/`e.lofcrt` reach `:1135`/`:1157` through a `CRT:` channel only.**
  The cassette arm of `fch_mode_class`'s NC branch is untested here — it needs a
  tape image and it is the same instruction.
* The two `IF !G8_RESIDENT` sites were retargeted with the rest and **have never
  been assembled**. `make switch-build-check` proves the arm builds; nothing runs
  it.
* `A=VARPTR(B` was fixed at `vptr_unset`. Whether other *factors* look up a name
  before validating their form is not measured — VARPTR is the only one whose
  grammar has a `)` after a bare name.
