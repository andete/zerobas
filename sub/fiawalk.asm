; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; fiawalk.asm -- fat_io_append's resume-point tail as a fatprim-tenant row
; (DISKOP_SEL_FIA_WALKED). docs/spec-eviction-g7-space.md, carve 2.
;
; No new tenant index: it joins the existing page-1 fatprim tenant's fp_table,
; exactly as the G4 eviction's fat_rand_* rows did. The body (basic/fiawalked-
; body.inc, shared verbatim with the lean cart) touches only FAT_*/FWR_* RAM and
; FSECTOR_BUF and calls nothing, so there is no marshalling beyond the fp_stash
; convention -- and since every path returns Cy = 0, only the ok tail is reachable.
;
; Clean-room: our own code, relocated. No disassembly.

t_fia_walked:
                call    fia_walked
                jp      fp_stash_ok

                include "basic/fiawalked-body.inc"
