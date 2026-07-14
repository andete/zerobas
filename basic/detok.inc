; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; detok.inc — the LIST / ASCII-SAVE detokeniser body (token stream -> source text).
; ===========================================================================
; Extracted verbatim from basic/list.asm so its PLACEMENT can be gated (subrom arc
; WAVE 3, docs/spec-basic-subrom-wave3-detok.md). Two homes:
;   * lean 16 KB cart (ROM_BASE >= $4000): included inline in list.asm, streaming
;     each rendered byte through `pchar` (the PRDEST sink) exactly as before —
;     byte-identical to the pre-extraction list.asm.
;   * repack build (ROM_BASE < $4000): NOT included resident; evicted to sub-ROM
;     page 0 (sub/detok.asm) where `pchar`/`print_string` are re-bound to buffer
;     appends into DETOKBUF, `div10` is a sub-local clone, and `kwtable` is the
;     co-located sub copy (shared with the wave-2 tokeniser). The resident `detok`
;     becomes a subrom_call stub that drains DETOKBUF back through the real pchar.
;
; The body below is unaware of its home: it only issues `call pchar` /
; `jp print_string` / `call div10` / `ld ix,kwtable` and lets each build bind those
; four symbols. `ln_div_entry` lives here too (used by detok_dec); the repack build
; keeps a SEPARATE resident copy for list_num + program.asm's line-number printing,
; which stay resident.
;
; Clean-room: original code (the reverse of this project's own tokeniser). No
; constant here is new; no disassembly. See list.asm's header for the token map.
; ===========================================================================

; --- detok: render the crunched token body at (HL) to the screen ------------
; Walks tokens until the $00 terminator, printing each one's source text. The
; inverse of interp.asm's `tokenise:`; it steps the same operand bytes `tok_skip`
; does, so an operand byte is never mistaken for a token. HL is consumed.
detok:
dt_lp:
                ld      a,(hl)
                or      a
                ret     z                   ; end of line
                cp      COLON               ; ':' may fold into ' or ELSE (below)
                jp      z,dt_colon
                cp      '"'                 ; string literal -> verbatim
                jp      z,dt_string
                cp      REM_TOKEN           ; REM (and its verbatim tail)
                jp      z,dt_rem
                cp      DATA_TOKEN          ; DATA (and its verbatim ASCII body)
                jp      z,dt_data
                cp      PEEK_PREFIX         ; $FF -> 2-byte function token (PEEK)
                jp      z,dt_func
                cp      LINENO_TOKEN        ; $0E,<lineno LE> -> decimal
                jp      z,dt_lineno
                cp      LINEADDR_TOKEN      ; $0D,<addr LE> -> decimal (post-RUN form)
                jp      z,dt_lineno
                cp      INT_DIGIT_BASE      ; $11..$1A -> single digit 0..9
                jr      c,dt_notdigit
                cp      $1A+1
                jp      c,dt_digit
dt_notdigit:
                cp      INT1_TOKEN          ; $0F,<byte> -> decimal
                jp      z,dt_byte
                cp      INT2_TOKEN          ; $1C,<word LE> -> decimal
                jp      z,dt_word
                cp      HEX_TOKEN           ; $0C,<word LE> -> &Hxxxx
                jp      z,dt_hex
                cp      OCT_TOKEN           ; $0B,<word LE> -> &Oxxxx (not emitted, but
                jp      z,dt_oct            ;  rendered for completeness)
                call    detok_op            ; operator token ($EF $F1.. ) -> its char
                jr      c,dt_step1          ; CF set -> char already printed, step 1
                call    detok_kw            ; keyword token -> its text from kwtable
                jr      c,dt_step1          ; CF set -> text printed, step 1
                ; plain byte (variable letter, space, '(' ')' ',' ';' '&' etc.).
                ; detok_op / detok_kw clobbered A, so reload the byte before output.
                ld      a,(hl)
                call    pchar
dt_step1:
                inc     hl
                jr      dt_lp

; --- dt_colon: ':' — fold ":'" -> ' and ":ELSE" -> ELSE --------------------
; The tokeniser stores ' as $3A $8F $E6 and ELSE as $3A $A1; LIST renders those
; as ' and ELSE with the leading colon swallowed (public language reference). A
; plain ':' otherwise.
dt_colon:
                inc     hl
                ld      a,(hl)
                cp      ELSE_TOKEN          ; ':' $A1 -> ELSE
                jr      z,dt_else
                cp      REM_TOKEN           ; ':' $8F $E6 -> ' (apostrophe comment)
                jr      z,dt_apos_try
                dec     hl                  ; plain ':' -> emit it verbatim
                ld      a,COLON
                call    pchar
                inc     hl
                jr      dt_lp
dt_else:
                ld      a,COLON             ; ELSE is the 2-byte token $3A,$A1; render it
                ld      c,ELSE_TOKEN        ; via the tlen==2 kwtable lookup -> "ELSE"
                call    detok_kw2
                inc     hl                  ; step past $A1
                jr      dt_lp
dt_apos_try:
                inc     hl
                ld      a,(hl)
                cp      APOS_MARK           ; the $E6 marker confirms the ' form
                jr      z,dt_apos
                dec     hl                  ; not ':REM... ' form: it was ':' then REM
                ld      a,COLON
                call    pchar
                jr      dt_lp               ; HL on the REM token -> dt_rem handles it
dt_apos:
                inc     hl                  ; past $E6
                ld      a,QUOTE_REM         ; print '
                call    pchar
                jr      dt_rem_tail         ; rest of line is the verbatim comment

; --- dt_rem: REM keyword then the verbatim rest of the line -----------------
dt_rem:
                ld      a,REM_TOKEN
                call    detok_kw            ; print "REM"
                inc     hl                  ; past the REM token
dt_rem_tail:
                ld      a,(hl)              ; copy the comment tail verbatim to EOL
                or      a
                ret     z
                call    pchar
                inc     hl
                jr      dt_rem_tail

; --- dt_data: DATA keyword then its verbatim ASCII body (to ':' or EOL) -----
dt_data:
                ld      a,DATA_TOKEN
                call    detok_kw            ; print "DATA"
                inc     hl                  ; past the DATA token
dt_data_lp:
                ld      a,(hl)
                or      a
                ret     z                   ; end of line
                cp      COLON
                jp      z,dt_lp             ; ':' ends DATA -> resume normal detok
                call    pchar
                inc     hl
                jr      dt_data_lp

; --- dt_string: copy a string literal verbatim, incl. its quotes -----------
dt_string:
                ld      a,(hl)              ; opening quote
                call    pchar
                inc     hl
dt_str_lp:
                ld      a,(hl)
                or      a
                ret     z                   ; unterminated -> stop at EOL
                call    pchar
                inc     hl
                cp      '"'                 ; through the closing quote
                jr      nz,dt_str_lp
                jp      dt_lp

; --- dt_func: $FF,<fn> two-byte function token -----------------------------
; Only PEEK ($FF $97) exists today. detok_kw reverse-looks-up the 2-byte form.
dt_func:
                ld      a,(hl)              ; A = $FF (first token byte)
                inc     hl
                ld      c,(hl)              ; C = the second token byte
                call    detok_kw2           ; print the matching 2-byte keyword
                inc     hl                  ; step past the second byte
                jp      dt_lp

; --- dt_digit: $11..$1A -> a single ASCII digit -----------------------------
dt_digit:
                sub     INT_DIGIT_BASE      ; 0..9
                add     a,'0'
                call    pchar
                inc     hl
                jp      dt_lp

; --- dt_byte: $0F,<byte> -> decimal -----------------------------------------
dt_byte:
                inc     hl
                ld      e,(hl)
                ld      d,0
                inc     hl                  ; HL past the operand
                call    detok_dec
                jp      dt_lp

; --- dt_word / dt_lineno: $1C / $0E / $0D ,<word LE> -> decimal --------------
dt_word:
dt_lineno:
                inc     hl
                ld      e,(hl)              ; value low
                inc     hl
                ld      d,(hl)              ; value high
                inc     hl                  ; HL past the operand
                call    detok_dec
                jp      dt_lp

; --- dt_hex: $0C,<word LE> -> &Hxxxx ----------------------------------------
dt_hex:
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)
                inc     hl
                push    hl                  ; guard the cursor across the print
                ld      a,'&'
                call    pchar
                ld      a,'H'
                call    pchar
                call    detok_hex16         ; DE -> uppercase hex, no leading zeros
                pop     hl
                jp      dt_lp

; --- dt_oct: $0B,<word LE> -> &Oxxxx ----------------------------------------
; &O is reserved but never emitted by the tokeniser; rendered here so the
; detokeniser covers the whole `tok_skip` token set.
dt_oct:
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)
                inc     hl
                push    hl
                ld      a,'&'
                call    pchar
                ld      a,'O'
                call    pchar
                call    detok_oct16
                pop     hl
                jp      dt_lp

; --- detok_dec: print DE as unsigned decimal (no sign, no spaces) -----------
; Reuses list_num's formatter, which prints HL. Preserves HL? No — it clobbers
; HL via div10, so callers guard the cursor. Here detok already advanced HL past
; the operand and re-loads from the stack on return, so we save/restore it.
detok_dec:
                push    hl
                ld      h,d
                ld      l,e
                call    ln_div_entry        ; print HL as bare unsigned decimal
                pop     hl
                ret

; ln_div_entry: print HL as bare unsigned decimal (the digit loop of list_num).
ln_div_entry:
                ld      a,$FF
                push    af
dde_div:
                call    div10
                push    af
                ld      a,h
                or      l
                jr      nz,dde_div
                ld      de,NUMBUF
dde_wr:
                pop     af
                cp      $FF
                jr      z,dde_tail
                add     a,'0'
                ld      (de),a
                inc     de
                jr      dde_wr
dde_tail:
                xor     a
                ld      (de),a
                ld      hl,NUMBUF
                jp      print_string

; --- detok_hex16: print DE as uppercase hex, no leading zeros (>=1 digit) ----
; Build into NUMBUF most-significant nibble first, skipping leading zeros.
detok_hex16:
                ld      b,0                 ; B = "a non-zero nibble was seen" flag
                ld      hl,NUMBUF
                ld      a,d
                call    dh_nib_hi
                ld      a,d
                call    dh_nib_lo
                ld      a,e
                call    dh_nib_hi
                ld      a,e
                ld      c,a                 ; the last nibble is always emitted
                call    dh_nib_lo_last
                xor     a
                ld      (hl),a              ; 0-terminate
                ld      hl,NUMBUF
                jp      print_string
dh_nib_hi:
                rrca
                rrca
                rrca
                rrca
dh_nib_lo:
                and     $0F
                jr      nz,dh_emit          ; non-zero nibble -> always emit
                ld      a,b
                or      a
                ret     z                   ; still in leading zeros -> skip
                xor     a                   ; (a zero after a non-zero) -> emit 0
dh_emit:
                ld      b,1                 ; mark: from now on emit everything
                call    hex_digit
                ld      (hl),a
                inc     hl
                ret
dh_nib_lo_last:
                ld      a,c
                and     $0F
                call    hex_digit
                ld      (hl),a
                inc     hl
                ret

; --- detok_oct16: print DE as octal, no leading zeros (>=1 digit) ------------
; 16-bit value -> 6 octal digits MSB-first (digit 0 = bit 15 alone, digits 1..5
; = three bits each from bits 14..0), built into NUMBUF with leading zeros
; suppressed but the last digit always emitted.
detok_oct16:
                ld      b,0                 ; leading-zero suppression flag
                ld      hl,NUMBUF
                ld      a,d                 ; digit 0 = bit 15 (0 or 1)
                rlca                        ; CF = bit 15
                ld      a,0
                rla                         ; A = bit 15
                call    do_odigit_susp      ; emit unless a suppressed leading zero
                sla     e                   ; discard bit 15 (already emitted)
                rl      d
                ld      c,5                 ; five remaining 3-bit groups
do_olp:
                call    de_shift3           ; A = next 3 bits (DE <<= 3)
                dec     c
                jr      z,do_olast          ; the last group is always emitted
                call    do_odigit_susp
                jr      do_olp
do_olast:
                call    oct_digit
                ld      (hl),a
                inc     hl
                xor     a
                ld      (hl),a
                ld      hl,NUMBUF
                jp      print_string
; emit octal digit in A unless it is a leading zero (B tracks "seen non-zero").
do_odigit_susp:
                or      a
                jr      nz,do_oset
                ld      a,b
                or      a
                ret     z                   ; leading zero -> skip
                xor     a                   ; non-leading zero -> emit '0'
do_oset:
                ld      b,1
                call    oct_digit
                ld      (hl),a
                inc     hl
                ret
; de_shift3: shift DE left 3 bits, return the 3 bits that fell off the top in A.
de_shift3:
                ld      a,0
                ; bit 1
                sla     e
                rl      d
                rla
                sla     e
                rl      d
                rla
                sla     e
                rl      d
                rla
                and     7
                ret

; --- hex_digit / oct_digit: A (0..15 / 0..7) -> ASCII -----------------------
hex_digit:
                cp      10
                jr      c,hd_dec
                add     a,'A'-10
                ret
hd_dec:
                add     a,'0'
                ret
oct_digit:
                add     a,'0'
                ret

; --- detok_op: single-byte operator token -> its source char ----------------
; in:  A = token byte. out: CF set + the char printed (A clobbered) if it was an
; operator; CF clear (nothing printed) otherwise. The reverse of tk_op_*.
detok_op:
                cp      EQ_TOKEN            ; '='
                jr      z,dop_eq
                cp      PLUS_TOKEN          ; '+'
                jr      z,dop_plus
                cp      MINUS_TOKEN         ; '-'
                jr      z,dop_minus
                cp      STAR_TOKEN          ; '*'
                jr      z,dop_star
                cp      DIV_TOKEN           ; '/'
                jr      z,dop_div
                cp      IDIV_TOKEN          ; '\'
                jr      z,dop_idiv
    IF ROM_BASE < $4000
                cp      POW_TOKEN           ; '^' (math pack slice 2c, repack-
                jr      z,dop_pow           ; only -- docs/spec-basic-mathpack-
                                            ; slice2.md §13.3; lean has no `^`)
    ENDIF
                cp      GT_TOKEN            ; '>'
                jr      z,dop_gt
                cp      LT_TOKEN            ; '<'
                jr      z,dop_lt
                or      a                   ; not an operator -> CF clear
                ret
dop_eq:         ld      a,'='
                jr      dop_emit
dop_plus:       ld      a,'+'
                jr      dop_emit
dop_minus:      ld      a,'-'
                jr      dop_emit
dop_star:       ld      a,'*'
                jr      dop_emit
dop_div:        ld      a,'/'
                jr      dop_emit
dop_idiv:       ld      a,'\'
                jr      dop_emit
    IF ROM_BASE < $4000
dop_pow:        ld      a,'^'
                jr      dop_emit
    ENDIF
dop_gt:         ld      a,'>'
                jr      dop_emit
dop_lt:         ld      a,'<'
dop_emit:
                call    pchar
                scf
                ret

; --- detok_kw: single-byte keyword token -> its text (reverse kwtable) -------
; in:  A = token byte. out: CF set + the keyword text printed if a tlen==1 entry
; in kwtable carries this token; CF clear (nothing printed) otherwise. Preserves
; the caller's HL (it walks the table via IX/IY). Reverse of match_kw.
detok_kw:
                ld      c,a                 ; C = the wanted token byte
                push    hl
                push    bc
                push    ix
                ld      ix,kwtable
dk_entry:
                ld      a,(ix+0)            ; keyword length (0 = end of table)
                or      a
                jr      z,dk_none
                ld      b,a                 ; B = klen
                push    ix
                pop     iy
                inc     iy                  ; IY -> the keyword chars
                ; advance IX to the [tlen] byte: skip [klen] + klen chars
                ld      e,a
                ld      d,0
                inc     de                  ; DE = 1 + klen
                add     ix,de               ; IX -> [tlen]
                ld      a,(ix+0)            ; tlen
                cp      1                   ; only single-byte tokens match here
                jr      nz,dk_next
                ld      a,(ix+1)            ; the token byte
                cp      c
                jr      z,dk_hit
dk_next:
                ; skip [tlen] + tlen token bytes -> next entry's [klen]
                ld      a,(ix+0)
                ld      e,a
                ld      d,0
                inc     de
                add     ix,de
                jr      dk_entry
dk_hit:
                ; IY -> klen keyword chars; print B of them.
dk_print:
                ld      a,(iy+0)
                push    bc
                push    iy
                call    pchar
                pop     iy
                pop     bc
                inc     iy
                djnz    dk_print
                pop     ix
                pop     bc
                pop     hl
                scf
                ret
dk_none:
                pop     ix
                pop     bc
                pop     hl
                or      a                   ; CF clear -> not a keyword token
                ret

; --- detok_kw2: 2-byte function/keyword token ($FF + C) -> its text ----------
; in:  A = first token byte ($FF), C = second token byte. Prints the matching
; tlen==2 kwtable entry's text (PEEK for $FF $97). Preserves HL. If no match,
; prints nothing (defensive; the tokeniser only emits PEEK in this form).
detok_kw2:
                ld      b,a                 ; B = first token byte ($FF)
                push    hl
                push    bc
                push    ix
                ld      ix,kwtable
dk2_entry:
                ld      a,(ix+0)            ; klen (0 = end)
                or      a
                jr      z,dk2_none
                push    ix
                pop     iy
                inc     iy                  ; IY -> keyword chars
                ld      e,a
                ld      d,0
                inc     de
                add     ix,de               ; IX -> [tlen]
                ld      a,(ix+0)            ; tlen
                cp      2                   ; want a 2-byte token entry
                jr      nz,dk2_next
                ld      a,(ix+1)            ; first token byte
                cp      b
                jr      nz,dk2_next
                ld      a,(ix+2)            ; second token byte
                cp      c
                jr      z,dk2_hit
dk2_next:
                ld      a,(ix+0)
                ld      e,a
                ld      d,0
                inc     de
                add     ix,de
                jr      dk2_entry
dk2_hit:
                ; klen = (address of [tlen]) - (address of first keyword char). IY
                ; points at the chars, IX at [tlen], so the difference is klen.
                push    ix
                pop     de                  ; DE = address of [tlen]
                push    iy
                pop     hl                  ; HL = address of first char
                ex      de,hl
                or      a
                sbc     hl,de               ; HL = [tlen]addr - charsaddr = klen
                ld      b,l                 ; B = klen (fits in a byte)
dk2_print:
                ld      a,(iy+0)
                push    bc
                push    iy
                call    pchar
                pop     iy
                pop     bc
                inc     iy
                djnz    dk2_print
                pop     ix
                pop     bc
                pop     hl
                ret
dk2_none:
                pop     ix
                pop     bc
                pop     hl
                ret
