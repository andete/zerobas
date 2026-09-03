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
; 🔴 THE PARAGRAPH THAT STOOD HERE IS STALE, AND ITS CONDITION HAS BEEN MET.
; It read: "This is the COMPLETE feature for zerobas's current numeric domain
; (integers): the float-only format specs — the decimal point '.', exponential
; '^^^^', and the '+'/'-'/','/'**'/'$$' embellishments — arrive with Phase-3
; floats. The '_' literal-escape is likewise deferred."
; FLOATS HAVE ARRIVED (SNG/DBL tokens, the float-pack arc is concluded,
; `PRINT 1.5` renders), so the deferral's own precondition is satisfied and the
; specs are simply MISSING. Measured 2026-09-02 (D-PUSING,
; scratchpad/pusing_probe.py), both references agreeing on every one:
;
;   PRINT USING"##.##";1.5        refs ` 1.50`      here ` 1.`
;   PRINT USING"##.##";5          refs ` 5.00`      here ` 5.`
;   PRINT USING"#,###";1234       refs `1,234`      here `%1234,`
;   PRINT USING"+##";5            refs ` +5`        here `+ 5`
;   PRINT USING"##-";5            refs ` 5 `        here ` 5-`
;   PRINT USING"**##";5           refs `***5`       here `** 5`
;   PRINT USING"##.##^^^^";1.5    refs ` 1.50E+00`  here ` 1.`
;
; ⚠️ READ AS CURRENT, THE OLD TEXT PRICED THE FEATURE OUT OF EXISTENCE -- the
; same trap play.asm's "NO live drain" header sprang on D-PLAYFN. `_` and `$$`
; are NOT in that list: `_` agrees on all three today, and `$$` is a
; REFERENCES-DISAGREE row (vg8020 `  $5` vs cf3300 `$$ 5`, and this tree matches
; the CF-3300). Filed in TODO.md; unpriced.
; [[a-fix-falsifies-the-justification-beside-it]]
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

; 🔴 D-PUSING (docs/spec-basic-pusing.md): 18 rows x 3 machines, 13 DIFF. This
; head answered ERR 2 for everything malformed and SILENTLY COMPLETED for two
; whole shapes. The references distinguish FIVE cases and this routine now does
; too:
;
;   no format at all (EOL or ':')                     -> 24 Missing operand
;   format present but NOT a string                   -> 13 Type mismatch
;   format present, separator absent or ','           ->  2 Syntax error
;   ';' present, no values, format HAS a field        -> 24 Missing operand
;   ';' present, format has NO field (values or not)  ->  5 Illegal function call
;
; ⚠️ AND `,` IS NOT A SEPARATOR HERE, THOUGH IT IS BETWEEN VALUES. `PRINT
; USING"##",5` is ERR 2 on both references and printed here; `PRINT USING"##";1,2`
; is fine on all three. Two commas, two grammatical positions, two answers --
; measured separately, because carrying one row's answer into the other is
; exactly how the first prediction for this slice went wrong.
ex_print_using:
                inc     hl                  ; past the USING token
                ; The EOL/':' test must come FIRST, and that is what SPLITS the
                ; old shared `jp nc,stmt_error`: str_eval declines both for "there
                ; is nothing here" and for "there is something and it is not a
                ; string", and the references answer 24 and 13 respectively. With
                ; the missing case taken off the front, an NC below can only mean
                ; the second. (req_operand IS that test -- D-NGRAM2, interp.asm;
                ; sharing it does not move the split, it only stops open-coding it.)
                call    req_operand         ; `PRINT USING` / `PRINT USING:` -> ERR 24
                call    str_eval            ; STRPTR -> the format [len][bytes]
                jp      nc,type_mismatch_error  ; `PRINT USING 5` -> ERR 13 (0 B:
                                            ; the same instruction, retargeted)
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
                ; ONLY ';' separates the format from the value list. A ',' here,
                ; or nothing at all, is ERR 2 on both references -- and this used
                ; to accept the comma and fall through on neither. -3 B.
                call    skip_spaces
                cp      ';'
                jp      nz,stmt_error       ; ',' / EOL / a bare value -> ERR 2
                inc     hl
                xor     a
                ld      (PU_POS),a
                ld      (PU_FLAGS),a
                ; 🔴 A FIELD-LESS FORMAT IS AN ERROR IN EVERY CASE, NOT "literal
                ; text, well-defined". `PRINT USING"abc";` and `PRINT USING"abc";5`
                ; are BOTH ERR 5 on both references, and `PRINT USING"abc"` is
                ; ERR 2 (caught by the separator test above). The old
                ; pu_literal_only path emitted the format and swallowed the value
                ; list -- behaviour NEITHER reference has -- so it is deleted, and
                ; deleting it is what pays for this slice.
                push    hl                  ; pu_has_field clobbers HL (the token cursor)
                call    pu_has_field
                pop     hl
                jp      nc,pu_ifc           ; no field -> ERR 5, values or not
                ; ';' present and the format has a field: at least one value is
                ; REQUIRED. pu_main's own end-of-list test cannot serve here --
                ; it is also reached from pu_msep after a TRAILING separator,
                ; which is legal and suppresses the newline.
                call    req_operand         ; `PRINT USING"##";` -> ERR 24
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

; D-PUSING: pu_literal_only / pu_lo_skip / pu_lo_end DELETED (30 B). They
; implemented "a format with no field char is literal text: emit it, swallow any
; value list, newline" -- which is not what either reference does. Measured:
; `PRINT USING"abc"` is ERR 2, `PRINT USING"abc";` and `PRINT USING"abc";5` are
; ERR 5, and nothing is printed in any of them (CSRLIN unmoved). The block had
; exactly ONE incoming jump, so once that jump became `jp nc,pu_ifc` it was
; unreachable and `make deadcode` would have refused the build -- the gate is
; what turns "this is now wrong" into "this cannot be left behind".
; D-DUPSUPPLY: an ALIAS, not a ninth copy. These two instructions were
; byte-identical to `gb_illegal` (interp.asm) -- which already carries EIGHT
; names (eoi_err5/fchk_ifc/gfx_absent/gfx_err5/pl_absent/snd_illegal/
; strig_illegal) -- and `tools/dupspan_indep.py --samereg` decides the collapse
; from the ROM BYTES: terminates, no escaping relative jump, no fallthrough
; entry, and the canonical is in the SAME region (both page 1, so no tenant sees
; an address that is switched out). The one incoming jump was ALREADY a `jp`
; (`jp nc,pu_ifc` above), so nothing widens and the 5 B is net.
; 🎯 THIS IS THE WHOLE REMAINING SUPPLY. The sweep's 26 groups are 163 B nominal
; and price out at 5 B same-region -- every larger pair dies on "a relative jump
; leaves the span" or "runs off its end", exactly as the item predicted for LOOP
; BODIES. The NAME and its call site survive; only the second copy goes.
pu_ifc          equ     gb_illegal

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
                ; --- D-PUNUM: route by TYPE ------------------------------------
                ; The integer path is already right for FACTYP==2 (32767 and
                ; -32768 both agree with the references) and is cheaper, so it
                ; stays. Everything else -- a fraction, or a magnitude past int16
                ; -- goes to the sub-ROM renderer, which formats with the main
                ; ROM's OWN flt_fmt and rounds half-up. Before this, `eval` handed
                ; back a float and DE was read anyway: `USING"#######";1234567`
                ; printed 0. docs/spec-basic-pufloat.md §5.
                ld      a,(FACTYP)
                cp      2
                jr      z,pu_num_int
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_PUNUM
                call    subrom_call
                jp      c,subrom_absent_error
                ld      b,a                 ; the rendered length
                jr      pu_num_typed
pu_num_int:
                call    pu_fmt_int          ; NUMBUF = "[-]digits",0 ; B = length
pu_num_typed:
                ; D-PUSIGN: `+`/`-` sign placement, done sub-side (pure RAM over
                ; NUMBUF; ~60 B, and page 1 had 50). Returns the new length in A.
                ld      a,(PU_FLAGS)
                bit     3,a
                jr      z,pu_num_nosign
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_PUSIGN
                call    subrom_call
                jp      c,subrom_absent_error
                ld      b,a                 ; the rewritten length
pu_num_nosign:
                ld      a,(PU_W)
                sub     b                   ; pad = width - length
                jr      c,pu_num_over       ; length > width -> overflow
                jr      z,pu_num_emit
                ld      b,a                 ; B = pad count
                ; D-PUSTAR: `**` in the format pads with asterisks. The character
                ; is chosen ONCE, not per iteration, and carried on the stack
                ; because pchar does not promise A back.
                ld      a,(PU_FLAGS)
                bit     2,a
                ld      a,' '
                jr      z,pu_num_pad
                ld      a,'*'
pu_num_pad:
                push    af
                call    pchar
                pop     af
                djnz    pu_num_pad
                jr      pu_num_emit
                ; D-PUCARVE: the overflow arm ends the same four instructions as
                ; the normal one, so it FALLS THROUGH instead of repeating them --
                ; 8 B of duplicated tail for a 2 B jump, net +6 B in a page 1 that
                ; had TWELVE. It has to sit here, before pu_num_emit, for the
                ; fallthrough to exist; the two `jr`s above still reach both.
pu_num_over:
                ld      a,'%'               ; field overflow marker (MSX)
                call    pchar
pu_num_emit:
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
; D-DUPSPAN2: an ALIAS, not a second copy -- byte-identical to print_string,
; and POSITION-INDEPENDENT by tools/dupspan_indep.py (terminates, no
; escaping relative jump, not entered by fallthrough, same ROM region).
; The NAME and every call site survive; un-alias here for a distinct face.
pu_emit_str0    equ     print_string

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
