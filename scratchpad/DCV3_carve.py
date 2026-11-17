#!/usr/bin/env python3
"""D-DISKCARVE6 step 3 (2026-11-17): the plan's reserve. skip_sp (7 B, call-only; its loop's jr
moves with it) -> the 7 B pad in front of $47B2 (disk/fat.asm); fmt_err (6 B, reached by
`jp c` only, preceded by `jp dskio`) -> the 7 B pad in front of $5FE5. Both leave the pin-free
[$607B, $75A5) span, so their bytes land in the hole in front of $75A5. Refuses on a bad anchor."""
import sys


def edit(path, old, new):
    s = open(path).read()
    if s.count(old) != 1:
        sys.exit(f"{path}: anchor count {s.count(old)}: {old[:70]!r}")
    open(path, "w").write(s.replace(old, new))


K = "disk/kernel.asm"
sk = '''skip_sp:
                ld      a,(hl)
                cp      ' '
                ret     nz
                inc     hl
                jr      skip_sp
'''
edit(K, '''; skip_sp -- HL past the blanks at it; A = the first other character. 💰 D-DSKFMT
; carve 34 (2026-11-10): the loop stood three times (NAME's `AS`, COPY's `TO`, FILES).
''' + sk, '''; (skip_sp -- MOVED by D-DISKCARVE6 step 3 to the pad in front of $47B2, disk/fat.asm.)
''')
edit("disk/fat.asm", '''                jr      fat_write_buf_allfats
                ds      $47B2 - $, $00      ; pad remainder (net-zero: k_47B2 unaffected)''',
     '''                jr      fat_write_buf_allfats
; skip_sp -- HL past the blanks at it; A = the first other character. 💰 D-DSKFMT carve 34
; (2026-11-10): NAME's `AS`, COPY's `TO`, FILES. MOVED here by D-DISKCARVE6 step 3 (2026-11-17).
''' + sk + '''                ds      $47B2 - $, $00      ; pad remainder (net-zero: k_47B2 unaffected)''')
fe = '''fmt_err:
                push    af
                call    mtoff
                pop     af
                ret
'''
edit(K, '''                jp      dskio               ; A = B = 0, Cy = 0 once written
''' + fe, '''                jp      dskio               ; A = B = 0, Cy = 0 once written
; (fmt_err -- MOVED by D-DISKCARVE6 step 3 to the pad in front of $5FE5.)
''')
edit(K, '''                jp      bdos_close_rd
                ds      $5FE5 - $, $00  ; pad to the first free-region kernel entry''',
     '''                jp      bdos_close_rd
; fmt_err -- the motor off, A / F kept (FORMAT's error exit; MOVED here by D-DISKCARVE6 step 3).
''' + fe + '''                ds      $5FE5 - $, $00  ; pad to the first free-region kernel entry''')
print("ok")
