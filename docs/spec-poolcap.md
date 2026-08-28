# D-POOLCAP — a string function charged the pool twice for its own argument

**2026-08-28.** Narrows (does not close) the item D-FNGCROOT filed on 2026-08-27,
where a *control* — an expression with no `DEF FN` in it — failed on zerobas at
`CLEAR 100` while both references answered. **Zero bytes**; the threshold moves
**CLEAR 120 → 100**, and the remaining gap is measured and its site named.

## 1. Two explanations killed before the third was reached

**The pool is not smaller.** All three sides report identical readings:

| | grant `CLEAR 100` | grant `CLEAR 150` | free after the same stores | after one more concat |
|---|---|---|---|---|
| vg8020 / cf3300 / zb | 100 | 150 | 76 / 126 | 36 |

**The result is not over-allocated.** Reading `FRE("")` either side of a single
store — so the drop *is* the price — every side charges the same:

| store | vg8020 | cf3300 | zb |
|---|---|---|---|
| `Y$=LEFT$(X$,0)` | 0 B | 0 B | 0 B |
| `Y$=LEFT$(X$,5)` | 5 B | 5 B | 5 B |
| `Y$=LEFT$(X$,20)` | 20 B | 20 B | 20 B |
| `Y$=RIGHT$(X$,0)` / `MID$(X$,1,0)` | 0 B | 0 B | 0 B |

That refuted the obvious mechanism (a `LEFT$` result sized by its *source*). The
cost is a **transient peak**, which a before/after reading cannot see at all.

## 2. Bisecting the expression, then measuring the peak

Term by term, the first row that diverges names the term:

| row | vg8020 | cf3300 | zb |
|---|---|---|---|
| `LEN(STR$(FRE(""))+X$+X$)` | 43 | 43 | 43 |
| `LEN(X$+X$)` | 40 | 40 | 40 |
| **`LEN(LEFT$(…,0))`** | 0 | 0 | **Out of string space** |
| **`LEFT$(X$+X$,0)+A$`** | ABCD | ABCD | **Out of string space** |

🎯 `FRE("")` is **exonerated** — the last row contains none. What separates the
green rows from the red ones is the *source*: every passing row slices a
**variable**, every failing one slices a **temp**.

A peak shows up only as the minimum pool the expression needs at all, so walk
`CLEAR` down (24 B live, a 40 B temp):

| | `LEN(LEFT$(X$+X$,0))` works at | `LEN(LEFT$(X$,0))` at CLEAR 70 |
|---|---|---|
| vg8020 / cf3300 | **70** (lowest tested) | ✅ |
| zerobas | **120 only** | ✅ |

A 40 B temp, charged twice.

## 3. The cause was a known class with one site converted

`LEFT$`'s own header says it: *"Snapshot the source into an owned temp, then
truncate in place."* It called `str_snapshot_to_temp` — an unconditional copy —
and so did `RIGHT$` and `MID$`. But `str_snapshot_keep` already exists beside it,
and **its header describes exactly this defect**:

> a source that is ALREADY a temp-stack entry is returned AS-IS instead of being
> copied … with `CLEAR n` it was a second full charge against the user's pool.

D-CLP found the class, converted `basic/vars.asm`'s `str_set_key`, and left the
three string verbs. This is the same defect at the sites it was not applied to.

## 4. The fix, and the hazard it had to clear

`str_snapshot_arg` — an alias, not an `IF` at each of three call sites, because
the non-CLEARPOOL build has no `str_snapshot_keep` to call:

```
    IF CLEARPOOL
str_snapshot_arg equ str_snapshot_keep
    ELSE
str_snapshot_arg equ str_snapshot_to_temp
    ENDIF
```

**Zero bytes** — the same `call`, to a different label. All four walls unchanged:
low **39 B**, page 1 **89 B**, sub page 0 **2434 B**, sub page 1 **1622 B**.

🔴 **THE HAZARD IS IN LEFT$'s OWN SENTENCE: it truncates the snapshot IN PLACE.**
Handing back the source as-is means the truncation now mutates the source temp.
That is safe only while nothing else can still read it, which is a claim about the
row set, not about the code. Six rows were written to break it — nested slices, a
temp sliced two different ways in one expression, a slice printed beside a rebuilt
copy of the same concatenation:

| row | expression | all three sides |
|---|---|---|
| `h1.twice` | `LEFT$(X$+Y$,3)+"|"+X$+Y$` | `ABC\|ABCDEFGHIJKL` |
| `h2.nested` | `LEFT$(LEFT$(X$+Y$,8),3)` | `ABC` |
| `h3.midof` | `LEFT$(MID$(X$+Y$,2,8),3)` | `BCD` |
| `h4.bothend` | `RIGHT$(X$+Y$,3)+LEFT$(X$+Y$,3)` | `JKLABC` |
| `h5.var` | `LEFT$(Z$,3)+"|"+Z$` | `ABC\|ABCDEFGHIJKL` |
| `h6.deep` | `MID$(LEFT$(X$+Y$,9),3,4)+"|"+LEFT$(X$+Y$,2)` | `CDEF\|AB` |

No corruption observed. `string-acceptance`, `str-domain-acceptance`,
`strparen-acceptance`, `array-acceptance`, `deffn-strict` and `unit-test` are all
green, and **`switch-build-check` builds `CLEARPOOL equ 0`** — the arm the alias
exists for, and the one thing that could have made this fail to assemble.

## 5. What is still open, and where it lives

**The threshold moved 120 → 100. It did not reach 70.** zerobas still needs ~76 B
free where the references need ≤46 for the same expression, so **one extra charge
of roughly a temp remains**.

The next site is named, not guessed: `str_concat` snapshots **both** operands into
owned temps ([`basic/str-engine.asm:1435`](../basic/str-engine.asm:1435), *"Both
a$ and b$ are snapshotted into their OWN owned temp"*). For `X$+X$` that is
20 + 20 transient on top of the 40 B result. Here `keep` does not help — both
operands are *variables*, not temps — so closing the rest means re-reading the
descriptor after the allocation instead of copying it first, which is a different
and larger change.

⚠️ The `t.*` threshold rows are **not** in a gate. `t.70`/`t.80` are still red and
no probe here has an XFAIL class; the reproducer is
[`scratchpad/leftkeep_probe.py`](../scratchpad/leftkeep_probe.py). Pinning the
recovered ground (`t.100`, green now and red before) belongs in
`clearpool-acceptance`, whose own slice owns this pool.
