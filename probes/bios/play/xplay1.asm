; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XPLAY1 -- the background music player, black-box (2026-11-21, for the C-BIOS 0.32 player): queue packets put
; with PUTQ ($00F9), started with STRTMS ($0099), no BASIC statement involved. A 16 KB "AB" cartridge whose INIT
; hooks H.STKE (an RST 30h inter-slot call into this cartridge) and returns, so the scenarios run once every ROM
; (and, on a BASIC machine, the interpreter's set-up) has been initialised. Per scenario:
;   DI, GICINI ($0090), the scenario number to SCEN ($E010: the harness logs that write), the scenario's
;   (queue, byte) pairs through PUTQ, PLYCNT ($FB40) := the scenario's count, STRTMS, then EI and HALT for the
;   scenario's number of frames, DI. GO ($E013) := the scenario number right after STRTMS: frame 0 is the first
;   frame interrupt after it.
; The harness (probes/bios/play_trace.py) logs every PSG register select / data write with the machine time, every
; frame (VDP.IRQvertical raised) with MUSICF, PLYCNT, each voice block's first word and QUETAB's put / get bytes,
; and the SCEN writes. Then DONE ($E000) := $A5.
; Packet bytes used (the VG-8020's format as measured for PLAY, 2026-11-12, TODO D-STRTMS): a note
; [n << 5 | dur 12..8] [dur 7..0] [vol] ([M hi] [M lo]) [tone hi] [tone lo], a rest [$20 | dur hi] [dur lo] [vol],
; the end $FF; here they are only INPUTS -- what the player does with them is what is measured.
;
; CLEAN-ROOM: 100% own code; published BIOS entries (GICINI, PUTQ, STRTMS) and work-area cells.

GICINI  equ     $0090
STRTMS  equ     $0099
PUTQ    equ     $00F9
PLYCNT  equ     $FB40
EXPTBL  equ     $FCC1
H_STKE  equ     $FEDA
DONE    equ     $E000
SCEN    equ     $E010
CNT     equ     $E011
GO      equ     $E013

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                xor     a
                ld      (DONE), a
                in      a, ($A8)            ; our slot ID (page 1), for the RST 30h call in H.STKE
                rrca
                rrca
                and     3
                ld      c, a
                ld      hl, EXPTBL
                add     a, l
                ld      l, a
                ld      a, (hl)
                and     $80
                jr      z, plain
                inc     hl
                inc     hl
                inc     hl
                inc     hl
                ld      a, (hl)
                rrca
                rrca
                and     3
                rlca
                rlca
                or      c
                or      $80
                ld      c, a
plain:
                ld      a, $F7              ; RST 30h, slot, address, RET
                ld      (H_STKE), a
                ld      a, c
                ld      (H_STKE+1), a
                ld      hl, stke
                ld      (H_STKE+2), hl
                ld      a, $C9
                ld      (H_STKE+4), a
                ret

stke:
                ld      a, $C9
                ld      (H_STKE), a         ; once
                ld      hl, scenarios
next:
                ld      a, (hl)             ; scenario number; 0 ends the table
                or      a
                jr      z, fin
                di
                push    hl
                call    GICINI
                pop     hl
                ld      a, (hl)
                ld      (SCEN), a
                inc     hl
                ld      a, (hl)             ; PLYCNT
                ld      (cnt_p), a
                inc     hl
                ld      a, (hl)             ; frames
                ld      (CNT), a
                inc     hl
put:
                ld      a, (hl)             ; queue, or $FF: the pairs end
                inc     hl
                cp      $FF
                jr      z, start
                ld      e, (hl)
                inc     hl
                push    hl
                call    PUTQ
                pop     hl
                jr      put
start:
                push    hl
                ld      a, (cnt_p)
                and     $7F
                ld      (PLYCNT), a
                ld      a, (cnt_p)
                rlca
                call    nc, STRTMS          ; PLYCNT's bit 7 in the table: no STRTMS
                ld      a, (SCEN)
                ld      (GO), a             ; the harness counts frames from here
                ld      a, (CNT)
                ld      b, a
wait:
                ei
                halt
                djnz    wait
                di
                pop     hl
                jr      next
fin:
                ld      a, $A5
                ld      (DONE), a
                ld      a, 0
                ld      (SCEN), a
hang:
                jr      hang

cnt_p           equ     $E012

; ---- scenarios: number, PLYCNT (bit 7 set: PLYCNT := the rest, and STRTMS is NOT called), frames, then (queue, byte) pairs, $FF ----
scenarios:
                ; 1: one note on A (C: dur 25, vol 8, tone $01AC); B and C only their end marker
                db      1, 1, 34
                db      0,$60, 0,$19, 0,$88, 0,$01, 0,$AC, 0,$FF, 1,$FF, 2,$FF, $FF
                ; 2: A two notes (dur 3) and a rest (dur 2); B one note (dur 5); C NOTHING queued
                db      2, 1, 24
                db      0,$60, 0,$03, 0,$8A, 0,$00, 0,$D6
                db      0,$60, 0,$03, 0,$8C, 0,$01, 0,$1D
                db      0,$20, 0,$02, 0,$80, 0,$FF
                db      1,$60, 1,$05, 1,$89, 1,$01, 1,$53, 1,$FF, $FF
                ; 3: envelope: a note with M ($03E8, shape 0), one without M, then a plain volume note
                db      3, 1, 16
                db      0,$A0, 0,$04, 0,$D0, 0,$03, 0,$E8, 0,$01, 0,$AC
                db      0,$60, 0,$04, 0,$90, 0,$01, 0,$AC
                db      0,$60, 0,$03, 0,$8F, 0,$00, 0,$D6, 0,$FF, 1,$FF, 2,$FF, $FF
                ; 4: PLYCNT 2 -- two rounds queued (A: a note, end, a note, end; B / C two end markers)
                db      4, 2, 20
                db      0,$60, 0,$03, 0,$88, 0,$01, 0,$AC, 0,$FF
                db      0,$60, 0,$03, 0,$8A, 0,$00, 0,$D6, 0,$FF
                db      1,$FF, 1,$FF, 2,$FF, 2,$FF, $FF
                ; 5: a rest whose vol byte is $8A; B a rest only
                db      5, 1, 12
                db      0,$20, 0,$03, 0,$8A, 0,$60, 0,$02, 0,$88, 0,$01, 0,$AC, 0,$FF
                db      1,$20, 1,$02, 1,$80, 1,$FF, 2,$FF, $FF
                ; 6: a note of duration 0, then a note of 2
                db      6, 1, 12
                db      0,$60, 0,$00, 0,$8A, 0,$00, 0,$D6, 0,$60, 0,$02, 0,$88, 0,$01, 0,$AC, 0,$FF
                db      1,$FF, 2,$FF, $FF
                ; 7: the control -- PLYCNT 0: STRTMS starts nothing
                db      7, 0, 6
                db      0,$60, 0,$03, 0,$88, 0,$01, 0,$AC, 0,$FF, 1,$FF, 2,$FF, $FF
                ; 8: all three voices a note of 4 at once (the service order within a frame)
                db      8, 1, 10
                db      0,$60, 0,$04, 0,$88, 0,$01, 0,$AC, 0,$FF
                db      1,$60, 1,$04, 1,$89, 1,$00, 1,$D6, 1,$FF
                db      2,$60, 2,$04, 2,$8A, 2,$01, 2,$1D, 2,$FF, $FF
                ; 9: M bytes on a NON-envelope note (vol $C8), then a plain note
                db      9, 1, 10
                db      0,$A0, 0,$03, 0,$C8, 0,$07, 0,$D0, 0,$01, 0,$AC
                db      0,$60, 0,$02, 0,$88, 0,$00, 0,$D6, 0,$FF, 1,$FF, 2,$FF, $FF
                ; 10: B and C only (A its end marker): the voices numbered as the PSG's channels
                db      10, 1, 10
                db      0,$FF
                db      1,$60, 1,$03, 1,$87, 1,$00, 1,$D6, 1,$FF
                db      2,$60, 2,$03, 2,$86, 2,$01, 2,$1D, 2,$FF, $FF
                ; 12: PLYCNT 1 and the queues filled, but NO STRTMS (MUSICF 0): does the interrupt start it?
                db      12, $81, 6
                db      0,$60, 0,$03, 0,$88, 0,$01, 0,$AC, 0,$FF, 1,$FF, 2,$FF, $FF
                ; 11: a duration with high bits ($0102 = 258 frames), cut short by the next scenario's GICINI
                db      11, 1, 8
                db      0,$61, 0,$02, 0,$88, 0,$01, 0,$AC, 0,$FF, 1,$FF, 2,$FF, $FF
                db      0

                ds      $8000 - $, $FF
