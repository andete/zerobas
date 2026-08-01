# D-EXPKW — when an exponent marker is NOT a marker, on two MSX1 machines

Companion to [`docs/spec-basic-expkw.md`](spec-basic-expkw.md); the sequel to
[`docs/expbad-msx1-characterization.md`](expbad-msx1-characterization.md), whose
§1 conclusion — *"there is no failure case"* — this refutes.

**Instrument:** `("stored_line", TXTTAB)` — the exact bytes of the stored line,
link word dropped. Probe
[`probes/basic/basic_probe_lnblank.py`](../probes/basic/basic_probe_lnblank.py),
batteries `expk` / `expw` / `expb`. `make lnblank-characterize ONLY=expk,expw,expb`.

**Two oracles.** Every row asked of the **Philips VG-8020** and the **National
CF-3300**, every payload past `make lnblank-echo` on all three sides first.
**They agree on all 76 rows.** All three rounds were oracle-locked **before**
zerobas was run on any of them.

Token bytes as in the D-EXPBAD companion: `<1D> e m m m` single, `<1F> e m×7`
double, `<1C> lo hi` two-byte integer, `<11>`…`<1A>` the integers 0…9.
`<12>` is therefore the integer **1** — *the marker was not consumed at all* —
and it is the single byte that carries this whole measurement.

---

## 1. Round 1 — the seam D-EXPBAD could not see

D-EXPBAD generalised "the digits are optional, the marker is always eaten" from
five rows: `1E`, `1E+`, `1D`, `1E#`, `12345EX`. **Not one of them puts a reserved
word behind the marker.** Two words in the language begin with `E`:

| row | typed | **both references** | zerobas today |
|---|---|---|---|
| `expk-eqv` | `20 A=1 EQV 2` | `A<EF><12> <F9> <13>` — INT 1, `EQV` intact | `A<EF><1D>A<10><00><00>QV 2` |
| `expk-eqv0` | `20 A=1EQV 2` | `A<EF><12><F9> <13>` — **no blank, same answer** | `A<EF><1D>A<10><00><00>QV 2` |
| `expk-else` | `20 A=1 ELSE B=2` | `A<EF><12> :<A1> B<EF><13>` | `A<EF><1D>A<10><00><00>LSE B<EF><13>` |
| `expk-else0` | `20 A=1ELSE B=2` | `A<EF><12>:<A1> B<EF><13>` | `A<EF><1D>A<10><00><00>LSE B<EF><13>` |
| `expk-low` | `20 A=1 eqv 2` | `A<EF><12> <F9> <13>` — case-folded | `A<EF><1D>A<10><00><00>QV 2` |
| `expk-erl` | `20 A=1 ERL` | `A<EF><1D>A<10><00><00>RL` — **EATEN** | *agrees* |
| `expk-dim` | `20 A=1 DIM B` | `A<EF><1F>A<10>×6 IM B` — **EATEN**, double | *agrees* |
| `expk-dim0` | `20 A=1DIM B` | the same | *agrees* |
| `expk-nonkw` ^ | `20 A=1 EX` | `A<EF><1D>A<10><00><00>X` — eaten | *agrees* |
| `expk-okdig` ^ | `20 A=1E2 EQV 3` | `A<EF><1D>C<10><00><00> <F9> <14>` | *agrees* |

`^` = two-sided control.

**The `0` rows are the separation.** `1EQV` with no blank anywhere keeps its
`EQV`, so "a blank run protects the word" is refuted — and `dec-expboth`
(`1 E 2` → 100, D-DECBLANK) already said a blank cannot protect anything.

### 1.1 🔴 `expk-nonkwq` — a control that the references inverted

`("expk-nonkwq", "20 A=1 EQ")` was pinned as a **green control**. It exists to
say *the rule is a whole reserved WORD, not the letters* — `EQ` is no keyword, so
under a keyword-match reading its marker must be eaten. Both references store

    A<EF><12> EQ          the marker KEPT, for a two-letter fragment

and `expk-erl` — which **is** a whole keyword — loses its marker on both. So the
keyword reading is refuted **in both directions at once**, by one row written to
confirm it. That reading is what sent this slice to a contiguous walk.

### 1.1a ⚠️ `expk-else` typed a bare `2` first, and diverged for TWO reasons

The first cut was `20 A=1 ELSE 2`. With the fix in, it stayed red:

    both references   A<EF><12> :<A1> <0E><02><00>      a line-number REFERENCE
    zerobas           A<EF><12> :<A1> <13>              the integer constant 2

The `:<A1>` — this slice's whole subject — had come good; what remained is the
separately-filed `$0E`-refs divergence (the standing `ref-else` informational
row, out of this slice's scope). A row that can go red for two reasons confirms
neither, and had the marker bug still been live a reader would have credited the
wrong cause. The clause is now `B=2`, which reaches the same `$A1` and carries no
line-number reference. **The terminator changed, not the subject.**

### 1.2 🔴 `expk-ifelsei` — the other inverted control, and it renames the defect

`("expk-ifelsei", "20 IF 0 THEN A=1 ELSE B=2")` was pinned as this battery's
control on the assumption that only a **float** literal reaches the exponent
scan, so a surviving `$A1` would localise the defect to the float path and
exonerate `if_skip_to_else`. Measured, zerobas stores

    <8B> <11> <DA> A<EF><1D>A<10><00><00>LSE B<EF><13>       (integer literal)
    <8B> <11> <DA> A<EF><1D>A<15><00><00>LSE B<EF><13>       (expk-ifelse, `1.5`)

— the **same** damage. `1` reaches `tkf_try_exponent` exactly as `1.5` does
(that is the whole mechanism of `dec-ebig`). The reference keeps `<12> :<A1>`
and `<1D>A<15><00><00> :<A1>` respectively.

---

## 2. Round 2 — the contiguous second-letter walk (`expw`)

Round 1 left two candidate rules alive and refuted both. Six rows gave three
answers, so the space was walked instead of sampled: `20 A=1 E<c>` and
`20 A=1 D<c>` for all 26 letters, 52 rows, both references.

**`E` marker — the marker is KEPT for exactly two letters:**

| second letter | both references |
|---|---|
| **`L`** (`20 A=1 EL`) | `A<EF><12> EL` — **kept** |
| **`Q`** (`20 A=1 EQ`) | `A<EF><12> EQ` — **kept** |
| the other **24** | `A<EF><1D>A<10><00><00><c>` — eaten, forced SINGLE |

**`D` marker — 26/26 eaten**, every one forced to DOUBLE
(`A<EF><1F>A<10><00><00><00><00><00><00><c>`). There is no protected letter.

### 2.1 The set is not arbitrary, and it is not a keyword match

`ELSE` and `EQV` are the **only reserved words beginning with `E` that can
legally follow a numeric constant**, and no `D` word can. MS-BASIC hardcoded
exactly that pair — as **two letters**, not as words:

* `EQ` and `EL` are kept although neither is a keyword (§1.1);
* `ERL`, `EXP`'s `EX`, `END`'s `EN`, `EOF`'s `EO`, `ERASE`/`ERR`/`ERROR`'s `ER`
  are eaten although all of them **are** keywords or keyword prefixes.

A `match_kw`-based implementation would therefore diverge on `1 EQ` and `1 EL`.
**The faithful test is the letter.**

---

## 3. Round 3 — where the lookahead's boundaries are (`expb`)

`tkf_fetch` is blank-transparent, and D-EXPBAD's own header records that
committing at the wrong point silently eats a blank while every filed row stays
green. A two-letter lookahead lands in exactly that seam.

| row | typed | **both references** | reading |
|---|---|---|---|
| `expb-elblk` | `20 A=1 E L` | `A<EF><12> E L` | ★ the letter is reachable **ACROSS a blank run**, and the rollback restores the WHOLE run — blank, `E`, blank, `L` all verbatim |
| `expb-eqblk` | `20 A=1 E Q` | `A<EF><12> E Q` | the same on the other letter |
| 🔴 `expb-elsign` | `20 A=1 E+L` | `A<EF><1D>A<10><00><00>L` | **the test does NOT survive a sign** — `E` and `+` both eaten |
| `expb-elnoblk` | `20 A=1EL` | `A<EF><12>EL` | no blank: kept |
| `expb-ellow` | `20 A=1 el` | `A<EF><12> EL` | lowercase counts (case-folded) |
| `expb-elq3` | `20 A=1 ELQ` | `A<EF><12> ELQ` | a third letter is irrelevant — the rule is the two-letter prefix |
| `expb-eldot` | `20 A=.5EL` | `A<EF><1D>@P<00><00>EL` | a dot-leading literal reaches the same scan |
| `expb-elpct` | `20 A=1EL%` | `A<EF><12>EL%` | marker not consumed ⇒ `has_exp` clear, so `EL%` is an ordinary variable name and the `%` is **its** suffix, not the literal's |
| `expb-eldig` ^ | `20 A=1E2L` | `A<EF><1D>C<10><00><00>L` | CONTROL: a WELL-FORMED exponent, the `L` is not at a marker |
| `expb-dlblk` ^ | `20 A=1 D L` | `A<EF><1F>A<10>×6 L` | CONTROL: `D` has no protected letter, so the blank seam cannot change its answer |

### 3.1 🔴 `expb-elsign` decides WHERE the test goes

The lookahead is at the character **immediately after the marker** (across
blanks) and **nowhere else**. Behind a consumed sign the ordinary digit rules
resume, so `1 E+L` is a single `1.0` followed by `L`. A fix that tested for
`L`/`Q` after the sign lookahead would pass every row in §1 and §2 and fail this
one.

---

## 4. What this measures that no earlier row could

| filed as | measured |
|---|---|
| `float-acceptance` → `reg.C.if_skip_over_float`, *"a `tok_skip` float-literal stride bug"* | not `tok_skip` (which strides `$1D` correctly, [`basic/tokskip-body.inc:31`](../basic/tokskip-body.inc:31)), not `if_skip_to_else`, and **not about floats** (§1.2). The `ELSE` never reaches the stored line at all. |
| `logicops-acceptance` → *"50 rows, all `EQV`/`IMP`, both unimplemented"* | `EQV`/`IMP` **are** implemented ([`basic/expr.asm:148`](../basic/expr.asm:148), landed `ef098e9` at 156/156). All 49 failing rows contain **`EQV`**; not one fails on `IMP` alone. `PRINT 0 EQV 0` prints three items — `0`, the variable `QV`, `0`. |
| *"two unrelated standing failures"* | **one defect**, in `tkf_try_exponent`, regressed by `4b2202e` (D-EXPBAD). |
