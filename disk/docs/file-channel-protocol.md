<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# zerobas Disk BASIC file-channel protocol — pinned spec (Phase 2, Step-0 spike)

Status: **research-spike output, not yet implemented.** This pins how MSX **Disk
BASIC** moves bytes for the file verbs (`OPEN`/`PRINT#`/`INPUT#`/`CLOSE`/`FILES`),
so Phase 2 can decide *how* zerobas provides them. It is the complement of the
Phase-1.5 [`expansion-protocol.md`](expansion-protocol.md), which pinned the
drive-letter *loader* path and deliberately skipped the file verbs.

Every finding is cited to an allowed source: the **MSX2 Technical Handbook** (TH),
the public **MSX hook table**, or this spike's **black-box openMSX observation** of
the genuine **National CF-3300** Disk BASIC (BP on the documented `DSKIO ($4010)`
entry + live register/RAM read-out; the reference ROM's code bytes were never read
or disassembled). Harness: `disk-spec/tools/diskbasic_probe_filechannel.py`
(msx-preservation).

---

## 0. Headline finding (the gate result)

**Disk BASIC's file verbs move every byte through the *same standard
`DSKIO ($4010)` sector interface + FAT12/dir logic + an FCB* that the drive-letter
loader path uses — NOT a separate file-channel/expansion protocol.** There is no
opaque "open a channel" cross-slot contract to learn: `OPEN`/`PRINT#`/`INPUT#`/
`CLOSE` resolve the 8.3 name, walk the FAT/dir, and read/write logical sectors,
exactly like `BLOAD"A:"`/`SAVE"A:"` (expansion-protocol.md §3).

Consequences:

* The **file I/O verbs** do **not** use the BASIC STATEMENT (`$4004`) or DEVICE
  (`$4006`) expansion. `PROCNM ($FD89, 16B)` and `DEVICE ($FD99)` stay **all-zero**
  across the whole sequence (observed; same areas the 1.5 spike found zero for the
  loader). The DEVICE header word is `$0000`. They are built-in interpreter tokens
  whose handlers call DSKIO directly cross-slot. **Scope caveat:** this is about the
  file I/O verbs only — the `CALL`-dispatched commands (`CALL FORMAT`, `CALL SYSTEM`)
  *do* use the STATEMENT expansion seam and were **not** observed here; see §1a.
* The substrate is **exactly what zerobas already owns**: `basic/fat.asm`
  (`fat_mount`/`fat_find`/`fat_read_file_sector` + the `fat_alloc_cluster`/
  `fat_write_fat_entry`/`fat_dir_*` write-back layer), all oracle-confirmed in
  Phase 1.5. So providing the verbs is **EXTEND** (add statement handlers +
  sequential record buffering on top of the existing FAT engine), **not DELEGATE**
  (host the in-slot Disk BASIC extension). See §5.

---

## 1. Dispatch — how a file verb reaches disk code

`FILES`, `OPEN`, `PRINT#`, `INPUT#`, `CLOSE` are **built-in BASIC tokens**, not
CALL-expansion statements:

* Breakpoint on the disk ROM's STATEMENT handler (the `$4004` header word's target)
  does **not** fire for `FILES`/`OPEN` (observed).
* `PROCNM ($FD89)` / `DEVICE ($FD99)` remain zero throughout (observed) — the
  DEVICE-expansion call mechanism (TH §5.7) is never invoked.

So on a real machine the disk ROM's own Disk BASIC code implements these token
handlers and calls its DSKIO. **This does not constrain zerobas:** zerobas already
runs its own statement dispatch (`ex_print`, `ex_bload`, … in `basic/interp.asm`);
it would add `ex_open`/`ex_printhash`/`ex_inputhash`/`ex_close`/`ex_files` that call
its own FAT engine. No cross-slot expansion hosting is required.

### 1a. CALL-dispatched commands (`CALL FORMAT` / `CALL SYSTEM`) — Step-0b: OBSERVED

A correction to an earlier over-broad claim: the STATEMENT-expansion seam (`$4004`,
TH §5.7) is **not** dead — it is exactly how the `CALL <name>` / `_<name>` extended
commands are dispatched. The two Disk BASIC ones:

* **`CALL FORMAT` / `_FORMAT`** — format a disk.
* **`CALL SYSTEM` / `_SYSTEM`** — exit BASIC to MSX-DOS. **Out of scope** — the
  DOS-boot path already deferred (needs `MSXDOS.SYS`;
  [`provider-oracle-scope.md`](provider-oracle-scope.md) §6).

**Observed (Step-0b, `diskbasic_probe_format.py`, real CF-3300):** typing
`CALL FORMAT` writes **`PROCNM ($FD89) = "FORMAT"`** (`46 4F 52 4D 41 54`) — the
decisive proof that the CALL name is placed in PROCNM and dispatched through the
STATEMENT expansion (TH §5.7), in direct contrast to the file verbs, which leave
PROCNM zero. The organic flow then shows the disk ROM's **`CHOICE ($4019)`** output
(the `Drive name?(A,B)` prompt + the `1-1 side / 2-2 sides / 3 / 4` format-type
menu) and halts at `Strike a key when ready` before **`DSKFMT ($401C)`** runs. So
the seam is: `CALL <name>` → name in PROCNM → STATEMENT handler → `CHOICE` + `DSKFMT`
(+ the `HFORM $FFAC` hook).

**Implication for zerobas (EXTEND-vs-DELEGATE, CALL commands):** two clean options,
to pick at Step-2 implementation:
* **EXTEND** (consistent with the file verbs) — zerobas-BASIC adds a `CALL`/`_`
  statement parser that special-cases `FORMAT` and calls `DSKFMT ($4010+$0C)` /
  `CHOICE` of the in-slot disk ROM; implement zerobas-disk's currently-stub
  `CHOICE`/`DSKFMT` for its own drive. Simplest; self-contained.
* **DELEGATE** (the documented generic seam) — zerobas-BASIC implements a *generic*
  `CALL <name>` dispatcher that loads PROCNM and invokes the in-slot disk ROM's
  STATEMENT handler ($4004). More faithful and supports a foreign ROM's other CALL
  commands too, but requires zerobas-disk to grow a real STATEMENT handler (today
  `$4004 = 0`). Provider-side work.
Lean EXTEND for consistency + self-containment; the generic dispatcher is a nice
follow-on if foreign-ROM CALL-command support is ever wanted. Not a blocker either
way. The exact `DSKFMT` sector-write pattern is an implementation-time observation
(let the format complete past the keypress on a /tmp disk).

---

## 2. The file-channel I/O contract (observed DSKIO trace)

A full write+read round trip on the real CF-3300, drive A, 720 KB image
(`media $F9`), `slot=3 1` confirming the disk ROM. DSKIO register convention is
the standard one (expansion-protocol.md §3): A=drive, B=#sectors, C=media,
DE=first logical sector, HL=buffer, **CY clear=READ / set=WRITE**.

**`OPEN "O.DAT" FOR OUTPUT AS #1` : `PRINT #1,"HELLO"` : `CLOSE #1`**
```
DSKIO A=00 B=03 C=F9 DE=0001 HL=E595 CY=0   ; read FAT (sectors 1..3)
DSKIO A=00 B=01 C=F9 DE=0007 HL=EB95 CY=0   ; read root dir (sector 7)
DSKIO A=00 B=01 C=F9 DE=0007 HL=EB95 CY=1   ; WRITE root dir  -> create O.DAT entry
DSKIO A=00 B=01 C=F9 DE=001A HL=ED95 CY=1   ; WRITE data sector (sec 0x1A = cluster 8)
DSKIO A=00 B=01 C=F9 DE=0007 HL=EB95 CY=1   ; WRITE root dir  -> stamp size/first cluster
DSKIO A=00 B=03 C=F9 DE=0001 HL=E595 CY=1   ; WRITE FAT copy 1 (sectors 1..3)
DSKIO A=00 B=03 C=F9 DE=0004 HL=E595 CY=1   ; WRITE FAT copy 2 (sectors 4..6)
```

**`OPEN "O.DAT" FOR INPUT AS #1` : `LINE INPUT #1,A$` : `CLOSE #1`**
```
DSKIO A=00 B=03 C=F9 DE=0001 HL=E595 CY=0   ; read FAT
DSKIO A=00 B=01 C=F9 DE=0007 HL=EB95 CY=0   ; read root dir -> find O.DAT
DSKIO A=00 B=01 C=F9 DE=001A HL=ED95 CY=0   ; read data sector -> deliver "HELLO"
```

Observations:

* **Identical to the loader SAVE/LOAD pattern** (expansion-protocol.md §3): read
  FAT + root dir, then on write: data sector, dir entry, **both FAT copies** (the
  `DE=0001` and `DE=0004` writes). zerobas-disk already produces this exact
  sequence internally and it is MSX-DOS-1 byte-confirmed.
* **Buffers live in the disk ROM's RAM work area** ($E595 FAT, $EB95 dir, $ED95
  data — the disk ROM's own scratch). A sequential record is staged in the data
  buffer and flushed a full 512-byte sector at a time (the single data write at
  `CLOSE` for a sub-sector file); multi-sector files extend the same way (more
  data writes + FAT-chain links), the same model as zerobas's
  `disk_putbyte`/`disk_write_end`.
* **CY is the only direction signal** — read vs write is the carry, nothing else.

---

## 3. The FCB / channel structure (work-area observation)

The open file's control block is a standard **FCB carrying the 8.3 name**. The
work-area sweep after `OPEN` shows, at ~`$F869`:
```
... 4F 20 20 20 20 20 20 20 44 41 54 ...   = "O       DAT"
```
i.e. the 11-byte space-padded 8.3 field for `O.DAT` — the same FCB name layout
zerobas already builds in `DISK_FCB` (`basic/sysvars.inc`, `build_83_name`) and
that the disk ROM's `fat_find` matches. The file number (`#1`) indexes a small
channel table sized by `MAXFILES`. (Exact per-channel offsets are an
implementation detail for Step 2; the name field + a record buffer + a position
are the load-bearing parts, and zerobas already has equivalents.)

---

## 4. Minimal surface zerobas must add (EXTEND path)

Nothing new at the disk interface — only interpreter-side, layered on the existing
FAT engine:

1. **Statement handlers** for `OPEN`/`CLOSE`/`PRINT#`/`INPUT#`/`FILES` (+ the
   functions `EOF`/`LOF`/`LOC`), dispatched like every other zerobas verb.
2. **A small channel table** (sized by `MAXFILES`): per channel an FCB (8.3 name —
   reuse `build_83_name`), the FAT iterator state, a 512-byte record buffer, and a
   byte position — i.e. the `fat_io_open`/`fat_io_getbyte`/`fat_io_create`/
   `fat_io_putbyte`/`fat_io_close` primitives **already in `basic/fat.asm`**, plus
   a thin sequential-record/formatting layer (`PRINT#` formats like `PRINT`;
   `INPUT#`/`LINE INPUT#` parse like console input).
3. **Tokens** for the new keywords (oracle-lock the crunch bytes against the
   VG-8020, as every prior verb did).

No DSKIO/FAT changes; the engine is reused as-is.

---

## 5. Go / No-go + DELEGATE vs EXTEND

**GO — and EXTEND, not DELEGATE.**

* **GO:** the protocol is fully pinned black-box and holds no surprises — it is the
  standard DSKIO + FAT12 + FCB substrate, already implemented and oracle-confirmed
  in zerobas. No opaque cross-slot file-channel contract exists to block us.
* **EXTEND** (recommended): build `OPEN`/`PRINT#`/`INPUT#`/`CLOSE`/`FILES` as
  zerobas statement handlers over the existing `basic/fat.asm` engine + a channel
  table. Reuses proven, oracle-confirmed code; self-contained; no dependency on a
  foreign ROM's internals.
* **DELEGATE** (rejected *for the file I/O verbs*): hosting the in-slot disk ROM's
  Disk BASIC extension would mean driving an opaque, ROM-private cross-slot dispatch.
  For the file I/O verbs specifically (§0/§1) there is nothing to delegate *through* —
  they are built-in tokens that don't use the documented STATEMENT/DEVICE expansion —
  so delegation buys nothing the EXTEND path lacks and adds a hard dependency on
  undocumented internals. (Note: this verdict is scoped to the file I/O verbs. The
  `CALL`-dispatched commands *do* use the documented expansion seam, §1a, so their
  EXTEND-vs-DELEGATE call is separate and still open.)

This **revises** the Phase-2 plan's open fork (TODO.md "Step 1") *for the file I/O
verbs*: the spike resolves it in favour of EXTEND. The basic-side `fat.asm` is
**kept** (not retired) and the verb surface is layered on top. The `CALL FORMAT`
seam (§1a) remains an open Step-0b question.

Caveat for Step 2 (not blockers): the exact per-channel FCB offsets, `MAXFILES`
default/sizing, and `PRINT#`/`INPUT#` formatting edge cases are implementation
details to pin verb-by-verb against this same CF-3300 oracle as each is built.

---

## 6. Clean-room statement

All disk-ROM behaviour here was obtained by **black-box observation**: a breakpoint
on the documented `DSKIO ($4010)` entry, reading the live Z80 register file and RAM
work areas (`$FD89`, `$FD99`, `$F8xx`), and the VRAM screen. The disk ROM's code
bytes (slot 3-1, `$4000`–`$7FFF`) were never read, captured, or disassembled. Every
address/convention is cited to the MSX2 Technical Handbook, the public MSX hook
table, or such observation. No implementation code was written; no commit was made
to zerobas sources for this spike.

---

## 7. Harness

`disk-spec/tools/diskbasic_probe_filechannel.py` (msx-preservation): boots the real
`National_CF-3300` Disk BASIC on a **/tmp copy** of `test720.dsk` (never the
committed image — Disk BASIC writes would mutate it; see
[[test-disk-mutation-gotcha]]), types the `OPEN`/`PRINT#`/`CLOSE`/`OPEN`/`INPUT#`/
`CLOSE` sequence, logs every `DSKIO ($4010)` call's input registers + carry via a
logging breakpoint, and dumps the FCB work area + screen. Reproduces §2 and §3.
Note (harness gotcha): under `set throttle off` each Enter must be a separate
`type` event ~3 s after its command **and encoded as the `\r` escape, never a raw
CR byte** (a literal CR breaks Tcl line parsing and silently drops the Enter).
