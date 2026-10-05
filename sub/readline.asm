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
                xor     a
                ld      (INSFLG),a          ; a line that ends ends insert mode
                dec     a                   ; $FF: Ctrl-C
                jr      rl_stat
rl_more:
                xor     a                   ; 0: not finished, main keeps waiting
rl_stat:
                ld      (RL_STAT),a
                ret
rl_key:
                ; 🔤 D-INSMODE (2026-09-26): the reference's edit keys SHIFT the
                ; logical line (scratchpad/insmode_probe.py): INS (18) toggles
                ; insert mode (INSFLG $FF), in which a typed character pushes the
                ; rest of the line right; DEL ($7F) deletes the character UNDER the
                ; cursor and BS (8) the one to its left, both pulling the rest in.
                ; Enter, the cursor keys, HOME and CLS end insert mode; BS does
                ; not. 🏗️ $7F WAS erase-left since June (the Mac Backspace key
                ; arrives as the MSX DEL key) -- Joost ruled "Faithful DEL": the
                ; VG-8020 in openMSX treats that key as DEL too.
                cp      13                  ; Enter -> read the logical line back
                jp      z,rl_enter
                cp      8                   ; Backspace -> erase left, pull the line in
                jp      z,rl_bs
                cp      $7F                 ; DEL -> delete under the cursor
                jp      z,rl_del
                cp      18                  ; INS -> toggle insert mode
                jr      z,rl_ins
                cp      $20
                jr      nc,rl_char          ; printable (>= $20; $7F went above)
                cp      $1C                 ; $1C..$1F cursor keys
                jr      nc,rl_ctl
                cp      $0B                 ; HOME
                jr      z,rl_ctl
                cp      $0C                 ; CLS
                jr      z,rl_ctl
                cp      9                   ; TAB (D-EDCTRL)
                jr      z,rl_tab
                jp      rl_more             ; other control bytes: dropped, as before
; 🔤 TAB (D-EDCTRL, 2026-10-05): it TYPES SPACES to the next 8-column stop --
; the VG-8020 read, scratchpad/edctrl_probe.py: `AB`+TAB puts the cursor on
; column 9 (blanks 3..8), and over existing text it OVERWRITES (`ABCDEFGHIJ`,
; cursor on B, TAB -> `A.......` + cursor on 9). From column 33 or later on a
; 37-column row it fills to the edge and WRAPS to column 1 of a continuation row
; (LINTTB marks the row continued), and in insert mode it INSERTS the spaces and
; insert mode stays on. Every one of those is "a space through the ordinary
; character path, until (CSRX-1) is a multiple of 8", so that is what this is.
rl_tab:
                ld      a,' '
                call    rl_char1
                ld      a,(CSRX)
                dec     a
                and     7
                jr      nz,rl_tab
                jp      rl_more
rl_ins:
                ld      a,(INSFLG)
                cpl
                ld      (INSFLG),a
                jr      rl_more
rl_ctl:
                ld      c,a
                xor     a
                ld      (INSFLG),a          ; a cursor key / HOME / CLS ends insert mode
                ld      a,c
                call    rl_echo
                jp      rl_more
rl_char:
                call    rl_char1
                jp      rl_more
; rl_char1: A = a printable byte, typed at the cursor -- insert-aware echo that
; RETURNS (TAB loops over it). rl_echo is its overwrite half, also returning.
rl_char1:
                ld      c,a
                ld      a,(INSFLG)
                or      a
                ld      a,c
                jr      z,rl_echo           ; overwrite mode: straight to the echo
                push    af
                call    rl_shift_right      ; make room at the cursor
                pop     af
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
                ret     nc                  ; the column advanced: no wrap. A wrap
                                            ; leaves it BELOW where it was, whether
                                            ; C-BIOS wraps on the 40th character
                                            ; (CSRX 1) or on the 41st (CSRX 2).
                ; Wrapped on the bottom row: the screen scrolled. C-BIOS shifted
                ; LINTTB but dropped the mark of the row that wrapped (measured)
                ; -- write it -- and the row where input began moved up too.
                jp      rl_scrolled         ; tail: its ret is ours
rl_put:
                ld      a,c
                jp      CHPUT               ; tail: CHPUT's ret is ours
rl_bs:
                ld      a,(CSRX)
                dec     a
                jp      z,rl_more           ; column 1: nothing to erase on this row
                                            ; (unmeasured at a continuation row's
                                            ; column 1 -- today's behaviour kept)
                ld      a,$1D               ; cursor left, then delete there
                call    CHPUT
rl_del:
                call    rl_shift_left
                jp      rl_more

; --- Enter: the logical line under the cursor, VRAM -> (RL_HL) ---------------
rl_enter:
                xor     a
                ld      (INSFLG),a          ; Enter ends insert mode (measured)
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

; --- rl_scrolled: bookkeeping after a scroll this reader caused -------------
; The row above the bottom now continues onto it (rl_botfix), and the row where
; input began moved up with the screen. Shared by a typed wrap on the bottom row
; (rl_echo) and an insert that grows a line ending there (rsr_scroll).
rl_scrolled:
                xor     a
                call    rl_botfix           ; [bottom-2] = 0: continues; [bottom-1] = 1
                ld      hl,RL_ROW0
                ld      a,(hl)
                or      a
                ret     z                   ; already off the top
                dec     (hl)
                ret

; --- rl_vpeek / rl_vpoke / rl_vaddr / rl_lastrow: MOVED TO MAIN'S LOW REGION ---
; basic/edscreen.asm (D-EDCTRL, 2026-10-05). They are pure screen arithmetic over
; documented work-area cells and the RDVRM/WRTVRM BIOS entries, so they run
; unchanged from page 0, which stays mapped while this tenant owns page 1; the
; resident ABI imports them (tools/gen_resident_abi.py REQUIRED_SUB). Main's own
; screen-editor keys (CTRL-B/E/F/N/U) use the same four, and this tenant's page
; 1 got the bytes back.

; --- rl_shift_right: open a blank cell at the cursor (insert mode) -------------
; Every cell from the cursor to the logical line's end moves one right. If the
; line's LAST cell holds a character it would fall off, so the line first grows
; a row -- measured: the VG-8020 pushes the line below DOWN (a new row), and
; spills into a blank continuation row the line already has (that row's last
; cell is a blank, so it grows nothing).
rl_shift_right:
                call    rl_lastrow          ; B = the last row
                ld      a,(LINLEN)
                ld      c,a                 ; C = the last column
                call    rl_vpeek
                cp      ' '
                jr      z,rsr_room
                ; --- grow the line by one row, below row B ---
                ld      hl,(CSRY)           ; [the cursor: CSRY low, CSRX high]
                push    hl
                ld      a,(CRTCNT)
                cp      b
                jr      z,rsr_scroll        ; the line ends on the bottom row
                ld      a,b
                inc     a
                ld      (CSRY),a            ; ESC L at the row below: C-BIOS inserts
                ld      a,27                ; a blank row there and moves the rows
                call    CHPUT               ; below it down (its chput_esc_ll) ...
                ld      a,'L'
                call    CHPUT
                ; ... but NOT their LINTTB entries: its update loads DE from
                ; `ld d,a / ld e,0` (CRTCNT * 256, not CRTCNT), so its lddr lands in
                ; page-0 ROM and the table never moves. Shift it here: rows B+1 ..
                ; CRTCNT-1 move to B+2 .. CRTCNT.
                ld      a,(CRTCNT)
                sub     b
                dec     a                   ; the rows to move: CRTCNT - (B+1)
                jr      z,rsr_marks         ; none: the new row is the bottom one
                ld      c,a
                push    bc
                ld      a,(CRTCNT)
                ld      e,a
                ld      d,0
                ld      hl,LINTTB-1
                add     hl,de               ; DE -> LINTTB[bottom row - 1]
                ld      d,h
                ld      e,l
                dec     hl                  ; HL -> the entry above it
                ld      b,0
                lddr
                pop     bc
rsr_marks:
                ld      hl,LINTTB-1
                ld      e,b
                ld      d,0
                add     hl,de
                ld      (hl),0              ; row B now continues ...
                inc     hl
                ld      (hl),1              ; ... onto the new row, which ends it
                pop     hl
rsr_again:
                ld      (CSRY),hl
                jr      rl_shift_right      ; again: the new row's last cell is blank
rsr_scroll:
                ; 📏 D-INSBOTTOM (measured 2026-09-26, scratchpad/insbottom_probe.py):
                ; the VG-8020 SCROLLS the screen up one row, and the line's spill
                ; lands on the freed bottom row, which continues the line. A LF on
                ; the bottom row scrolls; rl_scrolled then does exactly what a wrap
                ; that scrolled does in rl_echo (LINTTB's two stale entries, and
                ; the row where input began moves up).
                ld      a,b
                ld      (CSRY),a
                ld      a,10
                call    CHPUT
                call    rl_scrolled
                pop     hl
                dec     l                   ; the cursor moved up with the screen
                jr      rsr_again
rsr_room:
                ; (B,C) = the line's last cell; walk back to the cursor
rsr_lp:
                ld      a,(CSRY)
                cp      b
                jr      nz,rsr_move
                ld      a,(CSRX)
                cp      c
                ret     z                   ; reached the cursor: its cell is free
rsr_move:
                ld      d,b
                ld      e,c                 ; DE = the destination cell
                dec     c
                jr      nz,rsr_src
                dec     b                   ; column 0 -> the previous row's last
                ld      a,(LINLEN)
                ld      c,a
rsr_src:                                    ; BC = the source cell
                call    rl_vpeek            ; A = the cell before (BC, DE kept)
                push    bc
                ld      b,d
                ld      c,e
                call    rl_vpoke            ; destination := A
                pop     bc                  ; the source is the next destination
                jr      rsr_lp

; --- rl_shift_left: delete the cell at the cursor (DEL, and BS after a left) ----
; Every cell after the cursor moves one left; the logical line's last cell
; becomes a blank.
rl_shift_left:
                call    rl_lastrow
                ld      a,b
                ld      (RL_LAST),a         ; the last row (RL_LAST is Enter's, free here)
                ld      a,(CSRY)
                ld      b,a
                ld      a,(CSRX)
                ld      c,a                 ; (B,C) = the cursor
rsl_lp:
                ld      a,(RL_LAST)
                cp      b
                jr      nz,rsl_move
                ld      a,(LINLEN)
                cp      c
                jr      nz,rsl_move
                ld      a,' '               ; the last cell: now a blank
                jp      rl_vpoke
rsl_move:
                ld      d,b
                ld      e,c                 ; DE = the destination cell
                ld      a,(LINLEN)
                cp      c
                jr      nz,rsl_col
                inc     b                   ; past the row's end -> the next row's first
                ld      c,0
rsl_col:
                inc     c                   ; BC = the source cell
                call    rl_vpeek            ; A = the cell after (BC, DE kept)
                push    bc
                ld      b,d
                ld      c,e
                call    rl_vpoke            ; destination := A
                pop     bc                  ; the source is the next destination
                jr      rsl_lp
