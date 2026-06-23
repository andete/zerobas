# zerobas — mission

zerobas exists to do two things, and treats them as **equally important**. This
document is the charter; [`README.md`](README.md) is the entry point,
[`PROVENANCE.md`](PROVENANCE.md) the traceability rules, [`TODO.md`](TODO.md) the
roadmap, and [`docs/allowed-sources.md`](docs/allowed-sources.md) the rated source
catalogue that the discipline below depends on.

## Two co-equal goals

1. **Clean-room implementations.** Reimplement MSX1 system software — the BASIC
   interpreter, the cassette layer, the disk interface — from *published interfaces*
   and this project's own *black-box observation* of real machines alone, **never**
   from disassembly of the original ROMs. The result is freely distributable
   precisely because nothing protected went into it.

2. **Clean-provenance documentation.** In doing the first, produce documentation of
   **how these systems actually work** — and where good documentation does not yet
   exist, **producing it is a first-class goal, not a byproduct**.

Most projects would call the second a side effect. zerobas calls it a deliverable.

## Why the two are one discipline

The firewall that keeps the *code* distributable is exactly what makes the
*documentation* publishable. Datasheet- and oracle-derived facts have clean
provenance, so the artefacts the work throws off — the [`PROVENANCE.md`](PROVENANCE.md)
logs, the differential oracle probes, the behavioural specs
([`tape/docs/spec-cassette.md`](tape/docs/spec-cassette.md)), the characterisation
notes ([`disk/docs/provider-oracle-scope.md`](disk/docs/provider-oracle-scope.md)),
the rated catalogue ([`docs/allowed-sources.md`](docs/allowed-sources.md)), the host
unit-test harness — are themselves safe for the community to build on. Naming
documentation as a goal doesn't add a competing aim; it names the **second yield of
the same work**.

The governing rule that protects both is stated once, in the README: *documentation
may be used only where it specifies a published / standard interface the original was
built to conform to — never where it reveals a reference implementation's internals.*

## Aiming the documentation: value scales inversely with what exists

A useful lens for where the documentation effort is most worth spending:

- **An official datasheet exists** (Z80, V9938, V9990) → our value is *worked,
  validated integration*: how the parts actually behave together on real MSX, edge
  cases, confirmed quirks.
- **Only reverse-engineered compilations exist** → we can produce a
  *cleaner-provenance* reference, derived from allowed sources and the oracle rather
  than from someone else's disassembly.
- **Nothing exists** (e.g. the Konami SCC / SCC+, which has no manufacturer
  datasheet) → a careful black-box characterisation **produces the primary reference
  outright**. Highest value, precisely because the shelf is empty.

## Source, not sink

Everywhere else, zerobas is *downstream* of documentation: it consumes a datasheet or
oracles a ROM, and the discipline is about not laundering protected work. The empty-shelf
case inverts that. Where no datasheet exists, a clean-room characterisation **produces
primary documentation that doesn't currently exist** — for once zerobas is *upstream*,
a **source, not a sink**. The result (a register + waveform reference, method and
reproducible raw captures — the probe corpus *is* the document) is an A-grade,
clean-provenance artefact and a standalone gift to MSX preservation, valuable
**independently of whether the corresponding code ever ships**.

## Even the walls are deliverables

Not every interface can be reached from an allowed source. The MSX-DOS 1 in-ROM kernel
(`$4030`) cannot be cloned without disassembling proprietary code, so the DOS-boot is
walled (see [`disk/docs/provider-oracle-scope.md`](disk/docs/provider-oracle-scope.md)).
But a **precisely characterised clean-room boundary** — *where*, and *why*, an interface
cannot be cloned from any allowed source — is preservation knowledge in its own right. A
cleanly documented negative result is still a contribution.

## Scope and boundaries

- **MSX1 today.** Three components mirror the hardware they replace: `basic/` (a 16 KB
  cartridge ROM), `tape/` (a C-BIOS cassette patch), `disk/` (a disk-interface ROM).
- **BASIC is game-loader-scoped** — *just enough* MSX-BASIC to run the `.BAS` / binary
  loader stubs that boot many disk and tape games, not full-language compatibility —
  while cassette and disk are **device-complete** (read and write).
- **The firewall is load-bearing, not aspirational.** Every constant, address, table,
  and algorithm must trace to an allowed source or be explicitly quarantined; an
  unexplained magic value blocks release. This is what makes *both* deliverables real.
  Contributions are held to it by [`CONTRIBUTING.md`](CONTRIBUTING.md); the public/private
  boundary that keeps proprietary oracle material out of this repo is
  [`PUBLISHING.md`](PUBLISHING.md).
- **Charter raises are explicit.** Post-MSX1 axes — MSX2 / 2+ / Turbo-R (a *clone* axis
  with oracles) and extension-cartridge hardware such as the V9990 and Konami SCC/SCC+
  (a *greenfield, own-design* axis with no oracle) — are catalogued in
  [`TODO.md`](TODO.md) but out of charter until that document says otherwise.

## In one line

> zerobas reimplements MSX systems clean-room, and in doing so produces
> clean-provenance documentation of how they work. Both are the deliverable — and
> where good documentation does not yet exist, producing it is the point.
