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

**Scope today is MSX1.** The BASIC half is deliberately **game-loader-scoped** — *just
enough* MSX-BASIC to run the small `.BAS` / binary loader stubs that boot many disk and
tape games, not full-language compatibility — while the cassette and disk halves are
device-complete (read **and** write). Post-MSX1 axes (MSX2 / 2+ / Turbo-R, and
extension hardware such as the V9990 and Konami SCC/SCC+) are catalogued in
[`TODO.md`](TODO.md) but remain out of charter until a charter raise.

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

The behavioural specifications zerobas is built from live in the companion
analysis repo (`msx-preservation`, under `basic-spec/docs/`), produced by
driving a real MSX in openMSX as a black box.

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

## Build

Requires [pasmo](https://pasmo.speccy.org/) (the assembler C-BIOS uses):

```sh
make            # all portable deliverables: build/basic.rom, build/disk.rom,
                #   zerobas-msx1.ips/.bps, tape/zerobas-tape-msx1.ips/.bps
make machines   # install the openMSX machine configs (see below)
make install    # make + make machines
```

The patch deliverables need a stock C-BIOS main ROM to stamp/verify against;
`build-patches.sh` auto-detects openMSX's bundled copy, or pass `STOCK=<path>`.
ROMs land in the gitignored `build/`; the `.ips/.bps` patches are tracked at the
repo root.

## Two ways to run it: cartridge, or patched in next to the BIOS

`build/basic.rom` is an "AB" cartridge: drop it into any MSX slot and the BIOS finds
the header at `$4000` and calls INIT. That works, but it isn't where BASIC lives
on a real machine — there it sits in **slot 0 page 1 (`$4000-$7FFF`), right next
to the BIOS in page 0**, as one ROM. C-BIOS has no BASIC, so it leaves that page
almost empty — exactly the space zerobas is built for.

So zerobas can also ship as a **patch** that drops it into a stock C-BIOS main
ROM — the same legal firewall: C-BIOS and zerobas stay separate trees and are
combined only at apply-time. C-BIOS's cold-boot cartridge scan reaches its own
slot-0 page 1, finds zerobas's "AB" header, and calls INIT — so **no
boot-vector patch is needed**; the cartridge header does double duty.

`make patches` (a subset of `make`) does this: `build-patches.sh` splices
`build/basic.rom` into page 1, checks that the only stock bytes it overwrites are
C-BIOS's unimplemented-call `unknown@` stubs (none reachable by a direct
`CALL`/`JP`), and emits both patch formats.

To run it in openMSX without touching any ROM, `make machines` installs ready
machine configs into your openMSX user dir — per C-BIOS MSX1 region
(intl/BR/EU/JP), a `*_BASIC` (zerobas + tape) and a `*_BASIC_DISK` (+ zerobas-disk
in slot 3-1):

```sh
make machines                      # -> C-BIOS_MSX1[_BR/_EU/_JP]_BASIC[_DISK]
openmsx -machine C-BIOS_MSX1_BASIC               # boots straight to the zb> prompt
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
for byte. (Decimal `≥ 32768` — which the reference stores as a float — plus
`&O`/`&B` and line-number references are out of scope for now; use `&H` for
16-bit values.)

0. **header** — `INITXT` brings up the text screen; `CHPUT` prints a couple of
   original left-aligned lines (the same role as MSX-BASIC's top-of-screen
   header before its prompt — no reference text copied)
1. **prompt + line editor** — print `zb>` (deliberately *not* `Ok`, so zerobas
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
   dispatching each on its leading token: `POKE`, a `<letter> = <expr>`
   assignment, `REM` (ends the line), `BLOAD`; an empty line reprompts and
   anything else prints `syntax error`
4. the **BLOAD handler** parses `"CAS:"` (device) and optional `,R`, then:
   - `TAPION` — open tape, skip the file-header tone
   - read + verify the 16-byte file header (binary id `$D0`)
   - `TAPION` — skip the data-block tone
   - read the 6-byte address header (start / end / exec, little-endian)
   - load the payload bytes verbatim into RAM
   - `TAPIOF`, then (for `,R`) `JP (exec)` — the handoff

This is the *interpreter half* of BLOAD. The *device half* (decoding the
cassette signal) is the BIOS's job, via `TAPION`/`TAPIN`.

### Limitations (this slice)

- **Stored programs + control flow (Step B).** Numbered lines are stored at the
  real text base (`TXTTAB`/`$F676` = `$8001`, oracle-confirmed) in the real
  line-link format, with insert / replace / delete by line number, plus `NEW`
  and `RUN`. The tokeniser knows the full control-flow keyword set
  (`GOTO`/`GOSUB`/`IF`/`THEN`/`ELSE`/`FOR`/`TO`/`STEP`/`NEXT`/`DATA`/`READ`/
  `RESTORE`/`END`/…, from MSX2 Technical Handbook Table 2.20) and emits the `$0E`
  line-number identification code (Figure 2.12) for branch targets, so a stored
  program is byte-identical to a real ROM's. The executor runs `GOTO`,
  `GOSUB`/`RETURN`, `FOR … TO … [STEP …] … NEXT [var]`,
  `IF … THEN … [ELSE …]` (line-number or statement clauses), and `END`/`STOP`
  via a redirectable run loop with a line resolver. `GOSUB`/`RETURN` and
  `FOR`/`NEXT` use control stacks and a *mid-line resume* path (RETURN comes
  back to the statement after `GOSUB`; a continuing `NEXT` re-enters the loop
  body), so subroutines and loops nest and span lines. Conditions use real
  comparison operators — `=` `<` `>` and the compound `<=` `>=` `<>` (signed
  16-bit, yielding `-1`/`0`). The `FOR` loop is bottom-tested (the body always
  runs at least once), matching the VG-8020 oracle. `DATA`/`READ`/`RESTORE` work
  too: `DATA` items are stored as verbatim ASCII (byte-identical to the
  reference — the oracle stores them as text, not number tokens), `READ` parses
  them at run time into variables across statements and lines, and
  `RESTORE [<line>]` rewinds the data cursor. **Still out:** `ON … GOTO` and
  `ELSE <line>` branch lists, and string DATA. See
  [`spec-controlflow.md`](https://github.com/andete/msx-preservation/blob/main/basic-spec/docs/spec-controlflow.md).
  Validated on openMSX by `basic_probe_controlflow.py`, `basic_probe_loops.py`,
  `basic_probe_data.py` (stored programs + branches + loops + data) and
  `basic_probe_crunch.py` (byte-identical tokenisation).
- Variables are single-letter integers (`A`–`Z`); no strings, arrays, or
  multi-character names. Expressions have `+ - *`, the comparisons
  `= < > <= >= <>`, and `PEEK` (no `/`, no string ops).
- **Crunch fidelity scope:** decimal integer constants `0`–`32767`, `&H` hex
  (`0`–`FFFF`), and `= + - *` are byte-identical. Decimal `≥ 32768` (a float on
  the reference), `&O`/`&B`, floating-point, and line-number-reference tokens are
  not yet emitted.

### Validation

Run the oracle probes ([`probes/`](probes)) against this ROM:

```sh
# BLOAD pipeline (tokenise → execute → cassette load → ,R handoff)
python3 probes/basic/basic_probe_bload.py \
    --machine Philips_VG_8020 --cart build/basic.rom

# REM / POKE / PEEK / expression evaluator (results read back from RAM)
python3 probes/basic/basic_probe_statements.py \
    --cart build/basic.rom

# Step A: byte-identical crunch — zerobas TOKBUF vs reference KBUF, per line
python3 probes/basic/basic_probe_crunch.py \
    --machine Philips_VG_8020 --cart build/basic.rom

# Step B: stored programs + control flow (GOTO / IF…THEN…ELSE / comparisons)
python3 probes/basic/basic_probe_controlflow.py \
    --cart build/basic.rom

# Step B: subroutines + loops (GOSUB/RETURN, FOR…NEXT incl. nesting)
python3 probes/basic/basic_probe_loops.py \
    --cart build/basic.rom

# Step B: DATA / READ / RESTORE (ASCII items parsed across lines)
python3 probes/basic/basic_probe_data.py \
    --cart build/basic.rom
```

The cartridge boots to its prompt, the probe types a line + Enter, and the
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
oracle-validated against a real National CF-3300. The verb surface is the
**Phase 2** charter raise on the disk axis (the core *language* stays loader-stub
scoped — floats, the full string engine, arrays, graphics and sound are Phase 3+).
See [`TODO.md`](TODO.md) for the per-verb status.

## Layout

```
zerobas/
├── README.md
├── PROVENANCE.md      # provenance index -> per-component logs below
├── Makefile           # `make` -> all deliverables; `make machines` -> openMSX configs
├── build/             # gitignored build artifacts (basic.rom, disk.rom)
├── build-patches.sh   # splice into a stock C-BIOS page 1 -> zerobas-msx1.ips/.bps
├── zerobas-msx1.ips   # slot-0 page-1 patch, IPS (universal; used by installer)
├── zerobas-msx1.bps   # slot-0 page-1 patch, BPS (CRC-locked, checksummed)
├── basic/
│   ├── main.asm       # cartridge header + includes + page padding ($00 fill)
│   ├── interp.asm     # tokeniser + statement-loop executor (INIT entry)
│   ├── title.asm      # startup header lines (INITXT + CHPUT)
│   ├── repl.asm       # keyboard line editor + read/eval loop (zb> prompt)
│   ├── vars.asm       # integer variable store (A..Z, 16-bit)
│   ├── expr.asm       # 16-bit integer expression evaluator (incl. PEEK)
│   ├── poke.asm       # the POKE statement handler
│   ├── bload.asm      # the BLOAD statement handler + ,R handoff
│   ├── sysvars.inc    # BIOS entry points + tokens + RAM scratch (all cited)
│   └── PROVENANCE.md  # BASIC-component provenance log
├── tape/
│   ├── tape.asm       # cassette BIOS patch (TAPION / TAPIN / TAPIOF)
│   ├── build-patches.sh        # assemble tape.asm -> zerobas-tape-msx1.ips/.bps
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
    └── install-openmsx-machine.py  # write *_BASIC machines that patch on load
```
