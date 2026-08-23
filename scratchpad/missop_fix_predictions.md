# D-MISSOP FIX — predictions, written BEFORE the edit

Baseline `4dd24f6`, `7942cc20` / `34bb8554` / `031184d9`, page-1 free 2 B.

## The edit

`ev_f_err` (basic/expr.asm) gains `ld a,FPERR_MISSOP` + `call penderr_set`
(**+5 B**); `fperr_to_err` (basic/interp.asm) gains `db 24` (**+1 B**);
`FPERR_MISSOP` is equated beside `FPERR_STROOM` inside the SAME `IF CLEARPOOL`
so both switch states stay correct (**0 B**).

🎯 **THE FALL-THROUGH IS WHAT MAKES THIS FIVE BYTES AND NOT A NEW TEST.**
`ev_f_defer` already falls into `ev_f_err`, and `penderr_set` is SET-IF-EMPTY
and preserves every register AND the flags — so `ev_f_empty`'s FPERR=4 (ERR 2)
survives the second call unchanged, and only a reach with NO pending code takes
the new 24.

## Cost prediction

**~6 B, and page 1 has 2 — so `make basic-reloc` must FAIL by about 4 B.**
That failure IS the measurement (the T5 spec's own precedent). Predicted
overrun: **4 B** (`-6 vs the ceiling` where clean read `-2`).

## Row predictions — 16 DIFF today

CLOSES (13 → `24`, the four POKE/VPOKE ones keeping their byte at `99`):
`poke.val` `poke.plus` `poke.colon` `vpoke.val` `out.val` `sound.val`
`let.val` `let.plus` `defusr.val` `pset.val` `circle.val` `sprite.val`
`print.val`

CLOSES, less certain (currently ERR 2, reaches ev_f_err through
`ex_let_str`, which CLEARS ERRMARK and lets `check_expr_errors` abort on the
RHS's own deferred code): **`lets.val`** (`A$=`) → `24`.

STAYS RED (predicted MISS — a different abort route, not `ev_f_err`):
**`key.val`** (`KEY1,`, a STRING operand via `str_eval`) and **`midd.val`**
(`MID$(A$,2)=`, its own handler) stay at `2`.

**So: 14 of 16 close, 2 stay.**

## Must NOT move — the 10 green rows

`poke.paren` (ERR 2) and `poke.addr` (ERR 2) are the first-error-wins controls:
if either becomes 24, the set-if-empty argument is wrong and the design fails.
`color.val` / `locate.addr` (optional slots, complete) must still read `0`.
The five hand-written ERR-24 verbs must still read `24`.

## Gates

🔴 **THE ONE THAT CAN SINK IT:** `basic/str-engine.asm`'s backtracking
`jp ev_f_err` sites (`:544`, `:579`) — a string path that falls through
`ev_f_err` BENIGNLY is now poisoned with a pending ERR 24. Predicted: the string
suites stay green because those sites raise anyway, but this is the row set to
watch and I am NOT confident. `unit-test` 59/59 predicted to hold.

---

# BLAST-RADIUS predictions, written BEFORE `scratchpad/missop_blast.py` ran

🔴 Found AFTER the fix shipped, by grepping for actual `jp/jr ev_f_err`
INSTRUCTIONS instead of the symbol: `str-engine.asm`'s five mentions are
HISTORICAL COMMENTS about code converted away long ago, and **every real jump is
inside `expr.asm`** — eight of them. **Only ONE is the missing operand.**

The other seven now defer ERR 24 too, and a missing `)` is the classic
`Syntax error`. Predictions:

| row | statement | site | predicted refs | predicted zb |
|---|---|---|---|---|
| `b.paren` | `A=(1+2` | :807 | `2` | `24` 🔴 NEW DIFF |
| `b.vpnopar` | `A=VARPTR 5` | :1880 | `2` | `24` 🔴 |
| `b.vpbadarg` | `A=VARPTR(5)` | :1884 | `2` | `24` 🔴 |
| `b.vpnoclose` | `A=VARPTR(B` | :1880/4 | `2` | `24` 🔴 |
| `b.basenopar` | `A=BASE 5` | :2026 | `2` | `24` 🔴 |
| `b.basenoclose` | `A=BASE(0` | :2031 | `2` | `24` 🔴 |
| `b.eofdev` | `A=EOF(0)` | :1095 | `5` or `52` (LOW confidence) | `24` 🔴 |
| `b.lofdev` | `A=LOF(0)` | :1116 | `5` or `52` (LOW confidence) | `24` 🔴 |
| `b.parenok` / `b.vpok` / `b.baseok` | well formed | — | `0` | `0` |

⚠️ **ALL EIGHT SITES WERE SILENT BEFORE THE FIX**, so a row reading the wrong
code now was reading NO code before: "different wrong", not "regressed". But it
is not fixed either.

## What the answer decides

* **If the references say 24 at those slots too** → the wide siting is right and
  the shipped 5 B stands.
* **If they say 2** → the tail is TOO WIDE and the fix must move to the single
  `ev_f_var` is_letter-failure site (:556). That design is
  `ev_f_missop: ld e,FPERR_MISSOP / jr ev_f_defer` (**4 B**, the same idiom
  `ev_f_tmm`/`ev_f_ifc`/`ev_f_empty` already use) plus retargeting :556's
  existing `jr nc,` — **cheaper than what shipped, and narrow.**

**I expect the second.** The knives were STOPPED before running rather than
scoring a design this probe may overturn.

---

# 🔴 THE ANSWER ARRIVED FROM A SHIPPED GATE, NOT FROM MY PROBE

Before `missop_blast.py` had run a single case, `make lineerr-acceptance`
returned **209/210 — one row diverging**:

    DIFF a.noclose   vg8020=' 2 , 7 , 4 '  cf3300=' 2 , 7 , 4 '  zb=' 24 , 7 , 4 '

`a.noclose` is `LINE (11,12-(20,21)`. The inner `(20,21)` is a parenthesised
expression closed by a `,` instead of a `)`, which is **site :807** — one of the
seven the blast table predicted. **Both references say ERR 2.** The wide siting
is WRONG, and the prediction ("I expect the second") is confirmed by an
independent 210-row suite that has been shipping since D-LINEERR.

🎯 **MY 26-ROW PROBE COULD NOT HAVE FOUND THIS.** Its denominator is BASIC
VERBS with a trailing value; the defect is in the EXPRESSION GRAMMAR, at a slot
no verb row visits. `lineerr-acceptance`'s `a.*` class sweeps *"every slot that
can END where a value was required"* structurally, through `LINE`'s grammar —
a different axis entirely. **The purpose-built instrument had a hole the
standing gate did not.**

## The narrowing

    ev_f_missop:  ld   e,FPERR_MISSOP     ; +2 B   the SAME idiom ev_f_tmm /
                  jr   ev_f_defer         ; +2 B   ev_f_ifc / ev_f_empty use
    expr.asm:556  jr nc,ev_f_err -> jr nc,ev_f_missop     0 B (same instruction)
    ev_f_err:     reverted to its original 4 instructions  -5 B

**Net vs the wide version: −1 B.** Slice cost 4 B + 1 table byte = **5 B**, and
page-1 free should read **4 B**.

Predicted after narrowing: `a.noclose` back to `2`; the 13 closed rows STAY
closed (all three subject shapes — `\0`, `:`, `+` — reach ev_f via `ev_f_var`'s
`is_letter` failure at :556, checked token-by-token against ev_f's `cp` chain);
every blast row back to its pre-fix value.
