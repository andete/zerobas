<!-- Copyright (c) 2026 Joost Yervante Damad -- SPDX-License-Identifier: 0BSD -->

# D-ARYOOS — a string ARRAY-ELEMENT store that will not fit says `Out of string space`

Measured 2026-08-20 on **three sides**: Philips VG-8020, National CF-3300, zerobas
(`C-BIOS_MSX1_EU_REPACK_DISK`). Closes the `TODO.md` residual *“`ex_let_arr_str`
SWALLOWS AN OUT-OF-STRING-SPACE AND THE PROGRAM RUNS ON”*, filed 2026-08-08.

Apparatus: [`probes/basic/basic_probe_clearpool.py`](../probes/basic/basic_probe_clearpool.py)
(`make clearpool-acceptance`, the `oos` and `arychg` batteries), plus a
three-sided stored-program re-measurement of the residual's own rows in the
residual's own mode.

---

## 1. The headline: HALF THE FILED DEFECT WAS ALREADY CLOSED, BY A SLICE THAT NEVER CLAIMED IT

The item said the store **swallows** the error and **the program runs on**. It
does not, and has not since `3dc1e7b`:

| row | program | vg8020 | cf3300 | zerobas **before** this slice |
|---|---|---|---|---|
| `s.aryoom` | `CLEAR 60` / `DIM A$(5)` / `B$=STRING$(25,"A")` / `A$(1)=B$` / `A$(2)=B$` / `PRINT"[OK]"` | `Out of string space in 50` | idem | **`Out of memory in 50`** |

It errors, it errors **on the right line**, and `[OK]` is never printed. What
was left of the two-part defect was the **message**, and nothing else.

🔴 **THE SWEEP THAT RE-READ THE ITEM LIVE IS THE COMMIT IMMEDIATELY BEFORE THE
ONE THAT FIXED IT.** `docs/todo-staleness-sweep-2026-08.md` §4.7 read `OK` on
zerobas and wrote **“LIVE, exactly as filed”** — correctly, at `14dc44d`.
D-STMTPEND landed at `3dc1e7b`, the very next commit, on the same day. Its own
header describes this class in as many words — *“a fault raised by a driver that
never calls `check_expr_errors` got silently discarded”* — and
`ex_let_arr_str` is exactly such a driver: it ends `jp exec_stmt`, and
`exec_stmt` now **reads** the pending cell instead of clearing it. Nobody
re-ran §4.7, so the item carried a false headline for eleven days.

🎯 **THE ITEM'S OWN TRAP PARAGRAPH IS WHAT SURVIVED, AND IT WAS RIGHT.** It
predicted that adding the missing check would raise `ARY_ERR=4` →
(`ary_errmap`) → `FPERR=6` → **ERR 7 `Out of memory`**, where both references
say **`Out of string space`** (ERR 14) — *“a wrong message, green on any gate
that only asks did-it-error”*. That is precisely the state D-STMTPEND left
behind, reached without anyone adding a check.

---

## 2. The rule

> A string array-element store that cannot get a **body** out of the `CLEAR n`
> pool is **`Out of string space`** (ERR 14) — the same error the scalar store
> already gives. An **allocation** that will not fit **variable space** —
> including a *string* array's own `[len][ptr]` slots — stays **`Out of
> memory`** (ERR 7).

### 2.1 The measured rows (stored programs, three sides)

| row | program (`:`-joined) | vg8020 | cf3300 | zb **before** | zb **after** |
|---|---|---|---|---|---|
| `s.ctl` 🟢 | `CLEAR 200:DIM A$(5):B$=STRING$(25,"A"):A$(1)=B$:PRINT"[";LEN(A$(1));"]"` | `[ 25 ]` | `[ 25 ]` | `[ 25 ]` | `[ 25 ]` |
| `s.aryoom` | `CLEAR 60:DIM A$(5):B$=STRING$(25,"A"):A$(1)=B$:A$(2)=B$:PRINT"[OK]"` | `Out of string space in 50` | idem | **`Out of memory in 50`** | `Out of string space in 50` ✅ |
| `s.autoary` | as above with **no `DIM`** (auto-dim) | `Out of string space in 40` | idem | **`Out of memory in 40`** | `Out of string space in 40` ✅ |
| `s.scalar` 🟢 | `CLEAR 60:B$=STRING$(25,"A"):C$=B$:D$=B$:PRINT"[OK]"` | `Out of string space in 40` | idem | `Out of string space in 40` | idem |
| `s.strdim` 🎯 | `CLEAR 100:DIM A$(20000):PRINT"[OK]"` | `Out of memory in 20` | idem | `Out of memory in 20` | idem |
| `s.inpary` | `CLEAR 60:DIM A$(5):B$=STRING$(25,"A"):A$(1)=B$:INPUT A$(2):PRINT"[OK]"`, response `AAAA…` (25) | `Out of string space in 50` | idem | *(unmeasured)* | `Out of string space in 50` ✅ |
| `s.inpscal` 🟢 | `CLEAR 60:B$=STRING$(25,"A"):C$=B$:INPUT D$:PRINT"[OK]"`, same response | `Out of string space in 40` | idem | *(unmeasured)* | `Out of string space in 40` |
| `s.readary` 🔴 | as `s.inpary` but `DATA AAAA…` + `READ A$(2)` | **`[OK]`** | **`[OK]`** | *(unmeasured)* | `Out of string space in 60` |
| `s.readscal` 🔴 | as above, `READ D$` into a **scalar** | **`[OK]`** | **`[OK]`** | *(unmeasured)* | `Out of string space in 50` |

### 2.2 🎯 `s.strdim` IS THE DENOMINATOR, AND IT RULES OUT THE CHEAP SPLIT

The item named the root correctly — `ARY_ERR=4` is a **conflation**, serving
both the array allocation OOM and `aeng_copy_str`'s string-heap OOM — and then
warned that the `DIM` half was **unmeasured**, assumed ERR 7 from the language
reference. It is measured now, and the row that matters is not the numeric
`DIM` the item had in mind.

`CLEAR 100 : DIM A$(20000)` is a **string** array. Its 20001 slots are
3 bytes each = 60003 bytes: under `$FFFF`, so D-ARR-B's size rule does not fire
(that would be `Subscript out of range`), and over the free *variable* space of
both machines (28815 ref / 15667 zb), so both allocate-and-fail. All three
machines answer **`Out of memory`**.

So a split keyed on *the array's type* — “string array → string space” — is
**refuted by measurement**. The split is by **which allocator failed**:

| site | what ran out | code | message |
|---|---|---|---|
| `ary_alloc` → `aal_oom` (`DIM`, auto-dim) | variable space | `ARY_ERR=4` | `Out of memory` |
| `scv_alloc` → `scv_oom` (scalar insert) | variable space | `ARY_ERR=4` | `Out of memory` |
| `aeng_copy_str` → `acs_oom` (the store) | the `CLEAR n` pool | **`ARY_ERR=5`** | **`Out of string space`** |

The numeric twins already stood in the gate and still pass: `oos-vs-oom`
(`CLEAR 100:DIM Q(5000)` → `Out of memory`) and `oos-dim-huge`
(`CLEAR 100:DIM Q(20000)` → `Subscript out of range`, D-ARR-B's size rule).

### 2.3 🔴 THE ROW WRITTEN TO TEST THE SECOND SITE REFUTED ITSELF

`basic/vars.asm`'s `tss_ary` is the *other* array-element string store — the
tail shared by **READ / INPUT / LINE INPUT / INPUT#n / LINE INPUT#n**. Unlike
`ex_let_arr_str` it already tested `ary_engine_call`'s NZ, so it always
reported; only its message was wrong, and the same one-code split fixes it.

> 🔴 **THIS SENTENCE SAID "the FIELD read" UNTIL 2026-08-21, AND THERE IS NO
> FIELD CALLER** (D-BLNF's sibling slice D-ARYSITE, §6). `basic/field.asm`
> reaches `tgt_parse_fld` → `tgt_parse` and **never** `tgt_store_str`: FIELD
> *binds* a descriptor into the record buffer, runs no `heap_alloc`, and so
> cannot reach the OOM this rule is about. `basic/vars.asm`'s own *"these FIVE
> store paths"* is right when it counts **verbs** — READ, INPUT, LINE INPUT,
> `INPUT#n`, `LINE INPUT#n`, the last two sharing one site — and this line
> turned the fifth verb into a fifth site and named the wrong one. The
> denominator is **four call sites**, by grep over `basic/` and `sub/`.

`READ` was chosen to measure it, being the only one of the five a stored
program reaches unattended. **Both references answered `[OK]`** — no error at
all. A stored `DATA` literal's descriptor points **at the program text** on the
reference and charges the pool nothing (the same finding `hold-lit-prog`
records in the `share` battery), so the store never allocates. The scalar twin
`s.readscal` diverges in exactly the same way, which is what proves it is the
S-CLP-5 **body-ownership** question — signed off out of scope — and not this
rule. `INPUT` takes its bytes from a transient line buffer, so the reference
must copy; `s.inpary` / `s.inpscal` are the valid rows, and all three sides
agree after the fix.

### 2.4 The pool arithmetic (`arychg`, now gated)

| row | program | vg8020 | zb |
|---|---|---|---|
| `arychg-dimonly` | `CLEAR 200:DIM A$(5):PRINT FRE("")` | ` 200 ` | ` 200 ` |
| `arychg-scalar` | `CLEAR 200:B$=STRING$(25,"A"):…` | ` 175 ` | ` 175 ` |
| `arychg-store1` | `… :A$(1)=B$:…` | ` 150 ` | ` 150 ` |
| `arychg-store2` | `… :A$(2)=B$:…` | ` 125 ` | ` 125 ` |

`arychg-dimonly` is the arithmetic behind §2.2: a `DIM A$(n)` charges the pool
**nothing**. The other three exist to **size** the error rows — an
echo-anchored tail can only read the *last* line, so each error row is built so
that the last line is the store that cannot fit, on both machines.

🔴 **THREE OF THESE FOUR PREDICTIONS WERE WRONG, ALL IN THE SAME DIRECTION.**
They were predicted at 150 / 125 / 100 on the reference and written into a
never-gated battery, on the strength of the `share` battery's *“an alias
charges twice there”*. That sentence is about `B$=A$`; it does **not**
generalise to a store out of a temp, and the reference adopts a temp's body
exactly as zerobas does. All four agree to the byte, so all four are now
**gated** — a battery declared unmeasurable turned out to be the cleanest
agreement in the slice.

---

## 3. The fix — 1 byte

| change | file | region | bytes |
|---|---|---|---|
| `acs_oom`: `ld a,4` → `ld a,5` | [`sub/arrays.asm`](../sub/arrays.asm) | sub page 0 | **0** |
| `ary_errmap`: 5th entry `db FPERR_STROOM` | [`basic/arrays.asm`](../basic/arrays.asm) | main **low** | **1** |

`FPERR_STROOM` is the *symbol*, not a literal 11: with `CLEARPOOL` off it is 6,
and the entry collapses back onto the pre-partition `Out of memory` exactly as
the five `str-engine.asm` sites do.

**No check was added to `ex_let_arr_str`, and none is needed** — `exec_stmt`
raises the pending code at the statement boundary, which is why the store
reports on its own line. What the site did need was a **comment repair**: it
said `-> always Z (op=3 cannot fail)`, false since slice 4a made the copy
heap-allocate. Two more prose sites said the same thing and are corrected —
`sub/arrays.asm`'s tenant header (*“COPY_STR always writes 0 — it cannot
fail”*) and `aeng_copy_str`'s own (*“so NO main-ROM change was needed”*: true
about **surfacing**, false about the **message**).

Walls, `make basic-reloc`, 2026-08-20: low **23 → 22 B**, main page 1 **22 B**
unchanged, sub page 0 **3299 B** unchanged, sub page 1 **1631 B** unchanged.
The whole cost is the one low-region table byte, as priced.

---

## 4. Knives

Every knife's discriminator is the **message**. A row scored error-vs-no-error
agrees on both sides under the wrong fix — which is the whole reason this
residual sat open for twelve days with the defect already half-fixed. Run
against `make clearpool-acceptance ONLY=oos` (14 rows) unless noted.

| knife | cut | predicted red | measured |
|---|---|---|---|
| K-AO1 | `acs_oom`'s `ld a,5` → `ld a,4` (restore the conflation) | `oos-arystore`, `oos-autostore` — **2** | **EXACT**, 12/14 |
| K-AO2 | `ary_errmap` entry 5 `FPERR_STROOM` → `6` | the same **2** | **EXACT**, 12/14 |
| K-AO3 | `ary_errmap` entry **4** `6` → `FPERR_STROOM` (split by type, not site) | `oos-vs-oom`, `oos-strdim-oom` — **2**, `oos-dim-huge` stays green | **EXACT**, 12/14 |
| K-AO4 | `exec_stmt`'s `or a` → `xor a` (restore the swallow) | `oos-arystore`, `oos-autostore`, `oos-arycont` — **3** | **EXACT**, 11/14 |
| K-AO5 | `aeng_copy_str`'s **second** `ld a,(hl)` → `ld a,l` (write a wrong dest length) | `oos-arystore-ctl` alone — **1** | 🔴 **MISS** — **4** red, 10/14 |

Baseline 14/14; ROM ids `05902dc7` (main) / `5553fa61` (sub), and the restored
tree rebuilds to both, which is the guard that no knife outlived its run. Each
knife names which ROM it moved: K-AO1 and K-AO5 move `sub.rom` only, K-AO2–4
`zerobas-main-eu.rom` only, exactly as their file placement predicts.

🔴 **K-AO5 MISSED, AND THE MISS IS A FINDING.** It was predicted to redden the
green control alone: the wrong length is written *after* `heap_alloc` has
already taken the right number of bytes, so the pool arithmetic looked
untouched. It reddened four rows, and the readings say why —
`LEN(A$(1))` comes back ` 6 `, and then `A$(2)=B$` **succeeds** (`oos-arystore`
reads `''`, `oos-arycont` prints `OK`). A descriptor claiming 6 bytes where 25
were allocated is a **GC root that disowns 19 live bytes**: the collector
reclaims them and the pool that should be exhausted has room again. 🎯 **A
LENGTH FIELD WRITTEN WRONG IS NOT A READ-SIDE DEFECT.** The prediction reasoned
about the allocator and forgot that the stored length is a live input to
everything downstream of it. The knife still did its job — the control is not
blind — but the blast-radius model was wrong.

K-AO1 is the whole argument in one cut: the two new rows redden and every old
`oos` row stays green, which is the measurement that the pre-existing battery
**could not separate the two rules**. K-AO3 is its mirror — it proves
`s.strdim` / `oos-strdim-oom` has teeth, so the by-site split is pinned in both
directions. K-AO5 proves the green control can go red.

Every cut is a **value**, never a call: deleting the only call to a routine
fails `make deadcode` and builds no ROM.

---

## 6. D-ARYSITE — the three callers "by construction" was standing in for, 2026-08-21

§2.3 measured **one** of `tss_ary`'s call sites (console `INPUT`) and found
`READ` to be no test at all. The rest were said to be reached *by construction*.
That is a claim, not a reading, and D-CIRCOVF is the standing reminder that a
bound stated by construction is owned by whoever deletes the construction. Five
rows now measure it. **Zero ROM bytes** — this slice is measurement and a
denominator correction.

### 6.1 🔴 The denominator was wrong, and the grep was the whole finding

`tgt_store_str` has **four** call sites, by grep over `basic/` and `sub/`:

| site | verb(s) | status |
|---|---|---|
| `basic/program.asm:1908` | `READ` | measured §2.3 — **no test** (both refs `[OK]`) |
| `basic/input.asm:138` | console `INPUT` | measured §2.1 (`s.inpary`) |
| `basic/input.asm:224` | console `LINE INPUT` | **new**: `i.oosline` |
| `basic/files.asm:781` | `INPUT#n` **and** `LINE INPUT#n`, disk **and** `CAS:` | **new**: `i.oosfile`, `i.oosfline` |

**There is no FIELD caller.** `basic/field.asm` reaches `tgt_parse_fld` →
`tgt_parse` and never `tgt_store_str`; FIELD *binds* a descriptor into the record
buffer and runs no `heap_alloc`, so the pool OOM this rule is about cannot happen
there. §2.3's *"the FIELD read"* turned the fifth **verb** into a fifth **site**
and named the wrong one; `basic/vars.asm`'s own *"these FIVE store paths"* is
right about verbs. 🎯 **Half the filed cost of this item was a fixture — `FIELD` +
`GET` — for a caller that does not exist.**

### 6.2 The rows, and why they need no disk write

`CLEAR 60` + a 25-char `B$` + a 25-char `A$(1)` leaves **ten** bytes of pool
(§2.4's measured arithmetic). `HI.TXT` on `disk/test720.dsk` is
`Hello from zerobas-disk!` + CRLF — a **24-character** line, over that headroom
and under the 25 the console rows type. So every file row reads an existing file
and **no row writes to the image**: no private copy, and nothing to perturb a
neighbour on `--repeat 2`.

| row | vg8020 | cf3300 | zb |
|---|---|---|---|
| `i.oosline` — `LINE INPUT A$(2)` | `Out of string space` | idem | idem |
| `i.ooslinescal` — the SCALAR twin | `Out of string space` | idem | idem |
| `i.oosfile` — `INPUT#1,A$(2)` | *(no disk)* | `Out of string space` | idem |
| `i.oosfilescal` — the SCALAR twin | *(no disk)* | `Out of string space` | idem |
| `i.oosfline` — `LINE INPUT#1,A$(2)` | *(no disk)* | `Out of string space` | idem |
| `i.ooslinefit` 🟢 — `CLEAR 200` | ` 25 ` | ` 25 ` | ` 25 ` |
| `i.oosfilefit` 🟢 — `CLEAR 200` | *(no disk)* | ` 24 ` | ` 24 ` |

`make inputary-acceptance` **7/7 → 14/14**, the seven shipped rows unchanged —
which is the check growing this probe's `ERRORS` tuple demands, because adding a
name to a classifier can change a shipped row's reading (the D-FNARG2 trap). The
two 🟢 fit controls exist because every other new row expects an **error**, and a
machine that cannot read a line at all produces one for free.

### 6.3 Knives — 3 of 3 EXACT

Baseline 14/14. Every discriminator is the **message**; every cut is a VALUE.

| knife | cut | predicted red | measured |
|---|---|---|---|
| K-AS1 | `acs_oom`'s `ld a,5` → `ld a,4` (un-split the code) | the **3 array rows** → `Out of memory`, **both scalar twins green** | **EXACT**, 11/14 |
| K-AS2 | `ary_errmap` entry 5 `FPERR_STROOM` → `6` | the same 3, a different site | **EXACT**, 11/14 |
| K-AS3 | `tss_ary`'s `ld a,3` → `ld a,0` (the shared tail's op) | **7**: `i.arystr`, `i.lineary`, the 3 array rows, both fit controls; `i.ary`/`i.arynodim` (numeric) and both scalar twins **green** | **EXACT**, 7/14 |

🎯 **K-AS3 IS THE ONE THAT ANSWERS THE ITEM.** K-AS1/K-AS2 prove the rows read
the *message* rather than merely "did it error". K-AS3 breaks the shared tail
itself and reddens exactly the rows that go through it — so the three new rows
provably reach `tss_ary`, rather than arriving at the same message some other
way. The two scalar twins staying green under all three cuts is the same
argument from the other side: they go through `str_set_key` and are not evidence
about this tail at all, which is what makes them controls.
