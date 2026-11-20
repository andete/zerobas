; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XSCANK -- docs/bios/SCANL.md, D-SCANLPAINT (2026-11-20): WHERE does the VG-8020 keep K, the run length of the most
; recent SCREEN 2 SCANR that its SCANL paints on top of HL? XGFX6 re-presets the graphics work area $F92D-$F955
; before every case and K still carried across cases, so it lives somewhere else. Here: SCREEN 2 (CHGMOD), the
; pattern table as CHGMOD leaves it, the colour bytes of row 0's characters 0 and 1 := $F4 (run 1 left them as CHGMOD
; did and saw no border: HL 256 on both), BDRATR := 15, then three
; scans from X 0 of pixel row 0 with B = 0 (count, do not paint), DE = 1, each with ONE border pixel set in the row:
;   case 0  VRAM $0008 := $80   border at X 8: run 8
;   case 1  VRAM $0000 := $20   border at X 2: run 2
;   case 2  VRAM $0000 := $04   border at X 5: run 5
; (the previous case's border byte cleared first). After each SCANR, interrupts off at once: the whole work area
; $F380-$FFFF is recorded. A cell reading 8 / 2 / 5 (or a 16-bit pair) across the three is a candidate for K.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xscank.asm --row nodisk
; The capture: CAP+0 = $A5 when finished; per case a record from CAP+1 of 3200 + 3 bytes: HL (low, high) after,
; then $F380-$FFFF, then the sentinel $C3.
;
; CLEAN-ROOM: 100% own code; published BIOS entries (CHGMOD, WRTVRM, SCANR), work-area RAM, VRAM through the BIOS.
;
; @cap C000
; @caplen 2600
; @timeout 60

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
cidx    equ     $EF02
CLOC    equ     $F92A
CMASK   equ     $F92C
BDRATR  equ     $FCB2
WRTVRM  equ     $004D
CHGMOD  equ     $005F
SCANR   equ     $012C

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      (ptr), hl
                ld      a, 2
                call    CHGMOD
                di
                ld      a, 15
                ld      (BDRATR), a
                ld      hl, $2000               ; colour table, char 0 row 0: foreground 15, background 4
                ld      a, $F4
                call    WRTVRM
                ld      hl, $2008               ; char 1 row 0
                ld      a, $F4
                call    WRTVRM
                di
                xor     a
                ld      (cidx), a
c_loop:
                ld      a, (cidx)
                ld      hl, cases
                add     a, a
                add     a, a                    ; 4 bytes a case: clear addr, set addr low, value
                ld      e, a
                ld      d, 0
                add     hl, de
                ld      e, (hl)                 ; the address to clear (low; high 0)
                inc     hl
                ld      d, (hl)                 ; the address to set (low; high 0)
                inc     hl
                ld      b, (hl)                 ; the value
                push    bc
                push    de
                ld      l, e
                ld      h, 0
                xor     a
                call    WRTVRM
                pop     de
                pop     bc
                ld      l, d
                ld      h, 0
                ld      a, b
                call    WRTVRM
                di
                ld      hl, 0
                ld      (CLOC), hl
                ld      a, $80
                ld      (CMASK), a
                ld      b, 0
                ld      de, 1
                call    SCANR
                di
                ex      de, hl                  ; DE := HL (the run)
                ld      hl, (ptr)
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl
                ex      de, hl                  ; DE := record pointer
                ld      hl, $F380
                ld      bc, 3200
                ldir
                ex      de, hl
                ld      (hl), $C3
                inc     hl
                ld      (ptr), hl
                ld      a, (cidx)
                inc     a
                ld      (cidx), a
                cp      3
                jr      c, c_loop
                ld      a, $A5
                ld      (DONE), a
hang:
                jr      hang

cases:
                db      $00, $08, $80, 0        ; clear $0000 (nothing yet), set $0008 := $80
                db      $08, $00, $20, 0        ; clear $0008, set $0000 := $20
                db      $00, $00, $04, 0        ; ($0000 overwritten) set $0000 := $04
