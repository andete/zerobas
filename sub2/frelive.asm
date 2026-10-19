; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; ===========================================================================
; frelive_tenant -- the stack the reference's evaluator holds at one FRE(n)
; (D-FREPLUS14, 2026-10-17; docs/spec-basic-frelive.md)
; zerobas-sub2 page-1 index 3 (SUB2_IDX_FRELIVE), reached from main's fre_go
; (basic/main.asm) through subrom2_call, for FRE(n) only.
;   in:  HL = the address of a result word (on the caller's stack),
;        DE = the MARK: one past this FRE's own `)` (the evaluator's cursor),
;        SAVTXT = the current statement's start (exec_stmt writes it at every
;        statement head: line start, after every `:`, after THEN / ELSE).
;   out: (HL) = the bytes to take off zerobas's fixed FRE(n): the statement's
;        base (18 LET / 14 PRINT, IF / 20 FOR) + the depth below. Clobbers all.
;
; Joost ruled 2026-10-16 that FRE(0) reads what the VG-8020 reads in EVERY
; expression shape. The reference counts FRE(0) down to its live Z80 stack, so
; what its evaluator holds open when FRE runs costs free memory -- MEASURED
; (scratchpad/freshape_probe.py -> freshape_run3.out, 44 shapes), additive over
; what is still PENDING:
;     an open `(` 6 . unary minus / NOT 6 . a function call 10 . a subscript 18
;     a pending `+ - * / ^` 8 + width(left) . a relational 10 + width(left)
;     MOD \ AND OR XOR EQV IMP 8 . a string concatenation 2
; with the left operand kept at its own width (integer 2, single 4, double 8,
; string 3). This is the shunting-yard scratchpad/frelive_model.py validated
; against all 44 measured depths, over TOKENS instead of text:
;   * an operand's type: a name's suffix, else DEFTBL ($F6CA, whose codes ARE the
;     widths 2/3/4/8); a constant's token ($0B-$1C integer, $1D single, $1F
;     double); a function's result (fl_fftab); an operator's result.
;   * a pending entry is [class|prec][type] on the Z80 stack; DE carries the sum
;     of their costs, kept as they are pushed and popped. The answer is the sum
;     still standing when the entry for THIS FRE (`)` at the mark) is popped.
;   * the statement: an assignment (a letter, LET) or FOR has its target skipped
;     to the first top-level `=`; `;`, a top-level `,`, TO, STEP, THEN, GOTO,
;     GOSUB and USING start a fresh expression (PRINT's items; measured:
;     `PRINT"[";FRE(0)` reads PRINT's base alone).
; NOT MEASURED -- best effort, never a hang, a crash or a read past the
; statement: the arguments after a multi-argument function's first (MID$,
; INSTR, STRING$ ...: the model's rule, a `,` keeps the function pending),
; string relationals (10 + 3), FN calls (as a function), TAB( / SPC( (as one),
; and the bases of every statement but LET / PRINT / IF / FOR (LET's).
; 🔒 DEGRADES TO DEPTH 0 (the base alone) on anything it cannot classify: a
; token the grammar does not allow where it stands (`PRINT "A"B`'s juxtaposed
; operand; `PRINT #1,`'s `#` is merely skipped), a statement without its `=`, a
; scan that reaches the statement's end or the mark without meeting the mark's
; `)` -- which is a FRE in a DEF FN BODY: its text is another line, so it reads
; the calling statement's base only (spec's phase 2) -- and a scan whose stack
; would come within FL_STK_MARGIN of CTLLIM (the pool's floor: the machine stack
; descends from the pool, and a near-full machine must not be written into).
; Reads only RAM (the statement, SAVTXT, DEFTBL, CTLLIM) and calls nothing
; outside this file: closure-clean for page 1.
; CLEAN-ROOM: own design over own measurements; no reference code read.
; ===========================================================================

FL_STK_MARGIN   equ     48          ; bytes kept clear above CTLLIM (DI here: no
                                    ; interrupt frame; our own calls nest 2 deep)

; The frame, IX-relative (pushed in this order, so the first is highest):
;   (ix+8,9) the result word's address   (ix+6,7) the mark
;   (ix+4,5) the statement base          (ix+2) a pending operator's precedence
;   (ix+3) its class byte (1 = `)`, 2 = `,`)
;   (ix+0) the current operand's type    (ix+1) 1 = an operand is expected
; Entry classes (high nibble of the entry's low byte; low nibble = precedence,
; 0 for the brackets and the bottom sentinel, so no operator reduces past them):
;   0 sentinel . 1 + - * . 2 relational . 3 integer op . 4 unary . 5 `(`
;   6 function . 7 subscript . 8 THIS kind of FRE . 9 / ^ (double result)
;   10 concatenation . 11 `+` not yet told from a concatenation (never stacked)
frelive_tenant:
                push    hl                  ; (ix+8)
                push    de                  ; (ix+6)
                ld      bc,18
                push    bc                  ; (ix+4) LET's base, the default
                push    bc                  ; (ix+2) (scratch)
                ld      bc,$0102
                push    bc                  ; (ix+0) type 2, (ix+1) expect an operand
                ld      ix,0
                add     ix,sp
                ld      de,0                ; DE = the depth so far
                push    de                  ; the bottom sentinel
                ld      hl,(SAVTXT)
                call    fl_sp
                cp      'A'
                jr      c,fl_kw
                cp      'Z'+1
                jr      c,fl_target         ; a letter: an implicit LET
fl_kw:
                or      a                   ; an empty statement (never one with a
                jp      z,fl_bail           ; FRE in it): never step past its end
                cp      COLON
                jp      z,fl_bail
                inc     hl                  ; past the statement token
                cp      LET_TOKEN
                jr      z,fl_target
                cp      FOR_TOKEN
                jr      z,fl_for
                cp      IF_TOKEN            ; an IF condition reads like a PRINT
                jr      z,fl_print          ; (4 B above a LET, measured `ifcond`)
                cp      PRINT_TOKEN
                jr      z,fl_print
                cp      PEEK_PREFIX
                jr      nz,fl_loop          ; any other statement: LET's base,
                inc     hl                  ; its arguments scanned as they come
                jr      fl_loop             ; ($FF: a two-byte statement token)
fl_print:
                ld      (ix+4),14
                jr      fl_loop
fl_for:
                ld      (ix+4),20           ; a FOR start reads 2 B below a LET
fl_target:                                  ; skip the target to its top-level `=`
                ld      b,0                 ; B = subscript parenthesis depth
fl_tg_lp:
                call    fl_tok
                jp      z,fl_bail           ; no `=`: not an assignment we know
                cp      '('
                jr      nz,fl_tg_1
                inc     b
fl_tg_1:
                cp      ')'
                jr      nz,fl_tg_2
                dec     b
fl_tg_2:
                cp      EQ_TOKEN
                jr      nz,fl_tg_lp
                inc     b
                dec     b
                jr      nz,fl_tg_lp         ; an `=` inside a subscript

; --- the expression loop: HL = the scan cursor, DE = the depth -----------------
fl_loop:
                push    de                  ; stop at the mark: the FRE we serve
                ld      e,(ix+6)            ; ends just before it, so reaching it
                ld      d,(ix+7)            ; means we passed it unseen
                ld      a,l
                sub     e
                ld      a,h
                sbc     a,d                 ; CF iff HL < the mark
                pop     de
                jp      nc,fl_bail
                call    fl_tok
                jp      z,fl_bail           ; the statement ended first
                call    fl_issep
                jp      z,fl_reset          ; `;` TO STEP THEN GOTO GOSUB USING
                bit     0,(ix+1)
                jp      z,fl_after
; --- an operand is expected ----------------------------------------------------
                ld      bc,$0050
                cp      '('
                jp      z,fl_push           ; an open parenthesis
                ld      c,$4C
                cp      MINUS_TOKEN
                jp      z,fl_push           ; unary minus (precedence 12)
                ld      c,$46
                cp      NOT_TOKEN
                jp      z,fl_push           ; NOT (precedence 6)
                cp      PLUS_TOKEN          ; unary plus: nothing pending
                jr      z,fl_loop
                cp      '#'                 ; PRINT #n's `#`: skipped
                jr      z,fl_loop
                cp      ','
                jp      z,fl_reset          ; an empty argument (`LOCATE ,`)
                ld      b,2
                cp      OCT_TOKEN
                jr      c,fl_op_1
                cp      SNG_TOKEN
                jr      c,fl_val            ; $0B-$1C: an integer constant
                ld      b,4
                jr      z,fl_val            ; $1D: a single
                ld      b,8
                cp      DBL_TOKEN+1
                jr      c,fl_val            ; $1E-$1F: a double
fl_op_1:
                ld      b,3
                cp      '"'
                jr      z,fl_val            ; a string literal (fl_tok skipped it)
                ld      b,2
                cp      '&'
                jr      z,fl_amp            ; `&B...` stays text: an integer
                cp      'A'
                jr      c,fl_op_2
                cp      'Z'+1
                ld      c,$70               ; a name followed by `(` is a subscript
                jr      c,fl_name
fl_op_2:
                cp      PEEK_PREFIX
                jp      z,fl_ff
                ld      c,$60
                cp      FN_TOKEN
                jr      z,fl_fn
                cp      TAB_TOKEN           ; TAB( and SPC( carry their `(`
                jr      z,fl_tabspc
                cp      SPC_TOKEN
                jr      z,fl_tabspc
                cp      USR_TOKEN
                jr      z,fl_usr
                push    hl                  ; the other single-byte functions and
                push    bc                  ; the pseudo-variables
                ld      hl,fl_sbtok
                ld      bc,fl_sbtok_n
                cpir                        ; Z: found, HL one past it
                ld      bc,fl_sbtok_n-1     ; -> its row in fl_sbtyp (`add hl` and
                add     hl,bc               ;  the loads keep Z)
                ld      a,(hl)
                pop     bc
                pop     hl
                jp      nz,fl_bail          ; nothing we can classify
                ld      b,a
                bit     7,a
                jr      z,fl_val            ; a pseudo-variable (ERR, TIME ...)
                and     $7F
                ld      b,a                 ; a function: its `(` must follow
                jp      fl_needparen

fl_val:                                     ; B = the operand's type
                ld      (ix+0),b
                ld      (ix+1),0            ; an operator (or a closer) is next
                jp      fl_loop
fl_amp:
                ld      a,(hl)              ; `&B1010`: letters and digits, verbatim
                call    fl_namech
                jr      nc,fl_val
                inc     hl
                jr      fl_amp
fl_tabspc:
                ld      b,3
                jp      fl_push
fl_usr:
                call    fl_sp               ; USR0( .. USR9(: the digit is a token
                sub     INT_DIGIT_BASE
                cp      10
                jr      nc,fl_usr_1
                inc     hl
fl_usr_1:
                ld      b,8
                jr      fl_needparen
fl_fn:                                      ; FN <name>: a function, the name's type
                call    fl_sp
                cp      'A'
                jp      c,fl_bail
                cp      'Z'+1
                jp      nc,fl_bail
                inc     hl
fl_name:                                    ; A = the first letter, HL past it,
                sub     'A'                 ; C = the class its `(` opens
                push    hl
                ld      hl,DEFTBL           ; the letter's DEF type: 2/3/4/8, the
                add     a,l                 ; widths themselves
                ld      l,a
                jr      nc,fl_name_1
                inc     h
fl_name_1:
                ld      b,(hl)
                pop     hl
fl_name_lp:
                ld      a,(hl)
                call    fl_namech
                jr      nc,fl_sfx
                inc     hl
                jr      fl_name_lp
fl_sfx:                                     ; A = the byte after the name
                inc     hl                  ; (consumed if it is a suffix)
                cp      '$'
                jr      z,fl_sfx_3
                cp      '%'
                jr      z,fl_sfx_2
                cp      '!'
                jr      z,fl_sfx_4
                cp      '#'
                jr      z,fl_sfx_8
                dec     hl                  ; no suffix
                jr      fl_sfx_end
fl_sfx_3:
                ld      b,3
                jr      fl_sfx_end
fl_sfx_2:
                ld      b,2
                jr      fl_sfx_end
fl_sfx_4:
                ld      b,4
                jr      fl_sfx_end
fl_sfx_8:
                ld      b,8
fl_sfx_end:
                call    fl_sp
                cp      '('
                jr      nz,fl_val           ; a plain variable
                inc     hl
                jr      fl_push             ; a subscript (C = $70) or an FN ($60)
fl_ff:                                      ; a $FF function: HL past its selector
                dec     hl
                ld      a,(hl)
                inc     hl
                ld      bc,$0080            ; THIS kind of FRE: class 8
                cp      FRE_TOKEN
                jr      z,fl_needparen
                sub     $81
                jp      c,fl_bail
                cp      fl_fftab_n
                jp      nc,fl_bail
                push    hl
                ld      hl,fl_fftab
                add     a,l
                ld      l,a
                jr      nc,fl_ff_1
                inc     h
fl_ff_1:
                ld      b,(hl)              ; its result type, 0 = the argument's
                pop     hl
                ld      c,$60
fl_needparen:
                call    fl_sp
                cp      '('
                jp      nz,fl_bail
                inc     hl
                ; fall through: push the function's entry

; --- fl_push: stack the entry BC, add its cost; an operand is expected next ----
fl_push:
                push    hl
                push    de
                ld      hl,(CTLLIM)         ; never within FL_STK_MARGIN of the
                ld      de,FL_STK_MARGIN    ; pool's floor: bail rather than write
                add     hl,de               ; (CF = 0: CTLLIM is far below $FFD0)
                sbc     hl,sp               ; CF iff SP is above floor + margin
                pop     de
                pop     hl
                jp      nc,fl_bail
                call    fl_cost
                add     a,e
                ld      e,a
                jr      nc,fl_push_1
                inc     d
fl_push_1:
                push    bc
                ld      (ix+1),1
                jp      fl_loop

; --- after an operand: an operator, a closer, or a separator -------------------
fl_after:
                ld      bc,$0101            ; `)`: reduce to its bracket (prec >= 1)
                cp      ')'
                jr      z,fl_reduce_bc
                inc     b                   ; `,`: likewise
                cp      ','
                jr      z,fl_reduce_bc
                cp      GT_TOKEN
                jp      c,fl_bail           ; nothing an operand may be followed by
                cp      LT_TOKEN+1
                jr      nc,fl_arith
fl_rel:                                     ; `<>`, `<=`, `=>` ... are ONE operator
                call    fl_sp
                cp      GT_TOKEN
                jr      c,fl_rel_end
                cp      LT_TOKEN+1
                jr      nc,fl_rel_end
                inc     hl
                jr      fl_rel
fl_rel_end:
                ld      a,$27               ; relational, precedence 7
                jr      fl_binop
fl_arith:
                sub     PLUS_TOKEN
                cp      fl_optab_n
                jp      nc,fl_bail
                push    hl
                ld      hl,fl_optab
                add     a,l
                ld      l,a
                jr      nc,fl_arith_1
                inc     h
fl_arith_1:
                ld      a,(hl)
                pop     hl
fl_binop:                                   ; A = the operator's class|prec
                ld      (ix+3),a
                and     $0F
                ld      (ix+2),a
                jr      fl_reduce
fl_reduce_bc:
                ld      (ix+2),c            ; precedence 1: every operator goes
                ld      (ix+3),b            ; 1 = `)`, 2 = `,`

; --- fl_reduce: pop every operator binding at least as tight as (ix+2) ---------
fl_reduce:
                pop     bc
                ld      a,c
                and     $0F
                jr      z,fl_red_stop       ; a bracket or the sentinel
                cp      (ix+2)
                jr      c,fl_red_stop       ; looser than the incoming operator
                call    fl_cost
                call    fl_sub
                ld      a,c                 ; the reduced value's type:
                and     $F0
                cp      $10
                jr      z,fl_red_max        ;   + - *: the wider of the two
                cp      $A0
                ld      a,3
                jr      z,fl_red_set        ;   concatenation: a string
                ld      a,c
                cp      $4C
                jr      z,fl_reduce         ;   unary minus: its operand's
                and     $F0
                cp      $90
                ld      a,8
                jr      z,fl_red_set        ;   / ^: a double
                ld      a,2                 ;   relational, integer op, NOT
fl_red_set:
                ld      (ix+0),a
                jr      fl_reduce
fl_red_max:
                ld      a,(ix+0)
                cp      b
                jr      nc,fl_reduce
                ld      (ix+0),b
                jr      fl_reduce
fl_red_stop:
                push    bc                  ; it stays
                ld      a,(ix+3)
                dec     a
                jr      z,fl_close
                dec     a
                jr      z,fl_comma
                ld      c,(ix+3)            ; a binary operator: stack it with its
                ld      b,(ix+0)            ; LEFT operand's type
                ld      a,c
                cp      $B8
                jp      nz,fl_push
                ld      c,$18               ; `+`: arithmetic ...
                ld      a,b
                cp      3
                jp      nz,fl_push
                ld      c,$A8               ; ... or, on a string, concatenation
                jp      fl_push
fl_comma:                                   ; inside a bracket: its next argument;
                ld      a,c                 ; at the top: a new item
                or      a
                jr      z,fl_reset
                ld      (ix+1),1
                jp      fl_loop
fl_close:
                pop     bc                  ; the bracket this `)` closes
                ld      a,c
                or      a
                jr      z,fl_bail           ; none: not an expression we follow
                call    fl_cost
                call    fl_sub
                ld      a,c
                cp      $80
                jr      nz,fl_close_1
                ld      a,l                 ; a FRE: is it THE one (`)` at the mark)?
                cp      (ix+6)
                jr      nz,fl_close_fre
                ld      a,h
                cp      (ix+7)
                jr      z,fl_done           ; DE = what stands below it
fl_close_fre:
                ld      b,4                 ; another FRE: a SINGLE. MEASURED -- the
                                            ; VG-8020 reads `FRE(0)-FRE(0)` as 12 =
                                            ; 8 + 4 (docs/binfre-vg8020-
                                            ; characterization.md §3.1); the model's
                                            ; double was never measured
                jr      fl_close_set
fl_close_1:
                cp      $50
                jp      z,fl_loop           ; `(`: the value keeps its type
                inc     b
                dec     b
                jp      z,fl_loop           ; ABS / INT / FIX: the argument's type
fl_close_set:
                ld      (ix+0),b            ; a function's result, a subscript's type
                jp      fl_loop

fl_reset:                                   ; a fresh expression: nothing pending
                ld      sp,ix
                ld      de,0
                push    de                  ; the sentinel again
                ld      (ix+1),1
                jp      fl_loop

fl_bail:
                ld      de,0                ; depth 0: the statement's base alone
fl_done:
                ld      sp,ix
                pop     bc
                pop     bc
                pop     hl                  ; HL = the base
                add     hl,de
                pop     de                  ; (the mark)
                pop     de                  ; DE = the result word's address
                ex      de,hl
                ld      (hl),e
                inc     hl
                ld      (hl),d
                ret

; --- helpers: none of them touches the entry stack ------------------------------

; fl_cost: A = the cost of entry BC (C = class|prec, B = its left operand's type).
fl_cost:
                push    hl
                ld      a,c
                rrca
                rrca
                rrca
                rrca
                and     $0F
                ld      hl,fl_costtab
                add     a,l
                ld      l,a
                jr      nc,fl_cost_1
                inc     h
fl_cost_1:
                ld      a,(hl)
                pop     hl
                bit     7,a
                ret     z
                and     $7F                 ; + the left operand's width
                add     a,b
                ret
; by class: sentinel, + - *, relational, integer op, unary, `(`, function,
; subscript, FRE, / ^, concatenation. Bit 7: + the left operand's width.
fl_costtab:
                db      0, $80+8, $80+10, 8, 6, 6, 10, 18, 10, $80+8, 2

; fl_sub: DE -= A.
fl_sub:
                push    hl
                ld      l,a
                ld      h,0
                ex      de,hl
                or      a
                sbc     hl,de
                ex      de,hl
                pop     hl
                ret

; fl_sp: skip blanks; A = the byte at HL.
fl_sp:
                ld      a,(hl)
                cp      ' '
                ret     nz
                inc     hl
                jr      fl_sp

; fl_namech: CF iff A continues a name (A-Z, 0-9, `.` -- D-NAMDOT).
fl_namech:
                cp      '.'
                scf
                ret     z
                cp      '0'
                ccf
                ret     nc
                cp      '9'+1
                ret     c
                cp      'A'
                ccf
                ret     nc
                cp      'Z'+1
                ret

; fl_issep: Z iff A starts a fresh expression (PRINT's `;`, FOR's TO / STEP,
; IF's THEN, ON's GOTO / GOSUB, PRINT USING). Preserves everything but F.
fl_issep:
                push    hl
                push    bc
                ld      hl,fl_septab
                ld      bc,fl_septab_n
                cpir
                pop     bc
                pop     hl
                ret
fl_septab:
                db      ';', TO_TOKEN, STEP_TOKEN, THEN_TOKEN, GOTO_TOKEN, GOSUB_TOKEN
                db      USING_TOKEN
fl_septab_n     equ     $ - fl_septab

; fl_tok: the token at HL (blanks skipped). Out: A = its first byte, HL past
; the whole of it -- a constant's value bytes, a $FF function's selector, a
; string literal's body and closing quote; Z iff the statement ends here (0 or
; `:`, HL left on it -- ELSE and `'` are `:`-led too). Preserves BC, DE.
fl_tok:
                call    fl_sp
                or      a
                ret     z
                cp      COLON
                ret     z
                inc     hl
                cp      '"'
                jr      z,fl_tok_str
                push    bc
                ld      b,1
                cp      INT1_TOKEN          ; $0F,<byte>
                jr      z,fl_tok_skip
                cp      PEEK_PREFIX         ; $FF,<selector>
                jr      z,fl_tok_skip
                inc     b
                cp      INT2_TOKEN          ; $1C,<word>
                jr      z,fl_tok_skip
                cp      OCT_TOKEN           ; $0B-$0E,<word>: &O, &H, line refs
                jr      c,fl_tok_done
                cp      INT1_TOKEN
                jr      c,fl_tok_skip
                ld      b,4
                cp      SNG_TOKEN           ; $1D,<4>
                jr      z,fl_tok_skip
                ld      b,8
                cp      DBL_TOKEN           ; $1F,<8>
                jr      nz,fl_tok_done
fl_tok_skip:
                inc     hl
                djnz    fl_tok_skip
fl_tok_done:
                pop     bc
                or      a                   ; NZ: A is a token, not an end
                ret
fl_tok_str:                                 ; to the closing quote, or stop ON the
                ld      a,(hl)              ; line's 0 (an unclosed literal)
                or      a
                jr      z,fl_tok_q
                inc     hl
                cp      '"'
                jr      nz,fl_tok_str
fl_tok_q:
                ld      a,'"'
                or      a
                ret

; The $FF functions' result types, by selector from $81: 3 string, 2 integer,
; 4 single, 8 double, 0 = the argument's own (ABS, INT, FIX). FRE ($8F) is
; class 8, tested before this table (fl_close_fre: a single, measured).
fl_fftab:
                db      3, 3, 3, 2, 0, 0, 8, 8   ; $81 LEFT$ RIGHT$ MID$ SGN INT ABS SQR RND
                db      8, 8, 8, 8, 8, 8, 4, 2   ; $89 SIN LOG EXP COS TAN ATN FRE INP
                db      2, 2, 3, 8, 2, 3, 2, 2   ; $91 POS LEN STR$ VAL ASC CHR$ PEEK VPEEK
                db      3, 3, 3, 2, 3, 2, 4, 8   ; $99 SPACE$ OCT$ HEX$ LPOS BIN$ CINT CSNG CDBL
                db      0, 2, 2, 2, 2, 2, 2, 2   ; $A1 FIX STICK STRIG PDL PAD DSKF FPOS CVI
                db      4, 8, 2, 2, 2, 3, 3, 3   ; $A9 CVS CVD EOF LOC LOF MKI$ MKS$ MKD$
fl_fftab_n      equ     $ - fl_fftab
; The single-byte function tokens and pseudo-variables (two parallel rows, so
; cpir cannot match a type byte), and their types: bit 7 set = a function, its
; `(` must follow. ERL and TIME are a guess (single): no row measured them.
fl_sbtok:
                db      STRING_TOKEN, INSTR_TOKEN, VARPTR_TOKEN, POINT_TOKEN
                db      VDP_TOKEN, BASE_TOKEN, PLAY_TOKEN
                db      ERR_TOKEN, CSRLIN_TOKEN, ERL_TOKEN, TIME_TOKEN, INKEY_TOKEN
fl_sbtok_n      equ     $ - fl_sbtok
fl_sbtyp:
                db      $83, $82, $82, $82
                db      $82, $82, $82
                db      2, 2, 4, 4, 3
    IF $ - fl_sbtyp - fl_sbtok_n
                db      FL_SBTYP_IS_NOT_ONE_ROW_PER_FL_SBTOK_ENTRY
    ENDIF
; The binary operators from PLUS_TOKEN ($F1): class|precedence.
;               +    -    *    /    ^    AND  OR   XOR  EQV  IMP  MOD  \
fl_optab:
                db      $B8, $18, $1B, $9B, $9D, $35, $34, $33, $32, $31, $39, $3A
fl_optab_n      equ     $ - fl_optab
