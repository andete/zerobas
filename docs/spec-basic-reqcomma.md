# D-NGRAM17 — one `req_comma`, and four rows that could not see their own site

*2026-08-31. `basic/interp.asm` (body), `field.asm` / `files.asm` /
`missing.asm` / `sound.asm` (4 sites). Probe `scratchpad/reqcomma_probe.py`
(12 rows), arms `scratchpad/reqcomma_knives.py`.*

**Cost: −14 B** — page-0 low 121 → **127**, main page 1 349 → **357**.
**Rows: 12, 1 DIFF (pre-existing, and newly diagnosed — §5).**

## 1. The family is bigger than the collapsible set

`basic/` has **72** `cp ','` sites. Enumerated at instruction level they group by
**where they jump**:

| destination | sites | meaning |
|---|---|---|
| `stmt_error` | **4** | the comma is REQUIRED — these |
| `exec_stmt` | 3 | an OPTIONAL comma that ends the statement |
| local labels | the rest | two-site groups, each with its own branch |

Only a shared *destination* can share a body — a caller's own decline target is
what keeps it at the call site (the D-NGRAM11 rule). The four are FIELD
(`exf_havech`), INPUT# (`inp_readvar`), SWAP (`ex_swap`) and SOUND (`ex_sound`),
9 B each; a 10 B body plus four 3 B calls is 22.

The body sits beside `req_letter` / `req_lineno` / `req_operand` in `interp.asm`,
and `sound.asm` is in the **low** region — so the scarce pool gains 6 of the 14.

## 2. Both halves, one row per site

`g.*` supplies the comma (it must be **consumed** — the `inc hl` — or the verb
misreads its next argument); `b.*` omits it (it must **raise**). A row set with
only the good half cannot see a lost `inc hl`.

## 3. 🔴 The knives found four rows that cannot reach their site

I predicted 5 and 4; **4 and 2 moved**. Every omission is a blind row, and that
is the real yield:

| row | why it cannot move |
|---|---|
| `g.sound` | read the **next line's** `PRINT`, so a broken SOUND was invisible |
| `g.field` | reads `LEN(A$)` **after a `CLOSE`**, which is 0 either way (§5) |
| `b.field` | raises `Bad file number` **before** the comma check is reached |
| `b.swap` | never presents a missing comma at all — see below |

🎯 **`g.sound` was fixable and is fixed.** Joined into one line
(`SOUND 0,0:PRINT "ZQ1"`), a SOUND that misparses aborts the statement and the
PRINT never runs — and the knife then moves it. **A knife that fails to move a
row is a claim about the row, not only about the code.**

🔬 **`b.swap` is blind for a measured reason, not a guessed one.** `x.spacename`
(`AB=9` then `PRINT A B`) reads **9**: the crunch folds `A B` into the single
variable `AB`. So `SWAP A B` presents *one* argument, and the fault comes from
SWAP's second-argument check long before `req_comma`.

## 4. The two arms cut the two halves of one sentence

| knife | cut | moves |
|---|---|---|
| K-C1 | drop the `inc hl` — matched but not consumed | the `g.*` rows |
| K-C2 | `jp nz,stmt_error` → `ret nz` — a missing comma accepted | the `b.*` rows |

Each leaves the other half's rows alone, which is what says the helper does both
jobs rather than one.

⚠️ **Both cuts are size-neutral on purpose.** A cut that changes the byte count
can push a `jr` out of range; the build then fails, the ROM is left unchanged,
and `knife_guard` reports the knife **INERT** — which is exactly what happened
one slice earlier in D-RUNARG.

## 5. 📌 A divergence the row set found: `CLOSE` clears a FIELDed variable

| | CF-3300 | zerobas |
|---|---|---|
| `FIELD#1,10 AS A$` → `LEN(A$)` | 10 | **10** ✅ |
| ...then `CLOSE#1` → `LEN(A$)` | **10** | **0** 🔴 |

Reading **before** the `CLOSE` agrees, so `FIELD` is right: **`CLOSE` empties the
field variable here and does not on the reference.** The reference leaves the
descriptor pointing into the released buffer; zerobas resets it.

Pre-existing (identical before and after this carve), no prior adjudication found,
and filed rather than fixed — whether to keep a deliberately dangling descriptor
is a judgement, not a measurement.
