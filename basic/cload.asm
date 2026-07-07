; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; cload.asm — the CLOAD and LOAD"CAS:" statement handlers.
;
; This is the *interpreter half* of the cassette program-load verbs. Where
; BLOAD (bload.asm) reads a BSAVE *binary image* into raw RAM, CLOAD and
; LOAD"CAS:" read a *tokenised BASIC program* off cassette into the stored-
; program area — the same line-link area that NEW / RUN / LIST manage — and make
; it the current program, as if it had been typed.
;
; Both verbs share one cassette I/O path (do_tape_prog). They differ only in how
; they parse their argument:
;   CLOAD ["filename"]      — the device is implicitly cassette; the optional
;                             quoted name is the tape file to find (we accept and
;                             ignore it: TAPION loads the next file on the tape).
;   LOAD "CAS:filename"     — the OPEN-style form: the device "CAS:" is explicit,
;                             then the optional filename.
;
; Cassette file format (MSX2 Technical Handbook, cassette file format). Like a
; BSAVE binary, a tokenised BASIC file is TWO tape blocks: a header block (10x
; file-id $D3 + a 6-char filename) and a data block (the program-area image) —
; so, like BLOAD, there are TWO TAPION calls, one per block tone. The data block
; omits the binary's 6-byte address header; it is the program image: a chain of
; [link:2 LE][lineno:2 LE][tokens...][00] lines ending in a $0000 link word (the
; same line-link layout zerobas stores at TXTBASE — see program.asm). The device
; half blocks on tape silence once a block's data runs out (it does NOT signal a
; clean end-of-data), so the reader stops EXACTLY at the program's $0000 end-link
; and never reads a byte past it. The saved absolute links are recomputed by
; `relink` after the load, so the loaded program's bytes become byte-identical to
; one typed in.
;
; CLEAN-ROOM: the file-type id ($D3) and the cassette block layout are from the
; MSX2 Technical Handbook (cassette file format, an allowed source); the in-RAM
; line-link program format and TXTBASE are this project's own / oracle-confirmed
; (program.asm, sysvars.inc). TAPION/TAPIN/TAPIOF are the documented BIOS
; contract (sysvars.inc). The "accept and discard the filename, load the next
; tape file" behaviour is an own-design simplification (no tape file catalogue);
; see PROVENANCE.md. No disassembly.

; --- do_cload: CLOAD ["filename"] --------------------------------------------
; Entry: HL -> the bytes after the CLOAD token. An optional quoted filename may
; follow; it is parsed-past and ignored (TAPION simply opens the next file).
do_cload:
                call    skip_spaces
                ld      a,(hl)
                or      a
                jr      z,do_tape_prog      ; bare CLOAD -> load the next tape file
                cp      COLON               ; CLOAD : ... -> bare form
                jr      z,do_tape_prog
                cp      '"'                 ; CLOAD "name" -> skip the quoted name
                jp      nz,load_error
                call    skip_quoted
                jr      do_tape_prog

; --- do_load: LOAD "CAS:filename" | LOAD "A:filename"[,R] --------------------
; Entry: HL -> the bytes after the LOAD token. The argument is a quoted device
; string: a "CAS:" prefix selects the (unchanged) cassette path; anything else is
; a disk filename (optional "A:"/"B:" drive prefix) read from the disk BDOS layer.
; A "CAS:" filename is parsed-past and ignored (TAPION opens the next tape file);
; a disk LOAD "name",R loads the tokenised BASIC program and runs it.
;
; The "CAS:" prefix is peeked NON-DESTRUCTIVELY (exactly like do_bload): only once
; the full prefix matches do we commit to the tape path, so a name like "CASETTE"
; falls through cleanly to the disk path.
do_load:
                call    skip_spaces
                ld      a,(hl)
                cp      '"'                 ; opening quote required
                jp      nz,load_error
                inc     hl
                ; --- device dispatch: "CAS:" -> tape, else -> disk ----------
                push    hl                  ; remember the filename start
                ld      de,dev_cas          ; compare device name to "CAS:"
dl_dev:
                ld      a,(de)
                or      a
                jr      z,dl_is_cas         ; matched all of "CAS:" -> tape
                ld      c,a                 ; expected (uppercase) char
                ld      a,(hl)              ; typed char
                call    upcase              ; case-insensitive (typed may be lower)
                cp      c
                jr      nz,dl_is_disk       ; prefix mismatch -> disk path
                inc     hl
                inc     de
                jr      dl_dev
dl_is_cas:
                pop     af                  ; discard saved filename start
                ; HL is now inside the quotes, past "CAS:": skip the rest of the
                ; quoted filename to the closing quote (filename ignored).
do_load_fn:
                ld      a,(hl)
                or      a
                jp      z,load_error        ; unterminated string
                inc     hl
                cp      '"'                 ; consume through the closing quote
                jr      nz,do_load_fn
                jr      do_tape_prog

; --- do_load disk path: LOAD "A:name"[,R] -----------------------------------
; HL was advanced partway through the "CAS:" compare and must NOT be trusted —
; restore the filename start from the stack. Parse the FCB (shared with do_bload)
; and the closing-quote + ,R, load the tokenised program from disk, then run it
; iff ,R was given (LOAD"name",R = load and run; standard MSX behaviour).
dl_is_disk:
                pop     hl                  ; HL = filename start (after the quote)
                call    parse_disk_fcb      ; build DISK_FCB; HL -> closing '"'
                call    parse_close_run     ; closing quote + optional ,R -> RUNFLAG
                jp      c,load_error
                call    disk_prog_load      ; load the tokenised program into TXTBASE
                ; ,R ? -> run the freshly loaded program; else back to the REPL.
                ld      a,(RUNFLAG)
                or      a
                ret     z
                jp      run_prog            ; RUN the loaded program (program.asm)

; --- do_run: RUN | RUN <lineno> | RUN "A:name" ------------------------------
; Entry: HL -> the bytes after the RUN token (verbatim ASCII args).
;
; RUN"filename" is a thin wrapper: load a tokenised BASIC program from disk
; (exactly as LOAD"name" does — same parse_disk_fcb + disk_prog_load path) and
; then RUN it. The implicit run is the only difference from LOAD"name": there is
; no ,R option, running is the whole point.
;
; Two cases, dispatched on the first non-space char after RUN:
;   '"'  -> RUN"A:name": a disk program load-then-run. inc past the quote, build
;           the FCB (parse_disk_fcb), consume the closing quote (parse_close_run,
;           which also tolerates a trailing ,R harmlessly — running is implicit
;           either way), load the tokenised program, then jp run_prog.
;   else -> a bare tokenised RUN, or RUN<lineno> (the tokeniser stored the line
;           number as a line-ref token after RUN_TOKEN). Both run the stored
;           program from the start; we ignore any line number, matching the
;           direct-mode bare-RUN semantics in program.asm's dl_cmd path. Just
;           jp run_prog.
;
; Mirrors do_load's disk path exactly (parse_disk_fcb + disk_prog_load), so
; RUN"file" parses identically to LOAD"file" minus the implicit run. The load
; logic is NOT duplicated.
do_run:
                call    skip_spaces
                ld      a,(hl)
                cp      '"'                 ; a quoted filename -> disk load+run
                jp      nz,run_prog         ; bare RUN / RUN<lineno> -> run stored
                inc     hl                  ; past the opening quote
                call    parse_disk_fcb      ; build DISK_FCB; HL -> closing '"'
                call    parse_close_run     ; consume closing quote (and any ,R)
                jp      c,load_error
                call    disk_prog_load      ; load the tokenised program into TXTBASE
                jp      run_prog            ; ...and run it (running is implicit)

; --- skip_quoted: HL on the opening '"' -> HL past the closing '"' ------------
; Used by CLOAD to discard its optional quoted filename. Clobbers A.
skip_quoted:
                inc     hl                  ; past the opening quote
sq_lp:
                ld      a,(hl)
                or      a
                ret     z                   ; unterminated -> stop (caller proceeds)
                inc     hl
                cp      '"'
                jr      nz,sq_lp
                ret

; --- do_tape_prog: the shared cassette tokenised-BASIC load path -------------
; Opens the tape, verifies the BASIC file-type id, reads the program-area image
; line-by-line into the stored-program area at TXTBASE, relinks it, and makes it
; the current program. Mirrors bload.asm's tape contract (TAPION per block;
; TAPIN trashes every register, so state lives in RAM).
do_tape_prog:
                ; --- open the tape and skip the header block's leader tone ---
                call    TAPION              ; sync block 1 (file header)
                jp      c,load_error

                ; --- file header: 10x BASIC_ID + 6-char filename ------------
                ; Mirrors bload.asm: byte 0 is the file-type id. We require the
                ; tokenised-BASIC id ($D3) and discard the remaining 15 bytes.
                call    TAPIN
                jp      c,load_error
                cp      BASIC_ID            ; must be a tokenised BASIC file
                jp      nz,load_error
                ld      b,15                ; remaining header bytes
ctp_skip_hdr:
                push    bc                  ; TAPIN trashes all regs
                call    TAPIN
                pop     bc
                jp      c,load_error
                djnz    ctp_skip_hdr

                ; --- data block: skip its leader tone -----------------------
                ; Like BLOAD, the program data is a SEPARATE tape block, so it
                ; needs its own TAPION to re-lock onto the data block's leader.
                call    TAPION
                jp      c,load_error

                ; --- start a fresh program: store cursor at the text base ---
                ld      hl,TXTBASE
                ld      (CLPTR),hl
                ld      (CLINK),hl          ; A_0 = the saving machine's text base.
                                            ; The saved link words are consecutive
                                            ; absolute addresses; the first line's
                                            ; predecessor address is the saving
                                            ; machine's text base, assumed == ours
                                            ; (TXTBASE $8001, the MSX disk-BASIC base)

                ; --- read the program image, stopping at the $0000 end-link --
                ; The device half does NOT signal a clean end of data: once the
                ; tape block's bytes run out, TAPIN blocks on silence rather than
                ; returning CF. So we must stop reading EXACTLY when the program
                ; ends — at the $0000 link word that terminates the line-link
                ; chain — never reading a byte past it.
                ;
                ; LENGTH-DRIVEN copy. A token body legitimately contains $00 bytes
                ; (e.g. INT2 `$1C lo hi`, &H `$0C lo hi`, line-number refs), so the
                ; first $00 is NOT the line boundary. The boundary is defined by the
                ; saved link words: each link is the saving machine's absolute
                ; address of the NEXT line, so this line's full length is
                ; (this link) - (previous link) and its body length is that minus the
                ; 4-byte link+lineno header. We copy EXACTLY that many body bytes —
                ; embedded $00s included — landing precisely on the next link word.
                ;
                ; Per line: read the 2-byte link word; $0000 -> end of program.
                ; Otherwise store link word + 2-byte line number verbatim, then copy
                ; the computed body byte count. The saved links are stored as-is;
                ; relink (token-aware) recomputes them below.
ctp_line:
                call    TAPIN               ; link low
                jp      c,load_error
                push    af                  ; preserve link-low: TAPIN clobbers C
                call    TAPIN               ; link high
                jp      c,ctp_link_err      ; must pop before leaving
                ld      b,a                 ; B = link high
                pop     af
                ld      c,a                 ; C = link low (restored)
                                            ; BC = saved link word L_n = A_{n+1}
                ld      a,b
                or      c
                jr      z,ctp_done          ; $0000 link -> program complete

                ; body length = L_n - A_n - 4   (A_n = CLINK = previous link word)
                ld      hl,(CLINK)          ; HL = A_n
                ld      (CLINK),bc          ; advance CLINK = L_n for the next line
                ld      a,c
                sub     l
                ld      e,a
                ld      a,b
                sbc     a,h
                ld      d,a                 ; DE = L_n - A_n = full line length
                dec     de
                dec     de
                dec     de
                dec     de                  ; DE = body length (incl. its $00 term)

                ; bounds: this line's header (>=4 bytes) must fit below TXTMAX
                push    de                  ; guard body length across TAPIN/stores
                ld      hl,(CLPTR)
                ld      de,TXTMAX-4
                or      a
                sbc     hl,de
                jp      nc,ctp_oom_pop

                ; store the (saved) link word verbatim; relink fixes it later
                ld      hl,(CLPTR)
                ld      (hl),c
                inc     hl
                ld      (hl),b
                inc     hl
                ld      (CLPTR),hl

                ; line number (2 bytes)
                call    TAPIN
                jp      c,ctp_err_pop
                ld      hl,(CLPTR)
                ld      (hl),a
                inc     hl
                ld      (CLPTR),hl
                call    TAPIN
                jp      c,ctp_err_pop
                ld      hl,(CLPTR)
                ld      (hl),a
                inc     hl
                ld      (CLPTR),hl
                pop     de                  ; DE = body length

                ; token body: copy EXACTLY DE bytes (embedded $00s and all)
ctp_body:
                ld      a,d
                or      e
                jr      z,ctp_line          ; whole body copied -> next line
                push    de                  ; guard remaining count across TAPIN
                ld      hl,(CLPTR)          ; bounds check
                ld      de,TXTMAX
                or      a
                sbc     hl,de
                jp      nc,ctp_oom_pop
                call    TAPIN
                jp      c,ctp_err_pop
                ld      hl,(CLPTR)
                ld      (hl),a
                inc     hl
                ld      (CLPTR),hl
                pop     de                  ; DE = remaining count
                dec     de
                jr      ctp_body

; ctp_link_err — the second TAPIN (link high) failed with CF; AF (link-low) is on
; the stack from the push before that call.  Pop it to restore balance, then error.
ctp_link_err:
                pop     af
                jp      load_error

; ctp_err_pop / ctp_oom_pop — body length / remaining count is on the stack; drop
; it before taking the shared error / out-of-memory path so the stack stays balanced.
ctp_err_pop:
                pop     de
                jp      load_error
ctp_oom_pop:
                pop     de
                jp      ctp_oom

ctp_done:
                call    TAPIOF              ; motor off (program fully read)

                ; --- write the $0000 end-of-program marker and set PRGEND ---
                ld      hl,(CLPTR)
                ld      (PRGEND),hl         ; end marker sits at the store cursor
                ld      (hl),0
                inc     hl
                ld      (hl),0
                ; keep the TXTTAB sysvar consistent with the program base
                ld      hl,TXTBASE
                ld      (TXTTAB),hl

                ; --- relink: recompute every line's absolute link pointer ---
                ; The saved links were absolute addresses on the saving machine;
                ; relink (program.asm) recomputes them from the loaded bytes, so
                ; the program is now byte-identical to one typed in.
                call    relink
                ret

ctp_oom:
                call    TAPIOF              ; stop the motor before reporting
                call    new_prog            ; leave a clean (empty) program
                ld      a,$CC               ; out-of-memory landmark (as store_line)
                ld      (ERRMARK),a
                ld      hl,err_prog_mem
                jp      print_string
err_prog_mem:   db      "out of memory",13,10,0

; --- disk_prog_load: load a TOKENISED BASIC program from disk ----------------
; The disk analogue of do_tape_prog. The FCB at DISK_FCB is fully built (drive
; code + 8.3 name) by parse_disk_fcb. This opens the file through the disk ROM's
; BDOS FCB layer, requires the on-disk tokenised-BASIC marker ($FF), streams the
; in-memory line-link image into the stored-program area at TXTBASE, closes the
; file, relinks, and returns — leaving a loaded, current program. The caller
; decides whether to RUN it (LOAD,R) so this is reusable by RUN"filename".
;
; On-disk tokenised-BASIC format (MSX-BASIC file formats, an allowed public
; language reference; see PROVENANCE.md §disk
; LOAD): a leading marker byte $FF (BASIC_DISK_ID), then the in-memory program
; image — the SAME line-link chain do_tape_prog reads:
;   [link:2 LE][lineno:2 LE][tokens...][00] per line, ending in a $0000 link word.
; This is DISTINCT from the BSAVE binary's $FE disk marker.
;
; Unlike the tape path (which has no clean end-of-data and must stop EXACTLY at
; the $0000 end-link), the disk reader has BOTH a real EOF (fat_io_getbyte CF=EOF)
; and the $0000 end-link. The $0000 link is the authoritative end (we stop there
; and close); an EOF encountered mid-line is a truncated/corrupt file -> error.
;
; Uses fat.asm's loader-side FAT12 engine over the standard $4010 DSKIO entry
; (disk-ROM-independent): fat_io_open (mount + find + prime) and fat_io_getbyte
; (the file byte stream). Mirrors do_tape_prog's ctp_line/ctp_body/ctp_done
; line-for-line, but sourcing bytes from fat_io_getbyte. No Close on the read side.
disk_prog_load:
                ; (1) disk ROM slot must have been recorded by the INIT scan.
                ld      a,(DISKSLOT_OK)
                or      a
                jp      z,load_error
                ; (2) open the file via the FAT12 engine (mount + find + prime).
                call    fat_io_open
                jp      c,load_error       ; not found / mount / I-O error
                ; (3) first byte selects the format: $FF = tokenised BASIC; anything
                ; else = an ASCII (SAVE",A") program (ASCII text never starts $FF).
                call    fat_io_getbyte
                jp      c,dpl_err           ; EOF before any data -> close + error
                cp      BASIC_DISK_ID
                jp      nz,ascii_load       ; not the $FF marker -> ASCII program load
                ; (5) start a fresh program: store cursor at the text base.
                ld      hl,TXTBASE
                ld      (CLPTR),hl
                ld      (CLINK),hl          ; A_0 = saving machine's text base (== ours)
                ; --- read the line-link image, stopping at the $0000 end-link ---
                ; LENGTH-DRIVEN, exactly like do_tape_prog's ctp_line/ctp_body: a
                ; token body may contain $00 bytes, so the line boundary is taken
                ; from the saved link-word differences, NOT the first $00. This
                ; line's body length = (this link) - (previous link) - 4; we copy
                ; exactly that many body bytes (embedded $00s included), landing on
                ; the next link word. The saved links are stored as-is; relink
                ; (token-aware) recomputes them below.
                ;
                ; Per line: read the 2-byte link word; $0000 -> end of program.
                ; Otherwise store link word + 2-byte line number verbatim, then copy
                ; the computed body byte count and loop.
dpl_line:
                call    fat_io_getbyte        ; link low
                jp      c,dpl_err           ; EOF mid-program -> truncated -> error
                push    af                  ; preserve link-low: fat_io_getbyte may clobber C
                call    fat_io_getbyte        ; link high
                jp      c,dpl_link_err      ; must pop before leaving
                ld      b,a                 ; B = link high
                pop     af
                ld      c,a                 ; C = link low (restored)
                                            ; BC = saved link word L_n = A_{n+1}
                ld      a,b
                or      c
                jr      z,dpl_done          ; $0000 link -> program complete

                ; body length = L_n - A_n - 4   (A_n = CLINK = previous link word)
                ld      hl,(CLINK)          ; HL = A_n
                ld      (CLINK),bc          ; advance CLINK = L_n for the next line
                ld      a,c
                sub     l
                ld      e,a
                ld      a,b
                sbc     a,h
                ld      d,a                 ; DE = L_n - A_n = full line length
                dec     de
                dec     de
                dec     de
                dec     de                  ; DE = body length (incl. its $00 term)

                ; bounds: this line's header (>=4 bytes) must fit below TXTMAX
                push    de                  ; guard body length across fat_io_getbyte
                ld      hl,(CLPTR)
                ld      de,TXTMAX-4
                or      a
                sbc     hl,de
                jp      nc,dpl_oom_pop

                ; store the (saved) link word verbatim; relink fixes it later
                ld      hl,(CLPTR)
                ld      (hl),c
                inc     hl
                ld      (hl),b
                inc     hl
                ld      (CLPTR),hl

                ; line number (2 bytes)
                call    fat_io_getbyte
                jp      c,dpl_err_pop
                ld      hl,(CLPTR)
                ld      (hl),a
                inc     hl
                ld      (CLPTR),hl
                call    fat_io_getbyte
                jp      c,dpl_err_pop
                ld      hl,(CLPTR)
                ld      (hl),a
                inc     hl
                ld      (CLPTR),hl
                pop     de                  ; DE = body length

                ; token body: copy EXACTLY DE bytes (embedded $00s and all)
dpl_body:
                ld      a,d
                or      e
                jr      z,dpl_line          ; whole body copied -> next line
                push    de                  ; guard remaining count across fat_io_getbyte
                ld      hl,(CLPTR)          ; bounds check
                ld      de,TXTMAX
                or      a
                sbc     hl,de
                jp      nc,dpl_oom_pop
                call    fat_io_getbyte
                jp      c,dpl_err_pop
                ld      hl,(CLPTR)
                ld      (hl),a
                inc     hl
                ld      (CLPTR),hl
                pop     de                  ; DE = remaining count
                dec     de
                jr      dpl_body

; dpl_link_err — the second fat_io_getbyte (link high) returned EOF; AF (link-low)
; is on the stack from the push before that call.  Pop it to restore balance, then
; fall through to dpl_err (close file + error path).
dpl_link_err:
                pop     af
                jp      dpl_err

; dpl_err_pop / dpl_oom_pop — drop the stacked body length / remaining count, then
; take the file-closing error / out-of-memory path (stack stays balanced).
dpl_err_pop:
                pop     de
                jp      dpl_err
dpl_oom_pop:
                pop     de
                jp      dpl_oom

dpl_done:
                ; (program fully read; no Close — the read side has no dirty state.)
                ; --- write the $0000 end-of-program marker and set PRGEND ---
                ld      hl,(CLPTR)
                ld      (PRGEND),hl         ; end marker sits at the store cursor
                ld      (hl),0
                inc     hl
                ld      (hl),0
                ; keep the TXTTAB sysvar consistent with the program base
                ld      hl,TXTBASE
                ld      (TXTTAB),hl
                ; --- relink: recompute every line's absolute link pointer ---
                call    relink
                ret

; dpl_err — take the normal error path. Reached on an unexpected EOF mid-program,
; a wrong marker, or an Open after the file vanished. (No Close: read side has no
; dirty state.)
dpl_err:
                jp      load_error

; dpl_oom — store overflow: leave a clean (empty) program, report "out of memory".
; Mirrors ctp_oom for the disk store-overflow case. (No Close: read side is clean.)
dpl_oom:
                call    new_prog            ; leave a clean (empty) program
                ld      a,$CC               ; out-of-memory landmark (as store_line)
                ld      (ERRMARK),a
                ld      hl,err_prog_mem
                jp      print_string

; --- ascii_load — LOAD of an ASCII (SAVE",A") program ------------------------
; Reached from disk_prog_load when the first byte is NOT the $FF tokenised marker.
; LOAD replaces the current program (unlike MERGE, which keeps it): clear it,
; re-open the stream from offset 0 (the marker probe consumed byte 0), then
; tokenise + store each line via the shared MERGE reader (ascii_read_lines,
; files.asm). Returns to disk_prog_load's caller, which honours ,R (RUNFLAG) /
; the implicit RUN"name" exactly as the tokenised path's `ret` does. A file that
; is not line-numbered ASCII (e.g. a BSAVE binary mis-routed here) trips the
; reader's non-numbered-line guard -> load_error. Clean-room: public ASCII format,
; no reference ROM read. See basic/docs/spec-ascii-saveload.md §4.
ascii_load:
                call    new_prog            ; LOAD replaces the current program
                call    fat_io_open         ; re-prime: reset the read to offset 0
                jp      c,load_error        ; file vanished between opens -> error
                call    ascii_read_lines    ; tokenise + store; CF set = bad line
                jp      c,load_error        ; non-numbered line / not an ASCII program
                ret                         ; caller handles ,R / returns to the REPL

; --- autoexec_run: cold-start AUTOEXEC.BAS auto-run (disk/docs/autoexec-bas-spec.md) ---
; Called once from interp.asm's `init`, between the startup banner (show_title)
; and the REPL (jp repl). Public spec (MSX2 Technical Handbook, Ch.3 MSX-DOS,
; boot procedure, an allowed source): "When MSX-DOS is not invoked and DISK-BASIC
; starts, if a BASIC program named AUTOEXEC.BAS exists, it will be carried out."
; Absent / empty -> silent, normal startup (black-box characterised on
; National_CF-3300; see disk/docs/autoexec-bas-spec.md §2).
;
; This is the do_run disk pattern (do_run, above) minus the command parser, plus
; a SILENT presence probe up front: disk_prog_load's own not-found path is the
; noisy load_error (right for a typed RUN"missing", wrong for a boot-time probe
; that must stay quiet on the common no-AUTOEXEC.BAS case). So we fat_mount +
; fat_find ourselves first and ret quietly on "no disk" / "not found" / "empty",
; only reaching disk_prog_load once a non-empty file is confirmed present.
autoexec_run:
                ; (1) no disk ROM recorded by the INIT scan -> silent skip (same
                ; gate disk_prog_load uses).
                ld      a,(DISKSLOT_OK)
                or      a
                ret     z
                ; (2) stage the upcased 11-byte 8.3 name at DISK_FCB_NAME.
                ld      hl,autoexec_name
                ld      de,DISK_FCB_NAME
                ld      bc,11
                ldir
                ; (3) silent presence probe: mount, then search the root dir.
                call    fat_mount
                ret     c                   ; no / bad disk -> silent skip
                ld      hl,DISK_FCB_NAME
                call    fat_find
                ret     c                   ; not found -> silent skip
                ; (4) empty file (size == 0, all 4 LE bytes) -> silent skip,
                ; matching stock's silent behaviour on a 0-byte AUTOEXEC.BAS.
                ld      hl,FAT_FILESIZE
                ld      a,(hl)
                inc     hl
                or      (hl)
                inc     hl
                or      (hl)
                inc     hl
                or      (hl)                ; Z iff size == 0 (all 4 bytes)
                ret     z
                ; (5) found & non-empty -> load the tokenised program, then RUN
                ; it (clear_vars + control-flow reset), and fall through to the
                ; caller's `jp repl`. disk_prog_load re-opens via fat_io_open
                ; (mount+find+prime again) -- cheap, reuses the whole loader; a
                ; load failure lands in disk_prog_load's load_error (prints +
                ; leaves an empty store), so the trailing run_prog is then a
                ; harmless no-op (error-then-Ok, per spec §3 point 5).
                call    disk_prog_load
                jp      run_prog

; --- autoexec_name: the upcased 11-byte 8.3 name we probe for on cold start ---
; "AUTOEXEC" (8) + "BAS" (3) = exactly 11 non-space characters -- no padding
; needed (see disk/docs/autoexec-bas-spec.md §3 point 2).
autoexec_name:  db      "AUTOEXECBAS"
