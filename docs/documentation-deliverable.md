<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# The documentation deliverable — discipline + coverage check

zerobas has **two co-equal deliverables** ([`../MISSION.md`](../MISSION.md)): the
clean-room **implementations**, and the clean-provenance **documentation** of how
the systems work. The implementations have a traceability audit
([`clean-room-audit.md`](clean-room-audit.md)). This is the parallel discipline
for the **second** deliverable — what counts as the documentation product, and a
cheap on-demand check that it actually exists rather than having quietly drifted
into working notes.

It exists because the documentation deliverable *did* drift: the disk track
generated a 1,716-line investigation journal but never distilled it into a
standalone spec, while the same firewall that made it publishable sat unused. The
discipline below is how that stops being invisible.

## Two genres — only one is the deliverable

The repo accumulates two very different kinds of prose, and they are easy to
conflate because both have clean provenance:

| Genre | What it is | Examples | Is it the deliverable? |
|-------|-----------|----------|:----------------------:|
| **Process / notebook** | the investigative trail — hypotheses, reversals, dated entries, "commit pending" | `disk/docs/provider-oracle-scope.md` (the `§8.x` series), `PROVENANCE.md` logs, the probe corpus | **No** — necessary scaffolding (provenance + reproducibility), not the product |
| **Product / spec** | the distilled, standalone "here is how this *actually behaves*" reference | `tape/docs/spec-cassette.md`, `basic/docs/spec-*.md` | **Yes** — this is what [`MISSION.md`](../MISSION.md) names as the goal |

The notebook is not waste — it is the provenance trail and must be kept. But the
**deliverable is the spec extracted *from* the notebook**, and producing the
notebook does not discharge the obligation to produce the spec. The drift happens
exactly when a track has a rich notebook and no spec, and that looks like "lots of
documentation" at a glance.

## The bar — what makes a doc the product spec

A document counts as the documentation deliverable iff **all** hold. These are
written to be checkable:

1. **Standalone** — readable without the notebook or the asm; states what *is*,
   not the journey to it. No live `REFUTED` / `REOPENED` / `commit-pending`
   scaffolding (that is notebook).
2. **Current** — no claim contradicted by a later notebook finding or the shipped
   asm. Reversed hypotheses are *pruned*, not preserved inline.
3. **Contract, not narrative** — documents observed input→output behaviour / the
   interface a reimplementer or preservationist needs, not the story of finding it.
4. **Clean-provenance & reproducible** — every non-obvious claim traces to oracle
   or datasheet (the same firewall as the code), and names the probe(s) that
   establish it so a reader can re-run. The probe corpus *is* part of the document.
5. **Honest at the walls** — where an interface cannot be cloned from any allowed
   source, the boundary (*where*, and *why*) is documented as a result. A cleanly
   documented negative result is a deliverable ([`MISSION.md`](../MISSION.md), "even
   the walls are deliverables").
6. **Aimed** — it *exists at all* wherever the value lens demands (next section).

## Aiming it — value scales inversely with what exists

From [`MISSION.md`](../MISSION.md), the lens for where a spec is *mandatory* vs
merely nice:

- **Nothing exists** (empty shelf — e.g. the disk-ROM `$40xx` kernel the MSX2 TH
  omits; the Konami SCC) → a clean characterisation **produces the primary
  reference outright**. Highest value; the spec is **mandatory**. zerobas is here a
  *source, not a sink*.
- **Only RE'd compilations exist** → we can produce a *cleaner-provenance*
  reference from allowed sources + oracle. Spec **strongly wanted**.
- **An official datasheet exists** (Z80, V9938) → our value is *worked, validated
  integration*, not a re-statement of the datasheet. Spec **optional / thin**.

The aiming rule means the documentation gaps are not equal: an empty-shelf gap is
a missing deliverable; a datasheet-exists gap is barely a gap at all.

## When to distil — settle-gated, not per-session or per-conclusion

The product spec is built **incrementally, but gated on a contract *settling*** —
which is neither of the two tempting poles:

- **Not per session / eagerly.** Mid-investigation a contract is *provisional*;
  distilling it risks speccing a claim that a later finding overturns (e.g.
  `§8.12` concluded `$4030` was a clean-room wall — `§8.13` retracted it). Eager
  distillation just relocates churn from the notebook, where it belongs, into the
  deliverable, where it is the failure this discipline exists to prevent.
- **Not batched at sub-project conclusion.** "Conclusion" recedes on a long track
  (the disk drift); and end-of-project distillation of a large journal is the most
  error-prone time to write the spec — stale context, reversed hypotheses to
  adjudicate. This is what neglect looks like in practice.

The rule:

1. **Seed the spec file early** — at sub-project start, or at its first settled
   contract — as a skeleton, not prose. The deliverable then always exists and
   *grows*; it is never a daunting from-scratch backfill at the end.
2. **Promote a contract notebook → spec the moment it settles** — in this
   workflow, the milestone-closure entries (contract confirmed, asm shipped, probe
   green; e.g. `§8.14 $4030 IMPLEMENTED`, `§8.27 $50A9 IMPLEMENTED`). This is the
   same milestone cadence that gates full-verify-trail, so spec promotion and
   doc-fidelity re-check happen at the same gates.
3. **Leave provisional contracts in the notebook** until they stop moving. The
   signal that one is *not* ready: an open question about it still live in the
   journal.

A track that is already deep (disk) therefore has a **one-time backfill** of its
*already-settled* contracts, then rides the cadence forward for the rest — it is
not treated as "conclude, then write."

## The coverage check (cheap, routine) — does the spec exist and is it current?

This is the new, genuinely-cheap check — the doc-side analogue of paper trail.
Read-only, no emulator. Run it per component, and especially after a track lands a
batch of findings.

For each component:

1. **Enumerate established behaviours** — from the notebook `§`-headers, the asm's
   inline citations, and the `TODO.md` done-items, list what the work has actually
   *established* about how the system behaves.
2. **Map each to a product spec** — is it written up in a doc that meets the bar
   above? Record: covered / notebook-only / undocumented.
3. **Check currency** — for each covered item, is the spec contradicted by a later
   notebook finding or by the shipped asm? Record stale spec claims.
4. **Apply the value lens** — rank the gaps: empty-shelf notebook-only items are
   *missing deliverables* (top); datasheet-exists items are barely gaps (bottom).

Output: a per-component **gap map** (covered / notebook-only / undocumented /
stale), ranked by mission value. This tells you *where the deliverable is missing*
without writing a line of it.

## Fidelity is NOT a new check — it is full-verify-trail, re-read

Whether a spec's documented contracts are *true* (match the oracle) is the same
question full-verify-trail ([`clean-room-audit.md`](clean-room-audit.md)) already
answers by re-running the probes — because a spec's contracts and the asm's cited
contracts are the *same contracts*. So **do not build a separate heavy
doc-fidelity check**: when you run full verify trail, read its probe-vs-finding
diffs for *doc* staleness too. A finding that came back STALE there is also a stale
spec claim. The only genuinely new work on the doc side is the cheap **coverage**
check above; correctness is shared.

This is the doc-side mirror of the audit's orthogonality lesson: coverage
(does the deliverable exist?) and fidelity (is it true?) are different questions,
and the cheap one — coverage — is the one that was being missed.

---

## Brief template — Documentation coverage check

Copy into an Agent prompt. Scope to one `<component>`. Read-only; no emulator.

```
You are running a DOCUMENTATION COVERAGE check of zerobas <component> (disk /
basic / tape). Read-only, no openMSX. Goal: a gap map showing where the PRODUCT
SPEC deliverable exists, is notebook-only, is missing, or is stale — NOT to write
the spec.

Read first:
  - MISSION.md (the two deliverables + the value lens)
  - docs/documentation-deliverable.md (this discipline; the two genres + the bar)
  - <component>/docs/*.md, <component>/PROVENANCE.md, <component>/TODO.md

Steps:
  1. ENUMERATE established behaviours: scan the notebook §-headers
     (e.g. disk/docs/provider-oracle-scope.md §8.x), the asm inline citations
     (<component>/<component>.asm), and TODO.md done-items. List what the work has
     established about how the system behaves.
  2. CLASSIFY each component doc as PROCESS/notebook or PRODUCT/spec using the bar
     in documentation-deliverable.md (standalone / current / contract-not-narrative
     / reproducible / honest-at-walls).
  3. MAP each established behaviour -> covered (in a spec meeting the bar) /
     notebook-only / undocumented.
  4. CURRENCY: flag spec claims contradicted by a later notebook finding or the
     shipped asm.
  5. AIM: rank gaps by the MISSION value lens (empty-shelf notebook-only =
     missing-deliverable/top; datasheet-exists = barely-a-gap/bottom).

Do NOT run probes or judge contract correctness (that is full-verify-trail).

Deliver: a per-behaviour gap-map table (behaviour | where documented | genre |
covered/notebook-only/undocumented | stale?), then a ranked MISSING-DELIVERABLE
list with, for each, the one-line spec that should exist and which notebook §§ /
probes it would be distilled from.
```

---

## Per-component status (initial application)

A first read of the discipline against the tree, 2026-06-24:

- **tape** — **has the deliverable.** `spec-cassette.md` (a standalone behavioural
  spec) *plus* `tape-internals.md`; both genres present. The model to copy.
- **basic** — **has the deliverable.** Four `spec-*.md` (tokenise, control-flow,
  tokens/statements, `BLOAD"…",R`). Product-shaped.
- **disk** — **has the deliverable; harvest discharged (2026-07-07).** Seeded
  2026-06-24, then — once the MSX-DOS-1 track concluded — the already-settled
  notebook contracts were promoted in a one-time harvest into
  [`../disk/docs/spec-diskrom-kernel.md`](../disk/docs/spec-diskrom-kernel.md)
  (commit 1ed1611). Now §1–5 boot-path ABI + **§6 the full BDOS-in-ROM function
  surface** (~40 functions → canonical page-1 entries; M13→M36) + **§7 work-area
  construction** + **§8 the C-BIOS seam rules** (seed-above-the-`$FF`-gate) + **§9
  Tier-C boundary behaviours** + the FDC-window/FAT12 remediations (§4) — primary
  documentation that existed nowhere before. The 2026-06-24 "seeded" spec had also
  gone **stale** (framed COMMAND.COM-hosting / `$5454`-output as deferred when they
  landed); the harvest corrected that currency too. The **Disk-BASIC verb surface**
  (a layer above the kernel ABI) was also promoted, to its own product spec
  [`../disk/docs/spec-diskbasic-verbs.md`](../disk/docs/spec-diskbasic-verbs.md)
  (distilled from the file-channel spike + the verb scoreboard). Going forward both
  specs ride the settle-gated cadence; nothing disk-side remains notebook-only that
  meets the bar for promotion.
