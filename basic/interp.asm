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
                ld      (TMISMATCH),a       ; A is still 0: clear the D-2 flag (a stale
                ld      (FPERR),a           ; set would misfire a later statement's check
    ENDIF                                   ; -- FPERR (F2 D-F2-1) mirrors TMISMATCH here
                call    skip_spaces         ; leading spaces are skipped (spec §5)
                ld      a,(hl)
                or      a
                ret     z                   ; end of line -> back to the prompt
                cp      COLON               ; ':' separator / empty statement
                jp      z,ex_sep
                cp      BLOAD_TOKEN
                jp      z,ex_bload
                cp      CLOAD_TOKEN
                jp      z,ex_cload
                cp      LOAD_TOKEN
                jp      z,ex_load
                cp      RUN_TOKEN
                jp      z,ex_run
                cp      BSAVE_TOKEN
                jp      z,ex_bsave
                cp      SAVE_TOKEN
                jp      z,ex_save
                cp      FILES_TOKEN
                jp      z,ex_files
                cp      MERGE_TOKEN
                jp      z,ex_merge
                cp      OPEN_TOKEN
                jp      z,ex_open
                cp      INPUT_TOKEN
                jp      z,ex_input
                cp      LINE_TOKEN
                jp      z,ex_line
                cp      CLOSE_TOKEN
                jp      z,ex_close
                cp      KILL_TOKEN
                jp      z,ex_kill
                cp      NAME_TOKEN
                jp      z,ex_name
                cp      MAX_TOKEN           ; MAX FILES = n  (MAXFILES config)
                jp      z,ex_maxfiles
                cp      FIELD_TOKEN         ; FIELD #f, w AS v$[,...]  (random access)
                jp      z,ex_field
                cp      LSET_TOKEN          ; LSET v$ = s$
                jp      z,ex_lset
                cp      RSET_TOKEN          ; RSET v$ = s$
                jp      z,ex_rset
                cp      GET_TOKEN           ; GET [#]f[,rec]  (read a record)
                jp      z,ex_get
                cp      PUT_TOKEN           ; PUT [#]f[,rec]  (write a record)
                jp      z,ex_put
                cp      CALL_TOKEN          ; CALL <name>  (only CALL FORMAT)
                jp      z,ex_call
                cp      '_'                 ; _<name>  (CALL abbreviation)
                jp      z,ex_call_us
                cp      CSAVE_TOKEN
                jp      z,ex_csave
                cp      POKE_TOKEN
                jp      z,ex_poke
                cp      VPOKE_TOKEN
                jp      z,ex_vpoke
                cp      OUT_TOKEN
                jp      z,ex_out
                cp      CLEAR_TOKEN
                jp      z,ex_clear
                cp      DEF_TOKEN
                jp      z,ex_def
                cp      PRINT_TOKEN
                jp      z,ex_print
                cp      CLS_TOKEN
                jp      z,ex_cls
                cp      SCREEN_TOKEN
                jp      z,ex_screen
                cp      COLOR_TOKEN
                jp      z,ex_color
                cp      WIDTH_TOKEN
                jp      z,ex_width
                cp      KEY_TOKEN
                jp      z,ex_key
                cp      LIST_TOKEN
                jp      z,ex_list
                cp      REM_TOKEN
                jr      z,ex_rem
                cp      DATA_TOKEN          ; DATA: skip this statement at run time
                jp      z,ex_data
                cp      READ_TOKEN
                jp      z,ex_read
                cp      RESTORE_TOKEN
                jp      z,ex_restore
                cp      GOTO_TOKEN
                jp      z,ex_goto
                cp      GOSUB_TOKEN
                jp      z,ex_gosub
                cp      ON_TOKEN
                jp      z,ex_on
                cp      RETURN_TOKEN
                jp      z,ex_return
                cp      FOR_TOKEN
                jp      z,ex_for
                cp      NEXT_TOKEN
                jp      z,ex_next
                cp      IF_TOKEN
                jp      z,ex_if
                cp      END_TOKEN
                jr      z,ex_end
                cp      STOP_TOKEN
                jp      z,ex_stop
                cp      CONT_TOKEN
                jp      z,ex_cont
                cp      ELSE_TOKEN          ; reached after a true THEN clause -> done
                jr      z,ex_rem
                cp      LET_TOKEN
                jp      z,ex_letkw
    IF ROM_BASE < $4000
                cp      PEEK_PREFIX         ; $FF -> a function token starting a statement;
                jp      z,ex_mid_stmt       ; only MID$ ($FF $83) is valid here (str-engine.asm)
    ENDIF
                call    is_letter           ; bare letter -> assignment
                jr      c,ex_let
                jp      stmt_error
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
                push    bc                  ; save key across '=' + str_eval
                call    skip_spaces
                ld      a,(hl)
                cp      EQ_TOKEN            ; '=' -> $EF
                jr      nz,ex_let_err
                inc     hl
                call    skip_spaces
                call    str_eval            ; STRPTR -> RHS descriptor, HL advanced
                jr      nc,els_err          ; not a string operand -> syntax error
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
                jp      exec_stmt
els_err:
                pop     bc
                jp      stmt_error

; --- skip_spaces: advance HL past 0x20 bytes -------------------------------
skip_spaces:
                ld      a,(hl)
                cp      ' '
                ret     nz
                inc     hl
                jr      skip_spaces

; --- stmt_error: unknown statement — report and return to the prompt -------
stmt_error:
                xor     a                   ; an error mid-PRINT# must reach the
                ld      (PRDEST),a          ; screen, not the half-written file
                ld      a,$DD               ; distinct from BLOAD's $EE tape error
                ld      (ERRMARK),a
                ld      hl,err_syntax
                call    print_string
                ret
err_syntax:
                db      "syntax error",13,10,0

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
                ld      hl,err_type_mismatch
                jr      fre_abort           ; shared PRDEST-zero+print+ret tail
                                            ; (fp_runtime_error, right below)
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
fp_runtime_error:
                ld      hl,err_overflow     ; program.asm (dl_overflow); shared wording
                ld      a,(FPERR)
                cp      2
                jr      z,fre_divzero
                cp      3
                jr      z,fre_illegal
                cp      4
                jr      z,fre_syntax
                jr      fre_abort
fre_divzero:
                ld      hl,err_fp_divzero
                jr      fre_abort
fre_syntax:
                ld      hl,err_syntax       ; D-F2-3: empty parenthesised/argument
                                            ; expression (SQR()/()/(5+)/(,)); reuse
                                            ; stmt_error's own lowercase "syntax error"
                                            ; string (spec-basic-empty-expr-syntax-error.md)
                jr      fre_abort
fre_illegal:
                ld      hl,err_illegal_fn   ; math pack slice 1b: SQR(x<0) (spec
                                            ; -basic-math-pack.md §10.4/§10.5)
fre_abort:
                xor     a
                ld      (PRDEST),a
                jp      print_string
err_fp_divzero:
                db      "division by zero",13,10,0
err_illegal_fn:
                db      "illegal function call",13,10,0

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
; case via `jr nc,els_err`, so only FPERR applies there, e.g.
; `A$=HEX$(65536.)`). Falls through (returns, BC untouched) if clear. Same
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
                call    find_line_bc        ; CF set + HL = line addr if found
                jr      nc,ex_goto_undef
                ld      (GOTOTGT),hl
                ld      a,1
                ld      (GOTOFLAG),a
                ret
ex_goto_undef:
                ld      a,$DB               ; "undefined line" landmark
                ld      (ERRMARK),a
                ld      hl,err_line
                jp      print_string
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

; --- tok_skip: advance HL past one token, including its operand bytes -------
tok_skip:
                ld      a,(hl)
                inc     hl
                cp      HEX_TOKEN           ; $0C ,word
                jr      z,tsk2
                cp      INT2_TOKEN          ; $1C ,word
                jr      z,tsk2
                cp      LINENO_TOKEN        ; $0E ,word
                jr      z,tsk2
                cp      LINEADDR_TOKEN      ; $0D ,word
                jr      z,tsk2
                cp      OCT_TOKEN           ; $0B ,word
                jr      z,tsk2
                cp      INT1_TOKEN          ; $0F ,byte
                jr      z,tsk1
                cp      PEEK_PREFIX         ; $FF ,function-token byte
                jr      z,tsk1
    IF ROM_BASE < $4000
                cp      SNG_TOKEN           ; $1D ,4 float value bytes (repack only —
                jr      z,tsk4              ; float literals only exist in the repack
                cp      DBL_TOKEN           ; build; gated so lean stays byte-identical).
                jr      z,tsk8              ; $1F ,8 float value bytes. A mantissa byte
                                            ; can be $00 (e.g. .5 -> 1D 40 50 00 00), so
                                            ; without this stride skip_to_eol/if_skip_to_
                                            ; else/data_seek mistake it for the line/stmt
                                            ; terminator -- a stored `10 A=1.5` never RUNs.
    ENDIF
                cp      '"'                 ; string literal
                jr      z,tsk_str
                cp      REM_TOKEN           ; REM -> rest of line
                jr      z,tsk_rem
                cp      DATA_TOKEN          ; DATA -> verbatim body to ':' / EOL
                jr      z,tsk_data
                ret                         ; 0-operand token / plain byte
tsk1:
                inc     hl
                ret
tsk2:
                inc     hl
                inc     hl
                ret
    IF ROM_BASE < $4000
tsk8:                                       ; DBL_TOKEN: 8 value bytes (4 here + 4 in tsk4)
                inc     hl
                inc     hl
                inc     hl
                inc     hl
tsk4:                                       ; SNG_TOKEN: 4 value bytes
                inc     hl
                inc     hl
                inc     hl
                inc     hl
                ret
    ENDIF
tsk_str:
                ld      a,(hl)
                or      a
                ret     z
                inc     hl
                cp      '"'
                jr      nz,tsk_str
                ret
tsk_rem:
                ld      a,(hl)
                or      a
                ret     z
                inc     hl
                jr      tsk_rem
tsk_data:                                   ; DATA body: verbatim ASCII to ':' or EOL,
                ld      a,(hl)              ; left un-consumed (the ':' / 00 is stepped by
                or      a                   ; the caller's outer loop). Skipping the body
                ret     z                   ; as a unit means a stray control byte in it
                cp      COLON               ; can never be misread as an operand-bearing
                ret     z                   ; token — same end position as the old
                inc     hl                  ; byte-by-byte walk on valid printable DATA.
                jr      tsk_data

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
