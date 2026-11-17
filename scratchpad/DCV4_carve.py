#!/usr/bin/env python3
"""D-DISKCARVE6 step 4 (2026-11-17): bytes for D-DOSDRVB part 2's MSX-DOS drive-B prompt.
A read-only agent's plan, each item checked against the source (every outside reference
`call` / `jp` / `ld`, the instruction in front of each source and target a terminator); two
of its items left out (toupper: needs the $47B9 anchor dropped, unproven; fmt_t_q: its pad's
pin line not found). Seven call-only routines MOVE out of the pin-free [$607B, $75A5) span
into exact-fit pads, and four in-span duplicate tails fold. Refuses on a bad anchor."""
import sys


def edit(path, old, new):
    s = open(path).read()
    if s.count(old) != 1:
        sys.exit(f"{path}: anchor count {s.count(old)}: {old[:70]!r}")
    open(path, "w").write(s.replace(old, new))


def move(src, body, note, dst, pad_line, header):
    edit(src, body, note)
    edit(dst, pad_line, header + body + pad_line)


K = "disk/kernel.asm"
F = "basic/fat-prim-body.inc"
TAG = "MOVED here by D-DISKCARVE6 step 4 (2026-11-17)"
OUT = "MOVED by D-DISKCARVE6 step 4 to the pad in front of"

# 1. fdc_wp_chkrdy (10 B) -> in front of $553C
move(K, '''fdc_wp_chkrdy:
                ld      a, (FDC_STATUS)
                and     ST_NOTRDY
                ret     z
                ld      a, 2
                scf
                ret
''', f"; (fdc_wp_chkrdy -- {OUT} $553C.)\n", K,
     '''                ds      $553C - $, $00      ; pad to the canonical _GDATE entry''',
     f"; fdc_wp_chkrdy -- the write path's NOT READY test, CY / A = 2 or NC ({TAG}).\n")
edit(K, '''; --- fdc_wp_chkrdy: the write path's NOT READY test (D-DISKERR) --------------''',
     '''; --- fdc_wp_chkrdy: the write path's NOT READY test (D-DISKERR; the body is in front of $553C) --''')

# 3. fmt_off (7 B of data) -> in front of $50E0
move(K, '''fmt_off:
                db      13, 17, 19, 20, 21, 22, 26
''', f"; (fmt_off -- {OUT} $50E0; its loop tests the pointer's low byte for EQUALITY.)\n", K,
     '''                ds      $50E0 - $, $00  ; pad up to the pinned CONIN line-routine entry''',
     f"; fmt_off -- the boot-sector offsets dskfmt_body sets ({TAG}).\n")

# 4. fmt_bkey (7 B) -> in front of $77B8
move(K, '''fmt_bkey:
                ld      ix,chget_getbyte
                jp      calbak
''', f"; (fmt_bkey -- {OUT} $77B8.)\n", K,
     '''                ret
                ds      $77B8 - $, $00
                jp      k_77B8          ; $77B8''',
     "")
# (the pad line above starts with `ret` -- re-insert the body AFTER that ret)
s = open(K).read()
bad = '''; (fmt_bkey -- ''' + OUT + ''' $77B8.)\n'''
s = s.replace('''fmt_bkey:
                ld      ix,chget_getbyte
                jp      calbak
                ret
                ds      $77B8 - $, $00
                jp      k_77B8          ; $77B8''', '''                ret
; fmt_bkey -- CALL FORMAT's key, through main's CHGET (''' + TAG + ''').
fmt_bkey:
                ld      ix,chget_getbyte
                jp      calbak
                ds      $77B8 - $, $00
                jp      k_77B8          ; $77B8''')
if s.count("fmt_bkey:") != 1 or "ret\n; fmt_bkey --" not in s:
    sys.exit("fmt_bkey placement")
open(K, "w").write(s)

# 5. fat_total_clusters (6 B) -> in front of $544E
move(F, '''fat_total_clusters:
                ; D-WCACHE W1: fat_mount computed it; no boot-sector read, so no
                ; failure either (Cy = 0, which every caller's `ret c` expects).
                ld      de, (FAT_TOTCLUS)
                or      a
                ret
''', f"; (the body -- {OUT} $544E, disk/kernel.asm.)\n", K,
     '''                ds      $544E - $, $00  ; pad up to the pinned $544E INNOE entry (M22a)''',
     f"; fat_total_clusters -- DE = total clusters, Cy = 0 (fat_mount's, D-WCACHE W1; {TAG}).\n")

# 6. fcf_zero (4 B) -> in front of $43A4 (disk/driver.asm)
move(F, '''fcf_zero:
                ld      de, 0
                ret
''', f"; (fcf_zero -- {OUT} $43A4, disk/driver.asm.)\n", "disk/driver.asm",
     '''                ds      $43A4 - $, $00      ; net-zero: fdc_write_phys stays at $43A4''',
     f"; fcf_zero -- fat_count_free's DE := 0 exit ({TAG}).\n")

# 8. disk_putbyte (7 B -> 8 B as jp) -> in front of $5058; its jr c becomes jp c
edit("basic/sv-diskwr.inc", '''disk_putbyte:
                call    fat_io_putbyte
                jr      c,sv_load_error        ; disk full / write error
                ret
''', f"; (disk_putbyte -- {OUT} $5058, disk/kernel.asm.)\n")
edit(K, '''                ds      $5058 - $, $00  ; pad up to the pinned $5058 SETDTA-cache entry''',
     f'''; disk_putbyte -- A = the byte, appended; a write error -> sv_load_error ({TAG}).
disk_putbyte:
                call    fat_io_putbyte
                jp      c,sv_load_error        ; disk full / write error
                ret
                ds      $5058 - $, $00  ; pad up to the pinned $5058 SETDTA-cache entry''')

# 9. hkcv_float (6 B) -> in front of $50A9; the jr nz into it becomes jp nz
move(K, '''hkcv_float:
                ld      de,FAC
                ldir                        ; the string's bytes ARE the packed value
                scf                         ; FACTYP is already the width
                ret
''', f"; (hkcv_float -- {OUT} $50A9.)\n", K,
     '''                ds      $50A9 - $, $00  ; pad remainder up to the kernel's $50A9 target''',
     f"; hkcv_float -- hk_cv's float: the string's bytes into FAC ({TAG}).\n")
edit(K, '''                jr      nz,hkcv_float''', '''                jp      nz,hkcv_float       ; (moved out of jr reach: carve step 4)''')

# in-span: hkdf_done falls into hkdf_bad; hkdf_bad is hk_claim_status's body
edit(K, '''hkdf_done:
                ld      (FAC),de
                xor     a
                ld      (DISKOP_STATUS),a   ; counted
                scf
                ret
hkdf_bad:
                ld      (DISKOP_STATUS),a   ; A = the ERR code main raises
                scf
                ret
''', '''hkdf_done:
                ld      (FAC),de
                xor     a                   ; counted (falls into hkdf_bad: carve step 4)
hkdf_bad:
                jp      hk_claim_status     ; DISKOP_STATUS := A, CF=1 (the same body)
''')
# in-span: fat_dir_update's write-back tail = fat_dir_create's
edit(F, '''                call    dir_stamp_date      ; +22..25 := time 0, date 0821h (as the CF-3300)
                ; write the dir sector back.
                ld      de, (FWR_DIRSEC)''', '''                call    dir_stamp_date      ; +22..25 := time 0, date 0821h (as the CF-3300)
                ; write the dir sector back.
fdir_wrback:                                ; (fat_dir_update's tail too: carve step 4)
                ld      de, (FWR_DIRSEC)''')
edit(F, '''                ld      hl, FWR_BYTES
                ld      bc, 4
                ldir
                ; write the dir sector back.
                ld      de, (FWR_DIRSEC)
                ld      hl, FAT_MBUF
                call    fatprim_write_sector
                ret     c
                or      a                   ; Cy = 0 success
                ret
''', '''                ld      hl, FWR_BYTES
                ld      bc, 4
                ldir
                jr      fdir_wrback         ; write the dir sector back (carve step 4)
''')
# in-span: fat_advance's tail = fat_open's
edit(F, '''fat_open:
                ld      hl, (FAT_FIRSTCLUS)
                ld      (FAT_CURCLUS), hl''', '''fat_open:
                ld      hl, (FAT_FIRSTCLUS)
fat_open_at:                                ; (fat_advance's tail too: carve step 4)
                ld      (FAT_CURCLUS), hl''')
edit(F, '''                call    fat_next_cluster
                ld      (FAT_CURCLUS), hl
                xor     a
                ld      (FAT_CLUSSEC), a
                ret
''', '''                call    fat_next_cluster
                jr      fat_open_at         ; FAT_CURCLUS := HL, the sector index 0
''')
print("ok")
