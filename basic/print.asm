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

; --- ex_lprint: LPRINT — PRINT with the sink re-pointed at LPT: ---------------
; D-LPTVERB, docs/spec-basic-lptverb.md §3.1. The whole item loop is ex_print's;
; only the two sink cells differ, exactly as LLIST shares ex_list (basic/list.asm).
;
; 🔴 THE SINK IS TWO CELLS, NOT ONE. PRDEST=1 alone routes pchar to pch_file,
; whose PRDEV then selects DISK -- so LPRINT would write into whatever file
; channel was last used. PRDEV=1 is what names the printer. Knife K2 is that cut,
; and its predicted RED is an empty log with a file-sink write, not just silence.
;
; ⚠️ NO SINK RESTORE, AND THAT WAS VERIFIED RATHER THAN ASSUMED: exec_stmt
; (basic/interp.asm) opens EVERY statement with `xor a / ld (PRDEST),a`, so
; R-LP10's "the next statement prints to the screen" is already the machine's
; behaviour. `scr-lprsink` is the row that would catch it if that ever changed.
; (D-EDITVERB's K3 note credits `repl` for this property; repl is the
; prompt-level half, exec_stmt the statement-level one.)
;
; ⚠️ AND UNLIKE LLIST, LPRINT DOES NOT END THE LINE (R-LP9) -- no ENDFLAG store
; here. `scr-lprtail` reads B=9 after `LPRINT"A":B=9`; with an ENDFLAG store it
; would read 0.
ex_lprint:
                inc     hl                  ; past the LPRINT token
                ld      a,1
                ld      (PRDEV),a           ; 1 = LPT: printer
                ld      (PRDEST),a          ; stream items to it
                call    skip_spaces
                cp      USING_TOKEN         ; LPRINT USING "fmt"; values (R-LP11)
                jp      z,ex_print_using
                ; 🔴 THE '#' TEST IS EXPLICIT, AND THE SPEC PREDICTED IT WOULD NOT
                ; NEED TO BE. §3.1 assumed that falling into the item loop with '#'
                ; in A would produce R-LP14's Syntax error "because the expression
                ; parser rejects it". It does not: measured, `LPRINT#1,"A"` printed
                ; a run of several hundred ` 0` values to the printer -- the parser
                ; read '#' as something evaluable and looped. An assumption the spec
                ; flagged AS an assumption, refuted by the row written to check it.
                ; `lpr-hash` (the log) alone could not have said so either: an empty
                ; log is equally consistent with a silent accept, and this log was
                ; not even empty. `scr-lprhash` is the row that names the message.
                cp      '#'
                jp      z,exp_pos_syn       ; ERR 2, and nothing printed
                jr      exp_loop

ex_print:
                inc     hl                  ; past the PRINT token
                ; PRINT #n, … (file form): redirect the item loop to the channel.
                call    skip_spaces
                cp      USING_TOKEN         ; PRINT USING "fmt"; values  (formatted)
                jp      z,ex_print_using
                cp      '#'
                jr      nz,exp_loop         ; no '#': ordinary screen PRINT
                inc     hl
                call    eval_chan           ; §5.7 gap 2: surface a channel-expr FP
                                            ; error (Division-by-zero / Overflow) as
                                            ; a run abort, matching INPUT# (files.asm)
                call    fch_check           ; D-BADFNUM: D!=0 -> ERR 5, 0 -> ERR 59,
                                            ; > MAXF -> ERR 52. Was `jp nc,load_error`,
                                            ; which answered one untrappable message
                                            ; to all three and let the program run on
                ; classify the channel by its stored mode WITHOUT selecting it: a
                ; device channel (LPT:/CRT:, FCH_MODES 5/6) owns no fat.asm context,
                ; so fch_select would LDIR a garbage buffer over the engine globals.
                ; D-NOTOPEN (docs/spec-basic-chan-notopen-err59.md): this used to
                ; hand-inline fch_mode_class's array read and OMIT its `or a`, so a
                ; NOT-OPEN channel (mode 0) matched none of the device compares,
                ; fell into the disk arm and derailed to `load_error` -- which
                ; PRINTS AND CONTINUES. The CF-3300 raises a trappable ERR 59 (and
                ; so does zerobas's own LOF(1) on the very same closed channel).
                ; Calling the shared classifier is the fix AND 4 bytes smaller.
                ; fch_mode_class preserves E (the `ld a,e / call fch_select` below
                ; needs it) and clobbers only A/HL, which the push/pop already
                ; guards; D no longer has to be zeroed and is not read after this.
                ; Raising from between the push and the pop is safe: raise_error
                ; resets SP from SAVSTK on BOTH the trap and the abort arm.
                push    hl                  ; save the text cursor (the call clobbers HL)
                call    fch_mode_class      ; A = FCH_MODES[ch]; ERR 59 if not open
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
                and     $FE                 ; S10.B: 3 (OUTPUT) or 2 (APPEND)
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
                call    skip_comma          ; consume the separator after #n (','/';')
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
                cp      USING_TOKEN
                jp      z,ex_print_using
                ; fall through into the shared item loop
exp_loop:
                call    skipsp_test
                jp      z,exp_nl_ret        ; end of line -> newline, done (repack:
                                            ; the F2 driver checks pushed this out of
                                            ; jr range, see below)
                cp      COLON
                jp      z,exp_nl_stmt       ; ':' -> newline, then next statement
                cp      ';'
                jr      z,exp_semi
                cp      ','
                jp      z,exp_comma
                cp      '"'
                jp      z,exp_str
                ; TAB( and SPC( are PRINT-ITEM dispatch, NOT $FF factors. Placing
                ; them here and NOWHERE in ev_f is what makes `X=TAB(5)` and
                ; `IF TAB(5)=0` a SYNTAX error (MEASURED) with no code at all: the
                ; token simply falls off the end of ev_f's chain into ev_f_err. A
                ; "PRINT mode" flag would have bought the same behaviour and a
                ; hidden global with it.
                cp      TAB_TOKEN           ; $DB -> TAB(n): absolute column
                jp      z,exp_tab
                cp      SPC_TOKEN           ; $DF -> SPC(n): n spaces
                jp      z,exp_spc
                cp      PEEK_PREFIX         ; $FF function token -> maybe a string function
                jp      z,exp_maybe_strfn   ; (repack: CHR$/STR$/LEFT$/…; falls back to exp_num)
                cp      STRING_TOKEN        ; $E3 STRING$(n,c) -> string (single-byte token,
                jp      z,exp_maybe_strfn   ;  not $FF-prefixed; str_eval handles it, prints)
                cp      INKEY_TOKEN         ; $EC INKEY$ -> string (single-byte token; str_eval
                jp      z,exp_maybe_strfn   ;  reads the key, prints it — else PRINT INKEY$ mismatches)
                ; ✅ D-STRPAREN: `PRINT (A$)`. This is the ONE item shape a peek
                ; cannot classify -- `(A$)` is a string and `(A+1)` is not, and
                ; nothing short of evaluating the inside can say which. So it is
                ; not classified: the STRING path is TRIED and allowed to
                ; decline. `str_eval_paren` (basic/strvar.asm) restores HL and
                ; returns CF clear on a non-string inside, and `exp_strvar`
                ; already has `jr nc,exps_fallback` -- whose own comment states
                ; the contract this relies on: "str_eval left HL unmoved on
                ; failure, so this restores the same cursor exp_num would see
                ; un-gated". So the numeric path is reached with exactly the
                ; cursor it would have had, and `PRINT (A+1)` is untouched --
                ; which is the GATED control `p.numprint`, not an assumption.
                ; ⚠️ `(` is $28 and collides with no token, so its position in
                ; this chain is free; it sits with the other string operands.
                ; 🎯 D-DEFFN JOINS THE `(` CASE, NOT THE INKEY$ ONE, AND THAT IS
                ; THE WHOLE REASON IT IS HERE. `FNA$("hi")` and `FNA(2)` share a
                ; token, so a PEEK cannot classify the item any more than it can
                ; classify `(A$)` versus `(A+1)` -- only the FN's own NAME can,
                ; and reading it is str_ev_fn's job. So the string path is TRIED
                ; and str_ev_fn DECLINES a numeric FN by restoring HL and
                ; returning CF clear, which is exactly the contract
                ; `jr nc,exps_fallback` below already relies on.
                ; 🔴 WITHOUT THIS ARM `PRINT FNA$("hi")` IS ERR 13, and it looks
                ; like a DEF FN defect rather than a PRINT classification one:
                ; the item fell through to `is_letter` -> exp_num -> ev_fn, whose
                ; own guard correctly refuses a `$` function in a numeric factor.
                ; b.str / o.defstr / o.quotedcolon are the three rows.
                cp      FN_TOKEN            ; $DE FN<name>[$] -> maybe a string
                jr      z,exp_strvar
                cp      '('
                jr      z,exp_strvar
                ; 🎯 D-UPSTR: `PRINT +A$`. THE THIRD SITE, and it joins the `(`
                ; case rather than the `"` one for the same reason `(` does -- a
                ; leading `+` classifies NOTHING (`+A$` is a string, `+1` is not),
                ; so the string path is TRIED and allowed to decline. str_eval ->
                ; str_eval_one -> str_eval_plus consumes the `+`, and on a numeric
                ; operand puts the cursor BACK ON it and returns CF clear, which is
                ; the contract `jp nc,exps_fallback` below already relies on. So
                ; `PRINT +1` reaches exp_num with exactly the cursor it had before.
                cp      PLUS_TOKEN          ; $F1 -> maybe a string (unary plus is the
                jr      z,exp_strvar        ; identity on both references)
                call    is_letter           ; a `$`-suffixed string variable?
                jr      nc,exp_num
                call    var_str_type        ; A=1 if `$` suffix
                or      a
                jr      nz,exp_strvar       ; string variable -> print its value
exp_num:
                call    eval                ; numeric expression -> DE = value
                call    check_expr_errors   ; D-2/D-F2-1 (interp.asm): abort the whole
                                            ; line before the newline/next item
                call    factyp_is2         ; §9.4: exp_num dispatches on FACTYP after eval
                jr      nz,exp_num_float
                push    hl                  ; print_number divides the value in HL,
                call    print_number        ;  clobbering the token cursor — guard it
                pop     hl                  ;  (same as exp_strvar does for print_strval)
                jr      exp_loop
exp_num_float:
                push    hl                  ; flt_out ends in print_string, which guards
                call    flt_out             ;  HL across CHPUT the same way (basic/float.asm)
                pop     hl
                jr      exp_loop
exp_strvar:
                ; S2 (spec-basic-print-unparen-compare.md §3): remember the
                ; operand START before str_eval consumes it -- if a relational
                ; operator follows the string value, this item is really the
                ; LHS of an unparenthesized comparison (`PRINT A$="YES"`) and
                ; must be re-parsed from here via eval/ev_rel instead of printed.
                push    hl                  ; operand START (peek may reparse via eval)
                call    str_eval            ; STRPTR -> the var's value, HL advanced
                jp     nc,exps_fallback    ; defensive: not a string after all
                call    skip_spaces
                call    relop_peek          ; ZF=1 iff (HL) is a relop token
                jr      nz,exps_notrel      ; no relop -> maybe an operator (below)
                pop     hl                  ; relop follows -> restore the operand START
                jr      exp_num             ; re-drive via eval -> ev_rel (-1/0, or D-2 abort)
; --- an OPERATOR after a string value is a Type mismatch ---------------------
; MEASURED (docs/logicops-vg8020-characterization.md §6): the reference rejects
; EVERY operator here -- `"A" AND 1`, and equally `- * / ^ \ MOD` and the rest.
; Twelve tokens; zerobas honoured only `+` (str_eval's own concat check) and
; silently mis-printed the other eleven: the item printed, exp_loop re-entered on
; the operator token, `eval` read it as a zero-valued factor, and the line emitted
; a SECOND bogus value (`PRINT "A" AND 1` -> `A 0`).
;
; This sits AHEAD of print_strval, not after it, because the reference raises the
; error BEFORE emitting the item -- `[|Type mismatch`, not `[A|Type mismatch`.
; Putting it after was the first attempt and it produced exactly that one-character
; divergence: the right error, one item too late.
;
; Relationals ($EE/$EF/$F0) never arrive here -- relop_peek above sent them back
; through eval/ev_rel as unparenthesized comparisons. An operator at the START of
; an item is still fine (`PRINT -1`): this is only the just-emitted-a-string path.
exps_notrel:
                ld      a,(hl)              ; relop_peek clobbers A -- re-read
                call    op_after_str_q      ; ZF=1 iff an operator token follows
                jr      nz,exps_print
                pop     de                  ; BALANCE the operand-START push before we
                                            ; abort. check_expr_errors pops only its OWN
                                            ; resume address, so leaving the guard on the
                                            ; stack strands one word per occurrence --
                                            ; harmless on some paths and a hard crash into
                                            ; garbage VRAM on others (`PRINT "A" IMP 1`).
                call    type_mismatch_set   ; deferred mark (ERRMARK + TMISMATCH)
                call    check_expr_errors   ; ... surfaced HERE; never returns
; D-XREG: an ALIAS across the low <-> page-1 boundary. Byte-identical to
; ems_print and POSITION-INDEPENDENT (tools/dupspan_indep.py), and the
; REGION question -- is this label reached from a tenant whose mapping
; switches the target page OUT? -- is answered by scratchpad/crossreg_probe.py
; and GATED by check_tenant_closure.py, whose K-XR1 knife proves it can see an
; `equ` (it resolves addresses from the sym, not from the source form).
; ⚠️ ENTERED BY FALLTHROUGH, so this cannot become an `equ` -- a `jp`
; has to stay in its place. tools/dupspan_indep.py calls it SAFE-JP.
exps_print:
                jp      ems_print
; D-XREG: an ALIAS across the low <-> page-1 boundary. Byte-identical to
; ems_fallback and POSITION-INDEPENDENT (tools/dupspan_indep.py), and the
; REGION question -- is this label reached from a tenant whose mapping
; switches the target page OUT? -- is answered by scratchpad/crossreg_probe.py
; and GATED by check_tenant_closure.py, whose K-XR1 knife proves it can see an
; `equ` (it resolves addresses from the sym, not from the source form).
exps_fallback   equ     ems_fallback
exp_semi:
                inc     hl                  ; ';' = no spacing
                ; 🎯 D-CARVE3: canonical PRINT item-list terminator -- end of
                ; statement, `:` or another item. Both PRINT arms share it.
exp_stmt_end:
                call    skipsp_test
                ret     z                   ; trailing ';' at EOL -> no newline
                cp      COLON
                jp      z,exec_stmt         ; trailing ';' before ':' -> no newline
                jp      exp_loop
exp_nl_ret:
                jp      print_crlf
exp_nl_stmt:
                call    print_crlf
                jp      exec_stmt           ; HL on ':' -> exec_stmt steps over it
exp_str:
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
                inc     hl                  ; past the opening quote
exp_str_lp:
                ld      a,(hl)
                or      a
                jp      z,exp_loop          ; unterminated -> stop (back to loop -> EOL)
                cp      '"'
                jr      z,exp_str_close
                rst     $18                 ; emit to screen or file (PRDEST)
                inc     hl
                jr      exp_str_lp
exp_str_close:
                inc     hl                  ; past the closing quote
                jp      exp_loop
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
                call    op_after_str_q      ; an OPERATOR ($F1..$FC) follows? ZF=1 if so.
                jr      z,slcq_yes          ; (widened from a bare `cp PLUS_TOKEN`: every
                ld      a,(hl)              ;  operator after a literal must leave the fast
                call    relop_peek          ;  char-by-char path, so exps_notrel can reject
slcq_yes:                                   ;  it BEFORE the literal is emitted. Only '+'
                pop     hl                  ;  used to, which is why `PRINT "A" AND 1`
                ret                         ;  printed the A and `PRINT "A" + 1` did not.)
slcq_no:
                pop     hl
                or      1                   ; A nonzero -> ZF=0 (not concat/compare)
                ret

; --- op_after_str_q: is A one of the contiguous operator tokens? -------------
; $F1 '+' .. $FC '\' -- '+' '-' '*' '/' '^' AND OR XOR EQV IMP MOD '\'. Same
; shape and contract as relop_peek (str-engine.asm): A is the peeked token byte,
; ZF=1 iff it is in range, only A and flags are touched. Relationals sit just
; BELOW this range ($EE/$EF/$F0) and are deliberately excluded -- they are a
; comparison to re-parse, not a type error.
op_after_str_q:
                sub     PLUS_TOKEN                  ; A -= $F1
                cp      IDIV_TOKEN - PLUS_TOKEN + 1 ; in the 12-token block?
                jr      c,oas_yes
                or      1                   ; out of range -> A nonzero -> ZF=0
                ret
oas_yes:
                cp      a                   ; in range -> force ZF=1
                ret
exp_comma:
                inc     hl
                call    print_comma_zone    ; pad to the next 14-column zone
                jr      exp_stmt_end        ; D-CARVE3 (-10 B, main page 1)

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
                call    neg_de_hl           ; HL = -value = magnitude
pn_conv:
                call    dgt_push            ; D-DGTPUSH: the shared digit loop
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
                ; 🎯 D-CARVE3: canonical "0-terminate NUMBUF and print it" tail;
                ; basic/list.asm's line-number emitter jumps here.
num_publish:
                xor     a
                ld      (de),a              ; 0-terminate
                ld      hl,NUMBUF
                jp      print_string        ; guards HL across CHPUT

; --- dgt_push: HL -> decimal digits on the STACK, LSB first, under a sentinel -
; D-DGTPUSH (2026-09-05). THREE main-ROM sites carried this eleven-byte loop
; byte for byte -- `pn_conv` here, `ln_div_entry` (basic/list.asm) and
; `pfi_pos` (basic/printusing.asm) -- found by `tools/clone_scout.py --extend`,
; which prices the collapse at 10 B and is exactly what it measured.
;
; 🔴 IT CANNOT BE A PLAIN SUBROUTINE, AND THAT IS THE WHOLE DESIGN. The loop
; PUSHES its results; a `call` would bury the return address underneath them and
; `ret` would pop a digit. So the return address is lifted into DE on entry and
; pushed back on top before the `ret` -- which is legal only because div10's
; contract is "clobbers A, B, HL" and leaves DE alone (basic/float-arith.asm).
; ⚠️ DE IS THEREFORE NOT AVAILABLE TO CALLERS ACROSS THIS CALL. All three
; sites reload DE (or HL) immediately afterwards, which is why the collapse is
; free rather than costing a push/pop pair at each of them.
;
;   in:  HL = magnitude (unsigned)
;   out: digits on the stack, least-significant first, with $FF beneath them;
;        HL = 0, A/B clobbered, DE clobbered.
dgt_push:
                pop     de                  ; the return address, out of the way
                ld      a,$FF               ; stack sentinel (not a digit)
                push    af
dgp_lp:
                call    div10               ; HL /= 10, A = remainder 0..9
                push    af                  ; push digit (least-significant first)
                ld      a,h
                or      l
                jr      nz,dgp_lp
                push    de                  ; return address back on top
                ret

; --- div10: HL = HL/10, A = remainder (0..9) -------------------------------
; Shift-and-subtract (standard binary divide). Clobbers A, B, HL.
;
; HOME (subrom-mathpack migration, 2026-07-13): NOT here in page 1, but in
;     the page-0 low region
;     (basic/float-arith.asm) instead, so the fp_sqrt PAGE-1 sub-ROM tenant's
;     page-0-resident float core (widen_uint_to) can still reach it while main-
;     ROM page 1 is switched out (see float-arith.asm's div10 header). All
;     callers here (pn_div, list.asm, printusing.asm) resolve to that page-0
;     copy by label, unchanged.

; --- D-TEMPPOL part 2 (2026-09-25): release a CONSUMED temporary -----------
; str_release_top: if STRPTR is the NEWEST temp-stack entry, pop it -- as the
; reference frees a temporary its consumer has used up. Without it LEN/ASC/VAL
; and every PRINT item kept their temp to the end of the statement, so a
; 10-entry pool ran out at 11 `LEN(MID$(..))` terms or 11 printed slices where
; the VG-8020 has no limit (scratchpad/tempst_probe.py). The descriptor's bytes
; are untouched -- its GC-root status ends, and (D-S2BHEAP) a body at the
; heap's edge moves FRETOP past it, but no byte is written -- so a caller that
; reads STRPTR right after (LEN's length, ASC's first byte) still reads the
; right value as long as nothing allocates in between. Page 1 on purpose: the two consumers are
; in the full low region and reach this through a same-size `jp`/`call` swap.
; Preserves HL, DE, BC, IX. Clobbers A, F.
str_release_top:
                push    hl
                push    de
                ld      hl,(STRPTR)
                ld      de,(TEMPPT)
                dec     de
                dec     de
                dec     de                  ; DE = the newest entry (TEMPPT-3)
                or      a
                sbc     hl,de
                jr      nz,srt_keep         ; not the newest -> keep it
                ld      (TEMPPT),de         ; pop
                ; D-S2BHEAP (2026-09-27): a body at the heap's edge is given
                ; back at once, as the reference's FRETOP reads -- `X=LEN(MID$(
                ; "ABCDEF",2,3))` holds 0 B on both (scratchpad/strtemp_probe.py).
                ; A temp's body is uniquely owned (sh_src_is_temp's invariant).
                ex      de,hl               ; HL = the entry
                ld      a,(hl)              ; A = len
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = body
                ld      hl,(FRETOP)
                sbc     hl,de               ; CF is clear: the pop's sbc gave Z
                jr      nz,srt_keep         ; not the edge: waits for a collection
                add     a,e
                ld      l,a
                adc     a,d
                sub     l
                ld      h,a                 ; HL = body + len
                ld      (FRETOP),hl
srt_keep:
                pop     de
                pop     hl
                ret
; LEN/ASC/VAL's shared exit (ev_str_arg): release, then the int-result tail
esa_release_int:
                call    str_release_top
                jp      flt_int_result
; a PRINT item (ems_print): print it, then release it
print_strval_rel:
                call    print_strval
                jr      str_release_top

; --- print_crlf: CR + LF ---------------------------------------------------
print_crlf:
                ld      a,13
                rst     $18
                ld      a,10
                ; ...and FALLS THROUGH into pchar (the `jr` here was to the very
                ; next instruction: -2 B, GA-CROSS-ROMSCAN)

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
                ; --- D-LPTVERB: maintain the printer column (LPOS's source) -----
                ; R-LS2/R-LS6: LPOS counts the bytes ACTUALLY SENT, which is why
                ; the counter lives here and not in ex_lprint -- TAB/SPC padding
                ; reaches the printer through this sink and never passes through
                ; the statement head. Knife K5 moves it to ex_lprint and predicts
                ; `lps-tab` reads 0 instead of 10 while `lps-after` still reads 3.
                ;
                ; R-LS3: a CR returns the head to column 0. LF is NOT counted as
                ; an advance -- see LPTPOS in basic/sysvars.inc for why a lone LF
                ; is a recorded CHOICE and not a measured rule.
                ld      a,c
                cp      13                  ; CR -> column 0
                jr      z,pch_lpt_home
                cp      10                  ; LF -> no advance, no reset
                jr      z,pch_done
                ld      a,(LPTPOS)
                inc     a
                jr      z,pch_done          ; 255 saturates rather than wrapping to
                                            ; 0, which would read as "line start"
                                            ; and suppress the R-LP16 flush
                ld      (LPTPOS),a
                jr      pch_done
pch_lpt_home:
                xor     a
                ld      (LPTPOS),a
                jr      pch_done
pch_disk:
                ; S10.B: an OUTPUT channel's byte goes to disk.rom (H_CHOUT), which
                ; raises 66 itself on a full disk. FCH_ACTIVE first: SAVE ,A parks
                ; the channels (fch_park) and streams through here with FCH_MODE
                ; still naming the last one. IX is guarded: a hook call is a CALLF.
                ld      a,(FCH_ACTIVE)
                or      a
                jr      z,pch_main
                ld      a,(FCH_MODE)
                cp      DOUT_MODE
                jr      nz,pch_main
                ld      a,c
                push    ix
                call    H_CHOUT
                ei                          ; a CALLF returns DI (cg_back's note)
                pop     ix
                jr      pch_done
pch_main:
                ld      a,c
                call    fat_io_putbyte
                jp      c,disk_error        ; D-DISKFULL: a full disk is ERR 66 here,
                                            ; as on the CF-3300 (it used to be dropped)
pch_done:
                pop     af
                pop     bc
                pop     de
                pop     hl
                ret

; --- TAB( / SPC( : the two PRINT-positioning items ---------------------------
; MEASURED (docs/cursor-vg8020-characterization.md §4), at a pinned WIDTH 40:
;   TAB(n)  ABSOLUTE 0-based column. If the cursor is ALREADY AT OR PAST n, do
;           NOTHING -- no move and NO NEWLINE. This is the clause a value-shaped
;           test cannot see, and the obvious "pad to column n" implementation
;           gets it wrong by wrapping.
;   SPC(n)  RELATIVE -- emit n spaces.
; Both wrap by ordinary line wrap once the padding runs past the width, which is
; where TAB(45) -> column 5 of the next row comes from: it is pchar's doing, not
; a special case here.
exp_tab:
                call    exp_pos_arg         ; A = n (0..255); HL past the ')'
                ld      c,a
                ld      a,(CSRX)
                dec     a                   ; 0-based current column
                ld      b,a
                ld      a,c
                sub     b                   ; n - column
                jp      z,exp_loop          ; already exactly AT n -> nothing
                jp      c,exp_loop          ; already PAST n -> nothing, NO newline
                jr      exp_pad
exp_spc:
                call    exp_pos_arg
                or      a
                jp      z,exp_loop          ; SPC(0) -> nothing
exp_pad:
                ld      b,a
                call    pcz_pad             ; emit B spaces (shared with comma zones)
                jp      exp_loop

; exp_pos_arg: parse the "(n)" of a TAB(/SPC( item -> A = n, HL past the ')'.
; The token INCLUDES the '(' (it is part of the keyword), so the argument starts
; immediately after it. get_byte_arg is exactly the measured coercion: truncate
; toward zero, ERR 6 (Overflow) outside int16 -- which is why TAB(99999) is an
; Overflow and not an Illegal function call -- and ERR 5 (Illegal function call)
; in-int16 but negative or >255. Both abort; neither returns.
exp_pos_arg:
                call    inc_eval            ; DE = argument, HL advanced
                call    get_byte_arg        ; A = n, or abort (ERR 6 / ERR 5)
                push    af
                call    skip_spaces
                cp      ')'
                jp      nz,exp_pos_syn      ; `jp`: pl_syntax is out of jr range (B4)
                inc     hl
                pop     af
                ret
; B4: an ALIAS, not a second copy -- byte-identical to play.asm's pl_syntax
; (`ld a,2 / jp raise_error`), the family's canonical tail.
exp_pos_syn     equ     pl_syntax           ; ERR 2 syntax error

; --- print_comma_zone: pad with spaces to the next 14-column tab zone -------
; MSX PRINT comma zones are 14 characters (public language reference). Reads the
; current column from CSRX (1-based). Clobbers A, B.
; D-CUR-1, MEASURED (docs/cursor-vg8020-characterization.md §5): the reference
; wraps to a NEW LINE rather than advancing when the next zone would not fit
; ENTIRELY -- the rule is `next_zone + 14 <= width`, not `next_zone < width`.
; The boundary is confirmed at WIDTH 28 (advances) vs 27 (wraps). This used to
; pad unconditionally and never wrap, which put the third item of
; `PRINT "A","B","C"` at column 28 instead of on the next line at every width
; from 30 to 40.
;
; NOTE a three-item row CANNOT tell the two candidate rules apart: zone 3 starts
; at 28 and 28+14=42 exceeds every legal SCREEN 0 width, so both predict a wrap
; everywhere. The two-item row is what settles it.
print_comma_zone:
                ; 🔴 D-LPTVERB: THE ZONE IS COUNTED FROM THE *ACTIVE SINK'S* COLUMN.
                ; This read CSRX unconditionally, which is the SCREEN cursor -- and
                ; printing to the printer moves neither CSRX nor LINLEN. Measured,
                ; `LPRINT"A","B"` padded to 14 spaces where both references pad to
                ; 13, because the screen cursor was still at column 0 while the
                ; printer head was at 1. R-LP5 says the zones are PRINT's, and that
                ; means PRINT's arithmetic over the printer's own column.
                ld      a,(PRDEST)
                or      a
                jr      z,pcz_screen        ; screen sink -> CSRX
                ld      a,(PRDEV)
                dec     a                   ; PRDEV 1 = LPT:
                jr      nz,pcz_screen       ; a FILE/CRT/tape channel keeps CSRX,
                                            ; which is what it did before this slice
                ld      a,(LPTPOS)          ; already 0-based
                jr      pcz_col
pcz_screen:
                ld      a,(CSRX)
                dec     a                   ; 0-based column
pcz_col:
                ld      c,a                 ; C = current column (for the fit test
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
                add     a,c                 ; A = the NEXT zone's absolute column
                add     a,14                ; ... and the column just past that zone
                ld      c,a
                ld      a,(LINLEN)
                cp      c                   ; width < zone end -> the zone does not fit
                jp      c,print_crlf        ; -> newline instead of padding
pcz_pad:
                ld      a,' '
                rst     $18                 ; screen or file (PRDEST); preserves BC
                djnz    pcz_pad
                ret
