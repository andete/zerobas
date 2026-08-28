# D-HALFIDX — IXH / IXL / IYH / IYL: a measured **no** on size, a live candidate on speed

**Status:** FILED 2026-08-28, nothing taken. Asked by Joost. Sweep:
[`scratchpad/halfindex_sweep.py`](../scratchpad/halfindex_sweep.py) (`--selftest`).

## 1. The question is not hardware

Joost confirmed (2026-08-28) that IXH/IXL/IYH/IYL are supported by **every
official MSX machine**, and `pasmo` assembles them correctly — `ld ixh,5` →
`DD 26 05`, `ld a,ixl` → `DD 7D`, `inc iyh` → `FD 24`, `add a,iyl` → `FD 85`.
Availability is settled and is not re-litigated here. The question is what they
are **worth**.

## 2. What the tree does today: three references, none of them an optimisation

| site | what it is |
|---|---|
| [`basic/initext.asm:127`](../basic/initext.asm) | `IYh` = slot id for `CALSLT` |
| [`basic/subromcall.asm:49`](../basic/subromcall.asm) | `IYh` = sub-ROM slot id (`CALSLT` ABI) |
| [`sub/format.asm:76`](../sub/format.asm) | `IYh` = disk-ROM slot id |

All three are the **MSX inter-slot call ABI**, not register allocation. So `IY`
is already spoken for on any path that reaches a BIOS or sub-ROM call, and `IX`
is a working pointer in the busiest files (167 refs in `sub/strheap.asm`, 136 in
`sub/arrays.asm`, 99 in `basic/expr.asm`).

## 3. 🎯 The prefix byte decides the whole size axis

Every half-index access costs **2 B** (`ld ixl,a` = `DD 6F`), against **1 B** for
a normal register and **1 B each** for `push rr` / `pop rr`. A half-index
register therefore **never beats a register or the stack for size**. It beats
only a *memory* temporary at 3 B per access, which reduces the entire size
opportunity to exactly one shape:

```
        ld   (cell),a       3 B   ->   ld   ixl,a      2 B
        ...                            ...
        ld   a,(cell)       3 B   ->   ld   a,ixl      2 B
                            ---                        ---
                            6 B                        4 B     = 2 B per pair
```

## 4. The sweep, and the test that actually decides it

Counted conservatively: named cell only (pointer derefs `(hl)`/`(de)`/`(bc)`/
`(sp)`/`(ix)`/`(iy)` are not temporaries), and **no `call`/`rst` inside the
window** — a call may clobber IX/IY, and `CALSLT` demonstrably does, per §2.

| region | pairs | ceiling |
|---|---|---|
| sub ROM | 24 | 48 B — but sub had 2444 + 1622 B free on 2026-08-28 |
| MAIN low | 7 | 14 B |
| MAIN page 1 | 6 | 12 B |

🔴 **Then the test that settles it: a spill is convertible only if NOTHING ELSE
READS THE CELL.** A cell with other readers is not a spill, it is state, and the
value has to stay in memory. Every main-region candidate but one fails it:

| cell | refs | verdict |
|---|---|---|
| `factyp` | 36 | state |
| `fp_lhsval` | 12 | state |
| `directf` | 10 | state |
| `in_rdlen` · `trapena` | 9 | state |
| `mul_i` · `mul_carry` · `cas_wcnt` | 8 | state |
| `scan_prim` | 6 | state |
| `subslot_ok` | 4 | state |
| **`mul_adig`** | **2** | ✅ the only convertible pair ([`float-arith.asm:827→844`](../basic/float-arith.asm), MAIN low) |

## 5. Verdict

* **SIZE — no.** **1 convertible pair, 2 B**, of 13 raw main-region hits. Not
  worth a slice, and worth writing down so the 26 B ceiling is not re-quoted by
  someone who stops at §4's table. This is the same lesson as
  [[grep-the-idiom-beats-the-clone-ranking]]: the raw hit count is a nominal
  price, and one more question turns it into a real one.
* **PERF — the live axis, unmeasured.** The 24 sub-ROM pairs sit in the inner
  loops (**9 in `sub/graphics.asm`**, 11 across `fp_rnd` / `fp_log` / `fp_sqrt`),
  where sub bytes are ~free so the prefix cost does not bite. T-states for the
  round trip: **memory pair 26, `push`/`pop` 21, half-index 16**, with no memory
  or stack traffic at all. That is the same territory as the PAINT perf work
  (3× → 2.02×, [[paintvram-slice]]) and it has **no measurement yet** — a
  candidate, not a finding.
