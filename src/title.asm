; title.asm — zerobas startup header.
;
; The few left-aligned lines printed at the top of the screen before the
; interpreter is ready — the same role as MSX-BASIC's "version / copyright /
; Bytes free" header that precedes its READ-EVAL prompt. The text is ORIGINAL
; to zerobas: no header text is copied from any reference ROM (which would be a
; clean-room violation and a false copyright claim). See PROVENANCE.md.
;
; Uses only documented BIOS entry points (INITXT, CHPUT); no disassembly.

show_title:
                call    INITXT          ; SCREEN 0 text mode + display on
                ld      hl,banner_text
st_loop:
                ld      a,(hl)
                or      a
                ret     z               ; 0x00 ends the header
                push    hl              ; guard HL across the BIOS call
                call    CHPUT
                pop     hl
                inc     hl
                jr      st_loop

; Left-aligned from the home position. 13/10 = CR/LF (CHPUT: 0x0D = start of
; line, 0x0A = next line). A trailing blank line separates the header from
; whatever the interpreter does next, as on a booted MSX.
banner_text:
                db      "zerobas version 0.1",13,10
                db      "clean-room MSX-BASIC cartridge loader",13,10,13,10
                db      0
