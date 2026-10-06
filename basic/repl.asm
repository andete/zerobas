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
                ; --- D-SPMERGE cut 2 step 3: BASE THE MACHINE STACK IN THE POOL --
                ; docs/spec-basic-spmerge.md §3/§9.4. Until now `SP` was whatever
                ; C-BIOS left it at ($F2EA), ~234 B above its floor and nowhere near
                ; the ~22 KB of free RAM the pool descends through -- which is why a
                ; LEGAL 16-deep parenthesised expression WRECKED the machine while
                ; both references answer to depth 32.
                ;
                ; 🔴 SITED HERE AND NOWHERE ELSE. `repl` is entered by `jp` only
                ; (basic/interp.asm and the `jr repl` below) and never returns, so
                ; discarding the stack here discards nothing live. Every other
                ; candidate has a return address in flight -- §3 is the list.
                ; 🎯 RE-READ, NEVER CACHED. `CLEAR n,addr` moves `CTLTOP` and so
                ; moves `CSP`; reading it on every pass through the prompt is what
                ; makes the stack follow `CLEAR`/`RUN`/`NEW` for free, and a cached
                ; boot value is exactly the `$D000` accident of §17.
                ; ⚠️ Frames may be LIVE here -- a `Break` leaves the GOSUB/FOR frames
                ; standing so `CONT` can resume -- so this bases the stack at the
                ; FRONTIER, below them, not at `CTLTOP`.
                ; 🔴 THE COLD-BOOT ZERO GUARD IS DEAD AND THAT IS MEASURED, NOT
                ; ARGUED (2026-09-12, D-SPMERGE step 5). It used to read `CSP` into
                ; HL and skip the move when it was zero, "pool not live yet, before
                ; ctl_reset". A breakpoint on both routines from a COLD BOOT says
                ; ctl_reset runs TWICE, at t=2.641 and t=2.656, and the first `repl`
                ; entry is at t=2.713 with `CSP=D906` already -- so the guarded arm
                ; cannot be taken, and every other entry here is a `jp` from a
                ; running machine. 4 B, which is where step 4's re-base is paid for.
                ; BISECT step 5: repl re-base removed entirely
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
                call    txt_mode            ; D-SCREDIT: the prompt after a graphics program is
                                            ; read in SCREEN 0 on both references
                call    curlin_direct       ; D-CURLIN: back at the prompt is
                                            ; direct mode, CURLIN = $FFFF, as the
                                            ; reference shows (body: str-engine.asm)
                ld      hl,prompt_text
                call    print_string
repl_read:
                call    read_line           ; LINEBUF <- typed line (ASCII, 0-term)
                jr      c,repl              ; CF set = ABORTED (Ctrl-C, D-CTRLC):
                                            ; discarded unexecuted, and prompted
                ; D-OKSTORE: the prompt follows only a direct command or an error --
                ; the protocol and the two cuts that failed are at PRMWANT
                ; (basic/sysvars.inc). ⚠️ A = 2 HERE BY read_line's CONTRACT (its
                ; Enter exit is RL_STAT's 1 through `rla` with CF clear; the CF
                ; exits left above) -- the protocol's "bit 1 alone" is that value.
                ld      (PRMWANT),a
                call    dispatch_line       ; store / RUN / NEW / direct-execute
                ld      a,(PRMWANT)
                or      a
                jr      z,repl_read         ; a silent line: no prompt
                jr      repl

; --- print_string: CHPUT a 0-terminated string at (HL) --------------------
print_string:
                ld      a,(hl)
                or      a
                ret     z
                rst     $18                 ; screen or file (PRDEST); preserves HL
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
                ; D-SCREDIT (docs/spec-basic-screditor.md): the line reader is the
                ; readline tenant (sub/readline.asm, page 1) -- cursor keys reach
                ; CHPUT, Enter reads the LOGICAL LINE under the cursor out of VRAM.
                ; The WAIT stays here, in main, inside CHGET with interrupts
                ; live: a page-1 tenant blocking in CHGET would starve PLAY and
                ; the traps (htimi_guard skips their seam while page 1 is not
                ; main-ROM), so the tenant is handed one key per call in RL_KEY
                ; and never waits. HL rides in
                ; through RL_HL; CF (set = Ctrl-STOP / Ctrl-C) rides back through
                ; RL_STAT, since a carry cannot cross subrom_call.
                ld      (RL_HL),hl
                call    txt_mode            ; INPUT inside SCREEN 2 reads its line in SCREEN 0 too (measured)
                ld      a,(CSRY)
                ld      (RL_ROW0),a         ; where input begins: the FSTPOS rule
                ld      a,(CSRX)
                ld      (RL_COL0),a
                ; C-BIOS's scroll never rewrites the last two LINTTB entries
                ; (D-SCREDIT, write-watchpoint), so after any output that wrapped
                ; at the row above the bottom and then scrolled, the row above the
                ; prompt still reads "continues" and Enter would splice it into the
                ; line (linemax's list-max: a LIST that filled the screen). The
                ; prompt always opens a FRESH line, so on the bottom row both
                ; entries are set to "ends" here; the tenant's own wraps re-mark.
                ld      a,(CRTCNT)
                ld      hl,CSRY
                cp      (hl)
                jr      nz,rl_wait          ; not on the bottom row: the table is C-BIOS's own
                ld      hl,LINTTB-2
                ld      e,a
                ld      d,0
                add     hl,de
                ld      (hl),1              ; the row above the prompt ended a line
                inc     hl
                ld      (hl),1              ; and so does the prompt row, until it wraps
rl_wait:
                ; D-CURSORBLOCK: the block cursor is up while the editor waits for
                ; a key and down while the tenant edits (sub/cursor.asm).
                ld      e,1
                call    rl_cursor
                ld      a,(RL_AUTO)
                or      a
                jr      z,rl_get            ; REPL: block in CHGET, as it always did
rl_poll:                                    ; R-AU8: an AUTO session may NOT block
                call    BREAKX              ; CF set = Ctrl-STOP is down
                jr      c,rl_break
                call    CHSNS               ; ZF set = nothing waiting yet
                jr      z,rl_poll
rl_get:
                call    CHGET               ; the WAIT is here, in main, inside CHGET:
                push    af
                ld      e,0
                call    rl_cursor           ; cursor down before the tenant edits
                pop     af
                ld      (RL_KEY),a          ; interrupts live (PLAY, the traps), and the
                                            ; harness's injector latch (latch-check) sees
                                            ; the same wait it always modelled
                call    ek_ctrl             ; D-EDCTRL: CTRL-B/E/F/N/U are main's
                jr      z,rl_wait           ; (basic/edctrl.asm); Z = handled
                ld      a,(RL_KEY)
                call    sr_inl1             ; D-STUBINL: one key
                db      low (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_READLINE)
                jp      c,subrom_absent_error
                ld      a,(RL_STAT)
                ld      hl,(RL_HL)          ; HL = the end of the text (AUTO's empty test)
                or      a
                jr      z,rl_wait           ; 0: more keys
                rla                         ; 1 -> CF clear (Enter); $FF -> CF set (break)
                ret
rl_break:                                   ; Ctrl-STOP while AUTO polls: the cursor
                ld      e,0                 ; comes down first, CF rides through
                call    rl_cursor           ; (subrom_call returns CF clear, so
                scf                         ; set it again)
                ret
; rl_cursor: E = 1 show / 0 remove the line editor's block cursor.
rl_cursor:
                call    sr_inl1             ; D-STUBINL
                db      low (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_CURSOR)
                ret

; --- txt_mode: back to the LAST TEXT MODE if a graphics mode is up ------------
; Measured on both references (docs/spec-basic-screditor.md §7): the prompt after
; a SCREEN 2 program and an INPUT inside one read their line in a TEXT mode;
; zerobas stayed in SCREEN 2, where C-BIOS's rows are 32 wide and a wrapping line
; read back garbled (graphics-acceptance phase M lost its second program's third
; line).
; 🔴 D-SCR1PROMPT (2026-09-26): THAT RULE WAS "SCREEN 0", AND IT IS "THE LAST
; TEXT MODE". The VG-8020 keeps SCREEN 1 at the prompt, and after `SCREEN 1`
; then a SCREEN 2 program it comes back to SCREEN 1 (SCRMOD 1, OLDSCR 1, LINLEN
; 29 -- scratchpad/scr1prompt_probe.py); this sent every non-zero SCRMOD to
; INITXT, so SCREEN 1 never survived a prompt and OLDSCR always read 0. The
; rule is the published TOTEXT's ($00D2): nothing in SCREEN 0/1, else the mode
; OLDSCR names -- which C-BIOS's INITXT/INIT32 maintain.
; The mode switch clears the screen, and the VG-8020 comes back WITH its
; function-key line (every row of scr1prompt_probe.py); zerobas's came back
; blank, so the switch is followed by key_repaint (D-KEYCLS) -- only when there
; WAS a switch: in SCREEN 0/1 nothing is touched.
txt_mode:
                ld      a,(SCRMOD)
                cp      2
                ret     c                   ; a text mode already: leave it alone
                call    TOTEXT
                jp      key_repaint

; 🏗️ D-ZBCRLF (Joost, 2026-09-24): *"the ZB prompt stays, but it should have
; the crlf like the OK prompt of the reference."* The TEXT stays `ZB` (the
; identity marker, 2026-09-01); the LAYOUT is the reference's -- `Ok` sits alone
; on its row and the typed line starts at column 0 of the next. Same-row `ZB`
; cost every typed line 2 columns the reference does not spend, which D-BOOTWIDTH
; exposed: at 37 columns a 35-37-char line wrapped here and not there.
; prompt_text -- MOVED to basic/islands.asm (D-ISLDATA2, 2026-10-03): pure data,
; read only by absolute `ld` from main; now in the $0160 island.
