; interp.asm — the tokeniser + execution-loop front-end.
;
; Replaces the old "INIT *is* the BLOAD" tracer bullet with a real (if tiny)
; interpreter spine: crunch an ASCII line into tokens, then dispatch on the
; leading token. For now the line is a fixed ROM string; a later phase reads it
; from the keyboard. The end-to-end behaviour (cassette load + ,R handoff) is
; unchanged — only *how the statement is reached* changes.
;
; Derived only from cbios-basic/docs/spec-tokenise.md (this project's own
; black-box oracle observation). No disassembly.

; --- INIT entry (cartridge header points here) -----------------------------
init:
                ld      hl,basic_line       ; ASCII source line (0-terminated)
                ld      de,TOKBUF           ; crunch destination
                call    tokenise
                ld      hl,TOKBUF
                jp      exec                ; dispatches; BLOAD+,R never returns

; The direct-mode line this build runs. spec-tokenise.md: keywords crunch,
; everything else (the "CAS:" string and the ,R option) is kept verbatim.
basic_line:
                db      "BLOAD",'"',"CAS:",'"',",R",0

; --- tokenise: ASCII line -> token stream ----------------------------------
; in:  HL = source (0-terminated ASCII), DE = destination buffer
; out: destination holds tokens, 0x00-terminated
; spec-tokenise.md: keyword -> single token byte (case-folded); string literals
; and all other bytes copied verbatim; line terminated by 0x00.
tokenise:
                ld      a,(hl)
                or      a
                jr      z,tk_end
                cp      '"'                 ; string literal: copy verbatim, no crunch
                jr      z,tk_string
                call    match_kw            ; CF set -> A=token, HL past keyword
                jr      c,tk_emit
                ld      a,(hl)              ; not a keyword: copy this byte
                inc     hl
tk_emit:
                ld      (de),a
                inc     de
                jr      tokenise
tk_string:
                ld      (de),a              ; opening quote
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
tk_end:
                xor     a
                ld      (de),a              ; 0x00 terminator
                ret

; --- match_kw: is a table keyword present at (HL)? -------------------------
; in:  HL = source position
; out: CF set   -> match:    A = token byte, HL advanced past the keyword
;      CF clear -> no match: HL unchanged
; Preserves caller's DE. Uses IX as the table cursor.
match_kw:
                push    de                  ; preserve caller's dst pointer
                ld      ix,kwtable
mk_entry:
                ld      a,(ix+0)            ; keyword length (0 = end of table)
                or      a
                jr      z,mk_none
                push    hl                  ; remember source start
                ld      b,a                 ; B = chars to compare
                push    ix
                pop     de
                inc     de                  ; DE -> keyword text
mk_cmp:
                ld      a,(de)              ; keyword char (stored uppercase)
                ld      c,a
                ld      a,(hl)              ; source char
                call    upcase              ; case-fold before comparing
                cp      c
                jr      nz,mk_fail
                inc     hl
                inc     de
                djnz    mk_cmp
                ld      a,(de)              ; matched: DE -> token byte
                pop     bc                  ; discard source start (HL is advanced)
                pop     de                  ; restore caller dst
                scf
                ret
mk_fail:
                ld      a,(ix+0)            ; this entry's length
                add     a,2                 ; stride = 1(len) + len + 1(token)
                ld      c,a
                ld      b,0
                add     ix,bc               ; IX -> next entry
                pop     hl                  ; restore source start
                jr      mk_entry
mk_none:
                pop     de                  ; restore caller dst
                or      a                   ; CF clear (no match)
                ret

; keyword -> token table. Layout per entry: [len][UPPERCASE chars...][token].
; Terminated by a 0 length byte. Source: spec-tokenise.md (oracle).
kwtable:
                db      5,"BLOAD",BLOAD_TOKEN
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

; --- exec: dispatch on the leading token -----------------------------------
; in: HL = token buffer (0x00-terminated)
exec:
                call    skip_spaces         ; leading spaces are skipped (spec §5)
                ld      a,(hl)
                cp      BLOAD_TOKEN
                jp      z,ex_bload
                jp      stmt_error          ; no other statement implemented yet
ex_bload:
                inc     hl                  ; HL -> args (past the BLOAD token)
                jp      do_bload

; --- skip_spaces: advance HL past 0x20 bytes -------------------------------
; in/out: HL. Preserves nothing but HL (A clobbered).
skip_spaces:
                ld      a,(hl)
                cp      ' '
                ret     nz
                inc     hl
                jr      skip_spaces

; --- stmt_error: unknown statement — drop a marker and halt ----------------
stmt_error:
                ld      a,$DD               ; distinct from BLOAD's $EE tape error
                ld      (ERRMARK),a
stmt_halt:
                jr      stmt_halt
