<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `GET` — read a record from a random-access file

> **Status (2026-11-04):** `GET` has one statement, `GET #`, documented here.
> No recorded difference: record numbers follow the CF-3300 across its whole
> range, 1 to 4294967295, since 2026-11-04. A `GET` without a record number reads the next record, as on
> the CF-3300, since 2026-10-09.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`GET #1,5` reads record 5 of the random-access file open as channel 1 into
that channel's record buffer, where the variables named by
[`FIELD`](FIELD.md) show it. It is the reading half of
[`PUT`](PUT.md). It is a Disk BASIC statement, so the reference is the
National CF-3300.

## Syntax

```
GET [#]<channel>[,<record number>]
```

The `#` may be left out. The file must have been opened for random access:
`OPEN "N.DAT" AS #1 LEN=16` (see [`OPEN`](OPEN.md)).

## Details

- **Records are numbered from 1.** The record length is the `LEN=` of the
  `OPEN` (1 to 256; 256 when `LEN=` is left out).
- **A record that starts inside the file is read**, even when it runs past
  the end. One that starts at or past the end is `Input past end` (error 55).
- **A fractional record number is truncated**: 2.7 is record 2, 1.99 is
  record 1.
- **A negative record number counts back from 65536**, as for
  [`PUT`](PUT.md): `GET #1,-2` reads record 65534. `-32768` and below are
  `Overflow`.
- **`LOC(1)` is the record number of the last `GET` or `PUT`** on the channel,
  and 0 straight after `OPEN`. It is never negative. A `GET` or `PUT` that
  fails leaves it one below the record it asked for: after `PUT #1,5`,
  `GET #1,9` is `Input past end` and `LOC(1)` is 8.
- **Without a record number** `GET` reads the record after the last one read
  or written on that channel (`LOC` + 1): the first bare `GET` after `OPEN`
  reads record 1. After a refused `GET` it asks for that same record again.

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
| the record starts at or past the end of the file | 55 `Input past end` |

All agree between the two machines. A disk read error during `GET` prints a
message without raising an error that `ON ERROR` could catch; that is part of
an open item (D-LOADERRRET).

## Example

```
10 ON ERROR GOTO 100
20 OPEN "N.DAT" AS #1 LEN=16
30 FIELD #1,10 AS N$,6 AS P$
40 LSET N$="ALICE":RSET P$="12"
50 PUT #1,1:CLOSE
60 OPEN "N.DAT" AS #1 LEN=16
70 FIELD #1,10 AS N$,6 AS P$
80 GET #1,1:PRINT "[";N$;"][";P$;"]"
90 GET #1,2
95 END
100 PRINT "Error";ERR:RESUME NEXT
RUN
[ALICE     ][    12]
Error 55
```

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_get.out`](../../scratchpad/kwdoc_get.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known for `GET #` since 2026-11-04, when record numbers of 65536 and up
started to work (*What we found*).

## What we found, and how

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
- **`GET #1,32768` was `Overflow`, and `GET #1,-32768` read record 32768**
  (fixed 2026-11-04, D-RECBIG). `GET` and `PUT` read the record number the
  same way, on both machines, and the fix was one change for both: see
  [`PUT`](PUT.md). On the CF-3300, in a file of 65535 records, `GET #1,40000`
  reads record 40000, `GET #1,-2` record 65534 and `GET #1,-32768` is
  `Overflow`; zerobas now agrees. `make recbig-acceptance` covers it.

- **A `GET` whose disk had gone answered a blank record** (fixed 2026-10-11,
  D-GETEJECT). With the disk taken out between `OPEN` and `GET`, the CF-3300
  raises `Disk offline` (70) in the `GET` line, so `ON ERROR` sees it. zerobas
  raised nothing and filled the record with spaces: the failed read was taken
  for the end of the file
  ([`geteject_run.out`](../../scratchpad/geteject_run.out)). Now it raises 70
  too. `make geteject-acceptance` covers it.

- **Records 128 KB or more into a file came from the wrong place** (fixed
  2026-10-15, found while moving `GET` into the disk ROM): the cluster walk
  used only the low byte of the sector number. On the same day: **a `GET` past
  the end of a file over 64 KB returned a blank record** instead of `Input past
  end`. Both are covered by `tests/test_rand_straddle.py`.
- **A `GET` without a record number always read record 1** (fixed
  2026-10-09, D-RECAUTO): the CF-3300 reads the record after the last one read
  or written. Found while writing these pages
  ([`getput_run.out`](../../scratchpad/getput_run.out)).
- **`GET` on a channel that was not open was a `Syntax error`** (fixed
  2026-07-31, D-NOTOPEN2); it is now 59, 61 or 58 as on the CF-3300.
- **Record 0 only printed a message** (fixed 2026-09-09, D-GETREC); it is now
  error 5. **Reading past the end returned a blank record** (fixed the same
  day, D-GETEOF): the CF-3300 says `Input past end` when the record *starts*
  at or past the end, and pads one that only *ends* past it.
- **Any record length now works** (2026-09-06, D-RECLENFIX): only powers of
  two were accepted before, and a record could not cross a sector.
- **With two random files open, `GET` on one could read the other's record**
  (fixed 2026-09-07, D-FIELDFIX).
- **`LOC` arrived on 2026-09-11** (D-LOC), reporting the last record as on the
  CF-3300.

## Where it lives

`ex_get` in [basic/field.asm](../../basic/field.asm) parses `#n` and checks
the channel; the record number and the record engine are the disk ROM's
(`hk_dget` in [disk/kernel.asm](../../disk/kernel.asm), since S10.D; the
record number's range is `rnd_parse` in [disk/fat.asm](../../disk/fat.asm)), as on
the CF-3300, whose disk ROM parses the record number itself. The record is
read into the channel's own block, at `VARPTR(#n)+9`, where `FIELD`'s
variables point (D-FLDDESC, 2026-10-17).

## Related concepts

- [Files and devices](../concepts/files-and-devices.md) — numbered channels to the disk, the tape, the screen and the printer

## Tests that cover it

- `make kwsweep` — the everyday row (`getkw`) and the error rows.
- `make diskbasic-acceptance` — the random-file round trips, including the
  two-record `FIELD` / `LSET` / `RSET` case.
- `make recbig-acceptance` — the record number's range, for `GET` and `PUT`.
