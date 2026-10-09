<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `CLOSE` — close one channel, several, or all

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`CLOSE #n` finishes the work on a channel opened with [`OPEN`](OPEN.md): what
is still waiting in its buffer is written to the disk, the file gets its
end-of-file mark, and the channel number is free again. A bare `CLOSE` closes
every open channel. The reference for disk files is the National CF-3300.
zerobas writes the same bytes and raises the same errors in every case we have
measured.

## Syntax

```
CLOSE [[#]<n>[,[#]<m>...]]
```

The `#` is optional, and a list closes several channels in one statement.

## Details

- **The data reaches the disk at the close.** A file written with
  `PRINT #1,"ABC"` and closed measures 6 bytes: the three letters, a carriage
  return and line feed, and the Ctrl-Z end mark.
- **Bare `CLOSE` closes everything**, including channels the statement does
  not name.
- **Closing a channel that is not open does nothing**, and neither does
  `CLOSE #0`. A channel past `MAXFILES` is `Bad file number` (52) — in a list,
  after the channels before it have been closed and written.
- **A full disk is reported at the close**, because that is when a short
  file's first cluster is allocated: `CLOSE` is `Disk full` (66) and the
  channel stays open; a second `CLOSE` frees it.
- **Other statements close files too**: `MAXFILES=` and an accepted
  [`CLEAR`](CLEAR.md) close every open channel, after which a `PRINT #1` is
  `File not OPEN` (59).

### Errors

| situation | error |
|---|---|
| a channel past `MAXFILES` (`CLOSE #16`) | 52 `Bad file number` |
| a channel below 0 or above 255 (`CLOSE #-1`) | 5 `Illegal function call` |
| a string as a channel (`CLOSE "A"`, `CLOSE #"A"`) | 13 `Type mismatch` |
| a list ending in a comma (`CLOSE 1,`) | 24 `Missing operand` |
| the disk fills up | 66 `Disk full` |

The enumerated set is {13, 24} for the bare form and {5, 13, 52} for the
channel form, the same on both machines.

## Example

```
10 OPEN "C.TXT" FOR OUTPUT AS #1
20 PRINT #1,"ABC"
30 CLOSE #1
40 OPEN "C.TXT" FOR INPUT AS #1
50 PRINT LOF(1):CLOSE
60 ON ERROR GOTO 90
70 CLOSE #1:CLOSE #0:CLOSE #2
80 CLOSE #-1:END
90 PRINT "Error";ERR:RESUME NEXT
RUN
 6
Error 52
Error 5
```

`CLOSE #1` and `CLOSE #0` on line 70 are silent; `#2` is past the default
`MAXFILES` of 1.

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_close.out`](../../scratchpad/kwdoc_close.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

Related, and not about `CLOSE` alone: keys typed while a long disk write runs
are partly lost on both machines, more of them on zerobas (about 42 % kept
against the CF-3300's 77 % in one measurement of `PRINT #` plus `CLOSE`). That
is filed as a TIER 3 item against the disk driver, D-FDCDI.

## What we found, and how

- **A full disk was never `Disk full`** (fixed 2026-10-02, D-DISKFULL): the
  close was silent and freed the channel, where the CF-3300 raises 66 and
  keeps it open.
- **An accepted `CLEAR` did not close the files** (fixed 2026-10-06,
  D-CLEARCLOSE): `PRINT #1` after it went on writing, where the CF-3300 says
  59 and the file ends at the `CLEAR`
  ([`clearopen_run.out`](../../scratchpad/clearopen_run.out)).
- **`CLOSE` of a bad channel did nothing** (fixed 2026-07-31, D-BADFNUM).
  `CLOSE #2`, `#16`, `#256` and `#-1` were silent no-ops; the CF-3300 raises 52
  or 5 and is lenient only about channel 0. A test had recorded the old
  behaviour as correct without ever asking the reference:
  [spec-basic-badfnum-channel-class.md](../spec-basic-badfnum-channel-class.md).
- **The test of `CLOSE` had to be designed so it could fail** (2026-09-12).
  A first row checked that the channel could be reopened after the close, and
  on zerobas at the time it passed with the `CLOSE` removed; the row now
  reads the file's length, which is only right if the close wrote it.

## Where it lives

- `ex_close` in [basic/files.asm](../../basic/files.asm): the list, the
  channel checks, `fch_do_close_ch` for one channel and `fch_close_all` for
  the bare form.
- The flush of a disk output channel, the Ctrl-Z and the directory entry are
  the disk ROM's ([disk/kernel.asm](../../disk/kernel.asm)).

## Related concepts

- [Files and devices](../concepts/files-and-devices.md) — numbered channels to the disk, the tape, the screen and the printer

## Tests that cover it

- `make kwsweep` — `CLOSE #1` and bare `CLOSE`, each read back by the file's
  length, and the error rows.
- `make badfnum-acceptance` — every channel class on every channel verb.
- `make diskfull-acceptance` — `CLOSE` on a full disk.
- `make clearclose-acceptance` — `CLEAR` closing open files.
- `make dout-acceptance` and `make putdir-acceptance` — what is on the disk
  after the close, for output and random files.
- `make kwram` — the RAM-usage comparison.
