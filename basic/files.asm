; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

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

; do_files — list the root directory (optionally filtered by an 8.3 wildcard
; filespec), then continue the statement loop.
; Entry: HL -> the bytes after the FILES token. FILES ["[drive:]pattern"] — the
; pattern uses 8.3 '*' and '?' wildcards; bare FILES lists everything.
do_files:
                ; (1) a disk-ROM slot must have been recorded by the INIT scan.
                ld      a,(DISKSLOT_OK)
                or      a
                jp      z,load_error
                ; (1b) parse the optional "filespec" into a match pattern (with
                ; '*'->'?' expansion via build_83_name); FILES_HASPAT flags its
                ; presence. The text cursor is advanced PAST the filespec here, so
                ; the saved cursor below already points at the statement's tail.
                call    skip_spaces
                xor     a
                ld      (FILES_HASPAT),a
                ld      a,(hl)
                cp      '"'
                jr      nz,df_nofilespec
                inc     hl                  ; past the opening quote
                call    parse_disk_fcb      ; DISK_FCB_NAME = 8.3 wildcard pattern
                inc     hl                  ; past the closing quote
                ld      a,1
                ld      (FILES_HASPAT),a
df_nofilespec:
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
                ; filespec filter: match the entry name (HL) against the pattern
                ; (DISK_FCB_NAME) with '?'/'*' wildcards; skip non-matches.
                ld      a,(FILES_HASPAT)
                or      a
                jr      z,df_do_emit        ; bare FILES -> list everything
                push    hl                  ; name_cmp advances HL by 11 -> guard it
                ld      de,DISK_FCB_NAME
                call    name_cmp            ; DE=pattern, HL=entry; Z=match
                pop     hl                  ; restore entry ptr (flags preserved)
                jr      nz,df_nextent       ; no match -> skip
df_do_emit:
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
                pop     hl                  ; restore the BASIC text cursor (already
                jp      exec_stmt           ; past the filespec, consumed at df head)
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
;   * up to FCH_CEIL (=2) channels open at once — a real multi-channel table
;     (MAXFILES) over fat.asm's single global state, via the write-back context
;     cache in the channel-manager section below. The ceiling is RAM-bounded
;     (real MSX MAXFILES reaches 15); channel numbers are range-checked to MAXF.
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
                ; --- device-name dispatch: "LPT:"/"CRT:" -> character-device
                ; channel (no disk file); anything else -> disk filename. Peeked
                ; case-insensitively; HL is restored on a miss (dev_cmp). CAS:/GRP:/
                ; COM: OPEN are not in this tier (an unknown xxx: stays a disk name).
                ld      de,dev_lpt
                call    dev_cmp
                jp      z,oo_dev_lpt
                ld      de,dev_crt
                call    dev_cmp
                jp      z,oo_dev_crt
                ld      de,dev_cas
                call    dev_cmp
                jp      z,oo_dev_cas
                call    parse_disk_fcb      ; build DISK_FCB_NAME; HL -> closing '"'
                inc     hl                  ; past the closing '"'
                call    skip_spaces
                ld      a,(hl)
                cp      FOR_TOKEN           ; FOR
                jp      nz,oo_random        ; no FOR clause -> RANDOM mode (OPEN..AS #n)
                inc     hl
                ; mode keyword: INPUT ($85); OUTPUT = OUT ($9C) + PUT ($B3); or
                ; APPEND = "APP" (verbatim ASCII $41 $50 $50) + END ($81) — none of
                ; these are single keywords: OUTPUT is two reserved words, and
                ; "APPEND" is not a reserved word at all, so the main-ROM tokeniser
                ; crunches it as the name "APP" followed by the END token (oracle:
                ; VG-8020 + zerobas both emit $41 $50 $50 $81 — already byte-identical).
                call    skip_spaces
                ld      a,(hl)
                cp      INPUT_TOKEN
                jr      z,oo_input
                cp      OUT_TOKEN
                jr      z,oo_output
                ; APPEND? match the literal "APP" + END-token sequence.
                cp      'A'
                jp      nz,stmt_error
                inc     hl
                ld      a,(hl)
                cp      'P'
                jp      nz,stmt_error
                inc     hl
                ld      a,(hl)
                cp      'P'
                jp      nz,stmt_error
                inc     hl
                ld      a,(hl)
                cp      END_TOKEN           ; the "END" half of app-END
                jp      nz,stmt_error
                inc     hl
                ld      a,3                 ; mode = APPEND (provisional open action)
                jr      oo_setmode
oo_output:
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
                jr      oo_setmode
oo_random:
                ld      a,4                 ; mode = RANDOM (no FOR clause)
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
                ; validate the channel against the MAXFILES ceiling (1..MAXF).
                ld      a,d
                or      a
                jp      nz,oo_fail_syn      ; > 255 -> bad file number
                ld      a,e
                call    fch_valid
                jp      nc,oo_fail_syn      ; 0 or > MAXF -> bad file number
                ; --- optional "LEN=r" record-size clause (Phase 2c; disk-BASIC
                ; option-closure Item 3). Parsed for every mode; only RANDOM GET/PUT
                ; reads it. A channel without LEN= defaults to 256. r must be a power
                ; of two in 1..256 so records tile the 512-byte sector without
                ; straddling (the sector-tiling scope; non-tiling sizes -> Syntax
                ; error). Stored per channel in FCH_RECLENS[ch].
                ld      a,e
                ld      (OO_RECLEN_CHAN),a  ; stash channel across the LEN= eval
                call    oo_parse_reclen     ; DE = reclen (default 256); HL past; Cy=1 bad
                jp      c,oo_fail_syn       ; non-tiling / out-of-range record size
                push    hl                  ; GUARD the text cursor -- the store below
                                            ; uses HL as scratch (a bug once: the lost
                                            ; cursor abandoned a same-line ':' tail)
                ld      a,(OO_RECLEN_CHAN)
                add     a,a                 ; channel * 2 (word index)
                ld      l,a
                ld      h,0
                ld      bc,FCH_RECLENS
                add     hl,bc
                ld      (hl),e
                inc     hl
                ld      (hl),d              ; FCH_RECLENS[ch] = reclen
                pop     hl                  ; restore the text cursor
                ld      a,(OO_RECLEN_CHAN)
                ld      e,a
                ld      d,0                 ; restore DE = channel for the rest of do_open
                ld      a,(DISKSLOT_OK)
                or      a
                jr      z,oo_nodisk         ; no disk -> fail BEFORE claiming a slot
                ; claim the channel's slot (saving any OTHER active channel) so the
                ; engine globals belong to this channel before fat_io_* fills them.
                push    de
                ld      a,e
                call    fch_claim           ; FCH_ACTIVE = e (no stale load)
                pop     de
                push    hl                  ; guard the text cursor — CALSLT (inside
                push    de                  ; fat_io_*) clobbers HL + regs
                ld      a,(FCH_MODE)        ; action: 1 INPUT/2 OUTPUT/3 APPEND/4 RANDOM
                cp      2
                jr      z,oo_create
                cp      3
                jr      z,oo_append
                cp      4
                jr      z,oo_random_setup
                call    fat_io_open         ; INPUT: mount + find + prime read
                jr      oo_done
oo_create:
                call    fat_io_create       ; OUTPUT: make/truncate + prime write
                jr      oo_done
oo_append:
                call    fat_io_append       ; APPEND: open existing + position at EOF
                jr      oo_done
oo_random_setup:
                ; RANDOM: open-or-create the on-disk file and seed the channel's
                ; record state (FWR_FIRST/FWR_BYTES/FWR_DIRSEC-OFF), then space-fill
                ; the record buffer. GET/PUT (basic/field.asm) drive the record I/O.
                call    fat_rand_open
oo_done:
                pop     de
                pop     hl
                jr      c,oo_fail           ; not found / dir-full / mount / I-O error
                ; success: record the open mode in the channel table + the mirror.
                ; APPEND (3) behaves exactly like OUTPUT (2) for every later op
                ; (PRINT#/CLOSE), so it is stored as 2 — the action distinction only
                ; mattered at open. The FCH_MODES address math uses HL, so guard the
                ; text cursor (HL) that exec_stmt needs to continue the line.
                ld      a,e
                ld      (FCH_NUM),a
                ld      a,(FCH_MODE)
                cp      3
                jr      nz,oo_storemode
                ld      a,2                 ; normalise APPEND -> OUTPUT for the table
                ld      (FCH_MODE),a
oo_storemode:
                push    hl
                ld      c,e
                ld      b,0
                ld      hl,FCH_MODES
                add     hl,bc
                ld      a,(FCH_MODE)        ; 1 (INPUT) or 2 (OUTPUT/APPEND)
                ld      (hl),a              ; FCH_MODES[ch] = mode (now committed)
                pop     hl
                jp      exec_stmt
oo_fail:
                ; post-claim failure (DE = channel): release the slot we claimed and
                ; mark the channel closed in the table (its globals are stale garbage).
                ld      c,e
                ld      b,0
                ld      hl,FCH_MODES
                add     hl,bc
                xor     a
                ld      (hl),a              ; FCH_MODES[ch] = 0
                ld      (FCH_MODE),a
                ld      (FCH_ACTIVE),a      ; no channel live (don't save the garbage)
                jp      load_error
oo_nodisk:
                xor     a
                ld      (FCH_MODE),a        ; no slot was claimed; leave FCH_ACTIVE alone
                jp      load_error
oo_fail_syn:
                xor     a
                ld      (FCH_MODE),a
                jp      stmt_error

; --- OPEN "LPT:"/"CRT:" device channel --------------------------------------
; A character-device channel: PRINT#n streams to the printer (LPTOUT) or the
; screen (CHPUT) via pchar's PRDEV dispatch. It owns NO fat.asm context (no
; fch_claim / fat_io_open), so it must never be fch_select'd; it is marked in
; FCH_MODES with the device value LPT_MODE/CRT_MODE and its channel number is
; classified straight from that array by PRINT#/CLOSE. Only FOR OUTPUT is valid
; (INPUT from LPT:/CRT: is an error); LEN= is rejected. Sinks are the already-
; implemented BIOS entry points (LPTOUT $00A5 in zerobas-tape; CHPUT $00A2).
; Entry: HL -> the char after the "LPT:"/"CRT:" prefix, inside the quotes.
oo_dev_lpt:
                ld      a,LPT_MODE
                jr      oo_dev_open
oo_dev_crt:
                ld      a,CRT_MODE
oo_dev_open:
                ld      (OO_DEVTYPE),a      ; remember the device type across the parse
                ; skip any remaining "filename" chars up to the closing quote (ignored)
oodv_fn:
                ld      a,(hl)
                or      a
                jp      z,oo_fail_syn       ; unterminated string
                inc     hl
                cp      '"'
                jr      nz,oodv_fn          ; consume through the closing quote
                ; require: FOR OUTPUT AS [#]n , then end-of-statement
                call    skip_spaces
                ld      a,(hl)
                cp      FOR_TOKEN
                jp      nz,oo_fail_syn      ; device channels require FOR OUTPUT
                inc     hl
                call    skip_spaces
                ld      a,(hl)
                cp      OUT_TOKEN           ; OUTPUT = OUT + PUT (two reserved words)
                jp      nz,oo_fail_syn      ; INPUT from LPT:/CRT: is invalid
                inc     hl
                ld      a,(hl)
                cp      PUT_TOKEN
                jp      nz,oo_fail_syn
                inc     hl
                call    skip_spaces         ; "AS" (verbatim ASCII, upper/lower)
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
                jr      nz,oodv_num
                inc     hl
oodv_num:
                call    eval                ; DE = channel number, HL past it
                ld      a,d
                or      a
                jp      nz,oo_fail_syn      ; > 255 -> bad file number
                ld      a,e
                call    fch_valid
                jp      nc,oo_fail_syn      ; 0 or > MAXF -> bad file number
                call    skip_spaces         ; only a terminator may follow (no LEN=)
                ld      a,(hl)
                or      a
                jr      z,oodv_ok
                cp      COLON
                jp      nz,oo_fail_syn
oodv_ok:
                ; mark the channel open as a device (FCH_MODES[ch] = LPT/CRT_MODE);
                ; no fat.asm I/O. Guard the text cursor across the array store.
                push    hl
                ld      d,0                 ; DE = channel (e set)
                ld      hl,FCH_MODES
                add     hl,de
                ld      a,(OO_DEVTYPE)
                ld      (hl),a
                pop     hl
                jp      exec_stmt

; --- OPEN "CAS:name" FOR OUTPUT|INPUT AS #n --------------------------------
; A cassette SEQUENTIAL data channel. Like LPT:/CRT: it owns no fat.asm context
; (never fch_select'd); unlike them it drives the real tape via the M1/M2 ASCII
; block machinery: FOR OUTPUT writes the $EA header now and PRINT#n buffers data
; bytes through the cassette sink (cas_wbyte), CLOSE flushing the final block;
; FOR INPUT re-locks the tape (TAPION), verifies the $EA id, primes data block 1,
; and INPUT#/LINE INPUT#n read via cas_in_getbyte (Ctrl-Z = EOF). Both OUTPUT and
; INPUT are valid (unlike LPT/CRT which are output-only); APPEND/RANDOM and LEN=
; are not. Clean-room: the cassette ASCII/sequential format is the MSX2 Technical
; Handbook cassette chapter (same $EA id + 256-byte blocks + Ctrl-Z as SAVE",A");
; the byte layer is our own M1/M2 code. See spec-cas-ascii-saveload.md §5 + the
; tape option-surface audit. A cassette channel must not be interleaved with a disk
; file channel (they share the $E600 block buffer) — documented (single tape file).
; Entry: HL -> the char after "CAS:" (dev_cmp advanced it), inside the quotes.
oo_dev_cas:
                call    tape_parse_name     ; fill TSV_NAME[0..5]; HL -> closing '"'
                ld      a,(hl)
                cp      '"'
                jp      nz,oo_fail_syn
                inc     hl                  ; past the closing '"'
                ; require FOR INPUT | FOR OUTPUT
                call    skip_spaces
                ld      a,(hl)
                cp      FOR_TOKEN
                jp      nz,oo_fail_syn      ; CAS: needs FOR (no RANDOM cassette)
                inc     hl
                call    skip_spaces
                ld      a,(hl)
                cp      INPUT_TOKEN
                jr      z,oocas_in
                cp      OUT_TOKEN           ; OUTPUT = OUT + PUT (two reserved words)
                jr      z,oocas_out
                jp      oo_fail_syn         ; APPEND not supported on cassette
oocas_in:
                inc     hl
                ld      a,CAS_IN_MODE
                jr      oocas_setmode
oocas_out:
                inc     hl
                ld      a,(hl)
                cp      PUT_TOKEN
                jp      nz,oo_fail_syn
                inc     hl
                ld      a,CAS_OUT_MODE
oocas_setmode:
                ld      (OO_DEVTYPE),a      ; remember the CAS mode across the AS/#n parse
                call    skip_spaces         ; "AS" (verbatim ASCII, upper/lower)
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
                jr      nz,oocas_num
                inc     hl
oocas_num:
                call    eval                ; DE = channel number, HL past it
                ld      a,d
                or      a
                jp      nz,oo_fail_syn      ; > 255 -> bad file number
                ld      a,e
                call    fch_valid
                jp      nc,oo_fail_syn      ; 0 or > MAXF -> bad file number
                call    skip_spaces         ; only a terminator may follow (no LEN=)
                ld      a,(hl)
                or      a
                jr      z,oocas_argsok
                cp      COLON
                jp      nz,oo_fail_syn
oocas_argsok:
                ; args fully validated -> now do the tape I/O (so a parse error never
                ; leaves a half-written tape). Guard the channel + text cursor across it.
                push    de                  ; DE = channel
                push    hl                  ; text cursor (TAPOON/TAPIN clobber all)
                ld      a,(OO_DEVTYPE)
                cp      CAS_OUT_MODE
                jr      z,oocas_do_out
                ; --- FOR INPUT: re-lock the tape, verify $EA, prime data block 1 ---
                ; OPEN"CAS:" opens the NEXT file (name-matching is Item A's CLOAD/
                ; LOAD/RUN/MERGE scope, not OPEN) — so match off, then cas_open_match
                ; consumes the full header and cas_ascii_setup primes block 1.
                xor     a
                ld      (CAS_WANT_ON),a     ; load next file (no name-match on OPEN)
                call    cas_open_match      ; TAPION header + read id/name; CF = tape end
                jr      c,oocas_ioerr
                ld      a,(CAS_HDRID)
                cp      ASCII_ID            ; a cassette data file is an $EA ASCII file
                jr      nz,oocas_ioerr
                call    cas_ascii_setup     ; prime data block 1
                jr      c,oocas_ioerr
                jr      oocas_mark
oocas_do_out:
                ; --- FOR OUTPUT: write the $EA header block; arm the data buffer ---
                call    cas_write_ea_header ; TAPOON long + $EA*10 + TSV_NAME + TAPOOF
                jr      c,oocas_ioerr       ; CAS_WCNT reset to 0 on success
oocas_mark:
                pop     hl                  ; text cursor
                pop     de                  ; channel
                push    hl                  ; guard cursor across the array store
                ld      d,0
                ld      hl,FCH_MODES
                add     hl,de
                ld      a,(OO_DEVTYPE)
                ld      (hl),a              ; FCH_MODES[ch] = CAS_OUT/CAS_IN (committed)
                pop     hl
                jp      exec_stmt
oocas_ioerr:
                pop     hl
                pop     de
                jp      load_error

; dev_cmp — case-insensitive compare of the string at (HL) against the
; 0-terminated device name at (DE). Match: Z, HL advanced past the prefix.
; Mismatch: NZ, HL unchanged. Clobbers A, C, DE.
dev_cmp:
                push    hl                  ; save the start for the mismatch restore
dcmp_lp:
                ld      a,(de)
                or      a
                jr      z,dcmp_hit          ; hit the 0 term -> full prefix matched
                ld      c,a                 ; expected (uppercase) char
                ld      a,(hl)
                call    upcase
                cp      c
                jr      nz,dcmp_miss
                inc     hl
                inc     de
                jr      dcmp_lp
dcmp_hit:
                pop     bc                  ; discard the saved start (keep advanced HL)
                xor     a                   ; Z set
                ret
dcmp_miss:
                pop     hl                  ; restore HL to the string start
                ld      a,1
                or      a                   ; NZ
                ret

dev_lpt:        db      "LPT:",0
dev_crt:        db      "CRT:",0

; oo_parse_reclen — parse an optional "LEN = expr" record-size clause at (HL).
; LEN is the $FF $92 function token; '=' is EQ_TOKEN. Absent -> DE = 256 (the
; historical fixed record length), Cy = 0. Present -> DE = the evaluated record
; length, validated to a power of two in 1..256 (so records tile the 512-byte
; sector with no straddle); a non-tiling / out-of-range value returns Cy = 1
; (caller raises Syntax error). HL advances past whatever was consumed.
; Clobbers A,BC,DE,HL.
oo_parse_reclen:
                call    skip_spaces
                ld      a,(hl)
                cp      PEEK_PREFIX         ; $FF function-token prefix?
                jr      nz,opr_default
                inc     hl
                ld      a,(hl)
                cp      LEN_TOKEN           ; $92 = LEN
                jr      z,opr_have
                dec     hl                  ; not LEN -> restore cursor to the $FF
opr_default:
                ld      de,256              ; no LEN= -> default record length
                or      a                   ; Cy = 0
                ret
opr_have:
                inc     hl                  ; past $92
                call    skip_spaces
                ld      a,(hl)
                cp      EQ_TOKEN            ; '='
                jr      nz,opr_bad
                inc     hl
                call    eval                ; DE = record length, HL past it
                ld      a,d
                or      a
                jr      z,opr_lowbyte       ; D=0 -> reclen 1..255
                ; D != 0: the only legal value is exactly 256 (D=1, E=0).
                dec     a
                jr      nz,opr_bad          ; D>=2 -> > 512
                ld      a,e
                or      a
                jr      nz,opr_bad          ; D=1,E!=0 -> > 256
                ld      de,256              ; reclen = 256 (2 records / sector)
                or      a                   ; Cy = 0
                ret
opr_lowbyte:
                ld      a,e
                or      a
                jr      z,opr_bad           ; reclen 0 invalid
                ld      b,a
                dec     a
                and     b                   ; (E & (E-1)) == 0 iff power of two
                jr      nz,opr_bad          ; not a power of two -> would straddle
                or      a                   ; Cy = 0 (A already 0); DE = reclen (D=0)
                ret
opr_bad:
                scf
                ret

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
                cp      '#'                 ; file form (#n) vs the console form
    IF ROM_BASE < $4000
                jp      nz,input_console    ; repack: console INPUT / LINE INPUT (basic/input.asm)
    ELSE
                jp      nz,stmt_error       ; lean: console INPUT = Phase 3
    ENDIF
                inc     hl
                call    eval                ; DE = channel number
                ld      a,e
                call    fch_valid
                jp      nc,load_error       ; 0 or > MAXF -> bad file number
                ; classify the channel by FCH_MODES[ch] WITHOUT fch_select (a cassette
                ; channel owns no fat.asm ctx — selecting it would LDIR garbage over
                ; the globals). CAS_IN reads via cas_in_getbyte; a disk channel keeps
                ; the fch_select + FCH_MODE==1 path. read_into_strscr sources bytes
                ; through the ARL_GETBYTE vector, set here per channel type.
                push    hl                  ; guard text cursor
                ld      d,0
                ld      hl,FCH_MODES
                add     hl,de
                ld      a,(hl)
                pop     hl
                cp      CAS_IN_MODE
                jr      z,inp_cas
                push    hl                  ; guard text cursor (fch_select uses LDIR)
                ld      a,e
                call    fch_select          ; make channel e live; FCH_MODE = its mode
                pop     hl
                ld      a,(FCH_MODE)
                cp      1                   ; a channel must be open for INPUT
                jp      nz,load_error
                ld      de,fat_io_getbyte   ; disk channel -> read via fat_io_getbyte
                ld      (ARL_GETBYTE),de
                jr      inp_readvar
inp_cas:
                ld      de,cas_in_getbyte   ; CAS: input channel -> tape block source
                ld      (ARL_GETBYTE),de
inp_readvar:
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
    IF ROM_BASE < $4000
                call    strscr_desc         ; RVDESC -> [len][ptr] wrapping STRSCR
                ex      de,hl               ; DE = RVDESC (str_set_key's source arg)
    ELSE
                ld      de,STRSCR
    ENDIF
                call    str_set_key         ; store the line into the string variable
                pop     hl
    IF ROM_BASE < $4000
                ; arrays slice-4c (§7.3) follow-up, same disposition as
                ; console/LINE INPUT's own checks (basic/input.asm): a
                ; scalar-CHAIN OOM here sets FPERR but does not itself abort.
                ; SP is at statement level (the guard words above are both
                ; popped) -- check_expr_errors (interp.asm) is the SP-clean-
                ; site variant. It also aborts on a stale TMISMATCH/FPERR from
                ; the earlier channel-number eval (files.asm ~:748, unchecked):
                ; a type-poisoned channel expr hard-zeroes to channel 0 and
                ; derails to "load error"/"syntax error" BEFORE this read, so
                ; no spurious late "type mismatch" is constructible here; but a
                ; mid-statement FP error like `INPUT#1+0*(1/0),B$` now surfaces
                ; "division by zero" AFTER the field is read (pre-slice-4c it
                ; was swallowed) -- a deliberate deviation from the reference's
                ; abort-before-read ordering (an earlier post-eval check would
                ; close it; deferred, out of this slice's scope -- Fable review
                ; 2026-07-17 finding A).
                call    check_expr_errors
    ENDIF
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
                call    arl_getbyte         ; byte source vector: fat_io_getbyte (disk)
                                            ; or cas_in_getbyte (CAS: input), set by
                                            ; ex_input per channel type
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
; CLOSE [#n] — close one channel, or (bare CLOSE) every open channel. An OUTPUT
; channel is flushed + Ctrl-Z-stamped via fch_do_close_ch (which selects it first,
; so the right channel's buffer/dir state is the one flushed).
ex_close:
                inc     hl                  ; HL -> bytes after the CLOSE token
                call    skip_spaces
                ld      a,(hl)
                or      a
                jr      z,dc_all            ; bare CLOSE (end of line) -> close all
                cp      COLON
                jr      z,dc_all            ; bare CLOSE before ':' -> close all
                ; CLOSE [#]n [, [#]m ...] — a comma-separated channel list. Loop:
                ; parse one [#]expr, close it, and while the next token is ',' repeat.
dc_listloop:
                call    skip_spaces
                ld      a,(hl)
                cp      '#'
                jr      nz,dc_num
                inc     hl
dc_num:
                call    eval                ; DE = channel number; HL = text cursor
                push    hl                  ; guard the cursor (HL is reused + CALSLT)
                ld      a,e
                call    fch_valid
                jr      nc,dc_done          ; out of range -> lenient no-op
                ld      c,e                 ; FCH_MODES[ch] == 0 ? -> already closed
                ld      b,0
                ld      hl,FCH_MODES
                add     hl,bc
                ld      a,(hl)
                or      a
                jr      z,dc_done           ; not open -> no-op
                ld      a,e
                call    fch_do_close_ch     ; flush (if OUTPUT) + mark closed
dc_done:
                pop     hl                  ; restore the text cursor
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      nz,dc_finish        ; no more channels in the list
                inc     hl                  ; consume ',' and parse the next channel
                jr      dc_listloop
dc_finish:
                jp      exec_stmt
dc_all:
                push    hl                  ; guard text cursor across CALSLT
                call    fch_close_all
                pop     hl
                jp      exec_stmt

; init_filechan — cold-start the file-channel state: no channel open, PRINT to
; screen, the multi-channel table empty, and MAXFILES = 1 (the observed default:
; OPEN #1 works with no MAXFILES on the real CF-3300). Called from `init` before
; the banner is printed.
init_filechan:
                xor     a
                ld      (FCH_NUM),a
                ld      (FCH_MODE),a
                ld      (PRDEST),a
                ld      (PRDEV),a           ; default PRINT# sink = disk file
                ld      (FCH_ACTIVE),a      ; no channel live in the engine globals
                ld      hl,fat_io_getbyte
                ld      (ARL_GETBYTE),hl    ; default ascii_read_lines source (D2)
                ; clear the per-channel mode array [0..FCH_CEIL].
                ld      hl,FCH_MODES
                ld      b,FCH_CEIL+1
ifc_zero:
                ld      (hl),a
                inc     hl
                djnz    ifc_zero
                ld      a,1
                ld      (MAXF),a            ; default ceiling = 1 (#1 always usable)
                call    fld_init            ; empty the random-access field table
                ret

; ===========================================================================
; Channel manager (Phase 2 MAXFILES) — the multi-channel substrate that retires
; the single-channel limit, WITHOUT touching the oracle-validated fat.asm engine.
;
; fat.asm keeps ONE global set of streaming state (FSECTOR_BUF + FCH_STATE0..).
; Each open channel owns a context block (FCH_CTX[ch] = [state:FCH_STATESZ][512])
; holding a saved copy; the globals always hold the "active" channel's LIVE state.
; This is a write-back cache: FCH_ACTIVE names the live channel; switching to a
; different channel SAVES the globals to the old channel's ctx and LOADS the new
; one's. Re-using the same channel back-to-back (the common case) copies nothing.
; FCH_MODE/FCH_NUM mirror the active channel so the existing read/write/PRINT#
; code (which reads those + the globals) works unchanged.
;
; Register discipline: these routines move state with LDIR, so they clobber
; A/BC/DE/HL but NOT IX/IY (no CALSLT). Statement callers guard their HL text
; cursor; the EOF/LOF function callers rely on IX (the token cursor) surviving.
; ===========================================================================

; fch_ctx_addr — HL = base of channel A's context block (A = 1..FCH_CEIL).
;   HL = FCH_CTX + (A-1)*FCH_CTXSZ. Clobbers A, B, DE.
fch_ctx_addr:
                dec     a                   ; 0-based block index
                ld      hl,FCH_CTX
                or      a
                ret     z                   ; index 0 -> FCH_CTX
                ld      b,a
                ld      de,FCH_CTXSZ
fca_lp:
                add     hl,de
                djnz    fca_lp
                ret

; fch_save_active — save the engine globals to the active channel's context block.
; No-op when no channel is active. Clobbers A/BC/DE/HL.
fch_save_active:
                ld      a,(FCH_ACTIVE)
                or      a
                ret     z                   ; nothing live -> nothing to save
                call    fch_ctx_addr        ; HL = ctx[active]
                ex      de,hl               ; DE = ctx dest
                ld      hl,FCH_STATE0       ; copy the 50-byte engine-state span
                ld      bc,FCH_STATESZ
                ldir                        ; DE -> ctx + FCH_STATESZ
                ld      hl,FSECTOR_BUF      ; then the 512-byte data buffer
                ld      bc,512
                ldir
                ret

; fch_load_ctx — load channel A's context block into the engine globals and make
; it the active channel (FCH_ACTIVE = A). Clobbers A/BC/DE/HL.
fch_load_ctx:
                push    af                  ; keep the channel number
                call    fch_ctx_addr        ; HL = ctx[A]
                ld      de,FCH_STATE0
                ld      bc,FCH_STATESZ
                ldir                        ; ctx state -> globals; HL -> ctx + 50
                ld      de,FSECTOR_BUF
                ld      bc,512
                ldir                        ; ctx buffer -> FSECTOR_BUF
                pop     af
                ld      (FCH_ACTIVE),a
                ret

; fch_sync_mirror — FCH_NUM = FCH_ACTIVE, FCH_MODE = FCH_MODES[FCH_ACTIVE].
fch_sync_mirror:
                ld      a,(FCH_ACTIVE)
                ld      (FCH_NUM),a
                ld      e,a
                ld      d,0
                ld      hl,FCH_MODES
                add     hl,de
                ld      a,(hl)
                ld      (FCH_MODE),a
                ret

; fch_select — make channel A live in the engine globals (loading its context if a
; different channel is currently active) and refresh the FCH_MODE/FCH_NUM mirror.
; A = channel (assumed already range-validated). Clobbers A/BC/DE/HL; preserves IX.
fch_select:
                ld      b,a
                ld      a,(FCH_ACTIVE)
                cp      b
                jr      z,fsel_sync         ; already live -> just refresh the mirror
                push    bc
                call    fch_save_active     ; flush the previously-active channel
                pop     bc
                ld      a,b
                call    fch_load_ctx        ; ctx[A] -> globals, FCH_ACTIVE = A
fsel_sync:
                jp      fch_sync_mirror

; fch_claim — make channel A the active slot WITHOUT loading its (about-to-be-
; overwritten) context, used by OPEN before fat_io_open/create fills the globals.
; Any OTHER currently-active channel is saved first. A = channel. Clobbers regs.
fch_claim:
                ld      b,a
                ld      a,(FCH_ACTIVE)
                cp      b
                ret     z                   ; A already owns the globals
                push    bc
                call    fch_save_active     ; preserve the other channel's state
                pop     bc
                ld      a,b
                ld      (FCH_ACTIVE),a      ; A claims the globals (no load)
                ret

; fch_valid — CF set iff 1 <= A <= MAXF (a legal, in-ceiling channel number).
; A = channel. Clobbers A, B.
fch_valid:
                or      a
                ret     z                   ; 0 -> CF clear (invalid)
                ld      b,a
                ld      a,(MAXF)
                cp      b                   ; MAXF - ch: CY set iff ch > MAXF
                ccf                         ; invert -> CY set iff ch <= MAXF
                ret

; fch_do_close_ch — close channel A: if open FOR OUTPUT, append the Ctrl-Z text-EOF
; marker, flush, and stamp the directory; then mark the channel closed and release
; the engine globals. A = channel (1..FCH_CEIL, assumed open). CALSLT inside
; fat_io_* clobbers everything incl. IX/IY — the caller must guard its HL cursor.
fch_do_close_ch:
                ; A device channel (LPT:/CRT:, FCH_MODES[ch] >= LPT_MODE) owns no
                ; fat.asm context: skip fch_select (which would LDIR an uninitialised
                ; ctx block over the engine globals, corrupting any concurrently-open
                ; disk channel) and the OUTPUT flush; just clear its mode entry.
                ld      e,a
                ld      d,0
                ld      hl,FCH_MODES
                add     hl,de
                ld      a,(hl)
                cp      LPT_MODE
                jr      c,fdcc_disk         ; mode < 5 -> disk channel (INPUT/OUTPUT)
                cp      CAS_OUT_MODE
                jr      z,fdcc_cas_out      ; 7 -> flush the final tape block + motor off
                cp      CAS_IN_MODE
                jr      z,fdcc_cas_in       ; 8 -> just stop the motor
                ld      (hl),0              ; LPT/CRT device channel: clear entry, done
                ret
fdcc_cas_out:
                push    hl                  ; guard FCH_MODES[ch] ptr across the flush
                call    cas_ascii_finish    ; Ctrl-Z EOF + pad the final block; the pad
                                            ; loop's 256th byte flushes it (TAPOON+256+
                                            ; TAPOOF), so the block is closed on return
                call    TAPIOF              ; motor off
                pop     hl
                ld      (hl),0              ; FCH_MODES[ch] = 0 (closed)
                ret
fdcc_cas_in:
                push    hl
                call    TAPIOF              ; motor off (input channel: nothing to flush)
                pop     hl
                ld      (hl),0
                ret
fdcc_disk:
                ld      a,e
                call    fch_select          ; load the channel; FCH_MODE = its mode
                ld      a,(FCH_MODE)
                cp      2
                jr      nz,fdcc_clear       ; INPUT (or none): no dirty state to flush
                ld      a,$1A               ; OUTPUT: CP/M text-EOF (Ctrl-Z), as on the
                call    fat_io_putbyte      ; real CF-3300 CLOSE of a sequential file
                call    fat_io_close        ; flush partial sector + dir size/cluster
fdcc_clear:
                ld      a,(FCH_ACTIVE)      ; = the channel (fch_select made it active)
                call    fld_clear_chan      ; drop any FIELD definitions on this channel
                ld      a,(FCH_ACTIVE)      ; (fld_clear_chan clobbered A; reload)
                ld      e,a
                ld      d,0
                ld      hl,FCH_MODES
                add     hl,de
                xor     a
                ld      (hl),a              ; FCH_MODES[ch] = 0 (closed)
                ld      (FCH_MODE),a        ; mirror
                ld      (FCH_ACTIVE),a      ; globals no longer hold a valid channel
                ret

; fch_close_all — close every open channel (flushing OUTPUT ones). Used by bare
; CLOSE and by MAXFILES (which reinitialises the channel table). Guard HL caller-
; side (CALSLT). Clobbers everything.
fch_close_all:
                ld      b,1                 ; channel index 1..FCH_CEIL
fcla_lp:
                ld      a,b
                cp      FCH_CEIL+1
                ret     nc
                push    bc
                ld      e,b
                ld      d,0
                ld      hl,FCH_MODES
                add     hl,de
                ld      a,(hl)
                or      a
                jr      z,fcla_next         ; not open -> skip
                ld      a,b
                call    fch_do_close_ch
fcla_next:
                pop     bc
                inc     b
                jr      fcla_lp

; --- KILL "name" — delete a file -------------------------------------------
; Frees the file's FAT cluster chain and marks its directory entry deleted, via
; the fat.asm `fat_delete` engine routine. Accepts the same "A:"/"B:" drive prefix
; + 8.3 name as the loader verbs (parse_disk_fcb), now including 8.3 '*'/'?'
; wildcards: `KILL "*.BAK"` deletes every match. Errors (no disk / none matched /
; I-O) reuse the loader's load_error path. See basic/PROVENANCE.md §KILL.
ex_kill:
                inc     hl                  ; HL -> bytes after the KILL token
                jp      do_kill
do_kill:
                call    skip_spaces
                ld      a,(hl)
                cp      '"'
                jp      nz,stmt_error       ; filename string required
                inc     hl                  ; HL -> first filename char
                call    parse_disk_fcb      ; build DISK_FCB_NAME (8.3 wildcard pattern)
                inc     hl                  ; past the closing '"'
                ld      a,(DISKSLOT_OK)
                or      a
                jp      z,load_error
                push    hl                  ; guard text cursor across CALSLT
                ; wildcard delete: fat_delete finds + frees + $E5-marks the FIRST
                ; matching entry (name_cmp honours '?'), so loop it until no match
                ; remains. C tracks whether anything was deleted -> File not found
                ; (load_error) if the pattern matched nothing (Q4.1). A non-wildcard
                ; name simply matches once, exactly as before.
                ld      c,0                 ; C = deleted-any flag
dk_loop:
                push    bc
                call    fat_delete          ; free chain + $E5-mark the first match
                pop     bc
                jr      c,dk_done           ; no (further) match -> stop
                ld      c,1                 ; deleted at least one
                jr      dk_loop
dk_done:
                pop     hl                  ; restore text cursor
                ld      a,c
                or      a
                jp      z,load_error        ; nothing matched -> File not found
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

; --- MAXFILES = n — size the multi-channel table ---------------------------
; MAXFILES sets how many file channels may be open simultaneously (the value also
; bounds every OPEN/INPUT#/PRINT#/CLOSE channel number, via fch_valid). Tokenised
; as MAX ($CD) + FILES ($B7) — two reserved words, oracle-locked like OUTPUT. Like
; the reference, changing MAXFILES reinitialises the file system: every open channel
; is closed first (OUTPUT ones flushed + Ctrl-Z-stamped). zerobas accepts 0..FCH_CEIL
; (the RAM-bounded ceiling, =2); a larger value is a syntax error — real MSX allows
; up to 15, a documented divergence (we have RAM for only FCH_CEIL 512-byte channel
; buffers). Entry: HL on the MAX token. See basic/PROVENANCE.md §MAXFILES.
ex_maxfiles:
                inc     hl                  ; past MAX ($CD)
                ld      a,(hl)
                cp      FILES_TOKEN         ; "MAXFILES" = MAX + FILES; require FILES
                jp      nz,stmt_error       ; bare MAX is not a statement
                inc     hl                  ; past FILES ($B7)
                call    skip_spaces
                ld      a,(hl)
                cp      EQ_TOKEN            ; '=' ($EF)
                jp      nz,stmt_error
                inc     hl
                call    eval                ; DE = requested ceiling
                ld      a,d
                or      a
                jp      nz,stmt_error       ; > 255 -> out of range
                ld      a,e
                cp      FCH_CEIL+1
                jp      nc,stmt_error       ; > FCH_CEIL -> beyond our RAM ceiling
                push    de                  ; guard the requested value
                push    hl                  ; guard the text cursor across CALSLT
                call    fch_close_all       ; MAXFILES reinitialises: close everything
                pop     hl
                pop     de
                ld      a,e
                ld      (MAXF),a            ; commit the new ceiling (0..FCH_CEIL)
                jp      exec_stmt

; --- MERGE "name" — merge an ASCII program from disk ------------------------
; Reads a SAVE",A"-style ASCII (line-numbered text) program file and stores each
; line into the CURRENT program (insert-or-replace by line number) — the existing
; program is KEPT, unlike LOAD. Each file line is accumulated into LINEBUF and fed
; to dispatch_line, exactly as if it had been typed: the same tokeniser + store_line
; path. Lines end at CR ($0D); LF ($0A) is ignored; a Ctrl-Z ($1A) or EOF ends the
; file. A non-blank, non-numbered line is a "Direct statement in file" error (also
; what guards against a tokenised file being read as garbage ASCII). The byte stream
; uses the global fat_io read state directly (like LOAD/BLOAD), so MERGE while a
; user file channel is open is undefined (documented). Token $B6 oracle-locked.
; Sources: MSX-BASIC language reference (MERGE merges ASCII line-numbered programs);
; the ASCII save format = line text + CR/LF, Ctrl-Z terminator. See PROVENANCE §MERGE.
ex_merge:
                inc     hl                  ; HL -> bytes after the MERGE token
                call    skip_spaces
                ld      a,(hl)
                cp      '"'
                jp      nz,stmt_error       ; filename string required
                inc     hl                  ; HL -> first filename char (inside quotes)
                ; device dispatch: "CAS:" -> tape ASCII merge; else -> disk. dev_cmp
                ; advances HL past a matched prefix, restores it on a miss (so the
                ; disk path still sees HL at the filename start).
                ld      de,dev_cas
                call    dev_cmp
                jp      z,merge_cas         ; matched "CAS:" -> tape merge (HL past prefix)
                call    parse_disk_fcb      ; build DISK_FCB_NAME; HL -> closing '"'
                inc     hl                  ; past the closing '"'
                ld      a,(DISKSLOT_OK)
                or      a
                jp      z,load_error
                push    hl                  ; guard the text cursor across the merge
                call    fat_io_open         ; mount + find + prime the sequential read
                jp      c,mrg_ioerr         ; not found / mount / I-O error
                call    ascii_read_lines    ; tokenise+store each line; CF set = bad line
                pop     hl                  ; restore the text cursor
                jp      c,stmt_error        ; non-numbered line -> "Direct statement in file"
                jp      exec_stmt
mrg_ioerr:
                pop     hl
                jp      load_error

; --- MERGE "CAS:name" — merge an ASCII program from cassette ------------------
; The tape counterpart of the disk MERGE above: read an $EA ASCII cassette file and
; store each line into the CURRENT program (insert/replace by number — the existing
; program is KEPT, NO new_prog). Reuses the M1 cassette-ASCII byte machinery: open
; the tape (TAPION), require the $EA file-type id, then cas_ascii_setup (skip header
; + prime block 1) + cas_ascii_drive (ascii_read_lines off cal_getbyte, restore +
; TAPIOF) — exactly what cas_ascii_load does, minus the new_prog. A tokenised ($D3)
; or unknown file is rejected (MERGE needs ASCII text). Clean-room: MERGE semantics
; from the MSX-BASIC language reference; format + byte source are our own M1 code.
; Entry: HL is inside the quotes, past "CAS:". Tier-3 (spec-cas-tier3-cload.md
; Item A): the name is now HONOURED — captured into CAS_WANT and located by
; cas_open_match (case-sensitive), skipping earlier non-matching files. An empty
; name (MERGE"CAS:") merges the next file, unchanged.
merge_cas:
                call    cas_capture_name    ; -> CAS_WANT + CAS_WANT_ON; HL on '"'
                ld      a,(hl)
                cp      '"'
                jp      nz,stmt_error       ; unterminated string
                inc     hl                  ; past the closing '"'
                push    hl                  ; guard the text cursor across the merge
                call    cas_open_match      ; find the (named) $EA file; header consumed
                jp      c,mc_ioerr
                ld      a,(CAS_HDRID)
                cp      ASCII_ID            ; MERGE requires an ASCII ($EA) file
                jp      nz,mc_ioerr         ; tokenised / other -> cannot merge
                call    cas_ascii_setup     ; prime data block 1
                jp      c,mc_ioerr
                ; NB: NO new_prog — MERGE inserts into the current program.
                call    cas_ascii_drive     ; read + tokenise + store each line; CF=bad line
                pop     hl                  ; restore the text cursor
                jp      c,stmt_error        ; non-numbered line -> "Direct statement in file"
                jp      exec_stmt
mc_ioerr:
                pop     hl
                jp      load_error

; --- ascii_read_lines — read a line-numbered ASCII (SAVE",A") program from the
; ALREADY-OPEN fat_io sequential stream, tokenising + storing each line via
; mrg_storeline -> dispatch_line (the same path as a typed line). SHARED by MERGE
; (which keeps the current program) and ASCII LOAD (whose caller cleared it via
; new_prog first). Lines end at CR ($0D); LF ($0A) is ignored; Ctrl-Z ($1A) or EOF
; ends the file. dispatch_line uses LINEBUF/TOKBUF/SL_* + the program text area, NOT
; the fat_io read state (FREAD_*/FSECTOR_BUF), so the file stream survives across it.
; Sources: MSX-BASIC language reference (ASCII program = line text + CR/LF, Ctrl-Z
; terminator); clean-room, no reference ROM read. See PROVENANCE §MERGE and
; basic/docs/spec-ascii-saveload.md §4.
;   out: CF clear = whole file stored OK; CF set = a non-blank, non-numbered line.
;
; Byte source (D2 getbyte indirection): reads go through arl_getbyte, which
; jumps through the ARL_GETBYTE RAM vector (sysvars.inc) instead of calling
; fat_io_getbyte directly. Defaulted to fat_io_getbyte at cold start
; (init_filechan), so MERGE and disk ASCII LOAD (both callers above/below) are
; byte-for-byte unchanged; cload.asm's cas_ascii_load re-points it at a TAPIN
; wrapper for a cassette ASCII load. See basic/docs/spec-cas-ascii-saveload.md §6 D2.
ascii_read_lines:
arl_newline:
                ld      hl,LINEBUF          ; start a fresh line
                ld      (MRG_PTR),hl
arl_charloop:
                call    arl_getbyte
                jr      c,arl_eofline       ; EOF -> flush any partial line, then finish
                cp      $1A
                jr      z,arl_eofline       ; Ctrl-Z soft-EOF -> finish
                cp      $0A
                jr      z,arl_charloop      ; ignore LF
                cp      $0D
                jr      z,arl_endline       ; CR -> end of this line
                ld      c,a                 ; C = the data char (survives the bounds math)
                ld      hl,(MRG_PTR)
                ld      a,l                 ; bounds: keep the last LINEBUF byte for the 0
                cp      (LINEBUF+LINEMAX-1) & $FF  ; (LINEBUF is one page -> low byte suffices)
                jr      nc,arl_charloop     ; line full -> drop extra chars
                ld      (hl),c
                inc     hl
                ld      (MRG_PTR),hl
                jr      arl_charloop
arl_endline:
                call    mrg_storeline       ; tokenise + store this line
                ret     c                   ; non-numbered line -> CF set (caller errors)
                jr      arl_newline
arl_eofline:
                ld      hl,(MRG_PTR)        ; flush a final line with no trailing CR
                ld      a,l
                cp      LINEBUF & $FF
                jr      z,arl_ok            ; nothing accumulated -> done
                call    mrg_storeline
                ret     c
arl_ok:
                or      a                   ; CF clear = success
                ret

; --- arl_getbyte: ascii_read_lines' byte-source indirection (D2) ------------
; Jumps through the ARL_GETBYTE RAM vector to the CURRENT byte-source routine
; (fat_io_getbyte by default; cload.asm's cal_getbyte during a cassette ASCII
; load). Standard Z80 call-through-pointer idiom: `call arl_getbyte` pushes
; OUR caller's return address, then `jp (hl)` jumps to the target WITHOUT
; touching the stack, so the target's own `ret` pops that same address —
; reaching ascii_read_lines exactly as a direct `call fat_io_getbyte` would.
; Preserves nothing (neither source routine does); ascii_read_lines already
; reloads everything it needs from RAM after each call.
;   out: A = byte, CF clear; or CF set = no more data (source-defined "EOF").
arl_getbyte:
                ld      hl,(ARL_GETBYTE)
                jp      (hl)

; mrg_storeline — 0-terminate LINEBUF at MRG_PTR and, if it is a numbered (or blank)
; line, hand it to dispatch_line (same tokenise + store_line path as a typed line).
;   out: CF set = a non-blank, non-numbered line (error); CF clear = stored/skipped.
; dispatch_line uses LINEBUF/TOKBUF/SL_* + the program text area — NOT the fat_io
; read state (FREAD_*/FSECTOR_BUF) — so the file stream survives across it.
mrg_storeline:
                ld      hl,(MRG_PTR)
                ld      (hl),0              ; terminate the accumulated line
                ld      hl,LINEBUF
                call    skip_spaces
                ld      a,(hl)
                or      a
                jr      z,msl_ok            ; blank line -> skip
                cp      '0'
                jr      c,msl_err
                cp      '9'+1
                jr      nc,msl_err          ; not a digit -> not a numbered line
                call    dispatch_line       ; numbered -> crunch + store (insert/replace)
msl_ok:
                or      a                   ; CF clear = ok
                ret
msl_err:
                scf                         ; CF set = direct/garbage line
                ret
