# SCOUT — `DEF FN`, the last missing MSX1 reserved word, measured instead of asserted

Status: **MEASUREMENT ONLY. No code changed.** 2026-08-22, from `4b2c5a5`.
Probe: [`scratchpad/deffn_scout.py`](../scratchpad/deffn_scout.py) + `.out`,
four rounds, VG-8020 + CF-3300 + zerobas, boot-per-case. **The two references
agree on every row.**

---

## 1. Why this, and why now

`make kwsweep` at HEAD: **`MISSING=1`**, and it is `deffn` —

    DEF FNA(X)=X+1:PRINT"[";FNA(2);"]"     ref `[ 3 ]`     zb `Syntax error in 10`

the only genuinely missing MSX1 reserved word, on a charter of **faithful full
MSX1 BASIC**. `TODO.md` has carried its price since the gap sweep as

> *an arc, not a slice (200–400 B): a definition table, argument binding,
> re-entrant evaluation*

which is an **assertion that has never been measured**. SCREEN 3 sat in exactly
that position — *"unpriced, NEVER SCOUTED"* — until it was priced and **fit**.
This scout does not price the implementation (nothing has been assembled, and a
size from arithmetic is not a measurement). It establishes the two things a price
has to be built on: **what the reference stores**, and **what it does**.

---

## 2. 🎯 The crunch — `FN` is ONE token, and it is the byte after `USR`

Stored program bytes, read from `TXTTAB` (`$F676`) in **direct mode**:

| program | both references |
|---|---|
| `10 DEF FNA(X)=X+1` | `97 20 DE 41 28 58 29 EF 58 F1 12 00` |
| `10 DEF FNQZ(Y)=Y*2` | `97 20 DE 51 5A 28 59 29 EF 59 F3 13 00` |
| `10 DEF USR=&HC000` | `97 20 DD EF 0C 00 C0 00` |

    97 = DEF   DE = FN   DD = USR   EF = '='   $11..$1A = the constants 0..9

> **`FN` is a single token, `$DE` — the byte immediately after `USR`'s `$DD`,
> which this tree already emits and already dispatches (`ex_def`, `ev_f_usr`).**

🔴 **And the NAME is stored as plain ASCII after the token** — `41` for `A`,
`51 5A` for `QZ` — arbitrary length, exactly like a variable name. **There is no
name table in the crunch.** That already contradicts the first third of the filed
price: the reference does not build "a definition table" at tokenise time; it
reads the name out of the program text at run time, like every other identifier.

Here, with no `FN` row in `basic/kwtable.inc`, the same line crunches to

    97 20 46 4E 41 28 58 29 EF 58 F1 12 00      ("F" "N" as ASCII)

— **one byte longer per occurrence**, which is exactly what the missing token
costs, and it is why `DEF` reaches `stmt_error`. `basic/usr.asm`'s own comment
already names the hook: *"Anything after DEF that is not USR (incl. DEF FN) hits
stmt_error."*

🟢 Two controls, `DEF USR` and a plain array reference, are **byte-identical on
all three sides**, so the dumper and the `DEF` path are sound and every
divergence above is about `FN`.

---

## 3. ✅ The surface — measured, and larger than the filed line implied

Both references agree on every row. zerobas is either `Syntax error` or, worse,
a **silent 0**.

| case | program | both refs | zerobas |
|---|---|---|---|
| parameter is **saved and restored** | `X=5:DEF FNA(X)=X+1` `:Y=FNA(2)` → `Y;X` | **`3 5`** | ERR 2 |
| …an unset parameter restored to 0 | `DEF FNA(Q)=Q+1:Y=FNA(7)` → `Y;Q` | **`8 0`** | ERR 2 |
| **two** parameters | `DEF FNA(X,Y)=X+Y` → `FNA(2,3)` | **`5`** | ERR 2 |
| **no** parameter | `DEF FNA=7` → `FNA` | **`7`** | ERR 2 |
| string-typed | `DEF FNA$(X$)=X$+"!"` → `FNA$("hi")` | **`hi!`** | ERR 2 |
| redefinition — last wins | `DEF FNA(X)=X+1` `:DEF FNA(X)=X+2` → `FNA(1)` | **`3`** | ERR 2 |
| **nested** — FN calling FN | `DEF FNB(X)=FNA(X)*2` → `FNB(3)` | **`8`** | ERR 2 |
| direct recursion | `DEF FNA(X)=FNA(X)` → `FNA(1)` | **ERR 7** | ERR 2 |
| undefined function | `FNZ(1)` | **ERR 18** | **`0`** |
| defined on a LATER, unexecuted line | `GOTO`-past the `DEF`, then `FNA(2)` | **ERR 18** | **`0`** |

🎯 **THE PARAMETER IS NOT CLOBBERED.** `X` is still **5** after `FNA(2)` was
called with `X` as the formal parameter. Classic Microsoft BASIC binds straight
through the variable table and leaves `X = 2`; MSX BASIC does not. **A save and
restore is required, and that is a design fact no manual reading would have
settled.**

🎯 **DIRECT RECURSION IS ERR 7 (`Out of memory`), not a refusal** — so the
reference's evaluation is genuinely re-entrant and simply runs the stack out.
That is the one part of the filed price the measurement **confirms**.

🔴 **AND THE TWO ERR 18 ROWS ARE A SILENT WRONG ANSWER HERE.** `FNZ(1)` is
`Undefined user function` on both references and reads **`0`** on zerobas —
parsed as an ordinary subscripted reference. This project ranks a silent wrong
answer worse than the refusal beside it, and `ERR 18` **already ships**:
`interp.asm`'s `err_msgtab` entry 18 and `sub/errmsg.asm`'s `em_undef_fn`
(`"Undefined user function"`) are both present and reachable today.

---

## 4. What this changes about the filed price

| filed | measured |
|---|---|
| "a definition table" | ❌ no table in the crunch — the name is ASCII in the program text, read at run time |
| "argument binding" | ✅ **and more than filed**: 0, 1 or 2+ parameters, string-typed, and the formal **must be saved and restored** |
| "re-entrant evaluation" | ✅ confirmed — recursion runs to ERR 7 |
| (unstated) | ✅ `ERR 18` and its message already ship |
| (unstated) | ✅ `FN` is one token adjacent to `USR`, whose statement and function paths both already exist |

**No total is claimed.** Nothing has been drafted or assembled, and this project
does not quote a size derived by arithmetic. What can be said is that the two
cheapest-looking components are cheaper than filed and the binding is dearer, and
that the surface to be gated is ten rows wide before any error-ordering work.

⚠️ **It still needs a carve wherever it lands.** `FN` evaluation must call `eval`,
which is main page 1 — and a sub-ROM tenant, page-0 or page-1, cannot reach main
page 1 (`check_sub_walls`' own closure gate). So this is resident code, in page 1
or the co-mapped low region, and **both walls must be read from `make
basic-reloc` at the time, never quoted from here.**

---

## 5. 🔬 Three apparatus faults, and what caught each

* 🔴 **THE READOUT READ THE SOURCE, NOT THE OUTPUT — ELEVEN ROWS, ALL "AGREEING".**
  The fixture ended in `PRINT"[";V;"]"` typed in direct mode, so the line's own
  **echo** sat on screen containing `[";V;"]` and the `[...]` regex found that.
  Every row returned its own program text and every row scored `refs-agree`.
  🟢 **The control caught it**: `b.ctl` is `X+1` with `X=5` and returned
  `'";X+1;"'` instead of `6`. Fixed with the `CLS` the PAINT probes already use.
* 🔴 **A CONTROL THAT FLIPPED WITH ITS SUBJECT UNCHANGED.** `defusr.ctl` read
  byte-identical on all three sides in round 1 and `REFS DIFFER` in round 3, on
  the same program. Nothing about `DEF USR` had moved — the **dump** had, from a
  stored `RUN 100` to a direct-mode command, which put the direct-line buffer and
  uninitialised RAM inside the compared window. The comparison now stops at the
  end-of-program marker, and both controls are identical again.
  🎯 **A control that changes verdict while its subject does not is a statement
  about the instrument**, and it is the only reason the trailing garbage was not
  written up as a machine difference.
* ⚠️ **THE CAPTURE LINE WAS ITSELF A SYNTAX ERROR ON TWO ROWS.** It built
  `60 V=<expr>`, and `b.param`'s expr is `Y;X` — PRINT syntax, not an expression
  — so **both references** reported `ERR 2 AT 60` and the row read as a
  divergence about `DEF FN`. It was a divergence about the harness. The `AT 60`
  is what gave it away: the fault was on the harness's own line, not the
  fixture's.
* ⚠️ **AND THE FIRST DUMP COULD NOT READ ITS OWN SUBJECT.** Round 1 put the
  dumper at lines 100–140 and ran `RUN 100`; on zerobas that printed nothing, and
  the raw screen read `Syntax error in 10` — a line the dump existed to READ
  stopped the dump from running. A stored line this build cannot execute has to
  be read without executing anything.

---

## 6. What is NOT claimed

* **No price, no design, no draft.** The next step is a design that names where
  the definition entry lives and how the formal is saved, and prices it by
  assembling it.
* **Nothing about error ORDERING.** Which fault wins when a `DEF FN` line is
  malformed in more than one way is unmeasured, and D-LINERR's rule says that is
  its own claim.
* **Nothing about `FN` in direct mode**, `DEF FN` inside `IF`, or interaction
  with `DEFINT`/`DEFSTR` type defaults.
* **Nothing about how many parameters are legal.** Two are measured; the ceiling
  is not.
