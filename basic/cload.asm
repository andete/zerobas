; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause

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

; --- do_load: LOAD "CAS:filename" --------------------------------------------
; Entry: HL -> the bytes after the LOAD token. The argument must be a quoted
; string beginning with the device name "CAS:"; any trailing filename inside the
; quotes is parsed-past and ignored.
do_load:
                call    skip_spaces
                ld      a,(hl)
                cp      '"'                 ; opening quote required
                jp      nz,load_error
                inc     hl
                ld      de,dev_cas          ; compare device name to "CAS:"
do_load_dev:
                ld      a,(de)
                or      a
                jr      z,do_load_dev_end   ; matched all of "CAS:"
                ld      c,a                 ; expected (uppercase) char
                ld      a,(hl)              ; typed char
                call    upcase              ; case-insensitive (typed may be lower)
                cp      c
                jp      nz,load_error       ; unsupported device
                inc     hl
                inc     de
                jr      do_load_dev
do_load_dev_end:
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

                ; --- read the program image, stopping at the $0000 end-link --
                ; The device half does NOT signal a clean end of data: once the
                ; tape block's bytes run out, TAPIN blocks on silence rather than
                ; returning CF. So we must stop reading EXACTLY when the program
                ; ends — at the $0000 link word that terminates the line-link
                ; chain — never reading a byte past it.
                ;
                ; Per line: read the 2-byte link word; $0000 -> end of program.
                ; Otherwise store the line verbatim — link word, 2-byte line
                ; number, then the token body up to and including its $00 — and
                ; loop. The saved links are stored as-is (relink recomputes them
                ; below), so the only thing we interpret from the stream is the
                ; per-line $00 terminator and the terminating $0000 link.
ctp_line:
                call    TAPIN               ; link low
                jp      c,load_error
                ld      c,a
                call    TAPIN               ; link high
                jp      c,load_error
                ld      b,a                 ; BC = saved link word
                ld      a,b
                or      c
                jr      z,ctp_done          ; $0000 link -> program complete

                ; bounds: this line's header (>=4 bytes) must fit below TXTMAX
                ld      hl,(CLPTR)
                ld      de,TXTMAX-4
                or      a
                sbc     hl,de
                jp      nc,ctp_oom

                ; store the (saved) link word verbatim; relink fixes it later
                ld      hl,(CLPTR)
                ld      (hl),c
                inc     hl
                ld      (hl),b
                inc     hl
                ld      (CLPTR),hl

                ; line number (2 bytes)
                call    TAPIN
                jp      c,load_error
                ld      hl,(CLPTR)
                ld      (hl),a
                inc     hl
                ld      (CLPTR),hl
                call    TAPIN
                jp      c,load_error
                ld      hl,(CLPTR)
                ld      (hl),a
                inc     hl
                ld      (CLPTR),hl

                ; token body: read + store until the $00 terminator (inclusive)
ctp_body:
                call    TAPIN
                jp      c,load_error
                ld      c,a                 ; guard the byte (TAPIN trashes all regs)
                ld      hl,(CLPTR)          ; bounds check
                ld      de,TXTMAX
                or      a
                sbc     hl,de
                jp      nc,ctp_oom
                ld      hl,(CLPTR)
                ld      a,c
                ld      (hl),a
                inc     hl
                ld      (CLPTR),hl
                or      a                   ; line's $00 terminator?
                jr      nz,ctp_body
                jr      ctp_line            ; next line

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
