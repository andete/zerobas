; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; arrays.asm — BASIC numeric arrays + DIM (slice 1, SPLIT design, main-ROM
; glue half). docs/spec-basic-arrays.md §10. The array *engine* (ary_find/
; ary_alloc/ary_resolve, the descriptor walk, offset arithmetic, bound
; checks, DIM allocation) now lives in the sub-ROM page-0 tenant
; sub/arrays.asm (SUBROM_IDX_ARY) — a pure-RAM leaf that calls nothing
; resident in the main ROM. This file keeps only the parts that MUST see
; main's `eval`/var machinery (page-0 low region, switched OUT while the
; array tenant runs) or FAC (the float accumulator):
;   - ex_dim: parses `NAME(b0[,b1...])[,...]`, `eval`s each bound, then
;     dispatches to the tenant (op=DIM) for the actual allocation.
;   - ex_let_arr / ev_f_arr: parse + `eval` each subscript, dispatch to the
;     tenant (op=RESOLVE, auto-dim on read) for the element address, then do
;     the FAC<->element copy + type coercion (reusing var_store_fac/
;     var_load_fac's own value-field codec).
;   - ary_reset: rewrites the "no arrays" sentinel at the current
;     PRGEND+2 whenever the program area is rebased (§9.6) — pure RAM,
;     trivial, kept main-side rather than round-tripping through the
;     sub-ROM for a two-byte write.
;   - ary_parse_subs(_kt): the shared "eval a comma-separated int-expr list
;     in parens into the ARY_NIDX/ARY_IDX param-block fields" front end,
;     used by both ex_dim (bound list) and ex_let_arr/ev_f_arr (subscript
;     list) — unchanged in shape from the WIP, just addressed at the new
;     param-block field locations (basic/sysvars.inc §10.2).
;
; Clean-room: array *semantics* are oracle-locked to the public MSX-BASIC
; language reference + the VG-8020 black-box capture (spec §4.1/§5); the
; descriptor layout (owned by sub/arrays.asm) is zerobas's own design. See
; sub/arrays.asm's own header for the split rationale and PROVENANCE.md.

    IF ROM_BASE < $4000

; --- err_subscript / err_redim: fp_runtime_error's message strings for -----
; FPERR 5/7 (interp.asm's fre_msgtab). Homed HERE (the low region) rather
; than alongside interp.asm's other error strings (page 1) because page 1 is
; nearly full (~30 B free pre-slice-1) and these ~49 B do not need to be
; page-1 resident — only the table's own pointer word does, and an absolute
; address costs the same regardless of which region it targets.
; Wording: reference-VERBATIM capitalised text ("Subscript out of range" /
; "Redimensioned array" / "Illegal function call"), NOT the lowercase house
; style of the D-2/D-F2-1 messages — spec §9.5 pins the array error surface
; "exact message text ... oracle-locked", and the §9.7 differential gate
; compares the screen tail against the VG-8020 byte-for-byte. The lowercase
; deviation stays confined to the pre-existing shared messages (overflow /
; division by zero / the shared FPERR=3 illegal-function-call that SQR/LOG
; still raise); the negative-subscript case therefore gets its OWN FPERR
; code (8) + capitalised string below instead of reusing FPERR=3.
err_subscript:
                db      "Subscript out of range",13,10,0
err_redim:
                db      "Redimensioned array",13,10,0
err_illegal_fn_arr:
                db      "Illegal function call",13,10,0

; --- fre_abort_low: the PRDEST-zero + fresh-line + print tail of ------------
; fp_runtime_error/type_mismatch_error (interp.asm page 1 jumps here; the
; body lives in the low region to keep page 1 shrinking, not growing). The
; reference starts every runtime error message at column 0 — if the aborted
; statement left the cursor mid-line (e.g. `PRINT"[";B(-1)` printed the `[`),
; it emits a CRLF first; at column 0 it prints no blank line. Oracle: the
; §9.7 differential tails ('[' then the message on its OWN row). CSRX is the
; 1-based cursor column (C-BIOS sysvar, same source print_comma_zone uses).
; HL = message string; pchar preserves all registers.
fre_abort_low:
                xor     a
                ld      (PRDEST),a          ; error text always goes to the screen
                ld      a,(CSRX)
                cp      2                   ; CSRX is 1-BASED: 1 = column 0. CF for
                                            ; 0 too -- CSRX=0 never occurs on real
                                            ; hardware, but the host unit-test
                                            ; harness (tests/msxtest.py) runs with
                                            ; zeroed RAM and no screen, and must not
                                            ; grow a phantom leading CRLF there.
                jp      c,print_string      ; at line start -> no fresh-line CRLF
                ld      a,13
                call    pchar
                ld      a,10
                call    pchar
                jp      print_string

; --- ary_reset: write the "no arrays" sentinel at the current ARYBASE ------
; (= PRGEND+2). Called whenever the program area may have moved or variables
; are wiped (§9.6): new_prog, run_prog, ex_clear, and relink (program.asm) —
; the last one covers store_line's own edits (Q-9c) AND CLOAD/LOAD's program
; replacement in one shot, since both funnel through relink. Idempotent
; (safe to call more than once). Unchanged from the WIP. Clobbers A, HL.
ary_reset:
                ld      hl,(PRGEND)
                inc     hl
                inc     hl                  ; HL = ARYBASE
                xor     a
                ld      (hl),a
                inc     hl
                ld      (hl),a
                ret

; --- ary_parse_subs: HL=cursor at '(' -> HL advanced past ')'; -------------
; (ARY_NIDX)/(ARY_IDX) filled with the parsed subscript/bound count/values
; (int16, strict domain via fac_to_int_strict — same rule as \, MOD, AND/OR/
; XOR/NOT operands and a variable store, §9.3). On a malformed list (missing
; ','/')') raises the deferred FPERR=4 "syntax error" via ev_f_empty (the
; SAME D-F2-4 malformed-call idiom expr.asm's ev_mc_arg family uses). More
; than MAXDIM subscripts -> FPERR=5 "Subscript out of range" (§9.1 Q-9b).
; Any operand error inside a subscript expression itself (overflow/div0/
; illegal/...) leaves FPERR already set by eval()/fac_to_int_strict — not
; re-checked mid-parse here (first-error-wins, deferred to the statement
; boundary, same discipline as D-F2-1/D-F2-4 elsewhere). Unchanged from the
; WIP other than the ARY_NIDX/ARY_IDX field addresses (basic/sysvars.inc
; §10.2). Clobbers A,B,C,D,E,H,L.
ary_parse_subs:
                inc     hl                  ; past '('
                xor     a
                ld      (ARY_NIDX),a
apsub_lp:
                call    skip_spaces
                call    eval                ; DE=value, HL=cursor advanced
                call    fac_to_int_strict   ; DE=strict int16 (FPERR=1 on overflow)
                ld      a,(ARY_NIDX)
                cp      MAXDIM
                jr      nc,apsub_toomany
                push    hl                  ; guard cursor across the ARY_IDX write
                ld      hl,ARY_IDX
                ld      c,a
                ld      b,0
                add     hl,bc
                add     hl,bc               ; HL = ARY_IDX + 2*a
                ld      (hl),e
                inc     hl
                ld      (hl),d
                pop     hl                  ; cursor restored
                ld      a,(ARY_NIDX)
                inc     a
                ld      (ARY_NIDX),a
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      z,apsub_comma
                cp      ')'
                jr      z,apsub_close
                jp      ev_f_empty          ; malformed list -> deferred syntax error
apsub_comma:
                inc     hl
                jr      apsub_lp
apsub_close:
                inc     hl                  ; past ')'
                ret
apsub_toomany:
                ld      a,5
                ld      (FPERR),a
apsub_skip_lp:
                ld      a,(hl)              ; best-effort: skip to ')' or end of line so
                or      a                   ; the cursor lands somewhere sane (the
                ret     z                   ; statement aborts via FPERR either way)
                cp      ')'
                jr      z,apsub_close
                inc     hl
                jr      apsub_skip_lp

; --- ary_parse_subs_kt: BC=key, A=type, HL=cursor at '(' -> BC=key, A=type --
; (both RESTORED, surviving ary_parse_subs's own eval()-clobbering calls),
; the cursor advanced past ')' left PUSHED on the stack UNDER the return (the
; caller pops it back whenever its own tail is ready for it; HL itself comes
; back holding the return address, i.e. clobbered — no caller reads HL before
; popping [CURSOR]). Shared front-end for every array-reference site (ex_dim's
; own bound-list parse, ex_let_arr/ev_f_arr's own subscript-list parse).
; NOTE the tail: after the two pops the return address is back on top, so the
; cursor must be slid UNDER it — `ex (sp),hl` + `jp (hl)`, NOT `push hl` +
; `ret` (that sequence *returns to the cursor address* and executes the
; tokenised line as code — the slice-1 integration bug, fixed 2026-07-15).
; Clobbers D,E,H,L (+ ary_parse_subs's own A,B,C clobbers, absorbed by the
; restore below).
ary_parse_subs_kt:
                push    bc                  ; [KEY]
                push    af                  ; [TYPE]
                call    ary_parse_subs      ; HL(cursor@'(') -> ARY_NIDX/ARY_IDX, HL past ')'
                pop     af                  ; TYPE restored (ary_parse_subs's own pushes
                pop     bc                  ; are already balanced by its own return, so
                                            ; KEY/TYPE sit exactly where we left them)
                ex      (sp),hl             ; TOS <- [CURSOR]; HL <- the return address
                jp      (hl)                ; return, leaving [CURSOR] on the stack

; --- ary_engine_call: subrom_call to the array tenant (SUBROM_IDX_ARY). ----
; The caller has already filled ARY_OP/ARY_KEY/ARY_TYPE (and ARY_NIDX/
; ARY_IDX, via ary_parse_subs_kt) in the param block. On return: reads
; ARY_ERR; if nonzero, maps it to the matching FPERR code (ary_errmap below)
; and returns NZ; if zero (ok), returns Z. CF from subrom_call itself (the
; sub-ROM absent — never on the merged machine, which always ships it) jumps
; straight to subrom_absent_error and never returns, the same defensive
; convention every other subrom_call site uses (evmc_sqr, list.asm detok,
; interp.asm tokenise). Clobbers A,IX — the caller must guard any live IX
; (e.g. the text cursor) around this call, the same discipline evmc_sqr uses
; across SUBROM_ENTRY_BASE_P1+3*SUBROM_IDX_SQR.
ary_engine_call:
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_ARY
                call    subrom_call
                jp      c,subrom_absent_error
                ld      a,(ARY_ERR)
                or      a
                ret     z
                ld      hl,ary_errmap-1
                ld      d,0
                ld      e,a
                add     hl,de
                ld      a,(hl)
                ld      (FPERR),a
                or      a                   ; ensure NZ (mapped codes are 5/6/7/8,
                                            ; never 0)
                ret
ary_errmap:                                 ; ARY_ERR 1..4 -> FPERR (§4.1 dispositions)
                db      5                   ; 1 Subscript-oor  -> 5 Subscript out of range
                db      8                   ; 2 Illegal-fn/neg -> 8 Illegal function call
                                            ;   (arrays' OWN capitalised message, NOT the
                                            ;   shared lowercase FPERR=3 — see the
                                            ;   err_subscript block comment above)
                db      7                   ; 3 Redimensioned  -> 7 Redimensioned array
                db      6                   ; 4 OOM             -> 6 out of memory

; --- ex_dim: DIM statement. HL enters on the DIM token. ---------------------
; For each comma-separated NAME(b0[,b1...]): reject a `$` string-array name
; (slice 3, Q-9a — plain Syntax error), parse the name, then the bound list
; via ary_parse_subs (reused — a DIM bound list is the identical "comma-
; separated int expr list in parens" shape as a subscript list, §9.4), then
; dispatch to the tenant (op=DIM) for the redim-check + allocation. Loops on
; ','.
ex_dim:
                inc     hl                  ; past the DIM token
ed_lp:
                call    skip_spaces
                call    var_str_type        ; A=1 if a `$` suffix (string array)
                or      a
                jp      nz,stmt_error       ; Q-9a: string arrays are slice 3
                call    var_name_key        ; BC=key, HL past name; (VARTYPE)=type
                call    skip_spaces
                ld      a,(hl)
                cp      '('
                jp      nz,stmt_error       ; DIM requires a bound list
                ld      a,(VARTYPE)
                call    ary_parse_subs_kt   ; BC,A,HL(@'(') -> BC,A restored (key,type);
                                            ; fills ARY_NIDX/ARY_IDX; [CURSOR] pushed
                ld      d,a                 ; stash TYPE across the FPERR peek
                ld      a,(FPERR)
                or      a
                jr      nz,ed_abort         ; the bound-list parse already aborted
                ld      (ARY_KEY),bc
                ld      a,d                 ; TYPE restored
                ld      (ARY_TYPE),a
                ld      a,1
                ld      (ARY_OP),a          ; op = DIM
                call    ary_engine_call     ; -> Z ok / NZ: FPERR already mapped+set
                jr      nz,ed_abort
                pop     hl                  ; [CURSOR] restored
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      nz,ed_done
                inc     hl
                jr      ed_lp
ed_done:
                jp      exec_stmt
ed_abort:
                pop     hl                  ; discard [CURSOR] (balance the stack)
                jp      fp_runtime_error

; --- ary_store_write: HL=element address, A=type(2/4/8); DE valid iff the -
; current FACTYP==2, else FAC/FACTYP hold the RHS's float value (the SAME
; RHS contract var_store_fac's own tail uses). Coerces into `type` and
; writes elsize bytes at HL — mirrors var_store_fac's own coercion +
; value-field write exactly (fac_to_int_strict / round_single_and_pack /
; round_and_finalize), just addressed directly instead of via
; var_alloc_or_find. On a coercion-time Overflow, sets FPERR and returns
; WITHOUT writing (mirrors var_store_fac's own D-F2-1 contract). Reuses
; vars.asm's VS_TARGET_TYPE/VS_INT_VAL scratch — dead here (var_store_fac
; isn't concurrently running; single-threaded interpreter). Unchanged from
; the WIP. Clobbers A,B,C,D,E,H,L.
ary_store_write:
                ld      (VS_TARGET_TYPE),a
                push    hl                  ; guard the element address across coercion
                cp      2
                jr      z,asw_int
                cp      4
                jr      z,asw_single
                ld      hl,ARGA
                call    widen_rhs_operand
                call    round_and_finalize
                jr      asw_coerced
asw_single:
                ld      hl,ARGA
                call    widen_rhs_operand
                call    round_single_and_pack
                jr      asw_coerced
asw_int:
                call    fac_to_int_strict   ; -> DE (truncate, strict int16);
                                            ; sets FPERR=1 on overflow
                ld      (VS_INT_VAL),de     ; stash: var_store_fac's own comment applies
                                            ; verbatim (DE must survive to the write-back)
asw_coerced:
                pop     hl                  ; element address restored
                ld      a,(FPERR)
                or      a
                ret     nz                  ; coercion overflow -> drop the store
                ld      a,(VS_TARGET_TYPE)
                cp      2
                jr      z,asw_wb_int
                ld      c,a                 ; byte count (4 single / 8 double)
                ld      b,0
                push    hl
                pop     de                  ; DE = dest (element address)
                ld      hl,FAC
                ldir                        ; FAC -> element address, verbatim
                ret
asw_wb_int:
                ld      de,(VS_INT_VAL)     ; the coerced value
                ld      (hl),e
                inc     hl
                ld      (hl),d
                ret

; --- ex_let_arr: array-element assignment  A(i[,j...]) = <expr> -----------
; BC=key, (VARTYPE)=type, HL=cursor at '(' on entry (reached from ex_let,
; interp.asm, right after var_name_key). Resolves the element address via
; the sub-ROM tenant (op=RESOLVE) BEFORE evaluating the RHS (so a self-
; referencing RHS like A(1)=B(2), or even A(1)=A(1)+1, can freely reuse the
; shared param-block subscript scratch without disturbing an already-
; resolved LHS target — ary_parse_subs's own ARY_NIDX/ARY_IDX are transient,
; reused by every array reference), then coerces+stores exactly like the
; scalar path (var_store_fac's own D-F2-1 contract, mirrored by
; ary_store_write above).
ex_let_arr:
                ld      a,(VARTYPE)
                call    ary_parse_subs_kt   ; BC,A restored (key,type); ARY_NIDX/ARY_IDX
                                            ; filled; [CURSOR] pushed
                ld      (ARY_KEY),bc
                ld      (ARY_TYPE),a
                ld      a,(FPERR)
                or      a
                jr      nz,ela_parse_abort  ; malformed subscript list / overflow
                xor     a
                ld      (ARY_OP),a          ; op = 0 (RESOLVE)
                call    ary_engine_call     ; -> Z ok / NZ: FPERR already mapped+set
                jr      nz,ela_resolve_abort
                pop     hl                  ; [CURSOR] restored
                ld      de,(ARY_ADDR)
                push    de                  ; [ADDR]
                ld      a,(ARY_TYPE)
                push    af                  ; [TYPE]
                call    skip_spaces
                ld      a,(hl)
                cp      EQ_TOKEN
                jr      nz,ela_err
                inc     hl
                call    eval                ; DE=RHS value, HL=cursor advanced
                ld      a,(TMISMATCH)
                or      a
                jr      nz,ela_abort_tm
                ld      a,(FPERR)
                or      a
                jr      nz,ela_abort_fp
                push    hl                  ; [CURSOR]
                pop     ix                  ; IX = cursor (free to reuse here — nothing
                                            ; in this statement chain relies on the
                                            ; caller's IX surviving through ex_let_arr)
                pop     af                  ; TYPE
                pop     hl                  ; ADDR (into HL — DE holds the live RHS
                                            ; value/FAC, which ary_store_write reads)
                call    ary_store_write     ; HL=elem addr,A=type; DE/FAC=RHS -> writes
                push    ix
                pop     hl                  ; HL = cursor restored
                ld      a,(FPERR)
                or      a
                jp      nz,fp_runtime_error ; coercion-time overflow (D-F2-1 pattern)
                jp      exec_stmt
ela_err:
                pop     af
                pop     de                  ; discard [TYPE],[ADDR]
                jp      stmt_error
ela_abort_tm:
                pop     af
                pop     de                  ; discard [TYPE],[ADDR]
                jp      type_mismatch_error
ela_abort_fp:
                pop     af
                pop     de                  ; discard [TYPE],[ADDR]
                jp      fp_runtime_error
ela_parse_abort:
                pop     hl                  ; discard [CURSOR]
                jp      fp_runtime_error
ela_resolve_abort:
                pop     hl                  ; discard [CURSOR]
                jp      fp_runtime_error

; --- ev_f_arr: array-element rvalue  A(i[,j...])  --------------------------
; BC=key, (VARTYPE)=type, HL=cursor at '(' on entry (reached from ev_f_var,
; expr.asm, right after var_name_key — ev_f reaches ev_f_var only for a
; plain letter, never a function token, so a '(' right after a plain name is
; unambiguously a subscript, §5/§9.4). Resolves via the sub-ROM tenant
; (op=RESOLVE, auto-dim on read), then loads FAC/FACTYP + the DE int16 fast
; path exactly like var_load_fac's own value-field read. Every array
; evaluation error is DEFERRED (matches ev_f_err's own convention: FPERR set,
; DE=0, checked at the statement boundary) — never an immediate `jp` out of
; the evaluator, the same D-F2-1 discipline the WIP's ary_load already
; followed.
ev_f_arr:
                ld      a,(VARTYPE)
                call    ary_parse_subs_kt   ; BC,A restored; ARY_NIDX/ARY_IDX filled;
                                            ; [CURSOR] pushed. A malformed list already
                                            ; set a deferred FPERR (ev_f_empty/
                                            ; apsub_toomany) but still returns normally.
                ld      (ARY_KEY),bc
                ld      (ARY_TYPE),a
                ld      a,(FPERR)
                or      a
                jr      nz,eva_deferred     ; parse-time error already deferred
                xor     a
                ld      (ARY_OP),a          ; op = 0 (RESOLVE, auto-dim on read)
                call    ary_engine_call     ; -> Z ok / NZ: FPERR already mapped+set
                                            ; (deferred, matches ary_resolve's own
                                            ; original convention)
                jr      nz,eva_deferred
                pop     hl                  ; [CURSOR] restored
                push    hl
                pop     ix                  ; IX = cursor (ev_f_var's own return contract)
                ld      hl,(ARY_ADDR)
                ld      a,(ARY_TYPE)
                cp      2
                jr      z,eva_int
                ld      (FACTYP),a
                ld      c,a
                ld      b,0
                ld      de,FAC
                ldir                        ; (HL=elem addr) -> (DE=FAC), elsize bytes
                call    flt_to_int16        ; DE = int16 fast path (FACTYP untouched)
                ret
eva_int:
                ld      (FACTYP),a
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = the loaded value
                ret
eva_deferred:
                pop     hl                  ; [CURSOR] restored
                push    hl
                pop     ix                  ; IX = cursor (ev_f_var's contract even on
                                            ; a deferred error)
                ld      de,0                ; matches ev_f_err's own convention
                ret

    ENDIF
