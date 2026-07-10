; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

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
                cp      USING_TOKEN         ; PRINT USING "fmt"; values  (formatted)
                jp      z,ex_print_using
                cp      '#'
                jr      nz,exp_loop         ; no '#': ordinary screen PRINT
                inc     hl
                call    eval                ; DE = channel number
                ld      a,e
                call    fch_valid
                jp      nc,load_error       ; 0 or > MAXF -> bad file number
                ; classify the channel by its stored mode WITHOUT selecting it: a
                ; device channel (LPT:/CRT:, FCH_MODES 5/6) owns no fat.asm context,
                ; so fch_select would LDIR a garbage buffer over the engine globals.
                push    hl                  ; save the text cursor (add hl,de clobbers HL)
                ld      d,0                 ; DE = channel (e preserved by fch_valid)
                ld      hl,FCH_MODES
                add     hl,de
                ld      a,(hl)              ; A = FCH_MODES[ch]
                pop     hl                  ; restore the text cursor
                cp      LPT_MODE
                jr      z,exp_dev_lpt
                cp      CRT_MODE
                jr      z,exp_dev_crt
                cp      CAS_OUT_MODE
                jr      z,exp_dev_cas
                cp      CAS_IN_MODE
                jp      z,load_error        ; PRINT# to an INPUT tape channel -> error
                                            ; (never fch_select it: no fat ctx exists)
                ; --- disk file channel (unchanged) ---
                push    hl                  ; guard text cursor (fch_select uses LDIR)
                ld      a,e
                call    fch_select          ; make channel e live; FCH_MODE = its mode
                pop     hl
                ld      a,(FCH_MODE)
                cp      2                   ; must be open FOR OUTPUT
                jp      nz,load_error
                xor     a
                ld      (PRDEV),a           ; 0 = disk sink
                jr      exp_sep
exp_dev_lpt:
                ld      a,1                 ; 1 = LPT: printer sink
                jr      exp_dev_set
exp_dev_crt:
                ld      a,2                 ; 2 = CRT: screen sink
                jr      exp_dev_set
exp_dev_cas:
                ld      a,3                 ; 3 = cassette sink (cas_wbyte, buffered)
exp_dev_set:
                ld      (PRDEV),a
exp_sep:
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
                ; PRINT #n[,] USING "fmt"; … — the file form. PRDEST is already 1, so
                ; the USING formatter (which emits through pchar / print_crlf) writes
                ; to the channel. The comma after #n was consumed above; USING may also
                ; follow #n directly (no comma) — both crunch to … 23 <ch> [2C] E4 ….
                call    skip_spaces
                ld      a,(hl)
                cp      USING_TOKEN
                jp      z,ex_print_using
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
    IF ROM_BASE < $4000
                cp      PEEK_PREFIX         ; $FF function token -> maybe a string function
                jp      z,exp_maybe_strfn   ; (repack: CHR$/STR$/LEFT$/…; falls back to exp_num)
                cp      STRING_TOKEN        ; $E3 STRING$(n,c) -> string (single-byte token,
                jp      z,exp_maybe_strfn   ;  not $FF-prefixed; str_eval handles it, prints)
                cp      INKEY_TOKEN         ; $EC INKEY$ -> string (single-byte token; str_eval
                jp      z,exp_maybe_strfn   ;  reads the key, prints it — else PRINT INKEY$ mismatches)
    ENDIF
                call    is_letter           ; a `$`-suffixed string variable?
                jr      nc,exp_num
                call    var_str_type        ; A=1 if `$` suffix
                or      a
                jr      nz,exp_strvar       ; string variable -> print its value
exp_num:
                call    eval                ; numeric expression -> DE = value
    IF ROM_BASE < $4000
                ld      a,(TMISMATCH)       ; D-2: `PRINT (A$<5)` aborts the whole line
                or      a                   ; before the newline/next item (mirrors ex_if)
                jp      nz,type_mismatch_error
    ENDIF
                push    hl                  ; print_number divides the value in HL,
                call    print_number        ;  clobbering the token cursor — guard it
                pop     hl                  ;  (same as exp_strvar does for print_strval)
                jp      exp_loop
exp_strvar:
    IF ROM_BASE < $4000
                ; S2 (spec-basic-print-unparen-compare.md §3): remember the
                ; operand START before str_eval consumes it -- if a relational
                ; operator follows the string value, this item is really the
                ; LHS of an unparenthesized comparison (`PRINT A$="YES"`) and
                ; must be re-parsed from here via eval/ev_rel instead of printed.
                push    hl                  ; operand START (peek may reparse via eval)
    ENDIF
                call    str_eval            ; STRPTR -> the var's value, HL advanced
    IF ROM_BASE < $4000
                jr      nc,exps_fallback    ; defensive: not a string after all
                call    skip_spaces
                ld      a,(hl)
                call    relop_peek          ; ZF=1 iff (HL) is a relop token
                jr      nz,exps_print       ; no relop -> plain PRINT (below)
                pop     hl                  ; relop follows -> restore the operand START
                jp      exp_num             ; re-drive via eval -> ev_rel (-1/0, or D-2 abort)
exps_print:
                pop     de                  ; drop the saved operand-start (balances the
                                             ;  push above; str_eval already clobbers DE,
                                             ;  so there is nothing in DE worth preserving)
                push    hl                  ; print_strval clobbers HL (token cursor)
                call    print_strval        ; emit the descriptor's bytes
                pop     hl
                jp      exp_loop
exps_fallback:
                pop     hl                  ; balance the operand-start push (str_eval left
                                             ;  HL unmoved on failure, so this restores the
                                             ;  same cursor exp_num would see un-gated)
                jp      exp_num
    ELSE
                jp      nc,exp_num          ; defensive: fall back to numeric
                push    hl                  ; print_strval clobbers HL (token cursor)
                call    print_strval        ; emit the descriptor's bytes
                pop     hl
                jp      exp_loop
    ENDIF
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
    IF ROM_BASE < $4000
                ; Repack: a PRINT item that LEADS with a string literal but is
                ; followed by '+' is a string concat (`"a"+"b"`, `"n="+STR$(x)`),
                ; and one followed by a relop (S2: `PRINT "YES"=A$`) is the LHS of
                ; an unparenthesized comparison. Route either through the
                ; concat-aware str_eval (exp_strvar's body, which now also owns the
                ; relop_peek gate) so both forms fold like every other string
                ; context; a plain literal (no trailing '+' or relop) keeps the
                ; fast char-by-char path below, so a literal longer than STRMAX
                ; still prints in full (un-clamped).
                call    str_lit_concat_q    ; ZF=1 if '+' or a relop follows the literal
                jr      z,exp_strvar        ; HL still @ opening quote -> str_eval
    ENDIF
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
    IF ROM_BASE < $4000
; --- str_lit_concat_q: does '+' or a relop follow this string literal? --------
; HL -> the opening '"' of a literal PRINT item. Scans past the closing quote and
; the intervening spaces (exactly as str_concat_tail does) and reports whether the
; next token is the '+' concat operator OR a relational operator (S2: a literal
; that leads an unparenthesized comparison, e.g. `PRINT "YES"=A$`, must ALSO
; route through the str_eval path so exp_strvar's relop_peek gate sees it). HL is
; preserved. out: ZF=1 iff PLUS_TOKEN or a relop token ($EE/$EF/$F0) follows.
str_lit_concat_q:
                push    hl
                inc     hl                  ; past the opening quote
slcq_lp:
                ld      a,(hl)
                or      a
                jr      z,slcq_no           ; unterminated (EOL) -> not a concat/compare
                inc     hl
                cp      '"'
                jr      nz,slcq_lp          ; scan to the closing quote
                call    skip_spaces         ; HL -> next non-space token
                ld      a,(hl)
                cp      PLUS_TOKEN          ; '+' ($F1) ? ZF=1 if so
                jr      z,slcq_yes
                call    relop_peek          ; else: a relop ($EE/$EF/$F0) follows? (str-engine.asm)
slcq_yes:
                pop     hl
                ret
slcq_no:
                pop     hl
                or      1                   ; A nonzero -> ZF=0 (not concat/compare)
                ret
    ENDIF
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
                ld      c,a                 ; C = byte to emit (survives the PRDEV load)
                ld      a,(PRDEST)
                or      a
                ld      a,c
                jr      nz,pch_file
                call    CHPUT
                jr      pch_done
pch_file:
                ; PRDEST=1: PRDEV selects the sink. 0=disk file, 1=LPT printer,
                ; 2=CRT screen (a device channel from OPEN"LPT:"/"CRT:"), 3=cassette
                ; (SAVE"CAS:",A's block-framed tape sink). C=byte.
                ld      a,(PRDEV)
                or      a
                jr      z,pch_disk          ; 0 -> disk file
                dec     a
                jr      z,pch_lpt           ; 1 -> LPT: printer
                dec     a
                jr      z,pch_crt           ; 2 -> CRT: screen
                ld      a,c                 ; 3 -> cassette ASCII data block
                call    cas_wbyte
                jr      pch_done
pch_crt:
                ld      a,c
                call    CHPUT
                jr      pch_done
pch_lpt:
                ld      a,c
                call    LPTOUT
                jr      pch_done
pch_disk:
                ld      a,c
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
