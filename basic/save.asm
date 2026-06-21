; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause

; save.asm — BSAVE / SAVE / CSAVE statement handlers (disk + cassette write).
;
; The WRITE mirror of bload.asm / cload.asm. Implements three verbs:
;
;   BSAVE "A:F",start,end[,exec]    -> disk binary: [$FE][start][end][exec] + data.
;   BSAVE "CAS:F",start,end[,exec]  -> tape binary: 10x$D0 + 6-char name (header
;                                       block); then start/end/exec + data (data block).
;   SAVE "A:F"                       -> disk tokenised: [$FF] + program image.
;   SAVE "CAS:F"                     -> tape tokenised: 10x$D3 + 6-char name (header
;                                       block); then program image (data block).
;   CSAVE "F"                        -> tape tokenised (same as SAVE"CAS:F").
;
; All tape writes use the TAPOON/TAPOUT/TAPOOF BIOS entry points at $00EA/$00ED/$00F0
; (zerobas-tape; sysvars.inc). TAPOUT CLOBBERS EVERY REGISTER: every loop counter
; and pointer must survive TAPOUT calls via RAM (TSV_PTR/TSV_END/TSV_CNT in page $E0).
;
; Cassette file format: two logical blocks per file (MSX2 TH cassette file format;
; cross-checked by cas_encode.py which mirrors what a real CSAVE writes):
;   Block 1 header: TAPOON(long) + 10x file-type-id + 6-char filename + TAPOOF.
;     file-type-id = $D3 (BASIC_ID) for tokenised (CSAVE / SAVE"CAS:").
;     file-type-id = $D0 (BINARY_ID) for binary (BSAVE"CAS:").
;   Block 2 data: TAPOON(short) + payload + TAPOOF.
;     Tokenised payload = program image TXTBASE..PRGEND+1 (same line-link image
;     the disk SAVE writes after its $FF marker; NO $FE/$FF disk markers on tape).
;     Binary payload = start(LE) + end(LE) + exec(LE) + RAM[start..end inclusive].
;
; Disk-path format (unchanged from the original implementation):
;   BSAVE disk: [$FE][start:2 LE][end:2 LE][exec:2 LE] then raw data.
;   SAVE  disk: [$FF] then the line-link program image.
;
; The ,A ASCII-save form is OUT OF SCOPE (load_error), matching the original.
;
; CLEAN-ROOM: cassette format sourced from MSX2 Technical Handbook cassette chapter
; (same allowed source as BINARY_ID/BASIC_ID constants already in sysvars.inc);
; cross-checked by cas_encode.py (our own code). Disk format unchanged. CSAVE token
; oracle-LOCKED ($9A, basic_probe_crunch.py). TAPOON/TAPOUT/TAPOOF contracts from
; tape/tape.asm (our own code). No disassembly. See basic/PROVENANCE.md.

; ===========================================================================
; do_bsave — BSAVE "device:name",start,end[,exec]
; Entry: HL -> the bytes after the BSAVE token (verbatim ASCII filename, then the
; crunched address args: comma + &H/decimal expression each).
do_bsave:
                call    skip_spaces
                ld      a,(hl)
                cp      '"'                 ; opening quote required
                jp      nz,load_error
                inc     hl
                ; --- device dispatch: "CAS:" -> tape, else -> disk ----------
                push    hl                  ; remember filename start
                ld      de,dev_cas
bsv_dev:
                ld      a,(de)
                or      a
                jr      z,bsv_is_cas        ; matched all of "CAS:" -> tape
                ld      c,a
                ld      a,(hl)
                call    upcase
                cp      c
                jr      nz,bsv_is_disk      ; prefix mismatch -> disk
                inc     hl
                inc     de
                jr      bsv_dev
bsv_is_disk:
                pop     hl                  ; restore filename start
                ; HL = filename start (after the quote); build the FCB.
                call    parse_disk_fcb      ; build DISK_FCB; HL -> closing '"'
                ld      a,(hl)
                cp      '"'                 ; consume the closing quote
                jp      nz,load_error
                inc     hl
                ; --- ,start ------------------------------------------------
                call    expect_comma_eval   ; DE = start, HL advanced
                ld      (CURPTR),de         ; CURPTR = start (the source walk cursor)
                ld      (EXECPTR),de        ; default exec = start (overridden if ,exec)
                ; --- ,end --------------------------------------------------
                call    expect_comma_eval   ; DE = end
                ld      (DSV_END),de        ; DSV_END = last data byte (inclusive)
                ; --- optional ,exec ----------------------------------------
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      nz,bsv_open         ; no ,exec -> exec already defaulted to start
                inc     hl                  ; past the comma
                call    eval                ; DE = exec
                ld      (EXECPTR),de
bsv_open:
                ; --- create the file and set the DTA -----------------------
                call    disk_write_begin    ; require DISKSLOT_OK; Set-DTA; Create
                ; --- 7-byte header: $FE start(LE) end(LE) exec(LE) ----------
                ; disk_putbyte clobbers ALL registers (its CALSLT may flush a
                ; record), so each 16-bit field is emitted via disk_putword, which
                ; reloads the word from its RAM home for the high byte rather than
                ; trusting a register across the call.
                ld      a,BSAVE_DISK_ID     ; $FE
                call    disk_putbyte
                ld      hl,CURPTR           ; start (LE)
                call    disk_putword
                ld      hl,DSV_END          ; end (LE)
                call    disk_putword
                ld      hl,EXECPTR          ; exec (LE)
                call    disk_putword
                ; --- data bytes RAM[start..end] inclusive ------------------
bsv_data:
                ld      hl,(CURPTR)
                ld      a,(hl)              ; the source byte
                call    disk_putbyte
                ld      hl,(CURPTR)
                ld      de,(DSV_END)
                ld      a,h
                cp      d
                jr      nz,bsv_next         ; high bytes differ -> more to do
                ld      a,l
                cp      e
                jr      z,bsv_fin           ; cur == end -> last byte written
bsv_next:
                ld      hl,(CURPTR)
                inc     hl
                ld      (CURPTR),hl
                jr      bsv_data
bsv_fin:
                jp      disk_write_end      ; flush + Close + back to the prompt

; --- tape BSAVE path ---
bsv_is_cas:
                pop     af                  ; discard saved filename start (HL past "CAS:")
                ; HL now points just past "CAS:" inside the quotes.
                ; Parse filename: up to 6 chars until '"', space-pad to 6.
                call    tape_parse_name     ; fills TSV_NAME[0..5]; HL -> closing '"'
                ld      a,(hl)
                cp      '"'
                jp      nz,load_error
                inc     hl                  ; past closing '"'
                ; --- ,start ------------------------------------------------
                call    expect_comma_eval   ; DE = start
                ld      (CURPTR),de
                ld      (EXECPTR),de        ; default exec = start
                ; --- ,end --------------------------------------------------
                call    expect_comma_eval   ; DE = end
                ld      (TSV_END),de
                ; --- optional ,exec ----------------------------------------
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      nz,bsv_cas_open
                inc     hl
                call    eval                ; DE = exec
                ld      (EXECPTR),de
bsv_cas_open:
                ; --- tape header block: TAPOON(long) + 10x$D0 + 6-char name + TAPOOF ---
                ld      a,$FF               ; non-zero -> long header
                call    TAPOON
                jp      c,load_error
                ; emit 10x BINARY_ID ($D0)
                ld      a,10
                ld      (TSV_CNT),a
bsv_cas_id:
                ld      a,BINARY_ID         ; $D0
                call    TAPOUT
                jp      c,load_error
                ld      a,(TSV_CNT)
                dec     a
                ld      (TSV_CNT),a
                jr      nz,bsv_cas_id
                ; emit 6-char name from TSV_NAME
                call    tape_name_emit
                jp      c,load_error
                call    TAPOOF              ; end of header block
                ; --- tape data block: TAPOON(short) + start/end/exec + data + TAPOOF ---
                xor     a                   ; zero -> short header
                call    TAPOON
                jp      c,load_error
                ; start (LE): low byte then high byte, each from CURPTR
                ld      hl,CURPTR
                call    tape_putword        ; emits (HL) then (HL+1)
                jp      c,load_error
                ; end (LE)
                ld      hl,TSV_END
                call    tape_putword
                jp      c,load_error
                ; exec (LE)
                ld      hl,EXECPTR
                call    tape_putword
                jp      c,load_error
                ; data bytes RAM[start..end] inclusive; CURPTR = start
bsv_cas_data:
                ld      hl,(CURPTR)
                ld      a,(hl)
                call    TAPOUT
                jp      c,load_error
                ld      hl,(CURPTR)
                ld      de,(TSV_END)
                ld      a,h
                cp      d
                jr      nz,bsv_cas_next
                ld      a,l
                cp      e
                jr      z,bsv_cas_fin       ; cur == end -> done
bsv_cas_next:
                ld      hl,(CURPTR)
                inc     hl
                ld      (CURPTR),hl
                jr      bsv_cas_data
bsv_cas_fin:
                call    TAPOOF              ; end of data block; motor off
                ret                         ; back to the REPL

; ===========================================================================
; do_save — SAVE "device:name"   (tokenised-BASIC save; ,A out of scope)
; Entry: HL -> the bytes after the SAVE token.
do_save:
                call    skip_spaces
                ld      a,(hl)
                cp      '"'                 ; opening quote required
                jp      nz,load_error
                inc     hl
                ; --- device dispatch: "CAS:" -> tape, else -> disk ----------
                push    hl                  ; remember filename start
                ld      de,dev_cas
sav_dev:
                ld      a,(de)
                or      a
                jr      z,sav_is_cas        ; matched all of "CAS:" -> tape
                ld      c,a
                ld      a,(hl)
                call    upcase
                cp      c
                jr      nz,sav_is_disk      ; prefix mismatch -> disk
                inc     hl
                inc     de
                jr      sav_dev
sav_is_disk:
                pop     hl                  ; restore filename start
                call    parse_disk_fcb      ; build DISK_FCB; HL -> closing '"'
                ld      a,(hl)
                cp      '"'                 ; consume the closing quote
                jp      nz,load_error
                inc     hl
                ; --- ,A ASCII-save form is OUT OF SCOPE (documented) --------
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jp      z,load_error        ; any SAVE"name",<flag> (incl. ,A) -> unsupported
                or      a
                jp      nz,load_error        ; trailing junk -> error
                ; --- create the file and set the DTA -----------------------
                call    disk_write_begin
                ; --- $FF tokenised-BASIC disk marker -----------------------
                ld      a,BASIC_DISK_ID     ; $FF
                call    disk_putbyte
                ; --- program image: TXTBASE .. PRGEND+1 inclusive ----------
                ; PRGEND points at the $0000 end-of-program marker (program.asm),
                ; so the last image byte is PRGEND+1. Walk inclusive.
                ld      hl,TXTBASE
                ld      (DSV_PTR),hl
                ld      hl,(PRGEND)
                inc     hl                  ; last image byte = PRGEND+1
                ld      (DSV_END),hl
sav_data:
                ld      hl,(DSV_PTR)
                ld      a,(hl)
                call    disk_putbyte
                ld      hl,(DSV_PTR)
                ld      de,(DSV_END)
                ld      a,h
                cp      d
                jr      nz,sav_next
                ld      a,l
                cp      e
                jr      z,sav_fin
sav_next:
                ld      hl,(DSV_PTR)
                inc     hl
                ld      (DSV_PTR),hl
                jr      sav_data
sav_fin:
                jp      disk_write_end

; --- tape SAVE path ---
sav_is_cas:
                pop     af                  ; discard saved filename start (HL past "CAS:")
                ; HL now points just past "CAS:" inside the quotes.
                ; Parse filename: up to 6 chars until '"', space-pad to 6.
                call    tape_parse_name     ; fills TSV_NAME; HL -> closing '"'
                ld      a,(hl)
                cp      '"'
                jp      nz,load_error
                inc     hl                  ; past closing '"'
                ; ,A is out of scope
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jp      z,load_error        ; SAVE"CAS:",A -> unsupported
                or      a
                jp      nz,load_error       ; trailing junk
                ; fall into shared tape tokenised-BASIC save
                jr      tape_save_basic

; ===========================================================================
; do_csave — CSAVE "name"  (tokenised-BASIC save to cassette)
; Entry: HL -> the bytes after the CSAVE token.
; The device is implicitly cassette (no "CAS:" prefix). The optional quoted
; name is parsed; a bare CSAVE (no name) uses a 6-space name.
do_csave:
                call    skip_spaces
                ld      a,(hl)
                or      a
                jr      z,csav_noname       ; bare CSAVE (no name)
                cp      COLON
                jr      z,csav_noname       ; CSAVE followed by : -> no name
                cp      '"'
                jp      nz,load_error       ; must be a quoted name
                inc     hl                  ; past opening '"'
                call    tape_parse_name     ; fills TSV_NAME; HL -> closing '"'
                ld      a,(hl)
                cp      '"'
                jp      nz,load_error
                inc     hl                  ; past closing '"'
                jr      tape_save_basic
csav_noname:
                ; no name given: fill TSV_NAME with 6 spaces
                ld      hl,TSV_NAME
                ld      b,6
csav_sp:
                ld      (hl),' '
                inc     hl
                djnz    csav_sp
                ; fall into tape_save_basic

; ===========================================================================
; tape_save_basic — shared cassette tokenised-BASIC save path.
; Writes a two-block cassette file: header block ($D3 ×10 + 6-char name in
; TSV_NAME) then data block (program image TXTBASE..PRGEND+1 inclusive).
; Reaches here with TSV_NAME already filled and HL past the opening quote.
; Clobbers everything (TAPOUT does); no return value (jumps to load_error on
; TAPOON/TAPOUT failure, else returns to the REPL).
; Format source: MSX2 TH cassette chapter; cas_encode.py build_cas_basic().
tape_save_basic:
                ; --- header block: TAPOON(long) + 10x$D3 + 6-char name + TAPOOF ---
                ld      a,$FF               ; non-zero -> long leader
                call    TAPOON
                jp      c,load_error
                ; emit 10x BASIC_ID ($D3)
                ld      a,10
                ld      (TSV_CNT),a
tsb_id:
                ld      a,BASIC_ID          ; $D3
                call    TAPOUT
                jp      c,load_error
                ld      a,(TSV_CNT)
                dec     a
                ld      (TSV_CNT),a
                jr      nz,tsb_id
                ; emit 6-char name
                call    tape_name_emit
                jp      c,load_error
                call    TAPOOF              ; end of header block
                ; --- data block: TAPOON(short) + program image + TAPOOF ------
                xor     a                   ; zero -> short leader
                call    TAPOON
                jp      c,load_error
                ; Set up the image walk: TSV_PTR = TXTBASE, TSV_END = PRGEND+1
                ld      hl,TXTBASE
                ld      (TSV_PTR),hl
                ld      hl,(PRGEND)
                inc     hl
                ld      (TSV_END),hl
tsb_data:
                ld      hl,(TSV_PTR)
                ld      a,(hl)
                call    TAPOUT
                jp      c,load_error
                ld      hl,(TSV_PTR)
                ld      de,(TSV_END)
                ld      a,h
                cp      d
                jr      nz,tsb_next
                ld      a,l
                cp      e
                jr      z,tsb_fin           ; cur == end -> done
tsb_next:
                ld      hl,(TSV_PTR)
                inc     hl
                ld      (TSV_PTR),hl
                jr      tsb_data
tsb_fin:
                call    TAPOOF              ; end of data block; motor off
                ret                         ; back to the REPL

; ===========================================================================
; tape_parse_name — extract up to 6 filename chars from the token stream.
; in:  HL -> first char of filename, inside an open quote.
; out: TSV_NAME[0..5] = up to 6 chars, space-padded; HL -> the closing '"'
;      (or at a NUL if the string is unterminated — caller checks for '"').
; Clobbers A, B, DE.
tape_parse_name:
                ld      de,TSV_NAME
                ld      b,6
tpn_loop:
                ld      a,(hl)
                or      a
                jr      z,tpn_pad           ; end of line -> pad remaining
                cp      '"'
                jr      z,tpn_pad           ; closing quote -> pad remaining
                ld      (de),a
                inc     hl
                inc     de
                djnz    tpn_loop
                ; 6 chars consumed; skip the rest of the filename to the closing '"'
tpn_skip:
                ld      a,(hl)
                or      a
                ret     z                   ; unterminated string -> stop (caller checks)
                cp      '"'
                ret     z                   ; closing quote found
                inc     hl
                jr      tpn_skip
tpn_pad:
                ; HL is on '"' or NUL; fill remaining TSV_NAME slots with ' '
                ld      a,b
                or      a
                ret     z                   ; nothing to pad
tpn_fill:
                ld      a,' '
                ld      (de),a
                inc     de
                djnz    tpn_fill
                ret

; ===========================================================================
; tape_name_emit — emit the 6 bytes of TSV_NAME via TAPOUT.
; in:  TSV_NAME[0..5] = the name to emit.
; out: CF = set if TAPOUT reported an error; else CF = clear.
; TAPOUT clobbers every register; the loop counter is kept in TSV_CNT.
tape_name_emit:
                ld      a,6
                ld      (TSV_CNT),a
                ld      hl,TSV_NAME
                ld      (TSV_PTR),hl        ; reuse TSV_PTR as walk pointer
tne_loop:
                ld      hl,(TSV_PTR)
                ld      a,(hl)
                call    TAPOUT
                ret     c                   ; propagate error
                ld      hl,(TSV_PTR)
                inc     hl
                ld      (TSV_PTR),hl
                ld      a,(TSV_CNT)
                dec     a
                ld      (TSV_CNT),a
                jr      nz,tne_loop
                or      a                   ; CF = 0 (success)
                ret

; ===========================================================================
; tape_putword — emit a 16-bit little-endian word stored at address HL via
; TAPOUT (low byte then high byte). TAPOUT clobbers every register, so the
; source address is held in TSV_PTR and reloaded for the high byte.
;   in:  HL = address of a 2-byte LE word in page-3 RAM.
;   out: CF set = error; both bytes emitted on success.
tape_putword:
                ld      (TSV_PTR),hl        ; save the word's address
                ld      a,(hl)              ; low byte
                call    TAPOUT
                ret     c
                ld      hl,(TSV_PTR)        ; reload (TAPOUT clobbered HL)
                inc     hl
                ld      a,(hl)              ; high byte
                call    TAPOUT
                ret                         ; CF from TAPOUT

; ===========================================================================
; expect_comma_eval — skip spaces, require a ',', then eval the following
; expression. DE = value, HL advanced. On a missing comma, jumps to load_error.
expect_comma_eval:
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jp      nz,load_error
                inc     hl                  ; past the comma
                call    eval                ; DE = value, HL advanced (BC clobbered)
                ret

; ===========================================================================
; Shared disk-write helper (the WRITE analogue of the read side's fat_io_open /
; fat_io_getbyte). Built on the loader-side FAT12 engine over the STANDARD $4010
; DSKIO entry (basic/fat.asm) — disk-ROM-independent, NOT the private bdos_entry.
; disk_write_begin creates a fresh file; disk_putbyte appends one byte (the engine
; buffers it into a 512-byte sector and flushes whole sectors as they fill);
; disk_write_end flushes the partial final sector and stamps the directory size.
; The engine tracks exact byte counts, so the on-disk file size is its true length
; (no 128-byte record zero-padding) — SAVE/BSAVE produce byte-exact images.

; disk_write_begin — require a recorded disk-ROM slot, then Create (truncate-or-
; make) the file named in DISK_FCB_NAME and arm the sequential-write iterator.
; On any failure jumps to load_error (does not return).
;
; DOCUMENTED DIVERGENCE (no write rollback): fat_io_create stamps the directory
; entry up front. If a later disk_putbyte/disk_write_end fails mid-stream (disk
; full / write error), the error path jumps to load_error WITHOUT fat_io_close, so
; the entry is left with an un-stamped size/first-cluster (a zero-length or partial
; file). Acceptable for a game loader — a failed SAVE simply needs re-issuing — and
; no caller depends on atomic write; surfaced here so it is not mistaken for a bug.
disk_write_begin:
                ld      a,(DISKSLOT_OK)
                or      a
                jp      z,load_error
                call    fat_io_create       ; mount + dir-create + reset write state
                jp      c,load_error        ; disk full / dir full / write protect / I-O
                ret

; disk_putword — write the 16-bit little-endian word stored at RAM address HL out
; through disk_putbyte (low byte then high byte). disk_putbyte clobbers HL (and
; everything else), so the source address is kept in a RAM slot (DSV_PTR, which is
; otherwise only used by do_save's own loop and is free during the BSAVE header)
; and reloaded for the high byte rather than trusted in a register.
;   in:  HL = address of a 2-byte LE word in page-3 RAM.
;   out: both bytes appended to the write stream. Clobbers all (via disk_putbyte).
disk_putword:
                ld      (DSV_PTR),hl        ; remember the word's address
                ld      a,(hl)              ; low byte
                call    disk_putbyte
                ld      hl,(DSV_PTR)        ; reload (disk_putbyte clobbered HL)
                inc     hl
                ld      a,(hl)              ; high byte
                call    disk_putbyte
                ret

; disk_putbyte — append the byte in A to the open-for-write file via the FAT12
; engine (which buffers into a 512-byte sector and flushes whole sectors as they
; fill). On a write error jumps to load_error.
;   in:  A = byte to write.
;   out: byte appended. Clobbers all (CALSLT clobbers everything across a sector
;        flush's DSKIO; the engine keeps its state in RAM).
disk_putbyte:
                call    fat_io_putbyte
                jp      c,load_error        ; disk full / write error
                ret

; disk_write_end — flush the buffered partial final sector and stamp the directory
; entry with the true byte count + first cluster (fat_io_close). On a write error
; jumps to load_error. Returns to the caller's caller (the REPL) on success.
disk_write_end:
                call    fat_io_close
                jp      c,load_error
                ret                         ; back to the prompt
