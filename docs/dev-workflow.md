# zerobas dev workflow

How to add a feature to the interpreter and prove it correct. This is the
procedural companion to [`PROVENANCE.md`](../PROVENANCE.md) (the *what is
allowed* rules) and [`TODO.md`](../TODO.md) (the *what is left* list).

It exists so a fresh session can ramp fast: the per-feature knowledge below was
learned the hard way and is **not** otherwise recoverable from the code.

## Per-feature checklist

Each TODO item is largely independent — do one per session, and finish with:

1. **Read the anchors first, in order:** `README.md`, `PROVENANCE.md`,
   `TODO.md`, `basic/sysvars.inc`, then the source files the feature touches
   (`basic/interp.asm` for tokeniser/dispatch, `basic/expr.asm` for expression
   factors, `basic/program.asm` for stored-line handling).
2. **Honour the clean-room rule.** Every new constant / token byte / address /
   algorithm must trace to an allowed source, cited inline at its definition.
   Allowed: MSX2 Technical Handbook, MSX Assembly Page (`map.grauw.nl`), a
   public MSX-BASIC *language* reference, hardware datasheets, C-BIOS sources,
   or this project's own black-box oracle observations. **Forbidden:** any
   MSX-BASIC / GW-BASIC / BASIC-80 source or disassembly, and any reference
   BIOS / BASIC ROM disassembly. A reference ROM is only ever an oracle:
   identical inputs in, observed outputs out.
3. **Quarantine own-design.** If correct MSX behaviour needs a forbidden source
   to reproduce, ship a documented simplification instead and mark it
   `quarantined` in `PROVENANCE.md` (e.g. the USR integer-only convention,
   unsigned `/`, div-by-zero → 0).
4. **Build clean:** `make` must emit a 16384-byte `build/basic.rom` with no warnings.
5. **Prove crunch is still byte-identical** (see below) — any tokeniser change
   can regress this.
6. **Run the regression probes** (control flow / loops / data / statements) —
   confirm no existing behaviour broke.
7. **Functional-test the new feature** in openMSX (see harness recipes).
8. **Update `TODO.md`** (check the item, note divergences) and append a
   `PROVENANCE.md` row. Do **not** commit unless asked.

## Build

```sh
make            # all portable deliverables: build/basic.rom + build/disk.rom +
                #   zerobas-msx1.ips/.bps + tape/zerobas-tape-msx1.ips/.bps
make disk       # just build/disk.rom
make patches    # just the zerobas page-1 .ips/.bps
make machines   # install openMSX configs into ~/.openMSX (separate: see below)
make install    # make + make machines
```

Build artifacts (the ROMs) land in the gitignored `build/` dir, never the repo
root — so a stale copy can't linger where a probe or installer would pick it up.
The tracked `zerobas-msx1.ips/.bps` deliverables stay at the root. The patch
targets need a stock C-BIOS ROM (auto-detected from openMSX, or `STOCK=<path>`).

The openMSX machine configs are a separate `make machines` target, not part of
`make`: they embed absolute paths to your openMSX ROMs + this repo, so they're an
install regenerated per environment, not a portable artifact. `make machines`
writes, per C-BIOS MSX1 region, a `*_BASIC` and a `*_BASIC_DISK`; the
`*_ZEROBASDISK` provider-oracle is a test machine (`make machines-oracle`), not a
release config.

Assembler is pasmo. A linter hook auto-adds SPDX / copyright headers to new
source files — don't hand-write them.

## The validation harness (lives in the msx-preservation repo)

All emulator tooling is in the sibling repo, not here:

```
../msx-preservation/                     # sibling checkout
  tools/omsx_run.py                      # headless openMSX driver
  basic-spec/tools/basic_probe_*.py      # differential + functional probes
  basic-spec/tools/cas_encode.py         # build_cas() — make a .cas payload
```

### Byte-identical crunch probe (run after ANY tokeniser change)

```sh
cd ../msx-preservation
python3 basic-spec/tools/basic_probe_crunch.py --cart ../zerobas/build/basic.rom
# want: "ALL PASS — crunch is byte-identical"
```

It feeds the identical line to a real **Philips VG-8020** (reference) and to
zerobas, breaks both at `TAPION ($00E1)` mid-`BLOAD"CAS:",R` (so the whole line
is already crunched), and compares the reference `KBUF ($F41F)` against zerobas
`TOKBUF ($E160)` byte for byte. To exercise a new keyword/operator, add the test
line to `LINES` (executable; `bload` trails) or `CRUNCH_ONLY` (non-executing
body; `bload` leads) — **then restore the probe to pristine before finishing**;
those test-line edits are scratch, never committed.

Other regression probes (same invocation shape, `--cart …/build/basic.rom`):
`basic_probe_controlflow.py`, `basic_probe_loops.py`, `basic_probe_data.py`,
`basic_probe_statements.py`.

### omsx_run.py — the headless driver

```sh
python3 tools/omsx_run.py --machine C-BIOS_MSX1 --cart build/basic.rom \
    --type 'PRINT 12*12\r' --type-delay 8 \
    --bp 0x7FF0 --reg PC --mem memory:0xE000:4 --out cap.txt
```

Hard-won determinism rules:

- **Sync on an event, never on time.** Use `--bp ADDR` (a "done" landmark the
  test cartridge / line jumps to). Real-BIOS machines boot slower than C-BIOS,
  so `--time` is a last-resort fallback only.
- **`--type-delay` is ABSOLUTE emulated seconds**, paired by position with each
  `--type`. The capture window must outlast the last keystroke: if you type at
  t=8 and t=12, a `--time 6` capture fires *before* the keys and grabs nothing.
- **zerobas REPL drops a trailing CR** in the same burst under `throttle off` —
  inject Enter as a *separate*, later `--type "\r"` event (see how the crunch
  probe sets `separate_enter=True`).
- **`CHPUT ($00A2)` / `CHGET ($009F)` guarantee no registers** — guard every
  register across a call to them.
- **One feature per run.** A long chained test line can error before reaching
  the breakpoint, leaving no capture file (a `FileNotFoundError`); test
  operators / statements one per run.

### Capture techniques

- **BLOAD-landmark freeze:** point a `.cas` payload at a `jr $` self-loop
  (`bytes([0x18,0xFE])`) loaded somewhere you control, break at the loop, and
  read RAM — freezes interpreter state after the line has fully executed.
  `build_cas("TOK", load, run, payload)` builds the tape.
- **PRINT / screen output:** dump the SCREEN 0 name table from VRAM with
  `--mem VRAM:0x0000:N` and decode the MSX character codes.

## Tokeniser quirks (the expensive lessons)

These govern `basic/interp.asm`'s `tokenise:` / `tk_loop:` and **must** be
preserved or the crunch probe regresses:

- **Keywords match at EVERY position mid-identifier**, exactly like MS-BASIC.
  `SCORE` crunches as `SC` + `OR` (`$F7`) + `E`, *not* as a single name. Do not
  try to consume a maximal identifier — emit char by char and let each position
  attempt a keyword match.
- **Digits stay verbatim only when already inside a name.** That is the entire
  job of the `TKNAME` in-name flag (`$E028`): a letter sets it; at each loop top
  it is read into `B` then cleared; a digit copies verbatim iff `B` says we were
  mid-name, otherwise it begins a number literal. `a1`, `x2`, `ab9` round-trip
  byte-identically because of this.
- **`OFF` has its own token `$EB`** (oracle-observed via `KEY OFF`).
- Token bytes come from MSX2 TH Table 2.20; line-number identification codes
  from Figure 2.12. New tokens go in `basic/sysvars.inc` with a cited source and
  in `kwtable` (layout: `[klen][UPPERCASE chars][tlen][token…]`, 0-terminated).

## Layout cheat-sheet

- **Expression precedence ladder** (`basic/expr.asm`, lowest binds last):
  `eval → ev_xor → ev_or → ev_and → ev_not → ev_rel → ev_e (+ -) →
  ev_mod → ev_idiv (\) → ev_t (* /) → ev_f`. Factors live in `ev_f`; add a new
  function/literal there. Cursor in `IX`, value out in `DE`; `eval` bridges
  `HL ↔ IX`.
- **Variables** (`basic/vars.asm`): 2-significant-char keys, 4-byte entries
  `[name0][name1][value:2]` at `VARTAB ($E1C0)`. Use `var_name_key` (HL→BC key)
  + `var_get_key` / `var_set_key`. Single-letter shims keep FOR/NEXT/READ
  working.
- **Statement dispatch** is by token in `basic/interp.asm`; one source file per
  verb (`basic/clear.asm`, `basic/usr.asm`, `basic/print.asm`, …) added to both
  `basic/main.asm` (include) and the `Makefile` `DEPS`.
