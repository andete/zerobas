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
| `lib/`   | shared infrastructure — `omsx_run.py` (headless openMSX state capture; the `--bp`-landmark trigger path), `omsx_repl.py` (typing-free KEYBUF-injection REPL driver — see below), `z80probe.py` (Z80 cartridge builder), `probe_cart.py` (sentinel-cart generator), `cas_encode.py` / `cas_decode.py` (cassette codecs) |
| `basic/` | `basic_probe_*.py` — zerobas-BASIC vs a reference MSX-BASIC ROM (Philips VG-8020) |
| `disk/`  | `disk_probe_*.py`, `diskbasic_probe_*.py` — zerobas-disk vs a reference disk ROM (National CF-3300) and real MSX-DOS 1 |
| `tape/`  | `bios_probe_*.py` — the cbios-tape cassette read/write path (TAPION/TAPIN/TAPOON/TAPOUT…) on patched C-BIOS |

Each probe is self-contained: it locates `lib/` and its sibling probes relative
to its own path, so it runs from anywhere with no `PYTHONPATH` set-up.

## Prerequisites

1. **openMSX** on your `PATH` (or `$OPENMSX`, or `--omsx <path>`).
2. **Build artifacts** — `make all` (produces `build/disk.rom`, `build/sub.rom`)
   and `make test-dsk` (produces `disk/test720.dsk`, a reproducible FAT12 image).
3. **openMSX machines** — `make machines-oracle` installs the zerobas machines
   (`C-BIOS_MSX1_EU_BASIC`, `…_BASIC_DISK`, and a region-universal `…_TAPE`) plus the
   CF-3300 provider oracle. (`make machines` omits the oracle test machine.)
   The acceptance gates use `C-BIOS_MSX1_EU_REPACK_DISK` from `make repack-machine`.
4. **Reference ROMs — you supply them.** The differential probes compare against
   proprietary reference machines (`Philips_VG_8020`, `National_CF-3300`) and, for
   the BDOS probes, a real MSX-DOS 1 disk. These ROMs/disks are **never shipped
   here** (see [PUBLISHING.md](../PUBLISHING.md)); install your own legally-obtained
   copies into openMSX. Tape corpora (`.cas` / `.wav`) are likewise yours to
   supply via `--corpus` / `$MSX_TAPE_CORPUS` and `--wav-dir` / `$MSX_TAPE_WAVS`.

## Headless conventions — ⚠️ every launch site must set BOTH

An openMSX launched from `probes/` runs headless, and that takes **two** settings,
not one:

```tcl
set renderer none          ; # no video output
set sound_driver null      ; # no HOST AUDIO DEVICE  <- easy to forget
```

`sound_driver` defaults to `sdl`, so a probe that sets only `renderer none`
**opens a real CoreAudio device and actively streams** PSG/keyclick output that
nothing ever reads — hundreds of start/stop cycles per gate run, audible on the
dev machine, and a candidate cause of the wedged-audio hang that presents as an
intermittent probe timeout. ⚠️ **NOT `mute` / `master_volume 0`** — those silence
the output and leave the driver churning.

**No probe in this tree needs a host sound driver.** PSG work
(`lib/psgtrace.py`, the `sound`/`play`/`beep` gates) reads the *emulated chip*
through `debug read_block {PSG regs}`, and cassette recording (`--record`,
`cassetteplayer new`) writes the *emulated cassette port* — **measured**: the
same `CSAVE` produces a byte-identical 128224-byte wav under `null` and under
`sdl`, decoding to the same tape bytes.

The setting reached only `disk/omsx_session.py` when it was introduced
(2026-07-30), leaving the other 69 launch sites — including `lib/omsx_repl.py`,
which every BASIC acceptance gate boots through — still streaming. Fixed across
all 70 on 2026-07-31. *(Ask at WHICH LAYER a lesson already applies.)*

## Running

```sh
# headline differential oracles
python3 probes/disk/disk_probe_dskio.py  --dsk disk/test720.dsk      # DSKIO == CF-3300
python3 probes/basic/basic_probe_print.py \
        --zb-machine C-BIOS_MSX1_EU_REPACK_DISK                      # PRINT == VG-8020
python3 probes/tape/bios_probe_tapwrite.py --out /tmp/tapwrite.rom    # build a cassette-write cart

# end-to-end BDOS $05 LSTOUT on the C-BIOS target (through the tape LPTOUT $00A5)
python3 probes/disk/disk_probe_lstout_cbios.py                       # prints "LP!" via a logger

# every probe takes --help
python3 probes/disk/disk_probe_bdos.py --help
```

### Driving the REPL — `lib/omsx_repl.py`

A probe that types BASIC at the `Ok`/`ZB` prompt and scrapes the result from
VRAM should deliver its lines through **`omsx_repl.run_case(machine, mode,
lines)`**, NOT openMSX `type`. `type` drives the keyboard *matrix* on a fixed
emulated-time schedule, which is timing-fragile (a leading key can double, an
Enter can be swallowed mid-type). `omsx_repl` instead injects each line into the
BIOS type-ahead buffer (`KEYBUF $FBF0` + `GETPNT`/`PUTPNT`, published MSX2-TH
contract, no disasm) so the ROM tokenises it with no matrix scan — deterministic.

- `run_case(machine, "direct", [line])` — one direct-mode REPL line. A line past
  the 40-byte KEYBUF cap is chunked transparently (no length limit up to ~255).
- `run_case(machine, "stored", body_lines)` — run a program: the body statements
  are numbered `10`/`20`/… and `RUN`; use `as_stored(":"-joined line)` to split.
- `result_span` / `screen_tail` / `result_span_after_echo` — the reusable
  `[…]`-bracket value + error-tail extractors (machine-agnostic re `Ok` vs `ZB`;
  the prompt strings live in one place, `omsx_repl.PROMPTS`).

**Batched delivery is now the default for a whole matrix** (since `5cde8a8` fixed
`NEW`/`CLEAR` to reset variables + DEFtbl on the repack build — `omsx_repl.py
--selftest <machine>` reports `batching AVAILABLE`). A gate that boots openMSX
once per case pays the ~0.4 s boot ×N; batching amortises it to one boot for the
whole matrix (~20× on the float gate). Two entry points build the pattern:

- `run_cases(machine, specs, *, batch=True, reset=("CLS",))` — deliver a list of
  `(mode, lines)` in ONE boot, `reset` injected before each case. Pick the reset
  per matrix: `("CLS",)` when no case assigns a variable (screen-clean suffices);
  `("NEW","CLS")` when cases set typed vars / DEF defaults that must not leak.
  `batch=False` restores boot-per-case (power-on-fresh, `reset` ignored).
- `run_differential(ref, zb, specs, compare, *, isolate=…)` — the differential
  driver: delivers to both machines batched, judges each case with `compare`, and
  **self-heals** — any disagreeing case is re-run boot-per-case (authoritative),
  so results equal a full boot-per-case run while clean cases keep batch speed.
  This tames batching's one hazard: a case that *wedges* the interpreter (a
  tokeniser-derail literal like `1e10#` spins the machine so no `reset` recovers
  it, poisoning every follower in that shared boot). Declare known wedgers in
  `isolate` to keep them out of the batch; the self-heal catches undeclared ones.
- `--boot-per-case` on each converted probe forces `batch=False` end-to-end — the
  isolation escape hatch when a batched case looks wrong.

The `basic_probe_float_{fmt,arith,vars}` probes use `run_differential`; copy them
as the template. `floatlit` and other breakpoint-synced probes (`--bp`, e.g. the
crunch/tokenise probes) are not flaky, use `omsx_run.py`, and stay boot-per-case
(they freeze the CPU at a landmark, so they can't share a boot — see
`docs/spec-acceptance-batching.md` for the plan to batch them).

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
