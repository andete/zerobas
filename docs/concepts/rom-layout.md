<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: verify=no reason="no example" -->

# ROM layout — how zerobas is put together

> **Status (2026-10-11):** the parts a program can see — the published BIOS
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
shape, built from four ROMs:

- **the main ROM** in slot 0 (`$0000`–`$7FFF`): the open-source C-BIOS in the
  low part, zerobas's interpreter in the rest;
- **a sub-ROM** in slot 3-2: 32 KB of interpreter code that did not fit in the
  main ROM;
- **a second sub-ROM** in slot 3-3, the same shape: 32 KB more room (since
  2026-10-12; empty so far, see below);
- **a disk ROM** in slot 3-1, on the disk machine only: Disk BASIC and the
  MSX-DOS kernel.

The same main ROM and sub-ROMs run on both targets: the diskless machine
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
| 3-3 | second sub-ROM, page 0 | second sub-ROM, page 1 | |

Slot bytes: `$83` RAM, `$87` disk ROM, `$8B` sub-ROM (the 2026-07-11 slot
map, [spec-basic-subrom.md](../spec-basic-subrom.md)), `$8F` second sub-ROM.

The second sub-ROM (marker `"Z2"`) exists because the first one filled up:
the first feature that needed it is `OPEN "GRP:"`, whose drawing lives there.
It is called exactly as the first is, by slot. It also takes code moved out of
the main ROM to make room there -- the first was the screen editor's CTRL
keys, on 2026-10-12. Each page also answers a test ping
([`sub2c_ping.out`](../../scratchpad/sub2c_ping.out)).
Its marker cannot be the first one's `"ZB"`: the boot scan keeps the last
subslot that carries `"ZB"`, so a second one would be taken for the first
([`sub2b_knife.out`](../../scratchpad/sub2b_knife.out)).

### C-BIOS, and zerobas as a patch next to it

C-BIOS is an open BIOS with no BASIC; it leaves page 1 of slot 0 empty, which
is where a real MSX keeps BASIC. zerobas ships as a patch against a stock
C-BIOS ROM (`zerobas-main-eu.ips` / `.bps`), never as a copy of it, so the two
stay separate trees ([README](../../README.md), *How it runs*). The patch:

- puts the interpreter at `$2781`–`$7FFF`. The part below `$4000` was C-BIOS's
  own, freed by removing its placeholder BASIC code and two boot messages
  zerobas can never print;
- puts more BASIC code into four runs of padding inside C-BIOS ("islands",
  [basic/islands.asm](../../basic/islands.asm));
- changes C-BIOS in a few places: small source patches in
  [cbios-repack/](../../cbios-repack/README.md) (the INS, DEL, HOME and CTRL
  keys, a scroll fix, one new hook, the registers five BIOS routines return,
  the reference's keyboard-scan entry at `&H0D12`), and a few bytes overwritten directly
  (the `RST $10` and `RST $18` vectors, and the cursor column `TTYPOS`, which
  C-BIOS kept one higher than the VG-8020 does).

C-BIOS's boot scan finds the `"AB"` header at `$4000` and calls zerobas's
INIT, which never returns: it ends at the BASIC prompt. A reset runs the same
path with the RAM of the session before still in place, so INIT starts by
forgetting anything that says the sub-ROM is already set up. So zerobas finishes the
boot scan itself, calling the INIT of every `"AB"` ROM in the remaining slots
— that is how the disk ROM installs its hooks
([basic/initext.asm](../../basic/initext.asm)). The sub-ROM is found by its own
`"ZB"` marker at `&H0000`. It carried the MSX2 SUB-ROM's `"CD"` until
2026-10-11 and wrote its slot to `EXBRSA` (`&HFAF8`); both now belong to a real
MSX2 SUB-ROM only, and `EXBRSA` reads 0, as on both MSX1 references (D-SUBSIG).

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

A contract is also what an entry leaves in the registers. Machine code keeps
values in registers across BIOS calls, and five C-BIOS routines returned
something other than what the VG-8020 returns: `CALATR` (`&H0087`) keeps `A`
there, where C-BIOS returned 4 × `A`; `CALPAT` (`&H0084`) returns the pattern's
offset in `DE`; `LDIRMV` (`&H0059`) returns `DE` just past the copied bytes and
`BC` = 0; `LDIRVM` (`&H005C`) returns `BC` = 0; and `DCOMPR` (`RST &H20`)
returns `A` = `H` − `D` (or `L` − `E`). zerobas's C-BIOS patches now give the
VG-8020's values ([cbios-repack/](../../cbios-repack/README.md), patches 9 and
10). Flags are not matched: neither machine documents them.

Some programs also call addresses inside the reference BIOS that no document
publishes. Joost's ruling of 2026-10-16: zerobas provides such an entry at its
address, with what it does measured from outside on the VG-8020 -- registers
in, registers and work-area RAM out, never the ROM's bytes. Buzz Off and Shark
Hunter call **`&H0D12`**, which scans the keyboard once (a newly pressed key
goes into the key buffer, as the interrupt's scan does) and returns `A` = the
low byte of `PUTPNT` minus that of `GETPNT` (0, with Z set, when the buffer is
empty), `HL` = `GETPNT`, `DE` = `KEYBUF` and `BC` = `&H00FF`, keeping `IX`,
`IY` and the alternate registers. C-BIOS had the start of its reset routine
there. It is patch 11: `&H0D12` jumps to the new routine, placed after C-BIOS's
last code, and nothing between `&H0D16` and the font moves. C-BIOS already
answered at two addresses just before it, `&H0D02` and `&H0D0E`, for the same
reason (the games Hacker and Star Force).

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
`$2781`–`$7FFF` image plus the islands, bounded by the `"AB"` header pinned at
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

- **There are sub-ROMs.** An MSX1 has none; zerobas's own (markers `"ZB"`
  in slot 3-2 and `"Z2"` in slot 3-3) hold the code that did not fit. A program could tell by
  reading `EXBRSA` (`&HFAF8`) until 2026-10-11: both references leave it 0 and
  zerobas wrote its sub-ROM's slot, 139. It no longer writes it
  ([`subsig_probe.out`](../../scratchpad/subsig_probe.out)).
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
- **In `SCREEN 0`, `ATRBAS` and `PATBAS` read 0** (`&HF928`, `&HF926`), where
  the VG-8020 keeps `&H1B00` and `&H3800`, so `CALATR` and `CALPAT` called in
  text mode answer differently
  ([`calatr_probe.out`](../../scratchpad/calatr_probe.out), rows `atr`, `pat8`).
  Filed as D-SPRBASE0; Demonia sets its own screen mode first and is not
  affected.
- **Scratch registers after some BIOS calls differ.** `SNSMAT` returns `C` =
  the row on the VG-8020; `GTSTCK`, `GTTRIG` and `CLRSPR` leave other values in
  registers they do not document. No program is known to read them; filed as
  D-BIOSSCRATCH.
- **Open:** a machine layout with more ROM is ruling R4 of the [space plan](../plan-main-rom-space-2026-10.md).

## What we found, and how

- **Buzz Off and Shark Hunter reset the machine** (fixed 2026-10-17,
  D-BIOSINT). Both loaded completely, then the machine went back to its boot
  screen. Logging their calls into the BIOS showed both calling `&H0D12`, an
  address no document lists; on zerobas it was the first byte of C-BIOS's
  reset. Our own test program called it on the VG-8020 with chosen registers
  and buffer contents, with and without a key held
  ([`biosint_probe.out`](../../scratchpad/biosint_probe.out)), and zerobas now
  answers the same. Both games play the VG-8020's attract demo.
- **Demonia played a different game, then reset** (fixed 2026-10-16,
  D-BIOSREGS). Once its tape entries worked (D-BASICINT2,
  [cassette.md](cassette.md)) it loaded, byte for byte as on the VG-8020; then
  its attract demo walked through rooms the VG-8020's never shows, and after
  about three minutes the machine reset. Logging all of its ~8000 BIOS calls on
  both machines, with the registers going in and coming out, showed where the
  two parted: `CALATR` changed `A`, which the game uses as its next sprite
  number; `LDIRMV` left `DE` where the next chunk could not follow; `DCOMPR`
  left a different `A`. With the five contracts matched it plays the
  VG-8020's demo ([`calatr_probe.out`](../../scratchpad/calatr_probe.out)).
- **A BASIC-program cartridge did not run** (fixed 2026-10-12, D-BASICROM,
  reported by Vampier). A cartridge whose header's TEXT field points at a BASIC
  program in its page 2 is run at boot by the reference: the cartridge stays
  mapped at `&H8000`, `TXTTAB` is TEXT + 1, the variables start at `&HC000`,
  and it runs in `SCREEN 1` at width 29, with no header first; after `END` it
  can be LISTed. zerobas booted to its prompt. It now does the same
  ([`basicrom_gate.out`](../../scratchpad/basicrom_gate.out), our own test
  cartridges). Vampier's game now starts, and then stops: its machine code
  keeps data in RAM that is free on the reference and is zerobas's own
  workspace here -- the RAM-usage gap, which is being closed.
- **A reset left the machine on C-BIOS's boot screen** (fixed 2026-10-11,
  D-RESETBOOT; reported by Joost). RAM survives a reset, and a cell left over
  from the session before told INIT the sub-ROM was already set up; INIT
  called it before scanning for it, and control fell back into the boot
  scan. A guard written for the random contents of RAM at power-on did not
  cover a true leftover value. The VG-8020 comes back to `Ok` with the
  program gone; zerobas now does the same
  ([`resetboot_trace.out`](../../scratchpad/resetboot_trace.out)).
- **The sub-ROM wore the MSX2 SUB-ROM's identity** (changed 2026-10-11,
  D-SUBSIG, Joost's ruling). It carried `"CD"` and wrote `EXBRSA`; on an
  MSX2, C-BIOS takes the first `"CD"` ROM it finds as the SUB-ROM, so ours
  would have captured `EXTROM`. Found while weighing more sub-ROM space
  ([`subrom_arch_report.md`](../../scratchpad/subrom_arch_report.md)).
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
- `make resetboot-acceptance` — a reset, idle and with a program stored,
  then a line through the sub-ROM; the VG-8020 as the control.
- `make patch-freshness-check` — the shipped patch matches the sources.
- `make hook-equate-check` — BASIC and the disk ROM agree on hook addresses.
- `make biosregs-acceptance` — what `CALATR`, `CALPAT`, `LDIRMV`, `LDIRVM`,
  `DCOMPR` and the keyboard-scan entry `&H0D12` leave in `A`, `BC`, `DE` and
  `HL` (and `IX`, for `&H0D12`), against the VG-8020.
- `make subrom-acceptance`, `make subrom-inttest` — both sub-ROM pages; interrupts under a page-0 tenant.
- `make nodisk-acceptance` — the diskless machine, hooks unclaimed.
