; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; p1vec.asm -- D-TPAP1: what an MSX-DOS program sees in PAGE 1, and whether the
; page-0 inter-slot entries still work from the TPA. Our own program; each step
; writes its number to $C000 BEFORE it runs, so a crash names the step, and its
; answer to $C001+ (9 = all done). The probe reads $C000.. back from RAM.
BDOS    equ     $0005
RDSLT   equ     $000C
WRSLT   equ     $0014
CALSLT  equ     $001C
ENASLT  equ     $0024
RSLREG  equ     $0138               ; main-ROM BIOS: A = the primary slot register
EXPTBL  equ     $FCC1
RAMAD1  equ     $F342
        org     $0100
        ld      a, 1
        ld      ($C000), a
        ld      a, $A5              ; a plain store into page 1, read back
        ld      ($4300), a
        ld      a, ($4300)
        ld      ($C001), a
        ld      a, 2
        ld      ($C000), a
        ld      a, (RAMAD1)         ; RDSLT from the RAM slot, page 1
        ld      hl, $4300
        call    RDSLT
        ld      ($C002), a
        ld      a, 3
        ld      ($C000), a
        ld      a, (RAMAD1)         ; WRSLT $5A into the RAM slot, read back plainly
        ld      hl, $4301
        ld      e, $5A
        call    WRSLT
        ld      a, ($4301)
        ld      ($C003), a
        ld      a, 4
        ld      ($C000), a
        ld      iy, (EXPTBL - 1)    ; IYh = the main ROM's slot
        ld      ix, RSLREG
        call    CALSLT
        ld      ($C004), a
        ld      a, 5
        ld      ($C000), a
        rst     $30                 ; CALLF: slot 0, RSLREG
        db      $00
        dw      RSLREG
        ld      ($C005), a
        ld      a, 6
        ld      ($C000), a
        ld      a, (RAMAD1)         ; ENASLT the RAM slot into page 1 (already there)
        ld      h, $40
        call    ENASLT
        ld      a, ($4300)
        ld      ($C006), a
        ld      a, 7
        ld      ($C000), a
        ld      c, $0C              ; a BDOS call, then page 1 again
        call    BDOS
        ld      a, ($4301)
        ld      ($C007), a
        ld      a, ($FFFF)          ; slot 3's subslots after it all
        cpl
        ld      ($C008), a
        in      a, ($A8)
        ld      ($C009), a
        ld      a, 8
        ld      ($C000), a
        ld      c, $0C              ; CPMVER through $F37D, not $0005 (D-TPAPTAIL)
        call    $F37D
        ld      ($C00A), a
        ld      a, l
        ld      ($C00B), a
        ld      a, 9
        ld      ($C000), a
        ld      c, $00
        call    BDOS
        ret
