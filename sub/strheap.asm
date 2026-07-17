; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; sub/strheap.asm — the string HEAP engine (arrays slice-4a, the sub-ROM
; page-0 tenant half; docs/spec-basic-arrays-slice4a-string-heap.md §4/§5/§9).
;
; A compacting string heap sharing the low free RAM span with the array
; region (spec §2): arrays grow UP from ARYBASE (= (PRGEND)+2), the heap grows
; DOWN from the ceiling C = min(HIMEM,TXTMAX) via the sysvar FRETOP. The
; collision test is the single invariant ARYEND <= FRETOP, where ARYEND is the
; array region's own $0000 terminator address (derived by a stride-walk from
; ARYBASE, exactly like sub/arrays.asm's own aal_walk — never stored).
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

    IF ROM_BASE < $4000

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
                ret
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
                ld      hl,(SH_SRC)
                ld      a,(SH_COUNT)
                ld      (hl),a              ; temp.len := count
                or      a
                ret     z                   ; count 0 -> empty, done
                ld      a,(SH_START)
                or      a
                ret     z                   ; start 0 -> already at the front
                push    af                  ; guard start                    [START]
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = body (ptr field, fresh read)
                pop     af                  ; A = start                        [ ]
                push    de                  ; guard body (destination base)      [BODY]
                ld      h,d
                ld      l,e                 ; HL = body (copy)
                ld      c,a
                ld      b,0                 ; BC = start (zero-extended)
                add     hl,bc               ; HL = body+start = source
                pop     de                  ; DE = body = destination              [ ]
                ld      a,(SH_COUNT)
                ld      c,a
                ld      b,0                 ; BC = count
                ldir                        ; move count bytes forward; dst(body)
                                            ; < src(body+start) always when
                                            ; start>0, so a forward LDIR is safe
                ret

; --- heap_alloc: A=len(0..255) -> CF set+HL=body ptr / CF clear=OOM --------
; (spec §4). A bump allocator on the downward frontier FRETOP. On a collision
; with the array region (candidate < ARYEND) triggers GC once, then retries;
; a still-failing retry is a genuine OOM. Own scratch frame on the STACK
; (IY-addressed, 4 bytes: LEN(1)/ARYEND(2)/RETRIED(1) — the sub/arrays.asm
; convention, since no fixed RAM byte is spare here either). Clobbers
; A,B,C,D,E,H,L,IY.
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
                call    strheap_aryend      ; -> HL = ARYEND
                ld      (iy+1),l
                ld      (iy+2),h
ha_attempt:
                ld      hl,(FRETOP)
                ld      e,(iy+0)
                ld      d,0                 ; DE = LEN
                or      a
                sbc     hl,de               ; HL = candidate = FRETOP - LEN
                ld      e,(iy+1)
                ld      d,(iy+2)            ; DE = ARYEND
                inc     de
                inc     de                  ; DE = ARYEND+2 (S4: ARYEND is the address
                                            ; of the LIVE 2-byte $0000 array sentinel;
                                            ; the heap body must start ABOVE it)
                push    hl                  ; guard candidate
                or      a
                sbc     hl,de               ; HL = candidate - (ARYEND+2)
                pop     hl                  ; HL = candidate (restored)
                jr      nc,ha_ok            ; candidate >= ARYEND+2 -> fits
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
                ld      hl,(PRGEND)
                inc     hl
                inc     hl                  ; HL = ARYBASE
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
                ; --- Phase C: the sort buffer is DETOKBUF ($BE00), for n <= 256
                ; roots (2N <= 512 B). A larger live-root set can't fit -> fall
                ; back to gc_slow (in-place O(n^2), no buffer). Switch on N, not
                ; SP: no GC scratch on the hardware stack, ever (see the header's
                ; SORT-BUFFER HOME + DETOKBUF-IDLE AUDIT notes).
                ld      l,(ix+4)
                ld      h,(ix+5)
                ld      de,256
                or      a
                sbc     hl,de               ; N - 256
                jr      c,gc_detok          ; N < 256 -> DETOKBUF path
                jp      nz,gc_slow          ; N > 256 -> O(n^2) fallback
                                            ; (N == 256 exactly -> 2N=512, fits)
gc_detok:
                ld      hl,DETOKBUF
                ld      (ix+6),l
                ld      (ix+7),h            ; BASE = DETOKBUF (fixed page-2 buffer)
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

; --- gc_slow: O(n^2) selection compaction, NO buffer (the fallback for n > 256
; roots, which the 512-B DETOKBUF sort buffer cannot hold -- a big FILLED
; string array; exactly what real MSX's own collector always does). Repeatedly
; walk all roots (MODE=2) to find the highest-ptr not-yet-compacted body, move
; it up to DEST, repeat until none remain. Correct for arbitrary n; slower.
; Reuses sg_move_one for the move. BEST_PTR in frame +6 (BASE slot, unused in
; this path), BEST_DESC in +16 (GAP slot, unused) — both clear of the array-
; walk's own +12/+14 scratch. No buffer -> frees only the 22-B frame.
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
; on each (spec §5.2 root set: STRTAB slots, string-array elements, temp-
; descriptor-stack entries). PRESERVES IX (the strheap_gc frame); ary_stride
; preserves IX/IY/BC too. Clobbers A,B,C,D,E,H,L (+ sg_visit's).
sg_walk:
                call    sg_walk_strtab
                call    sg_walk_arrays
                ; fall through to sg_walk_temps
; temp-stack entries [TEMPTOP, TEMPBASE), stride 3.
sg_walk_temps:
                ld      hl,(TEMPTOP)
sgw_tm_lp:
                ld      de,TEMPBASE
                push    hl
                or      a
                sbc     hl,de               ; cursor - TEMPBASE
                pop     hl
                ret     nc                  ; cursor >= TEMPBASE -> done
                call    sg_visit            ; HL preserved by sg_visit
                ld      de,3
                add     hl,de
                jr      sgw_tm_lp
; STRTAB slots (stride STRENTSZ); descriptor = slot+2 (skip name0/name1).
sg_walk_strtab:
                ld      hl,STRTAB
sgw_st_lp:
                ld      a,h
                cp      high STREND
                jr      nz,sgw_st_t
                ld      a,l
                cp      low STREND
                ret     z
sgw_st_t:
                ld      a,(hl)              ; name0
                or      a
                jr      z,sgw_st_n          ; free slot -> skip
                push    hl
                inc     hl
                inc     hl                  ; -> descriptor (slot+2)
                call    sg_visit
                pop     hl
sgw_st_n:
                ld      de,STRENTSZ
                add     hl,de
                jr      sgw_st_lp
; string-array elements: every element (stride 3) of every type==1 array
; descriptor, from data_start (desc+6+2*ndim) to data_end (desc+stride). The
; per-array element cursor/end live in the enclosing frame's +12/+14 (free
; during the walk — they become the sort's P/Q afterward).
sg_walk_arrays:
                ld      hl,(PRGEND)
                inc     hl
                inc     hl                  ; HL = ARYBASE
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
                ld      hl,(TEMPTOP)
                ld      de,3
                or      a
                sbc     hl,de
                ld      de,TEMPPOOL
                push    hl
                or      a
                sbc     hl,de
                pop     hl
                jr      c,stpa_overflow     ; new TEMPTOP < TEMPPOOL -> overflow
                ld      (TEMPTOP),hl        ; slot visible; HL = slot addr
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
; accumulator temp at SH_DEST (a temp slot, IN PLACE), clamping the combined
; length to STRMAX=255 (reference left-to-right truncation). SH_DEST's slot
; stays put; only its len/ptr change (its old body becomes GC garbage). This
; per-operand binary append (vs the old "build from the last B contiguous
; temps") is robust to operands whose OWN evaluation pushes intermediate
; temps -- e.g. "A"+MID$("XY"+"Z",1,2)+"B" (the STRCAT_R nesting case): each
; operand is fully evaluated and appended before the next, so no contiguity
; assumption is needed. SH_ERR: 0 ok / 1 heap OOM (SH_DEST left unchanged,
; still valid) / 2 temp-stack overflow (only if a fresh body alloc needs a
; slot -- it does not here, so 2 never occurs). Clobbers A,B,C,D,E,H,L.
sh_append:
                ld      hl,(SH_DEST)
                ld      a,(hl)              ; lenR
                ld      c,a                 ; C = lenR
                ld      hl,(SH_SRC)
                ld      a,(hl)              ; lenTk
                add     a,c                 ; total = lenR + lenTk
                jr      nc,sap_ok
                ld      a,255               ; clamp to STRMAX
sap_ok:
                or      a
                jr      z,sap_empty         ; total 0 -> R becomes empty
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
                ret
sap_empty:
                ld      hl,(SH_DEST)
                xor     a
                ld      (hl),a              ; R.len = 0
                inc     hl
                ld      (hl),a
                inc     hl
                ld      (hl),a              ; R.ptr = 0
                ld      (SH_ERR),a
                ret
sap_oom:
                pop     af                  ; discard [total]
                ld      a,1
                ld      (SH_ERR),a          ; heap OOM -- R left unchanged (valid)
                ret
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
; at (STRPTR); page-1/low both byte-full). Parses an optional-sign leading
; decimal integer from (STRPTR)'s body -> SH_PTR (0 if no digits; integer-
; only, spec D-E; SH_ERR always 0). Clobbers A,B,C,D,E,H,L.
sh_val_parse:
                ld      hl,(STRPTR)
                ld      b,(hl)              ; B = byte count
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = ptr (body)
                ex      de,hl               ; HL = body cursor
                ld      de,0                ; accumulator
                ld      c,0                 ; C bit0 = negative flag
svp_sp:
                ld      a,b
                or      a
                jr      z,svp_done
                ld      a,(hl)
                cp      ' '
                jr      nz,svp_sign
                inc     hl
                dec     b
                jr      svp_sp              ; skip leading spaces
svp_sign:
                cp      '-'
                jr      nz,svp_plus
                ld      c,1                 ; negative
                inc     hl
                dec     b
                jr      svp_digits
svp_plus:
                cp      '+'
                jr      nz,svp_digits
                inc     hl
                dec     b
svp_digits:
                ld      a,b
                or      a
                jr      z,svp_fin
                ld      a,(hl)
                cp      '0'
                jr      c,svp_fin
                cp      '9'+1
                jr      nc,svp_fin
                sub     '0'                 ; A = digit 0..9
                push    hl                  ; guard cursor across the *10
                push    af
                ld      h,d
                ld      l,e                 ; HL = acc
                add     hl,hl               ; *2
                add     hl,hl               ; *4
                add     hl,hl               ; *8
                ex      de,hl               ; DE = acc*8 ; HL = acc
                add     hl,hl               ; HL = acc*2
                add     hl,de               ; HL = acc*10
                pop     af                  ; A = digit
                ld      d,0
                ld      e,a
                add     hl,de               ; HL = acc*10 + digit
                ex      de,hl               ; DE = new acc
                pop     hl                  ; restore cursor
                inc     hl
                dec     b
                jr      svp_digits
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

    ENDIF
