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

do_bload:
                ; --- parse: "<device>" [ ,R ] ------------------------------
                call    skip_spaces
                ld      a,(hl)
                cp      '"'                 ; opening quote required
                jp      nz,load_error
                inc     hl
                ld      de,dev_cas          ; compare device name to "CAS:"
parse_dev:
                ld      a,(de)
                or      a
                jr      z,parse_dev_end     ; matched all of "CAS:"
                ld      c,a                 ; expected (uppercase) char
                ld      a,(hl)              ; typed char
                call    upcase              ; case-insensitive (typed may be lower)
                cp      c
                jp      nz,load_error       ; unsupported device
                inc     hl
                inc     de
                jr      parse_dev
parse_dev_end:
                ld      a,(hl)
                cp      '"'                 ; closing quote required
                jp      nz,load_error
                inc     hl
                ; optional ,R
                xor     a
                ld      (RUNFLAG),a         ; default: no handoff
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      nz,open_tape        ; no option -> plain load
                inc     hl
                call    skip_spaces
                ld      a,(hl)
                call    upcase              ; accept ,r as well as ,R
                cp      'R'                 ; only ,R is supported
                jr      nz,open_tape
                ld      a,1
                ld      (RUNFLAG),a

open_tape:
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
