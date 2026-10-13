<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Quickstart — run zerobas in openMSX

zerobas is a clean-room MSX1 BASIC. It runs in the [openMSX](https://openmsx.org/)
emulator, next to the free [C-BIOS](https://cbios.sourceforge.net/) — **no
proprietary ROM is needed to try it.**

## 1. Get openMSX

Install openMSX from [openmsx.org](https://openmsx.org/) (on Debian / Ubuntu:
`sudo apt-get install openmsx`). **Start it once** and close it: that creates
its user folder — `~/.openMSX` on Linux and macOS, `Documents\openMSX` on
Windows.

## 2. Get zerobas — download it

Download **`zerobas-openmsx.zip`** from the
[nightly release](https://github.com/andete/zerobas/releases/tag/nightly) and
unpack it. It holds one folder, `share`. Copy that folder into openMSX's user
folder, merging it with the `share` folder already there.

That adds two machines and their ROMs, and changes nothing else.

The nightly is rebuilt from every change to zerobas. It is checked by the unit
tests on GitHub; the full comparison with real MSX machines runs on the
developers' computers, because it needs their system ROMs.

<details>
<summary>Or build it yourself</summary>

You need `make`, `python3`, the [pasmo](https://pasmo.speccy.org/) Z80 assembler
(0.5.3 or newer) and openMSX.

| OS | |
|----|---|
| **Debian / Ubuntu** | `sudo apt-get install make python3 pasmo openmsx` |
| **macOS** | `make` and `python3` come with the Xcode command-line tools; pasmo built from [source](https://pasmo.speccy.org/) |
| **Windows** | `python3` from python.org; `make` and `pasmo` through [MSYS2](https://www.msys2.org/), Git Bash or WSL |

```sh
git clone https://github.com/andete/zerobas.git
cd zerobas
make
make install-openmsx
```

`make install-openmsx` builds the same folder as the download (in
`build/dist/`, and `build/zerobas-openmsx.zip`) and copies it into openMSX's
user folder. If openMSX keeps that folder somewhere else:
`python3 tools/make_dist.py --install --user <folder>`.

</details>

## 3. Run it

Start openMSX and choose a zerobas machine in its **Machine** menu:

- **zerobas_MSX1** — BASIC
- **zerobas_MSX1_disk** — BASIC with a disk drive; insert a disk image as
  drive A from the **Media** menu (`test720.dsk`, in the download and in
  `disk/` after a build, has a few files on it)

From a terminal the same is:

```sh
openmsx -machine zerobas_MSX1
```

```sh
openmsx -machine zerobas_MSX1_disk -diska test720.dsk
```

The prompt is `ZB` where a real MSX says `Ok`. Try:

```basic
10 FOR I=1 TO 5
20 PRINT I*I;
30 NEXT
RUN
```

and, on the disk machine, `FILES` to list the disk.

## 4. What to expect, and where to report

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
