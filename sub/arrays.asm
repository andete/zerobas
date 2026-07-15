; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; sub/arrays.asm — BASIC numeric arrays engine (slice-1 SPLIT design, the
; sub-ROM page-0 tenant half). docs/spec-basic-arrays.md §10 (the split
; contract): the array *semantics* (auto-dim to 10, base 0, subscript range/
; error dispositions) are oracle-locked to the public MSX-BASIC language
; reference + the VG-8020 black-box capture (spec §4.1/§5), carried over
; unchanged from the monolithic WIP (branch arrays-slice1-wip, basic/
; arrays.asm) — this is a RE-HOME + ABI-WIRE, not a rewrite of the algorithm.
; The array descriptor byte layout is zerobas's OWN design (spec §9.2/§10.3),
; exactly as VARTAB/STRTAB already are — never ROM disassembly.
;
; --- own-design descriptor (unchanged from the WIP, spec §9.2) -------------
;   +0  name0  : 1    upcased first char (0 = the terminator sentinel)
;   +1  name1  : 1
;   +2  type   : 1    2/4/8 (int/single/double), from suffix/DEFtbl
;   +3  ndim   : 1    dimension count (1..MAXDIM)
;   +4  stride : 2    CACHED total descriptor size in bytes (6+2*ndim+elsize*
;                     count) -- own-design redundancy, see the WIP's own
;                     header for the rationale (ary_find's skip-walk reads
;                     this instead of re-deriving it each step).
;   +6  bound0 : 2    inclusive upper subscript of dim 0 (LE)  ] ndim of these
;       ...             ...
;       element data : elsize*Pi(boundK+1) bytes, zero-filled on alloc
; elsize = type (2/4/8). Element order is column-major (first subscript
; varies fastest): off(i0,i1,..) = i0 + (b0+1)*(i1 + (b1+1)*(i2 + ...)),
; elem_addr = data_start + off*elsize.
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
; PRGEND/HIMEM, both read-only here) -- basic/sysvars.inc's ARY_OP..ARY_ERR
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

    IF ROM_BASE < $4000

; --- ary_engine: the tenant entry point (SUBROM_IDX_ARY, sub/equates.inc) --
; Reads ARY_OP and dispatches. op=0 (RESOLVE): read/write element address
; resolution, auto-dimensioning an undeclared array to bound 10 on first
; touch (§4.1 #1). op=1 (DIM): explicit declaration, redim-checked. Writes
; ARY_ADDR (RESOLVE only, harmless on DIM) and ARY_ERR (0 ok; 1 Subscript-oor;
; 2 Illegal-fn/negative; 3 Redimensioned; 4 OOM) either way. Clobbers
; everything (tenant convention; the caller is under subrom_call/CALSLT,
; which already clobbers all registers).
ary_engine:
                ld      a,(ARY_OP)
                or      a
                jp      nz,aeng_dim
                ld      bc,(ARY_KEY)
                ld      a,(ARY_TYPE)
                call    ary_resolve         ; -> HL=elem addr, A=err (0 ok)
                ld      (ARY_ADDR),hl
                ld      (ARY_ERR),a
                ret

; --- aeng_dim: ARY_OP=1 (explicit DIM). BC/A resolved from ARY_KEY/ARY_TYPE;
; (ARY_NIDX)/(ARY_IDX) hold the caller-parsed bound list (§9.4). ary_find
; first: if the array already exists (a previous DIM OR an auto-dim already
; touched it) -> ARY_ERR=3 (Redimensioned array, §4.1 #4); else ary_alloc
; with the parsed bounds.
aeng_dim:
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
                ld      ix,ARY_IDX          ; bounds source = the caller-parsed list
                call    ary_alloc           ; BC,A,IX -> HL=new desc+CF; else A=err(4)
                jr      nc,aeng_dim_err     ; A already holds the OOM err code (4)
                xor     a
                ld      (ARY_ERR),a         ; ok
                ret
aeng_dim_redim:
                ld      a,3                 ; Redimensioned array
                ld      (ARY_ERR),a
                ret
aeng_dim_err:
                ld      (ARY_ERR),a
                ret

; --- ARY_AUTODIM_BOUNDS: MAXDIM words, each = 10 (§4.1 #1). Read-only tenant
; data; ary_resolve's auto-dim path points IX here (vs. aeng_dim's IX, which
; points at the caller-parsed ARY_IDX for an explicit DIM) -- same ary_alloc,
; two different bounds sources, unchanged from the WIP.
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
; (push/pop) so the CALLER's own IX -- e.g. ary_resolve's ARY_IDX subscript-
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
; (Pi(bound_k+1)), HL advanced past the 2*ndim bytes. CF set = overflow (DE
; not meaningful; early return). Unchanged from the WIP other than calling
; the LOCAL ary_mul16_checked above instead of the resident mul16x16_32.
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
                ld      b,(hl)
                inc     hl                  ; BC=bound_k(raw); HL=advanced cursor
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
                ld      hl,(PRGEND)
                inc     hl
                inc     hl                  ; HL = ARYBASE
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
; terminator right after. Out: HL=new descriptor base, CF set. On OOM
; (bound-product overflow, or the descriptor+terminator would cross the
; ceiling), returns CF clear + A=4 (the ARY_ERR "Out of memory" code; nothing
; written) -- this differs from the WIP's own ary_alloc, which set FPERR
; (a main-ROM-only concept this tenant has no access to); every other detail
; (the terminator walk, the ceiling formula, the zero-fill) is unchanged.
; Own scratch frame on the STACK (IY-addressed, 7 bytes: KEY(2)/TYPE(1)/
; TAIL(2)/DATA_BYTES(2) -- see the file header for why this moved off
; ARY_SCR). Clobbers A,B,C,D,E,H,L,IX,IY.
ary_alloc:
                dec     sp
                dec     sp
                dec     sp
                dec     sp
                dec     sp
                dec     sp
                dec     sp                  ; reserve a 7-byte scratch frame
                ld      iy,0
                add     iy,sp               ; IY = frame base
                ld      (iy+0),c            ; KEY name1 (C)
                ld      (iy+1),b            ; KEY name0 (B)
                ld      (iy+2),a            ; TYPE
                ld      hl,(PRGEND)
                inc     hl
                inc     hl                  ; HL = ARYBASE
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
                jp      c,aal_oom
                ex      de,hl               ; HL = count
                ld      a,(iy+2)            ; TYPE (elsize)
                ld      d,0
                ld      e,a
                call    ary_mul16_checked   ; DE = data bytes; CF=overflow
                jp      c,aal_oom
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
                inc     hl
                inc     hl                  ; +2: reserve the fresh terminator
                ex      de,hl               ; DE = candidate end
                ; ceiling = min(HIMEM,TXTMAX), inlined (single call site) -- unchanged
                ; from the WIP (HIMEM==0 -> "never CLEAR'd" -> default TXTMAX).
                ld      hl,(HIMEM)
                ld      a,h
                or      l
                jr      z,aal_ceil_txtmax
                push    hl                  ; guard HIMEM value across the sbc
                ld      bc,TXTMAX
                or      a
                sbc     hl,bc               ; HL = HIMEM-TXTMAX
                pop     hl                  ; HL = HIMEM restored
                jr      c,aal_ceil_have     ; HIMEM<TXTMAX -> ceiling=HIMEM (in HL)
aal_ceil_txtmax:
                ld      hl,TXTMAX
aal_ceil_have:
                ; HL = ceiling, DE = candidate end (never touched above)
                ex      de,hl               ; HL = candidate end, DE = ceiling
                or      a
                sbc     hl,de               ; HL = candidate_end - ceiling
                jp      nc,aal_oom_pop1     ; candidate_end >= ceiling -> OOM
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
                ld      a,(ix+0)
                ld      (hl),a
                inc     hl
                inc     ix
                ld      a,(ix+0)
                ld      (hl),a
                inc     hl
                inc     ix
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
                inc     sp                  ; deallocate the 7-byte frame (INC SP: no
                                            ; register/flag effect other than SP)
                scf
                ret
aal_oom_pop1:
                pop     hl                  ; discard [DEND]
aal_oom:
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp                  ; deallocate the 7-byte frame
                ld      a,4                 ; ARY_ERR: Out of memory
                or      a                   ; CF clear
                ret

; --- ary_resolve: BC=key, A=type; (ARY_NIDX)/(ARY_IDX) prefilled by --------
; the caller (basic/arrays.asm's ary_parse_subs, main-ROM side). Out:
; HL=element address, A=0 (ok). On error, A = the ARY_ERR code and HL is a
; harmless dummy:
;   A=2 (Illegal function call) -- a negative subscript, §4.1 #9 (caught
;     BEFORE the bound compare, same disposition SQR(x<0) uses main-side).
;   A=1 (Subscript out of range) -- wrong dimension count vs the
;     descriptor's own ndim, or an in-range-but-over-bound index, §4.1 #8.
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
                ld      ix,ARY_AUTODIM_BOUNDS ; auto-dim (§4.1 #1): every bound=10
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
                ld      (iy+4),a            ; TYPE (= elsize)
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
                ld      ix,ARY_IDX
aryr_lp:
                ld      a,(iy+5)
                or      a
                jr      z,aryr_loop_done
                dec     a
                ld      (iy+5),a
                ld      e,(ix+0)
                ld      d,(ix+1)
                inc     ix
                inc     ix
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
                ld      a,(iy+4)            ; A = TYPE (elsize)
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
aryr_alloc_fail:
                ; A already holds the ARY_ERR OOM code (4) from ary_alloc; no frame
                ; was reserved yet (aryr_have_desc's own reservation never ran)
                ld      hl,0
                ret

    ENDIF
