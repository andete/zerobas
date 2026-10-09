<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: verify=no reason="needs a cassette" -->

# The cassette — files on tape, and how BASIC finds them

> **Status (2026-10-09):** every measured tape behaviour agrees with the
> VG-8020, and with the CF-3300 where a row was run there too: the recorded
> bytes, the search and its messages, the type filter, Ctrl-STOP. Open: a
> failing tape write and a damaged ASCII program still print `load error`
> instead of raising a code (part of D-LOADERRRET, TIER 3; the references'
> answer there is not measured). Speed is deliberately left out of these docs
> until on-par speed is established for every keyword.

## Summary

Every MSX has a cassette port, and on a diskless machine such as the Philips
VG-8020 it is the only storage. A tape holds files one after another; each
has a **type** (a tokenised BASIC program, an ASCII text file, or a binary
block of memory) and a **name** of up to six characters. Each verb writes
one type and reads one type: `CSAVE` and `CLOAD` the tokenised program,
`SAVE "CAS:"`, `LOAD "CAS:"` and `OPEN "CAS:"` the ASCII one, `BSAVE` and
`BLOAD` the binary one.

Reading is a search. The machine plays the tape, prints `Skip :` for each
file of the right type with another name and `Found:` for the one it takes,
and passes files of another type without a word. A file that is not on the
tape is not an error: the reference searches on, past the end of the tape,
until the user presses Ctrl-STOP, which is `Device I/O error` (19).

The reference is the Philips VG-8020; the National CF-3300 has the same
cassette port, and every row run on both agreed.

## How it works

### The signal

The tape carries a two-tone signal: a `0` bit is one cycle of the low tone,
a `1` bit two cycles of the high tone, and each byte is a start bit, eight
data bits low bit first, and stop bits. A file starts with a long leader of
the high tone before its header block, and each later block has a short
leader. Two rates exist, 1200 and 2400 baud; `CSAVE "X",2` records at 2400,
and the reader works out the rate from the leader by itself, so loading
needs no setting. The MSX BIOS entries are `TAPION`
(`&H00E1`, start reading and lock onto a leader), `TAPIN` (`&H00E4`, one
byte), `TAPIOF` (`&H00E7`), `TAPOON` (`&H00EA`, start writing with a leader),
`TAPOUT` (`&H00ED`), `TAPOOF` (`&H00F0`) and `STMOTR` (`&H00F3`)
([spec-cassette.md](../../tape/docs/spec-cassette.md)).

### The motor

The recorder's motor hangs on a relay, bit 4 of port `&HAA` (0 = running).
The tape verbs switch it on while they read or write and off afterwards;
`MOTOR ON`, `MOTOR OFF` and a bare `MOTOR` (toggle) switch it by hand, through
`STMOTR`. `INP(&HAA) AND 16` reads it back: 16 stopped, 0 running.

### A file on tape

A **header block** is ten identical type bytes and the six-byte name, padded
with blanks; then come the **data** blocks.

| type | id byte | written by | read by | the data |
|---|---|---|---|---|
| tokenised BASIC | `&HD3` | `CSAVE` | `CLOAD`, `CLOAD?` | one block: the program as stored in memory, its end marker, then seven zero bytes |
| ASCII | `&HEA` | `SAVE "CAS:"` (with or without `,A`), `OPEN "CAS:" FOR OUTPUT` | `LOAD`, `RUN`, `MERGE "CAS:"`, `OPEN "CAS:" FOR INPUT` | 256-byte blocks, each with its own short leader: text lines ending CR LF; the first Ctrl-Z (`CHR$(26)`) ends the file |
| binary | `&HD0` | `BSAVE "CAS:"` | `BLOAD "CAS:"` | one block: start, end and run addresses (low byte first), then the bytes |

The `CSAVE` recording of `10 PRINT"[Z9]":CSAVE"ZQ"`, decoded off the tape, is
byte for byte the same on the VG-8020 and zerobas, and the CF-3300 records
the same type, name and text. A `SAVE "CAS:"` is always ASCII on an MSX1,
with or without `,A`. The 8-byte sync
pattern `1F A6 DE BA CC 13 7D 74` seen in `.cas` files belongs to that file
container; it is not on the audio tape.

### The name

- **Six characters, padded with blanks**, in the header. A bare
  `SAVE "CAS:"` or `OPEN "CAS:" FOR OUTPUT` records six blanks.
- **The compare is exact, upper and lower case distinct**: `OPEN "CAS:rt"`
  does not find `RT`, on either reference.
- **A bare name takes the next file of the right type**: `CLOAD`,
  `LOAD "CAS:"`, `BLOAD "CAS:"`, `OPEN "CAS:" FOR INPUT`.
- **A name longer than six** is cut to six by zerobas; what the references do
  is not measured.

### The search

For each file it meets, the reader takes the header and decides:

1. **Wrong type** for this verb: skip its data silently, no row printed.
2. **Right type, wanted name** (or no name given): print `Found:name` and
   load it.
3. **Right type, other name**: print `Skip :name` and skip its data.

So on a tape holding a tokenised `X` and then an ASCII `X`, `LOAD "CAS:X"`
prints only `Found:X` and loads the second one, while `CLOAD "X"` loads the
first. Whether the name on screen carries its padding blanks cannot be told
from the screen and is not claimed. Every verb that reads prints these rows,
`OPEN "CAS:" FOR INPUT` and `MERGE` included; nothing prints while writing.

**Ctrl-STOP during the search** is `Device I/O error` (19), which an
`ON ERROR` handler can trap, for `LOAD`, `CLOAD`, `RUN`, `MERGE`, `BLOAD` and
`OPEN` alike.

### The verbs

| verb | does | notes |
|---|---|---|
| `CSAVE "n"[,1\|2]` | writes `&HD3` | the name is required (`CSAVE` is 24); speed 3 is 5 |
| `CLOAD ["n"]`, `CLOAD?` | reads `&HD3` | replaces the program and returns to `Ok`; `CLOAD?` compares instead |
| `SAVE "CAS:n"[,A]` | writes `&HEA` | ends a running program, as a text save does |
| `LOAD "CAS:n"[,R]`, `RUN "CAS:n"` | read `&HEA` | `,R` and `RUN` run it; nothing is printed after the run |
| `MERGE "CAS:n"` | reads `&HEA` | adds the lines to the program |
| `BSAVE "CAS:n",s,e[,x]` | writes `&HD0` | no `,S` on tape: there `S` is a variable used as the run address |
| `BLOAD "CAS:n"[,R]` | reads `&HD0` | an offset on tape is not measured on a reference |
| `OPEN "CAS:n" FOR OUTPUT` / `INPUT` | writes / reads `&HEA` | `PRINT #`, `INPUT #`, `LINE INPUT #`, `INPUT$`, `EOF` work; `APPEND` and random are 56 |

**On a diskless machine** a file name with no device is the cassette:
`LOAD "X"` reads the tape. The channel side of the cassette — directions,
`EOF`, the errors — is on [files-and-devices.md](files-and-devices.md).

## Example

On a tape holding two ASCII programs, `SK` (`10 PRINT"ZQ8"`) and then `RT`
(`10 PRINT"ZQ9"`), rewound:

```
LOAD "CAS:RT"
Skip :SK
Found:RT
LIST
10 PRINT"ZQ9"
```

`CLOAD "RT"` on the same tape would pass both files silently, because
neither is tokenised. This example needs a
cassette, so the example checker does not run it. The same rows — `Skip :SK`
then `Found:RT`, and the listing — are read on the VG-8020, the CF-3300 and
zerobas by `make castail-acceptance`
([cassearch-msx1-characterization.md](../cassearch-msx1-characterization.md)).

## Differences from the reference

No measured difference is open. Not compared, or not measured:

- **A failing tape write, and an ASCII program with a line that has no
  number**, print `load error` here and do not raise a code (part of
  D-LOADERRRET, TIER 3). Ctrl-STOP during a write gave no usable reading on
  either machine with the present rig.
- **The end of the tape without Ctrl-STOP.** The references wait on silence.
  zerobas's `TAPION` gives up after a fixed run of silence, so a dead tape
  ends the search; no row compares the two.
- **`SCREEN ,,,2`.** On the reference it copies the 2400-baud timing table
  into the work area's active cassette slots
  ([spec-cassette.md](../../tape/docs/spec-cassette.md), Phase 3); zerobas's
  `SCREEN` checks the argument and otherwise ignores it. No row compares the
  rate of a save that follows.
- **`LOAD "CAS:"` and a tokenised program.** Joost ruled on 2026-09-27 to keep
  zerobas loading a tokenised program this way; D-CASTYPE (2026-10-08) then
  made the search skip it as the VG-8020 does. He ruled on 2026-10-09: *"if
  we're more compliant with reference now that is fine"* (D-CASTYPERULE,
  closed).

## What we found, and how

- **zerobas printed no `Found:` / `Skip :` rows, and `OPEN "CAS:name"`
  ignored the name** (both fixed 2026-08-07, D-CASSEARCH and D-CASOPEN). Both
  were found by building a cassette instrument for another question
  ([castail-msx1-characterization.md](../castail-msx1-characterization.md),
  [casopen-msx1-characterization.md](../casopen-msx1-characterization.md)).
- **`SAVE "CAS:name"` wrote a tokenised tape** (fixed 2026-08-07, D-CASSAVE):
  decoding both references' recordings showed `$EA` with or without `,A`
  ([cassave-msx1-characterization.md](../cassave-msx1-characterization.md)).
- **A tape zerobas wrote hung the VG-8020** (fixed 2026-09-13, D-CASTAIL2):
  the program block lacked the seven zero bytes a real `CSAVE` writes.
  Diffing the two recordings found it in one reading
  ([`kwdrain_casbytes.out`](../../scratchpad/kwdrain_casbytes.out)).
- **A second program on a real tape could not be loaded** (fixed 2026-09-28,
  D-CASRELOCK). An earlier report had been withdrawn because of a test tape
  with a 16-byte pad that no machine writes.
- **The search did not filter by type, and a named `BLOAD` loaded the first
  binary file** (fixed 2026-10-08, D-CASTYPE, D-CASBIN;
  [`castype_after.out`](../../scratchpad/castype_after.out)). The prediction
  of a `Skip :` row for a wrong-type file missed: there is none.
- **Ctrl-STOP printed `load error` and the program ran on** (fixed
  2026-10-08, D-CASBRK); the VG-8020 raises 19.
- **The reader lost the second block of real recordings**: restarting the
  motor between blocks makes a burst of noise that the leader lock averaged
  in. Real game-tape captures, not synthetic ones, showed it.

## How zerobas does it

The open C-BIOS stubs the cassette read and write entries; zerobas provides
all seven in [tape/tape.asm](../../tape/tape.asm). `tapion` waits for a real
edge, skips the motor's spin-up noise, measures 16 leader half-periods and
sets the 0/1 threshold (`LOWLIM`, `&HFCA4`) at 1.75 times the short one;
`tapout` frames each byte with two stop bits; `stmotr` drives the relay.

The BASIC side shares one search. `cas_capture_name`
([basic/cascap-body.inc](../../basic/cascap-body.inc)) puts the wanted name
in `CAS_WANT`, and `CAS_WANT_ON` says what to look for: bit 0 a name was
given, bit 7 tokenised (`CLOAD`), bit 6 binary (`BLOAD`), neither ASCII.
`cas_open_match` in [basic/casmatch-body.inc](../../basic/casmatch-body.inc),
run as a sub-ROM tenant, reads each header, applies the three rules above
and prints the rows; `cas_skip_data` steps over a file's data according to
its type. `do_tape_prog` in [basic/cload.asm](../../basic/cload.asm) then
loads a tokenised program, relinking its lines because the saved links are
the saving machine's addresses, or hands an ASCII one to `cas_ascii_load`,
which tokenises each line as if typed. A failed search goes to `dpl_dio`,
which stops the motor and raises 19. Writes go through
[basic/save.asm](../../basic/save.asm) and the sub-ROM save tenant; ASCII
output is collected into 256-byte blocks and each block is sent in one go
(`cas_flush_block`), because the tape cannot wait between bytes
([spec-cas-ascii-saveload.md](../../basic/docs/spec-cas-ascii-saveload.md)).

## Related pages

[`CLOAD`](../keywords/CLOAD.md) · [`CSAVE`](../keywords/CSAVE.md) · [`LOAD`](../keywords/LOAD.md) · [`SAVE`](../keywords/SAVE.md) · [`MERGE`](../keywords/MERGE.md) · [`RUN`](../keywords/RUN.md) · [`BLOAD`](../keywords/BLOAD.md) · [`BSAVE`](../keywords/BSAVE.md) · [`OPEN`](../keywords/OPEN.md) · [`EOF`](../keywords/EOF.md) · [`MOTOR`](../keywords/MOTOR.md) · [`SCREEN`](../keywords/SCREEN.md)
— and the concept pages [files-and-devices.md](files-and-devices.md),
[program-text.md](program-text.md) and [errors.md](errors.md).

## Tests that cover it

Every one of these needs a tape, prepared or blank, which the gates mount in
openMSX:

- `make castail-acceptance` — the search rows, two files on one tape, the
  named and bare forms, `OPEN "CAS:"`, and what follows a tape `RUN`.
- `make cassave-acceptance` — the type byte, name and content each save
  verb records, decoded off the recording, on all three machines.
- `make castype-acceptance`, `make casbin-acceptance` — the type filter and
  binary files.
- `make casbrk-acceptance` — Ctrl-STOP during the search, under `ON ERROR`.
- `make cas-ascii-acceptance`, `make eofcas-acceptance`,
  `make casprdir-acceptance` — ASCII files and the tape channel.
- `make tapetail-acceptance`, `make loadtail-acceptance`,
  `make savetail-acceptance` — the option and tail errors on tape.
- `make kwsweep` — `CLOAD` against a prepared tape and `CSAVE` onto a blank
  one, compared byte for byte; `make missing-acceptance` — `MOTOR`.
- `make test` in `tape/` — the signal layer, written and read back at both
  rates ([tape-regression.md](../../tape/docs/tape-regression.md)).
