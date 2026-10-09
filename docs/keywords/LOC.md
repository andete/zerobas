<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `LOC` — where a file channel is

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`LOC(n)` reports the position of open file channel `n`. On a random-access
file it is the number of the record last read with `GET` or written with
`PUT`; on a file being read sequentially it is simply the file's size, and does
not move as the file is read. It is a Disk BASIC function, so the reference is
the National CF-3300; zerobas gives the same numbers in every case we have
measured. Its companion is [`LOF`](LOF.md), the file's length.

## Syntax

```
LOC(<channel number>)
```

One argument: the channel number.

## Details

- **Random-access file** (`OPEN ... AS #n LEN=r`): 0 right after the `OPEN`,
  then the record number of the last `GET` or `PUT` — `GET #1,3` makes it 3,
  `GET #1,7` makes it 7, `PUT #1,4` makes it 4.
- **Each channel has its own**: with two random files open, each `LOC`
  follows its own channel's `GET`s and `PUT`s.
- **File open for input**: the file's size, the same before any read and
  after 5 or 10 bytes. On the 26-byte `HI.TXT` it is 26 throughout.
- **File open for output or append**: it moves in whole 256-byte records as
  data is written, and on an append channel it can differ from `LOF`: a 6-byte
  file opened for `APPEND` reads `LOF` 6 and `LOC` 0, and both read 256 after
  300 more bytes.

### Errors

| situation | error |
|---|---|
| the channel is not open (`LOC(1)` with nothing open) | 59 `File not OPEN` |
| a channel above `MAXFILES` (`LOC(16)`) | 52 `Bad file number` |
| a string (`LOC("A")`) | 13 `Type mismatch` |
| no disk system (the diskless VG-8020), channel not open | 59 `File not OPEN` |

The whole set of errors `LOC` raises on the CF-3300 for these cases is
{13, 52, 59}; zerobas raises the same set.

## Example

On the test disk, where `TEST.BIN` is 2048 bytes and `HI.TXT` 26:

```
10 OPEN "TEST.BIN" AS #1 LEN=128
20 PRINT LOC(1);
30 GET #1,3:PRINT LOC(1);
40 GET #1,7:PRINT LOC(1)
50 CLOSE
60 OPEN "HI.TXT" FOR INPUT AS #1
70 A$=INPUT$(5,#1):PRINT LOC(1)
80 CLOSE
90 ON ERROR GOTO 120
100 PRINT LOC(1)
110 END
120 PRINT "Error";ERR:RESUME NEXT
RUN
 0  3  7
 26
Error 59
```

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_loc.out`](../../scratchpad/kwdoc_loc.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **`LOC` was missing, and looked present** (shipped 2026-09-11, D-LOC).
  zerobas did not know the word, so `LOC(1)` read as an element of an array
  named `LOC`, which BASIC creates on first use — a program got 0 and no
  error. It had been deferred because the one observation on file
  (`LOC(1)` on `HI.TXT` reads 26 before and after a read) looked unclear.
  Measuring a random file showed the rule is exact there (D-LOCSEM,
  2026-09-07, [`loc_probe.py`](../../scratchpad/loc_probe.py)), and Joost had
  ruled on 2026-09-10 *"missing keywords obviously need to be implemented"*.
- **Per channel, not one global.** A cheaper build would have kept one
  record number for the whole machine, right for one open random file and
  wrong with two. The reference is right with two, so zerobas keeps a record
  number per channel, cleared on every random `OPEN`.
- **Output and append channels** (2026-10-06, S10.B): once files being
  written became the disk ROM's, `LOC` and `LOF` on them read as on the
  CF-3300; before, zerobas reported the size at `OPEN` for both
  ([`applof_run.out`](../../scratchpad/applof_run.out)).

## Where it lives

- `ev_ff_loc` in [basic/expr.asm](../../basic/expr.asm): a random channel
  reads its own record number; any other open channel falls through to
  `LOF`'s code.
- The per-channel record numbers (`FCH_RECNOS`) are written by `GET` and
  `PUT` in the random-file engine,
  [basic/randio-body.inc](../../basic/randio-body.inc).

## Related concepts

- [Files and devices](../concepts/files-and-devices.md) — numbered channels to the disk, the tape, the screen and the printer

## Tests that cover it

- `make loc-acceptance` — the sequential reading, `GET`s of records 3 and 7,
  a `PUT` of record 4, and two random channels at once, against the CF-3300.
- `make kwsweep` — the everyday row and the error rows for {13, 52, 59}.
- `make dout-acceptance` — `LOC` and `LOF` while writing and appending.
- `make nodisk-acceptance` — the diskless answer, error 59.
- `make kwram` — the RAM-usage comparison.
