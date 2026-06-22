# tape — zerobas-tape cassette patch

**Makes cassette loading and saving work in openMSX's free C-BIOS.**

[C-BIOS](https://github.com/cbios/cbios) has no tape support — `BLOAD"CAS:"`,
`CLOAD`, and `CSAVE` all hang or do nothing. This component supplies real
`TAPION`/`TAPIN`/`TAPIOF` routines in a spare region of page 0, validated
at both 1200 and 2400 baud on MSX1, MSX2, and MSX2+.

The cassette patch and the zerobas BASIC ROM are applied together by the
repo-level installer:

```sh
# from the zerobas repo root — applies both patches, creates *_BASIC machines
python3 tools/install-openmsx-machine.py
openmsx -machine C-BIOS_MSX1_EU_BASIC
```

## Building the patch

```sh
make -C tape    # -> tape/zerobas-tape-msx1.ips + tape/zerobas-tape-msx1.bps
```

Requires [pasmo](https://pasmo.speccy.org/). The pre-built patches are already
committed and what the installer uses; rebuild only if you change `tape.asm`.

## More information

- **[docs/tape-internals.md](docs/tape-internals.md)** — how MSX cassette I/O
  actually works (hardware lines, FSK, the seven routines, the oracle method),
  synthesised from the whole effort; start here to *understand* tape
- **[DESIGN.md](DESIGN.md)** — what the patch does and how it's built
- **[PROVENANCE.md](PROVENANCE.md)** — every constant traced to an allowed source
- **[docs/spec-cassette.md](docs/spec-cassette.md)** — full behavioural spec of the
  seven entry points, derived by black-box oracle observation
- **[cassette-tool/](cassette-tool/README.md)** — host-side WAV/CAS analysis tools
  for stress-testing and cataloguing real tape captures
