; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XCLK -- D-MSX2SPEC, docs/msx2/sub/REDCLK.md / WRTCLK.md: the sub-ROM's REDCLK ($01F5, C = 00MMAAAA -> A) and
; WRTCLK ($01F9, C, A) through EXTROM, on the MSX2 / MSX2+ references, against the clock IC read directly through
; its published ports ($B4 the register, $B5 the data).
; REDCLK: for every block 0-3 and register 0-15: MODE (register 13) := its bits 3-2 kept, the block bits := ANOTHER
; block ((block + 1) AND 3) by hand -- does the call select the block itself? -- then REDCLK, then MODE read by
; port, then the same register read by port with MODE's block bits set to the case's block.
; WRTCLK: four settings registers (block 2 reg 1 and 5, block 3 reg 1 and 12): the value before (port), WRTCLK
; with a new value, read back (port), MODE after, then the ORIGINAL written back by WRTCLK and read back -- the
; blocks are battery-backed (openMSX saves them), so the probe leaves them as found.
; Interrupts off throughout. The capture (CAP = C001): +0 $A5 when finished; +1..: 64 REDCLK records of 6 bytes
; (C, A, F, MODE before the call, MODE after, the port's value) then 4 WRTCLK records of 8 bytes (C, the value
; before, the value written, read back, A after, F after, MODE after, read back after the restore).
; Goldfish pass 1 (2026-11-23), appended after those (+417..): blocks 2 and 3 preset by port so every address
; separates -- block 2 reg r := NOT block 0 reg r, block 3 reg r := NOT block 1 reg r (low nibble) -- then
; R2: 52 REDCLK records of 7 bytes, C = blocks 0-3 x registers 0-12, MODE preset to the block (C's block XOR 2) with
; TE / AE := register AND 3 (all four pairs on every block): C, A, F, MODE before, MODE after, the named block's
; register by port, the preselected block's same register by port; blocks 2 / 3 then restored by port.
; W2: 4 WRTCLK records of 10 bytes, MODE preset to another block and each TE / AE pair, A with bits 7-4 set and
; odd- / even-parity low nibbles: C, MODE before, the named register before, the preselected block's same register
; before, A written, A after, F after, MODE after, the named register after, the preselected one after (restored by
; port). Then $5A, the sentinel.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xclk.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries, the clock IC's published ports.
;
; @cap C000
; @caplen 0400
; @timeout 60

EXTROM  equ     $015F
DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $E904
cc      equ     $E906
mb      equ     $E907
wv      equ     $E908
ov      equ     $E909
pv      equ     $E90A
pa      equ     $E90B
sv2     equ     $E910
sv3     equ     $E920

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
                ld      hl, CAP+1
                ld      (ptr), hl
                xor     a
                ld      (cc), a
r_next:
                ; MODE := bits 3-2 kept, the block bits := (block + 1) AND 3
                ld      a, (cc)
                rrca
                rrca
                rrca
                rrca
                inc     a
                and     3
                ld      b, a
                call    mode_rd
                and     $0C
                or      b
                call    mode_wr
                call    mode_rd
                ld      (mb), a
                ; the call
                ld      a, (cc)
                ld      c, a
                ld      ix, $01F5
                call    EXTROM
                di
                push    af
                ld      de, (ptr)
                ld      a, (cc)
                ld      (de), a
                inc     de
                pop     bc
                ld      a, b
                ld      (de), a                 ; A
                inc     de
                ld      a, c
                ld      (de), a                 ; F
                inc     de
                ld      a, (mb)
                ld      (de), a                 ; MODE before
                inc     de
                push    de
                call    mode_rd
                pop     de
                ld      (de), a                 ; MODE after
                inc     de
                push    de
                call    port_rd                 ; the register by port
                pop     de
                ld      (de), a
                inc     de
                ld      (ptr), de
                ld      a, (cc)
                inc     a
                ld      (cc), a
                cp      $40
                jr      nz, r_next
                ; WRTCLK
                ld      hl, wcases
w_next:
                ld      a, (hl)
                cp      $FF
                jr      z, finish
                ld      (cc), a
                inc     hl
                ld      a, (hl)
                ld      (wv), a
                inc     hl
                push    hl
                call    port_rd
                ld      (ov), a
                ld      a, (cc)
                ld      c, a
                ld      a, (wv)
                ld      ix, $01F9
                call    EXTROM
                di
                push    af
                ld      de, (ptr)
                ld      a, (cc)
                ld      (de), a
                inc     de
                ld      a, (ov)
                ld      (de), a
                inc     de
                ld      a, (wv)
                ld      (de), a
                inc     de
                push    de
                call    port_rd
                pop     de
                ld      (de), a                 ; read back
                inc     de
                pop     bc
                ld      a, b
                ld      (de), a                 ; A
                inc     de
                ld      a, c
                ld      (de), a                 ; F
                inc     de
                push    de
                call    mode_rd
                pop     de
                ld      (de), a                 ; MODE after
                inc     de
                push    de
                ld      a, (cc)
                ld      c, a
                ld      a, (ov)
                ld      ix, $01F9
                call    EXTROM                  ; the original back
                di
                call    port_rd
                pop     de
                ld      (de), a
                inc     de
                ld      (ptr), de
                pop     hl
                jr      w_next
finish:
                ; ---- goldfish pass 1: R2 ----
                ld      b, 0                    ; save blocks 2 / 3, then preset them
sv_lp:
                ld      a, b
                or      $20
                call    pread
                ld      hl, sv2
                ld      e, b
                ld      d, 0
                add     hl, de
                ld      (hl), a
                ld      a, b
                or      $30
                call    pread
                ld      hl, sv3
                add     hl, de
                ld      (hl), a
                ld      a, b                    ; block 2 reg r := NOT block 0 reg r
                call    pread
                cpl
                and     $0F
                ld      e, a
                ld      a, b
                or      $20
                call    pwrite
                ld      a, b                    ; block 3 reg r := NOT block 1 reg r
                or      $10
                call    pread
                cpl
                and     $0F
                ld      e, a
                ld      a, b
                or      $30
                call    pwrite
                inc     b
                ld      a, b
                cp      13
                jr      nz, sv_lp
                xor     a
                ld      (cc), a
r2_next:
                ld      a, (cc)
                and     $0F
                and     3
                add     a, a
                add     a, a
                ld      b, a                    ; TE / AE := register AND 3
                ld      a, (cc)
                rrca
                rrca
                rrca
                rrca
                and     3
                xor     2                       ; the preselected block
                or      b
                call    mode_wr
                call    mode_rd
                ld      (mb), a
                ld      a, (cc)
                ld      c, a
                ld      a, $5C                  ; A's high nibble on entry: 5
                ld      ix, $01F5
                call    EXTROM
                di
                push    af
                ld      de, (ptr)
                ld      a, (cc)
                ld      (de), a
                inc     de
                pop     bc
                ld      a, b
                ld      (de), a                 ; A
                inc     de
                ld      a, c
                ld      (de), a                 ; F
                inc     de
                ld      a, (mb)
                ld      (de), a                 ; MODE before
                inc     de
                push    de
                call    mode_rd
                pop     de
                ld      (de), a                 ; MODE after
                inc     de
                push    de
                ld      a, (cc)
                call    pread
                pop     de
                ld      (de), a                 ; the named block's register
                inc     de
                push    de
                ld      a, (cc)
                xor     $20
                call    pread
                pop     de
                ld      (de), a                 ; the preselected block's
                inc     de
                ld      (ptr), de
                ld      a, (cc)
                inc     a
                ld      b, a
                and     $0F
                cp      13
                ld      a, b
                jr      nz, r2_st
                add     a, 3                    ; register 13 -> the next block's 0
r2_st:
                ld      (cc), a
                cp      $40
                jp      nz, r2_next
                ld      b, 0                    ; restore blocks 2 / 3
rs_lp:
                ld      hl, sv2
                ld      e, b
                ld      d, 0
                add     hl, de
                ld      e, (hl)
                ld      a, b
                or      $20
                push    bc
                call    pwrite
                pop     bc
                ld      hl, sv3
                ld      e, b
                ld      d, 0
                add     hl, de
                ld      e, (hl)
                ld      a, b
                or      $30
                push    bc
                call    pwrite
                pop     bc
                inc     b
                ld      a, b
                cp      13
                jr      nz, rs_lp
                ; ---- goldfish pass 1: W2 ----
                ld      hl, w2cases
w2_next:
                ld      a, (hl)
                cp      $FF
                jp      z, w2_done
                ld      (cc), a
                inc     hl
                ld      a, (hl)
                ld      (mb), a                 ; MODE on entry
                inc     hl
                ld      a, (hl)
                ld      (wv), a
                inc     hl
                push    hl
                ld      a, (mb)                 ; the preselected block's address of the same register
                and     3
                rlca
                rlca
                rlca
                rlca
                ld      b, a
                ld      a, (cc)
                and     $0F
                or      b
                ld      (pa), a
                ld      a, (cc)
                call    pread
                ld      (ov), a
                ld      a, (pa)
                call    pread
                ld      (pv), a
                ld      a, (mb)
                call    mode_wr
                ld      de, (ptr)
                ld      a, (cc)
                ld      (de), a                 ; C
                inc     de
                push    de
                call    mode_rd
                pop     de
                ld      (de), a                 ; MODE before (read)
                inc     de
                ld      a, (ov)
                ld      (de), a
                inc     de
                ld      a, (pv)
                ld      (de), a
                inc     de
                ld      a, (wv)
                ld      (de), a
                inc     de
                ld      (ptr), de
                ld      a, (cc)
                ld      c, a
                ld      a, (wv)
                ld      ix, $01F9
                call    EXTROM
                di
                push    af
                ld      de, (ptr)
                pop     bc
                ld      a, b
                ld      (de), a                 ; A after
                inc     de
                ld      a, c
                ld      (de), a                 ; F after
                inc     de
                push    de
                call    mode_rd
                pop     de
                ld      (de), a                 ; MODE after
                inc     de
                push    de
                ld      a, (cc)
                call    pread
                pop     de
                ld      (de), a                 ; the named register after
                inc     de
                push    de
                ld      a, (pa)
                call    pread
                pop     de
                ld      (de), a                 ; the preselected one after
                inc     de
                ld      (ptr), de
                ld      a, (ov)                 ; restore by port
                ld      e, a
                ld      a, (cc)
                call    pwrite
                ld      a, (pv)
                ld      e, a
                ld      a, (pa)
                call    pwrite
                pop     hl
                jp      w2_next
w2_done:
                ld      a, $08
                call    mode_wr
                ld      hl, (ptr)
                ld      (hl), $5A               ; the sentinel
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
                ei
fin:
                jr      fin

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
; the register (cc) read through the ports, MODE's block bits := its block for the read
port_rd:
                call    mode_rd
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
                ret

; the register at A = 00MMAAAA read through the ports (MODE's bits 3-2 kept, its bank := MM); A := the value
pread:
                push    bc
                ld      c, a
                call    mode_rd
                and     $0C
                ld      b, a
                ld      a, c
                rrca
                rrca
                rrca
                rrca
                and     3
                or      b
                call    mode_wr
                ld      a, c
                and     $0F
                out     ($B4), a
                in      a, ($B5)
                and     $0F
                pop     bc
                ret
; E written to the register at A = 00MMAAAA through the ports (MODE's bits 3-2 kept, its bank := MM)
pwrite:
                push    bc
                ld      c, a
                call    mode_rd
                and     $0C
                ld      b, a
                ld      a, c
                rrca
                rrca
                rrca
                rrca
                and     3
                or      b
                call    mode_wr
                ld      a, c
                and     $0F
                out     ($B4), a
                ld      a, e
                out     ($B5), a
                pop     bc
                ret

; W2: C, MODE on entry, A
w2cases:
                db      $21, $03, $F5
                db      $25, $04, $07
                db      $31, $09, $3E
                db      $3C, $0E, $C1
                db      $FF

; C, the new value
wcases:
                db      $21, $05
                db      $25, $0A
                db      $31, $03
                db      $3C, $09
                db      $FF

                ds      $8000 - $, $FF
