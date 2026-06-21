<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# Provider oracle — scope (Phase 1.5 box (b), the one open item)

Status: **Tier 1 DONE.** Phase 1.5 host + provider code is committed
(`a23d78d`, `15329e2`); the Tier-1 provider oracle is now built and passing. A
**genuine MSX1 BIOS** (National CF-3300) cold-boot scan calls zerobas-disk's INIT,
which installs `H.PHYD ($FFA7) = F7 87 10 40 C9`, and the **real BIOS PHYDIO**
($0144) call dispatches *through* that hook into our DSKIO — verified two ways:
sector 0 read back byte-identical to the on-disk boot sector with `CY=0`, and a
breakpoint on `$FFA7` is *hit* during PHYDIO (so the hook is load-bearing, not
bypassed). A CY=1 write+readback round trip on a high data sector also passes. **No
probe-injected hook anywhere in the path** — the hook is present only because the
real boot scan ran our INIT (confirmed by reading `$FFA7` after a clean cold boot,
before any stub injection). Tooling: `install-openmsx-machine.py --real-bios-disk`
builds `National_CF-3300_ZEROBASDISK` (real CF-3300 BIOS, zerobas-disk in slot 3-1).
Harness: `disk-spec/tools/disk_probe_provider_phydio.py`. **Tier 2** (a real
filesystem — DOS/Disk-BASIC — mounting a drive on us, the only organic GETDPB
consumer) remains deferred to Phase 2.

The remaining historical text below records the original scoping rationale.

The provider *contract* is also validated by strong
black-box checks (HPHYD bytes correct after INIT; GETDPB byte-identical to a CF-3300
differential trace; an injected-hook `CALL $FFA7` reaching our DSKIO). What Tier 1
adds on top is the **organic real host** proof: a genuine MSX BIOS, not a probe
stub, drives zerobas-disk through the standard hook/DSKIO path.

## 1. The circularity finding (read this first — it bounds the whole scope)

"A real MSX-DOS host drives zerobas-disk" is **partly self-contradictory** for a disk
ROM, and the contradiction defines what is and isn't in scope:

* **MSX-DOS is loaded *by* the disk ROM.** On a real MSX, the disk ROM's own boot code
  reads the boot sector, then loads `MSXDOS.SYS` + `COMMAND.COM` and jumps in (MSX2 TH,
  disk boot sequence). So "real MSX-DOS" does not exist *before* a disk ROM produces it.
  zerobas-disk does **not** implement the DOS boot loader (no `MSXDOS.SYS` load). A
  literal "boot real MSX-DOS off zerobas-disk" therefore requires building the DOS-boot
  path first — a **charter expansion**, Phase-2 territory, not a test harness.
* **Disk BASIC lives *inside* the disk ROM.** "Real Disk BASIC driving zerobas-disk" is
  likewise impossible — the Disk-BASIC verbs (`FILES`/`OPEN`/`PRINT#`/…) are code in the
  disk ROM itself. Hosting a foreign disk ROM's Disk-BASIC extension is the explicit
  **Phase-2** charter item.

What **is** organic and achievable without raising the charter: the **real main-BIOS
PHYDIO** code path. The standard MSX main BIOS exposes a `PHYDIO` routine that dispatches
through the `H.PHYD ($FFA7)` hook (MSX2 TH, disk basic interface / hook table). That is
real BIOS code — not C-BIOS, not a probe stub — exercising exactly the hook zerobas-disk
installs.

## 2. Tiers of "organic", and what each actually proves

| Tier | Host that drives us | Exercises | Achievable now? |
|------|--------------------|-----------|-----------------|
| 0 (done) | probe stub `CALL $FFA7` on C-BIOS | hook bytes + DSKIO routing + data | ✅ already passed |
| **1 (this scope)** | **real MSX1 main-BIOS `PHYDIO`** | real BIOS → `H.PHYD` → our DSKIO, organically | ✅ small tooling gap |
| 2 | real MSX-DOS / real Disk-BASIC filesystem layer | DSKIO **+ GETDPB** + dir/FAT consumed by a real FS | ❌ needs DOS-boot or Dos-BASIC hosting = Phase 2 |

GETDPB note: **PHYDIO alone never calls GETDPB** — only a filesystem layer (DOS/Disk-
BASIC) consumes a DPB. So Tier 1 does *not* organically exercise GETDPB; its differential
(byte-identical to CF-3300) stays the strongest available evidence until Tier 2. That is
acceptable: GETDPB has no behaviour beyond the bytes it returns, and those are pinned.

## 3. Recommended target: Tier 1 (real-BIOS PHYDIO)

**Deliverable:** prove that on a machine with a *genuine* MSX1 main BIOS, the cold-boot
scan calls zerobas-disk's INIT (installing `H.PHYD`), and a subsequent **real BIOS
`PHYDIO` call** routes through that hook into our DSKIO and returns correct sector data —
with no probe-injected hook anywhere in the path.

### Work breakdown
1. **Tooling (the one real gap).** Today `tools/install-openmsx-machine.py` wires
   zerobas-disk only behind **C-BIOS** machines. Add a variant that wires zerobas-disk
   behind a **real MSX1 BIOS**. Two options:
   * **(a) Replace CF-3300's disk ROM.** `National_CF-3300` has a real MSX1 BIOS *and* a
     stock disk ROM in slot 3-1; build a machine that keeps the CF-3300 main BIOS but
     swaps slot 3-1 to zerobas-disk. Cleanest — the slot wiring already matches our FDC
     model (National WD2793, the connection style we target).
   * (b) Add a disk slot to a disk-less real-BIOS machine (e.g. a `cf-1200`/`cf-2700`
     BIOS). More wiring, no upside over (a).
   Prefer (a). Reuse the existing `expand_slot3` / `--disk-rom` machinery; the only change
   is sourcing the main BIOS from a real ROM instead of C-BIOS.
2. **Harness.** A probe (sibling `disk-spec/tools/disk_probe_provider_phydio.py`) that:
   boots the Tier-1 machine on a **/tmp copy** of `test720.dsk` (never the committed
   image — see [[test-disk-mutation-gotcha]]); confirms `H.PHYD ($FFA7..AB)` holds our
   `F7 <slot> 10 40 C9` after boot (proves the *real* scan called our INIT); then issues a
   **real BIOS `PHYDIO`** call (entry address per MSX2 TH BIOS jump table — sourced from
   TH, not disassembly) to read sector 0, and asserts the bytes equal the on-disk boot
   sector and `CY=0`. Optionally a write+readback for the `CY=1` path.
3. **Clean-room.** All of the above is black-box: we call documented BIOS/hook entries and
   read RAM/registers; we never read the CF-3300 BIOS or disk-ROM code bytes. The BIOS
   `PHYDIO` entry address comes from the TH BIOS jump table (allowed source).

### What Tier 1 proves vs. leaves open
* **Proves:** a real MSX BIOS's own PHYDIO path reaches zerobas-disk's DSKIO via the
  standard hook — the load-bearing half of "real host can drive us", organically.
* **Leaves open (→ Tier 2 / Phase 2):** a real *filesystem* (DOS/Disk-BASIC) mounting a
  drive on us — which is the only thing that organically consumes GETDPB and the dir/FAT
  surface. That needs DOS-boot or Disk-BASIC hosting and is charter-raising.

## 4. Effort & risk

* **Effort:** ~one focused agent session. The bulk is the install-script Tier-1 variant
  + one new probe; no new asm in zerobas-disk (the provider code already shipped).
* **Risk / unknown to resolve in-session:** confirm the real main-BIOS `PHYDIO` actually
  dispatches through `H.PHYD` on the chosen machine (TH says it does; verify by the same
  black-box trace already used for the CF-3300 hook study). If a given BIOS reaches its
  disk ROM by a different internal route, fall back to a different real-BIOS machine — the
  hook contract itself is already CF-3300-confirmed.
* **Not in scope (explicitly):** implementing the MSX-DOS boot loader or hosting a foreign
  Disk-BASIC extension. Both are Phase 2; see [`expansion-protocol.md`](expansion-protocol.md) §"Charter boundary".

## 5. Recommendation

Tier 1 is worth doing — it converts the provider direction from "contract validated by
differential + stub" to "real BIOS code organically drives us", closing box (b) at the
highest fidelity available without raising the charter. Defer Tier 2 to Phase 2, where the
DOS-boot / Disk-BASIC-hosting work it depends on already lives.
