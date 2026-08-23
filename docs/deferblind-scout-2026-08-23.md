# SCOUT — D-DEFERBLIND: how wide is "witnessed only by a deferred error"?

2026-08-23, on `aafcaa8`. **Measurement only — no source changed, no ROM byte
moved** (`7942cc20` / `34bb8554` / `031184d9` throughout).

D-DEFFNKNIFE's K-FE1 found a shipped guard with **no witness at all**
([`spec-basic-deffnknife.md`](spec-basic-deffnknife.md) §4): `raise_error`'s
`FN_FEND` reset, named in two source files as proven by `o.errrestore`, and
`o.errrestore` cannot see it because `X/0` is a **deferred** fault. This scout
asks how many more guards are in that state.

---

## 1. 📏 The source split, counted — and the ERR code tells you nothing

`penderr_set` is the deferred-error write (D-PENDERR's first-error-wins cell).
**21 call sites** across `basic/` and `sub/`:

| file | sites |
|---|---|
| `basic/str-engine.asm` | 8 |
| `basic/float-arith.asm` | 6 |
| `basic/expr.asm` | 3 |
| `sub/fp_pow.asm` | 2 |
| `sub/fp_exp.asm` | 1 |
| `basic/arrays.asm` | 1 |

**Exactly ONE of the 21 raises on the spot** — `str_heap_oom_error`
(`str-engine.asm:90`), which follows `call penderr_set` with
`jp fp_runtime_error`. The other **20 return**, and the fault is realized at the
statement boundary.

🔴 **SO EVERY ERR CODE CAN ARRIVE EITHER WAY.** Overflow (6), division by zero
(11), illegal function call (5), syntax (2), subscript (9), out of memory (7),
redimension (10) and type mismatch (13) each appear at deferred sites, and
ERR 7 also appears at the one immediate site. **A row's expected ERR code
carries no information about whether that row can witness an ordering-sensitive
guard**, and no prose in the tree distinguishes the two. That is the whole
reason K-FE1's subject went unwitnessed through an entire arc.

---

## 2. 🎯 The class, stated so it can be checked

`exec_stmt` opens **every** statement with

    xor     a
    ld      (PRDEST),a          ; only PRINT#'s own item loop sets dest=file

so `PRDEST` cannot be left stale by any fault: the handler's first statement
resets it, and `stmt_error` / `fre_abort_low` / `type_mismatch_error` zero it
again on their own paths. `FN_FEND` is **not** reset there — which is exactly
why it needed its own store in `raise_error`, and why deleting that store was
invisible. So:

> **THE CLASS:** a RAM cell that means *"we are inside X"*, cleared by X's
> NORMAL exit, **not** cleared at the statement boundary, **read on a path
> outside X**, and reachable by a fault that raises before X's normal exit.

All four conjuncts matter. The last two are what separate a real member from
ordinary transient scratch: `FOSIGN` is *"transient, dead between PRINT items"*
(sysvars.inc's own words) and is rewritten before every read, so its staleness
is unobservable. `FN_FEND` is read by `scv_find` on **every scalar reference in
the language**, which is why a stale one is a silent wrong answer.

---

## 3. The measurement — three constructs, 27 of 27 readings agree

`scratchpad/deferblind_probe.py`. Each row is a whole program run boot-per-case
on **both references and zerobas**, printing one fenced value; the fall-through
prints nothing, so a row that produced no value reads `<NO OUTPUT>` and is
scored NOT MEASURED rather than as agreement. Each construct is run three ways:
with an **immediate** fault (`FNZ(0)` — an undefined user function, ERR 18
raised on the spot, available on every MSX1 and needing no `DEF FN` of our own),
with a **deferred** one (`1/0`) as the separating control, and with **no fault**
as the positive control.

| row | what it asks | VG-8020 | CF-3300 | zerobas |
|---|---|---|---|---|
| `for.imm` | does `NEXT` still find its frame after a trapped immediate fault? | `6` | `6` | **`6`** |
| `for.def` | …the deferred twin | `6` | `6` | **`6`** |
| `for.ctl` | …no fault at all | `6` | `6` | **`6`** |
| `gos.imm` | can `RETURN` still find its frame? | `BACK` | `BACK` | **`BACK`** |
| `gos.def` | …deferred twin | `BACK` | `BACK` | **`BACK`** |
| `gos.ctl` | …no fault | `BACK` | `BACK` | **`BACK`** |
| `fre.imm` | does a fault mid string-expression leak the heap? (`FRE("")` drift over five faulting iterations) | `4` | `4` | **`4`** |
| `fre.def` | …deferred twin | `4` | `4` | **`4`** |
| `fre.ctl` | …no fault | `4` | `4` | **`4`** |

**The FOR stack, the GOSUB stack and the string heap are all clean**, the two
references agree on every row, and zerobas matches both. ⚠️ Note `fre.ctl` is
also `4` — the four bytes are the loop's own allocation, not a leak, which is
what makes `fre.imm`'s `4` a zero rather than a small number.

---

## 4. 🔴 …and nine green rows are worth nothing until the shape can go red

`scratchpad/deferblind_calib.py` re-runs the **same** probe, zerobas only, with
**K-FE1 applied** — `raise_error`'s `ld (FN_FEND),a` turned into
`ld (FN_TYP),a`, the one cut known to leave a liveness cell standing. The cut is
imported from `scratchpad/deffn_knives.py`, not retyped, so there is one source
of truth for what K-FE1 is. Three `fn.*` rows were added for this: the same
program with an immediate fault inside the FN body, its deferred twin, and a
no-fault control.

    baseline roms=7942cc20 / 34bb8554 / 031184d9
    knifed   roms=b7b3cb1e / 34bb8554 / b5a0c5e6      (main moved, sub did not)

| | before | after |
|---|---|---|
| **`fn.imm`** | `5` | **`2`** |
| `fn.def`, `fn.ctl` | `5` | `5` |
| `for.*`, `gos.*`, `fre.*` (9 rows) | unchanged | unchanged |

> **CALIBRATION: PASS — moved = `['fn.imm']`, want = `['fn.imm']`.**

So the row shape **can** detect a stale liveness cell, it detects the one that
is known to exist, and it detects **only** that one under a cut aimed at it.
The nine zeros in §3 are a reading, not a silence. Restore returned all three
images to their baseline hashes.

---

## 5. ⚠️ What this does NOT establish — the denominator is three constructs

**"Found 0" is a fact about three constructs, not about the language**
([[a-hand-listed-denominator-is-a-scope-claim]]). A keyword sweep of
`basic/sysvars.inc` turns up **96** cells whose own comments say *in progress /
live / active / pending / depth*, and the great majority are transient scratch
that fail conjunct three (read only inside their own construct). Applying the
"read on a path outside X" filter by hand leaves a short candidate list, and
these are **untested**:

* 🔴 **`TRAPSVC`** — *"count of live SERVICING entries == depth of the service
  stack"*, incremented on trap dispatch (`traps.asm:369`) and decremented by
  `ex_return`'s `trap_return_check` (`traps.asm:421`), i.e. **only on a normal
  `RETURN` from the handler**. A handler left via `RESUME <line>` never returns,
  so the entry is never re-enabled and `TRAPSTK_MAX` is 6.
  ⚠️ **This is a DIFFERENT exposure from the one measured here** — the trigger
  is *RESUME out of a trap handler*, not deferred-vs-immediate, and both
  references would be expected to leak too. It needs its own reference
  measurement and its own slice; it is filed, not swept.
* `FCH_ACTIVE` / `FCH_NUM` / `FCH_MODE` — *"channel live in the engine
  globals, 0 = none"*. A fault mid-`OPEN` could leave a half-open channel
  visible to every later file statement.
* `GFX_DFTOP` — DRAW's X-frame stack depth, if a fault can raise inside an `X`
  substitution.

The instrument for each is the one calibrated in §4: run the construct three
ways (immediate / deferred / no fault) against both references, and prove the
shape can go red before believing a zero.

---

## 6. What was run

`scratchpad/deferblind_probe.out` (9 rows × 3 machines),
`scratchpad/deferblind_fn.out` (the 3 calibration rows × 3 machines),
`scratchpad/deferblind_calib.out` (12 rows × 2 builds, zerobas only).
36 boot-per-case runs in total. No gate was touched and no source file changed;
the ROMs are byte-identical to `aafcaa8` throughout.
