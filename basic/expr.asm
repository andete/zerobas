; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause

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
                inc     ix
                push    de
                call    ev_or               ; DE = rhs
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
                inc     ix
                push    de
                call    ev_and
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
                inc     ix
                push    de
                call    ev_not
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
                push    de                  ; lhs
                push    bc                  ; relation bits (in C)
                call    ev_e                ; DE = rhs
                pop     bc                  ; C = bits
                pop     hl                  ; HL = lhs
                call    cmp16_bits          ; A = actual relation bit (1/2/4)
                and     c                   ; intersect requested with actual
                jr      z,evr_false
                ld      de,$FFFF            ; true = -1
                ret
evr_false:
                ld      de,0                ; false = 0
                ret

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
                call    ev_mod              ; DE = rhs
                pop     hl                  ; HL = lhs
                add     hl,de
                ex      de,hl               ; DE = sum
                jr      ev_e_lp
ev_e_sub:
                inc     ix
                push    de                  ; lhs
                call    ev_mod              ; DE = rhs
                pop     hl                  ; HL = lhs
                or      a                   ; clear carry
                sbc     hl,de               ; HL = lhs - rhs
                ex      de,hl
                jr      ev_e_lp

; --- ev_mod: { MOD } over '\'-expressions (MSX precedence level 5) ----------
ev_mod:
                call    ev_idiv             ; DE = lhs
ev_mod_lp:
                call    ev_sp
                ld      a,(ix+0)
                cp      MOD_TOKEN
                ret     nz
                inc     ix
                push    de                  ; lhs (dividend)
                call    ev_idiv             ; DE = rhs (divisor)
                ld      b,d
                ld      c,e                 ; BC = divisor
                pop     de                  ; DE = dividend
                call    mod_de_bc           ; DE = remainder
                jr      ev_mod_lp

; --- ev_idiv: { '\' } over terms (integer division, level 4) ---------------
ev_idiv:
                call    ev_t                ; DE = lhs
ev_idiv_lp:
                call    ev_sp
                ld      a,(ix+0)
                cp      IDIV_TOKEN          ; '\'
                ret     nz
                inc     ix
                push    de                  ; lhs (dividend)
                call    ev_t                ; DE = rhs (divisor)
                ld      b,d
                ld      c,e                 ; BC = divisor
                pop     de                  ; DE = dividend
                call    div_de_bc           ; DE = quotient
                jr      ev_idiv_lp

; --- ev_t: term := factor { ('*' | '/') factor } ---------------------------
; '/' is real division on MSX; zerobas is integer-only, so it computes the
; integer quotient (documented divergence; floats are Phase 2).
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
                call    ev_f                ; DE = rhs
                pop     hl                  ; HL = lhs
                call    mul16               ; HL = lhs * rhs (low 16 bits)
                ex      de,hl               ; DE = product
                jr      ev_t_lp
ev_t_div:
                inc     ix
                push    de                  ; lhs (dividend)
                call    ev_f                ; DE = rhs (divisor)
                ld      b,d
                ld      c,e                 ; BC = divisor
                pop     de                  ; DE = dividend
                call    div_de_bc           ; DE = quotient
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
                cp      HEX_TOKEN           ; $0C -> 2-byte LE value (&H)
                jp      z,ev_f_word
                cp      OCT_TOKEN           ; $0B -> 2-byte LE value (&O)
                jp      z,ev_f_word
                cp      INT2_TOKEN          ; $1C -> 2-byte LE value
                jp      z,ev_f_word
                cp      INT1_TOKEN          ; $0F -> 1-byte value
                jp      z,ev_f_byte
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

ev_f_neg:
                inc     ix
                call    ev_f                ; DE = operand
                ld      hl,0
                or      a
                sbc     hl,de               ; HL = 0 - operand
                ex      de,hl
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
                jp      ev_f_err            ; unknown $FF function
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
ev_ff_eof:                                  ; EOF(#n): -1 at end of the input file
                ; The channel arg (DE) is ignored (single channel). EOF when every
                ; file byte has been delivered (FREAD_LEFT, 4-byte LE, == 0).
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
ev_ff_lof:                                  ; LOF(#n): length of the open file
                ; The channel arg (DE) is ignored. FAT_FILESIZE (set by fat_find at
                ; OPEN) is the file's byte count; return its low 16 bits.
                ld      de,(FAT_FILESIZE)
                ret
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
