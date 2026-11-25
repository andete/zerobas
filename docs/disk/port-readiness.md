<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# The disk ROM: readiness for C-BIOS

> **Status (2026-11-25):** first version. The priority (Joost, 2026-11-25): *"getting the disk rom in the best
> possible shape to port it to C-BIOS"*. This page is the map: what "ready" means, what is shown, and what is not.

## What "ready" means

zerobas's disk ROM (`build/disk.rom`, 16 KB, the CF-3300-style "AB" disk-interface ROM in its own slot) is ready when
C-BIOS -- **without a BASIC** -- can carry it and:

1. boot MSX-DOS 1 from it, and run MSX-DOS programs, as the reference machines do;
2. offer the published disk-ROM entries (DSKIO, DSKCHG, GETDPB, CHOICE, DSKFMT, MTOFF and the pinned kernel
   entries) and the MSX-DOS 1 BDOS with the references' observable behaviour;
3. depend on nothing of zerobas's own main ROM;
4. use only the RAM it claimed, wherever the host put that claim;
5. leave room to fix what is still found.

The reference is the National CF-3300 (zerobas's DISK build) and, for a host with a third-party cartridge, the
Philips VG-8020 with a Sony HBD-F1.

## Where it stands

| # | requirement | state | evidence |
|---|---|---|---|
| 1 | MSX-DOS 1 boots and runs | ✅ on zerobas's own DISK machine and on stock C-BIOS **with zerobas BASIC patched in**; ❌ **never shown on a C-BIOS with no BASIC** | `make dossession-acceptance`, `make bdos-cbios-selfcheck` (machine `C-BIOS_MSX1_EU_BASIC_DISK`: stock C-BIOS + zerobas BASIC as a page-1 patch) |
| 2a | the BDOS surface | ✅ byte-identical to the stock disk ROM on the CF-3300 host, and self-consistent between the CF-3300 and the C-BIOS (+ zerobas BASIC) host | `make bdos-acceptance`, `make bdos-cbios-selfcheck`; [D-DISKCONTRACT](../../todo/open/D-DISKCONTRACT.md) (1) |
| 2b | the published disk-ROM entries | ✅ specified and FINAL: [DSKIO](DSKIO.md), [DSKCHG](DSKCHG.md), [GETDPB](GETDPB.md), [CHOICE](CHOICE.md), [DSKFMT](DSKFMT.md) (MTOFF and the pinned kernel entries have no page of their own); open rows in [D-DISKCONTRACT](../../todo/open/D-DISKCONTRACT.md) | `scratchpad/disk_contract_inventory.md` |
| 3 | no dependence on zerobas's main ROM | ⚠️ **by reading, yes for MSX-DOS; not proven.** The disk ROM includes `disk/basic-resident-abi.inc`, generated from zerobas's own symbol file: six routines of zerobas's main ROM (`widen_int_to`, `widen_fac_to`, `round_single_and_pack`, `round_and_finalize`, `pu_deref_body`, `subrom_call`) and zerobas BASIC's cells. All five routine CALLS sit in Disk BASIC's MKS$ / CVS hooks (`hk_mkfloat`, `hk_cv` in `disk/kernel.asm`); `subrom_call` is named only in comments. A BASIC-less C-BIOS never reaches those hooks -- but no run has shown it | `grep` of `disk/*.asm` against the include (2026-11-25) |
| 4a | the host contract (what C-BIOS must provide) | ✅ items 1-4 met: the INIT stack, MS-BASIC's layout cells, H.RUNC, the start-up screen word at $7D2F | [disk-rom-host.md](../concepts/disk-rom-host.md); zerobas NODISK + Sony HBD-F1 runs a COMMAND.COM session as the VG-8020 + HBD-F1 does |
| 4b | RAM only inside the claim, as the references claim it | ✅ the two-step claim (INIT, then H.RUNC to $DF93) as the CF-3300; HOOK_SLOT inside the claim | [D-DISKROMHOST](../../todo/open/D-DISKROMHOST.md) steps 1-4(c), [ram-atlas.md](../ram-atlas.md) |
| 4c | the claim wherever the host put it | ❌ the work area is addressed at FIXED addresses: right only when the disk ROM is the first to claim RAM. Next: an INIT **guard** that declines to install when the claim is not where the addresses assume (Joost: "guard first"); the base-addressed rewrite later | [D-DISKROMHOST](../../todo/open/D-DISKROMHOST.md) step 4(d) |
| 5 | room to fix | ❌ **full: 65 B of $00 fill, 0 B usable before the next pinned entry (2026-11-25, `make basic-reloc`)** -- 753 B on 2026-11-04, about 9 KB in September. Every further change must carve first; the wall tool now prints `⚠️ LOW ROOM` below 256 B | `tools/check_disk_walls.py` |
| -- | real disks | 143 images: 99 run on both zerobas and the CF-3300 (D-DISKROMHOST step 4(e), 2026-11-25) | `scratchpad/diskcorpus_run.py` |

## The gaps, in order

1. **Room (5).** Nothing else can land without it. ONE build (Joost, 2026-11-25): the port uses the FULL disk ROM,
   Disk BASIC included -- no DOS-only build switch. Scouted 2026-11-25: jp -> jr 6 B, duplicated blocks ~10 B net,
   instruction pairs a few B; no dead code.
2. **The guard (4c).** A few bytes in INIT; it needs (1).
3. **A BASIC-less host (1, 3).** A test machine: stock C-BIOS, NO BASIC, zerobas's disk ROM in its slot; boot
   MSX-DOS and run the BDOS exercisers on it. That turns 3 from "by reading" into "shown", and finds any BASIC cell
   the DOS path still touches.
4. **The open entry rows (2b)** in D-DISKCONTRACT, one by one against the CF-3300.
5. **END and open disk files** ([D-ENDCLOSE](../../todo/open/D-ENDCLOSE.md)): measure on both references, then decide
   (Disk BASIC behaviour; a BASIC-less C-BIOS does not need it, so it ranks last here).

The free-space figures on this page are dated; re-run `make basic-reloc` before relying on one.
