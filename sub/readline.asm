; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; sub/readline.asm — readline_tenant: the screen editor's line reader (D-SCREDIT)
; docs/spec-basic-screditor.md. The REPL, INPUT, LINE INPUT, FORMAT's prompt and
; AUTO all read a typed line through main's `read_line` / `rl_loop`; since
; D-SCREDIT that stub marshals the write cursor in RL_HL and calls this tenant,
; which (1) echoes keys through CHPUT -- INCLUDING the cursor keys $1C..$1F,
; HOME and CLS, which `read_line` used to drop -- and (2) on Enter reads the
; LOGICAL LINE under the cursor back out of VRAM into the buffer, the way the
; reference does (D-EDITSCOUT: the counter payload reads 1 -> 2 -> 3 as
; re-entries accumulate; D-EDITLINE: the unit is the logical line and the
; boundary is bookkeeping the screen does not carry).
;
; The bookkeeping is LINTTB ($FBB2, one byte per row, MSX work area): zero =
; the row continues onto the next. Measured 2026-09-11: C-BIOS's CHPUT keeps it
; on the zerobas machine (zero on a wrapped PRINT row, non-zero on a VPOKEd
; one, shifted with every scroll) EXCEPT for the wrap that itself scrolls the
; screen, where the mark is dropped -- so the echo path below writes that one
; mark when it sees a typed character wrap on the bottom row.
;
; Start column: zerobas prints a `ZB` prompt the harness keys on, INPUT prints
; `? `, AUTO prints the line number; the reference's reader honours the column
; where input began (FSTPOS). RL_ROW0/RL_COL0 record it at entry; a scroll
; during typing moves RL_ROW0 up. On Enter, if the logical line's first row is
; that row the read starts at that column, else at column 1 -- skipping a `ZB`
; the row shows, which is what a re-entered REPL row carries.
;
; Interrupts: none needed. Main waits for a key with interrupts live and calls
; this tenant once per key (see readline_tenant), so nothing here blocks and
; the ISR keeps serving PLAY and the traps between keys.
;
; MARSHALLING: RL_HL in (the write cursor: LINEBUF, or AUTO's preset after the
; line number), RL_ROW0/RL_COL0 in (where input began, recorded by main at
; read_line), RL_STAT out (0 = more keys, 1 = Enter, $FF = Ctrl-C -- a carry
; cannot ride back through subrom_call).
;
; CLEAN-ROOM: original code; the keyboard loop is our own basic/repl.asm
; read_line moved here; CSRY/CSRX/LINLEN/CRTCNT/NAMBAS/LINTTB/SCRMOD and
; CHGET/CHPUT/CHSNS/BREAKX/RDVRM are documented MSX work-area cells and BIOS
; entries (MSX2 Technical Handbook). No reference-ROM disassembly.
; ===========================================================================

; --- readline_tenant: the SUBROM_IDX_READLINE entry -------------------------
; ONE KEY PER CALL. Main's read_line records where input began (RL_ROW0/RL_COL0),
; waits in MAIN inside CHGET -- interrupts live, so PLAY and the traps keep being
; served by the ISR, and the harness's injector latch sees the wait it models --
; and hands the key here in RL_KEY, so nothing in this tenant waits or needs EI. (The
; first cut blocked in CHGET here under EI: htimi_guard skips the PLAY/trap
; seam for every frame a page-1 tenant is mapped, and play-trace-acceptance
; went red -- music stopped at the prompt.) RL_STAT out: 0 = more keys,
; 1 = Enter (the line is in the buffer), $FF = Ctrl-C.
readline_tenant:
                ld      a,(RL_KEY)          ; the key main's CHGET returned: no wait here
                cp      3                   ; D-CTRLC: Ctrl-C aborts the line
                jr      nz,rl_key
                ld      a,$FF
                jr      rl_stat
rl_more:
                xor     a                   ; 0: not finished, main keeps waiting
rl_stat:
                ld      (RL_STAT),a
                ret
rl_key:
                cp      13                  ; Enter -> read the logical line back
                jp      z,rl_enter
                cp      8                   ; Backspace -> erase
                jr      z,rl_bs
                cp      $7F                 ; DEL (Mac Backspace via C-BIOS) -> erase
                jr      z,rl_bs
                cp      $1C                 ; $1C..$1F cursor keys, and every
                jr      nc,rl_echo          ; printable, reach CHPUT
                cp      $0B                 ; HOME
                jr      z,rl_echo
                cp      $0C                 ; CLS
                jr      z,rl_echo
                jp      rl_more             ; other control bytes: dropped, as before
rl_echo:
                ld      c,a                 ; C = the byte to echo
                ld      a,(CSRY)
                ld      hl,CRTCNT
                sub     (hl)                ; Z iff the cursor is on the bottom row
                jr      nz,rl_put
                ld      a,c
                cp      $20
                jr      c,rl_put            ; a cursor key does not wrap
                ld      a,(CSRX)
                ld      b,a                 ; B = the column before the echo
                ld      a,c
                call    CHPUT
                ld      a,(CSRX)
                cp      b
                jp      nc,rl_more          ; the column advanced: no wrap. A wrap
                                            ; leaves it BELOW where it was, whether
                                            ; C-BIOS wraps on the 40th character
                                            ; (CSRX 1) or on the 41st (CSRX 2).
                ; Wrapped on the bottom row: the screen scrolled. C-BIOS shifted
                ; LINTTB but dropped the mark of the row that wrapped (measured)
                ; -- write it -- and the row where input began moved up too.
                xor     a
                call    rl_botfix           ; [bottom-2] = 0: continues; [bottom-1] = 1
                ld      hl,RL_ROW0
                ld      a,(hl)
                or      a
                jp      z,rl_more           ; already off the top
                dec     (hl)
                jp      rl_more
rl_put:
                ld      a,c
                call    CHPUT
                jp      rl_more
rl_bs:
                ld      a,(CSRX)
                dec     a
                jp      z,rl_more           ; column 1: nothing to erase on this row
                ld      a,8                 ; back, blank, back: erase on screen
                call    CHPUT
                ld      a,32
                call    CHPUT
                ld      a,8
                call    CHPUT
                jp      rl_more

; --- Enter: the logical line under the cursor, VRAM -> (RL_HL) ---------------
rl_enter:
                ld      a,(CSRY)
                ld      b,a                 ; B = candidate first row (1-based)
rl_up:
                ld      a,b
                cp      2
                jr      c,rl_first          ; row 1 has nothing above it
                ld      hl,LINTTB-2
                ld      e,a
                ld      d,0
                add     hl,de               ; LINTTB[row-2]: does the row above continue onto this one?
                ld      a,(hl)
                or      a
                jr      nz,rl_first
                dec     b
                jr      rl_up
rl_first:
                ld      a,(RL_ROW0)
                cp      b
                ld      a,(RL_COL0)
                jr      z,rl_col            ; the line where input began: after the prompt
                ld      c,1
                call    rl_vpeek
                cp      'Z'
                ld      a,1
                jr      nz,rl_col
                ld      c,2
                call    rl_vpeek
                cp      'B'
                ld      a,1
                jr      nz,rl_col
                ld      a,3                 ; a re-entered REPL row: skip our own `ZB` prompt
rl_col:
                ld      c,a                 ; C = start column (1-based)
                ld      de,(RL_HL)          ; DE = the write cursor
rl_rows:
                ld      a,(LINLEN)
rl_chars:
                cp      c
                jr      c,rl_rowend         ; past the last column of this row
                push    af
                call    rl_vpeek            ; A = the character at row B, column C
                ld      (de),a
                ld      a,e                 ; cap: the last byte of LINEBUF stays free for
                cp      (LINEBUF+LINEMAX-1) & $FF   ; the terminator (LINEBUF is one page)
                jr      z,rl_full
                inc     de
rl_full:
                inc     c
                pop     af
                jr      rl_chars
rl_rowend:
                push    de
                ld      hl,LINTTB-1
                ld      e,b
                ld      d,0
                add     hl,de               ; LINTTB[row-1]: does row B continue?
                ld      a,(hl)
                pop     de
                or      a
                jr      nz,rl_last
                inc     b
                ld      c,1
                jr      rl_rows
rl_last:
                ld      a,b
                ld      (RL_LAST),a         ; the logical line's last row
                ld      hl,(RL_HL)          ; strip trailing blanks back to the floor
rl_strip:
                push    hl
                or      a
                sbc     hl,de               ; CF iff DE > floor
                pop     hl
                jr      nc,rl_term
                dec     de
                ld      a,(de)
                cp      ' '
                jr      z,rl_strip
                inc     de
rl_term:
                xor     a
                ld      (de),a              ; terminate the line
                ld      (RL_HL),de          ; publish the end: AUTO compares it with
                                            ; its preset to see an EMPTY entry (keep)
rl_down:                                    ; the cursor: below the logical line's LAST row
                ld      a,(RL_LAST)
                ld      hl,CSRY
                cp      (hl)
                jr      z,rl_crlf
                jr      c,rl_crlf
                ld      a,$1F               ; cursor down
                call    CHPUT
                jr      rl_down
rl_crlf:
                ld      a,13
                call    CHPUT
                ld      a,10
                call    CHPUT
                ld      a,(CRTCNT)
                ld      hl,RL_LAST
                cp      (hl)
                jr      nz,rl_ok            ; the LF did not scroll: the table is intact
                ld      a,1
                call    rl_botfix           ; it did: the line's last row moved up, and ENDS
rl_ok:
                ld      a,1                 ; 1: Enter -- the line is in the buffer
                jp      rl_stat

; --- rl_botfix: the two LINTTB entries C-BIOS's scroll never rewrites ---------
; Measured with a write-watchpoint (D-SCREDIT): after this reader marked
; LINTTB[bottom-2] = 0 for a wrap that scrolled, every later scroll (C-BIOS,
; PC $13CC) copied that 0 into [bottom-3] and NEVER rewrote [bottom-2] or
; [bottom-1] -- the shift stops two short of the end -- so the mark outlived
; its row and every Enter at the bottom spliced the row above the prompt into
; the read. After each scroll THIS reader causes, set the two stale entries:
; A = the mark for the row above the bottom, and the bottom row ends a line.
rl_botfix:
                ld      c,a
                ld      a,(CRTCNT)
                ld      hl,LINTTB-2
                ld      e,a
                ld      d,0
                add     hl,de
                ld      (hl),c              ; [bottom-2]
                inc     hl
                ld      (hl),1              ; [bottom-1]
                ret

; --- rl_vpeek: A = the screen character at row B, column C (both 1-based) ----
; The name table is NAMBAS + (row-1)*stride + margin + (col-1); the stride is
; the mode's (40 in SCREEN 0, 32 in SCREEN 1), not LINLEN, and the margin centres
; the LINLEN-wide window in it (see rl_vcol). Preserves BC, DE.
rl_vpeek:
                push    bc
                push    de
                ld      a,(SCRMOD)
                or      a
                ld      e,40
                jr      z,rl_stride
                ld      e,32
rl_stride:
                ld      d,0
                ld      hl,(NAMBAS)
                dec     b
                jr      z,rl_vcol
rl_vrow:
                add     hl,de
                djnz    rl_vrow
rl_vcol:
                ; The text window is CENTRED in the name table: column 1 sits at
                ; index (stride + 1 - LINLEN) / 2 -- measured: 1 at WIDTH 39 on
                ; C-BIOS (the prompt row reads `| ZB` with CSRX = 3), and the
                ; VG-8020's captures show two blanks at its default 37. 0 at 40.
                ld      a,e                 ; the stride
                inc     a
                ld      e,a
                ld      a,(LINLEN)
                ld      d,a
                ld      a,e
                sub     d                   ; stride + 1 - LINLEN
                srl     a                   ; the left margin
                add     a,c
                dec     a                   ; + (col - 1)
                ld      e,a
                ld      d,0
                add     hl,de
                call    RDVRM               ; A = VRAM byte at HL (BIOS)
                pop     de
                pop     bc
                ret
