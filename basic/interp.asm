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
    IF CLEARPOOL
                ; D-CLP: the string pool's default size, set BEFORE the first
                ; heap_reset (which clear_vars below reaches) so the floor is never
                ; derived from power-on RAM garbage. Cold-boot ONLY: NEW, RUN and a
                ; bare CLEAR all keep the current size (characterization §2.4), so
                ; this must NOT move into clear_vars.
                ld      hl,200
                ld      (POOLSIZE),hl
    ENDIF
                call    clear_vars          ; deterministic variable table
                ; Error-handling S2a: ERR/ERL are zeroed at COLD BOOT ONLY (this is
                ; the sole cold-only hook; clear_vars also runs on NEW/CLEAR/RUN, which
                ; the reference does NOT clear -- verified empirically 2026-07-18).
                ; On real hardware power-on RAM is garbage, so this explicit zero is
                ; load-bearing.
                ; 🔴 IT USED TO SAY "openMSX zero-fills RAM, hiding the omission",
                ; AND THAT IS FALSE -- MEASURED 2026-08-21, D-VALTYP
                ; (docs/valtyp-coldram-notes.md §1). Power-on RAM on this machine
                ; reads $FF from $D000 up through $F1xx; what is cleared is the
                ; STANDARD MSX system-variable area, by C-BIOS's own workspace
                ; init, not by the emulator. ERRFLG at $F414 happens to sit INSIDE
                ; that area (its whole 32-byte window reads 00), so the conclusion
                ; holds for THIS cell -- but only for this cell, and for a reason
                ; that has nothing to do with openMSX. See the FPERR store below,
                ; where the same sentence was wrong about the outcome too.
                xor     a
                ld      (ERRFLG),a
                ; D-STMTPEND: the pending-error cell needs the same cold-only
                ; zero, and for the same reason. exec_stmt used to clear it
                ; before anything could read it; now exec_stmt READS it first,
                ; so power-on RAM garbage would raise a bogus error out of the
                ; very first statement.
                ;
                ; 🔴 THIS IS THE ONE THE OLD SENTENCE WAS WRONG ABOUT, AND IT WAS
                ; WRONG IN BOTH HALVES (D-VALTYP, 2026-08-21,
                ; docs/valtyp-coldram-notes.md §2/§3). It said "openMSX zero-fills
                ; RAM, so NO emulator row can see this store". FPERR is $F069 --
                ; BELOW the standard system-variable area C-BIOS clears, in a
                ; 32-byte window that reads $FF except for this very byte. Knife
                ; K-VT1 cuts this store and the machine answers `Unprintable error
                ; in 10` to `10 PRINT"[OK]"`: it is the ONLY reason $F069 is zero,
                ; and it is loudly observable.
                ;
                ; ⚠️ K-SP4's recorded ZERO red rows still stands as a NUMBER, and
                ; `clearpool-acceptance` is 62/62 under K-VT1 as well -- what that
                ; measures is what the batteries type before their first scored
                ; row, NOT whether the store matters. A prediction and its reason
                ; are two claims and a green run confirms at most one.
                ld      (FPERR),a
                ld      hl,0
                ld      (ERRLIN),hl
                ; Error-handling S2b (packet §7, same cold-only hook, same
                ; UNVERIFIED-hypothesis flag as ONELIN/ONEFLG's run_prog re-arm
                ; above -- see sysvars.inc's own comment): a handler cannot
                ; survive power-on RAM garbage.
                ld      (ONELIN),hl         ; hl still 0 from just above
                ; D-DOTLINE R-DOT2: `.` reads 0 on a cold machine (clp-cold, both
                ; references). Same cold-only hook and the SAME power-on-RAM-is-
                ; garbage argument as ERR/ERL above. K6 predicted ZERO red rows
                ; for cutting it and measured zero.
                ; ⚠️ ITS STATED REASON WAS "openMSX zero-fills RAM" AND THAT IS
                ; FALSE (D-VALTYP 2026-08-21, docs/valtyp-coldram-notes.md §2).
                ; The right reason is narrower and is a fact about the ADDRESS:
                ; DOT is $F6B5, inside the standard system-variable area C-BIOS
                ; clears before BASIC runs, whose whole 32-byte window reads 00.
                ; Move this cell below $F400 and the argument evaporates -- as it
                ; already has for FPERR at $F069, four lines above.
                ; ⚠️ COLD-BOOT ONLY. NEW does NOT reset `.` (clp-new reads 20
                ; after a NEW that emptied the program), so this must not move
                ; into new_prog -- which is exactly where TRACEFLAG's reset lives,
                ; two cells apart in sysvars.inc, for a rule measured the other
                ; way.
                ld      (DOT),hl            ; hl still 0
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
                ld      (GFX_DANGLE),a      ; A still 0: angle 0 -- and MEASURED
                                            ; to be the same state an explicit
                                            ; `A0` leaves behind (d.a0.32k), so
                                            ; this cell needs no sentinel
                ld      (GFX_DSCALE),a      ; A still 0: the NEVER-SET scale
                                            ; state, which is NOT `S4` (D-DSCALE,
                                            ; spec-basic-lineerr.md §12). From
                                            ; boot both references move the FULL
                                            ; count; `S4` wraps. 0 is a sentinel
                                            ; `gdo_s` cannot write -- it maps S0
                                            ; to 4 (measured) -- so "never set"
                                            ; and every explicit S are distinct.
                ld      a,(FORCLR)
                ld      (ATRBYT),a
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
; basic/tokenise.inc (subrom arc wave 2,
; docs/spec-basic-subrom-wave2-tokeniser.md):
;   * the body is EVICTED to sub-ROM page 0
;     (sub/sub.asm, reunited with the tk_float crunch wave 1 already moved there).
;     `tokenise` is a two-line dispatch stub that CALSLTs the whole body once per
;     line — cold path (line-entry / program-LOAD only), so a whole-line DI span
;     is cosmetic (post-Enter; drifts JIFFY/TIME only, no functional effect,
;     spec §6 R-W2-1(a)). Both program.asm call sites (direct + numbered line)
;     and the ASCII LOAD/MERGE/CLOAD funnel reach it through this one label.
tokenise:
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_TOKENISE
                call    subrom_call         ; HL=src, DE=dest in; body 0-terminates
                                            ; dest in page-3 RAM; CF=1 if sub absent
                ret     nc                  ; call completed -> back to program.asm
                jp      subrom_absent_error ; reduced build w/o sub-ROM (never on the
                                            ; merged machine, which always ships it)

; keyword -> token table. Extracted to basic/kwtable.inc so its PLACEMENT could be
; moved (string-engine arc S3, spec §5b): it is assembled in the reclaimed low
; region (basic/main.asm), not here, freeing this page-1 room for the string
; engine — page 1 is otherwise full to $7FFF. `kwtable:` is reached only via
; `ld ix,kwtable` (match_kw, detok_kw2), so relocating the table changes nothing but
; where the label resolves. The reloc-only string-function keywords live inside the
; include, gated.

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
                ld      (SAVTXT),hl         ; error-handling S2b §4: capture THIS
                                            ; statement's start for RESUME. HL is
                                            ; still the untouched in: pointer here
                                            ; (reached at line start AND after every
                                            ; ':' via ex_sep) -- the ONLY clean source
                                            ; since raise_error fires from arbitrary
                                            ; call depth, not the statement head.
                ; D-STMTPEND (docs/spec-basic-stmtpend.md): THE STATEMENT
                ; BOUNDARY IS A READER, NOT A CLEAR. This was an unconditional
                ; `ld (FPERR),a` -- and since exec_stmt is where EVERY driver
                ; ends (`jp exec_stmt`), it was the point at which a fault
                ; raised by a driver that never calls check_expr_errors got
                ; silently discarded. Measured: `SCREEN 0*(1/0)` and
                ; `DEFUSR=0*(1/0)` printed NOTHING here and `Division by zero`
                ; on both references; `FOR I=0*(1/0) TO 3` ran the loop.
                ; A pending code at a statement boundary means the statement
                ; that just finished faulted and nobody looked, so REPORT it.
                ; 🎯 THE CLEAR IS THEN FREE: A is 0 on the fall-through exactly
                ; when the cell already is, so the store it replaces is
                ; redundant and the whole reader costs 4 bytes, not 7. The
                ; "cleared once per statement" invariant is unchanged -- it is
                ; now proved by the test instead of imposed by the store, and
                ; the CONSUME moved to record_errline (the one routine every
                ; raise passes through), so a trapped error's handler cannot
                ; re-raise the code that entered it.
                ; ⚠️ Cold boot must still zero the cell (power-on RAM is
                ; garbage) -- see the cold-only hook above.
                ld      a,(FPERR)
                or      a
                jp      nz,fp_runtime_error ; the FIRST fault outranks the rest
                                            ; of the statement, including its end
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
                call    skip_spaces         ; leading spaces are skipped (spec §5)
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
                ; D-LFILES (docs/spec-basic-lfiles.md). LFILES shares do_files's
                ; whole head and the dirverb tenant's whole walk -- only the sink
                ; and the layout differ, and both ride the op selector -- so this
                ; row plus a 2-byte `ld a,n` IS the main-side cost of the verb.
                ; The listing itself is sub-ROM page 1 (sub/dirverb.asm tnt_files).
                db      LFILES_TOKEN
                dw      ex_lfiles    ; LFILES ["<filespec>"] -- FILES to LPT:
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
                ; D-DEFINTTOK / D-DEFTYPETOK: the four DEF<type> verbs each have
                ; their OWN token ($AB..$AE) and share ONE handler -- ex_deftype
                ; steps over the token and the sub-ROM tenant reads it back to
                ; pick the type code, so three of these four rows are the entire
                ; main-ROM cost of the other three verbs. ex_def ($97) is now
                ; DEF USR and nothing else.
                db      DEFSTR_TOKEN
                dw      ex_deftype
                db      DEFINT_TOKEN
                dw      ex_deftype
                db      DEFSNG_TOKEN
                dw      ex_deftype
                db      DEFDBL_TOKEN
                dw      ex_deftype
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
                ; --- the EDITOR class (D-DELETE, docs/spec-basic-delete.md) ----
                ; At the tail for the MISSING class's reason and more so: DELETE
                ; is typed by a human at the prompt, so a linear search paying
                ; per entry examined costs it nothing anybody can perceive.
                ; ⚠️ THIS ROW IS 3 B AND THAT FIGURE IS MEASURED, NOT COMPUTED --
                ; D-KWGAP4's knife K5 added one row and watched page-1 free go
                ; 6 B -> 3 B. What changed since is the WALL, not the rate: the
                ; D-RETLN carve took page 1 to 124 B free.
                ; ⚠️ AND AN ENTRY HERE IS NOT OPTIONAL WIRING. SWAP's note below
                ; is the standing record of a build where the token and the code
                ; both existed, this row did not, and every gate row read exactly
                ; as if the verb were still absent.
                db      DELETE_TOKEN
                dw      ex_delete    ; DELETE [<line>][-[<line>]]
                ; D-EDITVERB: the other three editor verbs. Three rows at 3 B is
                ; the figure D-KWGAP4's knife K5 measured against a 6 B page-1
                ; wall, which is why it filed them instead of landing them; the
                ; wall is 356 B now (spec-basic-editverb.md §1.2).
                db      LLIST_TOKEN
                dw      ex_llist     ; LLIST [<line>][-[<line>]] -- LIST to LPT:
                db      RENUM_TOKEN
                dw      ex_renum     ; RENUM [<new>][,[<old>][,<inc>]]
                db      AUTO_TOKEN
                dw      ex_auto      ; AUTO [<start>][,<inc>]
                ; D-LPTVERB (docs/spec-basic-lptverb.md). LPRINT shares ex_print's
                ; whole item loop -- only the SINK differs -- so this row costs 3 B
                ; and the head costs 20. ⚠️ $9D is BIN$ in the $FF alphabet; LPOS
                ; ($FF,$9C) is dispatched from expr.asm's chain, NOT from here.
                db      LPRINT_TOKEN
                dw      ex_lprint    ; LPRINT [<items>] -- PRINT to LPT:
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
                ; collide (basic/sysvars.inc:2093 records the shared byte).
                db      SWAP_TOKEN
                dw      ex_swap    ; SWAP a,b
    ENDIF
                db      0                   ; end of table

ex_sep:
                inc     hl
                jp      exec_stmt
ex_end:
                ; D-CONTR (docs/spec-basic-cont-record.md §3.2): END IS A RUN STOP,
                ; so it records a CONT resume point like every other one -- the
                ; header on ex_stop used to assert the OPPOSITE as fact ("END does
                ; not: it ends the run with no resume point"), which was never
                ; measured and is wrong. The position is the token IMMEDIATELY
                ; AFTER the END token, i.e. MID-LINE: `10 END:PRINT"[9]"` + RUN +
                ; CONT prints [9] on the reference and then falls through to the
                ; next line (spec §2.1, cont2_end_rest -- that row is the
                ; discriminator against "resume at the next line"). HL is on the
                ; END token here (the dispatcher's contract, es_hit above), so the
                ; `inc hl` IS the measured resume position; HL is dead afterwards
                ; and A is reloaded below, so cont_record's clobbers are free.
                inc     hl
                call    cont_record         ; (basic/program.asm; run mode only)
                ; D-ONEFLG site B (docs/spec-basic-oneflg-reset-scope.md §4): END
                ; TERMINATES the run, so the handler context dies with it (spec
                ; §2 c3/c3c: after a handler ENDs the run, the reference traps the
                ; next error and answers a direct RESUME with "RESUME without
                ; error"). STOP does NOT come through here -- the token table
                ; dispatches it to ex_stop -- which is what keeps the measured
                ; TERMINATE-vs-SUSPEND asymmetry structural rather than a test:
                ; a Break must KEEP the flag so CONT can resume inside the
                ; handler (spec §2 c4b/c6).
                xor     a
                ld      (ONEFLG),a
                inc     a                   ; -> 1
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
                push    bc                  ; save key across '=' + eval
                call    skip_spaces
                cp      EQ_TOKEN            ; '=' crunches to $EF (spec §4)
                jr      nz,ex_let_err
                inc     hl
                call    eval                ; DE = value, HL = cursor (BC clobbered)
                call    check_expr_errors_popbc  ; D-2/D-F2-1 (below): discards the
                pop     bc                  ; BC = key
                push    hl                  ; guard cursor across the store
                ld      a,(LHS_VARTYPE)     ; F3 §11.2: coerce DE/FAC into the LHS's
                call    var_store_fac       ; LATCHED resolved type and store (vars.asm);
                                            ; may set FPERR on a coercion-time Overflow
                pop     hl
                ld      a,(FPERR)           ; store-coercion Overflow (§11.2) aborts the
                or      a                   ; statement exactly like an eval()-time one
                jp      nz,fp_runtime_error ; (D-F2-1 pattern); no stack cleanup needed --
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
                ld      a,(hl)
                cp      '('
                jp      z,ex_let_arr_str    ; string array-element lvalue (arrays
                                            ; slice-3, docs/spec-basic-arrays-
                                            ; slice3-strings.md §5.2,
                                            ; basic/arrays.asm) — the string
                                            ; sibling of ex_let's own numeric
                                            ; '(' peek right above
                push    bc                  ; save key across '=' + str_eval
                call    skip_spaces
                cp      EQ_TOKEN            ; '=' -> $EF
                jr      nz,ex_let_err
                inc     hl
                call    skip_spaces
                call    str_eval            ; STRPTR -> RHS descriptor, HL advanced
                jp      nc,els_typecheck    ; not a string operand -> D-MISS-1: is it a
                                            ; valid NUMERIC one (Type mismatch) or junk
                                            ; (syntax error)? basic/missing.asm.
                                            ; (Was `jr nc,ex_let_err`, sharing ex_let's
                                            ; "pop bc; jp stmt_error" tail.)
                call    cepb_fp             ; D-F2-1: e.g. A$=HEX$(65536.) aborts (the
                                            ; overflow happens inside str_eval's HEX$
                                            ; argument conversion, fac_to_int_addr) --
                                            ; enters check_expr_errors_popbc's FPERR-only
                                            ; half directly (str_eval already owns D-2)
                pop     bc                  ; BC = dest key
                push    hl                  ; guard cursor across str_set_key
                ld      de,(STRPTR)         ; DE -> source descriptor
                call    str_set_key         ; A$[key] := descriptor (clamped)
                pop     hl
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
                jp      exec_stmt

; --- skip_spaces: advance HL past 0x20 bytes -------------------------------
skip_spaces:
                ld      a,(hl)
                cp      ' '
                ret     nz
                inc     hl
                jr      skip_spaces

; --- fre_abort_low -------------------------------------------------------------
; The abort funnel (basic/arrays.asm) sets ENDFLAG (D-1) + emits the fresh-line and
; prints; the shared error sites in interp.asm/program.asm jump to it. (The retired
; lean 16 KB cart had no abort funnel at all -- untrapped-error abort is a Phase-3
; feature, docs/spec-basic-error-handling.md S1 -- and aliased this to plain
; `print_string` so those shared `jp`s assembled unchanged.)

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
                ; D-STMTPEND: A SYNTAX ERROR MUST NOT OUTRANK A FAULT THAT
                ; ALREADY HAPPENED. `FOR I=0*(1/0) STEP 2` reaches here with
                ; the division-by-zero code live, and reported `Syntax error`
                ; where both references report `Division by zero`; so did every
                ; statement whose delimiter check landed on a token a
                ; string-compare mismatch had stranded the cursor short of
                ; (`FOR I=(A$<5) TO 3`, `POKE (A$<5),0`). This is D-PENDERR's
                ; first-error-wins rule at the one READER that raises a code of
                ; its own instead of reading the cell. It is a `call`, not a
                ; reorder: with nothing pending it returns and ERR 2 is raised
                ; exactly as before -- which is what the n.syn.* rows hold.
                call    check_expr_errors
                ld      a,2                 ; -> trap if armed, else the identical
                jp      raise_error         ; message + abort (fre_abort_low tail)
    ; repack build: err_syntax now lives in the low region (basic/arrays.asm,
    ; near err_subscript/err_redim/...) instead of here -- page-1 is razor-
    ; thin (arrays slice 3, docs/spec-basic-arrays-slice3-strings.md §5.3
    ; space audit) and this string's home is unobserved (any absolute
    ; address costs the same to `ld hl,err_syntax`/print_string, and every
    ; OTHER reader -- fre_msgtab entry 4, D-F2-3 -- is near it).

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
type_mismatch_error:
                ld      a,13                ; ERR 13: type mismatch (error-handling
                jp      raise_error         ; S2a §2/(d), below) -- was ld hl,err_
                                            ; type_mismatch + jr fre_abort (byte-
                                            ; neutral: 2+3 vs 3+2)
; D-MSGMIGRATE: err_type_mismatch's TEXT now lives in the sub-ROM tenant
; (sub/errmsg.asm em_type_mismatch, keyed on ERRFLG=13). err_msgtab entry 13 is
; err_subhosted; type_mismatch_error above already goes through raise_error, so
; it sets ERRFLG on the way and needs no change at all.

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
; Error-handling S2a (spec-basic-error-handling-s2a-packet.md §2/(c)): FPERR
; (1..10, this project's own internal deferred-error numbering) maps to the
; MSX ERR code via `fperr_to_err`, then funnels into `raise_error` (below) —
; the single dispatcher that records ERRFLG/ERRLIN and prints the message
; (indexed from `err_msgtab` by ERR code, not FPERR). This REPLACES the old
; FPERR-indexed `fre_msgtab` (20 B, one dw per FPERR code) with a 10-byte
; byte map (FPERR -> ERR code) — every caller of fp_runtime_error has already
; confirmed FPERR is nonzero (the D-F2-1 "check right after eval()" pattern),
; so 1..10 is the only domain this ever sees.
; 🎯 D-MSGEXACT DELETED THE TWO SPECIAL CASES THAT USED TO STAND HERE, AND THE
; POLICY CHANGE IS WHAT KILLED THEM -- not a cleverer encoding.
; FPERR=6 (ERR 7) and FPERR=3 (ERR 5) each used to be intercepted by a `cp`/`jp z`
; pair, because ONE ERR CODE HAD TWO MESSAGES that differed only in CASE: the
; lowercase house-style string for the shared sites, and arrays' §9.5
; reference-verbatim capitalised string for the array sites. Now that every
; message is the reference's own text, the two spellings ARE THE SAME STRING --
; so the pairs, `fre_arymem_oom`, `fre_illegalfn_lc` and their shared
; `fre_store_raise` tail are all dead, and both codes flow through the generic
; table like every other FPERR. The lowercase policy was the ONLY thing paying
; for that apparatus (docs/spec-basic-msgexact.md §3.1): -33 B of page 1 here,
; plus -12 B of now-duplicate strings.
; ⚠️ TRAPPING IS PRESERVED, AND THAT IS NOT INCIDENTAL. Those routines existed
; partly to route FPERR=3/6 through the trap check (the S2b fix below: before it,
; SQR(-1)/LOG and array OOM NEVER trapped under ON ERROR). `raise_error` does the
; same check on its own path, so deleting them keeps the fix -- knife K3 cuts
; exactly this claim.
fp_runtime_error:
                ld      a,(FPERR)
                dec     a                   ; 0-based index (1..10 -> 0..9)
                ld      e,a
                ld      d,0
                ld      hl,fperr_to_err
                add     hl,de
                ld      a,(hl)              ; A = MSX ERR code
                jp      raise_error
; (fre_arymem_oom / fre_illegalfn_lc / fre_store_raise were HERE. D-MSGEXACT
; deleted all three -- see fp_runtime_error's header above. They existed to give
; ONE ERR code a second message that differed only in case; exact wording made
; the two spellings identical, so there is no second message to point at.)
fperr_to_err:
                db      6                   ; FPERR 1: overflow (err_overflow, program.asm's
                                            ; own string, dl_overflow -- REUSED byte-for-byte)
                db      11                  ; FPERR 2: division by zero (err_fp_divzero)
                db      5                   ; FPERR 3: illegal function call -- math pack
                                            ; slice 1b SQR(x<0)/LOG, and the deferred
                                            ; ASC domain check (ev_f_ifc). A REAL ENTRY
                                            ; since D-MSGEXACT: it was a `db 0` placeholder
                                            ; while FPERR=3 was intercepted upstream to get
                                            ; a LOWERCASE message. Same ERR 5, same string
                                            ; as FPERR=8 now -- knife K3 cuts this slot.
                db      2                   ; FPERR 4: syntax error (D-F2-3 empty
                                            ; parenthesised/argument expression; reuses
                                            ; stmt_error's own ERR-2 table entry)
                db      9                   ; FPERR 5: subscript out of range -- arrays
                                            ; slice-1 (§4.1 #3/#8): index out of range, or
                                            ; wrong dimension count
                db      7                   ; FPERR 6: out of memory (DIM/auto-dim OOM via
                                            ; ary_errmap). A REAL ENTRY since D-MSGEXACT --
                                            ; was a `db 0` placeholder while FPERR=6 was
                                            ; intercepted upstream to get the CAPITALISED
                                            ; message; that is now the only spelling.
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
    IF CLEARPOOL
                db      14                  ; FPERR 11 (= FPERR_STROOM, sysvars.inc):
                                            ; OUT OF STRING SPACE -- the string heap could
                                            ; not allocate, which with the D-CLP partition
                                            ; ON means the pool `CLEAR n` sized ran out.
                                            ; ⚠️ Deliberately NOT FPERR=6/ERR 7: an ARRAY
                                            ; that will not fit is out of MEMORY, and the
                                            ; probe's oos-vs-oom row pins the two apart.
                                            ; Unlike 3 and 6 this needs no special case in
                                            ; fp_runtime_error -- ERR 14 has exactly one
                                            ; message (err_out_of_str, str-engine.asm) and
                                            ; flows through the generic err_msgtab lookup.
    ENDIF
; D-MSGMIGRATE: err_fp_divzero's TEXT is sub-ROM-hosted (em_fp_divzero, ERRFLG
; = 11). fp_runtime_error reaches it through fperr_to_err -> raise_error ->
; err_msgtab entry 11, which is now err_subhosted -- one table operand, 0 B.
; 🎯 err_illegal_fn IS NOW AN ALIAS, NOT A STRING. It used to be the lowercase
; twin of arrays' capitalised err_illegal_fn_arr ("i" vs "I" + MSGESC_ILLFN);
; D-MSGEXACT made both the reference's `Illegal function call`, at which point
; they were byte-identical and one had to go. The LOW-REGION copy survives and
; this page-1 one is deleted (-3 B of page 1): every reader is an absolute
; address, so placement is free (see the err_subscript/err_redim note below).
; ⚠️ subromcall.asm's err_subrom_absent aliases THIS name, deliberately -- the
; "sub-ROM is missing" message must stay MAIN-resident (spec-basic-msgenc-carve.md
; §4.4 Q4), and err_illegal_fn_arr is in the low region, which satisfies that.
err_illegal_fn  equ     err_illegal_fn_arr
; D-MSGMIGRATE: err_resume_noerr's TEXT is sub-ROM-hosted (em_resume_noerr,
; ERRFLG = 22). ⚠️ IT HAD TWO READERS, NOT ONE -- err_msgtab entry 22 AND
; raise_error_forced's own `ld hl` below -- and BOTH are keyed on 22, because
; raise_error_forced stores ERRFLG before it loads the message. That second
; reader is why `res-noerr` is a gate row: `ERROR 22` exercises the table entry
; and nothing else, so the walk alone cannot see the direct site.
; (docs/spec-basic-error-handling-s2b-packet.md §5.4, ERR 22: a bare RESUME with
; ONEFLG=0, i.e. no active trap.)
; err_subscript/err_redim (arrays slice-1, §4.1 #3/#4/#8) live in
; basic/arrays.asm (the low region) instead of here: page 1 is nearly full,
; and these two strings (~49 B) do not need to be page-1 resident — only the
; err_msgtab POINTER (below) does (a plain absolute address, same cost
; regardless of which region the bytes it points at live in).

; --- raise_error: the S2 dispatcher (docs/spec-basic-error-handling-s2b- ---
; packet.md §5.1). in: A = MSX ERR code (1..23). Never returns to its caller.
; Records ERR/ERL (ERRFLG/ERRLIN, sysvars.inc), then decides trap vs abort:
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
                ld      (ERRFLG),a
                call    record_errline
                ; resolve the abort-fallback message FIRST (into HL), THEN decide
                ; trap vs abort in the shared raise_error_hl tail. Message-first so
                ; the two FPERR one-code-two-message special cases (fre_illegalfn_lc/
                ; fre_arymem_oom) can enter raise_error_hl with THEIR OWN message and
                ; still get the trap check (S2b fix: before this they jp'd fre_abort_
                ; low directly, so SQR(-1)/LOG/OOM errors NEVER trapped).
rerr_msg:                                  ; D-ONERR0 (docs/spec-basic-onerr0.md §4.3):
                                           ; a LABEL, zero bytes. `ON ERROR GOTO 0`
                                           ; inside a handler re-raises the error that
                                           ; entered it, and must enter HERE rather
                                           ; than at raise_error -- past the ERRFLG
                                           ; store (the code is already the one being
                                           ; re-raised) and past record_errline, which
                                           ; would rewrite ERRLIN/DOT from the line the
                                           ; re-raise is IN. Measured: ERR/ERL after
                                           ; the re-raise are the ORIGINAL 7 / 20
                                           ; (characterization row `e.reraise`), so
                                           ; skipping the record is the behaviour, not
                                           ; an optimisation.
                ld      a,(ERRFLG)
                dec     a                  ; 1-based code -> 0-based index; code 0 wraps
                                           ; to $FF (>= 25, so it too falls to unprintable
                                           ; -- ERROR n now validates 1..255 upstream, so
                                           ; 0 no longer reaches here, but keep it safe)
                cp      25                 ; index >= 25  <=>  code 0 (via $FF) or code >= 26
                jp      nc,rerr_unprintable ; D-MSGMIGRATE: straight to the marker.
                                           ; S-FCH-2's rerr_sparse/rerr_sparse2 used to
                                           ; sit here to pick 52/59/55/58/61's messages;
                                           ; all five migrated to the tenant, at which
                                           ; point every arm of both selectors was
                                           ; `ld hl,err_subhosted / jp raise_error_hl`
                                           ; -- which is what rerr_unprintable IS. 50 B
                                           ; of dispatch deleted, trap decision
                                           ; unchanged (both went through
                                           ; raise_error_hl).
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
; message, ERRFLG/ERRLIN already set. ONELIN is read via DE so HL (the message)
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
                ld      a,$FF                ; D-REHOME: the references store $FF
                                             ; here, MEASURED (sysvarsweep
                                             ; s7-fired). Both readers test it
                                             ; with `or a`, so this is a
                                             ; zero-byte, control-flow-neutral
                                             ; change that makes PEEK($F6BB)
                                             ; match the reference exactly.
                ld      (ONEFLG),a           ; inside a handler now
                xor     a
                ld      (RESUMEFLAG),a       ; rp_lp runs CURLINE (the handler) fresh
                jp      rp_lp
ra_abort:                                    ; the S1/S2a abort body (HL = message)
                ; D-CONTR (docs/spec-basic-cont-record.md §3.4): AN UNTRAPPED ABORT
                ; IS A RUN STOP TOO, and its resume point is the FAILING STATEMENT'S
                ; OWN START -- not the line start. Measured: `10 PRINT"[7]":B=ASC("")`
                ; + RUN + CONT re-raises `Illegal function call in 10` and does NOT
                ; reprint [7] (spec §2.1, cont2_err_mid is the discriminator).
                ; SAVTXT is exactly that pointer and is already maintained by
                ; exec_stmt at every statement entry -- see its own note there: the
                ; ONLY clean source, since raise_error fires from arbitrary call
                ; depth. No new sysvar, no new invariant.
                ; The push/pop pair is BALANCED before the `jp`, so the abort chain's
                ; depth-independence (D-CUR-D) is untouched; fre_abort_low resets SP
                ; from SAVSTK as its own first act regardless.
                push    hl                   ; guard the message across the record
                ld      hl,(SAVTXT)
                call    cont_record          ; (basic/program.asm; run mode only)
                pop     hl
                jp      fre_abort_low
rerr_unprintable:
                ; 🎯 D-MSGSUB: err_subhosted, NOT err_unprintable -- and that one
                ; changed operand is the whole sparse half of the slice. This is the
                ; fall-through of rerr_sparse -> rerr_sparse2 (52/59, then 55/58/61),
                ; i.e. EVERY code past the dense table. Pointing it at the marker
                ; routes the ten sparse holes (50/51/53/54/56/57/60/62/63/64) AND
                ; codes 26..49 / 65..255 into the tenant in ONE edit, with no
                ; membership test main-side and ZERO bytes. The tenant answers the
                ; codes it does not know with its own copy of `Unprintable error`,
                ; so their text is unchanged -- which is exactly what makes ERROR 26
                ; a live GREEN control riding the new mechanism (spec §3.2).
                ld      hl,err_subhosted
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
                ld      (ERRFLG),a
                call    record_errline
                ld      hl,err_subhosted     ; ERR 22's message, sub-hosted (D-MSGMIGRATE:
                jp      ra_abort             ; ERR-22-only) -> ALWAYS abort, never trap.
                                             ; D-CONTR: via ra_abort, not straight to
                                             ; fre_abort_low -- same 3 bytes, and the
                                             ; FORCED abort arm records a resume point
                                             ; too. Measured (spec §2.1, cont2_err22):
                                             ; `10 RESUME` + RUN + CONT re-raises
                                             ; `RESUME without error in 10`.

; --- record_errline: ERRLIN := run mode? CURLINE+2 : 65535 (direct) -------
; docs/spec-basic-error-handling-s2a-packet.md §3/(e). DIRECTF (D-2, D-1) is
; always valid here: it is DERIVED at rp_exec from CURLINE (program.asm,
; docs/spec-basic-direct-ctrl.md §5), which every line entry and every mid-line
; resume passes through. The run-mode read mirrors print_in_lineno's own CURLINE+2
; fetch (program.asm) byte-for-byte. 65535 is the ERL-in-direct-mode
; sentinel (spec-basic-error-handling-s2.md §9 Q2, black-box-pinned GW/MSX
; convention). Clobbers A, DE, HL.
record_errline:
                ; D-STMTPEND: CONSUME the pending-error code. Every raise passes
                ; through here exactly once (raise_error, and arrays.asm's
                ; e21_last `No RESUME` abort), and `rerr_msg` -- D-ONERR0's
                ; re-raise entry, which deliberately skips this routine -- is
                ; re-raising a code that was already consumed. Without this the
                ; statement-boundary reader in exec_stmt would see the SAME code
                ; again at the handler's first statement and raise it a second
                ; time, with ONEFLG set, i.e. forced abort: the handler would
                ; never run. Knife K-SP3 cuts it and reddens every trapped fault
                ; row in the gate, including rows this slice did not touch.
                xor     a
                ld      (FPERR),a
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
                ld      (ERRLIN),hl
                ; D-DOTLINE writer (c) (docs/spec-basic-dotline.md §2 R-DOT3c):
                ; an error in a STORED line records that line, which is what
                ; makes `LIST .` after a failure -- `.`'s documented use -- show
                ; the line that failed. `clp-trapend` says a TRAPPED error writes
                ; it too, so this belongs here (before the trap decision), not on
                ; the abort arm.
                ld      (DOT),hl
                ret
rel_direct:
                ld      hl,65535
                ld      (ERRLIN),hl
                ; 🔴 AND NOT HERE. A DIRECT-MODE ERROR WRITES `.` NOT AT ALL --
                ; it does NOT take ERRLIN's 65535 sentinel. `clp-direrr` types
                ; `ERROR 7` at the prompt with `.`=20 and reads 20 back, on both
                ; references. ⚠️ That is exactly why these two stores may not be
                ; folded into a shared tail, which is the obvious repack and
                ; would save 4 bytes: ERRLIN and DOT are written by the same
                ; event under DIFFERENT rules, and the cheaper shape is wrong.
                ret

; --- err_msgtab: MSX ERR code (1..25) -> message string (docs/spec-basic- --
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
                dw      err_subhosted       ; 1: next without for
                dw      err_syntax          ; 2: syntax error
                dw      err_subhosted       ; 3: return without gosub
                dw      err_subhosted       ; 4: out of data
                dw      err_illegal_fn_arr  ; 5: illegal function call (arrays' own
                                            ; capitalised string; §9.5 keep)
                dw      err_subhosted       ; 6: Overflow. D-MSGMIGRATE: sub-hosted
                                            ; (em_overflow) -- and it only became
                                            ; migratable when dl_overflow's float arm
                                            ; was FIXED to store ERRFLG at all. Until
                                            ; then this code had one ERRFLG-keyed reader
                                            ; and one that was not keyed on anything.
                dw      err_mem             ; 7: out of memory (program.asm err_mem;
                                            ; err_stack aliases it -- program.asm)
                dw      err_subhosted       ; 8: undefined line number (zerobas's own
                                            ; "undefined line" wording, spec-basic-error-
                                            ; handling.md §4)
                dw      err_subscript       ; 9: subscript out of range (arrays' own
                                            ; capitalised string; §9.5 keep)
                dw      err_redim           ; 10: redimensioned array (arrays' own
                                            ; capitalised string; §9.5 keep)
                dw      err_subhosted       ; 11: division by zero
                dw      err_subhosted       ; 12: Illegal direct. D-MSGSUB: the text
                                            ; lives in the sub-ROM tenant, keyed on
                                            ; ERRFLG. Still not RAISED by any zerobas
                                            ; site -- `ERROR 12` is the only way here --
                                            ; but it no longer prints the wrong thing.
                dw      err_subhosted       ; 13: type mismatch
    IF CLEARPOOL
                dw      err_out_of_str      ; 14: out of string space (D-CLP; was a
    ELSE                                    ; hole until the pool could raise it)
                dw      err_unprintable     ; 14: out of string space (hole)
    ENDIF
                                            ; hole until the pool could raise it)
                dw      err_subhosted       ; 15: String too long (D-MSGSUB, sub-hosted;
                                            ; not raised by any zerobas site)
                dw      err_too_complex     ; 16: string formula too complex
                dw      err_subhosted       ; 17: can't continue
                dw      err_subhosted       ; 18: Undefined user function (D-MSGSUB,
                                            ; sub-hosted; not raised -- DEF FN's own
                                            ; slice would be the raiser)
                dw      err_subhosted       ; 19: Device I/O error (D-MSGSUB, sub-hosted).
                                            ; The load_error family unification that would
                                            ; RAISE it is still its own later item
                                            ; (S1 §9.1) -- this fixes the TEXT only.
                dw      err_verify          ; 20: Verify error. 🎯 D-MSGEXACT: this was a
                                            ; HOLE pointing at "unprintable error" while
                                            ; cload.asm's own err_verify -- already the
                                            ; reference's exact `Verify error`, measured
                                            ; 2026-08-02 on a real CLOAD? mismatch -- sat
                                            ; right there on a separate path. Repointing
                                            ; costs 0 B and is the whole fix: `ERROR 20`
                                            ; now says what the tape path has always said.
                dw      err_no_resume       ; 21: no resume (D-ERR21, docs/spec-basic-
                                            ; err21-no-resume.md -- was a hole until the
                                            ; run loop could raise it: falling off the
                                            ; END of the program while still owing a
                                            ; RESUME. The string and e21_no_resume both
                                            ; live in basic/arrays.asm's low region;
                                            ; this entry also gives `ERROR 21` the right
                                            ; message, which it did not have)
                dw      err_subhosted       ; 22: RESUME without error (raised by
                                            ; raise_error_forced, below)
                dw      err_unprintable     ; 23: unprintable error (self; ERROR n with
                                            ; an out-of-table code, or any hole above)
                dw      err_subhosted       ; 24: missing operand. The table used to stop
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
                dw      err_subhosted       ; 25: line buffer overflow (D-LINEMAX R-2 --
                                            ; the crunched body exceeded TOKMAX_BODY=314).
                                            ; Same two-places-one-fact pair -- and the
                                            ; SECOND place did NOT move when this entry
                                            ; landed: `cp 24` stayed, so this entry was
                                            ; two bytes of DEAD TABLE and `ERROR 25` read
                                            ; `unprintable error` for the whole of
                                            ; D-LINEMAX. Fixed 2026-07-29 (`cp 24` ->
                                            ; `cp 25`, zero bytes). It went unnoticed
                                            ; because the ONLY raiser of 25 -- program.asm
                                            ; dl_overflow -- deliberately bypasses this
                                            ; table (see its header), so linemax-acceptance
                                            ; was green throughout. MEASURED on the
                                            ; VG-8020 before landing: `ERROR 25` ->
                                            ; `Line buffer overflow`, `ERROR 26` ->
                                            ; `Unprintable error` (so 25 IS the bound).
; --- err_subhosted: the whole main-side cost of D-MSGSUB's message text ------
; ONE BYTE. A body consisting of just MSGESC_SUB tells print_msg_stopcr's pm_sub
; arm (basic/program.asm) to dispatch to the sub-ROM page-1 tenant, which reads
; ERRFLG and emits the text itself. err_msgtab's four dense holes (12/15/18/19)
; and rerr_unprintable (the fall-through for EVERY out-of-dense code) point here
; instead of at err_unprintable -- five repoints, zero bytes between them.
;
; 🎯 ITS POSITION IS LOAD-BEARING, NOT LAYOUT. err_unprintable must be the VERY
; NEXT BYTE: when the sub-ROM is absent, subrom_call returns CF=1 without
; calling and pm_sub resumes the decode loop right here, so the machine prints
; `Unprintable error` -- exactly what it printed before this slice, instead of
; nothing. Do not insert anything between these two labels, and do not reorder
; them. tests/test_msgenc.py asserts the adjacency (the same shape as its
; err_overflow/err_linebuf_overflow gap control, and for the same reason: the
; pull to "tidy up" a one-byte string is real).
err_subhosted:  db      MSGESC_SUB          ; D-MSGSUB -- falls through, deliberately
err_unprintable:                            ; D-MSGENC (§4.4): 20 B -> 13 B. Note this
                db      "Unprintable",MSGESC_ERROR,0    ; SHRINKS at the very spot the
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
; out-of-table but in-range code (26..255) still prints "unprintable error" via
; err_msgtab's hole handling -- matching the reference for 26..49 but NOT for the
; disk codes 50..69 (`ERROR 52` -> `Bad file number` there), which is S-FCH-2's
; open item, not this one. HL enters on the ERROR token. Clobbers A, DE, HL.
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
                ld      (ERRFLG),a         ; empirically pinned VG-8020, all four RESUME
                                            ; forms: `0 / 20`, not `0 / 0`). Placed on the
                                            ; trap-active path only (after the ONEFLG!=0
                                            ; check) so ex_resume_noerr (ERR 22) is
                                            ; untouched; a malformed RESUME still aborts
                                            ; with ONEFLG intact (raise_error re-sets its
                                            ; own code, so ERRFLG=0 here is invisible).
                ; 🔴 D-DOTLINE: THERE IS NO `RESUME` WRITER OF `DOT`, AND THIS
                ; SLICE SHIPPED ONE BEFORE ITS OWN KNIFE FOUND IT.
                ; `clp-trap` (handler `50 RESUME NEXT`) and `clp-reslin`
                ; (`50 RESUME 30`) both read 50 and both looked like "a RESUME
                ; records the line it is IN". They have TWO SUFFICIENT CAUSES:
                ; the RESUME sends control to line 30, which then FALLS INTO
                ; line 50 AGAIN, where a second RESUME with no error active
                ; raises ERR 22 *in line 50* -- so record_errline's writer
                ; produces 50 unaided ([[row-with-two-candidate-causes]]).
                ; `clp-res15` was never a RESUME row at all: its handler sits
                ; BEFORE the erroring line, so it runs in sequence and raises
                ; the same ERR 22 there.
                ; 🎯 THE KNIFE THAT REDDENED NOTHING IS WHAT SAID SO. Cutting
                ; the write here moved ZERO of 139 rows -- a rule gated by
                ; nothing ([[knife-that-reddens-nothing-is-the-finding]]) -- and
                ; the row written to settle it, `clp-resend` (`30 A=A+4:END`, so
                ; line 50 is never re-entered), reads **20** on both references
                ; against this build's **50**. An ordinary RESUME leaves `.` on
                ; the ERRORING line. ~12 B of main page 1 recovered, and the
                ; rule withdrawn from the spec rather than pinned.
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
; --- res_ctx: LEAVE the handler and restore the erroring statement's context -
; ONEFLG:=0, CURLINE:=the erroring statement's CURLINE, HL:=its own text pointer
; (SAVTXT, as captured into ERRRESUME at trap time). Clobbers A, HL.
;
; 🔴 THIS WAS A SHARED ROUTINE, WAS INLINED WHEN ITS SECOND CALLER WENT AWAY,
; AND IS NOW SHARED AGAIN -- the comment that used to sit here said "inlined now
; that this is the only remaining site that needs CURLINE restored", and
; D-ONERR0 (docs/spec-basic-onerr0.md §4.2) is the site that makes that false.
; `ON ERROR GOTO 0` inside an active handler needs the IDENTICAL restore before
; it re-raises: the reference reports the ERRORING line, not the handler's, and
; a later CONT resumes at the ERRORING statement -- both measured, three sides
; (docs/onerr0-msx1-characterization.md rows `r.line` and `k.cont`). Re-sharing
; it is a 4-byte routine cost against 6 bytes saved at the new caller, which is
; what let the whole fix land inside main page 1's wall.
; ⚠️ The RESUME <line> arm above still does NOT come here -- it needs ONEFLG:=0
; and nothing else (rp_goto sets CURLINE from GOTOTGT), so it keeps its own
; 4-byte pair rather than paying for a restore it discards.
res_ctx:
                xor     a
                ld      (ONEFLG),a
                ld      hl,(ERRRESUME)
                ld      (CURLINE),hl
                ld      hl,(ERRRESUME+2)
                ret
res_same:                                   ; RESUME / RESUME 0 -> re-run the erroring
                call    res_ctx             ; statement; falls through to res_setptr
res_setptr:
                ld      (RESUMEPTR),hl
                jp      set_resumeflag_ret  ; shares RESUMEFLAG:=1 + ret with RETURN's
                                            ; own tail (program.asm) -- run loop's
                                            ; rp_resume jumps to (RESUMEPTR)

; --- check_expr_errors: shared post-eval() PENDING-ERROR check for --------
; drivers that need no extra stack cleanup before erroring (ex_if, exp_num
; via print.asm). Falls through (returns) if no code is pending. On error,
; fp_runtime_error prints the message and, via print_
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
;
; --- D-PENDERR: THIS ROUTINE AND check_fperr_only ARE NOW THE SAME ROUTINE ---
; (docs/spec-basic-penderr.md §5.1.) It used to open with a TMISMATCH test and a
; second abort tail of its own, and check_fperr_only was the fall-in entry point
; that skipped them. With one pending-error cell there is nothing to skip: both
; names are kept (twelve callers between them, and the DISTINCTION IS STILL
; MEANINGFUL PROSE at each site) but they are the same three instructions, and
; the -10 B is the TMISMATCH test plus the dead `cee_abort_tm` tail.
; ⚠️ The two names are NOT redundant documentation. A caller that entered at
; check_fperr_only was asserting "a type fault cannot be pending here, and if one
; were, aborting on it would be a behaviour change" -- see program.asm's READ site
; and input.asm's, each of which says so in its own comment. That assertion is
; still worth reading even though it is now free.
check_expr_errors:
check_fperr_only:
                ld      a,(FPERR)
                or      a
                jr      nz,cee_abort_fp
                ret
cee_abort_fp:
                pop     hl                  ; discard our own dead resume addr
                jp      fp_runtime_error    ; D-PENDERR: the type fault arrives here too
                                            ; now, as FPERR_TYPEMM -> fperr_to_err 10 ->
                                            ; ERR 13, the SAME code and the SAME
                                            ; err_msgtab entry type_mismatch_error raises

; --- check_expr_errors_popbc: the same check for drivers that must POP a --
; saved key (BC) off the stack before erroring (ex_let; ex_let_
; str enters at cepb_fp directly — str_eval already handles its own D-2
; case via its own `jr nc` to `ex_let_err`, e.g. `A$=HEX$(65536.)`).
; Falls through (returns, BC untouched) if clear. Same
; own-return-address hazard as check_expr_errors above, PLUS the caller's
; own saved key sitting just beneath it -- both must be discarded (in that
; order: ours first, since it's on top) before the abort chain fires.
; D-PENDERR: this was the SECOND hand-rolled copy of the TMISMATCH-then-FPERR
; ordering -- one a fix to check_expr_errors could never have reached, which is
; half of why D-TMFP's reorder was the wrong shape (spec-basic-tmfp.md §3). Its
; TMISMATCH half and its type-mismatch abort tail are gone: -11 B.
check_expr_errors_popbc:
cepb_fp:
                ld      a,(FPERR)
                or      a
                jr      nz,cepb_abort_fp
                ret
cepb_abort_fp:
                pop     hl                  ; discard our own dead resume addr
                pop     bc                  ; discard the caller's saved key
                jp      fp_runtime_error

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
                ld      a,8                 ; ERR 8: undefined line number
                jp      raise_error
; D-MSGMIGRATE: err_line's TEXT is sub-ROM-hosted (em_line, ERRFLG = 8).
; ex_goto_undef above reaches it through raise_error, so ERRFLG is set for it.

; --- ex_if: IF <expr> THEN <clause> [ELSE <clause>] ------------------------
; A clause is either a line number (implicit GOTO) or statements. Condition is
; true when the expression is non-zero (no comparison operators yet).
ex_if:
                inc     hl                  ; past the IF token
                call    skip_spaces
                call    eval                ; DE = condition, HL after expr
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
                call    skip_spaces
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
; --- D-EVALCHK: the CHECKED leaves — eval + the DEFERRED-ERROR test + coerce --
; (docs/spec-basic-evalchk.md.) The two leaves below differ from eval_byte_arg /
; eval_pos_arg by ONE call, and that call is the whole slice: a statement handler
; must surface an error the ARGUMENT EXPRESSION already raised BEFORE it coerces,
; not after.
;
; 🎯 THE ORDER IS THE RULE, MEASURED ON TWO REFERENCES (spec §1, characterization
; §2). fac_to_int_strict does not CLEAR FPERR, so a deferred `1/0` reaches
; get_int16_checked's own check_fperr_only tail and is reported correctly --
; which is why `WIDTH 1/0` was never wrong. But it does WRITE FPERR=1 on an
; out-of-int16 magnitude, OVER THE TOP of the pending FPERR=2, so a value that
; both faulted and overflows reported whichever was written LAST:
;
;   WIDTH 70000+0*(1/0)      VG-8020 / CF-3300: ERR 11    was ERR 6 here
;   WIDTH 70000+0*SQR(-1)    VG-8020 / CF-3300: ERR  5    was ERR 6 here
;   CLEAR 70000+0*(1/0)      VG-8020 / CF-3300: ERR 11    was ERR 6 here
;
; TWO ENTRY POINTS BECAUSE THERE ARE TWO COERCIONS -- WIDTH/FIELD want a byte,
; CLEAR wants an int16 with a sign test -- and they NEST, because get_byte_arg is
; get_int16_checked plus a two-instruction byte stage. So the byte leaf costs 5 B
; rather than 8 ([[the-existing-split-is-cheaper-than-a-new-guard]]).
;
; ⚠️ THE INTERPOSED FRAME IS SAFE, AND THAT WAS CHECKED RATHER THAN ASSUMED
; (spec §3.2). Each call site used to test at the STATEMENT HANDLER's own depth
; and now aborts one frame deeper. Both abort arms reset SP from SAVSTK before
; printing -- raise_error_hl's `ld sp,(SAVSTK)` on the trap path, fre_abort_low's
; on the untrapped one (4d35b6d, docs/spec-basic-abort-depth.md §4, added
; precisely because get_byte_arg's reject used to return INTO ex_width with A =
; the error code). type_mismatch_error and fp_runtime_error both funnel through
; raise_error, so both are covered. The standing detectors are the width probe's
; s0-300 / s0-256 / unt-300 rows: "the error fired AND LINLEN was not scribbled".
;
; Clobbers A. HL (cursor) and DE (the value) survive -- see spec §4.2.
eval_int16_checked:
                call    eval
                call    check_expr_errors   ; TMISMATCH -> ERR 13; a deferred
                                            ; FPERR -> its OWN code, BEFORE the
                                            ; coercion can overwrite it
                jr      get_int16_checked   ; -25, in range (spec §6.2)
; eval_byte_checked: the same, narrowed to 0..255. `jr gba_byte` rather than a
; second `call get_byte_arg`, so the int16 stage is not run twice.
eval_byte_checked:
                call    eval_int16_checked  ; DE = int16 (or aborts)
                jr      gba_byte            ; +17, in range (spec §6.2)

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
; gba_byte — the BYTE stage alone, for a caller that has already run the int16
; one (eval_byte_checked above). A label, not a routine: 0 bytes.
gba_byte:
                ld      a,d
                or      a                   ; high byte set -> >255 or negative
                jr      nz,gb_illegal
                ld      a,e
                ret
gb_illegal:
                ld      a,5
                jp      raise_error         ; ERR 5 illegal function call
