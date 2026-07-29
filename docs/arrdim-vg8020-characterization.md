<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-ARR-B — where the reference bounds a dimension (VG-8020 characterization)

**Measured 2026-07-29** on the stock `Philips_VG_8020` (real MSX-BASIC 1.0) via the
KEYBUF REPL driver, boot-per-case, against
`C-BIOS_MSX1_EU_REPACK_DISK` at `75e9628`. Probe
[`probes/basic/basic_probe_arrdim.py`](../probes/basic/basic_probe_arrdim.py),
`make arrdim-characterize`. Observed outputs only — no ROM disassembly
([`PROVENANCE.md`](../PROVENANCE.md)).

**Baseline: 27/46 gated rows agree, 3 reported-never-gated.** All **19** divergent
gated rows are one root cause — and D-ARR-B closed every one of them (`47/47 ALL
PASS`, 8 never-gated, once the `cap` battery below was added).

---

## 0. Why this was measured at all

`CLEAR 100 : DIM Q(20000)` answers **`Subscript out of range`** on the reference
and **`Out of memory`** here. That was found on 2026-07-29 as the `oos-vs-oom`
calibration row of the D-CLP matrix — a row aimed at proving `Out of string space`
was distinct from `Out of memory`, which instead answered a question nobody had
asked. It was split out and kept in that probe as `oos-dim-huge`, reported and
never gated, specifically so it could not be "discovered" later by a red gate
([`clearpool-vg8020-characterization.md`](clearpool-vg8020-characterization.md) §3).

⚠️ **The arrays arc asked this question and never answered it.**
[`spec-basic-arrays.md`](spec-basic-arrays.md) §4 lists ten characterization
targets. Nine of them have a row in the §4.1 results table. Target **#9 — "`Out of
memory` onset — the raise point when an array would overflow the ceiling"** — does
not. The divergence lived for a year in the hole that left. A target list is not
a measurement, and the difference is invisible unless someone diffs the questions
against the answers.

---

## 1. The rule

> **`elsize × Π(boundₖ + 1) > $FFFF` ⇒ `Subscript out of range`, raised before
> any allocation is attempted.**

Everything below is that one sentence, measured from four independent directions.

### 1.1 The bound moves with the ELEMENT SIZE — so it is a byte count

The discriminator battery. Each row is far past the free variable space on both
machines, so a machine with no dimension bound answers `Out of memory` throughout;
the flip is the finding.

| type | elsize | last `Out of memory` | first `Subscript out of range` | data bytes at the flip |
|---|---|---|---|---|
| `Q%` | 2 | `Q%(32766)` — 65534 B | `Q%(32767)` | 32768 × 2 = **65536** |
| `Q!` | 4 | `Q!(16382)` — 65532 B | `Q!(16383)` | 16384 × 4 = **65536** |
| `Q#` | 8 | `Q#(8190)` — 65528 B | `Q#(8191)` | 8192 × 8 = **65536** |
| `Q$` | 3 | `Q$(21844)` — 65535 B | `Q$(21845)` | 21846 × 3 = **65538** |
| `Q` (unsuffixed) | 8 | `Q(8190)` | `Q(8191)` | confirms **unsuffixed = double** |

This kills the two rival rules outright. A fixed subscript ceiling (`n > K`) or an
element-count overflow (`Π(boundₖ+1) > $FFFF`) both predict **the same n for all
four types**; the measured breaks differ by exactly the factor of the element
width. `Q%(32767)` is the sharpest single row: its element count is 32768, which
fits a 16-bit word comfortably, and it still raises — so the quantity under test
is bytes, not elements.

### 1.2 The header is NOT counted

`Q%(32766)` is 32767 × 2 = **65534** data bytes and answers `Out of memory`.
`Q!(16382)` is 65532 and answers `Out of memory`. An array descriptor cannot be
smaller than its name + type + dimension count + one bound word, so if the check
included the header either of these would have crossed `$FFFF` and raised. It is
the **element data alone**.

### 1.3 The test is `>` and not `>=`

`Q$(21844)` = 21845 × 3 = **`$FFFF` exactly** → `Out of memory`, i.e. accepted by
the bound and rejected by the allocator. `Q$(21845)` = 65538 → `Subscript out of
range`.

⚠️ **Only a string array can settle this.** The numeric widths are 2/4/8, all of
which divide `$10000`, so their products step straight from 65534/65532/65528 to
65536 and never land on `$FFFF`. The 3-byte element is the only one in the
language that can sit on the boundary — which is also what pins `elsize($) = 3`,
since a 2-byte string element would have put both of these rows far under the
limit and answered `Out of memory` twice.

### 1.4 It is the PRODUCT, and position-independent

| case | dims | elements | data bytes | reference |
|---|---|---|---|---|
| `DIM Q%(150,150)` | 151 × 151 | 22801 | 45602 | **`Out of memory`** |
| `DIM Q%(200,200)` | 201 × 201 | 40401 | 80802 | **`Subscript out of range`** |
| `DIM Q%(32767,0)` | 32768 × 1 | 32768 | 65536 | **`Subscript out of range`** |
| `DIM Q%(0,32767)` | 1 × 32768 | 32768 | 65536 | **`Subscript out of range`** |
| `DIM Q%(40,40,40)` | 41³ | 68921 | 137842 | **`Subscript out of range`** |

`Q%(200,200)` is the one that matters: **not one dimension is anywhere near a
ceiling** — 200 is an ordinary subscript — and it still raises. A per-dimension
rule cannot produce this. `Q%(150,150)` is the battery's own control: the product
fits 16 bits *and* exceeds both machines' free RAM, so it must fall through to
`Out of memory`, and does. `(32767,0)` vs `(0,32767)` shows the check is not
looking only at the first bound.

### 1.5 It is a property of the ALLOCATOR, not of `DIM`

| case | elements | data bytes | reference |
|---|---|---|---|
| `Q(1,1,1,1)=1` | 11⁴ = 14641 (auto-dim) | 117128 | **`Subscript out of range`** |
| `Q%(1,1,1,1)=1` | 11⁴ = 14641 (auto-dim) | 29282 | **`Out of memory`** |

First touch of an undeclared array **auto-dims every dimension to 10** (§4.1 #1),
so four subscripts of a *double* array ask for 117128 bytes with no large number
anywhere in the source line — and the reference raises the bound error. The `%`
row is the control: same shape, 29282 bytes, under `$FFFF` and over both machines'
free RAM, so it must be `Out of memory`, and is.

⚠️ **This decides where the fix goes.** Had the bound been a property of `DIM`'s
argument parser, a check in `ex_dim` would have satisfied every other row in this
document and left this one silently wrong — a whole second entry into the
allocator, reachable without the word `DIM` appearing at all.

---

## 2. What the bound does NOT reach

### 2.1 The argument's own domain beats it

| case | reference |
|---|---|
| `DIM Q(32768)` | **`Overflow`** |
| `DIM Q(65535)` | **`Overflow`** |
| `DIM Q(99999)` | **`Overflow`** |
| `DIM Q(-1)` | **`Illegal function call`** |
| `DIM Q(20000.7)` | **`Subscript out of range`** |

A subscript past int16 cannot be represented, so the coercion fails first and the
bound never runs. A negative one is `Illegal function call` — the same disposition
the arc already pinned for a negative *subscript* ([`spec-basic-arrays.md`](spec-basic-arrays.md)
§4.1 #9). A fractional bound is truncated/rounded into range and then bounded
normally, so the coercion runs **before** the bound in both directions.

### 2.2 The redim check beats it

`DIM Q(3) : DIM Q(20000)` → **`Redimensioned array`** on both machines. The
identity check fires before the size is looked at, so a re-declaration is reported
as one whatever its bounds say. zerobas already agrees.

### 2.3 It beats the deferred syntax error

`DIM Q(20000),` → **`Subscript out of range`** (not `Syntax error`) — the same
ordering `MID$(A$,0,)` settled in D-MISS-2 and `WIDTH 41,` in D-WID: the
domain/size error wins over a syntax error that is only discovered later in the
line.

---

## 3. What survives a failed `DIM` — both machines already agree

| case | reference | zerobas | meaning |
|---|---|---|---|
| `DIM Q(20000)` : `DIM Q(3)` | *(no error)* | *(no error)* | the failed DIM left **nothing** behind |
| `DIM Q(20000)` : `Q(11)=1` | `Subscript out of range` | `Subscript out of range` | Q is undefined, so it **auto-dims to 10** and 11 is out of range |
| `DIM P(2),Q(20000)` : `DIM P(2)` | `Redimensioned array` | `Redimensioned array` | **P survives its sibling's failure** — `DIM` commits per item, not per statement |

So the rollback contract is unchanged by this slice: the failing item writes
nothing, and earlier items in the same `DIM` list stay. Both machines do this
today; the rows are here because a fix that reordered the check could break it
silently.

⚠️ **Two of these three rows started out agreeing for the wrong reason**, and
would have shipped as green rows measuring nothing:

- `DIM P(2),Q(20000)` : `PRINT P(0)` → ` 0 ` on both. But an array that was
  **never created auto-dims to 10 on first touch and reads 0 too**, so the row
  passed whether P survived or not.
- `DIM Q(20000)` : `PRINT Q(10)` → ` 0 ` on both, identically hollow.

The fix in both cases is a readout the auto-dim cannot forge: re-`DIM` it (only a
live array answers `Redimensioned array`), or touch subscript **11**, which is out
of range for an auto-dimmed 0..10 array and in range for the 0..20000 one that was
asked for. This is the [[kwsweep-msx1-denominator]] failure mode — `PRINT
TAB(99999)` matching on both sides while `TAB(` did not exist — reproduced twice
inside one battery.

---

## 4. What zerobas does today, and why the fix is small

zerobas **already computes the exact quantity the rule needs**, in two steps, and
already detects both overflows:

- [`sub/arrays.asm`](../sub/arrays.asm) `ary_count_elems` multiplies the
  `boundₖ+1` terms with `ary_mul16_checked` and returns `CF` on overflow;
- `ary_alloc` then multiplies that count by `elsize_from_type` with the same
  checked multiply, again returning `CF`.

Both carry paths `jp c,aal_oom`, which sets `ARY_ERR=4` → `FPERR=6` → `Out of
memory`. **The measured rule is that those two paths — and only those two — are
`Subscript out of range`.** The set is identical: a byte product overflows exactly
when the element product overflows or the `elsize ×` step does.

The other three carry checks in `ary_alloc` (`tail + header`, `+ data bytes`, and
the `+2` terminator reservation) are **address-space wraps**, not size-rule
violations. Any case reaching them has a byte count ≤ `$FFFF`, which the reference
accepts and then fails on its own ceiling — so they must stay `Out of memory`.

---

## 4a. 🔴 What the calibration found while measuring something else

**The seventh consecutive slice** whose calibration battery turns up a live defect
nobody was looking for. Two of them here, and neither is in this slice's scope.

### 4a.1 `MAXDIM = 4` is a divergence, not a cap — D-ARR-C

| case | reference | zerobas |
|---|---|---|
| `DIM Q%(1,1,1,1,1)` | *(accepted, no error)* | **`Subscript out of range`** |
| `DIM Q%(1,1,1,1,1,1,1,1)` | *(accepted)* | `Subscript out of range` |
| `DIM Q%(0,0,0,0,0,0,0,0,0,0,0,0)` | *(accepted)* | `Subscript out of range` |

Every one of these is tiny — 32, 256 and 1 element — so nothing here is about
size. **The reference accepts at least twelve dimensions**, which is where the
echo-anchored form runs out: a `DIM` line with more subscripts is past the 37-char
limit of §4a.2.

**And there is no cap at all.** Once folding D-ARR-C in made the number something
that had to be *chosen* rather than bracketed, the `cap` battery measured it
properly — the long `DIM` moves into a **stored program line** (never anchored on),
`ON ERROR` catches whatever it raises, and the anchor becomes a short direct
`PRINT` of the trapped code:

| subscripts | 4 | 8 | 16 | 32 | 64 | 100 |
|---|---|---|---|---|---|---|
| reference `ERR` | 0 | 0 | 0 | 0 | 0 | 0 |
| zerobas `ERR` | 0 | **9** | **9** | **9** | **9** | **9** |

**The reference takes a hundred dimensions.** Past that it is the 254-character
input line that stops the probe, not the language. `cap-4` is the battery's
two-sided control: four subscripts are legal on both machines, and a run where
even that reads 9 is measuring the apparatus.

⚠️ **The readout had to move off the subject to measure this**, which is the
generalisable part: an echo-anchored readout cannot measure a statement longer
than the echo. Anchoring on a *later, shorter* line — with the subject stored and
its error trapped — buys the whole 254-character input line. Compare
[[missing-class-slice]] (a statement that MOVES THE CURSOR) and
[[width-domain-slice]] (one that MOVES THE INSTRUMENT); this is the third shape:
a statement **too long for the instrument**.
[`basic/sysvars.inc:1544`](../basic/sysvars.inc:1544) caps subscripts at
`MAXDIM = 4` and [`spec-basic-arrays.md`](spec-basic-arrays.md) §9.1 Q-9b records
that as a "slice-1 subscript-count cap" with the disposition `>MAXDIM subscripts
→ Subscript out of range`. That disposition was **chosen, written down, and never
measured against the reference**, in the same arc whose §4 target #9 was asked and
never answered.

It is out of D-ARR-B's scope: raising the cap costs RAM in the `ARY_IDX` subscript
block and widens every array descriptor, and it has nothing to do with the
byte-count rule. It is carried as **D-ARR-C**, reported-never-gated in the probe
with its reason on the row, exactly as D-CLP carried `oos-dim-huge` — the record,
not a silencing. ⚠️ Note the two interact: at twelve dimensions the auto-dim
product is 11¹² , so a raised cap makes §1.5's overflow reachable far more easily.

### 4a.2 The wrapped-echo guard was three characters too loose

D-CLP's apparatus guard — the one written *because* eleven rows had read `<none>`
on the reference — tested each line against `omsx_repl.COLS`, the **40-column
screen width**. A line does not wrap at the screen width; it wraps at **`LINLEN`**,
and D-WID had already measured that **the two machines do not boot at the same
one: reference 37, zerobas 39**
([`width-vg8020-characterization.md`](width-vg8020-characterization.md)).

This matrix hit it for real. A 39-character row (`DIM Q%(0,0,…)`, sixteen
dimensions) passed the guard, then came back `<no echo>` on **both** machines and
scored **PASS** — agreeing on nothing, the precise failure the guard exists to
prevent, three characters inside its own limit. Both probes now guard at
`ECHO_MAX = 37`, the tighter of the two boot widths, and the row is twelve
dimensions instead of sixteen. No D-CLP measurement changes (its longest line is
35), but its guard was not checking what it claimed to check.

**The lesson generalises past this probe:** a guard written from the *screen's*
dimension when the *machine's* setting is what governs is a guard that passes
everything it was built to catch. The number a guard uses has to be measured on
the same machine as the thing it guards.

---

## 5. The matrix

55 rows, nine batteries, boot-per-case. `ctl` 6, `repro` 2, `bnd` 9, `typ` 11,
`dim` 10, `dom` 6, `ord` 3, `post` 2, `cap` 6 — of which **47 are gated and 8 are
the D-ARR-C record** (`dim-5dim`/`-8dim`/`-12dim` + `cap-8`…`cap-100`), each row
printing its own reason. `cap-4` stays gated as that battery's control.

**Baseline 27/46 gated** before the `cap` battery existed; **47/47 ALL PASS**
after D-ARR-B landed.

- **`ctl` (6/6)** — two-sided apparatus rows, all green: a value read, an
  out-of-bounds subscript, a negative subscript, a re-`DIM`, plus a multi-line
  value row and a multi-line *error* row (the anti-`<none>` pair, which prove both
  readout shapes report something after a preceding statement has run).
- **`repro` (1/2)** — the reference's own recorded answers from
  [`clearpool-vg8020-characterization.md`](clearpool-vg8020-characterization.md)
  §3, asserted against the **reference column alone** before any verdict is read
  as a finding. `repro-oom` (`DIM Q(5000)` → `Out of memory`) is also a zerobas
  PASS; `repro-soor` is the divergence itself. [[validate-oracle-artifacts]]
- **The 19 divergent rows** are `repro-soor`, `bnd-8191`/`-8192`/`-10000`/
  `-16384`/`-20000`/`-32767`, `typ-i-32767`, `typ-s-16383`, `typ-d-8191`,
  `typ-str-32767`, `typ-str-21845`, `dim-200x200`/`-huge1st`/`-huge2nd`/`-3d`/
  `auto-4d`, `dom-frac`, `ord-syntax` — every one of them "reference says
  `Subscript out of range`, zerobas says `Out of memory`", and every one of them a
  case whose byte product exceeds `$FFFF`. **One root cause, nineteen rows, and
  the nineteenth (`auto-4d`) reaches it without the word `DIM`.**

⚠️ **No row measures a THRESHOLD.** The two machines have different memory maps by
construction (~28.8 KB free variable space on the reference, ~15.7 KB here) and
always will, so the point at which RAM runs out can never be made to agree. Every
`bnd`/`typ`/`dim` row is sized past **both** machines' free space; the only thing
under measurement is which error the machine picks. `dim-150x150` is the explicit
control for that sizing discipline.

---

Related: [[clearpool-slice]], [[arrays-dim-arc]], [[kwsweep-msx1-denominator]],
[[answer-signoff-questions-by-measuring]].
