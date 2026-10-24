; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
; trapstmt.asm -- zerobas-sub2 PAGE 0: the event-trap STATEMENTS (D-P0CB slice B,
; docs/spec-sub2-p0cb.md §5). Moved out of main page 1 (basic/program.asm) on
; 2026-10-21: ON STOP / SPRITE / STRIG / KEY / INTERVAL GOSUB, INTERVAL ON|OFF|STOP,
; STRIG(n) ON|OFF|STOP, KEY(n) ON|OFF|STOP. The trap MACHINERY -- the per-statement
; poll (check_traps), the ISR side, ZTRAP's helpers -- stays in main; only the
; statements that ARM it moved, and they are cold.
;
; Entered through page-0 index SUB2_IDX_TRAPS from main's `ex_sub2`
; (basic/program.asm), which each statement's 4-byte stub reaches with
;   in   HL = the cursor exactly where main's handler used to get it
;        C  = which statement (TT_* below) -- or, for OPEN / CLOSE / MERGE /
;             MAXFILES (D-P0CB slice C1), their token: trap_tenant forwards
;             C >= TT_COUNT to file_tenant (sub2/filestmt.asm), which passes
;             the SAVE / LOAD family (C2) and SCREEN / COLOR / WIDTH / KEY (D)
;             on through ls_tenant
;   out  DE = the main address to continue at (exec_stmt), HL = its cursor
; ex_sub2 then does `push de / ret`. A handler that used to end in `jp pop_exec`
; pops its own cursor here and returns exec_stmt: execution must never continue
; INSIDE this CALSLT, so no main continuation is ever called through p0cb.
;
; Every main routine is reached through p0cb (sub2/p0cb.asm) with its `p0_` alias
; from basic-resident-abi.inc; `rst $10` is this ROM's RST 10h (main's CHRGTR).
; A raise reached through p0cb never returns -- raise_error resets SP and runs
; main's error path with main's page 0 mapped -- exactly as the `jp nz,trap_syntax`
; it replaces never returned. The code is otherwise main's, statement for statement:
; each arm keeps the original's order of checks, so the errors and their order are
; the same ones the trap gates already pin.

TT_ON_STOP      equ     0
TT_ON_SPRITE    equ     1
TT_ON_KEY       equ     2
TT_ON_STRIG     equ     3
TT_ON_INTERVAL  equ     4
TT_INTERVAL     equ     5
TT_STRIG        equ     6
TT_KEY          equ     7                   ; main sends it no longer: since D-P0CB
                                            ; slice D, KEY(n) arrives as KEY_TOKEN
                                            ; and sub2/scrstmt.asm's scr_key jumps
                                            ; to tt_key itself (the table keeps the
                                            ; slot so the indices do not move)

TT_COUNT        equ     8                   ; C >= TT_COUNT: a statement TOKEN

trap_tenant:
                ; D-P0CB slice C1: main's OPEN / CLOSE / MERGE / MAXFILES enter
                ; ex_sub2 through ONE `ld c,a` (C = their token, always >= $80),
                ; so this entry serves both families and main pays 1 B, not a
                ; second CALSLT stub. sub2/filestmt.asm dispatches on the token.
                ld      a,c
                cp      TT_COUNT
                jp      nc,file_tenant      ; A = C = the statement token
                push    hl                  ; the cursor, under the arm's address
                add     a,a
                ld      e,a
                ld      d,0
                ld      hl,tt_tab
                add     hl,de
                ld      e,(hl)
                inc     hl
                ld      d,(hl)
                ex      de,hl               ; HL = the arm
                ex      (sp),hl             ; HL = the cursor, the arm on the stack
                ret                         ; -> the arm
tt_tab:
                dw      tt_on_stop, tt_on_sprite, tt_on_key, tt_on_strig
                dw      tt_on_interval, tt_interval, tt_strig, tt_key

; --- the shared tails -------------------------------------------------------------
tt_syntax:                                  ; trap_syntax = pl_syntax: a trappable ERR 2
                ld      ix,p0_pl_syntax
                jp      p0cb                ; raises; never returns
tt_illegal:                                 ; strig_illegal / eoi_err5 = gb_illegal: ERR 5
                ld      ix,p0_gb_illegal
                jp      p0cb
tt_pop_exec:                                ; main's `jp pop_exec`
                pop     hl
tt_exec:                                    ; main's `jp exec_stmt`
                ld      de,p0_exec_stmt
                ret

; --- ON STOP / ON SPRITE GOSUB [<line>] ----------------------------------------
tt_on_stop:
                ld      de,ZTRAP+ZTI_STOP*ZTRAP_ENTSZ+1
                jr      tt_eos_common
tt_on_sprite:
                ld      de,ZTRAP+ZTI_SPRITE*ZTRAP_ENTSZ+1
tt_eos_common:                              ; DE = &entry.handler; HL on the event token
                push    de
                inc     hl                  ; past STOP_TOKEN / SPRITE_TOKEN
                ld      ix,p0_req_gosub
                call    p0cb
                ld      ix,p0_skip_spaces
                call    p0cb
tt_eos_line:                                ; ON INTERVAL enters HERE, its target pushed
                call    tt_line_link        ; CF=1 -> DE = handler LINK
                jr      c,tt_eos_store
                ld      de,0
tt_eos_store:
                pop     bc                  ; BC = &entry.handler
                ld      a,e
                ld      (bc),a
                inc     bc
                ld      a,d
                ld      (bc),a
                jr      tt_exec             ; continue the same line (as ON ERROR GOTO)

; --- tt_line_link: main's trap_line_link -- an OPTIONAL `$0E,lo,hi` line ref ------
; CF=1 + DE = the handler's LINK; CF=0 when no line ref follows; ERR 8 (undefined
; line) raised through p0cb. is_lref is two compares, so it is local.
tt_line_link:
                ld      a,(hl)
                cp      LINENO_TOKEN
                jr      z,ttl_have
                cp      LINEADDR_TOKEN
                jr      z,ttl_have
                or      a                   ; not a line ref -> CF = 0
                ret
ttl_have:
                ld      ix,p0_lref_bc
                call    p0cb                ; BC = the handler line, HL past it
                push    hl
                ld      ix,p0_find_line_bc
                call    p0cb                ; CF + HL = the link if found
                jr      nc,ttl_undef
                ex      de,hl               ; DE = the handler's LINK
                pop     hl
                scf
                ret
ttl_undef:
                ld      ix,p0_ers_undef     ; tll_undef = ers_undef; raise_error resets
                jp      p0cb                ; SP, so the pushed cursor needs no pop

; --- INTERVAL ON | OFF | STOP ---------------------------------------------------
tt_interval:
                ld      ix,p0_skip_spaces
                call    p0cb                ; A = (HL)
                ld      ix,p0_onoff_decode
                call    p0cb                ; A = the ZTS_ state
                jp      nc,tt_syntax        ; bare `INTERVAL` / `INTERVAL FOO` -> ERR 2
                inc     hl                  ; consume the ON/OFF/STOP sub-keyword
                push    hl
                ld      hl,ZTRAP+ZTI_INTERVAL*ZTRAP_ENTSZ
                ld      ix,p0_set_state
                call    p0cb                ; (preserves HL)
                bit     7,(hl)
                jr      z,tt_pop_exec
                ld      ix,p0_trap_pend
                call    p0cb                ; make check_traps look once more
                jr      tt_pop_exec

; --- ON INTERVAL = <expr> GOSUB [<line>] -----------------------------------------
tt_on_interval:
                ld      ix,p0_skip_eq
                call    p0cb                ; A = the next non-blank; Z iff `=`
                jp      nz,tt_syntax        ; `ON INTERVAL GOSUB 800` -> ERR 2
                inc     hl
                ld      ix,p0_eval_addr
                call    p0cb                ; DE = n (checked address domain)
                ld      ix,p0_check_fperr_only
                call    p0cb                ; outside -32768..65535 -> Overflow (ERR 6)
                ld      a,d
                or      e
                jp      z,tt_illegal        ; ON INTERVAL=0 -> Illegal function call
                ld      (ZINTVAL),de        ; the period...
                ld      (ZINTCNT),de        ; ...and RELOAD the live counter
                ld      ix,p0_req_gosub
                call    p0cb
                ld      ix,p0_skip_spaces
                call    p0cb
                ld      de,ZTRAP+ZTI_INTERVAL*ZTRAP_ENTSZ+1
                push    de                  ; tt_eos_line pops it as the store target
                jp      tt_eos_line

; --- ON STRIG GOSUB [<l0>][,<l1>...] / ON KEY GOSUB <l1>[,<l2>...] ----------------
tt_on_key:
                ld      bc,10*256+0         ; B = slot limit, C = slot index 0..9
                jr      tt_trap_in
tt_on_strig:
                ld      bc,5*256+0          ; B = slot limit, C = slot index 0..4
tt_trap_in:
                inc     hl                  ; past the STRIG selector byte / KEY token
                ld      ix,p0_req_gosub
                call    p0cb
tt_eostr_lp:
                ld      ix,p0_skip_spaces
                call    p0cb
                push    bc                  ; tt_line_link clobbers BC (find_line_bc)
                call    tt_line_link
                pop     bc                  ; pop does not disturb CF
                jr      c,tt_eostr_store
                ld      de,0                ; empty slot -> CLEAR this trigger's handler
tt_eostr_store:
                push    hl
                push    de                  ; the LINK, across ztrap_entry (clobbers DE)
                ld      a,c
                bit     3,b                 ; B = 10: ON KEY -- the REVERSED band
                jr      z,tt_eostr_idx
                neg
                add     a,ZTI_KEY1+9-ZTI_STRIG0 ; + ZTI_STRIG0 below = ZTI_KEY1+9-C
tt_eostr_idx:
                add     a,ZTI_STRIG0
                ld      ix,p0_ztrap_entry
                call    p0cb                ; HL = &ZTRAP[3+C] (the state byte)
                pop     de
                inc     hl                  ; -> the handler field
                ld      (hl),e
                inc     hl
                ld      (hl),d
                pop     hl                  ; HL = cursor
                inc     c
                ld      ix,p0_skip_comma
                call    p0cb                ; another slot? Z iff `,`
                jp      nz,tt_exec          ; no -> statement done, continue the line
                inc     hl                  ; consume the comma
                ld      a,c
                cp      b                   ; slots 0..B-1 only
                jp      nc,tt_syntax        ; a 6th STRIG slot -> trappable ERR 2
                jr      tt_eostr_lp

; --- STRIG(n) ON | OFF | STOP -----------------------------------------------------
tt_strig:
                ld      ix,p0_inc_skip_paren
                call    p0cb                ; past the STRIG selector byte; Z iff `(`
                jp      nz,tt_syntax
                ld      ix,p0_inc_eval
                call    p0cb                ; DE = n; HL past the expression
                ld      ix,p0_get_byte_arg
                call    p0cb                ; A = E = n (ERR 6 > int16, ERR 5 > 255/neg)
                cp      5                   ; triggers 0..4
                jp      nc,tt_illegal       ; STRIG(5..255) -> ERR 5
                add     a,ZTI_STRIG0
                call    tt_entry_paren      ; DE = the entry, HL past `)`, A = the state
                ld      b,a
                inc     hl                  ; consume the ON/OFF/STOP sub-keyword
                push    hl                  ; the exec-continue cursor
                ex      de,hl               ; HL = the entry pointer
                ld      a,b
                cp      ZTS_ON
                jr      nz,tt_noseed        ; not enabling
                ld      a,(hl)
                and     ZTS_STATE_MASK
                cp      ZTS_ON              ; ZF=1 iff already ON -> not a transition
                jr      tt_flag
tt_noseed:      xor     a                   ; ZF = 1 -> do not seed
tt_flag:        push    af                  ; carry the decision across set_state
                ld      a,b                 ; A = the new state
                ld      ix,p0_set_state
                call    p0cb                ; maintains the TRAPENA "# ON" count
                pop     af
                jp      z,tt_pop_exec
                set     6,(hl)              ; seed the edge shadow (ZTS_SHADOW)
                jp      tt_pop_exec

; --- KEY(n) ON | OFF | STOP -------------------------------------------------------
; Entered by `jp` from scr_key (sub2/scrstmt.asm, D-P0CB slice D) with HL on the
; `(` and the stack as this file's arms get it -- main's ex_key peeked the `(` and
; went to ex_key_stmt's stub until then.
tt_key:
                ld      ix,p0_inc_eval
                call    p0cb                ; DE = n; HL past the expression
                ld      ix,p0_get_byte_arg
                call    p0cb                ; A = E = n
                dec     a                   ; 1..10 -> slot 0..9; KEY(0) wraps to 255
                cp      10
                jp      nc,tt_illegal       ; KEY(0) and KEY(11..255) -> ERR 5
                ld      c,a
                ld      a,ZTI_KEY1+9
                sub     c                   ; the REVERSED band
                call    tt_entry_paren      ; DE = the entry, HL past `)`, A = the state
                inc     hl                  ; consume the ON/OFF/STOP sub-keyword
                push    hl                  ; the exec-continue cursor
                ex      de,hl               ; HL = the entry pointer
                ld      ix,p0_set_state     ; main's trap_state_done is `call set_state`
                call    p0cb                ; then `jp pop_exec`: the second half is
                jp      tt_pop_exec         ; ours (no continuation through p0cb)

; tt_entry_paren -- STRIG(n) / KEY(n)'s shared middle: A = the ZTRAP index ->
; DE = the entry pointer; `)` required, then ON | OFF | STOP -> A = the state.
; Both originals spelled it out in full; here it is one copy (sub2 bytes are cheap,
; but two copies of the same refusals are two places to drift).
tt_entry_paren:
                push    hl
                ld      ix,p0_ztrap_entry
                call    p0cb                ; HL = &ZTRAP[A] (clobbers DE)
                ex      de,hl               ; DE = the entry pointer, kept to the end
                pop     hl
                ld      ix,p0_skip_spaces
                call    p0cb
                cp      ')'
                jp      nz,tt_syntax
                rst     $10                 ; past `)` (this ROM's RST 10h -> CHRGTR)
                ld      ix,p0_onoff_decode
                call    p0cb                ; A = the state; CF=0 on junk
                jp      nc,tt_syntax        ; bare `STRIG(n)` / `KEY(n)` -> ERR 2
                ret
