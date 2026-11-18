; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XSYNCHR2 -- docs/bios/SYNCHR.md round 2 (2026-11-18): SYNCHR ($0008, RST 08h) on its MISMATCH path. The probe points
; the published error hook H.ERRO ($FFB1) at its own RAM code, which records E (the error code the hook receives),
; restores the stack pointer saved before the call and goes on with the next case: BASIC's error handler is never
; let past the hook. Cases, each with HL = BUF:
;   0..255: the text "c 31 00", `rst $08 / db (c XOR $01)` -- the expected byte differs from the one at HL
;   256:    the text "20 2C 31 00" (a space, ','), expecting ','
;   257:    the text "09 2C 31 00" (a TAB, ','), expecting ','
;   258:    the text "2C 31 00", expecting ',' -- a match, as a control that the hook does not fire on one
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsynchr2.asm --row nodisk
; Runs from RAM ($EA00) with page 1 the main ROM (ENASLT, EXPTBL), as XCHRGTR.
; The capture: CAP+0 = $A5 when finished; per case 4 bytes from CAP+1: the path ($E7 = the hook ran, $5C = SYNCHR
; returned), E at the hook (0 when it returned), A after, HL - BUF low after (both 0 when the hook ran); then $C3.
;
; CLEAN-ROOM: 100% own code; a published BIOS entry and a published hook, work-area RAM.
;
; @cap C000
; @caplen 0420
; @timeout 60

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
ci      equ     $EF02                   ; the case (2 bytes)
ssp     equ     $EF04
H_ERRO  equ     $FFB1
RAMB    equ     $EA00
BUF     equ     $E900

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $041F
                ld      (hl), 0
                ldir
                ld      hl, blk
                ld      de, RAMB
                ld      bc, blk_end - blk
                ldir
                jp      RAMB

blk:
                ld      a, ($FCC1)
                ld      h, $40
                call    $0024                   ; ENASLT: page 1 := the main ROM
                di
                ld      a, $C3                  ; H.ERRO := jp on_err
                ld      (H_ERRO), a
                ld      hl, RAMB + on_err - blk
                ld      (H_ERRO+1), hl
                ld      hl, CAP+1
                ld      (ptr), hl
                ld      hl, 0
                ld      (ci), hl
c_lp:
                call    RAMB + one - blk
                ld      hl, (ci)
                inc     hl
                ld      (ci), hl
                ld      de, 259
                or      a
                sbc     hl, de
                jr      c, c_lp
                ld      a, $C9                  ; the hook back to a RET
                ld      (H_ERRO), a
                jp      RAMB + finish - blk

; one -- set the text and the expected byte for case (ci), call
one:
                ld      hl, (ci)
                ld      a, h
                or      a
                jr      nz, o_x
                ld      a, l                    ; 0..255: "c 31 00", expect c XOR 1
                ld      (BUF), a
                xor     $01
                ld      (RAMB + sy_byte - blk), a
                ld      a, $31
                ld      (BUF+1), a
                xor     a
                ld      (BUF+2), a
                jr      o_call
o_x:
                ld      a, $2C
                ld      (RAMB + sy_byte - blk), a
                ld      a, l
                cp      2
                jr      z, o_match
                or      a
                ld      a, $20
                jr      z, o_lead
                ld      a, $09
o_lead:
                ld      (BUF), a
                ld      hl, BUF+1
                jr      o_tail
o_match:
                ld      hl, BUF
o_tail:
                ld      (hl), $2C
                inc     hl
                ld      (hl), $31
                inc     hl
                ld      (hl), 0
o_call:
                ld      (ssp), sp
                ld      hl, BUF
                ld      a, $A7
                rst     $08
sy_byte:
                db      0
                push    hl                      ; returned: path $5C, E 0, A, HL - BUF low
                ld      h, a
                ld      a, $5C
                call    RAMB + emit - blk
                xor     a
                call    RAMB + emit - blk
                ld      a, h
                call    RAMB + emit - blk
                pop     hl
                ld      a, l
                sub     low BUF
                jp      RAMB + emit - blk

on_err:
                di
                ld      sp, (ssp)               ; back to `one`'s frame: its return address is on top
                ld      a, $E7
                call    RAMB + emit - blk
                ld      a, e
                call    RAMB + emit - blk
                xor     a
                call    RAMB + emit - blk
                jp      RAMB + emit - blk

finish:
                ld      a, $C3
                call    RAMB + emit - blk
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
halt_lp:
                jr      halt_lp

emit:
                push    hl
                ld      hl, (ptr)
                ld      (hl), a
                inc     hl
                ld      (ptr), hl
                pop     hl
                ret
blk_end:
