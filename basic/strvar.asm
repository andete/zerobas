; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; strvar.asm — minimal string-VALUE layer (own-design; see PROVENANCE.md).
;
; The STRING-OPERAND DISPATCHER: given a cursor, decide whether what it points at
; is a string operand at all, and if so leave STRPTR on its [len][bytes]
; descriptor. `str_eval_one` is the one-term half; `str_eval` chains
; `str_concat_tail` so `+` terms append. Both DECLINE (CF clear) on a numeric
; operand, and every caller keeps its own `jr c` / `jr nc` at the site.
;
; ⚠️ THIS HEADER USED TO SAY "Enough for PRINT ... There is NO heap, NO concat
; (`+`), and NO string functions (LEFT$/MID$/CHR$/…) — those are the Phase-2
; string engine", and that the reference's real heap/descriptor "is not
; reproduced — Phase 2". EVERY CLAUSE OF THAT IS FALSE (corrected 2026-09-03,
; D-DEFERSWEEP): the string engine shipped and its arc is CONCLUDED
; (basic/str-engine.asm, sub/strheap.asm), `str_eval` itself calls
; `str_concat_tail`, and the dispatch below routes INKEY$ / STRING$ / INPUT$ /
; MKI$ / SPRITE$ / FN…$ / a parenthesised subexpression / a `$` array element.
; A deferral is a promise with a trigger, and nothing in this tree watched this
; one fire. [[a-fix-falsifies-the-justification-beside-it]]
;
; A string VALUE is represented by a [len:1][bytes...] descriptor; STRPTR points
; at it and VALTYP=1 flags "the current operand is a string". The variable store
; (basic/vars.asm: str_find/str_get_key/str_set_key over STRTAB) holds the live
; values; STRSCR is scratch for a literal lifted out of the token stream.
;
; Clean-room: original code. String *semantics* are from the public MSX-BASIC
; language reference; the descriptor + store layout are zerobas' own design (the
; reference's heap layout is not reproduced — ours is in sub/strheap.asm and is
; not a copy of it). No disassembly.

; --- str_eval / str_eval_one: evaluate a string operand at (HL) -> descriptor -
; str_eval_one evaluates ONE string operand: a '"'-quoted literal or a `$`-suffixed
; variable name (the caller has already established it IS a string operand, e.g. via a
; leading '"' or var_str_type).
; out: STRPTR -> a [len][bytes] descriptor, VALTYP = 1, HL advanced past the operand.
;      CF set on success; CF clear (and VALTYP untouched) if the operand is not a
;      recognised string form (caller treats as error). Clobbers A, BC, DE, HL.
;
; str_eval is the PUBLIC entry every caller uses.
; (string-engine arc S3) it folds any trailing `+ operand` terms via str_concat_tail
; (basic/str-engine.asm, in the reclaimed low region), giving `A$+B$+C$` concatenation
; to every string context at once (PRINT, LET, function args, LSET/RSET, PRINT USING).
; --- str_eval_ix: evaluate the string expression at the IX cursor -------------
; D-NGRAM15. Seven sites said `push ix / pop hl / call str_eval` verbatim: four
; in basic/expr.asm and three in basic/str-engine.asm.
;
; 🔴 IT IS A TAIL JUMP, AND THAT MAKES IT FRAME-NEUTRAL. `call str_eval_ix`
; pushes the return to the SITE; the `jp` pushes nothing; `str_eval`'s own `ret`
; returns to the site. The depth at `str_eval` is therefore IDENTICAL to the
; open-coded form -- which matters because `str_eval` DECLINES (CF clear) as well
; as succeeding, and every caller keeps its OWN `jr c` / `jr nc` at the site.
; D-NGRAM8 lost exactly that when it put `str_eval` behind a `call` whose `ret`
; landed one frame too shallow and the decline stopped declining.
;
; ⚠️ SITED HERE, IN PAGE 1, BESIDE `str_eval` ITSELF -- not in the low region
; with three of its seven callers. `str_eval` is already a page-1 routine that
; `basic/str-engine.asm` (page-0 low) calls, so the low-region sites lose 3 B
; each and gain nothing to jump to: low +9 B, page 1 +6 B. The scarce region
; takes the larger share, which is the opposite of where the sites are.
;   out: HL = advanced cursor, CF/STRPTR exactly as `str_eval` leaves them.
str_eval_ix:
                push    ix
                pop     hl                  ; HL = cursor
                jp      str_eval            ; TAIL -- CF, HL and STRPTR go to OUR caller

str_eval:
                call    str_eval_one
                ret     nc                  ; not a string operand -> propagate
                jp      str_concat_tail     ; low region: append `+ operand` terms
str_eval_one:
                ld      a,(hl)
                cp      '"'
                jp      z,str_eval_lit      ; repack: str_eval_lit is in the low
                                            ; region (str-engine.asm) — out of jr
                                            ; range from here (page 1)
                cp      '('                 ; ✅ D-STRPAREN: a parenthesised STRING
                jr      z,str_eval_paren    ; subexpression -- `(A$)`, `("Z")`,
                                            ; `(A$+"Z")`, `((A$))`
                cp      INPUT_TOKEN         ; INPUT$(...) ? -> $85 ('INPUT') then '$'
                jp      z,str_eval_maybe_inputd
                cp      PEEK_PREFIX         ; $FF + selector -> a function token; MKI$ ?
                jr      z,str_eval_maybe_mki
                cp      STRING_TOKEN        ; $E3 -> STRING$(n,c) (string-functions Group B;
                jp      z,str_fn_string     ; single-byte reserved word, not $FF-prefixed)
                cp      INKEY_TOKEN         ; $EC -> INKEY$ (no args; single-byte reserved word)
                jp      z,str_fn_inkey
                cp      FN_TOKEN            ; $DE -> FN<name>$[(args)] (D-DEFFN).
                jp      z,str_ev_fn         ; DECLINES a numeric FN, exactly as
                                            ; str_eval_paren declines `(A+1)`
    IF G7_RESIDENT
                cp      SPRITE_TOKEN        ; $C7 -> SPRITE$(n) (graphics G7; the `$` is
                jp      z,ev_f_sprite       ; separate ASCII after the token)
    ENDIF
                call    is_letter           ; a `$`-suffixed variable?
                jr      nc,str_eval_no
                call    var_str_type        ; A=1 if `$` suffix
                or      a
                jr      z,str_eval_no       ; numeric name -> not a string operand
                ; string variable: key it and point STRPTR at its stored value.
                call    var_name_key        ; BC = key, HL past name + `$`
                ld      a,(hl)
                cp      '('
                jp      z,str_eval_arr      ; string array-element rvalue (arrays
                                            ; slice-3, docs/spec-basic-arrays-
                                            ; slice3-strings.md §5.2,
                                            ; basic/arrays.asm) — str_eval_one
                                            ; reaches this variable case only for
                                            ; a plain `$` name, never a string
                                            ; FUNCTION token (those dispatch
                                            ; earlier on their own distinct
                                            ; bytes), so a `(` here is
                                            ; unambiguously a subscript — the
                                            ; same disambiguation ev_f_var's
                                            ; numeric array check already relies
                                            ; on
                push    hl                  ; guard cursor across the lookup
                call    fld_lookup          ; FIELDed var? -> STRPTR=FLD_DESC slice, CF set
                jr      c,sev_have          ; fielded -> STRPTR already set
                call    str_get_key         ; HL -> [len][bytes] descriptor
                ld      (STRPTR),hl
sev_have:
                pop     hl
                jr      str_eval_ok
; Arrays slice-4a: the repack str_eval_lit (zero-copy literal-lift into
; RVDESC) lives in the low region (basic/str-engine.asm) — page 1 is byte-
; full; str_eval_one reaches it by the jp above.
; --- str_eval_paren: `( <string expression> )` -------------------------------
; D-STRPAREN (docs/spec-basic-strparen.md, measured in
; docs/strparen-msx1-characterization.md). `(A$)` was refused in every string
; context here and is ordinary on BOTH references -- eleven contexts, three
; controls, two references, all eleven divergent.
;
; 🎯 THE `ret nc` IS THE WHOLE DESIGN, not an error path. zerobas has a NUMERIC
; `eval` and a STRING `str_eval` and picks between them by PEEKING at the first
; byte; the reference has one type-polymorphic evaluator. A leading `(` is the
; one operand shape a peek cannot classify -- `(A$)` is a string and `(A+1)` is
; not, and nothing short of evaluating the inside can say which. So this routine
; is written to be TRIED and to leave no trace when it declines: on anything that
; is not a string it RESTORES HL and returns CF clear, exactly as `str_eval_no`
; does, and the caller falls through to the numeric path it would have taken
; anyway. That is what lets `basic/print.asm`'s item loop and `ev_rel` offer the
; string path first without committing to it.
;
; ⚠️ THE RECURSION IS `str_eval`, NOT `str_eval_one`, and that is what makes
; `(A$+"Z")` work: the `+` tail is `str_concat_tail`'s and it belongs INSIDE the
; parentheses. `((A$))` then falls out for free -- the inner call re-enters here.
; The Z80 stack cost is 2 bytes of return address per nesting level; BASIC's own
; line length bounds the depth long before that matters.
;
; ⚠️ A `(` HERE IS UNAMBIGUOUSLY A SUBEXPRESSION, never a subscript. `A$(1)`
; reaches the variable arm below via `is_letter`, which consumes the name first
; and only then looks for `(` -- the same disambiguation `ev_f_var`'s numeric
; array check already relies on. str_eval_one is entered at an OPERAND boundary.
;
;   in:  HL -> the '('
;   out: CF set  -> STRPTR = the value, HL past the ')'
;        CF clear-> HL RESTORED to the '(', nothing else touched
str_eval_paren:
                push    hl                  ; the '(' -- restored if we decline
                inc     hl
                call    str_eval            ; full string expression, `+` tail and all
                jr      nc,sep_decline      ; not a string inside -> hand it back
                call    skip_spaces
                cp      ')'
                jr      nz,sep_decline      ; `(A$` unterminated -> decline, and the
                                            ; caller's numeric path raises its own
                                            ; Syntax error at the same cursor
                inc     hl                  ; past the ')'
                pop     af                  ; discard the saved cursor (keep HL)
                scf
                ret
sep_decline:
                ; ⚠️ THIS RESTORE IS UNPINNED BY ANY ROW, AND THAT IS SAID OUT
                ; LOUD RATHER THAN LEFT TO BE FOUND. K-SP2 (`pop hl` -> `pop de`)
                ; REDDENS NOTHING, across two deliberate attempts to make it
                ; live:
                ;   * `p.numlet` (`B$=(A+1)`) agrees for the WRONG REASON --
                ;     `els_tc_common` raises `type_mismatch_error` once `eval`
                ;     returns, from ANY cursor, so a row scoring the FACE cannot
                ;     see a cursor at all;
                ;   * `p.numif` (`IF (A+1)=6`) scores a VALUE instead, and still
                ;     does not move: that caller guards its own cursor too.
                ; Every caller of `str_eval` that falls back turns out to save
                ; and restore its own operand start (`exp_strvar` explicitly, and
                ; `exps_fallback`'s comment says so), or to raise regardless.
                ; 🎯 KEPT ANYWAY, and not out of superstition: it costs ZERO
                ; bytes (`pop hl` and `pop af` are both one), and it is what
                ; makes the CONTRACT stated above ("HL RESTORED to the '('")
                ; TRUE. A future caller that re-parses from HL will depend on it
                ; and will have no way to discover it is missing.
                ; ⚠️ A guard with no row is exactly what D-FNEXPR2 shipped at
                ; `do_files` and filed against itself. This one is filed too
                ; [[a-shadowed-guard-has-no-knife]].
                pop     hl                  ; put the cursor back on the '('
                ; fall through into str_eval_no
str_eval_no:
                or      a                   ; CF clear -> not a string operand
                ret

; --- sea_fld: the FIELDed-READ hook for an ARRAY ELEMENT --------------------
; D-FLDARY (docs/spec-basic-fldary.md §4.3). 🔴 THE READ PATH IS A THIRD SITE AND
; NOBODY HAD LISTED IT. A fielded variable behaves only because the SCALAR path
; above calls fld_lookup; str_eval_arr (basic/arrays.asm) points STRPTR straight
; at the element and never consults FLD_TAB, so before this hook `LSET A$(1)`
; could not be read back whatever FIELD recorded -- and a fix that taught only
; the two PARSE sites about subscripts would have turned `d.ary` green for the
; wrong reason and left `s.fldary` red (spec §5.2).
;
; ⚠️ SITED IN PAGE 1 ON PURPOSE. str_eval_arr's own file is the LOW region, which
; had 7 B; carve_scout reports basic/arrays.asm as 0 of 46 labels in page 1. So
; the low side pays ONE byte for `jr z` -> `jp z` and the hook lives here, beside
; the scalar twin it mirrors. Placed between str_eval_no and str_eval_ok so the
; tail FALLS THROUGH (worth 3 B).
;
; 🎯 PUBLISHING STRPTR FIRST IS WHAT MAKES THIS 10 B INSTEAD OF 14. fld_lookup is
; `call fld_find` / `ret nc`: on a miss it touches nothing. So write the element
; address first and let a hit overwrite it -- the whole not-found branch goes.
;
; in:  DE = the resolved element address (str_eval_arr's success arm only -- the
;      deferred-error arm keeps its own STR_EMPTY tail and deliberately does NOT
;      look up: there is no element, and a lookup on a garbage offset is exactly
;      the wild read that arm exists to prevent).
;
; ⚠️ HL IS THE LIVE TEXT CURSOR HERE AND fld_lookup CLOBBERS IT. str_eval_one's
; SCALAR arm above guards it with its own push/pop for exactly this reason, and
; the array arm has no such guard of its own -- str_eval_arr advances HL past the
; subscripts and str_eval_ok returns it. Omitting these two bytes made every
; FIELDed array-element read return a wrecked cursor; the gate read `<NO OUTPUT>`
; on all six s.*/r.* rows while every d.* row stayed green, which is what pointed
; at the READ hook rather than at the parse sites.
sea_fld:
                ld      (STRPTR),de         ; default: the element itself, verbatim
                push    hl                  ; the text cursor -- see above
                call    fld_key_de          ; BC = the ARYTAB-relative element key
                call    fld_lookup          ; FIELDed? -> STRPTR = FLD_DESC slice
                pop     hl
                                            ; fall through into str_eval_ok
str_eval_ok:
                ld      a,1
                ld      (VALTYP),a
                scf
                ret

; --- INPUT$(n,#f): read EXACTLY n raw bytes from file channel f as a string ------
; Reached from str_eval when the operand is the INPUT token ($85). "INPUT$" crunches
; to INPUT ($85) + '$' ($24) — NOT a dedicated token (oracle: VG-8020 + zerobas both
; emit $85 $24). Only the FILE form INPUT$(n,#f) is supported; the keyboard form
; INPUT$(n) (no '#') is Phase 3 -> treated as "not a string operand" (caller errors).
; Unlike INPUT#/LINE INPUT#, INPUT$ does NO delimiter handling — it takes n bytes
; verbatim and the file cursor advances by n. The bytes go into the STRSCR
; descriptor (clamped to STRMAX; a longer n is still consumed so the cursor stays
; correct — documented). HL is the (HL-based) string-eval cursor; the numeric args
; use `eval` (which saves/restores IX); fat_io_getbyte's CALSLT clobbers everything,
; so the read state lives in RAM (INDLR_N target, IN_RDLEN stored count) and the
; cursor is guarded on the stack. CF-3300-validated (disk_probe_inputdollar.py).
; --- MKI$(n): pack a 16-bit integer into a 2-byte little-endian string -----------
; Reached from str_eval on a $FF function token. "MKI$" crunches to $FF $AE (oracle-
; locked). MKI$(n) returns the 2-byte string [lo][hi] of n; the inverse is CVI
; (basic/expr.asm). The numeric arg uses `eval` (saves/restores IX); the 2-byte
; result fills the STRSCR [len][bytes] descriptor (binary-safe: len-prefixed, so a
; $00 byte is fine). HL is guarded across the STRSCR write (the OPEN/INPUT$ lesson).
; CF-3300-validated (disk_probe_mkicvi.py). The float siblings MKS$/MKD$ are Phase 3.
str_eval_maybe_mki:
                inc     hl                  ; tentatively past $FF
                ld      a,(hl)
                cp      MKI_TOKEN           ; $AE -> MKI$  (2 bytes, integer)
                jr      z,str_mki
                cp      MKS_TOKEN           ; $AF -> MKS$  (4 bytes, single)
                jr      z,str_mks
                cp      MKD_TOKEN           ; $B0 -> MKD$  (8 bytes, double)
                jr      z,str_mkd
                jp      str_func_ff         ; repack: CHR$/STR$/LEFT$/RIGHT$/MID$ (HL on selector)

; --- MKI$ / MKS$ / MKD$: the value's STORED BYTES, as a string ---------------
; docs/spec-basic-mksd.md. One body, parameterised by C = the byte count, because
; the three verbs differ in exactly two things: how many bytes, and what the
; argument is coerced to first.
;
; 🎯 THE BYTE COUNT *IS* THE FACTYP CODE. MSX numbers the types 2/4/8 and the
; widths are 2/4/8, so `C` serves as both and no second table is needed. That is
; the reference's own numbering, not a coincidence this code invented.
;
; 🔬 MKS$/MKD$ EMIT EXACTLY WHAT THE VARIABLE STORE HOLDS, measured: the CF-3300's
; `MKS$(1.5)` reads back `65 21 0 0` byte for byte, which is what `PEEK(VARPTR(A!))`
; gives for `A!=1.5` on all three machines (docs/spec-basic-faczero.md §0). So the
; coercion here is the SAME pair `var_store_fac` uses -- widen, then round/pack to
; the target precision -- and not a private encoder that could drift from it.
; ⚠️ `MKS$(0)` is `0 0 0 0` on the reference, and would have been `0 255 255 255`
; here until D-FACZERO canonicalised zero's mantissa the day before this shipped.
str_mki:        ld      c,2
                jr      str_mkf
str_mks:        ld      c,4
                jr      str_mkf
str_mkd:        ld      c,8
str_mkf:
                inc     hl                  ; past the MKx$ selector
                ld      a,(hl)
                cp      '('
                jr      nz,str_eval_no
                inc     hl
                push    bc                  ; C (the width) across the argument eval
                call    eval                ; DE = n if int; FAC/FACTYP otherwise
                pop     bc
                ld      a,(hl)
                cp      ')'
                jr      nz,str_eval_no
                inc     hl                  ; HL past ')'
                push    hl                  ; guard the cursor across the STRSCR write
                ld      a,c
                ld      (STRSCR),a          ; length = the width; reloaded below because
                                            ; the coercion helpers clobber BC
                cp      2
                jr      z,str_mkf_int
                ld      hl,ARGA             ; --- coerce to single / double ---
                call    widen_rhs_operand   ; exact widen of the live RHS (float-arith)
                ld      a,(STRSCR)
                cp      4
                jr      nz,str_mkf_dbl
                call    round_single_and_pack   ; 6-digit half-up round -> FAC as single
                jr      str_mkf_copy
str_mkf_dbl:
                call    round_and_finalize      ; exact widen -> FAC as double
str_mkf_copy:
                ld      a,(STRSCR)
                ld      c,a
                ld      b,0
                ld      hl,FAC
                ld      de,STRSCR+1
                ldir                        ; the packed bytes ARE the string
                jr      str_mkf_desc
str_mkf_int:
                ; --- D-MKHOOK: MKI$ belongs to the DISK ROM ---------------------
                ; docs/spec-basic-nodisk.md. The verb's TABLE entry is faithfully
                ; ours (a diskless VG-8020 crunches MKI$ to `FF AE`), but its
                ; IMPLEMENTATION is the disk ROM's, reached through H.MKI$. Ask the
                ; hook: claimed -> CF=1, carry on; unclaimed -> C-BIOS's `ret`
                ; leaves CF as we set it, so we defer ERR 5. A diskless zerobas is
                ; then correct BY ABSENCE, the way the reference is, rather than by
                ; a presence guard bolted onto a verb that is still here.
                ; ⚠️ DE IS THE VALUE AND THE CALL CROSSES SLOTS. A claimed hook runs
                ; RST 30h/CALSLT, which is documented to affect DE among others, so
                ; the operand is guarded across it -- the unclaimed path is a bare
                ; `ret` and would have hidden this until a disk was present.
                push    de
                or      a                   ; CF clear = "nobody claimed it"
                call    H_MKI
                pop     de
                jr      c,str_mkf_int_go
                ld      a,3                 ; Illegal function call, DEFERRED --
                call    penderr_set         ; first-error-wins, so it outranks the
                                            ; syntax error the decline would raise
                                            ; (stmt_error calls check_expr_errors
                                            ; before it reaches `ld a,2`)
                pop     hl                  ; balance the guarded cursor
                jp      str_eval_no
str_mkf_int_go:
                ld      a,e
                ld      (STRSCR+1),a        ; low byte of n
                ld      a,d
                ld      (STRSCR+2),a        ; high byte of n
str_mkf_desc:
                call    strscr_desc         ; RVDESC -> [len][ptr] wrapping STRSCR
                                            ; (arrays slice-4a §10: every STRPTR
                                            ; target is a [len:1][ptr:2] descriptor)
                ld      (STRPTR),hl
                pop     hl                  ; restore the eval cursor
                jp      str_eval_ok
str_eval_maybe_inputd:
                inc     hl                  ; tentatively past the INPUT token
                ld      a,(hl)
                cp      '$'
                jr      z,str_inputd
                dec     hl                  ; not INPUT$ -> restore, not a string operand
                jp      str_eval_no
str_inputd:
                inc     hl                  ; past '$'
                ld      a,(hl)
                cp      '('
                jp      nz,str_eval_no
                inc     hl
                call    eval                ; DE = n (byte count); HL advanced past it
                ld      a,e
                ld      (INDLR_N),a         ; target count (low byte; n <= 255)
                ld      a,(hl)
                cp      ','                 ; INPUT$(n) keyboard form (no ',') = Phase 3
                jp      nz,str_eval_no
                inc     hl
                ld      a,(hl)
                cp      '#'                 ; file form requires '#f'
                jp      nz,str_eval_no
                inc     hl
                call    eval                ; DE = channel f; HL advanced
                ld      a,(hl)
                cp      ')'
                jp      nz,str_eval_no
                inc     hl                  ; HL past ')'
                call    fch_check           ; D-BADFNUM: 5 / 59 / 52. Was
                                            ; `jp nc,str_eval_no` -- a PARSE-level
                                            ; "not a string operand", which surfaced
                                            ; as Syntax error for every rejected
                                            ; channel. We are already past the ')'
                push    hl                  ; guard the eval cursor (fch_select + CALSLT)
                ; D-NOTOPEN2 §3.3: classify BEFORE fch_select, not after. The old
                ; order selected the channel and only then looked at its mode, so a
                ; not-open (or device) slot got fch_select'd -- the very thing
                ; fch_mode_class's header forbids. Measured reference rule: mode 1
                ; reads; RANDOM is ERR 61; EVERY other open mode is ERR 55.
                call    fch_mode_class      ; A = FCH_MODES[E]; ERR 59 if NOT OPEN
                cp      1                   ; open FOR INPUT -> read it
                jr      z,sid_ok
                cp      4
                ld      a,55                ; input past end (modes 2/3/5/6 alike)
                jr      nz,sid_raise
                ld      a,61                ; bad file mode (RANDOM)
sid_raise:
                jp      raise_error         ; no `pop hl` -- raise_error resets SP
sid_ok:
                ld      a,e
                call    fch_select          ; make channel f live; FCH_MODE = its mode
                call    str_inputd_read     ; fill STRSCR [len][bytes] with n bytes
                call    strscr_desc         ; RVDESC -> [len][ptr] wrapping STRSCR
                                            ; (arrays slice-4a §10)
                ld      (STRPTR),hl         ; the stack (HL here would clobber it)
                pop     hl                  ; restore the eval cursor (past ')')
                jp      str_eval_ok
; str_inputd_read — consume INDLR_N bytes from the open channel into STRSCR
; ([len][bytes]); store up to STRMAX, but keep consuming so the file cursor advances
; the full count. Stops early at EOF. All loop state is in RAM (CALSLT clobbers regs).
str_inputd_read:
                xor     a
                ld      (IN_RDLEN),a        ; stored count = 0
sidr_lp:
                ld      a,(INDLR_N)
                or      a
                jr      z,sidr_done         ; consumed all n
                call    fat_io_getbyte
                jr      c,sidr_done         ; EOF before n -> stop (partial)
                ld      c,a                 ; C = the byte read
                ld      hl,INDLR_N
                dec     (hl)                ; D-PEEPHOLE: -3 B (7 B -> 4 B)
                ld      a,(IN_RDLEN)
                cp      STRMAX
                jr      nc,sidr_lp          ; descriptor full -> consume but don't store
                ld      e,a
                ld      d,0
                ld      hl,STRSCR+1
                add     hl,de
                ld      (hl),c              ; store the byte
                ld      hl,IN_RDLEN
                inc     (hl)                ; D-PEEPHOLE: -3 B (7 B -> 4 B)
                jr      sidr_lp
sidr_done:
                ld      a,(IN_RDLEN)
                ld      (STRSCR),a          ; descriptor length
                ret

; --- print_strval: emit the descriptor at STRPTR via CHPUT ------------------
; Reads STRPTR (set by str_eval). CHPUT makes no register guarantees, so the
; descriptor cursor (HL) and the remaining count (B) are guarded across it.
; Clobbers A, B, HL.
; Arrays slice-4a: the repack print_strval lives in the low region (basic/
; str-engine.asm) — page 1 is byte-full; print.asm reaches it by in-slot
; call. strscr_desc / pu_deref_body live there too.
