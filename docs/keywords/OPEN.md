<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `OPEN` — open a file or device on a numbered channel

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. Recorded differences,
> all in the channel table: one file opened twice under names that differ only
> in case, `VARPTR(#0)`, and two details of the channel header (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`OPEN "file" FOR mode AS #n` connects channel `n` to a disk file or a device,
so that `PRINT #n`, `INPUT #n`, `LINE INPUT #n` and the other channel
statements can write or read it; [`CLOSE`](CLOSE.md) ends it. `MAXFILES` sets
how many channels exist. Disk files follow the National CF-3300; the
cassette and the screen and printer devices follow the Philips VG-8020 too.
zerobas writes the same bytes, reads them back the same way and raises the
same errors in every case we have measured, with the exceptions listed under
*Differences*.

## Syntax

```
OPEN <file name> [FOR INPUT|OUTPUT|APPEND] AS [#]<n> [LEN=<record length>]
MAXFILES=<count>
```

The file name is a string expression; `OPEN A$ AS #1` works. The `#` before
the channel number may be left out.

## Details

### Modes

- **`FOR OUTPUT`** creates the file, or empties an existing one.
- **`FOR INPUT`** reads an existing file from its start.
- **`FOR APPEND`** writes after what is already there; the file must exist.
- **No `FOR` at all is random access**, for [`FIELD`](FIELD.md), `GET` and
  `PUT`; `LEN=` (1 to 256) is the record length.

### Channels and `MAXFILES`

- **Channel numbers run from 1 to `MAXFILES`**, which is 1 after start-up.
  `MAXFILES=n` takes 0 to 15.
- **`MAXFILES` reserves the room at once**: each channel costs 267 bytes of
  `FRE(0)` on both machines, whether it is opened or not.
- **Assigning `MAXFILES` closes every file and clears the variables**, even
  when the value does not change. So does an accepted [`CLEAR`](CLEAR.md).
- **A channel already in use** is `File already open` (54); so is the same
  file opened on a second channel, in any mode.

### Devices

- **`"CRT:"`** (the screen) and **`"LPT:"`** (the printer) take output.
- **`"CAS:name"`** is the cassette. `FOR INPUT` searches the tape for that
  name, exactly matching upper and lower case, printing `Skip :` and `Found:`
  rows; a bare `"CAS:"` takes the next ASCII file. `FOR OUTPUT` writes the
  name into the tape header. `FOR APPEND` and random access are
  `Bad file name` (56) on both machines.
- **On a diskless machine** a name with no device is the cassette, and a
  drive name (`"A:X"`) is 56.

### Writing and reading

- **`PRINT #n`** writes the characters [`PRINT`](PRINT.md) would put on the
  screen, each line ended by a carriage return and a line feed; `PRINT #n
  USING` works too. [`CLOSE`](CLOSE.md) adds an end-of-file byte, Ctrl-Z
  (`CHR$(26)`), which `LOF` counts: `PRINT #1,"AB"` makes a 5-byte file.
- **`LINE INPUT #n,A$`** reads a whole line. **`INPUT #n,A,B$`** reads items:
  a number ends at a blank or a comma; a string item loses its leading
  blanks and ends at a comma or the end of the line; a quoted string keeps
  everything between the quotes, commas included. Both statements swallow
  the line feed after the carriage return.
- **Ctrl-Z ends the file** even when more bytes follow it: [`EOF`](EOF.md) is
  true as soon as the Ctrl-Z is next, and the textbook
  `IF EOF(1) ... LINE INPUT #1` loop reads exactly the lines that were
  written. A read at the end is
  `Input past end` (55), and the variable keeps its old value.
- **Wrong direction**: `PRINT #` to a channel open for input, or `INPUT #` from
  one open for output or append, is `Bad file number` (52); either on a
  random channel is `Bad file mode` (61). A channel that is not open is
  `File not OPEN` (59).

### The channel header, through `VARPTR(#n)`

[`VARPTR(#n)`](VARPTR.md) gives the address of channel `n`'s file control
block: a 9-byte header, then the 256-byte record buffer. After `OPEN`,
`PEEK` reads the mode at +0 (1 input, 2 output or append, 4 random) and the
device at +4 (0 for a disk file named without a drive, 1 for `A:`, &HFD
`CRT:`, &HFE `LPT:`, &HFF `CAS:`); +6 is the write position of a disk output
or append channel.

### Errors

| situation | error |
|---|---|
| the file does not exist (`FOR INPUT`, `FOR APPEND`) | 53 `File not found` |
| no `AS` part (`OPEN "A" FOR INPUT`), or `LEN` without `=` | 2 `Syntax error` |
| anything after the statement (`... AS 1,2`) | 2 `Syntax error`, before the disk is touched |
| channel 0, or past `MAXFILES` | 52 `Bad file number` |
| a channel number below 0 or above 255, `LEN=0`, `LEN=257` | 5 `Illegal function call` |
| a number as the name, a string as the channel or length | 13 `Type mismatch` |
| the channel is in use, or the file is open on another channel | 54 `File already open` |
| an empty name, a wildcard (`"A*.TXT"`), `CAS:` with APPEND or random | 56 `Bad file name` |
| a drive that does not exist (`"Q:X.TXT"`) | 62 `Bad drive name` |
| `MAXFILES=16`, `MAXFILES=-1` | 5 `Illegal function call` |
| `MAXFILES=65536` | 6 `Overflow` |

## Example

```
10 ON ERROR GOTO 110
20 OPEN "T.TXT" FOR OUTPUT AS #1
30 PRINT #1,"ONE":PRINT #1,2;3
40 CLOSE #1
50 OPEN "T.TXT" FOR INPUT AS #1
60 LINE INPUT #1,A$:INPUT #1,B,C
70 PRINT A$;B+C;EOF(1);PEEK(VARPTR(#1))
80 OPEN "HI.TXT" FOR INPUT AS #2
90 CLOSE:OPEN "NO.TXT" FOR INPUT AS #1
100 END
110 PRINT "Error";ERR:RESUME NEXT
RUN
ONE 5 -1  1
Error 52
Error 53
```

Line 80 fails because `MAXFILES` is still 1.

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_open.out`](../../scratchpad/kwdoc_open.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

- **The same file under two spellings** (TIER 6, open). `OPEN "TS.DAT" AS #1`
  then `OPEN "ts.dat" AS #2` opens on the CF-3300 and is
  `File already open` (54) here. The CF-3300 compares the names as typed,
  upper and lower case distinct, while its disk treats them as one file — so
  its own guard lets one file be opened twice. zerobas asks whether the
  directory entry is already open. Joost ruled on 2026-09-27 to *"fold into
  D-FCBSHAPE"* — refuse like the reference once a channel has the MSX block
  shape, where the name would have a home. That block turned out to have no
  name field, so copying the reference would cost 165 bytes of the disk
  machine's RAM, and the question is back with him.
- **`VARPTR(#0)`** — channel 0, the one `LOAD` and `SAVE` use — is an address
  on both references and `File not OPEN` (59) here, because zerobas reserves
  no block for it. Joost ruled on 2026-10-09: *"build it"*; it will cost
  every program 267 bytes of `FRE(0)`, as it does on the references.
- **Where the blocks sit.** On the references `VARPTR(#1)` moves by 265 for
  each step of `MAXFILES`; here by 267, because the two pointer bytes a
  channel costs sit above the blocks instead of below them.
- **The position byte of an input channel.** On the CF-3300, header +6 of a
  disk input channel counts the bytes read (modulo 256), and an `EOF` call
  moves it on by one; here it stays 0.
- **Related, filed against `INPUT #`** (TIER 6, D-INPQUOTE2): text after a
  closing quote, and a quote that is never closed, are read differently. After
  `"AB"CD` the CF-3300 hands `CD` to the next read; here it is dropped.

**RAM usage** is not yet proven.

## What we found, and how

- **A program could not use two disk files at once.** A second disk `OPEN`
  raised a spurious `Syntax error` (fixed 2026-09-02, D-OPEN2FIX), and
  switching between two channels inside a `FOR` loop or a `GOSUB` wrote a
  channel's buffer over the loop's own record (fixed 2026-09-29,
  D-CHANSWITCH).
- **Reading a text file to its end read one line too many** (fixed
  2026-09-28, D-SEQEOF): the Ctrl-Z end marker came back as data, so the
  textbook `EOF` loop got an extra `CHR$(26)` line and no read ever said
  `Input past end` ([`ipe_after_run.out`](../../scratchpad/ipe_after_run.out)).
- **`INPUT #` could not read a number at all** (fixed 2026-09-29, D-INPNUM):
  every numeric target was `Type mismatch`. A string field kept its leading
  blanks (D-INPSTR, the same day).
- **The same file could be opened on two channels** (fixed 2026-09-29,
  D-OPENSAME, except the case-spelling row under *Differences*).
- **`MAXFILES` charged 306 bytes a channel against the references' 267**
  (fixed 2026-09-30, D-FCBSHAPE): a channel is now the reference's 9-byte
  header plus 256-byte record, and `VARPTR(#n)`, a `Syntax error` until then,
  answers its address (D-VARPTRCH, the same day). Since
  2026-10-08 (D-FCBHDR) `OPEN` also fills the header's mode, device and
  position bytes, which read 255 here before
  ([`fcbhdr_after.out`](../../scratchpad/fcbhdr_after.out)).
- **Reading or writing in the wrong direction raised nothing a handler could
  see** (fixed 2026-10-06, D-CHDIR); the CF-3300 raises 52, or 61 on a random
  channel. On cassette, `PRINT #` to an input channel followed on 2026-10-08
  (D-CASPRDIR).
- **`OPEN "CAS:name" FOR INPUT` ignored the name** and opened whatever file
  came next on the tape (fixed 2026-08-07, D-CASOPEN):
  [casopen-msx1-characterization.md](../casopen-msx1-characterization.md).

## Where it lives

- `do_open` in [basic/files.asm](../../basic/files.asm): the name, the device,
  the mode, the channel checks (`fch_check`) and the header (`oo_hdr_tail`,
  which calls `t_fch_hdr` in [sub/fatprim.asm](../../sub/fatprim.asm)).
  `ex_maxfiles` is in the same file, and so is `INPUT #` (`inp_readvar`).
- `PRINT #` is `ex_print` in [basic/print.asm](../../basic/print.asm).
- Reading a disk text file — the Ctrl-Z end, the line feed, a numeric item —
  is the SEQIO tenant in [sub/bload.asm](../../sub/bload.asm) (`seq_peek`).
- A disk file open for output, and the "is this file already open" check
  (`hkk_open_check`), are the disk ROM's: [disk/kernel.asm](../../disk/kernel.asm).
- The block layout: [spec-fcbshape.md](../spec-fcbshape.md); the channel
  number rule: [spec-basic-badfnum-channel-class.md](../spec-basic-badfnum-channel-class.md).

## Related concepts

- [The cassette](../concepts/cassette.md) — files on tape, and how BASIC finds them
- [Files and devices](../concepts/files-and-devices.md) — numbered channels to the disk, the tape, the screen and the printer
- [The memory map](../concepts/memory-map.md) — where BASIC keeps things in RAM

## Tests that cover it

- `make kwsweep` — each of the four modes, a second channel with
  `MAXFILES=2`, `MAXFILES` clearing the variables, numeric and string
  `INPUT #`, the end-of-file rules, and every error row of `OPEN`.
- `make dout-acceptance` — output files: lengths across records, two output
  channels in turn, output beside append and input, directions.
- `make badfnum-acceptance` and `make nohash-acceptance` — channel numbers,
  with and without `#`.
- `make chancost-characterize` — what `MAXFILES` costs and clears.
- `make fcbhdr-acceptance` — the header bytes, on both references.
- `make clearclose-acceptance` — `CLEAR` closing open files.
- `make castail-acceptance`, `make casprdir-acceptance`,
  `make nodiskopen-acceptance` — the cassette and the diskless machine.
- `make kwram` — the RAM-usage comparison.
