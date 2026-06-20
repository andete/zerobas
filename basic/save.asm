; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause

; save.asm — the BSAVE and SAVE statement handlers (disk write side).
;
; The WRITE mirror of bload.asm / cload.asm. Where do_disk_bload reads a BSAVE
; binary image off disk and disk_prog_load reads a tokenised BASIC program off
; disk, do_bsave WRITES a BSAVE binary image and do_save WRITES the tokenised
; program image, both through the disk ROM's BDOS FCB write subset.
;
;   BSAVE "A:F",start,end[,exec]   -> on-disk binary file:
;        [$FE][start:2 LE][end:2 LE][exec:2 LE] then RAM[start..end] inclusive.
;        exec defaults to start when the ,exec arg is omitted (matches the read
;        side / MSX BASIC).
;   SAVE "A:F"                     -> on-disk tokenised-BASIC file:
;        [$FF] then the in-memory line-link program image TXTBASE..PRGEND+1
;        ([link:2][lineno:2][tokens][00] per line, ending in the $0000 end-link).
;        The ,A ASCII-save form is OUT OF SCOPE (documented unsupported): a ,A
;        flag takes load_error.
;
; Device scope: DISK ONLY. A "CAS:" device (tape write) is OUT OF SCOPE for both
; verbs — if the device parses as "CAS:" we take load_error (tape write
; unsupported). Bare names / "A:"/"B:" prefixes go to disk via parse_disk_fcb.
;
; CLEAN-ROOM: the on-disk $FE BSAVE header and $FF tokenised-BASIC marker, and
; the line-link program format, are the SAME allowed-source formats the read side
; consumes (sysvars.inc BSAVE_DISK_ID / BASIC_DISK_ID; MSX-BASIC file formats —
; MSX Wiki / MSX Resource Center). The BDOS Create/SeqWrite/Close call numbers are
; the MSX-DOS BDOS table (MSX2 TH). The SAVE/BSAVE keyword tokens are oracle-LOCKED
; (PROVENANCE.md "SAVE / BSAVE statement tokens — oracle-locked"). Reuses bload.asm
; plumbing: parse_disk_fcb, bdos_call, load_error, dev_cas, eval. No disassembly.
;
; Record granularity: the disk ROM's Sequential Write ($15) writes a FIXED 128-byte
; record from the DTA and Close stamps the directory size as (records x 128). So a
; saved file's length is rounded UP to the next 128-byte boundary, with trailing
; zero-fill. This is benign for BOTH formats: the BSAVE reader is bounded by the
; end address in the $FE header, and the tokenised reader stops at the $0000
; end-link — neither reads into the pad. A real MSX-DOS cross-read sees the same
; record-rounded size (a property of this BDOS implementation, not these handlers;
; disk/disk.asm is out of scope). See PROVENANCE.md §disk SAVE / BSAVE.

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
                call    reject_cas          ; "CAS:" device -> tape write unsupported
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

; ===========================================================================
; do_save — SAVE "device:name"   (tokenised-BASIC save; ,A out of scope)
; Entry: HL -> the bytes after the SAVE token.
do_save:
                call    skip_spaces
                ld      a,(hl)
                cp      '"'                 ; opening quote required
                jp      nz,load_error
                inc     hl
                call    reject_cas          ; "CAS:" device -> tape write unsupported
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

; ===========================================================================
; reject_cas — peek for a literal "CAS:" device prefix; if matched, take
; load_error (tape write unsupported). NON-DESTRUCTIVE on a mismatch, exactly
; like do_bload's CAS: peek: HL is preserved across the compare so a name like
; "CASE.BIN" falls through cleanly to the disk path.
;   in:  HL -> first filename char (the byte after the opening '"').
;   out: HL unchanged on a non-CAS name (caller proceeds to parse_disk_fcb); on a
;        "CAS:" match this jumps to load_error and does NOT return.
; Clobbers A, C, DE (HL preserved on return).
reject_cas:
                push    hl                  ; remember filename start
                ld      de,dev_cas          ; compare device name to "CAS:"
rc_cmp:
                ld      a,(de)
                or      a
                jr      z,rc_is_cas         ; matched all of "CAS:" -> tape write
                ld      c,a                 ; expected (uppercase) char
                ld      a,(hl)              ; typed char
                call    upcase              ; case-insensitive
                cp      c
                jr      nz,rc_not_cas       ; prefix mismatch -> disk path
                inc     hl
                inc     de
                jr      rc_cmp
rc_not_cas:
                pop     hl                  ; restore filename start; HL unchanged
                ret
rc_is_cas:
                pop     hl                  ; balance the stack
                jp      load_error          ; tape write is out of scope

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
; Shared disk-write helper (the WRITE analogue of the read side's
; disk_getbyte/bdos_call). disk_write_begin opens a fresh file and arms the
; 128-byte record accumulator; disk_putbyte appends one byte, issuing a
; Sequential Write whenever the record fills; disk_write_end flushes a partial
; record then Closes. State: DSV_OFF = next fill index into DISK_DTA (0..128).
; Uses bload.asm plumbing: DISKSLOT_OK, bdos_call, DISK_DTA.

; disk_write_begin — require a recorded disk-ROM slot, Set-DTA to DISK_DTA, then
; Create (truncate-or-make) the file named in DISK_FCB. Resets DSV_OFF to 0.
; On any failure jumps to load_error (does not return).
disk_write_begin:
                ld      a,(DISKSLOT_OK)
                or      a
                jp      z,load_error
                xor     a
                ld      (DSV_OFF),a         ; record buffer empty
                ld      c,BDOS_SETDTA
                ld      de,DISK_DTA
                call    bdos_call
                ld      c,BDOS_CREATE
                ld      de,DISK_FCB
                call    bdos_call
                or      a
                jp      nz,load_error       ; disk full / write protect / I-O
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

; disk_putbyte — append the byte in A to the current 128-byte record at DISK_DTA;
; when the record fills (128 bytes) issue a Sequential Write ($15) and reset the
; fill index. Mirrors disk_getbyte's record framing on the write side.
;   in:  A = byte to write.
;   out: byte buffered (and possibly a record flushed). On a write error jumps to
;        load_error. Clobbers A/B/C/D/E/H/L (CALSLT clobbers all across SeqWrite;
;        state is held in RAM). Preserves nothing.
disk_putbyte:
                ld      c,a                 ; C = byte to store (survives the index math)
                ld      a,(DSV_OFF)
                ld      e,a
                ld      d,0
                ld      hl,DISK_DTA
                add     hl,de               ; HL = DISK_DTA + DSV_OFF
                ld      (hl),c              ; store the byte
                inc     a                   ; advance the fill index
                ld      (DSV_OFF),a
                cp      128
                ret     nz                  ; record not full yet
                ; record full -> Sequential Write it, then reset the index.
                call    disk_flush_record
                ret

; disk_flush_record — write the current 128-byte DISK_DTA record via Sequential
; Write ($15) and reset DSV_OFF to 0. On a write error jumps to load_error.
disk_flush_record:
                ld      c,BDOS_SEQWR
                ld      de,DISK_FCB
                call    bdos_call
                or      a
                jp      nz,save_write_err   ; $01 disk full / $FF error -> close + error
                xor     a
                ld      (DSV_OFF),a
                ret

; disk_write_end — flush a partial final record (zero-padded to 128 bytes so the
; whole record is well-defined), then Close ($10) to finalise the directory size.
; Returns to the caller's caller (the REPL) on success.
disk_write_end:
                ld      a,(DSV_OFF)
                or      a
                jr      z,dwe_close         ; nothing buffered -> just close
                ; zero-pad the partial record up to 128 bytes.
                ld      e,a
                ld      d,0
                ld      hl,DISK_DTA
                add     hl,de               ; HL = first unused byte
                ld      a,128
                sub     e
                ld      b,a                 ; B = pad byte count (1..127)
dwe_pad:
                ld      (hl),0
                inc     hl
                djnz    dwe_pad
                call    disk_flush_record   ; write the (now full) final record
dwe_close:
                ld      c,BDOS_CLOSE
                ld      de,DISK_FCB
                call    bdos_call
                ret                         ; back to the prompt

; save_write_err — a Sequential Write failed mid-stream: close the file (best
; effort) then take the normal error path.
save_write_err:
                ld      c,BDOS_CLOSE
                ld      de,DISK_FCB
                call    bdos_call
                jp      load_error
