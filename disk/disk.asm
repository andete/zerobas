; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-disk — disk.asm
; ===========================================================================
; A clean-room MSX1 disk-interface ROM. Standalone 16 KB ROM that lives in an
; internal expansion slot (slot 3-1, page 1, $4000-$7FFF) on a built-in-disk
; MSX1. See README.md and disk/PROVENANCE.md.
;
; CLEAN-ROOM DISCIPLINE: every constant, address, and algorithm here traces to
; an allowed source (MSX2 Technical Handbook, the FDC datasheet, Microsoft FAT
; spec, ECMA-107, openMSX/C-BIOS sources, or this project's own black-box
; oracle observations). Nothing is derived from any disk-ROM or MSX-BASIC
; disassembly. See disk/PROVENANCE.md.
;
; FDC NOTE: the CF-3300's actual FDC is the Fujitsu MB8877A; it is WD179x-family
; compatible, so the WD2793 datasheet is a faithful compatible-family reference
; for the identical command/status register interface (oracle-validated
; byte-identical to the real CF-3300). openMSX models this FDC as a WD2793.
; "WD2793" below refers to that compatible interface, not a different chip.
;
; Runtime model: this is an "AB" disk-interface ROM. At boot the BIOS finds the
; header at $4000 and calls INIT, which (1) installs the standard HPHYD ($FFA7)
; -> DSKIO ($4010) inter-slot hook so a real MSX-BASIC / MSX-DOS host can drive
; us via PHYDIO (the Phase-1.5 PROVIDER surface), and (2) publishes the BDOS
; entry point via the SYSTEM ($F37D) sysvar (and seeds the default DTA), then
; returns to the BIOS boot scan. zerobas-BASIC itself reaches the file layer
; through that SYSTEM-vector BDOS entry across slots with CALSLT (the internal
; path) — NOT through the H.* / HPHYD chain; HPHYD exists for FOREIGN hosts. The
; disk subsystem reaches the physical driver through the six fixed-offset entry
; points at $4010..$401F.
;
; STATUS: INIT installs the HPHYD->DSKIO hook (provider direction) and publishes
; the BDOS entry + DTA default (internal direction). The FDC driver is
; implemented (WD2793, National memory-mapped register map, polled sector read
; AND polled sector write — physical write primitive). The FAT12 read layer is
; implemented (BPB parse, cluster-
; chain walk, root-directory 8.3 search, sequential file-sector read) as
; internal helpers. The BDOS/FCB layer is implemented (bdos_entry dispatches
; Open $0F / Sequential Read $14 / Close $10 on top of the FAT12 helpers); it is
; reached through the SYSTEM vector and is the bridge zerobas's BLOAD path
; calls. GETDPB ($4016) is REAL: it builds a Drive Parameter Block from the
; on-disk BPB for a foreign host (provider direction), field-for-field confirmed
; against a black-box CF-3300 GETDPB trace (see getdpb / disk/PROVENANCE.md §DPB).
; End-to-end disk I/O is implemented and the read + BDOS paths are differentially
; oracle-confirmed (probes/disk/disk_probe_dskio.py / disk_probe_bdos.py).
; ===========================================================================

; ===========================================================================
; Source split into logical parts (§8.71). Assembled with `pasmo -I disk`; each
; part is included verbatim below IN LAYOUT ORDER -- the build is position-
; dependent (ds-anchored canonical kernel addresses + the 16 KB page pad), so the
; include order reproduces the exact byte sequence. Do not reorder.
; ===========================================================================
                include "equates.inc"
                include "init.asm"
                include "pageenv.asm"
                include "driver.asm"
                include "fat.asm"
                include "kernel.asm"
                include "runtime.asm"
