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

; ===========================================================================
; Sequential file channel (Phase 2). A SINGLE open channel, layered on the
; existing fat.asm sequential engine (fat_io_open/getbyte + fat_io_create/putbyte/
; close), per the EXTEND verdict (file-channel-protocol.md §4/§5). Verbs:
;   OPEN "name" FOR INPUT  AS #n       open the named file for sequential read
;   OPEN "name" FOR OUTPUT AS #n       create/truncate the file for sequential write
;   LINE INPUT #n, A$                  read one line (to CR) into a string var
;   INPUT #n, A$                       read one field (to ',' or CR) into A$
;   PRINT #n, <items>                  write PRINT-formatted items to the file
;   CLOSE [#n]                          close the open channel (OUTPUT: flush + EOF)
; The channel state (FCH_NUM/FCH_MODE) persists across statements in RAM. PRINT#
; reuses the screen PRINT item loop, redirected byte-by-byte to the channel via
; the PRDEST flag + the `pchar` sink (basic/print.asm).
;
; Clean-room: original code; verb *semantics* + the FCB-by-name / sequential
; read+write model from the public MSX-BASIC language reference and the black-box
; CF-3300 DSKIO trace (file-channel-protocol.md §2/§3); the byte stream reuses
; fat.asm. No disassembly. See basic/PROVENANCE.md §file channel.
;
; Divergences (own design, quarantined; documented in PROVENANCE.md):
;   * ONE channel only — a MAXFILES channel table is a later sub-item; the
;     file number is recorded but not range-checked against a table.
;   * INPUT#/LINE INPUT# fill STRING variables only (numeric INPUT# is Phase 3);
;     a value longer than STRMAX is truncated (the string layer's own limit).
;   * console INPUT (no '#') and graphics LINE are NOT implemented — they error.
;   * OPEN handles FOR INPUT and FOR OUTPUT; APPEND is a later item.
;   * file/channel errors reuse the loader's `load_error` ("load error") path.

; --- OPEN "name" FOR INPUT AS #n -------------------------------------------
ex_open:
                inc     hl                  ; HL -> bytes after the OPEN token
                jp      do_open
do_open:
                call    skip_spaces
                ld      a,(hl)
                cp      '"'
                jp      nz,stmt_error       ; filename string required
                inc     hl                  ; HL -> first filename char
                call    parse_disk_fcb      ; build DISK_FCB_NAME; HL -> closing '"'
                inc     hl                  ; past the closing '"'
                call    skip_spaces
                ld      a,(hl)
                cp      FOR_TOKEN           ; FOR
                jp      nz,stmt_error
                inc     hl
                ; mode keyword: INPUT ($85), or OUTPUT = OUT ($9C) + PUT ($B3)
                ; (OUTPUT is two reserved words, not one keyword — oracle-observed).
                call    skip_spaces
                ld      a,(hl)
                cp      INPUT_TOKEN
                jr      z,oo_input
                cp      OUT_TOKEN
                jp      nz,stmt_error
                inc     hl
                ld      a,(hl)
                cp      PUT_TOKEN
                jp      nz,stmt_error
                inc     hl
                ld      a,2                 ; mode = OUTPUT
                jr      oo_setmode
oo_input:
                inc     hl
                ld      a,1                 ; mode = INPUT
oo_setmode:
                ld      (FCH_MODE),a        ; provisional; cleared on any failure
                ; "AS" is kept verbatim ASCII (not tokenised) — match it.
                call    skip_spaces
                ld      a,(hl)
                call    upcase
                cp      'A'
                jp      nz,oo_fail_syn
                inc     hl
                ld      a,(hl)
                call    upcase
                cp      'S'
                jp      nz,oo_fail_syn
                inc     hl
                call    skip_spaces
                ld      a,(hl)              ; optional '#'
                cp      '#'
                jr      nz,oo_num
                inc     hl
oo_num:
                call    eval                ; DE = channel number, HL past it
                ld      a,(DISKSLOT_OK)
                or      a
                jr      z,oo_fail
                push    hl                  ; guard the text cursor — CALSLT (inside
                push    de                  ; fat_io_open/create) clobbers HL + regs
                ld      a,(FCH_MODE)
                cp      2
                jr      z,oo_create
                call    fat_io_open         ; INPUT: mount + find + prime read
                jr      oo_done
oo_create:
                call    fat_io_create       ; OUTPUT: make/truncate + prime write
oo_done:
                pop     de
                pop     hl
                jr      c,oo_fail           ; not found / dir-full / mount / I-O error
                ld      a,e
                ld      (FCH_NUM),a         ; record the open channel
                jp      exec_stmt
oo_fail:
                xor     a
                ld      (FCH_MODE),a        ; not actually open
                jp      load_error
oo_fail_syn:
                xor     a
                ld      (FCH_MODE),a
                jp      stmt_error

; --- LINE INPUT #n, A$  (only the "LINE INPUT" form of LINE is supported) ---
ex_line:
                inc     hl                  ; HL -> bytes after the LINE token
                call    skip_spaces
                ld      a,(hl)
                cp      INPUT_TOKEN         ; LINE must be followed by INPUT
                jp      nz,stmt_error       ; graphics LINE = Phase 3
                inc     hl                  ; HL -> after INPUT
                ld      a,1                 ; read mode = LINE (stop at CR only)
                jr      input_common

; --- INPUT #n, A$  (file form only) ----------------------------------------
ex_input:
                inc     hl                  ; HL -> bytes after the INPUT token
                xor     a                   ; read mode = field (stop at ',' or CR)
input_common:
                ld      (FCH_RDMODE),a
                call    skip_spaces
                ld      a,(hl)
                cp      '#'                 ; only the file form (#n) is supported
                jp      nz,stmt_error       ; console INPUT = Phase 3
                inc     hl
                call    eval                ; DE = channel number (single channel)
                ld      a,(FCH_MODE)
                cp      1                   ; a channel must be open for INPUT
                jp      nz,load_error
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jp      nz,stmt_error
                inc     hl
                call    skip_spaces
                call    is_letter           ; a string variable name must follow
                jp      nc,stmt_error
                call    var_str_type        ; A = 1 if the name has a '$' suffix
                or      a
                jp      z,stmt_error        ; numeric INPUT# = Phase 3
                call    var_name_key        ; BC = key, HL past the name + '$'
                push    hl                  ; guard the BASIC text cursor
                push    bc                  ; guard the variable key across the read
                call    read_into_strscr    ; fill STRSCR [len][bytes] from the file
                pop     bc
                ld      de,STRSCR
                call    str_set_key         ; store the line into the string variable
                pop     hl
                jp      exec_stmt

; read_into_strscr — read bytes from the open channel into the STRSCR descriptor
; ([len][bytes]) until the mode's delimiter or EOF. FCH_RDMODE: 0 = field (stop at
; ',' or CR), 1 = line (stop at CR). LF bytes are ignored; CR ends the read. A byte
; past STRMAX is dropped (input keeps consuming to the delimiter). All loop state
; is in RAM — fat_io_getbyte's DSKIO clobbers every register.
read_into_strscr:
                xor     a
                ld      (IN_RDLEN),a
ris_lp:
                call    fat_io_getbyte
                jr      c,ris_done          ; EOF -> stop
                cp      $0A                 ; ignore LF entirely
                jr      z,ris_lp
                cp      $0D                 ; CR ends the line / field
                jr      z,ris_done
                ld      c,a                 ; C = candidate data byte
                ld      a,(FCH_RDMODE)
                or      a
                jr      nz,ris_keep         ; line mode keeps everything (but CR/LF)
                ld      a,c
                cp      ','                 ; field mode stops at a comma
                jr      z,ris_done
ris_keep:
                ld      a,(IN_RDLEN)
                cp      STRMAX
                jr      nc,ris_lp           ; full -> drop, keep consuming to delim
                ld      e,a
                ld      d,0
                ld      hl,STRSCR+1
                add     hl,de               ; HL -> STRSCR+1+len
                ld      (hl),c              ; store the byte
                ld      a,(IN_RDLEN)
                inc     a
                ld      (IN_RDLEN),a
                jr      ris_lp
ris_done:
                ld      a,(IN_RDLEN)
                ld      (STRSCR),a          ; descriptor length
                ret

; --- CLOSE [#n] -------------------------------------------------------------
ex_close:
                inc     hl                  ; HL -> bytes after the CLOSE token
                call    skip_spaces
                ld      a,(hl)
                or      a
                jr      z,dc_doclose        ; bare CLOSE (end of line)
                cp      COLON
                jr      z,dc_doclose        ; bare CLOSE before ':'
                cp      '#'
                jr      nz,dc_num
                inc     hl
dc_num:
                call    eval                ; consume + ignore the channel number
dc_doclose:
                ; OUTPUT flushes the buffered tail + stamps the directory entry
                ; (fat_io_close); INPUT has no dirty state.
                ld      a,(FCH_MODE)
                cp      2
                jr      nz,dc_clear
                push    hl                  ; guard text cursor across CALSLT
                ld      a,$1A               ; append the CP/M text-EOF marker (Ctrl-Z)
                call    fat_io_putbyte      ; — MSX Disk BASIC stamps it on CLOSE of a
                                            ; sequential OUTPUT file (CF-3300-confirmed)
                call    fat_io_close        ; flush data sector + dir size/cluster
                pop     hl                  ; CY (write error) is best-effort-ignored
dc_clear:
                xor     a
                ld      (FCH_NUM),a
                ld      (FCH_MODE),a         ; mark the channel closed
                jp      exec_stmt

; init_filechan — cold-start the file-channel state: no channel open, PRINT to
; screen. Called from `init` before the banner is printed.
init_filechan:
                xor     a
                ld      (FCH_NUM),a
                ld      (FCH_MODE),a
                ld      (PRDEST),a
                ret

; --- KILL "name" — delete a file -------------------------------------------
; Frees the file's FAT cluster chain and marks its directory entry deleted, via
; the fat.asm `fat_delete` engine routine. Accepts the same "A:"/"B:" drive prefix
; + 8.3 name as the loader verbs (parse_disk_fcb). Errors (no disk / not found /
; I-O) reuse the loader's load_error path. Divergence: no wildcard `KILL "*.BAK"`
; (single file only) — a later item. See basic/PROVENANCE.md §KILL.
ex_kill:
                inc     hl                  ; HL -> bytes after the KILL token
                jp      do_kill
do_kill:
                call    skip_spaces
                ld      a,(hl)
                cp      '"'
                jp      nz,stmt_error       ; filename string required
                inc     hl                  ; HL -> first filename char
                call    parse_disk_fcb      ; build DISK_FCB_NAME; HL -> closing '"'
                inc     hl                  ; past the closing '"'
                ld      a,(DISKSLOT_OK)
                or      a
                jp      z,load_error
                push    hl                  ; guard text cursor across CALSLT
                call    fat_delete          ; free chain + mark dir entry deleted
                pop     hl
                jp      c,load_error        ; not found / I-O error
                jp      exec_stmt

; --- NAME "old" AS "new" — rename a file -----------------------------------
; Locate the OLD file, then overwrite its directory entry's 11-byte 8.3 name field
; with the NEW name (no FAT change — same clusters). Both names use the shared
; parse_disk_fcb (drive prefix + 8.3); "AS" is verbatim ASCII. The OLD file is
; found FIRST (recording its location in FWR_DIRSEC/FWR_DIROFF) because building
; the NEW name reuses DISK_FCB_NAME. Errors (no disk / old not found / I-O) reuse
; load_error. Divergences: no "new already exists" check (own design); single
; drive (the drive prefix on either name is accepted + ignored for the stamp).
; See basic/PROVENANCE.md §NAME.
ex_name:
                inc     hl                  ; HL -> bytes after the NAME token
                jp      do_name
do_name:
                call    skip_spaces
                ld      a,(hl)
                cp      '"'
                jp      nz,stmt_error       ; old filename string required
                inc     hl                  ; HL -> first char of the old name
                call    parse_disk_fcb      ; old -> DISK_FCB_NAME; HL -> closing '"'
                inc     hl                  ; past the closing '"'
                ; "AS" (verbatim ASCII)
                call    skip_spaces
                ld      a,(hl)
                call    upcase
                cp      'A'
                jp      nz,stmt_error
                inc     hl
                ld      a,(hl)
                call    upcase
                cp      'S'
                jp      nz,stmt_error
                inc     hl
                call    skip_spaces
                ld      a,(hl)
                cp      '"'
                jp      nz,stmt_error       ; new filename string required
                ld      a,(DISKSLOT_OK)
                or      a
                jp      z,load_error
                ; find the OLD file first (records FWR_DIRSEC/FWR_DIROFF); HL still
                ; points at the new name's opening '"', so guard it across CALSLT.
                push    hl
                call    fat_mount
                jr      c,nm_fail
                ld      hl,DISK_FCB_NAME
                call    fat_find            ; old located; sets the entry location
                jr      c,nm_fail           ; old not found
                pop     hl                  ; HL -> new name's '"'
                inc     hl                  ; -> first char of the new name
                call    parse_disk_fcb      ; new -> DISK_FCB_NAME; HL -> closing '"'
                inc     hl
                ; read the dir sector, overwrite the 11-byte name, write it back.
                push    hl                  ; guard text cursor across CALSLT
                ld      de,(FWR_DIRSEC)
                ld      hl,FSECTOR_BUF
                call    read_sector
                jr      c,nm_fail2
                ld      hl,FSECTOR_BUF
                ld      de,(FWR_DIROFF)
                add     hl,de               ; HL -> the entry in the buffer
                ex      de,hl               ; DE -> dest name field
                ld      hl,DISK_FCB_NAME    ; source = the new 8.3 name
                ld      bc,11
                ldir                        ; overwrite the 11-byte 8.3 name
                ld      de,(FWR_DIRSEC)
                ld      hl,FSECTOR_BUF
                call    write_sector
                jr      c,nm_fail2
                pop     hl                  ; restore text cursor
                jp      exec_stmt
nm_fail:
                pop     hl                  ; balance the guarded cursor
                jp      load_error
nm_fail2:
                pop     hl                  ; balance the second guarded cursor
                jp      load_error
