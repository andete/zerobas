# D-FLDCLOSE — the reference's post-CLOSE FIELD variable is a LIVE pointer, not a stale value

*2026-08-31. No code change — this is the measurement Joost asked for before
deciding. Probe `scratchpad/fldclose_probe.py`, 9 rows, CF-3300 + zerobas.*

## 1. The question

D-NGRAM17 §5 found that after `CLOSE#1` a FIELDed variable reads `LEN(A$)=10` on
the CF-3300 and `0` here; reading *before* the close agrees, so `FIELD` is right
and `CLOSE` is the difference. Matching the reference means **not** clearing the
descriptor — which leaves it pointing into a released buffer.

**The deciding question, and the error code cannot answer it:** does the
reference's content merely *survive* (stale but stable), or is the variable a
**live alias** of whatever occupies that memory next?

## 2. The answer: it is live

`FIELD#1,10 AS A$` / `LSET A$="ABCDEFGHIJ"`, then:

| | CF-3300 | zerobas |
|---|---|---|
| **before** `CLOSE` — `A$` | `ABCDEFGHIJ` | `ABCDEFGHIJ` ✅ |
| after `CLOSE` — `LEN(A$)` | **10** | **0** |
| after `CLOSE` — `A$` | `ABCDEFGHIJ` | `<nothing>` |
| after `CLOSE` + 8 string allocations — `A$` | `ABCDEFGHIJ` | `<nothing>` |
| after `CLOSE` + reopen + `FIELD#1,10 AS C$` + `LSET C$="ZZZZZZZZZZ"` — `A$` | **`ZZZZZZZZZZ`** | `<nothing>` |

🎯 **Ordinary string churn does not disturb it** — the FIELD buffer is not in the
string heap, so eight `STRING$` allocations leave `A$` intact. **But re-opening a
channel and FIELDing it overwrites what `A$` reads.** The descriptor is a live
pointer into the FIELD buffer area, and a later `FIELD` silently rebinds it.

🟢 The two controls (`X$="HELLO"` with and without the churn) hold on both sides,
so the churn itself is not moving ordinary strings around.

## 3. What each choice actually costs

**Match the reference.** `A$` keeps working after `CLOSE`, which is the common
idiom — read a record, close the file, use the value. The price is that `A$`
becomes an alias: a later `FIELD` on any channel that reuses that buffer changes
it *silently*, with no error and no assignment in sight.

**Keep resetting (today).** No descriptor ever points at a freed buffer. The
price is that the common idiom is broken — `A$` reads empty the moment the file
is closed, which is the divergence D-NGRAM17 measured.

⚠️ **Neither is "safe".** One risks a silent wrong value in a narrow case; the
other guarantees a wrong value in a common one. That is why this is a judgement
and not a measurement — but the judgement is now being made against the real
behaviour rather than against a guess about it.
