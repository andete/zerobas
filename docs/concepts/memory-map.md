<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# The memory map — where BASIC keeps things in RAM

> **Status (2026-10-10):** program, variables and arrays sit at the Philips
> VG-8020's addresses and cost the same bytes, but
> zerobas's own workspace leaves a diskless machine 4978 bytes less `FRE(0)`
> (the disk build is 343 short of the National CF-3300; both 267 more since
> channel 0's block, 2026-10-10). Open, TIER 4: D-DIMRESERVE, the `GOSUB`
> frame, D-BOOTKEYS' CTRL.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

BASIC's RAM starts at `&H8000` on both machines. The program
starts at the bottom, its variables and arrays follow it, the stack and the
string space hang down from the top, and what lies between them is the free
memory `FRE(0)` reports. Above BASIC's top (`HIMEM`) come file buffers, the
disk system's work area on a disk machine, and from `&HF380` the system work
area, where the BIOS and BASIC keep their published variables.

Reference: the VG-8020 for BASIC's layout, the CF-3300 for what a disk ROM
adds. zerobas differs at the top: it keeps its own interpreter variables in
`&HE000`–`&HF37F`, RAM the VG-8020 leaves free for programs.

## How it works

### From the bottom up

| region | starts at (published cell) | grows | VG-8020 | zerobas |
|---|---|---|---|---|
| program text | `TXTTAB` `$F676` | up | `$8001` | `$8001` |
| simple variables | `VARTAB` `$F6C2` | up | after the program | the same address |
| arrays | `ARYTAB` `$F6C4` | up | after the variables | the same address |
| free memory | `STREND` `$F6C6` | — | end of the arrays | the same address |
| stack: `FOR`/`GOSUB` frames, expressions | `STKTOP` `$F674` | down | below the string space | below the file blocks |
| string space (`CLEAR n`) | `MEMSIZ` `$F672` (top) | down | below the file blocks | right under the ceiling |
| file blocks (`MAXFILES`) | `FILTAB` `$F860` | — | right under `HIMEM` | between stack and string space |
| BASIC's ceiling | `HIMEM` `$FC4A` | — | `$F380` at boot | `$E000` at boot (diskless) |
| interpreter workspace | — | — | none | `$E000`–`$F37F` |
| system work area | `$F380` | — | BIOS and BASIC | BIOS and BASIC |

The first four rows are the same addresses on both machines, measured in nine
states (start-up, variables, arrays, a string, `ERASE`, a program, a run):
none differs ([`ptrchain_after.out`](../../scratchpad/ptrchain_after.out)).
A numeric variable takes 11 bytes and an array 8 per element plus 8, on both.

The VG-8020's top at start-up, from its own pointers
([`ramlayout_run.out`](../../scratchpad/ramlayout_run.out)): `HIMEM` `$F380`;
two 265-byte file blocks (channel 1, and channel 0 for `LOAD`/`SAVE`) over a
small pointer table; `MEMSIZ` `$F168`; 200 bytes of strings; `STKTOP` `$F0A0`.

### The stack

On both machines one region, growing down from the stack top, holds the Z80
stack, the `FOR`/`GOSUB` frames and expression work; reaching the arrays is
`Out of memory` (error 7). zerobas computes its stack top as the reference
does (ceiling − file blocks − string space). The frames differ in size:

| frame | VG-8020 | zerobas |
|---|---|---|
| one `FOR` | 25 bytes | 11 bytes |
| one `GOSUB` | 7 bytes | 8 bytes |
| inside a `DEF FN` call | 14 bytes | 13 bytes |

([`fremops_run.out`](../../scratchpad/fremops_run.out), 2026-09-26.) So a
program near the end of memory runs out at a different depth.

### What moves the boundaries

| statement | effect, on both machines |
|---|---|
| `CLEAR n` | string space becomes n bytes; the stack top moves down by the difference, and `FRE(0)` with it |
| `CLEAR n,top` | `HIMEM` becomes `top`, `&H8000` to `&HF380` whatever it was at start-up; refused when the program and string space would not fit. zerobas gains no memory above `&HE000`, where its workspace is |
| `MAXFILES=n` | 267 bytes of `FRE(0)` per channel, 0 to 15; `FRE("")` unchanged; open files are closed and variables cleared |
| `DIM`, a new variable | `ARYTAB`/`STREND` move up |
| a program edit | everything above the program moves; variables are cleared |
| `RUN`, `NEW`, `CLEAR` | variables cleared; the string-space size is kept |

### `FRE(0)` on the two machines

Every allocation measured costs the same on both: `CLEAR 1000` 800 bytes,
`DIM A(100)` 816, `DIM A%(100)` 210, a 100-character string 6 (plus 100 of
string space), a 10-line program 270
([`fremem_run.out`](../../scratchpad/fremem_run.out)). Apart from the frames
above, what differs is the starting point. Measured with the same program on all four machines on
2026-09-30 ([`engrow0_run.out`](../../scratchpad/engrow0_run.out)), start-up
`HIMEM` is `$F380` on the VG-8020, `$E000` on zerobas without a disk, `$DE77`
on the CF-3300 and `$DD12` on zerobas with one; zerobas's `FRE(0)` is **4711
bytes below the VG-8020's** without a disk and **76 below the CF-3300's** with
one.

Most of the diskless gap is zerobas's 4992-byte workspace at `$E000`–`$F37F`;
the VG-8020 in turn spends about 270 bytes on channel 0, which zerobas does
not reserve yet. Inside one program, `FRE(0)` also depends on how deep the expression is that
reads it — on the VG-8020 each level of nesting costs a few bytes — so compare
readings taken by the same statement shape (see [`FRE`](../keywords/FRE.md)).

### The disk work area

The CF-3300's disk ROM lowers `HIMEM` at start-up to `$DE77` and keeps 5385
bytes above it. zerobas's disk ROM lowers it by 750 bytes, for its per-channel
disk state (50 bytes for each of 15 channels); its other cells live in
zerobas's own workspace. `&HC000`–`&HDFFF` is MSX-DOS's when the machine boots
MSX-DOS; BASIC and MSX-DOS never run together, so in BASIC it is ordinary
memory (see [msx-dos.md](msx-dos.md)).

### The published variables

Programs `PEEK` and `POKE` the system work area by documented address, and
zerobas keeps the commonly used cells where the reference keeps them: the
pointers above, `HIMEM`, `CURLIN` (`$F41C`), `ERRLIN`, `ERRFLG`, `ONELIN`,
`DEFTBL`, `USRTAB`, `VALTYP`, and the BIOS's own cells (cursor, colours,
`JIFFY`, the key buffers), which C-BIOS maintains.
[docs/ram-map.md](../ram-map.md) lists every one.

A watchpoint comparison (D-RAMFOOT, 2026-09-24) found 29 published variables
the VG-8020 writes and zerobas did not. Joost ruled *"All 29"*: keep them all
at the published address, scratch included. Where they stand:

| | variables |
|---|---|
| now kept, matching | `VARTAB`† `ARYTAB` `STREND` `TEMPST` `TEMPPT` `DAC` `FBUFFR` `RNDX` `TTYPOS` `FNKSWI` `ATRBYT` `CNSDFG` |
| already read the same | `PRTFLG` `DIMFLG` `SUBFLG` `PRMFLG` `PTRFIL` `ESCCNT` `GRPHED` |
| a stated difference (Joost, 2026-09-25: *"Stop here"*) | `ENDFOR` `TEMP` `ARYTA2` `DSCTMP` `ARG` `DECCNT` `HOLD` `HOLD2` `HOLD8` `LINWRK` |
| not yet | `FRETOP` |

† not one of the 29; it moved with the pointers. The stated ten are the
reference's internal pointers and scratch. Partly matched: `DAC` holds floats
and `USR`'s argument, but integers reach `DAC+2` only for `USR`; `FBUFFR`
holds a printed float's text, not an integer's (after `STR$`, one space more).

## Example

```
10 T=0:V=0:A=0:S=0
20 T=PEEK(&HF676)+256*PEEK(&HF677)
30 V=PEEK(&HF6C2)+256*PEEK(&HF6C3)
40 A=PEEK(&HF6C4)+256*PEEK(&HF6C5)
50 DIM Q(9)
60 S=PEEK(&HF6C6)+256*PEEK(&HF6C7)
70 PRINT T;A-V;S-A
80 X=PEEK(&HF678)+256*PEEK(&HF679)
90 PRINT HEX$(X)
100 CLEAR 500:PRINT FRE("")
RUN
 32769  44  88
F67A
 500
```

The program starts at `&H8001` (32769); four numeric variables take 44 bytes
and `Q(9)` 88; `TEMPPT` points at the empty temporary pool; `CLEAR 500` makes
a 500-byte string space. Nothing here depends on `HIMEM`, which differs.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_memory-map.out`](../../scratchpad/kwdoc_memory-map.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

- **Less free memory on a diskless machine** (TIER 4): 4978 bytes, above
  ([`fcb0_run.out`](../../scratchpad/fcb0_run.out),
  [`fcb0_disk.out`](../../scratchpad/fcb0_disk.out)).
  A program that just fits on the VG-8020 does not fit here; `CLEAR 25000` is
  accepted there and `Out of memory` here.
- **`DIM` leaves a little more room unused** (D-DIMRESERVE, TIER 4): sized to
  leave `K` bytes of `FRE(0)`, a `DIM` fits on the VG-8020 down to `K` = 110 and
  here down to 140 (it was 280 until 2026-10-10). zerobas keeps 116 bytes for its
  own stack below the top of memory, the deepest it goes without its formula
  check plus room to spare; the remaining 30 bytes are its deeper stack. A
  program line is stored to exactly the VG-8020's edge
  ([gate](../../probes/basic/basic_probe_dimedge.py)). Joost ruled on 2026-10-09
  to match the reference ([`DIM`](../keywords/DIM.md)).
- **Frame sizes** (table above). Joost ruled on 2026-09-27 that zerobas should
  never be worse; only `GOSUB` (8 against 7) is, and making it 7 turned out to
  be a redesign — that choice is back with him.
- **`STKTOP`, `MEMSIZ` and `FRETOP` are not published.**
- **SHIFT or CTRL held at start-up** (D-BOOTKEYS, TIER 4): as Joost recalls,
  on a disk MSX they skip parts of the disk system to free memory. Not yet
  measured on either machine.

## What we found, and how

- **Channel 0 had no block, and the blocks sat the other way round** (fixed
  2026-10-10, D-FCBSHAPE). Both references keep a block for channel 0 — the
  one `LOAD` and `SAVE` use — at every `MAXFILES`, `0` included, and put the
  2-byte pointer table *below* the blocks, so the top block stays put as
  `MAXFILES` grows and `VARPTR(#1)` moves by 265
  ([`fcb0_run.out`](../../scratchpad/fcb0_run.out)). zerobas now does both:
  `VARPTR(#0)` is an address, and every program has 267 bytes less `FRE(0)`,
  as on the references.
- **8 KB was reserved for nothing** (fixed 2026-09-01, D-RECLAIM): MSX-DOS's
  area was kept free in BASIC too. Joost ruled *"BASIC and DOS never
  co-exist"*; `FRE(0)` rose by 8192 ([spec-reclaim.md](../spec-reclaim.md)).
- **`HIMEM` said `$F380` while zerobas used the RAM under it** (fixed
  2026-09-25, D-HIMEMLIE): machine code put just under it would have hit the
  interpreter. Joost ruled *"truthful"*; it now starts at zerobas's ceiling.
- **A 1280-byte listing buffer was dropped** (2026-09-26, Joost: *"Drop
  DETOKBUF"*): the ceiling rose to `&HE000` ([spec-detokbuf-drop.md](../spec-detokbuf-drop.md)).
- **There were two stacks** (merged 2026-09-12, D-SPMERGE, Joost: *"the most
  compatible one"*). The Z80 stack sat in a few hundred bytes at the top, so a
  formula 16 parentheses deep wrecked the machine, where both references go
  32 deep ([spec-basic-spmerge.md](../spec-basic-spmerge.md)).
- **Joost's hunch that the reference is "very economical" with RAM held**:
  fewer cells written on 12 of 16 operations, 527 against 843 (D-RAMFOOT,
  [`ramfoot_run.out`](../../scratchpad/ramfoot_run.out)).
- **A file channel cost 306 bytes** (fixed 2026-09-30, D-FCBSHAPE): blocks now
  have the reference's 265-byte shape and cost 267, as on both references.
- **A comment said 376 bytes of workspace were spare; 10 were** (2026-08-22,
  [deffn-ramhunt-2026-08-22.md](../deffn-ramhunt-2026-08-22.md)); the map is
  now generated from the source and checked.

## How zerobas does it

Every RAM cell is declared in [basic/sysvars.inc](../../basic/sysvars.inc)
(and `disk/equates.inc`, `sub/`); [tools/ram_map.py](../../tools/ram_map.py)
generates [docs/ram-map.md](../ram-map.md) from them.

The boundaries are derived, not stored, in
[sub/strheap.asm](../../sub/strheap.asm): `strheap_ceiling` is the lower of
`HIMEM` and `TXTMAX` (`$E000`); `strheap_floor` subtracts the string space;
`strheap_chantab` subtracts `MAXFILES` × 267; `strheap_varceil` is the stack
top. `strheap_ctllim` stores the two that are needed on every push — the
published `STREND` and `CTLLIM`, the stack's floor — and `ctl_alloc` in
[basic/str-engine.asm](../../basic/str-engine.asm) refuses a frame that would
reach it, keeping a reserve for the Z80 stack. The cold start in
[basic/interp.asm](../../basic/interp.asm) sets `HIMEM` to `TXTMAX` unless a
disk ROM has already lowered it (`install_basic_hooks`,
[disk/kernel.asm](../../disk/kernel.asm)); `CLEAR` checks and records its two
arguments in [basic/clear.asm](../../basic/clear.asm).

## Related pages

- Keywords: [`FRE`](../keywords/FRE.md), [`CLEAR`](../keywords/CLEAR.md),
  [`VARPTR`](../keywords/VARPTR.md), [`PEEK`](../keywords/PEEK.md),
  [`POKE`](../keywords/POKE.md), [`DIM`](../keywords/DIM.md),
  [`OPEN`](../keywords/OPEN.md) (`MAXFILES`), [`USR`](../keywords/USR.md),
  [`BLOAD`](../keywords/BLOAD.md).
- Concepts: [strings-and-string-space.md](strings-and-string-space.md),
  [variables.md](variables.md), [program-text.md](program-text.md),
  [files-and-devices.md](files-and-devices.md), [msx-dos.md](msx-dos.md).
- More keywords: [`GOSUB`](../keywords/GOSUB.md).

## Tests that cover it

- `make ram-map-check` — the generated map matches the source.
- `make ramfree-acceptance`, `make txtceil-acceptance`, `make ctllim-acceptance`
  — zerobas's own map: declared spans really hold what they claim, the program
  stops at the string space, the stack stops at the arrays.
- `make parennest-acceptance` — deep expressions; `make clearpool-acceptance`,
  `make binfre-acceptance` — what `CLEAR` and `FRE` see.
- `make chancost-characterize`, `make fcbhdr-acceptance` — a file channel's
  cost and block.
- `make fcb0-acceptance` — channel 0's block, the stride and the blocks' order.
- `make sysvarsweep`, `make kwram` — the documented work-area cells, and RAM
  usage per keyword, against the reference.
