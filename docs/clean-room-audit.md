<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Clean-room audit — two checks

How to *prove*, after the fact, that a component's assembly is clean-room
compliant — not just assert it. This is the audit companion to
[`allowed-sources.md`](allowed-sources.md) (the *what is allowed* catalogue) and
[`dev-workflow.md`](dev-workflow.md) (the *how to build it cleanly* procedure).

It exists because a sub-agent once derived assembly from a path our charter
forbids, and "it boots / the probes pass" did **not** surface it. These two
checks are how we catch that class of failure deliberately, on demand. **Neither
runs automatically** — they are invoked, scoped to one target (`disk`, `basic`,
`tape`, or a future one), and the heavier one is gated to milestones.

## The chain every clean line stands on

Clean-room compliance is a property of a **provenance chain**, not of any single
artifact:

```
asm line ──cites──> finding (spec/PROVENANCE §) ──cites──> probe (code) ──observes──> oracle (black-box)
```

A line is clean iff this chain **exists**, is **unbroken**, and **every hop is
from an allowed source** — black-box oracle observation, a published datasheet /
standard, or our own design; never a disassembly, never a byte-copy of a
reference ROM / `MSXDOS.SYS` / `COMMAND.COM`. (Some hops legitimately ground out
in a datasheet or standard rather than a probe — e.g. ECMA-107 FAT12 offsets,
the Z80 ISA. Those terminate the chain just as validly; the audit confirms the
cited document is itself `Clean`/`Scoped` per [`allowed-sources.md`](allowed-sources.md),
not that a probe exists.)

In this repo the hops are concrete:

- **finding** — a numbered `§` entry in a component spec
  (`disk/docs/provider-oracle-scope.md`, the `§8.x` series) or a `§` section in a
  component `PROVENANCE.md`.
- **probe** — a `probes/<target>/*.py` black-box program that drives the oracle
  machine and records observed input→output behaviour.
- **oracle** — a real reference machine / disk under openMSX, observed only
  through its legal interface (inputs in, outputs out).

## The two checks — what each actually catches

The critical point, and the reason there are two: **they are orthogonal in
coverage even though the second contains the first's steps.**

|                       | clean-room violation | correctness drift / stale finding / probe rot |
|-----------------------|:--------------------:|:---------------------------------------------:|
| **Paper trail**       | ✅                   | ❌                                            |
| **Full verify trail** | ✅ (via its read pass)| ✅                                            |

A provenance violation is **invisible to probe execution**: if forbidden-sourced
bytes happen to be *correct*, every probe passes. So the failure that motivated
this doc is a **paper-trail-class** problem. Running probes does not add
provenance assurance — it adds *correctness* assurance. Choose the check by the
question you are asking, not by "how thorough do I want to be":

- **"Did someone violate clean-room?"** → **paper trail.** Right tool, cheap.
  Full-verify only catches it via the read pass it shares with paper trail.
- **"Is the asm correct *and* clean, ship-ready?"** → **full verify trail.**
  Here paper trail is subsumed — you get it for free inside the read pass.

### Cost — they differ a lot, asymmetrically

Both checks **read** every asm region + every cited finding + every cited probe's
source. That front half is roughly equal: bounded, parallelisable, no emulator.

All the divergence is full-verify's back half:

- spin up openMSX and **run** each cited probe (slow; honour the pty-leak +
  one-reused-sonnet-agent discipline — see the harness notes);
- **fix** probes that bit-rotted and **author** new probes where a behaviour has
  no coverage — this last item is the unbounded cost;
- diff fresh oracle output against the recorded finding.

Estimate on the disk track (heavy probe runs, churning `§8.x` surface):
**full verify ≈ 3–10× paper trail**, and far more fragile (emulator, agent
reuse, wall-clock). Where a behaviour is already locked into the host unit-test
harness (`make unit-test`), prefer that over a full emulator run for that hop.

The nesting only goes one way: **you never run both separately** — if you are
doing full verify, paper trail is the read pass inside it.

## When to run which

- **Paper trail — routine, mandatory gate on any sub-agent asm.** Run it on the
  *diff*, not the whole target, after any agent lands assembly. Cheap enough to
  be habitual. A whole-target paper trail is the one-time "clean the backlog"
  pass.
- **Full verify trail — a tier-closure ritual.** Run it deliberately a handful of
  times — before declaring a tier/phase closed — not as a routine gate.

### The precondition that keeps paper trail cheap

Paper trail is near-mechanical **only if the citation chain is written down**:
each asm region cites its `§finding`, each finding names its probe. Where the
citation is missing, the audit degrades into *re-deriving* provenance from
scratch — expensive, judgement-heavy, and exactly the gap a violation slips
through. So enforcing the inline-citation convention
([`dev-workflow.md`](dev-workflow.md) per-feature checklist) is not bookkeeping;
it is what makes the audit affordable. A missing citation is itself the first
finding.

### The one hop in paper trail that is *not* mechanical

Paper trail trusts the finding and probe docs. A finding can cite a real probe
yet have been *written* by interpreting forbidden material; a probe can exist yet
smuggle oracle internals instead of observing them black-box. So for each cited
probe the auditor must make one judgement call — **"is this genuinely black-box?"**
— not merely "does it exist." That is the integrity floor of the whole check.

---

## Brief template — Paper trail (provenance audit)

Copy into an Agent prompt. Scope to one `<target>` (or one diff). Read-only; no
emulator.

```
You are running a PAPER-TRAIL clean-room audit of zerobas <target> (e.g. disk).
Read-only. Do NOT run openMSX or any probe. Goal: prove every asm region stands
on an unbroken, allowed-source provenance chain — or list the breaks.

Read first, in order:
  - README.md (the firewall / governing test)
  - docs/allowed-sources.md (the rated source catalogue + the ✗ list)
  - docs/clean-room-audit.md (this method; the chain model)
  - <target>/PROVENANCE.md and <target>/docs/*.md (the findings)

Then walk <target>/<target>.asm region by region. For EACH region:
  1. Find its provenance citation (inline comment: §finding / PROVENANCE § /
     probe name / datasheet §). MISSING citation -> record as a BREAK (orphan asm).
  2. Resolve the citation. Confirm the finding documents a CONTRACT (observed
     input->output behaviour / a published interface), never a byte transcription
     or a disassembly restatement.
  3. Resolve finding -> its probe (or its datasheet/standard). If a probe:
     read the probe source and judge "is this genuinely BLACK-BOX?" — it drives
     the oracle through a legal interface and records outputs; it does NOT embed
     disassembled internals. If a document: confirm it is Clean/Scoped in
     allowed-sources.md, not a ✗ source.
  4. Verdict per region: CLEAN / BREAK (with the specific reason).

Do NOT run probes, do NOT judge correctness — only provenance.

Deliver: a per-region verdict table, then a BREAKS list ranked by severity
(forbidden-source citation > orphan asm > finding-not-a-contract >
probe-not-black-box > citation present but unresolvable). For each break: the
asm line range, what is wrong, and the minimal fix (add citation / write the
missing finding / re-derive cleanly / quarantine).
```

## Brief template — Full verify trail (provenance + correctness audit)

Copy into an Agent prompt. Scope to one `<target>`. Heavy: emulator + probe
runs. Milestone-gated. Honour the pty-leak / agent-reuse discipline — reuse ONE
sonnet agent across probe runs; do not spawn a fresh shell per probe.

```
You are running a FULL-VERIFY-TRAIL clean-room audit of zerobas <target>.
This is PAPER TRAIL + empirical re-check. Heavy (runs openMSX). Reuse ONE agent
across all probe runs.

Phase A — PAPER TRAIL: do the entire paper-trail brief above first. Produce its
per-region verdict table and BREAKS list. Do not skip; the read pass is shared.

Phase B — EMPIRICAL RE-CHECK, for each cited probe:
  5. Re-run the probe against the oracle machine (see docs/openmsx-harness.md;
     mind the test-disk mutation gotcha — work on /tmp copies, git-restore after).
     Prefer `make unit-test` for any hop already locked into the host harness
     instead of a full emulator run.
  6. Diff fresh oracle output vs the result recorded in the finding. Mismatch ->
     STALE FINDING (record old vs new).
  7. Where an asm behaviour is covered by NO probe, write the probe. If it cannot
     be written black-box, that asm is provenance-SUSPECT -> escalate to a BREAK.
  8. Confirm the asm's behaviour matches the (re-validated) finding.

Deliver: the paper-trail table/breaks, PLUS a correctness table (probe -> pass /
stale / newly-written), the list of any probes you added, and any asm that could
not be black-box-verified. State plainly what was re-run vs what leaned on
unit-test vs what could not be verified.
```

---

## Per-target notes

- **disk** — the active, churning track (Tier-2 DOS-boot, the `§8.x` series in
  `disk/docs/provider-oracle-scope.md`). Highest-risk surface; point the first
  whole-target paper trail here. Findings: `provider-oracle-scope.md` +
  `disk/PROVENANCE.md`. Probes: `probes/disk/`.
- **basic** — `basic/PROVENANCE.md`; probes `probes/basic/`. Much is locked into
  `make unit-test`, so its full-verify back half is cheaper than disk's.
- **tape** — `tape/PROVENANCE.md`; probes `probes/tape/`. Smallest surface
  (a C-BIOS patch, not a slot ROM).

---

## Audit run log

A run is only worth as much as its record — log each paper-trail / full-verify
pass here (date, scope, commit, verdict) so a later session knows what was
verified clean and at what point, rather than re-deriving it. A clean verdict is
a load-bearing fact for the public-release gate.

### 2026-06-24 — disk, paper trail — ✅ CLEAN (at `fd08480` + uncommitted `bdos_rdblk` comment fix)

First exercise of the discipline. Triggered by `provider-oracle-scope.md` §8.37:
a delegated sub-agent had disassembled `MSXDOS.SYS` internals, reverted §8.33's
`$F340=0`, and hacked dual-purpose entries onto `fdc_di_save`/`fat_find` — all
reportedly reverted to clean §8.36. This run **verified that revert held**, then
swept the whole file.

- **Scope:** first the touched region (`disk.asm` §8.33–8.38: `set_ramad`/`$F340`,
  `fdc_di_save`/`fdc_io_done`, `p1_blit`, `dskio_ok` `B=0`, `bdos_rdblk` `BC=HL`,
  `build_resident`, `$50A9`); then the whole `disk.asm` (302 defs / 60 sections).
- **§8.37 smoking guns — all confirmed reverted clean:** `$F340=0` present
  (disk.asm:560); `fdc_di_save` a clean single-purpose IFF guard, no dual entry;
  `fat_find` a clean single-purpose FAT12 scan, no overload. The
  disassembly-derived changes are **not in the working tree**.
- **Whole-file:** every section header carries a source citation; **zero**
  forbidden-source citations (every textual match is a *negation* — "never read");
  all cited `PROVENANCE.md` sections resolve; FDC cmd/status bits → WD2793
  datasheet, register map → openMSX scoped to register facts (GPL-conditional
  honoured); `getdpb` → §DPB + CF-3300 oracle; FAT layer → FAT spec / ECMA-107.
- **Probe integrity (the non-mechanical hop):** spot-checked `dosboot_{50a9,4030,
  fdc,dskio_exit}` — breakpoint + register/RAM/IO snapshot + entry present-vs-absent
  byte check; **genuinely black-box**, no disassembly or ROM-code lift.
- **Findings:** no clean-room breaks. One low-severity *comment* nit — `bdos_rdblk`'s
  `out:` header omitted the `BC=HL` return added in §8.33 (fixed; rides the next
  disk commit). This was a **provenance** pass, not a line-by-line correctness
  re-read (that is full-verify-trail, milestone-gated).
- **Not yet run:** tape, basic (lower-risk: published-interface sources, settled,
  no incident) — slated for the public-release gate, basic before tape.

### 2026-06-24 — basic, paper trail — ✅ CLEAN (at `d160f8c`)

Whole-component, no incident — establishing the public-release baseline. Surface:
24 `.asm` files + `sysvars.inc`, ~11.5 k lines, 901 labels.

- **Forbidden-source citations:** **zero**. Every `disassembly`/`gw-basic` mention
  is an attestation — **each of the 24 files carries a "No disassembly" header**,
  and `main.asm`/`sysvars.inc` state nothing is derived from an MSX-BASIC/GW-BASIC
  or reference-ROM disassembly.
- **Citation:** per-feature `basic/PROVENANCE.md` sections (each names its source
  files + verdict); local jump labels inherit their section's citation.
- **Highest-risk spot-read — the token tables (the most liftable-from-disassembly
  artifact):** **provably oracle-sourced, not lifted.** Crunch byte-identity to the
  VG-8020 is *verified* by `basic_probe_crunch.py`; every token byte traces to the
  black-box fidelity sweep (`spec-tokens-statements.md §3/§4`); the tokeniser/
  evaluator algorithm is own code "not derived from any disassembly." Byte-identity
  achieved by *observing* the ROM's output, never by reading its table — the
  gold-standard method. `kwtable` entries cite "oracle-LOCKED, VG-8020; MSX2 TH".
- **Findings:** no clean-room breaks. Provenance pass (file-attestation + section-
  citation + forbidden-scan + token-table spot-read), not a line-by-line re-read of
  11.5 k lines.

### 2026-06-24 — tape, paper trail — ✅ CLEAN (at `d160f8c`)

Whole-component, no incident. Smallest surface (a C-BIOS cassette patch); has its
own `tape/docs/clean-room-policy.md` and a `PROVENANCE.md §Audit`.

- **Forbidden-source citations:** **zero** (no mention at all).
- **Highest-risk spot-read — the waveform timing constants:** **all derived or
  own-design, round-trip-validated, "not copied from any ROM."** Half-period counts
  derive from documented FSK frequencies (Tech Handbook) + the 3.58 MHz Z80 clock
  (hardware) + a black-box-measured per-half cost (oracle); the leader/auto-baud/
  threshold values are own algorithm with no original analogue; all marked
  `quarantined`. The one `sourced` constant (`CASIN_R14=14`) is a PSG register
  number (hardware fact).
- **Findings:** no clean-room breaks.

**Whole-repo baseline: all three components (disk, basic, tape) paper-trail CLEAN
as of 2026-06-24** — the provenance precondition for public release is met.
