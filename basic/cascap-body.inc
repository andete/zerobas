; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; cascap-body.inc -- cas_capture_name, shared by main (basic/cload.asm, at its
; original position) and the sub-ROM BLOAD tenant (sub/bload.asm). D-CASBIN
; (2026-10-08): BLOAD's tape arm searches by NAME now, and main page 1 -- where
; this lives -- is switched out while that tenant runs, so the tenant needs its
; own copy; this file keeps it one source text, not two.
;
; Clean-room: our own code, moved verbatim from basic/cload.asm (see that file's
; header for the cassette file-format provenance). No reference ROM byte read.

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
                ld      bc,$0600            ; D-PEEPHOLE: b=6 slots left in
                                            ; CAS_WANT, c=0 chars copied so far
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
                djnz    ccn_pad_lp          ; D-PEEPHOLE: -1 B. djnz sets NO
                                            ; flags, and none are read after --
                                            ; ccn_flag opens `ld a,c / or a`,
                                            ; which redefines them. The `or a`
                                            ; guard above keeps B >= 1, so the
                                            ; B=0 wrap is unreachable either way.
ccn_flag:
                ld      a,c                 ; A = name-char count
                or      a
                jr      z,ccn_set           ; empty name -> store 0 (load next file)
                ld      a,1                 ; a name was given -> match it
ccn_set:
                ld      (CAS_WANT_ON),a
                ret
