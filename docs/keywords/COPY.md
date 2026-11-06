<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `COPY` — copy a file on the disk

> **Status (2026-11-06):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓.
> No recorded difference since 2026-11-06 (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`COPY "source" TO "destination"` makes a byte-for-byte copy of a file on the
disk, under a new name. It is a Disk BASIC statement: the reference is the
National CF-3300. zerobas copies the same bytes, gives the copy the same name
and date, and raises the same errors in every case we have measured,
wildcards that match several files included.

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
- **A wildcard source copies every file it matches**, one after another in
  the order of the disk's directory: `COPY "*.BIN" TO "*.BAK"` makes
  `TEST.BAK` and `PROG.BAK`. Each destination name is built from the source's:
  a fixed character stays, `?` takes the source's character at that place and
  `*` the rest of the name or extension. A `?` in the source also matches a
  blank place, so `PROG?.BAS` finds `PROG.BAS` too.
- **A plain destination is written once per match**, so after
  `COPY "*.BAS" TO "Z.TXT"` it holds the last file copied.
- **The directory is read as it changes.** A copy that the pattern also
  matches is met again later, and copying it onto itself is
  `Illegal function call` (error 5) — after every real copy is made:
  `COPY "*.BAS" TO "Z.BAS"` copies three files into `Z.BAS` and then stops
  with error 5. If the copy lands in an earlier free place in the directory
  (after a `KILL`), it is not met again and there is no error.
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
| a wildcard copy meets a file it has just made, whose name the source matches | 5 `Illegal function call`, after the other copies |
| the source or the destination is open (`OPEN`), under the same spelling | 64 `File still open` |
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

None recorded. The one that stood until 2026-11-06 is under *What we found*.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **A wildcard that matched several files was always error 5** (fixed
  2026-11-06, D-COPYALL). It had been left that way on purpose, because the
  CF-3300 seemed inconsistent: some cases returned, some never did. A careful
  measurement of 30 cases showed it was consistent all along. It copies every
  match, and the cases that "never came back" had simply not finished when our
  probe looked, 8 seconds after `RUN`. The error 5 it sometimes gives comes at
  the end, when the copying meets its own new file. Joost then ruled: *"copy
  every match like the reference"*. zerobas now gives the same files and the
  same messages in 28 of the 29 cases; the 29th differs only in how the
  screen scrolled
  ([`copymulti_probe.py`](../../scratchpad/copymulti_probe.py),
  [`copymulti_run1.out`](../../scratchpad/copymulti_run1.out),
  [`copyall_zb.out`](../../scratchpad/copyall_zb.out),
  [`copyall_cmp.out`](../../scratchpad/copyall_cmp.out)).

- **An open file was matched in any case** (fixed 2026-10-28; Joost ruled on
  2026-10-27 for an exact match that costs no more memory than the reference).
  The CF-3300 checks whether a file is open by the name as it was typed, upper
  and lower case distinct, while its disk treats both spellings as one file:
  with `TS.DAT` open, `COPY "ts.dat" TO "VV.DAT"` copies it there and was refused
  here; it now copies it here too. `COPY "a.txt" TO "A.TXT"` is still a copy
  onto itself (error 5): that check ignores case. The disk itself is upper case on both machines
  ([`fcbcase2_run.out`](../../scratchpad/fcbcase2_run.out),
  [`fcbcase_run.out`](../../scratchpad/fcbcase_run.out)).
- **The clock stopped while the disk worked** (fixed 2026-10-10, D-HOOKDI):
  `TIME` stopped during a `COPY` here; now it runs for 16 % of it, against
  37 % on the CF-3300. The disk ROM's code ran with interrupts off, so keys typed meanwhile
  were lost too. The CF-3300 switches them off only while it moves each
  sector, and since 2026-10-11 so does zerobas (D-FDCDI)
  ([readings](../../scratchpad/verbclock_copy.out)).

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
  partly our probe reading its own typed text; the whole picture came on
  2026-11-06 (the first entry above).
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
  names and checks for open files; `hkc_resolve` walks the directory and copies every wildcard match;
  `hkc_body` does the copy, sector by sector.
- The 2026-09-11 design notes are in
  [spec-basic-copy.md](../spec-basic-copy.md); where they disagree with this
  page, this page is current.

## Related concepts

- [ROM layout](../concepts/rom-layout.md) — how zerobas is put together

## Tests that cover it

- `make copy-acceptance` — plain, overwrite, large, blanks, string-variable
  and wildcard copies, several matches included, each copy's bytes read back
  from the disk image.
- `make kwsweep` — the everyday row and the error rows (13, 53, 64).
- `make nodisk-acceptance` — error 5 on a diskless machine.
- `make kwram` — the RAM-usage comparison.
