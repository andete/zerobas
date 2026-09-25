; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — detok.asm  (the DETOKENISER CORE; WAVE 3 tenant)
; ===========================================================================
; The LIST / ASCII-SAVE detokeniser body, evicted from the repack main ROM's
; basic/list.asm into sub-ROM PAGE 0 (docs/spec-basic-subrom-wave3-detok.md).
;
; WHY SUB-SIDE. detok is COLD (LIST / ASCII SAVE are peripheral verbs) and — once
; its I/O is factored out — PURE COMPUTATION over page-2/3 RAM, so it is a valid
; page-0 tenant run under DI. The leaf-audit (spec §0.1) found NO BIOS reach in any
; dt_* path: the only external symbols were `pchar` (the I/O sink), `print_string`
; (a pchar loop) and `div10` (pure compute). This file re-binds those three so the
; SHARED body (basic/detok.inc, the shared detok body) appends
; into DETOKBUF instead of streaming to the screen/file:
;   * pchar        -> db_putc  : append A to DETOKBUF (the "drain" now lives resident)
;   * print_string -> a DETOKBUF-append of a 0-terminated NUMBUF string
;   * div10        -> a byte-identical own-design clone (pure, 16-bit shift/subtract)
;   * kwtable      -> the co-located sub copy (shared with the wave-2 tokeniser; the
;                     resident kwtable is now DROPPED — both readers are sub-side, §2)
; The resident side (basic/list.asm `detok`) CALSLTs dtk_tenant once per line, then
; drains DETOKBUF through the REAL pchar, honouring PRDEST — so this one core still
; feeds both LIST->screen and ASCII-SAVE->disk.
;
; RAM: DETOKBUF ($BE00, 512 B) + DB_CUR ($F108, the write cursor) are shared
; sysvars.inc equates, so their addresses are byte-identical main/sub — no
; marshalling. The worst-case line is <=475 B (source cap 96; only `?`->PRINT
; expands, spec §0.2), so the 512 B buffer never overflows and no bound check is
; needed (matching the original streaming detok, which had none).
;
; CLEAN-ROOM: original code (copied verbatim from our own basic/list.asm via the
; shared detok.inc); div10 is our own basic/print.asm routine. No disassembly.
; ===========================================================================

; --- dtk_tenant: the SUBROM_IDX_DETOK entry (in: HL = token body pointer) ---
; Reset the buffer cursor, run the shared core (which appends every rendered byte
; to DETOKBUF via the local pchar below), then 0-terminate the buffer so the
; resident drain (list.asm) can stream it through print_string. CALSLT returns to
; the caller with page 0 restored.
dtk_tenant:
                call    db_begin            ; cursor -> DB_WIN, DB_MORE = 0; DB_SKIP
                                            ; is the resident loop's (D-DETOKBUF)
                ld      a,1
                ld      (DB_RESUME),a       ; LIST may abort + resume at a token
                ld      (DB_SP),sp          ; the SP pchar aborts back to
                call    detok               ; render the line through the window
dtk_end:
                ld      hl,(DB_CUR)
                ld      (hl),0              ; 0-terminate for the resident drain
                ret

; --- pchar (sub-local re-bind): append A to DETOKBUF ------------------------
; The shared detok.inc issues `call pchar` at every emit site; here that means
; "append the byte to the buffer" instead of "send it to the PRDEST sink". Like
; the resident pchar it PRESERVES EVERY REGISTER, so the body needs no other
; change. No overflow check (the buffer is sized for the worst case, header).
; 🪟 D-DETOKBUF S1: WINDOWED. The first DB_SKIP bytes are discarded, the next
; DB_WINSZ-1 are stored, and one past that sets DB_MORE instead of being
; stored -- so a re-runnable renderer can be driven window by window from the
; resident side and a 96 B buffer serves a 1271-char line. Every register and
; flag is still preserved. (The window sits in one page: sysvars.inc asserts
; it, and the bound test compares the low byte only.)
pchar:
                push    hl
                push    af
                ld      hl,(DT_TOKN)
                inc     hl
                ld      (DT_TOKN),hl        ; this token's output so far (resume skip)
                ld      hl,(DB_SKIP)
                ld      a,h
                or      l
                jr      nz,pc_skip          ; still before the window
                ld      hl,(DB_CUR)
                ld      a,l
                cp      low(DB_WIN + DB_WINSZ - 1)
                jr      nc,pc_full          ; past the window (last byte: the NUL)
                pop     af
                ld      (hl),a
                inc     hl
                ld      (DB_CUR),hl
                pop     hl
                ret
pc_skip:
                dec     hl
                ld      (DB_SKIP),hl
                jr      pc_out
pc_full:
                ld      a,(DB_RESUME)
                or      a
                jr      z,pc_more           ; KEY LIST: just flag (skip-from-start)
                ld      hl,(DT_TOK)         ; LIST: resume at this token, skipping
                ld      (DB_RESPTR),hl      ; the bytes of it already drained --
                ld      hl,(DT_TOKN)        ; DT_TOKN counted THIS byte, which was
                dec     hl                  ; not stored
                ld      (DB_RESSKIP),hl
                ld      a,1
                ld      (DB_MORE),a
                ld      sp,(DB_SP)          ; ABORT the render: the rest of the
                jp      dtk_end             ; line is the next window's
pc_more:
                ld      a,1
                ld      (DB_MORE),a
pc_out:
                pop     af
                pop     hl
                ret
; db_begin -- a renderer's entry: cursor at the window, DB_MORE clear.
;   out: DE = DB_WIN, A = 0. 🔴 HL IS PRESERVED, AND THE FIRST CUT DID NOT:
;   dtk_tenant's HL is the TOKEN BODY, and a db_begin that left HL = DB_WIN had
;   detok render an empty window -- every LIST line blank in test_list, the
;   helper-borrowed-the-caller's-register class, again.
; db_begin0 -- the same for a renderer that is NEVER re-run (PRINT USING): also
;   DB_SKIP = 0, so a stale skip from an earlier LIST can never eat its output.
db_begin0:
                push    hl
                ld      hl,0
                ld      (DB_SKIP),hl
                pop     hl
db_begin:
                xor     a
                ld      (DB_MORE),a
                ld      (DB_RESUME),a       ; not resumable unless the tenant says so
                ld      de,DB_WIN
                ld      (DB_CUR),de
                ret

; --- print_string (sub-local re-bind): append 0-terminated (HL) to DETOKBUF -
; The number renderers (ln_div_entry / detok_hex16 / detok_oct16) build their text
; into NUMBUF and tail `jp print_string`; here that appends NUMBUF to DETOKBUF and
; returns to the renderer's caller, exactly as the resident print_string would have
; drained NUMBUF to the sink. Walks A/HL only, so BC/DE survive (the local pchar
; preserves all).
print_string:
                ld      a,(hl)
                or      a
                ret     z
                call    pchar
                inc     hl
                jr      print_string

; --- div10 (sub-local clone of basic/print.asm div10) ----------------------
; HL = HL/10, A = remainder (0..9). Shift-and-subtract. Byte-identical own-design
; clone; the resident copy in print.asm (page 1) is invisible to a page-0 tenant.
; Used by ln_div_entry (decimal token rendering). Clobbers A, B, HL.
div10:
                xor     a
                ld      b,16
sd10_lp:
                add     hl,hl
                rla
                cp      10
                jr      c,sd10_skip
                sub     10
                inc     l
sd10_skip:
                djnz    sd10_lp
                ret

; --- the shared detok body (the shared detok body) -----
; Binds pchar/print_string/div10 (above), kwtable (the co-located sub copy), and
; NUMBUF (shared RAM) from this assembly. Defines detok/dt_*/detok_op/detok_kw*/
; the number renderers + ln_div_entry.
                include "basic/detok.inc"
