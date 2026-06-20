# Provenance log — index

Every constant, address, data table, and algorithm in this repo **must trace to
an allowed source**, or be explicitly **quarantined**. An unexplained magic
value blocks release. This file is the index; each component keeps its own log:

- [`basic/PROVENANCE.md`](basic/PROVENANCE.md) — the BASIC interpreter (tokeniser,
  REPL, statements, expression evaluator, `BLOAD"CAS:",R`).
- [`tape/PROVENANCE.md`](tape/PROVENANCE.md) — the cassette device half
  (`TAPION`/`TAPIN`/`TAPIOF`, waveform timing).
- [`disk/PROVENANCE.md`](disk/PROVENANCE.md) — the disk component (FDC, FAT).

## The two states

- **sourced** — traced to an allowed source (see [`README.md`](README.md) for the
  list) or to this project's own black-box **oracle observation**.
- **quarantined** — no copied source; derived from a documented format or spec
  and justified by oracle round-trip, or an original algorithm of ours. **Never**
  lifted from a reference ROM or any BIOS / MSX-BASIC / GW-BASIC disassembly.

The allowed-source list and the forbidden-source rule are stated once in
[`README.md`](README.md) and apply to every component log above.
