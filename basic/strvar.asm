; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

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

; --- str_eval / str_eval_one: evaluate a string operand at (HL) -> descriptor -
; str_eval_one evaluates ONE string operand: a '"'-quoted literal or a `$`-suffixed
; variable name (the caller has already established it IS a string operand, e.g. via a
; leading '"' or var_str_type).
; out: STRPTR -> a [len][bytes] descriptor, VALTYP = 1, HL advanced past the operand.
;      CF set on success; CF clear (and VALTYP untouched) if the operand is not a
;      recognised string form (caller treats as error). Clobbers A, BC, DE, HL.
;
; str_eval is the PUBLIC entry every caller uses. In the lean build it is exactly
; str_eval_one (no concat) — byte-identical, since the equate emits no bytes and
; str_eval_one lands at the same address the old str_eval did. In the repack build
; (string-engine arc S3) it folds any trailing `+ operand` terms via str_concat_tail
; (basic/str-engine.asm, in the reclaimed low region), giving `A$+B$+C$` concatenation
; to every string context at once (PRINT, LET, function args, LSET/RSET, PRINT USING).
    IF ROM_BASE < $4000
str_eval:
                call    str_eval_one
                ret     nc                  ; not a string operand -> propagate
                jp      str_concat_tail     ; low region: append `+ operand` terms
    ELSE
str_eval        equ     str_eval_one        ; lean: a string operand is one operand
    ENDIF
str_eval_one:
                ld      a,(hl)
                cp      '"'
                jr      z,str_eval_lit
                cp      INPUT_TOKEN         ; INPUT$(...) ? -> $85 ('INPUT') then '$'
                jp      z,str_eval_maybe_inputd
                cp      PEEK_PREFIX         ; $FF + selector -> a function token; MKI$ ?
                jp      z,str_eval_maybe_mki
    IF ROM_BASE < $4000
                cp      STRING_TOKEN        ; $E3 -> STRING$(n,c) (string-functions Group B;
                jp      z,str_fn_string     ; single-byte reserved word, not $FF-prefixed)
    ENDIF
                call    is_letter           ; a `$`-suffixed variable?
                jp      nc,str_eval_no
                call    var_str_type        ; A=1 if `$` suffix
                or      a
                jp      z,str_eval_no       ; numeric name -> not a string operand
                ; string variable: key it and point STRPTR at its stored value.
                call    var_name_key        ; BC = key, HL past name + `$`
                push    hl                  ; guard cursor across the lookup
                call    fld_lookup          ; FIELDed var? -> STRPTR=FLD_DESC slice, CF set
                jr      c,sev_have          ; fielded -> STRPTR already set
                call    str_get_key         ; HL -> [len][bytes] descriptor
                ld      (STRPTR),hl
sev_have:
                pop     hl
                jp      str_eval_ok
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
                jp      str_eval_ok
str_eval_no:
                or      a                   ; CF clear -> not a string operand
                ret
str_eval_ok:
                ld      a,1
                ld      (VALTYP),a
                scf
                ret

; --- INPUT$(n,#f): read EXACTLY n raw bytes from file channel f as a string ------
; Reached from str_eval when the operand is the INPUT token ($85). "INPUT$" crunches
; to INPUT ($85) + '$' ($24) — NOT a dedicated token (oracle: VG-8020 + zerobas both
; emit $85 $24). Only the FILE form INPUT$(n,#f) is supported; the keyboard form
; INPUT$(n) (no '#') is Phase 3 -> treated as "not a string operand" (caller errors).
; Unlike INPUT#/LINE INPUT#, INPUT$ does NO delimiter handling — it takes n bytes
; verbatim and the file cursor advances by n. The bytes go into the STRSCR
; descriptor (clamped to STRMAX; a longer n is still consumed so the cursor stays
; correct — documented). HL is the (HL-based) string-eval cursor; the numeric args
; use `eval` (which saves/restores IX); fat_io_getbyte's CALSLT clobbers everything,
; so the read state lives in RAM (INDLR_N target, IN_RDLEN stored count) and the
; cursor is guarded on the stack. CF-3300-validated (disk_probe_inputdollar.py).
; --- MKI$(n): pack a 16-bit integer into a 2-byte little-endian string -----------
; Reached from str_eval on a $FF function token. "MKI$" crunches to $FF $AE (oracle-
; locked). MKI$(n) returns the 2-byte string [lo][hi] of n; the inverse is CVI
; (basic/expr.asm). The numeric arg uses `eval` (saves/restores IX); the 2-byte
; result fills the STRSCR [len][bytes] descriptor (binary-safe: len-prefixed, so a
; $00 byte is fine). HL is guarded across the STRSCR write (the OPEN/INPUT$ lesson).
; CF-3300-validated (disk_probe_mkicvi.py). The float siblings MKS$/MKD$ are Phase 3.
str_eval_maybe_mki:
                inc     hl                  ; tentatively past $FF
                ld      a,(hl)
                cp      MKI_TOKEN           ; $AE -> MKI$
                jr      z,str_mki
    IF ROM_BASE < $4000
                jp      str_func_ff         ; repack: CHR$/STR$/LEFT$/RIGHT$/MID$ (HL on selector)
    ELSE
                dec     hl                  ; other $FF function -> not a string operand
                jp      str_eval_no
    ENDIF
str_mki:
                inc     hl                  ; past the MKI$ selector
                ld      a,(hl)
                cp      '('
                jp      nz,str_eval_no
                inc     hl
                call    eval                ; DE = n; HL advanced past the argument
                ld      a,(hl)
                cp      ')'
                jp      nz,str_eval_no
                inc     hl                  ; HL past ')'
                push    hl                  ; guard the cursor across the STRSCR write
                ld      a,2
                ld      (STRSCR),a          ; length = 2
                ld      a,e
                ld      (STRSCR+1),a        ; low byte of n
                ld      a,d
                ld      (STRSCR+2),a        ; high byte of n
                ld      hl,STRSCR
                ld      (STRPTR),hl
                pop     hl                  ; restore the eval cursor
                jp      str_eval_ok
str_eval_maybe_inputd:
                inc     hl                  ; tentatively past the INPUT token
                ld      a,(hl)
                cp      '$'
                jr      z,str_inputd
                dec     hl                  ; not INPUT$ -> restore, not a string operand
                jp      str_eval_no
str_inputd:
                inc     hl                  ; past '$'
                ld      a,(hl)
                cp      '('
                jp      nz,str_eval_no
                inc     hl
                call    eval                ; DE = n (byte count); HL advanced past it
                ld      a,e
                ld      (INDLR_N),a         ; target count (low byte; n <= 255)
                ld      a,(hl)
                cp      ','                 ; INPUT$(n) keyboard form (no ',') = Phase 3
                jp      nz,str_eval_no
                inc     hl
                ld      a,(hl)
                cp      '#'                 ; file form requires '#f'
                jp      nz,str_eval_no
                inc     hl
                call    eval                ; DE = channel f; HL advanced
                ld      a,(hl)
                cp      ')'
                jp      nz,str_eval_no
                inc     hl                  ; HL past ')'
                ld      a,e
                call    fch_valid
                jp      nc,str_eval_no      ; bad file number
                push    hl                  ; guard the eval cursor (fch_select + CALSLT)
                ld      a,e
                call    fch_select          ; make channel f live; FCH_MODE = its mode
                ld      a,(FCH_MODE)
                cp      1                   ; must be open FOR INPUT
                jr      nz,str_inputd_err
                call    str_inputd_read     ; fill STRSCR [len][bytes] with n bytes
                ld      hl,STRSCR           ; set STRPTR while the cursor is still on
                ld      (STRPTR),hl         ; the stack (HL here would clobber it)
                pop     hl                  ; restore the eval cursor (past ')')
                jp      str_eval_ok
str_inputd_err:
                pop     hl
                jp      str_eval_no

; str_inputd_read — consume INDLR_N bytes from the open channel into STRSCR
; ([len][bytes]); store up to STRMAX, but keep consuming so the file cursor advances
; the full count. Stops early at EOF. All loop state is in RAM (CALSLT clobbers regs).
str_inputd_read:
                xor     a
                ld      (IN_RDLEN),a        ; stored count = 0
sidr_lp:
                ld      a,(INDLR_N)
                or      a
                jr      z,sidr_done         ; consumed all n
                call    fat_io_getbyte
                jr      c,sidr_done         ; EOF before n -> stop (partial)
                ld      c,a                 ; C = the byte read
                ld      a,(INDLR_N)
                dec     a
                ld      (INDLR_N),a         ; one fewer to read
                ld      a,(IN_RDLEN)
                cp      STRMAX
                jr      nc,sidr_lp          ; descriptor full -> consume but don't store
                ld      e,a
                ld      d,0
                ld      hl,STRSCR+1
                add     hl,de
                ld      (hl),c              ; store the byte
                ld      a,(IN_RDLEN)
                inc     a
                ld      (IN_RDLEN),a
                jr      sidr_lp
sidr_done:
                ld      a,(IN_RDLEN)
                ld      (STRSCR),a          ; descriptor length
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
                call    pchar               ; screen or file (PRDEST); preserves all
                inc     hl
                djnz    psv_lp
                ret
