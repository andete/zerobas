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
                call    stmt_bare_end       ; D-BAREEND: Z iff the statement ends here
                jr      z,clr_done
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
                ; 🔴 D-HIMDOM (docs/spec-basic-himdom.md): THIS WAS
                ; `call eval_int16_checked` FOR ONE HOUR AND IT WAS THE WRONG
                ; LEAF. That routine's `get_int16_checked` stage raises ERR 6 for
                ; |x| > 32767, and D-CLRFIX justified it with `CLEAR 200,70000`
                ; -> ERR 6 on both references. **70000 is rejected under BOTH
                ; candidate rules**, so the row could not separate a SIGNED int16
                ; from the MSX ADDRESS domain -- and `&HD000` passed only because
                ; MSX BASIC reads a hex literal >= &H8000 as NEGATIVE (-12288),
                ; so |x| <= 32767 by accident. A DECIMAL in [32768, 65535] is the
                ; discriminator and no row had one:
                ;
                ;   CLEAR 200,50000   both references: ACCEPTED, HIMEM = 50000
                ;   CLEAR 200,40000   both references: ACCEPTED, HIMEM = 40000
                ;
                ; Rows d.50000 / d.40000. The coercion is the ADDRESS domain,
                ; -32768..65535, which is exactly what basic/poke.asm's argument
                ; parse already uses. `&HFFFF` and `-1` answer identically on
                ; both references, so the rule is the VALUE and not the syntax.
                ; ⚠️ eval_addr DEFERS (it sets FPERR and returns -- do_poke tests
                ; it by hand for the same reason), so check_expr_errors is a
                ; SEPARATE call here. It preserves DE and raises before the store
                ; and before clr_done falls into clear_vars, which is the whole
                ; point of D-CLRFIX and is unchanged.
                ; 🔴 D-HIMRANGE (docs/spec-basic-himrange.md): THE *RANGE* CHECK
                ; D-HIMDOM filed, now implemented. Measured on the VG-8020 AND
                ; the CF-3300 (both agree on every row, scratchpad/himdom_probe.py):
                ;   value >= 65536         -> ERR 6 (eval_addr sets FPERR=1 below)
                ;   value >  $F380 (62336) -> ERR 5 (above the top of RAM)
                ;   value <  $8000         -> ERR 5 (below RAM, in ROM)
                ;   $8000 <= value < floor -> ERR 7 (no room for prog + strings)
                ;   floor <= value <= $F380-> accepted, HIMEM moves
                ; floor = PRGEND + POOLSIZE + CLR_HIMEM_MARGIN -- it tracks the
                ; program TEXT (PRGEND) and the requested string space (POOLSIZE,
                ; stored by the string-space arm above BEFORE we get here), as the
                ; reference does; variables do NOT count because CLEAR wipes them
                ; (rows p.dim*).
                ; ⚠️ THE UPPER EDGE IS A CONSTANT $F380 ON BOTH MACHINES despite
                ; boot HIMEMs of 62336 (VG) vs 56951 (CF): raising the ceiling
                ; back up works (row t.4to6), so the check reads a FIXED top, not
                ; live HIMEM -- which REFUTES D-HIMDOM §5's machine-specific guess
                ; and is why zerobas needs no boot-time HIMEM init.
                ; 🔴 NOT the pool arm's `bit 7,d` sign test: &H9000 has bit 15 set
                ; exactly as -1 does yet is ACCEPTED on all three -- the domain is
                ; a RANGE, not a sign (docs/spec-basic-clrfix.md STILL OPEN note).
                call    eval_addr           ; DE = -32768..65535, FPERR=1 past it
                ld      a,(FPERR)
                or      a
                jr      nz,clr_h_store      ; >=65536 overflow already pending -> ERR 6;
                                            ; skip the range check (DE is 0 here anyway)
                                            ; and HL is still the statement cursor.
                push    hl                  ; guard the cursor across the arithmetic
                ld      hl,CLR_HIMEM_TOP    ; value > $F380 -> ERR 5
                or      a
                sbc     hl,de
                jr      c,clr_h_ill
                ld      hl,$7FFF            ; value <= $7FFF (< $8000) -> ERR 5
                or      a
                sbc     hl,de
                jr      nc,clr_h_ill
                ld      hl,(PRGEND)         ; floor = PRGEND + POOLSIZE + margin
                ld      bc,(POOLSIZE)
                add     hl,bc
                ld      bc,CLR_HIMEM_MARGIN
                add     hl,bc
                or      a
                sbc     hl,de               ; floor - value
                jr      c,clr_h_ok          ; value > floor  -> accepted
                jr      z,clr_h_ok          ; value == floor -> accepted
                ld      a,6                 ; value < floor -> ERR 7 Out of memory
                jr      clr_h_set           ; (fperr_to_err[6] = 7)
clr_h_ill:
                ld      a,3                 ; ERR 5 Illegal function call
clr_h_set:                                  ; (fperr_to_err[3] = 5)
                call    penderr_set         ; preserves DE and the pushed cursor
clr_h_ok:
                pop     hl                  ; restore the statement cursor
clr_h_store:
                call    check_expr_errors   ; raise BEFORE the store and the wipe
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
