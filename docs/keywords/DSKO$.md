<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `DSKO$` — write a raw disk sector

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`DSKO$ d,s` writes the disk system's sector buffer to sector `s` of drive
`d`. The buffer is the one [`DSKI$`](DSKI$.md) reads into, and its address is
the word at `&HF351`; the usual pattern is read a sector with `DSKI$`, change
bytes with `POKE`, write it back with `DSKO$`. It writes below the file
system, so it can damage a disk. It is a Disk BASIC statement: the reference
is the National CF-3300.

## Syntax

```
DSKO$ <drive number>, <sector number>
```

Two arguments, always. `DSKO$` is a statement only: `A$=DSKO$(0,0)` is
`Syntax error`.

## Details

- **It writes whatever is in the buffer**, to the sector named;
  `A$=DSKI$(0,0):DSKO$ 0,0` runs without an error on both machines.
- **The change is on the disk at once.** Writing a changed root-directory
  sector renames a file as far as `FILES` is concerned — the example does
  exactly that.
- **The drive is checked as for `DSKI$`**: drive 0 is the one drive, and a
  drive that does not exist (5 was measured) is `Bad drive name` (error 62).
- **The sector number is not checked against the disk's size**:
  `DSKO$ 0,9999` raises no error on the CF-3300, and none here.
- **A string argument** (`DSKO$ "A",0`) is `Type mismatch` (error 13);
  **one argument** (`DSKO$ 0`) is `Syntax error` (error 2).
- **No disk in the drive** is `Disk offline` (error 70), trappable.
- **Without a disk system** (the diskless VG-8020) `DSKO$` is `Illegal
  function call` (error 5) — even `DSKO$ 0`, because the word is refused
  before its arguments are read.

| you write | you get |
|---|---|
| `DSKO$ 0,7` | the buffer is written to sector 7 |
| `DSKO$ 5,0` | error 62, `Bad drive name` |
| `DSKO$ "A",0` | error 13, `Type mismatch` |
| `DSKO$ 0` | error 2, `Syntax error` |
| `DSKO$ 0,0` with no disk | error 70, `Disk offline` |

The whole set of errors `DSKO$` raises on the CF-3300 for these cases is
{2, 13, 62}; zerobas raises the same set.

## Example

This changes the first letter of the first directory entry, so `TEST.BIN`
is listed as `XEST.BIN` afterwards. The other files are untouched.

```
10 A$=DSKI$(0,7)
20 B=PEEK(&HF351)+256*PEEK(&HF352)
30 POKE B,ASC("X")
40 DSKO$ 0,7
50 FILES:PRINT
60 ON ERROR GOTO 90
70 DSKO$ 5,0
80 END
90 PRINT "Error";ERR:RESUME NEXT
RUN
XEST    .BIN HI      .TXT PROG    .BIN
PROG    .BAS PROG2   .BAS PROG3   .BAS
Error 62
```

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_dsko_s.out`](../../scratchpad/kwdoc_dsko_s.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **`DSKO$` arrived with `DSKI$` on 2026-09-11** (D-DSKIO), once the
  CF-3300 had shown where `DSKI$` puts its data; Joost had ruled the day
  before *"DSKI$ DSKO$ should also be implemented"*. Its test is a round
  trip: change the buffer, write, read a different sector, read the written
  one back — so a `DSKO$` that wrote nothing cannot pass.
- **An empty drive raised nothing** (fixed 2026-09-11, D-DISKERR). The
  emulated disk controller accepts a write with no disk in the drive, so the
  driver now checks the drive is ready before writing; the CF-3300 says
  `Disk offline`.
- **`DSKO$` listened on the wrong hook address** (fixed 2026-09-15,
  D-DSKOHOOK). zerobas's BASIC and its disk ROM used the same wrong address,
  so they agreed with each other and nothing failed; the CF-3300's disk ROM
  answers on a different cell, which un-claiming each cell on the reference
  revealed.
- **`DSKO$` with a file open damaged that file** (fixed 2026-09-23,
  D-ALIASWCELL). It shared the open file's sector buffer; the raw buffer is
  now separate, as on the CF-3300.

## Where it lives

- Main ROM: `ex_dsko` and the shared parse `dsk_core` in
  [basic/str-engine.asm](../../basic/str-engine.asm).
- The sector write itself is `tnt_dsko` in
  [sub/dirverb.asm](../../sub/dirverb.asm).
- Design and measurements: [spec-basic-dskio.md](../spec-basic-dskio.md).

## Tests that cover it

- `make dskio-acceptance` — the write round trip, with `XEST    BIN` read
  back from the disk image, and `DSKO$ 0` as error 2.
- `make kwsweep` — the round-trip row (88, the code of `X`) and the error
  rows for {2, 13, 62}.
- `make nodiskerr-acceptance` — error 70 on an empty drive.
- `make nodisk-acceptance` — error 5 on a diskless machine.
- `make kwram` — the RAM-usage comparison.
