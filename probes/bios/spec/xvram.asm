; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XVRAM -- docs/bios/RDVRM.md, WRTVRM.md, SETRD.md, SETWRT.md, FILVRM.md, LDIRMV.md, LDIRVM.md round 1
; (2026-11-18): the VRAM access calls. Per case (the table `cases` at the end: op, A, F, interrupts, HL, DE, BC,
; two window addresses W1 / W2, and whether the windows are VRAM (0) or RAM (1)) the probe first sets, BY HAND
; and slowly (a VRAM access at least 38 T-states from the next):
;   - VRAM: the 8 bytes from W1, from W2 and from HL AND $3FFF (DE AND $3FFF for LDIRVM) := pv(a) =
;     (a's low byte) XOR (a's high byte) XOR $5A, so each byte names its address;
;   - RAM windows: the 8 bytes from W1 := $E0 + i, from W2 := $E8 + i; LDIRVM's source $E9A0.. := $80 + i.
; Then IX $4321, IY $8765, the case's A, F, HL, DE, BC, interrupts on or off, and the call:
; op 0 RDVRM ($004A), 1 WRTVRM ($004D), 2 SETRD ($0050), 3 SETWRT ($0053), 4 FILVRM ($0056), 5 LDIRMV ($0059),
; 6 LDIRVM ($005C). Right after it: for SETRD two reads of port $98, for SETWRT two writes ($C7, $C8) to it.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xvram.asm --row both
; The capture: CAP+0 = $A5 when finished; per case a 32-byte record from CAP+1:
;   +0 A  +1 F  +2 B  +3 C  +4 D  +5 E  +6 H  +7 L  +8,9 IX (high, low)  +10,11 IY  after the call
;   +12 interrupts after (1 on)  +13,14 SETRD's two port reads (0 otherwise)
;   +15..22 the 8 bytes from W1 after  +23..30 from W2 (VRAM or RAM, as the case says)  +31 0
; then $C3.
;
; CLEAN-ROOM: 100% own code; published BIOS entries, work-area RAM, VRAM through the VDP's ports. No case copies
; RAM below $C000 into VRAM, and no BC = 0 copy is made (it would carry ROM bytes into VRAM).
;
; @cap C000
; @caplen 0500
; @timeout 60

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
tptr    equ     $EF02
STUB    equ     $E8F2                   ; ei / nop, call target, ret
cop     equ     $E910                   ; the case: op, A, F, ei, HL, DE, BC, W1, W2, wk (15 bytes)
cA      equ     $E911
cF      equ     $E912
cei     equ     $E913
cHL     equ     $E914
cDE     equ     $E916
cBC     equ     $E918
cW1     equ     $E91A
cW2     equ     $E91C
cwk     equ     $E91E
raf     equ     $E920                   ; F, A after
rbc     equ     $E922
rde     equ     $E924
rhl     equ     $E926
rix     equ     $E928
riy     equ     $E92A
riff    equ     $E92C
rp0     equ     $E92D
rp1     equ     $E92E
SRC     equ     $E9A0                   ; LDIRVM's source

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $04FF
                ld      (hl), 0
                ldir
                ld      hl, CAP+1
                ld      (ptr), hl
                ld      hl, cases
                ld      (tptr), hl
next:
                di
                ld      hl, (tptr)
                ld      a, (hl)
                cp      $FF
                jp      z, finish
                ld      de, cop
                ld      bc, 15
                ldir
                ld      (tptr), hl
                call    preset
                ld      a, (cF)
                ld      c, a
                ld      a, (cA)
                ld      b, a
                push    bc
                ld      ix, $4321
                ld      iy, $8765
                ld      hl, (cHL)
                ld      de, (cDE)
                ld      bc, (cBC)
                pop     af
                call    STUB
                ld      (rhl), hl
                ld      (rde), de
                ld      (rbc), bc
                ld      (rix), ix
                ld      (riy), iy
                push    af
                pop     hl
                ld      (raf), hl
                ld      a, i                    ; P/V := IFF2
                di
                push    af
                pop     hl
                ld      a, l
                and     4
                jr      z, i0
                ld      a, 1
i0:
                ld      (riff), a
                xor     a
                ld      (rp0), a
                ld      (rp1), a
                ld      a, (cop)
                cp      2
                jr      nz, nrd
                call    vget
                ld      (rp0), a
                call    vget
                ld      (rp1), a
nrd:
                ld      a, (cop)
                cp      3
                jr      nz, nwr
                ld      a, $C7
                call    vput
                ld      a, $C8
                call    vput
nwr:
                ; the record
                ld      hl, raf+1
                call    emitm
                ld      hl, raf
                call    emitm
                ld      hl, rbc+1
                call    emitm
                ld      hl, rbc
                call    emitm
                ld      hl, rde+1
                call    emitm
                ld      hl, rde
                call    emitm
                ld      hl, rhl+1
                call    emitm
                ld      hl, rhl
                call    emitm
                ld      hl, rix+1
                call    emitm
                ld      hl, rix
                call    emitm
                ld      hl, riy+1
                call    emitm
                ld      hl, riy
                call    emitm
                ld      hl, riff
                call    emitm
                ld      hl, rp0
                call    emitm
                ld      hl, rp1
                call    emitm
                ld      hl, (cW1)
                call    window
                ld      hl, (cW2)
                call    window
                xor     a
                call    emit
                jp      next

; window -- the 8 bytes from HL: VRAM (read by hand) or RAM, as cwk says
window:
                ld      a, (cwk)
                or      a
                jr      nz, w_ram
                call    vread
                ld      b, 8
w_v:
                call    vget
                call    emit
                djnz    w_v
                ret
w_ram:
                ld      b, 8
w_r:
                ld      a, (hl)
                call    emit
                inc     hl
                djnz    w_r
                ret

; preset -- VRAM / RAM windows, the call's VRAM span, LDIRVM's source, the stub
preset:
                ld      a, (cwk)
                or      a
                jr      nz, p_ram
                ld      hl, (cW1)
                call    vfill
                ld      hl, (cW2)
                call    vfill
                jr      p_span
p_ram:
                ld      hl, (cW1)
                ld      a, $E0
                call    rfill
                ld      hl, (cW2)
                ld      a, $E8
                call    rfill
p_span:
                ld      hl, (cHL)
                ld      a, (cop)
                cp      6
                jr      nz, p_s1
                ld      hl, (cDE)
p_s1:
                ld      a, h
                and     $3F
                ld      h, a
                call    vfill
                ld      hl, SRC
                ld      a, $80
                call    rfill
                ld      a, (cei)
                or      a
                ld      a, $00                  ; nop
                jr      z, p3
                ld      a, $FB                  ; ei
p3:
                ld      (STUB), a
                ld      a, $CD
                ld      (STUB+1), a
                ld      a, $C9
                ld      (STUB+4), a
                ld      a, (cop)
                add     a, a
                ld      hl, targets
                add     a, l
                ld      l, a
                jr      nc, p4
                inc     h
p4:
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                ld      (STUB+2), de
                ret

targets:
                dw      $004A, $004D, $0050, $0053, $0056, $0059, $005C

; vfill -- VRAM HL..HL+7 := pv(address), HL AND $3FFF
vfill:
                push    hl
                call    vwrite
                pop     hl
                ld      b, 8
vf_lp:
                ld      a, h
                and     $3F
                xor     l
                xor     $5A
                call    vput
                inc     hl
                djnz    vf_lp
                ret

; rfill -- RAM HL..HL+7 := A, A+1, ...
rfill:
                ld      b, 8
rf_lp:
                ld      (hl), a
                inc     hl
                inc     a
                djnz    rf_lp
                ret

; vwrite / vread -- the VDP's address := HL AND $3FFF, for writing / reading
vwrite:
                ld      a, l
                out     ($99), a
                ld      a, h
                and     $3F
                or      $40
                out     ($99), a
                ret
vread:
                ld      a, l
                out     ($99), a
                ld      a, h
                and     $3F
                out     ($99), a
                ret

; vput / vget -- one VRAM access, at least 38 T-states from the next
vput:
                out     ($98), a
                ret
vget:
                in      a, ($98)
                ret

finish:
                ld      a, $C3
                call    emit
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
halt_lp:
                jr      halt_lp

emitm:
                ld      a, (hl)
emit:
                push    hl
                ld      hl, (ptr)
                ld      (hl), a
                inc     hl
                ld      (ptr), hl
                pop     hl
                ret

; ---- cases: op, A, F, interrupts; HL, DE, BC, W1, W2; windows VRAM (0) / RAM (1); $FF ends ----
cases:
                db      $00, $A7, $00, $00
                dw      $1234, $9BDF, $1357, $1230, $2000
                db      $00                   ; 0
                db      $00, $A7, $FF, $00
                dw      $3FFF, $9BDF, $1357, $3FF8, $2000
                db      $00                   ; 1
                db      $00, $A7, $00, $01
                dw      $0000, $9BDF, $1357, $0000, $2000
                db      $00                   ; 2
                db      $00, $A7, $FF, $01
                dw      $4123, $9BDF, $1357, $0120, $2000
                db      $00                   ; 3
                db      $00, $A7, $00, $00
                dw      $C123, $9BDF, $1357, $0120, $2000
                db      $00                   ; 4
                db      $00, $A7, $FF, $00
                dw      $FFFF, $9BDF, $1357, $3FF8, $2000
                db      $00                   ; 5
                db      $01, $00, $00, $00
                dw      $1234, $9BDF, $1357, $1230, $1238
                db      $00                   ; 6
                db      $01, $FF, $FF, $00
                dw      $1234, $9BDF, $1357, $1230, $1238
                db      $00                   ; 7
                db      $01, $5A, $00, $01
                dw      $3FFF, $9BDF, $1357, $3FFB, $0003
                db      $00                   ; 8
                db      $01, $A5, $FF, $01
                dw      $4123, $9BDF, $1357, $011F, $0127
                db      $00                   ; 9
                db      $01, $3C, $00, $00
                dw      $C125, $9BDF, $1357, $0121, $0129
                db      $00                   ; 10
                db      $01, $C3, $FF, $00
                dw      $FFFF, $9BDF, $1357, $3FFB, $0003
                db      $00                   ; 11
                db      $02, $A7, $00, $00
                dw      $1234, $9BDF, $1357, $1230, $0000
                db      $00                   ; 12
                db      $02, $A7, $FF, $00
                dw      $3FFF, $9BDF, $1357, $3FF8, $0000
                db      $00                   ; 13
                db      $02, $A7, $00, $01
                dw      $4123, $9BDF, $1357, $0120, $0000
                db      $00                   ; 14
                db      $02, $A7, $FF, $01
                dw      $FFFF, $9BDF, $1357, $3FF8, $0000
                db      $00                   ; 15
                db      $03, $A7, $00, $00
                dw      $1234, $9BDF, $1357, $1230, $0000
                db      $00                   ; 16
                db      $03, $A7, $FF, $00
                dw      $3FFF, $9BDF, $1357, $3FFB, $0000
                db      $00                   ; 17
                db      $03, $A7, $00, $01
                dw      $4123, $9BDF, $1357, $011F, $0000
                db      $00                   ; 18
                db      $03, $A7, $FF, $01
                dw      $FFFF, $9BDF, $1357, $3FFB, $0000
                db      $00                   ; 19
                db      $04, $5A, $00, $00
                dw      $1234, $9BDF, $0008, $1230, $1238
                db      $00                   ; 20
                db      $04, $00, $FF, $00
                dw      $1234, $9BDF, $0001, $1230, $1238
                db      $00                   ; 21
                db      $04, $FF, $00, $01
                dw      $1200, $9BDF, $0100, $11F8, $12F8
                db      $00                   ; 22
                db      $04, $A5, $FF, $01
                dw      $3FFC, $9BDF, $0008, $3FF8, $0000
                db      $00                   ; 23
                db      $04, $96, $00, $00
                dw      $5234, $9BDF, $0004, $1230, $1238
                db      $00                   ; 24
                db      $04, $77, $FF, $01
                dw      $2000, $9BDF, $0000, $1FF8, $3FF8
                db      $00                   ; 25
                db      $05, $A7, $00, $00
                dw      $1234, $E980, $0008, $E97C, $E984
                db      $01                   ; 26
                db      $05, $A7, $FF, $01
                dw      $3FFC, $E980, $0008, $E97C, $E984
                db      $01                   ; 27
                db      $05, $A7, $00, $01
                dw      $5234, $E980, $0004, $E97C, $E984
                db      $01                   ; 28
                db      $05, $A7, $FF, $00
                dw      $1234, $E980, $0001, $E97C, $E984
                db      $01                   ; 29
                db      $06, $A7, $00, $00
                dw      $E9A0, $1234, $0008, $1230, $1238
                db      $00                   ; 30
                db      $06, $A7, $FF, $01
                dw      $E9A0, $3FFC, $0008, $3FF8, $0000
                db      $00                   ; 31
                db      $06, $A7, $00, $01
                dw      $E9A0, $5234, $0004, $1230, $1238
                db      $00                   ; 32
                db      $06, $A7, $FF, $00
                dw      $E9A0, $1234, $0001, $1230, $1238
                db      $00                   ; 33
                db      $FF
