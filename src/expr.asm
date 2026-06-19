; expr.asm — 16-bit integer expression evaluator.
;
; Evaluates an expression from the token/char stream. Grammar (small,
; precedence-climbing):
;
;   expr   := term  { ('+' | '-') term }
;   term   := factor { '*' factor }
;   factor := number | '&H' hex | letter(variable) | 'PEEK' '(' expr ')'
;           | '(' expr ')' | '-' factor
;
; Numbers and operators are plain ASCII in our stream (zerobas keeps them
; verbatim — see spec-tokens-statements.md §3/§4 — and parses them here at
; execution time). PEEK arrives as its oracle-sourced two-byte function token
; ($FF $97). All arithmetic is unsigned 16-bit, low-word on overflow.
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
                call    ev_e
                push    ix
                pop     hl                  ; HL = cursor (advanced)
                pop     ix
                ret

; --- ev_sp: skip spaces in the IX stream -----------------------------------
ev_sp:
                ld      a,(ix+0)
                cp      ' '
                ret     nz
                inc     ix
                jr      ev_sp

; --- ev_e: expr := term { (+|-) term } -------------------------------------
ev_e:
                call    ev_t                ; DE = first term
ev_e_lp:
                call    ev_sp
                ld      a,(ix+0)
                cp      '+'
                jr      z,ev_e_add
                cp      '-'
                jr      z,ev_e_sub
                ret
ev_e_add:
                inc     ix
                push    de                  ; lhs
                call    ev_t                ; DE = rhs
                pop     hl                  ; HL = lhs
                add     hl,de
                ex      de,hl               ; DE = sum
                jr      ev_e_lp
ev_e_sub:
                inc     ix
                push    de                  ; lhs
                call    ev_t                ; DE = rhs
                pop     hl                  ; HL = lhs
                or      a                   ; clear carry
                sbc     hl,de               ; HL = lhs - rhs
                ex      de,hl
                jr      ev_e_lp

; --- ev_t: term := factor { '*' factor } -----------------------------------
ev_t:
                call    ev_f                ; DE = factor
ev_t_lp:
                call    ev_sp
                ld      a,(ix+0)
                cp      '*'
                ret     nz
                inc     ix
                push    de                  ; lhs
                call    ev_f                ; DE = rhs
                pop     hl                  ; HL = lhs
                call    mul16               ; HL = lhs * rhs (low 16 bits)
                ex      de,hl               ; DE = product
                jr      ev_t_lp

; --- ev_f: factor ----------------------------------------------------------
ev_f:
                call    ev_sp
                ld      a,(ix+0)
                cp      '-'
                jp      z,ev_f_neg
                cp      '('
                jp      z,ev_f_paren
                cp      '&'
                jp      z,ev_f_hex
                cp      PEEK_PREFIX         ; $FF -> PEEK function token
                jp      z,ev_f_peek
                cp      '0'
                jr      c,ev_f_var          ; below '0' -> try variable
                cp      '9'+1
                jr      c,ev_f_dec          ; '0'..'9' -> decimal literal
                ; fall through: letter -> variable
ev_f_var:
                ld      a,(ix+0)
                call    upcase
                cp      'A'
                jr      c,ev_f_err
                cp      'Z'+1
                jr      nc,ev_f_err
                inc     ix                  ; consume the letter
                call    var_get             ; A = name -> DE = value
                ret
ev_f_err:
                ld      a,$DD               ; expression error marker
                ld      (ERRMARK),a
                ld      de,0
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
                call    ev_e                ; DE = inner value
                call    ev_sp
                ld      a,(ix+0)
                cp      ')'
                jp      nz,ev_f_err
                inc     ix
                ret

ev_f_peek:
                inc     ix                  ; skip $FF prefix
                ld      a,(ix+0)
                cp      PEEK_TOKEN          ; $97
                jp      nz,ev_f_err
                inc     ix                  ; skip $97
                call    ev_sp
                ld      a,(ix+0)
                cp      '('
                jp      nz,ev_f_err
                inc     ix
                call    ev_e                ; DE = address
                call    ev_sp
                ld      a,(ix+0)
                cp      ')'
                jp      nz,ev_f_err
                inc     ix
                ex      de,hl               ; HL = address
                ld      e,(hl)              ; read one byte
                ld      d,0                 ; PEEK yields 0..255
                ret

; --- ev_f_dec: decimal literal -> DE ---------------------------------------
ev_f_dec:
                ld      de,0
ev_f_dec_lp:
                ld      a,(ix+0)
                cp      '0'
                jr      c,ev_f_dec_end
                cp      '9'+1
                jr      nc,ev_f_dec_end
                sub     '0'                 ; A = digit 0..9
                push    af
                ld      h,d
                ld      l,e                 ; HL = acc
                add     hl,hl               ; 2*acc
                add     hl,hl               ; 4*acc
                add     hl,de               ; 5*acc  (DE still = acc)
                add     hl,hl               ; 10*acc
                ex      de,hl               ; DE = 10*acc
                pop     af
                add     a,e
                ld      e,a
                jr      nc,ev_f_dec_nc
                inc     d
ev_f_dec_nc:
                inc     ix
                jr      ev_f_dec_lp
ev_f_dec_end:
                ret

; --- ev_f_hex: '&H' hex literal -> DE --------------------------------------
ev_f_hex:
                inc     ix                  ; skip '&'
                ld      a,(ix+0)
                call    upcase
                cp      'H'
                jp      nz,ev_f_err         ; only &H supported
                inc     ix
                ld      de,0
ev_f_hex_lp:
                ld      a,(ix+0)
                call    upcase
                cp      '0'
                jr      c,ev_f_hex_end
                cp      '9'+1
                jr      c,ev_f_hex_dig      ; '0'..'9'
                cp      'A'
                jr      c,ev_f_hex_end
                cp      'F'+1
                jr      nc,ev_f_hex_end
                sub     'A'-10              ; 'A'..'F' -> 10..15
                jr      ev_f_hex_acc
ev_f_hex_dig:
                sub     '0'
ev_f_hex_acc:
                push    af                  ; save nibble
                ex      de,hl               ; HL = acc
                add     hl,hl
                add     hl,hl
                add     hl,hl
                add     hl,hl               ; acc * 16
                ex      de,hl               ; DE = acc*16
                pop     af
                add     a,e                 ; low nibble of DE*16 is 0 -> no carry
                ld      e,a
                inc     ix
                jr      ev_f_hex_lp
ev_f_hex_end:
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
