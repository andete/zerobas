; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; clear.asm — the CLEAR statement handler.
;
;   CLEAR [<string-space>][,<memory-top>]
;
; MSX-BASIC's CLEAR sets the size of the string heap and the highest address
; BASIC may use (HIMEM). Both arguments are optional and comma-separated, and a
; bare `CLEAR` is valid. Nearly every game-loader `.BAS` stub does
; `CLEAR <strings>,&Hxxxx` to drop the memory ceiling before `BLOAD"…",R`, so
; reaching BLOAD requires CLEAR to parse the full syntax without raising a
; `syntax error`.
;
; CLEAR also RESETS ALL VARIABLES (VARTAB, the string table, and the per-letter
; DEFtbl) — the MS-BASIC / MSX-BASIC semantics: CLEAR frees the variable space,
; not just resizes the heap. This wipe is gated to the repack build (see the
; ex_clear IF/ELSE below): the lean 16 KB basic.rom is byte-full at its $8000
; ceiling and has no typed vars / DEFtbl, so it keeps the original record-only
; exit and stays byte-identical.
;
; zerobas's memory model is deliberately minimal: there is NO string heap, and
; the RAM layout is fixed (variables live in VARTAB; BLOAD loads to fixed
; regions per sysvars.inc). So:
;   - the <string-space> argument is accepted and evaluated, then ignored —
;     there is no heap to size yet; and
;   - the <memory-top> argument is recorded in the documented HIMEM sysvar
;     ($FC4A), CLEAR's real home for the ceiling, so it is honoured as far as
;     the current model allows. No allocator consults HIMEM yet, so this is
;     record-only today; a future string heap / variable mover would read it.
; Each argument still passes through `eval`, so a genuinely malformed expression
; is not silently swallowed, and any trailing garbage after the statement falls
; through to `stmt_error` via the normal `exec_stmt` dispatch.
;
; Clean-room: original code. CLEAR *semantics* (string space + memory ceiling)
; from the public MSX-BASIC language reference; the CLEAR token ($92) is from the
; MSX2 Technical Handbook Table 2.20 and HIMEM ($FC4A) from the C-BIOS system
; variables (see sysvars.inc / PROVENANCE.md). No disassembly.
;
; Entry: ex_clear, HL -> the CLEAR token. On success continues the statement
; loop (`jp exec_stmt`), so `CLEAR …:SCREEN n:BLOAD …` chains on one line.

; The bare/argument parse is shared, but the exit differs by build. In the
; repack build CLEAR resets ALL variables (VARTAB / DEFtbl / strings), like NEW
; — MS-BASIC semantics; the argument expressions are evaluated first (they may
; still read variables), then everything is wiped. That wipe is gated to the
; repack build: the lean 16 KB basic.rom is byte-full at its $8000 ceiling AND
; has no typed vars / DEFtbl, so it keeps the original (record-only) exit and
; stays byte-identical.
    IF ROM_BASE < $4000
ex_clear:
                inc     hl                  ; past the CLEAR token
                call    skip_spaces
                ld      a,(hl)
                or      a
                jr      z,clr_done          ; bare CLEAR (end of line)
                cp      COLON
                jr      z,clr_done          ; bare CLEAR before ':'
                cp      ','                 ; "CLEAR ,himem" — string-space omitted
                jr      z,clr_himem
                call    eval                ; <string-space>
    IF CLEARPOOL
                ; --- D-CLP: the argument is RECORDED, and checked first ---------
                ; It used to be evaluated and thrown away, so `CLEAR -1`,
                ; `CLEAR 32768` and `CLEAR "200"` were all silently accepted where
                ; the reference raises (characterization §2.7). The rule is the
                ; two-stage int16 one every other numeric argument already uses --
                ; Overflow beyond int16 (raised by get_int16_checked itself),
                ; Illegal function call inside it -- plus a type check. Both
                ; rejects run at ex_clear's OWN depth (exec_stmt `jp`s here), so
                ; neither needs return-address parking.
                ld      a,(TMISMATCH)       ; `CLEAR "200"` -> Type mismatch
                or      a
                jp      nz,type_mismatch_error
                call    get_int16_checked   ; DE = int16, or aborts with Overflow
                bit     7,d                 ; the sign bit, tested in place: 2 B
                jp      nz,gb_illegal       ; against `ld a,d`/`rla`/`jr c` + a
                                            ; local `jp` (7 B). Negative -> ERR 5.
                ld      (POOLSIZE),de       ; heap_reset (below) derives POOLBASE
    ENDIF
                call    skip_spaces
                ld      a,(hl)
                cp      ','                 ; a second (memory-top) arg?
                jr      nz,clr_done         ; no comma -> done
clr_himem:
                inc     hl                  ; past the comma
                call    skip_spaces
                call    eval                ; DE = memory-top value
                ld      (HIMEM),de          ; record CLEAR's ceiling (record-only)
clr_done:
                push    hl                  ; clear_vars clobbers HL; guard the
                call    clear_vars          ; statement cursor across the wipe
                call    vars_reset          ; arrays slice-1 (§9.6) + slice-4b (§3b):
                                            ; CLEAR wipes any live scalars/arrays too;
                                            ; PRGEND is already valid here (a program
                                            ; may already exist)
                pop     hl
                jp      exec_stmt           ; HL = cursor; run the next statement
    ELSE
ex_clear:
                inc     hl                  ; past the CLEAR token
                call    skip_spaces
                ld      a,(hl)
                or      a
                jp      z,exec_stmt         ; bare CLEAR (end of line)
                cp      COLON
                jp      z,exec_stmt         ; bare CLEAR before ':'
                cp      ','                 ; "CLEAR ,himem" — string-space omitted
                jr      z,clr_himem
                call    eval                ; <string-space> (evaluated, ignored)
                call    skip_spaces
                ld      a,(hl)
                cp      ','                 ; a second (memory-top) arg?
                jp      nz,exec_stmt        ; no comma -> done
clr_himem:
                inc     hl                  ; past the comma
                call    skip_spaces
                call    eval                ; DE = memory-top value
                ld      (HIMEM),de          ; record CLEAR's ceiling (record-only)
                jp      exec_stmt           ; HL = cursor; run the next statement
    ENDIF
