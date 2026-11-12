; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
; paintbios.asm -- PNTINI ($0129) / SCANR ($012C) / SCANL ($012F), PAINT's published
; BIOS helpers, as one zerobas-sub PAGE-1 tenant (SUBROM_IDX_PAINT) behind the
; page-0 stub bios_pntini / bios_scanl / bios_scanr (basic/biosfnk.asm). D-BIOSRUNG,
; 2026-11-12: C-BIOS's three were bare `ret`s.
;
; Behaviour measured on the Philips VG-8020 (MSX1), called directly with the cursor
; placed by MAPXYC (zerobas scratchpad/paintbios_probe.py, paintbios_run.out ..
; paintbios_run10.out; TODO.md D-BIOSRUNG). Black-box: registers, work-area RAM, VRAM.
;   PNTINI   GFX_B (BDRATR, $FCB2) := A in SCREEN 3; in SCREEN 2 := ATRBYT (the
;            border IS the paint colour there, A is ignored).
;   SCANR    B = the fill switch (SCREEN 2; SCREEN 3 always fills), DE = the skip
;            count. While the pixel at the cursor is border-coloured: DE -= 1, stop
;            with HL = 0 when it reaches 0, else step right. Then count (HL) and fill
;            pixels up to the next border pixel, the cursor left ON it; at x 255
;            (block 63) with no border the cursor stays on the last pixel. DE back
;            as left by the skip.
;   SCANL    Always fills, from the pixel LEFT of the cursor (the start excluded) to
;            the next border pixel; the cursor left on the LAST FILLED pixel
;            (unmoved when the first one is a border); stops on x 0 / block 0. HL =
;            the count.
;   The fill, SCREEN 2: per pixel as SETC (the pattern bit set, the colour byte
;   ATRBYT << 4 | background); a byte the run covers WHOLLY becomes pattern $00,
;   colour byte = ATRBYT (the foreground cleared, measured over $C4).
;   SCREEN 3: per block as SETC (the nibble under CMASK).
;   BC / A on exit are not the VG-8020's leftovers (B the last partial mask, C $05
;   in SCREEN 2; BC $0F01 in SCREEN 3 -- no documented contract, origin unread).
;
; The tenant runs through CALSLT into page 1 with slot-0 page 0 still mapped, so it
; uses the BIOS's own cursor family (READC / SETC / RIGHTC / LEFTC -- the
; graphics-cursor span, cbios-repack/graphics-cursor.patch) instead of a copy.
; In: C = the op (0 SCANR, 1 SCANL, 2 PNTINI with the caller's A in B).
;
; Clean-room: own design from the black-box measurements above (registers, work-area
; RAM and VRAM read after a direct call); C-BIOS's own versions were bare `ret`s.
; Nothing here is derived from a disassembly or byte-copy of any reference ROM.
; Basis: basic/PROVENANCE.md.

PB_RIGHTC       equ     $00FC
PB_LEFTC        equ     $00FF
PB_READC        equ     $011D
PB_SETC         equ     $0120

paint_tenant:
                dec     c
                jr      z,pb_scanl
                dec     c
                jr      nz,pb_scanr
                ld      a,(SCRMOD)              ; PNTINI
                cp      3
                ld      a,b
                jr      z,pb_bd                 ; SCREEN 3: the border is A
                ld      a,(ATRBYT)              ; else the paint colour
pb_bd:
                ld      (GFX_B),a
                ret

pb_scanr:
                ld      c,$01                   ; a byte is whole at its last pixel
                ld      hl,0
pb_skip:
                call    pb_isbd
                jr      nz,pb_fill
                dec     de
                ld      a,d
                or      e
                ret     z                       ; the skip count used up: HL = 0
                call    pb_right
                jr      nc,pb_skip
                ret
pb_fill:
                inc     hl
                call    pb_set
                call    pb_right
                ret     c                       ; the screen's edge: stay on it
                call    pb_isbd
                jr      nz,pb_fill
                ret                             ; on the border

pb_scanl:
                ld      bc,$0180                ; always fills; whole at the first pixel
                ld      hl,0
pb_lft:
                call    pb_left
                ret     c                       ; the screen's edge
                call    pb_isbd
                jp      z,PB_RIGHTC             ; a border: back on the last filled one
                inc     hl
                call    pb_set
                jr      pb_lft

; Z iff the pixel at the cursor is the border colour. HL / DE / BC kept.
pb_isbd:
                call    PB_READC
                push    hl
                ld      hl,GFX_B
                cp      (hl)
                pop     hl
                ret

; One pixel (block) right / left; Cy and no move on the screen's last / first one.
pb_right:
                ld      a,(CLOC)
                or      7
                inc     a                       ; Z: CLOC's low byte $F8..$FF, x 248..255
                jr      nz,pb_rgo
                ld      a,(CMASK)
                rrca                            ; bit 0: the byte's last pixel / block
                ret     c
pb_rgo:
                jp      PB_RIGHTC               ; Cy clear (its AND flags)
pb_left:
                ld      a,(CLOC)
                and     $F8
                jr      nz,pb_lgo
                ld      a,(CMASK)
                rlca                            ; bit 7: the byte's first pixel / block
                ret     c
pb_lgo:
                jp      PB_LEFTC

; Fill the pixel at the cursor. B = the fill switch (SCREEN 2 only), C = CMASK at
; the byte's far end in the scan's direction, HL = the count so far. HL / DE / BC kept.
pb_set:
                ld      a,(SCRMOD)
                cp      3
                jp      z,PB_SETC               ; SCREEN 3: always, the block's nibble
                ld      a,b
                or      a
                ret     z                       ; SCANR without the fill switch
                call    PB_SETC
                ld      a,(CMASK)
                cp      c
                ret     nz                      ; not the byte's far end
                ld      a,l
                and     $F8
                or      h
                ret     z                       ; fewer than 8: the byte is partial
                push    hl
                ld      hl,(CLOC)
                xor     a
                call    WRTVRM                  ; whole: the pattern byte cleared ...
                set     5,h
                ld      a,(ATRBYT)
                call    WRTVRM                  ; ... and the colour byte = the paint colour
                pop     hl
                ret
