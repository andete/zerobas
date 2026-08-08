# D-NXARY — a `NEXT` operand is a full variable REFERENCE

*Measured 2026-08-08 at `5a50a04` (D-NXLIST), `make nxary-characterize`,
`probes/basic/basic_probe_nxary.py`. Three sides: Philips VG-8020, National
CF-3300, zerobas repack.*

🎯 **BOTH REFERENCES AGREE ON ALL 22 ROWS.**

⚠️ **Measured in three rounds, and rounds 2 and 3 each came from something
OTHER than the row set:** round 2 replaced a row that was measuring the wrong
thing (§3), and round 3's `a.strpick` was demanded by a KNIFE that reddened
nothing (§5).

---

## 1. The readings

| row | program (one statement per line) | both references | zerobas at `5a50a04` |
|---|---|---|---|
| `c.for` | `FOR I=1 TO 3` / `NEXT` / `PRINT I` | ` 4 ` | ` 4 ` 🟢 **control** |
| `c.aryrd` | `DIM A(3)` / `A(1)=7` / `PRINT A(1)` | ` 7 ` | ` 7 ` 🟢 **control** |
| `c.nofor` | `FOR A=1 TO 2` / `NEXT B` / `PRINT"[OK]"` | **NEXT without FOR** | **NEXT without FOR** 🟢 **control** |
| `a.lit` | `FOR A=1 TO 2` / `NEXT A(1)` | **NEXT without FOR** | **Syntax error** 🔴 |
| `a.oob` | `FOR A=1 TO 2` / `NEXT A(99)` | **Subscript out of range** | **Syntax error** |
| `a.spc` | `FOR A=1 TO 2` / `NEXT A (1)` | **NEXT without FOR** | **Syntax error** ⏸ **DEFERRED** (§4) |
| `a.dim` | `DIM A(3)` / `FOR A=1 TO 2` / `NEXT A(1)` | **NEXT without FOR** | **Syntax error** |
| `a.dimoob` | `DIM A(3)` / `FOR A=1 TO 2` / `NEXT A(9)` | **Subscript out of range** | **Syntax error** |
| `a.var` | `B=1` / `FOR A=1 TO 2` / `NEXT A(B)` | **NEXT without FOR** | **Syntax error** |
| `a.expr` | `FOR A=1 TO 2` / `NEXT A(1+1)` | **NEXT without FOR** | **Syntax error** |
| `a.2d` | `DIM A(3,3)` / `FOR A=1 TO 2` / `NEXT A(1,2)` | **NEXT without FOR** | **Syntax error** |
| `a.rank` | `DIM A(3,3)` / `FOR A=1 TO 2` / `NEXT A(1)` | **Subscript out of range** | **Syntax error** |
| `a.str` | `FOR A=1 TO 2` / `NEXT A$(1)` | **NEXT without FOR** | **NEXT without FOR** ✅ ⚠️ *for the wrong reason — §2* |
| `a.stroob` | `FOR A=1 TO 2` / `NEXT A$(99)` | **Subscript out of range** | **NEXT without FOR** 🔴 |
| `a.pct` | `FOR A%=1 TO 2` / `NEXT A%(1)` | **NEXT without FOR** | **Syntax error** |
| `a.pctoob` | `FOR A%=1 TO 2` / `NEXT A%(99)` | **Subscript out of range** | **Syntax error** |
| `a.strpick` | `DIM A(50)` / `DIM A$(3)` / `FOR A=1 TO 2` / `NEXT A$(9)` | **Subscript out of range** | *(added post-fix, §5)* **Subscript out of range** ✅ |
| `a.errno` | `ON ERROR GOTO 40` / `FOR A=1 TO 2` / `NEXT A(1)` / `PRINT ERR` | ` 1 ` | ` 2 ` 🔴 |
| `a.autodim` | `ON ERROR GOTO 40` / `FOR A=1 TO 2` / `NEXT A(1)` / `DIM A(3)` / `PRINT"[OK]"` | **Redimensioned array** | `OK` 🔴 |
| `a.list` | `FOR A=1 TO 2` / `FOR B=1 TO 2` / `NEXT B,A(1)` | **NEXT without FOR** | **Syntax error** |
| `a.dep8` | 8 nested `FOR`/`NEXT` pairs | `OK` | `OK` ✅ 🔴 **the CARVE's row** |
| `f.ary` | `DIM A(3)` / `FOR A(1)=1 TO 3` / `NEXT` | **Syntax error** | **Syntax error** ✅ 🔴 **negative control** |

**6 of the 21 scored rows agreed** at `5a50a04` (1 row deferred, §4).
After D-NXARY the battery is **21/21** — 22 cases, 1 deferred.

---

## 2. The rule, stated from the readings and from nothing else

> A `NEXT` operand is an **ordinary variable REFERENCE**: name, type suffix,
> and — when a `(` follows — a full subscript list that is **EVALUATED**,
> **auto-DIMs** an as-yet-unreferenced array, and is **range- and rank-checked**
> (`Subscript out of range`). A resolved array ELEMENT matches no `FOR` frame,
> so the answer is **NEXT without FOR** (ERR 1), in every type namespace.

Three of those clauses are readings no earlier row asked, and each decides bytes:

* 🎯 **`a.autodim` — THE RESOLVE AUTO-DIMS.** Trap the error, then `DIM A(3)`:
  both references answer **Redimensioned array**, so `NEXT A(1)` on an
  unreferenced `A()` *created* it. A side effect on a row that ERRORS, which no
  direct reading can see. It says the fix must use the auto-dimming resolve
  (`ary_op0_resolve` op=0) rather than a tightened one.
* 🎯 **`a.stroob` — AND `a.str` AGREES FOR THE WRONG REASON.** `NEXT A$(1)` was
  **already green** here, and for a reason with nothing to do with arrays:
  D-FORVAR made a `$` name resolve to `DEFTBL_STR`, a type no frame can hold, so
  ERR 1 falls out *without the subscript being looked at*. Put the subscript out
  of range and the two mechanisms separate — **a case that agrees can agree for
  the wrong reason**.
* 🎯 **`a.rank`** — a wrong-rank subscript is `Subscript out of range`, so this
  is the real resolve and not a subscript skipper.

And `a.errno` pins the error as a **number** (`ERR` = 1 through `ON ERROR`), not
as a wording that happens to match.

---

## 3. 🔴 Round 2: the first `a.autodim` measured something else, and it read fine

The first draft disarmed before the `DIM`:

```basic
10 ON ERROR GOTO 50
20 FOR A=1 TO 2
30 NEXT A(1)
40 END
50 ON ERROR GOTO 0
60 DIM A(3)
70 PRINT"[OK]"
```

Both references read **NEXT without FOR**; zerobas read `OK`. A clean 3-side
reading, a plausible-looking divergence — **and an answer to a question nobody
asked**, because in MS-BASIC `ON ERROR GOTO 0` executed *inside* a handler
**re-raises the error that entered it**. The row never reached the `DIM` at all
([[readout-blind-to-its-own-subject]]).

Rewritten to `DIM` inside the still-armed handler (an error there is fatal on
both machines), it answers **Redimensioned array**.

🔴 **The re-raise divergence it accidentally found is REAL** — zerobas does not
re-raise on `ON ERROR GOTO 0` inside a handler, where both references do. It
belongs to the error-handling surface, not to `NEXT`, and is filed in `TODO.md`
with this reading.

---

## 4. ⏸ `a.spc` — DEFERRED, and not for space

`NEXT A (1)` is **NEXT without FOR** on both references and `Syntax error` here.
`tgt_parse` tests for the subscript with a bare `ld a,(hl)` straight after
`var_name_key`, so its `(` is **lexically contiguous**: `A (1)` reads as the
scalar `A`, and ` (1)` then reaches statement position.

💰 **The fix is 3 bytes and page 1 has 5 — this is not a budget decline.**
`tgt_parse` has **seven** call sites (`READ`, console `INPUT`, `LINE INPUT`,
`MID$(…)=`, `FIELD`, `LSET`/`RSET`, `files.asm`) and a `call skip_spaces` there
changes what `READ A (1)` and `LSET A (1)=` *mean* at the six this slice does not
measure ([[a-shared-engine-fix-must-measure-its-other-callers]]). MS-BASIC's own
CHRGOT skips spaces, so the change is very likely right everywhere — and "very
likely" is what this tree does not ship. Filed in `TODO.md` with the six sites
named.

---

## 5. 🔴 `a.strpick` — the row a KNIFE demanded, not the row set

**K-NA3** forces `tgt_parse`'s MODE argument to 0, so the resolve is told the
TYPE CODE (`3` for a `$` name) instead of the mode (`1`). It reddened **nothing**
across 21 rows: the two namespaces coincide today
([[two-namespaces-sharing-a-value]]), so nothing in the battery could tell which
array was reached. *A cut with no row of its own is a missing row, not a bad cut.*

`a.strpick` gives the two candidates **different bounds** — `A(50)` and `A$(3)` —
and asks for subscript **9**, which is in range in one and out in the other. Both
references answer **Subscript out of range**, i.e. the `$` array. Re-run against
it, K-NA3 cuts exactly that one row: with mode 0 the resolve reaches `A(50)`, 9 is
in range, and the answer becomes `NEXT without FOR`.

⇒ `var_str_type` is **load-bearing**, and the row that proves it exists only
because the cuts were run before the row set was called finished
([[draft-the-knives-before-freezing-the-row-set]]).

---

## 6. Denominator

**(SUBSCRIPT FORM: literal / variable / expression) × (RANK: 1-D / 2-D / the
WRONG rank) × (RANGE: in / out) × (DIMmed / unDIMmed)**, plus the three type
namespaces and which array a `$` name actually reaches, plus the error NUMBER
read through `ON ERROR`, plus whether the resolve AUTO-DIMS, plus an array
element as a LIST element, plus 8-deep nesting for the carve, plus the
`FOR A(1)=` form both references REFUSE.

**Not covered, and named rather than implied:** a space before the `(` (§4 —
measured, divergent, DEFERRED with a priced reason); `ON ERROR GOTO 0`'s
re-raise inside a handler (§3 — measured, divergent, filed); a subscript that is
itself an array element (`NEXT A(B(1))`); a subscript with a side effect; and
nesting deeper than 8, where the two machines' limits are different mechanisms.
