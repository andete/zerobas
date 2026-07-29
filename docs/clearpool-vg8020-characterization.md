# The `CLEAR` string-pool partition — the VG-8020 differential (D-CLP)

Instrument: [`probes/basic/basic_probe_clearpool.py`](../probes/basic/basic_probe_clearpool.py),
boot-per-case, reference `Philips_VG_8020` against
`C-BIOS_MSX1_EU_REPACK_DISK`, measured on a clean-built `a6323b9`.
**6/51 gated rows agree, 45 diverge**, plus 2 reported-never-gated.

Opened by the `BIN$`/`FRE` slice as D-BF-A(c): zerobas has **one free gap**
where the reference has **two pools**, and `CLEAR`'s `<string-space>` argument
is evaluated and discarded ([`basic/clear.asm:61`](../basic/clear.asm:61)).

---

## 1. The apparatus

### 1.1 `FRE("")` is the one memory readout that is machine-independent

`FRE(0)` answers with free *variable* space — a property of each machine's
memory map, which is why the `BIN$`/`FRE` slice could only ever gate it as a
relation. But once the string pool is sized by `CLEAR n`, **`FRE("")` answers
with a number the user chose**, so two different machines must agree on the
nose. Absolute rows are legitimate here and nowhere else in this tree.

### 1.2 The oracle is checked against its own recorded answers first

Four rows are verbatim from
[`docs/binfre-vg8020-characterization.md`](binfre-vg8020-characterization.md) §1
(measured 2026-07-27) and are checked against the **reference column alone**
(`REPRO_EXPECT`): 500 → 500, 200 → 200, 100 → 100, and 500-minus-a-100-char
string → 400. All four reproduced. This is a statement about the oracle, not
about zerobas, and it is deliberately *not* a differential row — a control must
be something both machines are expected to pass today, and these are exactly
what zerobas is expected to fail.

### 1.3 ⚠️ The wrapped-echo fault, and the guard that now prevents it

The first run of this matrix put each case on one `:`-joined line. **Eleven rows
came back `<none>` on the REFERENCE**, and several of them were then scored
`PASS` because zerobas answered `<none>` too — agreeing on nothing.

The cause is exact and has a sharp boundary at 40 characters: both readouts are
echo-anchored, `_echo_idx` compares whole 40-column screen rows, and the echo of
a longer line **wraps onto a second row** where it can never be matched again.
Every readable row was ≤ 40 chars; every `<none>` row was longer.

Two fixes, both in the probe:

- every case is now a **list of short lines** with the `PRINT` last, so the
  readout anchors on a line that cannot wrap;
- an **apparatus guard** rejects any line ≥ `omsx_repl.COLS` *before booting an
  emulator*, so this cannot silently recur;
- and `ctl-multi` is a multi-line control whose subject allocates, so the
  readout shape most rows use is itself proven to report a value.

`basic_probe_str_domain.py`'s docstring already carried this warning. It was
read during this session and walked into anyway, which is the argument for the
guard being code rather than a comment.

---

## 2. The reference's model

### 2.1 The pool is carved out of the same RAM — the decisive rows

| row | reference |
|---|---|
| `CLEAR 200 : PRINT FRE(0)` | 28815 |
| `CLEAR 4000 : PRINT FRE(0)` | 25015 |

**Difference 3800 = 4000 − 200, exactly.** So the string pool and the variable
area share one region, split by a boundary that `CLEAR n` moves. This is what
makes the implementation a *partition* rather than a second allocator, and it is
why these two rows exist despite never being gateable (`FRE(0)`'s absolute value
is a memory-map property and the two machines differ by construction).

### 2.2 The two pools are INDEPENDENT — the core architectural claim

Equal-depth `FRE(0)` delta across a string assignment:

| row | reference | zerobas |
|---|---|---|
| `A$=STRING$(100,"A")` | **6** | 106 |
| `A$=STRING$(200,"A")` | **6** | 206 |

The reference charges the **body** to the string pool and only the 6-byte
**entry** to the variable pool; zerobas charges both to its single gap, so its
answer tracks the body length. Converse rows agree: `Q=1` and `DIM Q(50)` leave
`FRE("")` at 500 on the reference (a numeric variable never touches the string
pool) against 15856 / 15451 on zerobas.

### 2.3 `CLEAR n` sizes the pool to exactly n

`0`, `1`, `2`, `50`, `255`, `256`, `1000`, `4000` → `FRE("")` of exactly that.
`CLEAR 100.7` → **100**, so the argument truncates like every other numeric
argument.

### 2.4 The default is 200, and a bare `CLEAR` KEEPS the current size

| row | reference |
|---|---|
| boot, no `CLEAR` | 200 |
| `CLEAR` | 200 |
| `CLEAR 500 : CLEAR` | **500** |
| `CLEAR 500 : NEW` | **500** |
| `CLEAR 500 : RUN` | **500** |
| `CLEAR 500 : CLEAR ,&HD000` | **500** |

`dflt-keep` is the discriminator, and it settles a choice with two defensible
designs: a bare `CLEAR` does **not** reset the size to 200 — it keeps whatever
is set. The 200 in the first two rows is just the untouched boot default.
Neither `NEW`, `RUN`, nor the `,himem`-only form resizes the pool.

### 2.5 What is charged, and what is given back

| row | reference | reading |
|---|---|---|
| `A$="A"` | 499 | 1 byte, the body only |
| `A$=STRING$(100,"A")` then `B$=STRING$(50,"B")` | 350 | cumulative |
| `A$=STRING$(100,"A")` then `A$="B"` | **499** | the dead body IS reclaimed |
| `A$=STRING$(100,"A")` then `B$=A$` | **300** | `B$=A$` **COPIES** the body |
| `A$="ABCDE"` | 495 | a literal is copied into the pool |
| `DIM A$(2)` then `A$(1)=STRING$(100,"A")` | 400 | an array element uses the same pool |
| `X=LEN(STRING$(100,"A"))` | **500** | a pure temp is fully given back |

Two of these constrain the implementation more than they look. `B$=A$`
**copying** means the pool is charged per *reference*, not per distinct body.
And reclamation is real, not merely on collision — consistent with the
`BIN$`/`FRE` slice's finding that `FRE` compacts.

✅ **The stored-program literal is now MEASURED (2026-07-29) — it costs the
pool NOTHING.** §2.5's table was direct mode only, and the guess written here
was that a stored line's permanent tokens might let the reference point the
descriptor at the program text. It does:

| row | reference | reading |
|---|---|---|
| `A$="ABCDE"` (direct) | 495 | copied — the line buffer is transient, so it must be |
| `10 A$="ABCDE"` : `RUN` | **500** | **not copied at all** |
| `10 A$=` a 25-char literal : `RUN` | **500** | still nothing — so this is zero, not slack |

The 25-char row is the discriminator: 5 vs 0 is arguable as accounting noise,
25 vs 0 is not.

⚠️ **The finding does not land where S-CLP-4 expected.** That question was
phrased as "it changes what `heap_alloc` must do for a literal" — it does not.
Charging zero requires **storing by reference**, i.e. the same body-ownership
machinery `hold-alias` is about, so it belongs to **S-CLP-5**, which is signed
off out of D-CLP's scope. Both rows are therefore in the probe's `share`
battery: reported, never gated.

That is one difference showing up in two directions, which is why it cannot be
patched away with pool arithmetic. zerobas **owns a body per variable**
(`sh_var_store` heap-copies whatever the rvalue descriptor points at); the
reference decides ownership **per source**. So an alias charges twice there and
once here, and a stored literal charges nothing there and once here.

⚠️ Worth writing down before anyone implements it: a variable whose body points
into program text means `MID$(A$,1,1)="X"` writes into the **program**.

### 2.6 `Out of string space` is a real, distinct error

`CLEAR 100` then a 200-char, a 101-char, or two 60-char strings → **`Out of
string space`**; `CLEAR 0` then `A$="X"` likewise. Exactly 100 into a 100-byte
pool is accepted and leaves `FRE("")` at 0.

**The failed allocation is rolled back**: after `CLEAR 100 : A$=STRING$(200,"A")`
aborts, `FRE("")` still reads **100**. Nothing is partially charged.

This is ERR 14, which
[`basic/interp.asm:939`](../basic/interp.asm:939) currently lists as a **hole**
pointing at `err_unprintable` — so the slice must add the message, exactly as
`LOCATE` had to add ERR 24's.

### 2.7 `CLEAR n`'s own argument domain

| input | reference | zerobas |
|---|---|---|
| `CLEAR -1` | `Illegal function call` | *(nothing — accepted)* |
| `CLEAR 32768` / `60000` / `99999` | `Overflow` | *(nothing)* |
| `CLEAR "200"` | `Type mismatch` | *(nothing)* |

The same two-stage int16 rule the string family and `WIDTH` already implement,
plus a type check. zerobas raises **nothing** for all five — it evaluates the
argument and discards it, so a malformed one is silently accepted.

### 2.8 `,himem` does not resize the pool

`CLEAR 500,&HD000` → 500, `CLEAR 500,&H9000` → 500, `CLEAR ,&HD000` → 200
(unchanged). zerobas's `hmem-tight` answers **4091**, because its single gap is
bounded by `heap_reset`'s ceiling `C = min(HIMEM,TXTMAX)` and so shrinks when
HIMEM drops.

---

## 3. A pre-existing divergence found in passing — the sixth consecutive slice

`oos-vs-oom` exists to prove `Out of string space` is distinct from `Out of
memory`. It answered something else entirely:

| `CLEAR 100 : DIM Q(20000)` | reference | zerobas |
|---|---|---|
| | **`Subscript out of range`** | `Out of memory` |

The reference bounds a dimension **before** it tries to allocate; zerobas
allocates until it runs out. Nothing to do with the string pool — an
`ARRAYS`-arc divergence in code already marked implemented, found by a
calibration row aimed at something else. It is **not** in this slice's scope;
recorded here and in TODO.md so it is not "discovered" later by a red gate.

---

## 4. Where a fix would land, and against which walls

| piece | file | region | free |
|---|---|---|---|
| record `CLEAR`'s size argument + its domain check | [`basic/clear.asm`](../basic/clear.asm) | main page 1 | **3 B** ⚠️ |
| `heap_reset` — derive the pool base from the size | [`basic/str-engine.asm`](../basic/str-engine.asm) | main low region | 30 B |
| `heap_alloc` floor, `sh_free_gap` | [`sub/strheap.asm`](../sub/strheap.asm) | **sub-ROM** | ~3.4 KB |
| array-allocation ceiling | [`sub/arrays.asm`](../sub/arrays.asm) | **sub-ROM** | ~3.4 KB |
| ERR 14 message + table entry | [`basic/interp.asm`](../basic/interp.asm) | main page 1 | **3 B** ⚠️ |

**Most of the work is sub-ROM tenant code**, which is not wall-bound. The
binding constraint is the handful of bytes in main page 1 — and `a6323b9` left
that at 3 B free, so this slice must open with a carve.

The shape the measurements point to is a single moving boundary rather than a
second allocator, because §2.1 shows the pool is carved from the same region:

- a new 2-byte RAM cell `POOLBASE`; `CLEAR n` records n, `heap_reset` sets
  `POOLBASE := C − n` (`C = min(HIMEM,TXTMAX)`, already computed there);
- `heap_alloc`'s collision test changes floor from `ARYEND+2` to `POOLBASE`,
  and its failure becomes ERR 14 rather than ERR 7;
- `sh_free_gap` (i.e. `FRE("")`) becomes `FRETOP − POOLBASE`;
- the array/variable allocator's ceiling changes from `FRETOP` to `POOLBASE`,
  and *its* failure stays ERR 7.

That also explains §2.8 for free: `,himem` moves `C`, and `POOLBASE` is
re-derived from `C` and the recorded size, so the pool keeps its size.
