; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; sv-tsb.inc -- the shared cassette tokenised-BASIC writer (tape_save_basic .. tsb_fin).
; ===========================================================================
; Clean-room: own code. The cassette container format (the $D3 leader, the
; 6-character name field, the header-then-data block pair) is from the public
; MSX2 Technical Handbook cassette chapter and round-trip validated against our
; own encoder; nothing here is derived from a disassembly or byte-copy of any
; reference ROM. Basis: basic/PROVENANCE.md.
; ===========================================================================

; tape_save_basic — shared cassette tokenised-BASIC save path.
; Writes a two-block cassette file: header block ($D3 ×10 + 6-char name in
; TSV_NAME) then data block (program image TXTBASE..PRGEND+1 inclusive).
; Reaches here with TSV_NAME already filled and HL past the opening quote.
; Clobbers everything (TAPOUT does); no return value (jumps to sv_load_error on
; TAPOON/TAPOUT failure, else returns to the REPL).
; Format source: MSX2 TH cassette chapter; cas_encode.py build_cas_basic().
tape_save_basic:
                ; --- header block: TAPOON(long) + 10x$D3 + 6-char name + TAPOOF ---
                ld      a,$FF               ; non-zero -> long leader
                call    TAPOON
                jp      c,sv_load_error
                ; emit 10x BASIC_ID ($D3)
                ld      a,10
                ld      (TSV_CNT),a
tsb_id:
                ld      a,BASIC_ID          ; $D3
                call    TAPOUT
                jp      c,sv_load_error
                ld      a,(TSV_CNT)
                dec     a
                ld      (TSV_CNT),a
                jr      nz,tsb_id
                ; emit 6-char name
                call    tape_name_emit
                jp      c,sv_load_error
                call    TAPOOF              ; end of header block
                ; --- data block: TAPOON(short) + program image + TAPOOF ------
                xor     a                   ; zero -> short leader
                call    TAPOON
                jp      c,sv_load_error
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
                jp      c,sv_load_error
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
