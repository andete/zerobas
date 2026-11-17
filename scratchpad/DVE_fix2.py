#!/usr/bin/env python3
"""D-DISKVE (2026-11-17) round 2, from DVE_run1.out: after Ignore the CF-3300's C is the code the
handler was GIVEN (code | write), and the handler is entered with DE = the DISKVE cell + 1. Same
bytes in the wrapper; RDABS / WRABS keep the wrapper's B / C on Ignore. Refuses on a bad anchor."""
import sys


def edit(path, old, new):
    s = open(path).read()
    if s.count(old) != 1:
        sys.exit(f"{path}: anchor count {s.count(old)}: {old[:70]!r}")
    open(path, "w").write(s.replace(old, new))


edit("disk/kernel.asm", '''bdd_hand:
                ld      hl, (DISKVE)
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                ex      de, hl              ; HL = the handler
                pop     af
                ld      e, a                ; DSKIO's code
                pop     af                  ; A = the drive, Cy = a write
                push    af
                ld      b, a
                sbc     a, a
                and     1
                or      e
                ld      c, a                ; C = the code | the write bit
                ld      a, b                ; A = the drive
                ld      b, 1
                call    jp_hl
                ld      a, c
                dec     a
                jr      z, bdd_retry        ; 1 Retry
                jp      p, $0000            ; 2 Abort: the warm boot
                pop     af                  ; 0 Ignore
                pop     af
                pop     de
                pop     hl
                ld      a, $FF
                or      a                   ; Cy = 0, A = $FF: "ignored"
                ret
''', '''bdd_hand:
                pop     af
                ld      c, a                ; DSKIO's code
                pop     af                  ; A = the drive, Cy = a write
                push    af
                ld      b, a
                sbc     a, a
                and     1
                or      c
                ld      c, a                ; C = the code | the write bit
                ld      hl, (DISKVE)
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                ex      de, hl              ; HL = the handler; DE = the cell + 1, as the CF-3300's
                ld      a, b                ; A = the drive
                ld      b, 1
                push    bc
                call    jp_hl
                ld      a, c                ; the answer
                pop     bc                  ; B = 1, C = the code | write: what Ignore returns
                dec     a
                jr      z, bdd_retry        ; 1 Retry
                jp      p, $0000            ; 2 Abort: the warm boot
                pop     hl                  ; 0 Ignore: A = $FF already
                pop     hl
                pop     de
                pop     hl
                or      a                   ; Cy = 0, A = $FF: "ignored"
                ret
''')
edit("disk/fat.asm", '''                call    bdos_dskio
                pop     bc                  ; B := original count again (dskio clobbers B/C)
                pop     de                  ; (flags kept: CF is dskio's)
                jr      c, rdabs_ioerr
                inc     a                   ; A = $FF: DISKVE's handler answered Ignore
                jr      z, abs_ign
                ld      a, b                ; A := original count''', '''                call    bdos_dskio
                jr      c, abs_err
                inc     a                   ; A = $FF: DISKVE's handler answered Ignore
                jr      z, abs_ign
                pop     bc                  ; B := original count again (dskio clobbers B/C)
                pop     de
                ld      a, b                ; A := original count''')
edit("disk/fat.asm", '''abs_ign:
                ; After Ignore the CF-3300 returns A = $FF, B = 1, C = the handler's C (0
                ; for Ignore), DE = the sector, H = 1, L = $FF (scratchpad/XE2_ign_stock.out).
                ld      bc, $0100
                ld      hl, $01FF''', '''abs_ign:
                ; After Ignore the CF-3300 returns A = $FF, B = 1, C = the code the handler
                ; was given (bdos_dskio's B / C), DE = the sector, H = 1, L = $FF
                ; (scratchpad/XE2_ign_stock.out, DVE_run1.out).
                pop     hl                  ; (the count)
                pop     de                  ; the sector
                ld      hl, $01FF''')
edit("disk/fat.asm", '''                pop     af
                ret
rdabs_ioerr:''', '''                pop     af
                ret
abs_err:
                pop     bc
                pop     de                  ; the sector, handed back
rdabs_ioerr:''')
print("ok")
