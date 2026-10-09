<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `DSKI$` — read a raw disk sector

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. Two recorded
> differences: a sector number past the end of the disk, and drive 2 (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`DSKI$(d,s)` reads sector `s` of drive `d` into the disk system's sector
buffer. Despite the `$`, **its value is the empty string**: the data is not
returned, it is left in the buffer, whose address is the word at `&HF351`.
A program reads the bytes with `PEEK`. Its partner [`DSKO$`](DSKO$.md) writes
that buffer back to a sector. It is a Disk BASIC function, so the reference is
the National CF-3300.

## Syntax

```
DSKI$(<drive number>, <sector number>)
```

Two arguments, always. `DSKI$` is a function only: `DSKI$ 0,0` written as a
statement is `Syntax error`.

## Details

- **The value is `""`.** `LEN(DSKI$(0,0))` is 0 on both machines.
- **The sector lands in the buffer named by `&HF351`.** Read its address
  with `PEEK(&HF351)+256*PEEK(&HF352)`. The address itself differs between
  the CF-3300 and zerobas by design; a program that reads it through
  `&HF351` works on both.
- **Sector 0 is the boot sector; sector 7 is the start of the root
  directory** on the 720 KB test disk, whose first entry is `TEST    BIN`.
- **Drives 0 and 1 both name the one drive.** A higher drive number (3, 5
  and 9 were measured) is `Bad drive name` (error 62).
- **The sector number is not checked against the disk's size** on the
  CF-3300: `DSKI$(0,9999)` raises no error there, and none here either. See
  *Differences* for a sector where zerobas does raise one.
- **A string argument** (`DSKI$("A",0)`) is `Type mismatch` (error 13);
  **one argument** (`DSKI$(0)`) is `Syntax error` (error 2).
- **No disk in the drive** is `Disk offline` (error 70), trappable.
- **Without a disk system** (the diskless VG-8020) `DSKI$` is `Illegal
  function call` (error 5), raised before its arguments are read.

| you write | you get |
|---|---|
| `A$=DSKI$(0,7)` | `A$` is `""`; the root directory's first sector is in the buffer |
| `A$=DSKI$(5,0)` | error 62, `Bad drive name` |
| `A$=DSKI$("A",0)` | error 13, `Type mismatch` |
| `A$=DSKI$(0)` | error 2, `Syntax error` |
| `A$=DSKI$(0,0)` with no disk | error 70, `Disk offline` |

The whole set of errors `DSKI$` raises on the CF-3300 for these cases is
{2, 13, 62}; zerobas raises the same set.

## Example

```
10 A$=DSKI$(0,7)
20 B=PEEK(&HF351)+256*PEEK(&HF352)
30 FOR I=0 TO 10:C=PEEK(B+I)
40 PRINT CHR$(C);:NEXT:PRINT
50 PRINT LEN(A$)
60 ON ERROR GOTO 90
70 A$=DSKI$(5,0)
80 END
90 PRINT "Error";ERR:RESUME NEXT
RUN
TEST    BIN
 0
Error 62
```

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_dski_s.out`](../../scratchpad/kwdoc_dski_s.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**A sector far past the end of the disk.** On a crafted copy of the test disk,
`A$=DSKI$(0,4000)` raised no error on the CF-3300 and `Disk I/O error`
(error 69) on zerobas
([`errkeep3_run2.out`](../../scratchpad/errkeep3_run2.out)). Filed as a
TIER 6 item (D-BADCLUSTER, 2026-09-29), together with a `LOAD` case on the
same crafted disk: neither shape arises on an intact disk.
`DSKI$(0,9999)` agrees (no error on either machine), so the rule behind the
difference is not yet known.

**Drive 2.** The CF-3300 has one disk drive but treats drive 2 (`B:`) as a
second, logical drive on the same mechanism: `DSKI$(2,0)` prints `Insert
diskette for drive B: and strike a key when ready` and waits. zerobas has
no logical drive B and answers `Bad drive name`
([`errtext6064_run.out`](../../scratchpad/errtext6064_run.out)). Joost ruled
on 2026-10-09: *"yeah, we need to have the prompt mechanism"* — zerobas will
get the same logical drive B: and its prompt (D-DSKIB, open; `DSKF(2)` is the
same case).

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **"It returns the sector as a string" was wrong** (2026-09-07, D-DSKI). The
  first measurement found the value is always `""`, which left the question
  of where the data goes. A watchpoint on the CF-3300's RAM answered it
  (2026-09-11): the sector lands in the buffer whose address is at `&HF351`.
  Joost had ruled on 2026-09-10 *"DSKI$ DSKO$ should also be implemented"*,
  and both shipped the next day (D-DSKIO, [spec](../spec-basic-dskio.md)).
- **An empty drive gave `Syntax error`** (fixed 2026-09-11, D-DISKERR); the
  CF-3300 says `Disk offline`, error 70, which zerobas now hosts in its disk
  ROM ([spec-basic-diskerr.md](../spec-basic-diskerr.md)).
- **`DSKI$` with a file open emptied that file** (fixed 2026-09-23,
  D-ALIASWCELL). The raw read borrowed the sector number and buffer of the
  open file. It now uses its own buffer, as the CF-3300 does, and puts the
  file's state back afterwards.

## Where it lives

- Main ROM: `str_dski` in [basic/strvar.asm](../../basic/strvar.asm) makes
  the empty-string value; the parse and the drive check are `dsk_core` in
  [basic/str-engine.asm](../../basic/str-engine.asm), shared with `DSKO$`.
- The sector read itself is `tnt_dski` in
  [sub/dirverb.asm](../../sub/dirverb.asm).
- Design and measurements: [spec-basic-dskio.md](../spec-basic-dskio.md).

## Tests that cover it

- `make dskio-acceptance` — `LEN` of the value, the boot sector and the root
  directory read back through `&HF351`, on a private copy of the test disk.
- `make kwsweep` — the everyday row (the first directory byte, 84 for `T`)
  and the error rows for {2, 13, 62}.
- `make nodiskerr-acceptance` — error 70 on an empty drive.
- `make nodisk-acceptance` — error 5 on a diskless machine.
- `make kwram` — the RAM-usage comparison.
