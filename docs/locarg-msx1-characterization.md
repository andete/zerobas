# D-LOCARG — what LOCATE does with an argument it cannot use

*Measured 2026-08-09 on a **Philips VG-8020** and a **National CF-3300**, and on
zerobas, by `make locarg-characterize`
([`probes/basic/basic_probe_locarg.py`](../probes/basic/basic_probe_locarg.py)).
45 rows, three sides, **both references agreeing on every one** — so every
divergence below is zerobas's.*

Clean-room: BASIC typed into two reference machines and into zerobas, screen
output read back from VRAM. No reference ROM was disassembled or decoded.

---

## 1. The question, and the four rows that could not answer it

[`spec-basic-evalchk.md`](spec-basic-evalchk.md) §6.6 measured four rows against
`LOCATE`, found one divergence, priced a **−29 B** carve that would fix it, and
declined:

> *…LOCATE's own denominator (row/column, omitted arguments, the `CON_LASTROW`
> clamp, `CSRLIN`/`POS` read-back), none of which this probe has.*

That decline was right about the arithmetic — four rows are not a denominator —
and **wrong about the inventory**.

## 2. 🔴 THE DENOMINATOR IT ASKED FOR WAS ALREADY BUILT, AND HAD BEEN FOR WEEKS

`make missing-acceptance`
([`probes/basic/basic_probe_missing.py`](../probes/basic/basic_probe_missing.py))
is **214 recorded rows**, and its `locate` / `locerr` / `locrow` / `xchk`
batteries cover **every axis §6.6 named**:

| axis §6.6 called missing | where it already was |
|---|---|
| row / column | `locate` (24 rows, marker on a screen grid) |
| omitted arguments | `loc-col-only`, `loc-row-only`, `loc-bare-semi`, `le-comma`, `le-comma3` |
| the `CON_LASTROW` clamp | `locrow` (14 rows, scroll-free), `la-row-23/24` |
| `CSRLIN` / `POS` read-back | `xchk` (5 rows, and it says in its own header that it is a *declared* cross-check) |

The axis that genuinely did not exist was the one the carve moves: **a DEFERRED
expression error as an argument**. One axis, not five. 🎯 **A declined carve's
stated blocker can name work that already exists**, because the person pricing
it is reading the file the carve is in, not the gate list. The cheap check —
`grep LOCATE probes/` — costs one command and was not run.

So this slice built the missing axis and **used the existing 214 rows as its
green control set** rather than re-measuring them.

## 3. The rule, as measured

**An argument position is a BYTE ARGUMENT, and a deferred expression error
outranks the coercion's own complaint about it.**

All three columns below are the trapped reading `[ ERR  CSRLIN  POS(0) ]`, taken
inside an `ON ERROR` handler before anything prints. Every program seeds the
cursor with `CLS:LOCATE 7,4` first, so an unchanged cursor reads ` 4  7 ` and is
distinguishable from the CLS home position ` 0  0 `.

### 3.1 The part that was already right — and says so

| row | program | both refs | zerobas |
|---|---|---|---|
| `t.c.div` | `LOCATE 1/0,3` | ` 11  4  7 ` | ` 11  4  7 ` 🟢 |
| `t.c.sqr` | `LOCATE SQR(-1),3` | ` 5  4  7 ` | ` 5  4  7 ` 🟢 |
| `t.c.b5div` | `LOCATE 256+0*(1/0),3` | ` 11  4  7 ` | ` 11  4  7 ` 🟢 |

`fac_to_int_strict` does not CLEAR `FPERR`, so a deferred fault that does **not**
overflow int16 survives the coercion and is reported. `t.c.b5div` is the sharp
one: the value is out of the BYTE range too, and the fault still outranks the
`Illegal function call` that stage would have raised. Carried as a **negative
control** — a carve that fixed the next table by *adding* a check rather than by
*ordering* one would move it.

### 3.2 🔴 The part that was wrong, at every argument site

| row | program | both refs | zerobas before |
|---|---|---|---|
| `t.c.ovdiv` | `LOCATE 70000+0*(1/0),3` | ` 11  4  7 ` | ` 6  4  7 ` |
| `t.c.ovsqr` | `LOCATE 70000+0*SQR(-1),3` | ` 5  4  7 ` | ` 6  4  7 ` |
| `t.r.ovdiv` | `LOCATE 5,70000+0*(1/0)` | ` 11  4  7 ` | ` 6  4  7 ` |
| `t.u.ovdiv` | `LOCATE 5,3,70000+0*(1/0)` | ` 11  4  7 ` | ` 6  4  7 ` |
| `t.om.ovdiv` | `LOCATE ,70000+0*(1/0)` | ` 11  4  7 ` | ` 6  4  7 ` |
| `u.ovdiv` | `LOCATE 70000+0*(1/0),3`, **untrapped** | `Division by zero in 10` | `Overflow in 10` |

🎯 **`t.c.ovsqr` IS WHY THIS IS A RULE AND NOT "DIVISION BY ZERO IS SPECIAL".**
It faults with a **different code** (5, from `SQR(-1)`) through the identical
shape, and the references report *that* code. A fix that hard-coded 11 would
pass five of these six rows.

🎯 **`t.om.ovdiv` reaches the row argument through an OMITTED column**, which is
the only way to exercise `loc_next`'s second call site without a first argument
having been accepted first. `t.u.ovdiv` does the same for the third.

### 3.3 The grid the rule sits in — all green on all three sides

Per argument (column / row / cursor), reached directly or through an omission:
`>255` and negative are `Illegal function call` (5); past int16 is `Overflow`
(6); a string is `Type mismatch` (13); an absent one is **`Missing operand`
(24)** — a distinct error from `Syntax error`, and measured as such at
`LOCATE`, `LOCATE 5,`, `LOCATE 5,3,` and `LOCATE 5,3,:`.

**And the cursor did not move on any of them** — ` 4  7 ` in every row of the
table. That is the batch-then-apply rule, read directly rather than inferred
from where a message happened to print.

The one row where the cursor **does** move on an error is `t.four`
(`LOCATE 1,1,1,1` → ` 2  1  1 `): a fourth argument finds the first three
already applied. Carried as a negative control, because it is exactly the
ordering a carve could quietly flatten.

## 4. 🔴 The row this slice found and did NOT fix

| row | program | both refs | zerobas |
|---|---|---|---|
| `t.tmfp` | `LOCATE STR$(1/0),3` | ` 11  4  7 ` | ` 13  4  7 ` |

Both deferred flags are live at the coercion: a numeric fault (`FPERR` = 11,
from the `1/0` inside `STR$`) and a type fault (`TMISMATCH`, from the string
that came back). The references report the **numeric** one. zerobas reports the
type one — **before and after the carve alike**, because the test order is the
same either way.

🎯 **`t.c.str` IS WHAT MAKES THIS READABLE.** A type fault with *no* pending
numeric one is ` 13 ` on all three sides. So the claim is narrow: a pending
numeric fault outranks the type test too — the same rank rule as §3, one level
up.

It is **DEFERRED with a price** and the price is not the reason.
[`spec-basic-locarg.md`](spec-basic-locarg.md) §7 has the numbers; the short
version is that the order belongs to `check_expr_errors`, which has four other
callers, and D-EVALCHK §5.1 froze it as a *forced constraint* on the strength of
a row (`PRINT #A$,"X"`) that has a type fault and **no** pending numeric one —
i.e. a row that cannot discriminate. **A constraint can be frozen by a row that
does not test it.**

## 5. Where zerobas stands

**Before: 38/45. After: 44/45**, with `t.tmfp` printed and not scored.

`make missing-acceptance` reads **214/214 as recorded** before and after — the
carve moved nothing in LOCATE's position, clamp, omitted-argument or read-back
surface.

## 6. The denominator

(WHICH argument: column / row / cursor, each reached DIRECTLY or through an
OMITTED earlier one) × (WHICH fault: in range, >255, negative, >int16, string,
missing operand, a 4th argument, a DEFERRED expression error) × (whether the
deferred fault ALSO overflows int16 — the discriminator between *reported for
the right reason* and *reported because nothing overwrote it*) × (WHICH deferred
code: 11 from `1/0` vs 5 from `SQR(-1)`) × (the CURSOR side effect on every row)
× (TRAPPED vs UNTRAPPED, the second reading the message text, its line number,
and whether it printed **once**).

**Four positive controls** (`t.ok`, `t.c.256`, `u.ok`, `u.bare`) — two per
reading, because the two readings can fail independently. Their four expected
strings were written down before the first run and **all four landed exactly**.
**Four negative controls** (`t.c.str`, `t.bare`, `t.four`, `t.c.b5div`),
declared before the run, all four still green after the carve.

The position / clamp / omitted-argument axes are deliberately **not** re-measured
here: they are `make missing-acceptance`.

## 7. Why the untrapped battery exists

The block the carve deletes carried a warning about what a wrongly-framed abort
looked like, quoted from the gate that caught it:

```
LOCATE          zb: missing operand / missing operand
LOCATE "5",3    zb: type mismatch / missing operand
```

— two messages for one statement, the handler carrying on parsing after the
abort had already printed. That claim had been retired by `4d35b6d` (aborts
reset `SP` from `SAVSTK` and are depth-independent), but **a refuted claim is
not the same as an unmeasured one**. The eleven `u.*` rows run every abort class
untrapped and read the whole screen tail, so a second message — or a `[RANON]`
that should never print — is a red row rather than a silent one. All eleven are
green on all three sides through the new `call`.
