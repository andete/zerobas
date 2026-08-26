# D-EVFERR — predictions, WRITTEN BEFORE THE PROBE RAN

Pinned 2026-08-26, before `scratchpad/evferr_probe.py` was run once.
Walls read from clean on `423d298`: main page-0 low **45 B**, main page-1
**107 B**, sub p0 2464 B, sub p1 1622 B.

## 0. What the source says before any machine boots

`grep -rnE '^\s+(jp|jr)\s+(z,|nz,|c,|nc,)?ev_f_err'` over `basic/` and `sub/`
finds **SEVEN** instructions, not eight — D-MISSOPFIX converted `:556` to
`ev_f_missop`. And **two of the seven are not assembled**: `expr.asm:2032/2037`
sit inside `IF !G8_RESIDENT` and `basic/sysvars.inc:475` is
`G8_RESIDENT equ 1`. So the live set is **FIVE**:

| site | reached by | filed reading |
|---|---|---|
| `expr.asm:813` | `ev_f_paren`: `(expr` not closed by `)` | zb 0, refs 2 — LIVE |
| `expr.asm:1101` | `EOF(n)`, n a **device/cassette** channel | "agrees at 59" |
| `expr.asm:1122` | `LOF(n)`, same | "agrees at 59" |
| `expr.asm:1886` | `VARPTR` with no `(` | "agrees at 2" |
| `expr.asm:1890` | `VARPTR(<not a name>)` | "agrees at 2" |

🔴 **THE FILED REASON FOR THE BASE PAIR IS WRONG EVEN THOUGH ITS CONCLUSION
HOLDS.** TODO/§14.1 say *"those two sites are never reached: BASE is descoped and
carries its own inline `ERRMARK` body"*. BASE has **not** been descoped since
graphics slice G8 — `ev_f_base` is resident in `basic/graphics.asm:1292` and
raises `gfx_syntax` (ERR 2) for both malformed forms. The expr.asm stub the
filing describes is **not in the ROM at all**. Right answer, dead reasoning.

## 1. The SECOND CAUSE OF GREEN each "agrees" row needs

- `A=VARPTR 5` / `A=VARPTR(5)`: `ev_f_err` is silent and leaves the cursor
  UNADVANCED, so `5` / `5)` is a leftover token and **`es_noentry` raises the
  ERR 2** — the generic trailing-token layer, not the expression layer.
  **SEPARATOR: a form with nothing left over.**
- `A=EOF(0)` / `A=LOF(0)`: `fch_check` sends channel 0 to `err_notopen_raise`
  (ERR 59) **before** `fch_mode_class` runs, so `:1101`/`:1122` are never
  reached by those rows at all. **SEPARATOR: an OPEN device channel.**
- `A=BASE 5` / `A=BASE(0`: answered by `gfx_syntax` in graphics.asm; the expr
  sites are not assembled. **SEPARATOR: a form with nothing left over.**

## 2. Row-by-row predictions (`ERR`; 0 = the statement COMPLETED)

| row | statement | refs | zb | claim |
|---|---|---|---|---|
| `p.noclose` | `A=(1+2` | 2 | **0** | filed LIVE, re-verify |
| `p.colon` | `A=(1+2:B=3` | 2 | **0** | same site, terminator `:` |
| `p.nested` | `A=((1+2)` | 2 | **0** | same site, one level in |
| `p.print` | `PRINT(1+2` | 2 | **0** | a different consumer, same site |
| `p.ok` | `A=(1+2)` | 0 | 0 | control |
| `v.nopar` | `A=VARPTR 5` | 2 | 2 | agrees — via `es_noentry` |
| `v.nopareol` | `A=VARPTR` | 2 | **0** | 🔴 NEW LIVE — separator for `v.nopar` |
| `v.badarg` | `A=VARPTR(5)` | 2 | 2 | agrees — via `es_noentry` |
| `v.badargeol` | `A=VARPTR(` | 2 | **0** | 🔴 NEW LIVE — separator for `v.badarg` |
| `v.noclose` | `A=VARPTR(B` | 2 | **5** | filed LIVE, re-verify |
| `v.nocloseset` | `B=1:A=VARPTR(B` | 2 | 2 | separator: the divergence is the UNSET ordering only |
| `v.ok` | `B=1:A=VARPTR(B)` | 0 | 0 | control |
| `e.eofdev` | `A=EOF(0)` | 59 | 59 | agrees — `fch_check`, site not reached |
| `e.eofcrt` | `OPEN"CRT:"...:A=EOF(1)` | 5 | **0** | 🔴 NEW — separator, reaches `:1101` |
| `e.lofcrt` | `OPEN"CRT:"...:A=LOF(1)` | 5 | **0** | 🔴 NEW — separator, reaches `:1122` |
| `e.crtok` | `OPEN"CRT:"...:PRINT#1,"X"` | 0 | 0 | control: the OPEN itself works |
| `b.nopar` | `A=BASE 5` | 2 | 2 | agrees — `gfx_syntax` |
| `b.nopareol` | `A=BASE` | 2 | 2 | separator: still 2, because BASE is RESIDENT |
| `b.openeol` | `A=BASE(` | 2 | 2 | `gfx_syntax` beats the deferred ERR 24 |
| `b.ok` | `A=BASE(0)` | 0 | 0 | control |

**Predicted: 8 DIFF of 20** — 2 filed + 5 new + `v.noclose`'s own.
Predicted NEW live sites: `:1886`, `:1890`, `:1101`, `:1122`.
Predicted sites already correct: none of the five.

## 3. The design these predictions imply, if they hold

`vptr_close` (`expr.asm:1951`) already carries the cure and says so in its own
comment: *"the CHECKED deferred FPERR=4 syntax error, not the bare ERRMARK
`ev_f_err` ... **Byte-neutral vs `ev_f_err`**"*. Every site above whose reference
answer is **2** is a `jp nz,ev_f_err` → `jp nz,ev_f_empty` retarget, **0 B each**.
`ev_f_err` then keeps only the sites whose reference answer is NOT a syntax
error, which is the split by MEANING TODO:1069 asks for.

---

# ROUND 2 — predictions for the LAST DIFF, pinned before the rows ran

After the five retargets: **26 scored, 1 DIFF** — `v.noclose` (`A=VARPTR(B`,
B unset) is zb **5**, refs **2**, and `v.nocloseset` (`B=1:A=VARPTR(B`) is 2 on
all three. So the divergence is an ORDERING one: zerobas answers the operand's
DOMAIN error, the references answer the form's SYNTAX error.

🔴 **BEFORE PRICING A FIX AT `vptr_unset`, ASK WHETHER THE RULE HAS OTHER
MEMBERS** — *out of scope for the FIX is not out of scope for the DENOMINATOR*
([[a-row-written-off-as-out-of-scope-leaves-the-bookkeeping]]). Two candidates,
one arm over and one type over, and `vptr_none` carries its own untested
justification for declining the very check at issue: *"no `')'` check (it could
only raise a masking second error)"*.

| row | statement | refs | zb | why |
|---|---|---|---|---|
| `d.arybadsub` | `DIM Z(2):A=VARPTR(Z(9)` | **2** | **9** | if refs say 2, `vptr_none`'s justification is false and the class is WIDER than `vptr_unset` |
| `d.arybadsubok` | `DIM Z(2):A=VARPTR(Z(9))` | 9 | 9 | control |
| `d.strunset` | `A=VARPTR(B$` | **2** | **5** | same class as `v.noclose`, one TYPE over — a fix at `vptr_unset` covers it for free |
| `d.strunsetok` | `A=VARPTR(B$)` | 5 | 5 | control (D-VPTRDOM: an unset scalar is IFC) |

## The fix, if `d.arybadsub` reads 9/9

`vptr_unset` runs the close check first: `call ev_sp / cp ')' / jp nz,ev_f_empty`
ahead of its `ld e,3 / jp ev_f_defer`. **+8 B** of main page 1 (107 → 99).

⚠️ **NOT `call vptr_close`, WHICH WOULD BE 5 B CHEAPER.** Every factor error path
ends in `ret` **to the factor's caller**, so a `call` here puts one frame between
`ev_f_err`'s `ret` and the address it means to land on. It does unwind correctly
— through a second pass over the tail — and that is precisely the accident
[[abort-chain-returns-into-caller]] records twice as a measured failure.

---

# KNIFE PREDICTIONS, pinned before `scratchpad/evferr_knives.py` ran

Six size-neutral-or-deleting cuts, each with its row set named in advance. Three
claims, and they are different:

| knife | cut | predicted to move | the claim |
|---|---|---|---|
| K-EV1 | `ev_f_paren` back to `ev_f_err` | the 6 `p.*` rows → **0** | the site is LOAD-BEARING; reverting it re-creates COMPLETES-SILENTLY |
| K-EV2 | `ev_f_paren` → `ev_f_missop` | the 6 `p.*` rows → **24** | the CODE is a measured choice, not "any deferred error" |
| K-EV3 | VARPTR's missing-`(` → `ev_f_err` | `v.nopareol` → **0** only | NARROWNESS: one site, ONE row — and NOT `v.nopar`, which answers 2 through `es_noentry` regardless |
| K-EV4 | VARPTR's not-a-name → `ev_f_err` | `v.badargeol` → **0** only | the mirror of K-EV3: the two VARPTR sites are separate decisions |
| K-EV5 | EOF's `ev_f_ifc` → `ev_f_empty` | `e.eofcrt` → **2** only | 5-vs-2 is measured; and it separates EOF's site from LOF's |
| K-EV6 | delete `vptr_unset`'s close check | `v.noclose` **5**, `d.strunset` **5** | the ordering fix serves BOTH members of its class and nothing else — in particular **NOT** `d.arybadsub`, whose 9 is correct |

🔴 **K-EV3/K-EV4 ARE THE ONES THIS ITEM EXISTS FOR.** A knife that reddened
`v.nopar`/`v.badarg` would mean the separator rows were not separating, and the
whole §2 finding would be an artefact.
