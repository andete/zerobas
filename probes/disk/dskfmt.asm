; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; DSKFMT.COM -- D-DSKFMT (TODO.md): what the disk ROM's CHOICE ($4019) offers and
; what DSKFMT ($401C) writes, called directly under MSX-DOS through CALSLT with the
; disk interface's slot from $FB22 (dskent.asm's way). It FORMATS drive A -- the
; harness runs it on a throwaway copy of the boot image; this program is already in
; RAM. Captured:
;   $0400  codes: CHOICE's HL (2), DSKFMT's A, Cy, B (3), then each DSKIO read's
;          A, Cy (2 x 8)
;   $0440  the choice string (128 B, read with RDSLT; $EE = not reached)
;   $04C0  sectors 0..7 read back through DSKIO (4 KB; the media byte for the reads
;          taken from the new boot sector)
; Self-loop at `done` -- the disk_probe_diff.py capture anchor.
;
; CLEAN-ROOM: 100% own code; the published disk-ROM interface (CHOICE / DSKFMT /
; DSKIO register contracts), CALSLT / RDSLT and $FB22. No ROM byte is read except
; the choice string, which the published CHOICE hands out for display.
;
; Build: pasmo --bin dskfmt.asm dskfmt.com dskfmt.sym

                org     $0100

RDSLT           equ     $000C
CALSLT          equ     $001C
DSKSLT          equ     $FB22
WORK            equ     $2000                   ; DSKFMT's work area (TPA)

start:
                ld      ix, $4019               ; CHOICE
                call    xcall
                ld      (codes+0), hl
                ld      a, h
                or      l
                jr      z, fmt
                ld      de, choice
                ld      b, 128
cs_lp:                                          ; the string, through RDSLT
                push    bc
                push    de
                push    hl
                ld      a, (DSKSLT)
                call    RDSLT
                ei
                pop     hl
                pop     de
                pop     bc
                ld      (de), a
                inc     de
                inc     hl
                or      a
                jr      z, fmt
                djnz    cs_lp
fmt:
                ld      a, (fchoice)            ; the choice (build_dskfmt_disk.py --choice)
                ld      d, 0                    ; drive A
                ld      hl, WORK
                ld      bc, $2000
                ld      ix, $401C               ; DSKFMT
                call    xcall
                ld      (codes+2), a
                ld      a, 0
                rla                             ; Cy -> bit 0
                ld      (codes+3), a
                ld      a, b
                ld      (codes+4), a
                ld      a, $F9                  ; sector 0 with a 2DD guess first
                ld      (media), a
                ld      de, 0
                ld      hl, sectors
                ld      iy, codes+5
rd_lp:
                push    de
                push    hl
                push    iy
                ld      a, (media)
                ld      c, a
                xor     a                       ; drive A, Cy = 0: read
                ld      b, 1
                ld      ix, $4010               ; DSKIO
                call    xcall
                pop     iy
                ld      (iy+0), a
                ld      a, 0
                rla
                ld      (iy+1), a
                inc     iy
                inc     iy
                pop     hl
                pop     de
                ld      a, e
                or      a
                jr      nz, rd_next
                ld      a, (sectors+$15)        ; after sector 0: the new media byte
                ld      (media), a
rd_next:
                ld      bc, 512
                add     hl, bc
                inc     de
                ld      a, e
                cp      8
                jr      nz, rd_lp
done:
                jr      done

; xcall -- CALSLT the disk ROM at IX with A / BC / DE / HL as given; flags out.
xcall:
                push    af
                ld      a, (DSKSLT)
                ld      (xslot+3), a        ; IYh: `ld iy,nn` is FD 21 lo hi
                pop     af
                push    iy
xslot:          ld      iy, $0000               ; IYh = the slot (patched above)
                call    CALSLT
                pop     iy
                ei
                ret

media:          db      0
fchoice:        db      1                       ; patched by the builder

; ---------------------------------------------------------------------------
; captured block $0400-$14BF
; ---------------------------------------------------------------------------
                ds      $0400 - $, $00
codes:          ds      64, $EE
choice:         ds      128, $EE
sectors:        ds      8*512, $EE
