; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — errtrap.asm  (scan_stmt_end: RESUME NEXT's statement-advance)
; ===========================================================================
; error-handling S2b (docs/spec-basic-error-handling-s2b-packet.md §5.5):
; RESUME NEXT must advance from the erroring statement's own start (captured
; at trap time into ERRRESUME via SAVTXT, basic/interp.asm) to the NEXT
; statement -- either the next ':'-separated statement on the SAME line, or
; (if the erroring statement ran to end-of-line) the following line.
;
; WHY A SUB-ROM TENANT. The full QUOTE-AWARE scan (skip a $22 string literal
; so an embedded ':' is not a false statement separator; REM/DATA/ELSE/"'"
; tokens consume to EOL) did not fit main-ROM page-1's measured budget once
; the rest of S2b (trap branch, SAVSTK, ex_resume's other three forms) had
; already landed there. docs/subrom-tenant-playbook.md §3A classifies this as
; a PURE-LEAF tenant: it walks only the tokenised program TEXT, which lives
; in program RAM (pages 2/3), always visible from any sub-ROM page, and it
; calls NOTHING in main page-0/page-1. So the page choice is moot; it lands
; on the PAGE-1 island (sub_p1_table) alongside the math pack / format_tenant,
; needing no resident-ABI import (an empty leaf-audit, same shape as fp_rnd).
;
; ABI (docs/subrom-tenant-playbook.md §4): args/result marshalled through RAM
; (SSE_IN/SSE_OUT/SSE_EOL, basic/sysvars.inc -- aliased over the tape-CSAVE/
; CALL-FORMAT scratch window, the same collision-checked-reuse pattern those
; two already use: RESUME NEXT, a tape CSAVE/BSAVE, and CALL FORMAT never run
; at the same instant). Not through registers: CALSLT does not reliably
; preserve A across the call (the math-pack-subrom-tenant lesson), and this
; scanner's result is a 2-byte pointer PLUS a 1-byte disposition, too wide for
; a register-only return, so both directions go through RAM.
;
; in:  SSE_IN = the erroring statement's own start pointer (a SAVTXT/
;      ERRRESUME value: tokenised program-text RAM, never BIOS/low-region).
; out: SSE_EOL = 0 and SSE_OUT = the next statement's start (just past a
;      COLON, same line); SSE_EOL = 1 if the erroring statement ran to
;      end-of-line (SSE_OUT undefined -- the caller re-derives the next LINE
;      itself via the erroring line's own link field, res_next_eol in
;      basic/interp.asm). Clobbers A, HL (sub-side only; the caller relies on
;      nothing surviving back through subrom_call/CALSLT except the RAM cells
;      above -- see the math-pack-subrom-tenant lesson on A specifically).
;
; CLEAN-ROOM: original code; the quote-aware string-literal skip and the
; REM/DATA/ELSE consume-to-EOL statement shape are drawn from the published
; MSX-BASIC language reference's own statement grammar (allowed-source), not
; any disassembly. See sub/PROVENANCE.md.
; ===========================================================================

; --- scan_stmt_end: SUBROM_IDX_SCANSTMT entry -------------------------------
scan_stmt_end:
                ld      hl,(SSE_IN)
sse_lp:
                ld      a,(hl)
                or      a
                jr      z,sse_eol
                cp      COLON
                jr      z,sse_colon
                cp      $22                 ; string literal open
                jr      z,sse_string
                cp      REM_TOKEN
                jr      z,sse_toeol
                cp      DATA_TOKEN
                jr      z,sse_toeol
                cp      ELSE_TOKEN
                jr      z,sse_toeol
                inc     hl
                jr      sse_lp
sse_string:                                ; skip to the closing quote (or EOL if
                inc     hl                  ; the literal is left unterminated)
sse_str_lp:
                ld      a,(hl)
                or      a
                jr      z,sse_eol
                cp      $22
                jr      z,sse_str_close
                inc     hl
                jr      sse_str_lp
sse_str_close:
                inc     hl                  ; past the closing quote
                jr      sse_lp
sse_toeol:                                  ; REM/DATA/ELSE -- consume verbatim to EOL
                ld      a,(hl)
                or      a
                jr      z,sse_eol
                inc     hl
                jr      sse_toeol
sse_colon:
                inc     hl                  ; HL -> the next statement
                ld      (SSE_OUT),hl
                xor     a
                ld      (SSE_EOL),a
                ret
sse_eol:
                ld      a,1
                ld      (SSE_EOL),a
                ret
