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
                call    eval                ; D-F2-2 stage B: VPOKE's address is the VRAM
                call    get_vram_arg        ; domain 0..16383 (NOT the 0..65535 address
                                            ; domain F2 wired) -- >int16 ERR 6, 16384.. ERR 5.
                push    de                  ; save address
                call    skip_spaces
                cp      ','                 ; comma required
                jp     nz,vdp_err
                inc     hl
                call    eval_addr           ; DE = value, HL = cursor
                pop     bc                  ; BC = VRAM address (popped BEFORE the check so
                                            ; the stack is SP-clean for check_fperr_only --
                                            ; same shape do_out now uses; an out-of-domain
                                            ; addr OR value -> Overflow abort, ERR 6)
                call    check_fperr_only
                ld      a,e                 ; A = low byte of value
                push    hl                  ; save the executor's cursor
                ld      h,b
                ld      l,c                 ; HL = VRAM address (WRTVRM wants it here)
                call    WRTVRM              ; write A to VRAM[HL]
                pop     hl                  ; HL = cursor
                jp      exec_stmt           ; run the next statement

; --- do_out: OUT port,value -----------------------------------------------
; port = Z80 I/O port (BC = port for `out (c),a`), value low byte.
; --- ex_wait: WAIT port,mask[,xor] -------------------------------------------
; D-WAIT. Spin until `(INP(port) XOR xor) AND mask` is non-zero. The last MSX1
; MAIN-ROM statement zerobas did not have: `make kwsweep`'s crunch layer read
; `wait 0,0` back as the ASCII bytes 57 41 49 54 -- a VARIABLE named WAIT --
; where the reference stores the token $96.
; ⚠️ `mask = 0` NEVER terminates, on the reference too. That is the statement's
; documented behaviour and not a bug to guard: it is how WAIT is used to block on
; a hardware line. It is also why kwsweep lists WAIT crunch-only and never runs
; it, and why the acceptance rows below pick a mask that is satisfied at once.
; Register plan keeps the loop at SIX bytes: D = mask, E = xor, C = port.
;   in:  HL -> the WAIT token (the stmt_table contract, as for ex_out)
ex_wait:
                inc     hl                  ; past the token
                call    eval_addr           ; DE = port (checked, as OUT's is)
                push    de
                call    skip_spaces
                cp      ','                 ; the mask is NOT optional
                jp      nz,vdp_err
                inc     hl
                call    eval_addr           ; DE = mask
                ld      d,e                 ; D = mask
                ld      e,0                 ; E = xor, defaulted
                call    skip_spaces
                cp      ','
                jr      nz,wt_go            ; two-argument form
                inc     hl
                push    de                  ; guard mask+default across the eval
                call    eval_addr           ; DE = xor
                ld      a,e
                pop     de
                ld      e,a                 ; E = the given xor
wt_go:
                pop     bc                  ; BC = port (C = the port number)
                call    check_fperr_only    ; an out-of-domain port/mask/xor ->
                                            ; Overflow, exactly as do_out treats it
wt_lp:
                in      a,(c)
                xor     e
                and     d
                jr      z,wt_lp             ; still masked off -> keep waiting
                jp      exec_stmt           ; `in` preserves HL, so no guard is
                                            ; needed -- the do_out precedent below

do_out:
                call    eval_addr           ; D-F2-2 A1: OUT's port/value are the checked
                push    de                  ; save port
                call    skip_spaces
                cp      ','                 ; comma required
                jp     nz,vdp_err
                inc     hl
                call    eval_addr           ; DE = value, HL = cursor
                pop     bc                  ; BC = port (C = port number)
                call    check_fperr_only    ; an out-of-domain port OR value (FPERR sticky
                                            ; across both eval_addr's, set-only) -> Overflow
                                            ; abort (ERR 6). Same SP-clean tail-jumped-driver
                                            ; shape as ex_if/ex_let: on abort it discards our
                                            ; dead resume addr; on OK it returns here. The
                                            ; guard push/pop hl around `out (c),a` is
                                            ; dead (out preserves HL), so the repack tail
                                            ; simply omits it.
                ld      a,e                 ; A = low byte of value
                out     (c),a               ; raw Z80 port write
                jp      exec_stmt           ; HL still the cursor (out preserves it)
; D-DUPSPAN2: an ALIAS, not a second copy -- byte-identical to ex_let_err,
; and POSITION-INDEPENDENT by tools/dupspan_indep.py (terminates, no
; escaping relative jump, not entered by fallthrough, same ROM region).
; The NAME and every call site survive; un-alias here for a distinct face.
vdp_err         equ     ex_let_err
