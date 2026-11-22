; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; BDOSXT.COM -- D-DISKCONTRACT gap 11 (2026-11-17): SDATE ($2B) and STIME ($2D) with VALID
; and INVALID input, each followed by GDATE ($2A) and GTIME ($2C). BX2 calls STIME / GTIME
; with one valid value; nothing compared an out-of-range one (A = $FF?) or whether the clock
; keeps what was set.
;
; Each case is a 10-byte row: the case number, the setter's A, then GDATE's H L D E A and
; GTIME's H L D. GTIME's E (hundredths) is not recorded: it moves with the run's timing.
;
; CLEAN-ROOM: 100% own code; the published BDOS interface. Nothing of the reference read.
;
; Build: pasmo --bin bdosxt.asm bdosxt.com bdosxt.sym

                org     $0100

BDOS            equ     $0005

start:
                jr      begin                   ; $0102 = $7A: a distinctive arm signature
                db      $7A
begin:
                ld      ix, rows
                ld      hl, cases
next:
                ld      a, (hl)                 ; the BDOS function, 0 = the end
                or      a
                jp      z, finish
                ld      (ix+0), a
                ld      c, a
                inc     hl
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                push    hl
                ld      a, (hl)                 ; the case's HL
                inc     hl
                ld      h, (hl)
                ld      l, a
                push    ix
                call    BDOS                    ; SDATE: HL year, D month, E day
                pop     ix                      ; STIME: H hour, L minute, D second, E 1/100
                ld      (ix+1), a
                push    ix
                ld      c, $2A                  ; GDATE
                call    BDOS
                pop     ix
                ld      (ix+2), h
                ld      (ix+3), l
                ld      (ix+4), d
                ld      (ix+5), e
                ld      (ix+6), a
                push    ix
                ld      c, $2C                  ; GTIME
                call    BDOS
                pop     ix
                ld      (ix+7), h
                ld      (ix+8), l
                ld      (ix+9), d
                ld      de, 10
                add     ix, de
                pop     hl
                inc     hl
                inc     hl
                jr      next
finish:
                ld      a, $A5
                ld      (mark), a
                jp      done

; the cases: function, DE, HL
cases:
                db      $2B
                dw      $0B11, 2026             ; SDATE 2026-11-17: valid
                db      $2B
                dw      $0D01, 2026             ; month 13
                db      $2B
                dw      $021E, 2026             ; 2026-02-30
                db      $2B
                dw      $021D, 2024             ; 2024-02-29: a leap day, valid
                db      $2B
                dw      $0101, 1979             ; before 1980
                db      $2B
                dw      $0101, 2100             ; after 2099
                db      $2B
                dw      $0000, 2026             ; month 0, day 0
                db      $2D
                dw      $0000, $0C22            ; STIME 12:34:00.00: valid
                db      $2D
                dw      $0000, $1900            ; hour 25
                db      $2D
                dw      $0000, $0C3C            ; minute 60
                db      $2D
                dw      $3C00, $0C22            ; second 60
                db      $2D
                dw      $0064, $0C22            ; hundredths 100
                db      $2D
                dw      $0000, $1738            ; 23:56:00: valid (the minute stays in a run)
                db      0

                ds      $0330 - $, $00
done:
                jr      done                    ; the capture anchor, pinned at $0330
                ds      $0340 - $, $00
mark:           db      $EE                     ; $A5: the run finished
rows:           ds      13 * 10, $EE
