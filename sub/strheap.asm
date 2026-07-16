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
; enumerates the live-body root descriptors into a TRANSIENT hardware-stack
; buffer, SORTS them by heap address, then does ONE address-ordered
; compaction sweep -- the spec §5 design. The sort is an in-place SHELL SORT
; with Knuth (3k+1) gaps: O(n^1.5) worst case. This is the spec §5.3-permitted
; "O(n log n)-class sort" FALLBACK to the recommended O(n) radix counting
; sort -- chosen because it needs only the 2n-byte descriptor-address array on
; the stack (no 256/512-byte count array, no ping-pong output buffer), so it
; is markedly less error-prone to implement correctly while still crushing the
; reference's O(n^2) rescan for the string-array-heavy case (the whole point).
; GC is unobservable (it changes only timing, never a program's results), so
; [bug-for-bug compat](bug-for-bug-compat-over-accuracy.md) does not bind it.
; Zero PERMANENT RAM (the stack buffer is freed on return). NOTE for Fable: the
; deviation from the spec is the SORT ALGORITHM only (shell vs radix) -- the
; enumerate/sort/single-sweep STRUCTURE is exactly §5.1/§5.3. No disassembly.

    IF ROM_BASE < $4000

; --- strheap_engine: the tenant entry point (SUBROM_IDX_STRHEAP) -----------
; Reads SH_OP and dispatches. op=0 (ALLOC): SH_LEN -> SH_PTR (or SH_ERR=1 on
; OOM). op=1 (GC): unconditional compaction; SH_PTR := the new FRETOP;
; SH_ERR always 0 (GC cannot fail — an empty heap compacts to a no-op).
; op=2 (BUILD_CONCAT, shape-C follow-up): SH_LEN = operand count -> SH_PTR =
; the new result temp descriptor; SH_ERR = 0 ok / 1 = heap OOM (result
; truncated) / 2 = temp-descriptor-stack overflow (no result slot).
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
                jp      z,strheap_build_concat
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
; sh_temp_push_alloc (below, shared with strheap_build_concat) and re-derive
; OOM-vs-success from the WRITTEN slot's own [len][ptr] state (ptr==0 while
; len!=0 <=> the heap_alloc inside sh_temp_push_alloc failed) rather than
; threading extra registers through — simpler and correct either way.
she_temp_alloc:
                ld      a,(SH_LEN)
                call    sh_temp_push_alloc  ; -> CF+HL=slot,DE=body(or 0) /
                                            ; CF clear=temp-stack full
                jr      nc,she_ta_full
                ld      (SH_PTR),hl
                ld      (SH_PTR2),de
                xor     a
                ld      (SH_ERR),a
                ld      a,(hl)              ; slot.len
                or      a
                jr      z,she_ta_done       ; length 0 -> never OOM
                ld      a,d
                or      e
                jr      nz,she_ta_done      ; body nonzero -> real success
                ld      a,1
                ld      (SH_ERR),a          ; body 0, length nonzero -> OOM
she_ta_done:
                ret
she_ta_full:
                ld      a,2
                ld      (SH_ERR),a
                ret

she_snapshot:
                ld      hl,(SH_SRC)
                ld      a,(hl)              ; source length
                push    hl                  ; guard source addr          [SRC]
                call    sh_temp_push_alloc  ; -> CF+HL=slot,DE=body(or 0) /
                                            ; CF clear=temp-stack full
                jr      nc,she_sn_full
                push    hl
                pop     ix                  ; IX = slot (str_body_copy is a
                                            ; local call, not a CALSLT
                                            ; crossing — IX survives it)
                pop     hl                  ; HL = source addr (restored)   [ ]
                call    str_body_copy       ; HL=source, DE=body -> copies
                push    ix
                pop     hl                  ; HL = slot
                ld      (SH_PTR),hl
                xor     a
                ld      (SH_ERR),a
                ld      a,(hl)              ; slot.len
                or      a
                jr      z,she_sn_done       ; length 0 -> never OOM
                push    hl
                inc     hl
                ld      a,(hl)
                inc     hl
                or      (hl)                ; A = ptr-lo | ptr-hi (0 <=> ptr==0)
                pop     hl
                jr      nz,she_sn_done      ; ptr nonzero -> real success
                ld      a,1
                ld      (SH_ERR),a          ; ptr==0, length nonzero -> OOM
she_sn_done:
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
                push    hl                  ; guard candidate
                or      a
                sbc     hl,de               ; HL = candidate - ARYEND
                pop     hl                  ; HL = candidate (restored)
                jr      nc,ha_ok            ; candidate >= ARYEND -> fits
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
; Own scratch frame on the STACK (IX-addressed, 22 bytes) + a transient 2n
; descriptor-address buffer reserved BELOW it:
;   +0 OLD_FRETOP  +2 CEIL(C)  +4 N  +6 BASE(buffer)  +8 DEST  +10 GAP2/CURSOR
;   +12 P  +14 Q  +16 GAP(elem)  +18 TMP(descaddr)  +20 MODE(1)
; (+10 doubles as the FILL cursor during enumeration and gap*2 during sort;
;  +12/+14 double as the array-walk's ARR_CUR/ARR_END during enumeration and
;  the sort's outer/inner pointers afterward — never overlapping in time.)
; Clobbers A,B,C,D,E,H,L,IX,IY.
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
                ; --- Phase C: reserve the 2n descriptor-address buffer ---
                ld      l,(ix+4)
                ld      h,(ix+5)
                add     hl,hl               ; HL = 2*N (byte size)
                ex      de,hl
                ld      hl,0
                or      a
                sbc     hl,de               ; HL = -(2N)
                add     hl,sp
                ld      sp,hl               ; sp -= 2N
                ld      (ix+6),l
                ld      (ix+7),h            ; BASE = buffer base
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
                ; move this body up to DEST, fix its ptr
                ld      a,(bc)              ; A = n (body length)
                ld      e,a
                ld      d,0                 ; DE = n
                ld      l,(ix+8)
                ld      h,(ix+9)            ; HL = DEST
                or      a
                sbc     hl,de               ; HL = new_dest = DEST - n
                ld      (ix+8),l
                ld      (ix+9),h            ; DEST := new_dest
                ; source body = (descaddr).ptr
                push    bc                  ; guard descaddr
                ld      l,c
                ld      h,b
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = body (source)
                ld      l,(ix+8)
                ld      h,(ix+9)            ; HL = new_dest
                push    hl                  ; guard new_dest
                or      a
                sbc     hl,de               ; new_dest - body
                pop     hl                  ; HL = new_dest
                jr      z,sg_sw_fixup       ; already in place -> skip the move
                ; LDDR shift-up (new_dest >= body, compacting toward C). BC still
                ; holds descaddr in-register (the push at "guard descaddr" left a
                ; COPY on the stack for sg_sw_fixup; the register was untouched),
                ; and HL=new_dest, DE=body from above.
                ld      a,(bc)              ; A = n (body length)
                ld      c,a
                ld      b,0                 ; BC = n (loop count)
                push    bc                  ; guard n            stack: [descaddr][n]
                add     hl,bc               ; HL = new_dest + n
                dec     hl                  ; HL = dstlast
                ex      de,hl               ; DE = dstlast ; HL = body (source base)
                add     hl,bc               ; HL = body + n
                dec     hl                  ; HL = srclast
                pop     bc                  ; BC = n             stack: [descaddr]
                lddr                        ; (HL)->(DE) downward, BC bytes
sg_sw_fixup:
                pop     bc                  ; BC = descaddr (the guard pushed above)
                ld      l,c
                ld      h,b
                inc     hl                  ; -> ptr field
                ld      a,(ix+8)
                ld      (hl),a
                inc     hl
                ld      a,(ix+9)
                ld      (hl),a              ; descaddr.ptr := new_dest (fixed up)
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
                ; --- Phase G: publish new FRETOP, free buffer + frame ---
                ld      l,(ix+8)
                ld      h,(ix+9)
                ld      (FRETOP),hl
                push    ix
                pop     hl                  ; HL = frame base (buffer freed by this)
                ld      sp,hl               ; free the 2n buffer (sp := frame base)
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
                jr      nz,sgv_fill
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
; ROM's str_temp_alloc, basic/str-engine.asm — same contract, calling
; heap_alloc directly in-page instead of crossing subrom_call). out: CF set
; + HL=the new slot, DE=body-to-fill (0 if length 0 or on heap OOM, in
; which case the slot is left NEUTRALISED to len=0/ptr=0); CF clear = the
; temp-descriptor stack itself is full (no slot obtained at all). Clobbers
; A, B, C, D, E, H, L.
sh_temp_push_alloc:
                push    af                  ; guard the requested length
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
                ld      (TEMPTOP),hl
                pop     af                  ; A = length
                ld      (hl),a              ; slot.len = length
                ld      de,0
                or      a
                jr      z,stpa_ptr
                push    hl                  ; guard slot addr
                call    heap_alloc          ; A=len -> CF+HL=body / CF clear=OOM
                jr      nc,stpa_oom
                ex      de,hl               ; DE = body; HL = junk
                pop     hl                  ; HL = slot addr
stpa_ptr:
                inc     hl
                ld      (hl),e
                inc     hl
                ld      (hl),d
                dec     hl
                dec     hl                  ; HL = slot addr (restored)
                scf
                ret
stpa_oom:
                pop     hl                  ; HL = slot addr
                xor     a
                ld      (hl),a              ; neutralise: len := 0
                inc     hl
                ld      (hl),a
                inc     hl
                ld      (hl),a              ; ptr := 0
                dec     hl
                dec     hl                  ; HL = slot addr (restored)
                scf                         ; a slot WAS obtained (just empty)
                ret
stpa_overflow:
                pop     af                  ; discard the guarded length
                or      a                   ; CF clear -> no slot at all
                ret

; --- strheap_build_concat: SH_LEN=B(operand count) -> SH_PTR/SH_ERR --------
; (arrays slice-4a §7/§9 shape-C follow-up — moved from the main-ROM low
; region, which ran out of room for it during implementation; see
; basic/str-engine.asm's own sct_build_result header). The last B temp-
; descriptor-stack entries (pushed by the main-ROM concat spine,
; str_concat_tail, BEFORE this op is called) belong to this concat chain:
; operand N sits at TEMPTOP (the lowest address, most recently pushed),
; operand 1 at TEMPTOP+(B-1)*3 (pushed first, highest address). Sums their
; lengths (clamped to STRMAX=255 via the CARRY out of each 8-bit add), then
; pushes ONE result temp for that clamped total (sh_temp_push_alloc — temp-
; stack entry B+1, the final result) and copies each operand's CURRENT
; bytes (re-read fresh, since the result alloc may itself GC and relocate an
; operand's body — but every operand is ALREADY a legitimate temp-stack
; root, so GC fixes its ptr up correctly, spec §5.2(4)) into it, operand 1
; first, truncating at the clamp (reference left-to-right truncation).
; SH_ERR: 0 ok / 1 = heap OOM inside the result alloc (SH_PTR still a valid,
; truncated-to-shorter temp) / 2 = the temp-descriptor stack itself was too
; full for even the one result slot (SH_PTR undefined; the main-ROM glue
; falls back to STR_EMPTY). Own scratch frame on the STACK (IX-addressed, 8
; bytes: RDESC(2)/WRCUR(2)/ROOM(1)/WALK(2)/OOMFLAG(1) — the sub/arrays.asm
; convention). Clobbers A, B, C, D, E, H, L, IX.
strheap_build_concat:
                dec     sp
                dec     sp
                dec     sp
                dec     sp
                dec     sp
                dec     sp
                dec     sp
                dec     sp                  ; reserve an 8-byte scratch frame
                ld      ix,0
                add     ix,sp
                ld      a,(SH_LEN)
                ld      b,a                 ; B = operand count
                push    bc                  ; guard the ORIGINAL operand count   [CNT0]
                ld      hl,(TEMPTOP)        ; HL = operand N's slot (lowest addr)
                ld      c,0                 ; C = running total (clamped along the way)
sbc_sum_lp:
                ld      a,b
                or      a
                jr      z,sbc_sum_done
                dec     b
                ld      a,(hl)              ; this operand's length
                push    hl                  ; guard the walk cursor
                ld      e,a
                ld      a,c
                add     a,e                 ; A = running total + this length;
                                            ; CF set <=> the true sum exceeded 255
                jr      nc,sbc_sum_ok
                ld      a,255               ; overflowed -> clamp
sbc_sum_ok:
                ld      c,a                 ; C = new running total (clamped)
                pop     hl                  ; restore walk cursor
                ld      de,3
                add     hl,de               ; -> next (higher-address) operand slot
                jr      sbc_sum_lp
sbc_sum_done:
                ld      a,c                 ; A = total length (clamped 0..255)
                or      a
                ld      (ix+7),0            ; default: not an OOM (frame byte +7,
                                            ; the "pad" byte in the 8-byte-aligned
                                            ; frame -- see the header; reused here
                                            ; as an OOM flag)
                jr      z,sbc_alloc_go      ; total 0 -> never OOM regardless
                ld      (ix+7),1            ; nonzero total: tentatively OOM (the
                                            ; alloc below clears this back to 0
                                            ; on success)
sbc_alloc_go:
                call    sh_temp_push_alloc  ; -> CF+HL=result desc,DE=body(or 0) /
                                            ; CF clear=temp-stack overflow
                jp      nc,sbc_overflow
                ld      a,d
                or      e
                jr      z,sbc_have_room     ; body==0 (only possible here if the
                                            ; total was 0 too, per sh_temp_push_
                                            ; alloc's own contract, or a genuine
                                            ; OOM -- (ix+7) already disambiguates)
                ld      (ix+7),0            ; body nonzero -> alloc succeeded
sbc_have_room:
                ld      (ix+0),l
                ld      (ix+1),h            ; RDESC
                ld      (ix+2),e
                ld      (ix+3),d            ; WRCUR = result body (0 on OOM)
                ld      a,(hl)              ; ROOM: re-derive from the RESULT
                ld      (ix+4),a            ; descriptor's own (possibly-
                                            ; neutralised) length -- always
                                            ; correct either way
                pop     bc                  ; B = original operand count (restored) [ ]
                ; WALK starts at operand 1 = TEMPTOP + (B-1)*3 (the HIGHEST address
                ; in this group — left-to-right copy order starts there).
                ld      hl,(TEMPTOP)
                ld      a,b
                dec     a                   ; A = B-1
                ld      d,0
                ld      e,a
                add     hl,de
                add     hl,de
                add     hl,de               ; HL += 3*(B-1)
                ld      (ix+5),l
                ld      (ix+6),h            ; WALK = operand 1's slot
sbc_copy_lp:
                ld      a,b
                or      a
                jr      z,sbc_copy_done
                dec     b
                push    bc                  ; guard the remaining-operand count
                ld      a,(ix+4)
                or      a
                jr      z,sbc_copy_skip     ; no room left -> skip (still must
                                            ; advance WALK below, to keep B ticking
                                            ; down to the loop's own termination)
                ld      l,(ix+5)
                ld      h,(ix+6)            ; HL = this operand's temp-stack slot
                ld      a,(hl)              ; operand length
                ld      c,a
                ld      a,(ix+4)            ; ROOM
                cp      c
                jr      nc,sbc_take_op      ; ROOM >= operand len -> take it all
                ld      c,a                 ; else take only ROOM bytes
sbc_take_op:
                ld      a,(ix+4)
                sub     c
                ld      (ix+4),a            ; ROOM -= (bytes to take)
                ld      a,c
                or      a
                jr      z,sbc_copy_skip     ; nothing to take
                ld      l,(ix+5)
                ld      h,(ix+6)
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = this operand's body (fresh)
                ld      l,(ix+2)
                ld      h,(ix+3)            ; HL = WRCUR
                ex      de,hl               ; HL = operand body (source); DE = WRCUR (dest)
                ld      b,0                 ; BC = bytes to take (C already set)
                ldir                        ; DE advances to the new WRCUR
                ld      (ix+2),e
                ld      (ix+3),d            ; WRCUR updated
sbc_copy_skip:
                pop     bc                  ; restore remaining-operand count
                ld      l,(ix+5)
                ld      h,(ix+6)
                ld      de,3
                or      a
                sbc     hl,de               ; WALK -= 3 (toward operand N/TEMPTOP)
                ld      (ix+5),l
                ld      (ix+6),h
                jr      sbc_copy_lp
sbc_copy_done:
                ld      l,(ix+0)
                ld      h,(ix+1)            ; HL = RDESC (the result)
                ld      (SH_PTR),hl
                ld      a,(ix+7)            ; OOMFLAG (0 ok / 1 the result alloc
                                            ; itself hit heap OOM, set right after
                                            ; sh_temp_push_alloc above)
                ld      (SH_ERR),a
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp                  ; deallocate the 8-byte frame
                ret
sbc_overflow:
                pop     bc                  ; discard [CNT0]
                ld      a,2
                ld      (SH_ERR),a          ; temp-descriptor stack full
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp
                inc     sp                  ; deallocate the 8-byte frame
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
                call    sh_temp_push_alloc  ; -> CF+HL=slot,DE=body(or 0) /
                                            ; CF clear=temp-stack full
                jr      nc,shb_hex_full
                ld      (SH_PTR),hl
                xor     a
                ld      (SH_ERR),a
                ld      a,d
                or      e
                jr      nz,shb_hex_fill
                pop     af                  ; discard [CNT] (defensive; count
                                            ; is always >=1, so DE==0 here
                                            ; would only mean a genuine OOM)
                ld      a,1
                ld      (SH_ERR),a
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
                call    sh_temp_push_alloc  ; A=ndigits -> CF+HL=slot,DE=body
                                            ; (or 0) / CF clear=temp-stack full
                jr      nc,shb_oct_full
                ld      (SH_PTR),hl
                xor     a
                ld      (SH_ERR),a
                ld      a,d
                or      e
                jr      nz,shb_oct_fill
                pop     af                  ; discard [CNT] (defensive)
                ld      a,1
                ld      (SH_ERR),a
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
                call    sh_temp_push_alloc  ; -> CF+HL=slot,DE=body(or 0) /
                                            ; CF clear=temp-stack full
                jr      nc,shf_full
                ld      (SH_PTR),hl
                xor     a
                ld      (SH_ERR),a
                ld      a,d
                or      e
                jr      nz,shf_fill         ; body nonzero -> proceed to fill
                ld      a,(SH_LEN)
                or      a
                ret     z                   ; length 0 -> body==0 is expected,
                                            ; not an OOM
                ld      a,1
                ld      (SH_ERR),a          ; length nonzero but body==0 ->
                                            ; genuine heap OOM
                ret
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
                add     hl,bc               ; HL = a$-body + start = apos
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
