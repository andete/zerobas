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
                ; PRINT #n, … (file form): redirect the item loop to the channel.
                call    skip_spaces
                ld      a,(hl)
                cp      '#'
                jr      nz,exp_loop         ; no '#': ordinary screen PRINT
                inc     hl
                call    eval                ; DE = channel number
                ld      a,e
                call    fch_valid
                jp      nc,load_error       ; 0 or > MAXF -> bad file number
                push    hl                  ; guard text cursor (fch_select uses LDIR)
                ld      a,e
                call    fch_select          ; make channel e live; FCH_MODE = its mode
                pop     hl
                ld      a,(FCH_MODE)
                cp      2                   ; must be open FOR OUTPUT
                jp      nz,load_error
                call    skip_spaces         ; consume the separator after #n (','/';')
                ld      a,(hl)
                cp      ','
                jr      z,exp_hash_sep
                cp      ';'
                jr      nz,exp_hash_go      ; PRINT#1  (no items) -> just the CRLF
exp_hash_sep:
                inc     hl
exp_hash_go:
                ld      a,1
                ld      (PRDEST),a          ; items now stream to the file channel
                ; fall through into the shared item loop
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
                call    is_letter           ; a `$`-suffixed string variable?
                jr      nc,exp_num
                call    var_str_type        ; A=1 if `$` suffix
                or      a
                jr      nz,exp_strvar       ; string variable -> print its value
exp_num:
                call    eval                ; numeric expression -> DE = value
                push    hl                  ; print_number divides the value in HL,
                call    print_number        ;  clobbering the token cursor — guard it
                pop     hl                  ;  (same as exp_strvar does for print_strval)
                jp      exp_loop
exp_strvar:
                call    str_eval            ; STRPTR -> the var's value, HL advanced
                jp      nc,exp_num          ; defensive: fall back to numeric
                push    hl                  ; print_strval clobbers HL (token cursor)
                call    print_strval        ; emit the descriptor's bytes
                pop     hl
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
                call    pchar               ; emit to screen or file (PRDEST)
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
                call    pchar
                ld      a,10
                jp      pchar

; pchar — emit the byte in A to the current PRINT destination: the screen via
; CHPUT when PRDEST=0, or the open file channel via fat_io_putbyte when PRDEST=1.
; Preserves EVERY register (fat_io_putbyte's DSKIO clobbers the file, so we
; save/restore), making it a drop-in for `call CHPUT` at every PRINT emit site.
; A disk-full CY from the file path is best-effort-ignored here.
pchar:
                push    hl
                push    de
                push    bc
                push    af
                ld      c,a                 ; C = byte to emit
                ld      a,(PRDEST)
                or      a
                ld      a,c
                jr      nz,pch_file
                call    CHPUT
                jr      pch_done
pch_file:
                call    fat_io_putbyte
pch_done:
                pop     af
                pop     bc
                pop     de
                pop     hl
                ret

; --- print_comma_zone: pad with spaces to the next 14-column tab zone -------
; MSX PRINT comma zones are 14 characters (public language reference). Reads the
; current column from CSRX (1-based). Clobbers A, B.
; Divergence (documented, out of loader-stub scope): real MSX wraps a comma tab
; to a NEW LINE once the next zone would pass the screen width; this only pads on
; the current line. See basic/PROVENANCE.md §PRINT + basic_probe_print.py.
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
                call    pchar               ; screen or file (PRDEST); preserves BC
                djnz    pcz_pad
                ret
