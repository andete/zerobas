# D-TGTSPC — a SPACE between a variable reference and its `(`

*Measured 2026-08-08 at `030f068` (D-NXARY), `make tgtspc-characterize`,
`probes/basic/basic_probe_tgtspc.py`. Three sides: Philips VG-8020, National
CF-3300, zerobas repack. 28 rows in ~27 s.*

🎯 **BOTH REFERENCES AGREE ON ALL 28 ROWS.**

🔴 **SIX ROWS HAVE ONE REFERENCE, NOT TWO.** `INPUT #n` (`f.*`), `FIELD` (`d.*`)
and `LSET` (`s.*`) are Disk BASIC; a diskless VG-8020 answers `Syntax error` to
every one of those words, so it is not an oracle for them — it is a machine that
cannot express the question. Those six rest on the **CF-3300 alone**, which is a
weaker claim than every other row here. The probe prints it per row.

---

## 1. The readings

| row | program (one statement per line) | both references | zerobas at `030f068` |
|---|---|---|---|
| **the tokeniser — is the space even THERE?** | | | |
| `t.ctl` | `1 NEXT A(1)` *(stored, never run)* | `83204128122900` | `83204128122900` 🟢 **control** |
| `t.spc` | `1 NEXT A (1)` *(stored, never run)* | `8320412028122900` | `8320412028122900` ✅ |
| **1. `NEXT` — `ex_next`** | | | |
| `n.ctl` | `FOR A=1 TO 2` / `NEXT A(1)` | `NEXT without FOR` | `NEXT without FOR` 🟢 **control** |
| `n.spc` | `FOR A=1 TO 2` / `NEXT A (1)` | **NEXT without FOR** | **Syntax error** 🔴 |
| `n.spcoob` | `FOR A=1 TO 2` / `NEXT A (99)` | **Subscript out of range** | **Syntax error** 🔴 |
| **2. `READ` — `ex_read`** | | | |
| `r.ctl` | `DATA 7` / `DIM A(3)` / `READ A(1)` / `PRINT A;A(1)` | ` 0  7 ` | ` 0  7 ` 🟢 **control** |
| `r.spc` | `DATA 7` / `DIM A(3)` / `READ A (1)` / `PRINT A;A(1)` | ` 0  7 ` | **Syntax error** 🔴 |
| `r.spcauto` | `DATA 7` / `READ A (1)` / `PRINT A;A(1)` *(no `DIM`)* | ` 0  7 ` | **Syntax error** 🔴 |
| `r.spcoob` | `DATA 7` / `DIM A(3)` / `READ A (9)` | **Subscript out of range** | **Syntax error** 🔴 |
| **3. console `INPUT` — `inpc_vloop` / `inpc_vstr`** | | | |
| `i.ctl` | `DIM A(3)` / `INPUT A(1)` / `PRINT A;A(1)` ⌨ `7` | ` 0  7 ` | ` 0  7 ` 🟢 **control** |
| `i.spc` | `DIM A(3)` / `INPUT A (1)` ⌨ `7` | ` 0  7 ` | **Syntax error** 🔴 |
| `i.spcstr` | `DIM A$(3)` / `INPUT A$ (1)` ⌨ `HI` | `HI` | **Syntax error** 🔴 |
| **4. `LINE INPUT` — `inpc_line`** | | | |
| `l.ctl` | `DIM A$(3)` / `LINE INPUT A$(1)` ⌨ `HI` | `HI` | `HI` 🟢 **control** |
| `l.spc` | `DIM A$(3)` / `LINE INPUT A$ (1)` ⌨ `HI` | `HI` | **Syntax error** 🔴 |
| **5. `MID$(…)=` — `ex_mid_stmt`** | | | |
| `m.ctl` | `A$(1)="HELLO"` / `MID$(A$(1),1,2)="XY"` | `XYLLO` | `XYLLO` 🟢 **control** |
| `m.spc` | `A$(1)="HELLO"` / `MID$(A$ (1),1,2)="XY"` | `XYLLO` | **Syntax error** 🔴 |
| `m.trail` | `A$="HELLO"` / `MID$(A$ ,1,2)="XY"` | `XYLLO` | **Syntax error** 🔴 **the SCALAR path — §3** |
| **6. `INPUT #n` — `inp_readvar`** *(CF-3300 only)* | | | |
| `f.ctl` | write `TS.TXT`, `INPUT#1,A$(1)` | `HI` | `HI` 🟢 **control** |
| `f.spc` | write `TS.TXT`, `INPUT#1,A$ (1)` | `HI` | **Syntax error** 🔴 |
| **7. `FIELD` — `tgt_parse_fld` ← `ex_field`** *(CF-3300 only)* | | | |
| `d.ctl` | `OPEN"TS.DAT"AS #1` / `FIELD#1,10 AS A$(1)` | `OK` | `OK` 🟢 **control** |
| `d.spc` | `OPEN"TS.DAT"AS #1` / `FIELD#1,10 AS A$ (1)` | `OK` | **Syntax error** 🔴 |
| **8. `LSET`/`RSET` — `tgt_parse_fld` ← `lrset_common`** *(CF-3300 only)* | | | |
| `s.ctl` | FIELDed, `LSET A$(1)="HI"` | `HI␣␣␣␣␣␣␣␣` | `HI␣␣␣␣␣␣␣␣` 🟢 **control** |
| `s.spc` | FIELDed, `LSET A$ (1)="HI"` | `HI␣␣␣␣␣␣␣␣` | **Syntax error** 🔴 |
| **9. the BOUNDARY** | | | |
| `x.multi` | `FOR A=1 TO 2` / `NEXT A   (1)` *(3 spaces)* | **NEXT without FOR** | **Syntax error** 🔴 |
| `x.inner` | `FOR A=1 TO 2` / `NEXT A( 1 )` | `NEXT without FOR` | `NEXT without FOR` ✅ |
| `x.dollar` | `FOR A=1 TO 2` / `NEXT A $(1)` | **NEXT without FOR** | **Syntax error** ⏸ **DEFERRED** (§4) |
| `x.name` | `FOR AB=1 TO 2` / `NEXT A B` / `PRINT"[OK]"` | **`OK`** | **NEXT without FOR** ⏸ **DEFERRED** (§4) |
| **the NEGATIVE control** | | | |
| `z.for` | `DIM A(3)` / `FOR A (1)=1 TO 3` / `NEXT` | **Syntax error** | **Syntax error** ✅ 🔴 **negative control** |

**12 of the 26 scored rows agreed** at `030f068` (2 rows deferred, §4).
After D-TGTSPC the battery is **26/26** — 28 cases, 2 deferred.

---

## 2. The rule, stated from the readings and from nothing else

> A variable REFERENCE's subscript `(` may be separated from the name by any run
> of spaces. The reference then parses the **whole** reference — the subscript is
> **evaluated**, the array **auto-DIMs**, and it is **range-checked** — exactly
> as if the `(` had been contiguous. This holds at **every** statement that takes
> a variable as a target: `NEXT`, `READ`, console `INPUT` (both arms), `LINE
> INPUT`, `MID$()=`, `INPUT #n`, `FIELD` and `LSET`/`RSET`.

Four of those clauses are readings no earlier row asked, and each decides bytes:

* 🎯 **`t.spc` — THE SPACE SURVIVES THE CRUNCH, AND THAT IS WHAT SAYS WHICH FILE
  THE FIX BELONGS IN.** The first question is not *"does the reference skip the
  space"* but *"is the space still there when the parser runs"* — because if the
  reference's **tokeniser** stripped it, a parser-side fix would spend every byte
  in the wrong file, and the screen cannot tell the two apart (both give `NEXT
  without FOR`). Read from the STORED LINE BYTES through `TXTTAB`, the instrument
  `basic_probe_crunch.py` uses: `1 NEXT A (1)` crunches to
  `83 20 41 **20** 28 12 29 00` on all three sides, byte for byte. The `$20` is
  stored. ⇒ the parser skips it, and the fix is `tgt_parse`'s.
* 🎯 **`r.spcauto` — THE SPACED FORM AUTO-DIMS.** No `DIM` anywhere, and
  `READ A (1)` then `PRINT A;A(1)` reads ` 0  7 `: the ELEMENT took the value
  (the scalar is still 0) and the array was created. D-NXARY's `a.autodim` said
  the contiguous form auto-DIMs; this says the space changes nothing, so a fix
  must keep `ary_op0_resolve` op=0.
* 🎯 **`n.spcoob` / `r.spcoob` — THE FULL RESOLVE, THROUGH TWO DIFFERENT
  CALLERS.** `Subscript out of range` on both references means the spaced form
  evaluates and range-checks, not merely finds a `(`. Two callers rather than one
  because each has its own abort path.
* 🎯 **`r.spc` / `i.spc` PRINT *BOTH* CELLS.** ` 0  7 ` — not just ` 7 ` — is what
  distinguishes "the element took it" from "the scalar took it and the `(1)` was
  ignored". A row that printed only `A(1)` would have had two causes.

---

## 3. 🔴 `m.trail` — the row about the SCALAR path, which is a second divergence

Skipping spaces inside `tgt_parse` also consumes a **trailing** space on the
scalar path, and eight of the nine callers cannot see that: each does its own
`call skip_spaces` before reading the next delimiter. `ex_mid_stmt` is the
exception — `pop hl` / `ld a,(hl)` / `cp ','`, a bare read.

`MID$(A$ ,1,2)="XY"` is **`XYLLO`** on both references and **Syntax error**
here. So the trailing-space consumption is **required**, not merely tolerated:
one instruction closes two different divergences at that site.

The row was written as the *side effect* of the design and came back as a
*second subject*. It is the reason §4.3 of the spec is a fix and not a caveat.

---

## 4. ⏸ `x.dollar` / `x.name` — DEFERRED, and they are a DIFFERENT MECHANISM

| row | program | both references | zerobas |
|---|---|---|---|
| `x.dollar` | `FOR A=1 TO 2` / `NEXT A $(1)` | **NEXT without FOR** | **Syntax error** |
| `x.name` | `FOR AB=1 TO 2` / `NEXT A B` / `PRINT"[OK]"` | **`OK`** | **NEXT without FOR** |

🔴 **`x.name` IS THE BIG ONE.** `NEXT A B` *completing the `FOR AB` loop* means
the reference treats a space **inside a variable name** as insignificant — its
name scan skips spaces all the way down. That is `var_name_key` /
`var_str_type`, a cursor position *before* the one D-TGTSPC touches, and it
reaches **every variable reference in every expression**, not just the nine
lvalue targets. The skip this slice adds runs *after* `var_name_key` has already
stopped at the space, so it cannot reach either row.

Deferred, not declined-for-space: they are a **different rule** with a different
denominator ([[one-row-cannot-separate-two-rules]]), and folding them in would
leave no row able to separate the two. Filed in `TODO.md` with these two
readings as the denominator it starts from.

🎯 **AND A KNIFE CORROBORATED THE DEFERRAL'S STATED CAUSE.** K-TS4
(`spec-basic-tgtspc.md` §10.5(c)) marks every SCALAR target as an element, and it
moved `x.dollar` along with `m.trail` — which is only possible if zerobas really
does resolve `NEXT A $(1)` as the scalar `A`. The reason these rows are deferred
now rests on a cut, not only on a source reading.

⚠️ `x.inner` (`NEXT A( 1 )`) is the third boundary row and was **already green**
on all three sides — the array engine's own expression eval skips those spaces.
That is what scopes the defect to the `(` position itself rather than to
"spaces", and it is a control the fix must not disturb.

---

## 5. 🔴 The call-site count was wrong when the residual was filed

`TODO.md`, [`nxary-msx1-characterization.md`](nxary-msx1-characterization.md)
§4 and `ex_next`'s own code comment all say `tgt_parse` has **seven** call sites.
Walked: **eight `call tgt_parse` instructions, nine statement surfaces** — the
filed list is seven *other* surfaces and forgot to count `ex_next`, the site that
filed it, and it folds the console `INPUT`'s two arms (two distinct `call`s) into
one. The table is in [`spec-basic-tgtspc.md`](spec-basic-tgtspc.md) §3.1.

A hand-listed denominator is a scope claim
([[a-hand-listed-denominator-is-a-scope-claim]]), and this one was off by one in
the direction that matters: it under-counted the surface a fix has to be right
about.

---

## 6. Denominator

**(the NINE statement surfaces that reach `tgt_parse`) × (CONTIGUOUS `A(1)`
control / SPACED `A (1)`)**, plus whether the space **survives the crunch** at
all, plus whether the spaced form runs the **full** resolve (range check) and
**auto-DIMs**, plus the SCALAR-path side effect at the one caller that reads its
delimiter without its own `skip_spaces`, plus the other space positions (more
than one space; inside the subscript; before the `$` suffix; inside the NAME),
plus the `FOR A (1)=` form both references REFUSE.

**Not covered, and named rather than implied:** a TAB or any other whitespace
byte; a space before the `(` of a FUNCTION call or of `DIM`; `RSET` measured
separately from `LSET` (they share one parse site, so one pair of rows covers
both verbs — a claim about the CODE, not about the reference); a space before the
`(` of a subscript's own array element (`NEXT A (B (1))`); and the name-scan rule
§4 measures, which is filed as its own residual.
