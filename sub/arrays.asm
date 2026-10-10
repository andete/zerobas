; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; sub/arrays.asm — BASIC numeric + string arrays engine (slice-1 SPLIT
; design, the sub-ROM page-0 tenant half; slice-3 extends it to string
; elements, docs/spec-basic-arrays-slice3-strings.md §4/§5.1). docs/spec-
; basic-arrays.md §10 (the split contract): the array *semantics* (auto-dim
; to 10, base 0, subscript range/error dispositions) are oracle-locked to the
; public MSX-BASIC language reference + the VG-8020 black-box capture (spec
; §4.1/§5), carried over unchanged from the monolithic WIP (branch arrays-
; slice1-wip, basic/arrays.asm) — this is a RE-HOME + ABI-WIRE, not a rewrite
; of the algorithm. The array descriptor byte layout is zerobas's OWN design
; (spec §9.2/§10.3), exactly as VARTAB/STRTAB already are — never ROM
; disassembly.
;
; --- own-design descriptor (unchanged from the WIP, spec §9.2) -------------
;   +0  name0  : 1    upcased first char (0 = the terminator sentinel)
;   +1  name1  : 1
;   +2  type   : 1    2/4/8 (int/single/double) or 1 (string, slice-3), from
;                     suffix/DEFtbl
;   +3  ndim   : 1    dimension count (>=1; no cap -- D-ARR-C)
;   +4  stride : 2    CACHED total descriptor size in bytes (6+2*ndim+elsize*
;                     count) -- own-design redundancy, see the WIP's own
;                     header for the rationale (ary_find's skip-walk reads
;                     this instead of re-deriving it each step).
;   +6  bound0 : 2    inclusive upper subscript of dim 0 (LE)  ] ndim of these
;       ...             ...
;       element data : elsize*Pi(boundK+1) bytes, zero-filled on alloc
; elsize = elsize_from_type(type) (below): type/2/4/8 for numeric (unchanged
; identity elsize=type), but 1+STRMAX for a string (type=1, slice-3 §4 -- an
; inline [len][bytes:STRMAX] value, byte-identical to a STRTAB slot's value
; portion, NOT 1 byte). Element order is column-major (first subscript varies
; fastest): off(i0,i1,..) = i0 + (b0+1)*(i1 + (b1+1)*(i2 + ...)), elem_addr =
; data_start + off*elsize.
;
; --- allocator: ARYBASE derived, NO stored ARYEND (WIP deviation, retained) -
; ARYBASE is DERIVED (never stored) as (PRGEND)+2 -- the first byte after the
; stored program's own $0000 terminator (PRGEND, basic/sysvars.inc, is a live
; main-ROM sysvar, read directly here: pure RAM, no main-ROM CALL). "ARYEND"
; is a 2-byte $0000 SENTINEL at the tail of the packed descriptor list -- the
; same "name0==0 marks the end" convention var_find_typed/str_find (vars.asm)
; use for their own fixed pools. basic/arrays.asm's ary_reset (main-ROM side,
; unchanged from the WIP) rewrites that sentinel at the current PRGEND+2
; whenever the program area is rebased.
;
; --- WHY THIS IS A SUB-ROM TENANT (spec §10, SIGNED OFF 2026-07-15) --------
; The monolithic engine overran the repack ROM by ~284 B. This is the fix:
; the resolver/allocator leaf is a PURE-RAM operation (array-area walk,
; offset arithmetic, alloc, bound checks) that needs NEITHER main's `eval`
; (page-0 low region, switched OUT while this page-0 tenant runs) NOR main's
; page-1 body -- so it moves whole into the sub-ROM as page-0 tenant index
; SUBROM_IDX_ARY (sub/equates.inc), dispatched via the standard subrom_call
; ABI (IX=SUBROM_ENTRY_BASE_P0+3*index; args/results marshalled in the
; ARY_* param block, basic/sysvars.inc §10.2; under DI; CALSLT clobbers all
; registers). basic/arrays.asm (main-ROM side) keeps only the parts that
; MUST see main's eval/var machinery: parsing bound/subscript lists (calls
; `eval`+`fac_to_int_strict`) and the FAC<->element copy/coercion (calls
; var_store_fac's own value-field codec). This file calls NOTHING resident
; in the main ROM -- every callee below is co-resident in this same
; assembly unit (verified by tools/check_tenant_closure.py's absence of any
; basic/*.asm symbol reference here, and by inspection: no `call`/`jp` target
; below resolves outside this file).
;
; --- RAM: the param block is the ONLY RAM this file touches (besides -------
; PRGEND/HIMEM, both read-only here, and ARYTAB -- arrays slice-4b, read
; AND written here: the one live pointer the scalar insert-and-shift
; maintains) -- basic/sysvars.inc's ARY_OP..ARY_ERR
; span ($E028-$E037, aliased onto tokeniser/CLOAD/store_line scratch that is
; provably dead whenever an array reference can execute, spec §10.2/the WIP's
; own aliasing analysis, carried over unchanged). That span has NO slack left
; for internal bookkeeping (unlike the WIP's ARY_SCR, which aliased 7-8
; further bytes of the SAME then-larger span) -- CURLINE sits immediately
; above it, live during almost all statement execution, so this file cannot
; claim so much as one more RAM byte. ary_alloc/ary_resolve's own transient
; bookkeeping (previously ARY_SCR) is therefore carried on the HARDWARE STACK
; instead, addressed via IY as a per-call frame pointer (DEC SP/INC SP touch
; no register or flag other than SP, so reservation/deallocation is safe
; around every call/return path; IY is otherwise unused by this file). This
; is a JUDGMENT CALL logged for the slice-1 split report: no new sysvars.inc
; RAM claim was possible, so the scratch moved from a fixed address to a
; stack frame -- same data, same lifetime, different storage.


; --- ary_engine: the tenant entry point (SUBROM_IDX_ARY, sub/equates.inc) --
; Reads ARY_OP and dispatches. op=0 (RESOLVE): read/write element address
; resolution, auto-dimensioning an undeclared array to bound 10 on first
; touch (§4.1 #1). op=1 (DIM): explicit declaration, redim-checked. op=2
; (ERASE, slice-2 -- docs/spec-basic-arrays-slice2-erase.md §4.2): free an
; existing array, reverting it to undeclared. op=3 (COPY_STR, slice-3 --
; docs/spec-basic-arrays-slice3-strings.md §5.2): a pure-RAM STRMAX-clamped
; copy from (STRPTR) into (ARY_ADDR), for the string ARRAY STORE path only --
; unlike op=0/1/2, this op does NOT consult ARY_KEY/TYPE/NIDX/IDX at all (the
; caller has already RESOLVED the destination via a prior op=0 call and
; passes it directly as ARY_ADDR; see the main-ROM glue's own header,
; basic/arrays.asm's ex_let_arr_str, for why the resolve and the copy are two
; separate tenant calls rather than one fused op). Writes ARY_ADDR (RESOLVE
; only, harmless on DIM/ERASE/COPY_STR) and ARY_ERR (0 ok; 1 Subscript-oor;
; 2 Illegal-fn/negative/not-found; 3 Redimensioned; 4 OOM -- an ALLOCATION that
; will not fit variable space; 5 Out of string space -- a string BODY that will
; not fit the `CLEAR n` pool, D-ARYOOS) either way.
; ⚠️ THIS HEADER SAID "COPY_STR always writes 0 -- it cannot fail" UNTIL
; 2026-08-20, and it had been false since slice 4a made the copy heap-allocate
; (aeng_copy_str's own header says so, 280 lines below). No gate reads prose;
; the code it described is `acs_oom`. Clobbers everything (tenant
; convention; the caller is under subrom_call/CALSLT, which already clobbers
; all registers).
ary_engine:
                ld      a,(ARY_OP)
                or      a
                jr      z,aeng_resolve
                cp      1
                jp      z,aeng_dim
                cp      2
                jp      z,aeng_erase
                cp      3
                jp      z,aeng_copy_str
                cp      4
                jp      z,aeng_scalar_find  ; arrays slice-4b (docs/spec-
                                            ; basic-arrays-slice4b-scalar-
                                            ; reloc.md §4, Q4): scalar ops
                                            ; folded into this SAME tenant
                jp      aeng_scalar_alloc   ; op==5: the only other value the
                                            ; main-ROM glue ever writes
                                            ; (ex_let_arr_str, basic/arrays.asm)
aeng_resolve:
                ld      bc,(ARY_KEY)
                ld      a,(ARY_TYPE)
                call    ary_resolve         ; -> HL=elem addr, A=err (0 ok)
                ld      (ARY_ADDR),hl
                ld      (ARY_ERR),a
                ret

; --- aeng_dim: ARY_OP=1 (explicit DIM). BC/A resolved from ARY_KEY/ARY_TYPE;
; (ARY_NIDX)/(ARY_IDXP) locate the caller-parsed bound list (§9.4). ary_find
; first: if the array already exists (a previous DIM OR an auto-dim already
; touched it) -> ARY_ERR=3 (Redimensioned array, §4.1 #4); else ary_alloc
; with the parsed bounds.
aeng_dim:
                ; negative-bound check (§4.1 #9 disposition applied to the DIM
                ; bound list): the reference raises Illegal function call for
                ; DIM A(-1) -- the same check ary_resolve's aryr_neg does per
                ; subscript. Without it, bound=-1 ($FFFF) reaches
                ; ary_count_elems as bound+1 = 0 and silently allocates an
                ; empty array (found in the 2026-07-15 adversarial
                ; differential, zb printed the follow-up instead of erroring).
                ; Runs BEFORE the ARY_KEY load: it counts the loop in B, and a
                ; check placed between ary_find and ary_alloc would clobber the
                ; key's name0 -- every DIM'd descriptor got key $0000, i.e.
                ; read back as the TERMINATOR, so lookups fell through to
                ; auto-dim (caught live, 2026-07-15: DIM A(1,1,1,1) then
                ; A(1,1,1,1)=6 -> phantom auto-dim OOM).
                ld      a,(ARY_NIDX)
                ld      b,a                 ; B = ndim (>=1: the parser aborts an
                                            ; empty list before the engine call)
                ld      ix,(ARY_IDXP)       ; D-ARR-C: the bound list is the CALLER's
                                            ; on-stack block, addressed at its HIGH
                                            ; end (bound 0) and walked DOWNWARD --
                                            ; see the file header
aeng_dim_neglp:
                ld      a,(ix+1)            ; bound_k high byte
                and     $80
                jr      nz,aeng_dim_neg
                dec     ix
                dec     ix
                djnz    aeng_dim_neglp
                ld      bc,(ARY_KEY)
                ld      a,(ARY_TYPE)
                call    ary_find            ; BC,A -> CF/HL (BC preserved, but A is
                                            ; NOT -- ary_find's own contract only
                                            ; promises to preserve BC; af_notfound's
                                            ; own `or a` leaves A=0). Re-read TYPE
                                            ; before ary_alloc below (a real bug this
                                            ; slice's own unit test caught: A=0 was
                                            ; silently mis-DIMing every array as
                                            ; elsize 0).
                jr      c,aeng_dim_redim
                ld      a,(ARY_TYPE)        ; TYPE reloaded (see above)
                ld      ix,(ARY_IDXP)       ; bounds source = the caller-parsed list
                call    ary_alloc           ; BC,A,IX -> HL=new desc+CF; else A=err(4)
                jr      nc,aeng_dim_err     ; A already holds the OOM err code (4)
                xor     a
                ld      (ARY_ERR),a         ; ok
                ret
aeng_dim_neg:
                ld      a,2                 ; Illegal function call (negative bound)
                ld      (ARY_ERR),a
                ret
aeng_dim_redim:
                ld      a,3                 ; Redimensioned array
                ld      (ARY_ERR),a
                ret
aeng_dim_err:
                ld      (ARY_ERR),a
                ret

; --- aeng_erase: ARY_OP=2 (ERASE, slice-2 -- docs/spec-basic-arrays-slice2- -
; erase.md §4.2). BC/A resolved from ARY_KEY/ARY_TYPE by the caller (main-ROM
; ex_erase). ary_find first: not found (never dimmed/auto-dimmed, already
; erased, or a type mismatch -- type is part of the key, §4.1 #7) -> ARY_ERR=2
; (Illegal function call, Tier B of the two-tier error split, §3); found ->
; compact the descriptor list by sliding every FOLLOWING descriptor (plus the
; terminator) down over the erased one, freeing exactly its own stride worth
; of space.
aeng_erase:
                ld      bc,(ARY_KEY)
                ld      a,(ARY_TYPE)
                call    ary_find            ; CF set+HL=desc base if found; CF
                                            ; clear if not (BC preserved, unused
                                            ; again here)
                jr      nc,aer_notfound
                ; found: HL = desc (= DST, the compaction target). src =
                ; desc+stride; count = ARYTOP-src, where ARYTOP = the byte
                ; past the current $0000 terminator, found by a stride-walk
                ; starting AT src (every byte before src is untouched by this
                ; erase, so there is no need to re-walk from ARYBASE) -- the
                ; same "name0==0 marks the end" convention ary_alloc's own
                ; aal_walk already uses. Nothing stores ARYEND (the file
                ; header's own design note): the terminator IS the sentinel,
                ; so the LDIR below, which moves it along with every other
                ; following descriptor, IS the entire fix-up -- no separate
                ; pointer to patch. Erasing the last (or the only) array: src
                ; lands exactly on the terminator, so the walk falls through
                ; immediately (count=2) and the LDIR just slides the 2-byte
                ; terminator itself onto desc -- which is ARYBASE when desc
                ; was the only array -- the "no arrays" state, same as
                ; ary_reset (basic/arrays.asm) writes directly.
                push    hl                  ; [DST] (= desc)
                call    ary_stride          ; HL(preserved=desc) -> DE=stride
                add     hl,de               ; HL = SRC = desc+stride
                push    hl                  ; [SRC]
aer_walk:
                ld      a,(hl)              ; name0 (0 = terminator)
                or      a
                jr      z,aer_top
                call    ary_stride          ; HL(preserved) -> DE=stride
                add     hl,de
                jr      aer_walk
aer_top:
                inc     hl
                inc     hl                  ; HL = ARYTOP (byte past the terminator)
                pop     de                  ; DE = SRC restored
                or      a
                sbc     hl,de               ; HL = ARYTOP - SRC = COUNT
                ld      b,h
                ld      c,l                 ; BC = COUNT
                ex      de,hl               ; HL = SRC (was DE); DE = COUNT
                                            ; (dead -- already latched in BC)
                pop     de                  ; DE = DST (desc) restored
                ; --- D-LRVAR: fix up FLD_TAB's ELEMENT keys before the slide ----
                ; docs/spec-basic-lrvar.md §5.4. An element's field key is its
                ; ARYTAB-relative offset (D-FLDARY §4.2), and the LDIR below moves
                ; every descriptor above the erased one DOWN by exactly `stride` --
                ; so an untouched key would name a different variable's bytes.
                ; MEASURED, CF-3300: the reference KEEPS the field alive across
                ; `ERASE` of a sibling array (probe row e.erase), so the fix is to
                ; MOVE the keys, not to drop them -- which is what D-FLDARY priced
                ; and declined for want of exactly this reading.
                push    bc                  ; [COUNT]
                push    de                  ; [DST]
                push    hl                  ; [SRC]
                call    aer_fldfix
                pop     hl
                pop     de
                pop     bc
                ldir                        ; slide [SRC..SRC+COUNT) down onto
                                            ; DST -- moves every following
                                            ; descriptor AND the terminator in
                                            ; one shot; safe (dst < src by a
                                            ; constant `stride` throughout, the
                                            ; standard ascending-LDIR
                                            ; shift-left idiom -- no byte is
                                            ; written before it has been read)
                xor     a
                ld      (ARY_ERR),a         ; 0 ok
                ret
aer_notfound:
                ld      a,2
                ld      (ARY_ERR),a         ; 2 -> IFC (ary_errmap -> FPERR=8)
                ret

; --- aer_fldfix: slide FLD_TAB's ELEMENT keys over an ERASE compaction ------
; D-LRVAR, docs/spec-basic-lrvar.md §5.4. Called from aeng_erase with the
; compaction about to happen and both of its ends still in registers.
;
; in:  HL = SRC (absolute, the first descriptor that will move DOWN)
;      DE = DST (absolute, the erased array's own descriptor = where SRC lands)
; out: every FLD_TAB entry re-keyed. Clobbers AF,BC,DE,HL,IX -- the caller has
;      SRC/DST/COUNT on the stack across the call.
;
; A FIELD entry's key is (k0,k1); a SCALAR's k0 is an upcased letter ($41..$5A)
; and an ELEMENT's is (offset>>8)|$80, where offset = elem - (ARYTAB). The two
; spaces are disjoint by construction (D-FLDARY §4.2), so `bit 7` alone says
; which entries this can possibly concern -- a name key never moves.
;
;   offset  <  DST-ARYTAB   below the erased array          -> untouched
;   offset in [DST,SRC)     INSIDE the erased array          -> free the slot
;   offset  >= SRC-ARYTAB   above it, about to slide down    -> offset -= stride
;
; 🎯 THIS COSTS 0 B OF MAIN PAGE 1, WHICH IS THE WHOLE REASON IT IS HERE. D-FLDARY
; priced the fix as a resident `fld_clear_ary` called from ex_erase -- ~20 B of
; page 1 plus 3 B of the LOW region, on the two walls that bind. But aeng_erase is
; ALREADY a page-0 tenant, it ALREADY holds both ends of the compaction, and a
; page-0 tenant reaches RAM, which is where FLD_TAB ($EE64) lives. Sited here the
; sweep spends sub page 0, which has thousands of bytes free. The expensive thing
; was never the sweep -- it was the siting.
;
; ⚠️ ARY_KEY and ARY_IDXP are borrowed as 2-byte scratch, which costs 0 RAM and is
; safe HERE and nowhere by default: they are the tenant's INPUT cells (main fills
; ARY_OP..ARY_IDXP, calls, then reads only ARY_ADDR/ARY_ERR -- basic/sysvars.inc
; §ARY block), aeng_erase consumes ARY_KEY in its own first instruction and never
; reads it again, and ARY_IDXP belongs to aeng_dim alone. Every call site writes
; both before every call, so nothing carries across.
aer_fldfix:
                or      a
                sbc     hl,de               ; HL = stride (SRC - DST)
                ld      (ARY_KEY),hl        ; scratch: STRIDE
                ld      hl,(ARYTAB)
                ex      de,hl               ; HL = DST, DE = ARYTAB
                or      a
                sbc     hl,de               ; HL = LO = DST - ARYTAB
                ld      (ARY_IDXP),hl       ; scratch: LO
                ld      ix,FLD_TAB
                ld      b,FLD_SLOTS
afx_lp:
                ld      a,(ix+0)            ; chan
                or      a
                jr      z,afx_next          ; free slot
                ld      a,(ix+1)            ; k0
                bit     7,a
                jr      z,afx_next          ; a NAME key -- never moves
                and     $7F
                ld      h,a
                ld      l,(ix+2)            ; HL = the element's ARYTAB offset
                ld      de,(ARY_IDXP)       ; DE = LO
                or      a
                sbc     hl,de               ; HL = offset - LO
                jr      c,afx_next          ; below the erased array -> untouched
                ld      de,(ARY_KEY)        ; DE = stride
                or      a
                sbc     hl,de               ; HL = offset - LO - stride
                jr      c,afx_kill          ; inside the erased array -> the variable
                                            ; it names is gone
                ld      de,(ARY_IDXP)
                add     hl,de               ; HL = the compacted offset
                ld      a,h
                or      $80                 ; back into the element half of the key
                                            ; space (the offset only ever shrinks
                                            ; here, so bit 7 is the only bit to
                                            ; restore)
                ld      (ix+1),a
                ld      (ix+2),l
                jr      afx_next
afx_kill:
                ld      (ix+0),0            ; chan = 0 -> the slot is free again,
                                            ; exactly as fld_init/fld_clear_chan
                                            ; leave one
afx_next:
                ld      de,FLD_ENTSZ
                add     ix,de
                djnz    afx_lp
                ret

; --- aeng_copy_str: ARY_OP=3 (slice-3 COPY_STR, docs/spec-basic-arrays- ----
; slice3-strings.md §5.1/§5.2; REVISED arrays slice-4a, docs/spec-basic-
; arrays-slice4a-string-heap.md §10 "String array element load/store"). dest
; = (ARY_ADDR) -- an element address the caller has ALREADY resolved via a
; prior op=0 call (now a 3-byte [len][ptr] slot, not an inline value);
; source = (STRPTR), a plain RAM sysvar visible here exactly like PRGEND/
; HIMEM (RAM pages 2/3 are always mapped to a page-0 tenant). Store =
; heap_alloc(len) + copy + write the [len][ptr] descriptor (value semantics
; preserved -- a fresh body per store, no aliasing, exactly like str_set_key,
; vars.asm), reusing heap_alloc/str_body_copy directly (co-resident in this
; page-0 image, an in-page `call`, no subrom_call round trip).
;
; UNLIKE slice-3 (a fixed-size inline copy that could never fail), this now
; CAN fail: heap_alloc may return OOM. ARY_ERR=5 on that path (D-ARYOOS -- its
; OWN code; ary_errmap maps 5 -> FPERR_STROOM -> ERR 14 "Out of string space",
; which is what both references answer). ⚠️ It was ARY_ERR=4 from slice 4a to
; 2026-08-20, sharing ary_alloc's code, and this comment used to end "so NO
; main-ROM change was needed to surface this new failure mode" -- true about
; SURFACING and false about the message: 4 maps to ERR 7 "Out of memory". The
; one-byte main-ROM change is ary_errmap's 5th entry.
; §5.2(4) GC-safety: heap_alloc(len) may itself trigger a GC; the source
; descriptor is re-read FRESH via STRPTR (a stable sysvar address, never a
; bare body pointer) only AFTER heap_alloc returns, so a mid-alloc relocation
; of the source's own body (if it is itself heap-resident, e.g. a var being
; stored into an array) is picked up correctly by str_body_copy's own re-read
; contract. Clobbers A,B,C,D,E,H,L.
aeng_copy_str:
    IF CLEARPOOL
                ; --- D-CLP: ADOPT a temp's body, exactly as sh_var_store does -
                ; The scalar store (str_set_key -> op 12) and this array-element
                ; store are the SAME operation on two different destinations, so
                ; they must charge the pool the same. `CLEAR 500 : DIM A$(2) :
                ; A$(1)=STRING$(100,"A")` reads 400 on the reference, and reading
                ; 400 while PEAKING at 200 is only invisible while the pool is
                ; huge -- which `CLEAR n` is precisely what stops being true.
                ; A temp uniquely owns its body and is discarded at the statement
                ; boundary, so take it and zero the temp's descriptor (one body,
                ; one GC root). A non-temp source still copies below.
                ld      hl,(STRPTR)
                call    sh_hl_is_temp       ; HL preserved
                jr      nc,acs_copy
                ld      de,(ARY_ADDR)       ; DE = dest element slot
                ld      bc,3
                ldir                        ; dest := [len][ptr] verbatim
                ld      hl,(STRPTR)
                ld      (hl),0              ; temp.len = 0
                inc     hl
                ld      (hl),0
                inc     hl
                ld      (hl),0              ; temp.ptr = 0 -> no longer a GC root
                xor     a
                ld      (ARY_ERR),a         ; 0 ok
                ret
acs_copy:
    ENDIF
                ld      hl,(STRPTR)         ; HL = source descriptor (stable address)
                ld      a,(hl)              ; source length (already 0..255 --
                                            ; STRMAX=255 is the length field's own
                                            ; max, no clamp arithmetic needed)
                call    heap_alloc          ; A=len -> CF+HL=new body ptr / CF clear=OOM
                jr      nc,acs_oom
                push    hl                  ; guard the new (fresh, unaliased) body ptr
                ld      hl,(STRPTR)         ; HL = source descriptor (stable; re-fetch —
                                            ; str_body_copy re-reads len+ptr fresh from
                                            ; here, §5.2(4) GC-safety)
                pop     de                  ; DE = new body ptr
                push    de                  ; re-guard it for the descriptor write below
                call    str_body_copy       ; HL(source desc), DE(dest body) -> copies
                                            ; the source's CURRENT length bytes
                ld      hl,(STRPTR)
                ld      a,(hl)              ; length (re-read once more; unchanged —
                                            ; nothing mutates the source mid-op)
                ld      hl,(ARY_ADDR)       ; HL = dest element slot
                ld      (hl),a              ; dest.len
                inc     hl
                pop     de                  ; DE = body ptr (guarded above)
                ld      (hl),e
                inc     hl
                ld      (hl),d              ; dest.ptr := the new heap body
                xor     a
                ld      (ARY_ERR),a         ; 0 ok
                ret
acs_oom:
                ld      a,5                 ; D-ARYOOS: ARY_ERR 5 = OUT OF STRING
                                            ; SPACE, a code of its OWN. This was 4 --
                                            ; "the SAME code ary_alloc's own OOM
                                            ; uses" -- and that reuse WAS the defect,
                                            ; not a saving: ary_errmap maps 4 ->
                                            ; FPERR=6 -> ERR 7 `Out of memory`, and
                                            ; both references answer `Out of string
                                            ; space` (ERR 14) for a store that could
                                            ; not get a BODY. Measured 2026-08-20,
                                            ; docs/aryoos-msx1-characterization.md:
                                            ; `CLEAR 60:DIM A$(5):B$=STRING$(25,"A")
                                            ; :A$(1)=B$:A$(2)=B$` -> `Out of string
                                            ; space in 50` on vg8020 AND cf3300.
                                            ; 🎯 4 vs 5 IS ALLOCATION vs BODY, NOT
                                            ; NUMERIC vs STRING. `DIM A$(20000)` is a
                                            ; STRING array whose 3-byte slots will
                                            ; not fit VARIABLE space, and all three
                                            ; machines call that `Out of memory` --
                                            ; row s.strdim, the denominator row. So
                                            ; ary_alloc's OOM (aal_oom, scv_oom)
                                            ; stays 4 and only THIS site moves.
                                            ; Same instruction, same byte count: the
                                            ; whole price is ary_errmap's 5th entry,
                                            ; one byte of the main ROM's low region.
                ld      (ARY_ERR),a
                ret

; =============================================================================
; Arrays slice-4b — numeric SCALAR relocation (docs/spec-basic-arrays-
; slice4b-scalar-reloc.md). Q4 (signed off): folded into THIS tenant as new
; ARY_OP codes 4 (SCALAR_FIND) / 5 (SCALAR_ALLOC), reusing the ARY_KEY/
; ARY_TYPE/ARY_ADDR/ARY_ERR fields verbatim (identical shape to RESOLVE) --
; no new param block, no new SUBROM_IDX. Scalars now live in the SAME
; contiguous region arrays do: [PRGEND+2, ARYTAB) is the scalar region,
; [ARYTAB, ARYEND) the array region, sharing the one FRETOP collision / GC-
; once-retry invariant (§2/§4). Entry format is UNCHANGED from the pre-4b
; fixed pool ([name0][name1][type][value:2/4/8], stride = type+3, key
; (name0,name1,type)) -- only the location + walk moved.
; =============================================================================

; --- aeng_scalar_find: ARY_OP=4 (find-only, no insert -- reading an unset -
; scalar must NOT create it, exactly like the pre-4b var_find_typed). Writes
; ARY_ADDR = the entry address, or 0 if not found (0 is never a valid entry
; address -- program text starts at $8001); ARY_ERR always 0 (a miss is not
; an error, it is the MSX auto-init-to-0 contract).
aeng_scalar_find:
                ld      bc,(ARY_KEY)
                ld      a,(ARY_TYPE)
                call    scv_find            ; BC,A -> CF/HL
                jr      c,asf_found
                ld      hl,0                ; not found -> ARY_ADDR=0
asf_found:
                ld      (ARY_ADDR),hl
                xor     a
                ld      (ARY_ERR),a         ; find never errors
                ret

; --- aeng_scalar_alloc: ARY_OP=5 (find-or-insert, §3a). Writes ARY_ADDR = --
; the entry address (found or freshly inserted) and ARY_ERR (0 ok / 4 Out of
; memory -- the SAME code + main-ROM ary_errmap mapping arrays' own OOM
; already uses, §7.3: this REPLACES the pre-4b fixed-pool silent-drop with a
; real surfaced error, matching the array disposition).
aeng_scalar_alloc:
                ld      bc,(ARY_KEY)
                ld      a,(ARY_TYPE)
                call    scv_alloc           ; BC,A -> CF+HL=addr / CF clear+A=err(4)
                jr      nc,asa_err
                ld      (ARY_ADDR),hl
                xor     a
                ld      (ARY_ERR),a
                ret
asa_err:
                ld      (ARY_ERR),a         ; A already = 4 (OOM)
                ret

; --- fn_shadow_find: D-DEFFN's shadow lookup, and it costs the MAIN ROM ZERO -
; BYTES. in: BC = key (name0,name1), A = type. out: CF set -> HL = the shadow
; slot, shaped exactly like a scalar entry ([name0][name1][type][value]) so every
; caller downstream is unchanged; CF clear -> not a formal, walk the real chain.
; Preserves BC and A; clobbers D, E, H, L -- scv_find's own contract exactly.
;
; 🎯 IT LIVES HERE, IN THE TENANT, BECAUSE THAT IS WHERE IT IS FREE. Sitting at
; the top of scv_find it is reached by ALL FOUR accessors at once --
; var_find_typed and var_alloc_or_find (ARY_OP 4/5) and, since slice-4c
; unified string scalars into the same chain at type=1, str_get_key and
; str_set_key too. The obvious home (a `call fn_shadow` prelude in each of the
; four, basic/vars.asm) is ~64 B of a main ROM that has 100 free; this is ~40 B
; of a sub page 0 that has 3 KB, and the CALSLT it rides on is one every scalar
; reference already pays.
;
; ⚠️ THE FAST PATH IS "NO FN CALL IN PROGRESS" AND IT IS THE FIRST TEST. FN_FEND
; holds the LOW BYTE of one-past the live frame, and equals low FN_PAREA when no
; call is running -- the area never crosses a page (sysvars.inc asserts it), so
; one byte is the whole bound and the miss costs a load, a compare and a branch.
; 🔴 A STALE FRAME WOULD BE A SILENT WRONG ANSWER, not a crash: `X` would keep
; reading a dead formal after the call. raise_error resets FN_FEND for exactly
; that reason (basic/interp.asm) -- o.errfend18 / o.errfend13 (`X` = 5 after a
; body whose fault reached raise_error with the frame still LIVE) are the rows
; that say so. 🔴 NOT o.errrestore, which this comment used to name: `X/0` is a
; DEFERRED error realized at the statement boundary, so its FN call returns
; normally and fn_leave restores the frame before raise_error ever runs. A knife
; found that (D-DEFFNKNIFE K-FE1); the row was green with the reset disabled.
fn_shadow_find:
                ld      d,a                 ; D = the type being looked up
                ld      hl,FN_PAREA
fsf_lp:
                ld      a,(FN_FEND)
                cp      l
                jr      z,fsf_miss          ; walked the whole live frame
                ld      a,(hl)              ; name0
                inc     hl
                sub     b
                ld      e,a
                ld      a,(hl)              ; name1
                inc     hl
                sub     c
                or      e
                ld      e,a
                ld      a,(hl)              ; type -- A%/A!/A#/A$/A are five
                inc     hl                  ; distinct formals, as they are five
                sub     d                   ; distinct scalars
                or      e
                jr      z,fsf_hit
                ld      a,FN_SLOTSZ-3       ; HL is at slot+3; step to the next slot
                add     a,l
                ld      l,a
                jr      fsf_lp
fsf_hit:
                dec     hl
                dec     hl
                dec     hl                  ; HL = the slot BASE (an entry address)
                ld      a,d
                scf
                ret
fsf_miss:
                ld      a,d
                or      a                   ; CF clear
                ret

; --- scv_find: BC=key(name0,name1), A=type -> CF set+HL=entry base if found;
; CF clear+HL=(ARYTAB) if not found (the insertion point -- a not-found
; result always lands exactly at the current scalar-region end, since the
; walk below never overshoots it). Preserves BC (mirrors ary_find's own
; contract -- the caller needs the key intact afterward, e.g. scv_alloc's own
; insert). Type is part of the key (A/A%/A! are distinct scalars, exactly
; like arrays' own §4.1 #7). The scalar region has NO self-describing
; terminator (Q3: bounded by the stored ARYTAB, not a $0000 sentinel like the
; array region) -- unlike ary_find's af_lp, this walk's loop test is "have we
; reached ARYTAB yet", not "is name0 0" (a scalar entry's name0 is never 0;
; entries are never deleted). Clobbers A,D,E,H,L.
scv_find:
                call    fn_shadow_find      ; D-DEFFN: a formal of the FN call in
                ret     c                   ; progress SHADOWS the variable
                ld      d,a                 ; D = target type
                ld      hl,(PRGEND)
                inc     hl
                inc     hl                  ; HL = scalar-region base
scvf_lp:
                ; end-of-region test is done BYTE-WISE against (ARYTAB), NOT
                ; via `ld de,(ARYTAB)` + a 16-bit subtract -- specifically so
                ; D (the target type, loaded once above and needed on every
                ; hit-check for the rest of the walk) is never clobbered. A
                ; real bug this slice's own unit test caught: `ld de,(ARYTAB)`
                ; silently overwrote D each iteration, so the type compare
                ; after a name match compared against ARYTAB's own high byte
                ; instead of the caller's type -- every re-find of a just-
                ; inserted entry came back "not found".
                ld      a,(ARYTAB+1)        ; ARYTAB high byte
                cp      h
                jr      nz,scvf_go
                ld      a,(ARYTAB)          ; ARYTAB low byte
                cp      l
                jr      z,scvf_notfound     ; HL == ARYTAB -> reached the end
scvf_go:
                ld      a,(hl)              ; name0
                cp      b
                jr      nz,scvf_skip
                push    hl
                inc     hl
                ld      a,(hl)              ; name1
                inc     hl
                ld      e,(hl)              ; type
                pop     hl
                cp      c
                jr      nz,scvf_skip
                ld      a,e
                cp      d
                jr      nz,scvf_skip
                scf
                ret
scvf_skip:
                ; advance by THIS entry's own stride: 3 header bytes +
                ; elsize_from_type(type) -- arrays slice-4c (§3a): routed
                ; through the SAME map ary_stride/ary_alloc already use,
                ; instead of the raw pre-4c "type+3" (identity for numeric
                ; 2/4/8, but type=1 (string) now strides 6 = 3+3, not 4).
                ; elsize_from_type preserves BC,D,E,H,L (clobbers A only) --
                ; safe to call with D still holding the caller's target type.
                push    hl
                inc     hl
                inc     hl
                ld      a,(hl)              ; type byte (stride source)
                pop     hl
                call    elsize_from_type    ; A = elsize (identity for 2/4/8;
                                            ; 3 for type=1 string)
                add     a,3                 ; A = total entry width
                add     a,l
                ld      l,a
                jr      nc,scvf_lp
                inc     h
                jr      scvf_lp
scvf_notfound:
                or      a                   ; CF clear; HL = ARYTAB
                ret

; --- scv_alloc: BC=key, A=type -> CF set+HL=entry base (found OR newly ------
; inserted) / CF clear+A=4 (Out of memory: nothing moved, nothing written --
; leaves state consistent, mirroring the pre-4b var_store_fac silent-drop
; contract, §7.3). Not found -> insert-and-shift (§3a): open a `stride`-byte
; hole at the current ARYTAB by shifting the ENTIRE array region
; [ARYTAB, ARYEND+2) up by `stride`, collision-checked BEFORE moving anything
; (GC-once-retry, the SAME invariant ary_alloc's own aal_ceil_try uses --
; string-array element descriptors move with their array block but their
; heap `ptr` values are untouched, only the descriptor relocates).
; Own scratch frame on the STACK (IY-addressed, 19 bytes -- the sub/
; arrays.asm ary_alloc / sub/strheap.asm convention, since no fixed RAM byte
; is spare here either):
;   +0 KEY_C(name1) +1 KEY_B(name0) +2 TYPE +3 STRIDE +4/5 OLDBASE(=old
;   ARYTAB) +6/7 OLDEND(=old array terminator addr) +8/9 NEWEND(=OLDEND+
;   STRIDE) +10/11 CEND(=NEWEND+2) +12 RETRIED +13/14 SRC_LAST(=OLDEND+1)
;   +15/16 DST_LAST(=SRC_LAST+STRIDE) +17/18 COUNT(=SRC_LAST-OLDBASE+1)
; Clobbers A,B,C,D,E,H,L,IX,IY.
scv_alloc:
                call    scv_find            ; BC,A -> CF/HL; BC preserved
                ret     c                   ; already exists -> done
                ; not found: HL = ARYTAB (= old scalar-region end = the
                ; insertion point). Open the frame -- dec sp/inc sp touch no
                ; register or flag other than SP, so HL survives untouched.
                ; D-INPNUM funding (2026-09-29): was 19 x `dec sp` -- HL (scv_find's
                ; result) survives through DE, which is dead here (its first use below
                ; is a write) and so are the flags (IY is set next). 7 B, not 19.
                ex      de,hl
                ld      hl,-19
                add     hl,sp
                ld      sp,hl               ; reserve a 19-byte scratch frame
                ex      de,hl
                ld      iy,0
                add     iy,sp               ; IY = frame base
                ld      (iy+4),l
                ld      (iy+5),h            ; OLDBASE = HL (from scv_find)
                ld      (iy+0),c            ; KEY name1
                ld      (iy+1),b            ; KEY name0
                ld      a,(ARY_TYPE)        ; reload (scv_find clobbers A --
                                            ; the SAME A-not-preserved trap
                                            ; aeng_dim's own comment documents)
                ld      (iy+2),a            ; TYPE
                ; arrays slice-4c (§3a): STRIDE = elsize_from_type(type)+3,
                ; NOT raw type+3 -- routes through the SAME map scv_find/
                ; ary_stride/ary_alloc already use, so a type=1 (string)
                ; scalar strides 6 (3 header + the [len][ptr] descriptor),
                ; not 4. Identity for numeric 2/4/8 (unchanged from pre-4c).
                ; Clobbers A only -- IY/the frame survive.
                call    elsize_from_type
                add     a,3
                ld      (iy+3),a            ; STRIDE = elsize_from_type(type)+3
                call    strheap_aryend      ; HL = OLDEND (current array-
                                            ; region terminator address; the
                                            ; SAME in-page call ary_alloc's
                                            ; own GC-retry already makes)
                ld      (iy+6),l
                ld      (iy+7),h            ; OLDEND
                ld      e,(iy+3)
                ld      d,0
                add     hl,de               ; HL = NEWEND = OLDEND + STRIDE
                jp      c,scv_oom           ; defensive wrap guard (mirrors
                                            ; ary_alloc's own $FFFE/$FFFF one)
                ld      (iy+8),l
                ld      (iy+9),h            ; NEWEND
                ld      de,2
                add     hl,de               ; HL = CEND = NEWEND+2 (address
                                            ; just past the shifted terminator)
                jp      c,scv_oom
                ld      (iy+10),l
                ld      (iy+11),h           ; CEND
                xor     a
                ld      (iy+12),a           ; RETRIED = 0
scv_ceil_try:
    IF CLEARPOOL
                ; D-CLP: the ceiling is the STRING POOL FLOOR, not FRETOP -- the
                ; variable/array region grows up to where `CLEAR n` put the
                ; boundary, and the pool above it is not available to it at any
                ; price. A failure here stays ERR 7 (`Out of memory`): it is
                ; variable space that ran out, not string space.
                ; ⚠️ AND THE GC RETRY BELOW IS GONE, because it is now DEAD CODE,
                ; not because it is expendable. It retried once after strheap_gc
                ; on the reasoning that FRETOP can MOVE; the floor cannot -- GC
                ; compacts string bodies upward toward the ceiling and never
                ; touches the boundary. Retrying would re-run the identical
                ; comparison and reach the identical answer. (iy+12), the RETRIED
                ; slot, is deliberately left ALLOCATED but unused: every later
                ; frame offset is absolute, and renumbering six of them to
                ; reclaim one byte of STACK is a poor trade.
                ; ⚠️ D-FCH §3.2: strheap_VARCEIL, not strheap_floor -- the
                ; file-channel table is carved between them, and an array that
                ; grew into it would be silently overwritten by the next channel
                ; switch. Same clobber set, and it touches neither IX nor IY.
                call    strheap_varceil     ; HL = the variable-region ceiling
                ; 🔴 D-SPMERGE step 6: AND RESERVE THE MACHINE STACK UNDER IT. Since
                ; the merge `SP` lives BELOW `CSP`, and `strheap_varceil` clamps to
                ; `CSP` itself -- so without this the array region grows straight
                ; through the LIVE STACK. The stack's reserve below the pool top is
                ; kept from this side, which strheap_varceil's own note calls
                ; "only one side of it".
                ; The subtraction cannot wrap: the ceiling is a RAM address
                ; >= $8000, and a zero CSP left the clamp standing down.
                ; MEASURED without it: `DIM Z(1857)` + 26 scalars read NO OUTPUT AT
                ; ALL, where a clean tree raises `Out of memory` with 27 B spare.
                ; D-DIMRESERVE S3: STK_EDGE_RESERVE (116, measured -- see
                ; basic/sysvars.inc), not the 256 B page it was; DE is loaded next.
                ld      de,-STK_EDGE_RESERVE
                add     hl,de               ; keep STK_EDGE_RESERVE below the ceiling
    ELSE
                ld      hl,(FRETOP)         ; ceiling
    ENDIF
                ld      e,(iy+10)
                ld      d,(iy+11)           ; DE = CEND
                ex      de,hl               ; HL = CEND, DE = ceiling
                or      a
                sbc     hl,de               ; HL = CEND - ceiling
                jr      c,scv_ceil_fits     ; CEND < ceiling -> fits
    IF CLEARPOOL
                jp      scv_oom
    ELSE
                ld      a,(iy+12)
                or      a
                jp      nz,scv_oom          ; already retried once -> genuine OOM
                ld      a,1
                ld      (iy+12),a
                call    strheap_gc          ; recompute FRETOP (GC never
                                            ; touches array/scalar data --
                                            ; PRESERVES IY, so our frame
                                            ; survives, exactly like
                                            ; ary_alloc's own retry)
                jr      scv_ceil_try
    ENDIF
scv_ceil_fits:
                ; SRC_LAST = OLDEND+1 ; DST_LAST = SRC_LAST+STRIDE ;
                ; COUNT = SRC_LAST-OLDBASE+1  (the block to shift is
                ; [OLDBASE, OLDEND+2), i.e. SRC_LAST is its last byte)
                ld      l,(iy+6)
                ld      h,(iy+7)            ; HL = OLDEND
                inc     hl                  ; HL = SRC_LAST
                ld      (iy+13),l
                ld      (iy+14),h
                ld      e,(iy+3)
                ld      d,0                 ; DE = STRIDE
                add     hl,de               ; HL = DST_LAST
                ld      (iy+15),l
                ld      (iy+16),h
                ld      e,(iy+4)
                ld      d,(iy+5)            ; DE = OLDBASE
                ld      l,(iy+13)
                ld      h,(iy+14)           ; HL = SRC_LAST
                or      a
                sbc     hl,de               ; HL = SRC_LAST - OLDBASE
                inc     hl                  ; HL = COUNT
                ld      (iy+17),l
                ld      (iy+18),h
                ; --- LDDR: (DE=DST_LAST) <- (HL=SRC_LAST), BC=COUNT --------
                ; top-down (descending) to handle the growing overlap: the
                ; destination is ABOVE the source throughout (dst = src +
                ; STRIDE, STRIDE > 0), the textbook "shift right" idiom -- no
                ; byte is written before it has been read (the SAME
                ; direction discipline sg_move_one's own LDDR uses).
                ld      l,(iy+13)
                ld      h,(iy+14)           ; HL = SRC_LAST
                ld      e,(iy+15)
                ld      d,(iy+16)           ; DE = DST_LAST
                ld      c,(iy+17)
                ld      b,(iy+18)           ; BC = COUNT
                lddr
                ; --- write the new scalar entry at OLDBASE (the freed hole) -
                ld      l,(iy+4)
                ld      h,(iy+5)            ; HL = OLDBASE = new entry addr
                ld      a,(iy+1)            ; name0
                ld      (hl),a
                inc     hl
                ld      a,(iy+0)            ; name1
                ld      (hl),a
                inc     hl
                ld      a,(iy+2)            ; type
                ld      (hl),a
                inc     hl                  ; HL -> value field
                ; arrays slice-4c (§3a): B = elsize_from_type(type), NOT the
                ; raw type byte -- a type=1 (string) scalar's value field is
                ; the 3-byte [len][ptr] descriptor, not 1 byte. Identity for
                ; numeric 2/4/8 (unchanged from pre-4c). elsize_from_type
                ; clobbers A only -- HL (the write cursor) survives.
                call    elsize_from_type
                ld      b,a                 ; B = value width (elsize) -- same
                                            ; "count via B" convention
                                            ; var_alloc_or_find's own pre-4b
                                            ; zero_fill call used; reimplemented
                                            ; IN-TENANT (a local loop, not a
                                            ; call) since this tenant cannot
                                            ; call resident main-ROM code
                                            ; (zero_fill lives in float-
                                            ; arith.asm) -- the SAME reasoning
                                            ; ary_alloc's own aal_zero_lp
                                            ; already documents.
scva_zero_lp:
                ld      (hl),0
                inc     hl
                djnz    scva_zero_lp
                ; --- ARYTAB += STRIDE (the scalar region has grown) --------
                ld      hl,(ARYTAB)
                ld      e,(iy+3)
                ld      d,0
                add     hl,de
                ld      (ARYTAB),hl
                ; --- return HL = new entry base, CF set ---------------------
                ld      l,(iy+4)
                ld      h,(iy+5)
                ex      de,hl               ; D-INPNUM funding: HL is the caller's
                ld      hl,19               ; result, carried in DE (dead here; the
                add     hl,sp               ; `scf` below sets the flag it returns)
                ld      sp,hl               ; deallocate the 19-byte frame -- 7 B, not 19
                ex      de,hl
                ; D-CTLPOOL: the region's end just moved -- refresh the control
                ; pool's collision floor. HL is the caller's result, so it rides
                ; the stack across the walk.
                push    hl
                call    strheap_ctllim
                pop     hl
                scf
                ret
scv_oom:
                ld      hl,19               ; D-INPNUM funding: HL is no result on
                add     hl,sp               ; this path (A=4, CF clear below), so
                ld      sp,hl               ; deallocate the 19-byte frame -- 5 B, not 19
                ld      a,4                 ; ARY_ERR: Out of memory (same
                                            ; code arrays' own OOM uses)
                or      a                   ; CF clear
                ret

; --- ARY_AUTODIM_BOUNDS: FOUR words, each = 10 (§4.1 #1). Read-only tenant ---
; data; ary_resolve's auto-dim path points IX at its LAST word (vs. aeng_dim's
; IX, which points at the caller-parsed on-stack block for an explicit DIM) --
; same ary_alloc, two different bounds sources.
; D-ARR-C: this used to be MAXDIM words and stays FOUR now that MAXDIM is gone,
; because auto-dim past four subscripts can never allocate -- 11^5 elements is
; 322102 B at the narrowest element width, so ary_resolve answers `Subscript out
; of range` before it gets here (aryr_autodim_soor). Every entry is identical, so
; the downward walk may start at any word with ndim words below it.
ARY_AUTODIM_BOUNDS:
                dw      10,10,10,10

; --- ary_mul16_checked: HL,DE (unsigned 16-bit) -> DE = HL*DE truncated ----
; to 16 bits; CF set = the true 32-bit product does not fit 16 bits (DE is
; then only the low 16 bits, not meaningful alone). Local MSB-first shift-add
; multiply -- this tenant calls NOTHING resident in the main ROM (see the
; file header), so this REPLACES the WIP's call to the resident
; mul16x16_32 (float-arith.asm) with a self-contained implementation (same
; contract, fresh body -- the WIP's own ary_mul16_checked comment already
; documented HL/DE in, DE out, CF=overflow; that contract is unchanged).
; IX is borrowed as scratch for the remaining-multiplier value (shifted via
; `add ix,ix`, a standard documented Z80 op -- ADD ix,rr sets CF from the
; bit shifted out of bit 15, exactly like ADD HL,HL) and is saved/restored
; (push/pop) so the CALLER's own IX -- e.g. ary_resolve's subscript-block
; walk pointer, still live across this call inside its loop -- survives
; unchanged, the same discipline evmc_sqr uses for the text cursor across
; subrom_call. Clobbers A,B,C,H,L (+DE, the output).
ary_mul16_checked:
                push    ix                  ; save the caller's IX
                ld      b,h
                ld      c,l                 ; BC = multiplicand (operand 1, HL)
                push    de
                pop     ix                  ; IX = multiplier (operand 2, DE),
                                            ; consumed by the left-shift below
                ld      hl,0
                ld      d,h
                ld      e,l                 ; DE:HL = 0 (32-bit acc; DE=hi, HL=lo)
                ld      a,16
amc_lp:
                add     ix,ix               ; shift the remaining multiplier left;
                                            ; CF = the bit just shifted out (MSB-first)
                jr      c,amc_bit1
                add     hl,hl               ; acc <<= 1 (bit=0: no add)
                rl      e
                rl      d
                jr      amc_next
amc_bit1:
                add     hl,hl               ; acc <<= 1
                rl      e
                rl      d
                add     hl,bc               ; acc_lo += multiplicand
                jr      nc,amc_next
                inc     de                  ; propagate the carry into acc_hi
amc_next:
                dec     a
                jr      nz,amc_lp
                ; DE:HL = the true 32-bit product (DE=high, HL=low)
                ld      a,d
                or      e                   ; A=0 iff DE(high)==0 -> no overflow;
                                            ; 'or' always clears CF too
                ex      de,hl               ; DE = low16 (the truncated result,
                                            ; returned either way); EX does not
                                            ; touch flags, so Z/CF from 'or e' survive
                pop     ix                  ; caller's IX restored (POP: no flag effect)
                ret     z                   ; no overflow: CF already clear
                scf
                ret

; --- ary_count_elems: HL=bounds ptr (LE words), B=ndim(>=1) -> DE=count ----
; (Pi(bound_k+1)). CF set = overflow (DE not meaningful; early return).
; D-ARR-C: HL addresses bound **0** at the HIGH end of the list and the walk
; runs DOWNWARD (see the file header). The product is order-independent, so
; nothing about the arithmetic changes; only the cursor step does. The WIP's
; "HL advanced past the 2*ndim bytes" postcondition is DROPPED -- ary_alloc,
; the only caller, `ex de,hl`s the count out and never reads the cursor back.
; Clobbers A,B,C,D,E,H,L.
ary_count_elems:
                ld      de,1
ace_lp:
                ld      a,b
                or      a
                ret     z                   ; done: DE=count, CF clear
                dec     b
                push    bc                  ; [ndim_remaining(B), junk(C)]
                push    hl                  ; [old bounds cursor]
                ld      c,(hl)
                inc     hl
                ld      b,(hl)              ; BC=bound_k(raw); HL=&bound_k high byte
                dec     hl
                dec     hl
                dec     hl                  ; HL=&bound_{k+1} (DOWNWARD, D-ARR-C)
                inc     bc                  ; BC=bound_k+1
                ex      (sp),hl             ; TOS<-advanced cursor; HL<-old (discard)
                ex      de,hl               ; HL=running count; DE=old cursor (discard)
                push    bc
                pop     de                  ; DE=bound_k+1
                call    ary_mul16_checked   ; HL(count)*DE(bound_k+1)->DE=count,CF=ovf
                jr      c,ace_ovf
                pop     hl                  ; advanced cursor restored
                pop     bc                  ; ndim_remaining restored
                jr      ace_lp
ace_ovf:
                pop     hl                  ; balance: discard advanced cursor
                pop     bc                  ; balance: discard ndim_remaining
                scf
                ret

; --- elsize_from_type: A=type (1/2/4/8) -> A=elsize (bytes per element) ----
; (arrays slice-3, docs/spec-basic-arrays-slice3-strings.md §4/§5.1; REVISED
; arrays slice-4a, docs/spec-basic-arrays-slice4a-string-heap.md §3). Slice-1
; baked in the identity elsize=type (2/4/8, int/single/double) -- a STRING
; element (type=1) breaks that identity. Slice-3 sized it as a full inline
; [len][bytes:STRMAX] value; slice-4a REPLACES that with a 3-byte
; [len:1][ptr:2] descriptor pointing at a body in the string heap -- the
; SAME shape as a `$`-var STRTAB slot's own tail and a temp-descriptor-stack
; entry (§3 of the spec: "a small superset of today's [len][bytes...]
; convention"). This DECOUPLES a string array's element size from STRMAX
; entirely (elsize=3 regardless of STRMAX's value) and is what shrinks a
; string array 1+STRMAX-per-element (65 B at old STRMAX=64) down to 3 B/
; element. Consulted at every site that previously read `type` directly as a
; byte count: ary_alloc's data-region sizing (+ the zero-fill it drives,
; which now zero-fills [len=0][ptr=0] elements -- an empty string per the
; len==0/ptr==0 convention, exactly matching STR_EMPTY) and ary_resolve's
; ELSIZE cache. The descriptor's OWN stored type byte is UNCHANGED (still the
; raw 1/2/4/8). Preserves BC,D,E,H,L. Clobbers A only.
elsize_from_type:
                cp      1
                ret     nz                  ; numeric (2/4/8): elsize = type,
                                            ; unchanged from slice 1
                ld      a,3                 ; string (type=1): elsize = the
                                            ; [len:1][ptr:2] heap descriptor
                                            ; (slice-4a; was 1+STRMAX inline)
                ret

; --- ary_stride: HL=descriptor base (name0) -> DE=total byte size ----------
; (6+2*ndim+elsize*count). HL preserved. Unchanged from the WIP (a single
; cached-field read, no multiply). Clobbers nothing but the two temp bytes
; used to read it.
ary_stride:
                push    hl
                inc     hl
                inc     hl
                inc     hl
                inc     hl                  ; HL -> stride field (+4)
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = cached stride
                pop     hl                  ; [DESC] restored
                ret

; --- ary_find: BC=key(name0,name1), A=type -> CF set+HL=descriptor base if -
; found; CF clear+HL=terminator/tail slot if not found. Preserves BC. Type is
; part of the key (A/A%/A! are distinct arrays, §4.1 #7). Unchanged from the
; WIP (ARYBASE is now derived here directly, same formula). Clobbers
; A,D,E,H,L.
ary_find:
                ld      d,a                 ; D = target type
                ld      hl,(ARYTAB)         ; HL = ARYBASE (arrays slice-4b:
                                            ; the STORED scalar-region-end
                                            ; cell, was derived (PRGEND)+2)
af_lp:
                ld      a,(hl)              ; name0 (0 = terminator)
                or      a
                jr      z,af_notfound
                cp      b
                jr      nz,af_skip
                push    hl
                inc     hl
                ld      a,(hl)              ; name1
                inc     hl
                ld      e,(hl)              ; type
                pop     hl
                cp      c
                jr      nz,af_skip
                ld      a,e
                cp      d
                jr      nz,af_skip
                scf
                ret
af_skip:
                push    bc                  ; guard key
                ld      a,d
                push    af                  ; guard target type (D)
                call    ary_stride          ; HL(preserved) -> DE=stride
                add     hl,de               ; HL = next descriptor candidate
                pop     af
                ld      d,a                 ; target type restored
                pop     bc                  ; key restored
                jr      af_lp
af_notfound:
                or      a                   ; CF clear
                ret

; --- ary_alloc: BC=key, A=type, IX=bounds source (ndim int16 LE words; ------
; (ARY_NIDX)=ndim) -> appends a new descriptor at the current tail (found by
; a fresh terminator walk from ARYBASE), writes [name0][name1][type][ndim]
; [stride][bounds...][zero-filled data], writes a fresh 2-byte $0000
; terminator right after. Out: HL=new descriptor base, CF set. On failure,
; returns CF clear and nothing written, with A = the ARY_ERR code -- which is
; A=1 "Subscript out of range" when the ELEMENT DATA would not fit a 16-bit
; byte count (D-ARR-B, see aal_soor below) and A=4 "Out of memory" when the
; descriptor+terminator would cross the ceiling or wrap the address space.
; Both differ from the WIP's own ary_alloc, which set FPERR (a main-ROM-only
; concept this tenant has no access to); every other detail (the terminator
; walk, the ceiling formula, the zero-fill) is unchanged.
; Own scratch frame on the STACK (IY-addressed, 10 bytes: KEY(2)/TYPE(1)/
; TAIL(2)/DATA_BYTES(2)/CEND(2)/RETRIED(1) -- see the file header for why
; this moved off ARY_SCR. CEND/RETRIED are arrays slice-4a additions (docs/
; spec-basic-arrays-slice4a-string-heap.md §2/§5.4): the ceiling is now
; FRETOP (the string heap's own low boundary), and a ceiling collision GCs
; the heap once before retrying, reclaiming any slack the heap can give
; back). Clobbers A,B,C,D,E,H,L,IX,IY.
ary_alloc:
                dec     sp
                dec     sp
                dec     sp
                dec     sp
                dec     sp
                dec     sp
                dec     sp
                dec     sp
                dec     sp
                dec     sp                  ; reserve a 10-byte scratch frame
                ld      iy,0
                add     iy,sp               ; IY = frame base
                ld      (iy+0),c            ; KEY name1 (C)
                ld      (iy+1),b            ; KEY name0 (B)
                ld      (iy+2),a            ; TYPE
                ld      hl,(ARYTAB)         ; HL = ARYBASE (arrays slice-4b)
aal_walk:
                ld      a,(hl)
                or      a
                jr      z,aal_tail
                call    ary_stride          ; HL(preserved) -> DE=stride
                add     hl,de
                jr      aal_walk
aal_tail:
                ld      (iy+3),l
                ld      (iy+4),h            ; TAIL
                ld      a,(ARY_NIDX)
                ld      b,a
                push    ix
                pop     hl                  ; HL = bounds source ptr
                call    ary_count_elems     ; -> DE=count, CF=overflow
                jp      c,aal_soor          ; D-ARR-B site A -- see aal_soor
                ex      de,hl               ; HL = count
                ld      a,(iy+2)            ; TYPE
                call    elsize_from_type    ; A = elsize (2/4/8, or 1+STRMAX for
                                            ; a string element -- slice-3 §4)
                ld      d,0
                ld      e,a
                call    ary_mul16_checked   ; DE = data bytes; CF=overflow
                jp      c,aal_soor          ; D-ARR-B site B -- see aal_soor
                ld      (iy+5),e
                ld      (iy+6),d            ; DATA_BYTES
                ld      a,(ARY_NIDX)
                add     a,a
                add     a,6                 ; A = header size (6+2*ndim, incl. the
                                            ; cached stride field)
                ld      c,a
                ld      b,0                 ; BC = header size
                ld      l,(iy+3)
                ld      h,(iy+4)            ; HL = TAIL
                add     hl,bc               ; HL = data start
                jp      c,aal_oom
                ld      e,(iy+5)
                ld      d,(iy+6)            ; DE = DATA_BYTES
                add     hl,de               ; HL = data end (= new tail)
                jp      c,aal_oom
                push    hl                  ; [DEND] (the only guarded value)
                ld      de,2
                add     hl,de               ; +2: reserve the fresh terminator
                jp      c,aal_oom_pop1      ; data_end == $FFFE/$FFFF: the terminator
                                            ; reservation wraps candidate_end past
                                            ; $FFFF -> OOM. Was two unchecked `inc hl`
                                            ; (16-bit INC sets no carry), so a wrapped
                                            ; $0000/$0001 candidate slipped the ceiling
                                            ; sbc below and corrupted top-of-RAM
                                            ; instead of erroring (pre-existing slice-1
                                            ; alloc bug, 65-B string elements widened
                                            ; the window; caught by the slice-3
                                            ; adversarial review, fixed 2026-07-16).
                                            ; aal_oom_pop1 pops the [DEND] just pushed.
                ex      de,hl               ; DE = candidate end
                ; ceiling = FRETOP (arrays slice-4a §2, docs/spec-basic-arrays-
                ; slice4a-string-heap.md): the array region may not grow past the
                ; string heap's low boundary (the heap occupies [FRETOP,C) above
                ; it). On a collision, GC the heap ONCE (reclaim any compaction
                ; slack) and retry before declaring OOM (§5.4) -- GC never
                ; touches array data, so CEND (candidate end, stashed in the
                ; frame) survives the retry unguarded; only FRETOP can move.
                ld      (iy+7),e
                ld      (iy+8),d            ; CEND = candidate end
                xor     a
                ld      (iy+9),a            ; RETRIED = 0
aal_ceil_try:
    IF CLEARPOOL
                ; D-CLP: the ceiling is the STRING POOL FLOOR, not FRETOP -- see
                ; scv_ceil_try above for the full reasoning, including why the
                ; GC retry that stood here is DEAD CODE rather than a dropped
                ; safety net (GC moves FRETOP; it cannot move the boundary), and
                ; why (iy+9)'s RETRIED slot is left allocated. A failure here
                ; stays ERR 7 -- an array that will not fit is out of MEMORY,
                ; not out of string space. Removing the retry also removes the
                ; push ix/pop ix that guarded strheap_gc's IX clobber.
                ; strheap_floor touches neither IX nor IY.
                ; ⚠️ D-FCH §3.2: strheap_VARCEIL now, not strheap_floor -- see
                ; scv_ceil_try above; the channel table sits between the two.
                call    strheap_varceil     ; HL = the variable-region ceiling
                ; 🔴 D-SPMERGE step 6: AND RESERVE THE MACHINE STACK UNDER IT. Since
                ; the merge `SP` lives BELOW `CSP`, and `strheap_varceil` clamps to
                ; `CSP` itself -- so without this the array region grows straight
                ; through the LIVE STACK. The stack's reserve below the pool top is
                ; kept from this side, which strheap_varceil's own note calls
                ; "only one side of it".
                ; The subtraction cannot wrap: the ceiling is a RAM address
                ; >= $8000, and a zero CSP left the clamp standing down.
                ; MEASURED without it: `DIM Z(1857)` + 26 scalars read NO OUTPUT AT
                ; ALL, where a clean tree raises `Out of memory` with 27 B spare.
                ; D-DIMRESERVE S3: STK_EDGE_RESERVE (116, measured -- see
                ; basic/sysvars.inc), not the 256 B page it was; DE is loaded next.
                ld      de,-STK_EDGE_RESERVE
                add     hl,de               ; keep STK_EDGE_RESERVE below the ceiling
    ELSE
                ld      hl,(FRETOP)         ; ceiling
    ENDIF
                ld      e,(iy+7)
                ld      d,(iy+8)            ; DE = CEND
                ex      de,hl               ; HL = candidate end, DE = ceiling
                or      a
                sbc     hl,de               ; HL = candidate_end - ceiling
                jr      c,aal_ceil_fits     ; candidate_end < ceiling -> fits
    IF CLEARPOOL
                jp      aal_oom_pop1
    ELSE
                ld      a,(iy+9)
                or      a
                jp      nz,aal_oom_pop1     ; already retried once -> genuine OOM
                ld      a,1
                ld      (iy+9),a
                push    ix                  ; S3: strheap_gc clobbers IX (its own GC
                call    strheap_gc          ; frame base, never restored); IX is our
                pop     ix                  ; bounds-source pointer, read by
                                            ; aal_bounds_lp below -- guard it
                jr      aal_ceil_try
    ENDIF
aal_ceil_fits:
                ; --- fits: write the descriptor header (incl. cached stride) ---
                pop     hl                  ; [DEND] -> HL = data end (= new tail)
                ld      e,(iy+3)
                ld      d,(iy+4)            ; DE = TAIL
                push    hl                  ; re-guard data end for the terminator write
                or      a
                sbc     hl,de               ; HL = stride (data_end - TAIL)
                push    hl                  ; [STRIDE]  (stack, top->bottom: STRIDE,DEND)
                ld      l,(iy+3)
                ld      h,(iy+4)            ; HL = TAIL (new descriptor base)
                ld      a,(iy+1)            ; name0 (B, stashed at iy+1)
                ld      (hl),a              ; name0
                inc     hl
                ld      a,(iy+0)            ; name1 (C, stashed at iy+0)
                ld      (hl),a              ; name1
                inc     hl
                ld      a,(iy+2)            ; TYPE
                ld      (hl),a              ; type
                inc     hl
                ld      a,(ARY_NIDX)
                ld      (hl),a              ; ndim
                inc     hl                  ; HL -> stride field
                pop     de                  ; [STRIDE] -> DE  (stack: DEND)
                ld      (hl),e              ; stride low
                inc     hl
                ld      (hl),d              ; stride high
                inc     hl                  ; HL -> bounds[0]
                ld      a,(ARY_NIDX)
                ld      b,a
                or      a
                jr      z,aal_bounds_done
aal_bounds_lp:
                ; D-ARR-C: the SOURCE walks downward (bound 0 is at the high end
                ; of the caller's block); the DESTINATION still fills ascending
                ; k, so the descriptor layout is byte-for-byte what it was.
                ld      a,(ix+0)
                ld      (hl),a
                inc     hl
                ld      a,(ix+1)
                ld      (hl),a
                inc     hl
                dec     ix
                dec     ix
                djnz    aal_bounds_lp
aal_bounds_done:
                ; HL = data start (the header+bounds walk landed exactly here)
                pop     de                  ; [DEND] -> DE = data end (= new tail);
                                            ; stack now empty of our own pushes
                push    hl                  ; guard data start across the terminator write
                ex      de,hl               ; HL = data end
                ld      (hl),0              ; fresh 2-byte $0000 terminator
                inc     hl
                ld      (hl),0
                pop     hl                  ; HL = data start restored
                ld      c,(iy+5)
                ld      b,(iy+6)            ; BC = data bytes (already computed above)
                ld      a,b
                or      c
                jr      z,aal_zero_done     ; (defensive; data is never 0 in practice)
aal_zero_lp:
                ld      (hl),0
                inc     hl
                dec     bc
                ld      a,b
                or      c
                jr      nz,aal_zero_lp
aal_zero_done:
                ld      l,(iy+3)
                ld      h,(iy+4)            ; HL = the new descriptor's base
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp                  ; deallocate the 10-byte frame (INC SP: no
                                            ; register/flag effect other than SP)
                ; D-CTLPOOL: same refresh as scv_ceil_fits' -- a new array moved
                ; the region's end, so the pool's floor moved with it.
                push    hl
                call    strheap_ctllim
                pop     hl
                scf
                ret
; --- aal_soor: the SIZE-RULE exit (D-ARR-B, docs/spec-basic-arrdim.md §3) ---
; The reference rejects an array whose ELEMENT DATA would not fit a 16-bit byte
; count -- `elsize * PI(bound_k+1) > $FFFF` -- with `Subscript out of range`,
; BEFORE it attempts any allocation, and zerobas answered `Out of memory`
; (docs/arrdim-vg8020-characterization.md, 19 divergent rows, one cause).
;
; This is deliberately NOT a new check: ary_count_elems and ary_mul16_checked
; between them ALREADY compute that exact product and already return CF on
; overflow. Sites A and B above are that pair of carries, and the measured rule
; is that they -- and only they -- are the size rule. The two sets are provably
; identical: the byte product exceeds $FFFF exactly when the ELEMENT product
; overflows (site A; the byte product then certainly does too, elsize being >= 2)
; or when the `elsize *` step does (site B). So the whole fix is which code the
; existing failure reports, which is why it costs 4 bytes and no arithmetic.
;
; ⚠️ The three carry checks BELOW sites A/B (tail+header, +data bytes, and the
; +2 terminator reservation) stay `Out of memory`. They are ADDRESS-SPACE wraps,
; not size-rule violations: anything reaching them has a byte count <= $FFFF,
; which the reference accepts and then fails on its own ceiling.
;
; ⚠️ The AUTO-DIM path gets this for free and MUST: ary_resolve auto-dims through
; this same ary_alloc, and `Q(1,1,1,1)=1` on an undeclared array asks for
; 11^4 * 8 = 117128 bytes -- the reference raises the size rule there too, with
; neither `DIM` nor a large number anywhere in the line (characterization §1.5).
; A check written into ex_dim would have satisfied every other measured row and
; left that one silently wrong.
;
; Reached only from sites A and B, both of which are BEFORE the `push hl` that
; aal_oom_pop1 exists to undo -- so the 10-byte scratch frame is the whole of the
; unwind here, exactly as for aal_oom.
aal_soor:
                ld      a,1                 ; ARY_ERR: Subscript out of range
                jr      aal_unframe         ; (-> FPERR=5 via ary_errmap)
aal_oom_pop1:
                pop     hl                  ; discard [DEND]
aal_oom:
                ld      a,4                 ; ARY_ERR: Out of memory
aal_unframe:
                                            ; A is the ARY_ERR code and survives:
                                            ; INC SP touches neither A nor any
                                            ; flag, so the `or a` below still
                                            ; clears CY for both entries.
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp                  ; deallocate the 10-byte frame
                or      a                   ; CF clear
                ret

; --- ary_resolve: BC=key, A=type; (ARY_NIDX)/(ARY_IDXP) prefilled by -------
; the caller (basic/arrays.asm's ary_parse_subs, main-ROM side). Out:
; HL=element address, A=0 (ok). On error, A = the ARY_ERR code and HL is a
; harmless dummy:
;   A=2 (Illegal function call) -- a negative subscript, §4.1 #9 (caught
;     BEFORE the bound compare, same disposition SQR(x<0) uses main-side).
;   A=1 (Subscript out of range) -- wrong dimension count vs the
;     descriptor's own ndim, or an in-range-but-over-bound index, §4.1 #8;
;     ALSO an auto-dim allocation whose element data would not fit a 16-bit
;     byte count, which arrives here from ary_alloc's aal_soor (D-ARR-B).
;     `Q(1,1,1,1)=1` on an undeclared array is the reachable case: auto-dim
;     takes every dimension to 10, so it asks for 11^4 * 8 = 117128 bytes.
;   A=4 (Out of memory) -- an auto-dim allocation that would cross the
;     ceiling.
; Own scratch frame on the STACK (IY-addressed, 6 bytes: OFFSET(2)/MULT(2)/
; TYPE(1)/NDIM(1)), reserved AFTER the ary_find/ary_alloc dance completes --
; that dance needs no scratch of its own (ary_alloc has its own SEPARATE
; frame, reserved/freed entirely within its own call), so there is no
; nesting conflict with this routine's own frame. Clobbers A,B,C,D,E,H,L,
; IX,IY.
ary_resolve:
                push    bc                  ; guard key across ary_find
                push    af                  ; guard type
                call    ary_find            ; BC,A -> CF/HL (BC preserved)
                jr      c,aryr_found
                pop     af
                pop     bc
                ; D-ARR-C: auto-dim past FOUR subscripts is always the size rule,
                ; so it is answered here instead of walking a longer bound table.
                ; Auto-dim takes every bound to 10, so five subscripts ask for
                ; 11^5 = 161051 elements -- 322102 B at the NARROWEST element
                ; width (int, 2 B) -- and no element width can bring that back
                ; under $FFFF. MEASURED on the reference, not reasoned:
                ; Q(1,1,1,1,1)=1, Q%(1,1,1,1,1)=1 and the 8-subscript form all
                ; answer `Subscript out of range` where the 4-subscript int
                ; control answers `Out of memory` (docs/arrdim-c-vg8020-
                ; characterization.md §3). This is what keeps
                ; ARY_AUTODIM_BOUNDS four words long.
                ld      e,a                 ; stash TYPE across the count check
                ld      a,(ARY_NIDX)
                cp      5
                ld      a,e                 ; TYPE back -- LD r,r' touches no flag,
                                            ; so the CP above still decides below
                jp      nc,aryr_autodim_soor ; `jp`, not `jr`: the shared exit sits
                                            ; past the whole resolve loop
                ld      ix,ARY_AUTODIM_BOUNDS+6 ; auto-dim (§4.1 #1): every bound=10.
                                            ; Addresses the LAST of the four words,
                                            ; since the walk now runs downward --
                                            ; every entry is 10, so any start with
                                            ; ndim words below it reads the same
                                            ; list, and ndim<=4 is guaranteed above.
                call    ary_alloc           ; BC,A,IX -> HL=new desc+CF; else A=err(4)
                jp      nc,aryr_alloc_fail
                jr      aryr_have_desc
aryr_found:
                pop     af                  ; discard (the descriptor's OWN stored
                pop     bc                  ; ndim/type are authoritative from here)
aryr_have_desc:
                ; HL = descriptor base (found or freshly auto-dim'd)
                dec     sp
                dec     sp
                dec     sp
                dec     sp
                dec     sp
                dec     sp                  ; reserve a 6-byte scratch frame
                ld      iy,0
                add     iy,sp               ; IY = frame base
                inc     hl
                inc     hl                  ; HL -> type field
                ld      a,(hl)
                call    elsize_from_type    ; A = elsize (slice-3 §4) -- NOT the
                                            ; raw type; ary_resolve never reports
                                            ; type back to the caller (already
                                            ; known: ARY_TYPE, passed in)
                ld      (iy+4),a            ; ELSIZE (renamed from the slice-1
                                            ; "TYPE (=elsize)" comment: that
                                            ; identity breaks for a string, §4)
                inc     hl                  ; HL -> ndim field
                ld      a,(ARY_NIDX)
                cp      (hl)
                jp      nz,aryr_wrongdim
                ld      a,(hl)
                ld      (iy+5),a            ; NDIM (loop counter)
                inc     hl
                inc     hl
                inc     hl                  ; HL -> bounds[0] (past the 2-byte cached
                                            ; stride field)
                xor     a
                ld      (iy+0),a
                ld      (iy+1),a            ; OFFSET = 0
                ld      a,1
                ld      (iy+2),a
                xor     a
                ld      (iy+3),a            ; MULT = 1
                ld      ix,(ARY_IDXP)       ; D-ARR-C: subscript 0 at the HIGH end
aryr_lp:
                ld      a,(iy+5)
                or      a
                jr      z,aryr_loop_done
                dec     a
                ld      (iy+5),a
                ld      e,(ix+0)
                ld      d,(ix+1)
                dec     ix
                dec     ix                  ; DOWNWARD (D-ARR-C); the OFFSET/MULT
                                            ; math below is untouched
                ld      a,d
                and     $80
                jp      nz,aryr_neg         ; no outstanding push here
                ld      c,(hl)              ; bound_k low
                inc     hl
                ld      b,(hl)              ; bound_k high
                inc     hl                  ; BC=bound_k; HL=advanced bounds cursor
                push    hl                  ; [BND] guard across the range check + muls
                ld      a,e
                sub     c
                ld      a,d
                sbc     a,b                 ; CF set <=> DE(subscript) < BC(bound_k)
                jr      c,aryr_inrange
                ld      a,e
                cp      c
                jp      nz,aryr_oob         ; [BND] outstanding — aryr_oob pops it
                ld      a,d
                cp      b
                jp      nz,aryr_oob         ; [BND] outstanding — aryr_oob pops it
aryr_inrange:
                inc     bc                  ; BC = bound_k+1
                push    bc                  ; [BND1] bound_k+1 (stack: BND1,BND)
                ld      l,(iy+2)
                ld      h,(iy+3)            ; HL = MULT (old)
                call    ary_mul16_checked   ; DE = subscript*MULT (trusted to fit —
                                            ; bounded by the descriptor's own already-
                                            ; validated element count)
                ld      l,(iy+0)
                ld      h,(iy+1)            ; HL = OFFSET (old)
                add     hl,de
                ld      (iy+0),l
                ld      (iy+1),h            ; OFFSET += subscript*MULT
                pop     de                  ; [BND1] = bound_k+1
                ld      l,(iy+2)
                ld      h,(iy+3)            ; HL = MULT (old) again
                call    ary_mul16_checked   ; DE = MULT*(bound_k+1) (trusted to fit)
                ld      (iy+2),e
                ld      (iy+3),d            ; MULT updated
                pop     hl                  ; [BND] advanced bounds cursor restored
                jr      aryr_lp
aryr_loop_done:
                ; HL = data start (descriptor base + 6 + 2*ndim, past the cached-
                ; stride header)
                push    hl                  ; guard data start
                ld      e,(iy+0)
                ld      d,(iy+1)            ; DE = final OFFSET
                ld      a,(iy+4)            ; A = ELSIZE (slice-3 §4)
                ex      de,hl               ; HL = OFFSET
                ld      d,0
                ld      e,a                 ; DE = elsize (zero-extended)
                call    ary_mul16_checked   ; DE = OFFSET*elsize (trusted to fit — bounded
                                            ; by the descriptor's own already-validated
                                            ; total data size)
                pop     hl                  ; HL = data start
                add     hl,de               ; HL = element address
                xor     a                   ; A = 0 (ok)
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp                  ; deallocate the 6-byte frame
                ret
aryr_wrongdim:
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp                  ; deallocate the 6-byte frame
                ld      a,1                 ; ARY_ERR: Subscript out of range
                ld      hl,0
                ret
aryr_neg:
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp                  ; deallocate the 6-byte frame
                ld      a,2                 ; ARY_ERR: Illegal function call (negative,
                                            ; §4.1 #9)
                ld      hl,0
                ret
aryr_oob:
                pop     hl                  ; balance the one outstanding [BND] push
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp                  ; deallocate the 6-byte frame
                ld      a,1                 ; ARY_ERR: Subscript out of range
                ld      hl,0
                ret
aryr_autodim_soor:
                ld      a,1                 ; D-ARR-C: auto-dim past four subscripts
                                            ; -- ARY_ERR: Subscript out of range,
                                            ; the same code aal_soor returns for the
                                            ; same reason (the byte count cannot fit
                                            ; $FFFF), reached without an allocation
                                            ; attempt. Falls into the shared exit.
aryr_alloc_fail:
                ; A already holds the ARY_ERR OOM code (4) from ary_alloc; no frame
                ; was reserved yet (aryr_have_desc's own reservation never ran)
                ld      hl,0
                ret

