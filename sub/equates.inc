; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — equates.inc
; ===========================================================================
; Shared constants for the built-in MSX2-style sub-ROM (docs/spec-basic-subrom.md).
; ===========================================================================

; --- Entry-table bases (the $4010-style fixed dispatch contract, §3c/D-5) -----
; One append-only `jp` table per page; a tenant is addressed by
; IX = base + 3*index. Page 0 tenants see main BASIC (slot-0 page 1) but not the
; BIOS and run under DI; page 1 tenants see the BIOS but not main BASIC. The two
; pages are opposite islands (§3b). Entry 0 of each is the S2a round-trip PING.
SUBROM_ENTRY_BASE_P0    equ     $0010   ; page-0 table (clear of the CD header)
SUBROM_ENTRY_BASE_P1    equ     $4010   ; page-1 table (mirrors the $4010 disk DSKIO)

; --- S2a boot-gate scratch (page-3 RAM, visible from either sub-ROM page) ------
; The skeleton PING tenants write a page-tag byte here so the boot-gate probe can
; confirm a CALSLT to each entry round-tripped through the correct page. This is
; a fixed own-choice RAM cell in the repack-only free window ($F105, right after
; the float pack's last claim PLF_RA2 $F103 and below zerobas-disk's DRVA_DPB
; $F195 — see basic/sysvars.inc). S2a proves the mechanism by injection, so the
; main ROM does not yet reference this cell; S2b's dispatch stub will formalise
; the SUB_ARG/result marshalling block that starts here.
SUB_PING                equ     $F105   ; PING page tag: $C0 (page 0) / $C1 (page 1)
SUB_PING_P0             equ     $C0     ; written by the page-0 ping
SUB_PING_P1             equ     $C1     ; written by the page-1 ping
