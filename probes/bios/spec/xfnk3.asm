; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XFNK3 -- docs/bios/INIFNK.md round 2 (2026-11-17), after its first review (run 2: the work area compared BEFORE the
; row-24 VRAM reads, whose RDVRM let an interrupt run on the reference -- the confirming pass's finding): INIFNK ($003E) with SEVERAL inputs and
; everything else read. Three cases:
;   1 FNKSTR all $00                                          CNSDFG 0    A / F $A5 / $00
;   2 FNKSTR per key: key 1 $00 x 16, key 2 $5A x 16, key 3 "ABCDEFGHIJKLMNOP" (no 0), key 4 "list " then $5A
;     padding (the default string, but not its zeros), keys 5-10 $5A x 16; CNSDFG $FF, the key line drawn by INITXT
;     and row 24 then overwritten with $5A (does INIFNK redraw it?)            A / F $00 / $FF
;   3 FNKSTR all $5A (XFNK2's case)                          CNSDFG 0    A / F $5A / $FF
; Every register is loaded with case-dependent garbage before the call (BC, DE, HL, IX, IY), interrupts OFF; the work
; area $F380-$FFFF is copied to $D000 just before the call and compared after it (FNKSTR excluded).
; Per case a 236-byte record: FNKSTR (160), A F B C D E H L IXh IXl IYh IYl after the call (12), LD A,I's flags (bit 2
; = IFF2), row 24's first 40 cells, the number of work-area bytes that changed outside FNKSTR (2) and the first ten
; such addresses (20), the sentinel $C3.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xfnk3.asm --row both
;
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells; VRAM through RDVRM / FILVRM.
;
; @cap C000
; @caplen 02C6
; @timeout 60

RDVRM   equ     $004A
FILVRM  equ     $0056
INITXT  equ     $006C
INIFNK  equ     $003E
CNSDFG  equ     $F3DE
LINL40  equ     $F3AE
CRTCNT  equ     $F3B1
FNKSTR  equ     $F87F
WAREA   equ     $F380
SNAP    equ     $D000

DONE    equ     $C000
CAP     equ     $C001
CAPLEN  equ     710                     ; 2 + 3 x 236
ptr     equ     $EF00
ccase   equ     $EF02
cnt     equ     $EF04
naddr   equ     $EF06
rowptr  equ     $EF08

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, CAPLEN - 1
                ld      (hl), 0
                ldir
                ld      hl, CAP+2
                ld      (ptr), hl
                xor     a
                ld      (ccase), a
c_lp:
                ; the screen: 40 columns, 24 rows, CNSDFG per case
                ld      a, 40
                ld      (LINL40), a
                ld      a, 24
                ld      (CRTCNT), a
                ld      a, (ccase)
                cp      1
                ld      a, 0
                jr      nz, c_cns
                ld      a, $FF
c_cns:
                ld      (CNSDFG), a
                call    INITXT
                di
                ; FNKSTR per case
                ld      a, (ccase)
                ld      hl, fnk0
                or      a
                jr      z, c_fk
                ld      hl, fnk1
                dec     a
                jr      z, c_fk
                ld      hl, fnk2
c_fk:
                ld      de, FNKSTR
                ld      bc, 160
                ldir
                ; row 24 := $5A (case 2: a redraw would show)
                ld      hl, 920
                ld      bc, 40
                ld      a, $5A
                call    FILVRM
                di
                ; the work area, copied
                ld      hl, WAREA
                ld      de, SNAP
                ld      bc, 3200                ; $F380-$FFFF
                ldir
                ; every register: case-dependent garbage
                ld      a, (ccase)
                ld      e, a
                ld      d, 0
                ld      hl, afs
                add     hl, de
                add     hl, de
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                push    de                      ; AF
                ld      a, (ccase)
                add     a, $11
                ld      b, a
                ld      c, $3C
                ld      d, $69
                ld      e, a
                ld      h, $A2
                ld      l, a
                ld      ix, $4321
                ld      iy, $8765
                pop     af
                call    INIFNK
                ; the registers, at once
                push    iy
                push    ix
                push    hl
                push    de
                push    bc
                push    af
                ld      a, i
                jp      pe, $+5                 ; off? read again: an interrupt accepted DURING `ld a,i` reads
                ld      a, i                    ; P/V 0 (the NMOS erratum, D-IFFREAD1)
                push    af
                di
                ; the record: FNKSTR
                ld      hl, FNKSTR
                ld      de, (ptr)
                ld      bc, 160
                ldir
                ld      (ptr), de
                pop     bc                      ; LD A,I's flags in C
                pop     hl                      ; A F
                ld      a, h
                call    emit
                ld      a, l
                call    emit
                pop     hl                      ; B C
                ld      a, h
                call    emit
                ld      a, l
                call    emit
                pop     hl                      ; D E
                ld      a, h
                call    emit
                ld      a, l
                call    emit
                pop     hl                      ; H L
                ld      a, h
                call    emit
                ld      a, l
                call    emit
                pop     hl                      ; IX
                ld      a, h
                call    emit
                ld      a, l
                call    emit
                pop     hl                      ; IY
                ld      a, h
                call    emit
                ld      a, l
                call    emit
                ld      a, c
                call    emit
                ; run 2: row 24's 40 bytes are RESERVED here and read only after the work-area comparison -- RDVRM
                ; re-enables interrupts on the reference, so run 1's comparison after it saw the probe's own interrupt
                ld      hl, (ptr)
                ld      (rowptr), hl
                ld      de, 40
                add     hl, de
                ld      (ptr), hl
                ; the work area compared (FNKSTR excluded): the count, and the first ten addresses
                ld      hl, 0
                ld      (cnt), hl
                ld      hl, (ptr)
                ld      (naddr), hl             ; the addresses go after the count: reserve 2 + 20
                ld      de, 22
                add     hl, de
                ld      (ptr), hl
                ld      hl, WAREA
                ld      de, SNAP
w_lp:
                ld      a, h                    ; skip FNKSTR ($F87F-$F91E)
                cp      $F8
                jr      c, w_cmp
                jr      nz, w_hi
                ld      a, l
                cp      $7F
                jr      c, w_cmp
                jr      w_next
w_hi:
                cp      $F9
                jr      nz, w_cmp
                ld      a, l
                cp      $1F
                jr      c, w_next
w_cmp:
                ld      a, (de)
                cp      (hl)
                jr      z, w_next
                push    hl
                push    de
                ld      de, (cnt)
                inc     de
                ld      (cnt), de
                ld      a, d
                or      a
                jr      nz, w_skip
                ld      a, e
                cp      11
                jr      nc, w_skip
                ; store the address at naddr + 2 + 2 x (cnt - 1)
                dec     a
                add     a, a
                add     a, 2
                ld      e, a
                ld      d, 0
                ld      ix, (naddr)
                add     ix, de
                pop     de
                pop     hl
                ld      (ix+0), l
                ld      (ix+1), h
                jr      w_next
w_skip:
                pop     de
                pop     hl
w_next:
                inc     de
                inc     hl
                ld      a, h
                or      l
                jr      nz, w_lp
                ld      ix, (naddr)
                ld      hl, (cnt)
                ld      (ix+0), l
                ld      (ix+1), h
                ; now row 24, into its reserved slot
                ld      hl, (ptr)
                push    hl
                ld      hl, (rowptr)
                ld      (ptr), hl
                ld      hl, 920
                ld      b, 40
r_lp:
                push    bc
                push    hl
                call    RDVRM
                call    emit
                pop     hl
                pop     bc
                inc     hl
                djnz    r_lp
                pop     hl
                ld      (ptr), hl
                di
                ld      a, $C3                  ; the record's sentinel
                call    emit
                ld      a, (ccase)
                inc     a
                ld      (ccase), a
                cp      3
                jp      nz, c_lp
                ld      a, $A5
                ld      (CAP+1), a
                ld      (DONE), a
                ei
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

; AF per case (pushed as DE: D = A, E = F)
afs:            dw      $A500, $00FF, $5AFF

fnk0:           ds      160, 0
fnk1:           ds      16, 0
                ds      16, $5A
                db      "ABCDEFGHIJKLMNOP"
                db      "list "
                ds      11, $5A
                ds      96, $5A
fnk2:           ds      160, $5A
