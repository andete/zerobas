# D-VAL — VAL is a whole number parser, and it had one row of coverage

*2026-08-29. Probe `scratchpad/val_probe.py`. **Measurement only — no code
change.** 40 rows, **20 DIFF**.*

## 1. Why look

`probes/basic/basic_probe_string.py` carries exactly **one** VAL case —
`VAL("34")+1` → 35. That is thin for a function whose job is to re-implement the
tokeniser's numeric scanner over arbitrary user text: signs, fractions,
exponents, bases, embedded spaces, partial parses and junk.

⚠️ **VAL never raises on junk — it returns 0** — so a wrong answer here is
**silent**, which this project ranks worse than a refusal. There is no error code
to notice, only a number that is quietly not the reference's number.

## 2. What diverges — 20 of 40

| shape | references | zerobas |
|---|---|---|
| `VAL("1.5")` · `VAL(".5")` | 1.5 · .5 | **1 · 0** |
| `VAL("1.2.3")` | 1.2 | **1** |
| `VAL("&HFF")` · `VAL("&hff")` · `VAL("&HFFZZ")` | 255 | **0** |
| `VAL("&O17")` · `VAL("&B101")` | 15 · 5 | **0** |
| `VAL("&")` | **ERR 2** | **0** — a silent wrong answer |
| `VAL("1E3")` · `VAL("1E-3")` · `VAL("1D3")` · `VAL("1E38")` | 1000 · 1E-03 · 1000 · 1E+38 | **1** |
| `VAL("1 2")` · `VAL(" - 12")` | 12 · -12 | **1 · 0** |
| `STR$(1.5)` · `STR$(.5)` · `STR$(1E9)` | 1.5 · .5 · 1000000000 | **1 · 0 · 0** |
| `VAL(STR$(1.5))` | 1.5 | **1** |

What **works**: integers with signs, `VAL("")`/`VAL("ABC")` → 0, partial parses
(`VAL("12ABC")` → 12), leading spaces, `VAL("5.")` → 5, `VAL("1E")` → 1.
So the *integer* path is right; everything past the integer is missing.

## 3. 🔴 Attributing it to the right layer

`STR$(1E9)` → `0` could mean the float **literal** is broken, which would be a
far larger and completely different finding. Controls settle it:

| control | all three sides |
|---|---|
| `PRINT 1.5` | **1.5** ✓ |
| `PRINT 1E9` | **1000000000** ✓ |
| `PRINT 3/2` | **1.5** ✓ |
| `PRINT &HFF` | **255** ✓ |

Float literals, float arithmetic, hex literals and float printing **all work**.
The gap is precisely the two functions that convert between numbers and strings
*at runtime*. [[a-case-that-agrees-can-agree-for-the-wrong-reason]]

## 4. The deferral note is stale, and understates the gap

`basic/PROVENANCE.md`'s Phase-3 entry records the scope deferral:

> Scope-deferred (documented there, not built): string comparison (`=`/`<`/`>` on
> strings), INSTR/HEX$/OCT$/STRING$/SPACE$/INKEY$, the MID$ statement, and floats
> in VAL/STR$.

**Every other item on that list has since shipped** — string comparison, INSTR
(D-INSTRTM touched it today), HEX$/OCT$/STRING$/SPACE$ (D-SPCLAMP measured them
today), the MID$ statement (D-NGRAM9, D-MIDOP). Only VAL/STR$ remains, on a
charter of **faithful full MSX1 BASIC**.

⚠️ **And "floats" is not the whole gap.** The note never mentions **base
literals** (`&H`/`&O`/`&B`) or **exponents**, both of which VAL also lacks, nor
the `VAL("&")` silent-zero. A deferral note is a description of what was skipped
*then*; it is not a specification of what is missing *now*.

## 5. The route — a lead, not a verified plan

`sh_val_parse` (VAL's integer parse) lives in **`sub/strheap.asm`**, a sub-ROM
tenant. The tokeniser's own full numeric scanner — `tk_float`, reached from
`basic/tokenise.inc` — lives in **`sub/tkfloat.asm`**, in the same sub-ROM, and
it already handles every shape above. It takes `HL` as its source cursor and
`DE` as a token-buffer destination.

So the plausible route is **delegation rather than a second implementation**:
point the existing scanner at the string body and decode the token it emits, the
way `ev_f_float` already decodes a literal.

⚠️ **Unverified, and named as such.** Whether `tk_float` can be pointed at a RAM
buffer, what it does with trailing junk (VAL must stop and return, not error),
and whether the two tenants can call each other are all open. Sub page 0 had
**2329 B** free on 2026-08-29 (`make basic-reloc`; do not quote this), so space is
not the constraint — the interface is.

🎯 The next step is to answer those three questions about `tk_float`'s contract,
**before** pricing anything.
