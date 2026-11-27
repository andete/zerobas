<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# Carrying zerobas's disk ROM in C-BIOS

> **Status (2026-11-27):** ready for MSX-DOS 1 on a C-BIOS with no BASIC; Disk BASIC needs zerobas BASIC as host.
> Upstream submission is Joost's call, made together, not this page's. Readiness in detail:
> [port-readiness.md](port-readiness.md).

## What it is

`disk.rom` is a 16 KB "AB" disk-interface ROM for page 1 ($4000-$7FFF). It drives a **National-style memory-mapped
WD2793** whose registers sit at $7FB8-$7FBF and are mirrored across $7F80-$7FBF, like the National CF-3300's
(openMSX `NationalFDC`). It provides:

- the published disk-ROM entries: [DSKIO](DSKIO.md), [DSKCHG](DSKCHG.md), [GETDPB](GETDPB.md), [CHOICE](CHOICE.md),
  [DSKFMT](DSKFMT.md) and MTOFF;
- the MSX-DOS 1 BDOS (through $F37D and MSX-DOS's $0005);
- the boot of MSX-DOS 1 from a disk;
- Disk BASIC's hooks, when zerobas BASIC is the host (see below).

The reference for its behaviour is the National CF-3300.

## Slot

**One ROM image for every C-BIOS config** (D-DISKMSX2HOST, 2026-11-27): a config with a disk only adds the WD2793
block in a subslot of slot 3 it leaves free. Measured and gated on all 12 of C-BIOS's configs:

| family | configs | the disk in | gate |
|---|---|---|---|
| MSX1 | international, EU, JP, BR | 3-1 (slot 3 expanded; RAM in 3-0) | EU in the battery, all in the daily sweeps |
| MSX2 | international, EU, JP, BR | 3-1 (3-0 sub ROM, 3-2 RAM) | EU in the battery, all in the daily sweeps |
| MSX2+ | international, EU, JP, BR | 3-3 (3-1 is the music ROM) | EU in the battery, all in the daily sweeps |

The ROM takes its own slot byte from A at INIT (host item 5 below) and the RAM's subslot from page 3, and publishes
its slot (DRVTBL, SLTWRK). Before D-DISKMSX2HOST it assumed MSX1's layout (RAM in subslot 0, itself in subslot 1):
MSX2 restarted at MSX-DOS, MSX2+ never reached the BDOS.

Only one disk interface is supported. A second one initialised before this one is not handled (Joost, 2026-11-26:
deferred, very low priority).

## Building it

The ROM assembles from 19 source files with pasmo 0.5.3 or later, without the rest of zerobas's build:

```bash
pasmo -I disk --bin disk/disk.asm disk.rom
```

The 19 files are:

- `disk/disk.asm` and its parts under `disk/`;
- the shared FAT / SAVE bodies under `basic/*.inc`. These are disk-ROM **sources**: one FAT engine, two ROMs;
- the **committed** `disk/basic-resident-abi.inc`.

The Makefile's `DISK_SRC` + `DISK_PARTS` lists them. The result must be exactly 16384 bytes.

`make disk-standalone-check` proves this in every battery. It copies only those files into an empty directory,
assembles there without make, `build/` or any main-ROM symbols, and requires an image byte-identical to the one the
battery tested.

`basic-resident-abi.inc` is generated from zerobas's main-ROM symbols. It changes only when zerobas BASIC moves, and
`make diskrom-abi-check` keeps it in step. A port takes the committed copy as it is.

## What the host must provide

All five items are measured; [disk-rom-host.md](../concepts/disk-rom-host.md) gives the detail of 1-4.

1. The INIT runs on a stack **below** the RAM it will claim. The disk ROM lowers HIMEM ($FC4A).
2. MS-BASIC's memory-layout cells are in place when the INIT runs, because the disk ROM rebuilds that layout under
   its new HIMEM.
3. **H.RUNC ($FECB) is called** once, after the cartridge scan. The disk ROM finishes its set-up there: the second
   HIMEM step, the buffers and the MSX-DOS boot.
4. The main-ROM word at **$7D2F** is a routine the disk ROM CALSLTs from H.RUNC to set up the text screen.
5. The cartridge scan calls INIT with **the ROM's slot byte in A** (the CF-3300's scan passes A = $87 for 3-1). The
   disk ROM reads it as its first instruction (`disk/init.asm`).

A C-BIOS checkout from 0.32 on meets all five (gated at fac3f41). openMSX's bundled C-BIOS 0.29 does not: it
predates the disk-host work and reports "No cartridge found".

## RAM

The ROM uses two kinds of RAM:

- **A fixed work area at $F1C9-$F37F**, as the reference disk ROMs have. Programs of the time address it directly,
  so it stays fixed (Joost, 2026-11-27).
- **A claim taken from the top, through HIMEM**, in two steps as the CF-3300 does it: one at INIT, one at H.RUNC.

It publishes its work-area base in its SLTWRK page-1 entry ($F1BF − N).

A cartridge initialised before the disk ROM may claim N bytes under HIMEM:

- **Up to 439 B:** the disk ROM installs, and every published number moves by N, as on the CF-3300.
- **Over 439 B:** the disk ROM declines to install, the way it does when SHIFT is held at boot. The CF-3300 still
  installs up to 473 B. This is a known difference, pinned in `make diskguard-acceptance`.

## With and without BASIC

**On C-BIOS with no BASIC (the port):** MSX-DOS 1 boots and runs. The disk ROM installs its Disk BASIC hooks, but
nothing calls them, and no disk-ROM path enters zerobas's main ROM. Typing `BASIC` at A> has nothing to start, so it
comes back to MSX-DOS.

**With zerobas BASIC:** Disk BASIC works. zerobas BASIC marks itself with **ZB_HOST** before the cartridge scan:
$FD09-$FD0A = "ZB", which is slot 0's own SLTWRK entry. The disk ROM checks this marker before entering zerobas BASIC
for the BIOS FORMAT routine ($0147).

**With another BASIC (Microsoft's):** not supported yet. That is D-FOREIGNBASIC: a later step, after the port
(Joost, 2026-11-27).

## Gates

| target | what it holds |
|---|---|
| `make nobasic-acceptance` | Runs on the pinned C-BIOS hosts (`tools/cbios-nobasic.pin`): MSX1 EU, MSX2 EU, MSX2+ EU. The no-BASIC MSX-DOS session must read as on the CF-3300, and every run must show no disk-ROM path reaching zerobas's main ROM |
| `make nobasic-all-acceptance` | The same on all 12 C-BIOS configs (daily sweeps) |
| `make disk-standalone-check` | The standalone build above |
| `make bdos-acceptance`, `make bdos-cbios-selfcheck` | The BDOS surface |
| `make dossession-acceptance` | An MSX-DOS session against the CF-3300 |
| `make diskguard-acceptance` | Foreign claims of 0-440 B |

The pin moves only by hand: install the new C-BIOS with `--cbios <checkout>`, run `make nobasic-acceptance`, and
update the pin's revision and hashes in the same commit.

## Known differences from the CF-3300

| what | on the CF-3300 | here | item |
|---|---|---|---|
| a foreign claim of 440-473 B | installs | declines, as with SHIFT | [D-DISKROMHOST](../../todo/open/D-DISKROMHOST.md), pinned |
| BIOS FORMAT ($0147) on a host that is not zerobas BASIC | formats | returns Cy = 1 | [D-BIOSFORMAT](../../todo/open/D-BIOSFORMAT.md) |
| a second disk interface | supported | not handled | deferred |
| Ctrl-C during console OUTPUT (CONST) | -- | not measured | -- |

There are also BASIC-side differences, which a BASIC-less C-BIOS never meets:

- END keeps disk files open ([D-ENDCLOSE](../../todo/open/D-ENDCLOSE.md));
- the rest of the calling line after BDOS $00 through $F37D
  ([D-F37DTERMLINE](../../todo/open/D-F37DTERMLINE.md));
- BOTTOM is ignored ([D-BOTTOMIGN](../../todo/open/D-BOTTOMIGN.md)).

The real-disk corpus (`scratchpad/diskcorpus_run.py`) is the broader check: 143 images, most of which run on both
zerobas and the CF-3300.
