<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — disk-BASIC relocation: THE SEAM, MEASURED

**Status: AWAITING USER SIGN-OFF. No code written.**
This is the spec [`spec-diskbasic-relocation.md`](spec-diskbasic-relocation.md)
mandates ("the spec's first job is to **find the real seam**") and the
measurement Joost asked for on 2026-09-15 ("re-decide after the seam is
measured"). Every number below is measured, by
[`scratchpad/regionscout.py`](../../scratchpad/regionscout.py) and
[`scratchpad/seamscout.py`](../../scratchpad/seamscout.py), on the 2026-09-15
build.

## 0. The one-line result

**The seam the spec-input feared is already gone, and the seam that exists is a
different one.** Verbs↔FAT is **6 branch edges**, not the ~28 estimated.
Verbs↔INTERPRETER is **140 outbound edges**. Relocation is not a FAT problem; it
is an interpreter-coupling problem.

## 1. What is actually in main page 1

`regionscout.py` maps every main-image symbol to its source file and splits by
region. It cross-checks exactly against `basic-reloc`: page 1 12443 + 3936 =
16379, leaving the 5 B that tool reports; low region 6126 B, its string-engine
figure.

| file | kind | page 1 |
|---|---|---|
| `files.asm` | disk | 1600 |
| `cload.asm` | tape | 864 |
| `field.asm` | disk | 600 |
| `save.asm` | disk+tape | 533 |
| `fat.asm` | disk | 124 |
| `format.asm` | disk | 115 |
| `bload.asm` | disk | 100 |
| **disk-only** | | **2539** |
| **tape-only** | | **864** |
| **total** | | **3936** |

Against **5 B free in main page 1** and **0 B in the low region** — they share one
budget. `disk.rom` has ~8820 B free in 32 runs, largest usable hole 3182 B; the
sub ROM has 505 B (p0) + 50 B (p1).

## 2. 🔴 The estimate the spec-input was built on is refuted

`spec-diskbasic-relocation.md` says: *"Coupling count: `files.asm` → `fat.asm`
~15 calls, `field.asm` → ~13."* Measured:

| from | to | edges | targets |
|---|---|---|---|
| `files.asm` | `fat.asm` | **3** | `fat_io_append`, `fch_flush_active`, `fch_restage` |
| `field.asm` | `fat.asm` | **3** | `fatprim_bounce` ×3 |

**Six, not twenty-eight.** The reason is visible in `basic/fat.asm`'s own header:
the primitive/sector layer was evicted to the sub-ROM tenants (`fatprim_tenant`,
`fatio-body.inc`) after that estimate was written, and what remains of
`basic/fat.asm` in main page 1 is **124 B**. The "~28 cross-slot CALLSLTs back
into BASIC" the spec-input treats as the central obstacle **does not exist**.

⚠️ This also kills two of its four options on their own terms:

* **Option 1 — split `fat.asm` into loader-FAT vs channel/record-FAT.** Maximum
  relief **124 B**, the whole file. Not a lever.
* **Option 2 — bind the moved verbs to `disk/fat.asm` instead.** Avoids a
  duplication that is already only 124 B. Still worth doing *if* verbs move, but
  it is not a reason to move them.

## 3. The seam that does exist: the interpreter

| from | outbound edges to the rest of BASIC | top targets |
|---|---|---|
| `files.asm` | **99** | `interp.asm` 53, `program.asm` 11, `str-engine.asm` 5, `expr.asm` 4 |
| `field.asm` | **41** | `interp.asm` 27, `expr.asm` 7, `vars.asm` 4 |
| `save.asm` | 27 | `interp.asm` 13, `program.asm` 4 |
| `cload.asm` | 30 | `program.asm` 14, `fatio-body.inc` 6 |
| `bload.asm` | 9 | `interp.asm` 6 |
| `format.asm` | 9 | `interp.asm` 5 |

And inbound, which a move turns into cross-slot entries in the other direction:

| into | inbound edges | callers |
|---|---|---|
| `files.asm` | **26** | `expr.asm` 8, `str-engine.asm` 7, `input.asm` 3, `strvar.asm` 3, `print.asm` 2 |
| `bload.asm` | 6 | `bload-body.inc` 2, `print.asm` 2 |
| `field.asm` | 4 | `strvar.asm` 3, `vars.asm` 1 |
| `save.asm` | 4 | `interp.asm` 3, `print.asm` 1 |
| `cload.asm` | 4 | `interp.asm` 4 |

Plus the dispatch the edge scan cannot see, because `stmt_table` entries are `dw`:
**11** entries into `files.asm`, **5** into `field.asm`, **2** into `format.asm`,
**1** into `cload.asm`. Those 19 are exactly what the `$4004` STATEMENT expansion
would replace.

**So moving `files.asm` + `field.asm` means 140 outbound calls become cross-slot,
and 30 inbound ones need provider-side entry points.** That, not FAT, is the cost
to weigh.

## 4. What is NOT measured, and why

Option 3 ("minimal move — only the FAT-light verbs; measure the actual relief")
**cannot be priced by this instrument**. A branch-reachability closure from
`ex_files`/`ex_kill`/`ex_name` reaches 16 labels and 194 B against `files.asm`'s
measured 1600 — because **control reaches most of these bodies by FALLTHROUGH**,
which a branch walk cannot see. (The same blind spot `dupspan` has: a span is
entered without anything branching to it.) `seamscout.py` keeps the closure with
that warning, because the negative result is the finding.

➡️ Pricing option 3 needs a different method: an address-ordered partition of
`files.asm`'s symbols into verb bodies, cross-checked against the listing. That is
a measurement slice of its own, and it is the **only** thing standing between
here and a priced option 3.

## 5. The options, priced at the granularity that IS measured

| option | relief | what it costs |
|---|---|---|
| 1. split `fat.asm` | ≤ 124 B | refuted as a lever |
| 2. reuse `disk/fat.asm` | ≤ 124 B | ditto; do it only alongside a real move |
| 3. minimal move (`FILES`/`KILL`/`NAME`) | **unpriced** — needs §4 | fewest edges, but the number is not yet known |
| 4. move `files`+`field`(+`format`) | **2315 B** | 140 outbound edges cross-slot, 30 inbound entry points, 19 `dw` dispatches replaced by `$4004`; and it drops the foreign-disk-ROM interop |
| 5. tape → sub ROM (`cload.asm`) | 864 B | does not fit today: sub p0 has 505 B, p1 50 B. Needs a sub-ROM carve first (Joost ruled: carve the sub ROM first) |

⚠️ **On the interop.** `basic/fat.asm:11` and the 2026-06 spike record that the
BASIC-side FAT is *"the NECESSARY PRICE of the universal sector interface"*, proven
by every disk verb passing with the foreign CF-3300 disk ROM in slot 3-1.
**No standing gate asserts it** — `expansion-protocol.md` §251 lists the
host-direction test as an acknowledged *"Gap (small)"*. So the property is real,
documented and spike-proven, but nothing would go red if it broke. If option 4 is
taken, those documents must be corrected in the same slice, and the "Gap (small)"
entry closed as WONTFIX rather than left as a to-do.

## 6. Recommendation

**Price option 3 first (§4), then decide between 3 and 4.** Option 4's 2315 B is
real and large, but its 140 cross-slot edges are a different and bigger change than
the spec-input anticipated, and it spends a property this project deliberately
bought. Option 3 may deliver a useful fraction at a fraction of the coupling — and
today nobody can say, which is the one thing worth fixing next.

Options 1 and 2 should be struck from the parent spec as levers: measurement has
overtaken them.

## 7. Mechanism (unchanged from the parent spec, restated for completeness)

`$4004` STATEMENT expansion; `disk/init.asm` already lays an `"AB"` header with a
zeroed STATEMENT vector. The consumer slot-walk does not exist yet — an unknown
statement falls to `stmt_error` — so it must be written in `basic/interp.asm`.
Cross-slot idiom `CALLF`/`RST 30h`, as the HPHYD hook uses. Bodies assemble at the
`disk.rom` internal gaps with a `ds gap_end - $` guard, addresses confirmed against
a fresh build.

## 8. Verification (unchanged, and it is the reason this is one slice per step)

`diskbasic-acceptance` 34/34, `bdos-acceptance`, `bdos-cbios-selfcheck`,
`unit-test`, plus every moved verb end-to-end and the loader path. 🔴 **And a
relocation moves code between REGIONS, so it needs the full
`python3 scratchpad/kwknife.py --all` and `--allfn` re-measure** — the one-run
re-stamp that sufficed for D-KWSAVEEND's 3-byte tail does not.
