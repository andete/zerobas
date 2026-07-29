<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-ARR-C — the dimension count (`MAXDIM = 4` is a divergence, not a cap)

**Status: ✅ LANDED 2026-07-29 — `make arrdim-acceptance` 65/65 gated, ALL PASS,
−28 B in the low region.** S-ARR-C-1 = **B, pointer not
buffer**; S-ARR-C-3 = **delete `MAXDIM` entirely**; S-ARR-C-2/-4/-5 as
recommended. Split out of D-ARR-B by
[`spec-basic-arrdim.md`](spec-basic-arrdim.md) §7a. Measurement:
[`arrdim-c-vg8020-characterization.md`](arrdim-c-vg8020-characterization.md),
`make arrdim-characterize`, 73 rows. At sign-off: 55 gated / 18 never-gated;
as landed: **65 gated / 8 never-gated**. Baseline for this slice: **10 divergent
rows** (`dim-5dim`/`-8dim`/`-12dim`,
`cap-8`/`-16`/`-32`/`-40`/`-42`, `use-8`/`use-32`).

---

## 1. The divergence

`DIM A(0,0,0,0,0)` is accepted by the reference and answers `Subscript out of
range` here, from the fifth subscript on.
[`basic/sysvars.inc:1544`](../basic/sysvars.inc:1544) caps subscripts at
`MAXDIM = 4`; [`spec-basic-arrays.md`](spec-basic-arrays.md) §9.1 Q-9b records the
disposition `>MAXDIM subscripts → Subscript out of range` — **chosen, written
down, and never measured against the reference.** Same arc, same shape as §4
target #9, which was asked and never answered and hid D-ARR-B for a year.

## 2. The contract to implement

> **A subscript/bound list has no implementation-imposed length limit.** The only
> bound is what a program line can express.

Pinned by measurement (characterization §1–§3):

| clause | pinned by |
|---|---|
| there is **no cap** to match | `ERR` = 0 on the reference at 4, 8, 16, 32, 40, 42, 44, 64, 100 and **120** subscripts; `cap-120`'s line is 249 characters, three short of the reference's own input line |
| the dimensions are **really honoured**, not parsed and dropped | `use-32` stores through 32 subscripts and reads the value back (`[ 0  7 ]`). ⚠️ The `cap` rows alone cannot say this — a machine that drops the excess reads `ERR`=0 too |
| **auto-dim past four subscripts is the SIZE rule** | `Q(1,1,1,1,1)=1`, `Q%(1,1,1,1,1)=1` and the 8-subscript form all answer `Subscript out of range`; the 4-subscript int control answers `Out of memory`. 11⁵ elements is 322102 B at the *narrowest* element width, so no auto-dim past four can ever fit `$FFFF` |

Unchanged: everything D-ARR-B pinned. The size rule, the argument domain, the
negative-bound check, `Redimensioned array`, and the ordering between them all
apply per-subscript and are indifferent to how many subscripts there are.

## 3. ⚠️ The premise §7a split this on has MOVED — it is not an address-math rewrite

§7a's case for a separate slice was that the subscripts sit in **reverse order** on
the stack, so approach B "rewrites `ary_resolve`'s **column-major element-offset
math**, where a mistake is *silent memory corruption, not an error message*."

**That is wrong, and the correction is the reason this slice is tractable.**

`ary_parse_subs` pushes `v₀` first, so `v₀` lands at the **highest** address and
`v_{n-1}` at `SP`. Hand the tenant a pointer to **`v₀`** — the high end — and let
it walk **downward**, and every consumer visits `k = 0, 1, … n-1` in exactly the
order it does today. The change at each of the four consumers is `inc ix` → `dec
ix`: identical instruction count, identical size, and **the element-offset math is
not touched at all.** The descriptor layout does not change either, because
`aal_bounds_lp` still *writes* bounds in ascending `k`.

Per [[answer-signoff-questions-by-measuring]] and D-ARR-B's own "a sign-off's
premise can move after the sign-off": reported, not quietly delivered.

## 4. The design — a pointer, not a buffer

`ary_parse_subs` **already collects every subscript on the hardware stack**
(the 2026-07-15 re-entrancy fix: `X(X(0))` needs a per-nesting-level region, and
the stack gives one for free). It then copies them into `ARY_IDX`, an 8-byte RAM
buffer, purely so the tenant has a fixed address to read. `MAXDIM` exists only to
bound that copy. **Delete the copy and the cap has nothing left to bound.**

### 4.1 Param block (`basic/sysvars.inc` §10.2)

`ARY_IDX` (8 B) is replaced by two 2-byte fields, leaving **4 bytes free** in the
`$E028..$E037` span — a span whose own header records `CURLINE` immediately above
at `$E038` and no slack, so this *gives back* rather than asks:

| | was | becomes |
|---|---|---|
| `$E02D` | `ARY_IDX`, int16 × `MAXDIM` (8) | **`ARY_IDXP`** — pointer to subscript **0**, the high end of the on-stack block (2) |
| `$E02F` | *(part of `ARY_IDX`)* | **`ARY_CUR`** — the text cursor, parked across the engine call (2) |
| `$E031..$E034` | *(part of `ARY_IDX`)* | **free** |

`ARY_NIDX` (the count) is unchanged and stays the tenant's loop bound. `MAXDIM` is
deleted outright (§10, S-ARR-C-3).

`ARY_CUR` is safe against the same re-entrancy `ARY_NIDX`/`ARY_IDX` already survive:
it is written at the close paren, **after** every `eval` has returned, and consumed
by the engine call immediately after, so no nested parse can interleave with it —
the identical atomicity argument the block write already rests on.

### 4.2 Main side (`basic/arrays.asm`)

The parse and the engine call **fuse**. They must: the block lives on the stack, so
it cannot survive `ary_parse_subs`'s own `ret`. `ary_parse_subs` + `ary_parse_subs_kt`
+ each caller's publish/call/abort tail become one routine:

```
ary_parse_call:   ; BC=key, D=type, E=op, HL=cursor at '('
                  ; -> Z ok / NZ (FPERR set); HL = cursor past ')'
    push de                       ; [TYPE:OP]  guards, across eval
    push bc                       ; [KEY]
    <parse loop — UNCHANGED, minus the MAXDIM check>
  at ')':
    ld (ARY_CUR),hl               ; park the cursor
    pop bc                        ; B = n
    ld (ARY_NIDX),a               ; n
    IX = SP + 2n - 2              ; = &v₀, the HIGH end
    ld (ARY_IDXP),ix
    publish ARY_KEY/ARY_TYPE/ARY_OP from (ix+2..ix+5)
    FPERR check -> skip the call
    call ary_engine_call
  tail:
    ld hl,(ARY_CUR)
    SP += 2n + 4                  ; values + both guard words
    ld a,(FPERR) / or a           ; re-derive Z instead of preserving flags
    ret
```

Two details worth pinning:

- **The flags are re-derived, not preserved.** `FPERR` is provably 0 at the engine
  call (the parse bails first if not) and non-zero exactly when the engine failed,
  so `ld a,(FPERR) / or a` after the release reproduces `ary_engine_call`'s own
  Z/NZ for 4 bytes and no shadow-register games.
- **The guards are reached over, not popped.** They sit *above* the value block
  (pushed before `eval`, which is unavoidable), so they are read at constant
  displacements off the `IX` we compute anyway.

Call sites collapse to `ld de,<type:op>` + `call ary_parse_call`:
`ary_op0_resolve` (op 0), `ex_dim` (op 1). `ex_erase`/`ex_let_arr_str`'s op-2/op-3
calls have no subscript list and keep their own `ary_engine_call` + explicit
`[CURSOR]` push, unchanged.

### 4.3 Tenant side (`sub/arrays.asm`) — four pointers turn around

| site | change |
|---|---|
| `aeng_dim`'s negative-bound loop | `ld ix,ARY_IDX` → `ld ix,(ARY_IDXP)`; `inc ix` ×2 → `dec ix` ×2 |
| `ary_alloc`'s `aal_bounds_lp` | same; the descriptor is still written in ascending `k` |
| `ary_count_elems` | walks downward; the product is order-independent, and its "HL advanced" output is read by no caller |
| `ary_resolve`'s subscript walk | same; **the offset/MULT math is untouched** |

`ARY_AUTODIM_BOUNDS` stays **four** words and is pointed at its *last* entry (all
entries are 10, so a downward walk reads the same table). It never needs to be
longer, because auto-dim past four subscripts is always the size error —
**measured** (§2), not assumed. The tenant takes an explicit early exit:

> auto-dim (`ary_find` miss) with `(ARY_NIDX) > 4` ⇒ `ARY_ERR = 1` (`Subscript out
> of range`), without consulting the table.

### 4.4 Lifetime across `subrom_call`

The block must stay live from the close paren until the tenant returns.
`subrom_call`/`CALSLT` push strictly **below** `SP`, and the block sits **above**
it, so it survives untouched; the caller must not release it before the tenant
returns, which the fused routine guarantees by construction (the release is in its
own tail). `ary_engine_call`'s pushes are balanced, so `SP` at the tail equals `SP`
at the close paren — which is what makes `SP += 2n + 4` correct.

### 4.5 The stack budget, measured

C-BIOS sets `SP = $F300` and zerobas's own RAM tops out at `$EF00` — **1024 bytes**
of headroom. The worst case a program line can express is **43 subscripts = 86
bytes** (§5), under 9% of it, on top of `eval`'s own nesting. Measured, not
assumed; characterization §5.

## 5. ⚠️ What this slice CANNOT reach — `LINEMAX`

zerobas's last intact input line is **95 characters** against the reference's 250
(`LINEMAX = 96`, [`basic/sysvars.inc:760`](../basic/sysvars.inc:760); measured,
characterization §4). `20 DIM A(0,…)` is `2n+9` characters, so **43 subscripts is
zerobas's real ceiling** whatever this slice does.

`cap-44`/`-64`/`-100`/`-120` are therefore **not** D-ARR-C rows — the D-ARR-B commit
filed two of them under "MAXDIM=4" and that names the wrong cause. The cap is
precisely what hid it: the parse aborts at the fifth subscript long before the
truncated tail is reached, so all four read a ` 9 ` indistinguishable from a cap
row. They stay reported-never-gated under `LINEMAX`, which is its own item.

## 6. Space

The low region has **4 bytes free** and page 1 has **10** (clean build, `33b6446`),
and `ary_parse_subs`/`ary_op0_resolve` sit at `$3DB4`/`$3F91` — **in the low
region, the tighter wall.** So the accounting matters, and this slice is expected
to be **net-negative** because deleting the cap deletes machinery:

| | |
|---|---|
| `apsub_toomany`/`_tm_drop`/`_skip_lp`/`_skip_done` (`$3DFF..$3E12`) | **−20 B** |
| the `cp MAXDIM` / `jr nc` check | **−5 B** |
| `apsub_close`'s `ARY_IDX` address math + pop-copy loop | **−29 B** |
| `ary_parse_subs_kt`'s push/pop/`ex (sp),hl` shim | **−9 B** |
| `ary_op0_resolve` + `ex_dim` publish/call/pop tails, now shared | **≈ −30 B** |
| the fused close: park, `&v₀`, publish ×3 | **≈ +35 B** |
| the fused release tail | **≈ +20 B** |
| call-site `ld de,<type:op>` ×2 | **≈ +6 B** |

**Estimated net ≈ −30 B in the low region**, i.e. the slice funds itself and
widens the wall. ⚠️ **This is an estimate and the wall is 4 bytes** — it is
confirmed by building, not by this table (S-ARR-C-5). If it overruns, the lever is
promotion to the sub-ROM (~3.4 KB free), the D-CLP precedent; the clone frontier is
dry.

RAM: **−4 B** (the param block gives back four of `ARY_IDX`'s eight).

### 6.1 As built — measured from a clean build

| | before (`33b6446`) | after | |
|---|---|---|---|
| page-0 low region free | **4 B** | **32 B** | **28 B GIVEN BACK** |
| page-1 free | 10 B | 10 B | unchanged |
| sub-ROM | — | +~20 B | the tenant's downward walks + the auto-dim guard |

**The estimate held (−30 est. / −28 measured), and no funding was needed.** The
slice pays for itself out of the machinery the cap required: deleting a *check*
also deleted its unwind path, its skip-to-`)` recovery, the `_kt` shim and two
callers' publish/pop tails. `rm -rf build` first, per
[[measure-the-wall-from-clean]] — a warm tree has reported 55 B free where the
same sources overran by 14.

⚠️ Note the direction of the surprise: §7a's estimate of **−10…−15 B** was
*too pessimistic*, for the same reason its risk assessment was (§3). Removing a
constraint removes more than the line that states it: the cap's unwind path, its
skip-to-`)` recovery, the `_kt` shim and two callers' publish/pop tails all went
with the `cp MAXDIM`.

## 7. Gate

`make arrdim-acceptance` — the standing gate, 73 rows. After this slice:
**65 gated** (55 today + the 10 D-ARR-C targets), 8 never-gated (`cap-44`/`-64`/
`-100`/`-120`, `line-96`/`-97`/`-100`/`-250`), each printing its `LINEMAX` reason.

Plus, unchanged and required green: `make unit-test` (53/53 — `tests/test_arrays.py`
pokes `ARY_IDX` directly at eight sites and moves to `ARY_IDXP`),
`make array-acceptance` (149/151, the two `ifc.instr.*` reds being the standing
baseline), `make clearpool-acceptance` (52/52).

## 8. Falsification

Green suites and static reasoning have missed register/order bugs in this exact
routine before (the slice-1 `ex (sp),hl` bug *executed the tokenised line as
code*). So each claim gets a witness that goes red when the code under test is
deleted:

1. **the cap is gone** — `cap-8` (5+ subscripts accepted at all);
2. **the dimensions are honoured** — `use-32`: a value stored through 32 subscripts
   and read back. This is what a "parse and drop the excess" implementation fails
   and every `cap` row passes;
3. **the walk direction is right** — a host unit test (`tests/test_arrays.py`,
   emulator-free) that `DIM`s an asymmetric array — bounds `(1,2,3)`, so a
   *reversed* walk lands on a different element — writes a known value at
   `(1,0,2)` and reads back the element address, comparing it against the
   column-major address computed in Python. ⚠️ **This is the corruption-class
   check**: a reversed walk on a symmetric array is invisible, which is exactly
   why every existing `MAXDIM`-era test uses equal bounds;
4. **auto-dim past four is the size rule, through the allocator** — `auto-5d`,
   `auto-5d-int`, `auto-8d`. These pass *today* through the cap, so they must be
   re-confirmed to fail when `aal_soor` is broken deliberately, not merely observed
   still green ([[gate-can-be-green-while-measuring-nothing]]);
5. **the block survives `CALSLT`** — `use-32` again: 32 words on the stack across a
   `subrom_call`. A lifetime bug corrupts the readback rather than erroring.

## 9. Out of scope

- **`LINEMAX = 96`** (§5) — a real divergence, its own item.
- **The `Out of memory` threshold** — a property of each machine's memory map.
- A dimension count past what a 255-character line can express (~123) is
  unreachable on either machine and is not a target.

## 10. Sign-off

**S-ARR-C-1 — approach: pointer (B), not a bigger buffer (A).**
*Recommendation: B.* A raised `MAXDIM = N` costs `2N` bytes of RAM in a span with
no slack (86 B for the 43 a line can express), and leaves a number that was
*chosen* rather than measured — the exact mistake this slice exists to correct. B
gives back 4 B of RAM and ≈30 B of ROM. §3 removes the risk that split it out.

**S-ARR-C-2 — the auto-dim shortcut (`ndim > 4` ⇒ `Subscript out of range`,
without a table walk).** *Recommendation: yes*, on the §2 measurement: 11⁵ at the
narrowest element width is 322102 B, so no auto-dim past four can fit `$FFFF`, and
the reference answers the size error at 5, 5-int and 8.

**S-ARR-C-3 — delete `MAXDIM` entirely, or keep a residual defensive cap?**
*Recommendation: delete.* A residual cap would be another unmeasurable chosen
number; the real bound is the line length (43) and the stack has 12× headroom for
it (§4.5). Keeping one costs bytes to re-add the unwind machinery §6 deletes.

**S-ARR-C-4 — `cap-44`/`-64`/`-100`/`-120` + `line-*`: leave never-gated under
`LINEMAX`, or open the `LINEMAX` item now?** *Recommendation: leave them, correctly
labelled* (already done, `66a7e48`) and keep `LINEMAX` as a separate item. Raising
it touches the REPL, `ascii_read_lines` and a page-`$E1` buffer that G3/G4/G5
already share.

**S-ARR-C-5 — the space estimate is an estimate.** *Recommendation: implement,
then confirm against a clean build before the change is considered landed*, and
report a promotion requirement immediately if the low region overruns rather than
absorbing it into this slice. [[measure-the-wall-from-clean]].

---

Related: [[arrdim-slice]], [[arrays-dim-arc]], [[clearpool-slice]],
[[spec-before-implementation]], [[answer-signoff-questions-by-measuring]],
[[gate-during-implementation]], [[measure-the-wall-from-clean]],
[[promotion-funds-low-region]], [[refactor-inherits-clobber-contracts]].
