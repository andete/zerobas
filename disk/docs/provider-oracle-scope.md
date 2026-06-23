<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
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
Harness: `probes/disk/disk_probe_provider_phydio.py`. **Tier 2** (a real
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
2. **Harness.** A probe (sibling `probes/disk/disk_probe_provider_phydio.py`) that:
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
is compatible with a permissively-licensed (0BSD) reimplementation; black-box *runtime* use is always fine. None
of this is in scope now — DOS1 is the ceiling.

## 7. DOS-boot feasibility spike (2026-06-22) — GO, gap pinned

Tier 2 was de-risked with a black-box spike before committing to the boot-loader build.
Both gating prerequisites were checked empirically.

**Prerequisite (b) — a real MSX-DOS 1 system disk — SATISFIED (permanent disk on hand).**
A local MSX-DOS 1 system disk (`test.dsk`, 720 KB, OEM "NMS 8245") holds
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
        ; --- map whatever slot is in page 3 (always RAM) into page 0 ---------
        ; Runs from page 1. DERIVES the RAM slot from page 3 — never hardcode
        ; slot 3-0 (that was the §8.5 gap B host-portability bug).
        di
        in   a,($A8)      ; primary slot config
        ld   (saved_a8),a
        ld   a,($FFFF)    ; slot secondary reg (reads inverted)...
        cpl               ; ...so complement to get the live value
        ld   (saved_sec),a
        ; page-0 primary := page-3 primary   ($A8 bits 7-6 -> bits 1-0)
        ld   a,(saved_a8) : and %11000000 : rlca : rlca : ld c,a
        ld   a,(saved_a8) : and %11111100 : or  c : out ($A8),a
        ; page-0 subslot := page-3 subslot   ($FFFF bits 7-6 -> bits 1-0)
        ld   a,(saved_sec) : and %11000000 : rlca : rlca : ld c,a
        ld   a,(saved_sec) : and %11111100 : or  c : ld ($FFFF),a
        ; ... page 0 is now RAM (page-3's slot+subslot) ...
        ; restore: ld a,(saved_sec)/ld ($FFFF),a ; ld a,(saved_a8)/out ($A8),a
```

Key correctness points, all confirmed by an injected page-3 stub run on the live machine
(markers read back): writing `$A5` to `$0000` after the switch reads back **`$A5`** (RAM is
live in page 0); after restore `$0000` reads **`$F3`** (the BIOS `DI` opcode — ROM is back).
The captured `$A8 = $F0` and slot-3 secondary `= $00` (during BASIC) match the map exactly.
The routine **reads the current config and copies page 3's slot/subslot into the page-0
field** — and page 3 is *always* RAM (the stack lives there), so this is host-portable: it
preserves pages 1-3 (during INIT our ROM is in page 1) and never assumes a fixed RAM slot.
On the Tier-1 map this evaluates identically to the original `or $03` / `and $FC` sketch
(page 3 = slot 3-0 there, so the derivation yields slot 3-0) — so it inherits this section's
validation — while adapting on a host whose RAM is elsewhere. (The first sketch *hardcoded*
slot 3-0; that was the §8.5 gap B bug, corrected in the listing above.) Must run with
**interrupts disabled** (`di`): while page 0 is RAM the `$0038` vector is not yet the BIOS
handler. This is the proven foundation for a2 step (2); the remaining work is laying the
page-0 environment on top + the two-phase call.

**Derived (gap-B) version now validated in-tree (2026-06-22).** `page0_ram_in` /
`page0_ram_out` in `disk.asm` (the host-adaptive form above) were self-tested on
**`C-BIOS_MSX1_BASIC_DISK`** — the host whose RAM is *not* slot 3-0, where the hardcoded
`or $03` / `and $FC` version hung. After `page0_ram_in`, `$0000` accepts a written `$A5`
(RAM is live in page 0); after `page0_ram_out`, `$0000` reads back `$F3` (the C-BIOS `DI`
opcode — BIOS ROM restored), with the machine still running (PC `$11A0`, not wedged). So gap
B is **validated**, not merely design-resolved. The routines are committed (uncalled for now);
step 6 wires them in next.

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

## 8.5 First full build attempt (2026-06-22) — DOS path RUNS, two concrete gaps found

Design (1) was built end-to-end in `disk.asm` (read sector 0 → step-5 CY-reset `$C01E` →
switch RAM into page 0 → lay `$0030` CALLF shim + `$0038` int stub → step-7 CY-set `$C01E`),
**validated, and reverted.** It is the biggest jump yet and pinned exactly what remains.

**Major progress — the DOS boot path now executes.** Flow trace on the Tier-1 machine with
the real DOS disk: step 5 `$C01E` CY=0 (A8=`$FC`); step 7 `$C01E` CY=1 with **A8=`$FF`** (RAM
switched into page 0, env laid) — both calls reached, in order, with the right carry. The
screen changed from **"MSX BASIC version 1.0"** (the old fall-through) to **"MSX system
version 1.0 — Copyright 1983 by Microsoft"**, and the CPU is *running code in page-0 RAM*
(PC samples `$2677/$0EAD/$1983`). So the boot code ran the DOS path far enough to print and
execute — not the BASIC fall-through.

**Gap A — the boot reads the disk by a vector that is NOT H.PHYD.** Breakpoint counters over
the whole boot: **DSKIO (`$4010`) = 0, H.PHYD (`$FFA7`) = 0.** The boot code never used our
hook, then hung in a 1-instruction loop at **`$1418`** with **A8=`$03`** (it had reshuffled
the slots). So "design 1" (keep H.PHYD alive with a `$0030` CALLF shim) is **insufficient**:
the MSX-DOS 1 boot code locates the sector driver some other way — most likely a **disk
work-area routine pointer** the full step-6 installs (the stock's resident kernel: page-0
vectors `$000C→$DDF3`, `$0038→$DDAE` seen in §8.1 point into it). Next: identify *which*
address the boot reaches for (black-box: trace the boot's first post-step-7 disk access
target — never read its code) and provide a resident driver entry there that routes to our
`$4010`. The `$0030` CALLF shim itself worked structurally and is reusable.

**Gap B — the paging hardcodes the RAM slot (host-specific bug). RESOLVED (design).** The
build used `in a,($A8) : or $03` / `and $FC`, i.e. it hardcodes "RAM = slot 3-0" — true on the
CF-3300 but **not portable**. Regression check: Tier-1 + a *data* disk still fell through to
BASIC fine (slot 3 IS RAM there), but **`C-BIOS_MSX1_EU_BASIC_DISK` + a data disk hung at
C-BIOS init** — boot_disk runs in every host's INIT, and on a host whose RAM is not slot 3-0
the hardcoded switch maps the wrong slot into page 0 and wedges startup. **Fix (now pinned in
§8.2):** derive the RAM slot dynamically — copy page 3's primary-slot bits (`$A8` bits 7-6)
into the page-0 bits, and page 3's subslot (`$FFFF` bits 7-6) into the page-0 subslot — i.e.
"put whatever slot is in page 3 (always RAM) into page 0." The corrected §8.2 listing carries
this derivation; it is provably equivalent to the validated `or $03` / `and $FC` on Tier-1
(page 3 = slot 3-0 ⇒ derivation yields slot 3-0) and adapts elsewhere, so it removes the
host-specific assumption. End-to-end emulator re-validation lands with the next a2 build, when
the corrected paging is wired into the boot bridge **together with** the gap-A driver vector
— the bridge can only ship as a whole (it runs in every INIT, so a paging fix alone, with the
boot still hanging at gap A, is not independently committable as code).

**Status:** the DOS boot path is proven to run on our stack. Gap **B (RAM-slot derivation) is
resolved at the design level** (§8.2). Gap **A is now characterised** (§8.6): the boot's sector
driver is the **standard DSKIO (`$4010`)** — our build just hung *before* reaching it for want
of a fuller page-0 vector set. **a1 (steps 4-5) is now reinstated + committed in `disk.asm`**
(`boot_disk`, regression-gated — see TODO 2-Tier2-a1); a2 step 6 (the page-0 environment) is
the next build, on top of it.

## 8.6 Gap A characterised — the working boot uses standard DSKIO (`$4010`)

Black-box reference trace on the genuine **National CF-3300** booting a real MSX-DOS 1 system
disk (a `/tmp` copy — never the permanent image), 2026-06-22, via
`probes/disk/disk_probe_dosboot_trace.py`. Strictly oracle observation:
CPU breakpoints on the **documented** disk-ROM jump-table entries + a page-0 RAM dump; no kernel
code read or disassembled.

**Counters over boot+settle:** DSKIO `$4010` = **5**, DSKCHG `$4013` = 1, GETDPB `$4016` = 1,
PHYDIO `$0144` = 2. ⇒ the working MSX-DOS-1 boot **reaches the standard disk-ROM driver** — the
sector path *is* `$4010` DSKIO, not a bespoke vector.

**Page-0 environment shape at settle:** a *full* resident `JP`-vector table — live `JP` cells at
`$000C`, `$001C` (CALSLT), `$0024`, `$0030` (the RST 30h / CALLF handler) and `$0038` (int → the
resident kernel), corroborating §8.1. The targets (`$DDxx`/`$DExx`) are the kernel's own and stay
**opaque** — we record only which cells are live vectors (the env *shape*), never the bytes
behind them.

**This corrects the §8.5 gap-A inference.** §8.5 read "our build's `$4010` = 0, H.PHYD = 0" as
"the boot avoids `$4010`." The reference shows the opposite: the boot **does** use `$4010` — our
build simply **hung at `$1418` before the DSKIO call**, because it first dereferenced a page-0
vector our *minimal* env (`$0030` shim + `$0038` stub only) did not install. The driver was never
the problem; the **incomplete page-0 vector set** is.

**Sharpened gap-A direction.** Lay the fuller page-0 vector set the boot expects (shape per TH
ch.3; targets are our *own* RAM handlers, not the kernel's), routing the disk path through the
`$0030` CALLF handler to our DSKIO. Because our disk ROM stays in page 1 throughout, that handler
reaches `$4010` with a **direct `CALL` — no inter-slot mechanism needed**. The residual unknown
shrinks to *which* page-0 vector the boot hits at `$1418`; with the destination now known to be
the standard driver, the next a2 build re-runs the bridge with a trap on the unlaid vectors to
pin it.

## 8.7 Step-6 BUILT + regression-green; a3 trap REFUTES the inter-slot premise

**Step 6 is implemented and committed** (`disk.asm`): the `$0030` RST 30h / CALLF handler (it
saves the caller's registers to page-3 scratch, reads the inline CALLF operand off the stack, and
arranges the stack so a plain `ret` lands in the target — `$4010` DSKIO — with **A/B/C/DE/HL and
the carry flag all preserved**, the target's own RET falling on the byte after the operand); the
`lay_page0_env` JP-vector table (`$000C` RDSLT / `$0014` WRSLT / `$001C` CALSLT / `$0024` ENASLT /
`$0030` CALLF / `$0038` int → our own page-1 handlers); and the step-6/7 wiring in `boot_disk`
(`di` → `page0_ram_in` → `lay_page0_env` → `scf` → step-7 `$C01E` → on a data-disk return,
`page0_ram_out` → `ei` → BASIC). **Regression-green:** `disk_probe_files` + `disk_probe_bload_disk`
PASS on `C-BIOS_MSX1_BASIC_DISK` (sig `$EB`, `$1E` stub `D0 C9` — so step 6's paging *does* run on
that host), and `disk_probe_init` PASS (`SYSTEM $F37D = $439F`, the new `bdos_entry`).

**The a3 trap on `National_CF-3300_ZEROBASDISK` (real DOS disk, /tmp copy) REFUTES the whole
inter-slot-vector premise of §8.4/§8.6.** Black-box (`set_bp` counters, PC sampling, `$A8`/`$FFFF`
watchpoints):
- **Env verified correct at step-7 entry**: page-0 cells hold exactly our JPs (`$000C→rdslt_h`,
  `$001C→calslt_h`, `$0024→enaslt_h`, `$0030→callf_body`, `$0038→int_h`), RAM in page 0
  (`$FFFF`=`fb`→page-0 subslot 0 = slot 3-0 RAM), boot sector at `$C000`. So the build does exactly
  what step 6 specified. Both `$C01E` calls reached (count 2).
- **But the boot uses NONE of it.** Over the whole boot: `callf_body`=0, `rdslt_h`/`calslt_h`/
  `enaslt_h`=0, **DSKIO `$4010`=0, H.PHYD `$FFA7`=0, our ROM header `$4000`=0** (the boot never
  even looks at our disk ROM). Instead it relocates code into **page-0 RAM (`$02xx`)** and **page-3
  RAM (`$F380`)** and **scans slots by writing `$A8`/`$FFFF` directly** (`$FFFF` cycles subslots
  `00/10/20/30` then `00/40/80/C0` — a full primary+secondary sweep). The sweep maps **page 3**
  (stack + work area) to a slot that reads `$FF`, loses the stack, and the CPU wedges in a 1-insn
  loop at **`$0038`** (`$FF` = `RST 38h`). (`int_h` fired once first — DOS had `EI`'d.)
- ⇒ **MSX-DOS 1's boot/MSXDOS.SYS does NOT reach the driver through H.PHYD or the page-0 inter-slot
  primitives.** It expects the **standard disk WORK AREA** — `DRVTBL` + the per-drive driver
  slot/entry the real disk ROM's INIT/boot installs (MSX2 TH ch.3) — and, finding it absent, falls
  back to a destructive slot scan that the **expanded slot 3** (3-0 RAM / 3-1 our ROM) wedges.

**Reframed a3 (next build).** The remaining gap is **not** a richer page-0 inter-slot env — it is
the **disk work area**. zerobas-disk's INIT must populate the documented MSX disk work area so the
DOS boot locates the driver *without scanning*: the master disk-ROM slot, the drive count, and
`DRVTBL`/the per-drive driver entry (slot + `$4010`), per MSX2 TH ch.3 (allowed source; the
CF-3300 kernel's own layout stays opaque). The §8.4 "design 1" assumption (boot drives the disk
through H.PHYD → `$0030` CALLF → `$4010`) is **empirically false on this machine** and is retired;
the `$0030` handler + vector set stay laid (cheap, documented-shape, harmless, and possibly used by
a later DOS phase) but are no longer the load-bearing path. The step-6 env + paging are kept as the
validated foundation; a3 grows the work-area driver table on top, then re-traps.

## 8.8 a3 differential SIZES the gap — it is the disk ROM's full resident DOS kernel

A clean-room black-box **differential** (read RAM state on both machines — never ROM/kernel code)
settles what "the disk work area" actually entails, and it is far larger than a driver pointer.

**Method.** Boot the stock `National_CF-3300` (real disk ROM) and our `National_CF-3300_ZEROBASDISK`
(zerobas-disk), each on a /tmp copy of the same disk; dump page-3 RAM and diff. Two runs: (a) a
DATA disk (both reach Disk BASIC — a confound-free baseline), (b) the DOS disk (the stock reaches
`A>`). Both machines run the **same real CF-3300 main BIOS**, so every diff isolates what the
**disk ROM** sets up that zerobas-disk does not.

**Baseline result (data disk → BASIC, the decisive one).**
| work-area cell | stock CF-3300 | Tier-1 (zerobas-disk) | who sets it |
|---|---|---|---|
| `EXPTBL $FCC1-4` | `00 00 00 80` | `00 00 00 80` | **base BIOS** (identical) |
| `RAMAD0-3 $F341-4` (RAM slot per page) | `83 00 83 83` | **`FF FF FF FF`** | **disk ROM** (absent in ours) |
| `$F348..$F357` (disk work area / DRVTBL) | `87 93 DF 00 00 95 EF 95 ED 95 EB …` | **all `FF`** | **disk ROM** (absent in ours) |
| `SYSTEM $F37D` | `C3 31 F3` (`JP $F331`) | `9F 43` (`$439F`) | both, but different *form* |

So the **base BIOS sets only `EXPTBL`**; **RAMAD0-3 and the whole `$F348` disk work area are the
disk ROM's job**, and zerobas-disk installs neither. (`SYSTEM $F37D` is also telling: the stock
writes a `JP` there — `$F37D` is a *jump-table slot* in the disk environment — whereas our INIT
writes a bare BDOS address. zerobas's internal loader reads it as an address; real DOS expects the
jump table. The two uses coexist today only because nothing foreign reads our `$F37D`.)

**What the `$F348` table points at — the killer detail.** Its entries are `$95xx` (page 2) and
`$DFxx` (page 3) — **high-RAM addresses, not the disk ROM's page-1 window**. The DOS-disk run
corroborates: by its (early, post-DOS-load) capture the stock has DPBs in RAM
(`F9 00 02 0F 04 01 02 01 00 02 70 0E 00 CA 02 03 07 00`, the very bytes our GETDPB returns), the
MSX-DOS device table (`… PRN  LST  NUL  AUX  CON`), and a hook table across `$FE80-$FF00`/`$FFAC`
full of `F7 87 <addr>` CALLFs into both the disk ROM (`$60xx-$73xx`) and the high-RAM kernel. ⇒
the stock disk ROM **relocates a resident DOS kernel into high RAM at boot** and builds RAMAD +
the `$F348` work area + the `$FE/$FF` hook table + per-drive DPBs + the device table to point into
it. That resident kernel — reached via those `$95xx/$DFxx/$60xx` vectors — is exactly the
proprietary code the clean-room rule forbids reading, and providing *our own* equivalents would
require knowing each vector's precise runtime contract (i.e. reverse-engineering that kernel).

**Conclusion — the DOS-boot gap is a charter-level subsystem, and it abuts the clean-room wall.**
This is the §1 circularity finding made concrete: "boot real MSX-DOS off zerobas-disk" = **build
the disk ROM's full resident DOS kernel + its RAM environment** (relocated kernel, RAMAD0-3,
`$F348` DRVTBL/jump table, the `$FE/$FF` DOS hook set, per-drive DPBs, the device table), not a
boot bridge or a page-0 vector set. Much of it is defined only by the stock kernel's own code
(opaque), so a faithful clean-room reproduction needs the documented contracts for each piece
(MSX2 TH ch.3 + MSX-DOS 1 structure docs as allowed sources) and is a multi-slice Phase-2+ effort
on its own — materially bigger than the entire Disk-BASIC verb surface that closed Phase 2.

**Recommendation.** Treat the Tier-2 *DOS-boot* oracle as a **scoping decision** rather than a
keep-iterating item. The provider contract is already validated to the highest fidelity reachable
without raising the charter: Tier-1 (a real BIOS PHYDIO organically drives our DSKIO) PASSES, and
GETDPB is byte-identical to the CF-3300 differential (§2). What DOS-boot would add — a real DOS
*filesystem* organically consuming GETDPB — is strong but incremental evidence bought at a
charter-level, partly-clean-room-blocked price. Options: **(A) stop here**, recording DOS-boot as
characterized-but-deferred (the step-6 env + a1 bridge stay as the validated partial); **(B)** scope
a dedicated multi-slice "DOS resident environment" sub-track built strictly from MSX2 TH ch.3 +
MSX-DOS-1 structure docs (never the kernel), accepting several sessions and the risk that some
vector contracts are not cleanly documented. No further code shipped pending that decision; nothing
speculative was committed (RAMAD0-3 deliberately NOT set unconditionally — on the C-BIOS hosts the
BIOS already sets them, so writing our own value there would risk the whole regression suite).

**DECISION (2026-06-22): option (A) — characterized-but-deferred.** The Tier-2 *DOS-boot* oracle is
closed as **deferred**: the step-6 page-0 environment + the a1 boot bridge stay in `disk.asm` as the
validated partial (regression-green in every host's INIT), and the gap beyond them is now pinned and
sized (this §8.8) for whenever a future charter raise revisits it. The provider direction is
considered **done at the highest fidelity reachable without raising the charter** — Tier-1 (real BIOS
PHYDIO → our DSKIO, organic) PASSES and GETDPB is byte-identical to the CF-3300 differential (§2),
which §2 already deems sufficient pinning for GETDPB. No DOS-resident-environment sub-track is opened.

> **SUPERSEDED by §8.9 (same day, on user request to continue): §8.8's "charter-level, reconstruct
> the resident kernel" pessimism was WRONG.** A trap-driven slice found the boot drives *our own*
> `bdos_entry`; DOS-boot is far more tractable than §8.8 feared. The deferral is lifted; actively
> iterating.

## 8.9 a3 REOPENED — slice-1 finds (and fixes) the $F37D wedge; boot now drives our BDOS

On the user's "continue", the deferred sub-track was reopened with a **trap-driven incremental**
approach (don't reconstruct the full env — find the *load-bearing* cells empirically, fix one,
re-trap). This immediately overturned §8.8's central fear.

**Slice-1 diagnostic (read-watchpoint on the work area).** After step-7 entry the boot reads
**only `$F37D`/`$F37E`/`$F37F`**, and the reading PC *equals* each address — i.e. it **JUMPs to
`$F37D` and executes it**. It never reads RAMAD (`$F341-4`) at all, so §8.8's RAMAD lead was a red
herring. On the stock `$F37D` = `C3 31 F3` (`JP $F331`); our INIT had written the *raw word*
`9F 43` there (publishing `bdos_entry`), so the CPU executed `9F 43 FF` = `SBC A,A / LD B,E /
RST 38h` → the `$0038` wedge. **`$F37D` is the disk system's BDOS-call JP vector, not an address
word.** A follow-up trap caught the caller: the boot does `CALL $F37D` with **C=`$0F` (BDOS Open
File), DE = an FCB in the boot sector** holding **`MSXDOS  SYS`**. So the boot loads MSXDOS.SYS by
calling BDOS through `$F37D` — and **our `bdos_entry` is an oracle-validated FCB BDOS that handles
exactly `$0F`/`$14`/`$10`/`$1A`**.

**Slice-1 fix (tiny).** INIT now publishes `$F37D` as `JP bdos_entry` (`C3 <addr>`) instead of the
bare word. Safe because zerobas-BASIC's loader no longer reads `$F37D` (Phase 1.5 → DSKIO+own FAT;
`basic/sysvars.inc`). Regression-green: `disk_probe_files` + `disk_probe_bload_disk` +
`disk_probe_init` (now checks the `C3`/JP-target form) PASS on C-BIOS, and `disk_probe_bdos` PASS
(its cross-slot stub reads the entry from the JP target at `$F37E`). `bdos_entry` shifts → `$43A4`.

**Result — the boot now drives our BDOS.** Re-trap: the `$0038` wedge is **gone**; the boot reaches
`bdos_entry` (19×), `bdos_open` (9×), `fat_mount` (9×), runs real FDC sector reads (`fdc_read_phys`
24×), and requests **`MSXDOS  SYS`** by name. **This refutes §8.8 decisively:** the boot does *not*
require us to rebuild the stock's resident kernel — it uses **our own `bdos_entry`** as the resident
BDOS. The "huge work area + relocated kernel" the stock builds is the stock's *internal* way; the
boot's actual *requirement* is the BDOS JP vector + working sector I/O.

**New blocker (slice 2, PINNED to slice 3) — the boot loads MSXDOS.SYS via BDOS `$27`, which we
don't implement.** Logging the BDOS function code (C) at every `bdos_entry` call gave the decisive
pattern: the boot repeats **`Open $0F → SetDTA $1A → RandBlkRead $27`** (tally over a run: `$0F`×9,
`$1A`×4, `$27`×4, then `$09`/`$07`). `fat_find` *does* find `MSXDOS.SYS` (`ff_found`×4, `ff_notfound`=0)
and Open succeeds — but the boot then issues **BDOS `$27` (Random Block Read / RDBLK)** to pull the
file in, and our `bdos_entry` dispatch (`$0F/$10/$14/$15/$16/$1A`) returns `$FF` for `$27`. So every
read fails, the boot retries the `$0F/$1A/$27` loop, and the earlier red herrings — `dskio_err`=7,
`read_sector`=16632, the `$073A` `RST 38h` storm — are all just that retry spin (the FDC reads were
fine; none of the `$0038` hits land in our `$42xx` transfer loop). The trailing `$09` (print string)
/ `$07` (direct console in) are the boot printing after it gives up. ⇒ the gap is **one BDOS
function**, not a kernel: this is the documented FCB-BDOS *position model* meeting its first caller
that needs random/block access (BLOAD/LOAD/RUN, the only prior callers, used `$0F`+`$14` only).

**Slice 3 (next) — implement BDOS `$27` (RDBLK) in `bdos_entry`.** Contract (MSX-DOS 1 / CP/M block
I/O, to pin precisely + validate differentially): `DE` = FCB, `HL` = record count; start record =
the FCB random-record field (`+33…`), record size = FCB `+14` (default 128); read `HL` records from
that position into the DTA (`BDOS_DTA`), updating the random-record field + returning `A` = status
(0 ok / 1 EOF) and `HL` = records read. Build it over the existing FAT iterator + a seek (walk the
cluster chain to the start record); validate byte-identical to real MSX-DOS by extending
`disk_probe_bdos.py` with a `$27` case (the clean-room way — the oracle already differentials
`$0F`/`$14`). `$26` (RDBLK's write twin, WRBLK) and the `$09`/`$07` console funcs may surface next;
re-trap after `$27`.

## 8.10 Slice-3 DONE — `$27` works; MSXDOS.SYS loads byte-perfect + executes (loops on env)

`bdos_rdblk` (`$27`) is implemented in `disk.asm` and **works**. The trap caught the boot's exact
contract: `DE`=FCB, **`HL`=`$3F00`** (read-as-much-as-possible), **record size = FCB+14 = 1**,
random record (FCB+33) = 0, **DTA = `$0100`**. Our `$27` re-primes the file to the start, streams
bytes from `SECTOR_BUF` (refilling via `fat_read_file_sector`), bounds by the true size in
`BDOS_BYTESLEFT`, and returns `HL` = records read / `A` = `$00`/`$01` EOF.

**Validated byte-identical (the strongest check):** the 2432-byte MSXDOS.SYS landed at `$0100`
**byte-for-byte equal to the on-disk file** (`c3 00 02 45 00 4c 00 50 00 53 00 02 01 08 01 13 …` —
MSXDOS.SYS's real entry-vector header; the "interleaved zeros" were the file's own bytes, not a read
bug). Regression-green: `disk_probe_files` + `disk_probe_bload_disk` + `disk_probe_init` PASS on
C-BIOS, and `disk_probe_bdos` PASS (`$27` is inert on C-BIOS — only the DOS-boot path calls it).
`bdos_entry` stays at `$43A4` (new code lands after it). *(TODO: add a `$27` differential case to
`disk_probe_bdos.py` for a positive regression lock; the byte-identical load is the working proof.)*

**The boot now LOADS and EXECUTES MSXDOS.SYS** — `$0100`(=`JP $0200`) and `$0200` are each reached.
**New blocker:** MSXDOS.SYS's resident init **loops** (boot repeats `Open $0F → SetDTA $1A →
RDBLK $27` ~10×, reloading the file). Crucially it makes **no new BDOS calls** at `$0200` — so it is
**not** a missing BDOS function; MSXDOS.SYS runs, performs a non-BDOS **environment check**, finds it
unsatisfied, and returns to the boot loader (which retries). This points squarely back at the §8.8
**work area** (RAMAD0-3 `$F341-4`, the `$F348` disk-work-area/DRVTBL table) that the real disk ROM
installs and we don't — but now we know it precisely: it is what **MSXDOS.SYS's own init reads**, not
a kernel we must rebuild. Next: trap which `$F3xx` work-area cells MSXDOS.SYS reads at `$0200`, and
populate exactly those (clean-room: documented MSX disk work area + the §8.8 differential values),
re-trap toward `A>`.

## 8.11 Slice-4 finding — MSXDOS.SYS init `CALL`s disk-ROM entry `$4030` (the next gap; see §8.12)

The §8.10 "work area" guess was wrong: a read-watchpoint over `$F341-$F3FF` + `$FCC1` after MSXDOS.SYS
starts logged **zero** reads there (only repeated `$F37D` BDOS-vector fetches). MSXDOS.SYS does **not**
read RAMAD / `$F348`. Instead, a black-box CPU breakpoint shows MSXDOS.SYS's init **`CALL`s `$4030`**
in the disk ROM (page 1). Our ROM has no routine at `$4030` — it is 14 bytes into `init` ($4022, the
HPHYD-hook install: `3E 10 32 A9 FF …`), so the call executes INIT fragments and returns garbage,
and the boot loops. `$4030` is a disk-ROM entry **past the six standard ones** (`$4010` DSKIO …
`$401F` MTOFF). So the remaining gap is **one more disk-ROM entry point** the MS DOS kernel requires.

**Clean-room boundary — STOP and decide.** The six standard entries (`$4010-$401F`) are documented
(MSX2 TH ch.3); a seventh at `$4030` is **not** in our sourced material. Its contract is observable
only by **disassembling MSXDOS.SYS** (Microsoft, proprietary) — which the no-disassembly rule
forbids. (During this session's *diagnosis* the boot's MSXDOS.SYS bytes were inspected to locate the
failure; that is black-box fault-finding, but *implementing* `$4030` from that disassembly would
cross the line.) Two clean-room-safe ways forward, neither guaranteed:
1. **Research** whether `$4030` (and the disk-ROM↔MSX-DOS-kernel call interface generally) is
   documented in an *allowed* source (MSX2 TH ch.3 full disk-ROM entry list, the MSX Datapack, the
   open Nextor / MSX-DOS-2.20 driver docs — license permitting). If a documented contract exists,
   implement `$4030` from it. This is the only clean path to `A>`.
2. If `$4030`'s contract is **not** documented anywhere allowed, the DOS-boot oracle is blocked at
   the clean-room wall here — exactly the §8.8 risk, now located at one concrete entry point.

**State banked regardless (huge):** $F37D-JP (§8.9) + BDOS `$27` (§8.10) get a real MSX-DOS-1 boot
to **load MSXDOS.SYS byte-perfect and execute it**, driving our own `bdos_entry`. The gap shrank from
"rebuild the resident kernel" (§8.8) to a single un-sourced disk-ROM entry (`$4030`). All slice work
is regression-green on C-BIOS. Whether to pursue (1) is a scoping/provenance decision.

## 8.12 `$4030` research — NOT a clean-room wall; it is a tooling-access gap (research OPEN)

The research pass (allowed/public docs only; no disassembly) is **not yet conclusive**, and an
earlier draft that called this "the wall" was wrong — corrected here.

**Architecture (settled, from the allowed MSX2 TH ch.3):** *"The DOS kernel … resides in the disk
interface ROM and executes BDOS functions of MSXDOS.SYS. … MSXDOS.SYS is an intermediation which …
passes them to the DOS kernel."* So the BDOS/DOS kernel lives in the disk ROM, and MSXDOS.SYS calls
fixed kernel entries like `$4030`. The TH and komkon `DiskROM1.txt` (both allowed, both readable)
document only `$4010`–`$401F` and **explicitly do not** cover the `$4022`/`$4030` kernel region.

**But `$4030` is very likely DOCUMENTED in an allowed source we simply can't fetch.** The **MSX
Wiki is an allowed source** for this project (PROVENANCE.md already cites it — the slot-in-A INIT
convention; it is public interface documentation, the same category as the listed MSX Assembly Page,
not a disassembly). Web-search snippets of the msx.org **`Disk-ROM_BIOS`** wiki page show it lists
the **`$4022+` kernel entries** and **public kernel symbols `GETSLT`, `GETWRK`, `DIV16`, `ENASLT`** —
and **`GETWRK`** ("get work area", `HL` = a work-area pointer) matches our observed `CALL $4030`
with `HL=$F1C9` exactly. So the contract is plausibly published. The blocker is purely mechanical:
**msx.org returns HTTP 403 to every automated route** (rendered page, `?action=raw`, Wayback). This
is a *tooling-access gap, not a provenance wall.*

**Clean-room line (unchanged):** the msx.org wiki *interface tables* are usable if they describe the
entry (address + name + register convention). What is **off-limits** is the raw disassembly of the
proprietary disk ROM that also exists online (e.g. a GitHub `disk_850902.asm`) — implementing from
that would launder a disassembly, which the no-disassembly rule forbids. So: documentation OK,
disassembly NOT.

**Open question to resolve before any verdict:** read the msx.org `Disk-ROM_BIOS` (and
`Disc_Communication_Area`) pages and check whether `$4030`/`GETWRK` and the surrounding kernel
entries are documented with their calling conventions. If yes → implement `$4030` from that
documentation and re-trap (and be ready for the *next* kernel entry MSXDOS.SYS calls — the TH says
the whole kernel is in-ROM, so reaching `A>` may need a documented chain of entries, the scope of
which the wiki page will reveal). If the wiki only names the symbols without contracts → then, and
only then, is it the wall. Access route TBD: the user opening/pasting those two pages is the direct
unblock; alternatively a non-403 mirror.

**State banked regardless (huge, regression-green):** `$F37D`-JP (§8.9) + BDOS `$27` (§8.10) make a
genuine MSX-DOS-1 disk **load and execute MSXDOS.SYS byte-perfect off zerobas-disk**, driving our own
`bdos_entry`; the gap shrank from §8.8's "rebuild the resident kernel" to one kernel entry, `$4030`.
Those two fixes are kept. The provider direction stays validated to the highest clean-room fidelity
(Tier-1 PHYDIO→DSKIO PASS, GETDPB byte-identical).

**RESOLVED (2026-06-22 provenance tightening) — `$4030` is the wall, by policy.** The allowed-sources
review (README firewall, this date) settled the open question the other way: the **MSX Wiki is now
explicitly NOT an allowed source**, *because* its `$4030`/`GETWRK` knowledge is reverse-engineered
from the proprietary disk-ROM kernel (it appears in no published spec — the TH and komkon
`DiskROM1.txt` both omit the `$4022+` region). So there is **no allowed source for `$4030`'s
contract**, and the GitHub disk-ROM disassembly is forbidden. The DOS-boot oracle is therefore
**characterized-and-walled at `$4030`**: MSX-DOS 1's design puts the BDOS/DOS kernel inside the
proprietary disk ROM, and reaching `A>` would require binary-ABI-cloning it (`$4030` is the first of
N such entries) — which the clean-room charter forbids. Re-defer here, with the large progress banked.
To ever revisit, the charter would have to change, or an **open clean-room MSX-DOS-1 kernel**
reimplementation would have to exist as an allowed PROVENANCE input.

## 8.13 `$4030` RE-OPENED — the §8.12 "wall" conflated *no published doc* with *no allowed method*

**The §8.12 verdict was wrong, and is retracted.** It reasoned: the only clean route to `$4030`'s
contract is a *documented* one; the MSX Wiki is the only candidate and it is RE-derived (off-limits);
therefore walled. That argument silently dropped the method this entire project runs on — **black-box
oracle observation**. The charter's own rule (`DESIGN.md`, `PROVENANCE.md`) is explicit: *"a reference
ROM is only ever an oracle: identical inputs in, observed bytes/edges out."* That is precisely how the
**CF-3300 GETDPB** ($4016, equally undocumented in any published spec) was characterised
**field-for-field byte-identical** and reimplemented as our own clean-room code (§INIT + §DPB). `$4030`
is the *same situation*: an undocumented disk-ROM entry, observable as a black box on the genuine ROM,
reimplementable from the observed input→output contract. Cloning *behaviour* from observation is the
sanctioned clean-room outcome here; cloning *code* from a disassembly (or an RE compilation like the
wiki, hence its exclusion) is what is forbidden. The two are not the same, and §8.12 elided them.

**Method (probe `probes/disk/disk_probe_dosboot_4030.py`).** Boot the genuine **stock**
`National_CF-3300` (its own BASIC + disk ROMs) from a real MSX-DOS 1 disk and trap the *working*
boot's own `CALL $4030`. On entry: snapshot every register, the return address off the stack, and a
window of the disk work-area RAM. Arm a one-shot breakpoint at the return address; on return,
snapshot the output registers + the same RAM windows; diff. **We read only RAM (`$F1xx`) and CPU
registers — never the `$4000–$7FFF` ROM code, never MSXDOS.SYS bytes.** Pure inputs-in / outputs-out.

**First contract captured — deterministic across runs (2026-06-23):**

| | AF | BC | DE | HL | IX | IY | SP |
|---|---|---|---|---|---|---|---|
| **entry** | `0142` | `0980` | `0000` | `F1C9` | `F195` | `C0AB` | `8FFE` |
| **exit**  | `0142` | `0980` | `0000` | **`DD0E`** | `F195` | `C0AB` | `9000` (RET) |

So `$4030`, as called here: **returns a pointer in `HL` (`$F1C9` → `$DD0E`), preserves AF/BC/DE/IX/IY,
and writes nothing in `$F100–$F3FF`.** Caller is page-0 RAM at `$0241` (relocated MSXDOS.SYS).
`$DD0E` is high RAM (currently `$FF` fill — the per-driver work area the disk ROM's INIT reserves
below RAMTOP). Consistent with a "resolve/return the work-area pointer" operation.

**Corroboration the trap is genuinely inside the disk driver:** on entry `IX=$F195` points at
`00 | f9 00 02 0f 04 01 02 01 00 02 70 0e 00 ca 02 03 07 00` — i.e. drive byte `$00` (drive A)
followed by a DPB **byte-identical to our validated CF-3300 GETDPB output** (§DPB). So at the `$4030`
call, `IX` = the current drive's DPB and we are squarely in the disk-driver context, not some
coincidental `$4030` hit.

**Input-domain MAPPED (2026-06-23, `disk_probe_dosboot_4030.py --sweep`).** Same trap, but we now
**inject** controlled inputs at the `$4030` breakpoint (overwrite `HL`/`A` before the routine runs --
controlled-inputs-in, observed-outputs-out, still pure black box) and read the output. Seven vectors:

| injected A | injected HL | → output HL | other reg deltas |
|---|---|---|---|
| (real) | `F1C9` | `DD0E` | none |
| (real) | `C800` | `DD0E` | none |
| (real) | `E000` | `DD0E` | none |
| (real) | `0000` | `DD0E` | none |
| `00` | `F1C9` | `DD0E` | none |
| `01` | `F1C9` | `DD0E` | none |
| `02` | `F1C9` | `DD0E` | none |

**Rule: `$4030` IGNORES `HL` and `A` and returns a CONSTANT pointer (`$DD0E`), preserving
AF/BC/DE/IX/IY.** The simplest possible "get work area" semantics — a fixed work-area base, no inputs.
So our reimplementation is `ld hl,<our own work-area base> / ret` (which preserves AF too).

What remains is **not** the `$4030` contract (settled) but the *next* question: **what MSXDOS.SYS reads
from the returned pointer**, i.e. the work-area layout it expects at `$DD0E+`. We answer that
empirically by implementing `$4030` (returning a pointer to our own RAM) and re-trapping — the boot
will show exactly which offsets it touches. CLEAN-ROOM NOTE for that step: the stock's `$DDxx` region
holds data **and relocated proprietary kernel code** (§8.8: work-area JP targets into `$95xx/$DFxx`),
so we observe *which fields MSXDOS.SYS reads and how it uses them* (a contract we satisfy with our own
values / our own clean handlers), never lifting the bytes behind any vector it calls.

**Next steps (this re-opened track):**
1. **Input-domain mapping (Phase B).** Inject a CALSLT stub that drives `$4030` on the stock CF-3300
   with varied `HL`/`A` and tabulate outputs — same driven-oracle method used to map GETDPB across BPBs.
2. **Reimplement `$4030`** in `disk.asm` from the observed rule (our own work-area RAM, register
   convention matched), regression-gated on C-BIOS as ever.
3. **Re-trap the boot** and watch what MSXDOS.SYS reads from the returned pointer — expect the *next*
   undocumented entry or a work-area field to characterise, and iterate toward `A>`. §8.10 evidence
   (init makes essentially one non-BDOS call) suggests the live surface is small.

The §8.12 "characterized-and-walled / charter change required" framing is withdrawn: `$4030` is
tractable by the project's standard oracle discipline, no charter change needed. Writing our own
MSX-DOS 1 is **not** the plan and never was — existing disks drive our clean-room reimplementation of
the disk ROM's observed entry contract, exactly as they already drive our DSKIO/GETDPB/PHYDIO.

## 8.14 `$4030` IMPLEMENTED — the retry spin breaks; MSXDOS.SYS consumes our work area

`$4030` is now a real disk-ROM entry (`disk.asm`): the six standard entries end at `$401F`, the
`$4022-$402F` kernel slots are `$00` fill (the MSX-DOS-1 boot calls none of them, §8.11), and at
exactly `$4030` we inline the oracle-observed contract — `ld hl,GETWRK_AREA / ret` (returns a fixed
work-area pointer, preserves AF/BC/DE/IX/IY). `GETWRK_AREA` is our own reserved page-3 RAM (`$E780`,
past the RDBLK scratch); we choose the location freely since §8.13 proved `$4030` ignores its inputs.
`bdos_entry` shifted `$43A4→$43B6`; regression-green on `C-BIOS_MSX1_BASIC_DISK` (init/files/bload).

**Re-trap on the Tier-1 machine (real CF-3300 BIOS + zerobas-disk; `disk_probe_dosboot_retrap.py`),
deterministic across runs:**

| metric | pre-fix (§8.10/8.11) | now |
|---|---|---|
| `$4030` calls | landed in INIT garbage | **2** (a real entry) |
| `bdos_open` | ~9 (spin) | **2** |
| `bdos_rdblk` | repeated (reloaded MSXDOS.SYS) | **1** |
| work-area reads at `$E780` | — | **512**, first from MSXDOS.SYS PC `$0368` |
| settle PC | `$0038` loop (missing `$4030`) | `$0038` (new cause) |

**Two clear wins:** (1) the **retry spin collapsed** — MSXDOS.SYS loaded itself **once** (`rdblk=1`,
`open` 9→2) instead of looping, so `$4030` broke the wedge it was stuck on; (2) MSXDOS.SYS **actually
consumes** the pointer `$4030` returned — 512 reads of `$E780`, from its own relocated code at `$0368`.
So the entry is real, called, and used.

**New gap — the work-area LAYOUT.** The boot still ends at `$0038` and no `A>`/banner appears, because
our `$E780` work area is **uninitialised RAM** (the dump is leftover `0039 0039 …`), not the structure
MSXDOS.SYS expects. On the stock CF-3300 the disk ROM's INIT populates `$DD0E+` before the boot reads
it; we return a valid pointer but to empty RAM, so MSXDOS.SYS reads garbage, acts on it, and derails to
`$0038`.

**Next target (next session):** characterise the work-area layout MSXDOS.SYS expects at the returned
pointer. On the stock CF-3300, with a read-watch over `$DD0E+` after `$4030` returns, log *which
offsets* MSXDOS.SYS reads (and from which PC) and *what values* are there — then satisfy those fields
with our own values. CLEAN-ROOM: observe which fields are read and how they are *used* (counts /
pointers / flags = data we supply our own values for); if MSXDOS.SYS *executes* (CALLs/JPs into) a
work-area cell, that target is the proprietary kernel — we provide our own clean handler for the
observed behaviour, never lifting the bytes. Also pin the `$0038` derail (a bad jump computed from the
garbage fields, vs. an interrupt-vector issue) to confirm the layout is the lever.

## 8.15 The `$4030` work area is the disk ROM's RESIDENT RAM ENVIRONMENT (data + std vectors)

Characterising what MSXDOS.SYS does with the `$4030` pointer on the stock CF-3300 (black-box: trap the
consuming PC + execution-sample the region; no ROM/MSXDOS.SYS disassembly):

- `$4030` returns `$DD0E`, which is **offset 14 into the 256-byte page `$DD00–$DDFF`**. MSXDOS.SYS's
  init reads the **whole page** (sequential byte reads via a general routine at PC `$0368`; `$0368` is
  a generic accessor — 16k hits across `$C000–$FFFF`, so it is *not* work-area-specific).
- **The page is MIXED, not pure data.** Execution-sampling every 8 bytes across `$DD00–$DDFF`: the
  lower region is read as **data** (no execution at `$DD0E/$DD20/$DD50`), but the **upper region is
  executed as code** — first execution at `$DDB0` (310 hits in a 13 s boot). This corroborates §8.4's
  independent finding that the stock's resident vectors target this page (`$0038 → $DDAE` interrupt,
  `$000C → $DDF3` inter-slot). So `$DDAE+` is **resident handler code** the disk ROM relocates into
  RAM at boot, and the system runs it (e.g. on every interrupt via `$0038`).

**So `$4030`'s "work area" is the disk ROM's resident RAM environment**: low = DOS/disk work
variables (data), high (`~$DDAE+`) = the resident **interrupt + inter-slot handler vectors/code**.
This is the structure §8.4/§8.8 first glimpsed from the `$F348` side, now reached from the `$4030`
side. Our Tier-1 boot derails at `$0038` precisely because our returned area (`$E780`) carries neither
the work-variable data nor a resident interrupt/inter-slot environment for MSXDOS.SYS to land in.

**CLEAN-ROOM — still tractable, and on the right side of the line.** The *executed* parts are
**standard MSX functions** — interrupt service and `RDSLT/CALSLT/ENASLT` inter-slot calls — whose
behaviour is documented (MSX2 TH) and which we **already implement as our own clean code** in
`lay_page0_env` (`int_h`, `rdslt/wrslt/calslt/enaslt`, the `$0030` CALLF shim). So reaching `A>` means
**standing up our own resident environment** that satisfies MSXDOS.SYS's expectations — *not* lifting
the proprietary kernel's bytes. We never copy the stock's `$DDxx` code; we observe *which vectors the
boot uses and how*, and point them at our own handlers.

**Next steps:** (1) page-align + size the returned area to a 256-byte page (move `GETWRK_AREA` to a
page boundary, reserve `$100`); (2) lay our resident int + inter-slot vectors into its upper region
(reuse `lay_page0_env`'s handlers, retargeted to this page) and seed the low work-variable fields;
(3) re-trap — resolve the `$0038` derail by making MSXDOS.SYS's interrupt/inter-slot path land in OUR
handlers, and iterate. The remaining surface is a bounded resident-environment stand-up (standard
vectors we already have), not an open-ended kernel reconstruction.

## 8.16 §8.15 REFUTED — the lever is RAMAD0-3, not the work-area layout; page-0 RAM now maps

§8.15's plan (lay our resident vectors at an offset *inside* the `$4030` work area) was a hypothesis,
and characterising it first — before building — **refuted it** and found the true lever. New tool:
`probes/disk/disk_probe_dosboot_lowstore.py` (stock oracle + `--tier1` derail differential; black-box:
breakpoint `$4030`, RAM read/write watchpoints, register/RAM reads — no ROM/MSXDOS code read).

**Two oracle findings kill the §8.15 theory.** On the genuine CF-3300, after `$4030` returns its base
(`$DD0E`): (a) MSXDOS.SYS makes **zero writes to `$0000-$003F`** — it does not install work-area-relative
low-storage vectors post-`$4030`; (b) the `$0038` interrupt vector holds `JP $0C3C`, a **fixed page-0
handler, NOT inside the work area**. So the interrupt path is the standard MSX chain (`$0038` → BIOS
KEYINT → hooks → resident `$DDxx`), and the `$DDB0` execution §8.15 saw is reached via that hook chain,
not directly from `$0038`. The work-area *layout* is not the `$0038` lever.

**The differential names the real lever.** Page-0 low storage `$0000-$003F`, stock vs the derailing
Tier-1 boot:

| | stock (boots to A>) | Tier-1 pre-fix (derails) |
|---|---|---|
| `$0000-$003F` | full JP vector set, `$0038→$0C3C` | **all `$FF`** |
| settle PC / `[PC]` | running MSX-DOS | **`$0038`, `[PC]=$FF`** (= `RST 38h`) |
| stack@SP | — | `39 00 39 00 …` (`$0039` pushed forever) |

Page 0 read **all `$FF`** = an unmapped slot; the CPU executed `$FF` (`RST 38h`) at `$0038`, pushing
`$0039` and looping. **`RAMAD0-3` (`$F341-4`) is the cause:** MSXDOS.SYS reads it **84×** after `$4030`
to re-page RAM into page 0 (where the page-0 BIOS ROM was). The base BIOS sets only `EXPTBL`; **RAMAD is
the disk ROM's INIT job** (§8.8), and ours never set it → MSXDOS paged an empty slot → `$FF` → wedge.
(§8.9's "MSXDOS never reads RAMAD" was correctly scoped to the *boot-sector loader* phase; MSXDOS.SYS's
own post-`$4030` init **does** read it — a different phase.)

**Fix — `set_ramad` in INIT (`disk.asm`).** Derive the page-3 RAM-slot id (`F000SSPP`, host-adaptive,
the same way `page0_ram_in` does: `$A8` primary, `EXPTBL` expand flag, `$FFFF` subslot) and write it to
`RAMAD0-3`, **gated on `$FF`** so a host that already set RAMAD is untouched. Regression-safe: on the
C-BIOS hosts RAMAD = `$C9..` (≠`$FF`) → gate skips → C-BIOS exactly unchanged (and C-BIOS never boots
DOS, so nothing reads RAMAD there). On the real-CF-3300 Tier-1 host RAMAD = `$FF` → we fill it. Verified:
Tier-1 RAMAD at `$4030`-return is now `83 83 83 83`, **byte-identical to the stock**. `bdos_entry` shifts
`$43B6→$43EA` (init probe updated). Regression-green: `disk_probe_init`/`files`/`bload_disk`/`dskio` PASS.

**Result — page-0 RAM now maps; MSXDOS.SYS installs its BDOS.** Re-trap (Tier-1): the `$FF`/`$0038`
wedge is **gone**. Page 0 is RAM with MSXDOS's own low storage — `$0000 → JP $E703` (warm boot) and
**`$0005 → JP $E106` (BDOS entry, in MSXDOS's relocated high-RAM kernel)**. MSXDOS.SYS got materially
further: it paged RAM, relocated itself, and stood up its BDOS vector. A clear, measured advance.

**New gap — `$0038` fires constantly, but the cause was characterised before fixing (see §8.17).** The
first read was "interrupt storm": once MSXDOS `EI`s, `$0038 → JP $4191` (our `int_h`, still installed by
the boot-bridge `lay_page0_env`; page 1 is still our disk ROM, not evicted — live `$4191` =
`f5 db 99 f1 fb c9` = our `int_h`) fires **25 438×** in 13 s. **That framing was WRONG** — §8.17 shows
it is a *symptom* of a garbage slide, not an inadequate ISR. RAMAD (this §8.16) stands as a real,
regression-safe advance regardless; the true next gap is §8.17.

## 8.17 The "storm" is a garbage slide — MSXDOS.SYS `CALL`s the `$F368` disk-work-area jump table

Characterising the `$0038` firing before building an ISR (the discipline that paid off twice already)
**refuted the §8.16 "interrupt storm" reading.** Measurements (black-box, `--tier1`):

- **Not a hardware interrupt that won't clear.** At `int_h` the VDP `S#0` goes `$9F` (frame flag set)
  on the *first* hit then `$1F` (**flag clear**) on every subsequent hit — `int_h`'s `in a,($99)` *does*
  clear the VDP. The FDC is idle: `$7FBC` bit 7 (INTRQ) = 0, `$7FB8` = `$80` (not-ready). **Neither
  hardware source is asserting**, yet `$0038` keeps being reached every ~20 µs.
- **It is a `RST 38h` slide through `$FF` RAM.** Classifying each `$0038` entry by the byte *before* its
  return address: the firings are `RST 38h` opcodes (`$FF` = `RST 38h`) executed out of uninitialised
  RAM — the first slide returns to **`$F369`**, i.e. the CPU is executing `$FF` bytes at `$F368+`.
  (Real 60 Hz VDP interrupts are interleaved — returns into `$448B` = our `bdos_rdblk`, and into `int_h`
  itself — but the derail is the slide.)
- **The bad jump: MSXDOS.SYS does `CALL $F368`.** At the first entry to `$F368` the stack top is `$E2B6`
  (return into MSXDOS's relocated page-2 kernel). `$F368` is `$FF` on ours → the call slides.

**`$F368` is a fixed disk-work-area JUMP TABLE the disk ROM builds; ours is empty.** Dumping the stock
`$F340-$F38F` after `$4030` shows, past RAMAD (`$F341`=`83 83 83 83`) and DRVTBL (`$F348`=`87 93 df 0e
dd 95 …`, §8.8), an **8-slot `JP` table** MSXDOS.SYS calls:

| slot | stock | target region |
|---|---|---|
| `$F368` | `JP $DF57` | resident kernel (high RAM page 3) |
| `$F36B` | `JP $DF59` | " |
| `$F36E` | `JP $DF70` | " |
| `$F371` | `JP $F327` | in-work-area resident routine |
| `$F374` | `JP $F32C` | " |
| `$F377` | `JP $0000` | unused slot |
| `$F37A` | `JP $0000` | unused slot |
| `$F37D` | `JP $F331` | **SYSTEM / BDOS** (ours already = `JP bdos_entry`) |

So after RAMAD, MSXDOS.SYS's init reaches the disk system through this `$F368` table (not via the page-0
inter-slot vectors, and not the `$4030` work-area offset of §8.15). We populate only `$F341-4` (RAMAD)
and `$F37D` (SYSTEM); `$F368-$F37C` is `$FF`, so the first `CALL $F368` derails. This is the §8.8
resident environment, now **precisely located** as a small fixed jump table — far smaller than "rebuild
the kernel," and the `$F37D` slot is already ours.

**Next step (next session) — characterise + provide the `$F368` table entries.** For each used slot
(`$F368/$F36B/$F36E` first — the ones MSXDOS.SYS calls), black-box the routine's contract on the stock
(inputs in / observed effects + outputs) the GETDPB/`$4030` way, then point our `$F368` table at OUR
clean re-implementations (likely thin forwarders to our existing `$4010`-`$401F` driver, since the
table is the disk *driver* API the kernel calls). The `$DFxx` targets are the stock's resident kernel —
never copied; we observe behaviour and supply our own. CLEAN-ROOM unchanged. Also confirm whether
`$F368` is a *documented* MSX disk-work-area entry (source-upgrade check) vs purely oracle-derived.

## 8.18 `$F368` table built — MSXDOS.SYS now drives our disk driver + reads the filesystem

Characterising the used `$F368` slots on the stock (`disk_probe_dosboot_f368.py`, black-box) before
building them:

- **Only `$F368` (32×) and `$F36B` (31×) are called** of the eight (plus `$F37D`=SYSTEM, already ours);
  `$F36E/$F371/$F374/$F377/$F37A` are **never called**. Inputs carry `IX` = the drive-A DPB (`$F195`,
  the same DPB our GETDPB/`$4030` oracle saw).
- **Both are no-ops on this 64K machine.** The deep in/out trap shows `$F368`/`$F36B` return
  **register- and flag-transparent**, and an effects trap (watch *all* RAM writes + the FDC ports
  `$7FB8-$7FBF` + *all* I/O ports `$00-$FF` across a call) records **zero** writes, **zero** FDC access,
  **zero** I/O. They are the disk system's resident **RAM-segment-switch hooks**: on a machine with a
  memory mapper they'd page a segment, but the CF-3300 is plain 64K (one segment), so they just `RET`.

**Built (`disk.asm`, under the same `$FF`/real-CF-3300 gate as `set_ramad`).** `build_wa_table` lays
`JP wa_stub` into the seven slots `$F368-$F37A` (`wa_stub` = a single `RET` in our page-1 ROM, reached
exactly as `int_h`/`$0038` already is); the loop stops at `$F37C`, leaving `$F37D` = our SYSTEM
`JP bdos_entry` intact. Clean-room: our own `RET`; the stock's `$DFxx` targets are never read.
`bdos_entry` `$43EA→$43FB` (init probe bumped). Regression-green: `init`/`files`/`bload_disk`/`dskio` PASS.

**Result — a large advance.** Re-trap (Tier-1): the `$F368` slide is **gone**. MSXDOS.SYS proceeds
through its init, and the boot is now found **executing inside our own disk driver** (`PC` in our FDC
code `$431x/$436x`, a real `SP=$C004`) with the stack holding genuine filesystem bytes — `56 4F 4C 5F
49 44` = **"VOL_ID"** (a directory/volume entry) plus DPB fields. So MSXDOS.SYS is running its resident
code and reading the disk's directory through our driver — the furthest the DOS boot has reached.

**New gap — a downstream stack-corruption derail.** It does not yet reach `A>`. The boot ends reaching
our DSKIO (`$4010`) **once**, but with nonsensical parameters (`Cy=1` write, `B=$E8`=232 sectors,
`DE=$E880`=sector 59520 — far past the 1440-sector disk, `A=$7F`), then loops in our ROM without
issuing any FDC command. The cause is upstream: at that `$4010` entry the return address is `$3432` and
the stack bytes are **ASCII** (`32 34 35`="245", "VOL_ID"…) — **`SP` is pointing into a data/text buffer,
not a call stack**. So MSXDOS.SYS's stack was corrupted earlier and a garbage `RET`/`CALL` landed in
`$4010`. (Root cause found in §8.19.)

## 8.19 The post-`$F368` derail is a HIGH-RAM COLLISION — MSXDOS's kernel overlaps our scratch

Tracing where `SP` goes bad (black-box, `--tier1`) located the root cause, and it is NOT the `$F368`
no-op (that holds):

- **It is a `RST 38h` slide through `$FF` at `$8004+`** (page 2), the same `$8004` crawl §8.16 first
  saw. On the **stock**, `$8004` is `$FF` too and is **never jumped to** — so the slide is unique to our
  derail, not a routine the stock provides.
- **The slide is reached via a corrupted stack.** At the first jump to `$8004`: `SP=$E6FE`, and the
  bytes there are **`JP` vectors** (`c3 b0 e2`=`JP $E2B0`, `c3 0f e7`=`JP $E70F`, `c3 2c e7`=`JP $E72C`)
  — i.e. `SP` is pointing into **MSXDOS.SYS's relocated kernel jump table at `$E700+`**, not a clean
  stack. The stack grew into the kernel's vector table → a garbage `RET` → the `$8004` jump.
- **MSXDOS.SYS's resident kernel sits at `$E1xx–$E7xx` on our boot** (BDOS `$E106`, vectors `$E70F`/
  `$E72C`, stack `$E6FE`). That range **directly overlaps our disk-ROM high-RAM scratch**: `SECTOR_BUF`
  `$E2A0`, `FAT_*`, `WBUF` `$E560-$E75F`, `RDBLK_*` `$E76C`, `GETWRK_AREA` `$E780`. The kernel and our
  work area are fighting over the same RAM.

**Why the stock is fine — it reserves high RAM; we don't.** On the stock, `HIMEM` (`$FC4A`) = `$DF93`
and the `$4030` work area = `$DD0E`: the disk ROM's INIT lowers the top-of-RAM so the disk work area +
the resident environment occupy protected high RAM and MSXDOS.SYS positions its kernel/stack **clear of
it**. Our INIT never reserves our high-RAM region for the DOS environment, so MSXDOS.SYS relocates its
kernel up into `$E1xx-$E7xx` — straight over our scratch — and the collision corrupts the stack.

This is the §8.8 "resident environment" concern resurfacing as a concrete **memory-layout** problem, not
a code-reconstruction one: there is no missing kernel code to write, only a region to reserve.

**Next step (next session) — reserve our high-RAM region so MSXDOS.SYS's kernel lands clear of it.**
Characterise exactly which pointer MSXDOS-1 reads to position its kernel (lead: `HIMEM $FC4A`, stock
`$DF93`; and/or a memory-top work-area cell), then have our INIT set it below our scratch base (and/or
relocate the disk-ROM scratch so our reserved block matches the stock's `$DD0E`-style placement), then
re-trap. Clean-room: high-RAM reservation is standard documented MSX (MSX2 TH work area / HIMEM); no
kernel bytes are read. The `$F368` table + RAMAD advances stand regardless.

## 8.20 Memory-top lever narrowed — it is NOT HIMEM; the kernels differ by exactly `$1000`

Testing the §8.19 HIMEM hypothesis (and reverting it) sharpened the target:

- **The resident kernels differ by exactly 4 KB.** Stock BDOS base (`$0005` JP target) = **`$D606`**;
  our Tier-1 boot = **`$E106`** — `$E106 - $D606 = $1000`. MSXDOS.SYS positions its whole resident
  kernel 4 KB higher on ours, straight onto our scratch (`$E2A0-$E780`); the stock places it 4 KB lower
  and clear.
- **HIMEM is NOT the lever.** Setting `HIMEM ($FC4A) = $DF93` (the stock value; ours is `$F380`) under
  the gate did **not** move the kernel — BDOS stayed `$E106` — and actually regressed the boot (it then
  wedged at `$0038` with `SP=$30FF`, never reaching DSKIO). MSXDOS reads HIMEM 0× while positioning its
  kernel. Reverted; no net code change.

So MSXDOS-1 computes its kernel base from some *other* top-of-RAM source that is `$1000` higher on our
host than on the stock — i.e. the stock disk ROM reserves 4 KB of high RAM that ours does not, by a
mechanism other than HIMEM. (Note the stock `$F348` DRVTBL embeds both `$DF93` (HIMEM) and `$DD0E` (the
`$4030` work area) as words — candidates the kernel-placement code may consult.)

**Refined next step.** Find the cell/mechanism that fixes the 4 KB: differential-dump the page-3 work
area (`$F300-$FFFF`, plus `$0006-7` TPA-top via a kernel-PC trap) stock-vs-Tier-1 and locate the
pointer that is `$D6xx`/`$DDxx` on the stock and `$E1xx`/`$E7xx` on ours; or determine MSXDOS-1's
top-of-RAM probe and have INIT bound it below our scratch. Equivalently, relocate our entire disk-ROM
high-RAM scratch into a block MSXDOS protects (the `$4030`-communicated work area is only 128 B at
`$E780`; our `SECTOR_BUF`/`FAT_*`/`WBUF` are NOT communicated, which is why only they collide). The
`$F368` + RAMAD advances stand regardless.

## 8.21 The reservation is a DISK function (VG-8020 control) + MSXDOS dispatches through the `$F348` DRVTBL

Prompted by the question "is `$1000` a function of the system having a disk?", a no-disk control nails
both the reservation gap and the next concrete lever.

**HIMEM across machines — our disk ROM does ZERO high-RAM reservation.**

| machine | HIMEM `$FC4A` | reservation vs no-disk |
|---|---|---|
| Philips VG-8020 (no disk) | `$F380` | — (baseline) |
| National CF-3300, Disk BASIC | `$F1BF` | disk ROM reserved `$1C1` |
| National CF-3300, MSX-DOS | `$DF93` | DOS reserved much more |
| **our Tier-1 (real BIOS + zerobas-disk)** | **`$F380`** | **none — identical to the no-disk VG-8020** |

So memory-wise our disk system looks like a **diskless** machine: the real disk ROM lowers HIMEM (and
reserves more under DOS), and ours does not — confirming the `$1000` is the disk system's resident
footprint that MSXDOS.SYS places its kernel *below*, and that we under-reserve it. (HIMEM is still not
the cell MSXDOS-1 reads for kernel placement — §8.20 — but the reservation discipline is clearly a
standard disk-ROM job we skip.)

**The concrete lever: MSXDOS.SYS reads the `$F348` DRVTBL 208× — and ours is unbuilt.** Trapping reads
of `$F348-$F357` on the stock after `$4030`: **208 reads**. The stock DRVTBL is
`87 93 df 0e dd 95 ef 95 ed 95 eb 00 00 95 f1 aa` = a structured table:

| field | value | meaning (hypothesis) |
|---|---|---|
| `$F348` | `87` | the disk-interface slot id (= our slot 3-1) |
| `$F349` | `$DF93` | top-of-reserved-RAM (= HIMEM) |
| `$F34B` | `$DD0E` | the `$4030` disk work-area pointer |
| `$F34D/4F/51/55` | `$95EF/$95ED/$95EB/$95F1` | resident disk-driver routine pointers (page-2 kernel) |

We build RAMAD (`$F341`), the `$F368` table, and SYSTEM (`$F37D`) but **NOT** the `$F348` DRVTBL — so
MSXDOS.SYS dispatches disk operations through **garbage pointers**, which is the most likely source of
the bad jumps (e.g. the `$8004` page-2 slide of §8.19: a garbage `$95xx`→`$80xx` driver pointer). This
is the §8.8 finding, now confirmed as a live MSXDOS dependency and tied to the derail.

**Next step (next session) — build the `$F348` DRVTBL.** Characterise each field black-box (what
MSXDOS passes to / expects from the `$95xx` driver pointers — the GETDPB/`$4030`/`$F368` way), then
build our own DRVTBL: slot id `$87`, a reserved-top + `$4030` work-area pointer, and the driver-routine
pointers aimed at **our own** entries (our `$4010-$401F` driver / thin forwarders), never the stock's
`$95xx` kernel bytes. Do the high-RAM reservation alongside so the table's reserved-top is honoured.
Clean-room unchanged. This is the bounded resident-environment table §8.8 first sized — data + pointers
to code we already have, not a kernel to reconstruct.

## 8.22 The `$F348` DRVTBL fully characterised: the disk ROM builds it; the driver pointers are always-mapped high-RAM trampolines

Black-box probe `probes/disk/disk_probe_dosboot_drvtbl.py` (dump + read-watch + write-watch + deep
in/out trap, all on the stock CF-3300 with a /tmp DOS disk) pins the table down — and corrects a
misreading carried in §8.21.

**Layout (corrected).** The stock dump is `87 93 df 0e dd 95 ef 95 ed 95 eb 00 00 95 f1 aa`. `$95` is
the **low** byte of each pointer, not the high byte — §8.21's `$95EF/$95ED/$95EB/$95F1` reading slid a
byte off. Word-aligned from a 5-byte head (slot id + two words) the fields are:

| offset | value | meaning |
|---|---|---|
| `$F348 +0` | `$87` | disk-interface slot id (slot 3-1, expanded form) |
| `$F349 +1` | `$DF93` | top-of-reserved-RAM (= HIMEM) |
| `$F34B +3` | `$DD0E` | the `$4030` disk work-area pointer |
| `$F34D +5` | `$EF95` | driver-routine pointer (primary — see read profile) |
| `$F34F +7` | `$ED95` | driver-routine pointer |
| `$F351 +9` | `$EB95` | driver-routine pointer |
| `$F353 +11` | `$0000` | (unused entry) |
| `$F355 +13` | `$F195` | driver-routine pointer |
| `$F357 +15` | `$AA` | sentinel / next-entry head |

The four driver pointers `$EB95/$ED95/$EF95/$F195` are evenly spaced `$0200` apart and **all lie above
HIMEM `$DF93`, in page 3 (`$C000+`)** — i.e. inside the reserved high-RAM region, in always-mapped RAM.

**Who consumes it.** A single routine at **PC `$0368`** reads the table; the hottest fields over a 12 s
settle are `+5/+6` (`$EF95`, 146 reads) and `+0` (slot id, 69) — `$EF95` is the primary dispatch
pointer. Deep-trapping `$EF95` as code: it is entered with `A=$00` (drive A), `B`=count, a buffer in
`HL` advanced by the transfer on return (`$0100→$0700`) — a sector-I/O shape — and its **caller is
`$75A5`, inside the disk ROM (page 1)**, not MSXDOS. So MSXDOS reads the pointers but the disk ROM is
what dispatches through them.

**Who builds it (the decisive write-watch).** Every meaningful write to `$F348-$F357` comes from
**page 1 (`$453D`-`$5EAE`) — the disk ROM builds the whole DRVTBL**; MSXDOS never writes it. (The only
non-page-1 writes are the boot loader's `00`/`FF` clear pass from `$036A`/`$036D` in low RAM.) The
build order is visible: `$58AB`→slot id `$87`; `$594D`→`+1=$DF93`; `$5EAE`→`+3` written repeatedly as
the work-area pointer is allocated downward (`$DDF3→$DDAE→$DD0E`); `$58FE/$5906/$590D`→the three
`$EF95/$ED95/$EB95` pointers; `$587E/$453D`→`+13=$F195`, `+15=$AA`.

**Why the pointers are in high RAM — and why ours derails.** Under MSX-DOS page 1 (`$4000-7FFF`) is the
TPA (RAM), so the disk ROM at `$4xxx` is not directly callable; the disk ROM reserves high RAM (lowers
HIMEM to `$DF93`) and builds **always-mapped trampolines** in page 3 that dispatch (CALSLT slot `$87`)
into its `$4010` BIOS. The DRVTBL points at those trampolines. Ours does **none** of it — no
reservation (§8.21: our HIMEM = the diskless `$F380`), no trampolines, no table — so the pointers
MSXDOS/our-ROM read from `$F348` are garbage, the source of the `$8004` derail.

**Build spec (now fully shaped).** Mirror the disk ROM in our INIT, under the `$FF` real-CF-3300 gate:
1. **Reserve high RAM** — lower HIMEM and claim a page-3 block for the trampolines + the `$4030` work area.
2. **Build CALSLT trampolines** in that block, one per driver routine, each inter-slot-calling our own
   slot at the matching `$4010-$401F` BIOS entry (DSKIO/DSKCHG/GETDPB/…), preserving registers.
3. **Write the `$F348` DRVTBL**: slot id (our slot 3-1), `+1`=reserved-top, `+3`=`$4030` work-area
   pointer, `+5/+7/+9/+13`=our trampoline addresses, `+15`=sentinel.

Clean-room intact throughout: we observed register/flag in/out and writer/reader PCs only; the `$EB95-
$F195` trampoline bytes, the `$DFxx`/`$95xx`-region kernel, and MSXDOS.SYS were never read or
disassembled. Pointers in our build aim only at our own code. Next: map each trampoline to its `$401x`
BIOS entry (trap the CALSLT target per pointer), then build.

## 8.23 `build_drvtbl` shipped (faithful + consumed) — but the reserved-top is NOT the kernel-placement lever

Built the §8.22 spec in `disk.asm`: `build_drvtbl` (reached by fall-through from
`set_ramad`→`build_wa_table`, under the same `$FF` real-CF-3300 gate) lays four
`F7 <slot> <lo> 40 C9` CALLF trampolines in reserved page-3 RAM (`$E800`, the proven
H.PHYD form, into `$4010/$4013/$4016/$401C`) and writes the `$F348` DRVTBL: slot id |
reserved-top `$DF93` | `$4030` work-area ptr `$E780` | the four trampoline pointers |
`$0000` | `$AA` sentinel. `bdos_entry` `$43FB`→`$4453`; init probe bumped; regression-
green (init/files/bload_disk/dskio PASS on C-BIOS — the gate skips it there).

**Validated CONSUMED (the win to bank).** On Tier-1, MSXDOS reads our `$F348` **37×,
first from PC `$0368`** — the identical consumer routine as the stock's 208× (§8.22).
So `build_drvtbl` is wired into the live boot path: real MSXDOS finds and reads our
DRVTBL. (37 < 208 because ours derails before the boot completes.)

**NEGATIVE RESULT — reserved-top in DRVTBL+1 does NOT move the kernel.** BDOS base
(`$0005` JP target) stays **`$E106`** (not the stock's `$D606`); the `$1000` gap of
§8.20 is unchanged and the §8.19 collision persists. So MSXDOS-1 derives its kernel
base from some source *other* than DRVTBL+1 (and other than HIMEM, §8.20). The `$DF93`
we advertise is read but not used for placement.

**The derail today (re-measured).** The old `$0038` RST38 wedge is GONE (set_ramad +
`$F368` fixed it): MSXDOS.SYS now re-enables interrupts and the CPU is sampled in our
`int_h` (`$41FD`) — but the interrupted *main thread* has run away: histogram of the
return PC at `int_h` entry over 12 s = **`$FFFF` 98.7%** (351098/355598), with brief
excursions through our FDC code (`$42Dx`), page 2 (`$8425`), and the work area
(`$F33x`). A garbage-RET PC run-away — the §8.19 stack corruption from the `$E106`
kernel overlapping our `$E2A0-$E780` scratch, exactly as diagnosed, still the blocker.

**NEXT — find MSXDOS-1's real top-of-RAM source.** Trap the *stock's* kernel-base
computation (where it derives `$D606`) and identify the cell/probe it reads; then set
that on ours so the kernel lands clear of our scratch. Strong candidate: a RAM-size
probe skewed by our ROM's page-2 — our 16 KB ROM reads `$FF` at `$8000-$BFFF` where the
stock disk ROM maps content; a sizing routine could miscount by `$1000`. (The DRVTBL
trampolines are built but not yet exercised — the boot derails before dispatching a
disk op through them — so their `$401x` mapping stays unverified until the collision is
cleared.) Clean-room unchanged: register/flag + reader/writer PCs only.

## 8.24 KERNEL-PLACEMENT LEVER FOUND + FIXED — it is DRVTBL+3 (the `$4030` work-area pointer)

The §8.23 "find MSXDOS-1's real top-of-RAM source" step is **resolved**, and the §8.19 collision is
**cleared**. New black-box probe `probes/disk/disk_probe_dosboot_ramtop.py` watches the writer of the
CP/M BDOS vector (`$0005-$0007`; `$0006-7` word = BDOS base = kernel base) on stock vs Tier-1:

- **Stock**: `LD ($0006),HL` at PC `$D7C0`, **HL=`$D606`**, **DE=`$DC80`**.
- **Tier-1 (pre-fix)**: same routine relocated to PC `$E2C0` (= `$D7C0`+`$0B00`), **HL=`$E106`**,
  **DE=`$E780`** — the kernel `$0B00` higher, straight onto our scratch.

**The invariant pins the mechanism.** On BOTH machines **DE − HL = `$067A`** exactly — i.e. `$067A` is
the kernel size and **DE is the kernel TOP after the relocating `LDIR`**. The kernel top equals the
disk **work-area pointer we publish in DRVTBL+3** (Tier-1 DE `$E780` = our `GETWRK_AREA` = DRVTBL+3
`$80e7`; stock tracks its own `$DD0E` work area). So MSXDOS.SYS places its resident kernel with its TOP
at the `$4030` work-area pointer and its base `$067A` below — **DRVTBL+3 is the lever, not DRVTBL+1
(§8.23) or HIMEM (§8.20)**. (Correction to §8.20: the kernels differ by `$0B00`, not `$1000` — an
arithmetic slip; `$E106-$D606 = $0B00`.)

**Fix (one equate).** `GETWRK_AREA $E780 → $DD0E` (the stock work-area address). Our `$4030` now returns
`$DD0E`, so MSXDOS relocates its kernel to **`$D606` — byte-identical to the stock** — below our lowest
scratch (`$E29A`); the 128-byte work area DOS fills (`$DD0E-$DD8E`) is clear of both kernel and scratch.
Equate-only: no code moved, `bdos_entry` stays `$4453`, C-BIOS regression green (init/dskio PASS, 18
unit files PASS).

**Validated on Tier-1 (the win to bank).** Post-fix `ramtop` shows the writer back at PC `$D7C0` with
**HL=`$D606`** and `final_bdos = c3 06 d6` (`JP $D606`) — the kernel lands exactly where the stock's
does. The `$FFFF`-runaway derail of §8.23 is **GONE**: settle PC is real BIOS/code (`$2E98`/`$12EC`),
the boot reads the disk heavily through our driver (64× `$4030`, 24 opens, 37 RDBLK), and gets through
the MSX boot banner (SCREEN-1 "MSX system / version 1.0").

**NEXT GAP — a re-init / warm-boot spin.** The boot now *loads DOS* but does not reach `A>`: the BDOS
vector is re-published **6×** at `$D7C0` (the stock publishes it once) — MSXDOS.SYS keeps re-running its
resident init, a warm-boot loop after the kernel is placed but before COMMAND hands over the prompt.
Characterise what fails between publications (likely COMMAND.COM load/exec or a disk op returning an
error that triggers the warm-boot), with the DRVTBL trampolines now finally reachable to exercise.
Clean-room unchanged: register/flag + reader/writer PCs only; no ROM/MSXDOS code read.

## 8.25 The warm-boot spin = kernel `CALL $50A9` into an EMPTY page 1 (MSXDOS.SYS's upper part never loaded)

With the kernel correctly placed (§8.24), the boot now loads MSX-DOS but re-publishes the BDOS vector
~6× (a warm-boot loop) instead of reaching `A>`. New probe `probes/disk/disk_probe_dosboot_reinit.py`
traces the path right after a clean publication and pins the cause — and it is **content, not mapping**.

**Stock vs Tier-1 are byte-identical at the publish site.** Right after `LD ($0005),A` the kernel does,
on BOTH machines, `CALL $50A9` (`opcode cd a9 50` at `$D7CB`) with identical regs (`HL=$D606 DE=$DC80
SP=$DC00`) and identical `ppi $A8 = $FF` (page 1 = slot-3 RAM). So the slot mapping is fine and `$FF`
is NOT corruption — the stock runs the same way.

**The only difference is what lives at `$50A9` (page 1):**

| machine | `$50A9` bytes | publications | result |
|---|---|---|---|
| stock | `cd2d4721 55f33a47 f35e2356 23e5f5d5` (real MSXDOS.SYS loader) | **1** | boots to `A>` |
| Tier-1 | `00000000 00000000 00000000 00000000` (empty) | **6** | NOP-slide crash → warm-boot loop |

On Tier-1 the `CALL $50A9` lands in zeros and slides linearly (`$50A9, $50AA, $50AB, …` for 1000+
instructions — confirmed by an instruction trace), crashes, MSX-DOS warm-boots, re-runs its resident
init (re-publishing the vector), and loops. (Earlier `$4010/$4013/$401C` "calls" with garbage regs were
this runaway sweeping our jump table, not real disk ops — and indeed `count=0` real DSKIO calls ever
fire: the crash precedes the first sector read.)

**Root cause — MSXDOS.SYS's page-1 portion (`$4000+`) was never written to RAM during our DOS-boot
bridge.** Page 1 (`$4000-$7FFF`) held our disk ROM (slot 3-1) while the bridge loaded MSXDOS.SYS, so the
sectors that belong above `$4000` went to ROM / were discarded; when the kernel later runs with page 1 =
the slot-3 RAM sub-slot, that RAM is empty (`$00`) at `$50A9`. This is the page-1 analog of the §8.16
page-0 RAMAD fix: there the problem was page-0 *mapping*; here it is page-1 *load target*.

**NEXT — load MSXDOS.SYS's page-1 portion into RAM.** [SUPERSEDED by §8.26 — this NEXT was based on the
falsified page-1-load framing. The actual fix is to implement the `$50A9` disk-ROM entry.]

## 8.26 The warm-boot spin RE-ROOT-CAUSED: `$50A9` is an unimplemented DISK-ROM entry, not unloaded data

§8.25's "MSXDOS.SYS's page-1 portion was never loaded to RAM" is **falsified**. New probe
`probes/disk/disk_probe_dosboot_50a9.py` pins the true cause, and a first-cut fix along the §8.25 line
(a page-1-aware RAM store in `bdos_rdblk`) was tried and **reverted**: its store helper was *never called*
(0 entries) because the load never crosses `$4000`. Three facts overturn §8.25:

1. **MSXDOS.SYS is 2432 B (`$0980`)** on the test disk (root-dir read). The boot's `Open`/`SetDTA($0100)`/
   `RDBLK` loads it entirely into **page 0** (`$0100-$0A7F`); it never reaches page 1. So `$50A9` is **not**
   unloaded file data — there is no page-1 portion to lose.

2. **At the kernel `CALL $50A9` the page-1 sub-slot is the DISK ROM (3-1), not RAM.** Black-box at the
   publish site: `ppi $A8 = $FF`, `$FFFF` live `= $04` → page-1 bits `= 01` → sub-slot 1 = our disk ROM
   (slot 3-1), on **both** stock and Tier-1. So `$50A9` reads the **disk ROM at offset `$10A9`** — a fixed
   disk-ROM **entry point** the MSX-DOS kernel calls, the same class as `$4010`/`$4030`.

3. **The genuine CF-3300 disk ROM implements `$10A9`; ours leaves it `$00`.** Stock `$50A9` =
   `cd 2d 47 21 55 f3 …` (`CALL $472D` + work-area setup); our `build/disk.rom` offset `$10A9` is `$00`
   padding (our code is far smaller). So the kernel calls into zeros, NOP-slides, crashes → warm-boot spin.
   (The 6→1 publication change §8.25's first-cut produced was an *artefact*: its stub LDIR wrote `$E778-$E7A6`,
   which MSXDOS uses, corrupting its state — not a real boot.)

**BLACK-BOX CONTRACT of the stock `$50A9`** (the next reimplementation target; `disk_probe_dosboot_50a9.py
--stock`):

| | AF | BC | DE | HL | IX | IY |
|---|---|---|---|---|---|---|
| in  | C340 | 0000 | DC80 | **D606** (kernel base) | F195 | C0AB (FCB) |
| out | 0042 (Z) | 0000 | **F1AA** | **F359** | **F1AA** | C0AB |

Only non-stack memory write: `$F242 = $00` (via the `CALL $472D` sub-routine). BC and IY preserved. The
returned `HL=$F359` (`DRVTBL+$11`, past the `$F348` table §8.22) and `DE=IX=$F1AA` point into the disk
work area the disk ROM built. Returns to `$D7CE`, where the kernel consumes them.

**NEXT — reimplement the `$50A9` disk-ROM entry** (offset `$10A9`), like `$4030` (§8.13/§8.24): emit a
routine at `$50A9` honouring the contract above (write `$00` to `$F242`; return `A=0`/`Z`, `HL=$F359`,
`DE=IX=$F1AA`, preserve `BC`/`IY`), then **re-trap**: run with it in place and trace what the kernel does
with the returned pointers at `$D7CE+` to refine the `$F1AA`/`$F359` work-area layout it expects. Our disk
ROM stays in page 1 throughout boot (§8.4), so a `$50A9` entry is reachable exactly as `$4010`/`$4030` are.

Clean-room: we read the `$50A9` call-target bytes (present vs absent) and record the entry/exit register
**contract** + the single side-effect — black-box observations; no disk-ROM code is disassembled or copied.
