; sdatebad.asm -- D-DOSDATE: what does SDATE return, and store, for each date?
; For every row of `cases` (year word, month, day): SDATE, then record A and
; the day count at $F33B..$F33C into RESULT + 3 x i. PHASE ($C000) = 2 when done.
BDOS    equ     $0005
PHASE   equ     $C000
RESULT  equ     $C010
DAYS    equ     $F33B
        org     $0100
        ld      a, 1
        ld      (PHASE), a
        ld      ix, cases
        ld      iy, RESULT
        ld      b, NCASES
loop:   push    bc
        ld      l, (ix+0)
        ld      h, (ix+1)
        ld      d, (ix+2)
        ld      e, (ix+3)
        push    ix
        push    iy
        ld      c, $2B                  ; SDATE
        call    BDOS
        pop     iy
        pop     ix
        ld      (iy+0), a
        ld      a, (DAYS)
        ld      (iy+1), a
        ld      a, (DAYS + 1)
        ld      (iy+2), a
        ld      de, 4
        add     ix, de
        ld      de, 3
        add     iy, de
        pop     bc
        djnz    loop
        ld      a, 2
        ld      (PHASE), a
        ld      c, $00
        call    BDOS
        ret

cases:  db low 2100, high 2100, 1, 1           ; 0 past 2099
        db low 1979, high 1979, 12, 31         ; 1 before 1980
        db low 1999, high 1999, 13, 1          ; 2 month 13
        db low 1999, high 1999, 0, 1           ; 3 month 0
        db low 1999, high 1999, 1, 0           ; 4 day 0
        db low 1999, high 1999, 2, 29          ; 5 not a leap year
        db low 1999, high 1999, 4, 31          ; 6 April has 30
        db low 2000, high 2000, 2, 29          ; 7 leap year: valid
        db low 1980, high 1980, 1, 1           ; 8 the epoch
        db low 2099, high 2099, 12, 31         ; 9 the last day?
        db low 1999, high 1999, 12, 31         ; 10 valid, last so later tests see it
NCASES  equ     ($ - cases) / 4
