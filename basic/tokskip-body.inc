; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; tokskip-body.inc -- tok_skip, shared VERBATIM between the resident
; (basic/interp.asm, unchanged bytes) and the PAGE-0 sub-ROM tenant that needs it
; (sub/readdata.asm's data_seek). Extracted by the G7 eviction
; (docs/spec-eviction-g7-space.md) so the two copies can never drift: a token
; stride that is right in one page and stale in the other is exactly the class of
; bug the DATA scanner would hide (a float literal's $00 mantissa byte read as a
; line terminator). sub/lineedit.asm keeps its own page-1 copy under `le_`
; labels -- page 0 and page 1 are never mapped together, so each page needs one.

; --- tok_skip: advance HL past one token, including its operand bytes -------
tok_skip:
                ld      a,(hl)
                inc     hl
                cp      HEX_TOKEN           ; $0C ,word
                jr      z,tsk2
                cp      INT2_TOKEN          ; $1C ,word
                jr      z,tsk2
                cp      LINENO_TOKEN        ; $0E ,word
                jr      z,tsk2
                cp      LINEADDR_TOKEN      ; $0D ,word
                jr      z,tsk2
                cp      OCT_TOKEN           ; $0B ,word
                jr      z,tsk2
                cp      INT1_TOKEN          ; $0F ,byte
                jr      z,tsk1
                cp      PEEK_PREFIX         ; $FF ,function-token byte
                jr      z,tsk1
                cp      SNG_TOKEN           ; $1D ,4 float value bytes (repack only —
                jr      z,tsk4
                cp      DBL_TOKEN
                jr      z,tsk8              ; $1F ,8 float value bytes. A mantissa byte
                                            ; can be $00 (e.g. .5 -> 1D 40 50 00 00), so
                                            ; without this stride skip_to_eol/if_skip_to_
                                            ; else/data_seek mistake it for the line/stmt
                                            ; terminator -- a stored `10 A=1.5` never RUNs.
                cp      '"'                 ; string literal
                jr      z,tsk_str
                cp      REM_TOKEN           ; REM -> rest of line
                jr      z,tsk_rem
                cp      DATA_TOKEN          ; DATA -> verbatim body to ':' / EOL
                jr      z,tsk_data
                ret                         ; 0-operand token / plain byte
tsk1:
                inc     hl
                ret
tsk2:
                inc     hl
                inc     hl
                ret
tsk8:                                       ; DBL_TOKEN: 8 value bytes (4 here + 4 in tsk4)
                inc     hl
                inc     hl
                inc     hl
                inc     hl
tsk4:                                       ; SNG_TOKEN: 4 value bytes
                inc     hl
                inc     hl
                inc     hl
                inc     hl
                ret
tsk_str:
                ld      a,(hl)
                or      a
                ret     z
                inc     hl
                cp      '"'
                jr      nz,tsk_str
                ret
tsk_rem:
                ld      a,(hl)
                or      a
                ret     z
                inc     hl
                jr      tsk_rem
tsk_data:                                   ; DATA body: verbatim ASCII to ':' or EOL,
                ld      a,(hl)              ; left un-consumed (the ':' / 00 is stepped by
                or      a                   ; the caller's outer loop). Skipping the body
                ret     z                   ; as a unit means a stray control byte in it
                cp      COLON               ; can never be misread as an operand-bearing
                ret     z                   ; token — same end position as the old
                inc     hl                  ; byte-by-byte walk on valid printable DATA.
                jr      tsk_data

