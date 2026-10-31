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
                ; D-INPUTCOMMA (2026-10-30): the separator is checked BEFORE the
                ; prompt is shown. A `,` after the literal was taken here, with no
                ; "? "; both references say Syntax error for INPUT and LINE INPUT
                ; alike -- and print NOTHING first, where echoing while scanning
                ; showed the prompt (scratchpad/inputcomma_measure.out).
                push    hl                  ; the literal's first char
inpc_pscan:
                ld      a,(hl)
                or      a
                jp      z,stmt_error        ; unterminated prompt literal
                inc     hl
                cp      '"'
                jr      nz,inpc_pscan
                call    skip_spaces
                cp      ';'
                jp      nz,stmt_error       ; a prompt must be followed by ';'
                inc     hl                  ; past the ';'
                ex      (sp),hl             ; HL = the literal, [past the ';']
inpc_plit:
                ld      a,(hl)
                inc     hl
                cp      '"'
                jr      z,inpc_pdone
                call    CHPUT               ; echo the prompt char to the screen
                jr      inpc_plit
inpc_pdone:
                pop     hl                  ; past the ';': INPUT adds "? ", LINE INPUT nothing
                ld      a,(FCH_RDMODE)
                or      a
                jr      nz,inpc_dispatch
                call    inpc_print_q
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
                call    inp_readline        ; LINEBUF+1 <- typed line; cursor + source set
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
                ld      hl,msg_extra        ; (ld touches no flag)
                call    z,print_msg         ; "?extra ignored" — warn, keep what matched
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
                ; --- D-INPUTCONT: the list wants another variable, the line ran out:
                ; `?? ` and the rest, not a ?Redo. Both bodies are in main page 1
                ; (basic/files.asm, inpc_cont / inpc_redo_p1): this is the low
                ; region, which had 1 B.
                jp      inpc_cont
inpc_redo3:
                pop     hl                  ; drop textcur
                pop     bc                  ; drop key
                jp      inpc_redo_p1        ; ?Redo, then the WHOLE statement again
; D-XREG: an ALIAS across the low <-> page-1 boundary. Byte-identical to
; ex_let_err and POSITION-INDEPENDENT (tools/dupspan_indep.py), and the
; REGION question -- is this label reached from a tenant whose mapping
; switches the target page OUT? -- is answered by scratchpad/crossreg_probe.py
; and GATED by check_tenant_closure.py, whose K-XR1 knife proves it can see an
; `equ` (it resolves addresses from the sym, not from the source form).
; (inpc_synpop = ex_let_err: its equ is in basic/aliases-early.inc -- pasmo 0.5.3, D-PASMO053)

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
                call    inp_readline        ; LINEBUF+1 <- typed line; cursor + source set
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

; --- inp_readline: read the console answer ONE BYTE UP in LINEBUF ----------
; D-STRSCRBUF (2026-10-14): STRSCR is the reference's BUF -- the same buffer the
; answer is typed into. read_line fills LINEBUF..LINEBUF+255 (255 chars and the
; 0); the LDDR moves it to LINEBUF+1.. (BUF is 258 B, so LINEBUF+256 is still
; BUF), which leaves BUF[0] for the splitter's [len] / quote-state byte and puts
; every byte the splitter KEEPS at or behind the one it just read: the field is
; parsed in place, as the reference parses INPUT out of BUF. (A first idea, plain
; `STRSCR equ BUF` with the line at BUF+0, overtakes the reader by one byte on
; the first character -- and the [len] byte is written before anything is read.)
inp_readline:
                call    read_line           ; LINEBUF <- typed line (clobbers HL,A,B)
                ld      hl,LINEBUF+255
                ld      de,LINEBUF+256
                ld      bc,256
                lddr                        ; -> LINEBUF+1 .. LINEBUF+256
                ld      hl,LINEBUF+1
                ld      (INP_CURSOR),hl     ; the read cursor (16-bit)
                ld      de,linebuf_getbyte
                ld      (ARL_GETBYTE),de    ; the field splitter reads from LINEBUF
                ret

; --- inpc_more_input: is there another field to read from LINEBUF? ----------
; The only delimiters in LINEBUF are ',' and the 0 terminator (read_line stores
; no CR). `linebuf_getbyte` consumes a ',' and advances the cursor past it, but
; leaves the cursor ON the 0 at end-of-line. So a field was comma-terminated (=>
; more input follows) iff the byte just before the cursor is a ',' — and nothing
; was consumed at all (cursor == LINEBUF+1, D-STRSCRBUF) means an empty line.
; out: ZF = 1 iff more input remains (the last field ended on a ','). Clobbers A,HL.
; D-RAMBUF: the cursor is a 16-bit POINTER since LINEBUF became the reference's
; BUF ($F55E), which crosses $F600; "at the start" is its low byte equal to
; LINEBUF's (unique within the buffer's 255 B).
inpc_more_input:
                ld      hl,(INP_CURSOR)
                ld      a,l
                cp      low (LINEBUF+1)     ; D-STRSCRBUF: the line starts one byte up
                jr      z,inpc_nomore       ; at the start -> nothing consumed -> no more
                dec     hl
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

; --- fat_io_seqbyte / fat_io_eof: the INPUT channel's crossing (S10.C) -------
; fat_io_seqbyte is the ARL_GETBYTE source for a disk channel open FOR INPUT
; (INPUT#, LINE INPUT#, INPUT$): the next byte by the reference's text rules,
; CF set at the end. fat_io_eof is EOF()'s test: CF set = at the end. Both guard
; IX -- EOF() and INPUT$ run inside the evaluator, whose token cursor it is, and
; a hook is a CALLF.
; 🏗️ S10.C (D-ROMSIZE, 2026-10-15): THEY CROSS TO disk.rom NOW, NOT TO THE
; SUB-ROM. The channel is an MSX-DOS FCB in its engine row there since OPEN
; (hk_finp), its record the block's +9, and disk.rom's hk_chin reads it -- the
; D-SEQEOF rules (Ctrl-Z a soft end never consumed, INPUT# swallowing the LF
; after its CR, INPUT$ raw) and D-CHANSWITCH's numeric item moved with it from
; sub/bload.asm's seqio tenant, which keeps only the TAPE's EOF (expr.asm
; eof_dev). One cell, H_CHIN = $FE8A, the reference's per-byte one, with the
; operation in A (sysvars.inc says why one and not the reference's four).
; A CALLF returns DI (cg_back's note), hence the `ei`.
; ASCII LOAD / MERGE keep their own source (files.asm dsk_agetbyte).
; 🏗️ S10.E (2026-10-19): din_call is also LOF / LOC's crossing (basic/expr.asm
; ev_ff_field, A = 6 / 8, any disk mode): disk.rom answers from the FCB in DE:HL,
; which the CALLF and this body pass back untouched (D-XSLOTABI's both-ways ABI).
fat_io_eof:
                ld      a,2
                jr      din_call
fat_io_seqbyte:
                xor     a                   ; op 0: the next byte
din_call:
                push    ix
                call    H_CHIN              ; A = the byte, CF = the end
                ei
                pop     ix
                ret
    IF BASICINT_PINS
; 📌 REFILL FOR D-BASICINT'S $3297 PIN (S10.C, 2026-10-15). This block was 21 B
; (fat_io_seqbyte / fat_io_eof / seq_call over the seqio tenant) and is 14 now,
; and every byte removed ahead of a pinned address grows its `ds` pad (basic/
; float-arith.asm `ds $3297 - $`) -- Joost: no growing holes. So eval_addr, a
; self-contained 9 B wrapper entered only by `call` (tools/pin_plan.py's chunk
; list), moved here from basic/float-arith.asm, whose copy is now the ELSE arm:
; the pad goes 2 -> 0.
eval_addr:
                call    eval
                push    hl
                call    fac_to_int_addr
                pop     hl
                ret
    ENDIF

; --- linebuf_getbyte: ARL_GETBYTE source for the console line --------------
; The byte-source vector read_into_strscr calls (via arl_getbyte) while parsing a
; console INPUT line. Returns the next LINEBUF byte and advances INP_CURSOR; the 0
; terminator reports EOF (CF set) WITHOUT advancing, the same end contract
; fat_io_getbyte / cas_in_getbyte present for the file sources. The cursor is a
; 16-bit pointer (D-RAMBUF: LINEBUF is the reference's BUF, which crosses a page).
; out: A = byte, CF clear on success; CF set at end-of-line. Clobbers A (HL preserved).
linebuf_getbyte:
                push    hl
                ld      hl,(INP_CURSOR)
                ld      a,(hl)
                or      a
                jr      z,lgb_eof           ; 0 terminator -> EOF, leave the cursor on it
                inc     hl
                ld      (INP_CURSOR),hl     ; advance the cursor past this byte
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
                call    inp_val             ; A = ERR, HL = the end, DE = the int,
                scf                         ; C = the type (0 = the int; 4/8 = FAC)
                ret     nz                  ; a refused literal (`&`, `1E99`) -> ?Redo,
                                            ; A = VAL's code (READ's exr_nan reads it)
                push    de                  ; [the int]
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
                pop     de                  ; drop [the int]
                xor     a                   ; A = 0: not one of VAL's codes (S16)
                scf                         ; anything else after the number
                ret
inm_ok:
                pop     de                  ; DE = the int16 (D-WSZERO S16: was SH_PTR)
                ld      a,c                 ; A = the type, for inp_store (NC kept)
                ret

; inp_val: VAL's parse over the STRSCR field (sub op 19). Shared by console
; INPUT (inp_num, strict) and INPUT # (inp_numitem, lenient: the CF-3300 reads
; `12X` in a file as 12).
inp_val:
                ld      a,19
                jp      sh_go

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
                call    c,seq_end           ; a failed read / nothing read / the item
inu_got:
                call    inp_val             ; lenient: ERR is not a refusal here
                ld      a,c                 ; A = the type, across the key's pop
                pop     bc
                call    inp_store
                pop     hl
                jp      inp_tail

; inp_numread: one numeric INPUT # item -> STRSCR; CF = the end of the file.
; A DISK channel reads it in disk.rom (H_CHIN op 4, hk_chin's din_num, S10.C),
; which can PEEK -- the rules need it (D-CHANSWITCH; it was the seqio tenant's
; sq_numitem). A CAS: channel has no peek and keeps the field rule (commas and
; CR split; a blank does not).
inp_numread:
                ld      hl,(ARL_GETBYTE)
                ld      de,fat_io_seqbyte
                or      a
                sbc     hl,de
                jp      nz,read_into_strscr ; CAS: the field rule (FCH_RDMODE is 0)
                ld      a,4
                jp      din_call

; inp_store: the parsed number -> the resolved target (console INPUT and INPUT #).
; in: BC = key, (TGT_ADDR) per tgt_parse, A (the type) / DE / FAC as inp_num leaves them.
inp_store:                                  ; A = the type (inp_num / inu_got)
                or      a
                jp      z,tgt_store_num     ; an int16 in DE
                jp      tgt_store_fac       ; a float in FAC, FACTYP already its type

; D-MSGENC (§4.2): no phrase hit in either, but both shed the baked CRLF, which
; print_msg now emits. Their two print sites below move to print_msg with them.
; msg_redo -- MOVED to the end of the low region (basic/main.asm, D-BIOSINT
; 2026-10-17): the repacked C-BIOS grew 28 B ($0D12's keyboard-scan entry),
; BASIC_ORG followed it to $2781, and these 17 B of data -- read only by the
; absolute `ld hl` above -- went past the $3297 pin with float.asm's flt_neg
; (11 B), so its pad stays 0 (tools/pin_plan.py's exact fill).
msg_extra:      db      "?Extra ignored",0      ; 17 B -> 15 B

; REFILL (D-WSZERO S16, 2026-10-16): moved here from basic/arrays.asm, whole and
; self-contained (entered only by label), to refill bytes the stack parameter
; block freed in front of the $3297 pin -- tools/pin_plan.py's exact fill.
; --- ary_engine_call: subrom_call to the array tenant (SUBROM_IDX_ARY). ----
; The caller has already filled ARY_OP/ARY_KEY/ARY_TYPE (and ARY_NIDX/
; ARY_IDXP, via ary_parse_call) in the param block. On return: reads
; ARY_ERR; if nonzero, maps it to the matching FPERR code (ary_errmap below)
; and returns NZ; if zero (ok), returns Z. CF from subrom_call itself (the
; sub-ROM absent — never on the merged machine, which always ships it) jumps
; straight to subrom_absent_error and never returns, the same defensive
; convention every other subrom_call site uses (evmc_sqr, list.asm detok,
; interp.asm tokenise). Clobbers A,IX — the caller must guard any live IX
; (e.g. the text cursor) around this call, the same discipline evmc_sqr uses
; across SUBROM_ENTRY_BASE_P1+3*SUBROM_IDX_SQR.
ary_engine_call:
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_ARY
                call    sc_call             ; D-SCCALL: tenant call + absent raise
                ld      a,(ARY_ERR)
                or      a
                ret     z
                ld      hl,ary_errmap-1
                ld      d,0
                ld      e,a
                add     hl,de               ; Z80 ADD HL,rr affects C/H/N only --
                                            ; S/Z/P-V are UNCHANGED (documented Z80
                                            ; behaviour), so the NZ this routine
                                            ; must return is STILL the one the `or a`
                                            ; above set (A was nonzero, else we'd
                                            ; have taken `ret z`) and survives,
                                            ; untouched, through every instruction
                                            ; between here and the final `ret` below
                                            ; (none of LD (nn),A / LD A,(HL) / LD
                                            ; A,(nn) touch flags either) -- slice-3
                                            ; space audit: the trailing "ensure NZ"
                                            ; `or a` this comment replaces was
                                            ; therefore provably redundant
                ld      a,(hl)
                jp      penderr_set

; REFILL (D-WSZERO S16, 2026-10-16): moved here from basic/float-arith.asm, whole and
; self-contained (entered only by label), to refill bytes the stack parameter
; block freed in front of the $3297 pin -- tools/pin_plan.py's exact fill.
; --- pop_lhs_and_probe: shared preamble for combine_add/sub/mul/cmp -------
; (below): pops the lhs frame push_lhs_frame wrote (basic/float-arith.asm): its
; [FACTYP] into LHS_FACTYP, then -- by that type, as push_lhs_frame sized it --
; the lhs DE into FP_LHSVAL (2), FAC+0..3 into LHS_FAC (< 5: a single), or
; FAC+0..7 (> 5: a double). D-EVALSLOPE's typed-frame step, 2026-10-20: the
; frame was a fixed 12 B for every type; see push_lhs_frame's header for what
; each type's readers read, and why no other cell is needed.
; TWO return addresses sit on top of that frame by the time this runs, not
; one: this routine's own (pushed by
; "call pop_lhs_and_probe") AND its DIRECT caller's -- combine_add/sub/mul/
; cmp/div_float is itself reached via a plain "call" from an ev_* site made
; AFTER push_lhs_frame already ran, so that combine_* return address is
; ALSO sitting on top of the frame, one slot further down, for the entire
; time combine_* is running (an earlier version of this fix only accounted
; for one level and got the frame data wrong as a result -- caught by the
; eval() integration tests reading back a corrupted LHS_FACTYP). Fixed by
; stashing BOTH in RAM (PLF_RA = ours, PLF_RA2 = our caller's -- neither is
; a register, since DE and BC must both stay live across this call for
; various combine_* callers) before touching the frame, then restoring
; PLF_RA2 to the stack first (so it's sitting exactly where combine_* will
; expect its own eventual return address to be) and finally jumping to
; PLF_RA (a "jp (hl)" is equivalent to a "ret" here but doesn't need the
; target on the stack first). Note LD/PUSH/JP(HL) never touch flags on the
; Z80, so the ZF the final "cp 2" sets for our caller survives this restore
; untouched. out: ZF set iff both LHS_FACTYP and the current (rhs) FACTYP
; are int (==2); ZF clear otherwise (no caller reads A after a NZ: each one
; branches to its float path). Clobbers A, HL (DE, BC preserved).
; 🎯 THE NZ OF A FLOAT LHS IS `cp 5`'s: A < 5 (a single) jumps with NZ, A > 5 (a
; double) falls through with it, and nothing below touches the flags. It
; holds because no type is 5 (push_lhs_frame's header).
pop_lhs_and_probe:
                pop     hl                  ; HL = our own return address
                ld      (PLF_RA),hl
                pop     hl                  ; HL = our direct caller's (combine_*'s
                                            ; own) return address
                ld      (PLF_RA2),hl
                pop     af
                ld      (LHS_FACTYP),a
                cp      2
                jr      z,plap_int          ; an int16 lhs: only its DE is there
                pop     hl
                ld      (LHS_FAC+0),hl
                pop     hl
                ld      (LHS_FAC+2),hl
                cp      5
                jr      c,plap_ret          ; a single: done, NZ
                pop     hl
                ld      (LHS_FAC+4),hl
                pop     hl
                ld      (LHS_FAC+6),hl      ; a double: NZ (A > 5)
plap_ret:
                ld      hl,(PLF_RA2)        ; does not affect flags
                push    hl                  ; restore our caller's (combine_*'s
                                            ; own) return address to the stack,
                                            ; exactly where it needs to be for
                                            ; ITS eventual ret/tail-jump home
                ld      hl,(PLF_RA)         ; does not affect flags
                jp      (hl)                ; jump to OUR return address directly
                                            ; (cheaper than push+ret); does not
                                            ; affect flags -- ZF from the cp above
                                            ; reaches our caller intact
plap_int:
                pop     hl
                ld      (FP_LHSVAL),hl
                call    factyp_is2          ; ZF set iff the rhs is int16 too
                jr      plap_ret

; REFILL (D-WSZERO S16, 2026-10-16): moved here from basic/float-arith.asm, whole and
; self-contained (entered only by label), to refill bytes the stack parameter
; block freed in front of the $3297 pin -- tools/pin_plan.py's exact fill.
; --- mul16x16_32: HL(multiplicand, unsigned) * DE(multiplier, unsigned) ----
; -> 32-bit unsigned product in DE:HL (high:low). Classic shift-double-and-add
; over 16 iterations, MSB-first on the multiplier; own-design extension of
; expr.asm's mul16 (which only keeps the low 16 bits) to the full width,
; needed to detect MSX-signed 16-bit multiply overflow (spec §10.2 int-
; overflow promotion) exactly rather than by wraparound. (Until D-REREAD
; batch 4 its working state lived in RAM -- MULCAND / MULTPLR / MUL32 -- for
; "register pressure"; the accumulator fits DE:HL once the multiplier is
; kept in DE's top as the product shifts in.) Keeps BC; A = 0 on return.
mul16x16_32:
                ; 💰 D-REREAD batch 4 (2026-10-31, -40 B; ~3x faster a bit): the
                ; 32-bit accumulator lives in DE:HL, the multiplier shifting out of
                ; DE's top as the product shifts in (MULCAND / MULTPLR / MUL32 are
                ; no longer written). out: DE:HL = the product; BC kept; A = 0.
                push    bc                  ; C = the caller's sign: kept
                ld      b,h
                ld      c,l                 ; BC = multiplicand
                ld      hl,0                ; DE:HL = accumulator; DE = multiplier
                ld      a,16
m32_lp:
                add     hl,hl
                rl      e
                rl      d                   ; CF = the next multiplier bit
                jr      nc,m32_skip
                add     hl,bc
                jr      nc,m32_skip
                inc     de                  ; carry into the high word
m32_skip:
                dec     a
                jr      nz,m32_lp
                pop     bc
                ret
