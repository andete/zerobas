; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause

; clear.asm — the CLEAR statement handler.
;
;   CLEAR [<string-space>][,<memory-top>]
;
; MSX-BASIC's CLEAR sets the size of the string heap and the highest address
; BASIC may use (HIMEM). Both arguments are optional and comma-separated, and a
; bare `CLEAR` is valid. Nearly every game-loader `.BAS` stub does
; `CLEAR <strings>,&Hxxxx` to drop the memory ceiling before `BLOAD"…",R`, so
; reaching BLOAD requires CLEAR to parse the full syntax without raising a
; `syntax error`.
;
; zerobas's memory model is deliberately minimal: there is NO string heap, and
; the RAM layout is fixed (variables live in VARTAB; BLOAD loads to fixed
; regions per sysvars.inc). So:
;   - the <string-space> argument is accepted and evaluated, then ignored —
;     there is no heap to size yet; and
;   - the <memory-top> argument is recorded in the documented HIMEM sysvar
;     ($FC4A), CLEAR's real home for the ceiling, so it is honoured as far as
;     the current model allows. No allocator consults HIMEM yet, so this is
;     record-only today; a future string heap / variable mover would read it.
; Each argument still passes through `eval`, so a genuinely malformed expression
; is not silently swallowed, and any trailing garbage after the statement falls
; through to `stmt_error` via the normal `exec_stmt` dispatch.
;
; Clean-room: original code. CLEAR *semantics* (string space + memory ceiling)
; from the public MSX-BASIC language reference; the CLEAR token ($92) is from the
; MSX2 Technical Handbook Table 2.20 and HIMEM ($FC4A) from the C-BIOS system
; variables (see sysvars.inc / PROVENANCE.md). No disassembly.
;
; Entry: ex_clear, HL -> the CLEAR token. On success continues the statement
; loop (`jp exec_stmt`), so `CLEAR …:SCREEN n:BLOAD …` chains on one line.

ex_clear:
                inc     hl                  ; past the CLEAR token
                call    skip_spaces
                ld      a,(hl)
                or      a
                jp      z,exec_stmt         ; bare CLEAR (end of line)
                cp      COLON
                jp      z,exec_stmt         ; bare CLEAR before ':'
                cp      ','                 ; "CLEAR ,himem" — string-space omitted
                jr      z,clr_himem
                call    eval                ; <string-space> (evaluated, ignored)
                call    skip_spaces
                ld      a,(hl)
                cp      ','                 ; a second (memory-top) arg?
                jp      nz,exec_stmt        ; no comma -> done
clr_himem:
                inc     hl                  ; past the comma
                call    skip_spaces
                call    eval                ; DE = memory-top value
                ld      (HIMEM),de          ; record CLEAR's ceiling (record-only)
                jp      exec_stmt           ; HL = cursor; run the next statement
