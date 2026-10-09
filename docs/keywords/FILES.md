<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `FILES` — list the files on the disk

> **Status (2026-10-09):** level 0 since this page found a happy-path
> difference — where the cursor stands after the listing (below), an open
> TIER 1 item · reasonable time ✓ · common errors ✓ · RAM usage not yet
> proven · every error ✓. Until 2026-10-09 the tier sheet read level 3.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`FILES` prints the names of the files on the disk; `FILES "pattern"` prints
only the names that match, with `?` and `*` as wildcards. It is a Disk BASIC
statement, so the reference is the National CF-3300; zerobas lists the same
names in the same order and layout, and raises the same errors, in every case
we have measured. [`LFILES`](LFILES.md) is the same listing sent to the
printer.

## Syntax

```
FILES [<file name pattern>]
```

The pattern is a string expression and may carry a drive (`"A:*.BAS"`).

## Details

- **Each entry is printed as `NAME    .EXT`** — the name padded to eight
  characters, a dot, the extension — followed by a space. At `WIDTH 40` that
  makes three entries per row.
- **Entries come in directory order**, not sorted.
- **Wildcards** work as in file names: `FILES "*.BAS"` lists `PROG.BAS`,
  `PROG2.BAS` and `PROG3.BAS` on the test disk, and `FILES "PROG*.*"` adds
  `PROG.BIN`.
- **The cursor stays after the last entry**, on its row; the listing does
  not end with a new line of its own.
- **Nothing matches** — a pattern that finds no file, or a bare `FILES` on an
  empty disk — is `File not found` (error 53).

### Errors

| situation | error |
|---|---|
| no file matches the pattern | 53 `File not found` |
| an empty disk (bare `FILES`) | 53 `File not found` |
| a drive past `B:` (`FILES "Q:*.*"`) | 62 `Bad drive name` |
| a number instead of a pattern (`FILES 5`) | 13 `Type mismatch` |
| junk after the statement (`FILES,`) | 2 `Syntax error` |
| no disk in the drive | 70 `Disk offline` |
| no disk system (the diskless VG-8020) | 5 `Illegal function call` |

The whole set of errors `FILES` raises on the CF-3300 for its two forms is
{2, 13} for the bare form and {53, 62} with a pattern; zerobas raises the
same sets.

## Example

On the test disk, which holds `TEST.BIN`, `HI.TXT`, `PROG.BIN`, `PROG.BAS`,
`PROG2.BAS` and `PROG3.BAS`:

```
10 FILES:PRINT
20 FILES "*.BAS":PRINT
30 ON ERROR GOTO 60
40 FILES "NONE.*"
50 END
60 PRINT "Error";ERR:RESUME NEXT
RUN
TEST    .BIN HI      .TXT PROG    .BIN
PROG    .BAS PROG2   .BAS PROG3   .BAS
PROG    .BAS PROG2   .BAS PROG3   .BAS
Error 53
```

The `PRINT` after each `FILES` ends the listing's last row, which `FILES`
leaves open.

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_files.out`](../../scratchpad/kwdoc_files.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**Where the cursor stands after the listing.** When the last row of the
listing is exactly full (three names at width 40, two at width 37), the
CF-3300 moves to a new line and zerobas does not, so a `PRINT` straight after
`FILES` continues that row here. With a partly filled last row both machines
leave the cursor on it. Filed as D-FILESNL (2026-10-09,
[`filesnl_run.out`](../../scratchpad/filesnl_run.out)); `FILES:PRINT`, as in
the example above, looks the same on both.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **A pattern that matched nothing printed nothing** (fixed 2026-08-06,
  D-LFILES). The CF-3300 says `File not found`. It was found by a test written
  for `LFILES`, which shares the directory walk with `FILES`.
- **An empty disk printed nothing too** (fixed 2026-08-07, D-DSKMSG). The
  CF-3300 treats an empty directory the same as a pattern with no match.
  Measuring it needed a second, empty test disk — and a control that lists a
  file saved to it, because "printed nothing" is also what a dead disk prints.
- **On a diskless machine `FILES` ran and printed `load error`** (fixed
  2026-09-03, D-CHANHOOK); the VG-8020 answers error 5, and so does zerobas
  now.
- **An empty drive printed `load error` and carried on** (fixed 2026-09-11,
  D-DISKERR); the CF-3300 raises `Disk offline`, trappable, and stops.
- **The listing ended one character and one row out of place** (fixed
  2026-09-12, D-DFEND). zerobas ended with a new line and put the separating
  space before each entry rather than after it. Row by row the screen looked
  identical; only where the cursor came to rest differed, and a test reading
  `POS(0)` after `FILES` was what told them apart.
- **A drive letter past `B:` was not refused** (fixed 2026-09-28,
  D-DRVNAME): the file-name parser printed an error and let the statement
  carry on with drive A. It is now `Bad drive name`, as on the CF-3300, and
  `FILES "Q:*.*"` is one of the rows that agrees since.

## Where it lives

- Main ROM: `ex_files` in [basic/files.asm](../../basic/files.asm), through
  the shared `verb_run` prologue and the `H_FILE` hook.
- Disk ROM, [disk/kernel.asm](../../disk/kernel.asm): `hk_files` and
  `hkf_body` walk the directory; `df_emit` prints an entry and `df_end` ends
  the walk, for both `FILES` and `LFILES`.

## Tests that cover it

- `make diskbasic-acceptance` — the plain and the wildcard listing, compared
  with the CF-3300's screen.
- `make kwsweep` — the bare listing, the pattern listing and the error rows
  for {2, 13, 53, 62}.
- `make lptverb-acceptance` — `File not found` for no match and for an empty
  disk, rows it shares with `LFILES`.
- `make nodiskerr-acceptance` — error 70 on an empty drive.
- `make nodisk-acceptance` — error 5 on a diskless machine.
- `make kwram` — the RAM-usage comparison.
