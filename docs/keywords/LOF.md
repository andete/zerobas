<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `LOF` — the length of an open file

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`LOF(n)` returns the length in bytes of the file open on channel `n`. It is a
Disk BASIC function, so the reference is the National CF-3300; zerobas gives
the same length in every case we have measured. Its companion is
[`LOC`](LOC.md), the channel's position.

## Syntax

```
LOF(<channel number>)
```

One argument: the channel number.

## Details

- **A file open for input**: its size. The 26-byte `HI.TXT` reads 26.
- **A file just created for output**: 0.
- **A file written and closed**: everything that went into it. `PRINT #1,"AB"`
  then `CLOSE` gives a 5-byte file: `AB`, carriage return, line feed and one
  more byte, consistent with the end-of-file mark that closing a written file
  adds.
- **While a file is being written** (for output or append) the length moves
  in whole 256-byte records as data reaches the disk; on an append channel it
  can differ from `LOC` (see [`LOC`](LOC.md)).
- **A random-access file**: the size including records just written. After
  `PUT #1,1` on a file opened with `LEN=128`, `LOF(1)` reads 128 at once, even
  though the directory on the disk is only updated at `CLOSE`.
- **Large files are exact.** The result is a full-precision number, not a
  16-bit integer: after `PUT #1,300` with `LEN=256` it reads 76800, and
  `LOF(1)/7` prints `10971.428571429`.

### Errors

| situation | error |
|---|---|
| the channel is not open (`LOF(1)` with nothing open, `LOF(0)`) | 59 `File not OPEN` |
| a channel above `MAXFILES` (`LOF(16)`) | 52 `Bad file number` |
| a string (`LOF("A")`) | 13 `Type mismatch` |
| a device channel (`OPEN "CRT:" FOR OUTPUT AS #1`, then `LOF(1)`) | 5 `Illegal function call` |
| no disk system (the diskless VG-8020), channel not open | 59 `File not OPEN` |

The whole set of errors `LOF` raises on the CF-3300 for its enumerated cases
is {13, 52, 59}; zerobas raises the same set.

## Example

```
10 OPEN "HI.TXT" FOR INPUT AS #1
20 PRINT LOF(1):CLOSE
30 OPEN "N.TXT" FOR OUTPUT AS #1
40 PRINT LOF(1):PRINT #1,"AB":CLOSE
50 OPEN "N.TXT" FOR INPUT AS #1
60 PRINT LOF(1):CLOSE
70 ON ERROR GOTO 100
80 PRINT LOF(1)
90 END
100 PRINT "Error";ERR:RESUME NEXT
RUN
 26
 0
 5
Error 59
```

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_lof.out`](../../scratchpad/kwdoc_lof.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **A freshly created output file read −1** (fixed 2026-07-31, D-LOF). No
  path that creates a file wrote its size, so `LOF` returned whatever the
  previous file had left; the CF-3300 reads 0. Three create paths, not the one
  that was filed.
- **`LOF(0)` printed 0 instead of an error** (fixed 2026-07-31, D-BADFNUM).
  A rejected channel number raised nothing, so an armed `ON ERROR` never ran.
  Sweeping every channel-taking verb against every kind of bad channel number
  found 63 of the first 72 cases wrong
  ([spec](../spec-basic-badfnum-channel-class.md)).
- **`LOF` of a screen channel (`CRT:`) returned a number** (fixed 2026-08-26,
  D-EVFERR); both reference machines say error 5.
- **A 65280-byte file read −256** (fixed 2026-09-10, D-LOFU32). The length
  was handed back as a signed 16-bit integer, and anything past 65535 was cut
  short. Measuring the CF-3300 showed it returns the full size as a
  double-precision number; Joost had ruled *"do what the reference does"*.
- **Files being written** (2026-10-06, S10.B): once output and append
  channels became the disk ROM's, `LOF` on them moves in whole records as on
  the CF-3300; before, it read the size at `OPEN` throughout.

## Where it lives

- `ev_ff_lof` in [basic/expr.asm](../../basic/expr.asm): the channel checks
  (`fch_check`), then the channel's size as a double. `LOC` on a sequential
  channel joins it at `ev_ff_lof_checked`.

## Related concepts

- [Files and devices](../concepts/files-and-devices.md) — numbered channels to the disk, the tape, the screen and the printer

## Tests that cover it

- `make lof-acceptance` — `LOF` for every way a channel can be opened
  (input, output, append and random, on new and existing files), against the
  CF-3300.
- `make diskbasic-acceptance` — `EOF` and `LOF` on a read file.
- `make dout-acceptance` — `LOF` and `LOC` while writing and appending.
- `make putdir-acceptance` — `LOF` after a `PUT` before `CLOSE`.
- `make badfnum-acceptance` — the bad-channel-number errors.
- `make kwsweep` — the everyday row (26) and the error rows for {13, 52, 59}.
- `make kwram` — the RAM-usage comparison.
