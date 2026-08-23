; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; deffn.asm -- D-DEFFNEV: DEF FN's PARSE, as a PAGE-0 sub-ROM tenant
; (SUBROM_IDX_DEFFN). docs/spec-basic-deffnev.md, docs/deffn-design-2026-08-22.md.
;
; The resident half (basic/deffn.asm) owns everything that needs main page 0 or
; the Z80 stack: the two factor entries, the frame save/restore (which moves SP,
; and a routine under CALSLT may not), and a four-request SERVICER. Everything
; between those -- the name resolve, the two lists walked together, the
; delimiter agreement that IS the arity rule, the shadow slots and their
; ceiling, both directions of ERR 13 -- is here, because all of it is token
; walking over page-3 RAM and none of it touches `eval`.
;
; ⚠️ A CALSLT IS NOT RESUMABLE. This tenant is re-entered AT ITS TOP once per
; bounce and recovers its phase from L plus RAM. There are no locals: the Z80
; stack is the resident servicer's, and anything pushed here would be gone by
; the next entry.
;
;   tenant -> main   1  evaluate the expression at FN_PTR; say what you got
;                    2  store the value into (FN_KEY, FN_TYP)
;                    3  snapshot the string result off the frame, then LEAVE
;                    4  load (FN_KEY, FN_TYP) back into FAC, then LEAVE
;                    0  raise FN_TYP
;   main -> tenant  $81 a NUMERIC value (FAC/FACTYP/DE)
;                   $82 a STRING value (STRPTR)
;                   $83 stored
;
; 🎯 THE PHASE IS TWO CELLS THAT WERE ALREADY THERE, AND THAT IS FORCED, NOT
; ELEGANT. FN_AREA is 99 and FN_MAXP is exactly 9 with ZERO bytes to spare
; (sysvars.inc's `IF FN_MAXP < 9` assert is the guard), so a twelfth cell would
; drop the measured nine-formal ceiling to eight. So:
;   * L on entry (the servicer's answer, passed through CALSLT) separates
;     "nothing asked yet" (0) from "a value came back" ($81/$82) from "stored"
;     ($83) -- the two alphabets are disjoint, which is why one byte carries
;     BOTH directions of the protocol;
;   * FN_KEY's name0 byte separates the FORMAL phases from the BODY/RESULT ones:
;     $FF is the result slot's key and no formal can carry it, because a
;     formal's name0 is always an upcased letter.
; Together they name all five re-entry points with no cell of their own.
;
; ⚠️ FN_PTR CARRIES TWO DIFFERENT CURSORS AND FN_DPTR PARKS THE OTHER. While the
; formal list is walked, FN_PTR is the CALL cursor and FN_DPTR the DEFINITION
; cursor. Once the list closes the definition cursor IS the body, so the two
; swap: FN_PTR becomes the body (that is the expression the servicer evaluates)
; and FN_DPTR holds the call cursor the whole call must return. dfn_bodydone
; puts it back before either terminal request, because fn_fin reads FN_PTR.
;
; SUB-SIDE CLONES. A page-0 tenant cannot call main page 1 -- MEASURED: no
; page-0 tenant in this tree does, and there is no import mechanism
; (`sub/basic-resident-abi.inc` is generated for PAGE-1 tenants calling main's
; LOW region). So `var_name_key`, `is_ident_cont` and `deftbl_lookup` are cloned
; below, exactly as sub/deftype.asm clones `skip_spaces` and sub/sub.asm clones
; `is_letter`. Everything else this file needs is already co-resident in sub
; page 0: `skip_spaces` (readdata.asm), `is_letter` + `upcase` (sub.asm /
; tkfloat.asm) and -- the one that matters -- `scv_find` (arrays.asm), one
; page-local `call` away, which is what makes the definition lookup free.
;
; Clean-room: original code. The DEF FN / FN semantics implemented here are this
; project's own black-box measurements of a Philips VG-8020 and a National
; CF-3300 (docs/deffn-scout-2026-08-22.md, docs/deffn-design-2026-08-22.md, 82
; rows) plus the public MSX-BASIC language reference. No disassembly.

; --- the phase dispatch ----------------------------------------------------
deffn_tenant:
                ld      a,l                 ; the servicer's answer, in a register
                or      a
                jp      z,dfn_start         ; nothing asked yet: a fresh call
                cp      $83
                jr      z,dfn_stored
                ld      b,a                 ; B = $81 numeric / $82 string
                call    dfn_is_result
                jp      z,dfn_bodydone
                jp      dfn_actual
dfn_stored:
                call    dfn_is_result
                jp      z,dfn_load          ; the RESULT slot -> load it and leave
                jp      dfn_delim           ; a FORMAL -> the delimiters must agree

; --- dfn_is_result: Z iff FN_KEY names the $FFFF result slot ---------------
; A formal's name0 is an upcased letter, so $FF is a key no formal can carry --
; the same argument the resident coercion's own `$FFFF` re-key rides on.
dfn_is_result:
                ld      a,(FN_KEY+1)        ; name0 (ld (FN_KEY),bc puts B high)
                inc     a
                ret

; --- dfn_start: resolve the name, then open the parameter list -------------
; THE CALL ORDER IS MEASURED (design §4): name -> ERR 18 -> walk the two lists
; together -> ERR 2 on a shape mismatch -> ERR 5 past the ceiling -> bind ->
; evaluate. An undefined name beats every other fault: `FNZ(1,2)` -- undefined
; AND unmatched -- is ERR 18, not ERR 2 (o.undefarg), which is why the resolve
; is first and unconditional.
dfn_start:
                ld      hl,(FN_PTR)         ; the servicer left this past the FN token
                call    skip_spaces
                call    dfn_name_key        ; B,C = key, A = type, HL past name+suffix
                ld      (FN_PTR),hl
                ld      (FN_RTYPE),a        ; the FN's own type IS its result type
                                            ; (o.fnpct 2 vs o.fnbang 2.5)
                set     7,b                 ; the FN namespace: a key no ordinary
                                            ; name can produce, so no new table
                call    scv_find            ; the definition lives in the ORDINARY
                jp      nc,dfn_err18        ; variable chain (o.clearwipe3, o.namespace)
                inc     hl
                inc     hl
                inc     hl                  ; HL -> the recorded text pointer
                ld      e,(hl)
                inc     hl
                ld      d,(hl)
                ld      (FN_DPTR),de        ; the definition cursor
                ld      a,low FN_PAREA
                ld      (FN_SLOTP),a        ; the first formal takes slot 0
                ; ⚠️ FN_FEND IS **NOT** RESET HERE, AND THAT IS o.nestsame's WHOLE
                ; POINT. The actuals are evaluated in the CALLER's scope
                ; (o.actualfirst: `X=5 : DEF FNA(X)=X*10` called as `FNA(X+1)` is
                ; 60), so the outer frame stays visible until the last one has
                ; been evaluated. The slot walk grows FN_FEND without ever
                ; shrinking it; the exact frame is set once the list closes.
                ex      de,hl               ; HL = the definition cursor
                ld      a,(hl)
                cp      '('
                jp      nz,dfn_body         ; `DEF FNA=7` consumes NO parentheses
                                            ; at the call either -- `FNA(1)` is
                                            ; `7 1`, two PRINT items (o.argnoarg)
                inc     hl
                ld      (FN_DPTR),hl
                ld      hl,(FN_PTR)
                call    skip_spaces
                cp      '('
                jp      nz,dfn_err2         ; a list in the DEF and none at the
                                            ; call is ERR 2 (o.barecall)
                inc     hl
                ld      (FN_PTR),hl

; --- dfn_formal: read the next formal, then ask for its actual -------------
; The formal's key and type go into FN_KEY/FN_TYP BEFORE the bounce, which is
; what lets dfn_actual bind without re-reading the name -- and what makes
; FN_KEY the phase discriminator on the way back.
dfn_formal:
                ld      hl,(FN_DPTR)
                call    skip_spaces
                call    is_letter
                jp      nc,dfn_err2
                call    dfn_name_key
                ld      (FN_DPTR),hl
                ld      (FN_TYP),a
                ld      (FN_KEY),bc
                ld      a,1                 ; evaluate the actual at FN_PTR
                jp      dfn_req

; --- dfn_actual: the actual came back -- type-check it, open its slot -------
; 🎯 ONE `evaluate` REQUEST SERVES BOTH THE ACTUALS AND THE BODY, and BOTH
; DIRECTIONS OF ERR 13 FALL OUT OF THE ANSWER ALONE. The servicer offers
; `str_eval` first and lets it DECLINE (D-STRPAREN's contract), so $82 means
; "the actual is a string" and $81 means "it is not" -- a string actual in a
; numeric formal (`FNA("hi")`, o.strnum) and a numeric one in a string formal
; (`FNA$(1)`, o.numstr) are the two ways that answer can disagree with FN_TYP.
dfn_actual:                                 ; B = $81/$82
                ld      a,(FN_TYP)
                cp      DEFTBL_STR
                ld      a,b
                jr      z,dfn_a_str
                cp      $81
                jp      nz,dfn_err13        ; string actual, numeric formal
                ld      a,(FN_TYP)          ; the slot's header type IS the
                jr      dfn_a_open          ; formal's own resolved type
dfn_a_str:
                cp      $82
                jp      nz,dfn_err13        ; numeric actual, string formal
                ld      a,1                 ; the `$` unifier type (slice-4c):
                                            ; string scalars key at type 1, while
                                            ; FN_TYP stays DEFTBL_STR so the
                                            ; servicer routes to str_set_key
dfn_a_open:
                ; --- open the next shadow slot ----------------------------
                ; 🎯 THE CEILING IS A DIVISION, NOT A RULE. FN_PAREA_END is
                ; FN_PAREA + 9*11 because 11 is a scalar entry and the window
                ; holds nine of them -- the same 100/11 that predicts the
                ; reference's own measured nine (o.p9 -> 1, o.p10..o.p16 ->
                ; ERR 5, all AT THE CALL, while `DEF` with ten formals is OK).
                ; Nothing here spells 9.
                ; 🔴 INLINE, AND THAT IS A STACK DECISION. A helper would have to
                ; `jp` out to the ERR 5 disposition with its own return address
                ; still on the stack, and this tenant's `ret` goes back through
                ; CALSLT -- an imbalance there is a wild jump, not a wrong answer.
                ; 🔴 THE BOUND IS AN OFFSET, NOT AN ADDRESS, AND THAT IS A
                ; MEASURED FIX. `cp low FN_PAREA_END` reads as the obvious test
                ; and is WRONG TWICE over, because D-DEFFNEV grew FN_CELLS from
                ; 3 to 11 and slid the area up against LINEBUF: FN_PAREA_END is
                ; now $EB00 exactly, so `low FN_PAREA_END` is **0** and the
                ; compare is unconditionally NC -- ERR 5 on the FIRST formal, 44
                ; rows of the battery. And the mirror fault is underneath it: the
                ; ninth formal leaves FN_SLOTP wrapped to $00, which that same
                ; compare would have read as legal. Subtracting the base first
                ; turns both into one test -- the borrow catches the wrap, and
                ; the bound is FN_AREA, which is FN_MAXP*FN_SLOTSZ, so the
                ; ceiling stays the division it is measured to be and nothing
                ; here spells 9.
                ; ⚠️ IT SURVIVED THE WHOLE OF D-DEFFNEV BECAUSE THE TENANT WAS A
                ; STUB. `cp low FN_PAREA_END` was written when FN_PAREA_END was
                ; $EAF8 and was still correct then; the constant was falsified by
                ; an edit to a DIFFERENT symbol in a DIFFERENT file, and the only
                ; instrument that could see it is a build that RUNS.
                ld      c,a                 ; C = the header type
                ld      a,(FN_SLOTP)
                sub     low FN_PAREA        ; A = the next slot's byte offset
                jp      c,dfn_err5          ; ...wrapped off the top of the page
                cp      FN_AREA
                jp      nc,dfn_err5         ; past the ninth formal
                ld      a,(FN_SLOTP)
                ld      l,a
                ld      h,high FN_PAREA
                ld      de,(FN_KEY)         ; D = name0, E = name1
                ld      (hl),d
                inc     hl
                ld      (hl),e
                inc     hl
                ld      (hl),c              ; the slot is a scalar entry, verbatim
                ld      a,l
                add     a,FN_SLOTSZ-2       ; HL is at slot+2
                ld      (FN_SLOTP),a
                ld      hl,FN_FEND
                cp      (hl)
                jr      c,dfn_a_x
                ld      (hl),a              ; grow, never shrink
dfn_a_x:
                ld      a,2                 ; store the value into (FN_KEY, FN_TYP)
dfn_req:
                ret                         ; A **is** the request: subrom_call's
                                            ; documented result register, and the
                                            ; servicer's `ld l,a` next time round

; --- dfn_delim: the two delimiters must AGREE ------------------------------
; This is the WHOLE of the arity rule, and it is why ERR 2 comes out of
; `FNA(1,2)` on a one-formal FN (o.toomany), `FNA(1)` on a two-formal one
; (o.toofew), AND `DEF FNA(B(1))=...` (o.aryformal -- the definition's next
; character is `(`, the call's is `)`).
dfn_delim:
                ld      hl,(FN_DPTR)
                call    skip_spaces
                ld      (FN_DPTR),hl
                ld      c,a                 ; C = the definition's delimiter
                ld      hl,(FN_PTR)
                call    skip_spaces
                cp      c
                jp      nz,dfn_err2
                inc     hl
                ld      (FN_PTR),hl
                ld      hl,(FN_DPTR)
                inc     hl
                ld      (FN_DPTR),hl
                cp      ','
                jp      z,dfn_formal
                cp      ')'
                jp      nz,dfn_err2

; --- dfn_body: the list closed -- fix the frame and ask for the body -------
dfn_body:
                ld      a,(FN_SLOTP)
                ld      (FN_FEND),a         ; the live frame is EXACTLY this call's
                                            ; own formals -- which is why
                                            ; `DEF FNB(Y)=X` called from inside
                                            ; FNA(X) reads the GLOBAL X
                                            ; (o.dynscope -> 5, not 2)
                ld      hl,(FN_DPTR)
                call    skip_spaces
                cp      EQ_TOKEN            ; `=` crunches to $EF; a definition
                jr      nz,dfn_b_noeq       ; without one is legal (o.noeq) and
                inc     hl                  ; simply evaluates from here
dfn_b_noeq:
                ld      de,(FN_PTR)
                ld      (FN_DPTR),de        ; park the CALL cursor
                ld      (FN_PTR),hl         ; the body is what gets evaluated
                ld      hl,$FFFF
                ld      (FN_KEY),hl         ; ...and this is the phase mark
                ld      a,1
                jp      dfn_req

; --- dfn_bodydone: the body's value came back ------------------------------
dfn_bodydone:                               ; B = $81/$82
                ld      hl,(FN_DPTR)
                ld      (FN_PTR),hl         ; the cursor past the WHOLE call, back
                                            ; where fn_fin reads it
                ld      a,(FN_RTYPE)
                cp      DEFTBL_STR
                ld      a,b
                jr      z,dfn_bd_str
                cp      $81
                jp      nz,dfn_err13        ; `DEF FNA(X)=A$` -- a string body in a
                                            ; numeric function
                ; 🎯 THE RESULT COERCION RIDES THE VARIABLE STORE RATHER THAN
                ; DUPLICATING THE CODEC. By now the formals have been read and
                ; slot 0 is dead, so the value goes through var_store_fac /
                ; var_load_fac on a scratch slot keyed $FFFF. That is the
                ; int-truncate / single-round / double-widen ladder spec §11.2
                ; already owns, and it is what makes `DEF FNA%(X)=X/2` answer 2
                ; where its `!` twin answers 2.5.
                ld      hl,FN_PAREA
                ld      (hl),$FF
                inc     hl
                ld      (hl),$FF
                inc     hl
                ld      a,(FN_RTYPE)
                ld      (hl),a
                ld      (FN_TYP),a
                ld      a,low FN_PAREA + FN_SLOTSZ
                ld      (FN_FEND),a
                ld      a,2                 ; store the result into the $FFFF slot
                jp      dfn_req
dfn_bd_str:
                cp      $82
                jp      nz,dfn_err13        ; a `$` function whose body is not a
                                            ; string is ERR 13 (o.strbody)
                ld      a,3                 ; snapshot it off the frame, then leave
                jp      dfn_req
dfn_load:
                ld      a,4                 ; load the coerced result, then leave
                jp      dfn_req

; --- the dispositions ------------------------------------------------------
; 🎯 EVERY ONE OF THESE IS RAISED BY THE SERVICER'S ONE `ld a,(FN_TYP) / jp
; raise_error`, which is why three error tails left basic/deffn.asm when the
; parse did. ERR 7 is the only disposition still resident, because the Z80-stack
; floor is tested before any tenant call and SP is not something a routine under
; CALSLT may move.
dfn_err2:
                ld      a,2                 ; Syntax error
                jp      dfn_raise
dfn_err5:
                ld      a,5                 ; Illegal function call
                jp      dfn_raise
dfn_err13:
                ld      a,13                ; Type mismatch
                jp      dfn_raise
dfn_err18:
                ld      a,18                ; Undefined user function
dfn_raise:
                ld      (FN_TYP),a
                xor     a                   ; request 0 = raise FN_TYP
                jp      dfn_req

; ===========================================================================
; Sub-local clones (see the file header for why a page-0 tenant needs them)
; ===========================================================================

; --- dfn_name_key: basic/vars.asm's var_name_key, sub-side -----------------
; in:  HL = cursor at the first name char (guaranteed a letter).
; out: B = name0 (upcased), C = name1 (upcased letter / digit, or 0), A = the
;      RESOLVED type (2/4/8/DEFTBL_STR), HL past the whole name + any suffix.
; ⚠️ THE TYPE COMES BACK IN A, NOT IN (VARTYPE), and that is not a style choice:
; between this call and its use the servicer runs `eval`, which re-runs the
; resident var_name_key for every variable factor in the actual and overwrites
; the global. The resident caller (ex_deffn) reads VARTYPE immediately and is
; unaffected; here the type has to survive a bounce, so it goes to FN_TYP /
; FN_RTYPE via A.
; ⚠️ D-NAMSPC's widening is preserved verbatim: a name may contain SPACES at any
; position, and on the NO-SUFFIX path HL comes back past the name's TRAILING
; spaces too, because the skip in dfn_ident_cont runs before the name is
; decided. `DEF FNA (X)=X` is what depends on it -- the recorded definition
; pointer lands on the `(`.
dfn_name_key:
                ld      a,(hl)
                call    upcase
                ld      b,a                 ; name0
                inc     hl
                ld      c,0                 ; name1 default (single-char name)
                call    dfn_ident_cont
                jr      nc,dfn_nk_suffix
                call    is_letter
                jr      nc,dfn_nk_set2      ; a DIGIT second char is verbatim, and
                call    upcase              ; is_letter/dfn_ident_cont leave it in A
dfn_nk_set2:
                ld      c,a                 ; name1
                inc     hl
dfn_nk_more:
                call    dfn_ident_cont      ; consume (ignore) any 3rd+ chars --
                jr      nc,dfn_nk_suffix    ; and any spaces between them
                inc     hl
                jr      dfn_nk_more
dfn_nk_suffix:
                ld      a,(hl)              ; optional type suffix
                cp      '%'
                jr      z,dfn_nk_pct
                cp      '!'
                jr      z,dfn_nk_bang
                cp      '#'
                jr      z,dfn_nk_hash
                cp      '$'
                jr      z,dfn_nk_str
                jr      dfn_deftbl          ; no suffix -> the DEFtbl default for
                                            ; name0, and HL is NOT advanced
dfn_nk_pct:
                ld      a,2
                jr      dfn_nk_eat
dfn_nk_bang:
                ld      a,4
                jr      dfn_nk_eat
dfn_nk_hash:
                ld      a,8
                jr      dfn_nk_eat
dfn_nk_str:
                ld      a,DEFTBL_STR
dfn_nk_eat:
                inc     hl
                ret

; --- dfn_ident_cont: basic/vars.asm's is_ident_cont, sub-side --------------
; in:  HL = cursor. out: HL on the first NON-SPACE byte, A = that byte, CF set
; iff it is a letter or a digit. A is an OUTPUT (D-NAMSPC moved the load in
; here). The charset is the EXECUTOR's, not the tokeniser's -- `B .5` stays a
; Syntax error, which is D-NAMDOT's knife K4 written as a comment.
dfn_ident_cont:
                call    skip_spaces         ; A = first non-space, HL on it
                call    is_letter           ; letter -> CF set, A preserved
                ret     c
                cp      '0'
                jr      c,dfn_ic_no
                cp      '9'+1
                jr      nc,dfn_ic_no
                scf                         ; digit -> CF set
                ret
dfn_ic_no:
                or      a                   ; CF clear
                ret

; --- dfn_deftbl: basic/vars.asm's deftbl_lookup, sub-side ------------------
; in: B = upcased name0 letter. out: A = DEFTBL[B-'A'] (2/4/8/DEFTBL_STR).
; Preserves BC and HL -- the no-suffix path above needs the cursor NOT advanced
; and the key intact.
dfn_deftbl:
                push    hl
                ld      a,b
                sub     'A'
                ld      l,a
                ld      h,0
                ld      de,DEFTBL
                add     hl,de
                ld      a,(hl)
                pop     hl
                ret
