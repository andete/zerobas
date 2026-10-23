; D-TPAPTAIL (a): an MSX-DOS program calls $F37D (C = $0C CPMVER) instead of $0005.
; $C000 = the step started (2 = done); $C001/$C002 = L, H; $C003 = A.
        org     $0100
        ld      a, 1
        ld      ($C000), a
        ld      c, $0C
        call    $F37D
        ld      ($C003), a
        ld      a, l
        ld      ($C001), a
        ld      a, h
        ld      ($C002), a
        ld      a, 2
        ld      ($C000), a
        ld      c, $00
        call    $0005
        ret
