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
                ld      de,DETOKBUF
                ld      (DB_CUR),de         ; reset the DETOKBUF write cursor
                call    detok               ; render the whole line into DETOKBUF
                ld      hl,(DB_CUR)
                ld      (hl),0              ; 0-terminate for the resident drain
                ret

; --- pchar (sub-local re-bind): append A to DETOKBUF ------------------------
; The shared detok.inc issues `call pchar` at every emit site; here that means
; "append the byte to the buffer" instead of "send it to the PRDEST sink". Like
; the resident pchar it PRESERVES EVERY REGISTER, so the body needs no other
; change. No overflow check (the buffer is sized for the worst case, header).
pchar:
                push    hl
                push    af
                ld      hl,(DB_CUR)
                ld      (hl),a              ; A still holds the byte (push af didn't alter it)
                inc     hl
                ld      (DB_CUR),hl
                pop     af
                pop     hl
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
