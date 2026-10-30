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
; out: SSE_OUT = the resume pointer, CURLINE = the erroring line's -- either
;      the next statement just past a COLON on the SAME line, or (if the
;      erroring statement ran to end-of-line) that line's own $00, an empty
;      statement after which the run loop steps to the next line by its own
;      link walk, end of program and direct mode included. The main stub
;      always just does `ld hl,(SSE_OUT)`.
;      (D-RESNEXTDIRECT, 2026-10-30: this tenant used to do the end-of-line
;      advance itself and report $0000 for a "degenerate" case -- "the
;      erroring line's own link was $0000", which cannot happen -- while the
;      real end, the NEXT line being the end marker, went unhandled.)
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
                ld      (CURLINE),hl        ; restore the erroring line (the run loop
                                            ; steps on from it after an end-of-line)
                ld      hl,(ERRRESUME_TXT)    ; the erroring statement's own start
sse_lp:
                ld      a,(hl)
                or      a
                jr      z,sse_eol
                cp      COLON
                jr      z,sse_colon
                cp      REM_TOKEN
                jr      z,sse_toeol
                cp      DATA_TOKEN
                jr      z,sse_toeol
                cp      ELSE_TOKEN
                jr      z,sse_toeol
                ; 🔴 D-RESNEXTOVF (2026-10-09): ONE TOKEN AT A TIME, VALUE BYTES
                ; INCLUDED. This stepped one BYTE at a time, so a numeric
                ; constant's value read as text: `1E62` is 1D 7F 10 00 00, and its
                ; $00 ended the "line" -- RESUME NEXT after `PRINT 1E62*9:PRINT
                ; "A"` went to the NEXT line, skipping A (VG-8020: E 6 | A | B);
                ; 58 is 0F 3A, and that $3A resumed on the `*` (a second error).
                ; le_tok_skip (sub/lineedit.asm) is the stride skip_to_eol already
                ; walks with: every constant prefix's value bytes, $FF function
                ; tokens, and string literals (to the closing quote or the EOL
                ; $00, which the loop then reads). probes/basic/basic_probe_resnext.py.
                call    le_tok_skip
                jr      sse_lp
sse_toeol:                                  ; REM/DATA/ELSE -- consume verbatim to EOL
                ld      a,(hl)
                or      a
                jr      z,sse_eol
                inc     hl
                jr      sse_toeol
sse_colon:
                inc     hl                  ; HL -> the next statement (same line)
sse_eol:                                    ; (or HL on the line's own $00)
                ; 🔴 D-RESNEXTDIRECT (2026-10-30): AT END OF LINE, RESUME AT THE LINE'S
                ; OWN TERMINATOR AND LET THE RUN LOOP STEP TO THE NEXT LINE. This
                ; advanced CURLINE itself and handed back the next line's body --
                ; testing the ERRORING line's link for $0000, which a line that ran
                ; never has, and never the NEXT line's. After the LAST program line
                ; the next "line" is the end marker, and in direct mode it is
                ; dir_line's (basic/field.asm): both ran the bytes past it as
                ; statements, and the handler caught each error forever (`E 8 0` /
                ; `E 2 1800` ..., scratchpad/resnextlast_measure.out,
                ; resnextdirect_measure.out; the VG-8020 ends the run and says Ok).
                ; Resuming on the $00 is an empty statement: exec returns at once,
                ; the run loop follows CURLINE's link exactly as after any line, and
                ; the end marker ends the run its usual way (cont_record) -- one
                ; path, none of it here. CURLINE is already the erroring line's.
                ld      (SSE_OUT),hl
                ret
