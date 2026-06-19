; interp.asm — the tokeniser + execution-loop front-end.
;
; A small interpreter spine: crunch an ASCII line into tokens, then walk the
; line statement-by-statement (separated by ':'), dispatching each on its
; leading token. Statements implemented: BLOAD (cassette load + ,R handoff),
; POKE, a single-letter variable assignment, and REM (comment). PEEK is a
; function handled inside the expression evaluator.
;
; Derived only from this project's own black-box oracle observations
; (cbios-basic/docs/spec-tokenise.md, spec-tokens-statements.md) and the public
; MSX-BASIC language reference. No disassembly.

; --- INIT entry (cartridge header points here) -----------------------------
init:
                ei                          ; keyboard ISR must run for CHGET
                call    clear_vars          ; deterministic variable table
                call    show_title          ; startup header lines
                jp      repl                ; read/eval loop (never returns)

; --- tokenise: ASCII line -> token stream ----------------------------------
; in:  HL = source (0-terminated ASCII), DE = destination buffer
; out: destination holds tokens, 0x00-terminated
; spec-tokenise.md / spec-tokens-statements.md: a keyword crunches to its token
; byte(s) (case-folded); string literals and other bytes are copied verbatim;
; REM (and the '\'' abbreviation) keep the rest of the line verbatim; the line
; is terminated by 0x00.
tokenise:
                ld      a,(hl)
                or      a
                jp      z,tk_end
                cp      '"'                 ; string literal: copy verbatim
                jp      z,tk_string
                cp      QUOTE_REM           ; "'" comment -> treat as REM
                jp      z,tk_apos
                cp      '0'                 ; digit -> numeric constant
                jr      c,tk_nondigit
                cp      '9'+1
                jp      c,tk_number         ; '0'..'9'
tk_nondigit:
                cp      '&'                 ; "&H" hex constant
                jp      z,tk_hex
                call    match_kw            ; CF set: keyword token(s) emitted
                jr      nc,tk_notkw
                cp      REM_TOKEN           ; REM swallows the rest of the line
                jp      z,tk_rem_rest
                jp      tokenise
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
                call    is_letter           ; variable / option letter
                jr      c,tk_copy_up
tk_copy:
                ld      a,(hl)              ; punctuation / space: copy verbatim
                ld      (de),a
                inc     de
                inc     hl
                jp      tokenise
tk_copy_up:
                ld      a,(hl)              ; letters upcased outside strings (§4)
                call    upcase
                ld      (de),a
                inc     de
                inc     hl
                jp      tokenise
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
                jr      tokenise
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
tk_end:
                xor     a
                ld      (de),a              ; 0x00 terminator
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
tk_op_emit:
                ld      (de),a
                inc     de
                inc     hl
                jp      tokenise

; --- tk_number: crunch a decimal integer constant (spec §3) ----------------
;   0..9   -> $11+n          10..255 -> $0F,<byte>
;   256..  -> $1C,<word LE>  (>=32768 diverges from the reference's float form,
;                             which is out of scope this step — use &H instead)
; HL = source cursor, DE = destination cursor. DE is parked on the stack while
; the value is accumulated in DE; HL is parked during each *10 step.
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
                jp      tokenise
tk_num_b:
                ld      a,INT1_TOKEN
                ld      (de),a
                inc     de
                ld      a,c
                ld      (de),a
                inc     de
                jp      tokenise
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
                jp      tokenise

; --- tk_hex: crunch a "&H" hex constant -> $0C,<word LE> (spec §3) ----------
; "&O"/"&B"/bare "&" are out of scope: emit the '&' verbatim and resume.
tk_hex:
                inc     hl                  ; past '&'
                ld      a,(hl)
                call    upcase
                cp      'H'
                jr      z,tk_hex_h
                dec     hl                  ; not &H -> copy the '&' verbatim
                jp      tk_copy
tk_hex_h:
                inc     hl                  ; past 'H'
                push    de                  ; save destination cursor
                ld      de,0                ; DE = value
tk_hex_lp:
                ld      a,(hl)
                call    upcase
                cp      '0'
                jr      c,tk_hex_done
                cp      '9'+1
                jr      c,tk_hex_dig        ; '0'..'9'
                cp      'A'
                jr      c,tk_hex_done
                cp      'F'+1
                jr      nc,tk_hex_done
                sub     'A'-10              ; 'A'..'F' -> 10..15
                jr      tk_hex_acc
tk_hex_dig:
                sub     '0'
tk_hex_acc:
                ld      c,a                 ; nibble
                push    hl                  ; DE = DE*16 + nibble
                ld      h,d
                ld      l,e
                add     hl,hl
                add     hl,hl
                add     hl,hl
                add     hl,hl               ; acc*16
                ld      e,c
                ld      d,0
                add     hl,de               ; + nibble
                ex      de,hl               ; DE = new value
                pop     hl
                inc     hl
                jr      tk_hex_lp
tk_hex_done:
                ld      b,d
                ld      c,e                 ; BC = value
                pop     de                  ; restore destination cursor
                ld      a,HEX_TOKEN
                ld      (de),a
                inc     de
                ld      a,c                 ; value low
                ld      (de),a
                inc     de
                ld      a,b                 ; value high
                ld      (de),a
                inc     de
                jp      tokenise

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

; keyword -> token table. Entry layout: [klen][UPPERCASE chars][tlen][token...].
; Terminated by a 0 length byte. Tokens are oracle-sourced (spec-tokenise.md,
; spec-tokens-statements.md). PEEK is a two-byte function token ($FF $97).
kwtable:
                db      5,"BLOAD",1,BLOAD_TOKEN
                db      4,"POKE",1,POKE_TOKEN
                db      4,"PEEK",2,PEEK_PREFIX,PEEK_TOKEN
                db      3,"REM",1,REM_TOKEN
                db      0

; --- upcase: fold A to uppercase if it is 'a'..'z' -------------------------
; Preserves BC/DE/HL. Source: ASCII (allowed).
upcase:
                cp      'a'
                ret     c                   ; below 'a'
                cp      'z'+1
                ret     nc                  ; above 'z'
                sub     $20
                ret

; --- is_letter: CF set if A is 'A'..'Z' or 'a'..'z' (A preserved) ----------
is_letter:
                push    af
                call    upcase
                cp      'A'
                jr      c,il_no
                cp      'Z'+1
                jr      nc,il_no
                pop     af
                scf
                ret
il_no:
                pop     af
                or      a                   ; CF clear
                ret

; --- exec: walk the line, dispatching each statement -----------------------
; in: HL = token buffer (0x00-terminated). Statements are separated by ':'.
; Returns to the REPL at end of line (or hands off via BLOAD,R, never to return).
exec:
exec_stmt:
                call    skip_spaces         ; leading spaces are skipped (spec §5)
                ld      a,(hl)
                or      a
                ret     z                   ; end of line -> back to the prompt
                cp      COLON               ; ':' separator / empty statement
                jr      z,ex_sep
                cp      BLOAD_TOKEN
                jp      z,ex_bload
                cp      POKE_TOKEN
                jp      z,ex_poke
                cp      REM_TOKEN
                jr      z,ex_rem
                call    is_letter           ; bare letter -> assignment
                jr      c,ex_let
                jp      stmt_error
ex_sep:
                inc     hl
                jr      exec_stmt
ex_rem:
                ret                         ; rest of line is a comment -> done
ex_bload:
                inc     hl                  ; HL -> args (past the BLOAD token)
                jp      do_bload
ex_poke:
                inc     hl                  ; HL -> args (past the POKE token)
                jp      do_poke

; --- ex_let: single-letter assignment  <var> = <expr> ----------------------
ex_let:
                ld      a,(hl)              ; variable name
                push    af
                inc     hl
                call    skip_spaces
                ld      a,(hl)
                cp      EQ_TOKEN            ; '=' crunches to $EF (spec §4)
                jr      nz,ex_let_err
                inc     hl
                call    eval                ; DE = value, HL = cursor
                pop     af                  ; A = variable name
                push    hl                  ; guard cursor across var_set
                call    var_set             ; var[name] = DE
                pop     hl
                jp      exec_stmt           ; continue the line
ex_let_err:
                pop     af
                jp      stmt_error

; --- skip_spaces: advance HL past 0x20 bytes -------------------------------
skip_spaces:
                ld      a,(hl)
                cp      ' '
                ret     nz
                inc     hl
                jr      skip_spaces

; --- stmt_error: unknown statement — report and return to the prompt -------
stmt_error:
                ld      a,$DD               ; distinct from BLOAD's $EE tape error
                ld      (ERRMARK),a
                ld      hl,err_syntax
                call    print_string
                ret
err_syntax:
                db      "syntax error",13,10,0
