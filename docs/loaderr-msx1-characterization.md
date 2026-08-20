<!-- Copyright (c) 2026 Joost Yervante Damad -- SPDX-License-Identifier: 0BSD -->

# D-LOADERR — `load error` is printed, not raised, at six verbs

Measured 2026-08-20, two sides (National CF-3300, zerobas
`C-BIOS_MSX1_EU_REPACK_DISK`); a diskless VG-8020 cannot express any of it.
Completes the class D-DSKMSG §4.2 and D-DKNAME §3.4/§6.5 both stopped at —
*"that reading opens the whole `load error` wording divergence for
`LOAD`/`RUN`/`BLOAD`/`OPEN`/`APPEND`/`MERGE` — six verbs nothing has
measured."*

All six are measured. No ROM byte: this is the denominator and the price.

---

## 1. The rows

Stored programs, `RUN`, read off the screen.

| verb | program (line 10) | CF-3300 | zerobas |
|---|---|---|---|
| `LOAD` | `LOAD"FCZ.DAT"` | `File not found in 10` | **`load error`** then `[OK]` |
| `BLOAD` | `BLOAD"FCY.BIN"` | `File not found in 10` | **`load error`** then `[OK]` |
| `RUN"f"` | `RUN"FCZ.DAT"` | `File not found in 10` | **`load error`** then `[OK]` |
| `MERGE` | `MERGE"FCZ.DAT"` | `File not found in 10` | **`load error`** then `[OK]` |
| `OPEN…INPUT` | `OPEN"FCZ.DAT"FOR INPUT AS #1` | `File not found in 10` | **`load error`** then `[OK]` |
| `OPEN…APPEND` | `OPEN"FCZ.DAT"FOR APPEND AS #1` | `File not found in 10` | **`load error`** then `[OK]` |
| `SAVE` (bad arg) | `A$="FC2.DAT"` / `SAVE A$` | `OK` | **`load error`** then `[OK]` |
| 🎯 `BLOAD` wrong kind | `BLOAD"PROG.BAS"` | **`Bad file mode in 10`** | **`load error`** then `[OK]` |
| 🟢 `OPEN…INPUT` ok | `OPEN"PROG.BAS"FOR INPUT AS #1` | `[OK]` | `[OK]` |
| 🟢 `OPEN…APPEND` ok | `OPEN"PROG.BAS"FOR APPEND AS #1` | `[OK]` | `[OK]` |

Uniform, on both axes: the reference **raises** an ERR with a line number and
**stops**; zerobas **prints** a lowercase string and **carries on**.
[`basic/bload.asm:160`](../basic/bload.asm) `load_error` is `TAPIOF`, an
`ERRMARK` byte, `print_msg`, **`ret`** — no ERR code, no line number, no
`ON ERROR` trap.

The two green controls matter: the same verbs against a file that *does* exist
read `[OK]` on both sides, so the divergence is the failure path and not the
verb.

---

## 2. 🎯 `KILL` and `NAME` are the precedent, and they are already right

`dskmsg-acceptance` has gated `dsk-killnone` and `dsk-namenone` since
2026-08-07, and both **agree** — their missing-file arms route at
[`basic/files.asm`](../basic/files.asm) `df_notfound` (`ld a,53` +
`jp raise_error`). So the target face is not a guess; it is what two verbs in
the same battery already produce, with the machinery already resident.

Eight verbs share one class. Two are fixed. Six are not.

---

## 3. 🔴 The reference distinguishes NOT FOUND from WRONG KIND

`BLOAD"PROG.BAS"` — a real file, not a binary — is **`Bad file mode in 10`** on
the CF-3300 and `load error` here. So zerobas collapses at least two distinct
reference errors into one string, and a fix that routed every `load_error` at
ERR 53 would trade one wrong answer for another on this row.

🎯 **THAT IS THE `ARY_ERR=4` SHAPE AGAIN** (D-ARYOOS, the same day): one code
serving several causes, where the repair is a *split by which failure happened*
and not a rename. It is the reason §4 is a design question rather than an edit.

---

## 4. Why this is not a jump-target swap — stated by the source itself

[`basic/cload.asm:840`](../basic/cload.asm):

> 🔴 THE CONTRACT IS STATED ON THIS ROUTINE'S OWN EXITS, NOT INSIDE
> `load_error`. `load_error` is `jp`ed to from ~50 sites across
> files/save/print/field/format/bload/cload, **several of which RESUME into
> their caller on purpose**.

There are **73** real jumps to it (`jp`/`jr`/`call`, comments excluded), across
nine files. `load_error` *returning* is load-bearing: making it raise would
silently delete every one of those resumes.

So the fix is per-arm, and the arms are themselves conflated:

* `oo_fail` ([`basic/files.asm:347`](../basic/files.asm)) is OPEN's single
  post-claim failure exit, and its own comment says it covers **not found /
  dir-full / mount / I-O error**.
* `dpl_err` ([`basic/cload.asm`](../basic/cload.asm)) is the same for
  `LOAD`/`RUN"f"`/`MERGE`: **not found / mount / I-O error / EOF-before-data**.

Both take their CF from `fat_io_open`, which returns **carry and nothing else**.
🔴 **So the primitive has to return a status before either arm can be split**,
exactly as `aeng_copy_str` needed its own `ARY_ERR` code. Routing `oo_fail` or
`dpl_err` wholesale at `df_notfound` would report `File not found` for an
unreadable disk, which is a new defect in place of the old one.

💰 **Not priced.** The shape is: a status out of `fat_io_open` (and whatever
`disk_prog_load` learns from it), then per-cause arms. `df_notfound` already
exists and ERR 53's message is sub-hosted, so the *raise* end is free; the
*classification* end is the slice.

---

## 4a. ✅ FIXED THE SAME DAY — see [`loaderr-fix-notes.md`](loaderr-fix-notes.md)

§4 called this a design question. It was, and the design turned out to be
sixteen bytes: `fatprim_bounce` already records **which** primitive it is about
to run in `DISKOP_OP`, so `DISKOP_OP == FAT_FIND` on a failure means *mounted
fine, name not there* — no new status, no change to `fat_io_open`. Five of the
six verbs now raise ERR 53; `BLOAD` cannot use the test (sub-ROM tenant, never
writes the cell) and its two rows stay reported.

🔴 **And the first draft broke the cassette**, because `dpl_err` is shared with
`do_tape_prog` and no tape op writes that cell — caught by
`castail-acceptance`, a battery this slice does not own. §4's own warning
("routing `oo_fail` wholesale would report `File not found` for an unreadable
disk") was right about the class and I then missed nine instances of it one file
away. **Guarding an instance of a class is not guarding the class.**

## 5. Status

Seven rows added to
[`probes/basic/basic_probe_dskmsg.py`](../probes/basic/basic_probe_dskmsg.py),
**printed and NOT gated** — they diverge today, and gating a known divergence
turns a battery red forever instead of measuring anything. That is precisely the
state `dsk-namenone` was in until its arm split landed, and these graduate the
same way. A row here that started AGREEING would itself be a finding.

⚠️ **The `NOT_GATED` set is a list of measured holes, not a convenience.** It is
printed in the run's own tail with the reason, so it cannot quietly become the
place rows go to be forgotten.
