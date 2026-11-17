#!/usr/bin/env python3
"""D-DOSDRVB part 1 (2026-11-17): SELDSK stores the drive in $F247 (CURDRV_CELL), as on the
CF-3300 (scratchpad/XB_stock.out: SELDSK 1 -> $F247 = 1, CURDRV 1). The body moves into the
pin-free span (D-DISKCARVE6 step 3's 15 B); the old 4 B site in front of $55E6 becomes a jp.
Refuses on a bad anchor."""
import sys


def edit(path, old, new):
    s = open(path).read()
    if s.count(old) != 1:
        sys.exit(f"{path}: anchor count {s.count(old)}: {old[:70]!r}")
    open(path, "w").write(s.replace(old, new))


K = "disk/kernel.asm"
edit(K, '''seldsk_drv_body:
                ld      a, (DRVCNT)     ; DRVCNT = $F347 = logical-drive count ($02)
                ret
''', '''seldsk_drv_body:
                jp      seldsk_set      ; D-DOSDRVB: the body is in the pin-free span
''')
edit(K, '''                jr      bdos_dskio

; 🔴 D-ALIASWCELL (2026-09-23)''', '''                jr      bdos_dskio

; seldsk_set -- BDOS $0E SELDSK: E = the drive (0 A:, 1 B:) -> A = the logical-drive count
; (DRVCNT, $F347). 🎯 D-DOSDRVB part 1 (2026-11-17): the drive is STORED in $F247 (CURDRV_CELL)
; as on the CF-3300, so CURDRV answers it (scratchpad/XB_stock.out); it only returned the count.
; An E past the count leaves $F247 alone (not measured on the reference). Every register but
; A / F as before.
seldsk_set:
                ld      a, (DRVCNT)
                cp      e
                ret     c
                ret     z               ; E >= the count: not a drive
                push    af
                ld      a, e
                ld      (CURDRV_CELL), a
                pop     af
                ret

; 🔴 D-ALIASWCELL (2026-09-23)''')
print("ok")
