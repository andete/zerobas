; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; expr.asm — 16-bit integer expression evaluator.
;
; Evaluates an expression from the token/char stream. Grammar (small,
; precedence-climbing):
;
;   rel    := expr [ relop expr ]   (relop: < = > and compound <= >= <>)
;   expr   := term  { ('+' | '-') term }
;   term   := factor { '*' factor }
;   factor := const | letter(variable) | 'PEEK' '(' rel ')'
;           | 'VPEEK' '(' rel ')' | 'INP' '(' rel ')'
;           | 'VARPTR' '(' var ')' | 'BASE' '(' rel ')'
;           | '(' rel ')' | '-' factor
;
; A comparison yields -1 (true) or 0 (false). `eval` enters at `rel`; the bare
; arithmetic entry `ev_e` is still used where a relational makes no sense.
;
; The stream is the *crunched* token line (spec-tokens-statements.md §3/§4):
; constants arrive as their real MSX-BASIC tokens ($11+n digit, $0F+byte,
; $1C+word, $0C+word for &H) carrying a binary value; operators are tokens
; ('+' $F1, '-' $F2, '*' $F3); '(' ')' stay verbatim; PEEK is its two-byte
; function token ($FF $97); a variable is a single upcased letter. The evaluator
; *decodes* these tokens. All arithmetic is unsigned 16-bit, low-word on overflow.
;
; Clean-room: original code. POKE/PEEK *semantics* from the public MSX-BASIC
; language reference; the evaluator algorithm is our own. No disassembly.
;
; Cursor lives in IX throughout, which frees HL/DE/BC for arithmetic. The public
; wrapper converts to/from the caller's HL convention.

; --- eval: HL = cursor in -> DE = value, HL advanced past the expression -----
; Preserves the caller's IX. Clobbers A, BC, DE, HL.
eval:
                push    ix
                push    hl
                pop     ix                  ; IX = cursor
    IF ROM_BASE < $4000
                ld      a,2
                ld      (FACTYP),a          ; §9.4: eval() sets FACTYP=2 (int) on entry
    ENDIF
                call    ev_xor              ; lowest precedence layer
                push    ix
                pop     hl                  ; HL = cursor (advanced)
                pop     ix
                ret

; --- logical / bitwise layers (lowest precedence, left-assoc) --------------
; MSX-BASIC precedence below the relationals: NOT (unary) > AND > OR > XOR.
; All are 16-bit bitwise; they also implement logical tests on the -1/0 results
; the relationals produce. Tokens: AND $F6, OR $F7, XOR $F8, NOT $E0 (Table 2.20).
ev_xor:
                call    ev_or               ; DE = lhs
ev_xor_lp:
                call    ev_sp
                ld      a,(ix+0)
                cp      XOR_TOKEN
                ret     nz
    IF ROM_BASE < $4000
                ; spec §10.3 "strict int16 domain": convert the operand NOW
                ; (fac_to_int_strict re-derives it from FAC/FACTYP if it was
                ; float, ignoring the already-address-domain-rounded DE), then
                ; reset FACTYP=2 so it doesn't leak stale into the rhs eval —
                ; no FAC save is needed here (unlike ev_e/ev_t's double-
                ; widening sites) because the conversion to a plain int
                ; happens immediately, before the rhs eval can clobber FAC.
                call    fac_to_int_strict_reset
    ENDIF
                inc     ix
                push    de
                call    ev_or               ; DE = rhs
    IF ROM_BASE < $4000
                call    fac_to_int_strict_reset
    ENDIF
                pop     hl                  ; HL = lhs
                ld      a,l
                xor     e
                ld      l,a
                ld      a,h
                xor     d
                ld      h,a
                ex      de,hl               ; DE = lhs XOR rhs
                jr      ev_xor_lp
ev_or:
                call    ev_and
ev_or_lp:
                call    ev_sp
                ld      a,(ix+0)
                cp      OR_TOKEN
                ret     nz
    IF ROM_BASE < $4000
                call    fac_to_int_strict_reset
    ENDIF
                inc     ix
                push    de
                call    ev_and
    IF ROM_BASE < $4000
                call    fac_to_int_strict_reset
    ENDIF
                pop     hl
                ld      a,l
                or      e
                ld      l,a
                ld      a,h
                or      d
                ld      h,a
                ex      de,hl               ; DE = lhs OR rhs
                jr      ev_or_lp
ev_and:
                call    ev_not
ev_and_lp:
                call    ev_sp
                ld      a,(ix+0)
                cp      AND_TOKEN
                ret     nz
    IF ROM_BASE < $4000
                call    fac_to_int_strict_reset
    ENDIF
                inc     ix
                push    de
                call    ev_not
    IF ROM_BASE < $4000
                call    fac_to_int_strict_reset
    ENDIF
                pop     hl
                ld      a,l
                and     e
                ld      l,a
                ld      a,h
                and     d
                ld      h,a
                ex      de,hl               ; DE = lhs AND rhs
                jr      ev_and_lp
ev_not:
                call    ev_sp
                ld      a,(ix+0)
                cp      NOT_TOKEN
                jr      z,ev_not_do
                jp      ev_rel              ; no NOT -> drop to the relational layer
ev_not_do:
                inc     ix
                call    ev_not              ; unary, right-assoc (NOT NOT x)
    IF ROM_BASE < $4000
                call    fac_to_int_strict_reset
    ENDIF
                ld      a,e
                cpl
                ld      e,a
                ld      a,d
                cpl
                ld      d,a                 ; DE = ~DE (ones complement)
                ret

; --- ev_rel: relational layer ----------------------------------------------
; rel := arith [ relop arith ]   (relop is one or two of  <  =  > ).
; A comparison yields -1 (true) or 0 (false), per MSX-BASIC, using a signed
; 16-bit compare. Relop tokens: '<' $F0, '=' $EF, '>' $EE (Table 2.20); the
; compound forms (<=, >=, <>) arrive as two operator tokens and are merged.
ev_rel:
    IF ROM_BASE < $4000
                ; string-compare S2 (repack build only): probe the LHS for a string
                ; operand before committing to the numeric ev_e below. IX is the live
                ; token cursor throughout the interpreter (str_eval never touches it),
                ; so a failed probe leaves IX exactly where it was -- no restore needed,
                ; the unchanged numeric body below just reads IX itself.
                push    ix
                pop     hl                  ; HL = cursor (bridge for the probe)
                call    str_eval            ; CF set -> LHS is a string; STRPTR->desc
                jp      c,ev_rel_str        ; string LHS -> the string-compare path
    ENDIF
                call    ev_e                ; DE = lhs (arithmetic)
                call    ev_sp
                ld      a,(ix+0)
                call    relop_bit
                ret     nc                  ; no relational operator -> plain value
                ld      c,b                 ; C = requested relation bits
                inc     ix
                call    ev_sp
                ld      a,(ix+0)
                call    relop_bit           ; a second relop? (<=, >=, <>)
                jr      nc,evr_rhs
                ld      a,c
                or      b
                ld      c,a                 ; merge the two relation bits
                inc     ix
evr_rhs:
    IF ROM_BASE < $4000
                ; D-2 symmetric case (`5 < A$`): the LHS was just confirmed numeric (we
                ; only reach evr_rhs via the unchanged ev_e call above), so probe the RHS
                ; cursor for a string operand BEFORE ev_e reads it as a number -- ev_f_var
                ; would otherwise silently read A$'s name-keyed numeric shadow cell instead
                ; of erroring. CF clear (not a string) leaves the cursor untouched (the
                ; same str_eval failure contract the LHS probe above relies on), so the
                ; unchanged fallthrough is unaffected.
                push    bc
                push    de
                push    ix
                pop     hl
                call    str_eval
                pop     de
                pop     bc
                jp      c,evr_mismatch      ; RHS is a string, LHS was numeric -> D-2
    ENDIF
                push    de                  ; lhs
    IF ROM_BASE < $4000
                ; spec §10.1: relationals over any float operand compare AS
                ; floats after widening (never int-converted, `40000=40000!`
                ; -> -1, no Overflow). Save the LHS's FACTYP+FAC on the
                ; machine stack (same fixed-size frame protocol as the ev_e/
                ; ev_t double-arithmetic sites) before the rhs eval clobbers
                ; FAC, then reset FACTYP=2 for the rhs eval.
                call    push_lhs_frame
                call    set_factyp_int_ret  ; FACTYP:=2 for the rhs eval
    ENDIF
                push    bc                  ; relation bits (in C)
                call    ev_e                ; DE = rhs
                pop     bc                  ; C = bits
    IF ROM_BASE < $4000
                call    combine_cmp         ; pops the lhs frame + value; A =
                                            ; relation bit (1/2/4); FACTYP:=2
    ELSE
                pop     hl                  ; HL = lhs
                call    cmp16_bits          ; A = actual relation bit (1/2/4)
    ENDIF
                and     c                   ; intersect requested with actual
                jr      z,evr_false
                ld      de,$FFFF            ; true = -1
                ret
evr_false:
                ld      de,0                ; false = 0
                ret
    IF ROM_BASE < $4000
evr_mismatch:
                jp      type_mismatch_set   ; sets ERRMARK+TMISMATCH, DE=0, ret (str-engine.asm)
    ENDIF

; --- relop_bit: A = token -> CF set & B = relation bit, else CF clear -------
; '<' -> 1 (less), '=' -> 2 (equal), '>' -> 4 (greater).
relop_bit:
                cp      LT_TOKEN
                jr      z,rb_lt
                cp      EQ_TOKEN
                jr      z,rb_eq
                cp      GT_TOKEN
                jr      z,rb_gt
                or      a                   ; CF clear -> not a relop
                ret
rb_lt:
                ld      b,1
                scf
                ret
rb_eq:
                ld      b,2
                scf
                ret
rb_gt:
                ld      b,4
                scf
                ret

; --- cmp16_bits: signed compare HL(lhs) vs DE(rhs) -> A = 1/2/4 -------------
; 1 = lhs<rhs, 2 = equal, 4 = lhs>rhs. Clobbers A, HL, flags (DE preserved).
cmp16_bits:
                ld      a,h
                cp      d
                jr      nz,c16_ne
                ld      a,l
                cp      e
                jr      nz,c16_ne
                ld      a,2                 ; equal
                ret
c16_ne:
                or      a
                sbc     hl,de               ; lhs - rhs; signed: less iff S xor V
                jp      pe,c16_vset
                jp      m,c16_lt            ; V clear -> less iff S set
                jr      c16_gt
c16_vset:
                jp      p,c16_lt            ; V set  -> less iff S clear
                jr      c16_gt
c16_lt:
                ld      a,1
                ret
c16_gt:
                ld      a,4
                ret

; --- ev_sp: skip spaces in the IX stream -----------------------------------
ev_sp:
                ld      a,(ix+0)
                cp      ' '
                ret     nz
                inc     ix
                jr      ev_sp

; --- ev_e: expr := mod-term { (+|-) mod-term } -----------------------------
; Operators are tokens: '+' = PLUS_TOKEN ($F1), '-' = MINUS_TOKEN ($F2). The
; operands are MOD-expressions (MSX precedence: + - is below MOD, \, * /).
ev_e:
                call    ev_mod              ; DE = first term
ev_e_lp:
                call    ev_sp
                ld      a,(ix+0)
                cp      PLUS_TOKEN
                jr      z,ev_e_add
                cp      MINUS_TOKEN
                jr      z,ev_e_sub
                ret
ev_e_add:
                inc     ix
                push    de                  ; lhs
    IF ROM_BASE < $4000
                ; spec §1 bullet 4: save the lhs's FACTYP+FAC on the machine
                ; stack (fixed-size frame) before the rhs eval clobbers FAC,
                ; reset FACTYP=2 for the rhs eval. combine_add decides int-
                ; fast-path (with signed-overflow-promotion) vs BCD add.
                call    push_lhs_frame
                call    set_factyp_int_ret  ; FACTYP:=2 for the rhs eval
    ENDIF
                call    ev_mod              ; DE = rhs
    IF ROM_BASE < $4000
                call    combine_add         ; pops the frame; DE = result
    ELSE
                pop     hl                  ; HL = lhs
                add     hl,de
                ex      de,hl               ; DE = sum
    ENDIF
                jr      ev_e_lp
ev_e_sub:
                inc     ix
                push    de                  ; lhs
    IF ROM_BASE < $4000
                call    push_lhs_frame
                call    set_factyp_int_ret  ; FACTYP:=2 for the rhs eval
    ENDIF
                call    ev_mod              ; DE = rhs
    IF ROM_BASE < $4000
                call    combine_sub
    ELSE
                pop     hl                  ; HL = lhs
                or      a                   ; clear carry
                sbc     hl,de               ; HL = lhs - rhs
                ex      de,hl
    ENDIF
                jr      ev_e_lp

; --- ev_mod: { MOD } over '\'-expressions (MSX precedence level 5) ----------
ev_mod:
                call    ev_idiv             ; DE = lhs
ev_mod_lp:
                call    ev_sp
                ld      a,(ix+0)
                cp      MOD_TOKEN
                ret     nz
    IF ROM_BASE < $4000
                ; spec §10.3: \ / MOD operands convert via the STRICT int16
                ; domain (not the address domain) -- immediately, no FAC save
                ; needed since the plain int value is captured before the
                ; rhs eval can clobber FAC.
                call    fac_to_int_strict_reset
    ENDIF
                inc     ix
                push    de                  ; lhs (dividend)
                call    ev_idiv             ; DE = rhs (divisor)
    IF ROM_BASE < $4000
                call    fac_to_int_strict_reset
    ENDIF
                ld      b,d
                ld      c,e                 ; BC = divisor
                pop     de                  ; DE = dividend
    IF ROM_BASE < $4000
                call    signed_mod_de_bc    ; D-C: MSX-signed MOD (spec §10.4)
    ELSE
                call    mod_de_bc           ; DE = remainder
    ENDIF
                jr      ev_mod_lp

; --- ev_idiv: { '\' } over terms (integer division, level 4) ---------------
ev_idiv:
                call    ev_t                ; DE = lhs
ev_idiv_lp:
                call    ev_sp
                ld      a,(ix+0)
                cp      IDIV_TOKEN          ; '\'
                ret     nz
    IF ROM_BASE < $4000
                call    fac_to_int_strict_reset
    ENDIF
                inc     ix
                push    de                  ; lhs (dividend)
                call    ev_t                ; DE = rhs (divisor)
    IF ROM_BASE < $4000
                call    fac_to_int_strict_reset
    ENDIF
                ld      b,d
                ld      c,e                 ; BC = divisor
                pop     de                  ; DE = dividend
    IF ROM_BASE < $4000
                call    signed_div_de_bc    ; D-C: MSX-signed \ (spec §10.4)
    ELSE
                call    div_de_bc           ; DE = quotient
    ENDIF
                jr      ev_idiv_lp

; --- ev_t: term := factor { ('*' | '/') factor } ---------------------------
; '/' is real division on MSX; the repack build makes it always float (spec
; §10.1); the lean build keeps the integer-quotient divergence (unchanged).
ev_t:
                call    ev_f                ; DE = factor
ev_t_lp:
                call    ev_sp
                ld      a,(ix+0)
                cp      STAR_TOKEN          ; '*'
                jr      z,ev_t_mul
                cp      DIV_TOKEN           ; '/'
                jr      z,ev_t_div
                ret
ev_t_mul:
                inc     ix
                push    de                  ; lhs
    IF ROM_BASE < $4000
                call    push_lhs_frame
                call    set_factyp_int_ret  ; FACTYP:=2 for the rhs eval
    ENDIF
                call    ev_f                ; DE = rhs
    IF ROM_BASE < $4000
                call    combine_mul
    ELSE
                pop     hl                  ; HL = lhs
                call    mul16               ; HL = lhs * rhs (low 16 bits)
                ex      de,hl               ; DE = product
    ENDIF
                jr      ev_t_lp
ev_t_div:
                inc     ix
    IF ROM_BASE < $4000
                push    de                  ; lhs
                call    push_lhs_frame
                call    set_factyp_int_ret  ; FACTYP:=2 for the rhs eval
                call    ev_f                ; DE = rhs
                call    combine_div_float   ; ALWAYS float (spec §10.1)
    ELSE
                push    de                  ; lhs (dividend)
                call    ev_f                ; DE = rhs (divisor)
                ld      b,d
                ld      c,e                 ; BC = divisor
                pop     de                  ; DE = dividend
                call    div_de_bc           ; DE = quotient
    ENDIF
                jr      ev_t_lp

; --- ev_f: factor ----------------------------------------------------------
; Decodes the crunched tokens (spec §3): constant tokens carry their binary
; value; '(' / ')' stay verbatim; PEEK is $FF $97; a bare upcased letter is a
; variable; unary minus is MINUS_TOKEN.
ev_f:
                call    ev_sp
                ld      a,(ix+0)
                cp      MINUS_TOKEN         ; unary minus
                jp      z,ev_f_neg
                cp      '('
                jp      z,ev_f_paren
                cp      PEEK_PREFIX         ; $FF -> PEEK / VPEEK / INP function token
                jp      z,ev_f_ff
                cp      USR_TOKEN           ; $DD -> USR[n](arg) function
                jp      z,ev_usr
                cp      VARPTR_TOKEN        ; $E7 -> VARPTR(var) function
                jp      z,ev_f_varptr
                cp      BASE_TOKEN          ; $C9 -> BASE(n) function
                jp      z,ev_f_base
    IF ROM_BASE < $4000
                cp      INSTR_TOKEN         ; $E5 -> INSTR([p,]a$,b$) (string-functions
                jp      z,ev_f_instr        ; Group C; single-byte token, not $FF-prefixed)
    ENDIF
                cp      HEX_TOKEN           ; $0C -> 2-byte LE value (&H)
                jp      z,ev_f_word
                cp      OCT_TOKEN           ; $0B -> 2-byte LE value (&O)
                jp      z,ev_f_word
                cp      INT2_TOKEN          ; $1C -> 2-byte LE value
                jp      z,ev_f_word
                cp      INT1_TOKEN          ; $0F -> 1-byte value
                jp      z,ev_f_byte
    IF ROM_BASE < $4000
                cp      SNG_TOKEN           ; $1D -> single float literal (basic/float.asm)
                jp      z,ev_f_float
                cp      DBL_TOKEN           ; $1F -> double float literal
                jp      z,ev_f_float
    ENDIF
                cp      INT_DIGIT_BASE      ; $11
                jr      c,ev_f_var
                cp      $1A+1               ; $11..$1A -> digit token
                jp      c,ev_f_digit
                ; fall through: letter -> variable (or error)
ev_f_var:
                ld      a,(ix+0)
                call    is_letter           ; must start with a letter
                jr      nc,ev_f_err
                push    ix
                pop     hl                  ; HL = cursor
                call    var_name_key        ; BC = key, HL past the (multi-char) name
                push    hl
                pop     ix                  ; IX = advanced cursor
                call    var_get_key         ; BC = key -> DE = value
                ret
ev_f_err:
                ld      a,$DD               ; expression error marker
                ld      (ERRMARK),a
                ld      de,0
                ret

; constant decoders --------------------------------------------------------
ev_f_digit:                                 ; $11..$1A -> value 0..9
                ld      a,(ix+0)
                sub     INT_DIGIT_BASE
                ld      e,a
                ld      d,0
                inc     ix
                ret
ev_f_byte:                                  ; $0F,<byte>
                inc     ix
                ld      a,(ix+0)
                ld      e,a
                ld      d,0
                inc     ix
                ret
ev_f_word:                                  ; $0C/$1C,<word LE>
                inc     ix
                ld      a,(ix+0)
                ld      e,a                 ; value low
                inc     ix
                ld      a,(ix+0)
                ld      d,a                 ; value high
                inc     ix
                ret

    IF ROM_BASE < $4000
; --- ev_f_float: SNG_TOKEN/DBL_TOKEN factor -> FAC/FACTYP + DE (§9.4) ------
; Copies the token's 4 (single) / 8 (double) value bytes into FAC, sets
; FACTYP (4/8), and returns DE = the value rounded to int16 (flt_to_int16,
; basic/float.asm) so every existing int consumer keeps working unchanged
; (interim divergence D-F1-2: float into an int context rounds silently).
ev_f_float:
                ld      a,(ix+0)            ; SNG_TOKEN or DBL_TOKEN
                ld      c,4                 ; C = value byte count (single)
                ld      b,4                 ; B = FACTYP value (single)
                cp      DBL_TOKEN
                jr      nz,eff_sz
                ld      c,8
                ld      b,8
eff_sz:
                inc     ix                  ; past the token
                ld      a,b
                ld      (FACTYP),a
                ld      hl,FAC
                ld      b,c                 ; B = copy count
eff_cp:
                ld      a,(ix+0)
                ld      (hl),a
                inc     hl
                inc     ix
                djnz    eff_cp
                jp      flt_to_int16        ; DE = rounded int16 (0 if out of range)
    ENDIF

ev_f_neg:
                inc     ix
                call    ev_f                ; DE = operand
                ld      hl,0
                or      a
                sbc     hl,de               ; HL = 0 - operand
                ex      de,hl
    IF ROM_BASE < $4000
                ld      a,(FACTYP)
                cp      2
                jr      z,evfn_ret
                call    flt_neg
evfn_ret:
    ENDIF
                ret

ev_f_paren:
                inc     ix                  ; '('
                call    ev_xor              ; DE = inner value (full expression)
                call    ev_sp
                ld      a,(ix+0)
                cp      ')'
                jp      nz,ev_f_err
                inc     ix
                ret

; --- ev_f_ff: a $FF-prefixed function token (PEEK / VPEEK / INP) -----------
; All three take a single parenthesised expression; they differ only in how the
; argument is used. We parse "( <expr> )" once, then read from RAM (PEEK), VRAM
; (VPEEK) or a Z80 port (INP). The second token byte selects the read.
ev_f_ff:
                inc     ix                  ; skip the $FF prefix
                ld      a,(ix+0)            ; the function selector byte
                cp      PEEK_TOKEN          ; $97 -> PEEK
                jr      z,ev_ff_arg
                cp      VPEEK_TOKEN         ; $98 -> VPEEK
                jr      z,ev_ff_arg
                cp      INP_TOKEN           ; $90 -> INP
                jr      z,ev_ff_arg
                cp      EOF_TOKEN           ; $AB -> EOF
                jr      z,ev_ff_arg
                cp      LOF_TOKEN           ; $AD -> LOF
                jr      z,ev_ff_arg
                cp      DSKF_TOKEN          ; $A6 -> DSKF
                jr      z,ev_ff_arg
                cp      CVI_TOKEN           ; $A8 -> CVI (takes a STRING arg)
                jp      z,ev_ff_cvi
    IF ROM_BASE < $4000
                jp      ev_ff_strnum        ; repack: LEN/ASC/VAL (string->number), else ev_f_err
    ELSE
                jp      ev_f_err            ; unknown $FF function
    ENDIF
ev_ff_arg:
                ld      c,a                 ; C = selector (survives the parse)
                inc     ix                  ; skip the selector byte
                call    ev_sp
                ld      a,(ix+0)
                cp      '('
                jp      nz,ev_f_err
                inc     ix
                push    bc                  ; guard the selector across the eval
                call    ev_xor              ; DE = argument (full expression)
                pop     bc
                call    ev_sp
                ld      a,(ix+0)
                cp      ')'
                jp      nz,ev_f_err
                inc     ix
    IF ROM_BASE < $4000
                call    flt_int_result      ; the function returns an int even if its
    ENDIF                                   ;  arg was a float (clobbers A only; C kept)
                ld      a,c                 ; dispatch on the selector
                cp      VPEEK_TOKEN
                jr      z,ev_ff_vpeek
                cp      INP_TOKEN
                jr      z,ev_ff_inp
                cp      EOF_TOKEN
                jr      z,ev_ff_eof
                cp      LOF_TOKEN
                jr      z,ev_ff_lof
                cp      DSKF_TOKEN
                jr      z,ev_ff_dskf
                ; PEEK: read one byte of RAM at the address in DE.
                ex      de,hl               ; HL = address
                ld      e,(hl)              ; read one byte
                ld      d,0                 ; PEEK yields 0..255
                ret
ev_ff_vpeek:                                ; VPEEK: read one byte of VRAM (DE = addr)
                ex      de,hl               ; HL = VRAM address (RDVRM wants it here)
                call    RDVRM               ; A = VRAM[HL]; makes no register guarantees
                ld      e,a
                ld      d,0                 ; VPEEK yields 0..255
                ret
ev_ff_inp:                                  ; INP: read one Z80 port (DE = port)
                ld      b,d
                ld      c,e                 ; BC = port (in (a),(c) reads from BC)
                in      a,(c)               ; A = port input
                ld      e,a
                ld      d,0                 ; INP yields 0..255
                ret
ev_ff_eof:                                  ; EOF(n): -1 at end of the input file n
                ; Select channel n (DE = arg) so FREAD_LEFT belongs to it, then test
                ; whether every file byte has been delivered (4-byte LE == 0). fch_select
                ; uses LDIR only (no CALSLT), so IX — the evaluator's token cursor —
                ; survives; it does clobber HL/BC/A (the factor caller tolerates that,
                ; like PEEK). A bad channel number is a function error.
                ld      a,e
                call    fch_valid
                jp      nc,ev_f_err
                call    ev_chan_hasfile     ; device/cassette channels have no length
                jp      nc,ev_f_err         ; -> function error (never fch_select them)
                ld      a,e
                call    fch_select
                ld      hl,FREAD_LEFT
                ld      a,(hl)
                inc     hl
                or      (hl)
                inc     hl
                or      (hl)
                inc     hl
                or      (hl)
                ld      de,0
                ret     nz                  ; bytes remain -> not EOF -> 0
                dec     de                  ; all delivered -> EOF -> -1 ($FFFF)
                ret
ev_ff_lof:                                  ; LOF(n): length of open input file n
                ; Select channel n so FAT_FILESIZE (set by fat_find at OPEN, part of
                ; the per-channel state span) belongs to it; return its low 16 bits.
                ld      a,e
                call    fch_valid
                jp      nc,ev_f_err
                call    ev_chan_hasfile     ; device/cassette channels have no length
                jp      nc,ev_f_err         ; -> function error (never fch_select them)
                ld      a,e
                call    fch_select
                ld      de,(FAT_FILESIZE)
                ret

; ev_chan_hasfile — CF set if channel E is a disk file channel (FCH_MODES[E] <
; LPT_MODE), CF clear if it is a length-less device channel (LPT/CRT/CAS, mode >=
; LPT_MODE). Lets EOF()/LOF() reject device+cassette channels (which own no fat.asm
; ctx and would corrupt the engine globals if fch_select'd) as a function error.
; Preserves E + IX (no CALSLT); clobbers A/HL. FCH_MODES[0] is unused/0, so a 0
; channel (already rejected by fch_valid) would read as a file channel — harmless.
ev_chan_hasfile:
                ld      a,e
                add     a,FCH_MODES & $FF   ; HL = FCH_MODES + E (page-local; array is
                ld      l,a                 ; well within one page of its base)
                ld      a,FCH_MODES >> 8
                adc     a,0
                ld      h,a
                ld      a,(hl)              ; A = FCH_MODES[E]
                cp      LPT_MODE
                ret                         ; CF set (A<LPT_MODE) = disk file channel
ev_ff_dskf:                                 ; DSKF(d): free clusters on the drive
                ; The drive arg (DE) is ignored (single drive). Returns the count
                ; of free FAT entries — = free KB on a 1 KB/cluster 720 KB volume.
                ; CALSLT (inside fat_count_free) clobbers IX/IY, and IX is the
                ; evaluator's live token cursor — guard it on the stack.
                push    ix
                push    iy
                call    fat_count_free      ; DE = free cluster count
                pop     iy
                pop     ix
                ret
ev_ff_cvi:                                  ; CVI(s$): integer from s$'s first 2 bytes
                ; CVI takes a STRING argument, so it cannot use ev_ff_arg's numeric
                ; ev_xor. Parse "( <string> )" by bridging the IX token cursor to the
                ; HL-based str_eval and back, then read 2 little-endian bytes from the
                ; resulting descriptor. (IX is reloaded from str_eval's advanced HL, so
                ; an inner eval clobbering IX is harmless.) Entered with IX on the
                ; CVI selector byte.
                inc     ix                  ; skip the CVI selector
                call    ev_sp
                ld      a,(ix+0)
                cp      '('
                jp      nz,ev_f_err
                inc     ix
                call    ev_sp
                push    ix
                pop     hl
                call    str_eval            ; STRPTR -> [len][bytes]; HL advanced; CF=ok
                jp      nc,ev_f_err         ; not a string operand
                push    hl
                pop     ix                  ; IX = cursor past the string operand
                call    ev_sp
                ld      a,(ix+0)
                cp      ')'
                jp      nz,ev_f_err
                inc     ix
    IF ROM_BASE < $4000
                call    flt_int_result      ; CVI returns an int; a float nested in
    ENDIF                                   ;  the string arg must not stick (A only)
                ld      hl,(STRPTR)
                inc     hl                  ; -> the value bytes
                ld      e,(hl)              ; low byte
                inc     hl
                ld      d,(hl)              ; high byte  -> DE = int (LE)
                ret

; --- ev_f_varptr: VARPTR(<var>) -> address of the variable's value field -----
; Returns the address of the 2-byte value cell in zerobas's own variable table
; (VARTAB), NOT the reference ROM's variable-area address — zerobas's table is
; its own layout, so VARPTR yields OUR address. This is a documented divergence
; (PROVENANCE.md): a loader stub that pokes through VARPTR sees a valid, writable
; 16-bit cell, which is all the loader use needs. If the variable does not yet
; exist it is created (value 0) so the returned address is always valid.
ev_f_varptr:
                inc     ix                  ; skip the VARPTR token
                call    ev_sp
                ld      a,(ix+0)
                cp      '('
                jp      nz,ev_f_err
                inc     ix
                call    ev_sp
                ld      a,(ix+0)
                call    is_letter           ; the argument must be a variable name
                jp      nc,ev_f_err
                push    ix
                pop     hl                  ; HL = cursor at the name
                call    var_name_key        ; BC = key, HL past the name
                push    hl
                pop     ix                  ; IX = advanced cursor
                ; ensure the variable exists: read its value, write it back. A new
                ; variable is allocated with its current (0) value; an existing one
                ; is left unchanged. Then var_find gives the entry address.
                push    bc
                call    var_get_key         ; DE = current value (0 if unset)
                pop     bc
                push    bc
                call    var_set_key         ; allocate-if-new, value unchanged
                pop     bc
                call    var_find            ; CF set, HL = entry address
                jr      nc,vptr_none        ; table full -> address 0 (defensive)
                inc     hl
                inc     hl                  ; HL = value field (entry+2)
                ex      de,hl               ; DE = the value-field address
                call    ev_sp
                ld      a,(ix+0)
                cp      ')'
                jp      nz,ev_f_err
                inc     ix
                ret
vptr_none:
                ld      de,0                ; table full: no address (own-design)
                call    ev_sp
                ld      a,(ix+0)
                cp      ')'
                jp      nz,ev_f_err
                inc     ix
                ret

; --- ev_f_base: BASE(<n>) -> a VDP table base address ----------------------
; BASE(n) returns the base address of a VDP table for the current screen mode
; (name / colour / pattern-generator / sprite-attribute / sprite-pattern, per
; group of 5 starting at n=0). zerobas drives the screen entirely through the
; C-BIOS CHGMOD path and keeps no per-mode VDP table-base map of its own, and
; reproducing the reference's exact BASE() value table would require a forbidden
; source. So BASE is **descoped**: the argument is parsed and evaluated, and the
; function returns 0 with an expression-error marker (ERRMARK), rather than
; fabricating an address. This is a documented divergence (PROVENANCE.md);
; loader stubs that need real VDP table bases are out of scope for now.
ev_f_base:
                inc     ix                  ; skip the BASE token
                call    ev_sp
                ld      a,(ix+0)
                cp      '('
                jp      nz,ev_f_err
                inc     ix
                call    ev_xor              ; evaluate + discard the index argument
                call    ev_sp
                ld      a,(ix+0)
                cp      ')'
                jp      nz,ev_f_err
                inc     ix
    IF ROM_BASE < $4000
                call    flt_int_result      ; BASE yields an int (0) even over a float arg
    ENDIF
                ld      a,$DD               ; BASE is descoped -> expression-error marker
                ld      (ERRMARK),a
                ld      de,0                ; ...and a 0 result (no fabricated address)
                ret

; --- mul16: HL = (HL * DE) low 16 bits -------------------------------------
; Shift-add, MSB-first over 16 iterations. Clobbers A, BC, DE, HL.
mul16:
                ld      b,h
                ld      c,l                 ; BC = multiplicand
                ld      hl,0                ; product
                ld      a,16
mul_lp:
                add     hl,hl               ; product <<= 1
                ex      de,hl
                add     hl,hl               ; multiplier <<= 1, CF = old MSB
                ex      de,hl               ; (ex does not affect flags)
                jr      nc,mul_skip
                add     hl,bc               ; bit set -> product += multiplicand
mul_skip:
                dec     a
                jr      nz,mul_lp
                ret

; --- div_de_bc / mod_de_bc: DE / BC -> quotient / remainder in DE -----------
; Unsigned 16-bit divide. zerobas treats operands as 0..65535 (address math),
; diverging from MSX's signed integer divide — documented; signed/float is a
; later model. Division by zero yields 0 and sets ERRMARK (no crash). Clobber
; A, BC, HL.
div_de_bc:
                ld      a,b
                or      c
                jr      z,div_zero          ; divisor 0 -> error, result 0
                call    udiv16              ; DE = quotient, HL = remainder
                ret
mod_de_bc:
                ld      a,b
                or      c
                jr      z,div_zero
                call    udiv16              ; HL = remainder
                ex      de,hl               ; DE = remainder
                ret
div_zero:
                ld      a,$DD               ; expression-error marker (cf. ev_f_err)
                ld      (ERRMARK),a
                ld      de,0
                ret

; --- udiv16: DE / BC -> DE = quotient, HL = remainder ----------------------
; Restoring division: shift the dividend (DE) left into the remainder (HL) one
; bit at a time, subtracting the divisor when it fits and setting the quotient
; bit in DE's vacated low end. Counter in A (untouched by the body). 16 steps.
udiv16:
                ld      hl,0                ; remainder
                ld      a,16
udiv_lp:
                sla     e
                rl      d                   ; DE <<= 1; CF = old bit15
                adc     hl,hl               ; HL = HL<<1 | CF (32-bit shift of HL:DE)
                or      a                   ; clear CF for the trial subtract
                sbc     hl,bc               ; HL -= divisor; CF set if it didn't fit
                jr      nc,udiv_fit
                add     hl,bc               ; restore remainder (divisor too big)
                jr      udiv_next           ; quotient bit stays 0
udiv_fit:
                inc     e                   ; set the quotient's low bit
udiv_next:
                dec     a
                jr      nz,udiv_lp
                ret
