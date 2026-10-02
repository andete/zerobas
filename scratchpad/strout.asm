; strout.asm -- BDOS $09 STROUT, then terminate. PHASE ($C000) 1 before, 2 after.
BDOS    equ     $0005
PHASE   equ     $C000
        org     $0100
        ld      a, 1
        ld      (PHASE), a
        ld      de, msg
        ld      c, $09
        call    BDOS
        ld      a, 2
        ld      (PHASE), a
        ld      c, $00
        call    BDOS
        ret
msg:    db      "HELLO-STROUT$"
