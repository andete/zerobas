<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# What a directory-MUTATING disk verb says when nothing matched — MSX1 measured

Probe: [`basic_probe_dskmsg.py`](../probes/basic/basic_probe_dskmsg.py)
(`make dskmsg-characterize` / `make dskmsg-acceptance`).
Spec: [`spec-basic-dskmsg.md`](spec-basic-dskmsg.md).
Predecessor: [`lptverb-msx1-characterization.md`](lptverb-msx1-characterization.md)
§4, which measured the same disposition for `FILES`/`LFILES` (R-LF4/R-LF6) and
whose implementing slice deliberately did **not** carry the answer over to
`KILL`.

---

## 0. Why this is a ONE-REFERENCE reading, and why that is structural

`KILL`, `NAME` and `FILES` are Disk-BASIC words: they live in the disk ROM's
crunch table, and a diskless MSX1 has no entry for any of them. On the Philips
VG-8020 all three answer `Syntax error`, which measures **the absence of a disk
interface**, not a language rule. So the battery is two-sided by construction —
the National CF-3300 and zerobas — and the probe refuses a `--sides vg8020` run
rather than printing a column of `Syntax error` that a reader could mistake for a
measurement.

Same structural reason as `LFILES`'s missing VG-8020 column
([`lptverb-msx1-characterization.md`](lptverb-msx1-characterization.md) §0), and
it is stated for the same reason: an absence that is not written down reads as an
omission.

## 1. The apparatus, and the two controls that make it readable

Fixture: a /tmp copy of `disk/test720.dsk` — directory `TEST.BIN`, `HI.TXT`,
`PROG.BIN`, `PROG.BAS`, `PROG2.BAS`. Boot-per-case, the side's reset carried
into the case (the CF-3300's leading `""` answers its boot date prompt and
`SCREEN 0` puts it in the 40-column mode this scrape reads).

🔴 **EVERY SUBJECT ROW HERE EXPECTS AN ERROR MESSAGE, AND THAT IS THE
DISPOSITION A TOTALLY DEAD SUBJECT SATISFIES.** `make fat-error-acceptance`
scored `ALL PASS 8/8` on a 16384-byte all-`$00` `build/disk.rom`, and on five
further corruptions — red in 0 of 6
([[gate-whose-answer-is-an-error-passes-a-dead-subject]]). When the disk
subsystem is dead every file is missing, so the wanted observable arrives for a
reason unrelated to the rule. Two positive controls run in the **same
invocation, on the same mounted image**, and both assert positive TEXT rather
than the absence of an error string:

| control | asserts | why it is not redundant |
|---|---|---|
| `dsk-ctl` — `FILES"HI.TXT"` | the reading contains `HI` **and** `TXT` | the volume mounts, the root-directory walk runs and a named file is FOUND — the Cy=0 half of the path `dsk-killnone` is the Cy=1 half of |
| `dsk-killhit` — `KILL"HI.TXT"` then `FILES` | `HI      .TXT` **absent** and `TEST`/`BIN` **present** | `KILL` reached the FAT layer and SUCCEEDED. The absence half alone is a negative assertion a machine that cannot read a directory also satisfies; the survivors are what make it positive evidence |
| `dsk-namehit` — `NAME"HI.TXT" AS "BYE.TXT"` then `FILES` (added 2026-08-07, D-DKNAME) | `BYE`, `TXT` **and** `TEST` **present**, `HI      .TXT` **absent** | the same shape for the verb the other two say nothing about. **ONE CONTROL PER GATED VERB** — §4 is why it arrived a slice after the other two |

Without `dsk-killhit`, a build whose `KILL` was a no-op that always errored would
score a perfect run: `dsk-ctl` green (KILL untouched) and `dsk-killnone` green
(it errors, which is the want). The control is what separates *"KILL refuses a
no-match"* from *"KILL refuses"*.

🔴 **AND THAT SENTENCE WAS MEASURED FOR `NAME`, NOT ARGUED** (D-DKNAME's knife
K-NAMECTL, [`spec-basic-dkname.md`](spec-basic-dkname.md) §6.4). With
`tnt_name_stamp` re-reading the directory sector instead of writing it back —
`NAME` reports success and renames nothing — `dsk-namenone` still reads
`File not found` **on both sides**, `dsk-ctl` and `dsk-killhit` hold
byte-for-byte, and `make fat-error-acceptance` scores **8/8 ALL PASS at exit 0**
with its own PRECONDITION green. Only `dsk-namehit` reds. Two instruments
reporting a clean run over a provably broken verb is what a per-verb control
costs, and what it buys.

⚠️ **`dsk-killhit` and `dsk-namehit` write, so each gets a private copy of the
image.** Boot-per-case reboots the machine but keeps handing openMSX the same
file; shared with the read-only rows they would delete or rename `HI.TXT` out
from under `dsk-ctl` on a `--repeat 2` second pass.

## 2. Measured rules

Both rows below were taken on the CF-3300 on 2026-08-07, with both controls
green, **before** any zerobas change.

| # | rule | evidence |
|---|---|---|
| **R-DK1** | 🔴 `KILL` at a filespec that matches nothing prints **`File not found`** — the same message, and the same ERR 53 disposition, as `FILES`/`LFILES` (R-LF4/R-LF6). | `KILL"NOSUCH.XXX"` → `File not found` (`dsk-killnone`) |
| **R-DK2** | `NAME`'s missing-OLD-file answer is **`File not found`** too. | `NAME"NOSUCH.BAS" AS "ZZ.BAS"` → `File not found` (`dsk-namenone`) |

## 3. The zerobas baseline, before any implementation

| row | CF-3300 | zerobas at `152cdaa` | |
|---|---|---|---|
| `dsk-ctl` | `HI      .TXT` | `HI      .TXT` | ✅ control |
| `dsk-killhit` | `FILES / TEST    .BIN PROG    .BIN PROG    .BAS / PROG2   .BAS` | identical | ✅ control |
| `dsk-killnone` | `File not found` | **`load error`** | 🔴 diverges |
| `dsk-namenone` | `File not found` | **`load error`** | 🔴 diverges |

`load error` is zerobas's own lowercase wording, a divergence
`basic/PROVENANCE.md` quarantines for the whole no-disk / mount / I-O class.

## 4. 🔴 R-DK2 was MEASURED and deliberately NOT ACTED ON — for ONE SLICE

✅ **CLOSED 2026-08-07 by D-DKNAME**
([`spec-basic-dkname.md`](spec-basic-dkname.md)). `dsk-namenone` is a **gated**
row and reads `File not found` on both sides; the printed `NOT GATED:` line is
gone with it, and `basic/files.asm` has a `nm_notfound` arm.
**The section below is kept as written**, because the reason the two verbs moved
a slice apart is the finding — and because the third bullet was **right about the
mechanism and wrong about the size**: §2.2 of the new spec shows the shared exit
was only the first of two conflations, and the arm split cost **4 B**, not ≈5.

Both verbs answer the same on the reference, and only one is changed by
[`spec-basic-dskmsg.md`](spec-basic-dskmsg.md). The distinction is not
convenience:

* **`do_kill`'s divergence is one its own inline comment contradicts.**
  `basic/files.asm` reads `jp z,load_error ; nothing matched -> File not found`
  — the code and the comment on the same line disagree, and R-DK1 says the
  comment was right.
* **`do_name`'s divergence is one `basic/PROVENANCE.md` §NAME states outright**
  (*"Errors (no disk / old not found / I-O) reuse load_error"*), with the code
  and the comment agreeing.
* **And the fixes are not the same size.** `do_kill`'s no-match arm is reachable
  on its own (§2 of the spec makes it so). `do_name`'s is `nm_fail`, a **shared
  exit** for the `fat_mount` failure *and* the `fat_find` miss, so making the
  miss reference-exact means splitting the arm first — ≈5 B more, and a second
  unmeasured disposition to reason about.

Retiring a quarantined divergence silently, one verb at a time and on a reading
taken for its neighbour, is how a divergence register stops describing the tree —
which is the exact failure D-LFILES filed this residual to avoid. R-DK2 is
recorded, printed by the gate as an explicitly **not-gated** characterization
row, and filed in `TODO.md`.

## 5. Measured NOT to be measured

* **`KILL` / `NAME` with no disk mounted, or on an unreadable volume.** Nothing
  here drives that arm, and the spec's knife K-KILL2 is a written-down predicted
  MISS for exactly that reason — as is D-DKNAME's **K-NAME2**, which re-pointed
  `NAME`'s mount arm at `df_notfound` and moved **nothing** on either instrument,
  in both rounds. What zerobas prints there is `load error` by design (the
  quarantined class above); what the CF-3300 prints is **not claimed**.
* ⚠️ **AND AN I-O ERROR DURING THE DIRECTORY SCAN IS NOT SEPARATED EITHER.**
  `fat_find`'s own contract is `Cy = 1 not found / error`, so since D-DKNAME a
  `read_sector` failure mid-walk reaches `NAME`'s `File not found` arm. `KILL`
  has the same shape one primitive over (an I-O error inside `fat_delete` reads
  as "nothing matched"). Stated, not measured; separating either needs a status
  out of the primitive.
* **`ERR` / `ON ERROR` behaviour of the new disposition.** `File not found`
  arrives through `raise_error` with code 53, so `ERR` reads 53 and `ON ERROR`
  traps it where `load error` did neither. That is a consequence of the
  mechanism, stated, and no row here reads it.
* **`KILL` at a WILDCARD that matches nothing** (`KILL"*.ZZZ"`). Same tenant
  arm, same `deleted-any = 0` return; not separately typed.
