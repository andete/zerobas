<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Quickstart — run zerobas in openMSX

zerobas is a clean-room MSX1 BASIC. It runs in the [openMSX](https://openmsx.org/)
emulator, next to the free [C-BIOS](https://cbios.sourceforge.net/) that ships
with openMSX — **no proprietary ROM is needed to try it.**

## 1. Install the tools

You need `make`, `python3`, the [pasmo](https://pasmo.speccy.org/) Z80 assembler
and openMSX.

| OS | |
|----|---|
| **Debian / Ubuntu** | `sudo apt-get install make python3 pasmo openmsx` |
| **macOS** | `make` and `python3` come with the Xcode command-line tools; the openMSX app from [openmsx.org](https://openmsx.org/); pasmo built from [source](https://pasmo.speccy.org/) |
| **Windows** | `python3` from python.org; `make` and `pasmo` through [MSYS2](https://www.msys2.org/), Git Bash or WSL; openMSX from [openmsx.org](https://openmsx.org/) |

**Start openMSX once** (and close it). That creates its user folder
(`~/.openMSX` on Linux and macOS), which step 3 writes into.

## 2. Build

```sh
git clone https://github.com/andete/zerobas.git
cd zerobas
make
```

The ROMs land in `build/`.

## 3. Install the machines

```sh
make machines
```

This writes two machine definitions into openMSX's user folder:
`C-BIOS_MSX1_EU_BASIC` (BASIC only) and `C-BIOS_MSX1_EU_BASIC_DISK` (with Disk
BASIC). They copy no ROM: they point at openMSX's own C-BIOS and at the files in
this checkout. So:

- **moved the checkout, or ran `make clean`?** Run `make` and `make machines`
  again.
- **openMSX keeps its user folder somewhere else?** Run
  `python3 tools/install-openmsx-machine.py --user <folder> --disk-rom build/disk.rom --sub-rom build/sub.rom`.

## 4. Run it

Start openMSX the way you usually do and choose the zerobas machine in its
**Machine** menu: *zerobas BASIC* (BASIC only) or *zerobas Disk BASIC* (with a
disk drive; insert [`disk/test720.dsk`](disk/test720.dsk) as disk A from the
**Media** menu to have something on it).

From a terminal the same is:

```sh
openmsx -machine C-BIOS_MSX1_EU_BASIC
```

```sh
openmsx -machine C-BIOS_MSX1_EU_BASIC_DISK -diska disk/test720.dsk
```

The prompt is `ZB` where a real MSX says `Ok`. Try:

```basic
10 FOR I=1 TO 5
20 PRINT I*I;
30 NEXT
RUN
```

and, on the disk machine, `FILES` to list the disk.

## 5. What to expect, and where to report

zerobas aims to behave exactly like a real MSX1 (a Philips VG-8020 for BASIC, a
National CF-3300 for Disk BASIC). What already works, keyword by keyword, is in
[docs/keywords/](docs/keywords/README.md); how the machine works underneath is in
[docs/concepts/](docs/concepts/README.md). Known gaps are listed in the
[README](README.md#what-works).

Found something that differs from a real MSX? Open an issue at
<https://github.com/andete/zerobas/issues> with the BASIC you typed, what zerobas
showed, and — if you know it — what a real MSX1 shows.

## Going further

- `make unit-test` — the emulator-free unit tests; no openMSX needed.
- The full check compares zerobas with the reference machines running in
  openMSX, which needs your own copies of their system ROMs. See
  [How it is checked](README.md#how-it-is-checked).
