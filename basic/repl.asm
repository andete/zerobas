; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; repl.asm — keyboard line editor + read/eval loop.
;
; Reads a line from the keyboard via the BIOS (CHGET), echoes it with simple
; editing (Backspace/DEL), and on Enter hands the line to `dispatch_line`
; (store a numbered line, RUN, NEW, or tokenise+execute a direct line), then
; loops.
;
; The prompt is deliberately "ZB", NOT the original interpreter's "Ok": zerobas
; should never be mistaken for stock MSX-BASIC.
;
; It ALWAYS STARTS ON A FRESH LINE, which is a compatibility fix, not cosmetics.
; The reference opens a line before its prompt whenever the cursor is not at
; column 0; zerobas used to print the prompt wherever the cursor stood, so
; `PRINT "A";` read `Azb>` on one row where the reference reads `A` then `Ok`
; on two. Latent for a long time because nearly everything printed ends with a
; newline -- TRON, whose decoration deliberately emits no newline of its own,
; is what made it visible (docs/spec-basic-missing-class.md).
;
; ⚠️ CONDITIONAL, not unconditional. Emitting CRLF every time would put a BLANK
; row between ordinary output and the prompt, which the reference does not do --
; "always start on a fresh line" and "always emit a newline" are different
; statements, and only the first one is the reference's behaviour. Being at
; column 0 already IS being on a fresh line.
;
; Clean-room: this is an original line editor using only documented BIOS entry
; points (CHGET, CHPUT). No disassembly.

repl:
                ; --- D-LPTVERB R-LP16: flush a partial PRINTER line -------------
                ; MEASURED, and it took three rows to establish: `LPRINT"A";`
                ; leaves a trailing CR/LF in the printer log, while
                ; `LPRINT"ABC";:PRINT LPOS(0)` reads 3 -- no CR/LF had been sent at
                ; that point IN THE SAME LINE. Asking LPOS from a SEPARATE command
                ; reads 0. So the flush happens on the return to COMMAND LEVEL, not
                ; at the end of the statement, and this is the only place that is.
                ;
                ; ⚠️ THE BODY IS IN THE LOW REGION (basic/str-engine.asm,
                ; `lpt_flush`), not inline here: inline it cost ~20 B and the image
                ; overran the $8000 ceiling by ~9 B. Page 1 and the low region are
                ; co-mapped, so this is an in-slot call for 3 B.
                ;
                ; ⚠️ ORDER vs THE "Ok" PROMPT IS UNMEASURED: the printer log and
                ; the screen are captured separately, so no row can see which came
                ; first. Flushing first is the choice; it is not a measured rule.
                ; Knife K3 deletes this call and predicts `lpr-trsemi` alone.
                call    lpt_flush
                xor     a                   ; the prompt + any output go to the
                ld      (PRDEST),a          ; screen (defensive after a PRINT#)
                ld      (RL_AUTO),a         ; ...and the line editor blocks again
                                            ; (defensive after an AUTO session:
                                            ; a typed line that ERRORS out of one
                                            ; unwinds straight to here, so clearing
                                            ; the flag only in ex_auto's own exit
                                            ; would leave the PROMPT polling and a
                                            ; Ctrl-STOP there dispatching a stale
                                            ; buffer -- D-EDITVERB §3.3)
                ld      a,(CSRX)            ; CSRX is 1-BASED, so 1 == column 0 ==
                dec     a                   ; already at the start of a line
                call    nz,print_crlf       ; mid-row -> open a line first
                ld      hl,prompt_text
                call    print_string
                call    read_line           ; LINEBUF <- typed line (ASCII, 0-term)
                call    dispatch_line       ; store / RUN / NEW / direct-execute
                jr      repl

; --- print_string: CHPUT a 0-terminated string at (HL) --------------------
print_string:
                ld      a,(hl)
                or      a
                ret     z
                call    pchar               ; screen or file (PRDEST); preserves HL
                inc     hl
                jr      print_string

; --- read_line: edit a line into LINEBUF, echoing as we go -----------------
; Returns with LINEBUF holding the typed ASCII line, 0-terminated. Handles
; Backspace ($08), DEL ($7F), and Enter ($0D); other control characters are
; ignored. (openMSX maps the Mac Backspace key to the MSX DEL key, so C-BIOS's
; CHGET delivers $7F rather than $08 -- both are treated as erase-left here.)
; HL is the write cursor; it is guarded across every BIOS call (CHGET/CHPUT
; make no register guarantees).
; ⚠️ TWO ENTRY POINTS. `read_line` starts a fresh line at LINEBUF; `rl_loop` is
; entered with HL ALREADY SET, which is how AUTO prepends its line number -- the
; digits are written at LINEBUF and the user's body accumulates after them, so
; the buffer dispatch_line finally sees is an ordinary `<number> <body>` and
; needs no second parser. rl_bs's floor is still LINEBUF, so backspacing can
; erase the number itself; that matches a screen editor where the whole row is
; editable, but it is NOT measured -- see the spec's pin list.
;
; CF ON RETURN: clear = the line was ended with Enter; SET = the poll below saw
; Ctrl-STOP (only reachable with RL_AUTO set).
read_line:
                ld      hl,LINEBUF
rl_loop:
                push    hl
                ld      a,(RL_AUTO)
                or      a
                jr      z,rl_get            ; REPL: block in CHGET as before
                ; R-AU8: an AUTO session may NOT block. Ctrl-STOP is not a
                ; character and never arrives through CHGET, so a blocking read
                ; can only be left by typing something -- the session would be
                ; unbreakable. CHSNS says whether a key is waiting; BREAKX scans
                ; the key matrix directly, which is the only thing that can see it.
rl_poll:
                call    BREAKX              ; CF set = Ctrl-STOP is down
                jp     c,rl_break
                call    CHSNS               ; ZF set = nothing waiting yet
                jr      z,rl_poll
rl_get:
                call    CHGET               ; wait for a key -> A
                pop     hl
                cp      13                  ; Enter -> finish
                jr      z,rl_enter
                cp      8                   ; Backspace -> erase
                jr      z,rl_bs
                cp      $7F                 ; DEL (Mac Backspace via C-BIOS) -> erase
                jr      z,rl_bs
                cp      32                  ; ignore other control chars
                jr      c,rl_loop
                ld      b,a                 ; hold the char
                ld      a,l                 ; bounds: keep the last byte free for the
                cp      (LINEBUF+LINEMAX-1) & $FF  ; Enter terminator, so a full line's 0
                jr      nc,rl_loop          ;  lands inside LINEBUF (not TOKBUF). LINEBUF
                                            ;  is one page ($E1xx), so the low byte suffices.
                ld      (hl),b
                inc     hl
                ld      a,b
                push    hl
                call    CHPUT               ; echo (CHGET does not echo)
                pop     hl
                jr      rl_loop
rl_bs:
                ld      a,l
                cp      LINEBUF & $FF
                jr      z,rl_loop           ; at start -> nothing to erase
                dec     hl
                push    hl
                ld      a,8                 ; back, blank, back: erase on screen
                call    CHPUT
                ld      a,32
                call    CHPUT
                ld      a,8
                call    CHPUT
                pop     hl
                jr      rl_loop
; D-XREG: an ALIAS across the low <-> page-1 boundary. Byte-identical to
; lgb_eof and POSITION-INDEPENDENT (tools/dupspan_indep.py), and the
; REGION question -- is this label reached from a tenant whose mapping
; switches the target page OUT? -- is answered by scratchpad/crossreg_probe.py
; and GATED by check_tenant_closure.py, whose K-XR1 knife proves it can see an
; `equ` (it resolves addresses from the sym, not from the source form).
rl_break        equ     lgb_eof
rl_enter:
                ld      (hl),0              ; terminate the line
                ld      a,13                ; echo CR/LF
                call    CHPUT
                ld      a,10
                call    CHPUT
                or      a                   ; CF CLEAR = a normal Enter finish.
                ret                         ; CHPUT makes no flag guarantee, and
                                            ; ex_auto branches on this carry.

prompt_text:
                db      "ZB",0
