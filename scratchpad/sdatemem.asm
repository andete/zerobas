; sdatemem.asm -- D-DOSDATE design input. PHASE ($C000): 1 before SDATE, 3 in
; the SDATE call, 4 after it, 5 done. The probe dumps $F330..$F345 at each phase
; change and logs the first page-1 PC while PHASE = 3.
BDOS    equ     $0005
PHASE   equ     $C000
        org     $0100
        ld      a, 1
        ld      (PHASE), a
        ld      bc, 0                   ; ~0.5 s busy wait: the poller sees this phase
w1:     dec     bc
        ld      a, b
        or      c
        jr      nz, w1
        ld      a, 3
        ld      (PHASE), a
        ld      hl, 1999
        ld      d, 12
        ld      e, 31
        ld      c, $2B                  ; SDATE 1999-12-31
        call    BDOS
        ld      a, 4
        ld      (PHASE), a
        ld      bc, 0                   ; ~0.5 s busy wait: the poller sees this phase
w2:     dec     bc
        ld      a, b
        or      c
        jr      nz, w2
        ld      a, 5
        ld      (PHASE), a
        ld      c, $00
        call    BDOS
        ret
