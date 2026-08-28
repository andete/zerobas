# D-DIMBARE — `DIM`'s bound list is optional, and the source said it was not

**Status:** SHIPPED 2026-08-28. **11 DIFF → 0**, **+1 B of the low region**
(38 B free on 2026-08-28 — a reading; `make basic-reloc` is the current one).

## 1. How this was found

Not by looking for it. D-POPRAISE ([spec-popraise.md](spec-popraise.md)) needed a
BASIC row that reached `ee_synerr_pop`, one of the `stmt_error` discard-tails it
was pricing. `arrays.asm:601` reaches that tail with the comment

> `jr ee_synerr_pop ; DIM requires a bound list`

so the row was `DIM A`. It came back **`OK` on both references and `ERR 2` on
zerobas** — the witness row was a divergence, and the justification beside the
code was false. [[a-justification-parenthesis-is-an-unrun-claim]], this time in
the source rather than in a filing.

## 2. What the references actually do — characterised, not assumed

A bare "they accept it" is the sort of claim nobody re-runs, so the behaviour was
mapped before anything was written. `scratchpad/popmerge_probe.py`, VG-8020 +
CF-3300 + zerobas, one boot per row:

| row | statement | references | zerobas (before) |
|---|---|---|---|
| `s.dim` | `DIM A` | `OK` | `ERR 2` |
| `d.str` | `DIM A$` | `OK` | `ERR 2` |
| `d.list` | `DIM A,B` | `OK` | `ERR 2` |
| `d.mixed` | `DIM A,B(2)` | `OK` | `ERR 2` |
| `e.after` | `DIM A(2),B` | `OK` | `ERR 2` |
| `e.before` | `DIM B,A(2)` | `OK` | `ERR 2` |
| `e.twoname` | `DIM A B` | `OK` | `ERR 2` |
| `d.scalar` | `DIM A : A=5 : PRINT A` | `5` | `ERR 2` |
| `d.aselem` | `DIM A : A(0)=5 : PRINT A(0)` | `5` | `ERR 2` |
| `d.twice` | `DIM A : DIM A` | `OK` | `ERR 2` |
| `d.thenary` | `DIM A : DIM A(2)` | `OK` | `ERR 2` |

🎯 **The last two carry the semantics.** Neither reports `Redimensioned array`,
so the ignored item **creates nothing** — `DIM A` is not "declare A with a
default bound", it is a no-op for that item. That is what makes falling into the
list continuation the faithful fix rather than allocating anything.

(`DIM A B` fits the same rule: MSX strips spaces, so it is `DIM AB` — a single
bare name. `docs/spec-basic-arrays-slice2-erase.md` §326 already recorded that
tokenisation for `ERASE`.)

## 3. Two rules fitted all eleven rows

* **(a)** an item with **no bound list** is accepted and ignored;
* **(b)** `DIM` is simply **lax about anything that is not `(`**.

Both agree on every row in §2, so the rows in §2 cannot choose between them —
[[two-rules-that-coincide-on-every-row-you-have]]. The cases that *separate* them
were measured **before** the fix was written:

| row | statement | references | zerobas | verdict |
|---|---|---|---|---|
| `e.bare` | `DIM` | `ERR 2` | `ERR 2` | (b) would accept → **regression** |
| `e.trail` | `DIM A,` | `ERR 2` | `ERR 2` | (b) would accept → **regression** |
| `e.digit` | `DIM 1` | `ERR 2` | `ERR 2` | already agrees |
| `e.dollar` | `DIM $` | `ERR 2` | `ERR 2` | already agrees |
| `e.openpar` | `DIM A(` | `ERR 24` | `ERR 24` | already agrees |

**Rule (a).** The wider reading would have planted regressions in rows that were
green, which is the whole reason the separation was measured first.

## 4. The fix — 3 bytes for 2, +1 B

`basic/arrays.asm`, where `jr ee_synerr_pop` (2 B) stood:

```
                pop     af                  ; discard [STR?] -- nothing is created
                jr      ed_next             ; +1 B of the low region
```

`ed_next` is a new **label, 0 B**, on the existing `skip_spaces / cp ',' /
jr nz,ed_done / inc hl / jr ed_lp` continuation. Re-entering through `ed_lp`
rather than bypassing it is what keeps `is_letter` guarding the next item. Low
region 39 → 38 B free. Everything else on the `ed_haveparen` path is untouched,
which is why `DIM A(` keeps its `ERR 24`.

## 5. Falsification — three claims, three cuts, and one prediction that missed

[`scratchpad/dimbare_knives.py`](../scratchpad/dimbare_knives.py). Guarded per
D-KNIFEGUARD (originals in memory, restored by `try/finally` **and** `atexit`).

| knife | claim | moved |
|---|---|---|
| **K-DB1** | the fix is what moves the rows | **11** — exactly the §2 set, back to `ERR 2` |
| **K-DB2** | `jr ed_next` (not `ed_done`) is load-bearing | **3** — `d.list`, `d.mixed`, `e.before`; the single-item rows stayed green |
| **K-DB3** | the green guard rows are genuinely guarding | **2** |

K-DB3 is the one that had to exist. The §3 separating rows are green *before and
after* the fix, so on their own they prove nothing at all; K-DB3 cuts `ed_lp`'s
`is_letter` reject to `ed_next` — making rule (b) real — and asks which of them
notices.

### 🔴 Predicted 4, measured 2 — and the other two agree for a different reason

`DIM` and `DIM A,` went green under K-DB3. **`DIM 1` and `DIM $` did not.** They
still error, through a **second cause** this line has nothing to do with: the
offending token is left under HL, `ed_done` reaches `exec_stmt`, and `exec_stmt`
rejects it there. So the §3 claim is narrower than first written — rule (b) would
have shipped **two** regressions, not four — and two of those rows are
[[a-case-that-agrees-can-agree-for-the-wrong-reason]]: they agree under both
rules, via a mechanism that is not the guard being tested.

## 6. Prose corrected rather than deleted

A fix falsifies the paragraph beside the code it adds, and no gate reads prose
([[a-fix-falsifies-the-justification-beside-it]]). Two places asserted the
refuted grammar and now carry the inverted conclusion plus the evidence:

* [`basic/arrays.asm`](../basic/arrays.asm) `ex_dim`'s header — *"For each
  comma-separated `NAME(b0[,b1...])`"*;
* [`spec-basic-arrays.md`](spec-basic-arrays.md) §`ex_dim` — the same grammar.
