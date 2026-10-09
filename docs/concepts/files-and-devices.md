<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# Files and devices — numbered channels to the disk, the tape, the screen and the printer

> **Status (2026-10-09):** every everyday channel operation agrees with the
> references except one: `GET #` / `PUT #` without a record number always use
> record 1 here (D-RECAUTO, TIER 1, open). Channel #0 is ruled to be built
> (part of D-FCBSHAPE, TIER 4); the other recorded differences are TIER 6
> edges. Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

MSX BASIC reaches files and devices through **numbered channels**. `OPEN`
connects a number to a disk file, the cassette, the screen or the printer;
`PRINT #`, `INPUT #`, `LINE INPUT #`, `INPUT$`, `GET #` and `PUT #` move data;
`EOF`, `LOC` and `LOF` ask where it stands; `CLOSE` finishes it. Each device
refuses what it cannot do with a specific error.

How many channels exist is set by `MAXFILES`, 1 after start-up; each one
reserves a block of memory at once, which `VARPTR(#n)` finds. The reference
for disk files is the National CF-3300; for the cassette, the screen and the
printer it is the Philips VG-8020, and where a device row was also run on the
CF-3300 it agreed.

## How it works

### Channels and `MAXFILES`

- **Channel numbers run from 1 to `MAXFILES`**; `MAXFILES=n` takes 0 to 15.
  A fraction is truncated (`MAXFILES=15.9` is 15); 16, a negative number or
  32767 is `Illegal function call` (5); outside −32768..32767 it is
  `Overflow` (6).
- **The room is reserved at once**: each channel costs 267 bytes of `FRE(0)`
  on both machines, opened or not, and `OPEN` itself costs nothing more
  ([chancost-cf3300-characterization.md](../chancost-cf3300-characterization.md)
  §2, §4). The string space (`FRE("")`) is not touched.
- **Setting `MAXFILES` closes every file and clears the variables**, even to
  the same value; so does an accepted `CLEAR`.
- **Channel 0 is not for programs**: `OPEN ... AS #0` is `Bad file number`
  (52), and `CLOSE #0` does nothing. On the references it is the channel
  `LOAD` and `SAVE` use.

### Devices

| name | device | modes |
|---|---|---|
| `"X.DAT"`, `"A:X.DAT"` | a disk file | `INPUT`, `OUTPUT`, `APPEND`, random |
| `"CAS:name"` | the cassette | `INPUT`, `OUTPUT` |
| `"CRT:"` | the screen | output only |
| `"LPT:"` | the printer | output only |

- **With no `FOR` clause** a disk file is opened for random access, and a
  `CRT:` or `LPT:` channel for output.
- **On a diskless machine** a name with no device is the cassette, and a
  drive name (`"A:X"`) is `Bad file name` (56).
- **`"Q:X"`** is `Bad drive name` (62). The single-drive CF-3300 prompts for
  a disk swap when drive B is addressed (measured with `DSKI$`), which is ruled
  to be built (D-DSKIB, TIER 6, 2026-10-09); `OPEN "B:X"` is not measured.
- **`GRP:`** and other device names are not measured on either machine;
  zerobas does not treat `GRP:` as a device. The cassette is
  [cassette.md](cassette.md).

### Sequential and random access

**Sequential** channels carry text. `PRINT #n` writes what `PRINT` would put
on the screen, each line ended by a carriage return and a line feed; `CLOSE`
adds an end-of-file byte, Ctrl-Z (`CHR$(26)`). `FOR APPEND` writes over that
Ctrl-Z, so text appended to a closed file reads back as one stream. `LINE
INPUT #` reads a line, `INPUT #` reads items as `INPUT` does, `INPUT$(n,#f)`
reads n raw bytes. A read stops at the first Ctrl-Z, even if more bytes
follow it; reading past it is `Input past end` (55).

**Random** channels (`OPEN "f" AS #n LEN=r`) hold fixed records of 1 to 256
bytes. `FIELD` names pieces of the channel's record buffer, `LSET` and `RSET`
fill them, `PUT #n,k` writes the buffer to record k, `GET #n,k` reads record k
into it. Records are numbered from 1.

| ask | sequential input | sequential output / append | random |
|---|---|---|---|
| `EOF(n)` | −1 when the next byte is the end or Ctrl-Z | error 61 | error 61 |
| `LOF(n)` | the file's size | moves in whole 256-byte records | the size, including records just `PUT` |
| `LOC(n)` | the file's size, unmoving | moves in whole 256-byte records | the record of the last `GET` or `PUT` |

`LOF` is the full size (76800 after `PUT #1,300` at `LEN=256`). A random
file's directory entry is written at `CLOSE`, not at each `PUT`, as on the
CF-3300.

### What each device refuses

| statement | wrong direction or mode | `LPT:` / `CRT:` | `CAS:` |
|---|---|---|---|
| `PRINT #` | to an input channel: 52; to a random one: 61 | works | to an input channel: 52 |
| `INPUT #`, `LINE INPUT #` | from an output channel: 52; random: 61 | — | from an output channel: 52 |
| `GET #`, `PUT #` | a sequential disk file: 61 | `LPT:`: 58 `Sequential I/O only` | 58 |
| `FIELD` | a sequential disk file: 61 | `LPT:`: 5 | 5 |
| `INPUT$(n,#f)` | — | `LPT:`: 55 | output channel: 55; input channel reads |
| `EOF`, `LOF` | see the table above | `CRT:`: 5 | `EOF` works on an input channel |
| `OPEN` with `APPEND` or random | — | `LEN=` is `Syntax error` (2); `FOR APPEND` not measured | 56 `Bad file name` |

A channel not open is 59 for all of these; past `MAXFILES`, 52; below 0 or
above 255, 5.

### The channel block, through `VARPTR(#n)`

`VARPTR(#n)` is the address of channel n's file control block: a 9-byte
header, then the 256-byte record buffer, 265 bytes in all.

| offset | holds | values written by `OPEN` |
|---|---|---|
| +0 | the mode | 1 input, 2 output or append, 4 random |
| +4 | the device | 0 a disk file named without a drive, 1 `A:`, &HFD `CRT:`, &HFE `LPT:`, &HFF `CAS:` |
| +6 | the position | the write position of a disk output or append channel; 0 for a disk input or random channel |
| +9 | the record buffer | 256 bytes |

On the CF-3300, +1..+2 of a disk channel point into the disk ROM's work area;
the other header bytes are not part of the measured contract. The 2 bytes of
the 267 outside the block are a table of pointers to the blocks.

## Example

```
10 ON ERROR GOTO 110
20 OPEN "D.TXT" FOR OUTPUT AS #1
30 PRINT #1,"ONE":CLOSE
40 OPEN "D.TXT" FOR APPEND AS #1
50 PRINT #1,"TWO":CLOSE
60 OPEN "D.TXT" FOR INPUT AS #1
70 IF EOF(1) THEN 90
80 LINE INPUT #1,A$:PRINT A$:GOTO 70
90 PRINT LOF(1);PEEK(VARPTR(#1)):CLOSE
100 PRINT #1,"X"
105 OPEN "HI.TXT" FOR INPUT AS #2:END
110 PRINT "Error";ERR:RESUME NEXT
RUN
ONE
TWO
 11  1
Error 59
Error 52
```

`TWO` is appended over the Ctrl-Z that closed `ONE`: 11 bytes, two lines.
The header's mode byte reads 1 (input). Line 100 writes to a closed channel;
line 105 asks for channel 2 while `MAXFILES` is 1.

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_files-and-devices.out`](../../scratchpad/kwdoc_files-and-devices.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

- **`GET #` / `PUT #` without a record number** (D-RECAUTO, found 2026-10-09,
  open, TIER 1). The CF-3300 takes the record after the last one read or
  written (`LOC` + 1): three bare `PUT #1` at `LEN=8` make a 24-byte file.
  zerobas always uses record 1, so the same loop makes an 8-byte file holding
  only the last record ([`getput_run.out`](../../scratchpad/getput_run.out)).
- **Channel #0** (part of D-FCBSHAPE, TIER 4). `VARPTR(#0)` is an address on
  both references and `File not OPEN` (59) here: zerobas reserves no block
  for it. Joost ruled on 2026-10-09: *"build it"*, at 267 bytes of `FRE(0)`
  for every program, as the references pay.
- **Where the blocks sit.** The references keep the pointer table below the
  blocks, so `VARPTR(#1)` moves by 265 for each step of `MAXFILES`; here it is
  above them, and it moves by 267
  ([`varptrch_run.out`](../../scratchpad/varptrch_run.out)).
- **The position byte of an input channel.** On the CF-3300, header +6 of a
  disk input channel counts the bytes read, modulo 256; here it stays 0. Not
  built: a write on every byte read, for a value only `PEEK` can see.
- **One file under two spellings** (TIER 6). The CF-3300 lets `"TS.DAT"` and
  `"ts.dat"` be open at once, comparing names as typed while its disk treats
  them as one file; zerobas says 54. Joost ruled on 2026-09-27 to fold this
  into D-FCBSHAPE; the MSX block has no name field, so copying the reference
  would cost 165 bytes of the disk machine's RAM. Open.
- **Record numbers above 32767** (D-RECBIG, TIER 6, open) are `Overflow`
  here; the CF-3300 accepts up to 65535.
- **Text after a closing quote** in `INPUT #` (D-INPQUOTE2, TIER 6, open):
  `CD` in `"AB"CD` goes to the next read there and is dropped here.
- **`OPEN "CRT:" FOR INPUT`** is `Syntax error` here; on the CF-3300 the
  program never came back, and a hang is deliberately not copied (D-DEVBARE,
  2026-08-30).

## What we found, and how

- **The channel block was 306 bytes, then 265** (D-FCBSHAPE, 2026-09-30).
  `PEEK`ing around `VARPTR(#n)` on both references showed the 9-byte header
  and the pointer table; zerobas's 50 bytes of disk bookkeeping moved out of
  the block ([spec-fcbshape.md](../spec-fcbshape.md)). Since 2026-10-08 `OPEN`
  fills the header (D-FCBHDR, [`fcbhdr_after.out`](../../scratchpad/fcbhdr_after.out)).
- **Two disk files at once did not work** — a second `OPEN` raised a spurious
  `Syntax error` (fixed 2026-09-02, D-OPEN2FIX), two random files shared one
  record buffer (fixed 2026-09-07, D-FIELDFIX), and switching channels inside
  a loop wrote one buffer over another (fixed 2026-09-29, D-CHANSWITCH).
- **Bad channel numbers were silent** (fixed 2026-07-31, D-BADFNUM): 63 of
  the first 72 cases of a sweep over every channel statement were wrong
  ([spec-basic-badfnum-channel-class.md](../spec-basic-badfnum-channel-class.md)).
  The same day `MAXFILES=65536` stopped being taken silently as `MAXFILES=0`
  (D-MFDOM, [spec-basic-maxfiles-domain.md](../spec-basic-maxfiles-domain.md)).

## How zerobas does it

`do_open`, `ex_close` and `ex_maxfiles` are in
[basic/files.asm](../../basic/files.asm), with one channel-number rule,
`fch_check` (5, 59 or 52), for every channel statement. `do_open` tells the
devices apart by name (`dev_cmp`); `PRINT #` to `LPT:` or `CRT:` goes to the
printer or the screen, `CAS:` to the tape, anything else is a disk name.

Channel blocks are carved out of free memory when `MAXFILES` is set, 265 bytes
each plus 2 bytes of table; `fch_ctx_addr` finds one, and `VARPTR(#n)`
(`ev_ff_varptrch` in [basic/expr.asm](../../basic/expr.asm)) returns it.
`OPEN` writes the header through `t_fch_hdr` in
[sub/fatprim.asm](../../sub/fatprim.asm). Mode, record length and last record
sit in fixed per-channel tables (`FCH_MODES`, `FCH_RECLENS`, `FCH_RECNOS` in
[basic/sysvars.inc](../../basic/sysvars.inc)).

Each disk channel's 50 bytes of FAT bookkeeping live in a row of
`DSK_ENGTAB`, which the disk ROM reserves at start-up by lowering `HIMEM` by
750 bytes, the way the CF-3300 reserves its own work area; `t_fch_save` and
`t_fch_load` swap rows when the program switches channels. Reading disk text
(the Ctrl-Z rule, the line feed, `EOF`'s look-ahead) is the sub-ROM's SEQIO
tenant (`seq_peek` in [sub/bload.asm](../../sub/bload.asm)); writing,
appending and the "is this file already open" check are the disk ROM's
([disk/kernel.asm](../../disk/kernel.asm)). Random records go through
`ex_get` / `ex_put` in [basic/field.asm](../../basic/field.asm) and the record
engine [basic/randio-body.inc](../../basic/randio-body.inc), which keeps each
channel's last record number for `LOC`; the CF-3300's bare `GET` / `PUT` use
that number plus one.

## Related pages

[`OPEN`](../keywords/OPEN.md) · [`CLOSE`](../keywords/CLOSE.md) · [`GET`](../keywords/GET.md) · [`PUT`](../keywords/PUT.md) · [`FIELD`](../keywords/FIELD.md) · [`LSET`](../keywords/LSET.md) · [`EOF`](../keywords/EOF.md) · [`LOC`](../keywords/LOC.md) · [`LOF`](../keywords/LOF.md) · [`VARPTR`](../keywords/VARPTR.md) · [`INPUT`](../keywords/INPUT.md) · [`PRINT`](../keywords/PRINT.md) · [`CLEAR`](../keywords/CLEAR.md)
— and the concept pages [cassette.md](cassette.md), [disk.md](disk.md),
[memory-map.md](memory-map.md) and [errors.md](errors.md).
- More keywords: [`RSET`](../keywords/RSET.md).

## Tests that cover it

- `make kwsweep` — every channel statement's everyday row and error rows.
- `make chancost-characterize` — what `MAXFILES` costs, clears and accepts.
- `make fcbhdr-acceptance` — the header bytes after `OPEN`, per device.
- `make badfnum-acceptance`, `make nohash-acceptance` — channel numbers.
- `make dout-acceptance`, `lof-acceptance`, `loc-acceptance`,
  `diskbasic-acceptance`, `putdir-acceptance` — disk files.
- `make clearclose-acceptance`, `nodiskopen-acceptance`,
  `casprdir-acceptance`, `eofcas-acceptance` — `CLEAR`, the diskless machine,
  the cassette channel.
