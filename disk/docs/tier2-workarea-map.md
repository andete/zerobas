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
| `$F100-$F17C` | **executable RAM-resident routines** (Z80 code; e.g. `call $F16F`, inter-slot helpers) | `$FF` |
| `$F1A8-$F1C8` | **drive-A DPB + drive table** (`95 E5 01 F9 00 02 0F 04 …` = BPB-derived DPB) | `$FF` |
| `$F1C9-$F1FE` | DOS resident code + struct (`CD 6B F3 … ED B0 …` calls the `$F36B` page switch) | mostly `$FF` |
| `$F21C-$F22B` | **device-name table** `PRN LST NUL AUX CON` | `$FF` |
| `$F2B8-$F2E0` | **resident `COMMAND COM` FCB + DPB** (`06 "COMMAND COM" …`) | `$FF` |
| `$F2FF-$F322` | DOS flags/counters (mostly `00`, a few set) | `$FF` |
| `$F327-$F33F` | **executable code** (`3E 1A C9 …`) + flags incl. **`$F338`=00** | `$FF` |
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

## 6. Provenance

Black-box oracle observation only (snapshot/diff/watch memory; override registers to isolate
dependencies). No disassembly of the disk ROM, MSXDOS.SYS, or COMMAND.COM. Probes:
`disk_probe_dosboot_{wadiff,fopenoverride,fopenromcalls,bdosseq,bdoscallers}.py`. Oracle disk
`~/Documents/msx/msx/disks/msxdos103-cmd111.dsk` (md5 `7bf624375473e76c9eddb683da174faa`), run on a
`/tmp` copy (one path mutated the copy — always restore from canonical; the canonical was untouched).
