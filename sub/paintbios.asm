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
;   PNTINI   (main's own since D-PNTINIREGS: basic/biosfnk.asm bios_pntini.)
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
;   The fill: the run is COUNTED first and then painted in one NSETCX call from its first
;   pixel (D-SCANSTOP, 2026-11-19) -- SCREEN 2 bytes decided whole, a covered byte pattern
;   $00 / colour ATRBYT; SCREEN 3 the blocks' nibbles. Painting while scanning recoloured a
;   cell's foreground before the scan reached the cell's border pixel.
;   CSAVEA / CSAVEM ($F942 / $F944), where the VG-8020's SCANR records the run's start, are
;   inside zerobas's interrupt trampoline (SUB_INT_RAM, $F92D-$F950): not written (D-SCANRSAVE).
;   BC / A on exit are not the VG-8020's leftovers (no documented contract, origin unread).
;
; The tenant runs through CALSLT into page 1 with slot-0 page 0 still mapped, so it
; uses the BIOS's own cursor family (READC / NSETCX / RIGHTC / LEFTC -- the
; graphics-cursor span, cbios-repack/graphics-cursor.patch) instead of a copy.
; In: C = the op (0 SCANR, 1 SCANL). PNTINI moved to main (basic/biosfnk.asm bios_pntini,
; D-PNTINIREGS 2026-11-19): its registers and interrupt state are kept there.
;
; Clean-room: own design from the black-box measurements above (registers, work-area
; RAM and VRAM read after a direct call); C-BIOS's own versions were bare `ret`s.
; Nothing here is derived from a disassembly or byte-copy of any reference ROM.
; Basis: basic/PROVENANCE.md.

PB_RIGHTC       equ     $00FC
PB_LEFTC        equ     $00FF
PB_READC        equ     $011D
PB_NSETCX       equ     $0123

paint_tenant:
                dec     c
                jr      z,pb_scanl              ; (PNTINI is main's own since D-PNTINIREGS)
pb_scanr:
                ld      hl,0
pb_skip:
                call    pb_isbd
                jr      nz,pb_run
                dec     de
                ld      a,d
                or      e
                ret     z                       ; the skip count used up: HL = 0
                call    pb_right
                jr      nc,pb_skip
                ret
; D-SCANSTOP (2026-11-19): COUNT the run first, THEN paint it -- as the VG-8020 (docs/bios/
; SCANR.md R-SR-SCAN / R-SR-PAINT). Painting pixel by pixel while scanning recoloured a
; cell's foreground to ATRBYT before the scan reached that cell's border pixel, so a
; border drawn in a cell's foreground colour was read as paint and the run went on.
pb_run:
                push    de                      ; DE back as the skip left it
                ld      de,(CLOC)
                ld      a,(CMASK)
                ld      c,a                     ; DE / C = the run's first pixel
pb_cnt:
                inc     hl
                call    pb_right
                jr      c,pb_rend               ; the screen's edge: stay on its last pixel
                call    pb_isbd
                jr      nz,pb_cnt               ; (the cursor is left ON the border)
pb_rend:
                ld      a,(SCRMOD)
                cp      3
                jr      z,pb_rpaint             ; SCREEN 3 always fills
                ld      a,b
                or      a
                jr      z,pb_rout               ; SCREEN 2 without the fill switch
pb_rpaint:
                ld      b,c
                call    pb_paint
pb_rout:
                pop     de
                ret

pb_scanl:
                ld      hl,0
pb_lft:
                call    pb_left
                jr      c,pb_lend               ; the screen's edge: on the last counted one
                call    pb_isbd
                jr      z,pb_lbd
                inc     hl
                jr      pb_lft
pb_lbd:
                call    PB_RIGHTC               ; a border: back on the last counted one
pb_lend:
                ld      de,(CLOC)               ; always fills, from the leftmost counted pixel
                ld      a,(CMASK)               ; (D-SCANLPAINT: the VG-8020 paints HL + K there,
                ld      b,a                     ;  K the last SCREEN 2 SCANR's run -- open)
                jp      pb_paint

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

; Paint HL pixels (blocks) in ATRBYT from DE / B (a CLOC / CMASK), as NSETCX sets them (a
; whole byte: pattern $00, colour ATRBYT); the cursor, HL and DE kept, B lost. HL 0: nothing
; (NSETCX's HL 0 would still rewrite the colour byte).
pb_paint:
                ld      a,h
                or      l
                ret     z
                push    hl
                push    de
                ld      a,(CMASK)
                push    af
                ld      a,b
                ld      (CMASK),a
                ld      bc,(CLOC)
                push    bc                      ; the cursor now
                ld      (CLOC),de
                call    PB_NSETCX
                pop     hl
                ld      (CLOC),hl
                pop     af
                ld      (CMASK),a
                pop     de
                pop     hl
                ret
