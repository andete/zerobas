<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 — the MSX-DOS-1 DOS work area ($F100-$F3FF) the disk ROM builds at boot

**Status:** characterisation, 2026-06-26. The defining finding of the DOS-boot hunt. Also a
documentation deliverable (clean-provenance map of an undocumented internal — dual mission).

## 1. What this is

To boot genuine MSX-DOS 1 to `A>`, the disk ROM constructs a large **DOS work area** in page-3 RAM
(`$F100-$F3FF`) during boot — executable RAM-resident routines, the DPB and drive table, device
names, the resident-command FCB area, and a block of DOS pointers. The relocated MSXDOS.SYS kernel
and COMMAND.COM read this area directly and call routines inside it. **zerobas-disk does not build
it** (the regions are `$FF`/padding/stubs), which is why COMMAND.COM derails on startup.

Evidence: `disk_probe_dosboot_wadiff.py` snapshots `$F100-$F3FF` at the COMMAND.COM `$0100` entry on
ours vs the National_CF-3300 oracle. **462 of 768 bytes differ; ours is almost entirely `$FF`.**
This was reached by following one symptom to ground: COMMAND.COM does `ld a,($F338)` at `$C26B` and
branches on it (stock `$00`, ours `$FF`); a write-watch showed stock writes `$F338=00` from
`PC=$57BE` at boot time (t≈3.8 s), ours never does (`$57BE` is `00` padding in our ROM). `$F338`
turned out to be just one byte of the whole unbuilt area.

## 2. Map of the area (stock contents at COMMAND.COM entry, black-box)

All addresses oracle-observed; contents summarised, never disassembled into source.

| region | stock content (observed) | ours |
|--------|--------------------------|------|
| `$F100-$F17C` | **executable RAM-resident routines** (inter-slot / driver-dispatch helpers that call into `$F16F` etc.) | `$FF` |
| `$F1A8-$F1C8` | **drive-A DPB + drive table** (`95 E5 01 F9 00 02 0F 04 …` = BPB-derived DPB) | `$FF` |
| `$F1C9-$F1FE` | DOS resident code + a struct; the routine invokes the `$F36B` page-switch hook and performs a block copy | mostly `$FF` |
| `$F21C-$F22B` | **device-name table** `PRN LST NUL AUX CON` | `$FF` |
| `$F2B8-$F2E0` | **resident `COMMAND COM` FCB + DPB** (`06 "COMMAND COM" …`) | `$FF` |
| `$F2FF-$F322` | DOS flags/counters (mostly `00`, a few set) | `$FF` |
| `$F327-$F33F` | **small executable routines** plus flags including **`$F338`=00** | `$FF` |
| `$F345`,`$F347` | small DOS params (`07`, `02`) | `$FF` |
| `$F34D-$F37F` | **DOS pointer block** — drive-DPB pointers (`95 EF 95 ED 95 EB`), hook/segment-switch vectors (`$F369`=`57 DF`, …) | ours has its OWN pointers ($E795/$E79B wa_seg, $41B0) — i.e. ours built a *different, partial* set |
| `$F3DC` | CSRY cursor row (4 vs 12) | benign |

(The `$F100` block low bytes `… 6E F1 77 F2 00 …` and the `$F34D` pointers show the area is
self-referential: resident routines + a pointer table into them + the device/DPB structures.)

## 3. Why earlier framings were too small

- **"Fix FOPEN ($21→$FF)"** — a red herring: COMMAND.COM doesn't branch on the FOPEN return
  (register-override proved it, `disk_probe_dosboot_fopenoverride.py`); it branches on `$F338`,
  a work-area cell set at boot.
- **"Intercept $0005 → our BDOS" (fork B)** — even a complete BDOS doesn't help if COMMAND.COM and
  the kernel read this work area *directly* (they do: `$F338`, and presumably the resident routines
  and structures). The viability gate (kernel never re-enters via `$0005`) still holds, but the
  premise that a register-level intercept suffices is false.
- **"Reproduce the $4462 FOPEN chain" (fork A)** — necessary for file ops, but the work area is
  built *before* FOPEN at boot; FOPEN is downstream of it.

## 4. The real scope

Reaching `A>` requires reproducing the **disk-ROM-resident DOS-work-area construction**: the boot
step(s) that build `$F100-$F3FF` (resident routines + DPB/drive table + device names + resident-FCB
area + the pointer block). This is the disk-ROM-resident portion of the shared MSX-DOS-1 kernel —
a large, multi-milestone sub-system, not a single veneer. It is well-bounded (the area is fixed at
`$F100-$F3FF`; the construction runs at boot), and much of it is documented MSX disk-work-area
layout (drive table, DPB, device names, hooks), though the resident *code* blocks need black-box
contract characterisation.

## 5. Strategic options (for the user)

1. **Bank as documentation + pause the build.** We have mapped, clean-room, exactly how MSX-DOS
   boot builds the DOS work area and why ours stops — a real deliverable (dual mission). Pause the
   "reach A>" implementation, which is now known to be large.
2. **Commit to the build.** Characterise the construction region-by-region and build it in the disk
   ROM (resident routines + structures + pointers), net-zero, clean-room.
3. **Characterise the construction first.** Map exactly which boot code builds each region on stock
   (write-watch the whole `$F100-$F3FF` across boot), to size option 2 precisely before committing.

## 5a. Construction map (how stock builds it — sized build plan)

Write-watch of all writes to `$F100-$F3FF` across stock's boot (`disk_probe_dosboot_wabuild`,
last-writer-per-byte): **96 distinct disk-ROM writer routines, in 4 time-phases**, build the area.

| phase | t (s) | bytes finalised | what is built | example writer PCs |
|-------|-------|-----------------|---------------|--------------------|
| 1 | ~3.8 | 335 | clear/default pass: zeros + `$C9`-fill of the hook-stub table `$F24F-$F2B7` | `$57BE`, `$57D6`, `$57E0` |
| 2 | ~6.9 | 201 | DPB+drive table `$F195-$F1BC`; **resident code** `$F1C9-$F236` + `$F327-$F335`; segment-switch hook vectors `$F368-$F37F` (`C3 lo hi` jump table); drive-DPB pointers `$F34D-$F352` (`95 EF / 95 ED / 95 EB`) | `$588A`, `$58B8`, `$5935`, `$5960`, `$58F0`, `$5C7F` |
| 3 | ~9.9-10.5 | 221 | **resident routines** `$F100-$F17C`; the `COMMAND COM` FCB+DPB `$F2B8`; FCB/struct cells `$F2DC-$F2FD` | `$7958`, `$78A7`, `$7973/5`, `$4354`, `$5667`, `$4418` |
| 4 | ~11.3 | 11 | final cells at COMMAND.COM entry | `$74C5`, `$74CD`, `$4A6E` |

`$F380-$F3FF` is mostly the **standard disk-ROM hook/hardware area** (written early by `$7C9C` at
t≈1.2, plus BIOS console cells `$F3DC` CSRY etc.) — largely the documented MSX disk work area, less
DOS-specific.

**Effort breakdown for reproducing this (the sized plan):**
1. **Phase-1 clear/default** — easy: a memset-zeros + `$C9`-fill pass over the work area at boot.
2. **Structural data** — moderate, much already exists: DPB+drive table (we have real GETDPB,
   CF-3300-byte-identical), device-name table (`PRN LST NUL AUX CON`, static), the hook/segment-
   switch vector table `$F368-$F37F` and drive-DPB pointers (structural; some map to our wa_seg),
   the `COMMAND COM` resident FCB (static + DPB).
3. **Resident CODE blocks** — the hard core (~250 bytes): the executable routines at `$F100-$F17C`,
   `$F1C9-$F236`, `$F327-$F33F` that DOS calls directly (inter-slot/paging helpers around
   `$F368/$F36B`). Each needs black-box contract characterisation, then a clean-room reimplementation
   placed/copied into the work area at boot. This is the bulk of the build and the bulk of the risk.

**Net assessment:** a bounded but substantial multi-milestone sub-system — effectively the disk-ROM-
resident MSX-DOS-1 kernel. Phases 1–2 structural work is tractable and overlaps existing code;
phase-3 resident-code reproduction is the major effort. A reasonable build order is 1 → 2 → 3, with
the wadiff probe as the region-by-region acceptance test.

## 6. Provenance

Black-box oracle observation only (snapshot/diff/watch memory; override registers to isolate
dependencies). No disassembly of the disk ROM, MSXDOS.SYS, or COMMAND.COM. Probes:
`disk_probe_dosboot_{wadiff,fopenoverride,fopenromcalls,bdosseq,bdoscallers}.py`. Oracle disk
`~/Documents/msx/msx/disks/msxdos103-cmd111.dsk` (md5 `7bf624375473e76c9eddb683da174faa`), run on a
`/tmp` copy (one path mutated the copy — always restore from canonical; the canonical was untouched).
