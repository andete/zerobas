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
analysis repo (`msx-preservation`, under `basic-spec/docs/`), produced by
driving a real MSX in openMSX as a black box.

## Build

Requires [pasmo](https://pasmo.speccy.org/) (the assembler C-BIOS uses):

```sh
make            # -> basic.rom (16 KB cartridge)
```

## Two ways to run it: cartridge, or patched in next to the BIOS

`basic.rom` is an "AB" cartridge: drop it into any MSX slot and the BIOS finds
the header at `$4000` and calls INIT. That works, but it isn't where BASIC lives
on a real machine — there it sits in **slot 0 page 1 (`$4000-$7FFF`), right next
to the BIOS in page 0**, as one ROM. C-BIOS has no BASIC, so it leaves that page
almost empty — exactly the space zerobas is built for.

So zerobas can also ship as a **patch** that drops it into a stock C-BIOS main
ROM — the same delivery mechanism as the sibling [cbios-tape](https://github.com/andete/cbios-tape)
project, and the same legal firewall: C-BIOS and zerobas stay separate trees and
are combined only at apply-time. C-BIOS's cold-boot cartridge scan reaches its
own slot-0 page 1, finds zerobas's "AB" header, and calls INIT — so **no
boot-vector patch is needed**; the cartridge header does double duty.

```sh
make patches    # -> zerobas-msx1.ips + zerobas-msx1.bps (vs a stock C-BIOS main ROM)
```

`build-patches.sh` splices `basic.rom` into page 1, checks that the only stock
bytes it overwrites are C-BIOS's unimplemented-call `unknown@` stubs (none
reachable by a direct `CALL`/`JP`), and emits both patch formats. To use it in
openMSX without touching any ROM, the installer writes `*_BASIC` machines that
apply the IPS on load:

```sh
python3 tools/install-openmsx-machine.py   # -> C-BIOS_MSX1[_EU/_BR/_JP]_BASIC
openmsx -machine C-BIOS_MSX1_BASIC         # boots straight to the zb> prompt
```

(zerobas is MSX1 BASIC, so only the MSX1 C-BIOS variants are targeted. The BPS
is CRC-locked to one stock ROM and fails cleanly on a mismatch; the IPS is
universal and is what the installer uses.)

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
  `IF … THEN … [ELSE …]` (line-number or statement clauses), and `END`/`STOP`
  via a redirectable run loop with a line resolver. **Still out:** `FOR…NEXT`,
  `GOSUB`/`RETURN`, `DATA`/`READ` (need loop/return stacks + mid-line resume);
  and `IF` conditions are non-zero tests until comparison operators (`=`/`<`/`>`)
  land in the evaluator. See [`spec-controlflow.md`](https://github.com/andete/msx-preservation/blob/main/basic-spec/docs/spec-controlflow.md).
  Assemble-verified; an oracle probe for stored-program + branch bytes is the
  next validation step.
- Variables are single-letter integers (`A`–`Z`); no strings, arrays, or
  multi-character names. Expressions have `+ - *` and `PEEK` only (no `/`,
  comparisons, or string ops).
- **Crunch fidelity scope:** decimal integer constants `0`–`32767`, `&H` hex
  (`0`–`FFFF`), and `= + - *` are byte-identical. Decimal `≥ 32768` (a float on
  the reference), `&O`/`&B`, floating-point, and line-number-reference tokens are
  not yet emitted.

### Validation

Run the oracle probes (in the `msx-preservation` repo) against this ROM:

```sh
# BLOAD pipeline (tokenise → execute → cassette load → ,R handoff)
python3 basic-spec/tools/basic_probe_bload.py \
    --machine Philips_VG_8020 --cart /path/to/zerobas/basic.rom

# REM / POKE / PEEK / expression evaluator (results read back from RAM)
python3 basic-spec/tools/basic_probe_statements.py \
    --cart /path/to/zerobas/basic.rom

# Step A: byte-identical crunch — zerobas TOKBUF vs reference KBUF, per line
python3 basic-spec/tools/basic_probe_crunch.py \
    --machine Philips_VG_8020 --cart /path/to/zerobas/basic.rom
```

The cartridge boots to its prompt, the probe types a line + Enter, and the
result is observed by dumping RAM (no PRINT). Expected: `ALL PASS` for the
statements probe, and `PASS marker JONG at 0xE000` / `PASS PC at landmark` for
BLOAD — byte-for-byte identical to the reference MSX-BASIC's own behaviour.

### Note on C-BIOS

C-BIOS's *own* cassette routines (`TAPION`/`TAPIN`/`TAPIOF`) are **stubs that
always fail** — so on bare C-BIOS a cassette `BLOAD` cannot complete (the ROM
reaches `BLOAD`, calls `TAPION`, gets a failure, and takes its error path,
observable as the byte `$EE` at `$E010`). The sibling
[cbios-tape](https://github.com/andete/cbios-tape) patch supplies real
`TAPION`/`TAPIN`/`TAPIOF` in page 0, and the zerobas machine installer
([tools/install-openmsx-machine.py](tools/install-openmsx-machine.py)) applies
**both** IPS patches — cbios-tape (page 0) then zerobas (page 1) — so the full
cassette `BLOAD` pipeline now completes end-to-end: C-BIOS + cbios-tape (device
half) + zerobas (interpreter half).

The next transport is **disk**, where a disk-interface ROM provides the device
half (`PHYDIO` / the `H.*` hooks) — a future transport here.

## Layout

```
zerobas/
├── README.md
├── PROVENANCE.md      # provenance log (sourced / quarantined)
├── Makefile           # pasmo -> basic.rom (16 KB); `make patches` -> .ips/.bps
├── build-patches.sh   # splice into a stock C-BIOS page 1 -> zerobas-msx1.ips/.bps
├── zerobas-msx1.ips   # slot-0 page-1 patch, IPS (universal; used by installer)
├── zerobas-msx1.bps   # slot-0 page-1 patch, BPS (CRC-locked, checksummed)
├── src/
│   ├── main.asm       # cartridge header + includes + page padding ($00 fill)
│   ├── interp.asm     # tokeniser + statement-loop executor (INIT entry)
│   ├── title.asm      # startup header lines (INITXT + CHPUT)
│   ├── repl.asm       # keyboard line editor + read/eval loop (zb> prompt)
│   ├── vars.asm       # integer variable store (A..Z, 16-bit)
│   ├── expr.asm       # 16-bit integer expression evaluator (incl. PEEK)
│   ├── poke.asm       # the POKE statement handler
│   ├── bload.asm      # the BLOAD statement handler + ,R handoff
│   └── sysvars.inc    # BIOS entry points + tokens + RAM scratch (all cited)
└── tools/
    ├── pad_rom.py     # pad/verify the ROM to exactly 16 KB
    ├── rom_patch.py   # make/apply/inspect IPS + BPS patches (shared w/ cbios-tape)
    ├── overlay_page1.py        # splice zerobas into C-BIOS page 1 + vet the splice
    └── install-openmsx-machine.py  # write *_BASIC machines that patch on load
```
