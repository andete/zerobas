; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBPVR -- D-MSX2SPEC, docs/msx2/sub/PUTVRM.md: the sub-ROM's PUTVRM ($0129) through EXTROM, on the MSX2 / MSX2+
; references. Its inputs are unknown (MAP lists it, the handbook does not), so every register carries a distinct value
; and the probe records what changed.
; Per case (the table `cases`: SCRMOD, LINL40 / LINL32, F A C B E D L H, CSRX, CSRY): CHGMOD (main $005F) with the width
; set first; interrupts off, SCNCNT := $FF; CSRX / CSRY set; VRAM $00000-$07FFF := an address-dependent pattern
; ((hi XOR lo) + seed, seed = 8 x case + $13); the 16-bit sums of VRAM $08000-$0FFFF and $10000-$1FFFF; the work area
; $F380-$FFFE copied; the whole VDP state (@vdpfull); A F BC DE HL from the table, IX = $0129; the call. Then SP, every
; register, the interrupt state (read twice), the work-area cells that changed, the VDP state again, every VRAM byte in
; $00000-$07FFF that no longer holds its pattern, the two sums again, CSRX / CSRY.
; The probe runs on its own stack (SP := $F37E), so the work-area diff sees no stack traffic of ours.
; The capture (CAP = C001): +0 $A5 when finished, +1 the case count; per case a $230-byte record from +2:
;   +0 case, +1 A, +2 F, +3 B, +4 C, +5 D, +6 E, +7 H, +8 L, +9 IXh, +10 IXl, +11 IYh, +12 IYl (all after the call),
;   +13 IFF after, +14 CSRX after, +15 CSRY after, +16/17 the count of changed VRAM bytes in $0000-$7FFF,
;   +18/19 sum $8000-$FFFF before, +20/21 sum $10000-$1FFFF before, +22/23 and +24/25 the same after,
;   +26 the count of changed work-area bytes (255 = 255 or more), +27 0, +28/29 SP before the call, +30/31 SP after,
;   +32..+175 the first 48 changed VRAM bytes (address hi, lo, value read), +176..+303 the first 32 changed work-area
;   bytes (address lo, hi, before, after), +304..+417 the VDP state before, +418..+531 after (@vdpfull's 114 bytes).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubpvr.asm --row msx2all
; Decode: python3 scratchpad/xsubpvr_decode.py scratchpad/AE_xsubpvr_msx2.out
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports, the VDP's
; registers read by the debugger.
;
; @cap C000
; @caplen 1B00
; @vdpfull E8F0 E900
; @timeout 400

CHGMOD  equ     $005F
EXTROM  equ     $015F
CSRY    equ     $F3DC
CSRX    equ     $F3DD
LINL40  equ     $F3AE
LINL32  equ     $F3AF
SCNCNT  equ     $F3F6
DONE    equ     $C000
CAP     equ     $C001
RECLEN  equ     $0230
WABUF   equ     $DC00
WALEN   equ     $0C7F
SNAPFN  equ     $E8F0
SNAPP   equ     $E900
ptr     equ     $E904
tp      equ     $E906
cidx    equ     $E908
seed    equ     $E909
spb     equ     $E90A
spa     equ     $E90C
dcount  equ     $E90E
wcount  equ     $E910
iffv    equ     $E911
cur     equ     $E920                   ; SCRMOD, width, F, A, C, B, E, D, L, H, CSRX, CSRY = 12
rsv     equ     $E930                   ; F A C B E D L H IXl IXh IYl IYh after the call

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      sp, $F37E
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $1AFF
                ld      (hl), 0
                ldir
                ld      a, $C9
                ld      (SNAPFN), a
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
                ld      bc, 12
                ldir
                ld      (tp), hl
                ld      a, (cur+1)
                ld      (LINL40), a
                ld      (LINL32), a
                ld      a, (cur)
                call    CHGMOD
                di
                ld      a, $FF
                ld      (SCNCNT), a
                ld      a, (cur+10)
                ld      (CSRX), a
                ld      a, (cur+11)
                ld      (CSRY), a
                ld      a, (cidx)
                add     a, a
                add     a, a
                add     a, a
                add     a, $13
                ld      (seed), a
                call    vfill
                call    hisum
                ld      ix, (ptr)
                ld      (ix+18), c
                ld      (ix+19), b
                ld      (ix+20), e
                ld      (ix+21), d
                ld      hl, $F380
                ld      de, WABUF
                ld      bc, WALEN
                ldir
                ld      hl, (ptr)
                ld      bc, 304
                add     hl, bc
                ld      (SNAPP), hl
                call    SNAPFN
                ; the registers: F A, C B, E D, L H from the table
                ld      hl, (cur+2)
                push    hl
                ld      bc, (cur+4)
                ld      de, (cur+6)
                ld      hl, (cur+8)
                ld      ix, $0129
                pop     af
                ld      (spb), sp
                call    EXTROM
                ld      (spa), sp
                push    af
                push    bc
                push    de
                push    hl
                push    ix
                push    iy
                ld      a, i
                jp      pe, ie_on
                ld      a, i
ie_on:
                di
                push    af
                pop     hl
                ld      a, l
                rrca
                rrca
                and     1
                ld      (iffv), a
                pop     hl
                ld      (rsv+10), hl
                pop     hl
                ld      (rsv+8), hl
                pop     hl
                ld      (rsv+6), hl
                pop     hl
                ld      (rsv+4), hl
                pop     hl
                ld      (rsv+2), hl
                pop     hl
                ld      (rsv+0), hl
                call    wadiff
                ld      hl, (ptr)
                ld      bc, 418
                add     hl, bc
                ld      (SNAPP), hl
                call    SNAPFN
                ld      ix, (ptr)
                ld      a, (cidx)
                ld      (ix+0), a
                ld      a, (rsv+1)
                ld      (ix+1), a
                ld      a, (rsv+0)
                ld      (ix+2), a
                ld      a, (rsv+3)
                ld      (ix+3), a
                ld      a, (rsv+2)
                ld      (ix+4), a
                ld      a, (rsv+5)
                ld      (ix+5), a
                ld      a, (rsv+4)
                ld      (ix+6), a
                ld      a, (rsv+7)
                ld      (ix+7), a
                ld      a, (rsv+6)
                ld      (ix+8), a
                ld      a, (rsv+9)
                ld      (ix+9), a
                ld      a, (rsv+8)
                ld      (ix+10), a
                ld      a, (rsv+11)
                ld      (ix+11), a
                ld      a, (rsv+10)
                ld      (ix+12), a
                ld      a, (iffv)
                ld      (ix+13), a
                ld      a, (CSRX)
                ld      (ix+14), a
                ld      a, (CSRY)
                ld      (ix+15), a
                ld      hl, (spb)
                ld      (ix+28), l
                ld      (ix+29), h
                ld      hl, (spa)
                ld      (ix+30), l
                ld      (ix+31), h
                call    vdiff
                call    hisum
                ld      ix, (ptr)
                ld      (ix+22), c
                ld      (ix+23), b
                ld      (ix+24), e
                ld      (ix+25), d
                ld      hl, (ptr)
                ld      bc, RECLEN
                add     hl, bc
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

; vset: A = R#14 (the 16K block), HL = the address in it, C = $40 to write / $00 to read
vset:
                out     ($99), a
                ld      a, $8E
                out     ($99), a
                ld      a, l
                out     ($99), a
                ld      a, h
                and     $3F
                or      c
                out     ($99), a
                ret

; vfill: VRAM $0000-$7FFF := ((hi XOR lo) + seed)
vfill:
                xor     a
                call    vf_blk
                ld      a, 1
vf_blk:
                push    af
                ld      hl, 0
                ld      c, $40
                call    vset
                pop     af
                rrca
                rrca
                ld      d, a
                ld      a, (seed)
                ld      b, a
                ld      hl, 0
vf_l:
                ld      a, h
                or      d
                xor     l
                add     a, b
                out     ($98), a
                inc     hl
                ld      a, h
                cp      $40
                jr      nz, vf_l
                ret

; vdiff: every byte of $0000-$7FFF that is not its pattern -> count, first 48 at record +32
vdiff:
                ld      hl, 0
                ld      (dcount), hl
                ld      iy, (ptr)
                ld      bc, 32
                add     iy, bc
                xor     a
                call    vd_blk
                ld      a, 1
                call    vd_blk
                ld      hl, (dcount)
                ld      ix, (ptr)
                ld      (ix+16), l
                ld      (ix+17), h
                ret
vd_blk:
                push    af
                ld      hl, 0
                ld      c, 0
                call    vset
                pop     af
                rrca
                rrca
                ld      d, a
                ld      a, (seed)
                ld      b, a
                ld      hl, 0
vd_l:
                ld      a, h
                or      d
                xor     l
                add     a, b
                ld      e, a
                in      a, ($98)
                cp      e
                call    nz, vd_rec
                inc     hl
                ld      a, h
                cp      $40
                jr      nz, vd_l
                ret
vd_rec:
                ld      c, a
                push    hl
                ld      hl, (dcount)
                inc     hl
                ld      (dcount), hl
                ld      a, h
                or      a
                jr      nz, vr_x
                ld      a, l
                cp      49
                jr      nc, vr_x
                pop     hl
                push    hl
                ld      a, h
                or      d
                ld      (iy+0), a
                ld      (iy+1), l
                ld      (iy+2), c
                inc     iy
                inc     iy
                inc     iy
vr_x:
                pop     hl
                ret

; hisum: BC := sum of VRAM $08000-$0FFFF, DE := sum of $10000-$1FFFF (16-bit)
hisum:
                ld      hl, 0
                ld      a, 2
                call    blksum
                ld      a, 3
                call    blksum
                push    hl
                ld      hl, 0
                ld      a, 4
                call    blksum
                ld      a, 5
                call    blksum
                ld      a, 6
                call    blksum
                ld      a, 7
                call    blksum
                ex      de, hl
                pop     bc
                ret
blksum:
                push    hl
                ld      hl, 0
                ld      c, 0
                call    vset
                pop     hl
                ld      de, $4000
bs_l:
                in      a, ($98)
                add     a, l
                ld      l, a
                jr      nc, bs_n
                inc     h
bs_n:
                dec     de
                ld      a, d
                or      e
                jr      nz, bs_l
                ret

; wadiff: the work-area bytes $F380-$FFFE that differ from the copy -> count at +26, first 32 at +176
wadiff:
                ld      iy, (ptr)
                ld      bc, 176
                add     iy, bc
                xor     a
                ld      (wcount), a
                ld      hl, $F380
                ld      de, WABUF
                ld      bc, WALEN
wd_l:
                ld      a, (de)
                cp      (hl)
                call    nz, wd_rec
                inc     hl
                inc     de
                dec     bc
                ld      a, b
                or      c
                jr      nz, wd_l
                ld      ix, (ptr)
                ld      a, (wcount)
                ld      (ix+26), a
                ret
wd_rec:
                ld      a, (wcount)
                cp      255
                jr      z, wr_s
                inc     a
                ld      (wcount), a
wr_s:
                cp      33
                ret     nc
                ld      (iy+0), l
                ld      (iy+1), h
                ld      a, (de)
                ld      (iy+2), a
                ld      a, (hl)
                ld      (iy+3), a
                inc     iy
                inc     iy
                inc     iy
                inc     iy
                ret

; SCRMOD, width, F, A, C, B, E, D, L, H, CSRX, CSRY
cases:
                db      0, 40,  $00, $41, $11, $02, $0B, $09, $03, $05, 20, 15
                db      0, 40,  $FF, $42, $06, $03, $04, $0E, $07, $0C, 22, 10
                db      0, 40,  $00, $43, $13, $12, $15, $14, $01, $01, 18, 12
                db      0, 80,  $00, $41, $11, $02, $0B, $09, $03, $05, 20, 15
                db      0, 80,  $FF, $42, $06, $03, $04, $0E, $07, $0C, 22, 10
                db      0, 80,  $00, $43, $13, $12, $15, $14, $01, $01, 18, 12
                db      1, 32,  $00, $41, $11, $02, $0B, $09, $03, $05, 20, 15
                db      1, 32,  $FF, $42, $06, $03, $04, $0E, $07, $0C, 22, 10
                db      1, 32,  $00, $43, $13, $12, $15, $14, $01, $01, 18, 12
                db      5, 32,  $00, $41, $11, $02, $0B, $09, $03, $05, 20, 15
                db      5, 32,  $FF, $42, $06, $03, $04, $0E, $07, $0C, 22, 10
                db      5, 32,  $00, $43, $13, $12, $15, $14, $01, $01, 18, 12
                db      $EE

                ds      $8000 - $, $FF
