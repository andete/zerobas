# D-INTERPSPEED — zerobas's interpreter is 2.5–3.1× slower than the CF-3300, on everything

*Measured 2026-09-02. Probe:
[`scratchpad/interpspeed_probe.py`](../scratchpad/interpspeed_probe.py).
**Measurement only — no code change.***

## 1. How this was found, which matters

Not by looking for it. D-PUTTIME was measuring per-`PUT` cost and added a
pure-CPU row — `FOR I=1 TO 2000:NEXT` — for one reason only: to prove `TIME` can
see CPU work at all before trusting it on disk work. It can. **The control was
the finding.**

## 2. The measurement

`TIME` is the 50/60 Hz jiffy counter, read from inside the machine, so the
harness's step is not in the loop — which matters, because a fixed step is
exactly what produced two days of wrong conclusions about `PUT`
([`spec-basic-put3slow.md`](spec-basic-put3slow.md)).

| row | construct | CF-3300 | zerobas | ratio |
|---|---|---|---|---|
| `s.for1k` | `FOR I=1 TO 1000:NEXT` | 96 | 295 | **3.07×** |
| `s.for2k` | `FOR I=1 TO 2000:NEXT` | 200 | 611 | **3.06×** |
| `s.for4k` | `FOR I=1 TO 4000:NEXT` | 407 | 1242 | **3.05×** |
| `c.goto2k` | `I=I+1:IF I<2000 THEN 30` — **no FOR at all** | 718 | 1797 | **2.50×** |
| `c.while` | `FOR J=1 TO 2000:I=I+1:NEXT` | 576 | 1692 | **2.94×** |
| `c.str` | `FOR I=1 TO 500:A$="AB"+"CD":NEXT` | 122 | 300 | **2.46×** |
| **`z.none`** | `X=1` — the floor | **0** | **0** | — |

## 3. Why the number is trustworthy

* **It is a ratio, not an offset.** 3.07 / 3.06 / 3.05 across a 4× range of loop
  counts. A fixed per-statement overhead would shrink as the loop grows; this
  does not move.
* **It is not `FOR`/`NEXT`.** `c.goto2k` has no `FOR` machinery anywhere and is
  still 2.50×. So the subject is statement dispatch and expression evaluation,
  not one verb.
* **The floor is clean.** `z.none` reads 0 on both, so the fixture contributes
  nothing to the numbers above.
* 🔴 **AND THE CLOCK IS THE SAME.** The obvious dissolution is that the two
  machines are clocked differently — that would produce exactly this and mean
  nothing. Checked: neither `National_CF-3300.xml` nor
  `C-BIOS_MSX1_EU_REPACK_DISK.xml` carries a clock-frequency tag and both are
  `<type>MSX`, so openMSX runs both at the standard 3.58 MHz Z80.
  [[apparatus-is-part-of-the-measurement]]

## 4. 🎯 It reframes the `PAINT` item

`TODO.md` carries *"`PAINT` IS STILL 1.9–2.0× SLOWER THAN BOTH REFERENCES"* as an
open performance defect. If the interpreter baseline is **2.5–3.1×**, then PAINT
at 1.9× is **faster than the machine it runs on** — its gap is measured against a
zero that does not exist on this tree. The same applies to any future speed
comparison: *the baseline is not 1.0*.

⚠️ That does not make the PAINT item wrong, and it is not retracted here — PAINT
is graphics-heavy and may have its own gap on top of the baseline. It means the
number needs re-reading against 2.5–3.1×, not against 1.

## 5. Mechanism: the CALSLT hypothesis, tested and REFUTED

*Added 2026-09-02, same day. §5 below is kept as filed; this section is what
happened when it was run.*

The hypothesis was that the repack's sub-ROM eviction — code reached by
`subrom_call`/CALSLT, bought to free MAIN PAGE 1 — puts a cross-slot call on a
per-statement path and so costs a broad constant factor.

**Step 1 — is there such a call? YES, and on a hotter path than expected.** A
bounded call-graph walk over `basic/` finds:

```
exec_stmt  -> subrom_call: NOT REACHABLE
ex_next    -> subrom_call: NOT REACHABLE
ex_if      -> subrom_call: NOT REACHABLE
ex_for     -> ex_for -> for_set -> var_store_fac -> vsf_coerced
                     -> var_alloc_or_find -> ary_engine_call -> subrom_call
```

and `var_alloc_or_find` is **not** the array path despite the name of its callee:
it sets `op = 5 SCALAR_ALLOC` and calls `ary_engine_call` **unconditionally**. So
*every scalar variable store crosses a slot*, once per assignment.

**Step 2 — does it cost anything? NO, not disproportionately.** Two rows differ
by exactly one scalar store per iteration:

| | CF-3300 | zerobas |
|---|---|---|
| `FOR I=1 TO 2000:NEXT` | 200 | 611 |
| `FOR J=1 TO 2000:I=I+1:NEXT` | 576 | 1692 |
| **marginal cost of the store** | **376** | **1081** |

**1081 / 376 = 2.87×** — the same as the 2.5–3.1× baseline, in fact slightly
*below* it. If the cross-slot call carried a cost unique to zerobas, this
marginal ratio would be far above 3, not under it.

🎯 **AND THE ORDERING POINTS THE SAME WAY.** `FOR`/`NEXT` (3.06×) does **not**
cross a slot per iteration — `ex_next` writes through the cached `FOR_CUR`
address — while the `GOTO` loop (2.50×) crosses one per iteration for its store.
**The path that crosses a slot is the LESS slowed of the two.** A dominant CALSLT
cost predicts the opposite.

⇒ **The eviction is not what makes this tree slow.** The 2.5–3.1× is in the
interpreter's own resident code, and optimising it means optimising that code —
not un-evicting tenants. That matters, because "the repack bought space with
speed" is the intuitive story and it is wrong.

⚠️ **WHAT THIS DOES NOT SAY:** that the cross-slot scalar store is free, or that
no OTHER tenant call is expensive. It says this one is not the explanation for
the constant factor. A per-call cost of the same order as everything else is
still a cost.

## 5b. The hypothesis as originally filed

The repack build evicts a great deal of code into **sub-ROM tenants** (page-0 and
page-1 islands reached by `subrom_call`/CALSLT), and it does so to buy MAIN PAGE
1 SPACE — the constraint nearly every slice in `TODO.md` is fighting. Cross-slot
calls are expensive. **If any per-statement or per-iteration path crosses a slot,
that would produce a broad constant-factor slowdown of exactly this shape.**

🔴 **UNTESTED, AND THE TEST EXISTS.** The tree still has build switches for
non-repack configurations; running the same rows on a build whose tenants are
inline would separate "the eviction cost this" from "the interpreter is simply
written this way". Until that is run, §5 is a story that fits, which is the
weakest kind of evidence and the kind this project has been burned by twice
today (a cluster leak and a stale cache key, both plausible, both refuted).
[[filed-justification-is-a-claim]]

## 6. What is NOT claimed

* Nothing about whether 3× matters. That is a charter question — the project
  targets *faithful* MSX1 BASIC, and whether faithful includes speed is Joost's
  call, not a measurement.
* Nothing about the cause (§5).
* `c.arith` (`FOR I=1 TO 2000:X=I*2+1:NEXT`) has **no zb reading**: at 1004
  jiffies on the reference, 3× exceeds even the 60 s step. Consistent with the
  finding, but it is an absence and is not counted as a data point.
