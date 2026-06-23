# Tape regression suite (cbios-tape read/write path)

A regression net for the full open cassette stack — **zerobas** (clean-room
BASIC) + **stock C-BIOS** + the **cbios-tape** IPS — driven headlessly through
openMSX (see [`openmsx-harness.md`](../../docs/openmsx-harness.md)). It exists to guard the
3744-baud read-margin fix and the 1200/2400 paths against regression, and to
cross-validate the read path against real-world tapes.

Everything observes the BIOS as a black box (public entry points
`TAPION`/`TAPIN`/`TAPOON`/`TAPOUT`); decoding tape *data* is not reading any
reference BIOS/BASIC ROM, so it stays clean-room.

## The tiers

| Tier | Runner | Input | Oracle | Pass/fail? |
|------|--------|-------|--------|------------|
| 1 — deterministic | `make test` in `tape/` | self-authored, generated from code | exact expected bytes | yes (committed, reproducible) |
| 2 — `.cas` corpus | `probes/tape/bios_probe_realtape.py --corpus` | real game `.cas` (local) | the `.cas` container itself | yes (reliable) |
| 3 — analog `.wav` | `probes/tape/bios_probe_realtape.py --wav-dir` | real cassette recordings (local) | `cas_decode.py` / `--expect-header` | characterization |

### Tier 1 — deterministic (committed)

```sh
# in tape/ (builds patches then runs tests):
make test

# or directly, from the repo root:
python3 tape/tools/run_tape_regression.py
```

Six checks, all from this project's own content (no copyrighted ROMs, no game
tapes):

1. **`.cas` BLOAD @3744** on `C-BIOS_MSX1_EU_BASIC` (stock C-BIOS + cbios-tape
   IPS + zerobas IPS, no cart) — the rolled-together shipping target BLOADs a
   `.cas` end to end, incl. the `,R` handoff. This is the path the 3744 margin
   fix unblocked.
2. **`.cas` readback @3744** on `C-BIOS_MSX1_EU_TAPE` — a generated `.cas`
   container is synthesised by openMSX at 3744 baud, then read byte-for-byte via
   `TAPION`/`TAPIN`. Isolates the tape signal layer at 3744 baud from the full
   BLOAD/BASIC stack.
3. **Write → read round-trip @1200 and @2400** on `C-BIOS_MSX1_EU_TAPE` — a write
   cart lays a two-block BSAVE file, openMSX records it to a WAV, a read cart
   reads it back; bytes must match. Guards the slow bauds.
4. **Open-stack WAV BLOAD @1200 and @2400** — zerobas BLOADs a tape written by
   the cbios-tape write path and runs it.

Prerequisites are local setup, not committed: the `C-BIOS_MSX1_EU_BASIC` and
`C-BIOS_MSX1_EU_TAPE` machines (install via zerobas/cbios-tape's
`install-openmsx-machine.py`) and a built `zerobas/basic.rom`
(`--zerobas PATH`, or `--skip-openstack`).

### Tier 2 — real `.cas` corpus (local, reliable)

```sh
python3 probes/tape/bios_probe_realtape.py --corpus <your-cas-corpus> --limit 12
# or: export MSX_TAPE_CORPUS=...; python3 probes/tape/bios_probe_realtape.py
```

openMSX renders each `.cas` at 3744 baud; the read cart locks the first block,
re-locks, and reads into the next block. Ground truth is the `.cas` **container
itself** (split on the 8-byte sync marker `1F A6 DE BA CC 13 7D 74`), so this is
exact. A run passes when both leader locks succeed and the read bytes are a
contiguous subsequence of the container bytes.

This is the **high-value reliable tier** — broad coverage on real, varied game
data at the exact baud we fixed. The corpus is copyrighted game images and is
**never committed**; point at a local copy.

### Tier 3 — analog `.wav` (local, characterization)

```sh
python3 probes/tape/bios_probe_realtape.py --wav-dir <your-wav-dir> \
    --wav <your-wav> --expect-header hero \
    --wav <your-wav> --expect-header bride
```

Real cassette recordings. The oracle here is `cas_decode.py` (our own edge
decoder), which is **only trustworthy on standard 1200/2400 FSK** — it mis-clusters
turbo / non-2:1 encodings. So this tier is **characterization, not pass/fail**: it
prints what cbios-tape read vs what the oracle read, asserting only when they
agree or against an explicit `--expect-header` string (the human-readable file
name in the header block). It does not affect the suite exit code.

## Why `.cas` and analog `.wav` are different worlds

A **`.cas` file is a container of standard MSX FSK blocks** — each logical block
is stored as bytes, and openMSX synthesises a standard leader + Kansas-City FSK
for it at a fixed 3744 baud. The format *cannot represent* a custom/turbo
encoding: there is nowhere to put non-standard timing. So **every `.cas`, even of
a game that used a custom loader on its original tape, is BIOS-readable block by
block.** (The game's loader still issues ordinary `TAPIN` calls; it just manages
the blocks with its own naming — see Elite below.)

A genuine **custom or turbo loader only survives in an analog recording** (`.wav`).
There, the bulk of the tape may be at a faster baud or a non-standard framing the
BIOS read path is not meant to decode. cbios-tape can read the standard
header/bootstrap at the front; the turbo bulk is **out of scope** for a
BIOS-format read path (it's the game's own routine's job).

### Worked examples

- **Elite** (`.cas`): 12 standard-framed blocks — a `D0`
  "elite" header + binary bootstrap, then the loader's own named chunks
  (`TITLE DAT`, `CODE COMM`, `MATRIX DAT`, `SHAPES DAT`, `COCKPIT DAT`). cbios-tape
  reads block 0, consumes the full 1824-byte block 1, and **re-locks cleanly on
  block 2** ("TITLE DAT") at 3744 — the whole multi-block game is BIOS-readable
  from `.cas`.
- **Zanac** (analog `.wav`): a ~4000-baud **turbo** analog tape (FSK
  ratio ≈ 2.2, high frequencies). `cas_decode` returns garbage (its auto-threshold
  breaks), but cbios-tape's hardware-faithful auto-baud reads the header
  `D0×10 "Zanac "` correctly — hence `--expect-header Zanac` passes where the
  oracle can't. A good custom-loader **boundary** case.
- **Elevator Action** (analog `.wav`): FSK ratio ≈ 3.43 — a non-standard
  encoding. cbios-tape still reads the standard `D0×10 "Elevat"` header; the
  body is out of scope.
- **A truncated Hero clip** (`.wav`): a deliberately truncated capture (anomalous
  ratio 3.22). Its data block misreads — expected, it's a degraded test stub, not
  a bug. The full Hero capture reads fine.

## Clean-room / copyright

No game tapes or copyrighted ROMs are committed. Tiers 2–3 read a **local** copy
of the corpus via `--corpus` / `$MSX_TAPE_CORPUS` and `--wav-dir` /
`$MSX_TAPE_WAVS`. Reading tape *data* through the BIOS is black-box observation;
it is not reading reference BIOS/BASIC ROM code.
