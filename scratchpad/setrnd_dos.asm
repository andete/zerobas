; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; SETRND.COM -- D-BDOSFCB residual (2): MSX-DOS's own SETRND ($24 through $0005) for
; controlled FCB fields, the same ten rows as scratchpad/setrnd_probe.py's $F37D ones.
; Makes R.DAT (4 records of 128 B), closes, reopens, then per row: RS (+14..15), the
; previous RR (+33..36), EX (+12), CR (+32), +24, +13 as given, SETRND, and stores
; A and RR (+33..36) -- 5 bytes a row from $0400. $A5 at $04F0 before `done`.
; CLEAN-ROOM: 100% own code; the published BDOS contract.
;
; Build: pasmo --bin setrnd_dos.asm setrnd.com setrnd.sym

                org     $0100
BDOS            equ     $0005
CAPT            equ     $0400

start:
                ld      de, fcb
                ld      c, $16
                call    BDOS                    ; FMAKE
                ld      b, 4
mk_lp:
                push    bc
                ld      de, fcb
                ld      c, $15
                call    BDOS                    ; SEQWRITE (the DTA at $0080, whatever is there)
                pop     bc
                djnz    mk_lp
                ld      de, fcb
                ld      c, $10
                call    BDOS                    ; FCLOSE
                xor     a
                ld      (fcb+12), a
                ld      (fcb+32), a
                ld      de, fcb
                ld      c, $0F
                call    BDOS                    ; FOPEN
                ld      hl, rows
                ld      de, CAPT
row_lp:
                ld      a, (hl)
                cp      $FF
                jr      z, fin
                push    de
                ld      (fcb+14), a             ; RS low
                xor     a
                ld      (fcb+15), a
                inc     hl
                ld      a, (hl)
                ld      (fcb+33), a             ; the previous RR
                xor     a
                ld      (fcb+34), a
                ld      (fcb+35), a
                ld      (fcb+36), a
                inc     hl
                ld      a, (hl)
                ld      (fcb+12), a             ; EX
                inc     hl
                ld      a, (hl)
                ld      (fcb+32), a             ; CR
                inc     hl
                ld      a, (hl)
                ld      (fcb+24), a
                inc     hl
                ld      a, (hl)
                ld      (fcb+13), a
                inc     hl
                push    hl
                ld      de, fcb
                ld      c, $24
                call    BDOS                    ; SETRND
                pop     hl
                pop     de
                ld      (de), a
                inc     de
                push    hl
                ld      hl, fcb+33
                ld      bc, 4
                ldir
                pop     hl
                jr      row_lp
fin:
                ld      a, $A5
                ld      ($04F0), a
done:
                jr      done

; RS, previous RR, EX, CR, +24, +13 -- the $F37D probe's ten SETRND rows ($FF ends)
rows:
                db      128, 7, 0, 0, $40, 0
                db      128, 7, 0, 1, $40, 0
                db      128, 7, 0, 2, $40, 0
                db      128, 7, 0, 5, $40, 0
                db      128, 7, 1, 0, $40, 0
                db      128, 7, 1, 3, $40, 0
                db      128, 7, 0, 2, 0, 0
                db      128, 7, 0, 2, 0, 1
                db      1, 7, 0, 2, 0, 1
                db      128, $77, 0, 2, 0, 1
                db      $FF
fcb:            db      0, "R       DAT"
                ds      26, 0
