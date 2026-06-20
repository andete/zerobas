# Clean-room policy for the cassette BIOS reimplementation

The cassette routines (see [`feasibility.md`](feasibility.md)) are only
distributable — and only ever potentially upstreamable into C-BIOS — if their
provenance is clean. The risk here is **lower** than the BASIC project (there is no
Microsoft-BASIC lineage and the format is short and fully documented), but the
discipline is identical: reference BIOS ROMs and their public disassemblies exist
and could leak into the implementation through a human reader *or* an LLM context.
This document is the firewall. It extends the "oracle, not answer key" rule in
[`docs/openmsx-harness.md`](https://github.com/andete/msx-preservation/blob/main/docs/openmsx-harness.md) to the cassette
effort and mirrors [`basic-spec/docs/clean-room-policy.md`](https://github.com/andete/msx-preservation/blob/main/basic-spec/docs/clean-room-policy.md).

## Allowed sources

The implementation may be derived **only** from:

- MSX2 Technical Handbook (Konamiman's transcription) and the official ASCII chapters
  — cassette I/O chapter: baud rates, framing, leader, block layout, BIOS contracts.
- MSX Assembly Page (`map.grauw.nl`) — BIOS call list, sysvar map, i8255 PPI port and
  bit assignments.
- Hardware datasheets (Intel i8255 PPI; the cassette interface circuit description).
- C-BIOS sources (BSD 2-clause) for entry-point addresses, the existing `STMOTR`
  motor handling, hooks, and work-area addresses (`LOWLIM`, `WINWID`, `HEADER`,
  `BAUD`/`MINDEL`/`MAXDEL` timing sysvars, etc.).
- **This project's own black-box oracle observations** — bytes/edges in and out,
  captured in openMSX (with mounted tape media) or from a real machine, never the
  reference ROM's code.

## Forbidden sources

Never read, quote, paste, or feed into any tool or model:

- Any MSX BIOS disassembly or commented listing — including the cassette routines of
  any reference ROM (e.g. the Philips VG-8020 ROM used as the oracle).
- Any other vendor's cassette-routine source or decompilation.

The reference ROM and any reference tape are used **only** as black boxes: known
input in, observed bytes/edges out. A behavioural difference is a *bug report* to be
resolved from an allowed source — never by reading the original.

## Two-role split

Enforced even when one person (optionally with an LLM) does the work, by separating
the *phases* in time and keeping their inputs disjoint:

- **Spec author.** Observes the oracle (decoded bytes, captured `.cas`/`.wav` edges,
  PPI port states) and writes the behavioural spec citing only allowed sources. May
  look at oracle outputs; may **not** look at any original code.
- **Implementer.** Writes Z80 from the spec and the failing tests only. Never sees
  original or disassembled cassette code, and never sees the reference ROM's bytes.

## Provenance log

Every magic constant — baud-rate divisor, leader length, sync header bytes, PPI bit
masks, timing thresholds, work-area init values — carries an independent allowed
source, or it is **quarantined** (derived from spec/oracle, stubbed, or left
observable but uncopied — never lifted from the original). Record one row per item:

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| e.g. cassette sync header | `1F A6 DE BA CC 13 7D 74` | MSX2 Technical Handbook, cassette I/O chapter | sourced |
| e.g. PPI-C motor relay bit | bit 4 | MSX Assembly Page i8255 map + oracle (STMOTR probe) | sourced |
| e.g. a leader-length count | `??` | none found | quarantined |

`sourced` = traced to an allowed source or this project's own oracle observation.
`quarantined` = no allowed source; must be derived or stubbed, never copied. Anything
matchable *only* by looking at the original (exact timing-loop iteration counts, an
arbitrary delay constant) is quarantined by definition — and for timing values, a
quarantined constant is acceptable as long as the resulting **signal** round-trips
against the oracle, since the format (not the loop count) is the interface.

## LLM guardrail (if the hybrid method is chosen)

- Prompt and context may contain **only** allowed sources, the behavioural spec, and
  failing tests. Never paste disassembled or original cassette code into a model.
- Generate only from spec + failing tests.
- Reject any output containing a suspiciously specific timing constant or table until
  it is independently traced to an allowed source — or, for timing loops, justified
  from the documented baud rate and CPU clock and confirmed by oracle round-trip;
  otherwise quarantine it.

## Audit

Before any code is released — or offered upstream to C-BIOS — every constant and
table in the implementation must map to a `sourced` row in the provenance log or be
marked `quarantined` with a round-trip justification. An unexplained magic value
blocks release. The upstreaming decision (see
[`feasibility.md`](feasibility.md#keep-it-a-separate-or-upstreamable-component)) is
gated on a clean audit; until then nothing is folded into C-BIOS.
