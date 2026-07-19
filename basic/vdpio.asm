; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; vdpio.asm — the VPOKE and OUT statement handlers.
;
;   VPOKE addr,value   write one byte to VDP VRAM address `addr`
;   OUT   port,value   write one byte to Z80 I/O `port`
;
; Both take two 16-bit integer expressions and write the low byte of `value`.
; VPOKE addresses the VDP's video RAM through the BIOS (so the VRAM access
; protocol stays the BIOS's job); OUT issues a raw Z80 port write. These are the
; write halves; the read counterparts VPEEK / INP live in the expression
; evaluator (expr.asm), next to PEEK.
;
; Clean-room: original code, modelled on poke.asm's arg-parse. VPOKE / OUT
; *semantics* (write one byte to VRAM / to a port) from the public MSX-BASIC
; language reference; WRTVRM ($004D) is from the MSX Assembly Page / MSX2
; Technical Handbook (see sysvars.inc, PROVENANCE.md). No disassembly.
;
; Entry: do_vpoke / do_out, HL -> the bytes after the statement token. On success
; continue the statement loop (jp exec_stmt) so the verbs chain on one line.

; --- do_vpoke: VPOKE addr,value -------------------------------------------
; addr = VRAM address (full 16-bit, 0..&H3FFF used on TMS9918); value low byte.
do_vpoke:
    IF ROM_BASE < $4000
                call    eval                ; D-F2-2 stage B: VPOKE's address is the VRAM
                call    get_vram_arg        ; domain 0..16383 (NOT the 0..65535 address
                                            ; domain F2 wired) -- >int16 ERR 6, 16384.. ERR 5.
    ELSE                                    ; -- DE = checked VRAM address, HL = cursor
                call    eval                ; (lean: silent eager conversion)
    ENDIF
                push    de                  ; save address
                call    skip_spaces
                ld      a,(hl)
                cp      ','                 ; comma required
                jr      nz,vdp_err
                inc     hl
    IF ROM_BASE < $4000
                call    eval_addr           ; DE = value, HL = cursor
                pop     bc                  ; BC = VRAM address (popped BEFORE the check so
                                            ; the stack is SP-clean for check_fperr_only --
                                            ; same shape do_out now uses; an out-of-domain
                                            ; addr OR value -> Overflow abort, ERR 6)
                call    check_fperr_only
                ld      a,e                 ; A = low byte of value
                push    hl                  ; save the executor's cursor
    ELSE
                call    eval                ; DE = value, HL = cursor
                ld      a,e                 ; A = low byte of value
                pop     bc                  ; BC = VRAM address
                push    hl                  ; save the executor's cursor
    ENDIF
                ld      h,b
                ld      l,c                 ; HL = VRAM address (WRTVRM wants it here)
                call    WRTVRM              ; write A to VRAM[HL]
                pop     hl                  ; HL = cursor
                jp      exec_stmt           ; run the next statement

; --- do_out: OUT port,value -----------------------------------------------
; port = Z80 I/O port (BC = port for `out (c),a`), value low byte.
do_out:
    IF ROM_BASE < $4000
                call    eval_addr           ; D-F2-2 A1: OUT's port/value are the checked
    ELSE                                    ; ADDRESS domain (FPERR on overflow), not the
                call    eval                ; silent eager conversion -- mirrors POKE
    ENDIF                                   ; (basic/poke.asm). DE = port, HL = cursor
                push    de                  ; save port
                call    skip_spaces
                ld      a,(hl)
                cp      ','                 ; comma required
                jr      nz,vdp_err
                inc     hl
    IF ROM_BASE < $4000
                call    eval_addr           ; DE = value, HL = cursor
    ELSE
                call    eval
    ENDIF
                pop     bc                  ; BC = port (C = port number)
    IF ROM_BASE < $4000
                call    check_fperr_only    ; an out-of-domain port OR value (FPERR sticky
                                            ; across both eval_addr's, set-only) -> Overflow
                                            ; abort (ERR 6). Same SP-clean tail-jumped-driver
                                            ; shape as ex_if/ex_let: on abort it discards our
                                            ; dead resume addr; on OK it returns here. Lean
                                            ; keeps its own tail below (byte-identical); the
                                            ; guard push/pop hl around `out (c),a` there is
                                            ; dead (out preserves HL), so the repack tail
                                            ; simply omits it.
                ld      a,e                 ; A = low byte of value
                out     (c),a               ; raw Z80 port write
                jp      exec_stmt           ; HL still the cursor (out preserves it)
    ELSE
                push    hl                  ; guard the cursor across the port write
                ld      a,e                 ; A = low byte of value
                out     (c),a               ; raw Z80 port write
                pop     hl                  ; HL = cursor
                jp      exec_stmt           ; run the next statement
    ENDIF
vdp_err:
                pop     bc                  ; discard the saved address / port
                jp      stmt_error
