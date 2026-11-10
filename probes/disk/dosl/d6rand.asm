; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; D6RAND.COM -- D-DOSLADDER rung D6 (TODO.md): a random-access file the way a small
; database uses one. On R.DAT (FMAKE): WRRND records 0..4 (each 128 x its number);
; RDRND record 2; RDRND past the end (record 7: A = 1); WRZER record 9 (a gap of 5..8
; zero-filled); RDRND record 6 (inside that gap); FSIZE; one SEQREAD from record 0
; then SETRND; RDBLK 3 records of 64 bytes from record 4 (RS := 64); WRBLK 2 records
; of 64 bytes at record 30; FCLOSE; FOPEN again and FSIZE.
; Captured, the contract only: every call's A, a 16-bit sum of every block read,
; FSIZE's RR (+33..35), SETRND's RR, RDBLK's HL (records read), the size (+16..19)
; after FCLOSE and after the second FSIZE. No pointer is kept in IX across a BDOS
; call (D4's lesson). Self-loop at `done` -- the capture anchor.
;
; CLEAN-ROOM: 100% own code; the published MSX-DOS 1 BDOS functions.
;
; Build: probes/disk/build_dosl_disk.py --prog d6rand

                org     $0100

BDOS            equ     $0005

                jr      start
                db      $D6                     ; $0102: the capture's arm signature --
                                                ; unique: COMMAND.COM has $02 there, and the
                                                ; first cut's `ld de,buf` armed on it
start:
                ld      de, buf
                ld      c, $1A
                call    BDOS
                ld      de, fcb
                ld      c, $16                  ; FMAKE R.DAT
                call    BDOS
                ld      (cap+0), a
                ; --- WRRND records 0..4 ---------------------------------------------
                xor     a
wr_lp:
                ld      (recno), a
                call    fillbuf
                ld      a, (recno)
                call    setrr
                ld      de, fcb
                ld      c, $22                  ; WRRND
                call    BDOS
                ld      hl, cap+1
                or      (hl)
                ld      (hl), a                 ; every WRRND's A, OR'd
                ld      a, (recno)
                inc     a
                cp      5
                jr      nz, wr_lp
                ; --- RDRND 2, RDRND 7 (past the end) --------------------------------
                ld      a, 2
                call    rdrnd
                ld      (cap+2), a
                ld      (cap+3), hl             ; its sum
                ld      a, 7
                call    rdrnd
                ld      (cap+5), a
                ; --- WRZER 9, then RDRND 6 (in the gap) --------------------------------
                ld      a, 9
                ld      (recno), a
                call    fillbuf
                ld      a, 9
                call    setrr
                ld      de, fcb
                ld      c, $28                  ; WRZER
                call    BDOS
                ld      (cap+6), a
                ld      a, 6
                call    rdrnd
                ld      (cap+7), a
                ld      (cap+8), hl
                ; --- FSIZE ------------------------------------------------------------
                ld      de, fcb
                ld      c, $23
                call    BDOS
                ld      (cap+10), a
                ld      hl, (fcb+33)
                ld      (cap+11), hl
                ld      a, (fcb+35)
                ld      (cap+13), a
                ; --- SEQREAD from 0, SETRND -------------------------------------------
                xor     a
                ld      (fcb+12), a
                ld      (fcb+32), a             ; EX = CR = 0
                ld      de, fcb
                ld      c, $14
                call    BDOS
                ld      (cap+14), a
                ld      de, fcb
                ld      c, $24                  ; SETRND
                call    BDOS
                ld      hl, (fcb+33)
                ld      (cap+15), hl
                ; --- RDBLK 3 x 64 from record 4 ---------------------------------------
                ld      hl, 64
                ld      (fcb+14), hl            ; RS := 64
                ld      a, 4
                call    setrr
                ld      de, big
                ld      c, $1A
                call    BDOS
                ld      de, fcb
                ld      hl, 3
                ld      c, $27                  ; RDBLK
                call    BDOS
                ld      (cap+17), a
                ld      (cap+18), hl            ; records read
                ld      hl, big
                ld      bc, 192
                call    sum
                ld      (cap+20), hl
                ; --- WRBLK 2 x 64 at record 30 ----------------------------------------
                ld      a, 30
                call    setrr
                ld      de, fcb
                ld      hl, 2
                ld      c, $26                  ; WRBLK
                call    BDOS
                ld      (cap+22), a
                ld      de, fcb
                ld      c, $10                  ; FCLOSE
                call    BDOS
                ld      (cap+23), a
                ld      hl, (fcb+16)
                ld      (cap+24), hl
                ld      hl, (fcb+18)
                ld      (cap+26), hl            ; the size after FCLOSE
                ; --- FOPEN again, FSIZE ------------------------------------------------
                ld      hl, fcb0
                ld      de, fcb
                ld      bc, 37
                ldir
                ld      de, fcb
                ld      c, $0F
                call    BDOS
                ld      (cap+28), a
                ld      hl, (fcb+16)
                ld      (cap+29), hl
                ld      hl, (fcb+18)
                ld      (cap+31), hl            ; the size FOPEN reports
done:
                jr      done

; fillbuf -- buf := 128 x (recno)
fillbuf:
                ld      a, (recno)
                ld      hl, buf
                ld      b, 128
fb_lp:
                ld      (hl), a
                inc     hl
                djnz    fb_lp
                ret

; setrr -- the FCB's RR := A (r1 = r2 = 0)
setrr:
                ld      (fcb+33), a
                xor     a
                ld      (fcb+34), a
                ld      (fcb+35), a
                ret

; rdrnd -- RDRND record A into buf (pre-filled $EE); A = its A, HL = the 128-byte sum
rdrnd:
                call    setrr
                ld      hl, buf
                ld      b, 128
rr_fill:
                ld      (hl), $EE
                inc     hl
                djnz    rr_fill
                ld      de, buf
                ld      c, $1A
                call    BDOS
                ld      de, fcb
                ld      c, $21
                call    BDOS
                push    af
                ld      hl, buf
                ld      bc, 128
                call    sum
                pop     af
                ret

; sum -- HL := the 16-bit sum of BC bytes at HL
sum:
                ex      de, hl
                ld      hl, 0
sm_lp:
                ld      a, (de)
                add     a, l
                ld      l, a
                jr      nc, sm_nc
                inc     h
sm_nc:
                inc     de
                dec     bc
                ld      a, b
                or      c
                jr      nz, sm_lp
                ret

recno:          db      0
fcb:            db      0, "R       DAT"
                ds      37 - 12, 0
fcb0:           db      0, "R       DAT"
                ds      37 - 12, 0
buf:            ds      128, 0
big:            ds      192, 0

; ---------------------------------------------------------------------------
; captured block $0400-$041F
; ---------------------------------------------------------------------------
                ds      $0400 - $, $00
cap:            ds      33, $00
cap_end:
