<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# Hosting a stock disk ROM — what the main BIOS and BASIC owe a disk interface cartridge

> **Status (2026-11-24, D-NMSHOST):** measured with the Philips NMS 1200 and Sony HBD-F1 disk cartridges on the
> Philips VG-8020 (the reference) and on zerobas without its own disk ROM (`C-BIOS_MSX1_EU_REPACK_NODISK`). Items 1-3
> met: the NMS 1200's INIT ends on zerobas byte-identical to the reference, and with the HBD-F1 zerobas boots
> MSX-DOS 1.03 to COMMAND.COM's date prompt as the VG-8020 does. Item 4 (the screen DOS starts on) met with a locale-driven pin.
> Not covered: what follows the NMS 1200's date prompt (Disk BASIC, which calls MS-BASIC internals). This page is the
> checklist C-BIOS will need once disk facilities are ported to it.

A disk interface on an MSX1 is a cartridge with its own ROM. At power-on the main BIOS finds it, calls its INIT, and
from then on the disk ROM lives inside BASIC's memory and hooks. It was written against MS-BASIC, so it assumes
MS-BASIC's state at fixed published addresses. Everything below is measured black box: work-area RAM, slot state,
the stack pointer, the page and slot executing -- never a byte of the reference's ROM or its RAM-resident code.

## 1. The INIT runs on a stack below the RAM it will claim [M]

The disk ROM claims RAM by lowering HIMEM ($FC4A) and initialises what it claimed (the NMS 1200 zeroes from its new
HIMEM up). The VG-8020's boot scan calls it with SP = $F08E, below that area. zerobas called it late, from BASIC's
start-up, on C-BIOS's boot stack at $F2DA -- inside the claimed RAM: the INIT overwrote its caller's stack and the
machine restarted in a loop.

Evidence: [AE_nmshost_step1_zb.out](../../scratchpad/AE_nmshost_step1_zb.out) (the restart),
[AE_nmshost_step2_zb.out](../../scratchpad/AE_nmshost_step2_zb.out) (the path to it), the item's step 3 (1,798 writes
by the cartridge into $F2C0-$F2EF).

## 2. MS-BASIC's memory layout is in place when the INIT runs [M]

At the INIT the reference already has BASIC's layout below HIMEM, and the disk ROM reads it to rebuild the layout
under the HIMEM it lowers. The rule holds at both HIMEMs measured ($F380 at the INIT, $DF95 after the disk ROM):

| cell | rule | at HIMEM $F380 | at HIMEM $DF95 |
|---|---|---|---|
| MEMSIZ $F672 | HIMEM − $218 | $F168 | $DD7D |
| STKTOP $F674 | MEMSIZ − 200 | $F0A0 | $DCB5 |
| FILTAB $F860 | MEMSIZ + 2 | $F16A | $DD7F |
| $F862 | MEMSIZ + $0F | $F177 | $DD8C |
| SAVSTK $F6B1 | STKTOP − 2 | $F09E | $DCB3 |
| FRETOP $F69B | MEMSIZ (at boot) | $F168 | -- |
| TXTTAB / VARTAB / BOTTOM | unchanged | $8001 / $8003 / $8000 | the same |

The boot scan's stack is STKTOP (the INIT's $F08E is just below $F0A0). On zerobas the cells held zeros, so the
disk ROM computed addresses from them and wrote over zerobas's own RAM.

Evidence: [AE_nmshost_sysdata.out](../../scratchpad/AE_nmshost_sysdata.out) (the cells at the INIT, both machines;
read only from $F39A-$FD99 -- never the inter-slot code at $F380-$F399 or the hooks), the item's step 6 and the
end-of-run read.

**zerobas:** `layout_from_himem` ([basic/files.asm](../../basic/files.asm)) fills the cells by the rule; `init`
([basic/interp.asm](../../basic/interp.asm)) calls it and moves SP to STKTOP before the scan, and after the scan
rebuilds them when HIMEM moved without the disk ROM doing so (zerobas's own disk ROM lowers HIMEM without H.RUNC).

## 3. BASIC calls H.RUNC ($FECB) [M]

The disk ROM patches H.RUNC in its INIT and does the rest of its set-up there: the second HIMEM step, the 512-byte
buffers, the rebuilt layout. MS-BASIC calls H.RUNC once in its cold start, right after the cartridge scan, and on

| action | H.RUNC calls |
|---|---|
| NEW | 1 |
| a typed program line | 1 |
| RUN | 1 |
| CLEAR, CLEAR n | 0 |
| MAXFILES = n | 0 |
| a direct statement, a direct GOTO, a direct error | 0 |

(Unlike H.STKE: CLEAR and an error call that one.) zerobas never called H.RUNC.

Evidence: [AE_hrunc_when.out](../../scratchpad/AE_hrunc_when.out) (our own counting handler in the hook, VG-8020 and
zerobas before and after; [hrunc_when.py](../../scratchpad/hrunc_when.py)).

**zerobas:** `hrunc` ([basic/files.asm](../../basic/files.asm)) from NEW, a typed line, RUN and the cold start.

## 4. The main ROM word at $7D2F is a routine the disk ROM calls from H.RUNC [M]

In its H.RUNC handler the disk ROM reads two bytes from the main ROM (slot 0) at $7D2F-$7D30 with RDSLT and CALSLTs
the word they make. MS-BASIC keeps a routine's address there: on the reference the call sets up the text screen --
5 ms after H.RUNC is entered the VDP is in TEXT1, SCRMOD 0, LINLEN = LINL40 (37), the screen cleared, the cursor
home -- before the disk ROM reads the boot sector. zerobas has its own code at $7D2F (the bytes $23 $23), so the disk
ROM calls zerobas's $2323, the middle of an unrelated routine; it happens to return, and DOS then starts on C-BIOS's
SCREEN 1 start-up text with 29 columns.

Measured with the Sony HBD-F1 (the cartridge with which the VG-8020 does boot MSX-DOS 1.03 here) and the Philips
NMS 1200. Experiment on a patched copy of zerobas's own ROM with $006C (INITXT, the published BIOS entry) at $7D2F:
the cartridge calls $006C, and at MSX-DOS's entry ($0100) SCRMOD, LINLEN, LINL40 / LINL32, CRTCNT, the cursor, VDP R#0
/ R#1 / R#2 / R#4 / R#7, HIMEM and the screen text are the reference's, row for row. With the NMS 1200 the patch gives
the reference's TEXT1 screen too. The reference's word itself is never read (it is a ROM byte); only the effect of the
call is matched.

Evidence: [AE_dosref_ifaces.out](../../scratchpad/AE_dosref_ifaces.out) (the VG-8020 boots DOS with the HBD-F1, not
with the NMS 1200), [AE_dosref_zb.out](../../scratchpad/AE_dosref_zb.out) (zerobas boots DOS with the HBD-F1),
[AE_dosref_state.out](../../scratchpad/AE_dosref_state.out) (the state at $0100, both),
[AE_dosref_allhooks.out](../../scratchpad/AE_dosref_allhooks.out) (no hook between H.RUNC and the TEXT1 switch),
[AE_dosref_zbcalls.out](../../scratchpad/AE_dosref_zbcalls.out) (the RDSLTs of $7D2F / $7D30 and the CALSLT, zerobas's
own addresses), [AE_dosref_patch.out](../../scratchpad/AE_dosref_patch.out) and
[AE_dosref_nms_patch.out](../../scratchpad/AE_dosref_nms_patch.out) (the patched copy);
[dosref_probe.py](../../scratchpad/dosref_probe.py).

What the reference's routine does, measured between H.RUNC's entry and the disk ROM's first H.PHYD on the
reference and on the patched copy ([snapdiff.py](../../scratchpad/snapdiff.py),
[AE_dosref_snapdiff.out](../../scratchpad/AE_dosref_snapdiff.out)): the same 30 published bytes change, to the same
values (SCRMOD / OLDSCR, LINLEN, CSRY, RG0SAV-RG7SAV, the layout the disk ROM rebuilds; beyond them only the timer
counters differ); both write VRAM 3,008 times -- the font and a cleared 40 x 24 name table -- and end with the same
name table and VDP registers. Differences: the glyphs (each machine's own font) and the order -- the reference loads
VRAM with the display off before it reprograms R#2-R#6. The effect is INITXT's.

**It is not INITXT: it is the machine's own start-up screen.** The same disk-ROM call on other MSX1 machines
([AE_dosref_msx1.out](../../scratchpad/AE_dosref_msx1.out), the HBD-F1 + the same DOS disk; the CF-3300 with its own
built-in disk ROM): the Goldstar FC-200 does exactly what the VG-8020 does (display off, 3,008 VRAM writes, then
TEXT1; SCREEN 0, LINLEN 37 at DOS's entry); the National CF-2700, CF-3000 and CF-3300 do 2,944 writes and come back
to Graphic 1 -- SCREEN 1, LINLEN 29 at DOS's entry. So the routine behind $7D2F re-initialises BASIC's start-up
screen, whatever that is on the machine: text on the European and Korean machines, SCREEN 1 on the Japanese ones.
The same routine on two manufacturers' ROMs and the same disk-ROM call site on three supports $7D2F being a fixed
MSX-BASIC 1.0 location. No admissible document names it (docs/allowed-sources.md: the MSX Technical Data Book lists
CALBAS and the hooks for disk-ROM writers, not $7D2F; the sources that would name it are disassemblies, forbidden).

**zerobas (met, 2026-11-24, Joost: "go ahead with the locale-driven pin for EU"):** main ROM $7D2F holds
`STARTUP_SCREEN` ([basic/sysvars.inc](../../basic/sysvars.inc)) -- a locale choice: this EU build's start-up screen is
INITXT with LINL40 = 37, a JP variant's would be INIT32. The word sits inside a loop of
[basic/program.asm](../../basic/program.asm), stepped over as the operand of a `ld de,nn` (3 B, no pad), and
`tools/pin_plan.py` checks it. After it, with the HBD-F1, every recorded field at DOS's entry equals the VG-8020's
and the screen is the same line for line; the NMS 1200's date prompt stands alone on a cleared 40-column screen, as
on the reference ([AE_pin7d2f_after.out](../../scratchpad/AE_pin7d2f_after.out)).

## What the disk ROM writes

Every RAM address the NMS 1200 writes on the reference from power-on, with the first write's time:
[AE_nmsram_ref.out](../../scratchpad/AE_nmsram_ref.out). Below $F380: its HIMEM claim, its buffers, the boot sector at
$C000. Above: published system cells (DRVTBL, HIMEM, MEMSIZ / STKTOP, FILTAB, SAVSTK) and hooks. A host must keep
none of its own state in the RAM below HIMEM a disk ROM may claim -- zerobas's main BASIC state already lives at
$F380 and above ([ram_inventory_f380.md](../../scratchpad/ram_inventory_f380.md)); what sits below is its own disk
ROM's.

## Open (not measured or not met)

- The date format of the start-up prompt: D-M-Y on zerobas, M-D-Y on the VG-8020 -- the disk ROM reads it from the
  main ROM's published machine-ID information. A locale setting (C-BIOS EU's `LOCALE_DATE`); kept as C-BIOS has it
  (Joost, 2026-11-24).
- The screen before the NMS 1200's prompt: met by item 4.
- After the date: the reference enters Disk BASIC (MS-BASIC internals) -- out of scope for a host without MS-BASIC.
- MSX-DOS: the NMS 1200 in openMSX runs the boot sector ($C01E) of three DOS disks and never reaches DOS ($0100) --
  on the VG-8020, the Goldstar FC-200 and the National CF-3000 alike, and in a plain primary slot as well as the
  extension's secondary one ([AE_nms_dosboot.out](../../scratchpad/AE_nms_dosboot.out)); the only ROM image at hand is
  the extension's version 6 (version 4 not available). So the NMS 1200 as emulated here boots no DOS on any host --
  its cartridge / ROM / emulation, not the host. The Sony HBD-F1 is the working cartridge DOS reference. With the Sony HBD-F1 the VG-8020 boots MSX-DOS 1.03 to COMMAND.COM's date prompt, and so does zerobas
  without its disk ROM (2026-11-24) -- apart from the screen (item 4).
- H.RUNC on LOAD: unmeasured (zerobas calls it through NEW's code on LOAD's ASCII path).
- Other disk interfaces: the Sony HBD-F1 measured (items 1-4 hold); the Panasonic FS-FD1A does not start in this
  openMSX (no ROM).
