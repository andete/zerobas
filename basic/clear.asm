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
; not just resizes the heap.
;
; zerobas's memory model is deliberately minimal: there is NO string heap, and
; the RAM layout is fixed (variables live in VARTAB; BLOAD loads to fixed
; regions per sysvars.inc). So:
;   - the <string-space> argument is accepted and evaluated, then ignored —
;     there is no heap to size yet; and
;   - the <memory-top> argument is recorded in the documented HIMEM sysvar
;     ($FC4A), CLEAR's real home for the ceiling, so it is honoured as far as
;     the current model allows.
;     🔴 THE SENTENCE THAT USED TO FOLLOW HERE IS FALSE AND IS INVERTED, NOT
;     DELETED (D-CLRFIX, 2026-08-23). It said: "No allocator consults HIMEM yet,
;     so this is record-only today; a future string heap / variable mover would
;     read it." HIMEM IS CONSULTED, AND BY CLEAR ITSELF: basic/str-engine.asm
;     heap_reset -- called from clear_vars, which clr_done calls two lines below
;     -- computes FRETOP := min(HIMEM,TXTMAX), and the string pool's floor is
;     derived sub-side from the same figure. MEASURED, not argued: row q.commak
;     (`CLEAR ,200:A=1`) answered `Out of memory`, because writing 200 into
;     HIMEM and then wiping the variables leaves no heap for the very next
;     assignment. A comment saying a store is inert is the kind that stops
;     anyone auditing the store.
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
; still read variables), then everything is wiped.
ex_clear:
                inc     hl                  ; past the CLEAR token
                call    skip_spaces
                or      a
                jr      z,clr_done          ; bare CLEAR (end of line)
                cp      COLON
                jr      z,clr_done          ; bare CLEAR before ':'
                ; 🔴 D-CLRFIX (docs/spec-basic-clrfix.md). THE TWO LINES THAT USED
                ; TO STAND HERE ARE DELETED, AND THIS IS A CARVE, NOT A COST:
                ;
                ;     cp   ','               ; "CLEAR ,himem" -- string-space omitted
                ;     jr   z,clr_himem
                ;
                ; `CLEAR ,200` and `CLEAR ,&HD000` are **Syntax error on the
                ; VG-8020 AND the CF-3300** (rows q.comma / z.hd000) and completed
                ; SILENTLY here, having written HIMEM on the way (h.comma:
                ; `->200`). The form is not MSX BASIC. Without the special case a
                ; leading comma reaches eval_int16_checked, ev_f_empty sets the
                ; deferred FPERR=4, and that routine's OWN check_expr_errors
                ; raises it as ERR 2 at ex_clear's depth -- before POOLSIZE is
                ; stored and before clear_vars can eat the ON ERROR trap. The
                ; error the references give, for free, out of machinery already
                ; present. -4 B.
                ; ⚠️ THE ROWS IN docs/clearpool-vg8020-characterization.md §2.4 /
                ; §2.8 THAT USE THIS FORM ARE VACUOUS AND ARE ANNOTATED THERE, NOT
                ; DELETED: `CLEAR 500 : CLEAR ,&HD000` reads 500 on the reference
                ; because the second statement NEVER RAN (z.seq: `UNTRAPPED Syntax
                ; error in 30` on both references -- untrapped because the first
                ; CLEAR had already killed the handler, D-CLRTRAP §3.1).
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
                ; D-EVALCHK (docs/spec-basic-evalchk.md): the THIRD verbatim copy
                ; of `call eval` / inline TMISMATCH test / checked coercion, now
                ; one 3-byte call. 13 B -> 3 B, and -- as at ex_width -- the
                ; inline shape ran the check AFTER the coercion, so
                ; `CLEAR 70000+0*(1/0)` answered Overflow where both references
                ; answer Division by zero. `CLEAR "200"` -> Type mismatch and
                ; the Overflow-past-int16 stage are unchanged.
                ; ⚠️ THE int16 ENTRY POINT, NOT THE BYTE ONE: `CLEAR 500` is
                ; accepted on both references (probe row cl-500), so narrowing
                ; this to eval_byte_checked would be a regression -- which is
                ; exactly what knife K-EV3 cuts.
                call    eval_int16_checked  ; DE = int16, or aborts
                bit     7,d                 ; the sign bit, tested in place: 2 B
                jp      nz,gb_illegal       ; against `ld a,d`/`rla`/`jr c` + a
                                            ; local `jp` (7 B). Negative -> ERR 5.
                ld      (POOLSIZE),de       ; the pool floor is derived sub-side
    ELSE
                call    eval                ; <string-space>, evaluated and ignored
    ENDIF
                call    skip_spaces
                cp      ','                 ; a second (memory-top) arg?
                jr      nz,clr_done         ; no comma -> done
clr_himem:
                ; ⚠️ REACHED BY FALLTHROUGH ONLY since D-CLRFIX deleted its one
                ; incoming jump (the leading-comma arm above). `jr nz,clr_done`
                ; three lines up is the only way in.
                inc     hl                  ; past the comma
                call    skip_spaces
                ; 🔴 D-CLRFIX: `call eval` STOOD HERE WITH NO CHECK OF ANY KIND,
                ; and the slot deferred EVERY fault code -- 24 (`CLEAR 200,`),
                ; 11 (`,1/0`), 13 (`,"x"`) -- storing DE anyway, falling into
                ; clr_done -> clear_vars, and aborting into a machine whose ON
                ; ERROR trap the wipe had just eaten. All three are trapped on
                ; both references, and all three WROTE here (h.trail / h.div /
                ; h.str, HIMEM `->0`). It also had NO int16 coercion, so
                ; `CLEAR 200,70000` completed where both references answer
                ; ERR 6 (q.ovf) after truncating 70000 to 4464.
                ; 🎯 ONE 3-BYTE CALL FOR THREE FIXES, AT ZERO BYTES:
                ; eval_int16_checked IS `eval` + `check_expr_errors` +
                ; `get_int16_checked`. HL (cursor) and DE (value) survive and its
                ; interposed frame is SP-safe -- see its own header.
                ; ⚠️ `&H9000` is -28672 as a signed int16, so |x| <= 32767 and the
                ; ACCEPTED ceiling still passes: row h.set is `->36864` on all
                ; three machines, and it is the control this change could break.
                ; 🔴 STILL OPEN, AND NOT A SIGN TEST: `CLEAR 200,-1` is ERR 5 on
                ; both references and completes here. The pool argument below
                ; rejects negatives with `bit 7,d`, and that test is WRONG for
                ; HIMEM -- `&H9000` has bit 15 set too and is accepted. The domain
                ; is a RANGE with unmeasured edges; filed in TODO.md.
                call    eval_int16_checked  ; DE = int16, or aborts (ERR 2/6/11/13)
                ld      (HIMEM),de          ; record CLEAR's ceiling
clr_done:
                push    hl                  ; clear_vars clobbers HL; guard the
                call    clear_vars          ; statement cursor across the wipe
                call    vars_reset          ; arrays slice-1 (§9.6) + slice-4b (§3b):
                                            ; CLEAR wipes any live scalars/arrays too;
                                            ; PRGEND is already valid here (a program
                                            ; may already exist)
                pop     hl
                jp      exec_stmt           ; HL = cursor; run the next statement
