; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; poke.asm — the POKE statement handler.
;
;   POKE addr,value
;
; Writes the low byte of `value` to memory address `addr`. Both are 16-bit
; integer expressions (see expr.asm). PEEK is the read counterpart and lives in
; the evaluator, not here.
;
; Clean-room: original code. POKE *semantics* (write one byte to an address)
; from the public MSX-BASIC language reference. No disassembly.
;
; Entry: do_poke, HL -> the bytes after the POKE token. On success continues the
; statement loop (jp exec_stmt), so `poke ...:poke ...` chains on one line.

do_poke:
    IF ROM_BASE < $4000
                call    eval_addr           ; spec §10.3: POKE's arguments are the
    ELSE                                    ; checked ADDRESS domain (FPERR on overflow),
                call    eval                ; not the silent eager conversion (D-F2-2)
    ENDIF                                   ; -- DE = address, HL = cursor
                push    de                  ; save address
                call    skip_spaces
                ld      a,(hl)
                cp      ','                 ; comma required
                jr      nz,poke_err
                inc     hl
    IF ROM_BASE < $4000
                call    eval_addr           ; DE = value, HL = cursor
    ELSE
                call    eval
    ENDIF
                pop     bc                  ; BC = address
    IF ROM_BASE < $4000
                ld      a,(FPERR)
                or      a
                jp      nz,fp_runtime_error
    ENDIF
                ld      a,e                 ; low byte of value
                ld      (bc),a              ; the POKE
                jp      exec_stmt           ; HL = cursor; run the next statement
poke_err:
                pop     bc                  ; discard saved address
                jp      stmt_error
