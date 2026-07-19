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
; ABI (docs/subrom-tenant-playbook.md §4): the result is marshalled through
; RAM (SSE_OUT, basic/sysvars.inc -- aliased over the tape-CSAVE/CALL-FORMAT
; scratch window, the same collision-checked-reuse pattern those two already
; use: RESUME NEXT, a tape CSAVE/BSAVE, and CALL FORMAT never run at the same
; instant). Not through registers: CALSLT does not reliably preserve A across
; the call (the math-pack-subrom-tenant lesson), so the result goes through
; RAM, not A -- and it collapses to a PLAIN POINTER, no separate disposition
; byte: $0000 doubles as the one failure sentinel (a real statement/line
; pointer is never $0000), so one RAM cell carries the whole result. The
; INPUT needs no dedicated cell at all: this entry ALSO does the ONEFLG/
; CURLINE prep that RESUME's other three forms get from the main-side
; res_ctx (basic/interp.asm) -- ONEFLG and CURLINE are plain RAM, always
; visible sub-side (docs/subrom-tenant-playbook.md §2), and this entry reads
; ERRRESUME for its own input anyway, so absorbing the prep here (free --
; the sub-ROM has room) means the RESUME-NEXT main-side stub does not need
; to `call res_ctx` at all, one fewer page-1 call site.
;
; in:  ERRRESUME (RAM, set by the trap capture at basic/interp.asm
;      raise_error): [0..1] = the erroring line's own CURLINE value, [2..3] =
;      the erroring statement's own start pointer (a SAVTXT value: tokenised
;      program-text RAM, never BIOS/low-region).
; out: SSE_OUT<>0 is the correct resume pointer, with CURLINE already correct
;      too -- either the next statement just past a COLON on the SAME line
;      (CURLINE untouched), or (if the erroring statement ran to end-of-line)
;      the FOLLOWING line's first statement, in which case THIS tenant does
;      the CURLINE advance itself (CURLINE is plain RAM, always visible from
;      either sub-ROM page, docs/subrom-tenant-playbook.md §2 -- no need to
;      hand that arithmetic back to main). This collapses what would
;      otherwise be two different main-side cases into one: after a
;      successful call, the main stub always just does `ld hl,(SSE_OUT)` and
;      treats a nonzero result as the resume pointer.
;      SSE_OUT=0 is the one case the tenant CANNOT resolve on its own: the
;      erroring line's own link field was $0000 (the program ends there,
;      nothing to resume to -- degenerate; no ERR-21 site this slice,
;      err_msgtab's own comment) -- the main stub reports "Undefined line
;      number" (reusing GOTO's own path).
;      Clobbers A, HL (sub-side only; the caller relies on nothing surviving
;      back through subrom_call/CALSLT except the RAM cell above -- see the
;      math-pack-subrom-tenant lesson on A specifically).
;
; CLEAN-ROOM: original code; the quote-aware string-literal skip and the
; REM/DATA/ELSE consume-to-EOL statement shape are drawn from the published
; MSX-BASIC language reference's own statement grammar (allowed-source), not
; any disassembly. See sub/PROVENANCE.md.
; ===========================================================================

; --- scan_stmt_end: SUBROM_IDX_SCANSTMT entry -------------------------------
scan_stmt_end:
                xor     a
                ld      (ONEFLG),a          ; leaving the handler (RESUME NEXT commits)
                ld      hl,(ERRRESUME)
                ld      (CURLINE),hl        ; restore the erroring line (sse_eol below
                                            ; reads this back to find the NEXT line)
                ld      hl,(ERRRESUME+2)    ; the erroring statement's own start
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
                inc     hl                  ; HL -> the next statement (same line)
                ld      (SSE_OUT),hl
                ret
sse_eol:                                    ; erroring statement ran to end-of-line ->
                                            ; advance CURLINE to the FOLLOWING line and
                                            ; hand back ITS first statement (CURLINE is
                                            ; plain RAM -- the header's whole point)
                ld      hl,(CURLINE)        ; the erroring line's own link field
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = link to the next line
                ex      de,hl               ; HL = next line's link-field address
                ld      a,h
                or      l
                jr      z,sse_degenerate    ; $0000 link -> nothing to resume to
                ld      (CURLINE),hl        ; advance CURLINE to the next line
                inc     hl
                inc     hl
                inc     hl
                inc     hl                  ; HL -> next line's token body
                ld      (SSE_OUT),hl
                ret
sse_degenerate:                            ; HL is already $0000 here (the failed
                                            ; link-field test above) -- the sentinel
                                            ; the main stub checks for
                ld      (SSE_OUT),hl
                ret
