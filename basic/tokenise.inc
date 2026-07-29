; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; tokenise.inc — the tokeniser body (crunch ASCII line -> token stream).
; ===========================================================================
; Extracted from interp.asm so its PLACEMENT can be gated (subrom arc, wave 2,
; docs/spec-basic-subrom-wave2-tokeniser.md). Two homes:
;   * lean 16 KB cart (ROM_BASE >= $4000): interp.asm includes this inline,
;     byte-identical to the pre-extraction interp.asm.
;   * sub-ROM (sub/sub.asm, ROM_BASE=$2812): the WHOLE body is evicted to sub-ROM
;     page 0, reunited with the tk_float literal crunch (sub/tkfloat.asm) that
;     wave 1 already moved there. The repack MAIN ROM keeps only a two-line
;     `tokenise` dispatch stub (interp.asm) that CALSLTs this body once per line.
;
; Cold path: this runs only at line-entry / program-LOAD, never during RUN (the
; executor walks already-crunched tokens), so it fits the sub-ROM's page-0 tenant
; rule — pure buffer computation over page-2/3 RAM, no BIOS / low-region / ISR
; touch (leaf-audit, spec §3). The only non-RAM callees are pure leaves cloned
; sub-side: upcase (sub/tkfloat.asm), is_letter / is_ident_cont (sub/sub.asm),
; and tk_float itself, now an in-slot jump to the co-located crunch.
;
; Derived only from this project's own black-box oracle observations
; (basic-spec/docs/spec-tokenise.md, spec-tokens-statements.md) and the public
; MSX-BASIC language reference. No disassembly.
; ===========================================================================

; --- tokenise: ASCII line -> token stream ----------------------------------
; in:  HL = source (0-terminated ASCII), DE = destination buffer
; out: destination holds tokens, 0x00-terminated
; spec-tokenise.md / spec-tokens-statements.md: a keyword crunches to its token
; byte(s) (case-folded); string literals and other bytes are copied verbatim;
; REM (and the '\'' abbreviation) keep the rest of the line verbatim; the line
; is terminated by 0x00.
; External entry: reset the in-name flag, then run the per-char loop. Internal
; jumps target tk_loop (which preserves the flag across characters).
tokenise:
                xor     a
                ld      (TKNAME),a          ; a fresh line starts outside any name
    IF ROM_BASE < $4000
                ld      (TKOVF),a           ; ...and no float-literal overflow yet (F1,
    ENDIF                                   ;  basic/float.asm); A is still 0 here
tk_loop:
                ld      a,(TKNAME)
                ld      b,a                 ; B = were we inside a name? (digit rule)
                xor     a
                ld      (TKNAME),a          ; default after this char: not in a name
                ld      a,(hl)
                or      a
                jp      z,tk_end
                cp      '"'                 ; string literal: copy verbatim
                jp      z,tk_string
                cp      QUOTE_REM           ; "'" comment -> treat as REM
                jp      z,tk_apos
                cp      '0'                 ; a digit?
                jr      c,tk_nondigit
                cp      '9'+1
                jr      nc,tk_nondigit
                ; A digit continues a name (verbatim) only if we were in one;
                ; otherwise it begins a numeric constant. This is why `A1` keeps
                ; the '1' as $31 while `=1` crunches `1` to a number token.
                ld      a,b
                or      a
                jr      nz,tk_namedig
    IF ROM_BASE < $4000
                jp      tk_float            ; '0'..'9' starting a numeric constant
                                             ; (float-aware, basic/float.asm)
    ELSE
                jp      tk_number           ; '0'..'9' starting a numeric constant
    ENDIF
tk_namedig:
                ld      a,1
                ld      (TKNAME),a          ; the digit extends the name
                ld      a,(hl)              ; copy it verbatim
                ld      (de),a
                inc     de
                inc     hl
                jp      tk_loop
tk_nondigit:
    IF ROM_BASE < $4000
                cp      '.'                 ; '.'+digit leads a float literal (spec
                jr      nz,tk_nondot        ; §9.2); a lone '.' (no digit) stays
                push    hl                  ; verbatim below, like today
                inc     hl
                ld      a,(hl)
                pop     hl
                cp      '0'
                jr      c,tk_nondot
                cp      '9'+1
                jr      nc,tk_nondot
                jp      tk_float            ; basic/float.asm
tk_nondot:
    ENDIF
                cp      '&'                 ; "&H" hex constant
                jp      z,tk_hex
                call    match_kw            ; keyword match runs at EVERY position, so
                jr      nc,tk_notkw         ; reserved words inside a name still tokenise
                                            ; (SCORE -> SC,OR,E); TKNAME stays 0 here, so
                                            ; a keyword correctly breaks the name.
                cp      REM_TOKEN           ; REM swallows the rest of the line
                jp      z,tk_rem_rest
                cp      DATA_TOKEN          ; DATA body is stored verbatim (to ':')
                jp      z,tk_data_rest
                cp      CALL_TOKEN          ; CALL <name>: the device name is verbatim
                jp      z,tk_call_name      ; (oracle: `call format` keeps "FORMAT", not
                                            ;  FOR+MAT — the extended name is not crunched)
                call    branch_lineno       ; GOTO/GOSUB/THEN/… <n> -> $0E,<n LE>
                jp      tk_loop
tk_notkw:
                ld      a,(hl)              ; not a keyword
                cp      '='
                jp      z,tk_op_eq
                cp      '+'
                jp      z,tk_op_plus
                cp      '-'
                jp      z,tk_op_minus
                cp      '*'
                jp      z,tk_op_star
                cp      '<'
                jp      z,tk_op_lt
                cp      '>'
                jp      z,tk_op_gt
                cp      '/'
                jp      z,tk_op_div
                cp      '\'
                jp      z,tk_op_idiv
    IF ROM_BASE < $4000
                ; math pack slice 2c (repack-only -- docs/spec-basic-mathpack-
                ; slice2.md §13.3): '^' -> POW_TOKEN. Guarded so the lean 16 KB
                ; cart (assembled with this same shared file at ROM_BASE>=$4000)
                ; stays byte-identical -- lean has no `^` operator.
                cp      '^'
                jp      z,tk_op_pow
    ENDIF
                cp      '?'                 ; '?' abbreviates PRINT
                jp      z,tk_print_q
                cp      '_'                 ; '_' abbreviates CALL: the name is verbatim
                jp      z,tk_underscore
                call    is_letter           ; a letter starts / continues a name
                jr      c,tk_copy_up
tk_copy:
                ld      a,(hl)              ; punctuation / space: copy verbatim
                ld      (de),a
                inc     de
                inc     hl
                jp      tk_loop
tk_copy_up:
                ld      a,(hl)              ; a name letter, upcased (§4)
                call    upcase
                ld      (de),a
                inc     de
                inc     hl
                ld      a,1
                ld      (TKNAME),a          ; now inside a name
                jp      tk_loop
tk_string:
                ld      a,(hl)              ; opening quote
                ld      (de),a
                inc     de
                inc     hl
tk_str_loop:
                ld      a,(hl)
                or      a
                jr      z,tk_end            ; unterminated string -> just end
                ld      (de),a
                inc     de
                inc     hl
                cp      '"'                 ; copy through the closing quote
                jr      nz,tk_str_loop
                jp      tk_loop
tk_apos:
                ld      a,COLON             ; "'" -> $3A $8F $E6 (spec §3, byte-exact)
                ld      (de),a
                inc     de
                ld      a,REM_TOKEN
                ld      (de),a
                inc     de
                ld      a,APOS_MARK
                ld      (de),a
                inc     de
                inc     hl                  ; skip the "'"
tk_rem_rest:
                ld      a,(hl)              ; rest of line copied verbatim
                or      a
                jr      z,tk_end
                ld      (de),a
                inc     de
                inc     hl
                jr      tk_rem_rest
tk_data_rest:                               ; DATA body verbatim up to ':' or EOL
                ld      a,(hl)              ; (oracle: items stored as ASCII text;
                or      a                   ;  ':' ends DATA, the next statement is
                jp      z,tk_end            ;  crunched normally). Quoted ':' inside
                cp      COLON               ;  DATA is not special-cased (no strings).
                jp      z,tk_loop
                ld      (de),a
                inc     de
                inc     hl
                jr      tk_data_rest
tk_underscore:                              ; '_' (CALL abbreviation): copy it, then the
                ld      a,(hl)              ; device name verbatim (no keyword crunch).
                ld      (de),a
                inc     de
                inc     hl
                ; fall through into tk_call_name
tk_call_name:                               ; copy any spaces, then the device name —
                ld      a,(hl)              ; identifier chars upcased + verbatim, NOT
                cp      ' '                 ; keyword-crunched — then resume tokenising.
                jr      nz,tcn_name
                ld      (de),a              ; keep the space (oracle: `call format` ->
                inc     de                  ;  CA 20 46 4F 52 4D 41 54)
                inc     hl
                jr      tk_call_name
tcn_name:
                ld      a,(hl)
                call    is_ident_cont       ; letter / digit continues the name
                jp      nc,tk_loop          ; name ended -> normal tokenising for the rest
                call    upcase
                ld      (de),a
                inc     de
                inc     hl
                jr      tcn_name
tk_end:
                xor     a
                ld      (de),a              ; 0x00 terminator
    IF ROM_BASE < $4000
                ; D-LINEMAX R-2 (docs/spec-basic-linemax.md §2): the crunch is BOUNDED.
                ; Refuse a body longer than TOKMAX_BODY (314) -- the reference's measured
                ; ceiling, where it prints `Line buffer overflow` and stores nothing
                ; (characterization §2: 314 accepted / 315 refused, walked a byte at a
                ; time). TKOVF=2 is the reject reason; dispatch_line adjudicates it at
                ; line ENTRY, exactly like the =1 float-literal reject, so an over-long
                ; line is never executed and never stored.
                ;
                ; ONE site, at the true end of the crunch, and that is deliberate: the
                ; verbatim inner loops (tk_str_loop / tk_rem_rest / tk_data_rest) never
                ; re-enter tk_loop, so a per-character test at the loop head would MISS
                ; them. They are 1:1 and LINEMAX-bounded, so TOKBUF absorbs the overshoot
                ; (sysvars.inc) and the adjudication happens here, where the body length
                ; is final and the bound is provable rather than audited.
                push    hl                  ; HL = source cursor; callers don't read it,
                                            ; but tokenise's contract doesn't promise it
                ld      hl,-(TOKBUF+TOKMAX_BODY+1)
                add     hl,de               ; CF <=> DE >= TOKBUF+315, i.e. body > 314
                pop     hl                  ; (pop preserves flags)
                jr      nc,tke_fits
                ld      a,(TKOVF)           ; FIRST reject wins: sub/tkfloat.asm sets =1
                or      a                   ; mid-line and jumps straight here, and that
                jr      nz,tke_fits         ; overflow happened BEFORE the body ran long
                ld      a,25                ; the reject reason IS the ERR code (=25), so
                ld      (TKOVF),a           ; dispatch_line needs no second constant --
                                            ; page-1 room, see program.asm dl_overflow
tke_fits:
    ENDIF
                ret

; --- tk_op_*: emit an operator token (spec §4) -----------------------------
tk_op_eq:
                ld      a,EQ_TOKEN
                jr      tk_op_emit
tk_op_plus:
                ld      a,PLUS_TOKEN
                jr      tk_op_emit
tk_op_minus:
                ld      a,MINUS_TOKEN
                jr      tk_op_emit
tk_op_star:
                ld      a,STAR_TOKEN
                jr      tk_op_emit
tk_op_lt:
                ld      a,LT_TOKEN
                jr      tk_op_emit
tk_op_gt:
                ld      a,GT_TOKEN
tk_op_emit:
                ld      (de),a
                inc     de
                inc     hl
                jp      tk_loop
tk_print_q:                                 ; '?' -> PRINT token (oracle: ? -> $91)
                ld      a,PRINT_TOKEN
                jr      tk_op_emit
tk_op_div:
                ld      a,DIV_TOKEN
                jr      tk_op_emit
tk_op_idiv:
                ld      a,IDIV_TOKEN
                jr      tk_op_emit
    IF ROM_BASE < $4000
tk_op_pow:
                ld      a,POW_TOKEN
                jr      tk_op_emit
    ENDIF

    IF ROM_BASE >= $4000
; --- tk_number: crunch a decimal integer constant (spec §3) ----------------
;   0..9   -> $11+n          10..255 -> $0F,<byte>
;   256..  -> $1C,<word LE>  (>=32768 diverges from the reference's float form,
;                             which is out of scope this step — use &H instead)
; HL = source cursor, DE = destination cursor. DE is parked on the stack while
; the value is accumulated in DE; HL is parked during each *10 step.
;
; LEAN BUILD ONLY. The repack build routes a leading digit/`.` to tk_float (the
; float-aware literal crunch, sub/tkfloat.asm), whose integer path exits through
; tkf_emit_int_bc, so tk_number is never reached there — gating it out keeps it
; from consuming sub-ROM / repack page bytes (docs/spec-basic-subrom-wave2-
; tokeniser.md §3). The lean 16 KB cart has no float pack, so it keeps this
; integer-only crunch inline, byte-identical.
tk_number:
                push    de                  ; save destination cursor
                ld      de,0                ; DE = accumulated value
tk_num_lp:
                ld      a,(hl)
                cp      '0'
                jr      c,tk_num_done
                cp      '9'+1
                jr      nc,tk_num_done
                sub     '0'                 ; A = digit
                ld      c,a
                push    hl                  ; DE = DE*10 + C
                ld      h,d
                ld      l,e
                add     hl,hl               ; 2*acc
                add     hl,hl               ; 4*acc
                add     hl,de               ; 5*acc
                add     hl,hl               ; 10*acc
                ld      e,c
                ld      d,0
                add     hl,de               ; +digit
                ex      de,hl               ; DE = new acc
                pop     hl                  ; restore source cursor
                inc     hl
                jr      tk_num_lp
tk_num_done:
                ld      b,d
                ld      c,e                 ; BC = value
                pop     de                  ; restore destination cursor
                ld      a,b
                or      a
                jr      nz,tk_num_w         ; >=256 -> two-byte form
                ld      a,c
                cp      10
                jr      nc,tk_num_b         ; 10..255 -> one-byte form
                add     a,INT_DIGIT_BASE    ; 0..9 -> $11+n
                ld      (de),a
                inc     de
                jp      tk_loop
tk_num_b:
                ld      a,INT1_TOKEN
                ld      (de),a
                inc     de
                ld      a,c
                ld      (de),a
                inc     de
                jp      tk_loop
tk_num_w:
                ld      a,INT2_TOKEN
                ld      (de),a
                inc     de
                ld      a,c                 ; value low
                ld      (de),a
                inc     de
                ld      a,b                 ; value high
                ld      (de),a
                inc     de
                jp      tk_loop
    ENDIF

; --- tk_hex: crunch "&H" hex / "&O" octal constants -> $0C / $0B,<word LE> ---
; Oracle (basic_probe_crunch.py): the reference crunches `&H<hex>` to
; $0C,<value16 LE> and `&O<oct>` to $0B,<value16 LE> (HEX_TOKEN / OCT_TOKEN),
; full 0..&HFFFF — same shape as $1C int constants. `&B` and a bare `&` are
; copied VERBATIM: the VG-8020 has no `&B` binary token (oracle showed
; `a=&b1010` crunches to `& B 1 0 1 0` ASCII), so we must not invent one — `&B`
; is a documented own-design descope (PROVENANCE.md, quarantined). The single
; accumulator loop is parameterised by base (B) and token (C): hex *16 over
; 0-9 A-F, octal *8 over 0-7.
tk_hex:
                inc     hl                  ; past '&'
                ld      a,(hl)
                call    upcase
                cp      'H'
                jr      z,tk_hex_h
                cp      'O'
                jr      z,tk_hex_o
                dec     hl                  ; not &H/&O (&B, bare &) -> copy '&' verbatim
                jp      tk_copy
tk_hex_h:
                ld      a,16                ; hex: radix 16, accumulate over 0-9 A-F
                ld      (TKRADIX),a
                ld      a,HEX_TOKEN
                ld      (TKRTOK),a
                jr      tk_hex_go
tk_hex_o:
                ld      a,8                 ; octal: radix 8, accumulate over 0-7
                ld      (TKRADIX),a
                ld      a,OCT_TOKEN
                ld      (TKRTOK),a
tk_hex_go:
                inc     hl                  ; past the H / O
                push    de                  ; save destination cursor
                ld      de,0                ; DE = value
tk_hex_lp:
                ld      a,(hl)
                call    upcase
                cp      '0'
                jr      c,tk_hex_done       ; below '0' -> end of digits
                ld      c,a                 ; C = the upcased source char
                ld      a,(TKRADIX)
                cp      8
                jr      z,tk_hex_oct        ; octal: only '0'..'7'
                ; hex digit test: '0'..'9','A'..'F'
                ld      a,c
                cp      '9'+1
                jr      c,tk_hex_dig        ; '0'..'9'
                cp      'A'
                jr      c,tk_hex_done
                cp      'F'+1
                jr      nc,tk_hex_done
                sub     'A'-10              ; 'A'..'F' -> 10..15
                jr      tk_hex_acc
tk_hex_oct:                                 ; octal digit test: '0'..'7'
                ld      a,c
                cp      '7'+1
                jr      nc,tk_hex_done
                sub     '0'                 ; '0'..'7' -> 0..7
                jr      tk_hex_acc
tk_hex_dig:
                ld      a,c
                sub     '0'                 ; '0'..'9' -> 0..9
tk_hex_acc:
                ld      c,a                 ; digit value
                push    hl                  ; DE = DE*radix + digit
                ld      h,d
                ld      l,e
                ld      a,(TKRADIX)
                add     hl,hl               ; *2  (both radices)
                add     hl,hl               ; *4
                add     hl,hl               ; *8
                cp      8
                jr      z,tk_hex_mac        ; octal stops at *8
                add     hl,hl               ; *16 (hex)
tk_hex_mac:
                ld      e,c
                ld      d,0
                add     hl,de               ; + digit
                ex      de,hl               ; DE = new value
                pop     hl
                inc     hl
                jr      tk_hex_lp
tk_hex_done:
                ld      b,d
                ld      c,e                 ; BC = value
                pop     de                  ; restore destination cursor
                ld      a,(TKRTOK)          ; HEX_TOKEN ($0C) or OCT_TOKEN ($0B)
                ld      (de),a
                inc     de
                ld      a,c                 ; value low
                ld      (de),a
                inc     de
                ld      a,b                 ; value high
                ld      (de),a
                inc     de
                jp      tk_loop

; --- match_kw: is a table keyword present at (HL)? -------------------------
; in:  HL = source position, DE = destination cursor
; out: CF set   -> match: token byte(s) emitted to (DE), DE advanced, HL past
;                  the keyword, A = first token byte
;      CF clear -> no match: HL and DE unchanged
; Uses IX as the table cursor and IY as the keyword-char walker.
match_kw:
                push    iy
                ld      ix,kwtable
mk_entry:
                ld      a,(ix+0)            ; keyword length (0 = end of table)
                or      a
                jr      z,mk_none
                push    hl                  ; remember source start
                push    ix
                pop     iy
                inc     iy                  ; IY -> keyword chars
                ld      b,a                 ; B = chars to compare
mk_cmp:
                ld      a,(iy+0)            ; keyword char (stored uppercase)
                ld      c,a
                ld      a,(hl)              ; source char
                call    upcase              ; case-fold before comparing
                cp      c
                jr      nz,mk_fail
                inc     hl
                inc     iy
                djnz    mk_cmp
                ; matched: IY -> token-length byte, HL advanced past keyword
                pop     bc                  ; discard saved source start
                ld      a,(iy+0)            ; token length
                ld      b,a
                inc     iy                  ; IY -> token bytes
                ld      c,(iy+0)            ; remember first token byte
mk_emit:
                ld      a,(iy+0)
                ld      (de),a
                inc     iy
                inc     de
                djnz    mk_emit
                ld      a,c                 ; A = first token byte
                pop     iy                  ; restore caller IY
                scf
                ret
mk_fail:
                pop     hl                  ; restore source start
                ld      a,(ix+0)            ; klen
                ld      b,0
                ld      c,a
                inc     bc                  ; skip [klen][chars]
                add     ix,bc               ; IX -> token-length byte
                ld      a,(ix+0)            ; tlen
                ld      b,0
                ld      c,a
                inc     bc                  ; skip [tlen][tokens]
                add     ix,bc               ; IX -> next entry
                jr      mk_entry
mk_none:
                pop     iy                  ; restore caller IY
                or      a                   ; CF clear (no match)
                ret

; --- branch_lineno: emit a line-number reference after a branch keyword ------
; A = first token byte just emitted by match_kw, HL = source cursor (after the
; keyword), DE = dest cursor. If the keyword was GOTO/GOSUB/THEN/RESTORE/RUN, copy
; any spaces verbatim then, if a decimal number follows, emit it as the
; line-number identification code $0E,<value LE> (Figure 2.12) instead of the
; ordinary integer encoding. Otherwise returns unchanged. (ELSE <line> is not
; specially handled yet.) ON…GOTO/GOSUB comma-separated lists ARE handled, empty
; slots included — see bl_num.
branch_lineno:
                cp      GOTO_TOKEN
                jr      z,bl_yes
                cp      GOSUB_TOKEN
                jr      z,bl_yes
                cp      THEN_TOKEN
                jr      z,bl_yes
                cp      RESTORE_TOKEN
                jr      z,bl_yes
                cp      RUN_TOKEN
                jr      z,bl_yes
    IF ROM_BASE < $4000
                cp      RESUME_TOKEN        ; RESUME <line> / RESUME 0 (error-handling S2b,
                jr      z,bl_yes            ; repack-only): crunch the following number as
                                            ; $0E, like GOTO. RESUME NEXT / bare RESUME are
                                            ; unaffected (no digit follows -> bl_num returns
                                            ; without emitting). Lean stays byte-identical.
    ENDIF
                ret                         ; not a branch keyword
bl_yes:
                ld      a,(hl)              ; copy spaces verbatim
                cp      ' '
                jr      nz,bl_num
                ld      (de),a
                inc     de
                inc     hl
                jr      bl_yes
bl_num:
                ; AN EMPTY LIST SLOT MUST NOT END THE LIST. `ON KEY GOSUB 100,,600`
                ; and `ON STRIG GOSUB ,300` are legal on the reference: an omitted
                ; entry CLEARS that slot's handler and the list continues. Without
                ; this test the list-extension loop below reached a `,` here, found
                ; no digit and RETURNED, so every later target was crunched as an
                ; ordinary numeric literal instead of $0E,<line> -- and the trap
                ; parsers, which look for $0E, then ran off the end of their list
                ; and left the executor on a bare literal: `syntax error in 10`.
                ; Found by the T3 gate's K7 case (`ON KEY GOSUB 100,,,,,600`), but
                ; the bug is OLDER than T3 and is NOT KEY-specific -- it is in this
                ; SHARED crunch path, so T2's shipped `ON STRIG GOSUB ,300` had it
                ; too. That case passes in the T2 gate only because a syntax error
                ; and a correctly-cleared slot both leave the fire count at 0; the
                ; T2 gate has no `done` sentinel to tell them apart, which is
                ; exactly the "a baseline that cannot produce a non-zero answer
                ; proves nothing" trap this arc keeps re-learning.
                ; Placed at bl_num rather than in the loop tail so it also covers a
                ; list whose FIRST slot is empty (`GOSUB ,600`), where the comma
                ; follows the keyword directly and the loop has not started yet.
                ; REPACK-ONLY, like the RESUME crunch above and for the same reason:
                ; these 4 bytes overran the lean 16 KB cart's $8000 ceiling, which
                ; is byte-full. The lean build therefore KEEPS this bug. That is the
                ; documented response to a lean overflow (basic/main.asm's ceiling
                ; guard: "gate the feature on ROM_BASE or trim it"), and it costs
                ; the lean cart nothing it has: the interrupt traps whose parsers
                ; this unblocks are themselves repack-only.
    IF ROM_BASE < $4000
                cp      ','
                jr      z,bl_list
    ENDIF
                cp      '0'                 ; a decimal number must follow
                ret     c
                cp      '9'+1
                ret     nc
                push    de                  ; park dest while accumulating
                ld      de,0                ; DE = value
bl_acc:
                ld      a,(hl)
                cp      '0'
                jr      c,bl_done
                cp      '9'+1
                jr      nc,bl_done
                sub     '0'
                ld      c,a
                push    hl                  ; DE = DE*10 + C
                ld      h,d
                ld      l,e
                add     hl,hl
                add     hl,hl
                add     hl,de
                add     hl,hl
                ld      e,c
                ld      d,0
                add     hl,de
                ex      de,hl
                pop     hl
                inc     hl
                jr      bl_acc
bl_done:
                ld      b,d
                ld      c,e                 ; BC = line number
                pop     de                  ; restore dest cursor
                ld      a,LINENO_TOKEN      ; $0E
                ld      (de),a
                inc     de
                ld      a,c                 ; value low
                ld      (de),a
                inc     de
                ld      a,b                 ; value high
                ld      (de),a
                inc     de
                ; extend for ON…GOTO/GOSUB comma-separated lists
                ld      a,(hl)
                cp      ','
                ret     nz                  ; no comma -> single target, done
bl_list:
                ld      (de),a              ; emit the comma verbatim
                inc     de
                inc     hl                  ; past the comma
                jr      bl_yes              ; loop: spaces then next slot (a number,
                                            ; another comma = an empty slot, or
                                            ; anything else = end of the list)
