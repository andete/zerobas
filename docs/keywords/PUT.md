<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `PUT` — write a record to a random-access file (and `PUT SPRITE`)

> **Status (2026-10-09):** `PUT` starts two statements: `PUT #`, documented
> here, and `PUT SPRITE`, documented on [`SPRITE`](SPRITE.md). Two recorded
> differences for `PUT #`: **without a record number zerobas writes record 1,
> where the CF-3300 writes the next record** (an open TIER 1 item), and record
> numbers above 32767 (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`PUT #1,5` writes the record buffer of channel 1 — filled through the
variables named by [`FIELD`](FIELD.md), using [`LSET`](LSET.md) and
[`RSET`](RSET.md) — to record 5 of the random-access file. It is the writing
half of [`GET`](GET.md). It is a Disk BASIC statement, so the reference is the
National CF-3300.

`PUT SPRITE` places a sprite on the screen; it shares only the first word —
see [`SPRITE`](SPRITE.md), section *`PUT SPRITE` — the position*.

## Syntax

```
PUT [#]<channel>[,<record number>]
```

The `#` may be left out. The file must have been opened for random access:
`OPEN "N.DAT" AS #1 LEN=16` (see [`OPEN`](OPEN.md)).

## Details

- **Records are numbered from 1.** The record length is the `LEN=` of the
  `OPEN` (1 to 256; 256 when `LEN=` is left out).
- **Writing past the end makes the file longer**: on a new file at `LEN=16`,
  `PUT #1,3` makes `LOF(1)` 48. What the skipped records contain is not
  measured.
- **`LOF(1)` follows at once**: it is the larger of the old size and record ×
  length. Writing record 1 into a longer file leaves the size alone.
- **The directory entry is written at `CLOSE`**, not at each `PUT` — so
  until `CLOSE` (or `END`, or `RUN`, which close every file) the disk's
  directory still shows the old size. This is how the CF-3300 does it, and
  Joost ruled on 2026-09-27 to follow it (*"faithful: stamp at CLOSE"*),
  knowingly giving up the safety of a directory that is always up to date.
- **A fractional record number is truncated**: 2.7 is record 2.
- **`LOC(1)` is the record number of the last `GET` or `PUT`**, and 0 straight
  after `OPEN`.

### Errors

| situation | error |
|---|---|
| the channel is not open, or `#0` | 59 `File not OPEN` |
| the channel is a disk file not opened for random access | 61 `Bad file mode` |
| the channel is the printer (`LPT:`) | 58 `Sequential I/O only` |
| a channel number above `MAXFILES` | 52 `Bad file number` |
| channel `#256` or `#-1` | 5 `Illegal function call` |
| record number 0 | 5 `Illegal function call` |
| a string as the record number | 13 `Type mismatch` |

All agree between the two machines, except record numbers above 32767
(*Differences*).

## Example

```
10 ON ERROR GOTO 100
20 OPEN "N.DAT" AS #1 LEN=16
30 FIELD #1,10 AS N$,6 AS P$
40 LSET N$="ALICE":RSET P$="12"
50 PUT #1,1
60 LSET N$="BOB":RSET P$="345"
70 PUT #1,3
80 PRINT LOF(1);LOC(1)
90 PUT #1,0
95 CLOSE:END
100 PRINT "Error";ERR:RESUME NEXT
RUN
 48  3
Error 5
```

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_put.out`](../../scratchpad/kwdoc_put.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

All measured in [`getput_run.out`](../../scratchpad/getput_run.out):

- **A `PUT` without a record number** (D-RECAUTO, found 2026-10-09, open, a
  TIER 1 item). The CF-3300 writes the record after the last one read or
  written, so three bare `PUT #1` make records 1, 2 and 3 (`LOF` 24, `LOC` 3
  at `LEN=8`). zerobas writes record 1 each time (`LOF` 8, `LOC` 1) — a
  program that writes its records in order this way loses all but the last.
- **Record numbers above 32767** (D-RECBIG, open, TIER 6). The CF-3300 takes
  the record number like an address, 0 to 65535: `PUT #1,32768` at `LEN=1`
  writes record 32768, and `PUT #1,-1` writes record 65535. zerobas says
  `Overflow` for 32768 — a regression: both agreed on 2026-09-10, and a
  change on 2026-10-07 made the record number a checked integer. For −1
  zerobas gave no reading within a minute; that case is still to be measured.

## What we found, and how

- **`PUT` on a channel that was not open was a `Syntax error`** (fixed
  2026-07-31, D-NOTOPEN2); it is now 59, 61 or 58 as on the CF-3300.
- **With two random files open, `PUT` wrote one channel's record into the
  other's file** (fixed 2026-09-07, D-FIELDFIX).
- **Writing far past the end gave a negative file size** (fixed 2026-09-09,
  D-PUTEXTEND / D-PUTDOMAIN): `PUT #1,255` made `LOF` −256. Joost ruled on
  2026-09-10 to *"do what the reference does"*, and sizes became 32-bit
  (D-LOFU32, D-PUTU32): `PUT #1,300` at the default length gives 76800 on
  both machines.
- **The directory entry was rewritten at every `PUT`** (changed 2026-10-08,
  D-PUTDIR): now only at `CLOSE`, as on the CF-3300, per the ruling above. A
  `PUT` without `CLOSE` now leaves the disk exactly as the reference does.

## Where it lives

`ex_put` in [basic/field.asm](../../basic/field.asm) parses the statement; the
record engine is [basic/randio-body.inc](../../basic/randio-body.inc), run from
the sub-ROM; the directory entry is written by `CLOSE`
([basic/files.asm](../../basic/files.asm)).

## Tests that cover it

- `make kwsweep` — the everyday row (`puthash`) and the error rows.
- `make diskbasic-acceptance` — the random-file round trips.
- `make putdir-acceptance` — when the directory entry changes (at `CLOSE`).
