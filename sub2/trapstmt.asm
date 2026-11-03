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
;             SCREEN / COLOR / WIDTH / KEY (D) and DELETE / AUTO / RENUM on
;             to scr_tenant (the SAVE / LOAD family, C2, is the sub ROM's
;             page 1 since D-SUB2RETIRE: main's ex_ls)
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
                ; the arm is a tt_tab row (TT_COUNT = 8; C >= 8 went to file_tenant)
                ; z80flow: table tt_tab 8
                ret                         ; -> the arm
tt_tab:
                dw      tt_on_stop, tt_on_sprite, tt_on_key, tt_on_strig
                dw      tt_on_interval, tt_interval, tt_strig, tt_key

; --- the shared tails -------------------------------------------------------------
; (ERR 5 is filestmt.asm's fs_illegal: gb_illegal / strig_illegal / eoi_err5 are all
; `ld a,5 / jp raise_error`, and so is that tail -- one copy for both files.)
tt_syntax:                                  ; trap_syntax = pl_syntax: a trappable ERR 2
                ld      a,2                 ; pl_syntax is `ld a,2 / jp raise_error`
                jp      fs_raise            ; raises; never returns
tt_pop_exec:                                ; main's `jp pop_exec`
                pop     hl
tt_exec:                                    ; main's `jp exec_stmt`
                ld      de,p0_exec_stmt
                ret

; tt_entry_paren / tt_eostr_store compute &ZTRAP[i] in 8 bits (main's ztrap_entry
; is ZTRAP + 3*i): the 18-entry table must not cross a 256-byte page.
    IF (ZTRAP & $FF) + 3*17 + 2 > $FF
                db      TT_ZTRAP_CROSSES_A_PAGE
    ENDIF
    IF ZTRAP_ENTSZ - 3
                db      TT_ZTRAP_ENTSZ_IS_NOT_3
    ENDIF

; --- ON STOP / ON SPRITE GOSUB [<line>] ----------------------------------------
tt_on_stop:
                ld      de,ZTRAP+ZTI_STOP*ZTRAP_ENTSZ+1
                jr      tt_eos_common
tt_on_sprite:
                ld      de,ZTRAP+ZTI_SPRITE*ZTRAP_ENTSZ+1
tt_eos_common:                              ; DE = &entry.handler; HL on the event token
                inc     hl                  ; past STOP_TOKEN / SPRITE_TOKEN
tt_eos_gosub:                               ; ON INTERVAL enters HERE (DE = its field)
                push    de                  ; (req_gosub reads no DE)
                ld      ix,p0_req_gosub
                call    p0cb
                call    s2_skip_spaces
                call    tt_line_link        ; CF=1 -> DE = handler LINK
                jr      c,tt_eos_store
                ld      de,0
tt_eos_store:
                ex      (sp),hl             ; HL = &entry.handler, the cursor stacked
                ld      (hl),e
                inc     hl
                ld      (hl),d
                pop     hl                  ; HL = the cursor
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
                call    s2_skip_spaces      ; A = (HL)
                call    tt_onoff            ; A = the ZTS_ state, DE = past the sub-keyword
                push    de                  ; the exec-continue cursor
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
                jr      nz,tt_syntax        ; `ON INTERVAL GOSUB 800` -> ERR 2
                inc     hl
                ld      ix,p0_eval_addr
                call    p0cb                ; DE = n (checked address domain)
                ld      ix,p0_check_fperr_only
                call    p0cb                ; outside -32768..65535 -> Overflow (ERR 6)
                ld      a,d
                or      e
                jp      z,fs_illegal        ; ON INTERVAL=0 -> Illegal function call
                ld      (ZINTVAL),de        ; the period...
                ld      (ZINTCNT),de        ; ...and RELOAD the live counter
                ld      de,ZTRAP+ZTI_INTERVAL*ZTRAP_ENTSZ+1
                jp      tt_eos_gosub        ; GOSUB [<line>], as ON STOP's

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
                call    s2_skip_spaces
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
                call    s2_skip_comma       ; another slot? Z iff `,`
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
                jp      nc,fs_illegal       ; STRIG(5..255) -> ERR 5
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
                ld      ix,p0_set_state
                call    p0cb                ; maintains the TRAPENA "# ON" count
                pop     af
                jr      z,tt_px
                set     6,(hl)              ; seed the edge shadow (ZTS_SHADOW)
                jr      tt_px

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
                jr      nc,fs_illegal       ; KEY(0) and KEY(11..255) -> ERR 5
                ld      c,a
                ld      a,ZTI_KEY1+9
                sub     c                   ; the REVERSED band
                call    tt_entry_paren      ; HL = the entry, DE = the cursor, A = the state
                push    de                  ; the exec-continue cursor
                ld      ix,p0_set_state     ; main's trap_state_done is `call set_state`
                call    p0cb                ; then `jp pop_exec`: the second half is
tt_px:          jp      tt_pop_exec         ; ours (no continuation through p0cb)

; tt_entry_paren -- STRIG(n) / KEY(n)'s shared middle: A = the ZTRAP index ->
; `)` required, then ON | OFF | STOP. Out: HL = the entry pointer, DE = the cursor
; past the sub-keyword, A = the state. Both originals spelled it out in full; here
; it is one copy (two copies of the same refusals are two places to drift).
tt_entry_paren:
                ld      e,a                 ; &ZTRAP[A] = ZTRAP + 3A, in 8 bits (the
                add     a,a                 ; assert above), into DE; HL untouched
                add     a,e
                add     a,low ZTRAP
                ld      e,a
                ld      d,high ZTRAP        ; DE = the entry pointer, kept to the end
                call    s2_skip_spaces
                cp      ')'
                jp      nz,tt_syntax
                rst     $10                 ; past `)` (this ROM's RST 10h -> CHRGTR)
; tt_onoff -- ON | OFF | STOP at HL -> A = the state, HL = DE on entry, DE = the
; cursor past the sub-keyword; anything else is ERR 2. INTERVAL calls it too.
tt_onoff:
                ld      ix,p0_onoff_decode
                call    p0cb                ; A = the state; CF=0 on junk (DE kept)
                jp      nc,tt_syntax        ; bare `STRIG(n)` / `KEY(n)` -> ERR 2
                inc     hl                  ; consume the ON/OFF/STOP sub-keyword
                ex      de,hl
                ret
