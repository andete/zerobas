; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XLIN3 -- docs/bios/PINLIN.md round 3 (2026-11-21, D-EDITSTOP): CTRL+STOP and CTRL+C ending PINLIN / INLIN / QINLIN,
; and a STOP pause (INTFLG 4) pending when the line is read. Per case (the table `cases` at the end):
;   - CHPUT $0C (the screen cleared, the cursor home), then the case's text through CHPUT (so LINTTB is the editor's own);
;   - BUF ($F55E) := $FF x 40; INSFLG ($FCA8) := the case's; INTFLG ($FC9B) := the case's;
;   - the key buffer: KEYBUF ($FBF0) := the case's keys, GETPNT := KEYBUF, PUTPNT := KEYBUF + their length;
;   - the key matrix through the debugger at KSET (@keyset: hardware input, as a person presses the keys): no key,
;     except MASK1 in ROW1 and MASK2 in ROW2 ($FF: none) -- CTRL+STOP is row 6 $02 + row 7 $10. PRESSED DURING THE WAIT:
;     H.TIMI ($FD9F) jumps to a RAM counter (TICK) that calls KSET on the 10th timer interrupt after the call began (run 1
;     pressed them before the call: zerobas's editor waits for a key held at its start to be released -- D-STOPINPUT
;     round 4 -- and never returned; the VG-8020 took it as a new press), and RELEASES them 25 interrupts later (run 2:
;     zerobas's editor returns only once CTRL+STOP is up again, and never did);
;   - interrupts on (the timer interrupt scans the keys), then the call: op 0 PINLIN ($00AE), 1 INLIN ($00B1),
;     2 QINLIN ($00B4).
; After it returns: DI, the record; then the keys released (KSET), 8 frames (EI / HALT), KILBUF, INTFLG := 0.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xlin3.asm --row nodisk
; The capture: CAP+0 = $A5 when finished; per case a 72-byte record from CAP+1:
;   +0 the case number + 1 (written after the call returned)  +1 F  +2 H  +3 L  +4 CSRX  +5 CSRY  +6 INTFLG
;   +7 INSFLG  +8 CSTYLE ($FCAA)  +9 GETPNT's low byte  +10 PUTPNT's low byte  +11..18 BUF's first 8 bytes
;   +19..42 LINTTB ($FBB2, rows 1-24)  +43..54 row A's first 12 cells  +55..66 row B's
;   +67 / +68 SNSMAT rows 6 / 7 right after the return (bit clear = held: CTRL+STOP still down)  +69..71 0
; then $C3.
; Cases (op, INSFLG, INTFLG, the keys held, rows A / B; the text; the keys queued):
;   0: PINLIN, INSFLG $FF, CTRL+STOP; 'AB' on row 5, the cursor at column 3                      rows 5 / 6
;   1: INLIN, CTRL+STOP; the same                                                                  rows 5 / 6
;   2: QINLIN, CTRL+STOP; the same ('? ' printed at column 3)                                     rows 5 / 6
;   3: PINLIN, CTRL+STOP; 42 characters from row 7 column 1 (rows 7-8, one logical line), cursor at row 8 column 3
;                                                                                                  rows 8 / 9
;   4: PINLIN, CTRL+STOP; the same, then the cursor up one row (row 7 column 3)                    rows 8 / 9
;   5: PINLIN, CTRL+STOP; 'AB' on row 24                                                            rows 23 / 24
;   6: PINLIN; 'AB' on row 5; keys CTRL+C ($03)                                                     rows 5 / 6
;   7: INLIN; 'XY' on row 5; keys 'Q', CTRL+C                                                        rows 5 / 6
;   8: PINLIN, INTFLG 4 (a STOP pause pending); 'AB' on row 5; keys 'C', Enter                    rows 5 / 6
;
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells; VRAM through RDVRM; the key matrix set
; through the debugger (input, not a ROM byte).
;
; @cap C000
; @caplen 400
; @timeout 120
; @keyset E8F0 E8E0

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
tptr    equ     $EF02
KSET    equ     $E8F0
KLIST   equ     $E8E0
cop     equ     $E910
cins    equ     $E911
cint    equ     $E912
crow1   equ     $E913
cmask1  equ     $E914
crow2   equ     $E915
cmask2  equ     $E916
crowa   equ     $E917
crowb   equ     $E918
ctext   equ     $E91A
ckeys   equ     $E91C
cidx    equ     $E920
cnt     equ     $E921
cnt2    equ     $E926
SNSMAT  equ     $0141
TICK    equ     $E960
HTIMI   equ     $FD9F
raf     equ     $E922
rhl     equ     $E924
rsn6    equ     $E928
rsn7    equ     $E929
STUB    equ     $E930
CHPUT   equ     $00A2
RDVRM   equ     $004A
INITXT  equ     $006C
KILBUF  equ     $0156
LINL40  equ     $F3AE
CSRY    equ     $F3DC
CSRX    equ     $F3DD
BUF     equ     $F55E
LINTTB  equ     $FBB2
PUTPNT  equ     $F3F8
GETPNT  equ     $F3FA
KEYBUF  equ     $FBF0
INTFLG  equ     $FC9B
INSFLG  equ     $FCA8
CSTYLE  equ     $FCAA

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $03FF
                ld      (hl), 0
                ldir
                ld      a, $C9
                ld      (KSET), a
                ld      hl, tickc
                ld      de, TICK
                ld      bc, tickce - tickc
                ldir
                xor     a
                ld      (cnt), a
                ld      a, $C3
                ld      (HTIMI), a
                ld      hl, TICK
                ld      (HTIMI+1), hl
                ld      a, 40
                ld      (LINL40), a
                call    INITXT
                ld      hl, CAP+1
                ld      (ptr), hl
                ld      hl, cases
                ld      (tptr), hl
                xor     a
                ld      (cidx), a
next:
                di
                ld      hl, (tptr)
                ld      a, (hl)
                cp      $FF
                jp      z, finish
                ld      de, cop
                ld      bc, 14
                ldir
                ld      (tptr), hl
                ; the screen and the text
                ld      a, $0C
                call    CHPUT
                ld      hl, (ctext)
tx:
                ld      a, (hl)
                or      a
                jr      z, txe
                push    hl
                call    CHPUT
                pop     hl
                inc     hl
                jr      tx
txe:
                di
                ; BUF, INSFLG, INTFLG
                ld      hl, BUF
                ld      b, 40
bf:
                ld      (hl), $FF
                inc     hl
                djnz    bf
                ld      a, (cins)
                ld      (INSFLG), a
                ld      a, (cint)
                ld      (INTFLG), a
                ; the key buffer
                ld      hl, (ckeys)
                ld      de, KEYBUF
kb:
                ld      a, (hl)
                or      a
                jr      z, kbe
                ld      (de), a
                inc     hl
                inc     de
                jr      kb
kbe:
                ld      (PUTPNT), de
                ld      hl, KEYBUF
                ld      (GETPNT), hl
                ; the key matrix
                call    kclr
                ld      a, (crow1)
                ld      b, a
                ld      a, (cmask1)
                call    kput
                ld      a, (crow2)
                ld      b, a
                ld      a, (cmask2)
                call    kput
                ld      a, (crow1)
                cp      11
                ld      a, 0
                jr      nc, nocnt
                ld      a, 10                   ; KSET on the 10th timer interrupt from here
nocnt:
                ld      (cnt), a
                ld      a, 25
                ld      (cnt2), a
                ; the stub: call target, ret
                ld      a, $CD
                ld      (STUB), a
                ld      a, $C9
                ld      (STUB+3), a
                ld      a, (cop)
                add     a, a
                ld      hl, targets
                add     a, l
                ld      l, a
                jr      nc, s2
                inc     h
s2:
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                ld      (STUB+1), de
                ei
                call    STUB
                di
                ld      (rhl), hl
                push    af
                pop     hl
                ld      (raf), hl
                ld      a, 6
                call    SNSMAT
                ld      (rsn6), a
                ld      a, 7
                call    SNSMAT
                ld      (rsn7), a
                di
                ; the record
                ld      a, (cidx)
                inc     a
                call    emit
                ld      a, (raf)
                call    emit
                ld      a, (rhl+1)
                call    emit
                ld      a, (rhl)
                call    emit
                ld      a, (CSRX)
                call    emit
                ld      a, (CSRY)
                call    emit
                ld      a, (INTFLG)
                call    emit
                ld      a, (INSFLG)
                call    emit
                ld      a, (CSTYLE)
                call    emit
                ld      a, (GETPNT)
                call    emit
                ld      a, (PUTPNT)
                call    emit
                ld      hl, BUF
                ld      b, 8
r1:
                ld      a, (hl)
                call    emit
                inc     hl
                djnz    r1
                ld      hl, LINTTB
                ld      b, 24
r2:
                ld      a, (hl)
                call    emit
                inc     hl
                djnz    r2
                ld      a, (crowa)
                call    rrow
                ld      a, (crowb)
                call    rrow
                ld      a, (rsn6)
                call    emit
                ld      a, (rsn7)
                call    emit
                ld      b, 3
r3:
                xor     a
                call    emit
                djnz    r3
                ; release the keys, let the interrupt see it, empty the buffer
                xor     a
                ld      (cnt), a
                ld      (cnt2), a
                call    kclr
                call    KSET
                ld      b, 8
fr:
                ei
                halt
                djnz    fr
                di
                call    KILBUF
                xor     a
                ld      (INTFLG), a
                ld      (INSFLG), a
                ld      hl, cidx
                inc     (hl)
                jp      next

finish:
                ld      a, $C3
                call    emit
                ld      a, $A5
                ld      (DONE), a
hang:
                jr      hang

; A = row (1-24): its first 12 cells through RDVRM (the name table at 0, 40 columns)
rrow:
                dec     a
                ld      l, a
                ld      h, 0
                add     hl, hl
                add     hl, hl
                add     hl, hl                  ; x 8
                ld      d, h
                ld      e, l
                add     hl, hl
                add     hl, hl                  ; x 32
                add     hl, de                  ; x 40
                ld      b, 12
rr1:
                push    bc
                push    hl
                call    RDVRM
                call    emit
                pop     hl
                pop     bc
                inc     hl
                djnz    rr1
                ret

kclr:
                ld      hl, KLIST
                ld      b, 11
kz:
                ld      (hl), 0
                inc     hl
                djnz    kz
                ret

; B = row ($FF: none), A = mask
kput:
                ld      c, a
                ld      a, b
                cp      11
                ret     nc
                ld      hl, KLIST
                add     a, l
                ld      l, a
                jr      nc, kp1
                inc     h
kp1:
                ld      a, (hl)
                or      c
                ld      (hl), a
                ret

emit:
                push    hl
                ld      hl, (ptr)
                ld      (hl), a
                inc     hl
                ld      (ptr), hl
                pop     hl
                ret

; TICK (copied to RAM: H.TIMI runs whatever page 1 holds): count cnt down, KSET at 0
; (relocatable: relative jumps only), then cnt2 down, the matrix cleared and KSET at 0
tickc:
                push    af
                push    hl
                push    bc
                ld      a, (cnt)
                or      a
                jr      z, tk2
                dec     a
                ld      (cnt), a
                call    z, KSET
                jr      tk1
tk2:
                ld      a, (cnt2)
                or      a
                jr      z, tk1
                dec     a
                ld      (cnt2), a
                jr      nz, tk1
                ld      hl, KLIST
                ld      b, 11
tk3:
                ld      (hl), a
                inc     hl
                djnz    tk3
                call    KSET
tk1:
                pop     bc
                pop     hl
                pop     af
                ret
tickce:

targets:
                dw      $00AE, $00B1, $00B4

; op, INSFLG, INTFLG, ROW1, MASK1, ROW2, MASK2, row A, row B, 0, text, keys
cases:
                db      0, $FF, 0, 6, $02, 7, $10, 5, 6, 0
                dw      t_ab5, k_none
                db      1, 0, 0, 6, $02, 7, $10, 5, 6, 0
                dw      t_ab5, k_none
                db      2, 0, 0, 6, $02, 7, $10, 5, 6, 0
                dw      t_ab5, k_none
                db      0, 0, 0, 6, $02, 7, $10, 8, 9, 0
                dw      t_long, k_none
                db      0, 0, 0, 6, $02, 7, $10, 8, 9, 0
                dw      t_longup, k_none
                db      0, 0, 0, 6, $02, 7, $10, 23, 24, 0
                dw      t_ab24, k_none
                db      0, 0, 0, $FF, 0, $FF, 0, 5, 6, 0
                dw      t_ab5, k_ctrlc
                db      1, 0, 0, $FF, 0, $FF, 0, 5, 6, 0
                dw      t_xy5, k_qctrlc
                db      0, 0, 4, $FF, 0, $FF, 0, 5, 6, 0
                dw      t_ab5, k_center
                db      $FF

t_ab5:          db      13, 10, 13, 10, 13, 10, 13, 10, "AB", 0
t_xy5:          db      13, 10, 13, 10, 13, 10, 13, 10, "XY", 0
t_long:         db      13, 10, 13, 10, 13, 10, 13, 10, 13, 10, 13, 10
                db      "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdef", 0
t_longup:       db      13, 10, 13, 10, 13, 10, 13, 10, 13, 10, 13, 10
                db      "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdef", $1E, 0
t_ab24:         db      10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10
                db      "AB", 0
k_none:         db      0
k_ctrlc:        db      3, 0
k_qctrlc:       db      "Q", 3, 0
k_center:       db      "C", 13, 0

                ds      $8000 - $, $FF
