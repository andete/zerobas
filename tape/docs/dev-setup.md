# Dev setup: validating the cassette patch under openMSX

The cassette implementation and its patch build live **here** in this repo
(`tape.asm`, `make` → the `.ips`/`.bps`). The **validation harness** — the openMSX
probes — also lives here, in [`probes/`](../../probes)
(`probes/lib/omsx_run.py`, `probes/tape/bios_probe_tap*.py`); only the proprietary
oracle WAV captures stay local-only (never committed; see
[`PUBLISHING.md`](../../PUBLISHING.md)). The legal reasoning is in
[`feasibility.md`](feasibility.md) and [`clean-room-policy.md`](clean-room-policy.md).

## Where the build lives

`tape.asm` and the patch build are in this repo. To rebuild the patch:

```sh
make        # -> zerobas-tape-msx1.ips + .bps
```

`pasmo` assembles `tape.asm` to just the bytes the patch adds; **no C-BIOS is
compiled**. See [`../README.md`](../README.md) and [`../PROVENANCE.md`](../PROVENANCE.md).

## Boot in openMSX (patch applied on load)

**`C-BIOS_MSX1_EU_TAPE`** (tape only — `tools/install-openmsx-machine.py` in *this*
repo) or **`C-BIOS_MSX1_EU_BASIC`** (tape + zerobas BASIC — the same installer in
the [zerobas repo](https://github.com/andete/zerobas)) both apply this IPS on load.
For validating *just the tape layer* in isolation, `_TAPE` is cleaner; for end-to-end
`BLOAD"CAS:",R` testing, use `_BASIC`.

```sh
# sentinel smoke test (run from the repo root):
python3 probes/lib/probe_cart.py --out /tmp/sentinel.rom
python3 probes/lib/omsx_run.py --machine C-BIOS_MSX1_EU_TAPE --cart /tmp/sentinel.rom \
    --bp 0x7FF0 --reg PC --mem memory:0xE000:4 --out /tmp/cap.txt
# -> mem.memory:0xE000:4=4a4f4e47  ("JONG")
```

## The validate loop

1. **Edit** the routines in `tape.asm` (this repo).
2. **Build:** `make` (regenerates the IPS the machine loads).
3. **Test** with `--machine C-BIOS_MSX1_EU_TAPE`, using the probe harness in [`probes/`](../../probes):
   - *write path:* a `bios_probe_tap*.py` write cart + `omsx_run.py --record` →
     `probes/lib/cas_decode.py`, comparing the decoded bytes to the **VG-8020
     oracle** capture (must round-trip identically — see
     [`spec-cassette.md`](spec-cassette.md)).
   - *read path:* mount a known-good or recorded `.wav`/`.cas` and decode via
     `TAPION`+`TAPIN`. The full file round-trip is
     `probes/tape/bios_probe_tapfile.py` (`--write`/`--read`/`--analyze`).

The probes (`probes/tape/bios_probe_tap*.py`) and the shared openMSX harness
(`probes/lib/{omsx_run,probe_cart,z80probe,cas_decode}.py`) live here in this repo;
only the proprietary oracle WAV captures stay local-only.

## Clean-room reminder

The reference VG-8020 ROM is only ever a **black-box oracle**: identical inputs in,
observed bytes/edges out. Never read any reference BIOS disassembly. See
[`clean-room-policy.md`](clean-room-policy.md).
