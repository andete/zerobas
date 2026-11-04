; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
; trapstmt.asm -- main's LOW REGION: the event-trap STATEMENTS. ON STOP / SPRITE /
; STRIG / KEY / INTERVAL GOSUB, INTERVAL ON|OFF|STOP, STRIG(n) ON|OFF|STOP,
; KEY(n) ON|OFF|STOP. The trap MACHINERY -- the per-statement poll (check_traps),
; the ISR side, ZTRAP's helpers -- was always main's; only the statements that ARM
; it travelled.
;
; 🏗️ HISTORY. Main page 1 (basic/program.asm) until D-P0CB slice B (2026-10-21)
; moved them to zerobas-sub2 page 0 (sub2/trapstmt.asm, reached through ONE CALSLT
; per statement and calling main back through p0cb). D-SUB2RETIRE step 2c
; (2026-11-04, Joost: trapstmt goes "Into main (543 B low free)") brought them
; back -- into the LOW region, not page 1, which had the room: this file is
; included LAST in the low region (basic/main.asm), so no existing label moves.
; The code is sub2's after D-SUB2RETIRE step 2b's reread, with every crossing
; undone: `ld ix,p0_X / call p0cb` is `call X`, the sub2-local s2_skip_* leaves
; are main's skip_spaces / skip_comma, and the `ld de,p0_X / ret` continuation
; exits are `jp X`. A p0cb call passed A / F / BC / DE / HL both ways and spent IX
; and AF'; a direct call passes the same registers and keeps IX and AF', so every
; site's contract is the same or narrower. Each arm keeps the original's order of
; checks, so the errors and their order are the ones the trap gates already pin.
;
; ENTRY. Each statement label is its old main name: ex_on (basic/program.asm)
; reaches ex_on_stop / ex_on_sprite / ex_on_key / ex_on_strig / ex_on_interval,
; ex_ff_stmt reaches ex_strig_stmt / ex_interval, with HL where those stubs got it
; and the stack as the statement entered (exec_stmt's contract). ex_key_stmt is a
; CONTINUATION: sub2's scr_key (sub2/scrstmt.asm) returns it in DE with HL on the
; `(`, and main's ex_sub2 does `push de / ret` off sub2's CALSLT frame.
;
; CLEAN-ROOM: own-design (basic/PROVENANCE.md); the statement forms and their
; errors are the black-box measurements the trap specs cite (docs/spec-traps-*.md).

; tt_entry_paren / tt_eostr_store compute &ZTRAP[i] in 8 bits (main's ztrap_entry
; is ZTRAP + 3*i): the 18-entry table must not cross a 256-byte page.
    IF (ZTRAP & $FF) + 3*17 + 2 > $FF
                db      TT_ZTRAP_CROSSES_A_PAGE
    ENDIF
    IF ZTRAP_ENTSZ - 3
                db      TT_ZTRAP_ENTSZ_IS_NOT_3
    ENDIF

; --- ON STOP / ON SPRITE GOSUB [<line>] ----------------------------------------
ex_on_stop:
                ld      de,ZTRAP+ZTI_STOP*ZTRAP_ENTSZ+1
    IF TRAPS_T4
                jr      tt_eos_common
ex_on_sprite:
                ld      de,ZTRAP+ZTI_SPRITE*ZTRAP_ENTSZ+1
    ENDIF
tt_eos_common:                              ; DE = &entry.handler; HL on the event token
                inc     hl                  ; past STOP_TOKEN / SPRITE_TOKEN
tt_eos_gosub:                               ; ON INTERVAL enters HERE (DE = its field)
                push    de                  ; (req_gosub reads no DE)
                call    req_gosub
                call    skip_spaces
                call    tt_line_link        ; CF=1 -> DE = handler LINK
                jr      c,tt_eos_store
                ld      de,0
tt_eos_store:
                ex      (sp),hl             ; HL = &entry.handler, the cursor stacked
                ld      (hl),e
                inc     hl
                ld      (hl),d
                pop     hl                  ; HL = the cursor
                jp      exec_stmt           ; continue the same line (as ON ERROR GOTO)

; --- tt_line_link: main's trap_line_link -- an OPTIONAL `$0E,lo,hi` line ref ------
; CF=1 + DE = the handler's LINK; CF=0 when no line ref follows; ERR 8 (undefined
; line) raised by ers_undef, which pops the pushed cursor itself.
tt_line_link:
                ld      a,(hl)
                cp      LINENO_TOKEN
                jr      z,ttl_have
                cp      LINEADDR_TOKEN
                jr      z,ttl_have
                or      a                   ; not a line ref -> CF = 0
                ret
ttl_have:
                call    lref_bc             ; BC = the handler line, HL past it
                push    hl
                call    find_line_bc        ; CF + HL = the link if found
                jp      nc,ers_undef        ; tll_undef: pops the cursor, ERR 8
                ex      de,hl               ; DE = the handler's LINK
                pop     hl
                scf
                ret

    IF TRAPS_T5
; --- INTERVAL ON | OFF | STOP ---------------------------------------------------
ex_interval:
                call    skip_spaces         ; A = (HL)
                call    tt_onoff            ; A = the ZTS_ state, DE = past the sub-keyword
                push    de                  ; the exec-continue cursor
                ld      hl,ZTRAP+ZTI_INTERVAL*ZTRAP_ENTSZ
                call    set_state           ; (preserves HL)
                bit     7,(hl)
                call    nz,trap_pend        ; make check_traps look once more
                jp      pop_exec

; --- ON INTERVAL = <expr> GOSUB [<line>] -----------------------------------------
ex_on_interval:
                call    skip_eq             ; A = the next non-blank; Z iff `=`
                jp      nz,trap_syntax      ; `ON INTERVAL GOSUB 800` -> ERR 2
                inc     hl
                call    eval_addr           ; DE = n (checked address domain)
                call    check_fperr_only    ; outside -32768..65535 -> Overflow (ERR 6)
                ld      a,d
                or      e
                jp      z,gb_illegal        ; ON INTERVAL=0 -> Illegal function call
                ld      (ZINTVAL),de        ; the period...
                ld      (ZINTCNT),de        ; ...and RELOAD the live counter
                ld      de,ZTRAP+ZTI_INTERVAL*ZTRAP_ENTSZ+1
                jr      tt_eos_gosub        ; GOSUB [<line>], as ON STOP's
    ENDIF

; --- ON STRIG GOSUB [<l0>][,<l1>...] / ON KEY GOSUB <l1>[,<l2>...] ----------------
    IF TRAPS_T3
ex_on_key:
                ld      bc,10*256+0         ; B = slot limit, C = slot index 0..9
                jr      tt_trap_in
    ENDIF
ex_on_strig:
                ld      bc,5*256+0          ; B = slot limit, C = slot index 0..4
tt_trap_in:
                inc     hl                  ; past the STRIG selector byte / KEY token
                call    req_gosub
tt_eostr_lp:
                call    skip_spaces
                push    bc                  ; tt_line_link clobbers BC (find_line_bc)
                call    tt_line_link
                pop     bc                  ; pop does not disturb CF
                jr      c,tt_eostr_store
                ld      de,0                ; empty slot -> CLEAR this trigger's handler
tt_eostr_store:
                push    hl
                ld      a,c
                bit     3,b                 ; B = 10: ON KEY -- the REVERSED band
                jr      z,tt_eostr_idx
                neg
                add     a,ZTI_KEY1+9-ZTI_STRIG0 ; + ZTI_STRIG0 below = ZTI_KEY1+9-C
tt_eostr_idx:
                add     a,ZTI_STRIG0        ; A = the ZTRAP index
                ld      l,a
                add     a,a
                add     a,l                 ; 3 * index (the assert above: no carry)
                add     a,low (ZTRAP+1)     ; -> the handler field, DE (the LINK) kept
                ld      l,a
                ld      h,high ZTRAP
                ld      (hl),e
                inc     hl
                ld      (hl),d
                pop     hl                  ; HL = cursor
                inc     c
                call    skip_comma          ; another slot? Z iff `,`
                jp      nz,exec_stmt        ; no -> statement done, continue the line
                inc     hl                  ; consume the comma
                ld      a,c
                cp      b                   ; slots 0..B-1 only
                jp      nc,trap_syntax      ; a 6th STRIG slot -> trappable ERR 2
                jr      tt_eostr_lp

; --- STRIG(n) ON | OFF | STOP -----------------------------------------------------
ex_strig_stmt:
                call    inc_skip_paren      ; past the STRIG selector byte; Z iff `(`
                jp      nz,trap_syntax
                call    inc_eval            ; DE = n; HL past the expression
                call    get_byte_arg        ; A = E = n (ERR 6 > int16, ERR 5 > 255/neg)
                cp      5                   ; triggers 0..4
                jp      nc,gb_illegal       ; STRIG(5..255) -> ERR 5
                add     a,ZTI_STRIG0
                call    tt_entry_paren      ; HL = the entry, DE = the cursor, A = the state
                push    de                  ; the exec-continue cursor
                ld      b,a
                cp      ZTS_ON
                jr      nz,tt_noseed        ; not enabling
                ld      a,(hl)
                and     ZTS_STATE_MASK
                cp      ZTS_ON              ; ZF=1 iff already ON -> not a transition
                jr      tt_flag
tt_noseed:      xor     a                   ; ZF = 1 -> do not seed
tt_flag:        push    af                  ; carry the decision across set_state
                ld      a,b                 ; A = the new state
                call    set_state           ; maintains the TRAPENA "# ON" count
                pop     af
                jr      z,tt_px
                set     6,(hl)              ; seed the edge shadow (ZTS_SHADOW)
tt_px:          jp      pop_exec

; --- KEY(n) ON | OFF | STOP -------------------------------------------------------
; A CONTINUATION: sub2's scr_key (sub2/scrstmt.asm) peeks the `(` after KEY and
; returns here in DE with HL on it, off its CALSLT frame (main's ex_sub2 does the
; `push de / ret`), so the stack is the statement's own.
; NOT under TRAPS_T3, although its only way in is: tools/gen_resident_abi.py
; exports it to sub2 as p0_ex_key_stmt and REFUSES a missing name, so a T3-off
; build would stop there (sub2's tt_key was unconditional too).
ex_key_stmt:
                call    inc_eval            ; DE = n; HL past the expression
                call    get_byte_arg        ; A = E = n
                dec     a                   ; 1..10 -> slot 0..9; KEY(0) wraps to 255
                cp      10
                jp      nc,gb_illegal       ; KEY(0) and KEY(11..255) -> ERR 5
                ld      c,a
                ld      a,ZTI_KEY1+9
                sub     c                   ; the REVERSED band
                call    tt_entry_paren      ; HL = the entry, DE = the cursor, A = the state
                push    de                  ; the exec-continue cursor
                call    set_state           ; main's trap_state_done: set_state, then
                jr      tt_px               ; pop_exec

; tt_entry_paren -- STRIG(n) / KEY(n)'s shared middle: A = the ZTRAP index ->
; `)` required, then ON | OFF | STOP. Out: HL = the entry pointer, DE = the cursor
; past the sub-keyword, A = the state. One copy for both arms.
tt_entry_paren:
                ld      e,a                 ; &ZTRAP[A] = ZTRAP + 3A, in 8 bits (the
                add     a,a                 ; assert above), into DE; HL untouched
                add     a,e
                add     a,low ZTRAP
                ld      e,a
                ld      d,high ZTRAP        ; DE = the entry pointer, kept to the end
                call    skip_spaces
                cp      ')'
                jp      nz,trap_syntax
                rst     $10                 ; past `)` (CHRGTR)
; tt_onoff -- ON | OFF | STOP at HL -> A = the state, HL = DE on entry, DE = the
; cursor past the sub-keyword; anything else is ERR 2. INTERVAL calls it too.
tt_onoff:
                call    onoff_decode        ; A = the state; CF=0 on junk (DE kept)
                jp      nc,trap_syntax      ; bare `STRIG(n)` / `KEY(n)` -> ERR 2
                inc     hl                  ; consume the ON/OFF/STOP sub-keyword
                ex      de,hl
                ret
