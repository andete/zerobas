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
;   - vars_reset / ary_reset: arrays slice-4b (docs/spec-basic-arrays-
;     slice4b-scalar-reloc.md §3b) — vars_reset re-anchors ARYTAB=PRGEND+2
;     (the scalar region) then falls into ary_reset, which rewrites the "no
;     arrays" sentinel at the (now current) ARYTAB, whenever the program
;     area is rebased (§9.6) — pure RAM, trivial, kept main-side rather than
;     round-tripping through the sub-ROM for a two-byte write.
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
err_mem_arr:                                ; FPERR=6 (fre_msgtab entry 6) is set ONLY
                db      "Out of memory",13,10,0
                                            ; by ary_errmap (DIM/auto-dim OOM), so the
                                            ; whole FPERR=6 surface takes the reference-
                                            ; verbatim capitalised text (§9.5, same rule
                                            ; as err_subscript above; verified: VG-8020
                                            ; DIM X(5000) -> "Out of memory",
                                            ; 2026-07-15). program.asm's own lowercase
                                            ; err_mem (store_line's crunch-time OOM,
                                            ; printed directly, never via FPERR) is
                                            ; untouched.
err_syntax:                                 ; interp.asm's own stmt_error + fre_msgtab
                db      "syntax error",13,10,0
                                            ; entry 4 (D-F2-3) both reference this by
                                            ; absolute address; relocated here (repack
                                            ; only -- interp.asm keeps its own copy for
                                            ; the lean build) by the slice-3 space
                                            ; audit: page-1 was 7 B short even after
                                            ; the ary_op0_resolve dedup, and this
                                            ; string's home is unobserved (arrays
                                            ; slice-3, docs/spec-basic-arrays-slice3-
                                            ; strings.md §5.3).

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

; --- vars_reset: re-anchor ARYTAB = PRGEND+2 (empty scalar region), then ---
; fall through into ary_reset to write the "no arrays" sentinel at the (now
; freshly re-anchored) ARYTAB. Arrays slice-4b (docs/spec-basic-arrays-
; slice4b-scalar-reloc.md §3b/Q2): a scalar's chain address is PRGEND-
; relative, so whenever PRGEND moves (every program edit) the scalar region's
; base moves under it — the two regions MUST reset together, or the "old"
; scalars sit at the WRONG address (or under program text). This is also the
; deliberate MSX-faithful behaviour change from pre-4b zerobas (which kept
; scalars across a direct-mode edit as an artifact of the off-to-the-side
; fixed pool): stock MSX-BASIC clears ALL variables on a program edit too.
; The four call sites that used to call ary_reset directly (new_prog,
; run_prog, ex_clear, relink) now call THIS instead, so scalar + array reset
; stay a single call at each site (§3b). Clobbers A, HL.
vars_reset:
                ld      hl,(PRGEND)
                inc     hl
                inc     hl                  ; HL = PRGEND+2 (empty scalar region)
                ld      (ARYTAB),hl
                ; fall through: write the "no arrays" sentinel at (ARYTAB)

; --- ary_reset: write the "no arrays" sentinel at the current ARYTAB -------
; (= ARYBASE). Idempotent (safe to call more than once); re-anchored from
; the pre-4b `(PRGEND)+2` derivation onto the STORED `ARYTAB` cell (§4).
; Reached both via vars_reset's own fall-through (the normal path, every
; external call site) and callable standalone (kept as a separate label for
; clarity — no code currently calls it directly any more). Clobbers A, HL.
ary_reset:
                ld      hl,(ARYTAB)         ; HL = ARYBASE
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
; boundary, same discipline as D-F2-1/D-F2-4 elsewhere).
;
; RE-ENTRANCY (slice-1 fix 2026-07-15): a subscript expression can itself
; contain an array rvalue — X(X(0)) — whose inner ev_f_arr runs THIS parse
; again, on the same global ARY_NIDX/ARY_IDX block. The WIP wrote the block
; incrementally per subscript, so the inner parse clobbered the outer's
; partial count/values ("Subscript out of range" on every nested subscript).
; Now the values are collected on the CPU STACK during the loop — each
; nesting level gets its own stack region for free — and the block is
; written ATOMICALLY only at the close paren, after the last eval() has
; returned: any inner parse's whole write+resolve+read sequence completes
; strictly before (never interleaved with) the outer's single block write.
; Loop stack shape between evals: [COUNT(B), v_{n-1} .. v_0, RET] — the
; count word rides ON TOP so eval's own balanced pushes never disturb it.
; Clobbers A,B,C,D,E,H,L + IX (IX is free here: every caller's next step is
; ary_engine_call, which clobbers IX anyway).
ary_parse_subs:
                inc     hl                  ; past '('
                ld      b,0
                push    bc                  ; [COUNT] = 0 (C = don't-care)
apsub_lp:
                call    skip_spaces
                call    eval                ; DE=value, HL=cursor advanced
                push    hl                  ; guard the cursor: fac_to_int_strict
                                            ; CLOBBERS HL on the float path (FACTYP
                                            ; 4/8 -> domain_convert_core) while the
                                            ; FACTYP=2 path returns early with HL
                                            ; intact -- exactly why literal
                                            ; subscripts worked and variable ones
                                            ; (default DOUBLE) hit the ','/')' check
                                            ; with a trashed cursor -> phantom
                                            ; "syntax error" (slice-1 fix
                                            ; 2026-07-15). Same push/pop idiom as
                                            ; eval_addr (float-arith.asm).
                call    fac_to_int_strict   ; DE=strict int16 (FPERR=1 on overflow)
                pop     hl                  ; cursor restored
                pop     bc                  ; B = count so far
                ld      a,b
                cp      MAXDIM
                jr      nc,apsub_toomany
                push    de                  ; [VALUE] collected on the stack
                inc     b
                push    bc                  ; [COUNT] back on top
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      z,apsub_comma
                cp      ')'
                jr      z,apsub_close
                pop     bc                  ; malformed list: unwind [COUNT]+values
apsub_mf_drop:
                pop     de                  ; (B>=1 here — a value was just pushed)
                djnz    apsub_mf_drop
                jp      ev_f_empty          ; -> deferred syntax error
apsub_comma:
                inc     hl
                jr      apsub_lp
apsub_close:
                inc     hl                  ; past ')'
                push    hl
                pop     ix                  ; IX = cursor (parked across the pops)
                pop     bc                  ; B = n (1..MAXDIM)
                ld      a,b
                ld      (ARY_NIDX),a        ; the block write happens ONLY here,
                add     a,a                 ; after every subscript eval is done
                ld      hl,ARY_IDX
                add     a,l
                ld      l,a
                adc     a,h
                sub     l
                ld      h,a                 ; HL = ARY_IDX + 2n (values pop in
                                            ; reverse: last subscript first)
apsub_wr_lp:
                pop     de
                dec     hl
                ld      (hl),d
                dec     hl
                ld      (hl),e
                djnz    apsub_wr_lp
                push    ix
                pop     hl                  ; HL = cursor (past ')')
                ret
apsub_toomany:                              ; B = MAXDIM values already on the stack
                ld      a,5
                ld      (FPERR),a
apsub_tm_drop:
                pop     de                  ; unwind the collected values (B=MAXDIM
                djnz    apsub_tm_drop       ; here, never 0)
apsub_skip_lp:
                ld      a,(hl)              ; best-effort: skip to ')' or end of line so
                or      a                   ; the cursor lands somewhere sane (the
                ret     z                   ; statement aborts via FPERR either way)
                cp      ')'
                jr      z,apsub_skip_done
                inc     hl
                jr      apsub_skip_lp
apsub_skip_done:
                inc     hl                  ; past ')'
                ret

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
                add     hl,de               ; Z80 ADD HL,rr affects C/H/N only --
                                            ; S/Z/P-V are UNCHANGED (documented Z80
                                            ; behaviour), so the NZ this routine
                                            ; must return is STILL the one the `or a`
                                            ; above set (A was nonzero, else we'd
                                            ; have taken `ret z`) and survives,
                                            ; untouched, through every instruction
                                            ; between here and the final `ret` below
                                            ; (none of LD (nn),A / LD A,(HL) / LD
                                            ; A,(nn) touch flags either) -- slice-3
                                            ; space audit: the trailing "ensure NZ"
                                            ; `or a` this comment replaces was
                                            ; therefore provably redundant
                ld      a,(hl)
                ld      (FPERR),a
                ret
ary_errmap:                                 ; ARY_ERR 1..4 -> FPERR (§4.1 dispositions)
                db      5                   ; 1 Subscript-oor  -> 5 Subscript out of range
                db      8                   ; 2 Illegal-fn/neg -> 8 Illegal function call
                                            ;   (arrays' OWN capitalised message, NOT the
                                            ;   shared lowercase FPERR=3 — see the
                                            ;   err_subscript block comment above)
                db      7                   ; 3 Redimensioned  -> 7 Redimensioned array
                db      6                   ; 4 OOM             -> 6 Out of memory
                                            ;   (arrays' OWN capitalised string too --
                                            ;   err_mem_arr above; FPERR=6 has no other
                                            ;   setter)

; --- ex_dim: DIM statement. HL enters on the DIM token. ---------------------
; For each comma-separated NAME(b0[,b1...]): parse the name (a `$` string
; name is now LIVE, arrays slice 3, docs/spec-basic-arrays-slice3-strings.md
; §5.2 -- the old Q-9a reject is gone), then the bound list via ary_parse_subs
; (reused — a DIM bound list is the identical "comma-separated int expr list
; in parens" shape as a subscript list, §9.4), then dispatch to the tenant
; (op=DIM) for the redim-check + allocation. Loops on ','.
;
; String-ness detection mirrors ex_erase's own var_str_type-first idiom
; (docs/spec-basic-arrays-slice2-erase.md §4.1, the F1 lesson): var_name_key's
; own (VARTYPE) canNOT be trusted for a `$` name (vnk_dollar hardcodes
; VARTYPE=8, identical to a default-double `A`), so the string-ness flag is
; captured BEFORE var_name_key (which clobbers everything, incl. flags) and
; carried across it on the stack, then used to FORCE type=1 for a string name
; rather than trusting VARTYPE. This is what makes `DIM S$(5)` allocate a
; real type=1 (string) descriptor instead of an 8-byte-element double one.
ex_dim:
                inc     hl                  ; past the DIM token
ed_lp:
                call    skip_spaces         ; A = (hl), first non-space char
                call    is_letter           ; a DIM target must START with a letter;
                jp      nc,stmt_error       ; reject bare `$` / a digit name (D1,
                                            ; slice-3 adversarial catch: `DIM $(5)`
                                            ; and `DIM 1(5)` were silently accepted
                                            ; -- the deleted slice-2 `$`-reject had
                                            ; masked exactly this). Mirrors ex_erase's
                                            ; own is_letter guard below.
                call    var_str_type        ; A=1/CF set iff a `$` suffix (or a
                                            ; DEFSTR-defaulted bare name) --
                                            ; string array. HL NOT advanced.
                push    af                  ; [STR?] -- survives var_name_key
                call    var_name_key        ; BC=key, HL past name; (VARTYPE)=type
                call    skip_spaces
                ld      a,(hl)
                cp      '('
                jr      z,ed_haveparen
                jr      ee_synerr_pop       ; DIM requires a bound list -- shares
                                            ; ex_erase's own identical "pop [STR?];
                                            ; jp stmt_error" tail (below in this
                                            ; file), slice-3 space audit
ed_haveparen:
                pop     af                  ; recover string-ness (CF set iff string)
                ld      a,(VARTYPE)         ; numeric default: type 2/4/8 as parsed
                jr      nc,ed_settype
                ld      a,1                 ; string name -> FORCE type=1 (the F1
                                            ; lesson above): ary_alloc/ary_resolve
                                            ; then size it via elsize_from_type
                                            ; (sub/arrays.asm §4), not as an
                                            ; 8-byte-element double
ed_settype:
                call    ary_parse_subs_kt   ; BC,A,HL(@'(') -> BC,A restored (key,type);
                                            ; fills ARY_NIDX/ARY_IDX; [CURSOR] pushed
                ld      d,a                 ; stash TYPE across the FPERR peek
                ld      a,(FPERR)
                or      a
                jp      nz,ela_parse_abort  ; the bound-list parse already aborted --
                                            ; shares ex_let_arr's own identical
                                            ; "pop [CURSOR];jp fp_runtime_error" stub
                                            ; (below in this file; a plain `jr` can't
                                            ; reach that far, hence `jp` here, still a
                                            ; net win over a THIRD local copy of the
                                            ; 4-byte body, slice-3 space audit)
                ld      (ARY_KEY),bc
                ld      a,d                 ; TYPE restored
                ld      (ARY_TYPE),a
                ld      a,1
                ld      (ARY_OP),a          ; op = DIM
                call    ary_engine_call     ; -> Z ok / NZ: FPERR already mapped+set
                jp      nz,ela_parse_abort
                pop     hl                  ; [CURSOR] restored
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      nz,ed_done
                inc     hl
                jr      ed_lp
ed_done:
                jp      exec_stmt

; --- ex_erase: ERASE statement. HL enters on the ERASE token. --------------
; docs/spec-basic-arrays-slice2-erase.md §4.1. For each comma-separated bare
; NAME (no bound/subscript list): detect string-ness (var_str_type) then parse
; the name+type via var_name_key -- shared identity derivation, the slice-1
; lesson: any drift in (name0,name1,type) desyncs ary_find -- then dispatch to
; the tenant (op=ERASE) to free it. A STRING name (explicit `$` OR a DEFSTR-
; defaulted bare name) is FORCED to type=1 so ary_find can never match a
; numeric array; unlike ex_dim, a `$` name is NOT rejected up front -- it just
; falls through to Tier-B IFC (reference-faithful, since string arrays don't
; exist until slice 3, §1). (F1 fix 2026-07-15: keying on (VARTYPE) alone was
; WRONG -- var_name_key's vnk_dollar hardcodes VARTYPE=8 for a `$` suffix,
; identical to a default DOUBLE, so `ERASE A$` matched+freed the numeric `A`.
; The type-1 force below is what makes the string key distinct; see the inline
; comment at the var_str_type call.) Two-tier error split (§3):
;   Tier A `stmt_error` (lowercase house-style "syntax error", NOT the
;     reference's capitalised "Syntax error" -- same documented deviation as
;     every other zerobas syntax error) -- a malformed token where a NAME is
;     expected (bare ERASE / leading,trailing,double comma / a digit), or a
;     `(` right after a name (ERASE A() / ERASE A(1), which tokenise fine but
;     are a subscript/paren FORM error at statement execution).
;   Tier B `fp_runtime_error` (ARY_ERR=2 -> ary_errmap -> FPERR=8, the
;     reference-verbatim capitalised "Illegal function call", arrays' own
;     string above) -- a well-formed bare name that ary_find can't match (never
;     dimmed/auto-dimmed, already erased, or a type mismatch -- type is part
;     of array identity, slice-1 §4.1 #7).
; Left-to-right, first-bad-name-wins (§3): a name already processed before an
; abort stays erased (only observable via ON ERROR, out of scope, matches the
; oracle's own `erase.partial.A.first`/`erase.badname.first` captures).
;
; Simpler than ex_dim in one way (no bound list to parse, so no
; ary_parse_subs_kt call) but the SAME in another: ary_engine_call still needs
; the cursor parked on the stack across it, NOT left in HL. subrom_call's own
; "HL/DE pass through" note (basic/subromcall.asm) means the caller's HL rides
; INTO the sub-ROM tenant and comes back holding whatever the tenant (which
; clobbers everything, tenant convention) last left there -- never restored.
; ex_dim/ex_let_arr/ev_f_arr all already park the cursor on the stack for
; exactly this reason (via ary_parse_subs_kt's own [CURSOR] push); ex_erase has
; no subscript parse to piggyback that push on, so it pushes explicitly right
; around this call instead (adversarial-differential catch, 2026-07-15: a
; literal `ERASE A` on a previously-DIM'd array corrupted the cursor and threw
; a phantom "syntax error" on the FOLLOWING statement -- the not-found/Tier-B
; path never showed it, because fp_runtime_error abandons the cursor anyway).
ex_erase:
                inc     hl                  ; past the ERASE token
ee_lp:
                call    skip_spaces         ; A = (hl), the first non-space char
                call    is_letter           ; CF set = letter. This ONE peek covers
                                            ; every Tier-A "no name where a name is
                                            ; expected" case: bare ERASE (EOL), a
                                            ; leading/trailing/double comma (','),
                                            ; and a numeric argument (digit) --
                                            ; none of those set CF.
                jp      nc,stmt_error
                call    var_str_type        ; A=1 / CF set iff this is a STRING name --
                                            ; the unifying detector for BOTH an explicit
                                            ; `$` suffix AND a DEFSTR-defaulted bare name
                                            ; (basic/vars.asm). HL is NOT advanced. Needed
                                            ; because var_name_key's own (VARTYPE) can't
                                            ; distinguish a `$` name from a default DOUBLE:
                                            ; vnk_dollar hardcodes VARTYPE=8 (== type 8,
                                            ; double), so keying on (VARTYPE) alone would
                                            ; make `ERASE A$` match+free the numeric `A`
                                            ; (F1, 2026-07-15). Same var_str_type-first
                                            ; idiom ex_dim/LET/PRINT use to pick the
                                            ; string path before the real name advance.
                push    af                  ; [STRFLAG] -- CF/A survive var_name_key
                                            ; (which clobbers everything, incl. the flags
                                            ; and var_str_type's own B/DE scratch)
                call    var_name_key        ; BC=key, HL past name; (VARTYPE)=type
                call    skip_spaces
                ld      a,(hl)
                cp      '('
                jr      z,ee_synerr_pop     ; Tier A: 'ERASE A(' -- subscript/paren form
                                            ; (ERASE A(1)/A()) is a syntax error, not a
                                            ; lookup. Must POP [STRFLAG] first (below).
                ld      (ARY_KEY),bc
                pop     af                  ; recover string-ness (CF set iff string).
                                            ; LD (below) doesn't touch flags, so CF
                                            ; survives to the jr nc.
                ld      a,(VARTYPE)         ; numeric default: type 2/4/8 as-is
                jr      nc,ee_settype
                ld      a,1                 ; STRING name -> force type=1: no numeric
                                            ; array (2/4/8) can carry it, so ary_find
                                            ; never matches -> Tier-B IFC. Reference-
                                            ; faithful for slice 2 (string arrays don't
                                            ; exist yet, §1 divergence): explicit `$`
                                            ; AND DEFSTR-bare both land here uniformly.
                                            ; Slice 3 makes string arrays real and this
                                            ; key starts matching them.
ee_settype:
                ld      (ARY_TYPE),a
                ld      a,2
                ld      (ARY_OP),a          ; op = ERASE
                push    hl                  ; [CURSOR] -- guard across ary_engine_call
                                            ; (see the header comment above: the tenant
                                            ; clobbers HL, so it cannot ride in a
                                            ; register through this call)
                call    ary_engine_call     ; -> Z ok / NZ: FPERR already mapped+set
                                            ; (ARY_ERR=2 -> FPERR=8, Tier B)
                pop     hl                  ; [CURSOR] restored either way (harmless on
                                            ; the abort path too -- fp_runtime_error
                                            ; never reads HL, just tidy stack balance)
                jp      nz,fp_runtime_error
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      nz,ee_done
                inc     hl
                jr      ee_lp               ; next name
ee_done:
                jp      exec_stmt
ee_synerr_pop:
                pop     af                  ; discard [STRFLAG] (balance the stack) before
                                            ; the Tier-A abort -- the '(' check is the one
                                            ; exit that happens with [STRFLAG] still live
                jp      stmt_error

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
; ary_op0_resolve (the sub-ROM tenant op=RESOLVE, wrapped) BEFORE evaluating
; the RHS (so a self-referencing RHS like A(1)=B(2), or even A(1)=A(1)+1, can
; freely reuse the shared param-block subscript scratch without disturbing an
; already-resolved LHS target — ary_parse_subs's own ARY_NIDX/ARY_IDX are
; transient, reused by every array reference), then coerces+stores exactly
; like the scalar path (var_store_fac's own D-F2-1 contract, mirrored by
; ary_store_write above). ary_op0_resolve was originally this routine's own
; inlined prologue (parse-subs + fill ARY_KEY/TYPE + check FPERR + RESOLVE +
; check NZ), generalised out to a shared TYPE-parameterised helper (also used
; by the string array glue, below) once the slice-3 space audit needed the
; low-region bytes back.
;
; §13a FIX (docs/spec-basic-arrays-slice4b-scalar-reloc.md §13a, 2026-07-17):
; the RHS `eval` below can itself allocate a numeric SCALAR (VARPTR(newvar) is
; the only eval-time scalar allocator — a plain variable read is find-only).
; Slice-4b's insert-and-shift (§3a) means a scalar allocation shifts the
; WHOLE array region up by the entry's stride — so the element address
; resolved above goes STALE the instant `eval` allocates one. Documented
; MSX memory model (arc TXTTAB->VARTAB->ARYTAB->...): everything at or above
; ARYTAB shifts by exactly the amount ARYTAB itself moves, so the fix is a
; before/after ARYTAB delta correction. `ary_snapshot_offset`/
; `ary_apply_offset` (basic/vars.asm, page-1 — the low region has no headroom
; left for this arithmetic, §13a "the hard part") do the actual work; this
; routine only adds two 3-byte CALLs (replacing the old bare push/pop of a
; raw element address) — net LOW-REGION-NEGATIVE once ela_err/ela_abort_tm/
; ela_abort_fp relocate alongside them (below).
ex_let_arr:
                ld      a,(VARTYPE)
                call    ary_op0_resolve     ; Z: HL=cursor,DE=elem_addr / NZ:
                                            ; HL=cursor, FPERR already set
                jp      nz,fp_runtime_error ; [CURSOR] already consumed by
                                            ; ary_op0_resolve -- nothing to pop
                call    ary_snapshot_offset ; §13a: push [OFFSET]=ARYTAB-ADDR
                                            ; (page-1); HL=cursor preserved
                ld      a,(ARY_TYPE)
                push    af                  ; [TYPE]
                call    skip_spaces
                ld      a,(hl)
                cp      EQ_TOKEN
                jp      nz,ela_err
                inc     hl
                call    eval                ; DE=RHS value, HL=cursor advanced
                ld      a,(TMISMATCH)
                or      a
                jp      nz,ela_abort_tm
                ld      a,(FPERR)
                or      a
                jp      nz,ela_abort_fp
                push    hl                  ; [CURSOR]
                pop     ix                  ; IX = cursor (free to reuse here — nothing
                                            ; in this statement chain relies on the
                                            ; caller's IX surviving through ex_let_arr)
                pop     af                  ; TYPE
                call    ary_apply_offset    ; §13a: pops [OFFSET], HL = the
                                            ; CORRECTED element address (DE
                                            ; holds the live RHS value/FAC,
                                            ; untouched, which ary_store_write
                                            ; reads)
                call    ary_store_write     ; HL=elem addr,A=type; DE/FAC=RHS -> writes
                push    ix
                pop     hl                  ; HL = cursor restored
                ld      a,(FPERR)
                or      a
                jp      nz,fp_runtime_error ; coercion-time overflow (D-F2-1 pattern)
                jp      exec_stmt
ela_parse_abort:
                pop     hl                  ; discard [CURSOR]
                jp      fp_runtime_error
; ela_err/ela_abort_tm/ela_abort_fp themselves RELOCATED to basic/vars.asm
; (page-1, §13a space fix) — reached via the `jp` (not `jr`, now out of
; branch range) above. Each still discards exactly TWO stack words
; ([TYPE],[OFFSET] — the SAME word count as the pre-fix [TYPE],[ADDR] frame,
; since ary_snapshot_offset collapses the old two-word ADDR+ARYTAB-snapshot
; into one), so their bodies are byte-identical to the pre-fix ones, only
; moved.

; --- ev_f_arr: array-element rvalue  A(i[,j...])  --------------------------
; BC=key, (VARTYPE)=type, HL=cursor at '(' on entry (reached from ev_f_var,
; expr.asm, right after var_name_key — ev_f reaches ev_f_var only for a
; plain letter, never a function token, so a '(' right after a plain name is
; unambiguously a subscript, §5/§9.4). Resolves via ary_op0_resolve (the sub-
; ROM tenant op=RESOLVE, wrapped; auto-dim on read), then loads FAC/FACTYP +
; the DE int16 fast path exactly like var_load_fac's own value-field read.
; Every array evaluation error is DEFERRED (matches ev_f_err's own
; convention: FPERR set, DE=0, checked at the statement boundary) — never an
; immediate `jp` out of the evaluator, the same D-F2-1 discipline the WIP's
; ary_load already followed. ary_op0_resolve's own error return (NZ, HL=
; cursor already popped, whether from a parse-time deferred FPERR — ev_f_
; empty/apsub_toomany — or a resolve-time one) lands exactly on eva_deferred
; below with nothing further to unwind.
ev_f_arr:
                ld      a,(VARTYPE)
                call    ary_op0_resolve     ; Z: HL=cursor,DE=elem_addr / NZ:
                                            ; HL=cursor, FPERR already set (deferred)
                jr      nz,eva_deferred
                push    hl
                pop     ix                  ; IX = cursor (ev_f_var's own return contract)
                ex      de,hl               ; HL = elem addr (DE dead)
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
                push    hl
                pop     ix                  ; IX = cursor (ev_f_var's contract even on
                                            ; a deferred error)
                ld      de,0                ; matches ev_f_err's own convention
                ret

; =============================================================================
; Arrays slice 3 — STRING arrays (docs/spec-basic-arrays-slice3-strings.md).
; The tenant (sub/arrays.asm) now sizes/zero-fills a type=1 element as an
; inline [len][bytes:STRMAX] value via elsize_from_type (§4) — ary_find/DIM/
; RESOLVE/bound/neg/ndim checks are otherwise UNCHANGED. The STORE COPY body
; itself is ALSO tenant-side now (op=3 COPY_STR, sub/arrays.asm's
; aeng_copy_str) — unlike the numeric store (which needs FAC/type coercion, a
; main-only concept), a string element store is a pure-RAM length-clamped
; LDIR, a textbook shape-C leaf carve-out (subrom-tenant-playbook.md §3) that
; the razor-thin low region (§5.3) cannot otherwise afford. What's left here
; is the minimum main-ROM glue: the two dispatch sites' own tails, reached
; from page-1 call sites via a `$`-name-followed-by-`(` peek (interp.asm's
; ex_let_str, basic/strvar.asm's str_eval_one), mirroring the numeric
; ex_let/ev_f_var disambiguation exactly, both now built on ary_op0_resolve
; (below, shared with the NUMERIC ex_let_arr too — the slice-3 space audit's
; own generalisation of what was originally a string-only str_ary_resolve).
; =============================================================================

; --- ary_op0_resolve: BC=key, A=type, HL=cursor at '(' -> resolves an ------
; array element address (op=0 RESOLVE, auto-dim on first touch). SHARED by
; every RESOLVE-then-something call site: ex_let_arr (numeric store, TYPE=
; VARTYPE), ex_let_arr_str/str_eval_arr (string store/load, TYPE=1, below) --
; originally a string-only "str_ary_resolve" (arrays slice 3), generalised
; (TYPE became a caller-supplied parameter instead of a hardcoded 1) once the
; slice-3 space audit found the identical parse-subscripts+resolve prefix
; ex_let_arr had inlined its own copy of, §5.3's razor-thin-low-region
; pressure making the dedup worth it. Out: Z (ok) — HL=cursor (POPPED, i.e.
; [CURSOR] is consumed by this call, not left on the stack), DE=element
; address (== ARY_ADDR). NZ (error, already FPERR-mapped by ary_engine_call)
; — HL=cursor (POPPED), DE undefined. Either way [CURSOR] is popped EXACTLY
; ONCE by this routine; callers must not pop it again (a caller that used to
; land on a "pop hl;jp fp_runtime_error" abort stub after a NZ from the OLD
; inlined prologue must now `jp` straight to fp_runtime_error/its own deferred
; tail instead — the pop already happened in here). Clobbers A,B,C,D,E,H,
; L,IX (ary_parse_subs_kt/ary_engine_call's own clobbers).
ary_op0_resolve:
                call    ary_parse_subs_kt   ; BC,A restored (key,type);
                                            ; ARY_NIDX/ARY_IDX filled; [CURSOR]
                                            ; pushed
                ld      (ARY_KEY),bc
                ld      (ARY_TYPE),a
                ld      a,(FPERR)
                or      a
                jr      nz,aor_err          ; malformed subscript list / overflow
                xor     a
                ld      (ARY_OP),a          ; op = 0 (RESOLVE, auto-dim)
                call    ary_engine_call     ; -> Z ok / NZ: FPERR already mapped+set
                jr      nz,aor_err
                pop     hl                  ; [CURSOR] restored
                ld      de,(ARY_ADDR)       ; Z still holds from ary_engine_call's
                                            ; own success return (`or a`/`ret z`) --
                                            ; neither POP nor LD (nn) touches flags,
                                            ; so no separate flag-set instruction is
                                            ; needed here either (mirrors aor_err's
                                            ; own reasoning just below)
                ret
aor_err:
                pop     hl                  ; [CURSOR] restored -- NZ already
                                            ; holds from the `jr nz` that landed
                                            ; us here (POP touches no flag), so
                                            ; no separate flag-set instruction
                                            ; is needed
                ret

; --- ex_let_arr_str: string array-element assignment  S$(i[,j...])=<expr$> -
; BC=key, HL=cursor at '(' on entry (reached from ex_let_str, interp.asm,
; right after var_name_key — a `$` name followed by '(' is unambiguously a
; subscript, the exact string sibling of the numeric ev_f_arr/ex_let_arr
; disambiguation). Resolves elem_addr via ary_op0_resolve (type=1) BEFORE
; evaluating the RHS: this mirrors ex_let_arr's own self-reference discipline
; (S$(1)=S$(2), or even S$(1)=S$(1)+"X" once concat lands) — the RHS's own
; str_eval may itself resolve a NESTED array element via str_eval_arr
; (below), which clobbers the SAME shared ARY_KEY/ARY_TYPE/ARY_NIDX/ARY_IDX/
; ARY_ADDR param block ary_op0_resolve just wrote. So the LHS's resolved
; element address is kept on the STACK (not left in RAM) across str_eval —
; the identical hazard (and fix) ex_let_arr's own [ADDR] push documents for
; the numeric RHS-eval case. Once the RHS is stable (STRPTR set, no further
; array engine calls to race), the LHS address is re-published as ARY_ADDR
; and op=3 (COPY_STR, sub/arrays.asm) does the actual copy — safe ONLY
; because it runs strictly after the RHS is done, never fused with the
; resolve itself.
;
; §13a FIX: the SAME hazard ex_let_arr's own header documents — a numeric
; VARPTR sub-argument inside the string RHS (e.g. S$(0)=MID$(A$,VARPTR(B)))
; can allocate a scalar during `str_eval`, shifting the whole array region
; and staling the LHS address exactly like the numeric case. Shares
; ary_snapshot_offset/ary_apply_offset (basic/vars.asm, page-1) with
; ex_let_arr verbatim — this routine's own [ADDR] slot becomes ary_snapshot_
; offset's single [OFFSET] word (same size, so elas_err/elas_abort_fp's pop
; count is UNCHANGED, only relocated below).
ex_let_arr_str:
                ld      a,1                 ; type = 1 (string, always — this
                                            ; routine is only ever reached for
                                            ; a `$` name)
                call    ary_op0_resolve     ; Z: HL=cursor,DE=elem_addr / NZ:
                                            ; HL=cursor, FPERR already set
                jp      nz,fp_runtime_error ; [CURSOR] already consumed by
                                            ; ary_op0_resolve -- nothing to pop
                call    ary_snapshot_offset ; §13a: push [OFFSET] -- guarded
                                            ; across str_eval exactly like the
                                            ; old [ADDR] push (see header)
                call    skip_spaces
                ld      a,(hl)
                cp      EQ_TOKEN
                jp      nz,elas_err
                inc     hl
                call    skip_spaces
                call    str_eval            ; STRPTR -> RHS descriptor, HL advanced
                jp      nc,elas_err         ; not a string operand -> syntax error
                                            ; ([OFFSET] still on the stack --
                                            ; elas_err pops it)
                ld      a,(FPERR)           ; D-F2-1: a deferred error inside the RHS
                or      a                   ; (HEX$ overflow, or a nested array
                jp      nz,elas_abort_fp    ; subscript/bound error, §5.2) aborts
                                            ; here -- the SAME inline check
                                            ; ex_let_arr's own numeric RHS uses, NOT
                                            ; cepb_fp (that routine's own pop-two-
                                            ; off-the-stack contract assumes a
                                            ; DIFFERENT stack shape than this
                                            ; routine's single [OFFSET] frame)
                call    ary_apply_offset_hl_sub ; §13a: pops [OFFSET]; HL=cursor
                                            ; PRESERVED (str_eval's own advance),
                                            ; DE = the CORRECTED elem_addr
                ld      (ARY_ADDR),de       ; re-publish as op=3's INPUT (STRPTR
                                            ; already holds the stable RHS)
                ld      a,3
                ld      (ARY_OP),a          ; op = 3 (COPY_STR, pure-RAM leaf)
                push    hl                  ; [CURSOR] -- ary_engine_call/CALSLT
                                            ; clobbers everything, incl. HL
                call    ary_engine_call     ; -> always Z (op=3 cannot fail)
                pop     hl                  ; [CURSOR] restored
                jp      exec_stmt
; elas_err/elas_abort_fp RELOCATED to basic/vars.asm (page-1, §13a space
; fix) — reached via `jp` (was `jr`, now out of branch range) above; each
; still discards exactly ONE stack word ([OFFSET], same as the pre-fix
; [ADDR]), byte-identical bodies, only moved.

; --- str_eval_arr: string array-element rvalue  S$(i[,j...]) ---------------
; BC=key, HL=cursor at '(' on entry (reached from str_eval_one, basic/
; strvar.asm, right after var_name_key — a `$` name followed by '(' is
; unambiguously a subscript: str_eval_one's variable case is reached only
; for a plain `$` name, never a string FUNCTION token — LEN/MID$/etc. all
; dispatch earlier on their OWN distinct token bytes — the same
; disambiguation ev_f_var's numeric array check already relies on).
; Resolves via ary_op0_resolve (type=1, auto-dim on read), then -- UNLIKE the
; numeric load (ev_f_arr's FAC copy) -- sets STRPTR = elem_addr DIRECTLY and
; joins str_eval_ok: the element IS already a valid [len][bytes] descriptor
; (contract §4/§5.2), so every string consumer (print_strval, concat,
; LEN/MID$/...) reads it in place — zero-copy, exactly how str_get_key hands
; back an in-place STRTAB descriptor. Every array evaluation error is
; DEFERRED (mirrors ev_f_arr's own D-F2-1 discipline): FPERR is left set
; (already mapped by ary_engine_call, inside ary_op0_resolve), and STRPTR is
; pointed at the shared STR_EMPTY descriptor (vars.asm) instead of a
; stale/garbage address, so a caller that reads STRPTR before its own
; statement-boundary FPERR check (str_eval's own callers all do one right
; after — ex_let_str's cepb_fp, print's check_expr_errors) sees a harmless
; "" rather than crashing. CF is still SET / VALTYP=1 either way (a
; well-formed string OPERAND FORM was recognised — only its VALUE errored),
; joining str_eval_ok exactly like the success path.
str_eval_arr:
                ld      a,1                 ; type = 1 (string, always)
                call    ary_op0_resolve     ; Z: HL=cursor,DE=elem_addr / NZ:
                                            ; HL=cursor, FPERR already set
                jr      z,sea_have_de       ; success: DE already = elem_addr,
                                            ; the [len][bytes] descriptor itself
                                            ; (zero-copy) -- skip past the override
                ld      de,STR_EMPTY        ; deferred error: DE, not HL (HL still
                                            ; holds the cursor, untouched since
                                            ; ary_op0_resolve's own NZ return, which
                                            ; str_eval_ok needs) -- STR_EMPTY so a
                                            ; pre-FPERR-check read (if any) can't
                                            ; see garbage
sea_have_de:
                ld      (STRPTR),de         ; shared tail: whichever DE the branch
                                            ; above left, both paths do this
                jp      str_eval_ok

    ENDIF
