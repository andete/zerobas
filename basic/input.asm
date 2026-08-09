; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; input.asm — console INPUT / LINE INPUT (Phase-3 interactivity slice).
;
; The keyboard forms `INPUT ["prompt"{;|,}] var[,var...]` and
; `LINE INPUT ["prompt";] A$`. The FILE forms (`INPUT #n`, `LINE INPUT #n`) ship
; already in basic/files.asm; both stub the console form ("console INPUT = Phase 3").
; This file fills that stub — reached from files.asm's `input_common` via a gated
; `jp nz,input_console` (repack build only). Spec: docs/spec-basic-input.md.
;
; Almost entirely COMPOSITION of shipped routines, not new mechanism (spec §2):
;   read_line (repl.asm)              keyboard -> LINEBUF, 0-terminated ASCII
;   read_into_strscr + ARL_GETBYTE    field/line splitter -> STRSCR (files.asm);
;     + FCH_RDMODE                      re-pointed here at `linebuf_getbyte`
;   tgt_parse / tgt_store_num /       lvalue TARGET parse + store (vars.asm),
;     tgt_store_str / var_str_type      shared verbatim with ex_read (D-ARYLV,
;                                       docs/spec-basic-arylv.md). These wrap
;                                       var_name_key / var_store_fac / str_set_key,
;                                       which is what this file called directly
;                                       until an ARRAY ELEMENT became a legal
;                                       target on all THREE of its arms.
; The only genuinely new code is `linebuf_getbyte` (the LINEBUF byte source), the
; prompt/var-list driver, the strict numeric-field validator `input_num_field`, and
; the D-2 re-prompt loop (?redo from start / ?extra ignored).
;
; FCH_RDMODE distinguishes the two entries (set by files.asm before the hook):
;   0 = INPUT       -> "? " prompt, comma-separated field list, per-var parse
;   1 = LINE INPUT  -> no "? ", the whole line into one string var
;
; Clean-room: original code. INPUT *semantics* (the `;`/`,` prompt separators, the
; re-prompt on a bad/short line, integer numeric fields) are from the public
; MSX-BASIC language reference; the re-prompt WORDING is zerobas's own lowercase
; (like "syntax error" / "type mismatch"), NOT MSX's verbatim "?Redo from start".
; No disassembly.

; --- input_console: the console INPUT / LINE INPUT driver -------------------
; in: HL -> first token after INPUT (a '"' prompt or the first variable);
;     FCH_RDMODE = 0 (INPUT) / 1 (LINE INPUT).
input_console:
                xor     a
                ld      (PRDEST),a          ; INPUT is a console statement -> screen
                ; --- optional prompt literal + separator ---
                call    skip_spaces
                cp      '"'
                jr      nz,inpc_noprompt
                inc     hl                  ; past the opening quote
inpc_plit:
                ld      a,(hl)
                or      a
                jp      z,stmt_error        ; unterminated prompt literal
                inc     hl
                cp      '"'
                jr      z,inpc_psep
                call    CHPUT               ; echo the prompt char to the screen
                jr      inpc_plit
inpc_psep:
                call    skip_spaces
                cp      ';'
                jr      z,inpc_psemi
                cp      ','
                jr      z,inpc_pcomma
                jp      stmt_error          ; a prompt must be followed by ';' or ','
inpc_psemi:
                inc     hl                  ; ';' : INPUT adds "? ", LINE INPUT nothing
                ld      a,(FCH_RDMODE)
                or      a
                jr      nz,inpc_dispatch
                call    inpc_print_q
                jr      inpc_dispatch
inpc_pcomma:
                inc     hl                  ; ',' : never "? "
                jr      inpc_dispatch
inpc_noprompt:
                ld      a,(FCH_RDMODE)      ; no prompt: INPUT adds "? ", LINE INPUT nothing
                or      a
                jr      nz,inpc_dispatch
                call    inpc_print_q
inpc_dispatch:
                ; HL -> the first variable. Branch on the read mode.
                ld      a,(FCH_RDMODE)
                or      a
                jp      nz,inpc_line        ; LINE INPUT -> whole line into one $-var
                ; --- INPUT: comma-separated variable list ---
                push    hl                  ; [stack: varstart] — survives every ?redo
inpc_reread:
                call    read_line           ; LINEBUF <- typed line (clobbers HL,A,B)
                xor     a
                ld      (INP_CURSOR),a      ; reset the LINEBUF read cursor
                ld      de,linebuf_getbyte
                ld      (ARL_GETBYTE),de    ; field splitter reads from LINEBUF
                pop     hl                  ; HL = varstart
                push    hl                  ; keep it for a possible ?redo re-read
inpc_vloop:
                call    skip_spaces
                call    is_letter
                jp      nc,inpc_synpop      ; not a variable -> syntax error
                call    var_str_type        ; A = 1 if the name carries a '$'
                or      a
                jr      nz,inpc_vstr
                ; --- numeric variable ---
                call    tgt_parse           ; D-ARYLV: BC = key, HL past the whole
                                            ; reference, (TGT_ADDR) = element address or
                                            ; 0; (VARTYPE) = the resolved type (F3).
                                            ; A already holds the mode (0) it wants.
                jp      nz,fp_runtime_error ; a bad subscript raises the ARRAY engine's
                                            ; own error. [varstart] is still on the
                                            ; stack and that is FINE: fre_abort_low does
                                            ; `ld sp,(SAVSTK)` as its own first act
                                            ; (D-CUR-D), so raising here is
                                            ; DEPTH-INDEPENDENT -- and the ON ERROR trap
                                            ; branch resets SP the same way.
                push    bc                  ; [stack: varstart, key]
                push    hl                  ; [stack: varstart, key, textcur]
                call    read_into_strscr    ; STRSCR <- the next field (mode 0)
                call    input_num_field     ; STRSCR -> DE; CF set if not an integer
                jr      c,inpc_redo3        ; bad numeric field -> ?redo
                pop     hl                  ; textcur
                pop     bc                  ; key
                push    hl                  ; guard textcur across the store
                call    tgt_store_num       ; D-ARYLV: var[key] := DE, or the resolved
                                            ; ELEMENT := DE, coerced either way (vars.asm)
                pop     hl
                jr      inpc_after
inpc_vstr:
                ; --- string variable ---
                call    tgt_parse           ; D-ARYLV: BC = key, HL past the whole
                                            ; reference, (TGT_ADDR) per above; A already
                                            ; holds the mode (1) it wants
                jp      nz,fp_runtime_error ; same depth-independent abort as the numeric
                                            ; arm above
                push    bc
                push    hl
                call    read_into_strscr    ; STRSCR <- the next field (mode 0)
                pop     hl
                pop     bc
                push    hl                  ; guard textcur across the store
                call    tgt_store_str       ; D-ARYLV: var$[key] = the field bytes, or
                                            ; the resolved element (op=3 COPY_STR)
                pop     hl
                ; arrays slice-4c (§7.3) follow-up: a scalar-CHAIN OOM here
                ; sets FPERR (str_set_key's own ARY_OP=5 path) but does not
                ; itself abort (var_alloc_or_find's contract) -- was silently
                ; swallowed (FPERR cleared at the next exec_stmt) before this
                ; check. ⚠️ D-STMTPEND: that swallow no longer exists anywhere --
                ; the statement boundary REPORTS a live code instead of clearing
                ; it -- so this check is now about WHERE the abort lands (here,
                ; with the stack contract below honoured) rather than about
                ; whether one happens at all. Reuses check_expr_errors_popbc
                ; (interp.asm) rather
                ; than a bespoke checker: [stack: varstart] is live here
                ; (pushed at inpc_dispatch, line 83), matching that routine's
                ; own "discard our return addr + ONE caller word" abort
                ; contract exactly (TMISMATCH is always 0 here -- INPUT never
                ; sets it -- so only its FPERR half ever fires). OK path is a
                ; plain `ret`, HL (textcur, needed by inpc_after below)
                ; untouched.
                call    check_expr_errors_popbc
inpc_after:
                call    skip_spaces
                cp      ','
                jr      z,inpc_morevars
                ; end of the variable list: any leftover input -> ?extra ignored.
                push    hl                  ; guard textcur across inpc_more_input
                call    inpc_more_input     ; ZF=1 iff LINEBUF still has an unread field
                jr      z,inpc_extra
                pop     hl
                pop     bc                  ; drop varstart
                jp      exec_stmt
inpc_extra:
                ld      hl,msg_extra
                call    print_msg           ; "?extra ignored" — warn, keep what matched
                                            ; (D-MSGENC: print_msg emits the CRLF)
                pop     hl                  ; textcur
                pop     bc                  ; drop varstart
                jp      exec_stmt
inpc_morevars:
                inc     hl                  ; past the ',' in the program text
                push    hl                  ; guard textcur across inpc_more_input
                call    inpc_more_input     ; ZF=1 iff a field is available for the next var
                pop     hl
                jr      z,inpc_vloop        ; more input -> read the next variable
                ; the list wants another variable but the line ran out -> too few.
inpc_redo0:
                ld      hl,msg_redo
                call    print_msg           ; "?redo from start" (D-MSGENC: CRLF emitted)
                call    inpc_print_q
                jp      inpc_reread         ; re-read the whole line (stack: varstart)
inpc_redo3:
                pop     hl                  ; drop textcur
                pop     bc                  ; drop key
                jr      inpc_redo0
inpc_synpop:
                pop     bc                  ; drop varstart
                jp      stmt_error

; --- LINE INPUT: the whole typed line into one string variable -------------
inpc_line:
                call    skip_spaces
                call    is_letter
                jp      nc,stmt_error
                call    var_str_type
                or      a
                jp      z,stmt_error        ; LINE INPUT requires a string variable
                call    tgt_parse           ; D-ARYLV: BC = key, HL past the whole
                                            ; reference, (TGT_ADDR) = element address or
                                            ; 0; A already holds the mode (1) it wants.
                                            ; ⚠️ LINE INPUT re-parses its own target
                                            ; rather than sharing the list driver above,
                                            ; which is why it was a THIRD divergent
                                            ; INPUT arm and needs its own call here.
                jp      nz,fp_runtime_error ; the stack is clean at this point --
                                            ; inpc_dispatch pushes [varstart] only on the
                                            ; INPUT path, AFTER the branch to here
                push    hl                  ; guard the text cursor across the read
                push    bc                  ; save the key
                call    read_line           ; LINEBUF <- typed line
                xor     a
                ld      (INP_CURSOR),a
                ld      de,linebuf_getbyte
                ld      (ARL_GETBYTE),de
                call    read_into_strscr    ; STRSCR <- the whole line (mode 1)
                pop     bc                  ; key
                call    tgt_store_str       ; D-ARYLV: var$[key] = the line, or the
                                            ; resolved element (op=3 COPY_STR)
                pop     hl                  ; text cursor after the variable
                ; arrays slice-4c (§7.3) follow-up, same disposition as
                ; console INPUT's own check just above: a scalar-CHAIN OOM
                ; here sets FPERR but does not itself abort. SP is at
                ; statement level here (both guard words already popped) --
                ; check_expr_errors (interp.asm) is the SP-clean-site variant
                ; (no extra word to discard); TMISMATCH is always 0 (LINE
                ; INPUT never sets it).
                call    check_expr_errors
                jp      exec_stmt

; --- inpc_print_q: emit the "? " input prompt to the screen ----------------
inpc_print_q:
                ld      a,'?'
                call    CHPUT
                ld      a,' '
                call    CHPUT
                ret

; --- inpc_more_input: is there another field to read from LINEBUF? ----------
; The only delimiters in LINEBUF are ',' and the 0 terminator (read_line stores
; no CR). `linebuf_getbyte` consumes a ',' and advances the cursor past it, but
; leaves the cursor ON the 0 at end-of-line. So a field was comma-terminated (=>
; more input follows) iff the byte just before the cursor is a ',' — and nothing
; was consumed at all (cursor == 0) means an empty line.
; out: ZF = 1 iff more input remains (the last field ended on a ','). Clobbers A,HL.
inpc_more_input:
                ld      a,(INP_CURSOR)
                or      a
                jr      z,inpc_nomore       ; cursor 0 -> nothing consumed -> no more
                ld      l,a
                dec     l
                ld      h,high LINEBUF      ; LINEBUF is one page ($E1xx)
                ld      a,(hl)
                cp      ','                 ; ZF = 1 iff the last delimiter was ','
                ret
inpc_nomore:
                or      1                   ; A nonzero -> ZF = 0 (no more input)
                ret

; --- linebuf_getbyte: ARL_GETBYTE source for the console line --------------
; The byte-source vector read_into_strscr calls (via arl_getbyte) while parsing a
; console INPUT line. Returns the next LINEBUF byte and advances INP_CURSOR; the 0
; terminator reports EOF (CF set) WITHOUT advancing, the same end contract
; fat_io_getbyte / cas_in_getbyte present for the file sources. LINEBUF is one page,
; so the cursor is a single low byte.
; out: A = byte, CF clear on success; CF set at end-of-line. Clobbers A (HL preserved).
linebuf_getbyte:
                push    hl
                ld      a,(INP_CURSOR)
                ld      l,a
                ld      h,high LINEBUF
                ld      a,(hl)
                or      a
                jr      z,lgb_eof           ; 0 terminator -> EOF, leave the cursor on it
                ld      a,l
                inc     a
                ld      (INP_CURSOR),a      ; advance the cursor past this byte
                ld      a,(hl)              ; the data byte
                pop     hl
                or      a                   ; CF clear -> success
                ret
lgb_eof:
                pop     hl
                scf
                ret

; --- input_num_field: STRSCR field -> signed 16-bit integer -----------------
; Strict validator for a numeric INPUT field (str_val_parse is too lenient — it
; would accept "12x" as 12). Accepts (spaces)(+|-)?(digit+)(spaces) and nothing
; else; empty / non-numeric / trailing junk is rejected so the driver can ?redo.
; in:  STRSCR = [len][bytes].
; out: DE = value; CF clear iff a clean integer, CF set otherwise.
; Clobbers A,BC,DE,HL.
input_num_field:
                ld      hl,STRSCR
                ld      b,(hl)              ; B = field length
                inc     hl                  ; HL -> the bytes
                ld      de,0                ; DE = accumulator
                ld      c,0                 ; C: bit0 = negative, bit1 = saw a digit
inf_lead:
                ld      a,b
                or      a
                jr      z,inf_fin           ; ran out during the lead -> no digit -> bad
                ld      a,(hl)
                cp      ' '
                jr      nz,inf_sign
                inc     hl
                dec     b
                jr      inf_lead            ; skip leading spaces
inf_sign:
                cp      '-'
                jr      nz,inf_plus
                set     0,c                 ; negative
                inc     hl
                dec     b
                jr      inf_digits
inf_plus:
                cp      '+'
                jr      nz,inf_digits
                inc     hl
                dec     b
inf_digits:
                ld      a,b
                or      a
                jr      z,inf_fin
                ld      a,(hl)
                cp      '0'
                jr      c,inf_trail
                cp      '9'+1
                jr      nc,inf_trail
                sub     '0'                 ; A = digit 0..9
                push    hl
                push    af
                ld      h,d
                ld      l,e                 ; HL = acc
                add     hl,hl               ; *2
                add     hl,hl               ; *4
                add     hl,hl               ; *8
                ex      de,hl               ; DE = acc*8 ; HL = acc
                add     hl,hl               ; HL = acc*2
                add     hl,de               ; HL = acc*10
                pop     af                  ; A = digit
                ld      d,0
                ld      e,a
                add     hl,de               ; HL = acc*10 + digit
                ex      de,hl               ; DE = new accumulator
                pop     hl
                set     1,c                 ; saw a digit
                inc     hl
                dec     b
                jr      inf_digits
inf_trail:
                ld      a,b                 ; remaining chars must be spaces only
                or      a
                jr      z,inf_fin
                ld      a,(hl)
                cp      ' '
                jr      nz,inf_bad
                inc     hl
                dec     b
                jr      inf_trail
inf_fin:
                bit     1,c
                jr      z,inf_bad           ; no digit at all -> invalid
                bit     0,c
                jr      z,inf_ok
                ld      hl,0                ; negate: DE = 0 - DE
                or      a
                sbc     hl,de
                ex      de,hl
inf_ok:
                or      a                   ; CF clear = valid
                ret
inf_bad:
                scf
                ret

; D-MSGENC (§4.2): no phrase hit in either, but both shed the baked CRLF, which
; print_msg now emits. Their two print sites below move to print_msg with them.
msg_redo:       db      "?Redo from start",0    ; 19 B -> 17 B
msg_extra:      db      "?Extra ignored",0      ; 17 B -> 15 B
