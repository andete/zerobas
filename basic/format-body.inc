; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; format-body.inc — CALL FORMAT's sector-build/write BULK (shared body).
;
; docs/spec-evict-call-format.md. This is the pure geometry-driven engine that
; clears the FAT/root region, stamps every FAT copy's head, and writes the boot
; sector — everything AFTER the interactive 360k/720k menu has already picked a
; geometry descriptor. Entered with HL = the chosen descriptor's base address
; (GEOM_360K or GEOM_720K); out: Cy = 0 ok, Cy = 1 = no disk / write error (the
; write_sector disposition, tail-propagated all the way to the caller).
;
; Included from TWO homes, exactly the printusing.asm / pu-render.inc pattern
; (docs/spec-evict-printusing.md / commit c3fc2d8):
;   * lean 16 KB cart (basic/format.asm, ROM_BASE >= $4000): inline, right after
;     fmt_sel_720 falls through into fmt_selected below — BYTE-IDENTICAL to the
;     pre-eviction build (this file is a pure relocation of that exact code,
;     nothing added/removed/reordered).
;   * sub-ROM PAGE-1 tenant (sub/format.asm, repack): format_tenant reads
;     FMT_GEOMSEL (RAM) to pick GEOM_360K/GEOM_720K (which live sub-side too,
;     included via this same file) and jumps in here. `write_sector` there is
;     re-bound to a SUB-LOCAL CALSLT write path (main's basic/fat.asm
;     write_sector is page-1-main-resident, invisible to a page-1 tenant) that
;     also stashes the disposition in FMT_RESULT (RAM) — Cy cannot ride back
;     through subrom_call/CALSLT to the resident stub (spec §4), but every
;     write in this body funnels through that one sub-local write_sector, so
;     FMT_RESULT is always fresh by the time control returns there.
;
; Clean-room: our own code, extracted verbatim from basic/format.asm (see that
; file's header for the full CALL FORMAT provenance / oracle citations).

; --- geometry descriptor offsets (used by fmt_geom_byte/fmt_geom_word below) --
GM_FIRSTFAT     equ     0       ; word: first FAT sector (= reserved sector count)
GM_NUMFATS      equ     2       ; byte: number of FAT copies
GM_SECPERFAT    equ     3       ; word: sectors per FAT copy
GM_LASTSYS      equ     5       ; word: last system sector to clear (= firstData - 1)
GM_MEDIA        equ     7       ; byte: media descriptor (FAT entry 0)
GM_BOOT         equ     8       ; 32-byte boot-sector template (jump + OEM + BPB + hidden)

fmt_selected:
                ld      (FMT_DESC),hl
                ; --- clear sectors firstFAT..lastSys (FATs + root directory) ---
                call    fmt_zero_buf        ; FSECTOR_BUF = 512 zeros
                ld      a,GM_FIRSTFAT
                call    fmt_geom_byte       ; firstFAT (low byte; < 256)
                ld      (FMT_SEC),a
fmt_zloop:
                ld      a,GM_LASTSYS
                call    fmt_geom_byte       ; lastSys (low byte; < 256)
                ld      c,a
                ld      a,(FMT_SEC)
                cp      c
                jr      c,fmt_zwrite        ; sec < lastSys -> write
                jr      z,fmt_zwrite        ; sec == lastSys -> write (inclusive)
                jr      fmt_fatheads        ; sec > lastSys -> done clearing
fmt_zwrite:
                ld      a,(FMT_SEC)
                ld      e,a
                ld      d,0
                ld      hl,FSECTOR_BUF
                call    write_sector
                ret     c
                ld      a,(FMT_SEC)
                inc     a
                ld      (FMT_SEC),a
                jr      fmt_zloop
                ; --- stamp each FAT copy's head: [media][$FF][$FF] ---
fmt_fatheads:
                call    fmt_zero_buf
                ld      a,GM_MEDIA
                call    fmt_geom_byte
                ld      (FSECTOR_BUF),a
                ld      a,$FF
                ld      (FSECTOR_BUF + 1),a
                ld      (FSECTOR_BUF + 2),a
                ld      a,GM_NUMFATS
                call    fmt_geom_byte
                ld      (FMT_SEC),a         ; reuse FMT_SEC as the FAT-copy counter
                ld      a,GM_FIRSTFAT
                call    fmt_geom_word       ; HL = first FAT-copy sector
fmt_fatlp:
                ld      a,(FMT_SEC)
                or      a
                jr      z,fmt_boot
                push    hl
                ex      de,hl               ; DE = sector
                ld      hl,FSECTOR_BUF
                call    write_sector
                pop     hl
                ret     c
                push    hl                  ; HL = current FAT-copy sector
                ld      a,GM_SECPERFAT
                call    fmt_geom_word       ; HL = secPerFAT
                ex      de,hl               ; DE = secPerFAT
                pop     hl
                add     hl,de               ; next FAT copy
                ld      a,(FMT_SEC)
                dec     a
                ld      (FMT_SEC),a
                jr      fmt_fatlp
                ; --- write the boot sector (BPB) last ---
fmt_boot:
                call    fmt_zero_buf
                ld      hl,(FMT_DESC)
                ld      de,GM_BOOT
                add     hl,de               ; HL = the 32-byte boot template
                ld      de,FSECTOR_BUF
                ld      bc,32
                ldir
                ld      de,0                ; sector 0
                ld      hl,FSECTOR_BUF
                jp      write_sector        ; tail: returns its Cy (ok / error)

; fmt_menu_text — at its ORIGINAL position (do_format's era) between fmt_boot and
; fmt_geom_byte, so the lean cart's inline byte layout stays IDENTICAL to the
; pre-eviction build. Unused sub-side (the menu stays main-resident, spec §2) but
; harmless — sub-ROM space is not tight (playbook §1).
fmt_menu_text:  db      "1=360k 2=720k? ",0

; fmt_geom_byte / fmt_geom_word — read a field at (FMT_DESC)+A. byte -> A; word -> HL.
fmt_geom_byte:
                ld      hl,(FMT_DESC)
                ld      e,a
                ld      d,0
                add     hl,de
                ld      a,(hl)
                ret
fmt_geom_word:
                ld      hl,(FMT_DESC)
                ld      e,a
                ld      d,0
                add     hl,de
                ld      a,(hl)
                inc     hl
                ld      h,(hl)
                ld      l,a
                ret

; fmt_zero_buf — fill FSECTOR_BUF with 512 zero bytes. Clobbers BC, DE, HL.
fmt_zero_buf:
                ld      hl,FSECTOR_BUF
                ld      de,FSECTOR_BUF + 1
                ld      bc,511
                ld      (hl),0
                ldir
                ret

; --- geometry descriptors --------------------------------------------------
; All format geometry lives HERE — adding another is a new descriptor + a menu entry;
; the build/write engine above is geometry-agnostic. Each: [firstFAT:2][numFATs:1]
; [secPerFAT:2][lastSys:2][media:1] then a 32-byte boot template (jump + own OEM +
; BPB +11..27 + hidden). The boot-code region (+36..) stays zero (not copied from any
; ROM). Geometry confirmed field-for-field against black-box CF-3300 formats (720K =
; "2 sides, double track"; 360K = "2 sides").
GEOM_720K:                                  ; 720 KB, media $F9 (1440 sectors, 3 sec/FAT)
                dw      1                   ; GM_FIRSTFAT
                db      2                   ; GM_NUMFATS
                dw      3                   ; GM_SECPERFAT
                dw      13                  ; GM_LASTSYS  : firstRoot(7)+rootSecs(7)-1
                db      $F9                 ; GM_MEDIA
                db      $EB,$FE,$90
                db      "ZEROBAS "
                db      $00,$02,$02,$01,$00,$02,$70,$00,$A0,$05,$F9,$03,$00,$09,$00,$02,$00
                db      $00,$00,$00,$00
GEOM_360K:                                  ; 360 KB, media $FD (720 sectors, 2 sec/FAT)
                dw      1                   ; GM_FIRSTFAT
                db      2                   ; GM_NUMFATS
                dw      2                   ; GM_SECPERFAT
                dw      11                  ; GM_LASTSYS  : firstRoot(5)+rootSecs(7)-1
                db      $FD                 ; GM_MEDIA
                db      $EB,$FE,$90
                db      "ZEROBAS "
                db      $00,$02,$02,$01,$00,$02,$70,$00,$D0,$02,$FD,$02,$00,$09,$00,$02,$00
                db      $00,$00,$00,$00
