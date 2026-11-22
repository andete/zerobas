; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XBBLK5 -- the BDOS's block functions through $F37D, round 5 (2026-11-22), answering review pass 3 (scratchpad/
; BBLK_review3.md): WRBLK at a nonzero RR with record size 128 and past the end (a gap); WRZER's zero fill over a
; sector that still holds OLDER data; RDBLK with record size $0180 (one word: 384, or +14 alone: 128?); a read past
; the end over older sector data; FOPEN with +14 / +15 nonzero going in; +15 $FF into FSIZE. XBBLK4's frame
; (probes/bios/spec/xbblk4.asm: mode 8 = FSIZE through the second FCB, here with the template's +14 / +15 $FF80)
; with a 66-byte record: A, F, the FCB, the DTA's first 13, HL, then the DTA at +127, +128, +383, +384, +511, +512,
; +520, +700, +767, +768, +1023, +1024. The DTA's 1040 bytes hold $40 + the case + i (AND $FF) before each case.
; Cases:
;   0: SETDTA $A800 (C $1A)
;   1: FMAKE F.TXT (C $16)
;   2: WRBLK 1024 x 1 (RS 1, RR 0) (C $26)
;   3: FCLOSE (C $10)
;   4: FOPEN F.TXT, +14 $80 / +15 $FF going in (C $0F)
;   5: RDBLK HL 1, RS $0180, RR 0 (C $27)
;   6: WRBLK HL 0, RS 128, RR 3 (shrink 1024 -> 384) (C $26)
;   7: RDBLK HL 1, RS $0400, RR 0 (past the end over older data) (C $27)
;   8: WRZER RS 128, RR 6, HL 1 (zero fill over older data) (C $28)
;   9: WRBLK 2 x 128 at RR 2 (C $26)
;   10: WRBLK 1 x 1 at RR 2000 (past the end) (C $26)
;   11: FCLOSE (C $10)
;   12: FSIZE through FCB2 (+14 $80 / +15 $FF going in) (C $23)
;   13: FOPEN F.TXT (C $0F)
;   14: RDBLK 8 x 128 from RR 0 (C $27)
;   15: RDBLK 8 x 128 from RR 8 (C $27)
;
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xbblk5.asm --row disk   (run 1; --row cf3300: run 2)
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells.
;
; @disk empty
; @type-at 20 \r
; @cap 9000
; @caplen 430
; @timeout 60

CALSLT  equ     $001C
BDOS    equ     $F37D
cmode   equ     $A4F0
cno     equ     $A4F1
FCB     equ     $A600
DTAB    equ     $A800
DTA     equ     $F23D
cde     equ     $A408
chl     equ     $A40A
DRVSLT  equ     $FB22
tptr    equ     $A402
entry   equ     $A404
cb      equ     $A406
cc      equ     $A407
EXPTBL  equ     $FCC1
H_STKE  equ     $FEDA

DONE    equ     $9000           ; the capture (below HIMEM: the disk ROM's work area is live once H.STKE runs)
CAP     equ     $9001
FCB2    equ     $A640
ptr     equ     $A400
rsave   equ     $A410
buf     equ     $A412

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $42F
                ld      (hl), 0
                ldir
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
                ld      hl, CAP
                ld      (ptr), hl
                ld      hl, cases
                ld      (tptr), hl
                xor     a
                ld      (cno), a            ; the case counter (outside the cleared capture)
nxt:
                ld      hl, (tptr)
                ld      a, (hl)
                cp      $FF
                jp      z, fin
                ld      (cc), a
                inc     hl
                ld      a, (hl)             ; 0 keep, 1 name, 2 name + new, 3 name + $FF fill, 4 DE / HL
                inc     hl
                ld      (cmode), a
                cp      4
                jr      nz, notregs
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                ld      (cde), de
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                ld      (chl), de
                jp      fset
notregs:
                cp      8
                jp      z, m8               ; 8: FSIZE through FCB2, reset from the template
                cp      7
                jp      z, pokes            ; 7: pokes, then HL from the table
                cp      5
                jr      z, pokes            ; 5: poke into the FCB as it is
                or      a
                jp      z, fset
                push    af
                push    hl
                ld      hl, FCB             ; clear the FCB
                ld      b, 37
fc:
                ld      (hl), 0
                inc     hl
                djnz    fc
                pop     hl
                ld      de, FCB + 1
                ld      bc, 11
                ldir
                pop     af
                cp      2
                jr      nz, not2
                ld      de, FCB + 17
                ld      bc, 11
                ldir
not2:
                cp      3
                jp      nz, chk6
                push    hl
                ld      hl, FCB + 12        ; $FF at +12 .. +36
                ld      b, 25
ff1:
                ld      (hl), $FF
                inc     hl
                djnz    ff1
                pop     hl
chk6:
                ld      a, (cmode)
                cp      6
                jp      nz, fset
pokes:
                ld      b, (hl)             ; the pair count, then (offset, value) pairs
                inc     hl
pk1:
                ld      e, (hl)
                inc     hl
                ld      d, 0
                ld      a, (hl)
                inc     hl
                push    hl
                ld      hl, FCB
                add     hl, de
                ld      (hl), a
                pop     hl
                djnz    pk1
                ld      a, (cmode)
                cp      7
                jr      nz, fset
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                ld      (chl), de
m8:
                push    hl
                ld      hl, fcb2t
                ld      de, FCB2
                ld      bc, 37
                ldir
                pop     hl
fset:
                ld      (tptr), hl
                ld      a, (cno)            ; the DTA: 128 x ($40 + the case number)
                add     a, $40
                ld      hl, DTAB            ; 1040 bytes: $40 + the case + i
                ld      bc, 1040
fd:
                ld      (hl), a
                inc     a
                inc     hl
                dec     bc
                ex      af, af'
                ld      a, b
                or      c
                jr      z, fde
                ex      af, af'
                jr      fd
fde:
                ld      hl, cno
                inc     (hl)
                ld      a, (DRVSLT)
                or      a
                jr      nz, go
                ld      hl, (ptr)
                ld      de, 66
                add     hl, de
                ld      (ptr), hl
                jp      nxt
go:
                ld      a, (cc)
                ld      c, a
                ld      de, FCB
                ld      hl, (chl)           ; HL from the table (modes 4 and 7)
                ld      a, (cmode)
                cp      4
                jr      nz, notdta
                ld      de, (cde)
notdta:
                cp      8
                jr      nz, notf2
                ld      de, FCB2
notf2:
                di
                call    BDOS
                di
                ld      (rsave), hl         ; HL after the call, for the record's end
                push    af
                ld      hl, (ptr)
                ld      (hl), a
                inc     hl
                push    hl
                push    af
                pop     hl
                ld      a, l
                pop     hl
                ld      (hl), a
                inc     hl
                ex      de, hl
                ld      a, (cmode)
                ld      hl, FCB
                cp      8
                jr      nz, capf
                ld      hl, FCB2
capf:
                ld      bc, 37
                ldir
                ld      hl, DTAB
                ld      bc, 13
                ldir
                ld      a, (rsave+1)
                ld      (de), a
                inc     de
                ld      a, (rsave)
                ld      (de), a
                inc     de
                ld      a, (DTAB + 127)
                ld      (de), a
                inc     de
                ld      a, (DTAB + 128)
                ld      (de), a
                inc     de
                ld      a, (DTAB + 383)
                ld      (de), a
                inc     de
                ld      a, (DTAB + 384)
                ld      (de), a
                inc     de
                ld      a, (DTAB + 511)
                ld      (de), a
                inc     de
                ld      a, (DTAB + 512)
                ld      (de), a
                inc     de
                ld      a, (DTAB + 520)
                ld      (de), a
                inc     de
                ld      a, (DTAB + 700)
                ld      (de), a
                inc     de
                ld      a, (DTAB + 767)
                ld      (de), a
                inc     de
                ld      a, (DTAB + 768)
                ld      (de), a
                inc     de
                ld      a, (DTAB + 1023)
                ld      (de), a
                inc     de
                ld      a, (DTAB + 1024)
                ld      (de), a
                inc     de
                ld      (ptr), de
                pop     af
                jp      nxt
fin:
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

fcb2t:
                db      0, "F       TXT", 0, 0, $80, $FF
                ds      21, 0
cases:
                db      $1A, 4
                dw      $A800, $0000
                db      $16, 1, "F       TXT"
                db      $26, 7, 6, 14, $01, 15, $00, 33, $00, 34, $00, 35, $00, 36, $00
                dw      1024
                db      $10, 0
                db      $0F, 6, "F       TXT", 2, 14, $80, 15, $FF
                db      $27, 7, 5, 14, $80, 15, $01, 33, $00, 34, $00, 35, $00
                dw      1
                db      $26, 7, 5, 14, $80, 15, $00, 33, $03, 34, $00, 35, $00
                dw      0
                db      $27, 7, 5, 14, $00, 15, $04, 33, $00, 34, $00, 35, $00
                dw      1
                db      $28, 7, 5, 14, $80, 15, $00, 33, $06, 34, $00, 35, $00
                dw      1
                db      $26, 7, 5, 14, $80, 15, $00, 33, $02, 34, $00, 35, $00
                dw      2
                db      $26, 7, 5, 14, $01, 15, $00, 33, $D0, 34, $07, 35, $00
                dw      1
                db      $10, 0
                db      $23, 8
                db      $0F, 1, "F       TXT"
                db      $27, 7, 5, 14, $80, 15, $00, 33, $00, 34, $00, 35, $00
                dw      8
                db      $27, 7, 5, 14, $80, 15, $00, 33, $08, 34, $00, 35, $00
                dw      8
                db      $FF

                ds      $8000 - $, $FF
