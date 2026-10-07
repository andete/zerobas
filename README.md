# zerobas

**zerobas** is a **clean-room reimplementation of MSX1 system software** — the BASIC
interpreter, the cassette layer, and the disk interface — derived only from published
interfaces and this project's own black-box observation of real machines, never from
disassembly of the original ROMs. The components mirror the hardware they replace:
[`basic/`](basic/) (the interpreter, built into a C-BIOS main-ROM image) with its
sub-ROM [`sub/`](sub/), [`tape/`](tape/) (the cassette BIOS layer), and
[`disk/`](disk/) (a disk-interface ROM with its own Disk BASIC and file layer).

It has **two co-equal goals**: producing the clean-room *implementations*, and —
because the same discipline makes the resulting facts publishable — producing
**clean-provenance documentation** of how these systems actually work, especially
where good documentation does not yet exist (see [`MISSION.md`](MISSION.md)).

**Scope today is MSX1.** The BASIC half targets **faithful, full MSX1 BASIC** — a
clean-room reimplementation of the real MSX1 MSX-BASIC language, reference-compatible
where clean-room-achievable. (It began life *game-loader-scoped* — just enough to run
the `.BAS` / binary loader stubs that boot disk and tape games; that Phase-1 target is
complete, and the charter has since been raised to full-language faithfulness, which
Phase-3 pursues.) The cassette and disk halves are device-complete (read **and**
write). Post-MSX1 axes (MSX2 / 2+ / Turbo-R, and extension hardware such as the V9990
and Konami SCC/SCC+) are catalogued in [`TODO.md`](TODO.md) but remain out of charter
until a charter raise.

zerobas is a deliberately **separate project** from the open BIOS it runs on
(C-BIOS). It copies no C-BIOS code: it ships as a **patch** against a stock C-BIOS
ROM, and the few edits it needs inside C-BIOS itself are kept as small, reviewable
patch files against a pinned C-BIOS tag ([`cbios-repack/`](cbios-repack/)), whose
BSD-2 notice travels with the result. This is a legal firewall: a provenance
challenge to zerobas can never contaminate the mature, uncontested BIOS it runs
alongside.

## Two co-equal goals

zerobas has **two deliverables, not one**: the clean-room **implementations**, and the
clean-provenance **documentation** of how these systems work that the same discipline
yields — and where good documentation does not yet exist, producing it is a
**first-class goal, not a byproduct**. The same firewall that keeps the code
distributable is what makes the documentation publishable, so the artefacts the work
throws off (the [`PROVENANCE.md`](PROVENANCE.md) logs, the oracle probes, the
behavioural specs and characterisation notes, the rated source catalogue) are
themselves safe for the community to build on.

**The full charter — why the two are one discipline, how to aim the documentation
(value scales inversely with what already exists), "source not sink", and why even the
walls are deliverables — is [`MISSION.md`](MISSION.md).**

## Traceability is the whole point

Every constant, address, data table, and algorithm in this repo **must trace to
an allowed source.** This is not a guideline — it is the load-bearing property
that makes the code distributable.

- **[`PROVENANCE.md`](PROVENANCE.md)** — the provenance index, pointing at one
  log per component ([`basic/`](basic/PROVENANCE.md), [`tape/`](tape/PROVENANCE.md),
  [`disk/`](disk/PROVENANCE.md)). Each log has one row per item, marked `sourced`
  (traced to an allowed source) or `quarantined` (no allowed source; stubbed or
  derived, never copied).
- **Inline citations** — every non-obvious value or algorithm in the `.asm`
  files names its source in a comment (e.g. `; spec-bload-r.md §3`,
  `; MSX2 Technical Handbook, cassette I/O`).
- **[`docs/dev-workflow.md`](docs/dev-workflow.md)** — how to add a feature and
  prove it correct: the per-feature checklist, the openMSX validation harness,
  and the tokeniser quirks a new session must know.

**The one test that governs every source.** Documentation may be used only where
it specifies a **published / standard interface the original was built to conform
to** — never where it reveals a reference implementation's *internals*. Internal
behaviour that appears in no published spec is reverse-engineered knowledge of
protected code, and stays forbidden even after it has been copied into a wiki, a
forum post, or an annotated "documentation" file. Each item below lists *what may
be taken from it*; nothing beyond that scope is sourced.

| Allowed source | What may be taken from it — and only this |
|----------------|-------------------------------------------|
| **MSX2 Technical Handbook** (Konamiman's public English translation) | documented BIOS / BDOS / hardware *interfaces*: entry addresses, calling conventions, work-area layouts. Never any reproduced ROM code. |
| **MSX Assembly Page** (`map.grauw.nl`) | the *standard* BIOS-call / system-variable interface it consolidates; corroborate against the TH for anything that looks implementation-internal. |
| **Public MSX-BASIC language & file-format reference** | language syntax / semantics and on-disk / on-tape file-format layouts (the user-visible contract). Never interpreter internals. |
| **Hardware datasheets** (TMS9918, AY-3-8910, i8255, MB8877A — the CF-3300 FDC — and the WD179x/WD2793-compatible reference) | full register / timing / command specs. Gold standard, no restriction. |
| **Open standards** (Microsoft FAT spec, ECMA-107) | FAT12 and 3.5" disk-geometry structures. |
| **National CF-3300 schematic** (open hardware) | FDC wiring / memory-mapped register window — hardware facts only (pin the exact document; see disk/PROVENANCE.md). |
| **C-BIOS** (BSD 2-clause) | system-variable *addresses* and standard-interface *facts* only (it is itself a clean-room BIOS). Do not copy its code/expression without honouring BSD-2. |
| **openMSX** (GPL) | hardware *register addresses / port maps* only — facts, never code (GPL must not enter this 0BSD tree). |
| **komkon MSX docs** (`fms.komkon.org`) | published hook / system-variable *address tables* (facts) only — not RE-derived routine-behaviour descriptions. |
| **Nextor Driver Development Guide** | the documented DPB / disk-driver *interface contract* only — never Nextor source code. |
| **Open-sourced third-party MSX software** (demos, homebrew — *low-tier, corroboration only*) | a non-authoritative *worked example* of how a **documented public hardware interface** is exercised, to corroborate a datasheet/oracle — never as primary documentation. Only the author's original work (nothing it lifted from a proprietary ROM); techniques, never copied code; never for BIOS/BASIC/DOS behaviour. See [`docs/allowed-sources.md`](docs/allowed-sources.md). |
| **This project's own black-box oracle** | observed input→output behaviour of a real MSX. The gold standard — *provided it stays black-box*: observe outputs, never read or disassemble a reference ROM or any proprietary binary (BIOS, MSX-BASIC ROM, disk-ROM, MSXDOS.SYS, COMMAND.COM). |

**Forbidden, without exception:** any MSX-BASIC / GW-BASIC / BASIC-80 source or
disassembly; any reference BIOS / BASIC-ROM / disk-ROM disassembly; and the bytes
of any proprietary system binary (reference ROM, MSXDOS.SYS, COMMAND.COM) read as
anything other than an *oracle* — identical inputs in, observed outputs out. The
**MSX Wiki, MSX Resource Center, and other community reverse-engineering
compilations are NOT allowed sources**: where they merely restate a published
interface, cite that published source instead; where they reveal proprietary
internals, they are out. These rules must never be broken by a contributor or by
any tool or model — see [`CONTRIBUTING.md`](CONTRIBUTING.md), which turns this
firewall into a contribution gate with a clean-room sign-off.

The **full rated, per-document catalogue** — every concrete document graded by
quality (A/B/C) and mapped to the MSX generation(s) it serves, including the
VDP / sound / CPU datasheets for MSX2 / MSX2+ / Turbo-R — lives in
[`docs/allowed-sources.md`](docs/allowed-sources.md).

The behavioural specifications zerobas is built from live beside the code in the
component `docs/` directories (e.g. [`basic/docs/`](basic/docs)), produced by
driving a real MSX in openMSX as a black box. The broader characterisation corpus
and workbench stay in a private analysis area (see [`PUBLISHING.md`](PUBLISHING.md)).

## Authorship & AI assistance

This project is **human-authored and human-directed** by Joost Yervante Damad.
The architecture, the clean-room methodology, the oracle-not-answer-key approach,
and every design and staging decision are his; AI coding assistants (Anthropic's
Claude) were used as a **tool** under that direction — drafting, refactoring, and
exploring under review — much like a compiler or an editor's autocomplete, not as
an independent author.

A few consequences worth stating plainly:

- **Ownership.** The work is owned by its human author and licensed under
  [0BSD](LICENSE) (see *License* below). AI assistance confers no third-party
  rights: under Anthropic's terms the output belongs to the user, and Anthropic
  claims no copyright in it.
- **The `Co-Authored-By: Claude` trailer** on some commits is an attribution and
  transparency convention — a record that an AI assisted — **not** a legal
  co-authorship or rights claim.
- **The provenance firewall applies to the AI too.** The
  [clean-room rules](tape/docs/clean-room-policy.md) bind every contributor *and
  every tool or model*: no MSX-BASIC / GW-BASIC / BASIC-80 source, and no
  reference BIOS/BASIC ROM disassembly, is ever read by a human or fed into a
  model. AI context is restricted to the same allowed sources, behavioural specs,
  and black-box oracle observations as a human contributor.

The real protection here is not copyright — much clean-room BIOS code, constrained
to a fixed hardware contract, is thinly protectable regardless of who or what
typed it — but the **provenance discipline** above: the demonstrable absence of
copied expression.

## License

The entire project — **both the code and the documentation** — is released under the
**[BSD Zero Clause License (0BSD)](LICENSE)**, the most permissive option: use, copy,
modify, and redistribute for any purpose, with **no conditions and no attribution
requirement**. This is deliberate and serves the mission ([`MISSION.md`](MISSION.md)):
the implementations *and* the clean-provenance documentation are meant to be a
community resource anyone can build on freely.

- **No warranty, no liability.** The work is provided **"AS IS"**, without warranty of
  any kind; **in no event shall the author be liable** for any claim, damages, or other
  liability arising from its use (the full disclaimer is in [`LICENSE`](LICENSE), and it
  is the author's published term whether or not a redistributor reproduces it).
- **Patents.** The author **asserts no patents** over this work and never will. 0BSD is
  patent-silent by design; this pledge states the intent plainly — information here is
  meant to be free, and patents only stifle that.
- **Why 0BSD (not CC0) for the docs.** A single permissive license keeps the project
  simple and avoids CC0's explicit patent reservation (the basis of its rejection from
  Debian main); 0BSD also carries the no-warranty **and** no-liability disclaimer that
  CC0 lacks.

This covers only zerobas's own work. It does **not** relicense anything it merely
interoperates with: **C-BIOS** stays BSD-2-Clause and **openMSX** stays GPL — zerobas
combines with them at runtime only and copies no code from either (see the provenance
firewall above).

The shipped patches (`zerobas-main-eu.ips` / `.bps`) do carry **compiled C-BIOS bytes**:
the repack edits C-BIOS source ([`cbios-repack/`](cbios-repack/)) and the result is part
of the patched image. C-BIOS's own BSD-2 notice therefore travels with them —
[`cbios-repack/LICENSE.C-BIOS`](cbios-repack/LICENSE.C-BIOS), verbatim from the pinned
C-BIOS tag.

## Build

The build is cross-platform — it needs only [pasmo](https://pasmo.speccy.org/) (the
assembler C-BIOS uses), `python3`, and `make`. No part of the **deliverable** build
depends on openMSX. (Building it on Linux / Windows is detailed in
[`docs/portability.md`](docs/portability.md).)

Prerequisites:

| OS | Install |
|----|---------|
| **Linux** (Debian/Ubuntu) | `sudo apt-get install pasmo python3 make` |
| **macOS** | `python3` + `make` from the Xcode CLI tools; install pasmo from [source](https://pasmo.speccy.org/) |
| **Windows** | `python3` from python.org, plus `pasmo` + `make` (via [MSYS2](https://www.msys2.org/), Git Bash, or WSL — the build needs a Unix-style `make`) |

```sh
make            # everything needing no C-BIOS checkout: build/disk.rom,
                #   build/sub.rom, tape/zerobas-tape-msx1.ips/.bps
make release    # + regenerate the shipped BASIC patch (needs CBIOS=<checkout>)
make unit-test  # emulator-free Z80 unit tests (no openMSX, no reference ROMs)
make machines   # install the openMSX machine configs (see below)
make install    # make + make machines
```

The tape patch needs a stock C-BIOS main ROM to stamp/verify against;
`tools/build_patches.py` auto-detects openMSX's bundled copy (Linux / macOS /
Windows install locations), or pass `STOCK=<path>`. ROMs land in the gitignored
`build/`; the `.ips/.bps` patches are tracked at the repo root.

## How it runs: patched in next to the BIOS

On a real machine BASIC sits in **slot 0 page 1 (`$4000-$7FFF`), right next to the
BIOS in page 0**, as one ROM. C-BIOS has no BASIC, so it leaves that space free —
which is exactly the space zerobas is built for, and then some: zerobas also
reclaims `$2765-$3FFF` from C-BIOS's page 0, so the shipped image spans
`$2765-$7FFF`. Code that does not fit there lives in a **sub-ROM** in slot 3-2
([`sub/`](sub/)), and Disk BASIC in its own **disk ROM** in slot 3-1
([`disk/`](disk/)) — the same places a real MSX keeps them.

zerobas therefore ships as a **patch** against a stock C-BIOS main ROM — the same
legal firewall as everything else here: C-BIOS and zerobas stay separate trees and
are combined only at apply-time. C-BIOS's cold-boot cartridge scan reaches its own
slot-0 page 1, finds zerobas's "AB" header at `$4000`, and calls INIT — so **no
boot-vector patch is needed**; the cartridge header does double duty.

`make release` builds that pair (`zerobas-main-eu.ips/.bps`) by diffing the merged
image against a pristine C-BIOS built from a pinned tag, so **regenerating** it needs
a C-BIOS checkout (`CBIOS=<path>`). **Applying** it does not: that pristine ROM is
byte-identical to openMSX's own bundled `cbios_main_msx1_eu.rom`.

⚠️ **EU only.** The repack rewrites C-BIOS's page-0 layout, so the shipped patch
targets the EU C-BIOS ROM.

To run it in openMSX without touching any ROM, `make machines` installs ready
machine configs into your openMSX user dir — a `C-BIOS_MSX1_EU_BASIC` (no disk) and
a `C-BIOS_MSX1_EU_BASIC_DISK` (+ zerobas-disk in slot 3-1), each with zerobas-sub in
slot 3-2, plus a `*_TAPE` machine per C-BIOS region:

```sh
make machines                                        # -> C-BIOS_MSX1_EU_BASIC[_DISK]
openmsx -machine C-BIOS_MSX1_EU_BASIC                # boots straight to the ZB prompt
openmsx -machine C-BIOS_MSX1_EU_BASIC_DISK -diska disk/test720.dsk   # + disk
```

For development, `make repack-machine` installs the two machines the test battery
uses, built from your working tree: `C-BIOS_MSX1_EU_REPACK_DISK` and
`C-BIOS_MSX1_EU_REPACK_NODISK`.

These configs embed absolute paths to your openMSX ROMs and this repo, so they're
an install (regenerated per environment), not a portable file — which is why
`make machines` is separate from `make`. (zerobas is MSX1 BASIC, so only the MSX1
C-BIOS variants are targeted. The BPS is CRC-locked to one stock ROM and fails
cleanly on a mismatch; the IPS is universal and is what the configs use. The
`National_CF-3300_ZEROBASDISK` provider-oracle is a test machine — `make
machines-oracle` — not part of the release set.)

## What works

zerobas aims to run **any MSX1 BASIC program as a real MSX1 does**, and is most of
the way there:

- **The language** — integers, single- and double-precision floats with the MSX
  BCD maths (`SIN`, `LOG`, `^`, …), strings, arrays, `DEF FN`, `PRINT USING`,
  `DATA`/`READ`, the full control-flow set, and error handling (`ON ERROR`,
  `RESUME`, `ERR`/`ERL`) that raises the reference's error code on the
  reference's line.
- **The machine** — the screen editor, `KEY` / `STOP` / `SPRITE` / `STRIG` /
  `INTERVAL` traps, the MSX1 screen modes and graphics statements (`PSET`,
  `LINE`, `CIRCLE`, `PAINT`, `DRAW`, sprites), `PLAY` and `SOUND`, joystick and
  paddle input, `USR` / `DEFUSR` machine-code calls.
- **Storage** — cassette (`CSAVE`/`CLOAD`, ASCII `SAVE`/`LOAD`/`MERGE`, `BSAVE`/
  `BLOAD`, `OPEN"CAS:"`) and **Disk BASIC** (`FILES`, `KILL`, `NAME`, `COPY`,
  sequential and random files with `FIELD`/`GET`/`PUT`, `BLOAD`/`BSAVE`, `DSKF`,
  …) on a FAT12 floppy.
- **Two targets** — a disk machine (checked against a National CF-3300) and a
  **diskless** one (checked against a Philips VG-8020), where the cassette is the
  default device as on a real cassette-only MSX.

**The live, per-keyword status is [`docs/tier-status.md`](docs/tier-status.md)**,
generated from measurements (`make tiers-md`), never typed by hand. For every one of
the 159 MSX1 reserved words it shows which rungs are proven: every form agrees with
the reference (T1), it completes within 10× the reference's time (T2), its common
errors match (T3), its RAM use (T4), its speed ratio (T5) and its full error set
(T6) — and lists the open TODO items against it.

**Known gaps**, all tracked in [`TODO.md`](TODO.md) by priority tier:

- **Speed.** The interpreter is roughly 2.5–4× slower than the reference — inside
  the 10× "reasonable time" bar, but not on par yet.
- **String space.** A string literal assigned in a program is still copied into
  string space, where the reference points at the program text, so programs that
  fill large string arrays from literals can run out of string space here only.
- **RAM usage** is measured but not yet proven equal to the reference's.
- **Rare error paths** — the long tail of unusual errors (TIER 6).
- **MSX2 and later** are out of scope for now.

## How it is checked

Every claim above is **measured against a real machine**, never against memory or
a specification alone. The probes in [`probes/`](probes/) boot a stock Philips
VG-8020 and a National CF-3300 in openMSX next to zerobas, type the same BASIC into
both, and compare what comes back — screen text, error code and line, RAM, VRAM.

```sh
make repack-machine   # build + install the two machines the probes use
make gates            # the whole battery: static checks + reference differentials
make gates-fast       # the static half only
make kwsweep          # every MSX1 keyword's forms, reference vs zerobas
make tiers-md         # regenerate docs/tier-status.md from the measurements
```

A change is only accepted when it ships with its proof: a probe row that agreed
with the reference **for the right reason**, and a **knife** — the fix deliberately
cut out again, showing that exactly those rows go red. The reference ROMs
themselves are never read: the oracle is used strictly as a black box.

Real programs are part of the check too: [`scratchpad/vleermuis/`](scratchpad/vleermuis/)
loads a 1989 type-in game (MIT-licensed) from a generated cassette image on both
machines and compares them — it found a string-space defect no keyword row had.

## Layout

```
zerobas/
├── README.md, MISSION.md, PROVENANCE.md, CONTRIBUTING.md, PUBLISHING.md, LICENSE
├── TODO.md                 # every open item, by priority tier
├── Makefile                # `make` -> deliverables; `make machines`; `make gates`
├── zerobas-main-eu.ips/.bps  # the shipped BASIC: a patch against stock C-BIOS (EU)
├── basic/                  # the interpreter (relocated into the main ROM image)
│   ├── main.asm            # the image: includes + layout
│   ├── interp.asm          # tokeniser + statement executor
│   ├── expr.asm, float*.asm, str-engine.asm, vars.asm, arrays.asm, ...
│   ├── docs/               # behavioural specs
│   └── PROVENANCE.md
├── sub/                    # the sub-ROM (slot 3-2): heap, graphics, PLAY, ... tenants
├── disk/                   # the disk-interface ROM (slot 3-1): Disk BASIC, FAT12, BDOS
├── tape/                   # the cassette BIOS layer
├── cbios-repack/           # our patches to C-BIOS source + its licence notice
├── probes/                 # the black-box oracle harness (openMSX) and its probes
├── tests/                  # emulator-free unit tests (`make unit-test`)
├── tools/                  # build, patching, gate and measurement tools
├── docs/                   # specs, characterisations, tier-status.md
└── scratchpad/             # working evidence: probe outputs, knives, experiments
```
