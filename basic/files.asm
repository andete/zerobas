; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause

; files.asm — Disk BASIC file-channel verbs (Phase 2), built by EXTEND over the
; existing basic/fat.asm engine (file-channel-protocol.md §4/§5: the file verbs
; move bytes through the SAME standard DSKIO+FAT12 substrate as the loader, so
; they are layered on fat.asm, not delegated to the in-slot Disk BASIC).
;
; First verb: FILES — list the root-directory file names.
;
;   FILES                 list every file in the root directory
;
; Output format (oracle-pinned, black-box, real National CF-3300 Disk BASIC v1.0,
; diskbasic_probe_files.py): each entry renders as the 8.3 name in a fixed 12-char
; field — 8-char name (space-padded) + '.' + 3-char extension (space-padded) —
; entries separated by a single space and wrapped to as many fields as fit the
; active text width, in raw directory order. Deleted ($E5) and volume/sub-dir
; entries are skipped; the listing stops at the first free ($00) directory slot.
; The wrap is driven by the live cursor column (CSRX) against the active width
; (LINLEN) — the faithful MSX algorithm — so it reproduces CF-3300's 2-per-line at
; WIDTH 29 and scales to any width.
;
; Divergences (own design, documented in basic/PROVENANCE.md §FILES):
;   * an optional <filespec> pattern argument is parsed-past and IGNORED — FILES
;     always lists the whole directory (pattern matching is a later Phase-2 item);
;   * the disk-name / "Ok" framing is the REPL's, not emitted here.
;
; Clean-room: original code. FILES *semantics* (list the directory) + the 8.3
; field layout from the MSX-BASIC language reference and black-box CF-3300
; observation; the FAT12 directory walk reuses fat.asm primitives (read_sector +
; the on-disk directory-entry layout, Microsoft FAT spec). No disassembly.
; See file-channel-protocol.md and basic/PROVENANCE.md §FILES.

; ex_files — statement trampoline (entered from exec_stmt with HL on the token).
ex_files:
                inc     hl                  ; HL -> bytes after the FILES token
                jp      do_files

; do_files — list the root directory, then continue the statement loop.
; Entry: HL -> the bytes after the FILES token (an optional, ignored filespec).
do_files:
                ; (1) a disk-ROM slot must have been recorded by the INIT scan.
                ld      a,(DISKSLOT_OK)
                or      a
                jp      z,load_error
                push    hl                  ; save the BASIC text cursor across listing
                ; (2) mount the volume (BPB geometry into the fat.asm scratch).
                call    fat_mount
                jr      c,df_io_pop
                ; (3) walk the root directory: FAT_DIRSEC/FAT_DIRREM track position.
                ld      hl,(FAT_FIRSTROOT)
                ld      (FAT_DIRSEC),hl
                ld      hl,(FAT_ROOTSECS)
                ld      (FAT_DIRREM),hl
df_secloop:
                ld      hl,(FAT_DIRREM)
                ld      a,h
                or      l
                jr      z,df_end            ; scanned every root sector
                ld      de,(FAT_DIRSEC)
                ld      hl,FSECTOR_BUF
                call    read_sector
                jr      c,df_io_pop         ; FDC / DSKIO error
                xor     a
                ld      (FILES_ENTIDX),a    ; entry 0..15 within this sector
df_entloop:
                call    df_entptr           ; HL -> current 32-byte dir entry
                ld      a,(hl)
                or      a
                jr      z,df_end            ; $00 = first free slot -> end of dir
                cp      $E5
                jr      z,df_nextent        ; deleted entry
                push    hl
                ld      de,11
                add     hl,de
                ld      a,(hl)              ; attribute byte (+11)
                pop     hl
                and     $18                 ; volume-label | sub-directory -> skip
                jr      nz,df_nextent
                call    df_emit             ; print this entry's 8.3 name field
df_nextent:
                ld      a,(FILES_ENTIDX)
                inc     a
                ld      (FILES_ENTIDX),a
                cp      16                  ; 512 / 32 entries per sector
                jr      c,df_entloop
                ld      hl,(FAT_DIRSEC)     ; advance to the next root-dir sector
                inc     hl
                ld      (FAT_DIRSEC),hl
                ld      hl,(FAT_DIRREM)
                dec     hl
                ld      (FAT_DIRREM),hl
                jr      df_secloop
df_end:
                ; terminate the final line if we stopped mid-line (CSRX != column 1).
                ld      a,(CSRX)
                dec     a
                jr      z,df_endline
                call    print_crlf
df_endline:
                pop     hl                  ; restore the BASIC text cursor
                ; skip the optional (ignored) filespec to ':' or end of line.
df_skip:
                ld      a,(hl)
                or      a
                jp      z,exec_stmt         ; EOL -> exec_stmt returns to the REPL
                cp      COLON
                jp      z,exec_stmt
                inc     hl
                jr      df_skip
df_io_pop:
                pop     hl                  ; balance the saved text cursor
                jp      load_error

; df_entptr — HL = FSECTOR_BUF + FILES_ENTIDX*32 (the current dir entry).
; Recomputed from RAM each time so CHPUT's register clobber is harmless.
df_entptr:
                ld      a,(FILES_ENTIDX)
                ld      l,a
                ld      h,0
                add     hl,hl               ; *2
                add     hl,hl               ; *4
                add     hl,hl               ; *8
                add     hl,hl               ; *16
                add     hl,hl               ; *32
                ld      de,FSECTOR_BUF
                add     hl,de
                ret

; df_emit — print one directory entry's 8.3 name field, handling the separator /
; line wrap. HL -> the 32-byte directory entry (name at +0..10). Clobbers regs;
; the entry index lives in RAM so the caller re-derives the pointer.
df_emit:
                ; separator / wrap decision from the live cursor column.
                ld      a,(CSRX)
                dec     a                   ; 0-based column (0 = line start)
                or      a
                jr      z,de_field          ; first field on the line -> no separator
                ; not at line start: does " " + a 12-char field still fit?
                ld      b,a                 ; B = current 0-based column
                ld      a,(LINLEN)
                sub     b                   ; A = columns left on this line
                cp      13                  ; need 1 (space) + 12 (field)
                jr      nc,de_sep           ; room -> print the separating space
                call    print_crlf          ; no room -> wrap to a new line
                jr      de_field
de_sep:
                push    hl
                ld      a,' '
                call    CHPUT
                pop     hl
de_field:
                ; 8 name chars (raw, already upper-case + space-padded on disk)
                ld      b,8
de_name:
                ld      a,(hl)
                push    hl
                push    bc
                call    CHPUT
                pop     bc
                pop     hl
                inc     hl
                djnz    de_name
                push    hl                  ; '.' separator between name and ext
                ld      a,'.'
                call    CHPUT
                pop     hl
                ld      b,3                 ; 3 extension chars
de_ext:
                ld      a,(hl)
                push    hl
                push    bc
                call    CHPUT
                pop     bc
                pop     hl
                inc     hl
                djnz    de_ext
                ret
