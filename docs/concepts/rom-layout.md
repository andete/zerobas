<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: verify=no reason="no example" -->

# ROM layout — how zerobas is put together

> **Status (2026-10-09):** the parts a program can see — the published BIOS
> entry points, the slot conventions, the hooks and their addresses — follow
> the published MSX interfaces; where the code sits inside the ROMs is
> zerobas's own and differs from a real MSX by design. Open: `RST 8` (SYNCHR)
> is still C-BIOS's debug stub (D-SYNCHR, TIER 6), and the disk ROM's
> SHIFT/CTRL boot options are not built (D-BOOTKEYS, TIER 4).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

On a real MSX1 the BIOS and MSX-BASIC share one 32 KB ROM in slot 0, and a
disk interface brings its own ROM with Disk BASIC in it. zerobas has the same
shape, built from three ROMs:

- **the main ROM** in slot 0 (`$0000`–`$7FFF`): the open-source C-BIOS in the
  low part, zerobas's interpreter in the rest;
- **a sub-ROM** in slot 3-2: 32 KB of interpreter code that did not fit in the
  main ROM;
- **a disk ROM** in slot 3-1, on the disk machine only: Disk BASIC and the
  MSX-DOS kernel.

The same main ROM and sub-ROM run on both targets: the diskless machine
(compared with the Philips VG-8020) has nothing in slot 3-1. A program sees
none of this except through published addresses — work-area variables, hooks,
BIOS entry points — and those are where a real MSX has them.

## How it works

### The slots

| slot | page 0 `$0000` | page 1 `$4000` | pages 2–3 |
|---|---|---|---|
| 0 | C-BIOS + the low part of BASIC | BASIC (`"AB"` header at `$4000`) | C-BIOS logo ROM (page 2) |
| 1, 2 | | cartridge slots | |
| 3-0 | RAM | RAM | RAM |
| 3-1 | | disk ROM (disk machine only) | |
| 3-2 | sub-ROM, page 0 | sub-ROM, page 1 | |
| 3-3 | empty | empty | empty |

Slot bytes: `$83` RAM, `$87` disk ROM, `$8B` sub-ROM (the 2026-07-11 slot
map, [spec-basic-subrom.md](../spec-basic-subrom.md)).

### C-BIOS, and zerobas as a patch next to it

C-BIOS is an open BIOS with no BASIC; it leaves page 1 of slot 0 empty, which
is where a real MSX keeps BASIC. zerobas ships as a patch against a stock
C-BIOS ROM (`zerobas-main-eu.ips` / `.bps`), never as a copy of it, so the two
stay separate trees ([README](../../README.md), *How it runs*). The patch:

- puts the interpreter at `$2765`–`$7FFF`. The part below `$4000` was C-BIOS's
  own, freed by removing its placeholder BASIC code and two boot messages
  zerobas can never print;
- puts more BASIC code into four runs of padding inside C-BIOS ("islands",
  [basic/islands.asm](../../basic/islands.asm));
- changes C-BIOS in a few places: small source patches in
  [cbios-repack/](../../cbios-repack/README.md) (the INS, DEL, HOME and CTRL
  keys, a scroll fix, one new hook), and a few bytes overwritten directly
  (the `RST $10` and `RST $18` vectors, and the cursor column `TTYPOS`, which
  C-BIOS kept one higher than the VG-8020 does).

C-BIOS's boot scan finds the `"AB"` header at `$4000` and calls zerobas's
INIT, which never returns: it ends at the BASIC prompt. So zerobas finishes the
boot scan itself, calling the INIT of every `"AB"` ROM in the remaining slots
— that is how the disk ROM installs its hooks
([basic/initext.asm](../../basic/initext.asm)). The sub-ROM is found by its
`"CD"` signature, and its slot is written to `EXBRSA` (`&HFAF8`), the
published MSX2 cell for it.

### The published BIOS entry points

C-BIOS's published entry points in page 0 keep their addresses, and zerobas
calls them as any program would: `SCREEN` calls `CHGMOD`, `COLOR` calls
`CHGCLR`, `CLS` calls `CLS`, inter-slot calls go through `CALSLT`. Joost's
rule of 2026-10-04: *a published BIOS entry point keeps its published
contract* — zerobas may implement one, never repurpose it. So `RST $10`
(`CHRGTR`) and `RST $18` (`OUTDO`) point at zerobas's own routines, because
C-BIOS's `$0010` returns HL past the character instead of on it; each calls
its published hook (`H.CHRG`, `H.OUTD`) first. A proposal to point `RST $08`
(`SYNCHR`) at a byte-saving dispatcher was rejected under the same rule.

### The hooks

The hook area is a run of 5-byte cells in RAM from `&HFD9A`; C-BIOS fills it
with `RET` (`$C9`) at boot. A ROM *claims* a hook by writing an inter-slot call
into its cell: `F7 <slot> <low> <high> C9` (`RST 30h`, slot byte, address,
`RET`). An unclaimed cell returns at once and leaves the carry flag as the
caller set it, which is how BASIC tells that nobody answered.

Disk BASIC is built on this, on the CF-3300 and on zerobas alike. The main
ROM owns the keyword table, so a diskless machine still knows `FILES` or
`MKI$`; running one calls its hook, which the disk ROM has claimed — or, with
no disk ROM, is a `RET`, and the answer is `Illegal function call`, as on the
VG-8020. Some of the cells zerobas's disk ROM claims:

| hook | address | for |
|---|---|---|
| `H.PHYD` | `&HFFA7` | the standard sector call, for MSX-DOS and other hosts |
| `H.NAME`, `H.KILL`, `H.COPY` | `&HFDF9`, `&HFDFE`, `&HFE08` | `NAME`, `KILL`, `COPY` |
| `H.DSKF`, `H.DSKI`, `H.DSKO` | `&HFE12`, `&HFE17`, `&HFDEF` | `DSKF`, `DSKI$`, `DSKO$` |
| `H.FILE` | `&HFE7B` | `FILES`, `LFILES` |
| `H.LSET`, `H.RSET`, `H.FIEL` | `&HFE21`, `&HFE26`, `&HFE2B` | `LSET`, `RSET`, `FIELD` |
| `H.MKI$` … `H.CVD` | `&HFE30`–`&HFE49` | `MKI$`, `MKS$`, `MKD$`, `CVI`, `CVS`, `CVD` |
| `H.ERRP` | `&HFEFD` | the messages of disk errors 66 and 68–70 |
| `H.FORM` | `&HFFAC` | `CALL FORMAT` |

Every row is among the 35 cells the CF-3300's disk ROM claims, all pointing
into its page 1; the verb rows were also checked by writing a `RET` into the
cell there and watching the keyword answer `Illegal function call`. The main
ROM claims two hooks itself: `H.TIMI` (`&HFD9F`, the frame interrupt), which
drives `PLAY` and the `ON … GOSUB` traps, and `H_ZKEY` (`&HFFCF`), which is
not a standard hook (see *Differences*).

### The sub-ROM and its tenants

Each piece of code in the sub-ROM is a **tenant**: an entry in one of two jump
tables, one per page, which the main ROM calls with `CALSLT` by its index. A
call maps only the page it calls, so the two pages behave differently:

| | page-0 tenant | page-1 tenant |
|---|---|---|
| switched out while it runs | the BIOS and the low part of BASIC | main page 1 (most of BASIC) |
| still visible | main page 1, RAM | the BIOS, the low part of BASIC, RAM |
| examples | the tokeniser, the `LIST` detokeniser, arrays, the string heap, the graphics engine, `DEF FN`, `READ` | the maths functions, `PLAY`'s parser, the screen editor's line reader, `BLOAD`, `SAVE`, the error messages |

On 2026-10-09 the page-0 table had 19 rows and the page-1 table 29, test
entries included ([sub/sub.asm](../../sub/sub.asm)). While a page-0 tenant
runs, the interrupt vector at `$0038` is the sub-ROM's, so the sub-ROM's own
`$0038` jumps to a stub in RAM that maps the BIOS back and runs the real
interrupt handler. That keeps the frame interrupt, and `PLAY`, running during
a long `CIRCLE`; on the VG-8020 the frame counter advances during one too.

The **disk ROM** keeps fixed addresses — the standard disk entry points at
`$4010`–`$401F`, `$4022` (start BASIC) and the kernel entries MSX-DOS expects —
so its free space lies in holes between them
([disk-rom-layout.md](../disk-rom-layout.md); [disk.md](disk.md), [msx-dos.md](msx-dos.md)).

### The byte budget, and the walls

A real MSX1 fits BIOS and BASIC into 32 KB. zerobas's part of slot 0 is the
`$2765`–`$7FFF` image plus the islands, bounded by the `"AB"` header pinned at
`$4000` and the end of page 1 at `$8000`. The parts below and above `$4000`
are mapped together, so a routine can move between them and their free bytes
form one budget — except that a routine must stay below `$4000` when a page-1
tenant, the disk ROM or the interrupt handler can reach it while page 1 is
switched out.

Each region's remaining space is a **wall**; `make basic-reloc` prints all
five (main below `$4000`, main page 1, the sub-ROM's two pages, the disk ROM's
holes) from the built ROMs. No figure is quoted here: they change with every
slice. When main is full, code moves to a tenant or the disk ROM, or bytes
are carved. Joost, 2026-09-25:
*"Clearly reference fits everything in 32k"*; and on 2026-09-18: *"Lets
consider main + sub our replacement of reference main; the end result should
be similar to the reference both for with disk and without disk."*

### The clean-room boundary

Every address and convention here comes from a published interface (the MSX2
Technical Handbook, hardware datasheets, C-BIOS's own source) or from
black-box observation of the VG-8020 and the CF-3300 in openMSX. No reference
ROM is read or disassembled; a CF-3300 hook cell is read for its slot byte,
never for the code it points at. The allowed sources are listed in the
[README](../../README.md), [allowed-sources.md](../allowed-sources.md) and
[PROVENANCE.md](../../PROVENANCE.md).

## Differences from the reference

- **There is a sub-ROM.** An MSX1 has none; the MSX2 convention (a `"CD"` ROM,
  its slot in `EXBRSA`) holds the code that did not fit. Whether an MSX1
  program can tell, for example by reading `EXBRSA`, has not been measured.
- **`H_ZKEY` (`&HFFCF`) is a hook zerobas added to C-BIOS.** The `KEY` trap
  must see a function key as the keyboard scan stores it; `H.KEYI` and
  `H.TIMI` both run before that scan, on C-BIOS and on the VG-8020 (D-T3-3),
  and a sweep of the hook cells found no later one. Unclaimed, it is a `RET`.
- **`RST 8` (SYNCHR) is C-BIOS's stub**, which prints `SYNCHR` and returns.
  It matters to machine code and extension ROMs that use it; filed as
  D-SYNCHR, TIER 6, not yet measured on either reference.
- **SHIFT or CTRL held at power-on** is not built. On the CF-3300 they are
  expected to skip the disk ROM's start-up, or its second drive, for more RAM;
  filed as D-BOOTKEYS (TIER 4), to be measured there first.
- **Open:** a machine layout with more ROM is ruling R4 of the [space plan](../plan-main-rom-space-2026-10.md).

## What we found, and how

- **On the CF-3300, Disk BASIC lives behind hooks** (D-CFARCH, 2026-09-15): 35
  claimed cells, all slot 3-1, and the disk ROM calls back into main BASIC to
  evaluate its arguments. Joost the same day: *"now update our disk basic to
  use the same architecture"*. The first verbs moved into zerobas's disk ROM
  that day (D-DISKVERB..4).
- **A wrong hook address passed every test** (fixed 2026-09-15, D-DSKOHOOK).
  `H.DSKO` was `&HFDF4` on both sides — in the BASIC that calls it and the
  disk ROM that claims it. Un-claiming cells on the CF-3300 showed `&HFDEF`;
  a gate now checks that the two files agree.
- **A page-1 tenant must not wait.** The screen editor's line reader first
  waited for keys inside the sub-ROM (D-SCREDIT, 2026-09-11), and `PLAY`
  stopped at the prompt: the frame-interrupt work is skipped while a tenant
  holds page 1. Now main waits and calls the tenant once per key.
- **A layout review nearly moved the keyboard hook into page 1** (2026-07-30,
  [rom-region-structure-review.md](../rom-region-structure-review.md)). Its
  tool followed only calls and jumps, and the hook is installed with
  `ld hl,zkey_hook`. The tool now follows every reference to a label.

## How zerobas does it

The main image is one assembly, [basic/main.asm](../../basic/main.asm): the
low-region files, the `"AB"` header, page 1, then the islands, which
`tools/build_mainrom.py` lays into C-BIOS's padding, refusing any byte outside
the ranges it allows. The patch is that merged ROM's difference from a stock
C-BIOS built from a pinned tag.

A tenant call is `subrom_call` in
[basic/subromcall.asm](../../basic/subromcall.asm): the index becomes an
address in the sub-ROM's table, called with `CALSLT` under `DI`; arguments and
results travel in RAM cells. The same file holds `htimi_guard`, which skips
the `PLAY` and trap work for any frame in which page 1 is not the main ROM,
and the RAM interrupt trampoline. The main-ROM routines a tenant may call are
a generated list, `sub/basic-resident-abi.inc`, and the closure gates refuse a
tenant that would reach a switched-out page.

The disk ROM's INIT ([disk/init.asm](../../disk/init.asm)) takes its own slot
byte from `A`, installs `H.PHYD`, then walks `hook_tab` in
[disk/kernel.asm](../../disk/kernel.asm), writing one cell per hook; a handler
that needs BASIC's evaluator calls back into slot 0 through `calbak`
([spec-diskbasic-hook-rearchitecture.md](../../disk/docs/spec-diskbasic-hook-rearchitecture.md)).

## Related pages

- Concepts: [memory-map.md](memory-map.md), [interrupts-and-traps.md](interrupts-and-traps.md),
  [disk.md](disk.md), [msx-dos.md](msx-dos.md), [screen-editor.md](screen-editor.md).
- Keywords: [`USR`](../keywords/USR.md) and [`DEF`](../keywords/DEF.md)
  (`DEF USR`), [`KEY`](../keywords/KEY.md), [`FILES`](../keywords/FILES.md),
  [`COPY`](../keywords/COPY.md).

## Tests that cover it

- `make basic-reloc` — the five walls, the `"AB"` header, tenant closures.
- `make repack-boot` — a cold boot of the merged machine.
- `make patch-freshness-check` — the shipped patch matches the sources.
- `make hook-equate-check` — BASIC and the disk ROM agree on hook addresses.
- `make subrom-acceptance`, `make subrom-inttest` — both sub-ROM pages; interrupts under a page-0 tenant.
- `make nodisk-acceptance` — the diskless machine, hooks unclaimed.
