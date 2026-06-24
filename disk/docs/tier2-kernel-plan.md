<!--
SPDX-License-Identifier: 0BSD
Copyright (c) 2026 Joost Yervante Damad
-->
# Tier-2 kernel phase — the plan to host COMMAND.COM to `A>`

**Status.** GREEN-LIT 2026-06-24 (user: *"we want the full work in the end. The
guidance stands, but we continue."*). This is the forward plan for the phase the
spec [§5](spec-diskrom-kernel.md#5-the-commandcom-load-phase--kerneldisk-rom-call-surface-characterised-reimplementation-deferred)
recorded as *characterised but paused*. It supersedes the "paused" status with a
roadmap; **no asm is written until the architecture fork below is signed off**
(spec-before-implementation).

This plan is itself a documentation deliverable. The provenance trail lives in the
notebook ([`provider-oracle-scope.md`](provider-oracle-scope.md) §8.40–8.46); each
milestone, once settled, distils into [`spec-diskrom-kernel.md`](spec-diskrom-kernel.md) §5.

## Working discipline (standing, restated because this phase is the riskiest)

- **One milestone per session; user reviews between steps.** Opus-driven — no
  sub-agent delegation for judgement on this sub-track.
- **Spec/scope before code.** This doc is that scope; the per-milestone contract is
  characterised and written *before* its asm.
- **Commit each finished milestone** (notebook + spec + probe), no need to ask.
- **Clean-room firewall — the load-bearing rule.** `COMMAND.COM` and `MSXDOS.SYS`
  are **only ever oracles**: identical inputs in, observed outputs out. They are
  **never disassembled or byte-copied** — not their loader bytes, not the page-0
  slot helper, not the `$DDxx` kernel. Every new address / constant / algorithm is
  cited inline to an allowed source (MSX2 TH, map.grauw.nl, hardware datasheets,
  C-BIOS, or our own black-box observation). The one provenance breach this project
  ever had (§8.37) came from a brief that omitted this rule; if any asm is ever
  delegated, the firewall goes in the brief verbatim. `make audit-citations` +
  a human paper-trail pass gate every milestone.
- **No regression.** The unified ROM must keep Disk-BASIC byte-identical: after
  every milestone, `make unit-test`, DSKIO == CF-3300, and the file read/write/dir
  differentials stay green. The cluster lives inside active code, so the M3
  net-zero relocation discipline holds.
- **Scope ceiling.** MSX-DOS **1** only (DOS2 / Nextor is a separate future axis).

## Architecture — what the black box actually requires

§8.45 + §8.46 reframed §8.41's "reproduce the 63 % kernel". There are **two
distinct service surfaces**, not one monolith:

1. **COMMAND.COM's own interface** — what the proprietary shell at `$0100` actually
   calls: its BDOS path (which COMMAND.COM installs at `$0005` itself — `$0005=$00`
   at entry, §8.45) plus the fixed page-1 cluster entries it reaches (e.g. `$607B`
   from `ra=$0100`, §8.41). **This is the surface we must satisfy.**
2. **The page-0 vector table + `$DDxx/$DExx` high-RAM kernel** — §8.46 showed these
   are called only by disk-ROM and high-RAM-kernel PCs, **never by COMMAND.COM**.
   They are the stock's *internal* inter-slot bridge between its page-1 disk ROM and
   the kernel it relocates into high RAM — an artifact of *that* architecture, not a
   contract COMMAND.COM depends on.

### The fork (needs sign-off before M5.3 asm)

- **(a) Faithful relocation model** — reproduce the stock's "relocate the resident
  kernel into high RAM + page-0 inter-slot vectors" structure. Maximum fidelity to
  the stock's *internal* shape; maximum cost; edges closest to re-creating
  MSX-DOS-1 — the thing this sub-track set out *not* to do.
- **(b) Minimal faithful host (recommended)** — keep our DOS logic in the page-1
  ROM, reuse the oracle-validated `bdos_entry` as the resident BDOS, point
  COMMAND.COM's `$0005` path at it, and fill the fixed page-1 cluster contracts
  COMMAND.COM/the loader reach. Lay only the page-0 environment COMMAND.COM actually
  needs (per M5.1), with our *own* slot helper written from the public slot-select
  spec. Fidelity is measured at the **observable boundary** — does COMMAND.COM reach
  `A>` and behave identically — not at the kernel's internal addresses. Cleaner
  clean-room story (contracts, never byte-repro), smaller surface, reuses validated
  code.

Recommendation: **(b)**. The remaining milestones below assume (b); (a) would
insert a "stand up the `$DDxx` band + page-0 vectors" milestone before M5.4.

## Milestones (each: characterise on stock → implement → re-probe progress)

- **M5.1 — COMMAND.COM service-interface map.** Black-box on stock: trace the
  outbound CALL targets COMMAND.COM (`$0100-$1FFF`) invokes, how/when it installs
  `$0005`, and which page-1 cluster entries it reaches. Deliverable: the
  COMMAND.COM→DOS contract list (the precise surface (b) must provide).
- **M5.2 — BDOS path + gap list.** Characterise how COMMAND.COM calls each BDOS
  function; map onto `bdos_entry`; list functions it doesn't yet implement (cf. the
  Random-Block-Read precedent, §8.9). Implement the gaps, validated via
  `disk_probe_bdos.py` cases.
- **M5.3 — `k_47B2` loader body (first cut).** Read COMMAND.COM via our
  CF-3300-identical file layer to `$0100`; lay the page-0 env COMMAND.COM needs (our
  own slot helper from public spec); set the register contract (§5.2); `jp $0100`.
  Validate: COMMAND.COM's own code runs at `$0200` (first proprietary COMMAND.COM
  code executing on zerobas) — measured by a new incremental **progress probe**.
- **M5.4 … M5.N — fill the page-1 cluster contracts** in the order COMMAND.COM hits
  them (the `$5454` playbook ×~N): characterise each entry's contract on stock,
  implement behind its existing veneer, re-run the progress probe, repeat. Each is
  one session.
- **M5.final — reach + validate `A>`.** Pin the `A>` screen
  (`disk_probe_provider_dosboot.py`) against the stock CF-3300 (byte/behaviour), and
  round-trip a `DIR` / file op through the live shell.

## Validation strategy

- **Incremental progress probe** after every milestone: "how far does COMMAND.COM
  get" (PC high-water / last cluster entry reached / screen state) — the single
  metric that says a milestone advanced the boot.
- **Regression gates stay green throughout** (unit-test, DSKIO==CF-3300, file
  diffs) — the unified ROM must never regress Disk-BASIC.
- **Oracle:** `msxdos103-cmd111.dsk` (SHA256 `666cbc6d…`), always on a `/tmp` copy
  (openMSX can write back); `git status` + original-hash check after each run.

## Open questions (resolved as milestones land)

- The exact BDOS-call mechanism COMMAND.COM uses (M5.1/M5.2) — `$0005` JP it
  installs, vs. a cluster entry.
- Whether any cluster entry, once COMMAND.COM drives it, transitively needs a
  high-RAM kernel routine we chose not to build under (b) — the trigger to revisit
  the fork mid-stream.
