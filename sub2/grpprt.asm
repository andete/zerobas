; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; ===========================================================================
; grpprt_tenant -- one byte of PRINT # to an OPEN "GRP:" channel (D-OPENGRP)
; zerobas-sub2 page-1 index 1 (SUB2_IDX_GRPPRT), reached from main's pchar
; (basic/print.asm pch_grp) through subrom2_call. The FIRST tenant of the
; second sub ROM (D-SUB2 stage d).
;   in:  E = the byte. Main has already refused SCREEN 0/1 (ERR 5).
;   out: nothing; GRPACX/GRPACY moved. Clobbers everything (it is a CALSLT).
;
; THE RULE, ALL OF IT MEASURED ON THE VG-8020 (TODO.md D-OPENGRP, rounds 1-5;
; scratchpad/opengrp*_probe.out):
;   * CHR$(32..255): the font glyph at the graphic cursor (GRPACX, GRPACY),
;     each 1 bit set exactly as PSET sets a pixel in FORCLR -- round 4 drew a
;     glyph both ways over clashing 8x1 colour cells and read every pixel back
;     identical -- and 0 bits left alone (transparent). Then the cursor moves
;     8 right. SCREEN 3: every bit is a 4x4 block (PSET there sets the block),
;     the pitch is 4 and the advance 32.
;   * x reaching 256 -> x 0 and down one line; y reaching 192 -> y 0. A glyph
;     that crosses the right or bottom edge is clipped, not moved.
;   * CHR$(13): x 0, down one line (8 / 32). Every other code below 32 -- LF
;     and CLS's 12 included -- is ignored.
;   * CHR$(1) is a header, consumed by the next byte: a byte in 64..95 then draws
;     glyph byte-64 (`CHR$(1);"A"` is the smiley, glyph 1); ANY other byte acts
;     as if no header came -- a control code acts (CR is a new line), 32..63
;     and 96..255 draw themselves (round 6: "0", "?", "`" and 255 measured).
; HOW: each 1 bit is ONE CALL OF THE GRAPHICS TENANT'S OWN PLOT (ROM 1 page 0,
; GFX_OP 1, the routine PSET uses), by a nested CALSLT straight from here --
; the BIOS is page 0 while a page-1 tenant runs -- ROM 2 page 1 -> ROM 1 page
; 0, under DI as subrom_call makes it. NOT through main's sr_inl0: that drags
; its whole static call graph (the absent-ROM print path among it) into the
; resident closure, which the closure gate rightly refuses. So the colour-clash
; rule is PSET's by construction, not a second copy of it; the cost is a slot
; crossing per lit pixel (TIER 5 business, not this item's).
; The clip is the plot's own precondition (gfx_in_range's: x 0..255, y 0..191,
; checked on the 16-bit value) -- the tenant must never be handed an
; off-screen GXPOS (basic/graphics.asm, the D-GIRDOM2 note).
; CLEAN-ROOM: own design; the behaviour is measured, the font is read through
; the published CGPNT pointer. No reference code read.
; ===========================================================================
grpprt_tenant:
                ld      a,(SCRMOD)
                and     1                   ; 0 = SCREEN 2, 1 = SCREEN 3
                ld      c,a
                add     a,a
                add     a,c
                inc     a
                ld      c,a                 ; C = the pixel pitch S: 1 or 4
                ld      b,0                 ; BC = S, for 16-bit adds
                ld      hl,GRP_HDR
                ld      a,e
                bit     0,(hl)              ; a CHR$(1) header pending?
                ld      (hl),b              ; any next byte consumes it
                jr      z,gp_plain
                cp      64                  ; only 64..95 are graphic-glyph codes:
                jr      c,gp_plain          ; below, the byte is itself (a control
                cp      96                  ; acts, 32..63 draws itself) -- above,
                jr      nc,gp_plain         ; it draws itself too (round 6)
                sub     64                  ; header + 64..95 -> glyph 0..31
                jr      gp_glyph
gp_plain:
                cp      32
                jr      nc,gp_glyph
                cp      13
                jr      z,gp_cr
                dec     a
                ret     nz                  ; every other control code: ignored
                inc     (hl)                ; CHR$(1): arm the header
                ret

gp_glyph:
                push    bc                  ; S, for the advance below
                ld      l,a
                ld      h,b
                add     hl,hl
                add     hl,hl
                add     hl,hl               ; the glyph's offset, 8 bytes each
                ld      de,(CGPNT+1)        ; the font (main ROM, page 0: visible
                add     hl,de               ; from a page-1 tenant)
                ld      a,1
                ld      (GFX_OP),a          ; the plot (PSET's op)
                ld      a,(FORCLR)
                ld      (GFX_C),a           ; in the foreground colour
                ld      de,(GRPACY)         ; DE = the row's y
                ld      b,8
gp_row:
                push    bc                  ; B = rows left, C = S
                push    hl                  ; the glyph row's address
                ld      a,(hl)              ; its 8 bits, MSB = leftmost
                ld      hl,(GRPACX)         ; HL = the pixel's x
                ld      b,0
gp_bit:
                add     a,a                 ; CF = this pixel's bit
                jr      nc,gp_next
                push    af
                push    bc
                push    de
                push    hl
                ld      a,h
                or      d
                jr      nz,gp_clip          ; x or y outside 0..255 (or negative)
                ld      a,e
                cp      192
                jr      nc,gp_clip          ; below the screen
                ld      (GXPOS),hl
                ld      (GYPOS),de
                ld      a,(SUBSLOT)         ; ROM 1 (3-2): the graphics tenant
                ld      h,a
                ld      l,0
                push    hl
                pop     iy                  ; IYh = its slot (the CALSLT ABI)
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_GRAPHICS
                di                          ; as subrom_call: the plot's lean VDP
                call    CALSLT              ; access must not race the ISR
gp_clip:
                pop     hl
                pop     de
                pop     bc
                pop     af
gp_next:
                add     hl,bc               ; x += S
                or      a
                jr      nz,gp_bit           ; until no lit bit is left in the row
                ex      de,hl
                add     hl,bc               ; y += S
                ex      de,hl
                pop     hl
                inc     hl                  ; the next glyph row
                pop     bc
                djnz    gp_row
                pop     bc                  ; C = S
                ; --- advance: x += 8*S; reaching 256 is a new line ------------
                ld      a,c
                add     a,a
                add     a,a
                add     a,a                 ; 8 * S
                ld      hl,(GRPACX)
                add     a,l
                ld      l,a
                jr      nc,gp_xs
                inc     h
gp_xs:
                ld      (GRPACX),hl
                ld      a,h
                or      a
                ret     z                   ; still on the line
                ; falls into the new line
gp_cr:
                ld      hl,0
                ld      (GRPACX),hl
                ld      a,c
                add     a,a
                add     a,a
                add     a,a                 ; 8 * S
                ld      hl,(GRPACY)
                add     a,l
                ld      l,a
                jr      nc,gp_ys
                inc     h
gp_ys:
                ld      a,h
                or      a
                jr      nz,gp_top
                ld      a,l
                cp      192
                jr      c,gp_sty            ; y reaching 192 wraps to the top
gp_top:
                ld      hl,0
gp_sty:
                ld      (GRPACY),hl
                ret
