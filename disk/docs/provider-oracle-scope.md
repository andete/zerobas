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

## 6. DOS-version scope + the DOS-boot prerequisite (Phase 2 refinement)

**DOS1 is the ceiling (confirmed).** zerobas-disk is MSX1 / FAT12 / single-directory —
DOS1-class. The Tier-2 oracle's authoritative reference is therefore **real MSX-DOS 1**,
black-boxed (proprietary → the clean-room way). **MSX-DOS 2** (subdirectories, FAT16,
MSX2-era) is **out of current scope** — a future axis, not Phase 2.

**Tier 2 needs DOS-boot, not just a disk.** Per §1, a real DOS only exists *after* a disk
ROM loads `MSXDOS.SYS`; zerobas-disk does not implement that boot path. So the organic
Tier-2 oracle ("real DOS1 mounts a drive on us and consumes our GETDPB") is gated on
building **MSX-DOS-boot support** in zerobas-disk — a **distinct sub-track** from the Disk
BASIC verb-surface integration that is Phase 2's core (the file-channel spike). It also
needs a real **MSX-DOS 1 system disk** re-supplied (the 1.5 FCB work used one that is no
longer present in the environment). Until both exist, GETDPB stays pinned by the Tier-0/1
differential (byte-identical to CF-3300), which §2 already deems sufficient.

**The DOS-version asymmetry (for a future DOS2 axis).** If the charter is ever raised to
DOS2, its references are largely **open**, unlike proprietary DOS1:

* **Open MSX-DOS 2 kernel** — the MSX-DOS 2.20 sources were released (Konamiman hosts
  them): an open reference for the DOS2 BDOS/DPB contract.
* **Nextor** — Konamiman's open MSX-DOS-2-compatible kernel (FAT16, MSX1-capable).
  Architecturally a disk-ROM *replacement* (brings its own sector driver), so it does
  **not** sit on top of zerobas-disk as a GETDPB consumer — useful instead as an open
  protocol reference and as a foreign standard disk ROM for host-direction tests.
* **Sunrise** — produced MSX-DOS 2.20 cartridges + IDE interfaces; part of the same open
  2.20 lineage.

Before treating any of these *sources* as an allowed PROVENANCE input, confirm the license
is compatible with a BSD-2 reimplementation; black-box *runtime* use is always fine. None
of this is in scope now — DOS1 is the ceiling.

## 7. DOS-boot feasibility spike (2026-06-22) — GO, gap pinned

Tier 2 was de-risked with a black-box spike before committing to the boot-loader build.
Both gating prerequisites were checked empirically.

**Prerequisite (b) — a real MSX-DOS 1 system disk — SATISFIED (permanent disk on hand).**
`/Users/joost/Documents/msx/msx/disks/test.dsk` (720 KB, OEM "NMS 8245") holds
`MSXDOS.SYS` + `COMMAND.COM` and boots on the **stock National CF-3300** (its own disk
ROM) straight to a DOS prompt:

```
MSX-DOS version 1.03   Copyright 1984 by Microsoft
COMMAND version 1.08
A>
```

So the disk is genuinely bootable MSX-DOS 1.03 / COMMAND 1.08 — the authoritative Tier-2
reference, and it's the same image already recorded as the BDOS oracle (`test.dsk`; see
the `msxdos-oracle-disk` note). The spike used a `/tmp/dostest.dsk` copy; the build session
should drive the durable `test.dsk` (on a `/tmp` working copy, never mutating the original
— see the test-disk-mutation gotcha).

**The gap — CONFIRMED, and precisely located.** Booting that *same* disk on the Tier-1
machine `National_CF-3300_ZEROBASDISK` (real CF-3300 BIOS, zerobas-disk in slot 3-1)
**falls through to BASIC**, not DOS:

```
MSX BASIC version 1.0   Copyright 1983 by Microsoft   28815 Bytes free   Ok
```

…even though `H.PHYD ($FFA7)` reads back `F7 87 10 40 C9` after the cold boot — i.e.
zerobas-disk's INIT *did* run and *did* install the hook. The real BIOS then has **no boot
procedure in our ROM to invoke**, so it proceeds to BASIC. This is the entire Tier-2
deliverable in one sentence: **zerobas-disk installs the hook but never reads the boot
sector or chainloads the DOS.** (Harness used: `disk/docs/` probe pattern — boot the
machine on a `/tmp` copy, `debug read_block VRAM 0x1800 768` for the SCREEN1 name table,
`debug read_block memory 0xFFA7 5` for the hook bytes.)

### What "DOS-boot support" actually requires (scope, to pin in the build session)
The standard MSX disk-ROM boot is **not** "implement MSXDOS.SYS's loader" — that loader is
the **boot-sector code on the DOS disk itself**. zerobas-disk's job is the small bridge
that hands control to it. Per the MSX disk-boot sequence (MSX2 TH ch.3 / MSX Assembly Page
— allowed sources; the exact entry-condition contract is the first thing to pin, ideally
cross-checked by a black-box trace of *where* the stock CF-3300 disk ROM reads sector 0 and
jumps):

1. **Read the boot sector** (logical sector 0 of drive A) into **`$C000`** via our own
   DSKIO.
2. **Hand off to the boot code** — set up the documented entry conditions and **`JP $C01E`**
   (the boot sector's executable entry); if the disk is non-bootable / has no `MSXDOS.SYS`,
   the boot code returns and BASIC starts (so the fall-through must stay graceful — exactly
   today's behaviour for a blank disk).
3. **Satisfy what the boot code + MSXDOS.SYS call** — they drive the drive through the
   standard BIOS surface we already provide: DSKIO (`$4010`, via the hook), GETDPB
   (`$4016`), DRIVES, etc. **This is where GETDPB finally gets its first *organic*
   consumer** — the whole reason Tier 2 is the strongest provider evidence.

### Proposed slices (each independently observable)
- **2-Tier2-a — boot bridge.** Add the read-sector-0 + `JP $C01E` boot path to
  zerobas-disk's INIT (or the standard boot hook). Oracle: the Tier-1 machine now reaches
  `MSX-DOS version 1.03 … A>` on `dostest.dsk`, byte-for-byte screen-identical to the stock
  CF-3300 reference above. Graceful fall-through to BASIC on a blank disk preserved.
- **2-Tier2-b — organic GETDPB + FS surface.** With DOS up, exercise a real DOS command
  that mounts/uses the drive (`DIR`, a file copy) and confirm it routes through our GETDPB
  + DSKIO + dir/FAT — the organic consumer the differential could only approximate. Trap
  `$4016` to prove GETDPB is hit by real DOS code, not a probe stub.
- **2-Tier2-c — regression.** Fold the boot-bridge logic into the host unit-test layer
  where it's emulator-testable (sector-0 read + the handoff setup), and pin the A> screen
  in a sibling `disk_probe_provider_dosboot.py`.

**Risk to resolve first in the build session:** the precise boot entry-condition contract
(register/work-area state `$C01E` expects, and whether the boot is driven from INIT
directly or via a standard boot hook like `H.STKE`/the boot procedure vector). The TH
documents the sequence; a black-box BP trace on the stock CF-3300 (where does it read
sector 0, what's in registers at the `$C01E` jump) is the clean-room way to confirm it —
never reading the CF-3300 ROM bytes. Everything else (DSKIO/GETDPB/DRIVES) already ships.

## 8. Boot-sequence depth finding (2026-06-22) — the boot is steps 4–7, not a one-call bridge

A first build attempt (a boot bridge in INIT: read sector 0 → `CALL $C01E` with CY reset)
was written, validated, and then **reverted** — it proved the *mechanism* but also proved
it is **insufficient**, which is the useful result. What we learned (and the corrected
scope for 2-Tier2-a):

**Empirical (Tier-1 machine, BP trace).** The bridge ran correctly: sector 0 landed at
`$C000` (`EB FE 90 "NMS…"`), the `$EB` signature matched, and `$C01E` was reached with
**carry reset** (`AF=0044`). The boot code nonetheless **returned** (machine fell through
to `MSX BASIC 1.0`), even after the entry registers were made to match the stock CF-3300
`$C01E` snapshot (`DE=$F368 HL=$F323 IX=$6050 IY=$0314`). So the gap is **not** the
register values.

**Authoritative (MSX2 TH ch.3, numbered boot steps — allowed source).** The disk boot is a
**four-step environment hand-off**, and `$C01E` is called **twice**:
- **Step 4** — read sector 0 → `$C000`; on error or first byte ∉ {`$EB`,`$E9`} → DISK-BASIC.
- **Step 5** — `CALL $C01E` with **CY reset**: the "custom boot program" entry; the data-disk
  default is `RET NC`, so a non-system disk returns here → BASIC.
- **Step 6** — **prepare the MSX-DOS environment**: switch RAM into page 0 and set up the
  page-0 BDOS / jump vectors (`$0005` etc.) that the boot code and `MSXDOS.SYS` use.
- **Step 7** — `CALL $C01E` with **CY set**: the boot code now loads `MSXDOS.SYS` at `$0100`
  and jumps in; **Step 8** loads `COMMAND.COM`. `H.STKE ($FEDA)` governs the DOS-vs-BASIC
  decision.

So the first attempt implemented steps 4–5 only. **The real work in 2-Tier2-a is step 6**
— a genuine subsystem (RAM-into-page-0 paging + the page-0 DOS environment + the second
`$C01E` call with CY set), not a thin bridge. DSKIO/GETDPB/DRIVES still suffice for the
*sector* surface, but the *page-0 DOS environment* is new code zerobas-disk does not have.

**Revised 2-Tier2-a plan:**
1. Reinstate the proven steps 4–5 (read sector 0, `CALL $C01E` CY-reset; the data-disk
   `RET NC` fall-through is preserved). Keep it minimal — drop the speculative register
   replication (the trace showed it doesn't matter).
2. Implement **step 6**: pin, from TH ch.3 + a black-box trace of the stock CF-3300's
   page-0 state just before its CY-set `$C01E` call, exactly what must be in page 0 (RAM
   switched in; which `$00xx` vectors hold what — `$0005` BDOS, the disk work-area hooks).
   This is the new subsystem; budget it as its own sub-slice (**2-Tier2-a2**).
3. **Step 7**: `CALL $C01E` with CY set; validate the Tier-1 machine reaches
   `MSX-DOS version 1.03 … A>` screen-identical to the stock reference.
4. **Regression gate (do this when reinstating step 4–5):** the boot bridge runs in INIT on
   *every* host, including the `C-BIOS_MSX1_*_BASIC_DISK` machines the whole probe suite
   boots with `test720.dsk`. Confirm those still bring up zerobas-BASIC (the data-disk
   `RET NC` path must stay transparent) before relying on it.

Net: Tier-2 is bigger than first scoped — the boot bridge is the easy 20%; the page-0
MSX-DOS environment (step 6) is the 80%. Still GO, but it's a multi-slice subsystem.

## 8.1 Step 6 design (slice 2-Tier2-a2) — the page-0 MSX-DOS environment

Pinned 2026-06-22 from MSX2 TH ch.3 (the documented page-0 layout — allowed source) and a
black-box trace of the stock CF-3300 at *both* `$C01E` calls. **Clean-room boundary:** the
environment is built from the DOCUMENTED CP/M-style layout + our own `bdos_entry`; we do
NOT read or replicate the CF-3300's resident kernel code (the `$DDxx` bytes its page-0
vectors point at are reference disk-ROM code — off-limits). The trace is used only to
confirm the *shape* (which page-0 cells change, RAM-vs-ROM), never to copy code.

**What the trace showed (the step-5 → step-7 delta):**
- **Step 5 entry** (CY reset): `$0000 = F3 C3 D7 02…` — **ROM BIOS is in page 0**.
- **Step 7 entry** (CY set): `$0000 = 00 00 …` — **RAM is in page 0** (zeroed), with the
  interrupt vector `$0038 = C3 AE DD` (`JP $DDAE`) and `$000C = JP $DDF3` pointing at a
  resident kernel in high RAM. `$0005` (BDOS) is **still 0** at step-7 entry.
- ⇒ The one structural fact we take: **step 6 switches RAM into page 0 and installs the
  interrupt + resident-entry vectors before the CY-set call.** (We build the *contents*
  from docs, not from `$DDxx`.)

**The documented target page-0 environment (TH ch.3 / standard MSX-DOS = CP/M-style):**
- `$0000` warm-boot entry; `$0005` BDOS entry (CALL with the function in C);
  `$0006-0007` = top of TPA; `$0038` maskable-interrupt vector;
  `$005C`/`$006C` default FCBs; `$0080` default DMA (128-byte disk transfer area).

**The big reuse insight:** zerobas-disk already ships `bdos_entry` — a CP/M-compatible FCB
BDOS (Open/Read/SetDTA/…), oracle-validated byte-identical to MSX-DOS 1 (`disk_probe_bdos.py`).
That is exactly the resident BDOS the boot needs. So step 6 should wire **`$0005` → a page-0
trampoline that inter-slot-CALLs our `bdos_entry`** (slot from the INIT scan, address from
the published `SYSTEM $F37D` vector), rather than build a new BDOS.

**Implementation prerequisites (a2), in order:**
1. **RAM into page 0.** Page 0 is currently the main-BIOS ROM; the boot needs RAM there.
   Pin the slot/subslot paging that puts RAM in page 0 for the Tier-1 config (TH §2 slot
   model; `ENASLT`/`PUT_P0`/the slot registers). This is the fiddly, hang-prone part —
   validate it in isolation (switch RAM in, read `$0000` back as RAM, switch BIOS back).
2. **Lay the page-0 environment** per the documented layout: `$0000` warm-boot stub,
   `$0005` → `bdos_entry` trampoline, `$0006-7` = TPA top, `$0038` int vector, `$0080` DMA.
3. **Two-phase `$C01E`:** step 5 `CALL $C01E` CY-reset (already proven), then build the
   env, then step 7 `CALL $C01E` CY-set.

**Open question to resolve first (by experiment, clean-room):** exactly how the boot-sector
code loads `MSXDOS.SYS` once entered with CY set — via `$0005` BDOS Open/Read (so wiring
`$0005 → bdos_entry` suffices), or via direct `PHYDIO`/`DSKIO` sector reads (so the env need
only page RAM in + set vectors). The trace shows `$0005 = 0` at step-7 *entry*, so either the
boot code sets `$0005` itself or it reads sectors directly. Resolve by building the minimal
env + wiring `$0005 → bdos_entry` and observing whether `MSXDOS.SYS` lands at `$0100` — do
**not** trace into the boot-sector code to find out (it is Microsoft MSX-DOS code).

## 8.2 Prerequisite (1) VALIDATED — RAM-into-page-0 paging works

The hang-prone sub-step is **proven** (2026-06-22, black-box). The Tier-1 machine's slot map
(from its config): page 0 = slot 0 (BIOS/BASIC ROM); **slot 3 is expanded** with **3-0 =
64 KB Main RAM** and **3-1 = our disk ROM** (pages 1-2); page 3 (stack + `$FFFF`) = slot 3-0.
So "RAM in page 0" = map page 0 → **slot 3-0**, an *expanded* slot, so both `$A8` (primary)
and `$FFFF` (secondary) must move — while leaving page 1 (our running code) and page 3 (the
stack and the `$FFFF` register itself) untouched. BIOS `ENASLT` can't do it (it lives in
page 0, which vanishes mid-switch), so we drive the slot ports directly from our page-1 code:

```
        ; --- map RAM (slot 3-0) into page 0; runs from page 1 ----------------
        in   a,($A8)      ; primary slot config
        ld   (saved_a8),a
        ld   a,($FFFF)    ; slot-3 secondary reg (reads inverted)...
        cpl               ; ...so complement to get the live value
        ld   (saved_sec),a
        in   a,($A8) : or  $03 : out ($A8),a     ; page-0 primary bits -> slot 3
        ld   a,(saved_sec) : and $FC : ld ($FFFF),a   ; page-0 subslot bits -> 0 (RAM)
        ; ... page 0 is now RAM ...
        ; restore: ld a,(saved_sec)/ld ($FFFF),a ; ld a,(saved_a8)/out ($A8),a
```

Key correctness points, all confirmed by an injected page-3 stub run on the live machine
(markers read back): writing `$A5` to `$0000` after the switch reads back **`$A5`** (RAM is
live in page 0); after restore `$0000` reads **`$F3`** (the BIOS `DI` opcode — ROM is back).
The captured `$A8 = $F0` and slot-3 secondary `= $00` (during BASIC) match the map exactly.
The routine **reads the current config and only rewrites the page-0 bits**, so it adapts to
the boot context too (during INIT our ROM is in page 1, i.e. slot-3 secondary has bits 2-3 =
1 — preserved by the `and $FC`). Must run with **interrupts disabled** (`di`): while page 0
is RAM the `$0038` vector is not yet the BIOS handler. This is the proven foundation for
a2 step (2); the remaining work is laying the page-0 environment on top + the two-phase call.

## 8.3 Open question RESOLVED — boot loads MSXDOS.SYS by *sector reads*, not BDOS

Black-box experiment on the stock CF-3300 (2026-06-22): BP at `$C01E` armed after the 2nd
(CY-set) hit, then BP at `$0005` logging the caller of each BDOS call. The first six `$0005`
calls all came from **high page-3 RAM** (`$C23B`, `$C24E`, `$CBFF`, `$CC04`, `$CE5C`…) with
function codes `01/24/0D/53/75` — that is **MSXDOS.SYS already relocated and running**, not
the boot sector (`$C000..$C0FF`), and not an Open+Read file-load sequence. ⇒ **MSXDOS.SYS is
already loaded before the first BDOS call**, so the boot sector loads it by **direct sector
reads (PHYDIO-class), not `$0005` BDOS.** Consequence: **no resident BDOS / TPA / `$0006-7`
layout is needed for the load** — that whole axis of complexity is off the table.

## 8.4 The actual core of step 6 — a RAM-resident inter-slot path (the real 80%)

Resolving 8.3 exposes the true hard part. With **RAM switched into page 0**, every page-0
BIOS routine is gone — including the inter-slot primitives `RST 30h`/CALLF (`$0030`) and
`CALSLT` (`$001C`). But our provider hook **`H.PHYD ($FFA7) = F7 87 10 40 C9` is exactly a
`RST 30h` (CALLF) to slot 3-1 `$4010`** — so with RAM in page 0, `H.PHYD` **breaks** (the
`RST 30h` lands in RAM garbage at `$0030`). That is why the stock disk ROM builds a resident
kernel in high RAM and points the page-0 vectors at it (`$0038→$DDAE`, `$000C→$DDF3`,
observed in §8.1): step 6 is really *"stand up a minimal RAM-resident BIOS-call environment
so the disk driver stays reachable after RAM replaces the page-0 ROM."*

**Our advantage (a real simplification):** during the boot **page 1 stays our disk ROM**
(slot 3-1, never remapped), so our **DSKIO is directly `CALL $4010`-able with no inter-slot
mechanism at all**. So step 6 does NOT need a full CALLF/CALSLT reimplementation — it needs
just enough RAM page-0 environment that the boot sector's sector-read path reaches `$4010`.
Two candidate designs to try (experiment, cheapest first):
1. **Tiny `$0030` CALLF shim in RAM page 0.** Put a handler at `$0030` that emulates CALLF
   for the one case we need — read the inline slot+addr after the `RST`, and (since the
   target slot 3-1 is already in page 1) just `CALL`/`JP` the inline address — so the
   existing `H.PHYD` chain keeps working unmodified. Smallest change; keeps the standard hook.
2. **Resident driver vector.** Lay the documented page-0 vectors the boot/`MSXDOS.SYS` expect
   (`$0038` int → a safe RAM handler, the disk-driver entry where the boot code looks) such
   that sector I/O routes to our `$4010` directly.
Resolve which the boot sector actually uses by building (1) — minimal RAM `$0030` shim +
the validated paging + the two-phase `$C01E` — and observing whether `MSXDOS.SYS` lands and
`A>` appears; if the boot reaches for a vector we didn't set, the trace will show the address
(a clean-room signal — never read the boot-sector code). **Net:** step 6 shrank on one axis
(no BDOS/TPA) and sharpened on another (a RAM-resident `RST 30h`/driver path); the next build
turn implements design (1).
