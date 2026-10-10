<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `BLOAD` — load a binary file into memory

> **Status (2026-10-10):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`BLOAD "file"` reads a file written by [`BSAVE`](BSAVE.md) back into memory,
at the address stored in the file. With `,R` it then runs the loaded machine
code; with `,S` (Disk BASIC) it loads into video memory instead. It works on
disk (the reference is the National CF-3300) and on cassette (the Philips
VG-8020). zerobas loads the same bytes to the same place and raises the same
errors in every case we have measured.

## Syntax

```
BLOAD <file name>[,R][,S][,<offset>]
```

The file name is a string expression (`BLOAD A$` works) and may carry a device:
`"A:X.BIN"` for a drive, `"CAS:X"` for the cassette.

## Details

- **The file says where it goes.** A BSAVE file starts with a 7-byte header:
  the byte `&HFE`, then the start, end and run (exec) addresses. `BLOAD` puts
  the bytes from the start address up to the end address.
- **`,R` runs the code** at the exec address once it is loaded. Six bytes of
  machine code saved with BSAVE and reloaded with `BLOAD "R.BIN",R` run, and a
  plain `BLOAD` of the same file does not.
- **`,S` loads into video memory**: the header's addresses are taken as VRAM
  addresses (`&HC800` wraps to 2048 in the 16 KB VRAM), and `VPEEK` reads the
  bytes back.
- **The offset** is added to the start, end and exec address alike:
  `BLOAD "X.BIN",&H1000` loads 4096 bytes higher, and with `,R` runs the code
  at its moved exec address. The offset is an address (−32768 to 65535), and
  the sum wraps round 64 KB: a file saved at `&HC000` loads at `&HB000` with an
  offset of `&HF000` or of `61440`. A variable works too: in
  `BLOAD "X.BIN",Q` the `Q` is the offset.
- **The tail is checked before the file is looked up**: `BLOAD "NOSUCH.BIN","A"`
  is `Type mismatch` (13), not `File not found`.
- **The rest of the line runs**: `BLOAD "X.BIN":DEFUSR=&HC000` works.
- **On cassette** (`BLOAD "CAS:name"`), the tape is searched by name and only
  binary files count: a BASIC program of the same name is stepped over without
  a word. The search prints `Skip :` for each binary file passed over and
  `Found:` for the one taken, as on the VG-8020. Without a name the next binary
  file is taken. A tape search that is broken with Ctrl-STOP is
  `Device I/O error` (19); a file that is not on the tape is not an error —
  the machine keeps searching.
- **On a diskless machine** a name with no device reads the cassette, and a
  drive name (`"A:X"`) is `Bad file name` (56).

### Errors

| situation | error |
|---|---|
| the file does not exist on the disk | 53 `File not found` |
| the file exists but is not a BSAVE file (no `&HFE` first byte), even if it is called `.BIN` | 61 `Bad file mode` |
| a number instead of a name (`BLOAD 5`) | 13 `Type mismatch` |
| a string as the offset | 13 `Type mismatch` |
| an offset past 65535 (`70000`) | 6 `Overflow` |
| no name at all (`BLOAD`) | 24 `Missing operand` |
| a tape search broken with Ctrl-STOP | 19 `Device I/O error` |
| a drive name on a diskless machine | 56 `Bad file name` |

The disk set the sweep checks per form is {13, 24, 53} for the plain load and
{53} for `,R` and `,S`; both machines agree on all of them.

## Example

On a disk holding `PROG.BIN`, a BSAVE file of 50 bytes at `&HC000` whose
first byte is 62 and last byte 31, and `HI.TXT`, a text file:

```
10 ON ERROR GOTO 90
20 POKE &HC000,7
30 BLOAD "PROG.BIN"
40 PRINT PEEK(&HC000);PEEK(&HC031)
50 BLOAD "PROG.BIN",&H100
60 PRINT PEEK(&HC100)
70 BLOAD "HI.TXT"
80 BLOAD "NONE.BIN":END
90 PRINT "Error";ERR:RESUME NEXT
RUN
 62  31
 62
Error 61
Error 53
```

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_bload.out`](../../scratchpad/kwdoc_bload.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**. Not yet measured on a
reference: an offset on the cassette (`BLOAD "CAS:X",&H1000`; the tape load
applies it through the same code as the disk load, but no tape here holds a
saved binary to try it on).

## What we found, and how

- **The clock stopped while the disk worked** (fixed 2026-10-10, D-BLDI):
  a long `BLOAD` from disk kept `TIME` running for none of its work here,
  against 48 % on the CF-3300; now 45 %. After the first sector every disk transfer came back with
  interrupts off, so keys typed meanwhile were lost too; now each one gives
  back the state it found ([before](../../scratchpad/verbclock_run.out),
  [after](../../scratchpad/verbclock_bldi.out)). `make loaddi-acceptance`
  has a `bload` row.

- **A named tape `BLOAD` loaded the wrong file, silently** (fixed 2026-10-08,
  D-CASBIN). It never looked at the name: with two binaries on the tape,
  `BLOAD "CAS:X"` loaded whichever came first. It now searches like every
  other tape verb, prints the same `Found:` and `Skip :` rows as the VG-8020,
  and the other tape loaders step over binary files instead of stopping on
  them ([`casbin_before.out`](../../scratchpad/casbin_before.out)).
- **The offset was not implemented** (fixed 2026-10-07, D-BLOADOFS). The
  CF-3300 took `BLOAD "X.BIN",Q` as "load at offset Q"; zerobas refused it.
  Measuring the offset showed it moves the exec address too, wraps round
  64 KB, and is parsed before the disk is touched
  ([`bloadofs_after.out`](../../scratchpad/bloadofs_after.out)).
- **`BLOAD` ended the line** (fixed 2026-09-28, D-SAVECOLON), so
  `BLOAD "X.BIN":DEFUSR=&HC000` never set the `USR` address.
- **A file that is not a BSAVE file printed `load error` and carried on**
  (fixed 2026-08-21, D-BLMODE). The CF-3300 raises `Bad file mode` (61) and
  stops; the rule is about the `&HFE` first byte, not the `.BIN` name.
- **A missing file printed `load error` instead of raising `File not found`**
  (fixed 2026-08-21, D-BLNF), so an `ON ERROR` handler never saw it. The file
  name became a string expression the same day (D-FNEXPR2).

## Where it lives

- Main ROM: `do_bload` and `pcr_bload` in
  [basic/bload.asm](../../basic/bload.asm) evaluate the name and parse the
  whole tail (`,R`, `,S`, offset), then call the sub-ROM; the `,R` jump into
  the loaded code is made here, because it never returns.
- Sub-ROM: the load itself is [basic/bload-body.inc](../../basic/bload-body.inc),
  run from the BLOAD tenant in [sub/bload.asm](../../sub/bload.asm): the disk
  read, the tape read, and `bl_apply_ofs` for the offset.
- The tape search: `cas_capture_name` in
  [basic/cascap-body.inc](../../basic/cascap-body.inc) and the matcher in
  [basic/casmatch-body.inc](../../basic/casmatch-body.inc).

## Related concepts

- [The cassette](../concepts/cassette.md) — files on tape, and how BASIC finds them
- [The memory map](../concepts/memory-map.md) — where BASIC keeps things in RAM

## Tests that cover it

- `make kwsweep` — the plain, `,R` and `,S` rows, the error rows, and
  `BLOAD` followed by more statements on the same line.
- `make bloadofs-acceptance` — the offset: relocation, wrap-round, exec, order
  of checks, and the diskless `BLOAD "CAS:X","A"`.
- `make casbin-acceptance` and `make castype-acceptance` — the tape search by
  name and by file type, against the VG-8020.
- `make casbrk-acceptance` — Ctrl-STOP during the tape search.
- `make dskmsg-acceptance` — the missing-file and wrong-kind-of-file errors.
- `make nodiskverbs-acceptance` — the diskless machine.
- `make kwram` — the RAM-usage comparison.
