<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes run='SAVE "MY.BAS"' answers='SAVE "MY.TXT",A|NEW|LOAD "MY.TXT"|LIST|FILES "MY.*"' -->

# `SAVE` — write the program to a file

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error not yet proven. No known
> divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`SAVE "file"` writes the program in memory to a disk file in its tokenised
(compact, internal) form; `SAVE "file",A` writes it as plain text, the same
lines `LIST` shows. [`LOAD`](LOAD.md) reads either back. On disk the reference
is the National CF-3300; on cassette (`SAVE "CAS:name"`) it is the Philips
VG-8020, and there a `SAVE` always writes text — the tokenised tape save is
[`CSAVE`](CSAVE.md).

## Syntax

```
SAVE <file name>[,A]
```

The file name is a string expression and may carry a device (`"A:X.BAS"`,
`"CAS:X"`).

## Details

- **Tokenised by default, text with `,A`.** The tokenised file starts with the
  byte `&HFF`, then the program as it sits in memory. Saved from the same
  program, the file has the same length on both machines (68 bytes for the
  sweep's one-line program, read back with `LOF`).
- **A text save ends the program.** `SAVE "X",A` inside a program writes the
  file and returns to `Ok`; the next statement never runs. (It drives the same
  walk as `LIST`, which also ends a program.) A tokenised `SAVE` does not:
  the rest of the line, and the program, carry on.
- **On cassette every `SAVE` is a text save**, `,A` or not: the tape file has
  the ASCII type byte `&HEA`, on both reference machines. It ends a running
  program, as a disk text save does.
- **Anything after the name except `,A` is `Syntax error`**:
  `SAVE "J.BAS" 5`, `SAVE "X.BAS",B`, `SAVE "X.BAS",A,1`. For the first, the
  CF-3300 raises it before writing anything and creates no file. The same
  errors hold on cassette.
- **The directory entry is dated as on the CF-3300**: 1984-01-01, time 0, for
  `SAVE` and `SAVE ,A` alike (Joost, 2026-10-01: *"Stamp as 3300"*).
- **Disk faults are reported**: a full disk is `Disk full` (66), a
  write-protected one `Disk write protected` (68).
- **Open files are safe.** A `SAVE` with a data file open saves, and a
  `SAVE ,A` between two `PRINT #1`s leaves channel 1's file whole.
- **On a diskless machine** a name with no device goes to the cassette, and a
  drive name (`"A:X"`) is `Bad file name` (56).

### Errors

| situation | error |
|---|---|
| no name (`SAVE`) | 24 `Missing operand` |
| a number instead of a name (`SAVE 5`) | 13 `Type mismatch` |
| a drive that does not exist (`SAVE "Q:X.BAS"`) | 62 `Bad drive name` |
| anything after the name but `,A` | 2 `Syntax error` |
| the disk is full | 66 `Disk full` |
| the disk is write-protected | 68 `Disk write protected` |
| a drive name on a diskless machine | 56 `Bad file name` |

## Example

The program is typed, then saved both ways, wiped with `NEW`, and the text
copy loaded back:

```
10 PRINT "SAVED"
20 END
SAVE "MY.BAS"
SAVE "MY.TXT",A
NEW
LOAD "MY.TXT"
LIST
10 PRINT "SAVED"
20 END
FILES "MY.*"
MY      .BAS MY      .TXT
```

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_save.out`](../../scratchpad/kwdoc_save.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

**Every error** is not yet ticked: re-measured on 2026-10-07 every case of
`SAVE`'s enumerated error set ({2, 13, 24, 62} tokenised, {2} with `,A`)
agrees with the CF-3300
([`t6enum_b8_zb_1007.out`](../../scratchpad/t6enum_b8_zb_1007.out)), but the
keyword sweep does not yet carry a row for every code of every form.
**RAM usage** is not yet proven either.

Related, and not about `SAVE` alone: keys typed while a long disk write runs
are partly lost on both machines, more of them on zerobas (about 42 % kept
against the CF-3300's 77 % in one measurement). That is filed as a TIER 3 item
against the disk driver, D-FDCDI.

## What we found, and how

- **`SAVE ,A` beside an open output file emptied that file** (fixed
  2026-10-03, D-ASAVECHAN), and a `SAVE ,A` after a `PRINT #` to `CRT:` listed
  the program to the screen and left the file empty (fixed 2026-10-08,
  D-ASAVEDEV).
- **Write errors never reached BASIC** (fixed 2026-09-28, D-WPROTECT): one
  instruction in our disk driver cleared the error flag on every failed
  write, so a write-protected disk "saved". The same work found that a `SAVE`
  with any file open wrote nothing and said nothing (D-SAVEOPEN). A full disk
  printed `load error` until D-DISKFULL (2026-10-02).
- **`SAVE` ended the line**, and read a `:` after the name as junk (fixed
  2026-09-28, D-SAVECOLON).
- **A text save did not end the program** (fixed 2026-09-15, D-KWSAVEEND,
  on disk; 2026-10-07, D-NODISKVERBS, on cassette).
- **`SAVE "CAS:name"` wrote a tokenised tape** (fixed 2026-08-07,
  D-CASSAVE). Both references write text; decoding the recordings of both
  forms on both machines showed `SAVE "CAS:x"` and `SAVE "CAS:x",A` are one
  behaviour: [cassave-msx1-characterization.md](../cassave-msx1-characterization.md).
- **A mistyped option printed `load error`** (fixed 2026-10-06, D-SAVETAIL);
  both references raise a trappable `Syntax error`.

## Where it lives

- `do_save`, `sav_flag_a` (the `,A` parse, shared by disk and tape),
  `ascii_save` and `cas_ascii_save` in [basic/save.asm](../../basic/save.asm).
- A tokenised disk save is `hk_dpsave` in
  [disk/kernel.asm](../../disk/kernel.asm); since 2026-10-08 a disk text save
  is written by the disk ROM too.

## Related concepts

- [The cassette](../concepts/cassette.md) — files on tape, and how BASIC finds them
- [MSX-DOS](../concepts/msx-dos.md) — booting DOS, the BDOS, and the way back to BASIC
- [Program text](../concepts/program-text.md) — how a typed line becomes a program line

## Tests that cover it

- `make kwsweep` — a tokenised save read back with `LOF`, the text save ending
  the run, the error rows, and `SAVE` followed by more statements.
- `make savetail-acceptance` — the option errors, on disk and on cassette.
- `make diskascii-acceptance` and `make asavedev-acceptance` — the text file,
  byte for byte against the CF-3300.
- `make savedate-acceptance`, `make diskfull-acceptance`,
  `make wprotect-acceptance`, `make asavechan-acceptance` — the date stamp,
  a full disk, a protected disk, an open channel.
- `make cassave-acceptance` — what a cassette `SAVE` writes.
- `make nodiskverbs-acceptance` — the diskless machine.
- `make kwram` — the RAM-usage comparison.
