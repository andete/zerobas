; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; title-body.inc — the startup-header body, shared by both builds.
; ===========================================================================
; Extracted from basic/title.asm so the SAME source serves two homes (the
; casmatch-body.inc / cal-refill-body.inc precedent):
;
;   * (retired) the lean 16 KB cart, included at its original position in
;     basic/title.asm;
;   * repack build: included by sub/title.asm instead, as the
;     sub-ROM PAGE-1 tenant SUBROM_IDX_TITLE, freeing main-ROM page-1 tail space
;     to fund the input-devices I2 slice (docs/spec-basic-input-devices.md §9.5).
;
; Page-1 tenancy is the right one here: the only outward edges are INITXT and
; CHPUT, which are page-0 BIOS — visible from a page-1 tenant, NOT from a page-0
; one. No arguments, no return value, no RAM state: the simplest tenant shape in
; the tree, and the only one so far that needs no absent-sub-ROM error path (a
; cosmetic header that silently does not print is a fine degradation).
;
; Uses only documented BIOS entry points (INITXT, CHPUT); no disassembly.
; ===========================================================================
show_title:
                call    INITXT          ; SCREEN 0 text mode + display on
                ld      hl,banner_text
st_loop:
                ld      a,(hl)
                or      a
                ret     z               ; 0x00 ends the header
                push    hl              ; guard HL across the BIOS call
                call    CHPUT
                pop     hl
                inc     hl
                jr      st_loop

; Left-aligned from the home position. 13/10 = CR/LF (CHPUT: 0x0D = start of
; line, 0x0A = next line). A trailing blank line separates the header from
; whatever the interpreter does next, as on a booted MSX.
banner_text:
                db      "zerobas version 0.1",13,10
                db      "clean-room MSX-BASIC program loader",13,10,13,10
                db      0
