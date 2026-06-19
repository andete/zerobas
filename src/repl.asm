; repl.asm — keyboard line editor + read/eval loop.
;
; Reads a line from the keyboard via the BIOS (CHGET), echoes it with simple
; editing (Backspace), and on Enter tokenises and executes it, then loops.
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
                ld      hl,LINEBUF
                ld      de,TOKBUF
                call    tokenise
                ld      hl,TOKBUF
                call    exec                ; may hand off (no return) or return
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
; Backspace ($08) and Enter ($0D); other control characters are ignored.
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
                cp      32                  ; ignore other control chars
                jr      c,rl_loop
                ld      b,a                 ; hold the char
                ld      a,l                 ; bounds: LINEBUF..LINEBUF+LINEMAX-1
                cp      (LINEBUF+LINEMAX) & $FF   ; single page $E0, low byte ok
                jr      nc,rl_loop          ; buffer full -> drop the char
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
