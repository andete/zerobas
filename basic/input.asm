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
; prompt/var-list driver, the strict numeric-field reader `inp_num` (D-INPNUM), and
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
                jr      nz,inpc_line        ; LINE INPUT -> whole line into one $-var
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
                call    tgt_parse_req      ; D-ARYLV: BC = key, HL past the whole
                                            ; reference, (TGT_ADDR) = element address or
                                            ; 0; (VARTYPE) = the resolved type (F3).
                                            ; A already holds the mode (0) it wants.
                                           ; a bad subscript raises the ARRAY engine's
                                            ; own error. [varstart] is still on the
                                            ; stack and that is FINE: fre_abort_low does
                                            ; `ld sp,(SAVSTK)` as its own first act
                                            ; (D-CUR-D), so raising here is
                                            ; DEPTH-INDEPENDENT -- and the ON ERROR trap
                                            ; branch resets SP the same way.
                push    bc                  ; [stack: varstart, key]
                push    hl                  ; [stack: varstart, key, textcur]
                call    read_into_strscr    ; STRSCR <- the next field (mode 0)
                call    inp_num             ; D-INPNUM: STRSCR -> a number; CF = ?redo
                jr      c,inpc_redo3        ; bad numeric field -> ?redo
                pop     hl                  ; textcur
                pop     bc                  ; key
                push    hl                  ; guard textcur across the store
                call    inp_store           ; D-ARYLV: var[key] := the number, or the
                                            ; resolved ELEMENT := it, coerced either way
                pop     hl
                jr      inpc_after
inpc_vstr:
                ; --- string variable ---
                call    tgt_parse_req      ; D-ARYLV: BC = key, HL past the whole
                                            ; reference, (TGT_ADDR) per above; A already
                                            ; holds the mode (1) it wants
                                           ; same depth-independent abort as the numeric
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
                call    skip_comma
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
                jr      inpc_reread         ; re-read the whole line (stack: varstart)
inpc_redo3:
                pop     hl                  ; drop textcur
                pop     bc                  ; drop key
                jr      inpc_redo0
; D-XREG: an ALIAS across the low <-> page-1 boundary. Byte-identical to
; ex_let_err and POSITION-INDEPENDENT (tools/dupspan_indep.py), and the
; REGION question -- is this label reached from a tenant whose mapping
; switches the target page OUT? -- is answered by scratchpad/crossreg_probe.py
; and GATED by check_tenant_closure.py, whose K-XR1 knife proves it can see an
; `equ` (it resolves addresses from the sym, not from the source form).
inpc_synpop     equ     ex_let_err

; --- LINE INPUT: the whole typed line into one string variable -------------
inpc_line:
                call    req_letter          ; D-NGRAM: an INPUT target must be a name
                call    str_target_parse    ; string-var target: type-check, parse,
                                            ; raise -- D-NGRAM9
                                            ; reference, (TGT_ADDR) = element address or
                                            ; 0; A already holds the mode (1) it wants.
                                            ; ⚠️ LINE INPUT re-parses its own target
                                            ; rather than sharing the list driver above,
                                            ; which is why it was a THIRD divergent
                                            ; INPUT arm and needs its own call here.
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
                jp      CHPUT

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

; --- arl_set_src: point ARL_GETBYTE at the right FILE byte source ----------
; D-CASINP. Both INPUT#/LINE INPUT# (input_common, basic/files.asm) and
; INPUT$(n,#f) (str_eval_inputd, basic/strvar.asm) have to choose between the
; disk source and the tape source before reading. input_common did it inline;
; INPUT$ did not do it at all, which is why INPUT$ on a CAS: channel could only
; ever read a disk channel and was refused outright.
; 💰 SHARED RATHER THAN COPIED BECAUSE THE COPY DOES NOT FIT: duplicating the
; two-way choice inside INPUT$ prices at ~18 B against a 16 B page-1 wall, while
; this form lets input_common GIVE BACK the 14 B it spent inline. It lives in the
; low region beside linebuf_getbyte, the third source, where the room is.
;   in:  A = the channel's FCH_MODES value (1 = disk open FOR INPUT,
;        CAS_IN_MODE = OPEN"CAS:" FOR INPUT). A SURVIVES (`cp` does not write it).
;   out: ARL_GETBYTE set. ⚠️ CLOBBERS HL -- input_common holds the BASIC text
;        cursor there and guards it; INPUT$ has already pushed its own.
arl_set_src:
                ld      hl,fat_io_seqbyte   ; D-SEQEOF: the text rules (seqio tenant)
                cp      CAS_IN_MODE
                jr      nz,ass_store
                ld      hl,cas_in_getbyte
ass_store:
                ld      (ARL_GETBYTE),hl
                ret

; --- fat_io_seqbyte / fat_io_eof: stubs over the seqio tenant (D-SEQEOF) -----
; fat_io_seqbyte is the ARL_GETBYTE source for a disk channel open FOR INPUT
; (INPUT#, LINE INPUT#, INPUT$): the next byte by the reference's text rules,
; CF set at the end. fat_io_eof is EOF()'s test: CF set = at the end. Both guard
; IX -- EOF() and INPUT$ run inside the evaluator, whose token cursor it is, and
; this crosses once per BYTE, where the old source crossed only on a refill.
; ASCII LOAD / MERGE keep fat_io_getbyte: a program's Ctrl-Z ends it anyway.
fat_io_eof:
                ld      l,2
                jr      seq_call
fat_io_seqbyte:
                ld      l,0
seq_call:
                push    ix
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_SEQIO
                call    sc_call             ; A = the byte (subrom_call's `or a`)
                pop     ix
                ld      c,a
                ld      a,(SEQ_EOF)
                rra                         ; CF = the end flag
                ld      a,c
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

; --- inp_num: the STRSCR field -> a NUMBER, strictly (D-INPNUM, 2026-09-29) ---
; This was `input_num_field`, a 16-bit INTEGER validator (105 B), so `INPUT A`
; answered `1.5`, `1E3` or `&H10` was ?Redo here and `40000` silently became
; -25536 -- the VG-8020 reads all four (scratchpad/inpnum_run.out). VAL's parse
; already reads every one of those forms (sub/strheap.asm sh_val_parse over
; tk_float, rule 3: no second parser); op 19 runs it over STRSCR's field and
; SH_SRC says where the number ended. The console's own rule, measured
; (scratchpad/inpnum_run2.out): only BLANKS may follow it -- `1-2` and `&H1G`
; are ?Redo -- while an empty field, `+`, `-` and `.` are 0 and `1 2` is 12.
; out: CF clear = a number: SH_LEN = 0 and DE = the int16, or SH_LEN = FACTYP
;      (4/8) with the value in FAC. CF set = ?Redo. Clobbers A,BC,DE,HL,IX.
inp_num:
                call    inp_val             ; SH_ERR / SH_LEN / SH_PTR|FAC / SH_SRC
                ld      a,(SH_ERR)
                or      a
                scf
                ret     nz                  ; a refused literal (`&`, `1E99`) -> ?Redo
                ld      hl,(SH_SRC)         ; where the number ended
                ld      de,(TKVALEND)       ; one past the field's last byte
inm_lp:
                push    hl
                or      a
                sbc     hl,de
                pop     hl
                jr      z,inm_ok            ; only blanks followed (Z, CF clear)
                ld      a,(hl)
                inc     hl
                cp      ' '
                jr      z,inm_lp
                scf                         ; anything else after the number
                ret
inm_ok:                                     ; C4 shared tail (2026-10-03): str-engine's
                ld      de,(SH_PTR)         ; the int16, when SH_LEN says int  -- VAL's
                ret                         ; int arm (ev_ff_val) and expr.asm's FRE
                                            ; (ev_fre_close) jump here

; inp_val: VAL's parse over the STRSCR field (sub op 19). Shared by console
; INPUT (inp_num, strict) and INPUT # (inp_numitem, lenient: the CF-3300 reads
; `12X` in a file as 12).
inp_val:
                ld      a,19
                jp      sh_call_op

;   inp_numitem: INPUT #'s NUMERIC target (D-INPNUM). Reached by `jp` from
; files.asm's inp_readvar with HL on the variable name and FCH_RDMODE as INPUT #
; or LINE INPUT # set it. The item is read by read_into_strscr's numeric mode (a
; blank ends it), parsed LENIENTLY (`12X` in a file reads 12 on the CF-3300 --
; the console's strictness is not the file's), stored as LET stores, and the
; statement goes on at inp_tail exactly as a string item does. Measured rules:
; scratchpad/inpnum_run2.out (FILE round 2).
inp_numitem:
                ld      a,(FCH_RDMODE)
                or      a
                jp      nz,inp_str          ; LINE INPUT #: a string target only --
                                            ; str_target_parse raises its mismatch
                call    tgt_parse_req       ; A = 0 (numeric): BC = key, HL past it
                push    hl                  ; the text cursor
                push    bc                  ; the key
                call    inp_numread         ; STRSCR <- the item; CF = the end
                jr      nc,inu_got
                ld      a,(STRSCR)
                or      a
                jp      z,gp_past_eof       ; the end, and not one byte read -> 55
inu_got:
                call    inp_val             ; lenient: SH_ERR is not a refusal here
                pop     bc
                call    inp_store
                pop     hl
                jp      inp_tail

; inp_numread: one numeric INPUT # item -> STRSCR; CF = the end of the file.
; A DISK channel reads it in the seqio tenant (L = 4), which can PEEK -- the rules
; need it (D-CHANSWITCH, sub/bload.asm sq_numitem). A CAS: channel has no peek
; and keeps the field rule (commas and CR split; a blank does not).
inp_numread:
                ld      hl,(ARL_GETBYTE)
                ld      de,fat_io_seqbyte
                or      a
                sbc     hl,de
                jp      nz,read_into_strscr ; CAS: the field rule (FCH_RDMODE is 0)
                ld      l,4
                jp      seq_call

; inp_store: the parsed number -> the resolved target (console INPUT and INPUT #).
; in: BC = key, (TGT_ADDR) per tgt_parse, SH_LEN / DE / FAC as inp_num leaves them.
inp_store:
                ld      a,(SH_LEN)
                or      a
                jp      z,tgt_store_num     ; an int16 in DE
                jp      tgt_store_fac       ; a float in FAC, FACTYP already its type

; D-MSGENC (§4.2): no phrase hit in either, but both shed the baked CRLF, which
; print_msg now emits. Their two print sites below move to print_msg with them.
msg_redo:       db      "?Redo from start",0    ; 19 B -> 17 B
msg_extra:      db      "?Extra ignored",0      ; 17 B -> 15 B
