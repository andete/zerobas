<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-ARR-B — the array size bound (`Subscript out of range` before allocation)

**Status: SPEC, awaiting sign-off (S-ARR-B-1..4).**
Measurement: [`arrdim-vg8020-characterization.md`](arrdim-vg8020-characterization.md),
`make arrdim-characterize`, baseline **27/46 gated rows** (3 reported-never-gated).
Reopens one divergence in the concluded arrays/`DIM` arc
([`spec-basic-arrays.md`](spec-basic-arrays.md) §4 target **#9**, asked and never
answered).

---

## 1. The divergence

`DIM Q(20000)` answers **`Subscript out of range`** on the reference and **`Out of
memory`** here. Nineteen measured rows, one root cause: the reference rejects an
array whose element data would not fit a 16-bit byte count, *before* it tries to
allocate; zerobas allocates until it hits its ceiling, so its error is right only
by accident of size.

---

## 2. The contract to implement

> **`elsize × Π(boundₖ + 1) > $FFFF` ⇒ `Subscript out of range` (ERR 9 /
> `FPERR=5`), raised before any allocation is attempted and before the ceiling is
> consulted.**

Pinned by measurement, each clause independently:

| clause | pinned by |
|---|---|
| it is a **byte** count, not an element count | the flip moves with element width: `%` 32766/32767, `!` 16382/16383, `#` 8190/8191 — all at 65536 bytes (§1.1). `Q%(32767)` has 32768 elements, which fit a word, and still raises |
| the **header is excluded** | `Q%(32766)` = 65534 data bytes → `Out of memory`; any header would have pushed it over (§1.2) |
| the test is **`>`**, not `>=` | `Q$(21844)` = 21845 × 3 = `$FFFF` exactly → `Out of memory` (accepted by the bound, rejected by the allocator); `Q$(21845)` raises (§1.3) |
| it is the **product**, position-independent | `Q%(200,200)` raises with no dimension near a ceiling; `(32767,0)` and `(0,32767)` both raise; `Q%(150,150)` (45602 B) does not (§1.4) |
| `elsize($) = 3` | the same `Q$` pair — a 2-byte string element puts both far under the limit (§1.3) |
| it lives in the **allocator**, not in `DIM` | `Q(1,1,1,1)=1` on an *undeclared* array auto-dims to 10 per dimension = 117128 B and raises, with no `DIM` in the line and no large number in it either (§1.5) |

Unchanged, and already correct here (all measured, all agreeing today):

- a subscript past int16 is **`Overflow`** — the coercion beats the bound;
- a negative subscript is **`Illegal function call`**;
- a fractional bound is coerced first, then bounded (`DIM Q(20000.7)` → the bound);
- **`Redimensioned array` beats the bound** (`DIM Q(3):DIM Q(20000)`);
- the bound beats a **deferred syntax error** (`DIM Q(20000),`) — the same
  ordering D-MISS-2 settled for `MID$(A$,0,)` and D-WID for `WIDTH 41,`;
- a failed `DIM` **writes nothing**, and **earlier items in the same `DIM` list
  survive** (`DIM P(2),Q(20000)` leaves `P` live).

---

## 3. Design — route the two overflow detections that already exist

⚠️ **No new arithmetic.** [`sub/arrays.asm`](../sub/arrays.asm) already computes
exactly the quantity the rule needs, and already detects both overflows:

```
ary_alloc:
    ...
    call    ary_count_elems     ; DE = Π(boundₖ+1),  CF = overflow
    jp      c,aal_oom           ; <-- site A
    ...
    call    ary_mul16_checked   ; DE = elsize × count, CF = overflow
    jp      c,aal_oom           ; <-- site B
```

Both currently land on `aal_oom` (`ARY_ERR=4` → `ary_errmap` → `FPERR=6` → `Out of
memory`). **The measured rule is that sites A and B — and only they — are
`Subscript out of range`.** The two sets are provably identical: the byte product
`elsize × Π(boundₖ+1)` exceeds `$FFFF` exactly when the element product overflows
(site A — and then the byte product certainly does, since `elsize ≥ 2`) or the
`elsize ×` step does (site B).

The change is the epilogue plus two jump targets:

```
aal_soor:
                ld      a,1                 ; ARY_ERR: Subscript out of range
                jr      aal_unframe
aal_oom_pop1:
                pop     hl                  ; discard [DEND]
aal_oom:
                ld      a,4                 ; ARY_ERR: Out of memory
aal_unframe:
                <10 × inc sp>               ; deallocate the scratch frame
                or      a                   ; CF clear
                ret
```

`ld a,4` moves from *after* the `inc sp` run to *before* it, which is free: `INC
SP` touches neither `A` nor any flag, and the `or a` still clears `CY`. Sites A and
B become `jp c,aal_soor`.

Three details that make this safe rather than merely short:

1. **Stack depth.** Sites A and B are both *before* the `push hl` that
   `aal_oom_pop1` exists to undo, so the 10-byte frame is the whole of the unwind
   — `aal_soor` must not, and does not, pop anything else.
2. **The auto-dim path comes along for free**, which §1.5 says it must:
   `ary_resolve`'s auto-dim allocates through this same `ary_alloc`, so
   `Q(1,1,1,1)=1` gets the bound without a second site. A check written in
   `ex_dim` instead would have satisfied every other row in the matrix and left
   that one silently wrong.
3. **The other three carry checks stay `Out of memory`** — `tail + header`,
   `+ data bytes`, and the `+2` terminator reservation are **address-space wraps**,
   not size-rule violations. Any case reaching them has a byte count ≤ `$FFFF`,
   which the reference accepts and then fails on its own ceiling.

`ary_errmap` already maps `ARY_ERR=1 → FPERR=5 → "Subscript out of range"`
([`basic/arrays.asm`](../basic/arrays.asm)); no main-ROM change of any kind.

---

## 4. Cost and funding

**Estimated +4 bytes** (`ld a,1` + `jr`), entirely inside the `sub/arrays.asm`
page-0 tenant. **No carve, no promotion, no main-ROM byte.**

⚠️ This is the one place the walls do not bite. The tree stands at **4 B free in
the low region and 10 B in page 1**, and the clone frontier is dry — but the sub-ROM
has kilobytes, and the fix is genuinely leaf compute inside a tenant that already
computes the quantity ([[kwgaps-placement-not-funding]], which
[[missing-class-slice]] corrected to hold *only* for leaf compute; this qualifies,
where `LOCATE`/`SWAP` did not). **The estimate is not the cost — it is measured
from clean after the build** ([[measure-the-wall-from-clean]]).

---

## 5. Falsification plan — two sites, two disjoint row sets

The surgical falsification is unusually clean here, because the two sites catch
**different rows**:

| falsification | rows that must go red | rows that must survive |
|---|---|---|
| site **A** back to `aal_oom` | `dim-3d` alone (68921 elements — the only gated row whose *element* product overflows) | the other 18 |
| site **B** back to `aal_oom` | the other 18 | `dim-3d` |
| both | all 19 | the 27 |

A blunt falsification proves the file matters; this one proves each row measures
the site it is supposed to
([[gate-can-be-green-while-measuring-nothing]]).

The 27 rows that already pass are the standing survivor set — in particular
`dim-150x150`, `typ-i-32766`, `typ-s-16382`, `typ-d-8190`, `typ-str-21844` and
`auto-4d-int` are the *just-under-the-limit* controls: if the fix is off by one in
the wrong direction they go red while the divergent rows go green, and a tally
alone would look like progress.

---

## 6. Corpus fallout

- **`oos-dim-huge` graduates.** [`basic_probe_clearpool.py`](../probes/basic/basic_probe_clearpool.py)
  carries `CLEAR 100 : DIM Q(20000)` in its `arr` battery, reported and never
  gated, with the standing note that "it will turn from `----` to a gateable row
  the day the ARRAYS arc fixes it." This slice is that day: the row moves into a
  gated battery and D-CLP's tally goes 51/51 → 52/52 with 5 ungated.
- **`tests/test_arrays.py`** exercises `ARY_ERR` codes directly. Any case that
  drives an *overflowing* bound list and asserts `4` must become `1`; cases that
  overflow the **ceiling** (test 8/8d — a lowered `HIMEM`) keep `4` and are the
  unit-level counterpart of §3's third point. To be enumerated during
  implementation, not guessed here.
- **`make arrdim-acceptance`** becomes a standing gate alongside
  `clearpool-acceptance`.
- Full corpus re-run, not just this slice's gate ([[baseline-the-gate]] — D-CLP's
  first run piped each gate through `tail -6` and hid thirteen failures).

---

## 7. Open questions — SIGN-OFF REQUIRED

**S-ARR-B-1 — route the existing detections, or add an explicit pre-check?**
*Recommendation: route.* The sets are provably identical (§3), it costs 4 B against
an explicit check's ~20+, and it introduces no arithmetic that could itself be
wrong. The counter-argument is legibility: "bound the dimension before allocating"
reads as a *check*, and this implements it as an error-code choice on an existing
failure path. §3's block comment is where that has to be said in the source.

**S-ARR-B-2 — does D-ARR-C (`MAXDIM = 4`) fold into this slice?**
*Recommendation: no.* The reference accepts **at least twelve** dimensions where
zerobas raises `Subscript out of range` at five (§4a.1) — a live divergence found
by this matrix's calibration, but on a different cost axis entirely (RAM in the
`ARY_IDX` block, plus every descriptor widening) and with no relation to the
byte-count rule. It is recorded as three reported-never-gated rows carrying their
reason, exactly as D-CLP recorded this slice.

**S-ARR-B-3 — confirm the three address-space wrap checks stay `Out of memory`.**
*Recommendation: yes* (§3, point 3). No row can currently distinguish them —
reaching one requires a byte count ≤ `$FFFF` *and* a tail high enough to wrap
`$FFFF`, which needs a memory map neither machine has. **This is a reasoned
choice, not a measured one, and is flagged as such.**

**S-ARR-B-4 — is `arrdim-acceptance` a standing gate?**
*Recommendation: yes*, and `oos-dim-huge` graduates out of D-CLP's `arr` battery
in the same commit (§6).

---

## 8. Out of scope

- **D-ARR-C**, the dimension-count cap (S-ARR-B-2).
- The **`Out of memory` threshold itself**. It is a property of each machine's
  memory map (~28.8 KB free variable space on the reference, ~15.7 KB here) and can
  never be made to agree; every row in the matrix is sized past both.
- `OPTION BASE` — measured absent from MSX1 in the original arc (§4.1 #2).

---

Related: [[clearpool-slice]], [[arrays-dim-arc]],
[[answer-signoff-questions-by-measuring]], [[measure-the-wall-from-clean]],
[[gate-can-be-green-while-measuring-nothing]].
