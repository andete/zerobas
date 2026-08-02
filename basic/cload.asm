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
; follow. Tier-3 (spec-cas-tier3-cload.md Item A): the name is now HONOURED — it
; is captured into CAS_WANT and cas_open_match finds the matching tape file
; (skipping earlier non-matching files), instead of blindly loading the next one.
; Bare CLOAD (no name) clears CAS_WANT_ON -> load-next, unchanged.
do_cload:
                xor     a
                ld      (CAS_VERIFY),a      ; default: a real load (not CLOAD?)
                call    skip_spaces
                ; Tier-3 Item B: `CLOAD?` is the VERIFY form. Our tokeniser maps
                ; '?' to PRINT (interp.asm), so `CLOAD?` tokenises to CLOAD_TOKEN
                ; + PRINT_TOKEN — detect that leading PRINT_TOKEN here.
                cp      PRINT_TOKEN         ; CLOAD? -> compare-mode verify
                jr      nz,dcl_name
                inc     hl                  ; past the '?' (PRINT_TOKEN)
                ld      a,1
                ld      (CAS_VERIFY),a      ; compare, do not store
                xor     a
                ld      (CAS_VMIS),a        ; fresh verify (no mismatch yet)
                call    skip_spaces
dcl_name:
                ; A = (hl); HL at the first argument char (name or terminator).
                or      a
                jr      z,dcl_noname        ; bare CLOAD / CLOAD? -> next tape file
                cp      COLON               ; CLOAD : ... -> bare form
                jr      z,dcl_noname
                cp      '"'                 ; CLOAD "name" -> capture the quoted name
                jp      nz,load_error
                inc     hl                  ; past the opening quote
                call    cas_capture_name    ; -> CAS_WANT + CAS_WANT_ON=1
                jp      do_tape_prog        ; (CLOAD has no ,R; trailing chars ignored)
dcl_noname:
                xor     a
                ld      (CAS_WANT_ON),a     ; no name -> load the next tape file
                jp      do_tape_prog

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
                xor     a
                ld      (CAS_VERIFY),a      ; LOAD is a real load, never CLOAD? verify
                call    skip_spaces
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
                ; HL is now inside the quotes, past "CAS:". Tier-3: CAPTURE the
                ; quoted filename into CAS_WANT (cas_open_match then finds the named
                ; tape file, case-sensitive per spec §A.5) and leave HL ON the
                ; closing quote so parse_close_run can consume it + an optional ,R
                ; (LOAD"CAS:x",R loads *and runs*; a junk flag is a clean Syntax
                ; error). Empty name (LOAD"CAS:") -> CAS_WANT_ON=0 = load next.
                call    cas_capture_name    ; -> CAS_WANT + CAS_WANT_ON; HL on '"'
dl_cas_close:
                call    parse_close_run     ; closing quote + optional ,R -> RUNFLAG
                jp      c,load_error
                call    do_tape_prog        ; load the tokenised program off tape
                ld      a,(RUNFLAG)          ; ,R ? -> run it; else back to the REPL
                or      a
                ret     z
                jp      run_prog

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
                xor     a
                ld      (CAS_VERIFY),a      ; RUN"CAS:" is a real load, never verify
                call    skip_spaces
                cp      '"'                 ; a quoted filename -> device load+run
                jp      nz,run_prog         ; bare RUN / RUN<lineno> -> run stored
                inc     hl                  ; past the opening quote
                ; device dispatch: "CAS:" -> tape, else -> disk (mirrors do_load).
                ; dev_cmp advances HL past a matched prefix and restores it on a miss,
                ; so the disk path below still sees HL at the filename start.
                ld      de,dev_cas
                call    dev_cmp
                jr      z,dr_is_cas         ; matched "CAS:" -> tape program run
                call    parse_disk_fcb      ; build DISK_FCB; HL -> closing '"'
                call    parse_close_run     ; consume closing quote (and any ,R)
                jp      c,load_error
                call    disk_prog_load      ; load the tokenised program into TXTBASE
                jp      run_prog            ; ...and run it (running is implicit)
dr_is_cas:
                ; HL is inside the quotes, past "CAS:". Tier-3: CAPTURE the quoted
                ; filename into CAS_WANT (cas_open_match finds the named tape file,
                ; case-sensitive) and leave HL ON the closing quote for
                ; parse_close_run, exactly like do_load's dl_is_cas.
                call    cas_capture_name    ; -> CAS_WANT + CAS_WANT_ON; HL on '"'
dr_cas_close:
                call    parse_close_run     ; closing quote (+ harmless ,R: run is implicit)
                jp      c,load_error
                call    do_tape_prog        ; load the program off tape (tokenised OR
                                            ; $EA ASCII — do_tape_prog's 3-way dispatch)
                jp      run_prog            ; ...and run it

; --- cas_capture_name: parse a quoted tape name into CAS_WANT -----------------
; Entry: HL -> the first char of the name (inside the quotes, past the opening
; '"' or the "CAS:" prefix). Copies up to 6 chars — CASE PRESERVED, the CF-3300
; compare is byte-exact (spec §A.5) — into CAS_WANT, space-padding to 6; sets
; CAS_WANT_ON = 1 iff at least one name char was present (else 0 = load next).
; Stops ON the closing '"' or a NUL terminator, leaving HL there for the caller's
; parse_close_run / trailing handling (chars beyond 6 are advanced-over, not
; stored, so HL still lands on the quote). Clobbers A, BC, DE, HL.
cas_capture_name:
                ld      de,CAS_WANT
                ld      b,6                 ; slots left in CAS_WANT
                ld      c,0                 ; chars copied so far
ccn_lp:
                ld      a,(hl)
                or      a
                jr      z,ccn_pad           ; NUL -> stop
                cp      '"'
                jr      z,ccn_pad           ; closing quote -> stop
                ld      a,b
                or      a
                jr      z,ccn_over          ; CAS_WANT full -> ignore extra name chars
                ld      a,(hl)
                ld      (de),a              ; store this name char (case preserved)
                inc     de
                dec     b
                inc     c
ccn_over:
                inc     hl
                jr      ccn_lp
ccn_pad:
                ld      a,b
                or      a
                jr      z,ccn_flag          ; no slots left -> nothing to pad
ccn_pad_lp:
                ld      a,' '               ; space-pad the remaining slots
                ld      (de),a
                inc     de
                dec     b
                jr      nz,ccn_pad_lp
ccn_flag:
                ld      a,c                 ; A = name-char count
                or      a
                jr      z,ccn_set           ; empty name -> store 0 (load next file)
                ld      a,1                 ; a name was given -> match it
ccn_set:
                ld      (CAS_WANT_ON),a
                ret

; --- cas_open_match: resident marshalling shim ------------------------------
; docs/spec-eviction-g5-space.md. The full name-match loop + cas_skip_data
; (com_next/com_hdr/com_cmp/csd_tok/csd_ascii/... -- basic/casmatch-body.inc)
; moved whole to sub/casmatch.asm (SUBROM_IDX_CASMATCH) to free page-1 tail
; space for the G5 PAINT slice. No register inputs to marshal -- the body
; already reads/writes only RAM (CAS_WANT*/CAS_HDRNAME/CAS_HDRID) and BIOS
; (TAPION/TAPIN), both visible from a page-1 tenant. This stub just
; subrom_calls the tenant and converts its CM_STATUS byte back to the
; existing CF-return convention (out: CF clear = matched, CAS_HDRID set / CF
; set = not found or tape error) -- all 3 call sites (do_tape_prog below,
; files.asm merge_cas/oo_dev_cas) are unchanged, they already just test CF.
cas_open_match:
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_CASMATCH
                call    subrom_call
                jp      c,subrom_absent_error
                ld      a,(CM_STATUS)
                or      a
                ret     z                   ; matched -> CF clear
                scf
                ret

; --- do_tape_prog: the shared cassette BASIC-program load path ----------------
; Finds the requested tape file (cas_open_match: name-matching per Tier-3, or the
; next file for the bare form), then dispatches on its file-type id: $D3 reads a
; tokenised program-area image line-by-line into TXTBASE and relinks it; $EA is an
; ASCII (SAVE"CAS:",A) program handed to cas_ascii_load. TAPIN trashes every
; register, so all state lives in RAM. CLOAD, LOAD"CAS:" and RUN"CAS:" all reach
; here, so all three accept either format and honour the filename transparently.
do_tape_prog:
                call    cas_open_match      ; find the (named) file; header consumed
                jp      c,load_error        ; not found / tape error
                ld      a,(CAS_HDRID)
                cp      BASIC_ID            ; tokenised BASIC -> the store/compare loop
                jr      z,ctp_data_tokenised
                cp      ASCII_ID            ; ASCII program -> cas_ascii_load
                jp      nz,load_error       ; neither id -> unrecognised file
                ; $EA ASCII: CLOAD? verify is tokenised-only (spec §B) -> reject
                ld      a,(CAS_VERIFY)
                or      a
                jp      nz,load_error
                jp      cas_ascii_load
ctp_data_tokenised:
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

                ; store (load) OR compare (CLOAD? verify) the saved link word via
                ; cas_put — one mode-flagged emit point (relink fixes links later).
                ld      a,c
                call    cas_put
                ld      a,b
                call    cas_put

                ; line number (2 bytes)
                call    TAPIN
                jp      c,ctp_err_pop
                call    cas_put
                call    TAPIN
                jp      c,ctp_err_pop
                call    cas_put
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
                call    cas_put             ; store or compare the body byte
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
                ld      a,(CAS_VERIFY)
                or      a
                jr      nz,ctp_verify_done  ; CLOAD? -> report, do NOT mutate memory

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

; --- ctp_verify_done: CLOAD? end-of-tape -> report Ok / Verify error ----------
; Verify is NON-DESTRUCTIVE: no marker, no PRGEND, no relink — CAS_VMIS holds the
; verdict. A clean CAS_VMIS = identical (silent Ok); otherwise "Verify error".
; Any real difference (including nearly all length changes — the saved link words
; are absolute addresses, so a different program layout differs byte-for-byte and
; trips CAS_VMIS during the body compare) is caught. The one gap is a tape that is
; an EXACT PREFIX of a longer in-memory program (all compared bytes equal, tape
; ends early); that is outside the verify use case (confirming a same-length
; CSAVE round-trip) and is a documented limitation (spec §B).
ctp_verify_done:
                ld      a,(CAS_VMIS)
                or      a
                ret     z                   ; no difference -> Ok (memory intact)
                jp      verify_error        ; a byte differed -> "Verify error"

ctp_oom:
                call    TAPIOF              ; stop the motor before reporting
                ld      a,(CAS_VERIFY)
                or      a
                jp      nz,verify_error     ; CLOAD? overrun = mismatch, do NOT wipe
                call    new_prog            ; leave a clean (empty) program
                ld      a,$CC               ; out-of-memory landmark (as store_line)
                ld      (ERRMARK),a
                ld      hl,err_prog_mem
                jp      print_msg           ; D-MSGENC: err_prog_mem aliases err_mem,
err_prog_mem    equ     err_mem             ; repack: share sl_oom's "out of memory"
                                            ; (program.asm) — identical bytes. Part of
                                            ; D-2's self-funding string dedup (S1).

; --- cas_put: store-or-compare one program byte at CLPTR, advance CLPTR --------
; The single mode-flagged emit point of the tokenised tape reader (spec §B).
; CAS_VERIFY=0 (a real CLOAD/LOAD"CAS:"/RUN"CAS:") -> store A at CLPTR (plain
; load). CAS_VERIFY=1 (CLOAD?) -> COMPARE A against the in-memory program byte at
; CLPTR and set the sticky CAS_VMIS on any difference, WITHOUT writing (verify is
; non-destructive). CLPTR advances TXTBASE.. either way, so in verify mode it is
; exactly the in-memory comparand cursor. Preserves BC, DE; clobbers A, HL, flags.
;   in: A = the program byte just read from tape.
; Clobbers A, C, HL (BC is dead at every call site — the link bytes are stored
; before the next TAPIN, and TAPIN then trashes BC anyway).
cas_put:
                ld      c,a                 ; C = the byte
                ld      hl,(CLPTR)
                ld      a,(CAS_VERIFY)
                or      a
                ld      a,c                 ; A = the byte back
                jr      nz,cput_cmp
                ld      (hl),a              ; load mode: store the byte
                jr      cput_adv
cput_cmp:
                cp      (hl)                ; verify: compare vs the in-memory byte
                jr      z,cput_adv
                ld      a,1
                ld      (CAS_VMIS),a        ; mismatch -> sticky
cput_adv:
                inc     hl
                ld      (CLPTR),hl
                ret

; --- verify_error: report a CLOAD? mismatch (memory left untouched) -----------
verify_error:
                ld      hl,err_verify
                jp      print_msg                       ; D-MSGENC
err_verify:     db      "Verify",MSGESC_ERROR,0         ; 15 B -> 8 B

; --- cas_ascii_load: LOAD of an ASCII (SAVE"CAS:",A) cassette program --------
; Reached from do_tape_prog's header dispatch when byte 0 is $EA (ASCII)
; instead of $D3 (tokenised). Mirrors disk ascii_load (files.asm): LOAD
; replaces the current program (new_prog), then the file is tokenised + stored
; line-by-line by the shared MERGE reader (ascii_read_lines, files.asm) — the
; same path disk ASCII LOAD/MERGE use. The only cassette-specific part is the
; byte SOURCE: ascii_read_lines is re-pointed (D2 getbyte indirection,
; ARL_GETBYTE) at cal_getbyte (below), a TAPIN wrapper, instead of the default
; fat_io_getbyte — restored again before returning so a later MERGE/disk LOAD
; is unaffected.
;
; Entry: cas_open_match has already consumed the FULL 16-byte header (10x $EA +
; 6-char name) and matched the requested name; cas_ascii_setup then primes data
; block 1. (Pre-Tier-3 this routine skipped the 15 trailing header bytes itself.)
;
; BLOCK-BUFFERED byte source (D2 refinement, see spec §4): TAPIN is a REAL-TIME
; read — the tape keeps moving whether or not the CPU polls — so tokenising
; BETWEEN two TAPINs desyncs the next byte. ascii_read_lines does a full
; dispatch_line/tokenise/store_line per line, far more than enough to desync (a
; 34-byte file corrupted after line 1 in an unbuffered first cut). So cal_getbyte
; serves bytes instantly from the 256-byte CAL_BUF, refilled (cal_refill) by a
; tight TAPIN*256 loop only at a block boundary — exactly how real MSX slurps a
; block then tokenises during the inter-block leader gap. Symmetric with
; fat_io_getbyte serving from the 512-byte FSECTOR_BUF on disk.
;
; TWO HARD REQUIREMENTS ON cal_refill, both learned the hard way:
;  (1) STATE LIVES IN RAM, NOT ON THE STACK, ACROSS TAPIN. TAPIN clobbers every
;      register AND does not preserve a caller value pushed on the stack across
;      it — a `push hl`/`pop hl` of the buffer pointer around TAPIN reads back the
;      whole block as $00 (confirmed: the exact same tokenised block ctp_body
;      reads byte-perfect came back all-zero through a stack-guarded loop). So the
;      fill keeps its position in CAL_CNT (RAM) and recomputes the address each
;      byte — the same "state in RAM across a BIOS tape call" discipline
;      do_tape_prog's ctp_body uses (it guards CLPTR in RAM, not the stack).
;  (2) THE DATA-BLOCK TAPION MUST BE PROMPT. Deferring it past new_prog + the
;      ascii-reader entry makes it miss the block leader and fail to relock. So
;      block 1 is primed HERE, right after the header skip, in the same
;      back-to-back regime as do_tape_prog. cal_getbyte then TAPIONs only blocks
;      2+, the safe mid-tape re-lock the 256-byte format is built around.
;
; CAL_NEEDFILL=0 means "CAL_BUF holds a live block"; cal_getbyte sets it on each
; 256-byte wrap so the NEXT call refills. ascii_read_lines stops at the first
; Ctrl-Z ($1A) — which every producer puts in the LAST real block (§0.1) — so we
; never refill past the program (a TAPIN fail on a non-existent block is never
; reached on a well-formed tape). `,R`/RUN is unchanged — the caller (do_load's
; LOAD"CAS:",R / do_cload) applies RUNFLAG exactly as the tokenised path's `ret`.
cas_ascii_load:
                call    cas_ascii_setup     ; skip the rest of the header + prime block 1
                jp      c,load_error        ; header / block-1 unreadable -> load error
                call    new_prog            ; LOAD replaces the current program
                call    cas_ascii_drive     ; read+tokenise+store via the tape source
                jp      c,load_error        ; non-numbered line -> abort
                ret                         ; caller handles ,R / returns to the REPL

; --- cas_ascii_setup: prime data block 1 of an $EA cassette file --------------
; The whole 16-byte header (id + name) is now consumed upstream by cas_open_match
; (Tier-3 name-matching), so this only PRIMES the first data block. Shared by
; cas_ascii_load (LOAD), merge_cas and oo_dev_cas (all of which reach it via
; cas_open_match). Leaves CAL_BUF holding a live block, CAL_NEEDFILL=0, CAL_CNT=0.
;   out: CF set = data block 1 read failed.
cas_ascii_setup:
                ; prime block 1 PROMPTLY (TAPION + fill, back-to-back) so the
                ; data-block TAPION stays in the same regime as do_tape_prog's.
                call    cal_refill          ; data block 1 leader + slurp 256 bytes
                ret     c                   ; block 1 unreadable -> CF
                xor     a
                ld      (CAL_NEEDFILL),a    ; CAL_BUF now holds a live block (CAL_CNT=0)
                ret

; --- cas_ascii_drive: run ascii_read_lines off the tape byte source, then restore
; the default (disk) source and stop the motor. Shared by cas_ascii_load (LOAD) and
; merge_cas (MERGE"CAS:"). The getbyte indirection (ARL_GETBYTE) is pointed at
; cal_getbyte for the read and put back to fat_io_getbyte afterwards so a later
; MERGE / disk LOAD is unaffected.
;   out: CF from ascii_read_lines (set = a non-blank, non-numbered line).
cas_ascii_drive:
                ld      hl,cal_getbyte
                ld      (ARL_GETBYTE),hl
                call    ascii_read_lines    ; tokenise + store; CF set = bad line
                push    af                  ; preserve the ascii_read_lines result CF
                ld      hl,fat_io_getbyte
                ld      (ARL_GETBYTE),hl
                call    TAPIOF              ; motor off (file fully read), as ctp_done
                pop     af
                ret

; --- cal_getbyte: cassette ASCII-load byte source (D2 indirection target) ----
; Serves the next byte from CAL_BUF at position CAL_CNT (0..255) instantly — NO
; tape I/O — so the tokenise/store work ascii_read_lines does between calls is
; harmless. When the previous call drained the block (position wrapped 255->0),
; CAL_NEEDFILL is set and this call first TAPION-relocks + slurps the next block
; (cal_refill) before serving. CAL_BUF is page-aligned ($E600), so the byte
; address is high=$E6 / low=CAL_CNT.
;   out: A = byte, CF clear; or CF set = no more data (refill failed).
cal_getbyte:
                ld      a,(CAL_NEEDFILL)
                or      a
                jr      z,cal_serve         ; buffer still has bytes -> serve
                call    cal_refill          ; drained -> slurp the next block
                ret     c                   ; block missing / read fail -> EOF
                xor     a
                ld      (CAL_NEEDFILL),a    ; fresh block loaded (CAL_CNT = 0)
cal_serve:
                ld      a,(CAL_CNT)
                ld      l,a
                ld      h,CAL_BUF >> 8      ; HL = CAL_BUF + CAL_CNT (page-aligned)
                ld      a,(hl)              ; A = the byte to return
                ld      b,a                 ; save it across the counter bump
                ld      a,l
                inc     a                   ; advance position; 255 -> 0 wraps (8-bit)
                ld      (CAL_CNT),a
                jr      nz,cal_srv_ret      ; still within the block -> done
                ld      a,1
                ld      (CAL_NEEDFILL),a    ; block exhausted -> next call refills
cal_srv_ret:
                ld      a,b
                or      a                   ; CF clear = byte valid
                ret

; --- cas_in_getbyte: OPEN"CAS:" FOR INPUT byte source (ARL_GETBYTE target) ----
; Wraps cal_getbyte with the sequential-file EOF rule: a Ctrl-Z ($1A) in the data
; is end-of-file (§0.1 / MSX2 TH — the same soft-EOF that ends an ASCII program,
; but here INPUT#/LINE INPUT# must STOP on it rather than treat it as a data byte,
; since a data file has no line structure). Returns CF on either a real refill
; failure (cal_getbyte CF) or the Ctrl-Z. read_into_strscr (via arl_getbyte) then
; ends the field/line exactly as it does on a disk fat_io_getbyte EOF.
;   out: A = byte, CF clear; or CF set = end of file.
cas_in_getbyte:
                call    cal_getbyte
                ret     c                   ; source EOF (refill failed)
                cp      $1A
                jr      z,cig_eof           ; Ctrl-Z -> end of file
                or      a                   ; CF clear = valid byte (A = the byte)
                ret
cig_eof:
                scf
                ret

; cal_refill: shared verbatim via basic/cal-refill-body.inc so the sub-ROM
; casmatch tenant's own duplicate (needed because cas_skip_data's csd_ascii
; arm moved sub-side, docs/spec-eviction-g5-space.md) can never drift from
; this resident copy (still used here by cal_getbyte/ascii_read_lines).
                include "basic/cal-refill-body.inc"

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
                jp      print_msg           ; D-MSGENC (as ctp_oom above)

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
