; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; list.asm — the LIST statement (display the stored program).
;
;   LIST          list the whole stored program
;
; LIST walks the stored numbered-line program (the same one NEW / RUN manage,
; in program.asm) and prints each line as source text: the decimal line number,
; a space, then the *de-tokenised* body, then CR/LF.
;
; The hard part is the detokeniser (`detok`) — the exact inverse of interp.asm's
; `tokenise:`. It walks a line's crunched token body and renders every token the
; tokeniser can emit back to ASCII:
;   - keyword tokens                -> their keyword text (reverse of `kwtable`)
;   - 2-byte function token $FF $97 -> PEEK
;   - digit/byte/word int tokens
;     ($11+n / $0F,b / $1C,w / $0C &H,w / $0B &O,w) -> the decimal/hex source
;   - operator tokens ($EF $F1 $F2 $F3 $F4 $FC $EE $F0) -> = + - * / \ > <
;   - line-number reference $0E,<lineno LE> (and $0D,<addr> post-RUN) -> decimal
;   - string literals "…", REM / ' tails, and DATA bodies -> copied verbatim
;   - ELSE ($3A $A1) and ' ($3A $8F $E6) -> ELSE / ' (the leading ':' folded out)
; Everything `tok_skip` (interp.asm) knows how to step, `detok` knows how to
; render — they cover the same token set.
;
; Clean-room: original code. LIST *semantics* (number, space, source, newline)
; from the public MSX-BASIC language reference; the detokeniser is the reverse of
; this project's own oracle-sourced tokeniser (interp.asm `tokenise:` / `kwtable`,
; spec-tokenise.md / spec-tokens-statements.md). No constant here is new — each
; token byte it decodes is already defined+cited in sysvars.inc. No disassembly.
;
; Line-range / line-number arguments (LIST n, LIST n-m) are a documented Phase-2
; divergence; only the no-argument whole-program form is implemented.
;
; Entry: ex_list, HL -> the LIST token.

; --- ex_list: LIST (whole program) -----------------------------------------
; Walk the stored line-link chain from the text base, printing each line. Any
; argument is ignored (Phase-2 divergence). Returns to the caller (REPL/run loop)
; via exec_stmt so the line continues normally.
ex_list:
                inc     hl                  ; past the LIST token (args ignored)
                xor     a
                ld      (PRDEST),a          ; LIST always renders to the SCREEN sink
                call    list_walk           ; walk + emit the whole program
                jp      exec_stmt           ; LIST done -> continue the line

; --- list_walk — walk the stored program, emitting each line as "number space
; detokenised-body CRLF" through pchar. pchar follows the PRDEST sink: the screen
; for LIST (PRDEST=0), or the open file channel for ASCII SAVE (PRDEST=1, see
; ascii_save, save.asm) — so the ONE detokeniser feeds both. Returns after the
; $0000 end-of-program link. Clean-room: our own detokeniser; the ASCII listing
; format is the public MSX-BASIC language reference.
list_walk:
                ld      hl,TXTBASE
lst_lp:
                ld      e,(hl)              ; DE = link to next line
                inc     hl
                ld      d,(hl)
                dec     hl
                ld      a,d
                or      e
                ret     z                   ; $0000 link -> end of program
                push    de                  ; guard the link across the print
                inc     hl                  ; skip link (2) -> line number
                inc     hl
                ld      c,(hl)              ; line number, LE
                inc     hl
                ld      b,(hl)
                inc     hl                  ; HL -> token body
                push    hl                  ; guard the body pointer
                ld      d,b                 ; print_number wants the value in DE
                ld      e,c
                call    list_num            ; print the line number (no extra spaces)
                ld      a,' '               ; one space between number and body
                call    pchar
                pop     hl                  ; HL = token body
                call    detok               ; render the body through pchar (PRDEST)
                call    print_crlf
                pop     hl                  ; HL = link -> next line's link field
                jr      lst_lp

; --- list_num: print DE as an unsigned decimal line number ------------------
; print_number formats a *signed* value with a leading sign space and a trailing
; space; a line number wants neither, so we format the magnitude ourselves into
; NUMBUF (reusing div10 from print.asm) with no sign and no trailing space.
list_num:
                ex      de,hl               ; HL = value (magnitude; line nos are >=0)
                jp      ln_div_entry        ; print HL as bare unsigned decimal

; --- detok: render the crunched token body at (HL) -------------------------
; The whole detokeniser body (detok/dt_*/detok_op/detok_kw*/the number renderers
; + ln_div_entry) lives in basic/detok.inc. Its home depends on the build (subrom
; arc WAVE 3, docs/spec-basic-subrom-wave3-detok.md):
;   * lean 16 KB cart (ROM_BASE >= $4000): the body is inline here (the include
;     below), byte-identical to the pre-extraction list.asm — every rendered byte
;     streams through pchar (the PRDEST sink) exactly as before.
;   * repack build (ROM_BASE < $4000): the body is EVICTED to sub-ROM page 0
;     (sub/detok.asm), where pchar/print_string are re-bound to DETOKBUF appends
;     and kwtable is the co-located sub copy. `detok` here is a dispatch stub that
;     CALSLTs the core once per line to fill DETOKBUF, then drains it back through
;     the real pchar — honouring PRDEST, so the one core still feeds BOTH
;     LIST->screen and ASCII-SAVE->disk (the single list_walk:detok call site).
;     Cold path (LIST / ASCII SAVE only), so the whole-line DI span is cosmetic
;     (spec §5, same class as wave-2's tokeniser span). ln_div_entry stays RESIDENT
;     here: list_num (line numbers) and program.asm's error line-number printing
;     reach it by ordinary in-slot call and must not page out — a copy separate
;     from detok.inc's sub-side one (which serves the evicted detok_dec).
    IF ROM_BASE < $4000
detok:
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_DETOK
                call    subrom_call         ; HL=token body in; sub core fills DETOKBUF
                                            ; (0-terminated); CF=1 if the sub-ROM is absent
                jp      c,subrom_absent_error ; reduced build w/o sub-ROM (never on the
                                            ; merged machine, which always ships it)
                ld      hl,DETOKBUF
                jp      print_string        ; drain DETOKBUF -> pchar (PRDEST sink), then
                                            ; ret to list_walk

; ln_div_entry (RESIDENT copy): print HL as bare unsigned decimal. list_num and
; program.asm's line-number printing stay resident and reach this by in-slot call;
; detok.inc carries a byte-identical sub-side twin for the evicted detok_dec.
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

; hex_digit / oct_digit (RESIDENT copies): A (0..15 / 0..7) -> ASCII. Shared leaves
; — str-engine.asm's HEX$/OCT$ (which reimplement the nibble/group loop but reuse
; these leaves) stay resident and reach them by in-slot call, so they cannot move
; sub-side. detok.inc carries byte-identical twins for the evicted number renderers.
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
    ELSE
                include "basic/detok.inc"
    ENDIF
