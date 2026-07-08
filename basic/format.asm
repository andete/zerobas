; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; format.asm — CALL FORMAT (initialise a blank FAT12 filesystem on the disk).
;
;   CALL FORMAT          (or the abbreviation _FORMAT)
;
; A real MSX CALL FORMAT is interactive: it asks "Drive name? (A,B)" and then offers
; the disk ROM's CHOICE menu of geometries (on the National CF-3300: 1-side / 2-sides
; / ±double-track — 360 KB up to 720 KB). zerobas-disk targets drive A only, so it
; skips the drive prompt, but it DOES prompt a minimal geometry menu: "1=360K 2=720K"
; read via the REPL line editor (do_format, below) — the two supported FAT12 layouts
; (media $F9/720 KB and media $FD/360 KB). Any drive argument typed after the verb is
; parsed-past and ignored.
;
; zerobas-BASIC owns the FAT12 logic and drives the standard $4010 DSKIO read+write
; (basic/fat.asm), so it lays the filesystem down ITSELF — a fresh boot sector (BPB)
; + two FAT copies + an empty root directory via write_sector — without needing
; zerobas-disk's DSKFMT (a stub). This is the Phase-1.5 "BASIC owns the filesystem"
; model applied to formatting.
;
; GEOMETRY IS PARAMETERISED. All geometry lives in descriptor tables (GEOM_720K,
; GEOM_360K); the format logic reads their fields, with no hardcoded constants. The
; menu selection just picks which descriptor to hand the routine — the routine itself
; does not change. A further geometry is a new descriptor + a new menu line.
;
; Clean-room: original code. The CALL token ($CA) is oracle-locked to the VG-8020
; crunch. The BPB *geometry* (512 B/sec, 2 sec/clus, 1 reserved, 2 FATs, 112 root
; entries, 1440 sectors, media $F9, 3 sec/FAT) is the standard 720 KB FAT12 layout
; (Microsoft FAT spec / MSX2 TH), confirmed field-for-field against a black-box
; National CF-3300 "2 sides, double track" format. The boot-CODE region and OEM name
; are zerobas' OWN (not copied from any ROM) — the one documented divergence from a
; byte-identical CF-3300 format. No disassembly. See basic/PROVENANCE.md §CALL FORMAT.

; --- geometry descriptor offsets -------------------------------------------
GM_FIRSTFAT     equ     0       ; word: first FAT sector (= reserved sector count)
GM_NUMFATS      equ     2       ; byte: number of FAT copies
GM_SECPERFAT    equ     3       ; word: sectors per FAT copy
GM_LASTSYS      equ     5       ; word: last system sector to clear (= firstData - 1)
GM_MEDIA        equ     7       ; byte: media descriptor (FAT entry 0)
GM_BOOT         equ     8       ; 32-byte boot-sector template (jump + OEM + BPB + hidden)

; --- ex_call / _<name> — extended-statement dispatch -----------------------
; HL -> the CALL token (ex_call) or the '_' char (ex_call_us). Only CALL FORMAT is
; supported; any other name errors.
ex_call:
                inc     hl                  ; past the CALL token
                jr      exc_name
ex_call_us:
                inc     hl                  ; past '_'
exc_name:
                call    skip_spaces
                call    fmt_match_format    ; CF set if (HL) == "FORMAT"
                jp      nc,stmt_error       ; unsupported CALL extension
                ; skip an optional drive argument, e.g. ("A:"), to the statement end.
exc_skip:
                ld      a,(hl)
                or      a
                jr      z,exc_go
                cp      COLON
                jr      z,exc_go
                inc     hl
                jr      exc_skip
exc_go:
                push    hl                  ; save the statement-end cursor (CALSLT clobbers)
                call    do_format
                pop     hl
                jp      c,load_error        ; format I/O error
                jp      exec_stmt

; fmt_match_format — CF set iff the 6 chars at (HL) are "FORMAT" (case-insensitive);
; HL is advanced past them on a match. Clobbers A, B, DE, HL.
fmt_match_format:
                ld      de,fmt_name
                ld      b,6
fmf_lp:
                ld      a,(de)
                ld      c,a
                ld      a,(hl)
                call    upcase
                cp      c
                jr      nz,fmf_no
                inc     hl
                inc     de
                djnz    fmf_lp
                scf                         ; matched
                ret
fmf_no:
                or      a                   ; CF clear -> no match
                ret
fmt_name:       db      "FORMAT"


; --- do_format — interactively pick a geometry, then write a fresh filesystem ----
;   out: Cy = 0 ok; Cy = 1 = no disk / write error.
; A real CALL FORMAT lets you choose the disk geometry; with two geometries there now
; IS something to choose, so zerobas prompts a minimal 1=360K / 2=720K menu (its own —
; zerobas-disk's CHOICE offers none) and reads the answer via the REPL line editor. The
; chosen descriptor's base goes in FMT_DESC; the rest reads its fields through that
; pointer, so the logic is geometry-agnostic. Buffer: FSECTOR_BUF is the 512-byte write
; source (write_sector reads, never writes it, so one zero-fill is reused). Order: clear
; the FAT + root region, stamp each FAT's head (media + two $FF), write the boot sector.
do_format:
                ld      a,(DISKSLOT_OK)
                or      a
                jr      nz,fmt_menu
                scf                         ; no disk -> error
                ret
fmt_menu:
                ld      hl,fmt_menu_text
                call    print_string
                call    read_line           ; LINEBUF <- the typed choice (echoed)
                ld      a,(LINEBUF)
                cp      '1'
                jr      z,fmt_sel_360
                cp      '2'
                jr      z,fmt_sel_720
                jr      fmt_menu            ; invalid -> re-prompt (like the CF-3300 '?')
fmt_sel_360:
                ld      hl,GEOM_360K
                jr      fmt_selected
fmt_sel_720:
                ld      hl,GEOM_720K
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
; do_format is geometry-agnostic. Each: [firstFAT:2][numFATs:1][secPerFAT:2][lastSys:2]
; [media:1] then a 32-byte boot template (jump + own OEM + BPB +11..27 + hidden). The
; boot-code region (+36..) stays zero (not copied from any ROM). Geometry confirmed
; field-for-field against black-box CF-3300 formats (720K = "2 sides, double track";
; 360K = "2 sides").
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
