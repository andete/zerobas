; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XVRAM -- docs/bios/RDVRM.md, WRTVRM.md, SETRD.md, SETWRT.md, FILVRM.md, LDIRMV.md, LDIRVM.md round 2
; (2026-11-18; round 1 had cases 0-33, two windows and no port read after the other calls): the VRAM access calls. Per case (the table `cases` at the end: op, A, F, interrupts, HL, DE, BC,
; three window addresses W1 / W2 / W3, and a kind byte: bit 0 set = W1 / W2 are RAM, bit 1 set = W3 is RAM) the probe first sets, BY HAND
; and slowly (a VRAM access at least 38 T-states from the next):
;   - VRAM: the 8 bytes from each VRAM window, and from HL AND $3FFF (DE AND $3FFF for LDIRVM) := pv(a) =
;     (a's low byte) XOR (a's high byte) XOR $5A -- for LDIRMV / LDIRVM the whole BC bytes when BC is 8..$200;
;   - RAM windows: the 8 bytes from W1 := $E0 + i, from W2 := $E8 + i; LDIRVM's source $E9A0.. := $80 + i
;     (low byte), $110 bytes.
; Then IX $4321, IY $8765, the case's A, F, HL, DE, BC, interrupts on or off, and the call:
; op 0 RDVRM ($004A), 1 WRTVRM ($004D), 2 SETRD ($0050), 3 SETWRT ($0053), 4 FILVRM ($0056), 5 LDIRMV ($0059),
; 6 LDIRVM ($005C). Right after it: for SETRD two reads of port $98, for SETWRT two writes ($C7, $C8) to it,
; for every other call one read of port $98.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xvram.asm --row both
; The capture: CAP+0 = $A5 when finished; per case a 48-byte record from CAP+1:
;   +0 A  +1 F  +2 B  +3 C  +4 D  +5 E  +6 H  +7 L  +8,9 IX (high, low)  +10,11 IY  after the call
;   +12 interrupts after (1 on)  +13,14 the port reads after the call (SETRD two; SETWRT none, 0; the others one)
;   +15..22 the 8 bytes from W1 after  +23..30 from W2  +31..38 from W3 (VRAM or RAM, as the kind says)  +39..47 0
; then $C3.
;
; CLEAN-ROOM: 100% own code; published BIOS entries, work-area RAM, VRAM through the VDP's ports. No case copies
; RAM below $C000 into VRAM, and no BC = 0 copy is made (it would carry ROM bytes into VRAM).
;
; @cap C000
; @caplen 0E00
; @timeout 60

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
tptr    equ     $EF02
STUB    equ     $E8F2                   ; ei / nop, call target, ret
cop     equ     $E910                   ; the case: op, A, F, ei, HL, DE, BC, W1, W2, W3, kind (17 bytes)
cA      equ     $E911
cF      equ     $E912
cei     equ     $E913
cHL     equ     $E914
cDE     equ     $E916
cBC     equ     $E918
cW1     equ     $E91A
cW2     equ     $E91C
cW3     equ     $E91E
cwk     equ     $E920
slen    equ     $E930                   ; the span preset's length
raf     equ     $E940                   ; F, A after
rbc     equ     $E942
rde     equ     $E944
rhl     equ     $E946
rix     equ     $E948
riy     equ     $E94A
riff    equ     $E94C
rp0     equ     $E94D
rp1     equ     $E94E
SRC     equ     $E9A0                   ; LDIRVM's source

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $0DFF
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
                ld      bc, 17
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
                jr      z, nwr0
                cp      2
                jr      z, nwr
                call    vget                    ; the other calls: one read
                ld      (rp0), a
                jr      nwr
nwr0:
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
                ld      a, (cwk)
                push    af
                rrca
                ld      (cwk), a                ; bit 0 := W3's kind
                ld      hl, (cW3)
                call    window
                pop     af
                ld      (cwk), a
                ld      b, 9
z_lp:
                xor     a
                call    emit
                djnz    z_lp
                jp      next

; window -- the 8 bytes from HL: VRAM (read by hand) or RAM, as cwk says
window:
                ld      a, (cwk)
                and     1
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
                and     2
                jr      nz, p_w3r
                ld      hl, (cW3)
                call    vfill
p_w3r:
                ld      a, (cwk)
                and     1
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
                push    hl
                ld      bc, 8                   ; the span: 8 bytes, or BC for LDIRMV / LDIRVM with BC 8..$200
                ld      a, (cop)
                cp      5
                jr      c, p_s8
                ld      hl, (cBC)
                ld      de, 8
                or      a
                sbc     hl, de
                jr      c, p_s8
                ld      hl, (cBC)
                ld      de, $201
                or      a
                sbc     hl, de
                jr      nc, p_s8
                ld      bc, (cBC)
p_s8:
                ld      (slen), bc
                pop     hl
                call    vfilln
                ld      hl, SRC
                ld      bc, $110
                ld      e, $80
s_src:
                ld      (hl), e
                inc     hl
                inc     e
                dec     bc
                ld      a, b
                or      c
                jr      nz, s_src
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

; vfill -- VRAM HL..HL+7 := pv(address), HL AND $3FFF; vfilln -- (slen) bytes
vfill:
                ld      bc, 8
                ld      (slen), bc
vfilln:
                push    hl
                call    vwrite
                pop     hl
                ld      bc, (slen)
vf_lp:
                ld      a, h
                and     $3F
                xor     l
                xor     $5A
                call    vput
                inc     hl
                dec     bc
                ld      a, b
                or      c
                jr      nz, vf_lp
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

; ---- cases: op, A, F, interrupts; HL, DE, BC, W1, W2, W3; kind (bit 0 W1 / W2 RAM, bit 1 W3 RAM); $FF ends ----
cases:
                db      $00, $A7, $00, $00
                dw      $1234, $9BDF, $1357, $1230, $2000, $1230
                db      $00                   ; 0
                db      $00, $A7, $FF, $00
                dw      $3FFF, $9BDF, $1357, $3FF8, $2000, $3FF8
                db      $00                   ; 1
                db      $00, $A7, $00, $01
                dw      $0000, $9BDF, $1357, $0000, $2000, $0000
                db      $00                   ; 2
                db      $00, $A7, $FF, $01
                dw      $4123, $9BDF, $1357, $0120, $2000, $0120
                db      $00                   ; 3
                db      $00, $A7, $00, $00
                dw      $C123, $9BDF, $1357, $0120, $2000, $0120
                db      $00                   ; 4
                db      $00, $A7, $FF, $00
                dw      $FFFF, $9BDF, $1357, $3FF8, $2000, $3FF8
                db      $00                   ; 5
                db      $01, $00, $00, $00
                dw      $1234, $9BDF, $1357, $1230, $1238, $1230
                db      $00                   ; 6
                db      $01, $FF, $FF, $00
                dw      $1234, $9BDF, $1357, $1230, $1238, $1230
                db      $00                   ; 7
                db      $01, $5A, $00, $01
                dw      $3FFF, $9BDF, $1357, $3FFB, $0003, $3FFB
                db      $00                   ; 8
                db      $01, $A5, $FF, $01
                dw      $4123, $9BDF, $1357, $011F, $0127, $011F
                db      $00                   ; 9
                db      $01, $3C, $00, $00
                dw      $C125, $9BDF, $1357, $0121, $0129, $0121
                db      $00                   ; 10
                db      $01, $C3, $FF, $00
                dw      $FFFF, $9BDF, $1357, $3FFB, $0003, $3FFB
                db      $00                   ; 11
                db      $02, $A7, $00, $00
                dw      $1234, $9BDF, $1357, $1230, $0000, $1230
                db      $00                   ; 12
                db      $02, $A7, $FF, $00
                dw      $3FFF, $9BDF, $1357, $3FF8, $0000, $3FF8
                db      $00                   ; 13
                db      $02, $A7, $00, $01
                dw      $4123, $9BDF, $1357, $0120, $0000, $0120
                db      $00                   ; 14
                db      $02, $A7, $FF, $01
                dw      $FFFF, $9BDF, $1357, $3FF8, $0000, $3FF8
                db      $00                   ; 15
                db      $03, $A7, $00, $00
                dw      $1234, $9BDF, $1357, $1230, $0000, $1230
                db      $00                   ; 16
                db      $03, $A7, $FF, $00
                dw      $3FFF, $9BDF, $1357, $3FFB, $0000, $3FFB
                db      $00                   ; 17
                db      $03, $A7, $00, $01
                dw      $4123, $9BDF, $1357, $011F, $0000, $011F
                db      $00                   ; 18
                db      $03, $A7, $FF, $01
                dw      $FFFF, $9BDF, $1357, $3FFB, $0000, $3FFB
                db      $00                   ; 19
                db      $04, $5A, $00, $00
                dw      $1234, $9BDF, $0008, $1230, $1238, $1230
                db      $00                   ; 20
                db      $04, $00, $FF, $00
                dw      $1234, $9BDF, $0001, $1230, $1238, $1230
                db      $00                   ; 21
                db      $04, $FF, $00, $01
                dw      $1200, $9BDF, $0100, $11F8, $12F8, $11F8
                db      $00                   ; 22
                db      $04, $A5, $FF, $01
                dw      $3FFC, $9BDF, $0008, $3FF8, $0000, $3FF8
                db      $00                   ; 23
                db      $04, $96, $00, $00
                dw      $5234, $9BDF, $0004, $1230, $1238, $1230
                db      $00                   ; 24
                db      $04, $77, $FF, $01
                dw      $2000, $9BDF, $0000, $1FF8, $3FF8, $1FF8
                db      $00                   ; 25
                db      $05, $A7, $00, $00
                dw      $1234, $E980, $0008, $E97C, $E984, $1234
                db      $01                   ; 26
                db      $05, $A7, $FF, $01
                dw      $3FFC, $E980, $0008, $E97C, $E984, $3FFC
                db      $01                   ; 27
                db      $05, $A7, $00, $01
                dw      $5234, $E980, $0004, $E97C, $E984, $1234
                db      $01                   ; 28
                db      $05, $A7, $FF, $00
                dw      $1234, $E980, $0001, $E97C, $E984, $1234
                db      $01                   ; 29
                db      $06, $A7, $00, $00
                dw      $E9A0, $1234, $0008, $1230, $1238, $E9A0
                db      $02                   ; 30
                db      $06, $A7, $FF, $01
                dw      $E9A0, $3FFC, $0008, $3FF8, $0000, $E9A0
                db      $02                   ; 31
                db      $06, $A7, $00, $01
                dw      $E9A0, $5234, $0004, $1230, $1238, $E9A0
                db      $02                   ; 32
                db      $06, $A7, $FF, $00
                dw      $E9A0, $1234, $0001, $1230, $1238, $E9A0
                db      $02                   ; 33
                db      $00, $00, $A5, $00
                dw      $0812, $9BDF, $1357, $0810, $2000, $0810
                db      $00                   ; 34
                db      $00, $5A, $5A, $01
                dw      $2034, $9BDF, $1357, $2030, $2000, $2030
                db      $00                   ; 35
                db      $02, $00, $A5, $00
                dw      $0000, $9BDF, $1357, $0000, $2000, $0000
                db      $00                   ; 36
                db      $02, $5A, $5A, $01
                dw      $C0AB, $9BDF, $1357, $00A8, $2000, $00A8
                db      $00                   ; 37
                db      $02, $A7, $00, $00
                dw      $0812, $9BDF, $1357, $0810, $2000, $0810
                db      $00                   ; 38
                db      $02, $A7, $FF, $01
                dw      $2034, $9BDF, $1357, $2030, $2000, $2030
                db      $00                   ; 39
                db      $03, $00, $A5, $00
                dw      $0812, $9BDF, $1357, $080E, $2000, $080E
                db      $00                   ; 40
                db      $03, $5A, $5A, $01
                dw      $2034, $9BDF, $1357, $2030, $2000, $2030
                db      $00                   ; 41
                db      $03, $A7, $00, $00
                dw      $0000, $9BDF, $1357, $0000, $2000, $0000
                db      $00                   ; 42
                db      $01, $5A, $A5, $00
                dw      $2034, $9BDF, $1357, $2030, $2038, $2030
                db      $00                   ; 43
                db      $01, $C3, $5A, $01
                dw      $0812, $9BDF, $1357, $080E, $0816, $080E
                db      $00                   ; 44
                db      $04, $3C, $A5, $00
                dw      $D234, $9BDF, $0004, $1230, $1238, $1230
                db      $00                   ; 45
                db      $04, $3D, $5A, $01
                dw      $9234, $9BDF, $0004, $1230, $1238, $1230
                db      $00                   ; 46
                db      $04, $3E, $00, $00
                dw      $1200, $9BDF, $0108, $11FC, $1304, $1300
                db      $00                   ; 47
                db      $04, $3F, $FF, $01
                dw      $1200, $9BDF, $0100, $11FC, $12FC, $1300
                db      $00                   ; 48
                db      $05, $00, $A5, $00
                dw      $D234, $E980, $0004, $E97C, $E984, $1234
                db      $01                   ; 49
                db      $05, $5A, $5A, $01
                dw      $9234, $E980, $0004, $E97C, $E984, $1234
                db      $01                   ; 50
                db      $05, $00, $00, $00
                dw      $1200, $E980, $0108, $E97C, $EA84, $1300
                db      $01                   ; 51
                db      $06, $5A, $A5, $00
                dw      $E9A0, $D234, $0004, $1230, $1238, $E9A0
                db      $02                   ; 52
                db      $06, $00, $5A, $01
                dw      $E9A0, $9234, $0004, $1230, $1238, $E9A0
                db      $02                   ; 53
                db      $06, $A7, $FF, $00
                dw      $E9A0, $1200, $0108, $11FC, $1304, $EAA0
                db      $02                   ; 54
                db      $FF
