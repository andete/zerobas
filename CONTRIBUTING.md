<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Contributing to zerobas

Contributions are welcome — but zerobas is a **clean-room** project, and that imposes
one hard, non-negotiable condition that most projects don't have. Please read this
before opening a pull request; a contribution that breaches the provenance firewall
**cannot be accepted**, and because the repository history is public it cannot be
quietly removed afterwards. The gate is strict by necessity.

zerobas has **two co-equal deliverables** ([`MISSION.md`](MISSION.md)): the clean-room
**implementations** and the clean-provenance **documentation**. A good contribution
serves the firewall on both.

## Read first

- [`MISSION.md`](MISSION.md) — what the project is for, and why provenance is load-bearing.
- [`README.md`](README.md#traceability-is-the-whole-point) — the firewall and the
  allowed-source category list.
- [`docs/allowed-sources.md`](docs/allowed-sources.md) — every concrete source, rated and
  scoped.
- [`docs/dev-workflow.md`](docs/dev-workflow.md) — how to implement a feature and prove
  it correct (the per-feature checklist, the validation harness, the tokeniser quirks).

## The one hard rule: the provenance firewall

> Documentation may be used only where it specifies a **published / standard interface
> the original was built to conform to** — never where it reveals a reference
> implementation's *internals*.

**Forbidden, without exception** — never read, quote, paste, or feed into any tool or
model, and never derive a contribution from:

- any reference **BIOS / MSX-BASIC ROM / disk-ROM disassembly** or commented listing
  (including the reference ROMs used as oracles);
- any **MSX-BASIC / GW-BASIC / BASIC-80** source or decompilation;
- the **bytes of any proprietary system binary** (a reference ROM, `MSXDOS.SYS`,
  `COMMAND.COM`) read as anything other than a **black-box oracle** — identical inputs
  in, observed outputs out;
- community **reverse-engineering compilations** (e.g. the MSX Wiki / MSX Resource
  Center) *where they reveal protected internals*; cite the published source instead.

**This binds tools and AI models exactly as it binds humans.** Do not paste a
disassembly or proprietary code into an editor, assistant, or model while producing a
contribution. An AI's context is restricted to the same allowed sources, behavioural
specs, and black-box oracle observations as a human contributor.

## Every contribution must be traceable

Hold your contribution to the same standard as the existing tree:

- **Cite every non-obvious value.** Each new constant / address / token byte / data
  table / algorithm gets an **inline citation** at its definition *and* a row in the
  relevant `PROVENANCE.md`, marked `sourced` (traced to an allowed source or this
  project's own oracle observation) or `quarantined` (derived from a documented
  format/spec and justified by oracle round-trip — never copied). An unexplained magic
  value blocks the merge.
- **Capture what you learned.** If your work establishes something new about how the
  original behaves (a confirmed contract, a quirk, a corrected finding), write it into
  the relevant spec / characterisation doc — that documentation is a deliverable, not a
  byproduct.

## The two-role discipline

The firewall is easiest to keep if you separate, in time and inputs, the two roles
(see [`tape/docs/clean-room-policy.md`](tape/docs/clean-room-policy.md)):

- **Spec author** — observes the oracle (decoded bytes, captured edges, port states) and
  writes the behavioural spec from allowed sources. May see oracle *outputs*; may **not**
  see any original/reference *code*.
- **Implementer** — writes from the spec and the failing tests only; never sees original
  or disassembled reference code.

## How to contribute

1. Fork and branch; keep each PR to **one logical change** (the project works one TODO
   item at a time — see [`docs/dev-workflow.md`](docs/dev-workflow.md)).
2. Build: `make`. Test: `make unit-test` (emulator-free) — and the differential probes
   where applicable. Don't regress the byte-identical crunch probe.
3. Follow the per-feature checklist in `docs/dev-workflow.md`, including the
   `PROVENANCE.md` row and inline citations.
4. **Sign off every commit** (`git commit -s`) — see below.

## Sign-off: the Clean-Room Certificate of Origin

Every commit must carry a `Signed-off-by: Real Name <email>` line (add it with
`git commit -s`). By signing off, you certify the following — a Developer Certificate of
Origin extended with the clean-room clauses **(e)** and **(f)**:

> By making this contribution, I certify that:
>
> (a) the contribution was created in whole or in part by me, and I have the right to
>     submit it under the project's license; or
> (b) the contribution is based on previous work that, to the best of my knowledge, is
>     covered under an appropriate open-source license and I have the right under that
>     license to submit it under the project's license; or
> (c) the contribution was provided directly to me by some other person who certified
>     (a), (b), or (c), and I have not modified it.
> (d) I understand and agree that this contribution and this certificate are public and
>     a record of it (including my sign-off) is maintained indefinitely.
>
> (e) **Clean-room provenance.** Every fact, constant, address, table, and algorithm in
>     this contribution traces to an **allowed source** (`docs/allowed-sources.md`) or to
>     this project's own **black-box oracle** observation, cited accordingly — or is
>     explicitly quarantined. **None of it** was derived from a reference
>     BIOS/MSX-BASIC/disk-ROM disassembly, from MSX-BASIC/GW-BASIC/BASIC-80 source, from
>     the bytes of any proprietary system binary read as anything other than a black-box
>     oracle, or from a reverse-engineering compilation revealing protected internals.
> (f) **Tools included.** The same restriction was honoured for every tool and AI model I
>     used: no forbidden source was read by me or fed into any tool or model while
>     producing this contribution.

A sign-off that you cannot truthfully make means the contribution isn't ready — fix the
provenance first.

## License of contributions

zerobas is licensed under **[0BSD](LICENSE)** (code *and* documentation — see the
[License section](README.md#license)). **Inbound = outbound:** your contributions are
accepted under that same 0BSD license. There is no separate CLA; the sign-off above and
the project license are sufficient.
