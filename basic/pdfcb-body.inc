; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; pdfcb-body.inc — parse_disk_fcb, the disk drive-letter + 8.3-name parser.
; ===========================================================================
; Split out of bload-body.inc because it has NINE external callers (do_files,
; do_kill, do_name, do_open, do_run, ex_merge, bsv_is_disk, sav_is_disk,
; dl_is_disk) and so must stay RESIDENT in the repack build even though the
; BLOAD verb around it moves to a sub-ROM tenant (docs/spec-traps-t3-key.md §7.6).
; Included from THREE places, byte-identically:
;   * bload-body.inc, at its original position -- keeps the lean 16 KB cart
;     byte-identical;
;   * basic/bload.asm's repack branch -- the resident copy those nine keep calling;
;   * transitively into sub/bload.asm (via bload-body.inc) -- the tenant's copy.
; The resident and tenant copies differ only in what `build_83_name` binds to:
; the marshalling shim resident, the real sub-local body in the tenant.
; ===========================================================================

; parse_disk_fcb — parse a disk filename into the scratch FCB at DISK_FCB.
; Shared by BOTH do_bload's disk path (is_disk) and do_load's disk path so the
; drive-letter + 8.3-name logic lives in one place.
;   in:  HL -> first char of the quoted name (the byte after the opening '"'),
;             possibly an "A:"/"B:" drive prefix.
;   out: DISK_FCB_DRV = drive code (1=A, 2=B; default A when no prefix);
;        DISK_FCB_NAME = the 11-byte space-padded upper-case 8.3 field;
;        HL -> the closing '"' (so parse_close_run resumes there).
; On a malformed drive spec or a name that doesn't fit 8.3, jumps to bl_load_error
; (does not return). Clobbers A, B, C, DE, HL.
parse_disk_fcb:
                ; --- detect an optional drive letter "X:" -------------------
                ; "A:" / "B:" (case-insensitive). Default drive = A when absent.
                ; Look at name[0] and name[1]: a letter followed by ':' is a
                ; drive spec; anything else is a bare filename on drive A.
                ld      a,1                 ; default drive code = A
                ld      (DISK_FCB_DRV),a
                ld      a,(hl)
                call    bl_upcase
                ld      c,a                 ; C = candidate drive letter (upper)
                inc     hl
                ld      a,(hl)              ; second char
                cp      ':'
                jr      nz,no_drive         ; not "X:" -> bare name, drive A
                ; second char is ':' -> first char must be A or B
                ld      a,c
                cp      'A'
                jr      z,drive_a
                cp      'B'
                jr      z,drive_b
                jp      bl_load_error          ; "X:" with X not A/B -> reject
drive_a:
                ld      a,1
                jr      set_drive
drive_b:
                ld      a,2
set_drive:
                ld      (DISK_FCB_DRV),a
                inc     hl                  ; HL -> char after the ':'
                jr      build_name
no_drive:
                dec     hl                  ; undo the second-char peek; HL = name[0]
build_name:
                ; HL -> first char of the bare filename (after any "X:").
                ; --- convert to the 11-byte 8.3 field at DISK_FCB_NAME ------
                call    build_83_name       ; HL advanced to the closing quote
                jp      c,bl_load_error        ; name didn't fit 8.3 / malformed
                ret
