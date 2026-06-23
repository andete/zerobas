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

**Open question for reimplementation — the `HL` mapping rule.** One in-situ data point
(`$F1C9 → $DD0E`) does not determine the function. Crucially, when we reimplement `$4030` in
zerobas-disk we **choose our own work-area location**, so we need the *rule* (does it ignore `HL` and
return a fixed per-drive base? offset-translate `F1xx`→`DDxx`? select on `A`?), and then we need to
know *what MSXDOS.SYS reads from the returned pointer next* (the work-area layout it expects).

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
