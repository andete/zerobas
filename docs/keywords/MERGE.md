<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes answers='LIST|MERGE "NONE.BAS"' -->

# `MERGE` — add the lines of a text file to the program

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`MERGE "file"` reads a program saved as text (`SAVE "file",A`, or written line
by line with `PRINT #`) and adds its lines to the program in memory, as if
they had been typed: a new line number is inserted, an existing one is
replaced, and every other line stays. That is the difference from
[`LOAD`](LOAD.md), which throws the old program away. On disk the reference
is the National CF-3300; on cassette (`MERGE "CAS:name"`) the Philips VG-8020.

## Syntax

```
MERGE <file name>
```

The file name is a string expression (`MERGE A$` works) and may carry a
device (`"A:X.BAS"`, `"CAS:X"`).

## Details

- **`MERGE` ends the program.** Inside a running program the merge happens
  and the machine returns to `Ok`; the statements after `MERGE` do not run,
  on the same line or the next. Typed as a command followed by `:` and more
  statements, those do not run either.
- **The file must be text.** On zerobas a tokenised program file (a plain
  `SAVE`) is refused with `Syntax error` and nothing is merged; what the
  CF-3300 does with one has not been measured.
- **The merged lines land exactly as typed lines would**: they go through the
  same tokeniser, and on both machines `LIST` shows the same result.
- **On cassette** the tape is searched by name, and only ASCII files count; a
  tokenised or binary file of the same name is stepped over silently. The
  search prints `Skip :` and `Found:` rows, as `LOAD "CAS:"` does. Ctrl-STOP
  during the search is `Device I/O error` (19).
- **On a diskless machine** a name with no device reads the cassette, and a
  drive name (`"A:X"`) is `Bad file name` (56).

### Errors

| situation | error |
|---|---|
| the file does not exist | 53 `File not found` |
| a number instead of a name (`MERGE 5`) | 13 `Type mismatch` |
| no name at all (`MERGE`) | 24 `Missing operand` |
| a tape search broken with Ctrl-STOP | 19 `Device I/O error` |
| a drive name on a diskless machine | 56 `Bad file name` |

The enumerated set is {13, 24, 53}, the same on both machines.

## Example

The program writes a one-line text file and merges it: line 50 is replaced,
and the `PRINT "never"` after the `MERGE` does not run. `LIST` and a merge of
a missing file are then typed as commands:

```
10 OPEN "M.BAS" FOR OUTPUT AS #1
20 PRINT #1,"50 PRINT 2"
30 CLOSE #1:MERGE "M.BAS"
40 PRINT "never"
50 PRINT 1
RUN
LIST
10 OPEN "M.BAS" FOR OUTPUT AS #1
20 PRINT #1,"50 PRINT 2"
30 CLOSE #1:MERGE "M.BAS"
40 PRINT "never"
50 PRINT 2
MERGE "NONE.BAS"
File not found
```

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_merge.out`](../../scratchpad/kwdoc_merge.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**. Not measured on the reference:
`MERGE` of a tokenised program file.

## What we found, and how

- **On cassette, MERGE stopped at a tokenised file of the right name** (fixed
  2026-10-08, D-CASTYPE): the VG-8020 steps over it and searches on.
- **Ctrl-STOP during a tape MERGE raised error 255** (fixed 2026-10-08,
  D-CASBRK): a stale disk error code, on a machine with no disk. The VG-8020
  raises 19.
- **The file name had to be a literal** (fixed 2026-09-07, D-MERGEXPR).
  `MERGE A$` was `Syntax error`, and so were `MERGE 5` and a bare `MERGE`,
  where the CF-3300 answers 53, 13 and 24. Found by reading the code: the
  other file verbs had been converted on 2026-08-21 and `MERGE` was missed.
- **`MERGE` did not end the program** (fixed 2026-09-12, D-MERGERET). The merge
  itself was always right; the statements after it ran on, so
  `20 MERGE "N.BAS" / 30 POKE ...` poked here and not on the CF-3300. The
  same check found the identical fault in `LOAD`.
- **A missing file printed `load error` and the program ran on** (fixed
  2026-08-20, D-LOADERR-FIX); both references raise 53 and stop.

## Where it lives

- `ex_merge` in [basic/files.asm](../../basic/files.asm): the name, the device,
  and the end of the program. A disk file is opened by the disk ROM
  (`dsk_aopen`) and its bytes are read through it one at a time
  (`dsk_ascii_drive`); each line is tokenised and stored in main, as on the
  CF-3300, where `MERGE` and an ASCII `LOAD` are one mechanism.
- `merge_cas`, in the same file, is the cassette arm.

## Tests that cover it

- `make kwsweep` — `MERGE` of a file written with `PRINT #` ending the run,
  and the error rows.
- `make diskascii-acceptance` — `MERGE` against the CF-3300: a program built
  with `PRINT #`, merged, run.
- `make castail-acceptance` — the tape search rows for `MERGE "CAS:"`.
- `make castype-acceptance` and `make casbrk-acceptance` — the tape type
  filter and Ctrl-STOP.
- `make nodiskverbs-acceptance` — the diskless machine.
- `make kwram` — the RAM-usage comparison.
