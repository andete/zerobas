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

                ; --- ,R handoff: jump to the exec address -------------------
                ; spec-bload-r.md §3. Only when ,R was given.
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

; do_disk_bload — PLACEHOLDER. The scratch FCB at DISK_FCB is ready to be
; passed to the disk ROM's bdos_entry (C=BDOS_F_OPEN, DE=DISK_FCB) by the NEXT
; TODO item ("Disk BLOAD execute"). For now it falls through cleanly to
; load_error so the ROM behaves safely. DO NOT implement the disk read here.
do_disk_bload:
                jp      load_error

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
