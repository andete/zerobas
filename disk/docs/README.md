<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# disk/docs — index & map

Orientation for the disk-ROM docs. zerobas's mission is **dual and co-equal**:
clean-room *implementations* AND clean-provenance *docs* of undocumented MSX
internals — so the product specs below are deliverables, not scaffolding.

**Resuming the Tier-2 DOS-boot hunt? Read [tier2-STATE.md](tier2-STATE.md) first** —
it is the overwritten O(1) resume board (live thesis / settled facts / dead ends /
next action). Everything else is reference, deliverable, or provenance trail.

The docs sort into genres ([cadence](../../docs/documentation-deliverable.md)):
investigation **notebooks** distil settled contracts into **product specs**.

## Product specs — the deliverables (clean-provenance MSX internals)
- [spec-diskrom-kernel.md](spec-diskrom-kernel.md) — the MSX-DOS-1 disk-ROM kernel ABI ($4030/$50A9/$5454 entries + the $F100–$F3FF resident work area). The distilled product of the Tier-2 notebooks.
- [file-channel-protocol.md](file-channel-protocol.md) — Disk BASIC file-channel protocol (Phase 2).
- [expansion-protocol.md](expansion-protocol.md) — disk expansion / slot protocol (Phase 1.5).

## Reference — how things work / status
- [openmsx-probing-toolbox.md](openmsx-probing-toolbox.md) — the emulator probing catalogue (reverse-replay, watchpoints, slot/VRAM reads, symbol load).
- [oracle-artifacts.md](oracle-artifacts.md) — Tier-2 oracle artifact identity & provenance (hashes).
- [cbios-diskrom-status.md](cbios-diskrom-status.md) — C-BIOS disk-ROM status; what a `cbios-disk` effort faces.

## Resume board & notebooks (investigation trail)
- [tier2-STATE.md](tier2-STATE.md) — **read first** when resuming; overwritten, not appended.
- [provider-oracle-scope.md](provider-oracle-scope.md) — the big Phase-1.5 provider-oracle notebook (the §8.x trail; settled facts promote into spec-diskrom-kernel.md).
- [tier2-review-queue.md](tier2-review-queue.md) — live log of judgment calls taken without per-step sign-off (Open entries only).
- [tier2-review-archive.md](tier2-review-archive.md) — the reviewed/superseded history split out of the queue.

## Tier-2 plans & scope (process)
- [tier2-kernel-plan.md](tier2-kernel-plan.md) — the plan to host COMMAND.COM to `A>`.
- [tier2-architecture-audit.md](tier2-architecture-audit.md) — BIOS-agnostic disk ROM for C-BIOS (CF-3300 = oracle).
- [tier2-bdos-scope.md](tier2-bdos-scope.md) · [tier2-bdos-spec.md](tier2-bdos-spec.md) · [tier2-bdos-coverage.md](tier2-bdos-coverage.md) — BDOS sizing fork, the $0005-intercept spec, and the coverage scoreboard.
- [diskbasic-verb-coverage.md](diskbasic-verb-coverage.md) — Disk-BASIC verb coverage scoreboard + acceptance-gate scope (the BASIC-side counterpart of the BDOS coverage/gate work).
- [diskbasic-acceptance-spec.md](diskbasic-acceptance-spec.md) — spec for the `make diskbasic-acceptance` standing gate (awaiting sign-off).
- [tier2-workarea-map.md](tier2-workarea-map.md) — the $F100–$F3FF DOS work area the disk ROM builds at boot.

## Milestone specs — clean-room provenance (cited from the `.asm` source; keep)
Each is the pre-implementation spec for one landed milestone; the source files cite
them as the clean-room paper trail, so they are provenance, not stale scaffolding.
- [tier2-a2-spec.md](tier2-a2-spec.md) · [tier2-a2b-spec.md](tier2-a2b-spec.md) · [tier2-a3-spec.md](tier2-a3-spec.md) · [tier2-a5-spec.md](tier2-a5-spec.md) — the `int_h` / interrupt-relocation arc.
- [tier2-m5.4-spec.md](tier2-m5.4-spec.md) · [tier2-m5.6-spec.md](tier2-m5.6-spec.md) · [tier2-m6-spec.md](tier2-m6-spec.md) · [tier2-m8-spec.md](tier2-m8-spec.md) — COMMAND.COM-load, segment-switch hooks, work-area build, CONOUT.
- [tier2-f338-default-spec.md](tier2-f338-default-spec.md) · [tier2-gdate-spec.md](tier2-gdate-spec.md) · [tier2-phase1-spec.md](tier2-phase1-spec.md) — the DOS-default / date-path / work-area-clear slices.
