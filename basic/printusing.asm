; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause

; printusing.asm — PRINT USING formatted output.
;
;   PRINT USING <format$> ; <value> [ ; <value> ]...
;
; The format string is scanned left to right: literal characters are emitted as-is,
; and "fields" are replaced by successive values from the list. Supported fields:
;   #...#    numeric field, width = the count of '#'. The (integer) value is right-
;            justified in the field; a negative value's '-' takes a position; a value
;            that does not fit is printed in full preceded by '%' (MSX overflow).
;   \...\    fixed-width string field, width = 2 + the characters between the
;            backslashes. The string is left-justified and space-padded (truncated
;            if longer than the field).
;   !        the first character of the string value.
;   &        the whole string value (variable width).
; When the value list still has values after the format ends, the format repeats
; from the start (so e.g. "## " applied to 1,2,3 gives " 1  2  3 "). When the values
; run out, the remaining literal text up to the next field is emitted and output
; stops. A trailing ';' suppresses the closing newline, exactly like PRINT.
;
; This is the COMPLETE feature for zerobas's current numeric domain (integers): the
; float-only format specs — the decimal point '.', exponential '^^^^', and the
; '+'/'-'/','/'**'/'$$' embellishments — arrive with Phase-3 floats. PRINT# USING
; (the file form) and the '_' literal-escape are likewise deferred. (PROVENANCE.md
; §PRINT USING.)
;
; Clean-room: original code. Field semantics follow the public MSX-BASIC language
; reference; the USING token ($E4) is oracle-locked to the VG-8020 crunch. The
; integer formatter reuses print.asm's div10. No disassembly.
;
; Entry: ex_print_using, HL -> the USING token (ex_print dispatched here).

BACKSLASH       equ     $5C                 ; '\' (avoid the assembler's escape char)

ex_print_using:
                inc     hl                  ; past the USING token
                call    skip_spaces
                call    str_eval            ; STRPTR -> the format [len][bytes]
                jp      nc,stmt_error       ; the format must be a string
                ; copy the format into PU_FMT (it must survive later str_eval calls,
                ; which reuse STRSCR for literal string VALUES). Clamp to PU_FMTMAX.
                push    hl                  ; guard the token cursor
                ld      hl,(STRPTR)
                ld      a,(hl)
                cp      PU_FMTMAX+1
                jr      c,puf_lenok
                ld      a,PU_FMTMAX
puf_lenok:
                ld      (PU_FMTLEN),a
                inc     hl                  ; HL -> format bytes
                ld      de,PU_FMT
                ld      c,a
                ld      b,0
                or      a
                jr      z,puf_copied
                ldir
puf_copied:
                pop     hl                  ; HL = cursor past the format operand
                ; a ';' or ',' separates the format from the value list.
                call    skip_spaces
                ld      a,(hl)
                cp      ';'
                jr      z,puf_sep
                cp      ','
                jr      nz,puf_nosep
puf_sep:
                inc     hl
puf_nosep:
                xor     a
                ld      (PU_POS),a
                ld      (PU_FLAGS),a
                ; a format with NO field is just literal text -> emit it and finish.
                push    hl                  ; pu_has_field clobbers HL (the token cursor)
                call    pu_has_field
                pop     hl
                jr      nc,pu_literal_only
; --- main loop: one value per field, cycling the format ---------------------
pu_main:
                call    skip_spaces
                ld      a,(hl)
                or      a
                jr      z,pu_endlist        ; end of line
                cp      COLON
                jr      z,pu_endlist        ; next statement
                ld      a,(PU_FLAGS)
                and     $FE                 ; a value follows -> clear trailing-sep
                ld      (PU_FLAGS),a
                push    hl                  ; pu_to_field clobbers HL (the token cursor)
                call    pu_to_field         ; emit literals up to the next field
                pop     hl
                jr      c,pu_endlist        ; (defensive: no field -> stop)
                ld      a,(PU_TYPE)
                or      a
                jr      z,pu_mnum
                call    pu_do_string
                jr      pu_msep_chk
pu_mnum:
                call    pu_do_number
pu_msep_chk:
                call    skip_spaces
                ld      a,(hl)
                cp      ';'
                jr      z,pu_msep
                cp      ','
                jr      z,pu_msep
                jr      pu_endlist          ; no separator -> value list done
pu_msep:
                inc     hl
                ld      a,(PU_FLAGS)
                or      1                   ; possibly-dangling trailing separator
                ld      (PU_FLAGS),a
                jr      pu_main
pu_endlist:
                push    hl                  ; pu_emit_tail clobbers HL (the token cursor)
                call    pu_emit_tail        ; trailing literals up to the next field
                pop     hl
                ld      a,(PU_FLAGS)
                bit     0,a
                jr      nz,pu_skipnl
                call    print_crlf
pu_skipnl:
                call    skip_spaces
                ld      a,(hl)
                cp      COLON
                jp      z,exec_stmt         ; HL on ':' -> step into the next statement
                ret

; literal-only format (no field char): emit the whole format, swallow any value
; list, newline. Rare/degenerate but kept well-defined.
pu_literal_only:
                xor     a
                ld      (PU_POS),a
                push    hl                  ; pu_emit_tail clobbers HL (the token cursor)
                call    pu_emit_tail        ; no field -> emits the whole format
                pop     hl
pu_lo_skip:
                ld      a,(hl)
                or      a
                jr      z,pu_lo_end
                cp      COLON
                jr      z,pu_lo_end
                inc     hl
                jr      pu_lo_skip
pu_lo_end:
                call    print_crlf
                ld      a,(hl)
                cp      COLON
                jp      z,exec_stmt
                ret

; pu_has_field — CF set iff PU_FMT[0..PU_FMTLEN) contains a field char (#/!/&/\).
; Clobbers A, B, DE, HL.
pu_has_field:
                ld      hl,PU_FMT
                ld      a,(PU_FMTLEN)
                ld      b,a
                or      a
                ret     z                   ; empty -> CF clear
phf_lp:
                ld      a,(hl)
                cp      '#'
                jr      z,phf_yes
                cp      '!'
                jr      z,phf_yes
                cp      '&'
                jr      z,phf_yes
                cp      BACKSLASH
                jr      z,phf_yes
                inc     hl
                djnz    phf_lp
                or      a                   ; CF clear -> no field
                ret
phf_yes:
                scf
                ret

; pu_to_field — emit literal format chars from PU_POS until a field; on reaching the
; format end, wrap to 0 ONCE (format reuse). Out: CF clear + PU_TYPE/PU_W set +
; PU_POS advanced past the field; CF set if no field exists (after one wrap).
; Clobbers A, B, C, DE, HL.
pu_to_field:
                ld      a,(PU_FLAGS)
                and     $FD                 ; clear "wrapped" (bit1)
                ld      (PU_FLAGS),a
ptf_scan:
                ld      a,(PU_POS)
                ld      b,a
                ld      a,(PU_FMTLEN)
                cp      b
                jr      z,ptf_wrap          ; at end of format
                ld      e,b
                ld      d,0
                ld      hl,PU_FMT
                add     hl,de
                ld      a,(hl)
                cp      '#'
                jp      z,ptf_num
                cp      '!'
                jp      z,ptf_bang
                cp      '&'
                jp      z,ptf_amp
                cp      BACKSLASH
                jp      z,ptf_back
                call    pchar               ; literal -> emit
                ld      a,(PU_POS)
                inc     a
                ld      (PU_POS),a
                jr      ptf_scan
ptf_wrap:
                ld      a,(PU_FLAGS)
                bit     1,a
                jr      nz,ptf_nofield      ; already wrapped -> no field at all
                set     1,a
                ld      (PU_FLAGS),a
                xor     a
                ld      (PU_POS),a
                jr      ptf_scan
ptf_nofield:
                scf
                ret
ptf_num:
                ; width = run of '#' from PU_POS (bounded by the format end).
                ld      a,(PU_POS)
                ld      c,a                 ; C = scan index
                ld      b,0                 ; B = width
ptf_num_lp:
                ld      a,(PU_FMTLEN)
                cp      c
                jr      z,ptf_num_done
                ld      e,c
                ld      d,0
                ld      hl,PU_FMT
                add     hl,de
                ld      a,(hl)
                cp      '#'
                jr      nz,ptf_num_done
                inc     b
                inc     c
                jr      ptf_num_lp
ptf_num_done:
                ld      a,b
                ld      (PU_W),a
                ld      a,c
                ld      (PU_POS),a
                xor     a
                ld      (PU_TYPE),a         ; numeric (also CF clear)
                ret
ptf_bang:
                ld      a,(PU_POS)
                inc     a
                ld      (PU_POS),a
                ld      a,1
                ld      (PU_W),a
                ld      a,2                 ; type 2 = '!'
                ld      (PU_TYPE),a
                or      a                   ; CF clear
                ret
ptf_amp:
                ld      a,(PU_POS)
                inc     a
                ld      (PU_POS),a
                ld      a,1                 ; type 1 = '&'
                ld      (PU_TYPE),a
                or      a
                ret
ptf_back:
                ; find the closing '\' from PU_POS+1; width = closepos-PU_POS+1.
                ld      a,(PU_POS)
                ld      c,a
                inc     c                   ; scan from the char after the opening '\'
ptf_back_lp:
                ld      a,(PU_FMTLEN)
                cp      c
                jr      z,ptf_back_unterm   ; no closing '\' before the end
                ld      e,c
                ld      d,0
                ld      hl,PU_FMT
                add     hl,de
                ld      a,(hl)
                cp      BACKSLASH
                jr      z,ptf_back_close
                inc     c
                jr      ptf_back_lp
ptf_back_close:
                ld      a,c
                ld      hl,PU_POS
                sub     (hl)
                inc     a                   ; width = (close - open) + 1  (>= 2)
                ld      (PU_W),a
                inc     c                   ; PU_POS past the closing '\'
                ld      a,c
                ld      (PU_POS),a
                ld      a,3                 ; type 3 = '\..\'
                ld      (PU_TYPE),a
                or      a
                ret
ptf_back_unterm:
                ; lone '\' with no close -> treat it as a literal and keep scanning.
                ld      a,BACKSLASH
                call    pchar
                ld      a,(PU_POS)
                inc     a
                ld      (PU_POS),a
                jp      ptf_scan

; pu_emit_tail — emit literal format chars from PU_POS up to (not including) the next
; field or the format end. No wrap. Clobbers A, B, DE, HL.
pu_emit_tail:
                ld      a,(PU_POS)
                ld      b,a
                ld      a,(PU_FMTLEN)
                cp      b
                ret     z                   ; end of format
                ld      e,b
                ld      d,0
                ld      hl,PU_FMT
                add     hl,de
                ld      a,(hl)
                cp      '#'
                ret     z
                cp      '!'
                ret     z
                cp      '&'
                ret     z
                cp      BACKSLASH
                ret     z
                call    pchar
                ld      a,(PU_POS)
                inc     a
                ld      (PU_POS),a
                jr      pu_emit_tail

; pu_do_number — eval the next value and emit it right-justified in PU_W; '%' + full
; number on overflow. HL = token cursor (guarded across div10). Clobbers everything.
pu_do_number:
                call    eval                ; DE = value; HL advanced
                push    hl                  ; guard the token cursor
                call    pu_fmt_int          ; NUMBUF = "[-]digits",0 ; B = length
                ld      a,(PU_W)
                sub     b                   ; pad = width - length
                jr      c,pu_num_over       ; length > width -> overflow
                jr      z,pu_num_emit
                ld      b,a                 ; B = pad count
pu_num_pad:
                ld      a,' '
                call    pchar
                djnz    pu_num_pad
pu_num_emit:
                ld      hl,NUMBUF
                call    pu_emit_str0
                pop     hl
                ret
pu_num_over:
                ld      a,'%'               ; field overflow marker (MSX)
                call    pchar
                ld      hl,NUMBUF
                call    pu_emit_str0
                pop     hl
                ret

; pu_fmt_int — DE (signed 16) -> NUMBUF as "[-]digits",0; returns B = length.
; Reuses print.asm's div10 (which clobbers A,B,HL), so the length is derived from the
; final write pointer rather than counted in a register.
pu_fmt_int:
                ld      hl,NUMBUF
                bit     7,d
                jr      z,pfi_pos
                ld      (hl),'-'
                inc     hl
                push    hl                  ; save the digits-start pointer
                ld      hl,0
                or      a
                sbc     hl,de               ; HL = -value (magnitude)
                ex      de,hl               ; DE = magnitude
                pop     hl                  ; HL = NUMBUF+1
pfi_pos:
                ld      (PU_WP),hl          ; digits start
                ex      de,hl               ; HL = magnitude
                ld      a,$FF               ; stack sentinel
                push    af
pfi_div:
                call    div10               ; HL/=10, A = remainder
                push    af
                ld      a,h
                or      l
                jr      nz,pfi_div
                ld      hl,(PU_WP)
pfi_wr:
                pop     af
                cp      $FF
                jr      z,pfi_done
                add     a,'0'
                ld      (hl),a
                inc     hl
                jr      pfi_wr
pfi_done:
                ld      (hl),0              ; terminate
                ld      de,NUMBUF
                or      a
                sbc     hl,de
                ld      b,l                 ; B = length
                ret

; pu_emit_str0 — emit the 0-terminated string at HL via pchar. Clobbers A, HL.
pu_emit_str0:
                ld      a,(hl)
                or      a
                ret     z
                call    pchar
                inc     hl
                jr      pu_emit_str0

; pu_do_string — eval the next value as a string and emit it per PU_TYPE:
;   1 '&' whole, 2 '!' first char, 3 '\..\' fixed PU_W (left-justified, space-pad).
; pchar preserves all registers, so the B/C/HL loop counters survive each emit.
pu_do_string:
                call    str_eval            ; STRPTR -> the value [len][bytes]
                jp      nc,stmt_error       ; a string field needs a string value
                push    hl                  ; guard the token cursor
                ld      a,(PU_TYPE)
                cp      1
                jr      z,pus_whole
                cp      2
                jr      z,pus_first
                ; '\..\' fixed-width field
                ld      hl,(STRPTR)
                ld      a,(hl)
                ld      c,a                 ; C = source length
                inc     hl                  ; HL -> source bytes
                ld      a,(PU_W)
                ld      b,a                 ; B = field width
pus_fx_lp:
                ld      a,b
                or      a
                jr      z,pus_done          ; field filled
                ld      a,c
                or      a
                jr      z,pus_fx_pad        ; source exhausted -> pad with spaces
                ld      a,(hl)
                call    pchar
                inc     hl
                dec     c
                dec     b
                jr      pus_fx_lp
pus_fx_pad:
                ld      a,' '
                call    pchar
                djnz    pus_fx_pad
                jr      pus_done
pus_whole:
                ld      hl,(STRPTR)
                ld      b,(hl)              ; length
                inc     hl
pus_whole_lp:
                ld      a,b
                or      a
                jr      z,pus_done
                ld      a,(hl)
                call    pchar
                inc     hl
                dec     b
                jr      pus_whole_lp
pus_first:
                ld      hl,(STRPTR)
                ld      a,(hl)
                or      a
                jr      z,pus_done          ; empty string -> emit nothing
                inc     hl
                ld      a,(hl)
                call    pchar
pus_done:
                pop     hl
                ret
