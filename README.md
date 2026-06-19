# zerobas

A **clean-room, game-loader-scoped MSX1 BASIC**, built as a standalone 16 KB
cartridge ROM. Its goal is *just enough* MSX-BASIC to run the small `.BAS` /
binary loader stubs that boot many disk and tape games — not full-language
compatibility.

zerobas is a deliberately **separate project**. It is combined with an open MSX
BIOS (such as C-BIOS) only *at runtime*, never merged into its source tree. This
is a legal firewall: a provenance challenge to the BASIC code can never
contaminate the mature, uncontested BIOS it runs alongside.

## Traceability is the whole point

Every constant, address, data table, and algorithm in this repo **must trace to
an allowed source.** This is not a guideline — it is the load-bearing property
that makes the code distributable.

- **[`PROVENANCE.md`](PROVENANCE.md)** — the provenance log: one row per item,
  each marked `sourced` (traced to an allowed source) or `quarantined` (no
  allowed source; stubbed or derived, never copied).
- **Inline citations** — every non-obvious value or algorithm in the `.asm`
  files names its source in a comment (e.g. `; spec-bload-r.md §3`,
  `; MSX2 Technical Handbook, cassette I/O`).

**Allowed sources:** the MSX2 Technical Handbook, the MSX Assembly Page
(`map.grauw.nl`), public MSX-BASIC *language* reference, hardware datasheets
(TMS9918 / AY-3-8910 / i8255), C-BIOS sources (BSD 2-clause), and this project's
own black-box **oracle observations**.

**Forbidden, without exception:** any MSX-BASIC / GW-BASIC / BASIC-80 source or
disassembly, and any reference BIOS/BASIC ROM disassembly. These must never be
read by a contributor or fed into any tool or model. A reference ROM is only
ever an *oracle*: identical inputs in, observed outputs out.

The behavioural specifications zerobas is built from live in the companion
analysis repo (`msx-preservation`, under `cbios-basic/docs/`), produced by
driving a real MSX in openMSX as a black box.

## Build

Requires [pasmo](https://pasmo.speccy.org/) (the assembler C-BIOS uses):

```sh
make            # -> basic.rom (16 KB cartridge)
```

## Current status — first light: `BLOAD"CAS:",R`

The first working build is a **tracer bullet**: a single vertical slice that
proves the whole pipeline end to end before any breadth work. The cartridge
INIT (no tokeniser yet) reads a BSAVE-format binary from cassette via the
documented BIOS contract and performs the `,R` handoff:

1. `TAPION` — open tape, skip the file-header tone
2. read + verify the 16-byte file header (binary id `$D0`)
3. `TAPION` — skip the data-block tone
4. read the 6-byte address header (start / end / exec, little-endian)
5. load the payload bytes verbatim into RAM
6. `TAPIOF`, then `JP (exec)` — the `,R` handoff

This is the *interpreter half* of BLOAD. The *device half* (decoding the
cassette signal) is the BIOS's job, via `TAPION`/`TAPIN`.

### Validation

Run the oracle probe (in the `msx-preservation` repo) against this ROM:

```sh
python3 cbios-basic/tools/basic_probe_bload.py \
    --machine Philips_VG_8020 \
    --cart /path/to/zerobas/basic.rom
```

The cartridge boots, auto-loads a self-authored test binary from a `.cas`, and
hands off to it. Expected: `PASS marker JONG at 0xE000` and `PASS PC at landmark`
— byte-for-byte identical to the reference MSX-BASIC's own behaviour.

### Note on C-BIOS

C-BIOS's cassette routines (`TAPION`/`TAPIN`/`TAPIOF`) are **stubs that always
fail** — so a cassette `BLOAD` cannot complete under bare C-BIOS today (the ROM
reaches `BLOAD`, calls `TAPION`, gets a failure, and takes its error path; this
is observable as the byte `$EE` at `$E010`). zerobas's interpreter-half code is
correct regardless; making cassette work under C-BIOS is a C-BIOS task. The
realistic game-loader path on C-BIOS is **disk**, where a disk-interface ROM
provides the device half (`PHYDIO` / the `H.*` hooks) — a future transport here.

## Layout

```
zerobas/
├── README.md
├── PROVENANCE.md      # provenance log (sourced / quarantined)
├── Makefile           # pasmo -> basic.rom, padded to 16 KB
├── src/
│   ├── main.asm       # cartridge header + page padding
│   ├── bload.asm      # the BLOAD"CAS:",R tracer bullet
│   └── sysvars.inc    # BIOS entry points + RAM scratch (all cited)
└── tools/
    └── pad_rom.py     # pad/verify the ROM to exactly 16 KB
```
