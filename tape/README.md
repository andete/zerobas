# cbios-tape

**Make cassette (tape) loading and saving work in openMSX's free C-BIOS.**

[C-BIOS](https://github.com/cbios/cbios) is the open-source MSX BIOS that openMSX
uses when you don't have a real machine's ROM. It boots and runs cartridges fine,
but its **tape support is missing** — try to `RUN"CAS:"` or `CLOAD` a `.cas`/`.wav`
tape and nothing happens (reads hang, writes do nothing).

This project ships a tiny **patch** that fills in those missing tape routines. Apply
it to C-BIOS once and your C-BIOS machine in openMSX can load and save tapes at both
1200 and 2400 baud — just like a real MSX1.

You don't need to compile anything. The patch is already built and included in this
repo:

| File | What it is |
|---|---|
| `cbios-tape-msx1.ips` | The patch, IPS format — used by the installer below |
| `cbios-tape-msx1.bps` | The patch, BPS format — same thing, with a built-in checksum |

The **same patch works on every C-BIOS ROM** openMSX bundles, so the quick-start sets
up all of them at once. Tape is round-trip validated on MSX1, MSX2, **and** MSX2+ —
see [Which machines are supported](#which-machines-are-supported).

---

## Quick start (openMSX)

**Most users want tape *and* BASIC together.** The [zerobas](https://github.com/andete/zerobas)
project ships an installer that applies *both* patches at once — cbios-tape fills in
the cassette routines in page 0, zerobas puts clean-room BASIC in page 1 — and you
get a machine that boots straight to a `BLOAD"CAS:",R`-capable BASIC prompt:

```sh
# in the zerobas repo:
python3 tools/install-openmsx-machine.py   # -> C-BIOS_MSX1_EU_BASIC, etc.
openmsx -machine C-BIOS_MSX1_EU_BASIC
```

If you only want the tape layer (no BASIC — for development, testing, or if you have
another BASIC source), use this repo's own installer instead:

```sh
python3 tools/install-openmsx-machine.py   # -> C-BIOS_MSX1_EU_TAPE, etc.
openmsx -machine C-BIOS_MSX1_EU_TAPE
```

Both installers auto-detect where openMSX keeps its ROMs and write patch-on-load
machine configs into your personal openMSX folder. Nothing inside openMSX itself is
touched, so they survive openMSX updates. Use `--dry-run` to preview, or pass
`--share`/`--user` for non-default locations. If you move this repo, just re-run.

---

## Which machines are supported

| C-BIOS machine | Tape patch |
|---|---|
| `C-BIOS_MSX1` / `_EU` / `_BR` / `_JP` | ✅ supported — round-trip validated |
| `C-BIOS_MSX2` / `_EU` / `_BR` / `_JP` | ✅ supported — round-trip validated |
| `C-BIOS_MSX2+` / `_EU` / `_BR` / `_JP` | ✅ supported — round-trip validated |

The patch carries its own motor routine, so its **only** requirement is a small spare
ROM region — and that region is free in *every* C-BIOS ROM (all 12: MSX1, MSX2,
MSX2+). The installer sets up all of them, and a full BSAVE-style file (header + data
block) round-trips byte-for-byte through the byte-level entry points on each
generation, at both 1200 and 2400 baud. See [DESIGN.md](DESIGN.md) for the details.

---

## Loading and saving a tape

Insert a tape image and use normal MSX BASIC commands.

**Insert a tape:** in openMSX, use the media menu (Tape Deck / Cassette) to insert a
`.cas` or `.wav` file. On the command line: `openmsx -cassetteplayer mytape.cas …`.

**Load and run a BASIC program from tape:**

```basic
RUN"CAS:"
```

or, equivalently, `CLOAD` then `RUN`. For a machine-language (BSAVE) file:

```basic
BLOAD"CAS:",R
```

**Save to tape:** insert a *new, writable* tape via the openMSX Tape Deck (its
"Insert New" / record option), then:

```basic
CSAVE"NAME"                       ' BASIC program
BSAVE"CAS:NAME",start,end,exec    ' machine code
```

The motor, leader tones, and baud rate are all handled for you. Both 1200 and 2400
baud are supported.

---

## Prefer to make a real patched ROM file instead?

If you'd rather produce a standalone, already-patched ROM (instead of patching on
load), apply the **BPS** patch — it carries a checksum, so applying it to the wrong
ROM fails cleanly rather than silently corrupting:

```sh
python3 tools/rom_patch.py apply \
    /path/to/cbios_main_msx1_eu.rom \
    cbios-tape-msx1.bps \
    cbios_main_msx1_eu_tape.rom
```

The result has sha1 `ff8bcf59e457aad5352ec018feeebe236fc0f12b`. The stock EU ROM
ships with openMSX (e.g. on macOS:
`/Applications/openMSX.app/Contents/Resources/share/machines/cbios_main_msx1_eu.rom`).
Standard patch tools (`flips`, Lunar IPS, etc.) work too. To use the result in
openMSX, point a custom machine's `<filename>`/`<sha1>` at this new ROM (sha1
`ff8bcf59…`) instead of the stock one — i.e. a machine config like the installer
generates, but without the `<patches>` block.

---

## Building the patch yourself

The shipped `.ips`/`.bps` are reproducible from `src/tape.asm` with
[pasmo](https://pasmo.speccy.org/) and `python3`:

```sh
make
```

No C-BIOS source is compiled — see **[DESIGN.md](DESIGN.md)** for how the build works
and exactly which bytes the patch changes.

---

## More information

- **[docs/feasibility.md](docs/feasibility.md)** — verdict, scope, and roadmap for
  the clean-room implementation; also the index for the docs.
- **[docs/spec-cassette.md](docs/spec-cassette.md)** — the full behavioural spec of
  the seven entry points, derived by black-box oracle observation.
- **[cassette-tool/](cassette-tool/README.md)** — host-side cassette-audio tools
  for stress-testing this read path against real-tape impairments (WAV degradation
  generator + tolerance sweep) and cataloguing real captures.
- **[DESIGN.md](DESIGN.md)** — what the patch does, how it's built, and why it's a
  separate clean-room project rather than a fork of C-BIOS.
- **[PROVENANCE.md](PROVENANCE.md)** — the provenance log: every constant and
  algorithm traced to an allowed source.
- **C-BIOS** — https://github.com/cbios/cbios (BSD 2-clause). This project ships none
  of its code; the patch is clean-room cassette code plus seven redirected vectors.
