#!/usr/bin/env python3
"""D-DISKCARVE6 step 1 (2026-11-17): free a contiguous hole in front of disk.rom's $75A5 pin
for D-DISKVE. Moves four call-only routines out of the pin-free [$607B, $75A5) span into
exact-fit pads in front of other pins, and takes 8 B of jp->jr / dead-jr savings inside the
span (plan: a read-only agent's carve plan, checked against the source). Refuses on any
missing or non-unique anchor."""
import sys


def edit(path, old, new):
    s = open(path).read()
    if s.count(old) != 1:
        sys.exit(f"{path}: anchor count {s.count(old)}: {old[:70]!r}")
    open(path, "w").write(s.replace(old, new))


def cut(path, text):
    edit(path, text, "")
    return text


K = "disk/kernel.asm"
# --- move 1 / 2: wrblk_mul_rr_rs (14 B) -> $4FF8; wrblk_off24 (11 B) -> $420C ---------------
m1 = cut(K, '''wrblk_mul_rr_rs:
                call    rh_flush            ; D-PUTCACHE: WRBLK_MUL* are WBUF+500..511,
                call    wmr_core
                ld      (WRBLK_MULACC), hl
                ld      (WRBLK_MULACC + 2), de
                ret
''')
m2 = cut(K, '''; wrblk_off24 -- WRBLK_REC (24 bits) := RR x RS, its low three bytes: the same product.
; 💰 D-DSKFMT carve 36 (2026-11-10): it had its own RAM shift-and-add loop.
wrblk_off24:
                call    wmr_core
                ld      (WRBLK_REC), hl
                ld      a, e
                ld      (WRBLK_REC + 2), a
                ret
''')
edit(K, ''';   out: WRBLK_MULACC = the 32-bit product; trashes AF, BC, DE, HL
; wmr_core --''', ''';   out: WRBLK_MULACC = the 32-bit product; trashes AF, BC, DE, HL
; (wrblk_mul_rr_rs itself and wrblk_off24 -- MOVED by D-DISKCARVE6 to the pads in front of
; $5006 and $4217: call-only, their bytes freed here for the hole in front of $75A5.)
; wmr_core --''')
edit(K, '''                jp      bcw_own             ; (the ownership test is in front of $5FE5)
                ds      $5006 - $, $00  ; pad up to the pinned $5006 SNEXT entry''',
     '''                jp      bcw_own             ; (the ownership test is in front of $5FE5)
; wrblk_mul_rr_rs -- MOVED here by D-DISKCARVE6 (2026-11-17); its contract is at wmr_core.
''' + m1 + '''                ds      $5006 - $, $00  ; pad up to the pinned $5006 SNEXT entry''')
edit("disk/pageenv.asm", '''                ld      (FAT_DEFER), a
                ret
                ds      $4217 - $, $00      ; pad to rdslt_h (net-zero: stays $4217)''',
     '''                ld      (FAT_DEFER), a
                ret
''' + m2.replace("; wrblk_off24 --", "; wrblk_off24 -- (MOVED here by D-DISKCARVE6, 2026-11-17)") +
     '''                ds      $4217 - $, $00      ; pad to rdslt_h (net-zero: stays $4217)''')

# --- move 3: hl_x128 / hl_x32 (8 B) -> $445A ------------------------------------------------
m3 = cut(K, '''hl_x128:
                add     hl, hl
                add     hl, hl
hl_x32:
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                ret
''')
edit(K, '''; hl_x128 / hl_x32 -- HL := HL x 128 / x 32 (16 bits, flags as `add hl,hl`'s).''',
     '''; hl_x128 / hl_x32 -- HL := HL x 128 / x 32 (16 bits, flags as `add hl,hl`'s): MOVED by
; D-DISKCARVE6 to the pad in front of $4462 (disk/driver.asm).''')
edit("disk/driver.asm", '''                pop     hl
                ret
                ds      $4462 - $, $00      ; pad to the collision point''',
     '''                pop     hl
                ret
; hl_x128 / hl_x32 -- HL := HL x 128 / x 32 (MOVED here by D-DISKCARVE6, 2026-11-17).
''' + m3 + '''                ds      $4462 - $, $00      ; pad to the collision point''')

# --- move 4: fmt_buf (8 B) -> $5016 ----------------------------------------------------------
m4 = cut(K, '''fmt_buf:
                push    ix
                pop     hl
                ld      bc, FMT_BUF
                add     hl, bc
                ret
; fmt_track --''')
s = open(K).read()
anchor = '''fmt_err:
                push    af
                call    mtoff
                pop     af
                ret
'''
if s.count(anchor) != 1:
    sys.exit("fmt_err anchor")
s = s.replace(anchor, anchor + "; (fmt_buf -- MOVED by D-DISKCARVE6 to the pad in front of $501E.)\n; fmt_track --", 1)
# m4 ended with "; fmt_track --": the cut removed that prefix too; restore it once
open(K, "w").write(s)
edit(K, '''                jp      (hl)                ; sav_disk_write, or BSAVE's bsv_open
                ds      $501E - $, $00  ; pad up to the pinned $501E FSIZE entry (M28)''',
     '''                jp      (hl)                ; sav_disk_write, or BSAVE's bsv_open
; fmt_buf -- HL := IX + FMT_BUF (MOVED here by D-DISKCARVE6, 2026-11-17).
''' + m4.replace("; fmt_track --", "") + '''                ds      $501E - $, $00  ; pad up to the pinned $501E FSIZE entry (M28)''')

# --- savings (all inside the span) ----------------------------------------------------------
F = "basic/fat-prim-body.inc"
edit(F, '''                jr      dc_result           ; (a jump to the next line: kept so the
                                            ; gate's removal left disk.rom byte-
                                            ; identical; 2 B a later carve may take)
''', '''                                            ; (the `jr dc_result` to the next line went
                                            ; to D-DISKCARVE6, 2026-11-17: 2 B)
''')
s = open(F).read()
if s.count("                jp      dskio_calslt    ;") != 2:
    sys.exit("dskio_calslt jp count")
s = s.replace("                jp      dskio_calslt    ;", "                jr      dskio_calslt    ;")
open(F, "w").write(s)
W = "basic/sv-diskwr.inc"
s = open(W).read()
for o, n in (("jp      z,sv_load_error", "jr      z,sv_load_error"),
             ("jp      c,sv_load_error        ; disk full / dir full", "jr      c,sv_load_error        ; disk full / dir full"),
             ("jp      c,sv_load_error        ; disk full / write error", "jr      c,sv_load_error        ; disk full / write error")):
    if s.count(o) != 1:
        sys.exit(f"{W}: {o}")
    s = s.replace(o, n)
open(W, "w").write(s)
edit("basic/sv-savdisk.inc", '''sav_fin:
                jp      disk_write_end''', '''sav_fin:
                jr      disk_write_end''')
print("ok")
