# cassette-tool — MSX cassette-tape audio utilities

Host-side tools for working with **MSX cassette audio** (WAV captures of the FSK
signal). The first concrete need: stress-testing the [`zerobas-tape`](../README.md)
clean-room read path against impairments a real tape + audio chain introduce —
because everything proven there so far round-trips only against *synthetic*
signals (the clean, square, jitter-free output of its own write path under
openMSX), which proves the codec is self-consistent, not that it tolerates a real
tape.

## Tools

| Tool | Status | What it does |
|------|--------|--------------|
| [`degrade_wav.py`](degrade_wav.py) | ✅ | Apply parameterised, in-spec tape degradations to a cassette WAV (speed error, wow/flutter, low-pass edge rounding, DC bias / duty skew, gain, additive noise) |
| [`tolerance_sweep.py`](tolerance_sweep.py) | ✅ | Sweep one degradation parameter and report the decode pass/fail envelope, via a caller-supplied `--decode {wav}` command (decoupled from any specific decoder) |
| [`cas_identify.py`](cas_identify.py) | ✅ | Decode a WAV and report the MSX files in it (type marker, filename, binary load/exec addresses) — catalogues real captures and gives the byte-level reference for read-path checks |

Both are stdlib-only (no numpy/scipy), matching the rest of the repo's tooling.

> **Read-back harness.** Steps that *read a WAV back through the BIOS* —
> `omsx_run.py` and the `bios_probe_tap*.py` probes referenced below — live here in
> this repo, under [`probes/`](../../probes) (`probes/lib/` and `probes/tape/`),
> which drives openMSX headlessly. These host-side audio tools (and the vendored
> `cas_decode.py`) are self-contained here; the read-back step just points
> `--decode` at that harness.

## Workflow

1. Record a clean baseline WAV (e.g. with a zerobas-tape write probe under
   `omsx_run.py --record`).
2. Degrade it: `degrade_wav.py clean.wav out.wav --lowpass 4000 --noise 0.04`.
3. Read it back through the zerobas-tape read probes (`omsx_run.py --cassette out.wav`
   + `bios_probe_tap*.py --analyze`) and check it still round-trips.
4. Map a bound with `tolerance_sweep.py`, whose `--decode` runs step 3 on each
   degraded file.

## First tolerance envelope (zerobas-tape read path, 1200 baud)

Measured against the BSAVE two-block file round-trip
(`bios_probe_tapfile.py`). Indicative, not exhaustive:

| Impairment | Result |
|------------|--------|
| Low-pass (edge rounding) | **Very tolerant** — still decodes at a 1500 Hz cutoff. TAPIN is sign/zero-crossing based, so rounded edges still cross the midpoint. |
| Speed error (TAPION lock range) | **≈ −25% … +35%+**, asymmetric — a slow tape breaks before a fast one. The reader is otherwise baud-agnostic (TAPION re-measures the leader). |
| Additive noise | **Tight bound ≈ 0.05 of full scale.** The 1-bit comparator input has no hysteresis, so noise near each zero-crossing causes edge chatter → spurious half-periods → misframing. |

The noise result is the headline finding: the synthetic round-trips entirely hid
it. Whether to harden the reader (the input is 1-bit, so true hysteresis is a
hardware property the emulator models — not something TAPIN can add) or to treat
it as an input-conditioning requirement is an open question for zerobas-tape.

## Real captures (validated)

A set of genuine analog tape captures lives outside the repo in a local tape
directory (16-bit mono, mostly 43200 Hz — real capture-hardware
rate). `cas_identify.py` decodes them cleanly; all are **2400-baud** game tapes,
each an ASCII BASIC loader followed by a binary block:

| Game (`.wav`) | ASCII loader | binary | load / exec |
|---------------|--------------|--------|-------------|
| Hero | `hero` | `hero` | `0x8000` / `0xC351` |
| Beam Rider | `bride` | `beamr` | `0x8000` / `0xC101` |
| Hyper Sports | `load1` | `hyper1` | `0x8800` / `0xC800` |
| Road Fighter | `load1` | `roadf` | `0x8800` / `0xC802` |

### Full-corpus scan (what surfaced)

Running `cas_identify.py` across the whole local tape tree
(including manually-captured analog recordings) turned up useful structure and
three real tool limits:

- **Multi-block tapes decode end to end.** Some captures carry two binary blocks;
  one carries seven named blocks (`head0`…`head6`, including a doubled `head2`
  header). The continuous host decoder walks them all.
- **Baud/threshold auto-detection is not robust to outliers.** Several captures
  (Elevator Action, Zanac, Way of the Tiger, and others) report nonsense FSK
  frequencies (382 Hz … 13.5 kHz) and find
  no markers. Cause: `cas_decode.auto_threshold` splits on `(min+max)/2`, so one
  silence-gap or dropout outlier collapses the short/long split for the whole
  file. A per-region or percentile threshold would fix it — these are exactly the
  drift/dropout cases the synthetic signals never had.
- **Binary load/exec extraction is fragile.** `cas_identify` reads
  start/end/exec from the 6 bytes right after the filename, but on tape the data
  block follows the header across an inter-block leader; when that leader decodes
  to filler bytes (one capture shows `0xFFFF`-ish addresses) the field
  lands in the gap. The *names* are still correct; only the addresses need the
  decoder to locate the data block, not assume adjacency.

These are catalogued as known limits, not yet fixed — surfacing them was the
point of the scan.

**What real audio proved for the zerobas-tape read path:**
- The host decoder reads every capture perfectly (full Hero tape = ASCII BASIC
  loader + binary machine code, exact bytes).
- The BIOS reader (`TAPION`+`TAPIN`) reads **both blocks** of a real capture
  exactly at **2400 baud from genuine analog audio** — header (`EA`×10 + `"hero  "`)
  *and* the data block (`"10 COLOR15…"`), with `TAPION` re-locking mid-tape. Verified
  byte-for-byte against the host decoder on Hero, Beam Rider, Hyper Sports and
  Road Fighter.
- **Resolved (was open): mid-tape re-lock.** The second block originally returned
  garbage because the motor restart between blocks injects a spin-up transient (a
  flat patch + a stray ~100-count half + zero-crossing chatter) that a fixed
  "skip 8 / measure 16" `TAPION` either timed out on or averaged into the
  threshold. Synthetic tapes hid it (no real motor spin-up). The fix makes
  `TAPION` skip the transient and wait out flat patches while measuring the
  leader; see [`docs/spec-cassette.md`](../docs/spec-cassette.md).
  This is the headline case of a real-audio bug the synthetic round-trips could
  not surface.

## Still wanted

- **`.cas` ↔ WAV codec.** An independent host encoder/decoder of the MSX cassette
  format, to cross-check the zerobas-tape byte I/O (two implementations agreeing on
  the format is strong evidence neither copied the original).

## Relationship to `zerobas-tape/`

[`zerobas-tape`](../README.md) is the **on-MSX BIOS code** that reads and
writes the tape signal. This project is the **host-side audio tooling** that feeds
and checks it. They meet at the cassette WAV format but live on opposite sides of
the machine boundary.
