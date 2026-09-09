; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; vars.asm — integer variable store (multi-character names).
;
; Each variable is a 16-bit integer held in a dynamically-allocated table of
; 4-byte entries: [name0][name1][value:2]. Names are significant to two
; characters (public MSX-BASIC language reference): `name0` is the first letter,
; `name1` the second name char (letter or digit) or 0 for a single-char name.
; Any 3rd+ name characters and a trailing type-suffix (`% ! # $`) are consumed
; but ignored, so e.g. `SCORE`, `SC` and `SCX` all map to key (`S`,`C`). A name0
; of 0 marks the first free slot; lookup of an unset variable yields 0 (MSX
; auto-initialises numerics to 0).
;
; Phase 1 grew this from the single-letter A..Z store. zerobas is still
; integer-only: there are no string variables, arrays, or floats yet.
;
; Clean-room: original code. Variable *semantics* (a named 16-bit cell, 2
; significant characters, default 0) follow the public MSX-BASIC language
; reference; the table layout is our own choice (see PROVENANCE.md). No
; disassembly.
;
; F3 S3a (repack build only — docs/spec-basic-float-core.md §11): numeric
; variables become TYPED. A variable's identity is (name0, name1, resolved
; type); the resolved type comes from the name's suffix (`%`->2 int, `!`->4
; single, `#`->8 double, unsuffixed->8 double, hardcoded in S3a — the per-
; letter DEFtbl that can override the unsuffixed default is S3b, a separate
; slice). `A`, `A%`, `A!`, `A#` are up to 4 distinct entries, packed with
; VARIABLE-WIDTH entries [name0:1][name1:1][type:1][value: 2/4/8] instead of
; a fixed 4-byte stride — see var_find_typed/var_load_fac/var_store_fac
; below. Through F3/slice-4a the numeric pool stayed the fixed 128-byte span
; $E1C0..$E240 (VARTAB/VAREND, sysvars.inc); arrays slice-4b (docs/spec-
; basic-arrays-slice4b-scalar-reloc.md) RELOCATES it out of that fixed pool
; into the real-MSX contiguous chain (program text -> scalars -> arrays ->
; free -> string heap), where var_find_typed/var_alloc_or_find below become
; thin glue over the ARY sub-ROM tenant's new SCALAR_FIND/SCALAR_ALLOC ops
; (sub/arrays.asm) — VARTAB/VAREND are DEAD (the 128 B they described is freed
; RAM).
;
; ✅ `var_find` / `var_get_key` / `var_set_key` WERE the old int-only fixed-pool
; implementation with no callers left, and this header used to say so in the
; present tense and file their removal as a future carve. **They are gone** --
; the ROM REGION STRUCTURE REVIEW's R1 carve took them (and VARTAB / VARENTSZ /
; VARSLOTS / VAREND with them, see basic/sysvars.inc's own note); the paragraph
; describing them as still here outlived the code by three weeks and was found
; on 2026-08-22 by D-DEFFN looking for exactly the carve it advertises. The
; conclusion is inverted rather than deleted because the CLASS is worth keeping
; visible: a retired build's leftovers are a real carve source, and this one
; was already spent.

; --- is_ident_cont: skip spaces at (HL), then CF set iff an ident-cont char --
; 🔴 THIS IS A CURSOR SCAN, NOT A PREDICATE ON A. It used to be "CF set if A is
; an identifier continuation char, A preserved", and its three callers each did
; their own `ld a,(hl)` first. D-NAMSPC (docs/spec-basic-namspc.md, 55 rows on
; three sides with BOTH references agreeing) moved that load in here and put a
; space skip in front of it:
;   in:  HL = cursor.
;   out: HL on the first NON-SPACE byte, A = that byte, CF set iff it is a
;        letter 'A'..'Z'/'a'..'z' or a digit '0'..'9'. A is an OUTPUT now.
; 🎯 A SPACE INSIDE A VARIABLE NAME IS INSIGNIFICANT ON THE REFERENCE, AND THIS
; IS THE WHOLE RULE. `AB=7 : PRINT A B` reads ` 7 ` -- ONE value, the variable
; AB -- on both a VG-8020 and a CF-3300; `NEXT A B` closes a `FOR AB` loop;
; `A B C=7`, `AB CD` and `A B$` all key exactly what their contiguous spellings
; key. It reaches EVERY variable reference in every expression, which is why it
; lives in the one routine all three name-scan read points share rather than at
; the callers ([[a-shared-engine-fix-must-measure-its-other-callers]]).
; 🎯 AND IT IS FREE: all three callers were already loading the byte, so the
; three deleted `ld a,(hl)` pay for the `call skip_spaces` exactly (spec §6.3).
; ⚠️ THE SPACE IS GENUINELY THERE -- rows t.name / t.dollar / t.dig read the
; STORED LINE BYTES and the $20 survives the crunch on all three sides, in every
; position, INCLUDING before a digit (`1 A 1=1` -> 41 20 31 ..., the digit still
; verbatim). That is what says the fix belongs to the parser and not to the
; tokeniser, and a screen reading cannot tell the two apart.
; ⚠️ THE CHARACTER SET IS UNCHANGED, AND THAT DISTINCTION IS LOAD-BEARING.
; D-NAMDOT's knife K4 made the filed "accept `.` too" change here and drove
; `B.5=7` from ERR 2 to ERR 0 -- MSX1's tokeniser charset and its executor
; charset really are different charsets (PROVENANCE.md). This skips $20 BEFORE
; the same test; `B .5` stays Syntax error.
is_ident_cont:
                call    skip_spaces         ; A = first non-space, HL on it
                call    is_letter           ; letter -> CF set, A preserved
                ret     c
                cp      '0'
                jr      c,iic_no
                cp      '9'+1
                jr      nc,iic_no
                scf                          ; digit -> CF set
                ret
iic_no:
                or      a                    ; CF clear
                ret

; --- var_name_key: parse a variable name at (HL) -> key in BC ---------------
; in:  HL = cursor at the first name char (guaranteed a letter).
; out: B = name0 (upcased), C = name1 (upcased letter / digit, or 0). HL is
;      advanced past the whole name + any type-suffix char. Clobbers A.
; ⚠️ D-NAMSPC: the name may contain SPACES at any position inside it, and on the
;      NO-SUFFIX path HL comes back past the name's TRAILING spaces too -- the
;      skip in is_ident_cont runs before vnk_more decides the name has ended.
;      That is the same widening D-TGTSPC made one cursor position later, now at
;      all 11 call sites; rows w.let / w.print / w.for / w.comma are green BEFORE
;      and AFTER and are what catch a scan that eats one delimiter too many.
;      The SUFFIX path (vnk_eat) does NOT skip, so tgt_parse's own skip_spaces
;      is still load-bearing for `A$ (1)`.
; In the crunched stream a name's letters are already upcased and its digits are
; kept verbatim (see the tokeniser's identifier path), so this walks plain ASCII.
var_name_key:
                ld      a,(hl)
                call    upcase
                ld      b,a                 ; name0
                inc     hl
                ld      c,0                 ; name1 default (single-char name)
                call    is_ident_cont       ; D-NAMSPC: skips spaces first, so
                jr      nc,vnk_suffix       ; `A B` reaches name1 = 'B'
                call    is_letter
                ; D-NAMSPC carve: this used to branch to a `vnk_dig2` that did
                ; `ld a,(hl)` / `jr vnk_set2` -- a RELOAD OF WHAT A ALREADY
                ; HOLDS. is_letter is `push af` .. `pop af` on both exits and
                ; is_ident_cont only `cp`s, so a DIGIT second char is still in A
                ; here; the only thing vnk_set2's `upcase` would have done to it
                ; is nothing. −3 B, and rows r.digctl / r.dig / a.dig are what
                ; fail if that register reading is wrong (knife K-NS2).
                jr      nc,vnk_set2         ; digit second char -> verbatim, no upcase
                call    upcase
vnk_set2:
                ld      c,a                 ; name1
                inc     hl
vnk_more:
                call    is_ident_cont       ; consume (ignore) any 3rd+ chars --
                jr      nc,vnk_suffix       ; and any spaces between them
                inc     hl
                jr      vnk_more
; F3 S3a: the suffix now additionally RESOLVES the variable's type into
; (VARTYPE), sysvars.inc — replacing an earlier "consume and ignore" vnk_suffix. Consuming behaviour (which chars advance HL) is UNCHANGED:
; `%`/`!`/`#`/`$` are all still eaten; no suffix leaves HL on the following
; char, exactly as before.
vnk_suffix:
                ld      a,(hl)              ; optional type suffix
                cp      '%'
                jr      z,vnk_pct
                cp      '!'
                jr      z,vnk_bang
                cp      '#'
                jr      z,vnk_hash
                cp      '$'
                jr      z,vnk_dollar
                ; No suffix (S3b): the resolved type is the DEFtbl default for
                ; name0 (B, set at entry and preserved through the name walk) --
                ; DEFINT/SNG/DBL/STR may have overridden the double default.
                ; deftbl_lookup preserves BC/DE/HL, so the key + cursor survive.
                call    deftbl_lookup       ; A = DEFtbl default for name0 (B)
                ld      (VARTYPE),a         ; a DEFSTR letter yields 1 here, harmless:
                                            ; the numeric path is never entered for a
                                            ; name var_str_type routed to STRTAB
                ret                         ; no suffix -> HL NOT advanced (unchanged)
vnk_pct:
                ld      a,2
                ld      (VARTYPE),a
                jr      vnk_eat
vnk_bang:
                ld      a,4
                ld      (VARTYPE),a
                jr      vnk_eat
vnk_hash:
                ld      a,8
                ld      (VARTYPE),a
                jr      vnk_eat
vnk_dollar:
                ; D-FORVAR (docs/spec-basic-forvar.md §4.2): this used to write 8
                ; — byte for byte a default-double `A` — and five comments in
                ; this tree existed to warn readers that (VARTYPE) LIES for a `$`
                ; name. DEFTBL_STR is the code this SAME cell already carries for
                ; a DEFSTR'd unsuffixed name, so the value lands in an
                ; equivalence class every reader already handles rather than in a
                ; new one. It buys three measured rows: `NEXT A$` now matches no
                ; FOR frame (n.strnx — a MISS, which is what both references
                ; answer, not a type error), `FOR A$=` shares one guard with
                ; `DEFSTR A` / `FOR AB=` (f.str + f.defstr), and ev_f_var's
                ; check_vartype_num finally SEES a `$` name in a numeric factor
                ; — `A$="X" : B=1+A$` read ` 1 ` here against Type mismatch on
                ; both references (x.numstr), D-DEFSTR's own silent-wrong-answer
                ; class in the explicitly-suffixed form that slice did not cover.
                ld      a,DEFTBL_STR
                ld      (VARTYPE),a
vnk_eat:
                inc     hl
                ret

; --- var_str_type: does the name at (HL) carry a `$` suffix? -----------------
; in:  HL = cursor at the first name char (a letter). HL is NOT advanced.
; out: A = 1 if the name is a string variable, else 0. CF = the A==1 condition
;      is also reflected (set iff string). Clobbers A (repack build additionally
;      uses B/DE as scratch for the DEFtbl lookup -- no caller relies on those
;      across this call: each follows with eval() or var_name_key, which reset
;      BC/DE).
; Walks the identifier (letters/digits -- and, D-NAMSPC, across any SPACES inside
; the name: `A B$` is a STRING) to the first non-identifier char. A name
; is a string variable if it carries a `$` suffix OR (repack, S3b) it is
; unsuffixed and its first letter's DEFtbl default is DEFTBL_STR (DEFSTR). An
; explicit `% ! #` suffix is always numeric. Used by LET / PRINT / the factor
; layer to choose the string path before delegating the real advance to
; var_name_key.
var_str_type:
                ld      a,(hl)              ; F3 S3b: capture name0 for the DEFtbl
                call    upcase              ; default lookup below (the walk preserves
                ld      b,a                 ; B); repack-only scratch use of B/DE
                push    hl
vst_walk:
                call    is_ident_cont       ; D-NAMSPC: spaces inside the name are
                jr      nc,vst_suffix       ; skipped here too, so `A B$` is a STRING
                inc     hl
                jr      vst_walk
vst_suffix:
                cp      '$'
                jr      z,vst_yes
                cp      '%'                 ; an EXPLICIT numeric suffix is never a string,
                jr      z,vst_no            ; whatever DEFSTR may say for this letter
                cp      '!'
                jr      z,vst_no
                cp      '#'
                jr      z,vst_no
                ld      a,b                 ; no suffix -> consult the DEFtbl default
                call    is_letter           ; ...but only for a real name: MID$ literal
                jr      nc,vst_no           ; targets (MID$("AB",1)=..) and other non-
                                            ; letters reach here unguarded, and a non-
                                            ; letter name0 is never a string variable --
                                            ; guard keeps the DEFtbl index in range
                call    deftbl_lookup       ; A = DEFtbl default for name0 (B)
                cp      DEFTBL_STR          ; (DEFSTR makes an unsuffixed name a string)
                jr      z,vst_yes
vst_no:
                pop     hl
                xor     a                   ; not a string (A=0, CF clear)
                ret
vst_yes:
                pop     hl
                ld      a,1
                scf                          ; string (A=1, CF set)
                ret

; =============================================================================
; D-ARYLV — the lvalue TARGET layer for READ / INPUT / LINE INPUT.
; docs/spec-basic-arylv.md. Measured surface: docs/arylv-msx1-scout.md, 18 rows
; x 3 sides with BOTH references agreeing on all 18.
;
; A READ/INPUT target is any VARIABLE REFERENCE, which includes an ARRAY ELEMENT
; with a full subscript list -- any rank, any expression per subscript, at any
; position in the variable list. var_name_key above walks a name and a type
; suffix and never a subscript, so all four target-parse sites (ex_read's exr_lp,
; and input.asm's inpc_vloop / inpc_vstr / inpc_line) answered Syntax error where
; both references read the value.
;
; 🎯 THE FIX ALREADY EXISTED IN THIS TREE, TWICE: `A(1)=7` works (ex_let_arr /
; ex_let_arr_str, basic/arrays.asm) and `SWAP A,Q(0)` works (sw_operand/sw_array,
; basic/missing.asm). This was an inconsistency BETWEEN VERBS, not a missing
; capability -- which is why the scout's `c.let` row is a positive control: it is
; what says every red row was a missing PARSE and not a missing STORE.
;
; WHAT THE FOUR SITES SHARE IS ONE HEAD AND *TWO* STORES, not one head. The store
; forks by TYPE (numeric/string) and independently by TARGET FORM (scalar key /
; element address) -- a 2x2 of which the four sites use three combinations -- so
; folding the store into the parse would have been the mistake.
;
; 🔴 THESE LIVE IN PAGE 1 BECAUSE THREE OF THE FOUR SITES CANNOT AFFORD THEM.
; basic/input.asm is the LOW REGION, which had 3 B free; basic/program.asm is
; page 1. Low -> page-1 calls are already what inpc_vloop does for var_name_key /
; var_store_fac / str_set_key. Homing the shared code here makes all three low
; sites SHORTER than the sequences they replace, so the change spends page 1 and
; GIVES BACK low (spec §5.4 / scout §5).

; --- tgt_parse: a variable REFERENCE -- name, type suffix, optional (subs) ---
; in:  HL = cursor at the name's first letter (the caller has already checked
;           is_letter);
;      A  = the mode, exactly var_str_type's own return: 0 numeric / 1 string.
;           🎯 EVERY CALL SITE ALREADY HAS IT IN A at the call -- the same reuse
;           that funded 17 of D-READVAR's 32 bytes.
; out: Z  = ok / NZ = the array resolve failed, FPERR already mapped+set by
;           ary_engine_call (the caller aborts with `jp nz,fp_runtime_error`);
;      BC = the key (a SCALAR target's store argument);
;      HL = cursor past the whole reference (past `)` for an array; on the SCALAR
;           path, past any TRAILING SPACES too -- D-TGTSPC, see below);
;      (TGT_ADDR) = the element address, or 0 for a scalar.
; Clobbers A,BC,DE,HL. ⚠️ DE is NOT preserved (var_name_key alone did preserve
; it); checked at every site -- none has DE live across this call.
;
; ⚠️ THE CALL-SITE COUNT IN THIS TREE'S DOCS WAS WRONG UNTIL D-TGTSPC WALKED IT.
; This header said FOUR (D-ARYLV's), TODO.md and spec-basic-nxary.md said SEVEN.
; There are EIGHT `call tgt_parse` instructions from NINE statement surfaces:
;   ex_next (program.asm) NEXT · ex_read (program.asm) READ · inpc_vloop
;   (input.asm) console INPUT numeric · inpc_vstr (input.asm) console INPUT
;   string · inpc_line (input.asm) LINE INPUT · ex_mid_stmt (str-engine.asm)
;   MID$()= · inp_readvar (files.asm) INPUT #n · tgt_parse_fld (field.asm) ->
;   FIELD..AS and LSET/RSET.
; A rule changed here changes what a target MEANS at all nine
; ([[a-shared-engine-fix-must-measure-its-other-callers]]).
tgt_parse:
                push    af                  ; the mode must survive var_name_key
                call    var_name_key        ; BC=key, HL past name+suffix, (VARTYPE)
                ; D-TGTSPC (docs/spec-basic-tgtspc.md, 28 rows on three sides with
                ; BOTH references agreeing): the `(` may be separated from the name
                ; by SPACES. `NEXT A (1)` / `READ A (1)` / `LSET A$ (1)=` all target
                ; the ELEMENT on both references, and the space is genuinely THERE
                ; -- row t.spc reads the STORED LINE BYTES and the $20 survives the
                ; crunch byte for byte on all three sides, which is what says the
                ; fix belongs to the parser and not to the tokeniser.
                ; 🎯 ONE INSTRUCTION, IN THE ONE PLACE ALL NINE SURFACES SHARE. This
                ; is +2 B (skip_spaces returns exactly what `ld a,(hl)` returned when
                ; there is no space, with HL on the byte in A); eight per-caller
                ; skips would be >= 16 B into a 5 B wall and would still be wrong for
                ; the next caller anyone adds.
                ; ⚠️ AND IT CONSUMES A TRAILING SPACE ON THE SCALAR PATH TOO, WHICH IS
                ; A SECOND FIX AND NOT A SIDE EFFECT. Eight of the nine callers cannot
                ; see it -- each does its own skip_spaces before its next delimiter.
                ; ex_mid_stmt is the exception (`pop hl` / `ld a,(hl)` / `cp ','`), and
                ; row m.trail says `MID$(A$ ,1,2)="XY"` is XYLLO on both references and
                ; was Syntax error here. Spec §4.3.
                ; ⚠️ NOT EARLIER THAN var_name_key: a space INSIDE the name or before
                ; the `$` suffix is a different and far wider rule (rows x.dollar /
                ; x.name, both DEFERRED -- the reference's whole name scan skips
                ; spaces, so `NEXT A B` closes a `FOR AB` loop). Spec §5.2.
                call    skip_spaces         ; A = the first non-space, HL on it
                cp      '('                 ; a `(` after a name (spaces aside) is
                jr      z,tp_ary            ; unambiguously a subscript -- ev_f_var/
                                            ; str_eval_one rely on the same
                                            ; disambiguation (arrays §9.4)
                pop     af
                ld      de,0                ; 0 = "scalar; store through the key"
                xor     a                   ; Z = ok
                jr      tp_set
tp_ary:
                pop     af                  ; A = mode
                or      a
                jr      nz,tp_res           ; string -> ary type 1, already in A
                ld      a,(VARTYPE)         ; numeric -> the resolved type (F3)
tp_res:
                call    ary_op0_resolve     ; op=0 RESOLVE, auto-dims on first
                                            ; reference -- which is what makes the
                                            ; scout's unDIMmed row read a value
                ret     nz                  ; FPERR set; HL = cursor, nothing to unwind
tp_set:
                ld      (TGT_ADDR),de       ; (LD (nn),rr touches no flag, so the Z
                ret                         ; from either path survives to the caller)

; --- tgt_store_num: an int16 -> the resolved target -------------------------
; in:  BC = key (scalar targets only), DE = the value, (TGT_ADDR) per tgt_parse.
; Clobbers everything. Both arms coerce into the target's own resolved type.
tgt_store_num:
                ld      a,2
                ld      (FACTYP),a          ; DE is a plain int16 (F3: the store widens
                                            ; it per the target's type, e.g. double)
                ld      hl,(TGT_ADDR)
                ld      a,h
                or      l
                jr      nz,tsn_ary
                ld      a,(VARTYPE)
                jp      var_store_fac       ; scalar: var[key] := DE, coerced
tsn_ary:
                ld      a,(ARY_TYPE)        ; 🔴 NOT (VARTYPE) -- spec §5.2. Resolving
                                            ; A%(I) evaluates the subscript, which
                                            ; re-runs var_name_key for I and OVERWRITES
                                            ; (VARTYPE) with I's type. ary_parse_call
                                            ; latches the target's own type in ARY_TYPE
                                            ; for exactly this reason. With an untyped
                                            ; A(I) both cells hold the DEFtbl double and
                                            ; the substitution is INVISIBLE, which is why
                                            ; the scout carries r.arypct (and why K-AL4
                                            ; is a one-row knife rather than a no-op).
                jp      ary_store_write     ; array: element := DE, coerced

; --- tgt_store_str: the STRSCR field -> the resolved target -----------------
; in:  BC = key (scalar targets only), STRSCR = [len][bytes], (TGT_ADDR).
; Clobbers everything -- every caller already guards its text cursor on the
; stack across the store it replaces.
tgt_store_str:
                call    strscr_desc         ; HL = RVDESC -> [len][ptr] over STRSCR
                ld      de,(TGT_ADDR)
                ld      a,d
                or      e
                jr      nz,tss_ary
                ex      de,hl               ; DE = RVDESC (str_set_key's source arg)
                jp      str_set_key         ; scalar: var$[key] = the bytes
tss_ary:
                ; ex_let_arr_str's own shipped tail, byte for byte (call+pop ->
                ; jp): re-publish the element address as op=3's input and copy.
                ; 🎯 NO ary_snapshot_offset/ary_apply_offset HERE, and that is an
                ; argument rather than an omission (spec §5.1): ex_let_arr_str
                ; needs the ARYTAB-delta correction because `str_eval` runs
                ; between its resolve and its store and can allocate a scalar
                ; (VARPTR). Nothing on any of these FIVE store paths can --
                ; read_one_value is a subrom_call plus RAM reads, and
                ; read_into_strscr (console AND inp_readvar's file channel,
                ; D-LVFIX) calls only arl_getbyte. The source descriptor points
                ; into STRSCR, a fixed buffer, so a GC inside heap_alloc cannot
                ; move it either. ⚠️ ex_mid_stmt is the site where that argument
                ; does NOT hold -- see tgt_desc below.
                ld      (STRPTR),hl         ; source descriptor (aeng_copy_str's input)
                ld      (ARY_ADDR),de       ; dest element slot
                ld      a,3
                ld      (ARY_OP),a          ; op = 3 (COPY_STR)
                jp      ary_engine_call     ; NZ + FPERR on OOM; every caller runs a
                                            ; check_expr_errors* right after.
                                            ; D-ARYOOS: the OOM here is aeng_copy_str's
                                            ; heap_alloc, so it now arrives as ARY_ERR=5
                                            ; -> ERR 14 `Out of string space` instead of
                                            ; ERR 7. MEASURED at THIS site, not inferred
                                            ; from ex_let_arr_str's: row s.inpary,
                                            ; `INPUT A$(2)` on a full pool, is
                                            ; `Out of string space in 50` on vg8020,
                                            ; cf3300 and here, with s.inpscal (`INPUT
                                            ; D$`) as the scalar control.
                                            ; 🔴 READ IS NOT A TEST OF THIS SITE, and
                                            ; the row written to be one refuted itself:
                                            ; `READ A$(2)` answers `[OK]` on BOTH
                                            ; references, because a stored DATA
                                            ; literal's descriptor points AT THE PROGRAM
                                            ; TEXT and charges the pool nothing. The
                                            ; scalar twin `READ D$` diverges the same
                                            ; way, which is what proves it is the
                                            ; S-CLP-5 body-ownership question (signed
                                            ; off out of scope) and not this rule.
                                            ; INPUT's bytes come from a TRANSIENT line
                                            ; buffer, so the reference must copy, and
                                            ; there the two sides agree. TODO.md
                                            ; carries the READ residual.

; --- tgt_desc / tgt_desc_fix: a target HELD ACROSS AN EVALUATION -------------
; D-LVFIX (docs/spec-basic-lvsites.md §4.1/§5.1). ex_mid_stmt does not STORE
; through its target -- it stashes the target's DESCRIPTOR ADDRESS in MIDS_DEST,
; then parses n, m and the whole RHS, and only then hands the address to the
; sub-ROM tenant. Every one of those three evaluations can run VARPTR(<new
; var>), which arrays slice-4b §13a names as THE ONLY eval-time scalar allocator
; and which shifts the entire array region up by one scalar entry.
;
; 🔴 §13a's site audit EXEMPTED ex_mid_stmt in as many words -- "targets a SCALAR
; string in the fixed STRTAB pool ... so unaffected" -- and that exemption is a
; statement about the TARGET. Giving it an array element makes it the third site
; of the class, so the delta correction is forced, not defensive hardening: the
; symptom without it is a silent write to a neighbouring element.
;
; 🎯 THE OFFSET IS THE SNAPSHOT. ex_let_arr must push a separate [OFFSET] word
; (ary_snapshot_offset) because it keeps the raw address as well. Here the stash
; cell already exists, so storing an ARYTAB-RELATIVE offset in it instead of an
; address costs no stack word, no error-tail pop and no second RAM cell.
;
; ⚠️ The SCALAR arm is deliberately left uncorrected (§5.2): a scalar-chain
; insert shifts only the entries ABOVE the insertion point, so the ARYTAB delta
; is the wrong correction for it and applying it uniformly would turn a
; sometimes-stale address into an always-wrong one. Whether the scalar arm is
; stale today is a separate, pre-existing question -- the probe's m.ctldrift row
; measures it and does not fix it.
;
; ⚠️ (TGT_ADDR) is the arm discriminator and must survive the whole argument
; parse, so nothing between tgt_desc and tgt_desc_fix may call tgt_parse. It
; cannot today: all six tgt_parse callers are statement heads, and no statement
; head runs inside an eval. A future EXPRESSION-level caller breaks this
; silently.

; tgt_desc — in:  BC = key, (TGT_ADDR) = element address, or 0 for a scalar.
;            out: HL = scalar: the STRTAB descriptor address, verbatim;
;                      array : elem_addr - ARYTAB, an ARYTAB-relative offset.
tgt_desc:
                ld      hl,(TGT_ADDR)
                ld      a,h
                or      l
                jp      z,str_get_key       ; scalar: today's instruction, today's
                                            ; register contract, today's value
                ld      de,(ARYTAB)
                or      a
                sbc     hl,de               ; the §13a snapshot, folded into the value
                ret

; tgt_desc_fix — in:  (MIDS_DEST) as tgt_desc left it, (TGT_ADDR).
;                out: HL = the descriptor address, corrected for any ARYTAB move
;                     since. Keyed on the DELTA regardless of cause, so an
;                     auto-DIM or a string GC inside the RHS is covered by the
;                     same arithmetic.
tgt_desc_fix:
                ld      hl,(MIDS_DEST)
                ld      de,(TGT_ADDR)
                ld      a,d
                or      e
                ret     z                   ; scalar: unchanged (§5.2)
                ld      de,(ARYTAB)
                add     hl,de               ; offset + ARYTAB_now = §13a corrected
                ret
; =============================================================================

; --- (removed) the retired lean cart's int-only fixed-pool scalar store -----
; `var_find` / `var_get_key` / `var_set_key` lived here: a linear walk over the
; fixed 4-byte VARTAB pool, keyed on (name0,name1) with no type. Arrays slice-4b
; relocated shipped scalars into the real-MSX contiguous chain (the ARY sub-ROM
; tenant's scv_find/scv_alloc), which left all three with ZERO callers -- pasmo
; had been reporting two of them as unused ever since, inside ~230 lines of
; warning noise nobody read. Deleted by the ROM REGION STRUCTURE REVIEW's R1
; carve (docs/spec-rom-region-rebalance-r1.md A1): 80 B of main PAGE 1.
; The live typed counterparts are var_find_typed / var_alloc_or_find below --
; ⚠️ SIMILAR NAMES, DIFFERENT ANIMALS; the banner below is the one that matters.

; =============================================================================
; F3 S3a — the typed variable store (docs/spec-basic-float-core.md §11). These
; are the live counterparts to the int-only var_find walk that used to sit above
; (deleted by R1's carve), keyed on (name0, name1, type) and variable-width.
;
; Arrays slice-4b (docs/spec-basic-arrays-slice4b-scalar-reloc.md §3/§4/§5):
; the fixed VARTAB pool walk/room-check that used to live here MOVED into the
; ARY sub-ROM tenant (sub/arrays.asm scv_find/scv_alloc, new ARY_OP codes 4/5,
; Q4) — scalars now live in the real-MSX contiguous chain, sharing arrays' own
; [PRGEND+2, FRETOP) region and its FRETOP collision/GC-once-retry invariant.
; var_find_typed / var_alloc_or_find below are now THIN main-ROM glue: fill
; the (reused, unchanged) ARY_KEY/ARY_TYPE param-block fields, dispatch, read
; back ARY_ADDR/ARY_ERR. Both keep their PRE-4b register contract exactly, so
; var_load_fac/var_store_fac (below) and VARPTR (ev_f_varptr, expr.asm) —
; which call them — are UNCHANGED.
; =============================================================================

; --- var_find_typed: locate the entry for (key BC, type A) ------------------
; in:  BC = key (name0,name1), A = type (2/4/8).
; out: CF set  -> found,     HL = entry address (name0 field).
;      CF clear -> not found, HL undefined (does NOT allocate — reading an
;                  unset scalar must not create it; that's var_alloc_or_find,
;                  below). Clobbers A, B, C, D, E, H, L (BC no longer needs to
;                  survive — the caller, var_load_fac, never re-uses it after
;                  this call). IX is GUARDED (push/pop) across
;                  ary_engine_call: this pre-4b routine's documented contract
;                  never touched IX, and callers up the chain (ev_f_var,
;                  var_get/var_set, ev_f_varptr) hold the TEXT CURSOR in IX
;                  across it — a real bug this slice's own array-acceptance
;                  differential caught (every variable-subscript/loop-var
;                  reference through a scalar produced a phantom "syntax
;                  error": the cursor IX was silently trashed by
;                  ary_engine_call's own `ld ix,SUBROM_ENTRY_BASE_P0+...`).
var_find_typed:
                ld      (ARY_KEY),bc
                ld      (ARY_TYPE),a
                ld      a,4                 ; op = SCALAR_FIND
                ld      (ARY_OP),a
                push    ix                  ; guard the caller's IX (the text
                                            ; cursor, in every real caller)
                call    ary_engine_call     ; find never errors (ARY_ERR
                                            ; always 0 for op=4) -- the NZ/
                                            ; FPERR-mapping path is simply
                                            ; never taken here
                pop     ix
                ld      hl,(ARY_ADDR)
                ld      a,h
                or      l
                jr      z,vft_notfound      ; ARY_ADDR=0 -> not found (0 is
                                            ; never a valid entry address --
                                            ; program text starts at $8001)
                scf
                ret
vft_notfound:
                or      a
                ret

; --- var_alloc_or_find: BC=key, A=type -> HL = entry base, CF set ------------
; (name0/name1/type already written if this call just allocated the entry; a
; freshly allocated entry's VALUE bytes are zero-filled too, so an unset
; variable always reads back as 0). CF clear = Out of memory: the WHOLE chain
; is exhausted (§7.3 — this REPLACES the pre-4b fixed-pool silent-drop with a
; SURFACED runtime error, matching the array OOM disposition: FPERR is
; already set via ary_errmap by the time this returns NC, since op=5's
; ARY_ERR=4 maps through the SAME table entry arrays' own OOM uses). Nothing
; is written on failure (leaves state consistent). Shared by var_store_fac
; (which overwrites the value field afterward) and VARPTR (ev_f_varptr,
; expr.asm), which only needs the entry to EXIST. Clobbers A, B, C, D, E, H,
; L (BC not preserved — callers needing the key afterward must save it
; themselves, unchanged from the pre-4b contract). IX is GUARDED (push/pop)
; across ary_engine_call — see var_find_typed's own header just above for
; why (the SAME caller-held-cursor hazard; var_store_fac's own caller,
; ex_let, needs its cursor to survive var_store_fac intact).
var_alloc_or_find:
                ld      (ARY_KEY),bc
                ld      (ARY_TYPE),a
                ld      a,5                 ; op = SCALAR_ALLOC (find-or-
                                            ; insert-and-shift, §3a)
                ld      (ARY_OP),a
                push    ix                  ; guard the caller's IX
                call    ary_engine_call     ; Z ok (ARY_ADDR=addr) / NZ:
                                            ; FPERR already mapped+set (OOM)
                pop     ix
                jr      nz,vaof_fail
                ld      hl,(ARY_ADDR)
                scf
                ret
vaof_fail:
                or      a                   ; CF clear
                ret

; --- var_load_fac: BC=key, A=type -> FAC set, FACTYP=type, DE=int16 fast ----
; path (§9.4/§10.3 discipline: same sticky-FACTYP + flt_int_result contract
; ev_f_float uses for literals). An unset variable reads back as 0 (MSX auto-
; init). Clobbers A, B, C, D, E, H, L.
var_load_fac:
                push    af                  ; stash the target type across the call
                call    var_find_typed      ; BC,A -> CF/HL
                jr      c,vlf_found
                pop     af                  ; A = target type (unset -> zero value)
                ld      (FACTYP),a
                cp      2
                jp     z,vlf_unset_int
                xor     a
                ld      (FAC),a             ; lead byte 0 -> float zero
                ; 🔴 D-FACZERO DELIBERATELY DOES *NOT* CALL fac_zero_mantissa HERE,
                ; AND ITS OWN KNIFE IS WHY. K-FZ3 removed the call that used to sit
                ; on this line and moved ZERO rows -- including `z.unset` /
                ; `z.dunset`, added specifically to witness it. The reason is that
                ; `A!=B!` on an unset B! does not hand FAC's bytes to the store: it
                ; RE-PACKS through widen_rhs_operand + round_single_and_pack, whose
                ; own zero exit is already canonical. So the call was 3 bytes no row
                ; could defend, and this project does not ship guards like that.
                ; ⚠️ IT COMES BACK THE DAY A CONSUMER READS FAC WITHOUT RE-PACKING,
                ; and `MKS$`/`MKD$` are exactly that consumer -- see
                ; docs/spec-basic-faczero.md §5.
                ld      de,0
                ret
; D-DUPSPAN2: an ALIAS, not a second copy -- byte-identical to vptr_none,
; and POSITION-INDEPENDENT by tools/dupspan_indep.py (terminates, no
; escaping relative jump, not entered by fallthrough, same ROM region).
; The NAME and every call site survive; un-alias here for a distinct face.
vlf_unset_int   equ     vptr_none
vlf_found:
                pop     af                  ; A = type (== the entry's own stored type)
                ld      (FACTYP),a
                cp      2
                jr      z,vlf_found_int
                ld      c,a                 ; C = byte count (4 single / 8 double)
                ld      b,0
                push    hl
                pop     de
                inc     de
                inc     de
                inc     de                  ; DE -> value field (entry+3)
                ld      hl,FAC
                ex      de,hl               ; HL=value field(source), DE=FAC(dest)
                ldir
                jp      flt_to_int16        ; DE = int16 fast path (tail call)
vlf_found_int:
                inc     hl
                inc     hl
                inc     hl                  ; HL -> value field (entry+3, 2 bytes LE)
                ld      e,(hl)
                inc     hl
                ld      d,(hl)
                ret

; --- var_store_fac: BC=key, A=target type (2/4/8) -> coerce the live RHS -----
; (DE, valid iff the CURRENT (FACTYP)==2; else FAC/FACTYP hold the RHS's own
; float value) into type A per spec §11.2, then store (allocate-if-new; the
; pool-full case is a silent drop, matching the pre-F3 behaviour). On a
; coercion-time Overflow (int store outside -32768..32767; an extreme single/
; double whose dec_exp escapes -63..63 after rounding) this sets FPERR and
; returns WITHOUT storing — mirrors fac_to_int_strict's own contract; the
; caller (ex_let) checks FPERR right after, same D-F2-1 pattern as eval()'s own
; runtime errors. Clobbers A, B, C, D, E, H, L.
;   -> int:    TRUNCATE toward zero, STRICT int16 domain (fac_to_int_strict —
;              the same rule as \, MOD, AND, OR, XOR, NOT operands; a variable
;              store is an operand context, not a POKE/HEX$ address argument,
;              so the address domain's wrap-then-truncate does NOT apply here).
;   -> single: ROUND to 6 significant digits, half-up, carry renormalise
;              (round_single_and_pack, float-arith.asm).
;   -> double: exact (round_and_finalize on an exact widen; its own guard
;              digit is always 0 for an int/single/double source, so it never
;              actually rounds — reused purely for its bound-check + BCD-pack
;              tail).
var_store_fac:
                ld      (VS_TARGET_TYPE),a  ; stash the target type across coercion
                push    bc                  ; guard the key (coercion clobbers BC)
                cp      2
                jr      z,vsf_int
                cp      4
                jr      z,vsf_single
                call    arga_widen          ; D-ARGAWIDEN
                                            ; double) into a 14-digit ARGA (float-
                                            ; arith.asm)
                call    round_and_finalize  ; no-op round (guard digit is 0) + pack as
                                            ; double + FACTYP=8 + DE
                jr      vsf_coerced
vsf_single:
                call    arga_widen          ; D-ARGAWIDEN
                call    round_single_and_pack ; 6-digit half-up round + pack as single +
                                              ; FACTYP=4 + DE
                jr      vsf_coerced
vsf_int:
                call    fac_to_int_strict   ; -> DE (truncate, strict int16 domain);
                                            ; sets FPERR=1 on overflow (spec §10.3)
                ld      (VS_INT_VAL),de     ; stash it: var_alloc_or_find (below) CLOBBERS
                                            ; DE for its room-check arithmetic, so the int
                                            ; write-back must reload from RAM, not DE
vsf_coerced:
                pop     bc                  ; BC = key restored
                ld      a,(FPERR)
                or      a
                ret     nz                  ; coercion overflow -> drop the store
                ld      a,(VS_TARGET_TYPE)
                call    var_alloc_or_find   ; BC,A -> CF/HL (name/type written + value
                                            ; zeroed if freshly allocated); clobbers DE
                ret     nc                  ; pool completely full -> silently drop
                inc     hl
                inc     hl
                inc     hl                  ; HL -> value field (entry+3)
                ld      a,(VS_TARGET_TYPE)
                cp      2
                jp     z,vsf_wb_int
                ld      c,a                 ; C = byte count (4 single / 8 double)
                ld      b,0
                push    hl
                pop     de
                ld      hl,FAC
                ldir                        ; FAC -> value field, verbatim (same [lead+
                                            ; mantissa] bytes flt_out/var_load_fac read)
                ret
; D-XREG: an ALIAS across the low <-> page-1 boundary. Byte-identical to
; asw_wb_int and POSITION-INDEPENDENT (tools/dupspan_indep.py), and the
; REGION question -- is this label reached from a tenant whose mapping
; switches the target page OUT? -- is answered by scratchpad/crossreg_probe.py
; and GATED by check_tenant_closure.py, whose K-XR1 knife proves it can see an
; `equ` (it resolves addresses from the sym, not from the source form).
vsf_wb_int      equ     asw_wb_int

; --- deftbl_lookup: resolve a name's DEFtbl default type (S3b) ---------------
; in:  B = upcased name0 letter ('A'..'Z'). out: A = DEFTBL[B-'A'] (2 int / 4
; single / 8 double / DEFTBL_STR string). Preserves BC, DE, HL. The one home of
; the "unsuffixed name -> default type" rule: shared by var_name_key's no-suffix
; path, var_str_type, and the var_get/var_set single-letter shims (FOR/NEXT,
; READ), so a DEFINT/SNG/DBL/STR default reaches EVERY reference of a name, not
; just the multi-char LET path. Callers guarantee B is a letter (var_name_key
; entry requires one; var_str_type guards with is_letter; the shims upcase a
; loop/READ variable, always a letter).
deftbl_lookup:
                push    hl
                push    de
                ld      a,b
                sub     'A'
                ld      e,a
                ld      d,0
                ld      hl,DEFTBL
                add     hl,de
                ld      a,(hl)
                pop     de
                pop     hl
                ret

; =============================================================================
; §13a fix — the stale-array-element-address bug (docs/spec-basic-arrays-
; slice4b-scalar-reloc.md §13a). Shared page-1 home for basic/arrays.asm's
; ex_let_arr / ex_let_arr_str delta-correction calls: the LOW region ($2812-
; $3FFF) has only 3 B of headroom, nowhere near this arithmetic's footprint,
; while page 1 has 73 B free (§13a "the hard part" / §4 space accounting) —
; so the correction lives HERE instead, reached from arrays.asm by an
; ordinary same-bank `call` (low region and page 1 are the main ROM's
; co-mapped slot-0 pages, per clear_vars's own heap_reset call just above —
; no subrom_call/bank-switch is involved, unlike the SUBROM_IDX_ARY tenant).
;
; Mechanism (documented MSX memory model TXTTAB->VARTAB->ARYTAB->...->FRETOP
; ->HIMEM, own realisation — arc spec §2/§3a, no disassembly): a scalar
; insertion shifts everything at/above ARYTAB up by exactly the amount ARYTAB
; itself moves. ary_snapshot_offset (called right after ary_op0_resolve,
; before the RHS `eval`/`str_eval`) captures OFFSET = ARYTAB_before - elem_addr
; and pushes it (ONE word, replacing the pre-fix code's raw [ADDR] push —
; same stack footprint, so callers' error-tail pop counts are UNCHANGED).
; ary_apply_offset / ary_apply_offset_hl_sub (called after the RHS is safely
; evaluated) re-read ARYTAB and recover the CORRECTED address = ARYTAB_now -
; OFFSET = elem_addr + (ARYTAB_now - ARYTAB_before) — exactly the spec §13a
; formula. Two apply variants because the two call sites have different live
; registers at the correction point: ex_let_arr already has the text cursor
; parked in IX (so HL is free — the simple variant clobbers it and returns
; the corrected address IN HL) and the RHS's int-fast-path value in DE (which
; MUST survive, and does — neither variant touches DE); ex_let_arr_str still
; has the cursor live IN HL at that point (str_eval's own return contract),
; so the _hl_sub variant preserves HL and returns the corrected address in DE
; instead (also untouched by the plain variant, so the choice is per-caller
; convenience, not a hard constraint).
; =============================================================================

; --- ary_snapshot_offset: push [OFFSET]=ARYTAB-elem_addr; guard the cursor -
; in:  HL = cursor (live, e.g. just past the array reference's ')'),
;      DE = elem_addr (ary_op0_resolve's own RESOLVE-path return).
; out: HL = cursor, UNCHANGED. Stack gains exactly ONE word, [OFFSET] (signed
;      16-bit, ARYTAB_before - elem_addr), pushed on top of whatever the
;      caller already had there. Clobbers BC only — A/DE are NOT touched, so
;      a caller that still needs (ARY_TYPE) or elem_addr's own value in DE a
;      moment longer is unaffected (ex_let_arr reads (ARY_TYPE) right after
;      this call).
ary_snapshot_offset:
                pop     bc              ; BC = our own return address
                push    hl              ; stash the cursor (local temp)
                ld      hl,(ARYTAB)     ; HL = ARYTAB_before
                or      a
                sbc     hl,de           ; HL = ARYTAB_before - elem_addr = OFFSET
                ex      (sp),hl         ; TOS(cursor)<->HL(OFFSET): HL=cursor
                                        ; restored, TOS=OFFSET (left for the
                                        ; caller)
                push    bc              ; restore the return address on top
                ret

; --- ary_apply_offset: pop [OFFSET] -> HL = the CORRECTED element address --
; in:  stack top (below this call's own return address) = [OFFSET], as
;      pushed by ary_snapshot_offset above.
; out: HL = ARYTAB_now - OFFSET = the corrected element address (§13a
;      formula). [OFFSET] popped (net stack effect: -1 word, like a plain
;      `pop`). Clobbers BC only — A (TYPE) and DE (the RHS's live int-fast-
;      path value / FAC) are NOT touched, so ex_let_arr's caller-held TYPE
;      (in A) and RHS value (in DE) survive straight through into
;      ary_store_write.
ary_apply_offset:
                pop     hl              ; HL = our own return address
                pop     bc              ; BC = OFFSET
                push    hl              ; restore the return address on top
                ld      hl,(ARYTAB)     ; HL = ARYTAB_now
                or      a
                sbc     hl,bc           ; HL = ARYTAB_now - OFFSET = corrected
                ret

; --- ary_apply_offset_hl_sub: pop [OFFSET] -> DE = corrected address; -------
; HL (the text cursor) PRESERVED, unlike ary_apply_offset above (whose
; caller already parked its cursor in IX before calling, so HL was free to
; clobber — ex_let_arr_str's str_eval return contract leaves the cursor IN
; HL instead, so this variant guards it exactly like ary_snapshot_offset
; does on the way in).
; in:  HL = cursor (live), stack top (below this call's own return address)
;      = [OFFSET].
; out: HL = cursor, UNCHANGED. DE = ARYTAB_now - OFFSET = the corrected
;      element address. [OFFSET] popped. Clobbers BC only.
ary_apply_offset_hl_sub:
                pop     bc              ; BC = our own return address
                ex      (sp),hl         ; TOS(OFFSET)<->HL(cursor): HL=OFFSET,
                                        ; TOS=cursor (stashed)
                push    bc              ; return address on top of the stash
                push    hl              ; stash OFFSET too (need HL free below)
                ld      hl,(ARYTAB)     ; HL = ARYTAB_now
                pop     bc              ; BC = OFFSET restored
                or      a
                sbc     hl,bc           ; HL = ARYTAB_now - OFFSET = corrected
                ex      de,hl           ; DE = corrected (output); HL = don't-care
                pop     bc              ; BC = our own return address
                pop     hl              ; HL = cursor restored
                push    bc              ; return address back on top
                ret

; --- ela_err/ela_abort_tm/ela_abort_fp: ex_let_arr's error tails ------------
; (basic/arrays.asm), RELOCATED here by the §13a space fix (the low region's
; 3 B headroom had no room even for the two `jr`->`jp` conversions this
; relocation itself forces, let alone the routines above — moving these
; three small tails out is what pays for it, arrays.asm's own header
; explains the net-negative low-region delta). Bodies are BYTE-IDENTICAL to
; the pre-fix ones: each still discards exactly the two-word [TYPE],[OFFSET]
; frame ary_snapshot_offset/the TYPE push leave on the stack (the OFFSET
; word is the same SIZE as the old raw [ADDR] word, so the pop count here is
; UNCHANGED from pre-fix — only the location and the `jr`->`jp` at the call
; site changed). stmt_error/type_mismatch_error/fp_runtime_error (interp.asm)
; are page-1 resident too, so these are now a same-region tail all the way
; through.
; D-POPRAISE §7: an ALIAS, 0 B. `pop af / pop hl / jp stmt_error` is
; byte-for-byte the job ems_err_pop2 (basic/str-engine.asm) does in the low
; region, in different registers -- free to change, because the words are
; DISCARDED and stmt_error opens `xor a`, redefining both A and the flags.
; -5 B of page 1. Witnessed alone by K-EL1 (row `s.ary`, ERR 2 -> ERR 5 under a
; gb_illegal retarget): scratchpad/elaerr_knife.py.
; 🎯 THIS IS THE ONLY ZERO-COST MEMBER OF THAT GROUP, and the thing that decides
; it is not the address but the CALL SITE'S JUMP FORM. arrays.asm:849 reaches
; ela_err by `jp`, so the body may move anywhere. ee_synerr_pop and ex_let_err
; are reached by `jr`, which PINS them next to their callers: aliasing either
; costs +1 B per site and nets +1/+2 B, so the group is worth 5 B, not the 13 B
; its nominal body total suggests.
; Cross-region (page 1 -> low) exactly as elas_err below, D-XREG, gated by
; check_tenant_closure.py.
ela_err         equ     ems_err_pop2
; (`ela_abort_tm` — `pop af; pop hl; jp type_mismatch_error` — stood HERE and is
; GONE with D-PENDERR: ex_let_arr's type-fault arm and its numeric arm are the
; same arm now, so the two tails collapsed into ela_abort_fp below. -5 B, page 1.)
; D-POPRAISE: an ALIAS, 0 B. This body was `pop af / pop hl / jp
; fp_runtime_error` -- byte-for-byte the job cepb_abort_fp (basic/interp.asm)
; does, in different registers, and the register is free because the word is
; DISCARDED and fp_runtime_error writes A/DE/HL before reading anything. The
; two-word [TYPE],[OFFSET] frame this discards is a DIFFERENT MEANING from
; cepb's "our resume address plus the caller's saved key", and that is the
; point: the meanings differ, the mechanism does not, and only the mechanism is
; code. -5 B of page 1. Witnessed alone by K-PR3 (f.ary), see interp.asm.
ela_abort_fp    equ     cepb_abort_fp

; --- elas_err/elas_abort_fp: ex_let_arr_str's error tails -------------------
; (basic/arrays.asm), RELOCATED here for the identical reason (above). Each
; discards exactly ONE word ([OFFSET], same size as the pre-fix [ADDR]) —
; byte-identical bodies, only moved + the call sites' `jr`->`jp`.
; D-XREG: an ALIAS across the low <-> page-1 boundary. Byte-identical to
; ems_err_pop1 and POSITION-INDEPENDENT (tools/dupspan_indep.py), and the
; REGION question -- is this label reached from a tenant whose mapping
; switches the target page OUT? -- is answered by scratchpad/crossreg_probe.py
; and GATED by check_tenant_closure.py, whose K-XR1 knife proves it can see an
; `equ` (it resolves addresses from the sym, not from the source form).
elas_err        equ     ems_err_pop1
; D-POPRAISE: likewise, the ONE-word arm -> cee_abort_fp. -4 B of page 1.
; Witnessed alone by K-PR4 (f.arystr). Note this file now aliases BOTH of its
; string-lvalue tails away (elas_err above went to ems_err_pop1 under D-XREG);
; the pair is what made the shape visible -- a second `equ` beside a first one
; is what a repeated idiom looks like before anyone counts it.
elas_abort_fp   equ     cee_abort_fp

; --- for_get / for_set: the FOR frame's loop variable ------------------------
; D-FORVAR (docs/spec-basic-forvar.md §4.5). in: FOR_CUR[0..2] = the frame's key
; (name0, name1, resolved type), exactly as for_name (basic/program.asm) parsed
; it or as nx_have's ldir copied it back down. for_set preserves DE (the value).
;
; These were `var_get`/`var_set`, "single-letter compatibility shims" that took
; ONE upcased char in A, keyed it as (name, 0) and asked deftbl_num_type for the
; letter's DEFAULT type. D-READVAR retired READ's use of them and D-FORVAR
; retires the shim itself: the key now arrives whole, so the upcase, the
; hardcoded `ld c,0` and the DEFtbl lookup all go -- and with them
; deftbl_num_type, whose "ERR 13 on a DEFSTR letter" job moved to PARSE time,
; where row f.defstr says both references put it.
;
; The loop math itself stays plain int16 (D-D: a typed/float loop variable is
; deferred); for_set tags DE as int16 (FACTYP=2) so var_store_fac coerces the
; int value into the target's own resolved type -- which is what makes
; `FOR A#=1 TO 3` store into the double entry `PRINT A#` reads back (row f.hash),
; and `FOR A%=` into the int one `A` does not (row f.coll).
for_get:
                ld      bc,(FOR_CUR)        ; name0, name1
                ld      a,(FOR_CUR+2)       ; the resolved type -- var_find_typed keys on
                jp      var_load_fac        ; all three (FAC/FACTYP=type, DE=int16 tail)
for_set:
                ld      bc,(FOR_CUR)
                ld      a,2
                ld      (FACTYP),a          ; FOR/NEXT always hand for_set a plain int16
                                            ; value -- tag it so var_store_fac's target
                                            ; coercion widens DE via widen_int_to instead
                                            ; of misreading FAC
                ld      a,(FOR_CUR+2)
                jp      var_store_fac       ; tail call (DE preserved throughout)

; --- string-variable store (own-design; see PROVENANCE.md) -----------------
; Parallel to the numeric var_find/get/set, but over STRTAB, whose entries are
; [name0][name1][len][bytes:STRMAX]. The same 2-char key (BC) identifies a string
; variable; the `$` suffix (handled by the caller) is what selects this store
; instead of the numeric one, so `A` and `A$` are independent (as in MSX-BASIC).

; Arrays slice-4c (docs/spec-basic-arrays-slice4c-string-scalar-
; unification.md §3c): on the repack path string scalars are now ordinary
; entries in the SAME unified chain numeric scalars (4b) and arrays (1-3)
; already share — str_get_key/str_set_key become thin glue over the ARY
; tenant's scalar ops (ARY_OP 4/5, type=1), mirroring var_find_typed/
; var_alloc_or_find (above) exactly. str_find (the old STRTAB pool walk) is
; DELETED.

; --- str_get_key: BC = key -> HL = descriptor [len][ptr] ---------------------
; Read-only: op=4 (SCALAR_FIND) never inserts, so an unset variable is never
; created by a mere read (the pre-4c contract, preserved). Returns HL ->
; STR_EMPTY (a len-0 descriptor) on a miss, so the caller always has a
; printable/copyable value. Clobbers A, B, C, D, E, H, L.
str_get_key:
                ld      (ARY_KEY),bc
                ld      a,1                 ; type=1 -- the `$` unifier
                                            ; (var_str_type; A/A%/A!/A#/A$
                                            ; are five distinct entries)
                ld      (ARY_TYPE),a
                ld      a,4                 ; op = SCALAR_FIND
                ld      (ARY_OP),a
                call    ary_engine_call     ; find never errors (ARY_ERR
                                            ; always 0 for op=4)
                ld      hl,(ARY_ADDR)
                ld      a,h
                or      l
                jr      z,sgk_empty         ; ARY_ADDR=0 -> unset -> STR_EMPTY
                ld      de,3
                add     hl,de               ; HL -> descriptor (entry+3, past
                                            ; [name0][name1][type] -- ONE
                                            ; byte later than the pre-4c
                                            ; STRTAB slot+2, since a chain
                                            ; entry carries the explicit
                                            ; type byte a dedicated string
                                            ; pool omitted)
                ret
sgk_empty:
                ld      hl,STR_EMPTY        ; len-0 descriptor (uninitialised = "")
                ret
STR_EMPTY:      db      0                   ; a shared empty-string descriptor

; --- str_set_key: BC = key, DE -> source descriptor [len][ptr] ---------------
; Store: op=5 (SCALAR_ALLOC, find-or-insert) resolves/creates the dest entry,
; then the unchanged sub-side sh_var_store (op=12) heap-allocs a fresh body
; copy and writes [len][ptr]. scv_alloc (sub/arrays.asm) already writes the
; name + zero-fills a fresh entry's value field -- the old ssk_new manual
; name-write + BUG-B len-zeroing are SUBSUMED (structural, not a special
; case any more).
;
; H1 (docs/spec-basic-arrays-slice4c-string-scalar-unification.md §6, Q1 —
; the LOAD-BEARING fix): the target alloc below can shift the array region
; (any insert) and, on a FRETOP collision, run strheap_gc (which compacts
; heap bodies). A source that is a string-ARRAY element (its descriptor
; address moves with the shift) or RVDESC (fixed address, but NOT a GC root)
; would otherwise go STALE mid-store -- silently wrong content, green-suite-
; invisible (needs a FRESH dest var + RAM near FRETOP to force the collision
; GC). Fix: snapshot the source descriptor onto the temp-descriptor stack
; BEFORE the target alloc (str_snapshot_to_temp, the SAME primitive 4a's own
; concat uses for its operands) -- a temp entry is both fixed-address (the
; shift only touches [ARYTAB,ARYEND), never the temp pool) and an enumerated
; GC root (sg_walk_temps), so it is immune to BOTH hazards uniformly
; (existing string-scalar / temp-stack sources were already safe; this
; extends the same safety to array-element and RVDESC sources). Released
; (TEMPTOP restored) after the store on every exit path -- exact-restore
; (not a blind +3) so it stays correct even if the snapshot itself overflowed
; the temp stack (TEMPTOP then untouched by str_snapshot_to_temp; FPERR is
; already set either way, deferred-error discipline). Clobbers A, B, C, D,
; E, H, L; also leaves (STRPTR) dangling at the released temp slot (no caller
; reads STRPTR after a store -- verified across every str_set_key call site).
str_set_key:
                ld      hl,(TEMPTOP)
                push    hl                  ; [SAVED_TEMPTOP] -- exact restore
                                            ; point, correct whether or not
                                            ; the snapshot below actually
                                            ; pushes a slot
                push    bc                  ; [KEY] guard the destination key
                                            ; across the snapshot (CALSLT
                                            ; clobbers everything)
                ld      (STRPTR),de         ; STRPTR := source descriptor addr
    IF CLEARPOOL
                call    str_snapshot_keep   ; D-CLP: as below, EXCEPT that a
                                            ; source that is already a temp is
                                            ; returned as-is -- it was never
                                            ; exposed to either hazard (fixed
                                            ; address, GC root), and with a
                                            ; CLEAR-sized pool the redundant
                                            ; copy is a second full charge
    ELSE
                call    str_snapshot_to_temp ; HL = temp desc (fixed addr, GC
                                            ; root) / STR_EMPTY on overflow --
                                            ; FPERR already set either way
    ENDIF
                ld      (SH_SRC),hl         ; stash now -- a plain RAM cell,
                                            ; survives the target alloc below
                                            ; untouched (no CPU-stack relay
                                            ; needed for it)
                pop     bc                  ; [KEY] restored
                ld      (ARY_KEY),bc
                ld      a,1                 ; type=1 -- the `$` unifier
                ld      (ARY_TYPE),a
                ld      a,5                 ; op = SCALAR_ALLOC (find-or-
                                            ; insert-and-shift)
                ld      (ARY_OP),a
                call    ary_engine_call     ; Z: ARY_ADDR=entry (found or
                                            ; newly inserted) / NZ: FPERR
                                            ; already mapped+set (OOM)
                jr      nz,ssk_target_oom
                ld      hl,(ARY_ADDR)
                inc     hl
                inc     hl
                inc     hl                  ; HL -> dest descriptor (entry+3)
                ld      (SH_DEST),hl
                ld      a,12
                ld      (SH_OP),a           ; op = 12 (VAR_STORE) -- unchanged
                                            ; sub-side body copy
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_STRHEAP
                call    sc_call             ; D-SCCALL: tenant call + absent raise
                pop     hl                  ; [SAVED_TEMPTOP]
                ld      (TEMPTOP),hl        ; release the H1 snapshot
                ld      a,(SH_ERR)
                or      a
                ret     z
                jp      str_heap_oom_error
ssk_target_oom:
                pop     hl                  ; [SAVED_TEMPTOP]
                ld      (TEMPTOP),hl        ; release the H1 snapshot (the
                                            ; target alloc failed before ANY
                                            ; store happened, but the
                                            ; snapshot push above still ran)
                ret                         ; FPERR already mapped+set (OOM)


; --- clear_vars: empty the numeric AND string tables (called at INIT / RUN) --
; Zero name0 of every slot (a 0 name0 = empty). Clearing the whole numeric
; region keeps it tidy; for strings, zeroing each entry's name0 marks it free.
; Clobbers A, BC, HL.
clear_vars:
                ; Direct-mode control flow (docs/spec-basic-direct-ctrl.md §4,
                ; D-DIR-2): empty the FOR and GOSUB frame stacks. This MOVED here
                ; from run_prog, which was the only place that ever set them --
                ; so before the first RUN both pointers held power-on RAM garbage
                ; ($FFFF under openMSX, above both *_STK_END), and the very first
                ; direct-mode FOR or GOSUB took the depth-overflow arm and raised
                ; ERR 7 "out of memory". clear_vars has EXACTLY the four call
                ; sites the reset belongs at -- cold boot (interp.asm init), RUN,
                ; NEW and CLEAR -- and the VG-8020 resets on all four (measured:
                ; a live direct-mode FOR frame does NOT survive NEW or CLEAR, but
                ; DOES survive the end of the typed line that made it). Same
                ; "single hook covering all four" argument as the RND seed below.
                ; D-CTLPOOL: one call empties the whole pool AND re-derives its
                ; top from `strheap_varceil()` -- the address §14 measured the
                ; reference publishing as STKTOP. 🎯 THIS IS WHY DEPTH RESPONDS TO
                ; `CLEAR` AT ALL: ex_clear stores POOLSIZE and HIMEM BEFORE falling
                ; into clr_done, so the reset below picks up the new ceiling for
                ; free, and `CLEAR n` / `CLEAR n,addr` move the reachable depth the
                ; way both references do (spec-basic-trapsvc.md §11).
                call    ctl_reset
                ; --- D-CLRTRAP: and the EVENT TRAPS, for the same reason -------
                ; Measured on a VG-8020 (scratchpad/clrarm_probe.py): an
                ; `ON INTERVAL` trap that is ARMED AND LIVE fires 16 times in the
                ; window before a `CLEAR` and **0** in the window after it, against
                ; a no-CLEAR control that fires 16 and 16. zerobas fired 16 and 17
                ; -- `CLEAR` did not touch the trap block at all.
                ; 🎯 AND THIS CLOSES THE FILED TRAPSTK DEFECT WITH IT
                ; (docs/spec-basic-trapsvc.md §7): `clear_vars` reset GSP to the
                ; base WITHOUT resetting TRAPSTK, so an unrelated later
                ; GOSUB/RETURN landed on a stale record's saved gsp and re-enabled
                ; a trap the program had killed -- 17 fires against the
                ; reference's 1. Both rows are the same missing reset.
                ; ⚠️ clear_vars has EXACTLY FOUR call sites -- cold boot, RUN, NEW
                ; and CLEAR -- and trap_init already runs on the first two, so this
                ; adds NEW and CLEAR and is idempotent on the others. That is the
                ; same "single hook covering all four" argument the GOSUB/FOR reset
                ; above and the RND seed below already rest on.
                call    trap_init
                ld      hl,DEFTBL           ; F3 S3b: reset every letter's default type
                ld      b,26                ; to DOUBLE (8) -- DEFINT/SNG/DBL/STR are
                ld      a,8                 ; re-established by re-running their statements
cv_deftbl:                                  ; (RUN clears here first, then the program's
                ld      (hl),a              ;  DEF lines run); consulted by var_name_key /
                inc     hl                  ;  var_str_type at every variable reference
                djnz    cv_deftbl
                ld      hl,RND_S0_PACKED    ; math pack slice 2e (docs/spec-basic-
                ld      de,RND_SEED         ; mathpack-slice2.md §15.3): reset the
                ld      bc,7                ; RND generator's persistent 14-digit
                ldir                        ; state to S0 on every NEW/CLEAR/RUN +
                                            ; cold boot -- this clear_vars call IS
                                            ; the single hook that covers all four
                                            ; (§15.1's reference-identical reset).
                ; Arrays slice-4a (docs/spec-basic-arrays-slice4a-string-
                ; heap.md §2/§6): reset the string heap + temp-descriptor
                ; stack to empty. The reset body lives in the low region
                ; (basic/str-engine.asm heap_reset) — reached by an in-slot
                ; call (page 1 <-> low region are the main ROM's co-mapped
                ; slot-0 pages) — because page 1 is byte-full. clear_vars IS
                ; the single init/CLEAR/RUN hook that runs BEFORE PRGEND is
                ; necessarily established (see the vars_reset-NOT-called-here
                ; note just below) — arrays slice-4c (§3d/H3) ALSO calls
                ; heap_reset from vars_reset itself (basic/arrays.asm), so a
                ; bare relink (store_line edit / CLOAD, which does NOT run
                ; clear_vars) gets its own heap reset too, now that string
                ; SCALARS are chain-resident and relink's vars_reset already
                ; wipes their descriptors (pre-4c this call site alone was
                ; sufficient, since STRTAB heap bodies had to survive a bare
                ; relink; that is no longer true post-4c).
                call    heap_reset
                ; Error-handling S2a: ERRFLG/ERRLIN are NOT reset here. Empirically
                ; (adversarial verify pass, 2026-07-18) the reference PRESERVES ERR/ERL
                ; across NEW/CLEAR/RUN -- they hold the last raised error's code/line
                ; until the NEXT error, and are zeroed ONLY at cold boot. clear_vars
                ; runs on all four hooks (INIT/NEW/CLEAR/RUN), so the zero lives in
                ; `init` alone (interp.asm), not here. (The signed-off packet §4 claimed
                ; clear_vars-wide zeroing "matched reference"; that claim was false --
                ; see docs/spec-basic-error-handling-s2a-packet.md §4 correction.)
                ; arrays slice-4b (§3b) + §13a-F1 fix: DO NOT call vars_reset
                ; here. vars_reset reads (PRGEND) and WRITES the $0000 array
                ; sentinel THROUGH (ARYTAB)=(PRGEND)+2. At cold INIT
                ; (interp.asm) clear_vars runs BEFORE new_prog sets PRGEND, so
                ; PRGEND still holds power-on RAM garbage -> a wild write (Fable
                ; F1, empirically zeroed HIMEM; green-suite-invisible because
                ; openMSX zero-fills RAM so the write lands in ROM). INVARIANT:
                ; every clear_vars caller resets the scalar+array regions ITSELF
                ; AFTER establishing PRGEND -- init -> new_prog (jp vars_reset),
                ; NEW -> jp new_prog, run_prog / ex_clear -> explicit vars_reset.
                ; So the numeric scalar region no longer needs a fixed-pool wipe
                ; here.
                ; Arrays slice-4c (§3d): string scalars are chain-resident
                ; now, cleared by vars_reset (which every clear_vars CALLER
                ; invokes itself, AFTER establishing PRGEND -- the §13a-F1
                ; invariant documented above). The STRTAB pool this loop
                ; used to wipe no longer exists -- nothing to do here.
                jp      fld_init            ; also reset the random-access field table

; --- RND_S0_PACKED: math pack slice 2e (repack build only, docs/spec-basic- -
; mathpack-slice2.md §15.1/§15.3). S0's 7-byte packed-BCD encoding (2
; digits/byte, MSD-first -- same nibble convention as arga_pack_fac's own
; FAC-mantissa packing) of S0=40649651372358, the RND generator's power-on/
; reset seed (black-box recovered from the VG-8020, §15.1). Pure data, used
; ONLY by clear_vars above (via `ld hl,RND_S0_PACKED`) -- not reached by
; fallthrough, since clear_vars's own tail `jp fld_init` ends the routine
; before this point.
RND_S0_PACKED:  db      $40,$64,$96,$51,$37,$23,$58
