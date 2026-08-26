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
