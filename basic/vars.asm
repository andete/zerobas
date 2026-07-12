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
; slice). `A`, `A%`, `A!`, `A#` are up to 4 distinct entries. The numeric pool
; stays the SAME 128-byte span $E1C0..$E240 (VARTAB/VAREND, sysvars.inc,
; unchanged), now packed with VARIABLE-WIDTH entries
; [name0:1][name1:1][type:1][value: 2/4/8] instead of a fixed 4-byte stride —
; see var_find_typed/var_load_fac/var_store_fac below. `var_find`/
; `var_get_key`/`var_set_key` (this section, unmodified) remain the LEAN
; build's int-only implementation; every new typed routine is gated
; `IF ROM_BASE < $4000` so the lean 16 KB basic.rom stays byte-identical.

; --- is_ident_cont: CF set if A is an identifier continuation char ----------
; (a letter 'A'..'Z'/'a'..'z' or a digit '0'..'9'). A preserved.
is_ident_cont:
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
; In the crunched stream a name's letters are already upcased and its digits are
; kept verbatim (see the tokeniser's identifier path), so this walks plain ASCII.
var_name_key:
                ld      a,(hl)
                call    upcase
                ld      b,a                 ; name0
                inc     hl
                ld      c,0                 ; name1 default (single-char name)
                ld      a,(hl)
                call    is_ident_cont
                jr      nc,vnk_suffix       ; only one char
                call    is_letter
                jr      nc,vnk_dig2
                call    upcase
vnk_set2:
                ld      c,a                 ; name1
                inc     hl
vnk_more:
                ld      a,(hl)              ; consume (ignore) any 3rd+ chars
                call    is_ident_cont
                jr      nc,vnk_suffix
                inc     hl
                jr      vnk_more
vnk_dig2:
                ld      a,(hl)              ; digit second char, verbatim
                jr      vnk_set2
    IF ROM_BASE < $4000
; F3 S3a: the suffix now additionally RESOLVES the variable's type into
; (VARTYPE), sysvars.inc — replacing the lean build's "consume and ignore"
; vnk_suffix below. Consuming behaviour (which chars advance HL) is UNCHANGED:
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
                ld      a,8                 ; VARTYPE is unused by the string store (the
                ld      (VARTYPE),a         ; `$` path never reads it) — kept defined so a
                                            ; stray read never sees garbage
vnk_eat:
                inc     hl
                ret
    ELSE
vnk_suffix:
                ld      a,(hl)              ; optional type suffix, consumed/ignored
                cp      '%'
                jr      z,vnk_eat
                cp      '!'
                jr      z,vnk_eat
                cp      '#'
                jr      z,vnk_eat
                cp      '$'
                ret     nz
vnk_eat:
                inc     hl
                ret
    ENDIF

; --- var_str_type: does the name at (HL) carry a `$` suffix? -----------------
; in:  HL = cursor at the first name char (a letter). HL is NOT advanced.
; out: A = 1 if the name is a string variable, else 0. CF = the A==1 condition
;      is also reflected (set iff string). Clobbers A (repack build additionally
;      uses B/DE as scratch for the DEFtbl lookup -- no caller relies on those
;      across this call: each follows with eval() or var_name_key, which reset
;      BC/DE).
; Walks the identifier (letters/digits) to the first non-identifier char. A name
; is a string variable if it carries a `$` suffix OR (repack, S3b) it is
; unsuffixed and its first letter's DEFtbl default is DEFTBL_STR (DEFSTR). An
; explicit `% ! #` suffix is always numeric. Used by LET / PRINT / the factor
; layer to choose the string path before delegating the real advance to
; var_name_key.
var_str_type:
    IF ROM_BASE < $4000
                ld      a,(hl)              ; F3 S3b: capture name0 for the DEFtbl
                call    upcase              ; default lookup below (the walk preserves
                ld      b,a                 ; B); repack-only scratch use of B/DE
    ENDIF
                push    hl
vst_walk:
                ld      a,(hl)
                call    is_ident_cont
                jr      nc,vst_suffix
                inc     hl
                jr      vst_walk
vst_suffix:
                cp      '$'
                jr      z,vst_yes
    IF ROM_BASE < $4000
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
    ENDIF
vst_no:
                pop     hl
                xor     a                   ; not a string (A=0, CF clear)
                ret
vst_yes:
                pop     hl
                ld      a,1
                scf                          ; string (A=1, CF set)
                ret

; --- var_find: locate entry for key BC -------------------------------------
; out: CF set  -> found,     HL = entry address.
;      CF clear -> not found, HL = first free slot (or VAREND if table full).
; Clobbers A, HL (BC preserved).
var_find:
                ld      hl,VARTAB
vf_lp:
                ld      a,h                 ; reached the end of the table?
                cp      high VAREND
                jr      nz,vf_test
                ld      a,l
                cp      low VAREND
                jr      z,vf_full
vf_test:
                ld      a,(hl)              ; name0
                or      a
                jr      z,vf_free           ; empty slot -> not found
                cp      b
                jr      nz,vf_next
                inc     hl
                ld      a,(hl)              ; name1
                dec     hl
                cp      c
                jr      z,vf_hit
vf_next:
                ld      a,VARENTSZ
                add     a,l
                ld      l,a
                jr      nc,vf_lp
                inc     h
                jr      vf_lp
vf_hit:
                scf                          ; HL = entry start, CF set
                ret
vf_free:
                or      a                    ; CF clear, HL = free slot
                ret
vf_full:
                or      a                    ; CF clear, HL = VAREND (table full)
                ret

; --- var_get_key: BC = key -> DE = value (0 if unset) ----------------------
; Clobbers A, HL (BC preserved).
var_get_key:
                call    var_find
                jr      nc,vgk_zero
                inc     hl
                inc     hl                  ; HL = value field
                ld      e,(hl)
                inc     hl
                ld      d,(hl)
                ret
vgk_zero:
                ld      de,0
                ret

; --- var_set_key: BC = key, DE = value -> stored (allocates if new) ---------
; A new variable is written into the first free slot (name + value). If the
; table is full the assignment is silently dropped. Clobbers A, HL (BC, DE kept).
var_set_key:
                call    var_find
                jr      c,vsk_store         ; found existing entry
                ; not found: HL = free slot (or VAREND if full)
                ld      a,h
                cp      high VAREND
                jr      nz,vsk_new
                ld      a,l
                cp      low VAREND
                ret     z                   ; table full -> drop
vsk_new:
                ld      (hl),b              ; write the name into the free slot
                inc     hl
                ld      (hl),c
                dec     hl
vsk_store:
                inc     hl
                inc     hl                  ; HL = value field
                ld      (hl),e
                inc     hl
                ld      (hl),d
                ret

    IF ROM_BASE < $4000
; =============================================================================
; F3 S3a — typed variable store (repack build only, docs/spec-basic-float-
; core.md §11). var_find above stays the LEAN build's int-only 4-byte-stride
; walk; these are its variable-width counterparts, keyed on (name0,name1,type).
; =============================================================================

; --- var_find_typed: locate the entry for (key BC, type A) ------------------
; in:  BC = key (name0,name1), A = type (2/4/8).
; out: CF set  -> found,     HL = entry address (name0 field).
;      CF clear -> not found, HL = first free slot (bump pointer, i.e. the
;                  first name0==0 byte) or VAREND if the table is completely
;                  full. Since entries are never deleted, the free slot found
;                  here IS always the end of the list (a bump allocator).
; An entry whose name matches but whose OWN type byte differs from A is NOT a
; match (spec: `A`/`A%`/`A!`/`A#` are independent entries) — the walk skips
; past it by ITS OWN stored width and keeps looking. Clobbers A, D, H, L (BC
; preserved).
var_find_typed:
                ld      d,a                 ; D = target type
                ld      hl,VARTAB
vft_lp:
                ld      a,h
                cp      high VAREND
                jr      nz,vft_test
                ld      a,l
                cp      low VAREND
                jr      z,vft_full
vft_test:
                ld      a,(hl)              ; name0
                or      a
                jr      z,vft_free          ; empty slot -> not found
                cp      b
                jr      nz,vft_skip
                inc     hl
                ld      a,(hl)              ; name1
                dec     hl
                cp      c
                jr      nz,vft_skip
                push    hl
                inc     hl
                inc     hl
                ld      a,(hl)              ; this entry's type
                pop     hl
                cp      d
                jr      z,vft_hit
vft_skip:
                ; advance by THIS entry's own stride (3 header bytes + its value
                ; width, which is exactly its type value: 2/4/8 -> 5/7/11 total)
                push    hl
                inc     hl
                inc     hl
                ld      a,(hl)              ; type byte (stride source)
                pop     hl
                add     a,3                 ; A = total entry width
                add     a,l
                ld      l,a
                jr      nc,vft_lp
                inc     h
                jr      vft_lp
vft_hit:
                scf
                ret
vft_free:
                or      a
                ret
vft_full:
                or      a
                ret

; --- var_alloc_or_find: BC=key, A=type -> HL = entry base, CF set ------------
; (name0/name1/type already written if this call just allocated the entry; a
; freshly allocated entry's VALUE bytes are zero-filled too, so an unset
; variable always reads back as 0). CF clear = the pool has no room left for a
; new entry of this width; HL is then meaningless and nothing was written.
; Shared by var_store_fac (which overwrites the value field afterward) and
; VARPTR (ev_f_varptr, expr.asm), which only needs the entry to EXIST.
; Clobbers A, B, C, D, E, H, L (BC not preserved — callers needing the key
; afterward must save it themselves).
var_alloc_or_find:
                ld      (VS_TARGET_TYPE),a  ; stash the type across var_find_typed
                call    var_find_typed      ; BC,A -> CF/HL
                ret     c                   ; already exists
                ; not found: HL = free slot (bump ptr) or VAREND (no room at all)
                ld      a,h
                cp      high VAREND
                jr      nz,vaof_check_room
                ld      a,l
                cp      low VAREND
                ret     z                   ; HL==VAREND exactly -> CF clear, no room
vaof_check_room:
                push    hl                  ; guard the free-slot address
                ld      a,(VS_TARGET_TYPE)
                add     a,3                 ; A = this entry's total stride
                ld      e,a
                ld      d,0
                add     hl,de               ; HL = free + stride (one past the new entry)
                ld      de,VAREND
                or      a
                sbc     hl,de               ; HL = (free+stride) - VAREND
                jr      c,vaof_room_ok       ; borrow -> fits with room to spare
                ld      a,h
                or      l
                jr      z,vaof_room_ok       ; exact zero -> fits exactly up to VAREND
                pop     hl                  ; doesn't fit -> balance the stack, drop
                or      a                   ; CF clear
                ret
vaof_room_ok:
                pop     hl                  ; HL = free slot address (restored)
                ld      (hl),b              ; name0
                inc     hl
                ld      (hl),c              ; name1
                inc     hl
                ld      a,(VS_TARGET_TYPE)
                ld      (hl),a              ; type
                inc     hl                  ; HL -> value field
                ld      b,a                 ; B = value width (2/4/8) -- zero_fill counts
                                            ; in B via djnz (float-arith.asm), NOT C; a
                                            ; B=0 here would zero 256 bytes and plough
                                            ; through STRTAB ($E240), wiping string vars
                push    hl
                call    zero_fill           ; auto-init a fresh entry's value to 0
                                            ; (float-arith.asm; matches the pre-F3
                                            ; var_set_key "new" path's explicit zero
                                            ; write, which VARPTR relies on)
                pop     hl
                dec     hl
                dec     hl
                dec     hl                  ; HL back to entry base (name0) — same
                                            ; "HL=entry base" contract as the found path
                scf
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
                jr      z,vlf_unset_int
                xor     a
                ld      (FAC),a             ; lead byte 0 -> float zero
                ld      de,0
                ret
vlf_unset_int:
                ld      de,0
                ret
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
                ld      hl,ARGA
                call    widen_rhs_operand   ; exact widen of the live RHS (int/single/
                                            ; double) into a 14-digit ARGA (float-
                                            ; arith.asm)
                call    round_and_finalize  ; no-op round (guard digit is 0) + pack as
                                            ; double + FACTYP=8 + DE
                jr      vsf_coerced
vsf_single:
                ld      hl,ARGA
                call    widen_rhs_operand
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
                jr      z,vsf_wb_int
                ld      c,a                 ; C = byte count (4 single / 8 double)
                ld      b,0
                push    hl
                pop     de
                ld      hl,FAC
                ldir                        ; FAC -> value field, verbatim (same [lead+
                                            ; mantissa] bytes flt_out/var_load_fac read)
                ret
vsf_wb_int:
                ld      de,(VS_INT_VAL)     ; the coerced value (DE was clobbered above)
                ld      (hl),e
                inc     hl
                ld      (hl),d
                ret

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
    ENDIF

; --- var_get / var_set: single-letter compatibility shims ------------------
; A = name (one char). Map to key (upcased name, 0) — identical to the key a
; 1-char name produces via var_name_key, so single-letter variables set here are
; fully interoperable with multi-character ones. Used by FOR/NEXT and READ, whose
; loop/target variables are single-letter. var_set preserves DE (the value).
;
; F3 S3a/S3b (repack build): both shims route through the typed store at the
; letter's RESOLVED default type -- S3a hardcoded double; S3b resolves it via
; deftbl_lookup so DEFINT/SNG/DBL/STR reach FOR/NEXT and READ too. This is
; load-bearing: every unsuffixed REFERENCE resolves through the DEFtbl, and
; var_find_typed keys on (name,type), so a loop/READ variable stored under a
; DIFFERENT type than its references resolve to would read back as an unset 0
; (the S3b regression the shims must match). The loop math itself stays plain
; int16 (D-D: a typed/float loop variable is deferred); var_set tags DE as int16
; (FACTYP=2) so var_store_fac coerces the int value into the resolved type.
var_get:
                call    upcase
                ld      b,a
                ld      c,0
    IF ROM_BASE < $4000
                call    deftbl_lookup       ; A = the letter's resolved default type
                jp      var_load_fac        ; FAC/FACTYP=type, DE=int16 fast path (tail)
    ELSE
                jp      var_get_key
    ENDIF
var_set:
                call    upcase
                ld      b,a
                ld      c,0
    IF ROM_BASE < $4000
                ld      a,2
                ld      (FACTYP),a          ; FOR/NEXT & READ always hand var_set a plain
                                            ; int16 value (D-D: the loop math itself stays
                                            ; int16 in F3) -- tag it so var_store_fac's
                                            ; target coercion widens DE via widen_int_to
                                            ; instead of misreading FAC
                call    deftbl_lookup       ; A = the letter's resolved default type
                jp      var_store_fac       ; tail call (DE preserved across the lookup)
    ELSE
                jp      var_set_key
    ENDIF

; --- string-variable store (own-design; see PROVENANCE.md) -----------------
; Parallel to the numeric var_find/get/set, but over STRTAB, whose entries are
; [name0][name1][len][bytes:STRMAX]. The same 2-char key (BC) identifies a string
; variable; the `$` suffix (handled by the caller) is what selects this store
; instead of the numeric one, so `A` and `A$` are independent (as in MSX-BASIC).

; --- str_find: locate the string entry for key BC --------------------------
; out: CF set  -> found,     HL = entry address (name0 field).
;      CF clear -> not found, HL = first free slot (or STREND if full).
; Clobbers A, DE, HL (BC preserved).
str_find:
                ld      hl,STRTAB
sf_lp:
                ld      a,h                 ; end of the string table?
                cp      high STREND
                jr      nz,sf_test
                ld      a,l
                cp      low STREND
                jr      z,sf_full
sf_test:
                ld      a,(hl)              ; name0
                or      a
                jr      z,sf_free           ; empty slot -> not found
                cp      b
                jr      nz,sf_next
                inc     hl
                ld      a,(hl)              ; name1
                dec     hl
                cp      c
                jr      z,sf_hit
sf_next:
                ld      de,STRENTSZ
                add     hl,de
                jr      sf_lp
sf_hit:
                scf
                ret
sf_free:
                or      a
                ret
sf_full:
                or      a
                ret

; --- str_get_key: BC = key -> HL = descriptor [len][bytes...] ----------------
; Returns HL pointing at the entry's len byte (a valid [len][bytes] descriptor).
; If the variable is unset, returns HL -> STR_EMPTY (a len-0 descriptor), so the
; caller always has a printable/copyable value. Clobbers A, DE, HL (BC kept).
str_get_key:
                call    str_find
                jr      nc,sgk_empty
                inc     hl
                inc     hl                  ; HL -> len field (+2) = descriptor
                ret
sgk_empty:
                ld      hl,STR_EMPTY        ; len-0 descriptor (uninitialised = "")
                ret
STR_EMPTY:      db      0                   ; a shared empty-string descriptor

; --- str_set_key: BC = key, DE -> source descriptor [len][bytes...] ----------
; Copy the source string (len-prefixed at DE) into the key's slot, allocating a
; new slot if needed. Length is clamped to STRMAX (own-design truncation; no
; heap growth). If the table is full the assignment is silently dropped.
; Clobbers A, DE, HL (BC kept). DE may point into STRTAB itself (var-to-var copy
; A$=B$); the copy is forward and the destination is a different slot, so a plain
; LDIR is safe (a self-copy A$=A$ writes identical bytes).
str_set_key:
                push    de                  ; str_find clobbers DE — guard the source ptr
                call    str_find
                pop     de                  ; DE = source descriptor (restored)
                jr      c,ssk_store         ; existing slot
                ld      a,h                 ; not found: free slot or full?
                cp      high STREND
                jr      nz,ssk_new
                ld      a,l
                cp      low STREND
                ret     z                   ; table full -> drop
ssk_new:
                ld      (hl),b              ; write the name into the free slot
                inc     hl
                ld      (hl),c
                dec     hl
ssk_store:
                ; HL = entry name0 field; DE = source descriptor. LDIR copies
                ; (HL)->(DE), so the COPY needs HL=source, DE=dest: we read the
                ; length here, then swap the roles before the LDIR.
                inc     hl
                inc     hl                  ; HL -> dest len field
                ld      a,(de)              ; source length (DE = source descriptor)
                cp      STRMAX+1
                jr      c,ssk_len_ok
                ld      a,STRMAX            ; clamp to STRMAX
ssk_len_ok:
                ld      (hl),a              ; store the (clamped) length at the dest
                inc     hl                  ; HL -> dest bytes
                inc     de                  ; DE -> source bytes
                or      a
                ret     z                   ; zero-length -> done
                ld      c,a
                ld      b,0                 ; BC = byte count
                ex      de,hl               ; LDIR copies (HL)->(DE): HL=source, DE=dest
                ldir
                ret

; --- clear_vars: empty the numeric AND string tables (called at INIT / RUN) --
; Zero name0 of every slot (a 0 name0 = empty). Clearing the whole numeric
; region keeps it tidy; for strings, zeroing each entry's name0 marks it free.
; Clobbers A, BC, HL.
clear_vars:
    IF ROM_BASE < $4000
                ld      hl,DEFTBL           ; F3 S3b: reset every letter's default type
                ld      b,26                ; to DOUBLE (8) -- DEFINT/SNG/DBL/STR are
                ld      a,8                 ; re-established by re-running their statements
cv_deftbl:                                  ; (RUN clears here first, then the program's
                ld      (hl),a              ;  DEF lines run); consulted by var_name_key /
                inc     hl                  ;  var_str_type at every variable reference
                djnz    cv_deftbl
    ENDIF
                ld      hl,VARTAB
                ld      bc,VARSLOTS*VARENTSZ
cv_loop:
                ld      (hl),0
                inc     hl
                dec     bc
                ld      a,b
                or      c
                jr      nz,cv_loop
                ; clear the string store: name0 = 0 in every slot
                ld      hl,STRTAB
                ld      b,STRSLOTS
cv_str:
                ld      (hl),0              ; name0 = free
                ld      de,STRENTSZ
                add     hl,de
                djnz    cv_str
                jp      fld_init            ; also reset the random-access field table
