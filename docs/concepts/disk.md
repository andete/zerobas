<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# Disk BASIC — files on a 720 KB floppy, one drive

> **Status (2026-10-09):** the disk statements agree with the National CF-3300
> in the forms measured, except two open TIER 1 items in everyday use (the
> cursor after `FILES`, D-FILESNL; `GET #` / `PUT #` without a record number,
> D-RECAUTO). There is no logical drive B: yet (D-DSKIB, TIER 6, ruled to be
> built); the SHIFT/CTRL boot keys are unmeasured (D-BOOTKEYS, TIER 4).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

A disk MSX1 such as the National CF-3300 has one 3.5" drive and a disk ROM
that adds Disk BASIC: statements and functions that read and write files on
a 720 KB floppy in the FAT12 format MS-DOS also uses. zerobas has its own
disk ROM in the same place (slot 3-1), checked against the CF-3300 with the
same test disk on both machines.

For a user it works as on the reference: names are 8.3, the drive is `A:`,
the disk errors are numbered 50 to 72, and the directory and sector words
answer `Illegal function call` (5) on a machine without a disk.

## How it works

### The disk: a FAT12 volume

The test disk has the standard 720 KB layout that a CF-3300 writes for a
"2 sides, double track" format (numbers read from its boot sector):

| sectors | what |
|---|---|
| 0 | the boot sector: a jump, an 8-byte name, and the parameter block (BPB) — 512 bytes a sector, 2 sectors a cluster, 1 reserved sector, 2 FATs, 112 root entries, 1440 sectors, media byte `&HF9`, 3 sectors a FAT, 9 sectors a track, 2 sides |
| 1–3, 4–6 | two identical copies of the FAT |
| 7–13 | the root directory: 112 entries of 32 bytes |
| 14–1439 | file data, in clusters of 2 sectors (1 KB), numbered from 2: 713 clusters |

**The FAT** holds one 12-bit entry per cluster: `000` is free, any other
value is the next cluster of the same file, and `FFF` ends the chain. Two
entries share three bytes. `DSKF` counts the free entries, so its answer is in
kilobytes on this disk: 706 on the fresh test disk, whose six files use 7
clusters. `CALL FORMAT` also offers a 360 KB layout (media `&HFD`, 720
sectors, 2 sectors a FAT).

**A directory entry** is 32 bytes: the name (bytes 0–7) and extension
(8–10), upper case and padded with spaces; the attributes (11); the time
(22–23) and date (24–25) of the last write; the first cluster (26–27); the
size in bytes (28–31). A deleted entry starts with `&HE5`. A date is packed as
(year − 1980) × 512 + month × 32 + day.

**File names** are 8.3 and are upper-cased, so `"hi.txt"` and `"HI.TXT"` are
one file. Measured on the CF-3300 and matched (D-FSPEC, 2026-09-04;
D-FSPECCHAR, 2026-09-05):

- a name past 8 characters is not an error: the extension starts after the
  eighth, so `SAVE"TOOLONGNAME.BAS"` writes `TOOLONGN.AME`; `AB.EXTRA` is
  `AB.EXT`;
- an empty name, `"."`, `".."` or `"A.B.C"` is `Bad file name` (56) for
  every statement that needs a name, and so is a name containing a control
  character, `+ , / : ; = [ \ ]` or `&HFF`;
- `?` and `*` are wildcards for `FILES`, `KILL` and `COPY`; `OPEN` refuses
  them (56).

**Dates.** A file written from BASIC is stamped 1984-01-01 (`&H0821`), time 0,
as on the CF-3300 (Joost, 2026-10-01: *"Stamp as 3300"*). The date is a day
count kept at `&HF33B`; a `DATE` typed in MSX-DOS moves it, and a program
`SAVE`d in a disk BASIC entered with `A>BASIC` is stamped with that date, on
both machines ([MSX-DOS](msx-dos.md)). `COPY` keeps the source's date.

### Drives

`A:` is the one drive and the default; `DSKF` and `DSKI$` take 0 or 1 for it.
The CF-3300 also has a **logical drive B: on the same mechanism**: naming it
(`DSKF(2)`, `DSKI$(2,0)`, a `"B:"` file name) prints `Insert diskette for
drive B: and strike a key when ready` and waits, so two disks can share one
drive. zerobas lacks it (see *Differences*). Other letters (`C:`–`H:`, `Q:`
measured) are `Bad drive name` (62) on both.

### The disk statements, as a family

| words | what they do |
|---|---|
| [`FILES`](../keywords/FILES.md), [`LFILES`](../keywords/LFILES.md), [`DSKF`](../keywords/DSKF.md) | list the directory (optionally by a pattern); count free clusters |
| [`KILL`](../keywords/KILL.md), [`NAME`](../keywords/NAME.md), [`COPY`](../keywords/COPY.md) | delete, rename and copy files |
| [`DSKI$`](../keywords/DSKI$.md), [`DSKO$`](../keywords/DSKO$.md) | read or write one raw sector through the buffer whose address is at `&HF351` |
| [`LOAD`](../keywords/LOAD.md), [`SAVE`](../keywords/SAVE.md), [`RUN`](../keywords/RUN.md), [`MERGE`](../keywords/MERGE.md) | programs, tokenised or as text |
| [`BLOAD`](../keywords/BLOAD.md), [`BSAVE`](../keywords/BSAVE.md) | memory images |
| [`OPEN`](../keywords/OPEN.md), [`CLOSE`](../keywords/CLOSE.md), [`EOF`](../keywords/EOF.md), [`LOF`](../keywords/LOF.md), [`LOC`](../keywords/LOC.md) | file channels (`MAXFILES` sets how many) |
| [`FIELD`](../keywords/FIELD.md), [`GET`](../keywords/GET.md), [`PUT`](../keywords/PUT.md), [`LSET`](../keywords/LSET.md), [`RSET`](../keywords/RSET.md) | random-access records |
| `CALL FORMAT` | write an empty file system (360 KB or 720 KB) |

The file formats (`&HFF` before a tokenised program, `&HFE` and three
addresses before a `BSAVE` image) are on the keyword pages.

### Disk errors

Codes 50–59 are main-BASIC texts (the diskless VG-8020 has them too); 60
and up are the disk ROM's.

| code | text | where you meet it |
|---|---|---|
| 50, 52, 54, 55, 58, 59, 61 | `FIELD overflow`, `Bad file number`, `File already open`, `Input past end`, `Sequential I/O only`, `File not OPEN`, `Bad file mode` | file channels ([files and devices](files-and-devices.md)); 61 also for `BLOAD` of a file without `&HFE` |
| 53 | `File not found` | `LOAD`, `KILL`, `NAME`, `COPY`; `FILES` with no match or on an empty disk |
| 56 | `Bad file name` | see *File names* |
| 62 | `Bad drive name` | a drive past `B:` |
| 64 | `File still open` | `KILL`, `NAME`, `COPY` of an open file |
| 65 | `File already exists` | `NAME` onto an existing name |
| 66 | `Disk full` | no free cluster left |
| 68 | `Disk write protected` | `SAVE`, `SAVE ,A`, `BSAVE`, `OPEN … FOR OUTPUT` on a protected disk, another file open or not (`KILL`, `NAME`, `COPY` not measured) |
| 69 | `Disk I/O error` | a failed transfer |
| 70 | `Disk offline` | no disk in the drive |

zerobas also holds the texts of 51, 57, 60 and 63 (`Internal error`, `Direct
statement in file`, `Bad FAT`, `Bad sector number`); no keyword page records
a case that raises them. 67, 71 and 72 have no text here (`ERROR 67` prints
`Unprintable error`); the CF-3300's texts for them are unread. See
[errors](errors.md) for trapping.

### What the disk system costs in RAM

The CF-3300's disk ROM takes its work area from the top of BASIC's memory:
it boots with `HIMEM` `&HDE77` and 23430 bytes free, the diskless VG-8020 with
`&HF380` and 28815. zerobas's disk ROM lowers `HIMEM` by 750 bytes (disk state
for 15 channels); the rest of its cells sit in zerobas's own reserved RAM
([memory map](memory-map.md)). On 2026-09-30 zerobas's disk machine booted
with 23354 bytes free, 76 fewer than the CF-3300
([`engrow0_run.out`](../../scratchpad/engrow0_run.out)). Each extra `MAXFILES`
channel costs 267 bytes on both.

## Example

Read the boot sector and the FAT, write a file, read its directory entry
back. On the test disk (`TEST.BIN`, `HI.TXT`, `PROG.BIN`, `PROG.BAS`,
`PROG2.BAS`, `PROG3.BAS`):

```
10 A$=DSKI$(0,0)
20 B=PEEK(&HF351)+256*PEEK(&HF352)
30 PRINT PEEK(B+13);PEEK(B+17);
35 PRINT PEEK(B+22);HEX$(PEEK(B+21))
40 A$=DSKI$(0,1)
50 PRINT PEEK(B+3);PEEK(B+4);PEEK(B+5)
60 OPEN "N.TXT" FOR OUTPUT AS #1
70 PRINT #1,"AB":CLOSE
80 A$=DSKI$(0,7):E=B+192
90 FOR I=0 TO 10:PRINT CHR$(PEEK(E+I));
100 NEXT:D=PEEK(E+24)+256*PEEK(E+25)
110 PRINT PEEK(E+28);HEX$(D);DSKF(0)
RUN
 2  112  3 F9
 3  240  255
N       TXT 5 821 705
```

Row 1: 2 sectors a cluster, 112 root entries, 3 sectors a FAT, media `&HF9`.
Row 2: `TEST.BIN`'s chain — `03 F0 FF` unpack to `003` for cluster 2 (go on
at 3) and `FFF` for cluster 3 (the end). Row 3: the seventh directory entry,
the new file — name, size (5, as [`LOF`](../keywords/LOF.md) says), date
`&H0821` = 1984-01-01 — and the free count, one cluster below 706.

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_disk.out`](../../scratchpad/kwdoc_disk.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

- **`FILES` and the cursor** (D-FILESNL, TIER 1, 2026-10-09): after a listing
  whose last row is full, the CF-3300 starts a new line and zerobas does not.
- **`GET #` / `PUT #` without a record number** (D-RECAUTO, TIER 1,
  2026-10-09) use record 1 here; the CF-3300 takes the next record.
- **No logical drive B:** (D-DSKIB, TIER 6): `DSKF(2)` answers drive A's
  count, `DSKI$(2,0)` is `Bad drive name`, a `"B:"` name means `A:`. One
  physical drive stays (Joost, 2026-06-22); the prompt comes (ruled
  2026-10-09: *"yeah, we need to have the prompt mechanism"*).
- **Boot keys** (D-BOOTKEYS, TIER 4): Joost recalls SHIFT or CTRL held at
  power-on freeing RAM (by MSX convention SHIFT skips the disk ROM, CTRL drops
  drive B:). Neither is measured on the CF-3300 or built here.
- **`FILES " "` and `FILES "A:"`** list the disk on the CF-3300 and are
  `Bad file name` here, a pinned deferral in `namspc-acceptance` (D-FSPEC).
- **A wildcard `COPY` with two or more matches** is error 5 here (D-COPYWILD;
  Joost, 2026-10-09: *"stay error 5 for now"*).
- **Keys typed during long disk work** (D-FDCDI, TIER 3): both lose some,
  zerobas more; its driver keeps interrupts off for a whole sector operation.
- **`ERROR 60` to `64` on the diskless build** print the disk texts; the
  VG-8020 prints `Unprintable error` (D-NODISKERRTXT, TIER 6).
- **Own touches**: `CALL FORMAT` writes zerobas's boot code and disk name
  (the rest matches) and asks for no drive; the banner's disk line is ours.

## What we found, and how

- **Every write error was swallowed** (fixed 2026-09-28, D-WPROTECT): one
  instruction in our driver cleared the carry on every failed write, so a
  protected disk "saved" silently — found with a read-only test disk.
- **Raw sectors and open files shared one buffer** (fixed 2026-09-23,
  D-ALIASWCELL): `DSKF`, `KILL`, `NAME`, `COPY`, `DSKI$`, `DSKO$` or `SAVE`
  damaged a file being written. The CF-3300 keeps a separate raw buffer, and
  so does zerobas now.
- **A FAT entry straddling a sector edge was written wrongly** (fixed
  2026-07-04): clusters 170, 341 and 682, which no small-disk test reaches. A
  host unit test found it; the fix was checked against the FATs of 101 real
  disks.
- **Over-long names are truncated, not refused** (D-FSPEC, 2026-09-04) —
  only a statement that writes shows it; `FILES` says `File not found` anyway.

## How zerobas does it

The disk ROM ([disk/disk.asm](../../disk/disk.asm)) is 16 KB in slot 3-1,
with the standard entries at `&H4010` (`DSKIO`, `DSKCHG`, `GETDPB`, `CHOICE`,
`DSKFMT`, `MTOFF`); routines MSX-DOS calls sit at fixed addresses, so its free
space lies in pads between them ([disk-rom-layout.md](../disk-rom-layout.md)).
Its `INIT` ([disk/init.asm](../../disk/init.asm)) installs `H.PHYD`, publishes
the BDOS entry at `&HF37D`, reserves the channel table under `HIMEM` and boots
MSX-DOS from a system disk ([MSX-DOS](msx-dos.md));
[disk/driver.asm](../../disk/driver.asm) drives the controller.

The statements are parsed in the main ROM
([basic/files.asm](../../basic/files.asm); names in
[basic/fcbname-body.inc](../../basic/fcbname-body.inc)). The FAT12 engine
([basic/fat-prim-body.inc](../../basic/fat-prim-body.inc)) runs as a sub-ROM
tenant over `DSKIO`. `FILES`, `KILL`, `NAME`, `COPY` and `DSKF` cross to the
disk ROM through hooks (`H_FILE` … `H_DSKF`) answered by `hk_files` …
`hk_dskf` in [disk/kernel.asm](../../disk/kernel.asm); raw sectors move in
[sub/dirverb.asm](../../sub/dirverb.asm). Error texts 50–65 are in
[sub/errmsg.asm](../../sub/errmsg.asm), 66 and 68–70 in the disk ROM's
`hk_errp`, reached through `H.ERRP`.

## Related pages

The keyword pages in the table above; [MSX-DOS](msx-dos.md),
[files and devices](files-and-devices.md), [errors](errors.md),
[memory map](memory-map.md), [ROM layout](rom-layout.md),
[cassette](cassette.md); design notes
[spec-basic-diskerr.md](../spec-basic-diskerr.md) and
[spec-basic-dskio.md](../spec-basic-dskio.md).
- More keywords: [`DSKI$`](../keywords/DSKI$.md), [`DSKO$`](../keywords/DSKO$.md), [`KILL`](../keywords/KILL.md), [`NAME`](../keywords/NAME.md), [`LFILES`](../keywords/LFILES.md).

## Tests that cover it

- `make diskbasic-acceptance` — the statements against the CF-3300, by screen
  and by the disk image they leave; `make kwsweep` — every disk keyword's rows.
- `make copy-acceptance`, `dskio-acceptance`, `savedate-acceptance`,
  `namspc-acceptance` — `COPY`, raw sectors, date stamps, file names.
- `make wprotect-acceptance`, `diskfull-acceptance`, `nodiskerr-acceptance`
  — errors 68, 66 and 70; `make nodisk-acceptance` — error 5 without a disk.
- `make chancost-characterize` — channel cost; `make unit-test` — FAT12 on
  the host.
