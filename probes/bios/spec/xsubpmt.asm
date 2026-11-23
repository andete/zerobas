; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBPMT -- D-MSX2SPEC, docs/msx2/sub/PROMPT.md: the sub-ROM's PROMPT ($0181) through EXTROM, on the MSX2 / MSX2+
; references. Run with agent_wt.py --fresh.
; Per case (the table `cases`): clock-chip block 3 written through WRTCLK (sub-ROM $01F9, C = $30 + register) from
; `sets3` ($FF = leave); LINL40 := the case's width, CHGMOD (main $005F) into the case's mode; the name table's 24 rows
; := '#' ($23) by hand (so every character the call writes shows); CSRY / CSRX and CNSDFG from the table, CRTCNT 24;
; H.CHPU ($FDA4) := a RAM logger that appends A (the character CHPUT is asked to print) to a 48-byte log and counts;
; every OUT to port $98 is counted (@portlog, to $8000); A $5A / F $C3 through the stack, BC DE HL := $B1C1 $D1E1
; $4151; interrupts as the table says; the call. After it: A F IFF (read twice) BC DE HL IX IY, CSRY CSRX CNSDFG SCRMOD
; LINLEN CRTCNT, the H.CHPU log, the port-$98 count, clock-chip block 3 (ports $B4 / $B5), and four name-table rows from
; the case's first row (row length from SCRMOD / RG0SAV).
; The capture (CAP = C001): +0 $A5 when finished, +1 the case count; per case a 512-byte record from +2:
;   +0 case, +1 A, +2 F, +3 IFF, +4..+13 C B E D L H IXl IXh IYl IYh, +14 IFF first read,
;   +16 CSRY CSRX CNSDFG SCRMOD LINLEN CRTCNT, +24 H.CHPU count, +25..+72 the H.CHPU log (48),
;   +74 port-$98 byte count (2), +76 block 3 regs 0-12 after (13), +90 row length, +91 first row,
;   +96 four name-table rows (4 x 80), +511 $5E (sentinel).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubpmt.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries, hooks and work-area cells, the VDP's and the clock chip's
; published ports.
;
; @cap C000
; @caplen 2100
; @portlog 98 E948 E8F1
; @timeout 240

CHGMOD  equ     $005F
EXTROM  equ     $015F
DONE    equ     $C000
CAP     equ     $C001
RECLEN  equ     512
ARMFN   equ     $E8F1
ptr     equ     $E904
tp      equ     $E906
cidx    equ     $E908
rsave   equ     $E910
cur     equ     $E930                   ; mode, width, block-3 set, CSRY, CSRX, CNSDFG, flags, first row
cc      equ     $E940
nbase   equ     $E942
rlen    equ     $E944
LOGP    equ     $E948
hp      equ     $E94C
hcnt    equ     $E94E
HLOG    equ     $E9A0                   ; 48 bytes
HOOK    equ     $E960
LOGB    equ     $8000

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $20FF
                ld      (hl), 0
                ldir
                ld      a, $C9
                ld      (ARMFN), a
                ld      hl, 0
                ld      (LOGP), hl
                call    ARMFN
                ld      hl, hooksrc
                ld      de, HOOK
                ld      bc, hookend-hooksrc
                ldir
                ld      hl, CAP+2
                ld      (ptr), hl
                ld      hl, cases
                ld      (tp), hl
                xor     a
                ld      (cidx), a
c_next:
                ld      hl, (tp)
                ld      a, (hl)
                cp      $EE
                jp      z, finish
                ld      de, cur
                ld      bc, 8
                ldir
                ld      (tp), hl
                ld      a, (cur+2)
                ld      hl, sets3
                call    pick13
                ld      c, $30
                call    wrblk
                ld      a, (cur+1)
                ld      ($F3AE), a              ; LINL40
                ld      a, 29
                ld      ($F3AF), a              ; LINL32
                ld      a, (cur)
                call    CHGMOD
                di
                call    nsetup
                ; the name table := '#' over 24 rows (text modes only)
                ld      a, (cur)
                cp      2
                jr      nc, c_nofill
                ld      hl, (nbase)
                call    vwr
                ld      a, (rlen)
                ld      e, a
                ld      d, 24
c_f1:
                ld      b, e
c_f2:
                ld      a, $23
                out     ($98), a
                djnz    c_f2
                dec     d
                jr      nz, c_f1
c_nofill:
                ld      a, (cur+3)
                ld      ($F3DC), a              ; CSRY
                ld      a, (cur+4)
                ld      ($F3DD), a              ; CSRX
                ld      a, (cur+5)
                ld      ($F3DE), a              ; CNSDFG
                ld      a, 24
                ld      ($F3B1), a              ; CRTCNT
                ; the H.CHPU logger
                ld      hl, HLOG
                ld      (hp), hl
                xor     a
                ld      (hcnt), a
                ld      a, $C3
                ld      ($FDA4), a
                ld      hl, HOOK
                ld      ($FDA5), hl
                ld      hl, LOGB
                ld      (LOGP), hl
                ; the call
                ld      ix, $0181
                ld      hl, $5AC3
                push    hl
                ld      bc, $B1C1
                ld      de, $D1E1
                ld      hl, $4151
                ld      a, (cur+6)
                bit     0, a
                jr      z, c_di
                pop     af
                ei
                jr      c_go
c_di:
                pop     af
c_go:
                call    EXTROM
                push    iy
                push    ix
                push    hl
                push    de
                push    bc
                push    af
                ld      a, i
                push    af
                jp      pe, c_ion
                ld      a, i                    ; an "off" is read again (the NMOS ld a,i erratum)
c_ion:
                di
                push    af
                pop     hl
                ld      a, l
                rrca
                rrca
                and     1
                ld      (rsave+2), a
                pop     hl
                ld      a, l
                ld      (rsave+13), a
                pop     hl
                ld      (rsave), hl
                pop     hl
                ld      (rsave+3), hl
                pop     hl
                ld      (rsave+5), hl
                pop     hl
                ld      (rsave+7), hl
                pop     hl
                ld      (rsave+9), hl
                pop     hl
                ld      (rsave+11), hl
                ld      hl, (LOGP)
                ld      de, LOGB
                or      a
                sbc     hl, de
                push    hl
                ld      hl, 0
                ld      (LOGP), hl
                ld      a, $C9
                ld      ($FDA4), a
                ld      ($FDA5), a
                ld      ($FDA6), a
                ld      de, (ptr)
                ld      a, (cidx)
                ld      (de), a
                inc     de
                ld      a, (rsave+1)
                ld      (de), a
                inc     de
                ld      a, (rsave)
                ld      (de), a
                inc     de
                ld      a, (rsave+2)
                ld      (de), a
                inc     de
                ld      hl, rsave+3
                ld      bc, 10
                ldir
                ld      a, (rsave+13)
                rrca
                rrca
                and     1
                ld      (de), a
                inc     de
                inc     de                      ; +16
                ld      hl, cells
                ld      b, 6
c_cell:
                push    hl
                ld      a, (hl)
                inc     hl
                ld      h, (hl)
                ld      l, a
                ld      a, (hl)
                ld      (de), a
                inc     de
                pop     hl
                inc     hl
                inc     hl
                djnz    c_cell
                inc     de
                inc     de                      ; +24
                ld      a, (hcnt)
                ld      (de), a
                inc     de
                ld      hl, HLOG
                ld      bc, 48
                ldir                            ; +73
                inc     de
                pop     hl
                ex      de, hl
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl
                ex      de, hl                  ; +76
                ld      c, $30
                call    rdblk                   ; +89
                inc     de
                call    nsetup
                ld      a, (rlen)
                ld      (de), a                 ; +90
                inc     de
                ld      a, (cur+7)
                ld      (de), a                 ; +91
                ; four rows from the first row
                ld      hl, (ptr)
                ld      bc, 96
                add     hl, bc
                ex      de, hl
                ld      hl, (nbase)
                ld      a, (rlen)
                ld      c, a
                ld      b, 0
                ld      a, (cur+7)
                or      a
                jr      z, c_r0
c_ra:
                add     hl, bc
                dec     a
                jr      nz, c_ra
c_r0:
                call    vrd
                ld      b, 0
                ld      c, 4
c_rr:
                push    bc
                ld      b, 80
c_rb:
                in      a, ($98)
                ld      (de), a
                inc     de
                djnz    c_rb
                pop     bc
                ; the next row: re-address (a row may be 32 / 40 / 80 long)
                push    de
                ld      a, (rlen)
                ld      e, a
                ld      d, 0
                ld      hl, (cc)
                add     hl, de
                ld      (cc), hl
                call    vrd
                pop     de
                dec     c
                jr      nz, c_rr
                ld      hl, (ptr)
                ld      bc, RECLEN-1
                add     hl, bc
                ld      (hl), $5E
                inc     hl
                ld      (ptr), hl
                ld      a, (cidx)
                inc     a
                ld      (cidx), a
                ld      (CAP+1), a
                jp      c_next
finish:
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
                xor     a
                call    CHGMOD
                ei
fin:
                jr      fin

; the name base / row length from SCRMOD and RG0SAV
nsetup:
                ld      a, ($FCAF)
                ld      hl, ($F3B3)             ; TXTNAM
                ld      c, 40
                or      a
                jr      nz, ns1
                ld      a, ($F3DF)
                and     4
                jr      z, nsset
                ld      c, 80
                jr      nsset
ns1:
                ld      hl, ($F3BD)             ; T32NAM
                ld      c, 32
                dec     a
                jr      z, nsset
                ld      hl, 0
                ld      c, 80
nsset:
                ld      (nbase), hl
                ld      a, c
                ld      (rlen), a
                ret

; VRAM write / read address HL (< $4000); vrd remembers it in cc
vwr:
                xor     a
                out     ($99), a
                ld      a, $8E
                out     ($99), a
                ld      a, l
                out     ($99), a
                ld      a, h
                and     $3F
                or      $40
                out     ($99), a
                ret
vrd:
                ld      (cc), hl
                xor     a
                out     ($99), a
                ld      a, $8E
                out     ($99), a
                ld      a, l
                out     ($99), a
                ld      a, h
                and     $3F
                out     ($99), a
                ret

; HL := table + 13 * A
pick13:
                or      a
                ret     z
                ld      de, 13
pk:
                add     hl, de
                dec     a
                jr      nz, pk
                ret

; write the 13 nibbles at HL through WRTCLK, C = block base; $FF = skip
wrblk:
                ld      b, 13
wb:
                ld      a, (hl)
                cp      $FF
                jr      z, wb_s
                push    bc
                push    hl
                ld      ix, $01F9
                call    EXTROM
                di
                pop     hl
                pop     bc
wb_s:
                inc     hl
                inc     c
                djnz    wb
                ret

; read 13 registers of block C through the ports into DE.., DE advanced
rdblk:
                ld      b, 0
rb:
                ld      a, c
                or      b
                ld      (cc), a
                push    bc
                call    port_rd
                pop     bc
                ld      (de), a
                inc     de
                inc     b
                ld      a, b
                cp      13
                jr      nz, rb
                ret

mode_rd:
                ld      a, 13
                out     ($B4), a
                in      a, ($B5)
                and     $0F
                ret
mode_wr:
                push    af
                ld      a, 13
                out     ($B4), a
                pop     af
                out     ($B5), a
                ret
port_rd:
                call    mode_rd
                push    af
                and     $0C
                ld      b, a
                ld      a, (cc)
                rrca
                rrca
                rrca
                rrca
                and     3
                or      b
                call    mode_wr
                ld      a, (cc)
                and     $0F
                out     ($B4), a
                in      a, ($B5)
                and     $0F
                ld      b, a
                pop     af
                call    mode_wr
                ld      a, b
                ret

; H.CHPU: append A to HLOG (48 at most), count (copied to HOOK)
hooksrc:
                push    af
                push    hl
                ld      hl, hcnt
                inc     (hl)
                ld      hl, (hp)
                push    af
                ld      a, l
                cp      (HLOG+48) & 0FFh
                jr      z, hk_full
                pop     af
                ld      (hl), a
                inc     hl
                ld      (hp), hl
                jr      hk_x
hk_full:
                pop     af
hk_x:
                pop     hl
                pop     af
                ret
hookend:

cells:
                dw      $F3DC, $F3DD, $F3DE, $FCAF, $F3B0, $F3B1

; block 3, registers 0-12: ID, then 6 characters as low / high nibble
sets3:
                db      $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; 0 as found
                db      2, 1,4, 2,4, 3,4, 0,0, 1,5, 2,5                     ; 1 ID 2 "ABC" 0 "QR"
                db      2, 1,4, 2,4, 3,4, 4,4, 5,4, 6,4                     ; 2 ID 2 "ABCDEF"
                db      2, 0,0, 0,0, 0,0, 0,0, 0,0, 0,0                     ; 3 ID 2, six $00
                db      0, 8,5, 9,5, $A,5, 0,0, 0,0, 0,0                    ; 4 ID 0 (title) "XYZ"
                db      1, 8,5, 9,5, $A,5, 0,0, 0,0, 0,0                    ; 5 ID 1 (password) "XYZ"
                db      3, 8,5, 9,5, $A,5, 0,0, 0,0, 0,0                    ; 6 ID 3 "XYZ"
                db      2, 1,4, 2,4, 3,4, 0,0, 0,0, 0,0                     ; 7 ID 2 "ABC" then zeros

; mode, width, block-3 set, CSRY, CSRX, CNSDFG, flags (b0 EI), first row read (0-based)
cases:
                db      0, 40, 0,  6, 1, $00, 0, 4  ;  0 SCREEN 0 w40, as found, cursor (1, 6)
                db      0, 40, 0,  6, 1, $00, 1, 4  ;  1 the same, EI
                db      0, 40, 1,  6, 1, $00, 0, 4  ;  2 ID 2 "ABC" 0 "QR"
                db      0, 40, 2,  6, 1, $00, 0, 4  ;  3 ID 2 "ABCDEF"
                db      0, 40, 3,  6, 1, $00, 0, 4  ;  4 ID 2 six $00
                db      0, 40, 7,  6, 1, $00, 0, 4  ;  5 ID 2 "ABC" + zeros
                db      0, 40, 4,  6, 1, $00, 0, 4  ;  6 ID 0 title "XYZ"
                db      0, 40, 5,  6, 1, $00, 0, 4  ;  7 ID 1 password "XYZ"
                db      0, 40, 6,  6, 1, $00, 0, 4  ;  8 ID 3 "XYZ"
                db      0, 40, 2,  6, 5, $00, 0, 4  ;  9 "ABCDEF", cursor (5, 6)
                db      0, 40, 4,  6, 5, $00, 0, 4  ; 10 title (-> Ok?), cursor (5, 6)
                db      0, 80, 2,  6, 1, $00, 0, 4  ; 11 "ABCDEF", width 80
                db      1, 29, 2,  6, 1, $00, 0, 4  ; 12 "ABCDEF", SCREEN 1
                db      5, 40, 2,  6, 1, $00, 0, 4  ; 13 "ABCDEF", SCREEN 5
                db      0, 40, 2, 23, 1, $FF, 0, 20 ; 14 "ABCDEF", cursor on row 23, CNSDFG $FF
                db      0, 40, 4, 23, 1, $FF, 0, 20 ; 15 title (Ok), cursor on row 23, CNSDFG $FF
                db      $EE

                ds      $8000 - $, $FF
