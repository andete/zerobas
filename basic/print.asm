; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause

; print.asm — the PRINT statement.
;
;   PRINT [<item>] [ <sep> <item> ]...        sep = ';' or ','
;
; An <item> is a string literal ("...") or a numeric expression. ';' joins items
; with no spacing; ',' advances to the next 14-column tab zone. A trailing
; separator suppresses the closing newline; otherwise PRINT ends the line with
; CR/LF. A bare PRINT prints an empty line. (The `?` abbreviation crunches to the
; PRINT token in the tokeniser.)
;
; Numbers print in the MSX integer format: a leading space for non-negative
; values (the sign position) or '-' for negative, the decimal digits with no
; leading zeros, and a trailing space (public MSX-BASIC language reference). The
; value is treated as signed 16-bit, matching MSX integer variables.
;
; zerobas has no string engine yet, so string *variables* and string functions
; (CHR$, etc.) are not printable — only string literals and numeric expressions.
;
; Clean-room: original code. PRINT *semantics* + number format from the public
; MSX-BASIC language reference; CHPUT/CSRX from C-BIOS. No disassembly.
;
; Entry: ex_print, HL -> the PRINT token.

ex_print:
                inc     hl                  ; past the PRINT token
exp_loop:
                call    skip_spaces
                ld      a,(hl)
                or      a
                jr      z,exp_nl_ret        ; end of line -> newline, done
                cp      COLON
                jr      z,exp_nl_stmt       ; ':' -> newline, then next statement
                cp      ';'
                jr      z,exp_semi
                cp      ','
                jp      z,exp_comma
                cp      '"'
                jp      z,exp_str
                call    eval                ; numeric expression -> DE = value
                call    print_number
                jp      exp_loop
exp_semi:
                inc     hl                  ; ';' = no spacing
                call    skip_spaces
                ld      a,(hl)
                or      a
                ret     z                   ; trailing ';' at EOL -> no newline
                cp      COLON
                jp      z,exec_stmt         ; trailing ';' before ':' -> no newline
                jp      exp_loop
exp_nl_ret:
                call    print_crlf
                ret
exp_nl_stmt:
                call    print_crlf
                jp      exec_stmt           ; HL on ':' -> exec_stmt steps over it
exp_str:
                inc     hl                  ; past the opening quote
exp_str_lp:
                ld      a,(hl)
                or      a
                jp      z,exp_loop          ; unterminated -> stop (back to loop -> EOL)
                cp      '"'
                jr      z,exp_str_close
                push    hl                  ; CHPUT makes no register guarantees
                call    CHPUT
                pop     hl
                inc     hl
                jr      exp_str_lp
exp_str_close:
                inc     hl                  ; past the closing quote
                jp      exp_loop
exp_comma:
                inc     hl
                call    print_comma_zone    ; pad to the next 14-column zone
                call    skip_spaces
                ld      a,(hl)
                or      a
                ret     z                   ; trailing ',' at EOL -> no newline
                cp      COLON
                jp      z,exec_stmt         ; trailing ',' before ':' -> no newline
                jp      exp_loop

; --- print_number: DE = signed-16 value -> screen --------------------------
; Formats into NUMBUF (sign/space, digits, trailing space, 0) then print_string.
; The conversion touches no BIOS, so registers are safe until print_string.
print_number:
                ld      a,d
                add     a,a                 ; CF = sign bit (bit 7 of D)
                jr      c,pn_neg
                ld      a,' '               ; non-negative: sign-position space
                ld      (NUMBUF),a
                ex      de,hl               ; HL = magnitude (the value)
                jr      pn_conv
pn_neg:
                ld      a,'-'
                ld      (NUMBUF),a
                ld      hl,0
                or      a
                sbc     hl,de               ; HL = -value = magnitude
pn_conv:
                ld      a,$FF               ; stack sentinel (not a digit)
                push    af
pn_div:
                call    div10               ; HL /= 10, A = remainder 0..9
                push    af                  ; push digit (least-significant first)
                ld      a,h
                or      l
                jr      nz,pn_div
                ld      de,NUMBUF+1         ; write digits after the sign char
pn_wr:
                pop     af
                cp      $FF                 ; sentinel -> digits done
                jr      z,pn_tail
                add     a,'0'
                ld      (de),a
                inc     de
                jr      pn_wr
pn_tail:
                ld      a,' '               ; trailing space (MSX number format)
                ld      (de),a
                inc     de
                xor     a
                ld      (de),a              ; 0-terminate
                ld      hl,NUMBUF
                jp      print_string        ; guards HL across CHPUT

; --- div10: HL = HL/10, A = remainder (0..9) -------------------------------
; Shift-and-subtract (standard binary divide). Clobbers A, B, HL.
div10:
                xor     a
                ld      b,16
d10_lp:
                add     hl,hl               ; shift dividend left, into quotient
                rla                         ; A = running remainder<<1 | carry
                cp      10
                jr      c,d10_skip
                sub     10
                inc     l                   ; set quotient bit
d10_skip:
                djnz    d10_lp
                ret

; --- print_crlf: CR + LF ---------------------------------------------------
print_crlf:
                ld      a,13
                call    CHPUT
                ld      a,10
                jp      CHPUT

; --- print_comma_zone: pad with spaces to the next 14-column tab zone -------
; MSX PRINT comma zones are 14 characters (public language reference). Reads the
; current column from CSRX (1-based). Clobbers A, B.
print_comma_zone:
                ld      a,(CSRX)
                dec     a                   ; 0-based column
pcz_mod:
                cp      14
                jr      c,pcz_have
                sub     14
                jr      pcz_mod
pcz_have:
                ld      b,a                 ; column within the zone (0..13)
                ld      a,14
                sub     b                   ; spaces to the next zone (1..14)
                ld      b,a
pcz_pad:
                ld      a,' '
                push    bc                  ; CHPUT makes no register guarantees
                call    CHPUT
                pop     bc
                djnz    pcz_pad
                ret
