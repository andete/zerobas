<!-- Copyright (c) 2026 Joost Yervante Damad -->
<!-- SPDX-License-Identifier: 0BSD -->

# probes/ — the openMSX oracle harness

This is the **reproduction half** of zerobas's [dual mission](../MISSION.md): the
emulator-driven probes that establish, against real hardware behaviour, that a
zerobas implementation is byte-identical to what an MSX does — and that capture,
as observed facts, behaviour no public source documents.

Where [`tests/`](../tests) is the fast, emulator-free regression layer (a Z80
core in-process; `make unit-test`), `probes/` is the **heavy oracle layer**: it
boots openMSX, drives a routine through its *public entry points only*, and reads
back registers / memory / VRAM / disk sectors. A reference machine is used **only
as a black box** — identical inputs in, observed outputs out. No probe reads,
dumps, or disassembles any reference ROM. This is the clean-room discipline of
[CONTRIBUTING.md](../CONTRIBUTING.md) made executable.

## Layout

| Dir | Contents |
|-----|----------|
| `lib/`   | shared infrastructure — `omsx_run.py` (headless openMSX state capture), `z80probe.py` (Z80 cartridge builder), `probe_cart.py` (sentinel-cart generator), `cas_encode.py` / `cas_decode.py` (cassette codecs) |
| `basic/` | `basic_probe_*.py` — zerobas-BASIC vs a reference MSX-BASIC ROM (Philips VG-8020) |
| `disk/`  | `disk_probe_*.py`, `diskbasic_probe_*.py` — zerobas-disk vs a reference disk ROM (National CF-3300) and real MSX-DOS 1 |
| `tape/`  | `bios_probe_*.py` — the cbios-tape cassette read/write path (TAPION/TAPIN/TAPOON/TAPOUT…) on patched C-BIOS |

Each probe is self-contained: it locates `lib/` and its sibling probes relative
to its own path, so it runs from anywhere with no `PYTHONPATH` set-up.

## Prerequisites

1. **openMSX** on your `PATH` (or `$OPENMSX`, or `--omsx <path>`).
2. **Build artifacts** — `make all` (produces `build/basic.rom`, `build/disk.rom`)
   and `make test-dsk` (produces `disk/test720.dsk`, a reproducible FAT12 image).
3. **openMSX machines** — `make machines-oracle` installs the zerobas machines
   (`C-BIOS_MSX1[_EU/_BR/_JP]_BASIC`, `…_BASIC_DISK`) plus the CF-3300 provider
   oracle. (`make machines` omits the oracle test machine.)
4. **Reference ROMs — you supply them.** The differential probes compare against
   proprietary reference machines (`Philips_VG_8020`, `National_CF-3300`) and, for
   the BDOS probes, a real MSX-DOS 1 disk. These ROMs/disks are **never shipped
   here** (see [PUBLISHING.md](../PUBLISHING.md)); install your own legally-obtained
   copies into openMSX. Tape corpora (`.cas` / `.wav`) are likewise yours to
   supply via `--corpus` / `$MSX_TAPE_CORPUS` and `--wav-dir` / `$MSX_TAPE_WAVS`.

## Running

```sh
# headline differential oracles
python3 probes/disk/disk_probe_dskio.py  --dsk disk/test720.dsk      # DSKIO == CF-3300
python3 probes/basic/basic_probe_print.py --cart build/basic.rom      # PRINT == VG-8020
python3 probes/tape/bios_probe_tapwrite.py --out /tmp/tapwrite.rom    # build a cassette-write cart

# end-to-end BDOS $05 LSTOUT on the C-BIOS target (through the tape LPTOUT $00A5)
python3 probes/disk/disk_probe_lstout_cbios.py                       # prints "LP!" via a logger

# every probe takes --help
python3 probes/disk/disk_probe_bdos.py --help
```

`make probe` runs one probe per component as a smoke check (needs steps 1–4 above).

`make bdos-acceptance` replays the whole BDOS surface: it (re)builds the
BDOSX/BDOSX2/BDOSX3/BDOSX0 exercisers and asserts each still converges
0-byte-identical to the stock oracle (`disk/docs/tier2-bdos-coverage.md`). This is
the **standing regression gate** that turns the one-shot M19–M26 differentials into
"proven every release". Same oracle prerequisites as `make probe`; scope it with
`make bdos-acceptance ONLY=BDOSX3`, or run `disk_bdos_acceptance.py --list` to print
the replay plan without booting openMSX.

> **Disk-image safety.** openMSX can write back to a mounted `.dsk`. Probes that
> may write copy `disk/test720.dsk` to `/tmp` first; if you invoke one directly in
> write mode, point `--dsk` at a throwaway copy, never the committed image.

## Source of truth

zerobas is the **authoritative home** for these probes going forward. They are
own-authored ([0BSD](../LICENSE)) and carry no reference-ROM bytes — develop new
zerobas probes here, in public, not in a private workbench. Proprietary oracle
material stays out of the tree by policy ([PUBLISHING.md](../PUBLISHING.md)).
