; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause

; strvar.asm — minimal string-VALUE layer (own-design; see PROVENANCE.md).
;
; "Enough for PRINT": a string operand is either a "literal" or a `$`-suffixed
; variable that holds a previously-assigned string. There is NO heap, NO concat
; (`+`), and NO string functions (LEFT$/MID$/CHR$/…) — those are the Phase-2
; string engine. The few routines here let LET assign a string operand to a
; string variable and let PRINT emit one.
;
; A string VALUE is represented by a [len:1][bytes...] descriptor; STRPTR points
; at it and VALTYP=1 flags "the current operand is a string". The variable store
; (basic/vars.asm: str_find/str_get_key/str_set_key over STRTAB) holds the live
; values; STRSCR is scratch for a literal lifted out of the token stream.
;
; Clean-room: original code. String assignment / PRINT *semantics* are from the
; public MSX-BASIC language reference; the descriptor + store layout are zerobas'
; own minimal design (the reference's real string heap/descriptor is not
; reproduced — Phase 2). No disassembly.

; --- str_eval: evaluate a string operand at (HL) -> descriptor ---------------
; in:  HL = cursor at a string operand: either a '"'-quoted literal or a
;      `$`-suffixed variable name (the caller has already established it IS a
;      string operand, e.g. via a leading '"' or var_str_type).
; out: STRPTR -> a [len][bytes] descriptor, VALTYP = 1, HL advanced past the
;      operand. CF set on success; CF clear (and VALTYP untouched) if the operand
;      is not a recognised string form (caller treats as error).
; Clobbers A, BC, DE, HL.
str_eval:
                ld      a,(hl)
                cp      '"'
                jr      z,str_eval_lit
                call    is_letter           ; a `$`-suffixed variable?
                jr      nc,str_eval_no
                call    var_str_type        ; A=1 if `$` suffix
                or      a
                jr      z,str_eval_no       ; numeric name -> not a string operand
                ; string variable: key it and point STRPTR at its stored value.
                call    var_name_key        ; BC = key, HL past name + `$`
                push    hl                  ; guard cursor across the lookup
                call    str_get_key         ; HL -> [len][bytes] descriptor
                ld      (STRPTR),hl
                pop     hl
                jr      str_eval_ok
str_eval_lit:
                ; copy the literal's bytes into STRSCR as a [len][bytes] descriptor,
                ; clamped to STRMAX, advancing HL past the closing quote. HL stays
                ; the source cursor throughout; DE writes the descriptor.
                inc     hl                  ; past the opening quote
                ld      de,STRSCR+1         ; DE -> descriptor bytes
                ld      b,0                 ; B = length so far
sel_lp:
                ld      a,(hl)
                or      a
                jr      z,sel_close         ; unterminated -> stop (treat EOL as end)
                cp      '"'
                jr      z,sel_close_q
                ld      a,b
                cp      STRMAX
                jr      nc,sel_skip         ; full: drop extra chars (truncate)
                ld      a,(hl)
                ld      (de),a
                inc     de
                inc     b
sel_skip:
                inc     hl
                jr      sel_lp
sel_close_q:
                inc     hl                  ; past the closing quote
sel_close:
                ld      a,b
                ld      (STRSCR),a          ; store the length (HL = advanced cursor)
                push    hl                  ; guard the advanced source cursor
                ld      hl,STRSCR
                ld      (STRPTR),hl
                pop     hl                  ; HL = cursor past the operand
                jr      str_eval_ok
str_eval_no:
                or      a                   ; CF clear -> not a string operand
                ret
str_eval_ok:
                ld      a,1
                ld      (VALTYP),a
                scf
                ret

; --- print_strval: emit the [len][bytes] descriptor at STRPTR via CHPUT -------
; Reads STRPTR (set by str_eval). CHPUT makes no register guarantees, so the
; descriptor cursor (HL) and the remaining count (B) are guarded across it.
; Clobbers A, B, HL.
print_strval:
                ld      hl,(STRPTR)
                ld      b,(hl)              ; B = length
                inc     hl                  ; HL -> bytes
                ld      a,b
                or      a
                ret     z                   ; empty string -> nothing to print
psv_lp:
                ld      a,(hl)
                push    bc
                push    hl
                call    CHPUT
                pop     hl
                pop     bc
                inc     hl
                djnz    psv_lp
                ret
