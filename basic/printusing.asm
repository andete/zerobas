; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

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
; '+'/'-'/','/'**'/'$$' embellishments — arrive with Phase-3 floats. The '_' literal-
; escape is likewise deferred. (PROVENANCE.md §PRINT USING.)
;
; PRINT# USING (the file form) IS supported (repack): ex_print (basic/print.asm)
; dispatches a USING after a #channel here with PRDEST=1, so the formatter streams
; through pchar to the file. CF-3300-validated byte-for-byte
; (disk_probe_printusing_file.py). The format-copy A-preservation fix that made it
; correct is documented in pu_deref_body (basic/str-engine.asm) + docs/spec-print-
; hash-using.md.
;
; Clean-room: original code. Field semantics follow the public MSX-BASIC language
; reference; the USING token ($E4) is oracle-locked to the VG-8020 crunch. The
; integer formatter reuses print.asm's div10. No disassembly.
;
; Entry: ex_print_using, HL -> the USING token (ex_print dispatched here).

BACKSLASH       equ     $5C                 ; '\' (avoid the assembler's escape char)

; pu_deref_body ([len][ptr] -> body) lives in the low region (basic/str-
; engine.asm), shared with print_strval / field.asm / expr.asm's CVI — page 1
; is byte-full. PRINT USING's string-field sites below reach it by in-slot call.

ex_print_using:
                inc     hl                  ; past the USING token
                call    skip_spaces
                call    str_eval            ; STRPTR -> the format [len][bytes]
                jp      nc,stmt_error       ; the format must be a string
                ; copy the format into PU_FMT (it must survive later str_eval calls,
                ; which reuse STRSCR/RVDESC for literal string VALUES). Clamp to
                ; PU_FMTMAX.
                push    hl                  ; guard the token cursor
                ld      hl,(STRPTR)
                ld      a,(hl)
                cp      PU_FMTMAX+1
                jr      c,puf_lenok
                ld      a,PU_FMTMAX
puf_lenok:
                ld      (PU_FMTLEN),a
                call    pu_deref_body       ; arrays slice-4a: HL(desc)->HL(body)
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

; --- pu_to_field / pu_emit_tail: the PRINT USING format literal-scanners ------
; docs/spec-evict-printusing.md. These two are pure leaves (PU_* RAM + pchar), so
; they are EVICTED to sub-ROM page 0 (sub/printusing.asm) to free page-1 window
; space. The resident stubs CALSLT the tenant (which emits
; the literals into DETOKBUF), then drain DETOKBUF through print_string, honouring
; PRDEST — so PRINT# USING's file form (print.asm PRDEST=1) is untouched. The
; fragile value-render/deref paths (pu_do_number/pu_do_string/pu_fmt_int) stay
; resident, unchanged.
pu_to_field:
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_PU_TOFIELD
                call    subrom_call         ; tenant: emit leading literals -> DETOKBUF,
                                            ; set PU_TYPE/PU_W/PU_POS, A = no-field flag
                jp      c,subrom_absent_error
                push    af                  ; guard the no-field flag across the drain
                ld      hl,DETOKBUF
                call    print_string        ; drain literals -> pchar (PRDEST sink)
                pop     af                  ; A = 0 field found / 1 none
                or      a
                ret     z                   ; field -> CF clear
                scf                         ; no field -> CF set (pu_main: jr c,pu_endlist)
                ret
pu_emit_tail:
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_PU_TAIL
                call    subrom_call         ; tenant: emit trailing literals -> DETOKBUF
                jp      c,subrom_absent_error
                ld      hl,DETOKBUF
                jp      print_string        ; drain -> pchar (PRDEST), then ret

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
                call    pu_deref_body       ; HL -> source bytes
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
                call    pu_deref_body       ; HL -> bytes
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
                call    pu_deref_body       ; HL -> bytes
                ld      a,(hl)              ; A = first byte
                call    pchar
pus_done:
                pop     hl
                ret
