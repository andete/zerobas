; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; sub/strheap.asm — the string HEAP engine (arrays slice-4a, the sub-ROM
; page-0 tenant half; docs/spec-basic-arrays-slice4a-string-heap.md §4/§5/§9).
;
; A compacting string heap sharing the low free RAM span with the array
; region (spec §2): arrays grow UP from ARYBASE, the heap grows DOWN from the
; ceiling C = min(HIMEM,TXTMAX) via the sysvar FRETOP. The collision test is
; the single invariant ARYEND <= FRETOP, where ARYEND is the array region's
; own $0000 terminator address (derived by a stride-walk from ARYBASE,
; exactly like sub/arrays.asm's own aal_walk — never stored). ARYBASE itself
; was (PRGEND)+2 through slice-4a; arrays slice-4b (docs/spec-basic-arrays-
; slice4b-scalar-reloc.md §2) inserts a numeric-scalar region below the array
; area, so ARYBASE is now the STORED live cell `ARYTAB` (sysvars.inc)
; instead — the scalar region's OWN base is still (PRGEND)+2.
;
; Every string descriptor everywhere in this codebase is now a uniform 3-byte
; [len:1][ptr:2] triple: a `$`-var STRTAB slot's tail, a string array
; element, a temp-descriptor-stack entry. `ptr` -> a body in the heap
; ([FRETOP,C)) OR somewhere else entirely (a token-stream literal, STRSCR,
; STR_EMPTY, FLD_DESC) — a body is only a GC ROOT candidate when its ptr lies
; inside [FRETOP,C); anything else is definitionally stable and untouched by
; GC (spec §5.2). A LENGTH-0 descriptor's ptr is BY CONVENTION always 0 (never
; a real heap address), so the len==0 check alone excludes it from root
; consideration everywhere below — no separate "ptr==0" test is needed.
;
; --- WHY THIS IS A SUB-ROM TENANT (spec §9, SIGNED OFF 2026-07-16) ---------
; heap_alloc + GC (root enumeration, compaction) are pure-RAM pointer/memory
; operations exactly like the array engine (sub/arrays.asm) this file shares
; a ROM page with — no BIOS / low-region / main-ROM-resident touch. It calls
; NOTHING outside this file (verified by tools/check_tenant_closure.py) except
; ary_stride (sub/arrays.asm), a co-resident sibling in the SAME page-0 image
; (an in-page `call`, not a CALSLT — no ABI boundary crossed). Dispatched via
; the standard subrom_call ABI (IX=SUBROM_ENTRY_BASE_P0+3*SUBROM_IDX_STRHEAP,
; sub/equates.inc); args/results marshalled in the SH_* param block
; (basic/sysvars.inc). heap_alloc/strheap_gc are ALSO reusable as ordinary
; in-page subroutines — sub/arrays.asm's aeng_copy_str (string array element
; store) and ary_alloc's own GC-before-OOM retry (spec §5.4) call them
; directly, no dispatch/param-block round trip needed for an already-
; co-resident caller.
;
; --- OWN-DESIGN GC (spec §5): SORT-THEN-SWEEP, sub-quadratic ----------------
; The reference MS-BASIC/MSX collector is O(n^2) (no per-string linkage -> it
; rescans all descriptors to find the highest unmoved body, once per body --
; the notorious multi-second GARBAGE COLLECTION freeze). zerobas beats it: it
; enumerates the live-body root descriptors into a TRANSIENT buffer, SORTS
; them by heap address, then does ONE address-ordered compaction sweep -- the
; spec §5 design. The sort is an in-place SHELL SORT with Knuth (3k+1) gaps:
; O(n^1.5) worst case, the spec §5.3-permitted "O(n log n)-class sort" fallback
; to the recommended O(n) radix counting sort (it needs only the 2n-byte
; descriptor-address array, no count array / ping-pong buffer), still crushing
; the reference's O(n^2) rescan for the string-array-heavy case. GC is
; unobservable (it changes only timing, never a program's results), so
; [bug-for-bug compat](bug-for-bug-compat-over-accuracy.md) does not bind it.
; Zero PERMANENT RAM. NOTE for Fable: the only deviation from the spec is the
; SORT ALGORITHM (shell vs radix) -- the enumerate/sort/single-sweep STRUCTURE
; is exactly §5.1/§5.3. No disassembly.
;
; SORT-BUFFER HOME (S6, 2nd Fable review). The 2n descriptor-address sort
; buffer lives in DETOKBUF ($BE00, 512 B) -- an EXISTING page-2 RAM buffer
; (the sub-ROM LIST/ASCII-SAVE detokeniser's one-shot output area, always
; mapped + writable from a page-0 tenant), NOT on the high-RAM hardware stack.
; The earlier stack-buffer design grew down from SP through the DISK RESIDENT
; WORK AREA (W50A9_WRKB $F242 / CURDRV_CELL $F247 / RES_STUBS $F24E-$F2B7 /
; DRVTBL $F340) and could corrupt the disk kernel under DI -- retired entirely
; (no GC scratch on the stack, ever; that deletes the whole bug class). 512 B
; / 2 = a 256-ROOT cap for this sub-quadratic path; a bigger live-root set
; (n > 256, a big filled string array) falls back to gc_slow -- the in-place
; O(n^2) selection compaction that needs NO buffer (exactly what real MSX
; does). The switch is on the ROOT COUNT n, never on SP.
;
; DETOKBUF-IDLE AUDIT (obligation discharged, not assumed). Borrowing DETOKBUF
; is safe iff it is idle at every point a STRING GC can fire. String GC fires
; only inside heap_alloc / ary_alloc (mid string-expression or DIM). DETOKBUF /
; DB_CUR are written ONLY by the LIST / ASCII-SAVE detokeniser (basic/list.asm,
; basic/save.asm's list_walk reuse, sub/detok.asm) -- and that path NEVER calls
; str_eval / heap_alloc / str_temp / concat (verified: no such reference in
; list.asm/detok.asm/save.asm's detok body), so it can allocate no heap string
; and can trigger no GC. Detok also fills DETOKBUF fully then drains it with no
; heap alloc in between (list.asm: subrom_call detok -> DETOKBUF -> print_string;
; no str_eval between), so DETOKBUF is never LIVE across an allocation. LIST /
; SAVE and string-expression eval are disjoint statements. Therefore DETOKBUF
; is provably idle whenever a string GC runs. The string engine itself never
; touches DETOKBUF / DB_CUR.


; --- strheap_engine: the tenant entry point (SUBROM_IDX_STRHEAP) -----------
; Reads SH_OP and dispatches. op=0 (ALLOC): SH_LEN -> SH_PTR (or SH_ERR=1 on
; OOM). op=1 (GC): unconditional compaction; SH_PTR := the new FRETOP;
; SH_ERR always 0 (GC cannot fail — an empty heap compacts to a no-op).
; op=2 (APPEND, the concat accumulator step): SH_DEST = accumulator temp R,
; SH_SRC = the operand to append -> R := R + operand IN PLACE (clamped 255);
; SH_ERR = 0 ok / 1 = heap OOM (R unchanged).
; op=3 (TEMP_ALLOC, shape-C follow-up — the main-ROM low region ran out of
; room for the temp-descriptor-stack allocators themselves, see basic/str-
; engine.asm's str_temp_alloc header): SH_LEN = length -> SH_PTR = the new
; slot, SH_PTR2 = the body address to fill; SH_ERR as op=2.
; op=4 (SNAPSHOT, same follow-up): SH_SRC = source descriptor address ->
; SH_PTR = the new slot (an owned copy); SH_ERR as op=2 (no SH_PTR2 — the
; copy happens entirely tenant-side).
; op=5 (SLICE, same follow-up): SH_SRC = a temp-descriptor-stack entry
; address (already uniquely owned), SH_START/SH_COUNT = the 0-based
; start/count to keep of its CURRENT body (pre-validated by the caller:
; start+count <= length, count <= STRMAX). Moves those bytes to the front of
; the SAME body (no realloc — slicing only shrinks/moves within memory
; already owned) and sets the descriptor's length to count. No result
; value; SH_ERR always 0.
; Clobbers everything (tenant convention).
strheap_engine:
                ld      a,(SH_OP)
                or      a
                jp      z,she_alloc
                cp      1
                jp      z,she_gc
                cp      2
                jp      z,sh_append         ; op=2 (APPEND: R += Tk, in place)
                cp      3
                jp      z,she_temp_alloc
                cp      4
                jp      z,she_snapshot
                cp      5
                jr      z,she_slice_op
                cp      6
                jp      z,sh_hex_build
                cp      7
                jp      z,sh_oct_build
                cp      8
                jp      z,sh_fill
                cp      9
                jr      z,she_mid_store_op
                cp      10
                jr      z,she_cmp_op
                cp      11
                jr      z,she_instr_op
                cp      12
                jp      z,sh_var_store      ; sets SH_ERR itself (0 ok / 1 OOM)
                cp      14
                jp      z,sh_bin_build      ; BIN$ (op 8 is sh_fill, hence 14)
                cp      15
                jp      z,sh_free_gap       ; FRE
    IF CLEARPOOL
                cp      16
                jp      z,she_snap_keep     ; SNAPSHOT-UNLESS-ALREADY-A-TEMP (D-CLP)
                cp      17
                jp      z,sh_free_vars      ; FRE(n) -- free VARIABLE space (D-CLP)
                cp      18
                jp      z,sh_chan_addr      ; file-channel block address (D-FCH §3.2)
                cp      19
                jp      z,sh_val_scr        ; D-INPNUM: VAL-parse the STRSCR field
                cp      20
                jp      z,sh_ctl_reset      ; D-CTLPOOL: derive the pool's top
                cp      21
                jp      z,she_snap_slice    ; D-SLICEOOM: a slice's source
    ENDIF
                jp      sh_val_parse        ; op==13: the only other value the
                                            ; main-ROM glue ever writes
she_instr_op:
                call    sh_instr_search
                xor     a
                ld      (SH_ERR),a
                ret
she_cmp_op:
                ld      hl,(SH_SRC)
                ld      de,(SH_DEST)
                call    sh_cmp_bits
                ld      (SH_LEN),a          ; A = 1/2/4 relation bits (reuses
                                            ; SH_LEN as the 1-byte result field)
                xor     a
                ld      (SH_ERR),a
                ; D-TEMPPOL part 2: both operands are CONSUMED -- the answer is a
                ; number. Pop the right (newer) then the left, each only if it
                ; is on top: `X=(MID$(A$,1)="X")+...` held TWO temps per compare
                ; and ran out at 8 terms on a 10-entry pool (the VG-8020: none).
                ld      hl,(SH_DEST)
                call    sh_pop_top
                ld      hl,(SH_SRC)
                jp      sh_pop_top
she_mid_store_op:
                jp      sh_mid_store        ; sets SH_ERR itself (0 ok / 3 range)
she_slice_op:
                call    she_slice
                xor     a
                ld      (SH_ERR),a
                ret
she_gc:
                call    strheap_gc
                ld      hl,(FRETOP)
                ld      (SH_PTR),hl
                xor     a
                ld      (SH_ERR),a
                ret
she_alloc:
                ld      a,(SH_LEN)
                call    heap_alloc          ; -> CF+HL=ptr / CF clear=OOM
                jr      nc,she_oom
                ld      (SH_PTR),hl
                xor     a
                ld      (SH_ERR),a
                ret
she_oom:
                ld      a,1
                ld      (SH_ERR),a
                ret

; she_temp_alloc / she_snapshot: op=3/4 handlers. Both build on
; sh_temp_push_alloc (below, shared with sh_append (op=2)) and re-derive
; OOM-vs-success from the WRITTEN slot's own [len][ptr] state (ptr==0 while
; len!=0 <=> the heap_alloc inside sh_temp_push_alloc failed) rather than
; threading extra registers through — simpler and correct either way.
she_temp_alloc:
                ld      a,(SH_LEN)
                call    sh_temp_push_alloc  ; CF clear=overflow(A=2) / CF set:B=err(0/1)
                jr      nc,she_ta_full
                ld      (SH_PTR),hl
                ld      (SH_PTR2),de
                ld      a,b                 ; err code (0 ok / 1 heap OOM) -- S7:
                ld      (SH_ERR),a          ; read B, NOT the neutralised slot
                ret
she_ta_full:
                ld      a,2
                ld      (SH_ERR),a
                ret

    IF CLEARPOOL
; --- sh_src_is_temp: CF set iff (SH_SRC) is a TEMP-DESCRIPTOR-STACK entry ---
; i.e. lies in [TEMPPOOL, TEMPBASE). D-CLP uses this twice, and both uses rest
; on the same property: a temp entry is UNIQUELY OWNED (nothing else holds its
; body) and FIXED-ADDRESS (the array-region shift only touches [ARYTAB,ARYEND)),
; and it is an enumerated GC root (sg_walk_temps). Clobbers A,D,E,H,L.
sh_src_is_temp:
                ld      hl,(SH_SRC)
                ; fall through
; --- sh_hl_is_temp: the same test on an arbitrary HL, HL PRESERVED. ---------
; sub/arrays.asm aeng_copy_str needs it for (STRPTR) rather than (SH_SRC).
sh_hl_is_temp:
                push    hl
                ld      de,TEMPPOOL
                or      a
                sbc     hl,de
                pop     hl                  ; (pop does not touch flags)
                jr      c,sit_no            ; below the pool -> not a temp
                push    hl
                ld      de,TEMPBASE
                or      a
                sbc     hl,de
                pop     hl
                ret     c                   ; in [TEMPPOOL,TEMPBASE) -> CF set
sit_no:
                or      a                   ; CF clear
                ret

; --- she_snap_keep: op=16 -- SNAPSHOT UNLESS THE SOURCE IS ALREADY A TEMP ---
; D-CLP. basic/vars.asm str_set_key snapshots its source before the target
; alloc (the H1 fix, spec-basic-arrays-slice4c §6/Q1) because an array-element
; or RVDESC descriptor goes STALE across the region shift + collision GC. That
; reasoning has always excluded temp-stack sources -- str_set_key's own header
; says so ("existing string-scalar / temp-stack sources were already safe") --
; but it snapshotted them anyway, because before the partition the extra copy
; was free: it landed in a ~15 KB gap and the next GC took it back.
;
; It is not free any more. With `CLEAR n` sizing the pool, what matters is the
; PEAK, not the steady state, and `A$=STRING$(100,"A")` was measured costing
; 300 bytes of pool at its peak against the reference's 100 -- the STRING$ temp,
; this redundant snapshot of it, and the variable's own body. FRE("") hid it
; because FRE GCs first, so the resting number looked right while `CLEAR 100 :
; A$=STRING$(100,"A")` (which the reference accepts exactly) raised ERR 14.
; Dropping the redundant copy takes the peak to 200; sh_var_store's adoption of
; a temp body (below) takes it to 100, which is the reference's own figure.
she_snap_keep:
                call    sh_src_is_temp
                jp      nc,she_snapshot     ; not a temp -> the real snapshot
she_snap_asis:
                ld      hl,(SH_SRC)
                ld      (SH_PTR),hl         ; the source IS the owned temp
                xor     a
                ld      (SH_ERR),a
                ret

; --- she_snap_slice: op=21 -- a SLICE's source (D-SLICEOOM, 2026-09-26) ------
; LEFT$/RIGHT$/MID$ copied a non-temp source WHOLE before slicing it, so
; `CLEAR 60:A$=STRING$(50,"A"):B$=MID$(A$,2,3)` needed 53 B and raised `Out of
; string space` where the VG-8020 has room (FRE("") 7 after; scratchpad/
; sliceoom_probe.py). A SCALAR variable's descriptor is kept AS-IS instead:
; it is STABLE for the statement (new scalars are appended; only the array
; region shifts), and the GC keeps its ptr current, so she_slice can allocate
; just the result and copy from it. An ARRAY element's descriptor MOVES on that
; shift, but its distance from ARYTAB does not (a new scalar moves the whole
; region; a new array is appended past it; DIM/ERASE are statements), so it gets
; an OFFSET TEMP: a pushed slot [len][element - ARYTAB] with no body. Every real
; temp's ptr is a heap body (>= $8000) or 0 with len 0, and the offset is below
; $8000 -- that bit is the tag she_slice reads, and the GC's range test already
; skips it (ptr < FRETOP). Main reads only the len byte, which is the element's.
; Everything else -- an RVDESC or STRSCR (scratch the next sub-expression can
; clobber) -- takes op 16's rule unchanged. Concatenation and comparison stay
; on op 16: concat appends INTO its accumulator in place, which must never be a
; variable.
she_snap_slice:
                ld      hl,(SH_SRC)
                ld      de,(VARTAB)
                or      a
                sbc     hl,de
                jr      c,she_snap_keep     ; below the scalars -> op 16's rule
                ld      hl,(SH_SRC)
                ld      de,(ARYTAB)
                or      a
                sbc     hl,de
                jr      c,she_snap_asis     ; a scalar: stable, keep it
                ex      de,hl               ; DE = element - ARYTAB
                ld      hl,(SH_SRC)
                ld      bc,(STREND)
                or      a
                sbc     hl,bc
                jr      nc,she_snap_keep    ; past the arrays -> op 16's rule
                push    de                  ; [ofs]
                xor     a
                call    sh_temp_push_alloc  ; a bodiless slot; CF clear = overflow
                pop     de                  ; DE = ofs (pop keeps CF)
                jr      nc,sss_full         ; A = 2
                ld      (SH_PTR),hl
                ld      bc,(SH_SRC)
                ld      a,(bc)
                ld      (hl),a              ; slot.len = the element's
                inc     hl
                ld      (hl),e
                inc     hl
                ld      (hl),d              ; slot.ptr = the offset (bit 15 clear)
                xor     a
sss_full:
                ld      (SH_ERR),a
                ret
    ENDIF

she_snapshot:
                ld      hl,(SH_SRC)
                ld      a,(hl)              ; source length
                push    hl                  ; guard source addr          [SRC]
                call    sh_temp_push_alloc  ; CF clear=overflow / CF set:B=err,DE=body
                jr      nc,she_sn_full
                ld      (SH_PTR),hl         ; slot
                ld      a,b
                ld      (SH_ERR),a          ; err (0 ok / 1 heap OOM) -- S7
                or      a
                jr      nz,she_sn_oom       ; heap OOM -> no body to copy (DE=0)
                ; success: DE = body (nonzero). Copy source -> body.
                pop     hl                  ; HL = SRC (source descriptor)  [ ]
                call    str_body_copy       ; HL=source desc, DE=body
                ret
she_sn_oom:
                pop     hl                  ; discard [SRC]
                ret
she_sn_full:
                pop     hl                  ; discard [SRC]
                ld      a,2
                ld      (SH_ERR),a
                ret

; she_slice: op=5 handler (shape-C follow-up move of str_temp_slice,
; basic/str-engine.asm — LEFT$/RIGHT$/MID$'s in-place substring op; see that
; routine's own former header, now this one's). SH_SRC = temp descriptor
; (BC-style contract renamed to SH_SRC), SH_START/SH_COUNT = 0-based
; start/count of its CURRENT body to keep (pre-validated by the caller).
; Moves those bytes to the front of the SAME (uniquely-owned) body and sets
; the descriptor's length to SH_COUNT. Clobbers A, B, C, D, E, H, L.
she_slice:
    IF CLEARPOOL
                call    sh_src_is_temp
                jr      nc,she_slice_new    ; D-SLICEOOM: a kept scalar source
                inc     hl
                inc     hl
                bit     7,(hl)
                jr      z,she_slice_ofs     ; ptr < $8000: an array OFFSET temp
    ENDIF
                ; D-S2BHEAP (2026-09-27): the kept bytes go to the body's HIGH
                ; end, so the trimmed PREFIX is the part at the heap's edge --
                ; and a body AT the edge (FRETOP) gives it back at once, as the
                ; reference's heap reads: `A$=MID$("ABCDEF",2,3)` holds 3 B, not
                ; the 6 of the literal's copy (scratchpad/strtemp_probe.py).
                ld      hl,(SH_SRC)
                ld      bc,(SH_START)       ; C = start, B = count
                ld      a,(hl)              ; A = the body's length
                ld      (hl),b              ; temp.len := count
                inc     b
                dec     b
                ret     z                   ; count 0 -> empty, done
                sub     b                   ; A = shift = length - count
                ret     z                   ; nothing trimmed (start 0)
                inc     hl
                push    hl                  ; [&ptr]
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = body
                ld      hl,(FRETOP)
                or      a
                sbc     hl,de               ; Z iff the body is the heap's edge
                ld      l,a
                ld      h,0
                add     hl,de               ; HL = new ptr = body + shift (Z kept)
                jr      nz,ss_inner
                ld      (FRETOP),hl         ; the prefix is free space again
ss_inner:
                ex      (sp),hl             ; [new ptr], HL = &ptr
                pop     de                  ; DE = new ptr
                ld      (hl),e
                inc     hl
                ld      (hl),d              ; temp.ptr = new ptr
                sub     c                   ; A = bytes trimmed off the END
                ret     z                   ; none: the kept bytes end the body
                ld      h,d
                ld      l,e
                ld      c,b
                ld      b,0                 ; BC = count
                add     hl,bc
                dec     hl
                ld      d,h
                ld      e,l                 ; DE = the destination's last byte
                push    bc
                ld      c,a
                ld      b,0
                or      a
                sbc     hl,bc               ; HL = the source's last byte
                pop     bc
                lddr                        ; dst > src and they overlap: from the top
                ret
    IF CLEARPOOL
; she_slice_new -- the source is a SCALAR variable op 21 kept (not a temp):
; allocate ONLY the result as a new temp, then copy from the source's CURRENT
; body -- re-read after the alloc, which may have collected and moved it. The
; result becomes STRPTR. An overflow or OOM is a pending error (first error
; wins), raised at the statement boundary before the value is used.
she_slice_new:
                ld      a,(SH_COUNT)
                call    sh_temp_push_alloc  ; CF clear = no slot; CF set: B=err,
                jr      nc,ssn_full         ; HL = slot, DE = body
                ld      (STRPTR),hl         ; the result (a [0][0] slot on OOM)
                ld      a,b
                or      a
                ld      a,FPERR_STROOM
                jr      nz,ssn_err          ; heap OOM
                ld      a,d
                or      e
                ret     z                   ; count 0 -> the empty string, done
                push    de                  ; [body]
                ld      hl,(SH_SRC)
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = the source's body, NOW
                ld      a,(SH_START)
                ld      l,a
                ld      h,0
                add     hl,de               ; HL = source + start
                pop     de                  ; DE = the new body
                ld      a,(SH_COUNT)
                ld      c,a
                ld      b,0
                ldir
                ret
; she_slice_ofs -- the source is an OFFSET temp op 21 pushed for an array
; element: allocate the result's body, THEN find the element again (ARYTAB +
; offset -- the GC may have moved its body, never its offset) and copy; the
; slot becomes the result. During the alloc the slot is [len][offset], which
; the GC's range test skips. A real EMPTY temp ([0][0]) lands here too, and
; its count is 0.
she_slice_ofs:
                ld      a,(SH_COUNT)
                or      a
                jr      z,sso_empty
                call    heap_alloc          ; A = count -> CF+HL = body / CF clear = OOM
                jr      nc,sso_oom
                ex      de,hl               ; DE = the new body
                ld      hl,(SH_SRC)
                inc     hl
                ld      c,(hl)
                inc     hl
                ld      b,(hl)              ; BC = offset
                ld      hl,(ARYTAB)
                add     hl,bc               ; HL = the element's descriptor, NOW
                inc     hl
                ld      a,(hl)
                inc     hl
                ld      h,(hl)
                ld      l,a                 ; HL = its body, NOW
                ld      a,(SH_START)
                ld      c,a
                ld      b,0
                add     hl,bc               ; HL = source + start
                push    de                  ; [body]
                ld      a,(SH_COUNT)
                ld      c,a
                ldir
                pop     de                  ; DE = body
                ld      hl,(SH_SRC)
                ld      (hl),a              ; slot.len = count (A still = count)
                inc     hl
                ld      (hl),e
                inc     hl
                ld      (hl),d              ; slot.ptr = body
                ret
sso_oom:
                ld      a,FPERR_STROOM
                call    ssn_err             ; pending, first error wins
sso_empty:
                ld      hl,(SH_SRC)
                xor     a
                ld      (hl),a
                inc     hl
                ld      (hl),a
                inc     hl
                ld      (hl),a              ; slot = [0][0], the empty string
                ret
ssn_full:
                ld      a,9                 ; String formula too complex
ssn_err:
                ld      b,a
                ld      a,(FPERR)
                or      a
                ret     nz                  ; first error wins
                ld      a,b
                ld      (FPERR),a
                ret
    ENDIF

; --- strheap_floor: -> HL = the STRING POOL's low boundary (D-CLP) ----------
; docs/spec-basic-clearpool.md §3. `min(HIMEM,TXTMAX) - POOLSIZE`, i.e. the
; ceiling the heap compacts against minus the size CLEAR recorded. The pool is
; [floor, C); everything below the floor belongs to variables and arrays.
;
; DERIVED, NEVER STORED — S-CLP-2 reversed. The first design put a POOLBASE
; cell in RAM and had basic/str-engine.asm heap_reset write it. RAM was never
; the scarce resource; the LOW REGION is (30 B free at the time, and heap_reset
; lives there), while this ROM has ~3.4 KB. Deriving it here costs the main ROM
; zero bytes and makes `CLEAR ,himem` fall out for free: that form moves the
; ceiling and never touches POOLSIZE, so every re-derivation picks the new
; ceiling up on its own (characterization §2.8).
;
; The clamp is not decoration. POOLSIZE is bounded to int16 by CLEAR's own
; domain check, but HIMEM is user-settable (`CLEAR 500,&H9000`), so a ceiling
; below the requested pool is expressible. Answering 0 there makes every
; allocation fail with ERR 14, which is the honest reading of "the pool does
; not fit"; letting the subtraction wrap would put the floor ABOVE the ceiling
; and hand out bodies over the top of RAM. Clobbers A,B,C,D,E,H,L.
strheap_floor:
                call    strheap_ceiling     ; HL = C = min(HIMEM,TXTMAX)
                ld      de,(POOLSIZE)
                or      a
                sbc     hl,de
                ret     nc
                ld      hl,0                ; pool larger than the whole map
                ret

; --- strheap_ctllim: CTLLIM := ARYEND+2, the control pool's collision floor -
; D-CTLPOOL. The pool descends from CTLTOP and is full when its frontier would
; reach the first byte the variable/array region does not already own. ARYEND is
; found by walking the array chain -- sub-ROM knowledge -- so the main ROM cannot
; derive this, and a `subrom_call` on the PUSH path is not affordable:
; `FOR I=1 TO 1000:GOSUB 100:NEXT` pushes a thousand times.
;
; 🔴 SO THIS IS A STORED DERIVATION, AND STORED DERIVATIONS GO STALE -- exactly
; what strheap_floor's own header argues against. It is safe only because it has
; ONE definition (here) and is refreshed at every point the region's end can
; move: both allocator success paths (scv_ceil_fits, aal's descriptor tail) and
; sh_ctl_reset. ⚠️ A path that grows the region without passing one of those
; would leave CTLLIM STALE-LOW, which is the DANGEROUS direction -- the pool
; would be allowed to overwrite live variables. That is a gate's job, not a
; comment's: see docs/spec-basic-trapsvc.md §17.
; Clobbers A,B,C,D,E,H,L (strheap_aryend's).
strheap_ctllim:
                call    strheap_aryend      ; HL = ARYEND (the live $0000 terminator)
                ld      (STREND),hl         ; D-ADDR29 S2: the PUBLISHED STREND is
                                            ; exactly ARYEND (ptrchain_probe, 9/9)
                inc     hl
                inc     hl                  ; +2: past the live 2-byte sentinel, the
                ld      (CTLLIM),hl         ; first byte the region does not own
                ret

; --- strheap_varceil: -> HL = the VARIABLE/ARRAY region's ceiling (D-FCH §3.2)
; `strheap_floor() - MAXF*FCH_CTXSZ`. The file-channel table is carved out of
; the pool immediately BELOW the string pool's floor, so the map is
;
;   [PRGEND+2 .. varceil) variables+arrays | [varceil .. floor) CHANNEL TABLE
;   | [floor .. C) string pool
;
; and `MAXFILES=n` costs n*FCH_CTXSZ of FRE(0) while leaving FRE("") alone —
; which is exactly what the CF-3300 does (characterization §2 the 267 B/channel
; ladder, §5 the string pool reading 200 at MAXFILES 0 and 8 alike).
;
; ⚠️ DERIVED, NEVER STORED, for the same reason strheap_floor is: the inputs
; (MAXF, POOLSIZE, HIMEM) all live in RAM, so every derivation is current and no
; hook is needed at `CLEAR`/`MAXFILES`/boot. Storing it would cost main-ROM
; bytes AND open a staleness hole; this costs the main ROM nothing.
;
; ⚠️ The clamp mirrors strheap_floor's: `MAXFILES=15` with a small `CLEAR`
; ceiling is expressible, and answering 0 makes every allocation fail honestly
; rather than wrapping the ceiling above the pool.
; Clobbers A,B,C,D,E,H,L. Preserves IX/IY (both array callers rely on IY).
strheap_varceil:
                call    strheap_chantab     ; HL = the channel table's base
svc_ctl:
                ; 🎯 D-CTLPOOL, THE SYMMETRIC HALF -- and it is one comparison.
                ; Control frames descend from this same ceiling, so the variable
                ; and array region may only grow up to the pool's live FRONTIER,
                ; not to the empty pool's top. Without this a deep recursion and a
                ; fresh `DIM` would silently overwrite each other -- the pool's own
                ; check (main-ROM ctl_alloc, against CTLLIM) is only one side of it.
                ; ⚠️ CSP == CTLTOP when the pool is empty, so this costs nothing at
                ; rest and every caller keeps its previous answer.
                ; ⚠️ AND IT MUST NOT FIRE BEFORE THE POOL IS INITIALISED: CSP is
                ; power-on garbage until clear_vars runs, so a zero CSP would answer
                ; "no room at all". `sh_ctl_reset` runs from clear_vars at cold boot,
                ; before any array can exist, and the guard below keeps a
                ; never-initialised CSP from shrinking the ceiling to nothing.
                ld      de,(CSP)
                ld      a,d
                or      e
                ret     z                   ; CSP not initialised yet -> unchanged
                ; ⚠️ NO STACK RESERVE HERE, AND THAT IS DELIBERATE (D-SPMERGE step 6).
                ; The merge does need `CTL_STACK_MARGIN` kept clear below the
                ; frontier, but NOT in this routine: `strheap_varceil()` is ALSO the
                ; pool's TOP (`CTLTOP`, basic/program.asm) and the source of the
                ; program-text store ceiling `SL_CEIL`, so a reserve taken here moves
                ; the whole map. MEASURED: a `dec d` on this line turned txtceil's
                ; POSITIVE control red with `stored=0` -- the bound refused every
                ; program, exactly what that control exists to catch -- and took
                ; loc-acceptance with it. The reserve belongs at the two ARRAY-growth
                ; consumers in sub/arrays.asm, and that is where it now is.
                push    hl
                or      a
                sbc     hl,de
                pop     hl
                ret     c                   ; ceiling already below CSP -> unchanged
                ex      de,hl               ; CSP is the lower of the two
                ret

; --- strheap_chantab: -> HL = the FILE-CHANNEL TABLE's base (D-CHANSWITCH) ---
; `strheap_floor() - MAXF*FCH_CTXSZ`: varceil's own first half, WITHOUT the
; D-CTLPOOL clamp to CSP. 🔴 sh_chan_addr (op 18) used to derive the block
; address from strheap_varceil itself -- and with a FOR or GOSUB frame standing
; the clamp returns CSP, so channel 1's block sat ON the newest control frame
; and every channel switch (fch_save_active, 306 B) wrote over it. Measured,
; not reasoned: two OUTPUT channels written in a FOR loop gave NO READING and
; from a GOSUB `File not found`, where the CF-3300 writes both files
; (scratchpad/chanloop_run8.out). The table does not move with the frames;
; only the variable region's ceiling does.
; Clobbers A,B,C,D,E,H,L.
strheap_chantab:
                call    strheap_floor       ; HL = the string pool's floor
                ld      a,(MAXF)
                inc     a                   ; D-FCBSHAPE FCB #0 (2026-10-10): MAXFILES
                                            ; + 1 blocks -- the reference reserves #0
                                            ; at EVERY MAXFILES, 0 included
                                            ; (scratchpad/fcb0_run.out)
                ld      b,a
                ld      de,-FCH_CTXSZ       ; 267 a channel (D-FCBSHAPE S1)
svc_sub_lp:
                add     hl,de               ; CF set iff no borrow (HL >= block)
                jr      nc,svc_under
                djnz    svc_sub_lp
                ret
svc_under:
                ld      hl,0                ; the table does not fit under the pool
                ret

; --- heap_alloc: A=len(0..255) -> CF set+HL=body ptr / CF clear=OOM --------
; (spec §4). A bump allocator on the downward frontier FRETOP.
;
; D-CLP: the collision floor is the POOL FLOOR (strheap_floor above), not
; ARYEND+2 — that is the whole partition. Before, the string area and the
; variable area were the same piece of memory and the allocator failed only
; when the two MET; now the boundary is where `CLEAR n` put it, and a failure
; here is `Out of string space` (ERR 14) rather than `Out of memory` (ERR 7).
; The main-ROM glue maps SH_ERR=1 to FPERR_STROOM for exactly that reason.
;
; ⚠️ THE GC RETRY STAYS LIVE HERE, unlike the two array ceilings (sub/arrays.asm
; scv_ceil_try/aal_ceil_try), whose retries this same change turns into dead
; code. The asymmetry is real and worth stating: an array's ceiling was FRETOP,
; which GC MOVES, and is now the floor, which GC cannot move — so retrying buys
; nothing there. The heap's own frontier is FRETOP, which GC still moves UP by
; reclaiming dead bodies, so a retry here still converts an apparent overflow
; into a successful allocation. That is what makes `CLEAR 500 : A$=STRING$
; (100,"A") : A$="B"` read 499 rather than 399.
;
; Own scratch frame on the STACK (IY-addressed, 4 bytes: LEN(1)/FLOOR(2)/
; RETRIED(1) — the sub/arrays.asm convention, since no fixed RAM byte is spare
; here either). Clobbers A,B,C,D,E,H,L,IY.
heap_alloc:
                or      a                   ; len 0 -> a 0-length body needs no storage;
                jr      nz,ha_real          ; return ptr 0 (honours the len-0 => ptr==0
                ld      hl,0                ; header convention, §3), no frame, no FRETOP
                scf                         ; change
                ret
ha_real:
                dec     sp
                dec     sp
                dec     sp
                dec     sp                  ; reserve a 4-byte scratch frame
                ld      iy,0
                add     iy,sp
                ld      (iy+0),a            ; LEN
                xor     a
                ld      (iy+3),a            ; RETRIED = 0
    IF CLEARPOOL
                call    strheap_floor       ; -> HL = the pool floor (D-CLP)
    ELSE
                call    strheap_aryend      ; -> HL = ARYEND
    ENDIF
                ld      (iy+1),l
                ld      (iy+2),h
ha_attempt:
                ld      hl,(FRETOP)
                ld      e,(iy+0)
                ld      d,0                 ; DE = LEN
                or      a
                sbc     hl,de               ; HL = candidate = FRETOP - LEN
                ld      e,(iy+1)
                ld      d,(iy+2)            ; DE = the floor
    IF CLEARPOOL
                                            ; D-CLP: the pool floor is an ADDRESS THE
                                            ; POOL OWNS, not a sentinel to stay above,
                                            ; so there is no +2 here. `CLEAR 100` then
                                            ; a 100-byte string must land exactly ON it
                                            ; and leave FRE("") = 0 (characterization
                                            ; §2.6, the oos-exact row); an off-by-two
                                            ; would make the pool two bytes short of
                                            ; the size the user asked for.
    ELSE
                inc     de
                inc     de                  ; DE = ARYEND+2 (S4: ARYEND is the address
                                            ; of the LIVE 2-byte $0000 array sentinel;
                                            ; the heap body must start ABOVE it)
    ENDIF
                push    hl                  ; guard candidate
                or      a
                sbc     hl,de               ; HL = candidate - floor
                pop     hl                  ; HL = candidate (restored)
                jr      nc,ha_ok            ; candidate >= floor -> fits
                ; collision: already retried once?
                ld      a,(iy+3)
                or      a
                jr      nz,ha_oom
                ld      a,1
                ld      (iy+3),a
                call    strheap_gc          ; recompute FRETOP (ARYEND unchanged —
                                            ; GC never touches array data)
                jr      ha_attempt
ha_ok:
                ld      (FRETOP),hl
                inc     sp
                inc     sp
                inc     sp
                inc     sp                  ; deallocate the 4-byte frame
                scf
                ret
ha_oom:
                inc     sp
                inc     sp
                inc     sp
                inc     sp                  ; deallocate the 4-byte frame
                or      a                   ; CF clear
                ret

; --- strheap_aryend: -> HL = ARYEND (the array region's own $0000 -----------
; terminator address, walked fresh from ARYBASE via the co-resident
; ary_stride, sub/arrays.asm — the identical walk aal_walk/ary_find already
; do). Never stored; O(number of arrays), acceptable (small in practice; only
; GC itself is required to be O(n) in the ROOT count). Clobbers A,D,E,H,L.
strheap_aryend:
                ld      hl,(ARYTAB)         ; HL = ARYBASE (arrays slice-4b:
                                            ; the STORED scalar-region-end
                                            ; cell, was derived (PRGEND)+2)
sae_walk:
                ld      a,(hl)
                or      a
                ret     z                   ; HL = ARYEND (the terminator)
                call    ary_stride          ; HL(preserved) -> DE=stride
                add     hl,de
                jr      sae_walk

; --- strheap_ceiling: -> HL = C = min(HIMEM,TXTMAX) -------------------------
; The heap's fixed upper bound (strings compact TIGHT AGAINST this, never
; against the fluctuating FRETOP). A small duplicate of sub/arrays.asm's own
; ary_alloc ceiling calc (now simplified there to just read FRETOP, §2) — the
; two copies necessarily differ in what they read (this is the ABSOLUTE
; ceiling; arrays' own ceiling is now the heap's LOW boundary), so sharing
; code across the two purposes buys nothing; small-proven-idiom duplication
; is this codebase's own established precedent (e.g. is_letter, above).
; Clobbers A,B,C,H,L.
strheap_ceiling:
                ld      hl,(HIMEM)
                ld      a,h
                or      l
                jr      z,shc_txtmax
                push    hl
                ld      bc,TXTMAX
                or      a
                sbc     hl,bc
                pop     hl
                jr      c,shc_have          ; HIMEM<TXTMAX -> ceiling=HIMEM
shc_txtmax:
                ld      hl,TXTMAX
shc_have:
                ret

; --- strheap_gc: O(n^1.5) SORT-THEN-SWEEP compaction (spec §5) --------------
; This is the SIGNED-OFF sub-quadratic collector (§5.3): enumerate the live
; heap-body root descriptors into a TRANSIENT hardware-stack buffer, SORT
; them by heap address, then do ONE address-ordered compaction sweep. The
; sort is an in-place SHELL SORT with Knuth (3k+1) gaps — O(n^1.5) worst
; case, the "O(n log n)-class sort" fallback the sign-off explicitly permits
; over the radix counting sort (it needs only the 2n-byte descriptor-address
; array on the stack — no 256/512-byte count array, no ping-pong output
; buffer — so it is far less error-prone to get right, while still crushing
; the reference MSX collector's O(n^2) rescan for the string-array-heavy
; case, which is the whole point). Zero PERMANENT RAM (the buffer is freed on
; return); the descriptors carry no per-body header (the zero-overhead heap,
; §3), so location/length live only in the owning descriptor throughout.
;
; Because value-copy semantics give every live string its OWN fresh body (no
; aliasing — str_set_key/aeng_copy_str/snapshot all copy), the root ptrs are
; DISTINCT, so a single address-ordered sweep moves each body exactly once
; (no re-scan, unlike the reference). A non-heap ptr (literal/STR_EMPTY/
; RVDESC-over-STRSCR/FLD_DESC) sits OUTSIDE [OLD_FRETOP,C) and is skipped by
; the range test, so it is never a root (§5.2).
;
; Own scratch frame on the STACK (IX-addressed, 22 bytes); the 2n descriptor-
; address sort buffer is in DETOKBUF (fixed, NOT on the stack):
;   +0 OLD_FRETOP  +2 CEIL(C)  +4 N  +6 BASE(=DETOKBUF)  +8 DEST  +10 GAP2/CURSOR
;   +12 P  +14 Q  +16 GAP(elem)  +18 TMP(descaddr)  +20 MODE(1)
; (+10 doubles as the FILL cursor during enumeration and gap*2 during sort;
;  +12/+14 double as the array-walk's ARR_CUR/ARR_END during enumeration and
;  the sort's outer/inner pointers afterward — never overlapping in time.)
; Clobbers A,B,C,D,E,H,L,IX. PRESERVES IY (the body never touches it) -- load-
; bearing: heap_alloc holds its retry flag in (iy+3) ACROSS its `call strheap_gc`
; (heap_alloc ~:307), and ary_alloc likewise relies on IY surviving the GC.
strheap_gc:
                ld      hl,-22
                add     hl,sp
                ld      sp,hl               ; reserve the 22-byte frame
                push    hl
                pop     ix                  ; IX = frame base
                ld      hl,(FRETOP)
                ld      (ix+0),l
                ld      (ix+1),h            ; OLD_FRETOP
                call    strheap_ceiling     ; HL = C
                ld      (ix+2),l
                ld      (ix+3),h            ; CEIL = C
                ld      (ix+8),l
                ld      (ix+9),h            ; DEST = C (compact tight against C)
                ; --- Phase B: count in-range roots -> N (+4) ---
                xor     a
                ld      (ix+4),a
                ld      (ix+5),a            ; N = 0
                ld      (ix+20),a           ; MODE = 0 (count)
                call    sg_walk
                ; N==0 (empty heap) -> FRETOP = C, nothing to move.
                ld      a,(ix+4)
                or      (ix+5)
                jp      z,sg_finish
                ; --- Phase C: the sort buffer (2N B) --------------------------
                ; 🔁 D-DETOKBUF S2 (2026-09-25): NOT DETOKBUF any more -- that
                ; 1280 B buffer is gone (Joost: "Drop DETOKBUF"). The array goes
                ; in the VARIABLE free area, [ARYEND+2, SP): since D-SPMERGE the
                ; stack descends from the pool frontier TOWARD the arrays, so the
                ; bottom of that gap is idle during a collection -- it is the
                ; FRE(0) space, usually thousands of bytes. It needs 2N B plus
                ; CTL_STACK_MARGIN of headroom under the live SP; failing that,
                ; gc_slow (in-place O(n^2), no buffer) as before.
                ; ✅ AND THE OLD N <= 256 CAP IS GONE WITH IT: it was DETOKBUF's
                ; 512 B, not the sort's -- sg_shellsort is 16-bit throughout.
                ; ⚠️ The base is the LIVE ARYEND (the array walk), not CTLLIM: a
                ; stored derivation could be stale mid-allocation, and a stale
                ; floor would put the array ON the arrays.
                call    strheap_aryend      ; HL = ARYEND (preserves IX, the frame)
                inc     hl
                inc     hl                  ; HL = the first free byte above them
                push    hl                  ; [base]
                ld      l,(ix+4)
                ld      h,(ix+5)
                add     hl,hl               ; 2N
                pop     de
                push    de                  ; DE = base   [base]
                add     hl,de               ; the array's end
                jp      c,gc_nobuf
                ld      de,CTL_STACK_MARGIN
                add     hl,de               ; ...plus the stack's headroom
                jp      c,gc_nobuf
                ex      de,hl               ; DE = end + margin
                ld      hl,0
                add     hl,sp               ; HL = SP (one word low: conservative)
                or      a
                sbc     hl,de
                jp      c,gc_nobuf          ; SP below end+margin -> no room
                pop     hl                  ; HL = base   [ ]
                ld      (ix+6),l
                ld      (ix+7),h            ; BASE = the free area's bottom
                ld      (ix+10),l
                ld      (ix+11),h           ; CURSOR = BASE (for the fill walk)
                ; --- Phase D: fill the buffer with the root descriptor addrs ---
                ld      a,1
                ld      (ix+20),a           ; MODE = 1 (fill)
                call    sg_walk
                ; --- Phase E: shell-sort the buffer ascending by ptr key ---
                call    sg_shellsort
                ; --- Phase F: sweep, highest ptr first (descending) ---
                ; P walks the sorted array from the LAST element down to BASE.
                ld      l,(ix+4)
                ld      h,(ix+5)
                dec     hl                  ; N-1
                add     hl,hl               ; 2*(N-1) (byte offset of last element)
                ld      e,(ix+6)
                ld      d,(ix+7)            ; DE = BASE
                add     hl,de               ; HL = &SRC[N-1]
                ld      (ix+12),l
                ld      (ix+13),h           ; P = &last element
sg_sweep:
                ld      l,(ix+12)
                ld      h,(ix+13)           ; HL = P
                ld      c,(hl)
                inc     hl
                ld      b,(hl)              ; BC = descaddr = SRC[i]
                call    sg_move_one         ; move its body up to DEST, fix its ptr
                ; P -= 2 ; loop while P >= BASE
                ld      l,(ix+12)
                ld      h,(ix+13)
                ld      de,2
                or      a
                sbc     hl,de               ; P -= 2
                ld      (ix+12),l
                ld      (ix+13),h
                ld      e,(ix+6)
                ld      d,(ix+7)            ; DE = BASE
                push    hl
                or      a
                sbc     hl,de               ; P - BASE
                pop     hl
                jp      nc,sg_sweep         ; P >= BASE -> more elements
                ; --- Phase G: publish new FRETOP, free the frame ---
                ; (the sort buffer is DETOKBUF, not on the stack -- nothing to
                ; free but the 22-B IX frame.)
                ld      l,(ix+8)
                ld      h,(ix+9)
                ld      (FRETOP),hl
                jr      sg_freeframe
sg_finish:
                ld      l,(ix+2)
                ld      h,(ix+3)            ; C
                ld      (FRETOP),hl         ; empty heap -> FRETOP = C
sg_freeframe:
                ld      hl,22
                add     hl,sp
                ld      sp,hl               ; free the 22-byte frame
                ret

; --- gc_slow: O(n^2) selection compaction, NO buffer -- the fallback when the
; variable free area cannot hold the 2N-B sort array under the live SP (since
; D-DETOKBUF S2; it used to be "n > 256 roots, which the 512-B DETOKBUF sort
; buffer cannot hold"). Exactly what real MSX's own collector always does. Repeatedly
; walk all roots (MODE=2) to find the highest-ptr not-yet-compacted body, move
; it up to DEST, repeat until none remain. Correct for arbitrary n; slower.
; Reuses sg_move_one for the move. BEST_PTR in frame +6 (BASE slot, unused in
; this path), BEST_DESC in +16 (GAP slot, unused) — both clear of the array-
; walk's own +12/+14 scratch. No buffer -> frees only the 22-B frame.
gc_nobuf:
                pop     hl                  ; drop [base]; no room -> in place
gc_slow:
                ; DEST is already CEIL (ix+8/9, set before Phase B).
gcs_outer:
                xor     a
                ld      (ix+6),a
                ld      (ix+7),a            ; BEST_PTR = 0
                ld      a,2
                ld      (ix+20),a           ; MODE = 2 (selection)
                call    sg_walk
                ld      a,(ix+6)
                or      (ix+7)
                jr      z,gcs_done          ; no unprocessed root -> done
                ld      c,(ix+16)
                ld      b,(ix+17)           ; BC = BEST_DESC
                call    sg_move_one         ; move its body to DEST, fix ptr, DEST-=n
                jr      gcs_outer
gcs_done:
                ld      l,(ix+8)
                ld      h,(ix+9)
                ld      (FRETOP),hl         ; publish new FRETOP
                jr      sg_freeframe        ; no buffer reserved -> free frame only

; --- sg_move_one: BC = descriptor address -> move its heap body UP to DEST ---
; (frame +8), fix the descriptor's ptr to the new location, and DEST -= n.
; Overlap-safe (new_dest >= body, compacting toward the ceiling -> LDDR). Used
; by both the shell-sort sweep and the O(n^2) fallback. Clobbers A,B,C,D,E,H,L.
sg_move_one:
                ld      a,(bc)              ; A = n (body length)
                ld      e,a
                ld      d,0                 ; DE = n
                ld      l,(ix+8)
                ld      h,(ix+9)            ; HL = DEST
                or      a
                sbc     hl,de               ; HL = new_dest = DEST - n
                ld      (ix+8),l
                ld      (ix+9),h            ; DEST := new_dest
                push    bc                  ; guard descaddr
                ld      l,c
                ld      h,b
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = body (source)
                ld      l,(ix+8)
                ld      h,(ix+9)            ; HL = new_dest
                push    hl
                or      a
                sbc     hl,de               ; new_dest - body
                pop     hl                  ; HL = new_dest
                jr      z,smo_fixup         ; already in place -> skip the move
                ; BC still = descaddr in-register; HL=new_dest, DE=body.
                ld      a,(bc)              ; A = n
                ld      c,a
                ld      b,0                 ; BC = n
                push    bc                  ; guard n         stack: [descaddr][n]
                add     hl,bc               ; new_dest + n
                dec     hl                  ; dstlast
                ex      de,hl               ; DE = dstlast ; HL = body (source base)
                add     hl,bc               ; body + n
                dec     hl                  ; srclast
                pop     bc                  ; BC = n          stack: [descaddr]
                lddr                        ; (HL)->(DE) downward, BC bytes
smo_fixup:
                pop     bc                  ; BC = descaddr
                ld      l,c
                ld      h,b
                inc     hl                  ; -> ptr field
                ld      a,(ix+8)
                ld      (hl),a
                inc     hl
                ld      a,(ix+9)
                ld      (hl),a              ; descaddr.ptr := new_dest (fixed up)
                ret

; --- sg_walk: visit EVERY live root descriptor, calling sg_visit(HL=descaddr)
; on each (arrays slice-4c, docs/spec-basic-arrays-slice4c-string-scalar-
; unification.md §5.2 root set, REVISED from the pre-4c STRTAB slots: the
; unified scalar chain, string-array elements, temp-descriptor-stack
; entries). PRESERVES IX (the strheap_gc frame); ary_stride preserves
; IX/IY/BC too. Clobbers A,B,C,D,E,H,L (+ sg_visit's).
sg_walk:
                call    sg_walk_scalars
                call    sg_walk_arrays
                call    sg_walk_fnframe
                ; fall through to sg_walk_temps
; temp-stack entries [TEMPPOOL, TEMPPT), stride 3 (the pool grows UP since
; D-ADDR29 TEMPPT).
sg_walk_temps:
                ld      hl,TEMPPOOL
sgw_tm_lp:
                ld      de,(TEMPPT)
                push    hl
                or      a
                sbc     hl,de               ; cursor - TEMPPT
                pop     hl
                ret     nc                  ; cursor >= TEMPPT -> done
                call    sg_visit            ; HL preserved by sg_visit
                ld      de,3
                add     hl,de
                jr      sgw_tm_lp
; --- sg_walk_fnframe: the DEF FN shadow slots [FN_PAREA, FN_FEND) --------
; 🔴 WITHOUT THIS, A STRING FORMAL'S BODY IS REACHABLE FROM NOTHING THE GC WALKS
; (D-FNGCROOT, docs/spec-deffn-gcroot.md). `str_set_key` (basic/vars.asm:979)
; snapshots the actual into a temp, stores THAT COPY's descriptor into the
; destination, and then restores TEMPTOP -- releasing the temp. While an FN call
; is live the destination is a shadow slot, because scv_find consults
; fn_shadow_find first (sub/arrays.asm). So the copy was referenced only by a
; slot this walk never visited.
;
; ⚠️ IT TOOK THREE ROUNDS TO PROVOKE, AND THE FIRST TWO WERE GREEN FOR REASONS
; THAT HAD NOTHING TO DO WITH THE HAZARD. A collection ALONE cannot catch it:
; compaction moves live bodies UPWARD (measured, $BAEB -> $BAFC) and the dead
; copy is the LOWEST allocation, so a GC moves everything AWAY from it and leaves
; its bytes intact. The frontier has to march back DOWN over the copy, which
; means ALLOCATING after the collection and before the formal is read. The
; catching row is g2.sub -- `DEF FNA$(S$)=LEFT$(STR$(FRE(""))+X$+X$,0)+S$` --
; which returned the literal garbage `376A` where both references say `ABCD`.
;
; Same shape as sg_walk_scalars: [name0][name1][type][value:8], a type==1 entry's
; [len][ptr] descriptor at entry+3. Stride is the fixed FN_SLOTSZ rather than
; elsize_from_type -- a shadow slot is always a full scalar entry, that being the
; whole point of the area. The end test is byte-wise against FN_FEND, mirroring
; fn_shadow_find's own loop: the area never crosses a page (sysvars.inc asserts
; it), and FN_FEND == low FN_PAREA means "no FN call in progress", so the very
; first compare returns and a program with no live FN call pays 8 T-states.
;
; ⚠️ THIS COVERS THE LIVE FRAME ONLY, AND AN OUTER FRAME IS STILL UNREACHABLE.
; fn_enter saves the caller's live prefix to the Z80 STACK, which no walk can
; address, so during a NESTED call an outer string formal's body has the same
; problem. Measured and recorded rather than implied -- see the spec's §6.
sg_walk_fnframe:
                ld      hl,FN_PAREA
sgw_fn_lp:
                ld      a,(FN_FEND)
                cp      l
                jr      z,sgw_fn_live_done  ; live frame done -> the SAVED ones (D-FNPOOL)
                push    hl                  ; [ENTRY]
                inc     hl
                inc     hl                  ; -> type field (entry+2)
                ld      a,(hl)
                cp      1
                jr      nz,sgw_fn_skip
                inc     hl                  ; -> descriptor (entry+3, NOT +2)
                call    sg_visit            ; visits [len][ptr]; preserves HL
sgw_fn_skip:
                pop     hl                  ; HL = entry base
                ld      a,FN_SLOTSZ
                add     a,l
                ld      l,a
                jr      sgw_fn_lp
sgw_fn_live_done:
                ; D-FNPOOL: ...and now the SAVED frames, which is the whole point
                ; of moving them into the pool. Each is [prevFNSP:2][size:1][prefix],
                ; and the prefix is a copy of FN_BASE, so its parameter area runs
                ; from prefix+FN_CELLS to prefix+size -- the same slot loop, a
                ; different base and end. An outer call's string formal is a root
                ; from here on (D-FNGCNEST measured it corrupting: `qLMNO`).
                ld      hl,(FNSP)
sgw_fnf_lp:
                ld      a,h
                or      l
                ret     z                   ; the chain is walked
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = prevFNSP
                inc     hl
                ld      c,(hl)              ; C = size
                inc     hl                  ; HL -> the saved prefix
                push    de                  ; [prev]
                ld      a,c
                sub     FN_CELLS            ; A = the parameter area's length
                jr      z,sgw_fnf_next
                jr      c,sgw_fnf_next
                ld      b,a                 ; B = bytes of slots to walk
                ld      de,FN_CELLS
                add     hl,de               ; HL -> the frame's first slot
sgw_fnf_slot:
                push    bc
                push    hl                  ; [ENTRY]
                inc     hl
                inc     hl                  ; -> type field
                ld      a,(hl)
                cp      1
                jr      nz,sgw_fnf_skip
                inc     hl                  ; -> descriptor
                call    sg_visit            ; visits [len][ptr]; preserves HL
sgw_fnf_skip:
                pop     hl
                ld      de,FN_SLOTSZ
                add     hl,de
                pop     bc
                ld      a,b
                sub     FN_SLOTSZ
                jr      c,sgw_fnf_next
                jr      z,sgw_fnf_next
                ld      b,a
                jr      sgw_fnf_slot
sgw_fnf_next:
                pop     hl                  ; HL = prevFNSP
                jr      sgw_fnf_lp
; --- sg_walk_scalars: the unified scalar chain [PRGEND+2, ARYTAB) --------
; (arrays slice-4c §3b, REPLACES sg_walk_strtab). Every entry is
; [name0][name1][type][value...]; a type==1 (string) entry's value is the
; [len:1][ptr:2] heap descriptor at entry+3 -- visit it; a numeric entry
; (2/4/8) is never a root, skip it. Stride is per-entry:
; elsize_from_type(type)+3, modelled directly on sg_walk_arrays/ary_stride's
; own per-descriptor stride. End-test is BYTE-WISE against (ARYTAB), not a
; 16-bit `ld de,(ARYTAB)` + subtract, mirroring scv_find's own scvf_lp
; (sub/arrays.asm) so no register beyond A is disturbed by the test.
;
; THE single most bug-prone byte in this slice: the descriptor offset is
; entry+3 (past [name0][name1][type]), NOT entry+2 like the old STRTAB
; slot (which had no type byte to skip). A stale +2 here would visit the
; TYPE byte as a [len], corrupting every GC compaction -- gated directly
; (array-acceptance's GC-root-correctness case is written to go red on a
; +2 regression, docs/spec-basic-arrays-slice4c-string-scalar-
; unification.md §9).
sg_walk_scalars:
                ld      hl,(PRGEND)
                inc     hl
                inc     hl                  ; HL = scalar-region base
sgw_sc_lp:
                ld      a,(ARYTAB+1)        ; end-of-region test, byte-wise
                cp      h
                jr      nz,sgw_sc_go
                ld      a,(ARYTAB)
                cp      l
                ret     z                   ; HL == ARYTAB -> every scalar scanned
sgw_sc_go:
                push    hl                  ; [ENTRY]
                inc     hl
                inc     hl                  ; -> type field (entry+2)
                ld      a,(hl)              ; A = type (kept live across the
                                            ; conditional visit, on the CPU
                                            ; stack, below)
                push    af                  ; [ENTRY][TYPE]
                cp      1
                jr      nz,sgw_sc_skip
                inc     hl                  ; -> descriptor (entry+3, NOT +2)
                call    sg_visit            ; visits [len][ptr] at entry+3
sgw_sc_skip:
                pop     af                  ; A = type restored
                call    elsize_from_type    ; A = elsize (identity 2/4/8;
                                            ; 3 for type=1 string); preserves
                                            ; BC,D,E,H,L
                pop     hl                  ; HL = entry base
                add     a,3                 ; A = total entry width
                add     a,l
                ld      l,a
                jr      nc,sgw_sc_lp
                inc     h
                jr      sgw_sc_lp
; string-array elements: every element (stride 3) of every type==1 array
; descriptor, from data_start (desc+6+2*ndim) to data_end (desc+stride). The
; per-array element cursor/end live in the enclosing frame's +12/+14 (free
; during the walk — they become the sort's P/Q afterward).
sg_walk_arrays:
                ld      hl,(ARYTAB)         ; HL = ARYBASE (arrays slice-4b)
sgw_ar_lp:
                ld      a,(hl)
                or      a
                ret     z                   ; terminator -> every array scanned
                push    hl                  ; [DESC]
                inc     hl
                inc     hl                  ; -> type (+2)
                ld      a,(hl)
                cp      1
                jr      nz,sgw_ar_next      ; not a string array -> next desc
                inc     hl                  ; -> ndim (+3)
                ld      a,(hl)
                add     a,a
                add     a,6                 ; header size (6+2*ndim)
                pop     hl                  ; HL = desc
                push    hl
                ld      e,a
                ld      d,0
                add     hl,de               ; HL = data_start
                ld      (ix+12),l
                ld      (ix+13),h           ; ARR_CUR = data_start
                pop     hl                  ; HL = desc
                push    hl
                call    ary_stride          ; DE = stride; HL(desc) preserved
                add     hl,de               ; HL = data_end
                ld      (ix+14),l
                ld      (ix+15),h           ; ARR_END = data_end
sgw_ar_elem:
                ld      l,(ix+12)
                ld      h,(ix+13)           ; HL = ARR_CUR
                ld      e,(ix+14)
                ld      d,(ix+15)           ; DE = ARR_END
                or      a
                sbc     hl,de               ; CUR - END
                jr      nc,sgw_ar_next      ; CUR >= END -> done elements ([DESC] still on stack)
                ld      l,(ix+12)
                ld      h,(ix+13)           ; HL = ARR_CUR (element descaddr)
                call    sg_visit
                ld      l,(ix+12)
                ld      h,(ix+13)
                ld      de,3
                add     hl,de
                ld      (ix+12),l
                ld      (ix+13),h           ; ARR_CUR += 3
                jr      sgw_ar_elem
sgw_ar_next:
                pop     hl                  ; HL = desc
                call    ary_stride          ; DE = stride; HL(desc) preserved
                add     hl,de               ; HL = next descriptor
                jr      sgw_ar_lp

; --- sg_visit: HL=descaddr -> if the descriptor names an in-range heap body,
; either count it (MODE=0: N++) or append its address to the fill buffer
; (MODE=1: store at CURSOR, CURSOR+=2). Preserves HL. Uses the enclosing
; frame (IX). Clobbers A,B,C,D,E.
sg_visit:
                call    sg_inrange          ; CF set iff a live in-range heap root; HL kept
                ret     nc
                ld      a,(ix+20)           ; MODE
                or      a
                jr      z,sgv_count         ; 0 = count
                dec     a
                jr      z,sgv_fill          ; 1 = fill
                ; MODE 2 = O(n^2) selection: track the highest ptr that is still
                ; < DEST (not yet compacted). BEST_PTR +6, BEST_DESC +16.
                push    hl
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = ptr
                pop     hl                  ; HL = descaddr
                ld      a,e
                sub     (ix+8)
                ld      a,d
                sbc     a,(ix+9)            ; ptr - DEST ; CF set = ptr < DEST (accept)
                ret     nc                  ; ptr >= DEST -> already compacted, skip
                ld      a,e
                sub     (ix+6)
                ld      a,d
                sbc     a,(ix+7)            ; ptr - BEST_PTR ; CF set = ptr < BEST_PTR
                ret     c                   ; not a new max -> keep the current best
                ld      (ix+6),e
                ld      (ix+7),d            ; BEST_PTR := ptr
                ld      (ix+16),l
                ld      (ix+17),h           ; BEST_DESC := descaddr
                ret
sgv_count:
                inc     (ix+4)              ; count: N++ (16-bit)
                ret     nz
                inc     (ix+5)
                ret
sgv_fill:
                ld      e,(ix+10)
                ld      d,(ix+11)           ; DE = CURSOR
                ld      a,l
                ld      (de),a
                inc     de
                ld      a,h
                ld      (de),a
                inc     de
                ld      (ix+10),e
                ld      (ix+11),d           ; CURSOR += 2
                ret

; --- sg_inrange: HL=descaddr -> CF set iff len>0 AND OLD_FRETOP <= ptr < CEIL
; (the descriptor names a live heap body, not a literal/STR_EMPTY/FLD_DESC/
; empty). Preserves HL. Clobbers A,D,E. Uses IX frame (+0 OLD_FRETOP, +2 CEIL).
sg_inrange:
                ld      a,(hl)
                or      a
                jr      z,sgir_no           ; len 0 -> not a root
                push    hl
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = ptr
                ; ptr >= OLD_FRETOP ?  (CF set from the sub/sbc = ptr < OLD_FRETOP)
                ld      a,e
                sub     (ix+0)
                ld      a,d
                sbc     a,(ix+1)
                jr      c,sgir_no_pop       ; ptr < OLD_FRETOP -> reject
                ; ptr < CEIL ?  (CF set = ptr < CEIL = accept)
                ld      a,e
                sub     (ix+2)
                ld      a,d
                sbc     a,(ix+3)
                pop     hl                  ; restore descaddr (POP keeps CF)
                ret                         ; CF set iff ptr < CEIL -> in range
sgir_no_pop:
                pop     hl
sgir_no:
                or      a                   ; CF clear -> not in range
                ret

; --- sg_shellsort: in-place shell sort (Knuth 3k+1 gaps) of the N-element ---
; descriptor-address array at BASE (frame +4 N, +6 BASE), ASCENDING by each
; element's ptr key (word at descaddr+1). O(n^1.5) worst case (spec §5.3's
; permitted O(n log n)-class fallback). GAP(elem) in +16, GAP2(bytes) in +10,
; outer pointer P in +12, inner pointer Q in +14, the element being inserted
; (TMP) in +18. Clobbers A,B,C,D,E,H,L.
sg_shellsort:
                ld      l,(ix+4)
                ld      h,(ix+5)
                ld      de,2
                or      a
                sbc     hl,de
                ret     c                   ; N < 2 -> already sorted
                ; gap = 1; while (3*gap+1 < N) gap = 3*gap+1
                ld      hl,1
sgs_grow:
                ld      d,h
                ld      e,l                 ; DE = gap (last valid candidate)
                add     hl,hl
                add     hl,de
                inc     hl                  ; HL = 3*gap+1
                push    hl
                ld      c,(ix+4)
                ld      b,(ix+5)
                or      a
                sbc     hl,bc               ; (3gap+1) - N
                pop     hl
                jr      c,sgs_grow          ; < N -> keep growing (gap = HL)
                ex      de,hl               ; HL = gap (last value that stayed < N)
sgs_gaploop:
                ld      (ix+16),l
                ld      (ix+17),h           ; GAP (elem)
                add     hl,hl               ; gap*2 (byte stride)
                ld      (ix+10),l
                ld      (ix+11),h           ; GAP2
                ; --- one gapped insertion pass ---
                ; P = BASE + GAP2   (first i = gap element)
                ld      l,(ix+6)
                ld      h,(ix+7)            ; BASE
                ld      e,(ix+10)
                ld      d,(ix+11)           ; GAP2
                add     hl,de
                ld      (ix+12),l
                ld      (ix+13),h           ; P = BASE + GAP2
sgs_outer:
                ; P < BASE + 2N ?  (P_end exclusive)
                ld      l,(ix+4)
                ld      h,(ix+5)
                add     hl,hl               ; 2N
                ld      e,(ix+6)
                ld      d,(ix+7)
                add     hl,de               ; HL = BASE + 2N = P_end
                ex      de,hl               ; DE = P_end
                ld      l,(ix+12)
                ld      h,(ix+13)           ; HL = P
                or      a
                sbc     hl,de               ; P - P_end
                jp      nc,sgs_shrink       ; P >= P_end -> this pass done
                ; TMP = word[P]
                ld      l,(ix+12)
                ld      h,(ix+13)
                ld      a,(hl)
                ld      (ix+18),a
                inc     hl
                ld      a,(hl)
                ld      (ix+19),a           ; TMP = descaddr at P
                ; Q = P
                ld      a,(ix+12)
                ld      (ix+14),a
                ld      a,(ix+13)
                ld      (ix+15),a           ; Q = P
sgs_inner:
                ; Qprev = Q - GAP2 ; if Qprev < BASE -> stop
                ld      l,(ix+14)
                ld      h,(ix+15)           ; Q
                ld      e,(ix+10)
                ld      d,(ix+11)           ; GAP2
                or      a
                sbc     hl,de               ; HL = Qprev
                ld      e,(ix+6)
                ld      d,(ix+7)            ; BASE
                push    hl                  ; guard Qprev
                or      a                   ; clear CF before the compare (A holds a
                                            ; frame byte; `or a` just forces CF=0)
                sbc     hl,de               ; Qprev - BASE
                pop     hl                  ; HL = Qprev
                jr      c,sgs_place         ; Qprev < BASE -> insertion point reached
                ; key(word[Qprev]) > key(TMP) ?  -> shift and continue
                ; keyprev = ptr(word[Qprev])
                push    hl                  ; guard Qprev
                ld      c,(hl)
                inc     hl
                ld      b,(hl)              ; BC = descaddr at Qprev
                call    sg_keyof            ; BC=descaddr -> DE = its ptr key
                ; keytmp = ptr(TMP)
                ld      c,(ix+18)
                ld      b,(ix+19)           ; BC = TMP descaddr
                push    de                  ; guard keyprev
                call    sg_keyof            ; -> DE = keytmp
                pop     bc                  ; BC = keyprev
                ; compare keyprev(BC) > keytmp(DE) ?  keytmp - keyprev < 0 (borrow)
                ld      a,e
                sub     c
                ld      a,d
                sbc     a,b                 ; CF set <=> keytmp < keyprev <=> keyprev > keytmp
                pop     hl                  ; HL = Qprev (POP keeps CF)
                jr      nc,sgs_place        ; keyprev <= keytmp -> insertion point
                ; shift: word[Q] = word[Qprev]
                ld      c,(hl)
                inc     hl
                ld      b,(hl)              ; BC = word[Qprev]
                ld      l,(ix+14)
                ld      h,(ix+15)           ; HL = Q
                ld      (hl),c
                inc     hl
                ld      (hl),b              ; word[Q] = word[Qprev]
                ; Q = Qprev
                ld      l,(ix+14)
                ld      h,(ix+15)
                ld      e,(ix+10)
                ld      d,(ix+11)
                or      a
                sbc     hl,de               ; Q -= GAP2
                ld      (ix+14),l
                ld      (ix+15),h
                jr      sgs_inner
sgs_place:
                ; word[Q] = TMP
                ld      l,(ix+14)
                ld      h,(ix+15)           ; Q
                ld      a,(ix+18)
                ld      (hl),a
                inc     hl
                ld      a,(ix+19)
                ld      (hl),a
                ; P += 2 ; next outer
                ld      l,(ix+12)
                ld      h,(ix+13)
                inc     hl
                inc     hl
                ld      (ix+12),l
                ld      (ix+13),h
                jp      sgs_outer
sgs_shrink:
                ; gap = (gap-1)/3 ; if gap==0 done
                ld      l,(ix+16)
                ld      h,(ix+17)           ; GAP
                dec     hl                  ; gap-1
                call    sg_divby3           ; HL = (gap-1)/3
                ld      a,h
                or      l
                ret     z                   ; gap 0 -> fully sorted
                jp      sgs_gaploop

; --- sg_keyof: BC = descriptor address -> DE = its ptr key (word at desc+1).
; Preserves BC,HL. Clobbers A? no — only DE.
sg_keyof:
                push    hl
                ld      h,b
                ld      l,c
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = ptr
                pop     hl
                ret

; --- sg_divby3: HL = HL / 3 (unsigned, remainder discarded). Shift-and- -----
; subtract restoring division. Clobbers A,B,DE... only A,B. Preserves DE.
sg_divby3:
                ld      a,0                 ; running remainder
                ld      b,16
sgd3_lp:
                add     hl,hl               ; dividend/quotient <<= 1, MSB -> CF
                rla                         ; rem = (rem<<1) | CF
                cp      3
                jr      c,sgd3_no
                sub     3
                inc     l                   ; quotient bit0 := 1 (bit0 just vacated)
sgd3_no:
                djnz    sgd3_lp
                ret

; --- str_body_copy: sub-side copy (aeng_copy_str's own use, sub/arrays.asm) -
; in: HL = source descriptor address (STABLE — a STRTAB slot / array element
; / temp-stack entry; NEVER a bare heap body address), DE = destination body
; address (already heap_alloc'd, big enough for the source's CURRENT
; length). Re-reads the source's length+ptr FRESH from (HL) at call time —
; the general "copy after an alloc that may have GC'd" pattern (spec
; §5.2(4)): a caller must re-derive the source through its STABLE descriptor
; address after any heap_alloc call, never cache a raw body pointer across
; one. Clobbers A,B,C,D,E,H,L.
str_body_copy:
                push    de
                ld      a,(hl)
                or      a
                jr      z,sbc_empty
                ld      c,a
                ld      b,0
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = source body (fresh)
                ex      de,hl               ; HL = source body; DE = junk (old desc+2)
                pop     de                  ; DE = dest body (restored)
                ldir
                ret
sbc_empty:
                pop     de
                ret

; --- sh_temp_push_alloc: A=length -> push a temp-descriptor-stack entry ----
; owning a fresh heap body of that length (the sub-side sibling of the main-
; ROM's str_temp_alloc, basic/str-engine.asm). out:
;   CF clear = temp-descriptor stack overflow (NO slot pushed; A=2).
;   CF set   = a slot WAS pushed (TEMPTOP advanced). B = error code
;              (0 ok / 1 heap OOM). HL = slot addr, DE = body-to-fill (0 iff
;              length 0 OR heap OOM). On success the slot is [len][body]; on
;              heap OOM it is left neutralised [0][0].
; S2 fix: the slot is initialised to [0][0] BEFORE heap_alloc runs, so if that
; alloc triggers GC, sg_walk_temps sees len=0 and correctly skips this slot
; (it would otherwise see len>0 + a STALE in-range ptr = phantom root ->
; double-move corruption). The real [len][body] is written only AFTER the
; alloc returns. S7 fix: callers read B (not the neutralised slot len) to
; detect OOM, so an OOM is never silently swallowed. Clobbers A,B,C,D,E,H,L.
sh_temp_push_alloc:
                push    af                  ; [len] guard the requested length
                ld      hl,(TEMPPT)         ; HL = the slot: the next free one
                push    hl                  ; [len][slot]
                ld      de,3
                add     hl,de               ; HL = the new TEMPPT
                push    hl                  ; [len][slot][new]
                ld      de,TEMPBASE+1
                or      a
                sbc     hl,de               ; new TEMPPT - (TEMPBASE+1)
                pop     de                  ; DE = new TEMPPT   [len][slot]
                pop     hl                  ; HL = slot         [len]
                jr      nc,stpa_overflow    ; new TEMPPT > TEMPBASE -> overflow
                ld      (TEMPPT),de         ; slot visible; HL = slot addr
                ; init the slot [0][0] so it is NOT a GC root during the alloc
                xor     a
                ld      (hl),a
                inc     hl
                ld      (hl),a
                inc     hl
                ld      (hl),a
                dec     hl
                dec     hl                  ; HL = slot addr
                pop     af                  ; A = length     [ ]
                or      a
                jr      z,stpa_len0         ; length 0 -> slot [0][0], DE=0, ok
                push    hl                  ; [slot] guard slot addr
                push    af                  ; [slot][len] guard length across heap_alloc
                call    heap_alloc          ; A=len -> CF+HL=body / CF clear=OOM
                jr      nc,stpa_oom
                ex      de,hl               ; DE = body
                pop     af                  ; A = length   [slot]
                pop     hl                  ; HL = slot     [ ]
                ld      (hl),a              ; slot.len = length
                inc     hl
                ld      (hl),e
                inc     hl
                ld      (hl),d              ; slot.ptr = body
                dec     hl
                dec     hl                  ; HL = slot addr
                ld      b,0                 ; err = 0 (ok)
                scf
                ret
stpa_len0:
                ld      de,0                ; body = 0
                ld      b,0                 ; err = 0 (an empty string is not an error)
                scf
                ret
stpa_oom:
                pop     af                  ; discard [len]   [slot]
                pop     hl                  ; HL = slot addr  [ ]
                ld      de,0                ; no body (slot already neutralised [0][0])
                ld      b,1                 ; err = 1 (heap OOM)
                scf                         ; a slot WAS obtained (empty)
                ret
stpa_overflow:
                pop     af                  ; discard [len]
                ld      a,2
                or      a                   ; CF clear -> no slot at all (A=2)
                ret

; --- sh_append: op=2 (APPEND) — the concat accumulator step. Append the ----
; string at SH_SRC (any stable descriptor: temp / var slot / RVDESC) onto the
; accumulator temp at SH_DEST (a temp slot, IN PLACE). SH_DEST's slot
; stays put; only its len/ptr change (its old body becomes GC garbage). This
; per-operand binary append (vs the old "build from the last B contiguous
; temps") is robust to operands whose OWN evaluation pushes intermediate
; temps -- e.g. "A"+MID$("XY"+"Z",1,2)+"B" (the STRCAT_R nesting case): each
; operand is fully evaluated and appended before the next, so no contiguity
; assumption is needed. SH_ERR: 0 ok / 1 heap OOM (SH_DEST left unchanged,
; still valid) / 2 temp-stack overflow (only if a fresh body alloc needs a
; slot -- it does not here, so 2 never occurs) / 3 combined length > STRMAX.
; Clobbers A,B,C,D,E,H,L.
;
; 🔴 SH_ERR=3 REPLACES A CLAMP, AND THE CLAMP'S COMMENT WAS FALSE (D-STRLONG,
; docs/spec-basic-strlong.md). Until 2026-08-28 an over-STRMAX total was set to
; 255 and RETURNED, and the line above said that was "reference left-to-right
; truncation". It is not: `X$=STRING$(200,"A") : PRINT LEN(X$+X$+X$)` is
; `String too long` on BOTH the VG-8020 and the CF-3300, and 255 here -- a
; SILENT WRONG ANSWER, which this project ranks below the refusal beside it.
; 🎯 THE TEST IS SITED BEFORE EVERY ALLOCATION on purpose. `add a,c` is the
; first thing sh_append does, so the raise costs no pool and leaves R valid,
; which is what lets a small pool report the LENGTH error rather than the
; out-of-space error it used to reach first (the sweep in the spec, §4).
sh_append:
                ld      hl,(SH_DEST)
                ld      a,(hl)              ; lenR
                ld      c,a                 ; C = lenR
                ld      hl,(SH_SRC)
                ld      a,(hl)              ; lenTk
                add     a,c                 ; total = lenR + lenTk
                jr      c,sap_toolong       ; D-STRLONG: over STRMAX -> ERR 15, and
                                            ; NOTHING has been touched yet -- R, the
                                            ; heap and FRETOP are all still intact
sap_ok:
                or      a
                jr      z,sap_empty         ; total 0 -> R becomes empty
                call    sap_try_extend      ; D-CONCATPEAK: grow R in place if it is
                jr      c,sap_release       ; the TOP body -- A/C restored if it is not
                push    af                  ; [total] guard
                call    heap_alloc          ; A=total -> CF+HL=newbody / CF clear=OOM.
                                            ; May GC; R and Tk are re-read fresh below
                                            ; (their ptrs are updated if GC moved them).
                jr      nc,sap_oom
                pop     af                  ; A = total (= ROOM)
                push    hl                  ; [newbody] guard
                push    af                  ; [newbody][total]
                ld      c,a                 ; C = ROOM remaining
                ex      de,hl               ; DE = newbody (dest cursor)
                ld      hl,(SH_DEST)        ; R descriptor
                call    sap_copy_clamped    ; copy min(lenR,ROOM) of R's body; DE+=,C-=
                ld      hl,(SH_SRC)         ; Tk descriptor
                call    sap_copy_clamped    ; copy min(lenTk,remaining) of Tk's body
                pop     af                  ; A = total     [newbody]
                pop     de                  ; DE = newbody  [ ]
                ld      hl,(SH_DEST)
                ld      (hl),a              ; R.len = total
                inc     hl
                ld      (hl),e
                inc     hl
                ld      (hl),d              ; R.ptr = newbody (old R body -> garbage)
                xor     a
                ld      (SH_ERR),a
                jr      sap_release
sap_empty:
                ld      hl,(SH_DEST)
                xor     a
                ld      (hl),a              ; R.len = 0
                inc     hl
                ld      (hl),a
                inc     hl
                ld      (hl),a              ; R.ptr = 0
                ld      (SH_ERR),a
                ; fall through
; --- sap_release (D-TEMPPOL, 2026-09-25): the operand is CONSUMED -----------
; Once Tk's bytes are in R, a Tk that is the NEWEST temp-stack entry is popped,
; as the reference frees a consumed temporary. Without it every function
; operand of a flat chain kept its descriptor to the end of the statement:
; `MID$(A$,1)+MID$(A$,1)+...` ran out at 11 terms on the 10-entry pool where
; the VG-8020 takes 14 (scratchpad/tempst_probe.py). A Tk that is a variable,
; a literal or an OLDER temp is left alone -- only the top entry can be popped
; without disturbing a live one. SH_ERR is already 0 on every path here.
sap_release:
                ld      hl,(SH_SRC)
                ; fall through
; --- sh_pop_top (D-TEMPPOL part 2): HL = a descriptor; pop it iff it is the ---
; NEWEST temp-stack entry. The one rule every consumer below uses: only the top
; entry can be released without disturbing a live one, and a variable, literal
; or older temp is left alone. Clobbers A, D, E, H, L.
sh_pop_top:
                ld      de,(TEMPPT)
                dec     de
                dec     de
                dec     de                  ; DE = the newest entry (TEMPPT-3)
                or      a
                sbc     hl,de
                ret     nz                  ; not the newest entry -> keep it
                ld      (TEMPPT),de         ; pop: its body is garbage now
                ret
sap_oom:
                pop     af                  ; discard [total]
                ld      a,1
                ld      (SH_ERR),a          ; heap OOM -- R left unchanged (valid)
                ret
sap_toolong:
                ld      a,3
                ld      (SH_ERR),a          ; D-STRLONG: combined length > STRMAX.
                                            ; R is unchanged and still valid; main's
                                            ; sct_append_err maps 3 -> FPERR_STRLONG.
                ret
; --- sap_try_extend (D-CONCATPEAK, docs/spec-concatpeak.md): grow R's body ---
; IN PLACE when R is the TOP heap allocation.
;
; The heap grows DOWNWARD from FRETOP (heap_alloc: `candidate = FRETOP - LEN`,
; then `ld (FRETOP),hl`), so the MOST RECENT body sits exactly AT FRETOP -- and
; in `A$ + B$` that body is the operand-1 snapshot str_concat_tail made one step
; earlier. Extending it costs only the `ext` new bytes instead of a fresh
; lenR+lenTk body allocated WHILE THE OLD ONE IS STILL LIVE, which is what made
; the transient peak `4L+4` where both references cope at `3L+4`:
;
;     old:  held + R(L) + new(2L)  = 4L + held      `CLEAR 70`, L=20 -> OOM
;     new:  held + R(L) +   ext(L) = 3L + held      -> fits
;
; 🎯 IT ALSO LEAVES NO GARBAGE. The realloc path abandons R's old L bytes; here
; the new body [F-ext, F+lenR) COVERS the old one exactly, so nothing is dropped
; for the GC to reclaim later.
;
; ⚠️ WHY THE DOWNWARD MOVE IS SAFE, AND WHY Tk CANNOT BE CLOBBERED. R's bytes
; move from [F, F+lenR) to [F-ext, F-ext+lenR) -- dest < src, so a FORWARD `ldir`
; is correct even though the ranges overlap. Tk is then written to
; [F-ext+lenR, F+lenR). Every heap body lies at >= FRETOP = F, and Tk cannot lie
; inside R's own old range, so Tk's body is at >= F+lenR -- at or above the top of
; the write range, never inside it. A literal or STRSCR source is not in the heap
; at all and sits below the pool floor.
;
;   in:  A = total (already clamped to STRMAX), C = lenR,
;        SH_DEST = R's descriptor, SH_SRC = Tk's descriptor
;   out: CF set   = done. R.len/R.ptr updated, FRETOP lowered, SH_ERR = 0.
;        CF clear = not applicable (R has no body, or is not the top allocation,
;                   or the extension would cross the pool floor). A AND C ARE
;                   RESTORED so the caller's realloc path runs unchanged -- an
;                   early exit that ate `total` would corrupt the fallback.
; Clobbers B,D,E,H,L (and A/C only on the CF-set path).
sap_try_extend:
                ld      b,a                 ; B = total (A restored at every no-exit)
                ld      a,c
                or      a
                jr      z,sate_no           ; R has no body to extend
                ld      hl,(SH_DEST)
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = R.ptr
                ld      hl,(FRETOP)
                or      a
                sbc     hl,de
                jr      nz,sate_no          ; R is not the top allocation
                ld      a,b
                sub     c                   ; A = ext = total - lenR
                jr      z,sate_len_only     ; the clamp swallowed all of Tk
                ld      e,a
                ld      d,0                 ; DE = ext
                ld      hl,(FRETOP)
                or      a
                sbc     hl,de               ; HL = newstart
                ; 🔴 strheap_floor's OWN HEADER SAYS "Clobbers A,B,C,D,E,H,L" --
                ; strheap_ceiling inside it does `ld bc,TXTMAX`. The first cut of
                ; this routine held `total` in B and `lenR` in C across that call
                ; and the ldir below then ran with a GARBAGE length: every
                ; concatenation in the language died. Guard them.
                ; [[a-scratch-register-that-was-the-callers-value]]
                push    bc                  ; [total|lenR]
                push    hl                  ; [total|lenR][newstart]
    IF CLEARPOOL
                call    strheap_floor       ; the SAME floor heap_alloc honours
    ELSE
                call    strheap_aryend
                inc     hl
                inc     hl                  ; body must start ABOVE the sentinel
    ENDIF
                ex      de,hl               ; DE = floor
                pop     hl                  ; HL = newstart          [total|lenR]
                push    hl
                or      a
                sbc     hl,de
                pop     hl                  ; HL = newstart (flags kept)
                pop     bc                  ; B = total, C = lenR -- `pop rr` does
                                            ; NOT touch flags, so CF above survives
                jr      nc,sate_fits
sate_no:
                ld      a,b                 ; restore total for the realloc path
                or      a                   ; CF clear
                ret
sate_fits:
                ld      (FRETOP),hl         ; the body starts here now
                ld      d,h
                ld      e,l                 ; DE = dest cursor
                push    bc                  ; [total|lenR]
                ld      hl,(SH_DEST)
                inc     hl
                ld      a,(hl)
                inc     hl
                ld      h,(hl)
                ld      l,a                 ; HL = R's OLD body (the old FRETOP)
                ld      b,0                 ; BC = lenR
                ldir                        ; move R down; DE = newstart + lenR
                pop     bc                  ; B = total, C = lenR
                push    bc                  ; [total|lenR]
                ld      a,b
                sub     c
                ld      c,a
                ld      b,0                 ; BC = ext (what is left for Tk)
                ld      hl,(SH_SRC)
                inc     hl
                ld      a,(hl)
                inc     hl
                ld      h,(hl)
                ld      l,a                 ; HL = Tk's body
                ldir                        ; append Tk's first `ext` bytes
                pop     bc                  ; B = total
sate_write:
                ld      hl,(SH_DEST)
                ld      (hl),b              ; R.len = total
                inc     hl
                ld      de,(FRETOP)
                ld      (hl),e
                inc     hl
                ld      (hl),d              ; R.ptr = FRETOP
                xor     a
                ld      (SH_ERR),a
                scf                         ; handled
                ret
sate_len_only:
                ; total == lenR: R keeps its body, only the length changes.
                jr      sate_write

; sap_copy_clamped: HL=source descriptor, DE=dest body cursor, C=room remaining.
; Copies min(source_len, C) bytes of the source's CURRENT body to (DE);
; advances DE past them and reduces C by the count. Source len+ptr re-read
; fresh (post-GC-safe). Clobbers A,B,HL.
sap_copy_clamped:
                ld      a,(hl)              ; source len
                cp      c
                jr      c,sacc_have         ; len < room -> copy len
                ld      a,c                 ; else copy room
sacc_have:
                or      a
                ret     z                   ; nothing to copy
                ld      b,a                 ; B = count
                ld      a,c
                sub     b
                ld      c,a                 ; ROOM -= count
                inc     hl
                ld      a,(hl)              ; ptr-lo
                inc     hl
                ld      h,(hl)              ; ptr-hi
                ld      l,a                 ; HL = source body
sacc_lp:
                ld      a,(hl)
                ld      (de),a
                inc     hl
                inc     de
                djnz    sacc_lp
                ret

; --- sh_hex_build / sh_oct_build: op=6/7 handlers (shape-C follow-up move ---
; of str_fn_hex/str_fn_oct's digit-building bodies, basic/str-engine.asm —
; the main-ROM low region ran out of room for them). SH_NUM = n (unsigned
; 16-bit) -> push a temp-descriptor-stack entry holding n's hex/octal text
; (uppercase, no leading zeros, always >=1 digit — D-2: HEX$(0)="0"). Builds
; into NUMBUF (shared main-ROM scratch, dead here for the SAME reason the
; main-ROM str_fn_hex's own comment gave: this runs mid string-expression-
; eval, before any PRINT-item formatting of THIS item could touch it — a
; page-0 tenant sees the SAME RAM, page 2/3 always mapped) then commits via
; sh_temp_push_alloc. sh_hex_digit/sh_oct_digit are local clones of basic/
; list.asm's resident hex_digit/oct_digit (a RESIDENT leaf a page-0 tenant
; cannot call without resident-ABI plumbing; duplicating this 2-4-byte leaf
; is simpler — the established small-proven-idiom precedent, e.g. is_letter
; above). SH_ERR: 0 ok / 1 = heap OOM (can't practically happen for a <=6-
; byte alloc, but honoured regardless) / 2 = temp-descriptor stack full.
sh_hex_build:
                ld      de,(SH_NUM)
                ld      hl,NUMBUF
                ld      c,0                 ; C = digit count so far
                ld      b,0                 ; B = "a non-zero nibble seen" flag
                ld      a,d
                call    shx_nib_hi
                ld      a,d
                call    shx_nib_lo
                ld      a,e
                call    shx_nib_hi
                ld      a,e
                and     $0F                 ; the last nibble is always emitted
                call    sh_hex_digit
                ld      (hl),a
                inc     hl
                inc     c
                ld      a,c                 ; A = total digit count (1..4)
                push    af                  ; guard the count             [CNT]
                call    sh_temp_push_alloc  ; CF clear=overflow / CF set:B=err,DE=body
                jr      nc,shb_hex_full
                ld      (SH_PTR),hl
                ld      a,b
                ld      (SH_ERR),a          ; err (0 ok / 1 heap OOM) -- S7
                or      a
                jr      z,shb_hex_fill      ; ok -> fill (DE=body, count>=1)
                pop     af                  ; heap OOM -> discard [CNT], leave SH_ERR=1
                ret
shb_hex_fill:
                pop     af                  ; A = count                    [ ]
                ld      c,a
                ld      hl,NUMBUF
shb_hex_cp:
                ld      a,(hl)
                ld      (de),a
                inc     hl
                inc     de
                dec     c
                jr      nz,shb_hex_cp
                ret
shb_hex_full:
                pop     af                  ; discard [CNT]
                ld      a,2
                ld      (SH_ERR),a
                ret
shx_nib_hi:
                rrca
                rrca
                rrca
                rrca
shx_nib_lo:
                and     $0F
                jr      nz,shx_emit         ; non-zero nibble -> always emit
                ld      a,b
                or      a
                ret     z                   ; still in leading zeros -> skip
                xor     a                   ; a zero after a non-zero -> emit 0
shx_emit:
                ld      b,1                 ; mark: emit everything from now on
                call    sh_hex_digit
                ld      (hl),a
                inc     hl
                inc     c
                ret
sh_hex_digit:
                cp      10
                jr      c,shx_dec
                add     a,'A'-10
                ret
shx_dec:
                add     a,'0'
                ret

; --- sh_free_gap: op=15 handler, the FRE value (docs/spec-basic-binfre.md §4) -
; -> SH_PTR = the number of bytes still allocatable; SH_ERR = 0 always.
;
; ✅ D-CLP: the two pools are now REAL on this side too, so this is
; `FRETOP - strheap_floor()` -- the bytes still allocatable from the pool
; `CLEAR n` sized, which is what `FRE("")` means on the reference. Before the
; partition, zerobas had ONE free gap (heap_alloc's floor was ARYEND+2 and
; CLEAR's argument was discarded), so FRE(n) and FRE(s$) reported the SAME
; quantity -- D-BF-A(c), the six rows the BIN$/FRE slice recorded and could not
; gate. They gate now.
;
; The floor still comes from heap_alloc's OWN rule (strheap_floor, the same call
; the allocator makes) rather than a restatement of the layout, which is what
; keeps FRE from drifting away from what an allocation will actually accept --
; the same discipline the ARYEND+2 version had, pointed at the new boundary.
; Note there is no +2 any more: the pool OWNS its floor address (the old +2 was
; for the live 2-byte $0000 array sentinel the heap had to stay above), and
; `CLEAR 100` then a 100-byte string must read exactly 0.
sh_free_gap:
                ; FRE COMPACTS FIRST -- measured, not assumed: on the reference a
                ; string that has been dropped is fully recovered by the next
                ; FRE(s$). zerobas's heap is a bump allocator that only collects on
                ; a COLLISION (heap_alloc above), so FRETOP still counts every dead
                ; temp; `A$=STRING$(100,"A")` leaves 200 bytes of garbage behind the
                ; live body. Without this, FRE reports garbage as used and answers
                ; 306 where the allocator would happily hand back 106.
                call    strheap_gc
    IF CLEARPOOL
                call    strheap_floor       ; HL = the pool floor
    ELSE
                call    strheap_aryend      ; HL = ARYEND (the $0000 terminator)
                inc     hl
                inc     hl                  ; +2: heap_alloc's own floor
    ENDIF
                ex      de,hl
                ld      hl,(FRETOP)
                or      a
                sbc     hl,de               ; HL = FRETOP - floor
                jr      nc,sfg_have
                ld      hl,0                ; a full heap must read 0, never negative
sfg_have:
                ld      (SH_PTR),hl
                xor     a
                ld      (SH_ERR),a
                ret

    IF CLEARPOOL
; --- sh_free_vars: op=17 handler -- FRE(n), free VARIABLE space (D-CLP) -----
; -> SH_PTR = `floor - (ARYEND+2)`, the room the variable/array region still has
; before it reaches the string pool; SH_ERR = 0 always.
;
; sh_free_gap above answers the OTHER pool. Splitting them is the partition's
; most visible consequence for a user: before D-CLP zerobas had one free gap and
; FRE(0) and FRE("") reported the SAME number (D-BF-A(c)); now FRE(0) is what is
; left for variables and FRE("") is what is left of `CLEAR n`.
;
; ⚠️ NO GC HERE, deliberately, and that is not an oversight copied from
; sh_free_gap. GC compacts STRING BODIES; it cannot move ARYEND and it cannot
; move the floor, so it could not change this answer by a byte -- calling it
; would only make FRE(0) slow. sh_free_gap needs it because its answer is
; FRETOP, which garbage does move.
;
; The `+2` is heap_alloc's old sentinel rule, kept HERE where it still belongs:
; ARYEND addresses the LIVE 2-byte $0000 array terminator, so the first byte the
; region does not already own is ARYEND+2.
;
; ⚠️ D-FCH §3.2: the ceiling here is now strheap_varceil, NOT strheap_floor —
; the file-channel table sits between them, so `MAXFILES=n` shows up in FRE(0)
; and not in FRE(""), which is the measured reference split (characterization
; §2 vs §5). This is the routine that makes the ladder visible.
sh_free_vars:
                call    strheap_aryend      ; HL = ARYEND (the $0000 terminator)
                inc     hl
                inc     hl                  ; HL = ARYEND+2 (past the live sentinel)
                push    hl
                call    strheap_varceil     ; HL = the variable ceiling (clobbers D,E)
                pop     de                  ; DE = ARYEND+2
                or      a
                sbc     hl,de               ; HL = floor - (ARYEND+2)
                jr      nc,sfv_have
                ld      hl,0                ; region already at/over the floor -> 0
sfv_have:
                ld      (SH_PTR),hl
                xor     a
                ld      (SH_ERR),a
                ret

; --- sh_ctl_reset: op=20 -- (re)derive the CONTROL POOL's top and floor -----
; ⚠️ NO `IF CLEARPOOL` WRAPPER HERE: this sits INSIDE the block opened above for
; sh_free_vars/sh_chan_addr. A nested one closed the OUTER block early and the
; machine booted to a garbage screen -- pasmo assembles an unbalanced pair
; without complaint, so the only symptom was a dead ROM.
; D-CTLPOOL (docs/spec-basic-trapsvc.md §11-§16). CTLTOP := strheap_varceil();
; CSP := GSP := FSP := TSP := CTLTOP; CTLLIM := ARYEND+2. SH_ERR always 0.
;
; 🎯 CTLTOP IS `strheap_varceil()` AND THAT IS THE MEASURED REFERENCE STKTOP.
; §14 read the reference's published STKTOP and found it is
; `(ceiling - files) - string space` -- the same expression this file already
; computes for the channel table and the string pool. Nothing new is derived
; here; the control pool simply starts where the reference's stack starts.
;
; ⚠️ THIS IS THE ONLY POOL OPERATION THAT CROSSES A SLOT, and it is the only one
; that may: it needs `strheap_varceil` (POOLSIZE/HIMEM/MAXF) and `strheap_aryend`
; (an array-chain walk), both sub-ROM knowledge, and it runs from clear_vars --
; cold boot, RUN, NEW and CLEAR. The PUSH and POP paths are main-ROM and touch
; nothing but RAM: `FOR I=1 TO 1000:GOSUB 100:NEXT` is a thousand pushes and a
; thousand pops, and a CALSLT on either would land on the hot path
; docs/spec-basic-interpspeed.md measures.
; Clobbers everything (tenant convention).
sh_ctl_reset:
                ; D-FNPOOL: no FN call is live across a NEW / RUN / CLEAR, and FNSP
                ; is power-on garbage until something writes it -- `sg_walk_fnframe`
                ; WALKS that chain now, so an unzeroed cell is a wild read on the
                ; first GC of a fresh machine (measured: the nested-FN row went from
                ; a wrong answer to a dead machine, while the same nesting without a
                ; collection stayed correct). It is zeroed HERE rather than in
                ; clear_vars because main page 1 had five bytes and this needs six.
                ld      hl,0
                ld      (FNSP),hl
                call    strheap_varceil     ; HL = the pool top (= reference STKTOP)
                ld      (CTLTOP),hl
                ld      (CSP),hl
                ld      (GSP),hl
                ld      (FSP),hl
                ld      (TSP),hl
                ld      (SH_PTR),hl
                call    strheap_ctllim      ; CTLLIM := ARYEND+2 (and STREND)
                xor     a
                ld      (SH_ERR),a
                ret

; --- sh_chan_addr: op=18 handler -- the DYNAMIC file-channel block address ---
; SH_LEN = channel 1..MAXF -> SH_PTR = strheap_varceil() + (ch-1)*FCH_CTXSZ,
; i.e. the base of that channel's context block inside the carved table.
; SH_ERR = 0 always (the caller has already range-checked the channel through
; fch_valid; an out-of-range one would simply address past the table).
;
; This is the whole main-ROM-visible surface of §3.2: basic/files.asm's
; fch_ctx_addr used to be `ld hl,FCH_CTX` + a stride loop over a table at a
; FIXED address, and is now this call. Siting the arithmetic here rather than
; resident is the S-FCH-1 lesson applied a second time — its callee
; (strheap_varceil, via strheap_floor/strheap_ceiling) was already sub-ROM, so
; keeping the caller resident would have bought nothing and cost real bytes.
sh_chan_addr:
                call    strheap_chantab     ; HL = the table base -- NOT varceil, whose
                                            ; CSP clamp moved it onto the control
                                            ; frames (D-CHANSWITCH)
                ; D-FCBSHAPE FCB #0 + geometry (2026-10-10): the reference's order,
                ; bottom up -- FILTAB's pointer table (2 B a channel, #0 included),
                ; then FCB #0, #1 .. #MAXFILES -- so VARPTR(#n) moves 265 (not 267)
                ; a MAXFILES step and #0 is the lowest block (fcb0_run.out). The
                ; table's bytes stay reserved: nothing here writes FILTAB.
                ld      a,(MAXF)
                inc     a
                add     a,a                 ; the pointer table's size
                ld      e,a
                ld      d,0
                add     hl,de               ; HL = FCB #0
                ld      a,(SH_LEN)          ; A = channel number, 0..MAXFILES
                or      a
                jr      z,sca_have          ; channel 0 -> the first block
                ld      b,a
                ld      de,FCH_BLKSZ        ; D-FCBSHAPE S1: the 265 B stride; the
                                            ; 2 B a channel above the blocks are FILTAB's
sca_lp:
                add     hl,de
                djnz    sca_lp
sca_have:
                ld      (SH_PTR),hl
                xor     a
                ld      (SH_ERR),a
                ret
    ENDIF

; --- sh_bin_build: op=14 handler (docs/spec-basic-binfre.md §3.1) ------------
; SH_NUM = n (unsigned 16-bit) -> push a temp-descriptor-stack entry holding n's
; BINARY text: no leading zeros, always >=1 digit (BIN$(0)="0"), up to SIXTEEN.
;
; NO SCRATCH BUFFER, unlike its two siblings. sh_hex_build/sh_oct_build stage
; digits in NUMBUF, which is 8 bytes — ample for their 4- and 6-digit worst
; cases. BIN$ needs sixteen and does not fit, and enlarging NUMBUF is not free
; (the MID$ statement aliases it, basic/sysvars.inc). But the staging step was
; never load-bearing: sh_temp_push_alloc already takes the digit count in A, so
; COUNT the significant bits first, allocate exactly that many, then emit
; straight into the body MSB-first. The count loop leaves HL pre-shifted so the
; most significant 1 is in bit 15, which is also exactly what the emit loop
; wants — the two halves share the same normalisation for free.
;
; n=0 takes the count-1 path with HL=0, so the emit loop writes a single '0'
; and the >=1-digit rule needs no special case of its own.
; SH_ERR: 0 ok / 1 = heap OOM / 2 = temp-descriptor stack full.
sh_bin_build:
                ld      hl,(SH_NUM)
                ld      c,1                 ; BIN$(0) is one digit
                ld      a,h
                or      l
                jr      z,sbb_have
                ld      c,16
sbb_lead:
                bit     7,h                 ; normalise: shift until the top bit is
                jr      nz,sbb_have         ; the most significant 1, counting down
                add     hl,hl
                dec     c
                jr      sbb_lead
sbb_have:
                ld      a,c                 ; A = ndigits (1..16)
                push    bc                  ; guard the count             [CNT]
                push    hl                  ; guard the normalised value  [CNT][VAL]
                call    sh_temp_push_alloc  ; CF clear=overflow / CF set:B=err,DE=body
                jr      nc,sbb_full
                ld      (SH_PTR),hl
                ld      a,b
                ld      (SH_ERR),a          ; err (0 ok / 1 heap OOM) -- S7
                or      a
                jr      z,sbb_fill          ; ok -> fill (DE=body, count>=1)
                pop     hl                  ; heap OOM -> discard the guards,
                pop     bc                  ; leave SH_ERR=1
                ret
sbb_fill:
                pop     hl                  ; HL = normalised value       [CNT]
                pop     bc                  ; C  = ndigits                [ ]
sbb_lp:
                ld      a,'0'
                bit     7,h
                jr      z,sbb_emit
                inc     a                   ; '1'
sbb_emit:
                ld      (de),a
                inc     de
                add     hl,hl
                dec     c
                jr      nz,sbb_lp
                ret
sbb_full:
                pop     hl                  ; discard [VAL]
                pop     bc                  ; discard [CNT]
                ld      a,2
                ld      (SH_ERR),a
                ret

sh_oct_build:
                ld      de,(SH_NUM)
                ld      hl,NUMBUF
                ld      b,0                 ; leading-zero suppression flag
                ld      a,d                 ; digit 0 = bit 15
                rlca
                ld      a,0
                rla
                call    sho_digit_susp
                sla     e
                rl      d
                ld      c,5                 ; five remaining 3-bit groups
sho_lp:
                call    sho_shift3
                dec     c
                jr      z,sho_last
                call    sho_digit_susp
                jr      sho_lp
sho_last:
                call    sh_oct_digit
                ld      (hl),a
                inc     hl                  ; HL = end (NUMBUF + ndigits)
                ld      de,NUMBUF
                or      a
                sbc     hl,de               ; HL = ndigits (1..6; H=0)
                ld      a,l
                push    af                  ; guard ndigits               [CNT]
                call    sh_temp_push_alloc  ; CF clear=overflow / CF set:B=err,DE=body
                jr      nc,shb_oct_full
                ld      (SH_PTR),hl
                ld      a,b
                ld      (SH_ERR),a          ; err (0 ok / 1 heap OOM) -- S7
                or      a
                jr      z,shb_oct_fill      ; ok -> fill
                pop     af                  ; heap OOM -> discard [CNT], leave SH_ERR=1
                ret
shb_oct_fill:
                pop     af                  ; A = ndigits                  [ ]
                ld      c,a
                ld      hl,NUMBUF
shb_oct_cp:
                ld      a,(hl)
                ld      (de),a
                inc     hl
                inc     de
                dec     c
                jr      nz,shb_oct_cp
                ret
shb_oct_full:
                pop     af                  ; discard [CNT]
                ld      a,2
                ld      (SH_ERR),a
                ret
; emit octal digit in A unless it is a leading zero (B tracks "seen non-zero").
sho_digit_susp:
                or      a
                jr      nz,sho_set
                ld      a,b
                or      a
                ret     z                   ; leading zero -> skip
                xor     a                   ; non-leading zero -> emit '0'
sho_set:
                ld      b,1
                call    sh_oct_digit
                ld      (hl),a
                inc     hl
                ret
; sho_shift3: shift DE left 3 bits, return the 3 bits that fell off the top in A.
sho_shift3:
                ld      a,0
                sla     e
                rl      d
                rla
                sla     e
                rl      d
                rla
                sla     e
                rl      d
                rla
                and     7
                ret
sh_oct_digit:
                add     a,'0'
                ret

; --- sh_fill: op=8 handler (shape-C follow-up move of SPACE$/STRING$/CHR$'s
; shared "push a temp of SH_LEN bytes, each = SH_FILLBYTE" tail,
; basic/str-engine.asm — the main-ROM low region ran out of room). out:
; SH_PTR = the new temp descriptor. SH_ERR as the other ops (0/1/2).
; Clobbers A, B, C, D, E, H, L.
sh_fill:
                ld      a,(SH_LEN)
                call    sh_temp_push_alloc  ; CF clear=overflow / CF set:B=err,DE=body
                jr      nc,shf_full
                ld      (SH_PTR),hl
                ld      a,b
                ld      (SH_ERR),a          ; err (0 ok / 1 heap OOM) -- S7
                or      a
                ret     nz                  ; heap OOM -> no body to fill (DE=0)
                ld      a,d
                or      e
                ret     z                   ; length 0 -> nothing to fill
shf_fill:
                ld      a,(SH_LEN)
                ld      b,a                 ; B = fill count
                ld      a,(SH_FILLBYTE)
shf_lp:
                ld      (de),a
                inc     de
                djnz    shf_lp
                ret
shf_full:
                ld      a,2
                ld      (SH_ERR),a
                ret

; --- sh_mid_store: op=9 handler (shape-C follow-up move of the MID$ ---------
; STATEMENT's range-check + avail/cap arithmetic + byte-overwrite,
; basic/str-engine.asm ex_mid_stmt — pure memory/arithmetic work once n/m
; are already parsed (via `eval`, main-side); the main-ROM low region ran
; out of room for it. SH_SRC = B$ (RHS) descriptor address, SH_DEST = A$
; (target) descriptor address, SH_START = n (1-based position, full 16-bit
; — aliases SH_COUNT for its high byte, see sysvars.inc), SH_NUM = m (cap
; request, $00FF if omitted). Validates 1<=n<=La (La read from SH_DEST);
; SH_ERR=3 on failure (the caller maps this to stmt_error's "syntax error",
; D-3), else derives avail=La-n+1, cap=min(avail,m), k=min(cap,Lb), and
; overwrites k bytes of A$'s body starting at body+(n-1) with B$'s current
; bytes. LEN(A$) never changes. Clobbers A, B, C, D, E, H, L.
sh_mid_store:
                ld      bc,(SH_START)       ; BC = n (16-bit; C=lo,B=hi via
                                            ; the SH_START/SH_COUNT alias)
                ld      a,b
                or      a
                jr      nz,smd_range        ; n > 255 -> error
                ld      a,c
                or      a
                jr      z,smd_range         ; n == 0 -> error
                ld      hl,(SH_DEST)        ; HL -> A$ descriptor
                ld      a,(hl)              ; A = La
                cp      c
                jr      c,smd_range         ; La < n -> error
                sub     c                   ; A = La - n
                inc     a                   ; A = avail = La-n+1 (1..La)
                ld      b,a                 ; B = avail
                ld      de,(SH_NUM)         ; DE = m
                ld      a,d
                or      a
                jr      nz,smd_cap_avail    ; m >= 256 -> cap = avail
                ld      a,b
                cp      e                   ; avail - m
                jr      c,smd_cap_avail     ; avail < m -> cap = avail
                ld      a,e                 ; cap = m
                jr      smd_have_cap
smd_cap_avail:
                ld      a,b                 ; cap = avail
smd_have_cap:
                ; k = min(cap, Lb). cap in A, Lb = (SH_SRC).
                ld      b,a                 ; B = cap
                ld      hl,(SH_SRC)         ; HL -> B$ descriptor
                ld      a,(hl)              ; A = Lb
                cp      b
                jr      nc,smd_k            ; Lb >= cap -> k = cap (B unchanged)
                ld      b,a                 ; k = Lb
smd_k:
                ld      a,b
                or      a
                jr      z,smd_done          ; k == 0 -> nothing to copy
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = B$ body (source)
                push    de                  ; guard source                 [SRC]
                push    bc                  ; guard k (B)                  [SRC][K]
                ld      hl,(SH_DEST)        ; HL = A$ descriptor address
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = A$ body (dest base)
                pop     bc                  ; BC restored: B=k             [SRC]
                ld      hl,(SH_START)       ; n (1-based; write_ptr =
                                            ; body+(n-1)); high byte (garbage
                                            ; here, aliases the now-dead cap
                                            ; slot) is not used below
                ld      a,l
                dec     a
                add     a,e
                ld      e,a
                jr      nc,smd_nocarry
                inc     d
smd_nocarry:
                pop     hl                  ; HL = B$ body (source)          [ ]
                ld      c,b
                ld      b,0                 ; BC = k
                ldir                        ; overwrite k bytes of A$ with
                                            ; B$'s bytes
smd_done:
                xor     a
                ld      (SH_ERR),a
                ret
smd_range:
                ld      a,3
                ld      (SH_ERR),a
                ret

; --- sh_cmp_bits: op=10 handler (shape-C follow-up move of str_cmp_bits, ---
; basic/str-engine.asm's UNSIGNED byte-by-byte string comparator — pure
; memory work, no `eval` dependency; the main-ROM low region ran out of room
; for it). in: HL = lhs descriptor, DE = rhs descriptor. out: A = 1 (lhs<rhs)
; / 2 (equal) / 4 (lhs>rhs) — the same 1/2/4 encoding the main-ROM's
; ev_rel_str intersects with its requested-bits mask. Compares corresponding
; bytes by raw unsigned value; at the first differing byte the smaller
; byte's string is less; if all shared bytes match, the SHORTER string is
; less; same length + all bytes equal -> equal. Clobbers A, B, C, D, E, H, L.
sh_cmp_bits:
                ld      a,(hl)              ; A = lhslen
                ld      b,a                 ; B = lhslen (temp, for the tie-break)
                ld      a,(de)              ; A = rhslen
                cp      b
                jr      z,scmp_tb_eq
                jr      c,scmp_tb_gt        ; rhslen < lhslen -> lhs > rhs
                ld      a,1                 ; rhslen > lhslen -> lhs < rhs
                jr      scmp_tb_push
scmp_tb_eq:
                ld      a,2
                jr      scmp_tb_push
scmp_tb_gt:
                ld      a,4
scmp_tb_push:
                push    af                  ; stash the tie-break bit
                ld      a,(de)              ; A = rhslen
                ld      c,a
                ld      b,0                 ; BC = rhslen
                ld      a,(hl)              ; A = lhslen
                cp      c
                jr      nc,scmp_minlen_c    ; lhslen >= rhslen -> min = rhslen(C)
                ld      c,a                 ; else min = lhslen
scmp_minlen_c:
                ; C = minlen. Resolve both bodies (dereference [len][ptr]).
                push    bc                  ; guard minlen                 [TB][MINLEN]
                inc     hl
                ld      a,(hl)              ; lhs ptr-lo
                push    af
                inc     hl
                ld      a,(hl)              ; lhs ptr-hi
                ld      h,a
                pop     af
                ld      l,a                 ; HL = lhs body
                push    hl                  ; guard it                     [TB][MINLEN][LBODY]
                inc     de
                ld      a,(de)              ; rhs ptr-lo
                push    af
                inc     de
                ld      a,(de)              ; rhs ptr-hi
                ld      d,a
                pop     af
                ld      e,a                 ; DE = rhs body
                pop     hl                  ; HL = lhs body                [TB][MINLEN]
                pop     bc                  ; BC = minlen (B=0,C=minlen)   [TB]
                ld      a,c
                or      a
                jr      z,scmp_tie          ; minlen 0 -> nothing to compare
scmp_loop:
                ld      a,(de)              ; A = rhsbyte
                cp      (hl)                ; vs lhsbyte (raw unsigned compare)
                jr      z,scmp_eqbyte
                jr      c,scmp_gt           ; rhsbyte < lhsbyte -> lhs > rhs
                jr      scmp_lt             ; rhsbyte > lhsbyte -> lhs < rhs
scmp_eqbyte:
                inc     hl
                inc     de
                dec     bc
                ld      a,b
                or      c
                jr      nz,scmp_loop
scmp_tie:
                pop     af                  ; A = the stashed tie-break bit
                ret
scmp_gt:
                pop     af
                ld      a,4
                ret
scmp_lt:
                pop     af
                ld      a,1
                ret

; --- sh_instr_search: op=11 handler (shape-C follow-up move of ------------
; instr_search, basic/str-engine.asm's INSTR search body — pure memory
; work once a$/b$/p are already parsed+snapshotted main-side; the main-ROM
; low region ran out of room for it). SH_SRC = a$ temp descriptor address,
; SH_DEST = b$ temp descriptor address, SH_P = p (already validated >=1
; main-side). out: SH_PTR = 1-based match position, or 0 if not found.
; Empty b$ (len_b=0): result = min(len_a+1, p). Otherwise: max_start =
; len_a-len_b+1 (<=0 -> no room -> 0); if p > max_start, no match; else try
; start = p..max_start, comparing len_b bytes each time. Clobbers A, B, C,
; D, E, H, L, IX, IY.
sh_instr_search:
                ld      ix,(SH_SRC)         ; IX = a$ descriptor
                ld      iy,(SH_DEST)        ; IY = b$ descriptor
                ld      bc,(SH_P)           ; BC = p
                ld      a,(ix+1)
                ld      (ISRCH_A),a
                ld      a,(ix+2)
                ld      (ISRCH_A+1),a       ; ISRCH_A = a$'s CURRENT body base
                ld      a,(iy+1)
                ld      (ISRCH_B),a
                ld      a,(iy+2)
                ld      (ISRCH_B+1),a       ; ISRCH_B = b$'s CURRENT body base
                ld      a,(iy+0)            ; A = len_b
                or      a
                jr      nz,sis_nonempty
                ; --- empty b$: result = min(len_a+1, p) ---
                ld      a,(ix+0)            ; len_a
                inc     a                   ; ceiling = len_a+1 (saturates at
                jr      nz,sis_ceil_ok      ; 255 if len_a was 255 -- see the
                ld      a,255               ; main-ROM's own former comment)
sis_ceil_ok:
                ; A = min(A, BC) inline (str_min_bc's own logic — a main-ROM
                ; resident leaf a page-0 tenant cannot call).
                inc     b
                dec     b
                jr      nz,sis_empty_result ; p >= 256 -> min is A (ceiling)
                cp      c
                jr      c,sis_empty_result  ; ceiling < p -> min is A
                ld      a,c                 ; else min is p
sis_empty_result:
                ld      l,a
                ld      h,0
                ld      (SH_PTR),hl
                ret
sis_nonempty:
                ld      a,(ix+0)            ; len_a
                sub     (iy+0)              ; A = len_a - len_b
                inc     a                   ; A = max_start
                jp      m,sis_zero          ; negative -> no room
                or      a
                jr      z,sis_zero          ; zero -> no room
                ld      d,a                 ; D = max_start
                ld      a,b
                or      a
                jr      nz,sis_zero         ; p >= 256 > max_start -> no match
                ld      a,c                 ; A = p
                cp      d
                jr      z,sis_outer         ; p == max_start
                jr      c,sis_outer         ; p < max_start
                jr      sis_zero            ; p > max_start
sis_outer:
                ld      c,a                 ; C = start (1-based)
                ld      hl,(ISRCH_A)
                ld      b,0
                add     hl,bc               ; HL = a$-body + start
                dec     hl                  ; HL = apos (S5: start is 1-based and
                                            ; ISRCH_A is the BODY base, so byte at
                                            ; position `start` is body+(start-1))
                ld      de,(ISRCH_B)        ; DE = b$-body = bpos
                ld      b,(iy+0)            ; B = len_b (inner-loop counter)
sis_cmp:
                ld      a,(de)
                cp      (hl)
                jr      nz,sis_next
                inc     hl
                inc     de
                djnz    sis_cmp
                ld      l,c                 ; full match -> result = start
                ld      h,0
                ld      (SH_PTR),hl
                ret
sis_next:
                ld      a,c                 ; A = start
                inc     a                   ; start++
                push    af
                ld      a,(ix+0)
                sub     (iy+0)
                inc     a                   ; A = max_start (recomputed)
                ld      d,a
                pop     af                  ; A = start (restored)
                cp      d
                jr      z,sis_outer
                jr      c,sis_outer
sis_zero:
                ld      hl,0
                ld      (SH_PTR),hl
                ret

; --- sh_var_store: op=12 handler (shape-C follow-up move of str_set_key's --
; ssk_store, basic/vars.asm — the LET-into-a-`$`-var store; page 1 ran out
; of room for it). SH_SRC = source descriptor address (STABLE), SH_DEST =
; the destination STRTAB slot's [len][ptr] field address. heap_alloc(source
; length) + copy + write, exactly like aeng_copy_str (sub/arrays.asm) for
; the array-element case — value-copy semantics (a fresh body per store, no
; aliasing). SH_ERR: 0 ok / 1 Out of memory. Clobbers A, B, C, D, E, H, L.
sh_var_store:
    IF CLEARPOOL
                ; --- D-CLP: ADOPT a temp's body instead of copying it -------
                ; A temp-descriptor-stack entry uniquely owns its body and is
                ; discarded at the statement boundary, so allocating a second
                ; body and copying into it charges the pool TWICE for one
                ; string. The reference charges once -- measured: `CLEAR 100 :
                ; A$=STRING$(100,"A")` is ACCEPTED there and leaves FRE("") at
                ; exactly 0 (characterization §2.6, the oos-exact row). This is
                ; the last of the three charges that made zerobas's peak 3x.
                ;
                ; Value-copy semantics are preserved, not weakened: the body had
                ; exactly ONE owner before (the temp) and has exactly one after
                ; (the variable). The temp's descriptor is then ZEROED so it
                ; stops being a GC root -- without that, one body would have two
                ; roots and the compaction sweep would relocate it twice.
                ; A non-temp source (a var slot, an array element, RVDESC) still
                ; takes the copy path below: those are not ours to take.
                call    sh_src_is_temp
                jr      nc,svs_copy
                ld      hl,(SH_SRC)
                ld      de,(SH_DEST)
                ld      bc,3
                ldir                        ; dest := [len][ptr] verbatim
                ld      hl,(SH_SRC)
                ld      (hl),0              ; temp.len = 0
                inc     hl
                ld      (hl),0
                inc     hl
                ld      (hl),0              ; temp.ptr = 0 -> no longer a root
                xor     a
                ld      (SH_ERR),a
                ret
svs_copy:
    ENDIF
                ld      hl,(SH_SRC)
                ld      a,(hl)              ; source length
                call    heap_alloc          ; -> CF+HL=new body / CF clear=OOM
                jr      nc,svs_oom
                push    hl                  ; guard new body ptr            [BODY]
                ld      hl,(SH_SRC)         ; re-fetch source desc (stable addr)
                pop     de                  ; DE = new body ptr               [ ]
                push    de                  ; re-guard it                     [BODY]
                call    str_body_copy       ; HL=source(desc), DE=body -> copies
                                            ; the source's CURRENT length fresh
                ld      hl,(SH_SRC)
                ld      a,(hl)              ; length (re-read; unchanged)
                ld      hl,(SH_DEST)
                ld      (hl),a              ; dest.len
                inc     hl
                pop     de                  ; DE = body ptr (guarded above)    [ ]
                ld      (hl),e
                inc     hl
                ld      (hl),d              ; dest.ptr := the new heap body
                xor     a
                ld      (SH_ERR),a
                ret
svs_oom:
                ld      a,1
                ld      (SH_ERR),a
                ret

; --- sh_val_parse: op=13 handler (shape-C follow-up move of VAL's integer ---
; parser, basic/str-engine.asm's str_val_parse — pure-RAM parse of the string
; at (STRPTR); page-1/low both byte-full). Parses the leading number of
; (STRPTR)'s body: an integer -> SH_PTR (0 if no digits), anything else through
; tk_float (D-VALFLOAT), and `&H`/`&O`/`&B` literals (D-VALBASE), which can set
; SH_ERR. Clobbers A,B,C,D,E,H,L.
; --- sh_val_scr: op=19 (D-INPNUM) -- the same parse over STRSCR's field ------
; INPUT's numeric targets (console and INPUT #) read the typed / file field into
; STRSCR = [len][bytes] and need VAL's reading of it: every form 1985 listings
; type -- fractions, exponents, `&H`, a type suffix, blanks inside the number --
; is already right in sh_val_parse / tk_float (rule 3: no second parser). The
; field is not a string DESCRIPTOR, so this entry decodes [len][bytes] itself and
; joins the body below. SH_SRC then says where the number ended, for the
; console's strictness test (`1-2` and `&H1G` are ?Redo on the VG-8020;
; scratchpad/inpnum_run2.out).
sh_val_scr:
                xor     a
                ld      (SH_LEN),a
                ld      hl,STRSCR
                ld      b,(hl)              ; B = the field's length
                inc     hl                  ; HL = its first byte
                jr      svp_body

sh_val_parse:
                xor     a
                ld      (SH_LEN),a          ; 0 = "the answer is the integer in
                                            ; SH_PTR"; every early exit below
                                            ; (empty, bare sign, base literal)
                                            ; inherits it, and only the float
                                            ; decode overwrites it
                ld      hl,(STRPTR)
                ld      b,(hl)              ; B = byte count
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = ptr (body)
                ex      de,hl               ; HL = body cursor
svp_body:
                ; --- D-VALFLT: publish the body's END as tk_float's bound ------
                ; A string body is not 0-terminated, so the crunch would run off
                ; it. TKVALEND is a POSITION, not a counter, because tkf_fetch's
                ; callers REWIND across a blank run they decide not to consume
                ; (docs/spec-basic-valfloat.md §2). 0 means unbounded, and a heap
                ; body is never at address 0.
                push    hl
                ld      d,0
                ld      e,b
                add     hl,de
                ld      (TKVALEND),hl       ; one past the last body byte
                ld      (SH_SRC),hl         ; D-INPNUM: where the number ENDED --
                                            ; the end unless a scan below stops
                                            ; short (tk_float, a base literal)
                pop     hl
                ld      de,0                ; the "no number here" answer
                ld      c,e                 ; C bit0 = negative flag
svp_sp:
                ld      a,b
                or      a
                jp      z,svp_done          ; D-VALFLT put ~140 B between here and
                                            ; the tail; both empty-answer arms are
                                            ; `jp` for reach, not for style
                ld      a,(hl)
                cp      ' '
                jr      nz,svp_sign
                inc     hl
                dec     b
                jr      svp_sp              ; skip leading spaces
svp_sign:
                ; --- D-VALBASE: `&H` / `&O` / `&B` base literals -------------
                ; Measured on both references before a line was written:
                ;   &HFF &hff &HFFZZ "  &HFF" -> 255   (stop at the first invalid
                ;                                       digit; case-insensitive)
                ;   &O17 -> 15    &B101 -> 5
                ;   &HFFFF -> -1        (the accumulator is SIGNED int16)
                ;   &H1FFFF -> ERR 6    (overflow past 16 bits)
                ;   &H &HZZ &O9 &B2 -> 0 (a prefix with no valid digit is NOT an
                ;                         error, it is zero)
                ;   & and &17 -> ERR 2  ('&' not followed by H/O/B)
                ;   -&H10 -> 0          (a sign before a base literal does not
                ;                        apply -- and that falls out for free,
                ;                        because the '&' test is BEFORE the sign
                ;                        one, so a leading '-' consumes itself and
                ;                        the digit scan then meets '&' and stops)
                ; 🟢 The scan is LENGTH-BOUNDED by B, like the decimal path, so it
                ; cannot run off the end of a body that is not 0-terminated.
                cp      '&'
                jp      z,svp_base
                cp      '-'
                jr      nz,svp_plus
                ld      c,1                 ; negative
                inc     hl
                dec     b
                jr      svp_flt
svp_plus:
                cp      '+'
                jr      nz,svp_flt
                inc     hl
                dec     b
; --- D-VALFLT: the number itself is the TOKENISER'S scanner --------------------
; VAL's own parser read a leading signed DECIMAL INTEGER and stopped, so 16 rows
; of scratchpad/val_probe.py were wrong: every fraction, every exponent, every
; embedded blank, and every value past int16 (which wrapped, silently). All of
; that is already written, correct and oracle-pinned, in tk_float -- so VAL calls
; it rather than growing a second copy that would drift.
;
; 🟢 THE SCRATCH GOES ON THE STACK, where it cannot alias anything. The emitted
; token needs at most 9 bytes (DBL_TOKEN + 8), and three shared RAM buffers were
; examined and all three turned out to be owned (TOKBUF: direct-mode lines
; EXECUTE from it; DETOKBUF: PRINT USING drains it; FOUTBUF: four math-pack files
; write it). The question dissolves at SP: this scratch is written and read
; inside one call, tk_float's own pushes go BELOW SP, and an interrupt lands
; below them -- so nothing can reach it. Ten bytes of stack in a tenant is
; nothing. docs/spec-basic-valfloat.md §4a.
; ⚠️ AND IT IS DECODED BEFORE IT IS RELEASED. Once SP moves back up the bytes
; are above SP, where the next interrupt overwrites them.
svp_flt:
                ld      a,b
                or      a
                jp      z,svp_done          ; a bare sign, or nothing left -> 0
                xor     a
                ld      (TKOVF),a           ; the reject flag is ours to read: only
                                            ; `tokenise` clears it, and VAL does
                                            ; not go through tokenise
                push    bc                  ; the sign, across tk_float
                ex      de,hl               ; DE = source cursor
                ld      hl,-10
                add     hl,sp
                ld      sp,hl               ; 10 bytes of scratch AT SP
                ex      de,hl               ; HL = source cursor, DE = emit dest
                call    tk_float
                ld      (SH_SRC),hl         ; D-INPNUM: tk_float's stop (tkf_done
                                            ; hands the source cursor back in HL)
                ld      a,(TKOVF)
                or      a
                jr      nz,svp_frel         ; refused: NOTHING was emitted, so the
                                            ; scratch holds whatever was on the
                                            ; stack -- decoding it would read a
                                            ; float type out of garbage
                ld      hl,0
                add     hl,sp               ; HL -> the emitted token
                call    svp_token           ; -> DE = int16, or FAC/FACTYP/SH_LEN
svp_frel:
                ld      hl,10
                add     hl,sp
                ld      sp,hl               ; scratch released
                pop     bc                  ; C bit0 = negative
                ld      a,(TKOVF)
                or      a
                jp      nz,svp_bovf         ; `VAL("1E99")` -> Overflow on both
                                            ; references, the same ERR 6 the base
                                            ; literal's own overflow raises
                ld      a,(SH_LEN)
                or      a
                jr      z,svp_fin           ; an integer: the sign path below
                ; a float: the sign is a BIT, and value 0 is exempt -- the same
                ; rule as basic/float.asm's flt_neg, which cannot be called from
                ; here (main low region, invisible to a page-0 tenant).
                bit     0,c
                jr      z,svp_fok
                ld      a,(FAC)
                or      a
                jr      z,svp_fok
                xor     $80
                ld      (FAC),a
svp_fok:
                xor     a
                ld      (SH_ERR),a
                ret

; --- svp_token: decode the token tk_float emitted at (HL) -------------------
; out: SH_LEN = 0 and DE = the int16 value, or SH_LEN = FACTYP (4/8) with FAC
; holding the value bytes -- exactly the state basic/expr.asm's ev_f_float
; leaves, so the glue's flt_to_int16 finishes the job the same way.
; Clobbers A,B,C,D,E,H,L.
svp_token:
                ld      a,(hl)
                inc     hl
                cp      SNG_TOKEN
                jr      z,svp_t_sng
                cp      DBL_TOKEN
                jr      z,svp_t_dbl
                ld      de,0
                cp      INT2_TOKEN
                jr      z,svp_t_w
                cp      INT1_TOKEN
                jr      z,svp_t_b
                sub     INT_DIGIT_BASE      ; $11..$1A -> the value 0..9
                ld      e,a
                ret
svp_t_b:
                ld      e,(hl)              ; $0F,<byte>
                ret
svp_t_w:
                ld      e,(hl)              ; $1C,<word LE>
                inc     hl
                ld      d,(hl)
                ret
svp_t_dbl:
                ld      c,8
                jr      svp_t_f
svp_t_sng:
                ld      c,4
svp_t_f:
                ld      a,c
                ld      (SH_LEN),a          ; the marker IS the FACTYP value
                ld      (FACTYP),a
                ld      b,0
                ld      de,FAC
                ldir
                ret

svp_fin:
                bit     0,c
                jr      z,svp_done          ; non-negative -> DE is the value
                ld      hl,0
                or      a
                sbc     hl,de               ; HL = -DE
                ex      de,hl               ; DE = negated value
svp_done:
                ld      (SH_PTR),de
                xor     a
                ld      (SH_ERR),a
                ret

; --- D-VALBASE: the base-literal scan ---------------------------------------
; in:  HL = cursor ON the '&', B = bytes remaining.
; Registers are reassigned for this path: DE = cursor, HL = accumulator. That is
; the other way round from the decimal path above, and deliberately so -- the
; accumulate here is a SHIFT loop, and `add hl,hl` is the only 16-bit shift the
; Z80 has, so the accumulator has to be HL.
; C = (shift count << 4) | max digit value: hex $4F, octal $37, binary $11.
; Multiplying by a power of two means `acc = acc*base + digit` is a shift then an
; OR, because the digit is always < base.
svp_base:
                ex      de,hl               ; DE = cursor, HL = free
                ld      hl,0                ; HL = accumulator
                inc     de
                dec     b
                jr      z,svp_amperr        ; a bare '&' -> ERR 2
                ld      a,(de)
                and     $DF                 ; upcase (h/o/b); a digit becomes junk,
                                            ; which is what we want -- '&17' is an
                                            ; error, not octal
                ld      c,$4F               ; hex:    shift 4, max digit 15
                cp      'H'
                jr      z,svp_bpfx
                ld      c,$37               ; octal:  shift 3, max digit 7
                cp      'O'
                jr      z,svp_bpfx
                ld      c,$11               ; binary: shift 1, max digit 1
                cp      'B'
                jr      z,svp_bpfx
                ; ⚠️ EXPLICIT CODES, NOT AN OFFSET. The first draft wrote the
                ; MSX error numbers here and added 3 to reach the SH_ERR codes --
                ; which inverted them, so `VAL("&")` raised Overflow and
                ; `VAL("&H1FFFF")` raised Syntax error. Both rows were red in the
                ; obvious way and the cleverness bought nothing.
svp_amperr:
                ld      a,4                 ; SH_ERR 4 -> FPERR 4 -> ERR 2 (syntax)
                jr      svp_berr
svp_bovf:
                ld      a,5                 ; SH_ERR 5 -> FPERR 1 -> ERR 6 (overflow)
svp_berr:
                ld      (SH_ERR),a
                ld      de,0
                ld      (SH_PTR),de
                ret
svp_bpfx:
                inc     de
                dec     b
svp_bloop:
                ld      a,b
                or      a
                jr      z,svp_bfin
                ld      a,(de)
                cp      '0'
                jr      c,svp_bfin
                cp      '9'+1
                jr      c,svp_bdec
                and     $DF                 ; upcase a-f
                cp      'A'
                jr      c,svp_bfin
                cp      'F'+1
                jr      nc,svp_bfin
                sub     'A'-10              ; A = 10..15
                jr      svp_bval
svp_bdec:
                sub     '0'                 ; A = 0..9
svp_bval:
                ; A = digit value; B = bytes remaining, C = packed(shift<<4|max).
                ; 🔴 C MUST SURVIVE THE WHOLE LOOP -- an earlier draft used it as
                ; scratch for the max and then for the shift count, so the SECOND
                ; digit of `&HFF` was validated against the shift count instead of
                ; the max. Caught by tracing the register flow, not by a row.
                ; [[a-scratch-register-that-was-the-callers-value]]
                ; The count goes on the stack instead, which frees B to hold the
                ; digit across the shifts.
                push    bc                  ; [count|packed]
                ld      b,a                 ; B = digit
                ld      a,c
                and     $0F                 ; A = max digit for this base
                cp      b
                jr      c,svp_bpopfin       ; max < digit -> out of range: STOP, and
                                            ; that is a value, not an error (&O9 = 0)
                ld      a,c
                rrca
                rrca
                rrca
                rrca
                and     $0F
                ld      c,a                 ; C = shift count (packed is safe on the stack)
svp_bsh:
                add     hl,hl               ; acc <<= 1, watching for 16-bit overflow
                jr      c,svp_bovfpop
                dec     c
                jr      nz,svp_bsh
                ld      a,b                 ; A = digit
                or      l                   ; digit < base, so OR == ADD here
                ld      l,a
                pop     bc                  ; count|packed both restored
                inc     de
                dec     b
                jr      svp_bloop
svp_bovfpop:
                pop     bc
                jr      svp_bovf
svp_bpopfin:
                pop     bc
svp_bfin:
                ld      (SH_SRC),de         ; D-INPNUM: the base scan's stop (DE is
                                            ; its cursor on this path)
                ex      de,hl               ; DE = accumulator (the value)
                ld      (SH_PTR),de
                xor     a
                ld      (SH_ERR),a
                ret

