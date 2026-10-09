<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `BSAVE` — save a block of memory to a file

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error not yet proven. No known
> divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`BSAVE "file",start,end` writes the bytes from `start` to `end` (both
included) to a file, with a header that lets [`BLOAD`](BLOAD.md) put them back
in the same place. An optional fourth address says where `BLOAD ...,R` should
start running them. It works on disk (the reference is the National CF-3300)
and on cassette (the Philips VG-8020).

## Syntax

```
BSAVE <file name>,<start>,<end>[,<exec>]
BSAVE <file name>,<start>,<end>,S          (disk only: save video memory)
```

The file name is a string expression and may carry a device (`"A:X.BIN"`,
`"CAS:X"`). The addresses are numeric expressions; a hexadecimal literal such
as `&HC800` is the usual way to write them.

## Details

- **The file is a 7-byte header plus the bytes.** The header is `&HFE`, then
  the start, end and exec addresses, low byte first.
- **The exec address defaults to the start.** With a fourth argument of
  `&HC900` on a block saved from `&HC800`, the header's seventh byte (the
  exec's high byte) reads 201; without it, 200.
- **The exec address can be a variable**: `BSAVE "F",&HC000,&HC00F,Q` saves
  with exec = Q.
- **`,S` saves video memory — on disk only.** On a disk `,S` is the VRAM flag,
  and `,SX` is `Syntax error`. On cassette there is no flag: in
  `BSAVE "CAS:X",&HC000,&HC010,S` the `S` is a variable used as the exec
  address, on both reference machines.
- **The exec is checked like an address**: `70000` is `Overflow` (6) and
  `"A"` is `Type mismatch` (13), and on disk the file is then not created.
- **The rest of the line runs**: `BSAVE "X.BIN",A,B:PRINT "saved"` prints.
- **An open output file is left alone**: a `BSAVE` between two `PRINT #1`s
  does not disturb the file being written on channel 1.
- **On a diskless machine** a name with no device goes to the cassette, and
  a drive name (`"A:X"`) is `Bad file name` (56).

### Errors

| situation | error |
|---|---|
| the end address left out (`BSAVE "X.BIN",&HC000`) | 2 `Syntax error` |
| a fifth argument | 2 `Syntax error` |
| a string as an address (`BSAVE "X.BIN","A",1`) | 13 `Type mismatch` |
| a number instead of a name (`BSAVE 5,1,2`) | 13 `Type mismatch` |
| an exec past 65535 | 6 `Overflow` |
| a drive name on a diskless machine | 56 `Bad file name` |

The enumerated set is {2, 13} for both forms, the same on both machines.

## Example

```
10 ON ERROR GOTO 110
20 A=&HC800
30 FOR I=0 TO 4:POKE A+I,65+I:NEXT
40 BSAVE "ABC.BIN",A,A+4
50 FOR I=0 TO 4:POKE A+I,0:NEXT
60 BLOAD "ABC.BIN"
70 FOR I=0 TO 4:B$=B$+CHR$(PEEK(A+I))
80 NEXT:PRINT B$
90 BSAVE "X.BIN",A
100 END
110 PRINT "Error";ERR:RESUME NEXT
RUN
ABCDE
Error 2
```

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_bsave.out`](../../scratchpad/kwdoc_bsave.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

**Every error** is not yet ticked: re-measured on 2026-10-07 every case of
`BSAVE`'s error set agrees with the CF-3300
([`t6enum_b8_zb_1007.out`](../../scratchpad/t6enum_b8_zb_1007.out)), but the
keyword sweep does not yet carry a row for each code of each form, which the
rung requires. **RAM usage** is not yet proven either.

## What we found, and how

- **A variable exec address was refused** (fixed 2026-10-07, D-BSAVEVAR).
  `BSAVE "F",&HC000,&HC00F,Q` printed `load error` and saved nothing; both
  references save with exec = Q
  ([`bsavevar_before.out`](../../scratchpad/bsavevar_before.out)).
- **Bad tails on cassette printed `load error`** (fixed 2026-10-07,
  D-TAPETAIL), and measuring them showed that a tape `BSAVE` has no `,S` flag
  on either reference — `S=70000` first makes it `Overflow`, which only a
  variable can do ([`tapetail_after.out`](../../scratchpad/tapetail_after.out)).
- **A disk `BSAVE` beside an open output file emptied that file** (fixed
  2026-10-03, D-ASAVECHAN): the save streamed through the same buffers as the
  open channel, and the CF-3300's file came back whole where ours was 0 bytes.
- **`BSAVE` ended the line** (fixed 2026-09-28, D-SAVECOLON).
- **The file name had to be a literal** (fixed 2026-08-21, D-FNEXPR2); it is a
  string expression on both references.

## Where it lives

- `do_bsave`, `bsave_opt4` (the disk fourth argument) and `bsave_opt4_cas`
  (the tape one) in [basic/save.asm](../../basic/save.asm), which hands the
  write to the sub-ROM's save tenant through `sv_tenant`.
- The write itself: [basic/sv-bsvdisk.inc](../../basic/sv-bsvdisk.inc) (disk)
  and [basic/sv-bsvcas.inc](../../basic/sv-bsvcas.inc) (tape), assembled into
  [sub/save.asm](../../sub/save.asm).

## Related concepts

- [The cassette](../concepts/cassette.md) — files on tape, and how BASIC finds them

## Tests that cover it

- `make kwsweep` — a round trip through the disk (save, overwrite, load, read
  back), the exec address read out of the header, `,R` running what was saved,
  `,S` with `BLOAD`, the error row for a missing end address, and `BSAVE`
  followed by more statements.
- `make bsavevar-acceptance` — a variable as the exec address, and `,SX`.
- `make tapetail-acceptance` — the cassette tails and the exec typed as an
  address, on both references.
- `make asavechan-acceptance` — `BSAVE` beside an open output channel.
- `make nodiskverbs-acceptance` — the diskless machine.
- `make kwram` — the RAM-usage comparison.
