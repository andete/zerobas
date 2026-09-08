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
                call    eval_addr           ; spec §10.3: POKE's arguments are the
                push    de                  ; save address
                call    skip_spaces
                cp      ','                 ; comma required
                jp     nz,poke_err
                inc     hl
                call    eval_byte_checked   ; DE = value 0..255, HL = cursor
                                            ; 🔴 D-RAWVAL: the VALUE is a BYTE, not an
                                            ; address. `eval_addr` applies the ADDRESS
                                            ; domain -- which WRAPS by design -- so
                                            ; `,256` wrote 0 and `,-1` wrote 255 with no
                                            ; error, where both references raise ERR 5
                                            ; and write nothing. `eval_byte_checked` is
                                            ; the same 3 bytes and already existed.
                                            ; 🎯 ORDER PRESERVED, AND MEASURED:
                                            ; its int16 stage runs check_fperr_only on
                                            ; the STICKY FPERR first, so `POKE 99999,256`
                                            ; stays ERR 6 (overflow beats domain) --
                                            ; the row nobody had, because every existing
                                            ; row pairs a bad address with a legal value.
                pop     bc                  ; BC = address
                call    check_fperr_only
                ld      a,e                 ; low byte of value
                ld      (bc),a              ; the POKE
                jp      exec_stmt           ; HL = cursor; run the next statement
; D-DUPSPAN2: an ALIAS, not a second copy -- byte-identical to ex_let_err,
; and POSITION-INDEPENDENT by tools/dupspan_indep.py (terminates, no
; escaping relative jump, not entered by fallthrough, same ROM region).
; The NAME and every call site survive; un-alias here for a distinct face.
poke_err        equ     ex_let_err
