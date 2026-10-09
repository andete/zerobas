<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `COPY` — copy a file on the disk

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. One recorded
> difference: a wildcard that matches several files (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`COPY "source" TO "destination"` makes a byte-for-byte copy of a file on the
disk, under a new name. It is a Disk BASIC statement: the reference is the
National CF-3300. zerobas copies the same bytes, gives the copy the same name
and date, and raises the same errors in every case we have measured, except
one wildcard case that is a deliberate decision.

## Syntax

```
COPY <source file name> TO <destination file name>
```

Both names are string expressions (`COPY A$ TO B$` works) and may carry a
drive (`"A:HI.TXT"`). Blanks around `TO` are allowed. The source may contain
the wildcards `?` and `*`; so may the destination.

## Details

- **The copy is exact.** Every byte of the source ends up in the destination,
  files of several sectors and clusters included.
- **An existing destination is overwritten**, silently.
- **The copy keeps the source's date and time**; it is not stamped with the
  current date.
- **A `?` in the destination is filled from the source's name**, even when the
  source has no wildcard: `COPY "HI.TXT" TO "X?.TXT"` makes `XI.TXT`.
- **A wildcard source that matches exactly one file** copies that file:
  `COPY "HI.*" TO "H2.*"` makes `H2.TXT`.
- **The rest of the line runs** after `COPY`: `COPY "A" TO "B":PRINT "done"`.
- **Without a disk system** (a diskless MSX such as the VG-8020) `COPY` is
  `Illegal function call` (error 5).

### Errors

| situation | error |
|---|---|
| the source does not exist | 53 `File not found` |
| a wildcard source matches nothing | 53 `File not found` |
| copying a file onto itself | 5 `Illegal function call` |
| no `TO` part (`COPY "HI.TXT"`) | 5 `Illegal function call` — but 53 if the source does not exist either, because the source is looked up first |
| a wildcard source matches two or more files | 5 `Illegal function call` (see *Differences*) |
| the source or the destination is open (`OPEN`) | 64 `File still open` |
| a number instead of a name (`COPY 5 TO "B"`) | 13 `Type mismatch` |
| no disk in the drive | 70 `Disk offline` |

Not yet measured on the reference: a disk that fills up during the copy, a
write-protected disk with no file open, and device names (`CRT:`, `LPT:`,
`CAS:`) as source or destination.

## Example

On a disk holding `HI.TXT`, `TEST.BIN`, `PROG.BIN`, `PROG.BAS`, `PROG2.BAS`
and `PROG3.BAS`:

```
10 ON ERROR GOTO 90
20 COPY "HI.TXT" TO "HI2.TXT"
30 COPY "HI.TXT" TO "X?.TXT"
40 COPY "NONE.TXT" TO "N.TXT"
50 COPY "HI.TXT" TO "HI.TXT"
60 FILES
70 END
90 PRINT "Err";ERR;"in";ERL:RESUME NEXT
RUN
Err 53 in 40
Err 5 in 50
TEST    .BIN HI      .TXT PROG    .BIN
PROG    .BAS PROG2   .BAS PROG3   .BAS
HI2     .TXT XI      .TXT
```

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_copy.out`](../../scratchpad/kwdoc_copy.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**A wildcard source that matches two or more files is always error 5 here.**
On the CF-3300 the result is not consistent: copying `*.BAS` to a plain name
is error 5, `PROG*.BAS` to `Q*.BAS` over the disk's own files returns without
an error, and with two freshly written files, or inside an `ON ERROR`
program, the machine never comes back. Why those cases differ has not been
measured, and what the CF-3300 writes when it does return has not been read
back. Joost ruled on 2026-10-09: *"stay error 5 for now"*.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **`COPY` arrived on 2026-09-11** (D-COPY), after its behaviour on the
  CF-3300 was surveyed first (D-COPYVERB, 2026-09-07). Its test reads the
  copied file back off the disk image and compares the bytes, so a `COPY` that
  made the directory entry but wrote nothing could not pass.
- **It moved into the disk ROM** (D-DISKVERB3 on 2026-09-15, D-COPYLOCAL on
  2026-09-21), freeing main-ROM space; the behaviour did not change.
- **An open file used to be copied** (fixed 2026-09-28, D-COPYNAMEOPEN). The
  CF-3300 refuses with error 64 when the source or destination is open.
- **The error code could be lost** when a file was open (fixed 2026-09-28,
  D-ERRKEEP).
- **Wildcards were always error 5** (fixed 2026-09-28, D-COPYWILD). Measuring
  the CF-3300 showed one match copies, no match is 53, and — the surprise — a
  `?` in the destination is filled from the source even when the source is a
  plain name. zerobas had made a file literally named `H?.TXT`. On the same day
  an early claim that "two or more matches never complete" turned out to be
  partly our probe reading its own typed text; the corrected picture is the
  one under *Differences*.
- **`COPY` without `TO` on a missing file was 5, not 53** (fixed 2026-09-29,
  D-NOASTO): the CF-3300 looks the source up before it notices the missing
  `TO`.
- **The copy got today's date** (fixed 2026-10-01, D-COPYDATE); the CF-3300
  keeps the source's.

## Where it lives

- Main ROM: `ex_copy` in [basic/files.asm](../../basic/files.asm) hands the
  statement to the disk ROM through the `H_COPY` hook and turns its answer into
  a BASIC error.
- Disk ROM, [disk/kernel.asm](../../disk/kernel.asm): `hk_copy` reads the two
  names and checks for open files; `hkc_resolve` counts wildcard matches;
  `hkc_body` does the copy, sector by sector.
- The 2026-09-11 design notes are in
  [spec-basic-copy.md](../spec-basic-copy.md); where they disagree with this
  page, this page is current.

## Tests that cover it

- `make copy-acceptance` — plain, overwrite, large, blanks, string-variable
  and wildcard copies, each copy's bytes read back from the disk image.
- `make kwsweep` — the everyday row and the error rows (13, 53, 64).
- `make nodisk-acceptance` — error 5 on a diskless machine.
- `make kwram` — the RAM-usage comparison.
