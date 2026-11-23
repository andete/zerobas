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
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xclk.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries, the clock IC's published ports.
;
; @cap C000
; @caplen 0200
; @timeout 60

EXTROM  equ     $015F
DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $E904
cc      equ     $E906
mb      equ     $E907
wv      equ     $E908
ov      equ     $E909

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $01FF
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

; C, the new value
wcases:
                db      $21, $05
                db      $25, $0A
                db      $31, $03
                db      $3C, $09
                db      $FF

                ds      $8000 - $, $FF
