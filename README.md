# zerobas

**zerobas** is a **clean-room reimplementation of MSX1 system software** — the BASIC
interpreter, the cassette layer, and the disk interface — derived only from published
interfaces and this project's own black-box observation of real machines, never from
disassembly of the original ROMs. Three components mirror the hardware they replace:
[`basic/`](basic/) (a standalone 16 KB cartridge ROM), [`tape/`](tape/) (a C-BIOS
cassette patch), and [`disk/`](disk/) (a disk-interface ROM).

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

zerobas is a deliberately **separate project**. It is combined with an open MSX
BIOS (such as C-BIOS) only *at runtime*, never merged into its source tree. This
is a legal firewall: a provenance challenge to zerobas can never contaminate the
mature, uncontested BIOS it runs alongside.

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
reclaims `$2812-$3FFF` from C-BIOS's page 0, so the shipped image spans
`$2812-$7FFF`.

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
targets the EU ROM. Until 2026-07-29 zerobas also shipped `zerobas-msx1.ips/.bps`, a
region-universal page-1 splice carrying a **lean 16 KB build** — but that build was
not a smaller zerobas, it was one missing seven source files (no strings, no `INPUT`,
no floats, no arrays, no error codes, no KEY traps), so it is retired. As of
2026-07-29 it is gone from the source too: the 284 `IF ROM_BASE` gates that selected
it are deleted and `basic/main.asm` assembles the one image
([`docs/spec-lean-retire-s3-gates.md`](docs/spec-lean-retire-s3-gates.md)).

To run it in openMSX without touching any ROM, `make machines` installs ready
machine configs into your openMSX user dir — a `C-BIOS_MSX1_EU_BASIC` and a
`C-BIOS_MSX1_EU_BASIC_DISK` (+ zerobas-disk in slot 3-1), each with zerobas-sub in
slot 3-2, plus a region-universal `*_TAPE` per C-BIOS region:

```sh
make machines                      # -> C-BIOS_MSX1[_BR/_EU/_JP]_BASIC[_DISK]
openmsx -machine C-BIOS_MSX1_BASIC               # boots straight to the ZB prompt
openmsx -machine C-BIOS_MSX1_BASIC_DISK -diska disk/test720.dsk   # + disk
```

These configs embed absolute paths to your openMSX ROMs and this repo, so they're
an install (regenerated per environment), not a portable file — which is why
`make machines` is separate from `make`. (zerobas is MSX1 BASIC, so only the MSX1
C-BIOS variants are targeted. The BPS is CRC-locked to one stock ROM and fails
cleanly on a mismatch; the IPS is universal and is what the configs use. The
`National_CF-3300_ZEROBASDISK` provider-oracle is a test machine — `make
machines-oracle` — not part of the release set.)

## Current status — byte-identical crunch + REM / POKE / PEEK + `BLOAD"CAS:",R`

The build has a real (if tiny) interpreter spine with a keyboard prompt, a
16-bit integer expression evaluator, single-letter integer variables, and a
`:`-separated statement loop. Statements: `BLOAD` (cassette load + `,R`
handoff), `POKE`, `REM` (and its `'` abbreviation), a `<letter> = <expr>`
assignment, and `PEEK(...)` as an expression function. On boot the cartridge
INIT prints a startup header, then runs a read/eval loop: read a typed line,
tokenise it, dispatch each statement, repeat.

Expressions are 16-bit unsigned integers: decimal and `&H` hex literals,
single-letter variables `A`–`Z`, `PEEK(expr)`, parentheses, unary `-`, and
`+ - *` (with `*` binding tighter). As of **Step A** the tokeniser crunches
**byte-identically** to a real MSX-BASIC ROM: integer constants (`$11+n` /
`$0F`,b / `$1C`,w-LE), `&H` constants (`$0C`,w-LE), and the operators
`= + - *` (`$EF $F1 $F2 $F3`) all use the reference's exact token bytes
(oracle-sourced, `spec-tokens-statements.md §3/§4`); letters are upcased outside
string literals; and the evaluator *decodes* these tokens at run time. This is
verified against the reference VG-8020 by a differential crunch test
(`basic_probe_crunch.py`): zerobas's `TOKBUF` equals the reference's `KBUF`, byte
for byte. ~~(Decimal `≥ 32768` — which the reference stores as a float — plus
`&O`/`&B` and line-number references are out of scope for now; use `&H` for
16-bit values.)~~ 📏 **Stale, and measured 2026-09-05**: `PRINT 40000` reads
`40000`, `PRINT &O17` reads `15`, and the tokeniser emits the `$0E`
line-number identification code for branch targets. **`&B` stays out on
purpose**, not for want of work — the oracle emits no `&B` token, so zerobas
fabricates none (`basic/PROVENANCE.md`, quarantined).

0. **header** — `INITXT` brings up the text screen; `CHPUT` prints a couple of
   original left-aligned lines (the same role as MSX-BASIC's top-of-screen
   header before its prompt — no reference text copied)
1. **prompt + line editor** — print `ZB` (deliberately *not* `Ok`, so zerobas
   is never mistaken for stock MSX-BASIC) and read a line via `CHGET`, echoing
   with Backspace editing until Enter (both `$08` and `$7F`/DEL erase left, so
   the Mac Backspace key — which openMSX delivers as the MSX DEL key — works)
2. **tokenise** the line → **byte-identical to a real MSX-BASIC ROM**: keywords
   (`BLOAD`→`$CF`, `POKE`→`$98`, `PEEK`→`$FF $97`, `REM`→`$8F`), the integer/`&H`
   constants, and the `= + - *` operators all crunch to the reference's exact
   token bytes; letters are upcased outside string literals; string literals and
   the `REM`/`'` comment tail are kept verbatim; the line is `$00`-terminated
   (see `spec-tokenise.md`, `spec-tokens-statements.md`)
3. **execute** — walk the line statement-by-statement (`:` separated),
   dispatching each on its leading token through the statement table; an empty
   line reprompts and an unknown one raises `Syntax error`.
   ~~dispatching each on its leading token: `POKE`, a `<letter> = <expr>`
   assignment, `REM` (ends the line), `BLOAD`~~ 📏 **That four-statement list is
   the loader-era slice.** The dispatcher now covers the MSX1 statement surface —
   `make kwsweep` reports **0 MISSING** reserved words (2026-09-05); see *What is
   implemented, and what is not* below.
4. the **BLOAD handler** parses `"CAS:"` (device) and optional `,R`, then:
   - `TAPION` — open tape, skip the file-header tone
   - read + verify the 16-byte file header (binary id `$D0`)
   - `TAPION` — skip the data-block tone
   - read the 6-byte address header (start / end / exec, little-endian)
   - load the payload bytes verbatim into RAM
   - `TAPIOF`, then (for `,R`) `JP (exec)` — the handoff

This is the *interpreter half* of BLOAD. The *device half* (decoding the
cassette signal) is the BIOS's job, via `TAPION`/`TAPIN`.

### What is implemented, and what is not

> 📏 **THIS SECTION IS GENERATED FROM MEASUREMENTS, NOT FROM MEMORY**, and the
> figures below were re-read on **2026-09-05**. Re-run them rather than trusting
> them: `make kwsweep` for the keyword axis, `make gates` for the battery, and
> `TODO.md`'s open list for the divergences. It replaces a *"Limitations (this
> slice)"* section that described a game-loader-scoped slice from early in the
> project — it listed `ON … GOTO` as "still out" and said variables were
> single-letter integers with no strings or arrays, all of which predate the
> string engine, the float pack and the array engine, and all of which the
> charter change to **faithful full MSX1 BASIC** superseded.

**The keyword axis is closed.** `make kwsweep` walks the MSX1 reserved-word list
and reports, today: **0 MISSING**, 35 SUPPORTED, 1 DIVERGENT. It executes 37 of
55 words; the other 18 are crunch-only and each says why (destructive, printer-
bound, blocking on a keypress, or needing a disk fixture).

⚠️ **The one DIVERGENT is not a defect and checking that is the point.** `CSRLIN`
reads `4` on the reference and `3` here in a row that has no `CLS`, so it reports
wherever the boot banner and the batch's own scrolling left the cursor — the
reference disagrees with *itself* (4 vs 9) across differently-scrolled batches.
`CSRLIN` is correct and gated at a pinned `WIDTH 40` by `cursor-acceptance`.

**Variables and expressions are the real MSX1 surface**: integers, floats and
strings with multi-character names and type suffixes (`% ! # $`), arrays with
`DIM`, `DEF FN`, the full operator set including `/` and `^`, string functions,
and `PRINT USING`. The three-page ROM layout that made a single-letter integer
slice necessary is long gone.

**What is measurably still divergent**, each with a row set and a TODO entry —
this list is the honest part, and it is short:

* **`SCREEN 3` pixel operations** — `PSET`/`LINE` draw on both references and
  raise `Illegal function call` here. A whole feature: there is no SCREEN-3
  rasteriser, and the refusal is correct for every mode that IS implemented.
* **A SCREEN-2 `PAINT` with `C != B`** floods the whole screen on both
  references; here it stops at any pixel whose colour is `B`. Measured
  2026-09-05: the references do not bound the fill at all in that regime.
* **`OPEN … LEN=r`** accepts any `1..256` on the CF-3300 and only the powers of
  two here — a deliberate limit while `fat_rand_put`/`fat_rand_get` cannot span
  two sectors, not an oversight.
* **Unary `+` on a STRING** (`B$=+A$`) is `Type mismatch` here and the identity
  there. The numeric forms were fixed 2026-09-05.
* **`LOAD"CAS:"` on a tokenised tape** — the reference searches to end-of-tape
  and does not return, which no acceptance row can express.

**The battery is the standing answer to "does it still work":** `make gates`
runs **114 units** — static checks plus differential probes that boot a real
Philips VG-8020 and a National CF-3300 in openMSX beside the zerobas image and
compare readings row by row.

### Validation

Run the oracle probes ([`probes/`](probes)) against this ROM:

These run zerobas on the installed repack machine (`make repack-machine` first);
the reference side, where a probe has one, is a stock Philips VG-8020. Nothing
inserts a cartridge any more — the merged main ROM is slot 0.

```sh
# BLOAD pipeline (tokenise → execute → cassette load → ,R handoff)
python3 probes/basic/basic_probe_bload.py \
    --machine C-BIOS_MSX1_EU_REPACK_DISK

# REM / POKE / PEEK / expression evaluator (results read back from RAM)
python3 probes/basic/basic_probe_statements.py

# Byte-identical crunch — zerobas TOKBUF vs reference KBUF, per line
python3 probes/basic/basic_probe_crunch.py \
    --machine Philips_VG_8020 --zb-machine C-BIOS_MSX1_EU_REPACK_DISK

# LIST / detokeniser round-trip, read off the SCREEN 0 name table
python3 probes/basic/basic_probe_list.py

# Cassette verbs (CSAVE/CLOAD/SAVE"CAS:"/LOAD"CAS:"/MERGE/OPEN"CAS:")
python3 probes/basic/basic_probe_cas_verbs.py
```

⚠️ **A probe moved between machines measures the MACHINE too.** Measured
2026-07-29: a Philips VG-8020 lays SCREEN 0 text out at column **2** and a C-BIOS
machine at column **1**, so a raw name-table diff across the two reports the margin
as a PRINT defect. `basic_probe_print.py` pins the margin per capture off that
capture's own echo row; any new cross-machine screen probe must do the same.

zerobas boots to its prompt, the probe types a line + Enter, and the
result is observed by dumping RAM (no PRINT). Expected: `ALL PASS` for the
statements probe, and `PASS marker JONG at 0xE000` / `PASS PC at landmark` for
BLOAD — byte-for-byte identical to the reference MSX-BASIC's own behaviour.

### Note on C-BIOS

C-BIOS's *own* cassette routines (`TAPION`/`TAPIN`/`TAPIOF`) are **stubs that
always fail** — so on bare C-BIOS a cassette `BLOAD` cannot complete (the ROM
reaches `BLOAD`, calls `TAPION`, gets a failure, and takes its error path,
observable as the byte `$EE` at `$E010`). The [`tape/`](tape/) component of
this repo supplies real `TAPION`/`TAPIN`/`TAPIOF` in page 0, and the installer
([tools/install-openmsx-machine.py](tools/install-openmsx-machine.py)) applies
**both** IPS patches — tape (page 0) then zerobas (page 1) — so the full
cassette `BLOAD` pipeline completes end-to-end: C-BIOS + tape (device half) +
zerobas (interpreter half).

The second transport is **disk** (`disk/` → `disk.rom`, slot 3-1) — **complete**:
a standard disk-interface ROM provides the device half (`PHYDIO` / the `H.*`
hooks + `GETDPB`), `basic.rom` owns the FAT12 filesystem and drives it through the
standard `$4010` DSKIO interface, and the interpreter exposes a full Disk BASIC
file-channel verb surface (`OPEN`/`PRINT#`/`INPUT#`, random-access
`FIELD`/`GET`/`PUT`, `FILES`/`KILL`/`NAME`, `PRINT USING`, `CALL FORMAT`, …), each
oracle-validated against a real National CF-3300. The verb surface was the
**Phase 2** charter raise on the disk axis; **Phase 3** then raised the core
*language* charter from loader-stub to **faithful full MSX1 BASIC** — floats, the
full string engine, and arrays/DIM have since landed, with graphics and sound still
ahead.
See [`TODO.md`](TODO.md) for the per-verb status.

## Layout

```
zerobas/
├── README.md
├── PROVENANCE.md      # provenance index -> per-component logs below
├── Makefile           # `make` -> all deliverables; `make machines` -> openMSX configs
├── build/             # gitignored build artifacts (disk.rom, sub.rom, ...)
├── zerobas-main-eu.ips  # shipped BASIC: merged repack main ROM, IPS (EU; used by installer)
├── zerobas-main-eu.bps  # shipped BASIC: merged repack main ROM, BPS (CRC-locked)
├── basic/
│   ├── main.asm       # org $2812 + "AB" header + includes + page padding ($00 fill)
│   ├── interp.asm     # tokeniser + statement-loop executor (INIT entry)
│   ├── title.asm      # startup header lines (INITXT + CHPUT)
│   ├── repl.asm       # keyboard line editor + read/eval loop (ZB prompt)
│   ├── vars.asm       # integer variable store (A..Z, 16-bit)
│   ├── expr.asm       # 16-bit integer expression evaluator (incl. PEEK)
│   ├── poke.asm       # the POKE statement handler
│   ├── bload.asm      # the BLOAD statement handler + ,R handoff
│   ├── sysvars.inc    # BIOS entry points + tokens + RAM scratch (all cited)
│   └── PROVENANCE.md  # BASIC-component provenance log
├── tape/
│   ├── tape.asm       # cassette BIOS patch (TAPION / TAPIN / TAPIOF)
│   ├── zerobas-tape-msx1.ips     # page-0 tape patch, IPS (used by installer)
│   ├── zerobas-tape-msx1.bps     # page-0 tape patch, BPS (CRC-locked)
│   ├── PROVENANCE.md  # tape-component provenance log
│   ├── DESIGN.md      # design notes for the tape patch
│   ├── docs/          # cassette spec and feasibility notes
│   └── cassette-tool/ # host-side WAV/CAS analysis tools
├── disk/
│   └── PROVENANCE.md  # disk-component provenance log (FDC, FAT12, BDOS — complete)
└── tools/
    ├── pad_rom.py     # pad/verify the ROM to exactly 16 KB
    ├── rom_patch.py   # make/apply/inspect IPS + BPS patches
    ├── overlay_page1.py        # splice zerobas into C-BIOS page 1 + vet the splice
    ├── build_patches.py        # build the IPS/BPS patches (portable; page-1 + --tape)
    ├── openmsx_paths.py        # cross-platform openMSX / C-BIOS path discovery
    └── install-openmsx-machine.py  # write *_BASIC machines that patch on load
```
