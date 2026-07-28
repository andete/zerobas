; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; interp.asm — the tokeniser + execution-loop front-end.
;
; A small interpreter spine: crunch an ASCII line into tokens, then walk the
; line statement-by-statement (separated by ':'), dispatching each on its
; leading token. Statements implemented: BLOAD (cassette load + ,R handoff),
; POKE, a single-letter variable assignment, and REM (comment). PEEK is a
; function handled inside the expression evaluator.
;
; Derived only from this project's own black-box oracle observations
; (basic-spec/docs/spec-tokenise.md, spec-tokens-statements.md) and the public
; MSX-BASIC language reference. No disassembly.

; --- INIT entry (cartridge header points here) -----------------------------
init:
                ei                          ; keyboard ISR must run for CHGET
                call    clear_vars          ; deterministic variable table
    IF ROM_BASE < $4000
                ; Error-handling S2a: ERR/ERL are zeroed at COLD BOOT ONLY (this is
                ; the sole cold-only hook; clear_vars also runs on NEW/CLEAR/RUN, which
                ; the reference does NOT clear -- verified empirically 2026-07-18).
                ; On real hardware power-on RAM is garbage, so this explicit zero is
                ; load-bearing (openMSX zero-fills RAM, hiding the omission).
                xor     a
                ld      (ERRCODE),a
                ld      hl,0
                ld      (ERRLINE),hl
                ; Error-handling S2b (packet §7, same cold-only hook, same
                ; UNVERIFIED-hypothesis flag as ONELIN/ONEFLG's run_prog re-arm
                ; above -- see sysvars.inc's own comment): a handler cannot
                ; survive power-on RAM garbage.
                ld      (ONELIN),hl         ; hl still 0 from just above
                ld      (ONEFLG),a          ; A still 0 from the xor a above (the ld hl/
                                            ; ld (nn),hl between don't touch A) -- the
                                            ; ERR-reset-on-RESUME follow-up reclaimed
                                            ; this once-redundant xor a
    IF G6_RESIDENT
                ; G6 DRAW's PERSISTENT state (docs/spec-basic-graphics-g6.md §4).
                ; MEASURED: S and A survive RUN, NEW, CLEAR, CLS, COLOR and SCREEN --
                ; ONLY a power-on resets them -- so this cold-only hook is the sole
                ; place they may be initialised (a reset anywhere warmer would be
                ; measurably wrong). Same power-on-RAM-is-garbage argument as ERR/ERL
                ; above: openMSX zero-fills RAM and would hide the omission. ATRBYT
                ; joins them -- it is the shared graphics attribute a colourless DRAW
                ; reads (§6), so it must start at FORCLR, not at RAM garbage.
                ld      (GFX_DANGLE),a      ; A still 0: angle 0
                ld      a,4
                ld      (GFX_DSCALE),a      ; scale 4 = 1:1
                ld      a,(FORCLR)
                ld      (ATRBYT),a
    ENDIF
    ENDIF
                call    clear_usrtab        ; zero the DEF USR vectors
                call    init_filechan       ; no open channel; PRINT dest = screen
                call    new_prog            ; empty stored program (Step B)
                call    init_ext_roms       ; run the boot-scan INITs C-BIOS skips
                                            ; (e.g. zerobas-disk in slot 3-1) since
                                            ; our own INIT never returns to the scan
                call    show_title          ; startup header lines
                call    autoexec_run        ; auto-run AUTOEXEC.BAS if present (cload.asm)
                jp      repl                ; read/eval loop (never returns)

; --- tokenise: ASCII line -> token stream ----------------------------------
; The whole crunch body (tokenise/tk_*/tk_hex/match_kw/branch_lineno) lives in
; basic/tokenise.inc. Its home depends on the build (subrom arc wave 2,
; docs/spec-basic-subrom-wave2-tokeniser.md):
;   * lean 16 KB cart (ROM_BASE >= $4000): the body is inline here, byte-identical
;     to the pre-extraction interp.asm; a leading digit routes to the inline
;     integer crunch tk_number.
;   * repack build (ROM_BASE < $4000): the body is EVICTED to sub-ROM page 0
;     (sub/sub.asm, reunited with the tk_float crunch wave 1 already moved there).
;     `tokenise` is a two-line dispatch stub that CALSLTs the whole body once per
;     line — cold path (line-entry / program-LOAD only), so a whole-line DI span
;     is cosmetic (post-Enter; drifts JIFFY/TIME only, no functional effect,
;     spec §6 R-W2-1(a)). Both program.asm call sites (direct + numbered line)
;     and the ASCII LOAD/MERGE/CLOAD funnel reach it through this one label.
    IF ROM_BASE < $4000
tokenise:
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_TOKENISE
                call    subrom_call         ; HL=src, DE=dest in; body 0-terminates
                                            ; dest in page-3 RAM; CF=1 if sub absent
                ret     nc                  ; call completed -> back to program.asm
                jp      subrom_absent_error ; reduced build w/o sub-ROM (never on the
                                            ; merged machine, which always ships it)
    ELSE
                include "basic/tokenise.inc"
    ENDIF

; keyword -> token table. Extracted to basic/kwtable.inc so its PLACEMENT can be
; gated (string-engine arc S3, spec §5b): the lean 16 KB build includes it inline
; HERE (byte-identical); the repack build (ROM_BASE < $4000) instead assembles it in
; the reclaimed low region (basic/main.asm), freeing this page-1 room for the string
; engine — page 1 is otherwise full to $7FFF. `kwtable:` is reached only via
; `ld ix,kwtable` (match_kw, detok_kw2), so relocating the table changes nothing but
; where the label resolves. The reloc-only string-function keywords live inside the
; include, gated, so the lean table stays byte-identical.
    IF ROM_BASE >= $4000
                include "basic/kwtable.inc"
    ENDIF

; --- upcase: fold A to uppercase if it is 'a'..'z' -------------------------
; Preserves BC/DE/HL. Source: ASCII (allowed).
upcase:
                cp      'a'
                ret     c                   ; below 'a'
                cp      'z'+1
                ret     nc                  ; above 'z'
                sub     $20
                ret

; --- is_letter: CF set if A is 'A'..'Z' or 'a'..'z' (A preserved) ----------
is_letter:
                push    af
                call    upcase
                cp      'A'
                jr      c,il_no
                cp      'Z'+1
                jr      nc,il_no
                pop     af
                scf
                ret
il_no:
                pop     af
                or      a                   ; CF clear
                ret

; --- exec: walk the line, dispatching each statement -----------------------
; in: HL = token buffer (0x00-terminated). Statements are separated by ':'.
; Returns to the REPL at end of line (or hands off via BLOAD,R, never to return).
exec:
exec_stmt:
                xor     a                   ; each statement starts on the screen;
                ld      (PRDEST),a          ; only PRINT#'s own item loop sets dest=file
    IF ROM_BASE < $4000
                ld      (SAVTXT),hl         ; error-handling S2b §4: capture THIS
                                            ; statement's start for RESUME. HL is
                                            ; still the untouched in: pointer here
                                            ; (reached at line start AND after every
                                            ; ':' via ex_sep) -- the ONLY clean source
                                            ; since raise_error fires from arbitrary
                                            ; call depth, not the statement head.
                ld      (TMISMATCH),a       ; A is still 0: clear the D-2 flag (a stale
                ld      (FPERR),a           ; set would misfire a later statement's check
                                            ; -- FPERR (F2 D-F2-1) mirrors TMISMATCH here
                ld      de,TEMPBASE         ; arrays slice-4a §6: the temp-descriptor
                ld      (TEMPTOP),de        ; stack is emptied at every statement
                                            ; boundary (mirrors the old STRTMP ring's
                                            ; implicit per-statement reset) -- temps
                                            ; never survive past the statement that
                                            ; created them. MUST use DE, not HL: HL is
                                            ; the live statement cursor here (in: HL =
                                            ; token buffer) -- clobbering it made every
                                            ; statement dispatch on $E3D4 -> syntax error
                                            ; (Fable review 2026-07-16). DE is dead on entry.
    ENDIF
                call    skip_spaces         ; leading spaces are skipped (spec §5)
                ld      a,(hl)
                or      a
                ret     z                   ; end of line -> back to the prompt
                ; The dispatch is a TABLE SEARCH (D-KW-2). The 69-entry `cp`/`jp z`
                ; chain this replaces charged 5 B per statement token before it did
                ; anything, and the MISSING-class slice does not fit behind it
                ; (docs/decision-missing-class-slicing.md §4). Now 3 B per token.
                ;
                ; THE REGISTER CONTRACT IS THE CHAIN'S, EXACTLY. A handler is entered
                ; with A = the statement token, HL = the cursor, Z set -- the same
                ; state the `cp`/`jp z` chain left. That is deliberate and it is free:
                ; an earlier revision held the token in B and let A fall out holding
                ; the handler's low address byte -- a silent clobber-contract change
                ; of the kind that is green on every static check, and invisible to a
                ; gate that stops AT the handler without running its body. Comparing
                ; against `(hl)` in place needs no register at all, so B and C stay
                ; untouched too, and `ld a,(hl)` restores A from the cursor for
                ; nothing. tests/test_stmt_dispatch.py asserts all three.
                ld      de,stmt_table
es_scan:
                ld      a,(de)
                inc     de
                or      a                   ; $00 terminates the table -- safe as a
                                            ; sentinel because a $00 statement byte is
                                            ; end-of-line and returned two lines above,
                                            ; so it can never reach the search.
                jr      z,es_noentry
                cp      (hl)                ; compare against the statement byte IN PLACE
                jr      z,es_hit
                inc     de                  ; step over this entry's address
                inc     de
                jr      es_scan
es_hit:
                ex      de,hl               ; HL = &handler, DE = the live cursor
                ld      a,(hl)
                inc     hl
                ld      h,(hl)
                ld      l,a                 ; HL = the handler's address
                ex      de,hl               ; HL = cursor again -- every handler's `in:`
                ld      a,(hl)              ; contract is HL = cursor, A = the token
                push    de                  ; ... and the address goes via the stack,
                ret                         ; since HL is spoken for.
es_noentry:
                ld      a,(hl)              ; the search left A = 0 (the terminator)
                call    is_letter           ; bare letter -> assignment
                jp      c,ex_let
                jp      stmt_error

; --- stmt_table: statement token -> handler (D-KW-2) -------------------------
; `db <token>, dw <handler>`, $00-terminated. ORDER IS PRESERVED from the chain
; this replaces: a linear search still pays per entry examined, so the hot
; statements stay near the front exactly as they were.
;
; Two entries are not keyword tokens and never were: `'_'` is the CALL
; abbreviation (a literal character) and PEEK_PREFIX is $FF, the prefix of a
; two-byte function token that can START a statement (MID$/STRIG). Both were
; plain `cp` compares in the chain and are plain table entries here.
;
; REM_TOKEN needed an IF/ELSE in the chain purely because the forward span
; outgrew `jr`'s reach in the repack build; a table has no reach, so the pair
; collapses to one unconditional entry.
stmt_table:
                db      COLON
                dw      ex_sep    ; ':' separator / empty statement
                db      BLOAD_TOKEN
                dw      ex_bload
                db      CLOAD_TOKEN
                dw      ex_cload
                db      LOAD_TOKEN
                dw      ex_load
                db      RUN_TOKEN
                dw      ex_run
                db      BSAVE_TOKEN
                dw      ex_bsave
                db      SAVE_TOKEN
                dw      ex_save
                db      FILES_TOKEN
                dw      ex_files
                db      MERGE_TOKEN
                dw      ex_merge
                db      OPEN_TOKEN
                dw      ex_open
                db      INPUT_TOKEN
                dw      ex_input
                db      LINE_TOKEN
                dw      ex_line
                db      CLOSE_TOKEN
                dw      ex_close
                db      KILL_TOKEN
                dw      ex_kill
                db      NAME_TOKEN
                dw      ex_name
                db      MAX_TOKEN
                dw      ex_maxfiles    ; MAX FILES = n
                db      FIELD_TOKEN
                dw      ex_field    ; FIELD #f, w AS v$[,...]
                db      LSET_TOKEN
                dw      ex_lset
                db      RSET_TOKEN
                dw      ex_rset
                db      GET_TOKEN
                dw      ex_get
                db      PUT_TOKEN
                dw      ex_put
                db      CALL_TOKEN
                dw      ex_call    ; CALL <name>
                db      '_'
                dw      ex_call_us    ; _<name> -- the CALL abbreviation, a CHARACTER
                db      CSAVE_TOKEN
                dw      ex_csave
                db      POKE_TOKEN
                dw      ex_poke
                db      VPOKE_TOKEN
                dw      ex_vpoke
                db      OUT_TOKEN
                dw      ex_out
                db      CLEAR_TOKEN
                dw      ex_clear
                db      DEF_TOKEN
                dw      ex_def
                db      PRINT_TOKEN
                dw      ex_print
                db      CLS_TOKEN
                dw      ex_cls
                db      SCREEN_TOKEN
                dw      ex_screen
                db      COLOR_TOKEN
                dw      ex_color
                db      WIDTH_TOKEN
                dw      ex_width
                db      KEY_TOKEN
                dw      ex_key
                db      LIST_TOKEN
                dw      ex_list
                db      REM_TOKEN
                dw      ex_rem    ; rest of line is a comment
                db      DATA_TOKEN
                dw      ex_data    ; skipped at run time
                db      READ_TOKEN
                dw      ex_read
                db      RESTORE_TOKEN
                dw      ex_restore
                db      GOTO_TOKEN
                dw      ex_goto
                db      GOSUB_TOKEN
                dw      ex_gosub
                db      ON_TOKEN
                dw      ex_on
                db      RETURN_TOKEN
                dw      ex_return
                db      FOR_TOKEN
                dw      ex_for
                db      NEXT_TOKEN
                dw      ex_next
                db      IF_TOKEN
                dw      ex_if
                db      END_TOKEN
                dw      ex_end
                db      STOP_TOKEN
                dw      ex_stop
                db      CONT_TOKEN
                dw      ex_cont
                db      ELSE_TOKEN
                dw      ex_rem    ; reached after a true THEN clause -> done
                db      LET_TOKEN
                dw      ex_letkw
    IF ROM_BASE < $4000
                db      PEEK_PREFIX
                dw      ex_ff_stmt    ; $FF -> MID$ / STRIG starting a statement
                db      DIM_TOKEN
                dw      ex_dim    ; DIM A(n)[,...]
                db      ERASE_TOKEN
                dw      ex_erase    ; ERASE name[,...]
                db      ERROR_TOKEN
                dw      ex_error    ; ERROR n
                db      RESUME_TOKEN
                dw      ex_resume    ; RESUME family
                db      SOUND_TOKEN
                dw      ex_sound    ; SOUND reg,value
                db      PLAY_TOKEN
                dw      ex_play    ; PLAY "mml"[,..]
                db      BEEP_TOKEN
                dw      ex_beep    ; BEEP (no args)
                db      PSET_TOKEN
                dw      ex_pset    ; PSET (x,y)[,c]
                db      PRESET_TOKEN
                dw      ex_preset    ; PRESET (x,y)[,c]
                db      CIRCLE_TOKEN
                dw      ex_circle    ; CIRCLE (x,y),r[,...]
                db      PAINT_TOKEN
                dw      ex_paint    ; PAINT [STEP](x,y)[,...]
    IF G6_RESIDENT
                db      DRAW_TOKEN
                dw      ex_draw    ; DRAW <string>
    ENDIF
    IF G7_RESIDENT
                db      SPRITE_TOKEN
                dw      ex_sprite    ; SPRITE$(n)=s$ / SPRITE ON|OFF|STOP
    ENDIF
    IF G8_RESIDENT
                ; G8: the pseudo-array assignments have NO statement token of
                ; their own -- a statement that STARTS with the function token is
                ; the assignment (docs/spec-basic-graphics-g8.md §2). `LET` in
                ; front is ERR 2 on the reference, which falls out for free:
                ; ex_letkw only accepts a variable name.
                db      VDP_TOKEN
                dw      ex_vdp_assign    ; VDP(n) = v
                db      BASE_TOKEN
                dw      ex_base_assign    ; BASE(n) = v
    ENDIF
                ; TIME = v: no statement token of its own either -- a statement
                ; that STARTS with the TIME factor token IS the assignment
                ; (docs/spec-basic-time.md §2, the same shape as G8 above).
                db      TIME_TOKEN
                dw      ex_time_assign
                ; --- the MISSING class (basic/missing.asm) --------------------
                ; docs/spec-basic-missing-class.md. Repack-only with the rest of
                ; the class, and at the TAIL: a linear search pays per entry
                ; examined, and none of these five is a hot statement. LOCATE is
                ; the warmest of them and still nowhere near PRINT/IF/FOR.
                ; ⚠️ These entries are the FALSIFICATION HANDLE for this slice --
                ; deleting one must fail exactly that word's gate rows and no
                ; others (spec §7.4).
                db      MOTOR_TOKEN
                dw      ex_motor    ; MOTOR | MOTOR ON | MOTOR OFF
                db      TRON_TOKEN
                dw      ex_tron
                db      TROFF_TOKEN
                dw      ex_troff
                db      LOCATE_TOKEN
                dw      ex_locate    ; LOCATE [col][,[row][,cursor]]
    IF SWAP_RESIDENT
                ; ⚠️ THIS ENTRY DID NOT EXIST when SWAP was gated off, and neither
                ; sysvars.inc's SWAP_RESIDENT block nor spec §10 noticed: both said
                ; the flag guarded "the kwtable row, the stmt_table dispatch row and
                ; the code", and listed flipping the flag as the whole of the wiring.
                ; Only two of the three were real. With the flag on and no arm here,
                ; SWAP crunched to $A4 and then fell off the end of this table into
                ; stmt_error, so EVERY row of the swap battery reported
                ; `syntax error` -- indistinguishable from SWAP still being absent.
                ; SWAP_TOKEN is $A4, the same byte as PDL_TOKEN in the $FF-prefixed
                ; FUNCTION namespace; statement tokens are unprefixed, so they do not
                ; collide (basic/sysvars.inc:1606 records the shared byte).
                db      SWAP_TOKEN
                dw      ex_swap    ; SWAP a,b
    ENDIF
    ENDIF
                db      0                   ; end of table

ex_sep:
                inc     hl
                jp      exec_stmt
ex_end:
                ld      a,1                 ; END / STOP -> stop the run
                ld      (ENDFLAG),a
                ret
ex_rem:
                ret                         ; rest of line is a comment -> done
ex_data:                                    ; DATA is a no-op at run time: skip its
                inc     hl                  ; verbatim body up to ':' or EOL, then
exd_lp:                                     ; continue with the next statement.
                ld      a,(hl)
                or      a
                ret     z                   ; end of line
                cp      COLON
                jp      z,exec_stmt         ; ':' -> next statement runs
                inc     hl
                jr      exd_lp
ex_bload:
                inc     hl                  ; HL -> args (past the BLOAD token)
                jp      do_bload
ex_cload:
                inc     hl                  ; HL -> args (past the CLOAD token)
                jp      do_cload
ex_load:
                inc     hl                  ; HL -> args (past the LOAD token)
                jp      do_load
ex_run:
                inc     hl                  ; HL -> args (past the RUN token)
                jp      do_run
ex_bsave:
                inc     hl                  ; HL -> args (past the BSAVE token)
                jp      do_bsave
ex_save:
                inc     hl                  ; HL -> args (past the SAVE token)
                jp      do_save
ex_csave:
                inc     hl                  ; HL -> args (past the CSAVE token)
                jp      do_csave
ex_poke:
                inc     hl                  ; HL -> args (past the POKE token)
                jp      do_poke
ex_vpoke:
                inc     hl                  ; HL -> args (past the VPOKE token)
                jp      do_vpoke
ex_out:
                inc     hl                  ; HL -> args (past the OUT token)
                jp      do_out

; --- ex_let: variable assignment  <var> = <expr> --------------------------
; The name may be multi-character (significant to 2 chars; see vars.asm). A
; `$`-suffixed name (A$) is a string variable: the RHS is a string operand (a
; "literal" or another string variable) — see ex_let_str. Numeric vars keep the
; integer path.
ex_let:
                call    var_str_type        ; A=1 if the name carries a `$` suffix
                or      a
                jr      nz,ex_let_str       ; string variable -> string assignment
                call    var_name_key        ; BC = key, HL past the name; (VARTYPE) =
                                            ; the resolved type (F3, repack only)
    IF ROM_BASE < $4000
                ld      a,(hl)
                cp      '('
                jp      z,ex_let_arr        ; array-element lvalue (arrays slice-1,
                                            ; docs/spec-basic-arrays.md §9.4/§10,
                                            ; basic/arrays.asm)
                ld      a,(VARTYPE)         ; F3: latch the LHS type NOW -- eval below
                ld      (LHS_VARTYPE),a     ; re-runs var_name_key for every RHS variable
                                            ; factor, clobbering the global (VARTYPE)
                                            ; (e.g. A%=A#: the A# factor would leave
                                            ; VARTYPE=8, mis-storing A% as double)
    ENDIF
                push    bc                  ; save key across '=' + eval
                call    skip_spaces
                ld      a,(hl)
                cp      EQ_TOKEN            ; '=' crunches to $EF (spec §4)
                jr      nz,ex_let_err
                inc     hl
                call    eval                ; DE = value, HL = cursor (BC clobbered)
    IF ROM_BASE < $4000
                call    check_expr_errors_popbc  ; D-2/D-F2-1 (below): discards the
    ENDIF                                        ; saved key before erroring
                pop     bc                  ; BC = key
                push    hl                  ; guard cursor across the store
    IF ROM_BASE < $4000
                ld      a,(LHS_VARTYPE)     ; F3 §11.2: coerce DE/FAC into the LHS's
                call    var_store_fac       ; LATCHED resolved type and store (vars.asm);
                                            ; may set FPERR on a coercion-time Overflow
    ELSE
                call    var_set_key         ; var[key] = DE
    ENDIF
                pop     hl
    IF ROM_BASE < $4000
                ld      a,(FPERR)           ; store-coercion Overflow (§11.2) aborts the
                or      a                   ; statement exactly like an eval()-time one
                jp      nz,fp_runtime_error ; (D-F2-1 pattern); no stack cleanup needed --
    ENDIF                                   ; this is a plain in-line check, not a "call"ed
                                            ; checker (unlike check_expr_errors_popbc)
                jp      exec_stmt           ; continue the line
ex_let_err:
                pop     bc
                jp      stmt_error

; --- ex_let_str: string-variable assignment  A$ = <string operand> -----------
; HL is on the name's first letter (var_str_type did not advance it). Parse the
; name + `$` for the destination key, the '=' token, then evaluate the RHS
; string operand into STRPTR and copy it into the variable's slot.
ex_let_str:
                call    var_name_key        ; BC = dest key, HL past name + `$`
    IF ROM_BASE < $4000
                ld      a,(hl)
                cp      '('
                jp      z,ex_let_arr_str    ; string array-element lvalue (arrays
                                            ; slice-3, docs/spec-basic-arrays-
                                            ; slice3-strings.md §5.2,
                                            ; basic/arrays.asm) — the string
                                            ; sibling of ex_let's own numeric
                                            ; '(' peek right above
    ENDIF
                push    bc                  ; save key across '=' + str_eval
                call    skip_spaces
                ld      a,(hl)
                cp      EQ_TOKEN            ; '=' -> $EF
                jr      nz,ex_let_err
                inc     hl
                call    skip_spaces
                call    str_eval            ; STRPTR -> RHS descriptor, HL advanced
    IF ROM_BASE < $4000
                jp      nc,els_typecheck    ; not a string operand -> D-MISS-1: is it a
                                            ; valid NUMERIC one (Type mismatch) or junk
                                            ; (syntax error)? basic/missing.asm.
                                            ; (Was `jr nc,ex_let_err`, sharing ex_let's
                                            ; "pop bc; jp stmt_error" tail; lean keeps
                                            ; its own separate els_err below, so its
                                            ; bytes stay untouched either way.)
    ELSE
                jr      nc,els_err          ; not a string operand -> syntax error
    ENDIF
    IF ROM_BASE < $4000
                call    cepb_fp             ; D-F2-1: e.g. A$=HEX$(65536.) aborts (the
                                            ; overflow happens inside str_eval's HEX$
                                            ; argument conversion, fac_to_int_addr) --
                                            ; enters check_expr_errors_popbc's FPERR-only
                                            ; half directly (str_eval already owns D-2)
    ENDIF
                pop     bc                  ; BC = dest key
                push    hl                  ; guard cursor across str_set_key
                ld      de,(STRPTR)         ; DE -> source descriptor
                call    str_set_key         ; A$[key] := descriptor (clamped)
                pop     hl
    IF ROM_BASE < $4000
                ; Arrays slice-4c (docs/spec-basic-arrays-slice4c-string-
                ; scalar-unification.md §7.3): a scalar-CHAIN OOM (the table-
                ; full disposition, now dynamic/unbounded rather than the
                ; pre-4c fixed 8-slot STRTAB) sets FPERR via str_set_key's
                ; own ARY_OP=5 -> ary_errmap path but does NOT itself abort
                ; (mirrors var_alloc_or_find's identical contract) -- must be
                ; surfaced HERE, exactly like ex_let's own post-store check
                ; just above for the numeric path. Without this the OOM was
                ; silently swallowed (the OLD STRTAB-full "silent drop"
                ; contract this slice retires; a string-heap BODY OOM is
                ; UNAFFECTED -- str_heap_oom_error already aborts
                ; unconditionally inside str_set_key itself).
                ld      a,(FPERR)
                or      a
                jp      nz,fp_runtime_error
    ENDIF
                jp      exec_stmt
    IF ROM_BASE >= $4000
els_err:
                pop     bc
                jp      stmt_error
    ENDIF

; --- skip_spaces: advance HL past 0x20 bytes -------------------------------
skip_spaces:
                ld      a,(hl)
                cp      ' '
                ret     nz
                inc     hl
                jr      skip_spaces

; --- fre_abort_low lean alias --------------------------------------------------
; The repack build's abort funnel (basic/arrays.asm) sets ENDFLAG (D-1) + emits the
; fresh-line and prints; the shared error sites in interp.asm/program.asm jump to it.
; The lean 16 KB build has no abort funnel (untrapped-error abort is a repack-only
; Phase-3 feature, docs/spec-basic-error-handling.md S1), so there `fre_abort_low`
; is just `print_string` -- every `jp fre_abort_low` in shared code assembles
; byte-for-byte to the old `jp print_string`, keeping basic.rom byte-identical.
    IF ROM_BASE >= $4000
fre_abort_low   equ     print_string
    ENDIF

; --- stmt_error: unknown statement — report and return to the prompt -------
; A statement-level syntax error is TRAPPABLE (repack build). Measured on the
; VG-8020: every malformed statement -- `FOR 1=0 TO 1`, `FOR (I)=…`, bare `FOR`,
; `SWAP 1,A`, `FOO 1,A`, `ZORK`, `A 1`, a dangling `GOTO` -- raises ERR 2 into an
; armed `ON ERROR GOTO` handler rather than aborting the RUN. zerobas used to
; abort every one of them, so an ON ERROR program could never see a syntax error
; (the same trappable-vs-abort seam the graphics arc hit; docs/spec-basic-
; graphics-g8.md §7 G8-trapclass logged it). Routing through raise_error fixes
; the WHOLE class in one place: err_msgtab[2] is this very string, so the
; untrapped output is unchanged, and ERRMARK/PRDEST keep their old meaning.
stmt_error:
                xor     a                   ; an error mid-PRINT# must reach the
                ld      (PRDEST),a          ; screen, not the half-written file
                ld      a,$DD               ; distinct from BLOAD's $EE tape error
                ld      (ERRMARK),a
    IF ROM_BASE < $4000
                ld      a,2                 ; -> trap if armed, else the identical
                jp      raise_error         ; message + abort (fre_abort_low tail)
    ELSE
                ld      hl,err_syntax
                call    print_string        ; lean: unchanged (byte-identical)
                ret
    ENDIF
    IF ROM_BASE >= $4000
err_syntax:
                db      "syntax error",13,10,0
    ENDIF
    ; repack build: err_syntax now lives in the low region (basic/arrays.asm,
    ; near err_subscript/err_redim/...) instead of here -- page-1 is razor-
    ; thin (arrays slice 3, docs/spec-basic-arrays-slice3-strings.md §5.3
    ; space audit) and this string's home is unobserved (any absolute
    ; address costs the same to `ld hl,err_syntax`/print_string, and every
    ; OTHER reader -- fre_msgtab entry 4, D-F2-3 -- is itself repack-only).
    ; The lean build keeps it here (ROM_BASE >= $4000 above), byte-identical.

; --- type_mismatch_error: D-2's statement-level abort (repack build only) ---
; string-compare S2 (spec-basic-string-compare.md §3c): the comparator has already
; set TMISMATCH (+ ERRMARK) and yielded 0 when a string met a non-string; the
; repack-gated driver that owns the condition (ex_if / ex_let / exp_num) jumps
; here right after its eval()/ev_rel call. Mirrors stmt_error exactly (zero
; PRDEST, ERRMARK already set by the comparator, print, ret to the prompt) --
; ev_rel has no mid-expression unwind, so this IS the line abort, realized at the
; statement boundary. Message is zerobas's OWN lowercase wording (like "syntax
; error") -- NOT MSX's verbatim "?Type mismatch Error" string (D-2: reference
; wording we don't copy).
    IF ROM_BASE < $4000
type_mismatch_error:
                ld      a,13                ; ERR 13: type mismatch (error-handling
                jp      raise_error         ; S2a §2/(d), below) -- was ld hl,err_
                                            ; type_mismatch + jr fre_abort (byte-
                                            ; neutral: 2+3 vs 3+2)
err_type_mismatch:
                db      "type mismatch",13,10,0
    ENDIF

; --- fp_runtime_error: F2's statement-level abort for runtime numeric ------
; errors (spec §10.2 D-F2-1: overflow / division by zero). Mirrors
; type_mismatch_error exactly (zero PRDEST, print, ret to the prompt) — the
; float ops (float-arith.asm) have no mid-expression unwind, only SET FPERR
; and yield a defined value (0), so this IS the abort, realized at the
; statement boundary by the driver that checks FPERR right after its
; eval()/ev_rel call (same D-2 pattern as TMISMATCH/type_mismatch_error).
; Message wording is zerobas's own lowercase text (D-F2-1): "overflow"
; REUSES program.asm's err_overflow string byte-for-byte (dl_overflow, the
; crunch-time overflow message) instead of duplicating it; "division by
; zero" is new. NOT the reference's verbatim "?Overflow"/"?Division by zero
; Error" text (divergence, like D-2).
    IF ROM_BASE < $4000
; Error-handling S2a (spec-basic-error-handling-s2a-packet.md §2/(c)): FPERR
; (1..10, this project's own internal deferred-error numbering) maps to the
; MSX ERR code via `fperr_to_err`, then funnels into `raise_error` (below) —
; the single dispatcher that records ERRCODE/ERRLINE and prints the message
; (indexed from `err_msgtab` by ERR code, not FPERR). This REPLACES the old
; FPERR-indexed `fre_msgtab` (20 B, one dw per FPERR code) with a 10-byte
; byte map (FPERR -> ERR code) — every caller of fp_runtime_error has already
; confirmed FPERR is nonzero (the D-F2-1 "check right after eval()" pattern),
; so 1..10 is the only domain this ever sees.
fp_runtime_error:
                ld      a,(FPERR)
                cp      6                   ; FPERR 6 is special-cased below: ERR 7's
                jp      z,fre_arymem_oom    ; err_msgtab entry is the LOWERCASE shared
                                            ; "out of memory" (program.asm err_mem), but
                                            ; FPERR=6's own message must stay arrays' own
                                            ; reference-verbatim CAPITALISED string
                                            ; (err_mem_arr, §9.5 keep) -- one ERR code,
                                            ; two dispositions depending on the SITE, so
                                            ; it cannot flow through the generic code->
                                            ; message table like every other FPERR.
                cp      3                   ; FPERR 3 is ALSO special-cased: ERR 5's
                jp      z,fre_illegalfn_lc  ; err_msgtab entry is arrays' CAPITALISED
                                            ; "Illegal function call" (needed by FPERR=8
                                            ; and a bare `ERROR 5`), but FPERR=3's own
                                            ; sites (SQR(x<0)/LOG(x<=0), and the deferred
                                            ; INSTR/ASC domain checks, ev_f_ifc) keep the
                                            ; pre-existing LOWERCASE err_illegal_fn (§9.5's
                                            ; "unlike the lowercase shared FPERR=3 SQR/LOG
                                            ; keep") -- same one-code-two-dispositions
                                            ; split as FPERR=6/ERR=7 above.
                dec     a                   ; 0-based index (1..10 -> 0..9)
                ld      e,a
                ld      d,0
                ld      hl,fperr_to_err
                add     hl,de
                ld      a,(hl)              ; A = MSX ERR code
                jp      raise_error
; --- fre_arymem_oom / fre_illegalfn_lc: the two FPERR codes (6/3) whose ------
; message can't flow through raise_error's generic err_msgtab lookup (see
; above) -- each sets ERRCODE/record_errline with a fixed message pointer, then
; enters the SHARED raise_error_hl trap decision (S2b fix: they MUST go through
; the trap check, else SQR(x<0)/LOG (FPERR=3) and array OOM (FPERR=6) errors
; never trap under ON ERROR -- the bug the empirical pass caught). HL = message.
; Clobbers as raise_error.
fre_arymem_oom:
                ld      a,7                 ; ERR 7: out of memory
                ld      hl,err_mem_arr
                jr      fre_store_raise
fre_illegalfn_lc:
                ld      a,5                 ; ERR 5: illegal function call (lowercase)
                ld      hl,err_illegal_fn
fre_store_raise:                            ; shared tail (space fix): A=ERR code, HL=msg.
                push    hl                  ; record_errline clobbers HL -- save the msg
                ld      (ERRCODE),a
                call    record_errline
                pop     hl
                jp      raise_error_hl
fperr_to_err:
                db      6                   ; FPERR 1: overflow (err_overflow, program.asm's
                                            ; own string, dl_overflow -- REUSED byte-for-byte)
                db      11                  ; FPERR 2: division by zero (err_fp_divzero)
                db      0                   ; FPERR 3: UNUSED slot (intercepted above via
                                            ; fre_illegalfn_lc before this table is ever
                                            ; indexed for FPERR=3 -- math pack slice 1b
                                            ; SQR(x<0)/LOG, and the deferred INSTR/ASC
                                            ; domain checks, ev_f_ifc, all keep the
                                            ; lowercase err_illegal_fn, unlike FPERR=8's
                                            ; capitalised err_illegal_fn_arr below)
                db      2                   ; FPERR 4: syntax error (D-F2-3 empty
                                            ; parenthesised/argument expression; reuses
                                            ; stmt_error's own ERR-2 table entry)
                db      9                   ; FPERR 5: subscript out of range -- arrays
                                            ; slice-1 (§4.1 #3/#8): index out of range, or
                                            ; wrong dimension count
                db      0                   ; FPERR 6: UNUSED slot (intercepted above via
                                            ; fre_arymem_oom before this table is ever
                                            ; indexed for FPERR=6) -- kept as a placeholder
                                            ; so every other FPERR's index stays FPERR-1,
                                            ; simpler than compacting the table
                db      10                  ; FPERR 7: redimensioned array -- arrays
                                            ; slice-1 (§4.1 #4): a second DIM of a live array
                db      5                   ; FPERR 8: illegal function call -- arrays
                                            ; slice-1 (§4.1 #9): negative subscript; arrays'
                                            ; OWN reference-verbatim capitalised
                                            ; "Illegal function call" (basic/arrays.asm
                                            ; err_illegal_fn_arr; §9.5 pins the array error
                                            ; surface oracle-exact, unlike the lowercase
                                            ; shared FPERR=3 SQR/LOG keep) -- ERR-5's table
                                            ; entry still points at THAT string, not FPERR=3's
                db      16                  ; FPERR 9: string formula too complex -- arrays
                                            ; slice-4a (docs/spec-basic-arrays-slice4a-
                                            ; string-heap.md §6/§11): temp-descriptor stack
                                            ; overflow (basic/str-engine.asm err_too_complex,
                                            ; low region)
                db      13                  ; FPERR 10: type mismatch -- a string function
                                            ; given a NON-string arg (LEN(5)/ASC(5)/VAL(5));
                                            ; ev_f_tmm (expr.asm) defers this via FPERR=10.
                                            ; Same ERR-13 table entry type_mismatch_error uses.
err_fp_divzero:
                db      "division by zero",13,10,0
err_illegal_fn:
                db      "illegal function call",13,10,0
err_resume_noerr:                          ; error-handling S2b (docs/spec-basic-error-
                db      "resume without error",13,10,0
                                            ; handling-s2b-packet.md §5.4, ERR 22): a
                                            ; bare RESUME with ONEFLG=0 (no active trap).
                                            ; House-style lowercase wording (D-2 policy,
                                            ; not the arrays arc's reference-verbatim
                                            ; capitalised text); referenced by err_msgtab
                                            ; entry 22 below.
; err_subscript/err_redim (arrays slice-1, §4.1 #3/#4/#8) live in
; basic/arrays.asm (the low region) instead of here: page 1 is nearly full,
; and these two strings (~49 B) do not need to be page-1 resident — only the
; err_msgtab POINTER (below) does (a plain absolute address, same cost
; regardless of which region the bytes it points at live in).

; --- raise_error: the S2 dispatcher (docs/spec-basic-error-handling-s2b- ---
; packet.md §5.1). in: A = MSX ERR code (1..23). Never returns to its caller.
; Records ERR/ERL (ERRCODE/ERRLINE, sysvars.inc), then decides trap vs abort:
; ONELIN==0 (no handler) or ONEFLG!=0 (already inside a handler with no
; RESUME yet -> real-MSX forced abort with the INNER message) fall to
; rerr_report, the unchanged S1/S2a abort body (err_msgtab lookup -> fre_
; abort_low, basic/arrays.asm low region: zero PRDEST, fresh-line if mid-
; line, print the message, and — run mode only — " in <line>", D-2). Otherwise
; the trap is taken: reset SP to the run-loop-clean SAVSTK anchor (the trap
; fires from arbitrary call depth — this MUST precede jp rp_lp, the whole
; reason SAVSTK exists), capture the erroring statement's resume context
; (CURLINE + SAVTXT) into ERRRESUME for a later RESUME, then reuse GOTO's own
; branch mechanism (GOTOTGT/GOTOFLAG + jp rp_lp) to jump to ONELIN's line —
; ONELIN stores the handler line's LINK address (find_line_bc's return
; convention, a CURLINE-shaped value), exactly what rp_goto expects.
; Clobbers A, DE, HL (and SP, on the trap path only).
raise_error:
                ld      (ERRCODE),a
                call    record_errline
                ; resolve the abort-fallback message FIRST (into HL), THEN decide
                ; trap vs abort in the shared raise_error_hl tail. Message-first so
                ; the two FPERR one-code-two-message special cases (fre_illegalfn_lc/
                ; fre_arymem_oom) can enter raise_error_hl with THEIR OWN message and
                ; still get the trap check (S2b fix: before this they jp'd fre_abort_
                ; low directly, so SQR(-1)/LOG/OOM errors NEVER trapped).
                ld      a,(ERRCODE)
                dec     a                  ; 1-based code -> 0-based index; code 0 wraps
                                           ; to $FF (>= 23, so it too falls to unprintable
                                           ; -- ERROR n now validates 1..255 upstream, so
                                           ; 0 no longer reaches here, but keep it safe)
                cp      24                 ; index >= 24  <=>  code 0 (via $FF) or code >= 25
                jr      nc,rerr_unprintable ; -> "unprintable error" (rerr_unprintable
                                           ; ignores A, so the pre-decrement is harmless)
                add     a,a                ; *2 (word table)
                ld      e,a
                ld      d,0
                ld      hl,err_msgtab
                add     hl,de
                ld      e,(hl)
                inc     hl
                ld      d,(hl)
                ex      de,hl              ; HL = the message string
; --- raise_error_hl: the shared S2b trap decision. in: HL = abort-fallback -----
; message, ERRCODE/ERRLINE already set. ONELIN is read via DE so HL (the message)
; survives to the abort path. Take the trap iff a handler is armed (ONELIN!=0) and
; we are not already inside one (ONEFLG==0); otherwise fall to ra_abort with HL.
raise_error_hl:
                ld      a,(ONEFLG)
                or      a
                jr      nz,ra_abort          ; inside a handler, no RESUME -> forced abort
                ld      de,(ONELIN)          ; DE = handler line LINK addr (kept to the end)
                ld      a,d
                or      e
                jr      z,ra_abort           ; no handler armed -> abort with HL's message
                ; take the trap (HL message discarded -- a trap prints nothing):
                ld      sp,(SAVSTK)          ; §6: unwind to the run-loop-clean depth
                ld      hl,(CURLINE)         ; capture the resume context (§4) via HL, so DE
                ld      (ERRRESUME),hl       ; keeps ONELIN for the CURLINE store below
                ld      hl,(SAVTXT)
                ld      (ERRRESUME+2),hl
                ld      (CURLINE),de         ; CURLINE := ONELIN: point the run loop AT the
                                             ; handler line. rp_lp runs CURLINE's own body, so
                                             ; setting CURLINE IS the branch (GOTOFLAG is only
                                             ; consumed by rp_goto's POST-exec arm, never by
                                             ; rp_lp; a plain jp rp_lp would re-run the ERRORING
                                             ; line and, ONEFLG now 1, force-abort)
                ld      a,1
                ld      (ONEFLG),a           ; inside a handler now
                xor     a
                ld      (RESUMEFLAG),a       ; rp_lp runs CURLINE (the handler) fresh
                jp      rp_lp
ra_abort:                                    ; the S1/S2a abort body (HL = message)
                jp      fre_abort_low
rerr_unprintable:
                ld      hl,err_unprintable
                jp      raise_error_hl       ; through the trap check (ERROR n with a
                                             ; wild code still traps if a handler is armed)

; --- raise_error_forced: like raise_error but ALWAYS aborts, never traps ---
; (docs/spec-basic-error-handling-s2b-packet.md §5.4). Used exactly where
; there is no error context to resume FROM, so re-entering ONELIN's handler
; would be wrong even if one happens to be armed — "RESUME without error"
; (ERR 22): raise_error's own ONEFLG==0 trap-decision would otherwise
; WRONGLY re-trap (ONELIN can be non-zero — a handler armed but not
; currently active — while ONEFLG is exactly 0, the "without error"
; condition itself). in: A = MSX ERR code. Clobbers A, DE, HL.
ex_resume_noerr:                    ; ERR 22 "resume without error" entry — falls
                ld      a,22        ; through into raise_error_forced (S2b space
                                    ; fix: raise_error_forced's ONLY caller, so the
                                    ; separate `ld a,22`/`jp` block is merged in here)
raise_error_forced:                          ; reached ONLY via ex_resume_noerr, A=22
                ld      (ERRCODE),a
                call    record_errline
                ld      hl,err_resume_noerr  ; ERR 22's message directly (this routine is
                jp      fre_abort_low        ; ERR-22-only) -> ALWAYS abort, never trap

; --- record_errline: ERRLINE := run mode? CURLINE+2 : 65535 (direct) -------
; docs/spec-basic-error-handling-s2a-packet.md §3/(e). DIRECTF (D-2, D-1) is
; always valid here: it is DERIVED at rp_exec from CURLINE (program.asm,
; docs/spec-basic-direct-ctrl.md §5), which every line entry and every mid-line
; resume passes through. The run-mode read mirrors print_in_lineno's own CURLINE+2
; fetch (program.asm) byte-for-byte. 65535 is the ERL-in-direct-mode
; sentinel (spec-basic-error-handling-s2.md §9 Q2, black-box-pinned GW/MSX
; convention). Clobbers A, DE, HL.
record_errline:
                ld      a,(DIRECTF)
                or      a
                jr      nz,rel_direct
                ld      hl,(CURLINE)
                inc     hl
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)
                ex      de,hl              ; HL = the erroring line number
                ld      (ERRLINE),hl
                ret
rel_direct:
                ld      hl,65535
                ld      (ERRLINE),hl
                ret

; --- err_msgtab: MSX ERR code (1..23) -> message string (docs/spec-basic- --
; error-handling-s2a-packet.md §2/(a)). Every code's message is stored ONCE
; (this table replaces the old FPERR-indexed fre_msgtab AND every direct
; site's own `ld hl,msg`); holes (12/14/15/18/19/20/21/22 -- not yet raised by
; any S2a site) point at the code-23 "unprintable error" string, same as an
; out-of-table `ERROR n` argument (raise_error, above). The capitalised
; arrays-arc strings (err_subscript/err_redim/err_mem_arr/err_illegal_fn_arr)
; stay separate from the lowercase shared strings, unmerged (spec-basic-
; arrays §9.5) -- their codes (9/10/7/5) just index this table at their own
; entries, same string, no new copy.
err_msgtab:
                dw      err_nofor           ; 1: next without for
                dw      err_syntax          ; 2: syntax error
                dw      err_noret           ; 3: return without gosub
                dw      err_data            ; 4: out of data
                dw      err_illegal_fn_arr  ; 5: illegal function call (arrays' own
                                            ; capitalised string; §9.5 keep)
                dw      err_overflow        ; 6: overflow (program.asm's dl_overflow
                                            ; string, reused byte-for-byte)
                dw      err_mem             ; 7: out of memory (program.asm err_mem;
                                            ; err_stack aliases it -- program.asm)
                dw      err_line            ; 8: undefined line number (zerobas's own
                                            ; "undefined line" wording, spec-basic-error-
                                            ; handling.md §4)
                dw      err_subscript       ; 9: subscript out of range (arrays' own
                                            ; capitalised string; §9.5 keep)
                dw      err_redim           ; 10: redimensioned array (arrays' own
                                            ; capitalised string; §9.5 keep)
                dw      err_fp_divzero      ; 11: division by zero
                dw      err_unprintable     ; 12: illegal direct (hole -- not yet raised)
                dw      err_type_mismatch   ; 13: type mismatch
                dw      err_unprintable     ; 14: out of string space (hole)
                dw      err_unprintable     ; 15: string too long (hole)
                dw      err_too_complex     ; 16: string formula too complex
                dw      err_cont            ; 17: can't continue
                dw      err_unprintable     ; 18: undefined user function (hole)
                dw      err_unprintable     ; 19: device I/O error (load_error family
                                            ; unification is its own later item, S1 §9.1;
                                            ; hole here)
                dw      err_unprintable     ; 20: verify error (hole -- cload.asm's own
                                            ; err_verify is a separate, untouched path)
                dw      err_unprintable     ; 21: no RESUME (hole -- no S2b site raises
                                            ; it: real MSX raises 21 when a trapped run
                                            ; falls off the END of the program without a
                                            ; RESUME, a control-flow edge this slice does
                                            ; not implement -- deliberately deferred)
                dw      err_resume_noerr    ; 22: RESUME without error (raised by
                                            ; raise_error_forced, below)
                dw      err_unprintable     ; 23: unprintable error (self; ERROR n with
                                            ; an out-of-table code, or any hole above)
                dw      err_missing_operand ; 24: missing operand. The table used to stop
                                            ; at 23, so this code -- ALREADY raised by
                                            ; graphics.asm g8_missing and time.asm
                                            ; tm_err24 -- printed "unprintable error" on
                                            ; every site that used it. Found by LOCATE,
                                            ; which is the third: `LOCATE` bare reads
                                            ; `Missing operand` on the reference and read
                                            ; `unprintable error` here. Adding the entry
                                            ; fixes all three at once. raise_error's own
                                            ; range test moved from `cp 23` to `cp 24`
                                            ; with it -- the table bound and that test are
                                            ; one fact in two places.
err_unprintable:
                db      "unprintable error",13,10,0
                ; err_missing_operand itself lives in basic/missing.asm. Sited
                ; there rather than here because 17 bytes inserted at this point
                ; land between page 1's dense forward `jr`s and their targets --
                ; pasmo rejected it outright ("Relative jump out of range",
                ; ex_resume). Same reason get_int16_checked sits at the end of
                ; this file rather than beside check_fperr_only.

; --- ex_error: ERROR n statement (docs/spec-basic-error-handling-s2a-------
; packet.md §3/(g); arg-validation follow-up 2026-07-19). The argument's
; FAITHFUL domain is 1..255 -- empirically pinned on the VG-8020: ERROR 0,
; ERROR 256 (and any >255 or <0) all raise ERR 5 "Illegal function call", while
; 1..255 raise that code verbatim (ERROR 200 -> ERR 200, an unprintable-message
; code, still ERR 200). So we reject the FULL evaluated value (not just its low
; byte): D<>0 (>= 256 or negative) OR E==0 (value 0) -> A=5 (same disposition as
; a plain `ERROR 5`, via raise_error/err_msgtab entry 5). In range -> A=E. An
; out-of-table but in-range code (24..255) still prints "unprintable error" via
; err_msgtab's hole handling. HL enters on the ERROR token. Clobbers A, DE, HL.
ex_error:
                inc     hl                  ; past the ERROR token
                call    eval                ; DE = code, HL advanced (unused past here)
                ld      a,d
                or      a                   ; high byte set -> value >255 or negative ->
                jr      nz,ee_illegal       ;   out of the 1..255 domain -> illegal fn
                or      e                   ; A was 0 (=d), so A:=e; Z <=> value 0
                jr      nz,ee_raise         ; 1..255 -> raise E verbatim
ee_illegal:
                ld      a,5                 ; 0 / >255 / negative -> ERR 5 illegal fn
ee_raise:
                jp      raise_error

; --- ex_resume: RESUME / RESUME 0 / RESUME NEXT / RESUME <line> ------------
; (docs/spec-basic-error-handling-s2b-packet.md §5.4). HL enters on the
; RESUME token. ONEFLG=0 (no active trap) -> "RESUME without error" (ERR 22)
; via raise_error_forced (NOT the ordinary raise_error -- see that routine's
; own header: ONELIN can be non-zero, a handler armed but not currently
; active, while ONEFLG is exactly 0, the "without error" condition itself).
; Otherwise clears ONEFLG and, per the crucial subtlety of §5.4: this
; routine RETURNS into the run loop, it does not itself jump (RESUME/RESUME
; NEXT are statements executed INSIDE the handler, reached via the run
; loop's `call exec`) -- res_same/res_next set RESUMEFLAG+RESUMEPTR(+
; CURLINE) and `ret`, so exec's normal return unwinds to rp_exec, which
; sees RESUMEFLAG and loops to rp_resume -> jumps to (RESUMEPTR). No SAVSTK
; reset needed here (the handler ran at the SAVSTK-clean depth the trap
; already established). RESUME <line> is the one exception -- a genuine
; line branch, so it goes via GOTOTGT/GOTOFLAG like GOTO, not RESUMEFLAG.
; RESUME NEXT's statement-advance (scan_stmt_end) is a pure-leaf sub-ROM
; tenant (SUBROM_IDX_SCANSTMT, sub/errtrap.asm, docs/subrom-tenant-
; playbook.md §3A) -- see res_next below for the marshaling. RESUME <line>'s
; tail (find_line_bc onward) shares code with GOTO's own tail via the
; goto_resolve label (basic/program.asm, a zero-cost label added at ex_goto_
; at's own `call find_line_bc` point -- GOTO's bytes/behaviour are otherwise
; untouched). Clobbers A, BC, DE, HL.
ex_resume:
                ld      a,(ONEFLG)
                or      a
                jp      z,ex_resume_noerr   ; `jp`, not `jr`: the err_msgtab entry for
                                            ; ERR 24 pushed this forward span one byte
                                            ; past `jr`'s reach. Same reason REM_TOKEN
                                            ; needed an IF/ELSE in the old dispatch
                                            ; chain; +1 B, repack-only, no behaviour.
                xor     a                   ; RESUME resets ERR to 0 (ERL is KEPT --
                ld      (ERRCODE),a         ; empirically pinned VG-8020, all four RESUME
                                            ; forms: `0 / 20`, not `0 / 0`). Placed on the
                                            ; trap-active path only (after the ONEFLG!=0
                                            ; check) so ex_resume_noerr (ERR 22) is
                                            ; untouched; a malformed RESUME still aborts
                                            ; with ONEFLG intact (raise_error re-sets its
                                            ; own code, so ERRCODE=0 here is invisible).
                inc     hl                  ; past RESUME_TOKEN
                call    skip_spaces         ; A = (hl)
                or      a                   ; bare RESUME / RESUME<EOL>?
                jr      z,res_same
                cp      COLON               ; bare RESUME before a further ':'-statement?
                jr      z,res_same
                cp      NEXT_TOKEN          ; RESUME NEXT
                jr      z,res_next
                cp      LINENO_TOKEN        ; RESUME <line> / RESUME 0
                jp      nz,stmt_error
                inc     hl
                ld      c,(hl)              ; target line number, LE
                inc     hl
                ld      b,(hl)
                inc     hl
                ld      a,b
                or      c
                jr      z,res_same          ; RESUME 0 == RESUME
                xor     a
                ld      (ONEFLG),a          ; leaving the handler -- CURLINE needs no
                                            ; touch here (rp_goto sets it from GOTOTGT
                                            ; the moment the branch below executes)
                jr      goto_resolve        ; shares find_line_bc + the undef check +
                                            ; GOTOTGT/GOTOFLAG + ret with GOTO's own
                                            ; tail (program.asm) -- BC already holds
                                            ; the target line number, exactly what
                                            ; goto_resolve expects
; res_next: RESUME NEXT -> the statement AFTER the erroring one. UNLIKE
; res_same, this does NOT call res_ctx: the tenant does that prep itself
; (ONEFLG:=0, CURLINE:=erroring CURLINE, reading ERRRESUME directly) since
; both are plain RAM, always visible sub-side (docs/subrom-tenant-
; playbook.md §2) -- no need to pay for it main-side AND sub-side when the
; tenant needs the same ERRRESUME read anyway for its own input. It reports
; via SSE_OUT alone (CALSLT clobbers all registers, and A specifically is not
; reliable back across it -- the math-pack-subrom-tenant lesson -- so the
; result goes through RAM, not A): a plain 2-byte pointer, with $0000 doing
; double duty as the one failure sentinel (a real statement/line pointer is
; never $0000) -- one RAM cell instead of a pointer-plus-flag pair. The
; tenant does the FULL job, including the EOL->next-line advance (it reads/
; writes CURLINE directly): SSE_OUT<>0 means it is the correct resume
; pointer AND CURLINE is already correct (unchanged for a same-line colon,
; advanced by the tenant itself for an end-of-line roll to the next line);
; SSE_OUT=0 is the degenerate case (the erroring line's own link was $0000
; -- program ends there, nothing to resume to; no ERR-21 site this slice,
; err_msgtab's own comment). subrom_call returns CF=1 only if the sub-ROM is
; absent (never on the merged machine).
res_next:
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_SCANSTMT
                call    subrom_call
                jp      c,subrom_absent_error ; reduced build w/o sub-ROM (never on
                                            ; the merged machine, which always ships it)
                ld      hl,(SSE_OUT)        ; next statement -- CURLINE already correct
                ld      a,h
                or      l
                jr      z,ex_goto_undef     ; degenerate (see header) -- reuses GOTO's
                                            ; own "Undefined line number" report
                jr      res_setptr
res_same:                                   ; RESUME / RESUME 0 -> re-run the erroring
                xor     a                   ; statement. Formerly a shared res_ctx
                ld      (ONEFLG),a          ; (called from here AND the RESUME <line>
                ld      hl,(ERRRESUME)      ; arm above); inlined now that this is the
                ld      (CURLINE),hl        ; only remaining site that needs CURLINE
                ld      hl,(ERRRESUME+2)    ; restored too (RESUME NEXT's res_next does
                                            ; the equivalent prep itself, sub-side; the
                                            ; RESUME <line> arm only needs ONEFLG:=0,
                                            ; above) -- ONEFLG:=0, CURLINE:=the erroring
                                            ; statement's CURLINE, HL:=its own text ptr
                                            ; (SAVTXT, as captured into ERRRESUME at
                                            ; trap time), falls through to res_setptr.
res_setptr:
                ld      (RESUMEPTR),hl
                jp      set_resumeflag_ret  ; shares RESUMEFLAG:=1 + ret with RETURN's
                                            ; own tail (program.asm) -- run loop's
                                            ; rp_resume jumps to (RESUMEPTR)

; --- check_expr_errors: shared TMISMATCH+FPERR post-eval() check for ------
; drivers that need no extra stack cleanup before erroring (ex_if, exp_num
; via print.asm). Falls through (returns) if neither flag is set. On error,
; type_mismatch_error/fp_runtime_error print the message and, via print_
; string's own final "ret", return not to us but to OUR caller (ex_if/
; exp_num) -- a full statement-abort, matching the ORIGINAL inline-check
; shape this routine replaced (a direct "jp nz,type_mismatch_error" right
; in the driver, no intervening call). Since THIS routine is itself
; reached via a plain "call check_expr_errors", its own return address
; sits on top of whatever our caller's stack looked like, and would
; otherwise be what that final "ret" lands on instead -- resuming our
; caller's own subsequent code after the abort already printed its message
; and should have skipped the rest of the statement (caught live: `IF A$<5
; THEN` printed "type mismatch" and then ALSO "syntax error", `PRINT A$<5`
; printed "type mismatch" and then ALSO " 0 " -- the driver's own
; leftover logic running when it should not have). Fixed the same way as
; check_preexp_bounds's identical hazard (float-arith.asm): discard our
; own return address before jumping into the abort chain. Clobbers A.
check_expr_errors:
                ld      a,(TMISMATCH)
                or      a
                jr      nz,cee_abort_tm
; check_fperr_only — same SP-clean-site shape as check_expr_errors above, but
; skips the TMISMATCH check (fall-in entry point, adds no bytes). For a
; caller where a TMISMATCH here would be a behaviour change vs today's
; ordering (e.g. INPUT#'s channel-number eval, files.asm: a TMISMATCH channel
; expr already hard-zeroes to channel 0 and derails through fch_valid to
; "load error" -- unrelated to this FPERR-only check).
check_fperr_only:
                ld      a,(FPERR)
                or      a
                jr      nz,cee_abort_fp
                ret
cee_abort_tm:
                pop     hl                  ; discard our own dead resume addr
                jp      type_mismatch_error
cee_abort_fp:
                pop     hl                  ; discard our own dead resume addr
                jp      fp_runtime_error

; --- check_expr_errors_popbc: the same check for drivers that must POP a --
; saved key (BC) off the stack before erroring (ex_let: both flags; ex_let_
; str enters at cepb_fp directly — str_eval already handles its own D-2
; case via its own `jr nc` (target: `els_err` lean / `ex_let_err` repack,
; slice-3 space audit merged the two — same body either way), so only FPERR
; applies there, e.g. `A$=HEX$(65536.)`). Falls through (returns, BC
; untouched) if clear. Same
; own-return-address hazard as check_expr_errors above, PLUS the caller's
; own saved key sitting just beneath it -- both must be discarded (in that
; order: ours first, since it's on top) before the abort chain fires.
check_expr_errors_popbc:
                ld      a,(TMISMATCH)
                or      a
                jr      z,cepb_fp
                pop     hl                  ; discard our own dead resume addr
                pop     bc                  ; discard the caller's saved key
                jp      type_mismatch_error
cepb_fp:
                ld      a,(FPERR)
                or      a
                jr      nz,cepb_abort_fp
                ret
cepb_abort_fp:
                pop     hl                  ; discard our own dead resume addr
                pop     bc                  ; discard the caller's saved key
                jp      fp_runtime_error
    ENDIF

; --- ex_letkw: optional LET keyword before an assignment -------------------
ex_letkw:
                inc     hl                  ; past the LET token
                call    skip_spaces
    IF G8_RESIDENT
                ; `LET VDP(0)=2` / `LET BASE(0)=…` are ERR 2 on the reference
                ; (measured, docs/spec-basic-graphics-g8.md §3). Without this they
                ; fall into ex_let, which takes the token for a variable name and
                ; silently performs an assignment to nothing.
                ld      a,(hl)
                cp      VDP_TOKEN
                jp      z,gfx_syntax
                cp      BASE_TOKEN
                jp      z,gfx_syntax
    ENDIF
    IF ROM_BASE < $4000
                ; `LET TIME=5` is ERR 2 on the reference (spec-basic-time.md
                ; §1.4) and needs the same explicit guard as VDP/BASE above, for
                ; the same reason: ex_let would take the token for a variable
                ; name and silently assign to nothing. It must raise DIRECTLY —
                ; routing it to ex_time_assign would PERFORM the assignment,
                ; since HL sits on the TIME token exactly as it does when
                ; exec_stmt dispatches the legal bare form.
                ld      a,(hl)
                cp      TIME_TOKEN
                jp      z,tm_err2
    ENDIF
                jp      ex_let              ; reuse <letter> = <expr>

; --- ex_goto: GOTO <line> --------------------------------------------------
; The target is the line-number reference $0E,<lineno LE> (the tokeniser emits
; this for a number after GOTO/THEN). Resolves it to the line's address, parks it
; in GOTOTGT and raises GOTOFLAG; the RUN loop performs the branch. `ex_goto_at`
; is the same with HL already on the $0E token (used by IF…THEN <line>).
ex_goto:
                inc     hl                  ; past the GOTO token
ex_goto_at:
                call    skip_spaces
                ld      a,(hl)
                cp      LINENO_TOKEN        ; $0E expected
                jp      nz,stmt_error
                inc     hl
                ld      c,(hl)              ; target line number, LE
                inc     hl
                ld      b,(hl)
                inc     hl
; goto_resolve: shared tail (error-handling S2b space fix) -- RESUME <line>
; (ex_resume, above) jumps in here with BC already holding its target line
; number (after its own RESUME-0 special-case check, which GOTO itself does
; not need), reusing find_line_bc + the undef check + the GOTOTGT/GOTOFLAG
; set + ret verbatim. A zero-cost label: GOTO's own bytes/behaviour here are
; completely unchanged.
goto_resolve:
                call    find_line_bc        ; CF set + HL = line addr if found
                jr      nc,ex_goto_undef
                ld      (GOTOTGT),hl
                ld      a,1
                ld      (GOTOFLAG),a
                ret
ex_goto_undef:
                ld      a,$DB               ; "undefined line" landmark
                ld      (ERRMARK),a
    IF ROM_BASE < $4000
                ld      a,8                 ; ERR 8: undefined line number
                jp      raise_error
    ELSE
                ld      hl,err_line
                jp      fre_abort_low       ; abort the RUN (D-1); lean == print_string
    ENDIF
err_line:
                db      "undefined line",13,10,0

; --- ex_if: IF <expr> THEN <clause> [ELSE <clause>] ------------------------
; A clause is either a line number (implicit GOTO) or statements. Condition is
; true when the expression is non-zero (no comparison operators yet).
ex_if:
                inc     hl                  ; past the IF token
                call    skip_spaces
                call    eval                ; DE = condition, HL after expr
    IF ROM_BASE < $4000
                call    check_expr_errors   ; D-2/D-F2-1: `IF A$<5 THEN...` / a runtime
                                            ; numeric error both abort before either clause
                ; Float truthiness (F2 review live-check, 2026-07-11: the
                ; reference takes the TRUE branch on `IF .5 THEN` — any
                ; nonzero float is true): a float condition must not be
                ; judged by the eagerly TRUNCATED DE (.5 -> 0, falsely
                ; false). FACTYP<>2 -> substitute DE := 0/1 from FAC's lead
                ; byte (whole lead byte 0 <=> value 0, spec §9.1), so the
                ; existing D/E tests below stay the only truthiness judges.
                ld      a,(FACTYP)
                cp      2
                jr      z,exif_truth_ok
                ld      de,0
                ld      a,(FAC)
                or      a
                jr      z,exif_truth_ok
                inc     e                   ; nonzero float -> DE=1 (true)
exif_truth_ok:
    ENDIF
                call    skip_spaces
                ld      a,(hl)
                cp      THEN_TOKEN
                jr      z,if_then
                cp      GOTO_TOKEN          ; allow `IF <expr> GOTO <line>`
                jr      z,if_goto_form
                jp      stmt_error
if_goto_form:
                ld      a,d                 ; condition true?
                or      e
                jr      z,if_false
                jp      exec_stmt           ; true: let exec run the GOTO at HL
if_then:
                inc     hl                  ; past THEN
                call    skip_spaces
                ld      a,d                 ; condition true?
                or      e
                jr      z,if_false
                ld      a,(hl)              ; true: line number -> GOTO, else run
                cp      LINENO_TOKEN
                jr      z,if_branch
                jp      exec_stmt
if_branch:
                jp      ex_goto_at          ; HL on $0E -> conditional GOTO
if_false:
                call    if_skip_to_else     ; scan to ELSE token or end of line
                or      a
                ret     z                   ; no ELSE -> line done
                inc     hl                  ; past the ELSE ($A1) token
                call    skip_spaces
                ld      a,(hl)
                cp      LINENO_TOKEN
                jr      z,if_branch
                jp      exec_stmt           ; ELSE <statements>

; --- if_skip_to_else: token-aware scan to the ELSE token or EOL -------------
; out: HL on the $A1 ELSE token (A = $A1) or on the 0 terminator (A = 0).
; Steps over operand bytes so a value that happens to equal $A1/$00 is not
; mistaken for a delimiter.
if_skip_to_else:
                ld      a,(hl)
                or      a
                ret     z                   ; end of line
                cp      ELSE_TOKEN
                ret     z                   ; ELSE found
                call    tok_skip
                jr      if_skip_to_else

                include "basic/tokskip-body.inc"

; --- skip_to_eol: HL at a token body -> HL just past the line's 00 terminator -
; Token-aware (steps whole tokens via tok_skip), so an operand byte equal to 00
; (e.g. the low byte of &HD000 -> $0C $00 $D0) is not mistaken for the
; terminator. Used to find a stored line's length and its next-line address.
skip_to_eol:
                ld      a,(hl)
                or      a
                jr      z,ste_done
                call    tok_skip
                jr      skip_to_eol
ste_done:
                inc     hl                  ; advance past the 00 terminator
                ret

    IF ROM_BASE < $4000
; --- D-F2-2 stage B: the shared Group-B checked-coercion leaves -------------
; The int-argument statements/functions NOT wired during F2 (STRING$/SPACE$/ON/
; WIDTH byte 0..255; VPOKE/VPEEK VRAM 0..16383) must raise the reference's
; Overflow (ERR 6, arg > int16) or Illegal function call (ERR 5, in-int16 but
; out of the per-site range), not silently take a wrong low byte. Every caller
; is main-resident (str-engine lives in the page-0 low region, the rest in
; page 1; all reach here in the same $0000-$7FFF map). Each re-coerces the arg
; CHECKED from FAC (fac_to_int_strict re-derives it — an out-of-int16 value is
; still a FLOAT in FAC even though eval's silent flt_to_int16 zeroed DE). Sited
; at the end of interp.asm (not inline near check_fperr_only) so the 31 B do not
; land between page 1's dense forward `jr`s and their targets (goto_resolve/ex_if).
;
; get_int16_checked: FAC -> DE = int16 (-32768..32767), aborting ERR 6 if the
; magnitude exceeds int16. HL (the caller's token cursor) is guarded across the
; conversion (fac_to_int_addr/_strict clobber HL — see eval_addr). check_fperr_
; only tail: on FPERR it pops this frame's return addr and jumps into the abort
; chain (SAVSTK resets SP), else returns clean with DE preserved. Clobbers A.
get_int16_checked:
                push    hl
                call    fac_to_int_strict   ; DE = int16; FPERR=1 if |x|>32767
                pop     hl
                jp      check_fperr_only    ; ERR 6 (aborts) or ret with DE intact
; get_vram_arg: FAC -> DE = a VRAM address 0..16383, else abort (ERR 6 if >int16,
; ERR 5 if in-int16 but outside 0..16383 — top two address bits set, incl. any
; negative). Serves VPOKE (statement) and VPEEK (function; see expr.asm). A/HL kept.
get_vram_arg:
                call    get_int16_checked
                ld      a,d
                and     $C0                 ; 0..16383 iff $0000..$3FFF (top 2 bits clear)
                ret     z
                jr      gb_illegal
; --- D-MISS-2: the string engine's argument-domain leaves -------------------
; (docs/spec-basic-str-domain.md §4.) CHR$/LEFT$/RIGHT$/MID$/INSTR accepted
; out-of-range arguments SILENTLY and computed a wrong answer where the
; reference raises; these two are what they call instead of `eval`.
;
; They FOLD `eval` INTO the check, and that is the whole reason this slice
; needed no funding. Every one of the eight sites already did `call eval`, so
; switching it to `call eval_byte_arg` costs ZERO bytes at the site and the
; check is paid for once, here, on the OTHER wall — page 1, while every caller
; is in the page-0 low region. Bolting a separate `call get_byte_arg` after
; each `eval` instead was built and measured: +26 B, all of it low-region, a
; 19 B overrun (spec §5). The usual "a shared helper is not free at two
; callers" result inverts when the helper ABSORBS a call that was already there.
;
; No register guards are needed at any site: get_int16_checked guards HL (the
; token cursor) across the conversion, and get_byte_arg returns D=0/E=byte with
; only A clobbered.
;
; ⚠️ Both leaves abort via raise_error from deep inside the EXPRESSION
; EVALUATOR, far below statement-handler depth. That is only correct because
; fre_abort_low resets SP from SAVSTK (4d35b6d, docs/spec-basic-abort-depth.md);
; before that fix these would have printed and `ret`ed into their own caller.
; It is also why no HOST unit test can cover them — tests/msxtest.py calls
; `eval` directly, so SAVSTK is never set (same reason D-F2-2 dropped
; SPACE$/STRING$'s out-of-domain rows from tests/test_str_fn.py). The openMSX
; differential `make str-domain-acceptance` is the only instrument.
;
; eval_pos_arg: eval + a 1..255 POSITION. MID$'s p and INSTR's p are the
; family's only 1-based arguments (measured: MID$("abc",0) raises where
; MID$("abc",255) does not), so 0 is rejected on top of get_byte_arg's rule.
eval_pos_arg:
                call    eval_byte_arg       ; A = E = 0..255 (or aborts)
                or      a
                ret     nz
                jp      gb_illegal          ; p = 0 -> Illegal function call
; eval_byte_arg: eval + get_byte_arg's plain 0..255. CHR$'s code, LEFT$/RIGHT$'s
; n, MID$'s count (function and statement).
eval_byte_arg:
                call    eval
                jp      get_byte_arg
; get_byte_arg: FAC -> A = E = a byte 0..255, else abort (ERR 6 if >int16, ERR 5
; if in-int16 but >255 or negative — high byte non-zero). Serves STRING$ (count
; and char code), SPACE$, ON n, WIDTH n, and — via the two leaves above — the
; whole string engine. DE preserved (D=0, E=byte) for ON's eon_seek_nth.
; Clobbers A.
;
; ⚠️ Its int16 stage accepts the RANGE -32768..32767, not the magnitude
; |x| <= 32767 that fac_to_int_strict's own header suggests. That is exactly
; the reference rule and it was verified at the boundary, not assumed:
; CHR$(-32768) raises Illegal function call and CHR$(-32769) raises Overflow on
; the VG-8020, and STRING$(-32768,65)/SPACE$(-32768) already agreed through
; THIS routine before D-MISS-2 was written (probe battery `bnd`).
get_byte_arg:
                call    get_int16_checked
                ld      a,d
                or      a                   ; high byte set -> >255 or negative
                jr      nz,gb_illegal
                ld      a,e
                ret
gb_illegal:
                ld      a,5
                jp      raise_error         ; ERR 5 illegal function call
    ENDIF
