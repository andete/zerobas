<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — disk-BASIC relocation: THE SEAM, MEASURED

**Status: AWAITING USER SIGN-OFF. No code written.** (Option 3 priced 2026-09-15; §4, §5 and §6 updated with the partition.)
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

## 4. Option 3, PRICED — and the method that failed first

A branch-reachability closure from `ex_files`/`ex_kill`/`ex_name` reaches 16
labels and **194 B** against `files.asm`'s measured 1600, because **control
reaches most of these bodies by FALLTHROUGH**, which a branch walk cannot see —
the same blind spot `dupspan` has. `seamscout.py` keeps that closure WITH the
warning, because the negative result is what sent the measurement somewhere else.

[`scratchpad/verbpartition.py`](../../scratchpad/verbpartition.py) does it the way
that works for a contiguous, address-ordered assembly file: sort the file's
symbols by address, cut at each VERB ENTRY, attribute each span to the verb that
opens it. **It sums to 1600 B — the same figure `regionscout.py` and
`basic-reloc` give** for `files.asm` in main page 1 on 2026-09-15.

| region opens at | group | bytes |
|---|---|---|
| `chan_gate` | infra | 22 |
| `ex_copy` | FAT-light | 24 |
| `disk_error` | infra | 10 |
| `ex_files` (+`ex_lfiles`) | FAT-light | 93 |
| `ex_open` | channel | 560 |
| `ex_line` (+`ex_input`) | channel | 144 |
| `ex_close` | channel | 54 |
| `init_filechan` | infra | 337 |
| `ex_kill` | FAT-light | 44 |
| `ex_name` | FAT-light | 95 |
| `ex_maxfiles` | channel | 41 |
| `ex_merge` | channel | 176 |
| **FAT-light total** | | **256** |
| **channel total** | | **975** |
| **infra total** | | **369** |

⚠️ **What the partition cannot say:** a span belongs to the verb that opens it
only if no other verb jumps into it. So the labels called from OUTSIDE
`files.asm`/`field.asm` are listed separately — **15 labels, 164 B** in
`files.asm` (`fname_expr` 30, `init_filechan` 30, `fch_select` 20, `fch_ctx_addr`
12, `disk_error` 10, `dirverb_op` 10, `df_or_loaderr` 9, `fch_modes_ptr` 9,
`pdfcb_resume` 7, `fch_check` 6, `chan_gate` 6, `ascii_read_lines` 6,
`read_into_strscr` 4, `arl_getbyte` 4, `dev_cmp` 1) and **3 labels, 39 B** in
`field.asm` (`fld_lookup` 19, `fld_key_de` 15, `fld_init` 5). Those do not travel
with a verb: they stay, or they need a provider-side entry.

## 5. The options, priced at the granularity that IS measured

| option | relief | what it costs |
|---|---|---|
| 1. split `fat.asm` | ≤ 124 B | refuted as a lever |
| 2. reuse `disk/fat.asm` | ≤ 124 B | ditto; do it only alongside a real move |
| 3. minimal move (`COPY`/`FILES`/`LFILES`/`KILL`/`NAME`) | **256 B** | the fewest edges; the shared infra (`disk_error`, `chan_gate`, `dirverb_op`) stays and its calls go cross-slot |
| 3b. all of `files.asm` except the shared infra | **1231 B** | adds the whole channel manager's clientele — `OPEN`/`CLOSE`/`INPUT#`/`MERGE` — and the 15 shared labels still stay |
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

**Option 3, at 256 B, is the one to take first — and it is worth taking.** Main
page 1 had **5 B** free on 2026-09-15, so 256 B is fifty times today's entire
headroom, bought with the smallest coupling of any option on the table: five verbs
that do directory work and nothing else, leaving the channel manager and every
shared helper where they are.

It is NOT the ~3 KB the parent spec hoped for, and that difference is the whole
value of measuring: **the bulk of `files.asm` is the CHANNEL machinery (975 B),
not the directory verbs (256 B)**, and the channel machinery is precisely the part
that is entangled — `init_filechan`, `fch_select`, `fch_check` and `fch_ctx_addr`
are called from `expr.asm`, `str-engine.asm`, `input.asm`, `strvar.asm` and
`print.asm`.

So the ladder, cheapest coupling first: **3 (256 B) → 3b (1231 B) → 4 (2315 B)**,
and each step buys bytes by taking on more interpreter entanglement, not more FAT.

Options 1 and 2 should be struck from the parent spec as levers: measurement has
overtaken them — both are capped at `basic/fat.asm`'s whole 124 B.

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
