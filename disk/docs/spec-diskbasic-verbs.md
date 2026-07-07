<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Behavioural spec: the zerobas Disk-BASIC verb surface

The BASIC-visible disk verbs zerobas implements — how they move bytes to and from a
FAT12 disk, the file-channel and record structures they use, and the state each is
verified in. This is a layer *above* the MSX-DOS-1 disk-ROM kernel ABI
([`spec-diskrom-kernel.md`](spec-diskrom-kernel.md)): the verbs are BASIC-interpreter
tokens whose handlers ultimately drive the standard `DSKIO ($4010)` + FAT12 engine.

**Genre / value.** The MSX2 Technical Handbook documents these verbs at the
*user-syntax* level. This spec deliberately does **not** restate that; its value is
the **worked, oracle-validated integration** the Handbook omits — the observed
byte-level `DSKIO` call sequence a verb produces, the FCB / channel structure, the
mapping onto zerobas's own implementation, and the exact verification state (which
verbs are locked by a self-asserting oracle differential, which are thin). All
disk-ROM behaviour here was obtained **black-box** (breakpoint on the documented
`DSKIO` entry + live register/RAM read-out); no reference ROM was disassembled
([`../../README.md`](../../README.md), clean-room).

> **Scope.** The **disk** verb surface only. Cassette verbs (`CSAVE`/`CLOAD`) belong
> to the tape stack ([`../../tape/docs/spec-cassette.md`](../../tape/docs/spec-cassette.md)).
> `CALL SYSTEM` (exit to MSX-DOS) is out of scope. `LOC`, `DSKI$`, `DSKO$`
> (direct-sector access) are **not implemented** (no token defined) — §7.

---

## 1. The verb surface

Every verb below is implemented and, at the 2026-07-05 baseline, converges against
the oracle under the standing gate `make diskbasic-acceptance` (**23/23**). "Handler"
is the zerobas dispatch entry; "verified by" names the self-asserting probe under
[`../../probes/disk/`](../../probes/disk/) (the reproducibility anchor, part of this
deliverable).

### Directory / file management

| Verb | Handler | Behaviour | Verified by |
|---|---|---|---|
| `FILES` | `ex_files` ([`../../basic/files.asm`](../../basic/files.asm)) | list the directory | `disk_probe_files` (live) |
| `KILL` | `ex_kill` | delete a file (free dir entry + FAT chain) | `disk_probe_kill` (live) |
| `NAME` | `ex_name` | rename a file; **rejects a collision** onto an existing name (shares the M35 refusal, [`spec-diskrom-kernel.md` §9](spec-diskrom-kernel.md)) | `disk_probe_name` (live), `test_fren_collision` (host) |
| `MAXFILES` | `ex_maxfiles` | size the open-channel table | `disk_probe_maxfiles` (live) |

### Program loaders

| Verb | Handler | Behaviour | Verified by |
|---|---|---|---|
| `SAVE` | (tokeniser + `fat_io_create`/`putbyte`) | write a tokenised program | `disk_probe_save` (artifact) |
| `LOAD` | `fat_io_open`/`getbyte` ([`../../basic/bload.asm`](../../basic/bload.asm)) | read a tokenised program; embedded-`NUL` safe | `disk_probe_load_disk`, `disk_probe_load_embedded_nul` (artifact) |
| `RUN "file"` | `ex_run` ([`../../basic/interp.asm`](../../basic/interp.asm)) | load + execute | `disk_probe_run_disk` (artifact) |
| `MERGE` | `ex_merge` | merge an ASCII-listed program | `disk_probe_merge` (live) |
| `BLOAD` | `fat_io_open`/`getbyte` | load a binary image (`+,R` auto-run) | `disk_probe_bload_disk`, `disk_probe_bload_fcb` (artifact) |
| `BSAVE` | `bsv_open` ([`../../basic/save.asm`](../../basic/save.asm)) | write a binary image | `disk_probe_save`, `disk_probe_save_bas` (artifact) |

### Sequential channel I/O

| Verb | Handler | Behaviour | Verified by |
|---|---|---|---|
| `OPEN` | `ex_open` ([`../../basic/files.asm`](../../basic/files.asm)) | open a channel `FOR INPUT`/`OUTPUT`/`APPEND` | `disk_probe_filewrite`/`fileread`/`append` (live) |
| `CLOSE` | `ex_close` | flush + release a channel | *incidental only — §7 thin cell* |
| `PRINT#` | `ex_print` ([`../../basic/print.asm`](../../basic/print.asm)) | formatted write to a channel | `disk_probe_filewrite`, `disk_probe_append` (live) |
| `PRINT# USING` | `ex_print_using` ([`../../basic/printusing.asm`](../../basic/printusing.asm)) | format-string write | `disk_probe_printusing_file` (live) |
| `INPUT#` | `ex_input` | parse fields from a channel (strings; numeric = Phase-3) | `disk_probe_fileread` (live) |
| `LINE INPUT#` | `ex_line` | read a whole line | *incidental only — §7 thin cell* |
| `INPUT$` | `ex_input` | read N raw bytes | `disk_probe_inputdollar` (live) |

### Random-access record I/O

| Verb | Handler | Behaviour | Verified by |
|---|---|---|---|
| `FIELD` | `ex_field` ([`../../basic/field.asm`](../../basic/field.asm)) | map string vars onto a record buffer | `disk_probe_field` (live), `test_field` (host) |
| `LSET` / `RSET` | (field.asm) | left/right-justify into a field | `disk_probe_field`/`getput`, `test_field` |
| `GET #n` | `ex_get` | read record n (kernel RDBLK path, [`spec-diskrom-kernel.md` §6.3](spec-diskrom-kernel.md)) | `disk_probe_getput`, `disk_probe_rdblk_roundtrip`, `test_rdblk_randrecord` |
| `PUT #n` | `ex_put` | write record n (kernel WRBLK/WRRND path) | `disk_probe_getput`, `disk_probe_wrblk_roundtrip`, `test_wrblk_*`/`test_wrrnd_extend` |
| `MKI$`/`MKS$`/`MKD$`, `CVI`/`CVS`/`CVD` | (field.asm) | numeric ↔ packed-bytes conversions | `disk_probe_mkicvi` (live) |

### File-position functions & formatting

| Verb | Handler | Behaviour | Verified by |
|---|---|---|---|
| `EOF` | (files.asm) | end-of-file test on a channel | `disk_probe_eof` (live) |
| `LOF` | (files.asm) | file length | `disk_probe_eof` (live) |
| `DSKF` | (files.asm) | free space on a drive | `disk_probe_dskf` (live) |
| `CALL FORMAT` | `ex_*` via the STATEMENT seam ([`../../basic/format.asm`](../../basic/format.asm)) | format a disk — §6 | `disk_probe_format` (structural) |

---

## 2. Dispatch — built-in tokens, not the CALL/DEVICE expansion

The file I/O verbs are **built-in interpreter tokens** whose handlers call the FAT
engine directly; they do **not** use the documented STATEMENT (`$4004`) or DEVICE
(`$4006`) expansion seam. Black-box confirmation: across a whole
`OPEN`/`PRINT#`/`CLOSE` sequence on the CF-3300, `PROCNM ($FD89)` and `DEVICE
($FD99)` stay **all-zero** and the disk-ROM STATEMENT handler never fires
(`diskbasic_probe_filechannel.py`). This is why zerobas provides them by **EXTEND**:
its own statement handlers (`ex_open`, `ex_print`, …) over its own `basic/fat.asm`
engine — no cross-slot hosting of a foreign ROM's Disk-BASIC extension is required.

The **one exception** is the `CALL <name>` family: `CALL FORMAT` *does* use the
STATEMENT-expansion seam — typing it writes `PROCNM = "FORMAT"` and dispatches
through the `$4004` handler (§6).

---

## 3. The file-channel I/O contract (observed `DSKIO` trace)

Disk-BASIC file verbs move every byte through the **same standard `DSKIO ($4010)`
sector interface + FAT12/dir logic + an FCB** as the drive-letter loader path — there
is no separate file-channel protocol. `DSKIO` register convention (the standard one):
`A`=drive, `B`=sector count, `C`=media, `DE`=first logical sector, `HL`=buffer,
**`CY` clear = READ / set = WRITE** — carry is the *only* direction signal.

A full write→read round-trip on the CF-3300 (720 KB image, `media $F9`), oracle-
observed:

```
OPEN "O.DAT" FOR OUTPUT : PRINT #1,"HELLO" : CLOSE
  DSKIO A=00 B=03 DE=0001 CY=0   ; read FAT (sectors 1..3)
  DSKIO A=00 B=01 DE=0007 CY=0   ; read root dir (sector 7)
  DSKIO A=00 B=01 DE=0007 CY=1   ; WRITE root dir  -> create O.DAT entry
  DSKIO A=00 B=01 DE=001A CY=1   ; WRITE data sector (cluster 8)
  DSKIO A=00 B=01 DE=0007 CY=1   ; WRITE root dir  -> stamp size/first cluster
  DSKIO A=00 B=03 DE=0001 CY=1   ; WRITE FAT copy 1 (sectors 1..3)
  DSKIO A=00 B=03 DE=0004 CY=1   ; WRITE FAT copy 2 (sectors 4..6)

OPEN "O.DAT" FOR INPUT : LINE INPUT #1,A$ : CLOSE
  DSKIO A=00 B=03 DE=0001 CY=0   ; read FAT
  DSKIO A=00 B=01 DE=0007 CY=0   ; read root dir -> find O.DAT
  DSKIO A=00 B=01 DE=001A CY=0   ; read data sector -> deliver "HELLO"
```

The write path stamps the directory entry twice (create, then size/first-cluster)
and writes **both FAT copies** — byte-identical to zerobas's own internal sequence,
which is MSX-DOS-1-confirmed. A sequential record is staged in a 512-byte data buffer
and flushed a full sector at a time; multi-sector files extend by more data writes +
FAT-chain links (zerobas's `fat_io_putbyte`/`fat_io_close`). The buffers live in the
disk ROM's own RAM work area (FAT/dir/data scratch), not in BASIC's variable area.

---

## 4. The FCB / channel structure

An open file's control block is a standard **FCB carrying the space-padded 11-byte
8.3 name**. After `OPEN "O.DAT"` the work area holds `4F 20 20 20 20 20 20 20 44 41
54` = `"O       DAT"` — the same layout zerobas builds via `build_83_name`
([`../../basic/sysvars.inc`](../../basic/sysvars.inc)) and that the kernel's
`fat_find` matches. The file number (`#n`) indexes a small channel table sized by
`MAXFILES`; each channel carries the FCB, the FAT-iterator state, a 512-byte record
buffer, and a byte position. zerobas's primitives are the `fat_io_open` /
`fat_io_create` / `fat_io_append` / `fat_io_getbyte` / `fat_io_putbyte` /
`fat_io_close` set in [`../../basic/fat.asm`](../../basic/fat.asm).

---

## 5. Random-access record I/O

`FIELD` maps string variables onto the channel's record buffer; `LSET`/`RSET`
justify into a field; `MKI$`/`MKS$`/`MKD$` and `CVI`/`CVS`/`CVD` pack/unpack numbers
to/from the fixed-width byte forms. `GET #n` / `PUT #n` are the record transfers:
they resolve to the kernel's **random block** paths — `GET` to RDBLK (`$47B2`,
M31), `PUT` to WRBLK/WRRND (`$47BE`/`rrnd`, M28/M36) — so the record-positioning,
past-EOF-extend, and size semantics are exactly those documented in
[`spec-diskrom-kernel.md` §6.3/§9](spec-diskrom-kernel.md). The random-open helper is
`fat_rand_open` ([`../../basic/field.asm`](../../basic/field.asm)); the transfers are
disk-artifact-round-trip verified against the CF-3300 and host-unit-tested
(`test_field`, `test_rdblk_randrecord`, `test_wrblk_*`, `test_wrrnd_extend`).

---

## 6. `CALL FORMAT`

`CALL FORMAT` (`_FORMAT`) is dispatched through the STATEMENT-expansion seam (§2):
typing it places `"FORMAT"` in `PROCNM ($FD89)`, the `$4004` handler runs, and the
flow reaches the disk ROM's `CHOICE ($4019)` output — the `Drive name?(A,B)` prompt +
the `1 / 2 / 3 / 4` format-type menu — then halts at `Strike a key when ready` before
`DSKFMT ($401C)` writes the fresh BPB + FAT. zerobas implements this in
[`../../basic/format.asm`](../../basic/format.asm) over its own drive; the produced
image is verified **structurally** — the formatted BPB/FAT bytes are asserted against
the public FAT12 spec for both 720 KB and 360 KB (`disk_probe_format`).

---

## 7. Scope boundaries (honest at the walls)

- **Not implemented (no token):** `LOC`, `DSKI$`, `DSKO$` — Phase-3 direct-sector
  access. Excluded from the coverage denominator, not silent gaps.
- **`CALL SYSTEM`** — exits BASIC to MSX-DOS; out of scope for the BASIC stack.
- **Numeric `INPUT#`** — Phase-3; today `INPUT#` reads strings only.
- **Two thin verification cells:** `CLOSE` and `LINE INPUT#` are exercised only
  *incidentally* inside other probes (no dedicated self-asserting differential of
  their own). They are implemented and pass, but their coverage depth is the two
  known-shallow spots; a dedicated CLOSE + LINE INPUT# differential is the tracked
  backfill.

---

## 8. Verification & clean-room basis

- **Standing gate:** `make diskbasic-acceptance`
  ([`diskbasic-acceptance-spec.md`](diskbasic-acceptance-spec.md)) replays the
  self-asserting Disk-BASIC probes and re-asserts each converges — **23/23** at the
  2026-07-05 baseline; re-run after any BASIC/kernel/ROM change (a red gate means
  *investigate*, not "the ROM regressed": the first run's SAVE/BSAVE red was a
  flaky openMSX type-injection artifact, disproved by an offline FAT12 dump).
- **Two legitimate oracle styles**, both gated: **live** CF-3300 differentials
  (directory / channel / record verbs) and the **read-only FAT12 artifact** oracle
  (the program loaders — compared to real stock images read per the public spec,
  [`oracle-artifacts.md`](oracle-artifacts.md)). `CALL FORMAT` uses a **structural**
  self-check against the FAT12 spec.
- **Host unit tests** (`make unit-test`) lock in the record paths emulator-free.
- **Clean-room.** Every disk-ROM behaviour above was obtained by black-box
  observation — a breakpoint on the documented `DSKIO ($4010)` entry, reading the
  live Z80 registers and the RAM work area (`$FD89`, `$FD99`, the FCB region) and the
  VRAM screen. The disk ROM's code bytes (slot 3-1, `$4000–$7FFF`) were never read or
  disassembled; every address/convention is cited to the MSX2 Technical Handbook, the
  public MSX hook table, or such observation.

## Provenance trail

This spec distils two working-genre documents, which remain the notebook / provenance
record: the file-channel research spike
[`file-channel-protocol.md`](file-channel-protocol.md) (the DSKIO trace + FCB
observation + the EXTEND-vs-DELEGATE decision) and the per-verb scoreboard
[`diskbasic-verb-coverage.md`](diskbasic-verb-coverage.md) (the coverage matrix + the
gate baseline). The underlying kernel-level contracts the record verbs stand on are in
[`spec-diskrom-kernel.md`](spec-diskrom-kernel.md).
