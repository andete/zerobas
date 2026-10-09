<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `GET` — read a record from a random-access file

> **Status (2026-10-09):** `GET` has one statement, `GET #`, documented here.
> One recorded difference, in everyday use: **without a record number zerobas
> reads record 1, where the CF-3300 reads the next record** (below, an open
> TIER 1 item).
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
- **A fractional record number is truncated**: 2.7 is record 2.
- **`LOC(1)` is the record number of the last `GET` or `PUT`** on the channel,
  and 0 straight after `OPEN`.
- **Without a record number** the CF-3300 reads the record after the last one
  read or written (`LOC` + 1); zerobas reads record 1 — see *Differences*.

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

**A `GET` without a record number** (D-RECAUTO, found 2026-10-09, open, a
TIER 1 item). The CF-3300 keeps a current record per channel and reads the
next one: after `PUT #1,1:PUT #1,2`, a bare `GET #1` asks for record 3 (here
past the end, so error 55). zerobas always reads record 1
([`getput_run.out`](../../scratchpad/getput_run.out)).

**A record number above 32767** (D-RECBIG, open, TIER 6) is `Overflow` here;
the CF-3300 accepts record numbers up to 65535, and reads −1 as 65535. See
[`PUT`](PUT.md).

## What we found, and how

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

`ex_get` in [basic/field.asm](../../basic/field.asm) parses the statement;
the record engine is [basic/randio-body.inc](../../basic/randio-body.inc), run
from the sub-ROM.

## Related concepts

- [Files and devices](../concepts/files-and-devices.md) — numbered channels to the disk, the tape, the screen and the printer

## Tests that cover it

- `make kwsweep` — the everyday row (`getkw`) and the error rows.
- `make diskbasic-acceptance` — the random-file round trips, including the
  two-record `FIELD` / `LSET` / `RSET` case.
