; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause

; repl.asm — keyboard line editor + read/eval loop.
;
; Reads a line from the keyboard via the BIOS (CHGET), echoes it with simple
; editing (Backspace/DEL), and on Enter hands the line to `dispatch_line`
; (store a numbered line, RUN, NEW, or tokenise+execute a direct line), then
; loops.
;
; The prompt is deliberately "zb>", NOT the original interpreter's "Ok": zerobas
; should never be mistaken for stock MSX-BASIC.
;
; Clean-room: this is an original line editor using only documented BIOS entry
; points (CHGET, CHPUT). No disassembly.

repl:
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
                push    hl                  ; guard HL across the BIOS call
                call    CHPUT
                pop     hl
                inc     hl
                jr      print_string

; --- read_line: edit a line into LINEBUF, echoing as we go -----------------
; Returns with LINEBUF holding the typed ASCII line, 0-terminated. Handles
; Backspace ($08), DEL ($7F), and Enter ($0D); other control characters are
; ignored. (openMSX maps the Mac Backspace key to the MSX DEL key, so C-BIOS's
; CHGET delivers $7F rather than $08 -- both are treated as erase-left here.)
; HL is the write cursor; it is guarded across every BIOS call (CHGET/CHPUT
; make no register guarantees).
read_line:
                ld      hl,LINEBUF
rl_loop:
                push    hl
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
rl_enter:
                ld      (hl),0              ; terminate the line
                ld      a,13                ; echo CR/LF
                call    CHPUT
                ld      a,10
                call    CHPUT
                ret

prompt_text:
                db      "zb>",0
