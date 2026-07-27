<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — `BIN$` and `FRE`, the last two SILENT-GAP words

**Status:** SPEC, 2026-07-27 — **awaiting sign-off on D-BF-A..D-BF-D.** No
implementation until they are answered. Step 4 of
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

**≈ 20 B returned to the low region, and `BIN$` lands inside it.** The
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
([`basic/sysvars.inc:691`](../basic/sysvars.inc:691)) — ample for their 4- and
6-digit worst cases. **`BIN$`'s 16 digits do not fit**, and this is the one
place `BIN$` cannot clone its siblings.

The answer is not a bigger buffer. `sh_temp_push_alloc` already takes the digit
count in `A` and hands back the body pointer, so `sh_bin_build` can **count the
significant bits first** (shift until zero, minimum 1), allocate, then fill the
body MSB-first from the known top bit — **no intermediate buffer at all**. It
lives in `sub/strheap.asm` beside `sh_oct_build` as op = 8; sub.rom has ~3.5 KB
free on page 1 and ~4.5 KB on page 0, so the leaf compute is free.

`kwtable.inc` gains one entry (`db 4,"BIN$",2,PEEK_PREFIX,BIND_TOKEN`) — also
free, since the wave-3 eviction made the sub-ROM copy the sole source. One
`cp BIND_TOKEN / jp z,str_fn_bin` arm joins `str_func_ff`
([`basic/str-engine.asm:562`](../basic/str-engine.asm:562)): 5 B.

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

`heap_alloc` ([`sub/strheap.asm:262`](../sub/strheap.asm:262)) is a bump
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
them asserts that layout matches the VG-8020 byte for byte — which this project
has never claimed. But they are also the only *absolute* teeth the numeric form
would have under D-BF-A(b).

**Recommendation: gate the string-pool delta (100, which is exact by
construction and layout-independent) and `fre-dim-drops`; measure the other four
during the spike and gate them only if they already agree.** Do not implement
*toward* them.

### D-BF-C — fix D-BF-1 and D-BF-2 in this slice?

**Recommendation: yes.** §3 shows the collapse puts both checks in the one place
`BIN$` needs them anyway, so the marginal cost is close to zero and the
alternative is writing the same check a third time. Both are silent wrong
answers in the very class this slice exists to empty.

### D-BF-D — is `BIN$`'s implementation the counted-bits builder (§3.1)?

**Recommendation: yes** — it avoids the `NUMBUF` problem outright rather than
enlarging a shared scratch buffer that `MID$`-statement aliasing already
constrains ([`basic/sysvars.inc:697`](../basic/sysvars.inc:697)).

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
rows, `fre-dim-drops`, and the GC rows.

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
