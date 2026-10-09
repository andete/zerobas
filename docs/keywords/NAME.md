<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `NAME` — rename a file on the disk

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`NAME "old" AS "new"` gives a file on the disk a new name. The file's bytes
stay where they are; only its directory entry changes, so it keeps its place
in the [`FILES`](FILES.md) listing. It is a Disk BASIC statement, so the
reference is the National CF-3300; zerobas renames the same way and raises the
same errors in every case we have measured.

## Syntax

```
NAME <old file name> AS <new file name>
```

Both names are string expressions. `AS` is written as plain text, not as a
keyword; both machines store it that way in the program.

## Details

- **The new name carries the old file's bytes**: a 5-byte file renamed and
  reopened under its new name still has `LOF` 5.
- **The old name is looked up first**, before the new name is even read. So
  if the old file is missing the answer is `File not found` whatever follows:
  `NAME "X.DAT" AS 5` and `NAME "NOPE.TXT"` (no `AS` at all) are both
  error 53.
- **Then the new name is checked**: if the old file exists, `NAME "HI.TXT"
  AS 5` is `Type mismatch` and `NAME "HI.TXT"` with no `AS` is `Syntax error`.
- **The new name must be free**: renaming onto an existing file is
  `File already exists` (error 65).
- **An open file cannot be renamed** (`File still open`, error 64); when
  error 65 would also apply, 64 is the one raised.

### Errors

| situation | error |
|---|---|
| the old file does not exist (with or without `AS`) | 53 `File not found` |
| the new name already exists | 65 `File already exists` |
| the old file is open | 64 `File still open` |
| a number as the old name (`NAME 5 AS "B"`) | 13 `Type mismatch` |
| a number as the new name, old file present | 13 `Type mismatch` |
| no `AS` part, old file present | 2 `Syntax error` |
| no disk in the drive | 70 `Disk offline` |
| no disk system (the diskless VG-8020) | 5 `Illegal function call` |

The whole set of errors `NAME` raises on the CF-3300 for its enumerated cases
is {13, 53, 64, 65}; zerobas raises the same set.

## Example

On the test disk, which holds `TEST.BIN`, `HI.TXT`, `PROG.BIN`, `PROG.BAS`,
`PROG2.BAS` and `PROG3.BAS`:

```
10 ON ERROR GOTO 80
20 NAME "HI.TXT" AS "HELLO.TXT"
30 NAME "NONE.TXT" AS "X.TXT"
40 NAME "PROG.BAS" AS "PROG2.BAS"
50 FILES
60 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
Error 53
Error 65
TEST    .BIN HELLO   .TXT PROG    .BIN
PROG    .BAS PROG2   .BAS PROG3   .BAS
```

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_name.out`](../../scratchpad/kwdoc_name.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **`NAME "HI.TXT" AS 5` was a `Syntax error`; the CF-3300 says `Type
  mismatch`** (fixed 2026-10-05, D-ASCIINUM), and the chase turned up a
  wider fault. Reading the stored program showed the `5` after
  `AS` is kept as the *character* "5", not as a number, on both machines
  alike (D-CRUNCHBYTES, 2026-09-09); the CF-3300's evaluator reads such a
  digit as a number and zerobas's did not. The same gap made
  `OPEN "F" AS 1` a `Syntax error` (D-ASCIIDIGIT), a real program's bug. Joost
  ruled on 2026-09-27 *"fix it"*.
- **The new name used to be read before the old file was looked up** (fixed
  2026-09-04, D-NAMEORD), so a missing old file with a bad new name gave the
  wrong error.
- **Renaming onto an existing name made two files of one name** (fixed
  2026-09-28, D-NAMEEXIST); the CF-3300 refuses with error 65, and zerobas
  gained that error's message (`File already exists`) with it.
- **An open file could be renamed under its channel** (fixed 2026-09-28,
  D-COPYNAMEOPEN); the CF-3300 says `File still open`.
- **`NAME "NOPE.TXT"` with no `AS` was a `Syntax error`** (fixed 2026-09-29,
  D-NOASTO); the CF-3300 looks the old file up first and says `File not
  found`.
- **`NAME` while another file was being written emptied that file** (fixed
  2026-09-23, D-ALIASWCELL), and **an empty drive printed `load error` and
  carried on** (fixed 2026-09-11, D-DISKERR).

## Where it lives

- Main ROM: `ex_name` in [basic/files.asm](../../basic/files.asm), through
  `verb_run` and the `H_NAME` hook.
- Disk ROM: `hk_name` in [disk/kernel.asm](../../disk/kernel.asm) looks the
  old file up, checks the open files and the new name, and rewrites the
  directory entry.

## Related concepts

- [Disk BASIC](../concepts/disk.md) — files on a 720 KB floppy, one drive

## Tests that cover it

- `make diskbasic-acceptance` — a rename compared with the CF-3300 by the disk
  image it leaves.
- `make kwsweep` — the everyday row (the renamed file's length read back
  under its new name) and the error rows for {13, 53, 64, 65}.
- `make namegate-acceptance` and `make nameord-acceptance` — the operand and
  ordering cases above.
- `make nodiskerr-acceptance` — error 70 on an empty drive.
- `make nodisk-acceptance` — error 5 on a diskless machine.
- `make kwram` — the RAM-usage comparison.
