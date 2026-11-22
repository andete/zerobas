; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; BDOSXC.COM -- D-DISKCONTRACT gap 5 (2026-11-17): what the console functions put ON THE
; SCREEN. strout-acceptance only checks that a text is present; BDOSX9 / BX2 compare
; CONOUT / DIRIO-out's registers, never their output.
;
; The program clears the screen (CONOUT 12), writes through CONOUT ($02) and STROUT ($09)
; -- TAB, BS, CR / LF, a BEL, an ESC Y cursor position -- then copies the screen's name
; table (960 bytes from NAMBAS, read through the VDP's ports by our own code) plus
; LINLEN / CSRY / CSRX into RAM, and loops. The capture is
; that RAM, diffed against the stock CF-3300.
;
; CLEAN-ROOM: 100% own code; the BDOS / BIOS entries and the work-area cells are the
; published MSX interface. Nothing of the reference read.
;
; Build: pasmo --bin bdosxc.asm bdosxc.com bdosxc.sym

                org     $0100

BDOS            equ     $0005
NAMBAS          equ     $F922
LINLEN          equ     $F3B0
CSRY            equ     $F3DC
CSRX            equ     $F3DD

start:
                jr      begin                   ; $0102 = $5A: a distinctive arm signature (a
                db      $5A                     ; $01 here would match boot RAM by chance)
begin:
                ld      hl, text
emit:
                ld      a, (hl)
                cp      $FF                     ; the table's end
                jr      z, emitted
                cp      $FE                     ; $FE <addr>: a STROUT of the $-string there
                jr      z, strout
                push    hl
                ld      e, a
                ld      c, $02                  ; CONOUT
                call    BDOS
                pop     hl
                inc     hl
                jr      emit
strout:
                inc     hl
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                push    hl
                ld      c, $09                  ; STROUT
                call    BDOS
                pop     hl
                jr      emit
emitted:
                ; the screen into RAM through the VDP's own ports (our code, no BIOS): the read
                ; address NAMBAS, then 960 reads. (A CALSLT to the main BIOS's LDIRMV copied
                ; NOTHING on either machine -- the buffer read all zero and so AGREED: XC_*.out.)
                di
                ld      hl, (NAMBAS)
                ld      a, l
                out     ($99), a
                ld      a, h
                and     $3F                     ; read mode: bits 7..6 = 00
                out     ($99), a
                ld      hl, screen
                ld      bc, 960
vread:
                in      a, ($98)
                ld      (hl), a
                inc     hl
                dec     bc
                ld      a, b
                or      c
                jr      nz, vread
                ei
                ld      a, (LINLEN)
                ld      (cells+0), a
                ld      a, (CSRY)
                ld      (cells+1), a
                ld      a, (CSRX)
                ld      (cells+2), a
                ld      a, $A5
                ld      (cells+3), a            ; the run finished
                jp      done

; the text: bytes go out through CONOUT; $FE + an address = STROUT; $FF = the end
text:
                ; The GATED text: what each control code does to the SCREEN. A TAB is only
                ; ever placed after CR LF or printable text: after FF / BS / BEL / an ESC
                ; sequence on the same line our logical column ($F237) counts differently from
                ; the CF-3300's -- filed TODO D-CONCOL (TIER 6) with the rows that measured it
                ; (scratchpad/XC3_stock.out / XC3_ours.out).
                db      12, 13, 10              ; clear the screen; CR LF resets the column
                db      "AB", 9, "C", 13, 10    ; TAB
                db      "XY", 8, "Z", 13, 10    ; BS
                db      "BEL", 7, "!", 13, 10   ; BEL
                db      27, "Y", 32+7, 32+5, "P" ; ESC Y row 7, column 5
                db      13, 10
                db      $FE
                dw      str1
                db      $FE
                dw      str2
                db      $FF
str1:           db      "Hello$"
str2:           db      13, 10, "STROUT", 9, "tab$"

                ds      $0330 - $, $00
done:
                jr      done                    ; the capture anchor, pinned at $0330
                ds      $0340 - $, $00
cells:          ds      4                       ; LINLEN, CSRY, CSRX, $A5
screen:         ds      960
