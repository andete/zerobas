<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — `BIN$` and `FRE`, the last two SILENT-GAP words

**Status:** ✅ **LANDED** `2facfc0`, `make binfre-acceptance` **83/83**. D-BF-A..D-BF-D
all signed off (§5); as-built in §8. Step 4 of
[`decision-kwgaps-slicing.md`](decision-kwgaps-slicing.md) §4.3. The behavioural
contract below is taken **entirely** from the committed measurement,
[`binfre-vg8020-characterization.md`](binfre-vg8020-characterization.md)
(`898299f`); nothing here is asserted from a manual.

Landing this empties the **SILENT-GAP class** — the arc's exit criterion, D-KW-3.

## 1. Scope

| in | out |
|---|---|
| `BIN$(n)` — the string function | `DEF FN`/`FN` (its own arc) |
| `FRE(n)` / `FRE(s)` — the two forms | `LOCATE`/`SWAP`/`TRON`/`TROFF`/`MOTOR` (the MISSING class, step 5) |
| **D-BF-1** `HEX$`/`OCT$` accept a string argument → `0` | |
| **D-BF-2** `OCT$` has no domain check → `OCT$(65536)` = `0` | |

D-BF-1 and D-BF-2 are in scope because they are **not a detour**: `BIN$` is the
third member of that family and needs precisely the check `OCT$` lacks and the
type test neither has. §3 shows they are cheaper to fix here than to leave.

## 2. Contract — `BIN$(n)`

* Unsigned 16-bit view of the domain −32768..65535; `BIN$(-1)` = `BIN$(65535)` =
  sixteen `1`s.
* **No leading zeros, always ≥ 1 digit** — `BIN$(0)` = `"0"`.
* **Up to 16 digits** (`LEN(BIN$(65535))` = 16).
* Float argument **truncates toward zero** — `BIN$(5.7)` = `101`.
* `n` outside the domain → `Overflow`. Missing/empty parens → `Syntax error`.
  String argument → `Type mismatch`.
* Token `$FF $9D`, oracle-measured. `BIN` without the `$` is **not** a keyword —
  `BIN(5)` stays an ordinary array element on both machines.

Every one of these matches `HEX$`/`OCT$` measured on the same run. `BIN$` is not
a new contract; it is the third instance of an existing one.

## 3. Placement — the family is a clone pair, and collapsing it funds `BIN$`

**Measured from `build/basic-reloc.sym`:** `str_fn_hex` = **43 B**,
`str_fn_oct` = **38 B**, at `$2C66` and `$2C91`. Both sit in the **low region**,
which has **7 B free** — the scarce wall. A third 43 B clone cannot go there.

The 5-byte difference between the two *is* D-BF-2: `str_fn_oct` is `str_fn_hex`
minus the `push hl` / `call fac_to_int_addr` / `pop hl` checked conversion
([`basic/str-engine.asm:969`](../basic/str-engine.asm:969)). Source and symbol
arithmetic agree exactly.

So the shape is the one §5a of the decision doc has been carving all arc:

```
today   str_fn_hex 43 + str_fn_oct 38                        = 81 B
after   shared body ~43 + 3 stubs (op byte + jp) ~6 each     ≈ 61 B
```

**≈ 20 B returned to the low region, and `BIN$` lands inside it.**
*(As built: 9 B returned, not 20 — the two argument checks D-BF-1/D-BF-2 cost
~17 B that the sketch above did not price. Still net positive, and still the
only way `BIN$` fits: §8.)* The
generalisation warning ([[generalisation-not-free-at-two-callers]]) says measure
the refactor *with* its beneficiaries: there are three here, not two, and the
third is the feature being paid for.

It also puts the argument handling in **one** place, so D-BF-1's type check and
D-BF-2's domain check are written once and apply to all three — rather than
three times, or (as today) once and not at all.

Both functions are **repack-only** (low region, behind `IF ROM_BASE < $4000`),
so the frozen lean `basic.rom` is untouched and needs no gating gymnastics.

### 3.1 The digit builder needs no scratch buffer

`HEX$`/`OCT$` build into `NUMBUF`, which is **8 bytes**
([`basic/sysvars.inc:753`](../basic/sysvars.inc:753)) — ample for their 4- and
6-digit worst cases. **`BIN$`'s 16 digits do not fit**, and this is the one
place `BIN$` cannot clone its siblings.

The answer is not a bigger buffer. `sh_temp_push_alloc` already takes the digit
count in `A` and hands back the body pointer, so `sh_bin_build` can **count the
significant bits first** (shift until zero, minimum 1), allocate, then fill the
body MSB-first from the known top bit — **no intermediate buffer at all**. It
lives in `sub/strheap.asm` beside `sh_oct_build` as **op = 14** (op 8 is
already `sh_fill`); sub.rom has ~3.5 KB
free on page 1 and ~4.5 KB on page 0, so the leaf compute is free.

`kwtable.inc` gains one entry (`db 4,"BIN$",2,PEEK_PREFIX,BIND_TOKEN`) — also
free, since the wave-3 eviction made the sub-ROM copy the sole source. One
`cp BIND_TOKEN / jp z,str_fn_bin` arm joins `str_func_ff`
([`basic/str-engine.asm:661`](../basic/str-engine.asm:661)): 5 B.

## 4. Contract — `FRE`, and the architectures genuinely differ

Measured on the reference:

* **Two independent pools.** `FRE(0)` reports free *variable/program* space,
  `FRE(s)` the *string* pool. `FRE(0)=FRE("")` is **false**; a 100-char string
  costs the string pool exactly 100 and the numeric pool only 6.
* The form is chosen by the argument's **type**, never its content:
  `FRE("")`, `FRE("ABCDE")` and `FRE(A$)` all agree.
* **The numeric argument is a dummy** (measured at equal depth; the naive
  mixed-depth test says the opposite — characterization §3.1).
* `FRE(s)` **compacts** the heap; after dropping a string the pool is whole.
* Missing parens, `FRE()`, `FRE(0,0)` → `Syntax error`.
* `FRE(0)` counts down to the **stack pointer** (6 B per nesting level). This is
  a VG-8020 internal and is **explicitly not part of the contract** — see §6.

### 4.1 zerobas has ONE gap where the reference has TWO pools

This is the crux of the slice and the reason D-BF-A exists.

```
zerobas          TXTTAB ..program.. PRGEND
                 [PRGEND+2, ARYTAB)   scalars
                 [ARYTAB,  ARYEND]    arrays  (ARYEND = live $0000 sentinel)
                 ARYEND+2 .. FRETOP   <-- THE ONE FREE GAP
                 [FRETOP, C)          string heap, grows DOWN, C = min(HIMEM,TXTMAX)
```

`heap_alloc` ([`sub/strheap.asm:392`](../sub/strheap.asm:392)) is a bump
allocator on the downward frontier `FRETOP` whose only floor is `ARYEND+2`.
There is **no string pool**: variables and strings compete for one gap. And
`CLEAR <string-space>` **evaluates its argument and discards it**
([`basic/clear.asm:61`](../basic/clear.asm:61)) — `heap_reset` sets
`FRETOP := min(HIMEM,TXTMAX)` regardless.

Consequences, stated plainly:

| reference row | reference | zerobas under a one-gap `FRE` |
|---|---|---|
| `FRE(0)=FRE("")` | 0 (differ) | **−1 (equal)** |
| `CLEAR 500:FRE("")` | 500 | the whole gap (thousands) |
| `CLEAR 200:FRE("")` | 200 | the whole gap |

The characterization's "**`CLEAR` pins the instrument**" move — the one place a
`FRE` *absolute* is legitimately comparable — is therefore **only available if
`CLEAR`'s string-space argument becomes a real pool boundary.** That is not a
detail of `FRE`; it is a change to the memory architecture.

## 5. Decisions required

### D-BF-A — how faithful should `FRE` be? *(the scoping question)*

> ✅ **ANSWERED: (c).** One-gap model in this slice; the `CLEAR` string-pool
> partition becomes its own named follow-on with its own spec and gate.

**(a) Two real pools.** Implement `CLEAR <n>` as a genuine string-pool
boundary: give the heap a floor at `C − n`, make `heap_alloc` collide against
*that* instead of `ARYEND+2`, and make variable/array growth collide against the
pool top. `FRE(0)` and `FRE("")` then mean what they mean on the reference, and
all five `CLEAR` absolutes become gateable.
*Cost: touches `heap_alloc`, `heap_reset`, `strheap_gc`, `ary_alloc` and
`ex_clear` — every one of which is currently green under its own gate. Large,
and the risk is concentrated in the string engine.*

**(b) One gap, documented deviation — RECOMMENDED.** `FRE(0)` and `FRE("")`
both report `FRETOP − (ARYEND+2)`, which is the truthful free-memory figure for
zerobas's actual architecture. Cheap (~35–45 B on page 1, which has 389 B free),
no change to the string engine, and it still clears the SILENT-GAP: today `FRE`
answers `0`, which is simply wrong; under (b) it answers how much memory there
actually is. Precedent: division is a documented deviation
([[bug-for-bug-compat-over-accuracy]]).
*Price: `FRE(0)=FRE("")` and all five `CLEAR` absolutes leave the gate (§6), so
the `FRE` battery keeps no absolute anchor except the allocation deltas.*

**(c) (b) now, (a) as its own follow-on slice.** The string-pool partition is a
coherent piece of work with its own spec, its own gate, and beneficiaries beyond
`FRE` (`CLEAR ,himem` is already record-only). This is (b) plus an honest TODO.

**Recommendation: (c).** Take the one-gap model in this slice, and open the
string-pool partition as a named follow-on rather than smuggling an
architecture change into a keyword slice.

### D-BF-B — gate the allocation-cost deltas?

Reference, at equal depth: `DIM A(100)` = **816** (101 × 8 + 8), `DIM A(10)` =
**96**, a scalar = **11**, `A$=STRING$(100,"A")` = **6** numeric + **100**
string.

These encode zerobas's **variable and array table layout**, not `FRE`. Gating
them asserts that layout matches the VG-8020 byte for byte.

> ✅ **ANSWERED: gate ALL of them** — my recommendation (gate only the
> layout-independent pair) was overruled, and the evidence says the stronger
> call was right.

**The claim was checkable before a line of `FRE` was written, and it checks
out.** `VARPTR` is implemented on both sides, and the stride between two
consecutive entries *is* the entry size those deltas are made of. The `layout`
battery (`make binfre-characterize ONLY=layout`) is **10/10**:

| what | ref | zerobas |
|---|---|---|
| scalar stride `VARPTR(Y)-VARPTR(X)` | 11 | **11** |
| two scalars apart | 22 | **22** |
| string descriptor stride | 6 | **6** |
| scalar → string entry | 11 | **11** |
| array element size | 8 | **8** |
| five elements | 40 | **40** |
| `DIM A(0)` stride (1 elem + header) | 16 | **16** |
| `DIM A(10)` stride | 96 | **96** |
| `DIM A(100)` stride | 816 | **816** |

Element size 8, array header 8, scalar entry 11, string entry 6 — identical on
both machines. So gating the `FRE` deltas asserts something that is **already
true**, and it will hold for the right reason rather than by luck. The layout
battery stays in the probe permanently: it is what will say *why* a `FRE` delta
row went red, distinguishing an `FRE` bug from a layout change.

### D-BF-C — fix D-BF-1 and D-BF-2 in this slice?

> ✅ **ANSWERED: yes.** §3 shows the collapse puts both checks in the one place
`BIN$` needs them anyway, so the marginal cost is close to zero and the
alternative is writing the same check a third time. Both are silent wrong
answers in the very class this slice exists to empty.

### D-BF-D — is `BIN$`'s implementation the counted-bits builder (§3.1)?

> ✅ **ANSWERED: yes** — it avoids the `NUMBUF` problem outright rather than
enlarging a shared scratch buffer that `MID$`-statement aliasing already
constrains ([`basic/sysvars.inc:758`](../basic/sysvars.inc:758)).

## 6. The gate

`make binfre-acceptance` — the characterization probe with `--gate`, every row
two-sided. Rows the probe already reports but **never** asserts, with reasons:

* **absolute `FRE` values** — two machines, two memory maps.
* **the numeric depth rows** — the VG-8020 evaluator's 6-B-per-level stack
  frame is a ROM internal, not a language contract.

Under D-BF-A(b) two more move to reported-not-gated, and the spec must say so
**before** the implementation rather than after it turns red:

* `FRE(0)=FRE("")` — one gap, so zerobas answers −1 where the reference answers 0.
* the five `CLEAR n` absolutes — `CLEAR`'s string-space argument is discarded.

Everything else is gated: all `BIN$` values and lengths, all `BIN$`/`FRE` error
rows, the `HEX$`/`OCT$` calibration (including the two D-BF fixes), the
equal-depth dummy-argument rows, the string-form purity and content-independence
rows, `fre-dim-drops`, the GC rows, the **ten `layout` rows**, and — per
D-BF-B — **all four allocation-cost deltas** (816 / 96 / 11 / 6 + 100).

The `layout` battery is the diagnostic that makes the delta rows readable: if a
delta goes red, `layout` says whether `FRE` broke or the variable/array table
moved. Gating both means the answer is never a guess.

**Falsification is part of Definition of Done**, not a nicety: the cursor slice
found two clauses each resting on a *single* row, which review had not noticed.
At minimum, break (i) the leading-zero suppression, (ii) the 16-digit count,
(iii) the domain check, (iv) the type check, and (v) the `FRE` form selection,
and confirm each moves the gate by more than one row.

## 7. Cost — an ESTIMATE, and the spike comes first

| piece | region | estimate |
|---|---|---|
| collapse `HEX$`/`OCT$` → shared body | low region | **−20 B** |
| `BIN$` stub + `str_func_ff` arm | low region | +11 B |
| D-BF-1 type check + D-BF-2 domain check (shared) | low region | +10 B |
| `FRE` — dispatch arm + the one-gap subtraction | page 1 | +35…45 B |
| `sh_bin_build` (op 8) | sub.rom | free |
| `kwtable.inc` entry | sub.rom | free |

Net: **low region ≈ +1 B against 7 B free** — uncomfortably tight — and **page 1
≈ +40 B against 389 B free**, comfortable.

⚠️ **This repo's estimates run optimistic**: the cursor cluster was estimated at
79 B and measured **109 B**, 38 % over. The low-region line above is close
enough to the wall that it must be a **measured spike, step one**, before any
behaviour is written — and `rm -rf build` first, because a warm tree once
reported 55 B free while the same sources overran by 14
([[measure-the-wall-from-clean]]). If the collapse does not return what §3
predicts, the fallback is to evict the whole family to a sub-ROM tenant, which
the playbook already covers.

## 8. As built (`2facfc0`)

| region | before | after | note |
|---|---|---|---|
| low region | 7 B free | **11 B free** | the collapse returned 9 B; `BIN$`'s `str_func_ff` arm spent 5 |
| page 1 | 389 B free | **311 B free** | `FRE` cost **78 B** against an estimated 35–45 |
| sub.rom | — | +`sh_bin_build`, +`sh_free_gap` | ops 14 and 15; free space, as predicted |
| lean cart | frozen | **byte-identical** | the whole family is repack-only |

**The estimate ran optimistic for the third slice running** — 78 B where 35–45
was predicted, ~75 % over, after the cursor cluster's 38 %. The low-region line
(the one that mattered) was the accurate one, because it was the one derived
from *measured* symbol sizes rather than reasoned about.

### 8.1 What the gate caught that the implementation forgot

`FRE` compacting the heap was **measured and written down** in the
characterization (§3 there) and then simply not carried into the code. The gate
found it as a 306-vs-6+100 divergence: `A$=STRING$(100,"A")` leaves the live
body *plus two dead temps* that only a collision would have collected.
`sh_free_gap` now compacts first.

Two further red rows were **not** bugs, and separating those two cases was the
substance of the fix rather than an afterthought — see §6's pool-separation
note. Every deviation that stayed red had been listed in §6 *before* the
implementation existed, so none of them was discovered by a red gate.

### 8.2 Falsification

Each clause was broken in turn and the gate re-run. All six are guarded, none by
a single row:

| broken clause | gate |
|---|---|
| `BIN$` leading-zero suppression | 72/83 — 11 rows |
| `BIN$` 16-digit width | 64/83 — 19 rows |
| the domain check (D-BF-2) | 78/83 — 5 rows |
| the type check (D-BF-1) | 81/83 — 2 rows |
| `FRE` string-form selection | 77/83 — 6 rows |
| `FRE` compaction | 81/83 — 2 rows |

**The last line is the one that justifies replacing a row rather than trusting
it.** `fre-gc-stable` reads `FRE` twice and agrees whether or not anything is
collected — **green while measuring nothing**. Both rows that catch a broken
compaction are the ones added to replace it (`fre-gc-teeth`, which pre-creates
the variable and allocates/drops the string *between* the two readings). Had the
original row been left to stand, breaking compaction would have moved the gate by
**zero**.

Two of the six were also a lesson in falsifying *properly*: the first attempt at
the type check inserted an instruction and merely broke the build, and the first
attempt at compaction patched the wrong `strheap_gc` call site. **A falsification
that fails to build, or fails to apply, has proved nothing** — both were redone
size-neutrally against the right line.

### 8.3 Follow-on opened by this slice

**The `CLEAR` string-pool partition** (D-BF-A(a), deferred as (c)). Give the
heap a floor at `C − n`, make `heap_alloc` collide against it instead of
`ARYEND+2`, and make variable/array growth collide against the pool top. That
would move six rows out of recorded-not-gated and back into the gate:
`FRE(0)=FRE("")`, the five `CLEAR n` absolutes, and the three pool-separation
rows. It is a string-engine change and wants its own spec and gate.
