<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `PUT` — write a record to a random-access file (and `PUT SPRITE`)

> **Status (2026-11-08):** `PUT` starts two statements: `PUT #`, documented
> here, and `PUT SPRITE`, documented on [`SPRITE`](SPRITE.md). One recorded
> difference for `PUT #`: the single record 4294967295 (below); one open
> item, a disk swapped before `CLOSE`. Record
> numbers follow the CF-3300 across the rest of its range since 2026-11-04.
> A `PUT` without a record number writes the next record, as on
> the CF-3300, since 2026-10-09.
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
- **A fractional record number is truncated**: 2.7 is record 2, 1.99 is
  record 1.
- **A negative record number counts back from 65536**: `PUT #1,-1` writes
  record 65535, `-2` record 65534, `-32767` record 32769. `-32768` and below
  are `Overflow`.
- **`LOC(1)` is the record number of the last `GET` or `PUT`**, and 0 straight
  after `OPEN`. It is never negative: after `PUT #1,-1` it is 65535.
- **Without a record number** `PUT` writes the record after the last one read
  or written on that channel (`LOC` + 1), so `PUT #1` in a loop writes records
  1, 2, 3, …

### Errors

| situation | error |
|---|---|
| the channel is not open, or `#0` | 59 `File not OPEN` |
| the channel is a disk file not opened for random access | 61 `Bad file mode` |
| the channel is the printer (`LPT:`) | 58 `Sequential I/O only` |
| a channel number above `MAXFILES` | 52 `Bad file number` |
| channel `#256` or `#-1` | 5 `Illegal function call` |
| record number 0 | 5 `Illegal function call` |
| record number −32768 or below, or 4294967296 or above | 6 `Overflow` |
| a string as the record number | 13 `Type mismatch` |
| the record would not fit on the disk | 66 `Disk full` |

All agree between the two machines, except the one case in *Differences*.

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

- **`PUT #1,4294967295#` succeeds on the CF-3300** and reports a file of
  4294967295 bytes, which no disk holds: its check of the free space wraps
  at that one value. zerobas says `Disk full`, as the CF-3300 does for every
  other record past the end of the disk (`PUT #1,1E9`). Measured on
  2026-11-04 ([`recwide_cf2.out`](../../scratchpad/recwide_cf2.out)).

## What we found, and how

- **Every `PUT` wrote its sector to the disk at once** (changed 2026-11-08,
  D-PUTCACHE). Logging the floppy controller's commands showed the CF-3300
  keeping the sector a record goes into in memory and writing it only when a
  record needs another sector, or at `CLOSE`: 20 records of 32 bytes are two
  sector writes there ([`fdcput_cf.out`](../../scratchpad/fdcput_cf.out)). zerobas
  read and rewrote the sector for every record. It now keeps the sector the
  same way.
- **A disk swapped between a `PUT` and its `CLOSE`** (found 2026-11-08, open).
  The CF-3300 writes the held record, its directory sector and its FAT onto
  the disk that is in the drive at `CLOSE`, so the NEW disk lists the file and
  reads the record back ([`diskswap_cf.out`](../../scratchpad/diskswap_cf.out)). zerobas
  now writes the held record there too, but it re-reads the new disk's
  directory instead of writing its own copy, so the new disk still says
  `File not found` ([`diskswap_zb_cache.out`](../../scratchpad/diskswap_zb_cache.out)).

- **Record numbers stopped at 65535** (fixed 2026-11-04, D-RECBIG, Joost:
  "Widen"). The CF-3300's record number is 32 bits: `PUT #1,65536` writes
  that record, `PUT #1,1E9` is `Disk full`, and 4294967296 is the first
  `Overflow`. zerobas kept it in 16 bits and said `Overflow` from 65536; it
  now keeps it in the channel's file control block as the CF-3300 does
  ([`recwide_cf.out`](../../scratchpad/recwide_cf.out),
  [`recwide_cf2.out`](../../scratchpad/recwide_cf2.out),
  [`recbig_gate_wide.out`](../../scratchpad/recbig_gate_wide.out)).
  Measuring it found that **a failed `GET` or `PUT` sets `LOC` to one below
  the record it asked for**: `PUT #1,1:PUT #1,1E9` leaves `LOC(1)` at
  999999999, and `PUT #1,5:GET #1,9` at 8. zerobas left `LOC` alone on a
  refused `GET`; it now follows the CF-3300.
- **`PUT #1,32768` was `Overflow`, and `PUT #1,-1` was read as an ordinary
  number** (fixed 2026-11-04, D-RECBIG). The CF-3300 writes record 32768,
  and reads −1 as record 65535. Both machines had agreed on 32768 on
  2026-09-10 ([`getput_run.out`](../../scratchpad/getput_run.out)); a change
  on 2026-10-07 made the record number a checked integer (−32768 to 32767),
  and no test held the old rows, so nothing noticed. The rule was then
  measured case by case on the CF-3300: truncated, 1 and up as is, −32767 to
  −1 counted back from 65536, −32768 and below `Overflow`, 0 `Illegal
  function call`. The same day **`LOC` showed record 65535 as −1**: it was
  read as a signed integer. It now prints 65535, as on the CF-3300. `make
  recbig-acceptance` covers both.

- **A `PUT #` whose disk had gone printed `load error` and went on** (fixed
  2026-10-11, with D-GETEJECT). The CF-3300 raises `Disk offline` (70) in the
  `PUT` line, so `ON ERROR` sees it; `GET #` and `PUT #` share their error exit
  here, and one change fixed both. `make geteject-acceptance` covers it.

- **Records 128 KB or more into a file were written to the wrong place**
  (fixed 2026-10-15, found while moving `PUT` into the disk ROM): the cluster
  walk used only the low byte of the sector number. Covered by
  `tests/test_rand_straddle.py`.
- **A `PUT` without a record number always wrote record 1** (fixed
  2026-10-09, D-RECAUTO), so a program writing its records in order kept only
  the last; the CF-3300 writes the record after the last one read or written.
  Found while writing these pages
  ([`getput_run.out`](../../scratchpad/getput_run.out)).
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

`ex_put` in [basic/field.asm](../../basic/field.asm) parses `#n` and checks
the channel; the record number and the record engine are the disk ROM's
(`hk_dget` in [disk/kernel.asm](../../disk/kernel.asm), since S10.D; the
record number's range is `rnd_parse` in [disk/fat.asm](../../disk/fat.asm)); the
directory entry is written by `CLOSE` (`hk_chclose`, same file). The sector a
`PUT` leaves unwritten is tracked by `RND_HSEC` and written by `rh_check` /
`rh_flush` ([disk/driver.asm](../../disk/driver.asm), [disk/fat.asm](../../disk/fat.asm)) before any other
sector is read.

## Related concepts

- [Files and devices](../concepts/files-and-devices.md) — numbered channels to the disk, the tape, the screen and the printer

## Tests that cover it

- `make kwsweep` — the everyday row (`puthash`) and the error rows.
- `make diskbasic-acceptance` — the random-file round trips.
- `make putdir-acceptance` — when the directory entry changes (at `CLOSE`).
- `tests/test_rand_straddle.py` (in `make unit-test`) — the record's last
  sector held until it is needed; sixteen `PUT`s into one sector and a `GET`
  of one of them with no disk reads or writes, then one write.
- `make recbig-acceptance` — the record number's range: fractions, 32768 to
  65535, negative numbers, −32768, 0, a string, and `LOC` afterwards.
