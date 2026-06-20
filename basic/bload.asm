; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause

; bload.asm — the BLOAD statement handler.
;
; This is the *interpreter half* of BLOAD: it does NOT decode the cassette
; signal itself (that is the BIOS "device half" — TAPION/TAPIN). It parses its
; arguments from the crunched token stream, drives the documented cassette BIOS
; contract to read a BSAVE-format binary, places the bytes in RAM, and (for ,R)
; performs the handoff by jumping to the exec address.
;
; Derived only from basic-spec/docs/spec-bload-r.md and spec-tokenise.md (this
; project's own black-box oracle observations) + the MSX2 Technical Handbook.
; No disassembly.
;
; Entry: do_bload, HL -> the bytes after the BLOAD token. spec-tokenise.md: the
; arguments are kept verbatim as ASCII, i.e. `"CAS:",R` followed by 0x00.
;
; Device-string grammar (this build):
;   "CAS:"            -> tape path (verbatim, unchanged from the original)
;   "A:name"/"B:name" -> disk path, explicit drive letter (case-insensitive)
;   "name"            -> disk path, defaults to drive A
; A disk filename needs NO new token: BLOAD arguments are kept verbatim ASCII in
; the crunch stream (spec-tokenise.md), so the tokeniser is untouched.

do_bload:
                ; --- parse: "<device>" [ ,R ] ------------------------------
                call    skip_spaces
                ld      a,(hl)
                cp      '"'                 ; opening quote required
                jp      nz,load_error
                inc     hl
                ; --- device dispatch: "CAS:" -> tape, else -> disk ----------
                ; Peek for the literal "CAS:" prefix. Match it verbatim and
                ; non-destructively decide; only commit to the tape path once
                ; the full prefix matched, so a name like "CASE.BIN" falls
                ; through to the disk path cleanly.
                push    hl                  ; remember filename start
                ld      de,dev_cas          ; compare device name to "CAS:"
parse_dev:
                ld      a,(de)
                or      a
                jr      z,is_tape           ; matched all of "CAS:" -> tape
                ld      c,a                 ; expected (uppercase) char
                ld      a,(hl)              ; typed char
                call    upcase              ; case-insensitive (typed may be lower)
                cp      c
                jr      nz,is_disk          ; prefix mismatch -> disk path
                inc     hl
                inc     de
                jr      parse_dev
is_tape:
                pop     af                  ; discard saved filename start
                ; HL now points just past "CAS:"; tape path continues verbatim.
                call    parse_close_run     ; closing quote + optional ,R
                jp      c,load_error
                ; --- open the tape and skip the file-header block's tone ---
                call    TAPION              ; sync block 1 (file header)
                jp      c,load_error

                ; --- file-header block: 10x BINARY_ID + 6-char filename ---
                ; spec-bload-r.md §1: header block is 16 bytes; byte 0 is the
                ; binary-file id. We verify the id and discard the rest.
                call    TAPIN
                jp      c,load_error
                cp      BINARY_ID           ; must be a binary (BSAVE) file
                jp      nz,load_error
                ld      b,15                ; remaining header bytes
skip_hdr:
                push    bc                  ; TAPIN trashes all regs
                call    TAPIN
                pop     bc
                jp      c,load_error
                djnz    skip_hdr

                ; --- data block: skip its tone, then read the 6-byte header --
                call    TAPION              ; sync block 2 (data)
                jp      c,load_error

                ; spec-bload-r.md §1: start(LE), end(LE), exec(LE).
                ; TAPIN trashes every register, so store each byte immediately.
                call    TAPIN
                ld      (CURPTR),a          ; start low
                call    TAPIN
                ld      (CURPTR+1),a        ; start high
                call    TAPIN
                ld      (ENDPTR),a          ; end low
                call    TAPIN
                ld      (ENDPTR+1),a        ; end high
                call    TAPIN
                ld      (EXECPTR),a         ; exec low
                call    TAPIN
                ld      (EXECPTR+1),a       ; exec high

                ; --- load loop: bytes start..end inclusive, verbatim --------
                ; spec-bload-r.md §2. State lives in RAM because TAPIN trashes
                ; all registers on every call.
load_loop:
                call    TAPIN
                jp      c,load_error
                ld      hl,(CURPTR)
                ld      (hl),a              ; store the byte
                ld      de,(ENDPTR)
                ld      a,h
                cp      d
                jr      nz,load_next        ; high bytes differ -> more to do
                ld      a,l
                cp      e
                jr      z,load_done         ; cur == end -> last byte stored
load_next:
                inc     hl
                ld      (CURPTR),hl
                jr      load_loop

load_done:
                call    TAPIOF              ; motor off
                ; fall through to the shared ,R handoff tail.

; load_handoff — shared ,R exec handoff (cassette + disk paths). spec-bload-r.md
; §3 / disk BLOAD: plain BLOAD returns; ,R jumps to the exec address (RUNFLAG was
; set by the parser; CURPTR/ENDPTR/EXECPTR are filled by whichever load ran).
load_handoff:
                ld      a,(RUNFLAG)
                or      a
                ret     z                   ; plain BLOAD: return to caller
                ld      hl,(EXECPTR)
                jp      (hl)

; ===========================================================================
; Disk path: parse a disk filename into the scratch FCB, then route to the
; placeholder. This item is PARSE-ONLY — do_disk_bload deliberately falls
; through to load_error; the NEXT TODO item ("Disk BLOAD execute") fills it in.
;
; On entry to is_disk: the top of the stack holds the filename start (the
; char after the opening quote), and HL points partway through the prefix
; comparison (it must NOT be trusted — restore from the stack). DE was
; pointing into dev_cas (don't care).
;
; FCB convention (CP/M / MSX-DOS, MSX2 TH): drive code 0=default, 1=A, 2=B.
; The 11-byte 8.3 name field is space-padded ($20), upper-cased. See
; basic/sysvars.inc DISK_FCB and PROVENANCE.md §disk-BLOAD scratch FCB.
is_disk:
                pop     hl                  ; HL = filename start (after quote)
                ; --- detect an optional drive letter "X:" -------------------
                ; "A:" / "B:" (case-insensitive). Default drive = A when absent.
                ; Look at name[0] and name[1]: a letter followed by ':' is a
                ; drive spec; anything else is a bare filename on drive A.
                ld      a,1                 ; default drive code = A
                ld      (DISK_FCB_DRV),a
                ld      a,(hl)
                call    upcase
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
                jp      load_error          ; "X:" with X not A/B -> reject
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
                jp      c,load_error        ; name didn't fit 8.3 / malformed
                ; --- shared closing-quote + ,R parse -----------------------
                call    parse_close_run
                jp      c,load_error
                ; FCB is fully built (DISK_FCB_DRV + DISK_FCB_NAME) and RUNFLAG
                ; is set. Hand off to the (placeholder) disk loader.
                jp      do_disk_bload

; do_disk_bload — real disk load via the disk ROM's BDOS FCB layer.
;
; The FCB at DISK_FCB is fully built (drive code + 8.3 name) and RUNFLAG is set.
; We reach the disk ROM's bdos_entry across slots with CALSLT ($001C): the slot
; id is DISKSLOT (recorded by the INIT scan, initext.asm) and the entry address
; is the SYSTEM sysvar ($F37D) the disk INIT filled. We then:
;   $1A Set-DTA -> DISK_DTA  (page-0 $0080 is BIOS ROM under Disk BASIC, unusable)
;   $0F Open    -> require A=$00
;   $14 SeqRead -> a 128-byte record stream; the first 7 bytes are the on-disk
;                  BSAVE header [$FE][start:2 LE][end:2 LE][exec:2 LE], the rest
;                  is data loaded into [start..end] inclusive.
;   $10 Close
; Then share the ,R handoff tail with the cassette path.
;
; SeqRead delivers 128-byte records but the 7-byte header is not record-aligned
; with the data, so we stream byte-by-byte through disk_getbyte (refilling a
; record via SeqRead when the buffer is exhausted) and track the byte offset in
; DTA_OFF/DTA_VALID. Sources: BDOS call numbers + Set-DTA — MSX2 TH / MSX-DOS
; BDOS table; disk BSAVE header — MSX-BASIC file formats (MSX Wiki / MSX Resource
; Center). See basic/PROVENANCE.md §disk BLOAD execute.
do_disk_bload:
                ; (1) disk ROM slot must have been recorded by the INIT scan.
                ld      a,(DISKSLOT_OK)
                or      a
                jp      z,load_error
                ; (3) Set-DTA -> our writable buffer; mark the record empty so the
                ; first disk_getbyte triggers a SeqRead.
                ld      a,128
                ld      (DTA_OFF),a         ; OFF==VALID -> buffer exhausted
                ld      (DTA_VALID),a
                ld      c,BDOS_SETDTA
                ld      de,DISK_DTA
                call    bdos_call
                ; (4) Open the file (DE = FCB). A=$00 required.
                ld      c,BDOS_OPEN
                ld      de,DISK_FCB
                call    bdos_call
                or      a
                jp      nz,load_error       ; not found / I-O error
                ; (5a) header byte 0 must be the BSAVE disk marker $FE.
                call    disk_getbyte
                jp      c,load_error
                cp      BSAVE_DISK_ID
                jp      nz,disk_load_err    ; close, then error
                ; header bytes 1..6: start(LE), end(LE), exec(LE) into the same
                ; CURPTR/ENDPTR/EXECPTR vars the tape path uses.
                call    disk_getbyte
                jp      c,disk_load_err
                ld      (CURPTR),a          ; start low
                call    disk_getbyte
                jp      c,disk_load_err
                ld      (CURPTR+1),a        ; start high
                call    disk_getbyte
                jp      c,disk_load_err
                ld      (ENDPTR),a          ; end low
                call    disk_getbyte
                jp      c,disk_load_err
                ld      (ENDPTR+1),a        ; end high
                call    disk_getbyte
                jp      c,disk_load_err
                ld      (EXECPTR),a         ; exec low
                call    disk_getbyte
                jp      c,disk_load_err
                ld      (EXECPTR+1),a       ; exec high
                ; (5b) stream data bytes into [start..end] inclusive.
disk_load_loop:
                call    disk_getbyte
                jp      c,disk_load_err     ; ran out before reaching end -> error
                ld      hl,(CURPTR)
                ld      (hl),a              ; store the byte
                ld      de,(ENDPTR)
                ld      a,h
                cp      d
                jr      nz,disk_load_next   ; high bytes differ -> more to do
                ld      a,l
                cp      e
                jr      z,disk_load_fin     ; cur == end -> last byte stored
disk_load_next:
                inc     hl
                ld      (CURPTR),hl
                jr      disk_load_loop
disk_load_fin:
                ; (6) close the file.
                ld      c,BDOS_CLOSE
                ld      de,DISK_FCB
                call    bdos_call
                ; (7) shared ,R handoff tail.
                jp      load_handoff

; disk_load_err — close the open file, then take the normal error path.
disk_load_err:
                ld      c,BDOS_CLOSE
                ld      de,DISK_FCB
                call    bdos_call
                jp      load_error

; disk_getbyte — return the next byte of the open file's data stream in A.
; Refills DISK_DTA via a SeqRead ($14) when the current 128-byte record is
; exhausted; CF set on EOF (no more data). State: DTA_OFF = next index into
; DISK_DTA, DTA_VALID = bytes in this record (always 128 from our SeqRead).
;   out: CF clear, A = byte; or CF set = EOF. Clobbers A/B/C/D/E/H/L (CALSLT
;        clobbers everything across the SeqRead; we restore from RAM each time).
disk_getbyte:
                ld      a,(DTA_OFF)
                ld      b,a
                ld      a,(DTA_VALID)
                cp      b
                jr      nz,dgb_have         ; bytes still left in DISK_DTA
                ; record exhausted: SeqRead the next 128 bytes.
                ld      c,BDOS_SEQRD
                ld      de,DISK_FCB
                call    bdos_call
                or      a
                jr      nz,dgb_eof          ; A=$01 EOF (or any non-zero) -> done
                xor     a
                ld      (DTA_OFF),a         ; back to byte 0 of the fresh record
                ld      a,128
                ld      (DTA_VALID),a
                ld      b,0                 ; B = current offset (0)
dgb_have:
                ; fetch DISK_DTA[B], then advance DTA_OFF.
                ld      hl,DISK_DTA
                ld      d,0
                ld      e,b
                add     hl,de
                ld      a,b
                inc     a
                ld      (DTA_OFF),a
                ld      a,(hl)              ; A = the byte
                or      a                   ; clear CF (A may be anything; OR clears C)
                ret
dgb_eof:
                scf
                ret

; bdos_call — inter-slot call into the disk ROM's bdos_entry.
;   in:  C = BDOS call number, DE = FCB / pointer
;   out: A = BDOS result (also stored to BDOS_RES). Slot id = DISKSLOT, entry
;        address = the SYSTEM sysvar ($F37D). DISKSLOT_OK must already be 1.
; CALSLT ($001C) clobbers AF/BC/DE/HL/IX/IY; callers keep their state in RAM.
; CALSLT reads the slot from IYh, so we build the slot word in RAM: low byte is
; don't-care, high byte = DISKSLOT. SCAN_IY (the INIT-scan CALSLT word, $E0D9) is
; dead once the REPL is running, so we reuse it rather than spend new RAM.
bdos_call:
                ld      a,(DISKSLOT)
                ld      (SCAN_IY+1),a       ; IYh = disk ROM slot id
                ld      iy,(SCAN_IY)
                ld      ix,(SYSTEM_VEC)     ; entry address = bdos_entry ($F37D)
                call    CALSLT
                ld      (BDOS_RES),a
                ret

; build_83_name — convert the filename at HL into the 11-byte 8.3 field at
; DISK_FCB_NAME (8 name + 3 ext, space-padded $20, upper-case).
;   in:  HL -> first filename char (the byte after any drive prefix)
;   out: HL -> the closing '"' (so parse_close_run resumes there);
;        CF clear on success, CF set if the name doesn't fit 8.3 or is empty.
; Rules (own design, documented in PROVENANCE.md §disk-BLOAD scratch FCB):
;   - split on the FIRST '.'; up to 8 chars before -> name, up to 3 after -> ext
;   - no '.' -> all-name, ext = 3 spaces
;   - the filename ends at the closing '"' (or NUL, defensively)
;   - more than 8 name chars or 3 ext chars, or an empty name, is REJECTED
;     (CF set) — truncation hides typos, so we error instead.
build_83_name:
                ; pre-fill the 11-byte field with spaces
                push    hl
                ld      hl,DISK_FCB_NAME
                ld      b,11
                ld      a,' '
bn_fill:
                ld      (hl),a
                inc     hl
                djnz    bn_fill
                pop     hl
                ; --- name part: up to 8 chars, until '.', '"', or NUL --------
                ld      de,DISK_FCB_NAME    ; DE -> name field write cursor
                ld      b,8                 ; max name chars remaining
bn_name:
                ld      a,(hl)
                cp      '"'
                jr      z,bn_done           ; end of filename, no extension
                or      a
                jr      z,bn_done           ; NUL (defensive) -> end
                cp      '.'
                jr      z,bn_ext            ; start of extension
                ; another name char
                ld      c,a                 ; must consume even if field full
                ld      a,b
                or      a
                jr      z,bn_reject         ; >8 name chars -> reject
                ld      a,c
                call    upcase
                ld      (de),a
                inc     de
                inc     hl
                dec     b
                jr      bn_name
bn_ext:
                ; HL -> '.'; skip it, write up to 3 ext chars
                inc     hl
                ld      de,DISK_FCB_NAME + 8 ; DE -> ext field write cursor
                ld      b,3                 ; max ext chars remaining
bn_ext_loop:
                ld      a,(hl)
                cp      '"'
                jr      z,bn_done
                or      a
                jr      z,bn_done
                cp      '.'
                jr      z,bn_reject         ; a second '.' is malformed 8.3
                ld      c,a
                ld      a,b
                or      a
                jr      z,bn_reject         ; >3 ext chars -> reject
                ld      a,c
                call    upcase
                ld      (de),a
                inc     de
                inc     hl
                dec     b
                jr      bn_ext_loop
bn_done:
                ; reject an empty name (e.g. "" or ".EXT" or "A:")
                ld      a,(DISK_FCB_NAME)
                cp      ' '
                jr      z,bn_reject         ; first name char still space -> empty
                or      a                   ; CF clear = success
                ret
bn_reject:
                scf
                ret

; parse_close_run — shared tail parse used by BOTH the tape and disk paths.
; Consumes the closing '"' and an optional ,R; sets RUNFLAG accordingly.
;   in:  HL -> the closing '"' of the device string
;   out: CF set if the closing quote is missing (caller -> load_error);
;        CF clear on success, RUNFLAG = 1 iff ,R (or ,r) was given.
parse_close_run:
                ld      a,(hl)
                cp      '"'                 ; closing quote required
                jr      nz,pcr_err
                inc     hl
                xor     a
                ld      (RUNFLAG),a         ; default: no handoff
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      nz,pcr_ok           ; no option -> plain load
                inc     hl
                call    skip_spaces
                ld      a,(hl)
                call    upcase              ; accept ,r as well as ,R
                cp      'R'                 ; only ,R is supported
                jr      nz,pcr_ok
                ld      a,1
                ld      (RUNFLAG),a
pcr_ok:
                or      a                   ; CF clear = success
                ret
pcr_err:
                scf
                ret

; device name accepted by this build. Source: spec-bload-r.md §5 ("CAS:").
dev_cas:
                db      "CAS:",0

; --- error path: stop the tape, drop a marker, report, return to the prompt -
; Reached when a cassette BIOS call fails (CF set), the file is not binary, or
; the arguments do not parse. Under bare C-BIOS this fires immediately: its
; TAPION/TAPIN are stubs that always set CF (observable as $EE at ERRMARK).
load_error:
                call    TAPIOF
                ld      a,$EE
                ld      (ERRMARK),a
                ld      hl,err_io
                call    print_string
                ret
err_io:
                db      "load error",13,10,0
