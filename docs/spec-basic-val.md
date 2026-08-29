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

## 5. The route — investigated 2026-08-29, and it changed under investigation

`sh_val_parse` (VAL's integer parse) lives in **`sub/strheap.asm`**, a sub-ROM
tenant. The tokeniser's own full numeric scanner — `tk_float`, reached from
`basic/tokenise.inc` — lives in **`sub/tkfloat.asm`**, in the same sub-ROM, and
it already handles every shape above. It takes `HL` as its source cursor and
`DE` as a token-buffer destination.

So the plausible route is **delegation rather than a second implementation**:
point the existing scanner at the string body and decode the token it emits, the
way `ev_f_float` already decodes a literal.

### 5.1 The three questions, answered 2026-08-29

**Q1 — can the scanner be pointed at a RAM buffer? YES.** The whole-tokeniser
tenant's contract is exactly the shape VAL wants: *in: HL = source (0-terminated
ASCII), DE = destination buffer; out: destination holds tokens, 0-terminated.*

**Q2 — trailing junk? A NON-ISSUE, and the question was slightly wrong.** The
tokeniser does not stop at junk; it crunches the whole line. VAL reads only the
**leading** token and ignores the rest — which *is* VAL's semantics
(`VAL("12ABC")` → 12). Nothing needs to stop.

**Q3 — can the two tenants call each other? THE QUESTION DISSOLVES.** VAL's glue
(`ev_ff_val`) is in the **main** ROM and already reaches the sub-ROM by
`subrom_call` — that is how it invokes `sh_val_parse` today. It would call
`SUBROM_IDX_TOKENISE` the same way and decode the result locally with
`ev_f_float`, which already turns a `SNG_TOKEN`/`DBL_TOKEN` at IX into
FAC/FACTYP + DE. No tenant needs to call another.

### 5.2 🔴 But a fourth blocker turned up, and it is the real one

**The destination buffer.** A whole-line tokenise needs ~256 B of scratch, and
the obvious candidates are all taken:

| buffer | why not |
|---|---|
| `TOKBUF` ($EC00, 576 B) | 🔴 **direct-mode lines EXECUTE out of it** — `ld hl,TOKBUF / jp rp_exec`. `PRINT VAL("1.5")` typed at the prompt would have VAL overwrite the statement running it. |
| `DETOKBUF` | `PRINT USING` drains its literals through it, and VAL can appear in a `PRINT USING` value list. |
| `LINEBUF` | the runtime `INPUT` line. |

So the whole-tokeniser route needs **new RAM**, which is the scarce resource this
route was supposed to avoid.

🎯 **Which flips the design back to `tk_float`.** It emits only a token byte plus
at most 8 value bytes, so its destination is ~**9 B of scratch**, not 256. Its
own blocker is the *exit protocol*: `tk_float` does not `ret` — it ends
`jp tk_loop` / `jp tk_end` back into the co-located tokeniser loop — so it needs
a small variant entry that returns instead.

**A ~6 B variant entry versus ~256 B of new RAM** is the trade, and it is now a
concrete question rather than an open one.

⚠️ Still unmeasured: whether the tokeniser's `TKOVF` crunch-time reject is what
makes `VAL("&")` an ERR 2 on the references, and what the integer tokens
(`INT1_TOKEN`, the digit tokens) decode through on the VAL path.
