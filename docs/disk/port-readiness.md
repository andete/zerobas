<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# The disk ROM: readiness for C-BIOS

> **Status (2026-11-26):** gaps 1-5 done -- room, the guard, a BASIC-less host, the entry rows and END measured. What is
> left is FIXES (six filed, pinned in their gates), and each needs disk-ROM room: row 5 is the next lever. The priority (Joost, 2026-11-25): *"getting the disk rom in the best
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
| 1 | MSX-DOS 1 boots and runs | ✅ on zerobas's own DISK machine, on stock C-BIOS with zerobas BASIC patched in, and -- since 2026-11-26 -- **on a C-BIOS with NO BASIC at all**: a C-BIOS checkout's own MSX1 build (0.32, fac3f41) with zerobas's disk ROM in slot 3-1 boots MSX-DOS 1.03 / COMMAND 1.08, and the whole typed session (DIR, TYPE, COPY, concatenation, REN, DEL, VERIFY, DATE, the error cases) reads as on the CF-3300, the disk image it leaves byte-identical: 21/21. `BASIC` at A> has nothing to start there, so the restart comes back to MSX-DOS | `make dossession-acceptance`; `make nobasic-dossession-acceptance CBIOS=<checkout>` (machine `CBIOS2_CUR_MSX1_EU_NOBASIC_DISK`, `tools/install_cbios_msx2.py`); [AE_nobasic_dossession.out](../../scratchpad/AE_nobasic_dossession.out) |
| 2a | the BDOS surface | ✅ byte-identical to the stock disk ROM on the CF-3300 host, and self-consistent between the CF-3300 and the C-BIOS (+ zerobas BASIC) host | `make bdos-acceptance`, `make bdos-cbios-selfcheck`; [D-DISKCONTRACT](../../todo/open/D-DISKCONTRACT.md) (1) |
| 2b | the published disk-ROM entries | ✅ specified and FINAL: [DSKIO](DSKIO.md), [DSKCHG](DSKCHG.md), [GETDPB](GETDPB.md), [CHOICE](CHOICE.md), [DSKFMT](DSKFMT.md) (MTOFF and the pinned kernel entries have no page of their own); open rows in [D-DISKCONTRACT](../../todo/open/D-DISKCONTRACT.md) | `scratchpad/disk_contract_inventory.md` |
| 3 | no dependence on zerobas's main ROM | ✅ **for MSX-DOS, shown (2026-11-26):** the BDOS exercisers on the BASIC-less C-BIOS host leave 30 of 30 memory regions byte-identical to the CF-3300 host's ([AE_nobasic_bdos.out](../../scratchpad/AE_nobasic_bdos.out), `disk_bdos_cbios_selfcheck.py --cbios-machine CBIOS2_CUR_MSX1_EU_NOBASIC_DISK`), and row 1's session runs there. ⚠️ Disk BASIC still names zerobas's main ROM, as before: The disk ROM includes `disk/basic-resident-abi.inc`, generated from zerobas's own symbol file: six routines of zerobas's main ROM (`widen_int_to`, `widen_fac_to`, `round_single_and_pack`, `round_and_finalize`, `pu_deref_body`, `subrom_call`) and zerobas BASIC's cells. All five routine CALLS sit in Disk BASIC's MKS$ / CVS hooks (`hk_mkfloat`, `hk_cv` in `disk/kernel.asm`); `subrom_call` is named only in comments. A BASIC-less C-BIOS never reaches those hooks -- but no run has shown it | `grep` of `disk/*.asm` against the include (2026-11-25) |
| 4a | the host contract (what C-BIOS must provide) | ✅ items 1-4 met: the INIT stack, MS-BASIC's layout cells, H.RUNC, the start-up screen word at $7D2F | [disk-rom-host.md](../concepts/disk-rom-host.md); zerobas NODISK + Sony HBD-F1 runs a COMMAND.COM session as the VG-8020 + HBD-F1 does |
| 4b | RAM only inside the claim, as the references claim it | ✅ the two-step claim (INIT, then H.RUNC to $DF93) as the CF-3300; HOOK_SLOT inside the claim | [D-DISKROMHOST](../../todo/open/D-DISKROMHOST.md) steps 1-4(c), [ram-atlas.md](../ram-atlas.md) |
| 4c | the claim wherever the host put it | ✅ **for a foreign claim of up to 439 B (scheme D, 2026-11-26).** A cartridge scanned before the disk ROM that claimed N bytes: zerobas installs as the CF-3300 does, every cell left at its address and every published NUMBER moved by N -- HIMEM at INIT, MSX-DOS, A> and Disk BASIC, FRE, MEMSIZ / STKTOP, MSX-DOS's $0006, the $4030 value, DRVTBL+1 / +3 and the SLTWRK entry ($F1BF - N): SAME at N = 0, 16, 300, 439. Over 439 B (our HOOK_SLOT $F1C8 would be in the claim) INIT declines as SHIFT held does; the CF-3300 installs up to 473 B -- a KNOWN difference, pinned. The full base-addressed rewrite (~2.3-3.6 KB) is not needed for this | [D-DISKROMHOST](../../todo/open/D-DISKROMHOST.md) step 4(d); `make diskguard-acceptance` (`probes/disk/disk_probe_guard.py`, test cartridge `probes/disk/claimonce.asm`) |
| 5 | room to fix | ❌ **full.** 0 B usable before the next pinned entry on 2026-11-25 (`make basic-reloc`) -- 753 B on 2026-11-04, about 9 KB in September. A first carve the same day (five tails shared, two `jp` -> `jr`, the $5E10 entry falling into its body, write_sector shortened and moved) paid for the guard and left a few bytes, under the tool's 16-byte floor. Every further change must carve first; the wall tool prints `⚠️ LOW ROOM` below 256 B | `tools/check_disk_walls.py` |
| -- | real disks | 143 images: 99 run on both zerobas and the CF-3300 (D-DISKROMHOST step 4(e), 2026-11-25) | `scratchpad/diskcorpus_run.py` |

## The gaps, in order

1. **Room (5).** Nothing else can land without it. ONE build (Joost, 2026-11-25): the port uses the FULL disk ROM,
   Disk BASIC included -- no DOS-only build switch. Scouted 2026-11-25: jp -> jr 6 B, duplicated blocks ~10 B net,
   instruction pairs a few B; no dead code. The first carve spent nearly all of that on (2); the next item that needs
   bytes needs a new route.
2. ✅ **The guard (4c)**, 2026-11-25. On A>BASIC (and $4022 from a program) the restart now also puts HIMEM back to
   $F380 before the INITs rerun, as at power-on -- else the guard read MSX-DOS's own claim as a foreign one and BASIC
   came up with no disk. Found on the way: zerobas BASIC drops a cartridge's small HIMEM claim at boot
   ([D-CARTCLAIM](../../todo/open/D-CARTCLAIM.md), a BASIC item).
3. ✅ **A BASIC-less host (1, 3)**, 2026-11-26. openMSX's own bundled C-BIOS (0.29) is NOT that host: it runs the
   disk ROM's INIT and then reports *"No cartridge found"* -- it predates the disk-host work (HIMEM and MS-BASIC's
   layout set before the scan; H.RUNC after it). The port's host is a C-BIOS checkout's own build, which boots
   MSX-DOS from zerobas's disk ROM with no BASIC anywhere; row 1's session and the BDOS exercisers pass there. The
   machine is a C-BIOS checkout's state, so its suite runs on request (`make nobasic-dossession-acceptance
   CBIOS=...`), not in the battery.
4. ✅ **The open entry rows (2b)**, MEASURED 2026-11-26: every row D-DISKCONTRACT's inventory left open now has a
   reading against the CF-3300. One fixed on the spot (D-F37DHIGH: an undefined function through $F37D answers A = 0,
   as the CF-3300 -- the fix was a byte shorter); two filed and pinned in their gates (D-VERIFYREAD: VERIFY ON reads
   each written sector back on the CF-3300, `make verifyread-acceptance`; D-BUFINCTL: Ctrl-C / Ctrl-P were stored as
   characters by the line input -- ✅ FIXED 2026-11-26, below). **What is left of the entry contract is FIXES, not
   unknowns** -- D-DOSDRVB, D-STIMERANGE, D-CONCOL, D-DSKIOCYL, D-VERIFYREAD -- and the room for them now exists
   (D-DISKREREAD, the same day: ~8 B -> 718 B by re-reading the code).
   ✅ **D-BUFINCTL FIXED 2026-11-26:** under MSX-DOS the line input (BDOS $0A) now does what the CF-3300's does with
   every control key -- Ctrl-C abandons the program (`^C`, COMMAND.COM's A> again), Ctrl-P / Ctrl-N turn the printer
   echo on / off ($F23B, and console output goes to the printer while it is on), Ctrl-U and ESC erase the line,
   Ctrl-X drops itself and the next key, Ctrl-R is dropped, Ctrl-E / Ctrl-S are stored and shown as `^E`
   (`make bufinctl-acceptance`, 11 rows; `make dosctl-acceptance`, every row SAME with no pins). BASIC's BUFIN
   ($F37D) is unchanged and not measured with these keys; Ctrl-C during OUTPUT (CONST) is not measured either.
5. ✅ **END and open disk files** ([D-ENDCLOSE](../../todo/open/D-ENDCLOSE.md)), MEASURED 2026-11-26: the
   references do not split -- the VG-8020 + HBD-F1 and the CF-3300 both close every open file at END, a disk file
   and `CRT:` alike (`make endclose-acceptance`); zerobas keeps them open. The fix is BASIC-side and waits; a
   BASIC-less C-BIOS does not need it.

The free-space figures on this page are dated; re-run `make basic-reloc` before relying on one.
