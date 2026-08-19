<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# `BIN$` and `FRE`, characterised against the VG-8020

**Status:** MEASUREMENT RECORD, 2026-07-27. Input to step 4 of
[`decision-kwgaps-slicing.md`](decision-kwgaps-slicing.md) §4.3 — **the last two
SILENT-GAP words**. Produced by
[`probes/basic/basic_probe_binfre.py`](../probes/basic/basic_probe_binfre.py)
(`make binfre-characterize`). Reference: `Philips_VG_8020`.

Today both parse as something else and answer without complaint: `BIN$(n)` as
the string array `BIN$` → `""`, `FRE(x)` as the array `FRE` → `0`.

## 1. Method — two words, two opposite measurement problems

`BIN$` is a **pure function of its argument**, so every answer is comparable
across the two machines. Better still, it has a family already implemented on
*both* sides — `HEX$` and `OCT$` — sharing its argument domain. Those rows are
the calibration battery, and they pin `BIN$`'s entire argument and error
contract using code that is not under test. (They also found two bugs; §5.)

`FRE` reports **memory**, and the two machines do not have the same memory. Its
absolute value is not comparable and never will be — a gate asserting one is
asserting that zerobas's memory map equals a VG-8020's. So `FRE` is measured
through **relations**: comparisons, and deltas between two readings.

### 1.1 `CLEAR` would pin the instrument — on a machine with a string pool

The cursor slice needed `WIDTH 40` before a single column could be compared.
`FRE` looked like it had the same move available: **string space is not a
property of the reference machine, the program sets it.** After `CLEAR 500` the
VG-8020 has been *told* to hold 500 bytes, so `FRE("")` becomes an absolute that
is legitimately comparable.

> ⚠️ **It turned out not to be usable, and that is a finding, not a footnote.**
> zerobas has **one free gap** where the reference has **two pools**, and
> `CLEAR`'s string-space argument is evaluated and discarded — so there is no
> pool to size. The rows below are still the right measurement of the
> *reference*; they simply cannot be *asserted* until the string-pool partition
> lands as its own slice (spec D-BF-A(c), §5 there). **The instrument-pinning
> move was real; the instrument it would have pinned does not exist on this
> side yet.**

| row | reference |
|---|---|
| `CLEAR 500:PRINT FRE("")` | **500** |
| `CLEAR 200:PRINT FRE("")` | **200** |
| `CLEAR 100:PRINT FRE("")` | **100** |
| `CLEAR 500:A$=STRING$(100,"A"):PRINT FRE("")` | **400** |
| `CLEAR 500:` + a 100- and a 50-char string | **350** |

Exact, to the byte, at every size. The string pool is `CLEAR`'s argument minus
the bytes actually held.

## 2. `BIN$(n)` — unsigned 16-bit, no leading zeros, up to 16 digits

| n | `BIN$(n)` | `LEN` |
|---|---|---|
| 0 | `0` | 1 |
| 1 | `1` | 1 |
| 2 | `10` | 2 |
| 5 | `101` | 3 |
| 255 | `11111111` | 8 |
| 256 | `100000000` | 9 |
| 32767 | `111111111111111` | 15 |
| 32768 | `1000000000000000` | 16 |
| 65535 | `1111111111111111` | 16 |
| −1 | `1111111111111111` | 16 |
| −2 | `1111111111111110` | 16 |
| −32768 | `1000000000000000` | 16 |
| 5.7 | `101` | 3 |
| −5.7 | `1111111111111011` | 16 |

Identical in shape to `HEX$`/`OCT$`, measured on the same run:

* **unsigned 16-bit view** of the domain −32768..65535 — `BIN$(-1)` and
  `BIN$(65535)` are the same string, exactly as `HEX$(-1)` = `FFFF`.
* **float truncates toward zero** — `BIN$(5.7)`=`101`, and `BIN$(-5.7)` is the
  pattern for −5, matching `HEX$(-5.7)`=`FFFB`.
* **no leading zeros, always ≥ 1 digit** — `BIN$(0)`=`"0"`, as `HEX$(0)`=`"0"`.
* concatenates and assigns like any temp: `"<"+BIN$(5)+">"` → `<101>`, and
  `LEN(BIN$(65535)+BIN$(65535))` = **32**, so a full-width temp survives being
  an operand.

### 2.1 The buffer is a measured constraint, not an assumption

`LEN(BIN$(65535))` = **16**. `HEX$`/`OCT$` build their digits in `NUMBUF`, which
is **8 bytes** ([`basic/sysvars.inc:753`](../basic/sysvars.inc:753)) and holds
their worst cases (4 and 6) comfortably. **`BIN$` does not fit it.** This is the
one place `BIN$` cannot simply clone its siblings, and it was worth measuring
rather than reasoning about — a 16-digit answer is a fact, a 16-byte buffer
requirement is a consequence.

### 2.2 Errors and scope

| line | reference |
|---|---|
| `PRINT BIN$(65536)` | `Overflow` |
| `PRINT BIN$(-32769)` | `Overflow` |
| `PRINT BIN$` | `Syntax error` |
| `PRINT BIN$()` | `Syntax error` |
| `PRINT BIN$("A")` | `Type mismatch` |
| `PRINT BIN(5)` | `0` — no `$`, so no keyword: an ordinary array element |

The same five questions asked of `HEX$` give the same five answers, which is
what makes this contract a *family* rule rather than four data points.

## 3. `FRE` — two pools, and the numeric argument is a dummy

| row | reference |
|---|---|
| `FRE(0)>1000` | −1 |
| `FRE(0)<0` | 0 |
| `FRE(0)=FRE("")` | **0 — two separate pools** |
| `FRE("")=FRE("ABCDE")` | −1 |
| `A$="ABC":FRE("")=FRE(A$)` | −1 |
| `X=FRE(0):DIM A(100):FRE(0)<X` | −1 |

* **Two pools.** The numeric form reports free *variable/program* space, the
  string form the *string* pool. They are never equal, and allocating in one
  barely moves the other: a `STRING$(100,"A")` costs the string pool exactly
  **100** bytes and the numeric pool only **6** (the `A$` entry itself).
* **The string argument's content is irrelevant** — only its *type* selects the
  form. `FRE("")`, `FRE("ABCDE")` and `FRE(A$)` all agree.
* **`FRE("")` collects.** After allocating a 100-byte string and dropping it,
  `FRE("")` is back to the full pool, and two consecutive calls agree.

### 3.1 The numeric argument is a dummy — and the naive test says the opposite

`PRINT FRE(0)=FRE(1)` answers **0**. Read literally that says the argument
selects something. It does not. The two calls sit at **different evaluation
depths**, and the discriminating row settles it:

| row | reference |
|---|---|
| `FRE(0)-FRE(0)` — *same argument* | **12** |
| `FRE(0)-FRE(1)` | **12** |
| `FRE(0)-(FRE(0))` | **18** |
| `FRE(0)-((FRE(0)))` | **24** |
| `FRE("")-FRE("")` | **0** |

`FRE(0)` is **impure**: it counts down to the **stack pointer**, and every extra
expression nesting level costs exactly **6 bytes**. Since the same-argument row
already differs by the full 12, the argument was never the variable. Asked at
*equal* depth, with both variables pre-created so nothing is allocated between
the readings, every argument agrees:

| row | reference |
|---|---|
| `X=0:Y=0:X=FRE(0):Y=FRE(1):PRINT X=Y` | −1 |
| ... `Y=FRE(-1)` | −1 |
| ... `Y=FRE(255)` | −1 |

**The numeric argument is a dummy**, exactly as `POS(n)`'s turned out to be.

### 3.2 Allocation costs, measured at equal depth

With the depth term cancelled, the deltas are clean and mutually consistent:

| allocation | numeric pool |
|---|---|
| `DIM A(100)` | **816** = 101 × 8 + 8 |
| `DIM A(10)` | **96** = 11 × 8 + 8 |
| a scalar (`Q=1`) | **11** |
| `A$=STRING$(100,"A")` | **6** |

The mixed-depth versions of these same rows read 828, 108, 23 and 18 — each
inflated by the evaluator frame the measurement itself pushed. **The
measurement's own cost was masquerading as the thing measured**, which is the
T4 sprite-cadence lesson arriving in a completely different subsystem.

### 3.3 What zerobas answers today

`FRE(0)` → `0` (array element). `FRE("")` → **`type mismatch`** — a string
subscript into a numeric array. So the string form is not silently wrong today;
only the numeric form is.

### 3.4 What must NOT be gated

* **Absolute `FRE` values.** Reference at boot: `FRE(0)`=28815, `FRE("")`=200,
  `FRE(0)` after `DIM A(100)`=27999. Two memory maps; asserting one asserts they
  are identical.
* **The numeric depth rows (§3.1).** They measure the VG-8020 evaluator's
  6-byte-per-level stack frame — a ROM internal, not a language contract.
  zerobas is free to have a different frame, or to measure against a fixed
  boundary and answer 0.

Both are recorded and reported by the probe in their own section, never
asserted. The `eq-*` rows and `FRE("")-FRE("")` **are** gated: they are
depth-neutral by construction and do state real contracts.

The §3.2 deltas were a **third, open** case — they encode zerobas's *variable and
array table layout*, not `FRE` itself. **Resolved: gate them all** (spec D-BF-B).
The `layout` battery settled it with `VARPTR` before any `FRE` code existed —
scalar stride 11, string entry 6, array element 8, array header 8, **identical on
both machines, 10/10** — so the deltas assert something already true.

A **fourth** case emerged only once `FRE` ran, and it is the one-gap model's real
price: any row that separates a string's **body** from its **variable entry**
(`fre-str-num`, `fre-str-str`, `fre-gc-recov`) is a *pool-separation* row. The
reference charges the body to the string pool and the entry to the numeric pool;
with one gap both come out of the same span, so 6-and-100 there is 106 here. No
implementation of `FRE` over one gap can match those, and they joined the
recorded-not-gated set rather than being "fixed".

## 4. Errors — `FRE`

| line | reference |
|---|---|
| `PRINT FRE` | `Syntax error` — parentheses required |
| `PRINT FRE()` | `Syntax error` |
| `PRINT FRE(0,0)` | `Syntax error` |

## 5. Two divergences found on the way, neither about these two words

The calibration battery has now turned up pre-existing divergences in **three
consecutive slices** of this arc. Both of these are in `HEX$`/`OCT$` — code
already marked implemented — and **both are silent wrong answers**, the same
class this slice exists to empty.

### D-BF-1 — `HEX$`/`OCT$` accept a STRING argument and answer 0

`PRINT HEX$("A")` → reference `Type mismatch`, zerobas prints **`0`**. The
argument is `eval`'d and its *type* is never checked, so a string operand leaves
a meaningless `DE` that gets formatted as a number.

### D-BF-2 — `OCT$` has no domain check at all

`PRINT OCT$(65536)` → reference `Overflow`, zerobas prints **`0`** (65536
truncated to 16 bits is 0, so it prints `OCT$(0)`). `HEX$` *does* check —
[`basic/str-engine.asm:969`](../basic/str-engine.asm:969) runs the argument
through `fac_to_int_addr` under a repack gate — and
[`str_fn_oct`](../basic/str-engine.asm:1132) simply does not have that block.
Source and measurement agree exactly.

Both matter to this slice beyond being free finds: `BIN$` is the third member of
that family and needs precisely the check `OCT$` is missing and the type test
neither has. Fixing them is very nearly the same code.

## 6. Method notes worth keeping

* **Calibrate an absent feature against its implemented siblings.** Every
  question the spec needed answered about `BIN$` — domain, sign, float
  coercion, digit count, five error cases — was answerable on `HEX$`/`OCT$`,
  where the answers arrive with a working implementation attached and any
  disagreement is a bug already in the tree. Three slices, three times this
  battery has paid for itself.
* **A relation survives what an absolute cannot.** No gate can compare two
  machines' free memory. It can compare *whether* two readings are equal,
  *which* is larger, and *by how much* — and those carry nearly the whole
  contract.
* ⚠️ **Ask whether the natural readout straddles two evaluation depths.** The
  obvious `X=FRE(0): <allocate> :PRINT X-FRE(0)` reads its endpoints at
  different depths and folds the evaluator's frame into the answer. Every
  numeric-form row here pre-creates its variables and reads both endpoints at
  the same depth so the term cancels.
* ⚠️ **`FRE(0)-FRE(0)` is the whole argument-sensitivity question in one row.**
  A non-zero answer to a *same-argument* difference proves impurity outright, and
  no argument-sensitivity row can be trusted until that is settled. The naive
  test said "the argument matters" and was inverted by one better case — the
  cursor slice's *pick the case that can discriminate the rule*, again.
