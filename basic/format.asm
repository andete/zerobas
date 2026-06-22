; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause

; format.asm — CALL FORMAT (initialise a blank FAT12 filesystem on the disk).
;
;   CALL FORMAT          (or the abbreviation _FORMAT)
;
; A real MSX CALL FORMAT is interactive: it asks "Drive name? (A,B)" and then offers
; the disk ROM's CHOICE menu of geometries (on the National CF-3300: 1-side / 2-sides
; / ±double-track — 360 KB up to 720 KB). zerobas-disk supports a SINGLE geometry
; (720 KB, media $F9) and its CHOICE entry returns "no choices", so there is nothing
; to ask: CALL FORMAT formats drive A as 720 KB with no prompts (the deliberately
; minimal, non-interactive form).
;
; zerobas-BASIC owns the FAT12 logic and drives the standard $4010 DSKIO read+write
; (basic/fat.asm), so it lays the filesystem down ITSELF — a fresh boot sector (BPB)
; + two FAT copies + an empty root directory via write_sector — without needing
; zerobas-disk's DSKFMT (a stub). This is the Phase-1.5 "BASIC owns the filesystem"
; model applied to formatting.
;
; GEOMETRY IS PARAMETERISED. All geometry lives in a descriptor table (GEOM_720K); the
; format logic reads its fields, with no hardcoded constants. Adding 360 KB (the
; CF-3300's media $FD / 720-sector / 2-sec-per-FAT variant) later is a new descriptor
; + wiring the CHOICE prompt back in — the routine itself does not change.
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

; --- do_format — write a fresh empty filesystem for the GEOM_720K geometry --
;   out: Cy = 0 ok; Cy = 1 = no disk / write error.
; Buffer: FSECTOR_BUF is the 512-byte write source. write_sector reads (never writes)
; it, so a single zero-fill is reused across all the cleared sectors. Order: clear the
; FAT + root region, stamp each FAT's head (media + two $FF), then write the boot
; sector last.
do_format:
                ld      a,(DISKSLOT_OK)
                or      a
                jr      nz,fmt_have_disk
                scf                         ; no disk -> error
                ret
fmt_have_disk:
                ; --- clear sectors firstFAT..lastSys (FATs + root dir) ---
                call    fmt_zero_buf        ; FSECTOR_BUF = 512 zeros
                ld      a,(GEOM_720K + GM_FIRSTFAT)
                ld      (FMT_SEC),a         ; start at the first FAT sector (low byte; < 256)
fmt_zloop:
                ld      a,(FMT_SEC)
                ld      hl,(GEOM_720K + GM_LASTSYS)
                cp      l
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
                ld      a,(GEOM_720K + GM_MEDIA)
                ld      (FSECTOR_BUF),a
                ld      a,$FF
                ld      (FSECTOR_BUF + 1),a
                ld      (FSECTOR_BUF + 2),a
                ld      a,(GEOM_720K + GM_NUMFATS)
                ld      (FMT_SEC),a         ; reuse FMT_SEC as the FAT-copy counter
                ld      hl,(GEOM_720K + GM_FIRSTFAT)    ; HL = current FAT-copy sector
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
                ld      de,(GEOM_720K + GM_SECPERFAT)
                add     hl,de               ; next FAT copy
                ld      a,(FMT_SEC)
                dec     a
                ld      (FMT_SEC),a
                jr      fmt_fatlp
                ; --- write the boot sector (BPB) last ---
fmt_boot:
                call    fmt_zero_buf
                ld      hl,GEOM_720K + GM_BOOT
                ld      de,FSECTOR_BUF
                ld      bc,32               ; jump + OEM + BPB + hidden
                ldir
                ld      de,0                ; sector 0
                ld      hl,FSECTOR_BUF
                jp      write_sector        ; tail: returns its Cy (ok / error)

; fmt_zero_buf — fill FSECTOR_BUF with 512 zero bytes. Clobbers BC, DE, HL.
fmt_zero_buf:
                ld      hl,FSECTOR_BUF
                ld      de,FSECTOR_BUF + 1
                ld      bc,511
                ld      (hl),0
                ldir
                ret

; --- 720 KB geometry descriptor (media $F9; the only geometry today) --------
; All format geometry is HERE — adding 360 KB is a sibling GEOM_360K table (media
; $FD, 720 total sectors, 2 sec/FAT) plus the CHOICE prompt, with do_format unchanged.
GEOM_720K:
                dw      1                   ; GM_FIRSTFAT  : reserved sectors
                db      2                   ; GM_NUMFATS
                dw      3                   ; GM_SECPERFAT
                dw      13                  ; GM_LASTSYS   : firstRoot(7)+rootSecs(7)-1
                db      $F9                 ; GM_MEDIA
                ; GM_BOOT: 32-byte boot template (jump, OEM, BPB +11..27, hidden +28..31).
                ; OEM is zerobas' own; boot-code region (+36..) stays zero (not copied).
                db      $EB,$FE,$90
                db      "ZEROBAS "
                db      $00,$02,$02,$01,$00,$02,$70,$00,$A0,$05,$F9,$03,$00,$09,$00,$02,$00
                db      $00,$00,$00,$00
