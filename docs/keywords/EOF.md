<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `EOF` — has a file been read to its end?

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`EOF(n)` is −1 (true) when nothing is left to read on channel `n`, and 0
while there is. It is how a program reads a file it did not write itself:
`IF EOF(1) THEN ... ELSE LINE INPUT #1,A$`. The channel must be open for
input (see [`OPEN`](OPEN.md)). Disk channels follow the National CF-3300;
the cassette channel too. zerobas answers the same values and raises the same
errors in every case we have measured.

## Syntax

```
EOF(<channel number>)
```

## Details

- **It looks at the next byte without reading it.** `EOF(1)` turns −1 as soon
  as the next byte is the end of the file or the Ctrl-Z end mark that
  [`CLOSE`](CLOSE.md) writes — even if more bytes follow the Ctrl-Z.
- **After the last line, it is already true.** `LINE INPUT #` and `INPUT #`
  take the line feed after the carriage return with them, so once the last
  line is read the Ctrl-Z is next and `EOF` is −1. The loop
  `IF EOF(1) THEN ... : LINE INPUT #1,A$` reads exactly the lines that were
  written. `INPUT$` takes bytes one by one and leaves the line feed.
- **A file read past its end** is `Input past end` (55) on the read, not on
  `EOF`.
- **A channel open for output, append or random access** is
  `Bad file mode` (61) — random included.
- **A cassette channel open for input works the same way**: 0, 0, then −1
  after the last line.
- **A screen or printer channel** (`"CRT:"`) is `Illegal function call` (5).

### Errors

| situation | error |
|---|---|
| the channel is not open (`EOF(1)`), or channel 0 | 59 `File not OPEN` |
| a channel past `MAXFILES` (`EOF(16)`) | 52 `Bad file number` |
| a channel below 0 or above 255 | 5 `Illegal function call` |
| a channel open for output, append or random access | 61 `Bad file mode` |
| a `CRT:` channel | 5 `Illegal function call` |
| a string as the channel (`EOF("A")`) | 13 `Type mismatch` |

The enumerated set is {13, 52, 59, 61}, the same on both machines.

## Example

```
10 OPEN "E.TXT" FOR OUTPUT AS #1
20 PRINT #1,"L1":PRINT #1,"L2"
30 CLOSE #1
40 OPEN "E.TXT" FOR INPUT AS #1
50 IF EOF(1) THEN 80
60 LINE INPUT #1,A$:PRINT A$;EOF(1)
70 GOTO 50
80 CLOSE #1:ON ERROR GOTO 120
90 PRINT EOF(1)
100 OPEN "F" FOR OUTPUT AS #1
110 PRINT EOF(1):CLOSE:END
120 PRINT "Error";ERR:RESUME NEXT
RUN
L1 0
L2-1
Error 59
Error 61
```

The loop reads two lines, and `EOF` is already −1 after the second. Line 90
asks a closed channel, line 110 one open for output.

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_eof.out`](../../scratchpad/kwdoc_eof.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**. Not measured: `EOF` on a
cassette channel open for output — the CF-3300 never came back from opening
one with an input tape in the recorder.

## What we found, and how

- **`EOF` on an output channel answered 0 and the program ran on** (fixed
  2026-09-30, D-EOFMODE); the CF-3300 raises `Bad file mode` (61) for output,
  append and random channels alike
  ([`eofmode_run.out`](../../scratchpad/eofmode_run.out)).
- **`EOF` on a cassette channel was `Illegal function call`** (fixed
  2026-09-30, D-EOFCAS), so the ordinary tape read loop died at its first
  test ([`eofcas_run.out`](../../scratchpad/eofcas_run.out)). The `5` had been
  measured for `CRT:` only and applied to every device.
- **The textbook loop read one line too many** (fixed 2026-09-28,
  D-SEQEOF). zerobas read the Ctrl-Z end mark as data and left the line feed
  after the last line unread, so `EOF` stayed 0 one line too long and the
  extra line came back as `CHR$(26)`
  ([`ipe_after_run.out`](../../scratchpad/ipe_after_run.out)).
- **`EOF` of a channel that does not exist answered a number** (fixed
  2026-07-31, D-BADFNUM): `PRINT EOF(0)` printed ` 0` and no handler ran. The
  CF-3300 raises 59.

## Where it lives

- `ev_ff_eof` in [basic/expr.asm](../../basic/expr.asm): the channel checks,
  the mode check (61), and the call to `fat_io_eof` in
  [basic/input.asm](../../basic/input.asm).
- The look-ahead itself is the SEQIO tenant in
  [sub/bload.asm](../../sub/bload.asm): `seq_peek` for a disk file and
  `sq_deveof` for the cassette.

## Tests that cover it

- `make kwsweep` — `EOF` before and after a file is read, the Ctrl-Z and
  line-feed rules, and every error row.
- `make eofcas-acceptance` — the cassette channel, against the CF-3300.
- `make badfnum-acceptance` — every channel class.
- `make kwram` — the RAM-usage comparison.
