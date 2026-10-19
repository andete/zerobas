<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `BLOAD` — load a binary file into memory

> **Status (2026-10-14):** level 3 — happy path ✓ · reasonable time ✓ · common
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
  plain `BLOAD` of the same file does not. The code is CALLED: when it
  returns, the rest of the line runs, so `BLOAD "CAS:",R:BLOAD "CAS:",R` loads
  and runs two parts in turn, as tape loaders often do.
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

- **A tape `BLOAD"CAS:…",R,offset` jumped to the wrong address** (fixed
  2026-10-19, D-CASOFS2X). The bytes landed at start + offset, as on the
  reference, but the tape path added the offset a second time after the data,
  so `,R` ran exec + 2 × offset. Our own tape of a few bytes of code, with a
  decoy where the doubled address pointed, showed it: the VG-8020 runs the
  loaded code and zerobas ran the decoy. A disk `BLOAD` never had it. Found
  by reading the code while the disk path moved into the disk ROM.
- **A bad drive or file name now gives the reference's error** (fixed
  2026-10-19, with the disk load's move into the disk ROM): `BLOAD"Q:X.BIN"`
  is `Bad drive name`, `BLOAD""` and `BLOAD"A:"` are `Bad file name`, as on
  the CF-3300. zerobas used to carry on with a stale file name.
- **A `,R` program that loads a bigger BASIC program left the variables
  behind** (fixed 2026-10-17, D-HFOXOOM). Harry Fox's loader moves the
  program end (`VARTAB`) and then types `RUN30`; zerobas took the new end
  but kept its variable chain where the old program ended, now inside the
  new program's text, and `RUN` read that as arrays: `Out of memory in 30`.
  When the code moves `VARTAB`, the variables now start empty at the new end;
  on the VG-8020 they are unusable then too, until the `RUN`
  (`basicint-acceptance` row `rvtarr`).
- **A tape name with a dot found nothing** (fixed 2026-10-17, D-CASDOT). On
  the VG-8020 a `.` ends the name: `BLOAD "CAS:AB.C"`, and a bare
  `BLOAD "AB.C"` on a diskless machine, look for `AB`. zerobas kept the dot as
  part of the name, so Harry Fox's loader, which asks for such a name, skipped
  every file to the tape's end. Nothing before the dot (`"CAS:.AB"`) is
  `Bad file name` (56) on both (`casbin-acceptance` rows `bdot`, `blead`).
- **A load into the top of memory could break the BASIC that runs next**
  (D-WSZERO, 2026-10-14 to 2026-10-16, done). A diskless
  VG-8020 leaves `&HECF8`–`&HF37F` to programs; zerobas kept its own state
  there, and tape loaders do `CLEAR n,&Hxxxx` and load right over it. Moving
  that state out, one group at a time, fixed in turn: the load itself
  stopping with `Device I/O error`, an error or `RESUME` after the load, `READ`,
  `PAINT`, `DRAW`'s scale, a `"A:X"` name, a `CRT:` channel left open across
  the load, the cursor of the next `INPUT`, `DEF FN` later on the `BLOAD`'s own
  line, `CONT`, the `Ok` after the program ends, a string variable reading
  back garbage when the loaded bytes happened to look like a `FIELD` entry, and
  `LSET` / `ERASE` touching the disk's field table. The test loads over the
  whole range and then runs each of these
  ([`wszero_s10_rows.out`](../../scratchpad/wszero_s10_rows.out)). Since
  2026-10-16 none of zerobas's state is left there and the ceiling is
  `&HF380`, so a loader that does *not* `CLEAR` first finds the stack where the
  VG-8020 has it: a load at `&HE000`–`&HF07F` without `CLEAR` stopped the
  program on zerobas and now runs as on the VG-8020
  ([`wszero_s15_before.out`](../../scratchpad/wszero_s15_before.out),
  [`wszero_s15_rows.out`](../../scratchpad/wszero_s15_rows.out), `noclear3`).
- **A `,R` program that loads a BASIC program lost it to its own variables**
  (fixed 2026-10-15, D-VARTABADOPT). Some loaders' machine code loads the next
  BASIC program and sets the end-of-program pointer (`VARTAB`, `&HF6C2`)
  themselves, as the reference expects. zerobas kept the program's end in its
  own place and, at the next `CLEAR` or `RUN`, put `VARTAB` back where its own
  record said -- so variables were stored over the program. Now the end that
  the `,R` code set is kept, as on the VG-8020.
- **Some games' `,R` code jumps into BASIC's own ROM** (supported 2026-10-15,
  D-BASICINT). Three tape titles jump to addresses no published table names:
  one runs the BASIC program it has just loaded (the reference's `RUN` at
  `$73AC`), one drops its return address and continues the `BLOAD` statement
  at `$6CF3`, and one uses a two-byte `pop hl / ret` at `$3297`. Each was
  measured from the outside on the VG-8020 with our own test code, and zerobas
  now has the same behaviour at the same addresses. Loopy Laundry loads and
  runs; before, these jumps landed on unrelated code.
- **After `BLOAD ...,R` the rest of the line was dropped** (fixed 2026-10-14,
  D-BLOADRTAIL). zerobas jumped to the loaded code instead of calling it, so
  when the code returned, the line ended there, and inside a program the
  program stopped. On the VG-8020 `BLOAD "CAS:T",R:PRINT "OK"` prints `OK`.
  Found by loading commercial tapes on both machines: several loaders run one
  part with `,R` and then carry on in BASIC, and here they stopped at the prompt
  after `Found:`.
- **Ctrl-STOP could not break a tape read once the file was found** (fixed
  2026-10-11, D-CASRBRK). The VG-8020 stops the read and says `Device I/O
  error` (19); zerobas read on to the end, because its cassette routines
  never looked at the keyboard after the search
  ([`casrbrk_diag.out`](../../scratchpad/casrbrk_diag.out)).
  Broken in the six bytes that give the load addresses, `BLOAD` read
  garbage for them and loaded the tape over the wrong memory — the screen
  came back as noise. Under `ON ERROR` the VG-8020 raises 19 in the line.
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
  whole tail (`,R`, `,S`, offset), then call the sub-ROM. For a disk file main
  then hands the load to the disk ROM through the `$FE5D` hook, the one the
  CF-3300's BLOAD uses too. The `,R` call into the loaded code is made here,
  after either load.
- Sub-ROM: [basic/bload-body.inc](../../basic/bload-body.inc), run from the
  BLOAD tenant in [sub/bload.asm](../../sub/bload.asm), decides between tape
  and disk, reads the tape (with `bl_apply_ofs` for the offset), and for a disk
  file builds its 8.3 name.
- Disk ROM: `hk_dpbload` in [disk/kernel.asm](../../disk/kernel.asm) reads a
  disk file (since 2026-10-19; the sub-ROM did this before): the `&HFE` header,
  the offset, and the bytes into RAM, or into VRAM for `,S`.
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
- `make casrbrk-acceptance` — the tape read broken with Ctrl-STOP, in the
  header leader and in the data.
- `make basicint-acceptance` — the three addresses games jump to after `,R`,
  against the VG-8020; `make pin-check` keeps them at those addresses.
- `make bloadrtail-acceptance` — what runs after `BLOAD "CAS:...",R`: the rest
  of the line, the next program line, and two `,R` loads in one line, with
  tapes the test builds itself.
- `make kwram` — the RAM-usage comparison.
