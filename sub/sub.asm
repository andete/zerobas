; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — sub.asm
; ===========================================================================
; The virtual zerobas machine's built-in MSX2-style sub-ROM: a standalone 32 KB
; ROM spanning BOTH pages of an internal expanded subslot (slot 3-2 on the
; merged/main machine; RAM stays 3-0, disk stays 3-1). It ships as a plain
; `.rom` like disk.rom — no C-BIOS interaction, no IPS splice, no relocation of
; stock code, so the output firewall (0 C-BIOS-leak bytes) is trivially clean.
; See docs/spec-basic-subrom.md and sub/PROVENANCE.md.
;
; This is the S2a SKELETON: an empty container that carries only the discovery
; signature and one round-trip PING per page. It has no real tenants yet — the
; first (float.asm's tokeniser+formatter) arrives with the S2b/eviction session,
; appended to the entry tables below. The main ROM does not yet call in; S2a's
; boot gate drives the CALSLTs by injection from the openMSX debugger.
;
; TWO OPPOSITE ISLANDS (spec §3b). CALSLT switches only the called page, so:
;   * PAGE 0 ($0000-$3FFF) — while a page-0 tenant runs, slot-0 page 1 (main
;     BASIC) stays visible but the BIOS/low-region/ISR are switched out; run
;     under DI. Signature `CD` lives here at $0000.
;   * PAGE 1 ($4000-$7FFF) — while a page-1 tenant runs, the BIOS is visible but
;     main BASIC is switched out; may EI. Deliberately NOT an "AB" header at
;     $4000 (the cartridge/disk boot scan checks $4000 for 'A'/'B'; a passive
;     sub-ROM must not be CALSLTed as a cartridge — D-7).
; Pages 2/3 (program RAM, sysvars) stay visible from either page, so the PINGs
; can write their page tag to SUB_PING in RAM from both sides.
;
; CLEAN-ROOM: every byte here is own-design. Discovery convention (sub-ROMs
; carry `CD`, cartridges `AB`; EXBRSA $FAF8 records the sub-ROM slot) is from the
; MSX2 Technical Handbook / MSX Assembly Page (allowed). Nothing is derived from
; any stock ROM's code. See sub/PROVENANCE.md.
; ===========================================================================

                include "equates.inc"

; Shared RAM-cell addresses (TKPOS/TKDIG/TKPC/TKSRCSAVE/... used by tkfloat.asm).
; ROM_BASE selects the repack cell layout from the SAME sysvars.inc the merged
; main ROM uses, so a sub-ROM tenant's RAM scratch is byte-address-identical to
; the main ROM's — no marshalling translation. sysvars.inc is pure equates
; (emits no bytes), so it does not perturb this ROM's $0000-based layout.
ROM_BASE        equ     $2812
                include "basic/sysvars.inc"

; ===========================================================================
; PAGE 0 — $0000-$3FFF (the callable-from-main region; `CD` signature)
; ===========================================================================
                org     $0000

; --- Sub-ROM signature (MSX2 sub-ROM ID; §3c/D-3) --------------------------
; `CD` at $0000 marks a sub-ROM (vs `AB` for a cartridge). init_ext_roms
; (S2b) RDSLT-checks $0000/$0001 for 'C'/'D' to discover and record our slot.
                db      "CD"                    ; $0000: sub-ROM signature
                dw      0                        ; $0002: INIT entry — none (passive
                                                 ;        callee, no boot CALSLT, D-7)
                dw      0                        ; $0004: reserved
                dw      0                        ; $0006: reserved
                dw      0,0,0,0                  ; $0008-$000F: reserved (RST area,
                                                 ;   unused — tenants run under DI)

; --- Page-0 entry table (append-only jp table; base $0010, §3c/D-5) --------
; IX = SUBROM_ENTRY_BASE_P0 + 3*index dispatches here. Index 0 = the S2a PING.
; Future page-0 tenants (float.asm's tokeniser+formatter first) append below and
; never move an existing entry, so a main-ROM stub hard-codes only its index.
    IF $ - SUBROM_ENTRY_BASE_P0
                db      SUB_P0_TABLE_NOT_AT_0010__HEADER_SIZE_DRIFT
    ENDIF
sub_p0_table:
                jp      sub_p0_ping             ; index 0 (SUBROM_IDX_PING)
                jp      tokenise                ; index 1 (SUBROM_IDX_TOKENISE): the WHOLE
                                                ;   tokeniser (wave 2). The tk_float crunch
                                                ;   is no longer a dispatch entry — it is an
                                                ;   in-slot `jp tk_float` from tk_loop.
                jp      dtk_tenant              ; index 2 (SUBROM_IDX_DETOK): the LIST /
                                                ;   ASCII-SAVE detokeniser core (wave 3);
                                                ;   fills DETOKBUF, resident side drains it.
                jp      sub_int_selftest        ; index 3 (SUBROM_IDX_INTTEST): the interrupt
                                                ;   self-test — runs EI, verifies the $0038
                                                ;   trampoline serviced the timer (JIFFY++).
                jp      ary_engine              ; index 4 (SUBROM_IDX_ARY): the numeric-array
                                                ;   engine (arrays slice-1 SPLIT design,
                                                ;   docs/spec-basic-arrays.md §10) — a
                                                ;   pure-RAM leaf (descriptor walk, offset
                                                ;   arithmetic, alloc, bound checks). Main-ROM
                                                ;   stub is basic/arrays.asm `ary_engine_call`.
                jp      strheap_engine          ; index 5 (SUBROM_IDX_STRHEAP): the string
                                                ;   heap engine (arrays slice-4a, docs/spec-
                                                ;   basic-arrays-slice4a-string-heap.md §9) —
                                                ;   heap_alloc + GC compaction, a pure-RAM
                                                ;   leaf. Main-ROM stub is basic/str-
                                                ;   engine.asm `str_heap_alloc`.
                jp      pu_tofield_tenant       ; index 6 (SUBROM_IDX_PU_TOFIELD): PRINT USING
                                                ;   format scanner — emit leading literals +
                                                ;   identify the next field (docs/spec-evict-
                                                ;   printusing.md). Main stub basic/printusing.asm.
                jp      pu_tail_tenant          ; index 7 (SUBROM_IDX_PU_TAIL): PRINT USING
                                                ;   trailing-literal emitter. Both are pure
                                                ;   PU_*-RAM+pchar leaves; render into DETOKBUF.

; --- Page-0 PING (S2a boot-gate tenant) -----------------------------------
; Proves a CALSLT to $0010 mapped slot 3-2 into PAGE 0 and that page-3 RAM is
; reachable from there: stamp SUB_PING with the page-0 tag and return. The
; distinct tag ($C0 vs the page-1 $C1) is what proves page-correct mapping — the
; two pings live in different pages of the same subslot, so only a page-selective
; CALSLT reaches each.
sub_p0_ping:
                ld      a,SUB_PING_P0
                ld      (SUB_PING),a
                ret

; --- $0038 interrupt trampoline entry (subrom trampoline slice) ------------
; The maskable-interrupt vector for the page-0 island. While a page-0 tenant runs
; EI, an IRQ lands here with page 0 = sub-ROM; jump to the RAM-resident stub, which
; maps the BIOS back into page 0, runs the real ISR, and returns (see
; basic/subromcall.asm sub_int_template, docs/spec-basic-subrom-trampoline.md). One
; instruction, executed BEFORE any slot switch, so it never pages out its own
; continuation. SUB_INT_RAM is a fixed RAM address, so this `jp` is byte-identical
; every build and needs no relocation. Reserving $0038 costs 3 bytes of page-0 body.
    IF $ > $0038
                db      SUB_P0_OVERRAN_0038__ENTRY_TABLE_OR_PING_TOO_BIG
    ENDIF
                ds      $0038 - $, $FF          ; pad the $001x tenants gap up to the vector
                jp      SUB_INT_RAM             ; $0038: -> the RAM trampoline

; --- Interrupt self-test tenant (index 3; the subrom-inttest gate) ---------
; A standing self-check that this page-0 island is interrupt-live. Entered under DI
; by CALSLT (spec §2.2 opt-in = EI after entry, DI before ret): read JIFFY, EI, spin
; well past one 50/60 Hz frame (~1.7 M cycles), DI, store the JIFFY delta in
; SUB_INT_DELTA. With the trampoline installed the timer ISR runs through the
; sub-ROM $0038 -> RAM stub, so the delta is >= 1; with it absent (or if the tenant
; stayed DI) it is 0. A byte delta suffices (~24-28 ticks < 256).
sub_int_selftest:
                ld      a,(JIFFY)               ; JIFFY low byte before
                ld      b,a
                ei
                ld      hl,0
sis_spin:
                dec     hl                      ; 0 -> 65536 iters (~1.7 M cycles) >> one frame
                ld      a,h
                or      l
                jr      nz,sis_spin
                di
                ld      a,(JIFFY)               ; JIFFY low byte after
                sub     b                       ; delta (mod 256; >= 1 if the timer ticked)
                ld      (SUB_INT_DELTA),a
                ret

; --- Page-0 tenants -------------------------------------------------------
; WAVE 2 (index 1 = tokenise): the WHOLE tokeniser body, evicted from the repack
; main ROM's basic/interp.asm and reunited here with the wave-1 tk_float literal
; crunch. It is pure buffer computation over page-2/3 RAM — no BIOS / low-region /
; ISR touch (leaf-audit, spec §3) — so it is a valid page-0 tenant run under DI.
; Its only non-RAM callees are pure leaves co-resident in this page:
;   * upcase / cmp16_bits / neg_de  — clones in tkfloat.asm (below).
;   * is_letter / is_ident_cont     — clones right below (the tokeniser's
;                                     identifier path; not needed by the crunch).
;   * tk_float                      — the wave-1 crunch, now reached by an ordinary
;                                     in-slot `jp tk_float` from tk_loop (wave 1's
;                                     per-literal CALSLT + disposition protocol were
;                                     reverted, spec §5).
;   * kwtable                       — a byte-identical DUPLICATE of the resident
;                                     repack copy (§4: the resident copy stays for
;                                     LIST/detok, which is I/O-bound and can't go
;                                     sub-side; a page-0 tenant can't see the
;                                     main-ROM low region either, so it needs its
;                                     own copy). Same kwtable.inc + same ROM_BASE
;                                     gating -> the two images can't drift.
                include "tkfloat.asm"
                include "basic/tokenise.inc"

; WAVE 3 (index 2 = detok): the LIST / ASCII-SAVE detokeniser core, evicted from
; the repack main ROM's basic/list.asm. Re-binds pchar/print_string/div10 to
; DETOKBUF appends and shares the co-located kwtable with the tokeniser above (so
; the resident kwtable is dropped). Its resident stub is basic/list.asm `detok`.
                include "detok.asm"

; ARRAYS SLICE-1 SPLIT (index 4 = ary_engine): the numeric-array engine
; (docs/spec-basic-arrays.md §10), moved whole into the sub-ROM because it
; overran the repack ROM by ~284 B as a monolithic main-ROM feature. Pure-RAM
; leaf: no BIOS / low-region / main-ROM-resident touch (leaf-audit, §10.1) —
; calls nothing outside this file. Its own header has the full rationale.
                include "arrays.asm"

; ARRAYS SLICE-4a (index 5 = strheap_engine): the string heap engine (docs/
; spec-basic-arrays-slice4a-string-heap.md), a sibling pure-RAM leaf sharing
; this page with the array engine above (co-resident, so aeng_copy_str/
; ary_alloc can call its heap_alloc/strheap_gc entry points directly, no
; CALSLT). Its own header has the full rationale.
                include "strheap.asm"

; PRINT USING format scanners (index 6/7 = pu_tofield_tenant / pu_tail_tenant):
; the two pure PU_*-RAM+pchar leaves evicted from basic/printusing.asm to free
; page-1 window space (docs/spec-evict-printusing.md). Reuses detok.asm's
; sub-local pchar (DETOKBUF append), included above — so this must follow it.
                include "printusing.asm"

; --- sub-local is_letter / is_ident_cont (byte-identical own-design clones) --
; Resident copies stay in the main ROM (basic/interp.asm is_letter, basic/vars.asm
; is_ident_cont) for the rest of the interpreter; a page-0 tenant can't reach them,
; so the tokeniser's identifier path uses these co-located clones. is_letter ->
; upcase (tkfloat.asm), is_ident_cont -> is_letter — the whole chain is here.
is_letter:
                push    af
                call    upcase
                cp      'A'
                jr      c,sil_no
                cp      'Z'+1
                jr      nc,sil_no
                pop     af
                scf
                ret
sil_no:
                pop     af
                or      a                   ; CF clear
                ret
is_ident_cont:
                call    is_letter           ; letter -> CF set, A preserved
                ret     c
                cp      '0'
                jr      c,siic_no
                cp      '9'+1
                jr      nc,siic_no
                scf                          ; digit -> CF set
                ret
siic_no:
                or      a                    ; CF clear
                ret

; --- sub-local keyword table (duplicate of the resident repack copy, §4) -----
; Assembled from the SAME basic/kwtable.inc under the SAME ROM_BASE (<$4000) as the
; resident repack copy, so the two are byte-identical by construction; the reloc
; build's byte-identity assert (tools/check_reloc.py) is the standing guard.
                include "basic/kwtable.inc"

; --- pad page 0 to the $4000 boundary --------------------------------------
                ds      $4000 - $, $FF

; ===========================================================================
; PAGE 1 — $4000-$7FFF (the BIOS-visible island; NOT an "AB" header)
; ===========================================================================
; $4000 deliberately holds a non-"AB" marker: try_init_slot RDSLT-checks $4000
; for 'A'/'B' on every expanded secondary (including 3-2), and a passive sub-ROM
; must not be picked up as a bootable cartridge (D-7). "S1" = sub-ROM page 1.
                db      "S1"                    ; $4000: page-1 marker (NOT 'A','B')
                dw      0                        ; $4002: reserved
                dw      0                        ; $4004: reserved
                dw      0                        ; $4006: reserved
                dw      0,0,0,0                  ; $4008-$400F: reserved

; --- Page-1 entry table (append-only jp table; base $4010, §3c/D-5) --------
; Mirrors the $4010 disk-DSKIO offset so a page-1 CALSLT looks exactly like the
; disk case the codebase already runs. Index 0 = the S2a PING.
    IF $ - SUBROM_ENTRY_BASE_P1
                db      SUB_P1_TABLE_NOT_AT_4010__HEADER_SIZE_DRIFT
    ENDIF
sub_p1_table:
                jp      sub_p1_ping             ; index 0: round-trip ping
                jp      fp_sqrt                 ; index 1 (SUBROM_IDX_SQR): SQR(x)'s
                                                ;   Heron/Newton body (math-pack slice
                                                ;   1b), migrated from main-ROM page-0
                                                ;   low (docs/spec-basic-subrom-
                                                ;   mathpack.md). Main-ROM stub is
                                                ;   basic/expr.asm `evmc_sqr`.
                jp      fp_atan                 ; index 2 (SUBROM_IDX_ATN): ATN(x)'s
                                                ;   reduction + minimax-polynomial body
                                                ;   (math pack slice 2a, docs/spec-
                                                ;   basic-mathpack-slice2.md §11) -- the
                                                ;   FIRST transcendental tenant. Main-ROM
                                                ;   stub is basic/expr.asm `evmc_atn`.
                jp      fp_exp                  ; index 3 (SUBROM_IDX_EXP): EXP(x)'s
                                                ;   table-assisted range reduction +
                                                ;   minimax-polynomial body (math pack
                                                ;   slice 2b, docs/spec-basic-mathpack-
                                                ;   slice2.md §12). Main-ROM stub is
                                                ;   basic/expr.asm `evmc_exp`.
                jp      fp_log                  ; index 4 (SUBROM_IDX_LOG): LOG(x)'s
                                                ;   split + breakpoint-table reduction +
                                                ;   minimax-polynomial body (math pack
                                                ;   slice 2b, docs/spec-basic-mathpack-
                                                ;   slice2.md §12). Main-ROM stub is
                                                ;   basic/expr.asm `evmc_log`.
                jp      fp_pow                  ; index 5 (SUBROM_IDX_POW): `^`'s
                                                ;   int-path square-and-multiply /
                                                ;   frac-path EXP(y*LOG(x)) body (math
                                                ;   pack slice 2c, docs/spec-basic-
                                                ;   mathpack-slice2.md §13). Main-ROM
                                                ;   stub is basic/float-arith.asm
                                                ;   `combine_pow`.
                jp      fp_sin                  ; index 6 (SUBROM_IDX_SIN): SIN(x)'s
                                                ;   sincos_kernel + quadrant-select
                                                ;   (math pack slice 2d, docs/spec-
                                                ;   basic-mathpack-slice2.md §14).
                                                ;   Main-ROM stub is basic/expr.asm
                                                ;   `evmc_sin`.
                jp      fp_cos                  ; index 7 (SUBROM_IDX_COS): COS(x),
                                                ;   same sincos_kernel (math pack
                                                ;   slice 2d, §14). Main-ROM stub is
                                                ;   basic/expr.asm `evmc_cos`.
                jp      fp_tan                  ; index 8 (SUBROM_IDX_TAN): TAN(x) =
                                                ;   SIN(x)/COS(x) (math pack slice 2d,
                                                ;   §14). Main-ROM stub is basic/
                                                ;   expr.asm `evmc_tan`.
                jp      fp_rnd                  ; index 9 (SUBROM_IDX_RND): RND(x)'s
                                                ;   14-digit BCD LCG advance (math
                                                ;   pack slice 2e, docs/spec-basic-
                                                ;   mathpack-slice2.md §15). LAST
                                                ;   slice-2 tenant. Main-ROM stub is
                                                ;   basic/expr.asm `evmc_rnd`.
                jp      format_tenant           ; index 10 (SUBROM_IDX_FORMAT): CALL
                                                ;   FORMAT's sector-build/write bulk
                                                ;   (docs/spec-evict-call-format.md),
                                                ;   evicted to fund error-handling
                                                ;   S2b. A SPLIT design (not a whole
                                                ;   leaf): the interactive menu +
                                                ;   dispatch stay main-resident
                                                ;   (basic/format.asm `do_format`);
                                                ;   this tenant is the pure geometry
                                                ;   -driven build/write engine, with
                                                ;   its own sub-local CALSLT write
                                                ;   path (main's write_sector is
                                                ;   page-1-main-resident, invisible
                                                ;   here).
                jp      scan_stmt_end           ; index 11 (SUBROM_IDX_SCANSTMT):
                                                ;   RESUME NEXT's quote-aware
                                                ;   statement-advance (sub/
                                                ;   errtrap.asm, docs/spec-basic-
                                                ;   error-handling-s2b-packet.md
                                                ;   §5.5) -- a PURE LEAF (playbook
                                                ;   §3A): walks only tokenised
                                                ;   program RAM text, calls
                                                ;   nothing in main. Main-ROM
                                                ;   stub is basic/interp.asm
                                                ;   `ex_resume`'s res_next arm.
                jp      fatprim_tenant          ; index 12 (SUBROM_IDX_FATPRIM):
                                                ;   the FAT12 primitive/sector
                                                ;   layer (docs/spec-evict-
                                                ;   diskfile-cluster.md §11,
                                                ;   Phase 1) -- ONE selector-
                                                ;   dispatched entry (DISKOP_OP
                                                ;   picks the routine) covering
                                                ;   all 15 marshalled
                                                ;   primitives, a pure
                                                ;   RAM+BIOS(CALSLT) leaf like
                                                ;   format_tenant/scan_stmt_end.
                                                ;   Main-ROM stubs are the
                                                ;   resident shims in
                                                ;   basic/fat.asm (repack).
                jp      dirverb_tenant          ; index 13 (SUBROM_IDX_DIRVERB):
                                                ;   the KILL/NAME directory-verb
                                                ;   I/O bodies (docs/spec-evict-
                                                ;   diskfile-cluster.md §12,
                                                ;   Phase 2) -- ONE selector-
                                                ;   dispatched entry (DISKOP_OP
                                                ;   picks KILL's delete loop vs
                                                ;   NAME's dir-entry stamp), each
                                                ;   calling the Phase-1 fatprim
                                                ;   primitives sub-locally. Main-
                                                ;   ROM heads are the repack
                                                ;   ELSE branches of do_kill/
                                                ;   do_name (basic/files.asm).

; --- Page-1 PING (S2a boot-gate tenant) -----------------------------------
; Proves a CALSLT to $4010 mapped slot 3-2 into PAGE 1 (main BASIC switched out,
; BIOS in) and that page-3 RAM is still reachable: stamp SUB_PING with the
; page-1 tag and return.
sub_p1_ping:
                ld      a,SUB_PING_P1
                ld      (SUB_PING),a
                ret

; --- Page-1 tenants ---------------------------------------------------------
; fp_sqrt (math-pack slice 1b -> subrom-mathpack migration, 2026-07-13): the
; FIRST page-1 tenant and the FIRST non-leaf tenant (calls back into main-ROM-
; resident code across the CALSLT via the imported resident ABI below). See
; docs/spec-basic-subrom-mathpack.md and this cluster's own header comment
; (moved verbatim from basic/float-arith.asm, only the FACTYP/DE finalization
; removed — now done by the caller, evmc_sqr, per §3/§4).
;
; Resident-ABI import (spec §4): the 9 addresses below are generated by
; tools/gen_resident_abi.py from build/basic-reloc.sym on every build (Makefile
; rule), so a page-0-low shift can never leave this ROM calling stale
; addresses — the build-order dependency (basic-reloc.sym -> this .inc ->
; sub.rom) forces a regen, and `make subrom-abi-check` is a standing strong
; consistency gate (re-diffs the shipped sub.rom against a fresh regen).
                include "basic-resident-abi.inc"

                include "fp_sqrt.asm"

; fp_atan (math pack slice 2a, docs/spec-basic-mathpack-slice2.md §11): the
; SECOND page-1 tenant and the FIRST transcendental. Reuses the identical
; resident-ABI import above (its own callee list is a SUBSET of fp_sqrt's --
; no new symbols needed) and math-coeffs.inc's generated FPNUM constant
; records (own decimal minimax, tools/gen_math_coeffs.py -- never the MSX
; ROM's own coefficients, which are binary-format anyway).
                include "math-coeffs.inc"
                include "fp_atan.asm"

; fp_exp + fp_log (math pack slice 2b, docs/spec-basic-mathpack-slice2.md
; §12): the THIRD and FOURTH page-1 tenants, delivered as a matched pair --
; both reuse fp_atan.asm's fat_copy18/fp_poly_horner directly (same
; assembly unit) and fp_exp.asm's own new fexp_cmp16/fexp_tbl18addr helpers
; (fp_log.asm calls the latter too, see each file's own header for the
; reuse rationale). Same math-coeffs.inc (already included above) supplies
; EXP_COEF/LOG_COEF/EXP_RC/EXP_C1/EXP_C2/LN10_C1/LN10_C2/POW8_TBL/EXP_TCOR/
; LNK_TBL/NEGLNK_TBL/LOG_BP.
                include "fp_exp.asm"
                include "fp_log.asm"

; fp_pow (math pack slice 2c, docs/spec-basic-mathpack-slice2.md §13): the
; FIFTH page-1 tenant, the `^` operator. Reuses fp_atan.asm's fat_copy18
; directly (same assembly unit) and, for its fractional path, calls
; fp_exp/fp_log DIRECTLY (same assembly unit, both already included above)
; -- the first tenant-to-tenant composition, no nested subrom_call. Same
; resident-ABI surface subset as the other page-1 tenants; no new
; math-coeffs.inc constants (POW needs none of its own).
                include "fp_pow.asm"

; fp_sin (math pack slice 2d, docs/spec-basic-mathpack-slice2.md §14): the
; SIXTH/SEVENTH/EIGHTH page-1 tenants (fp_sin/fp_cos/fp_tan, one body file
; sharing the sincos_kernel). Reuses fp_atan.asm's fat_copy18/fp_poly_horner
; directly (same assembly unit) and math-coeffs.inc's SIN_COEF/COS_COEF/
; TWO_OVER_PI/SIN_C1/SIN_C2 records (already included above). Same
; resident-ABI surface subset as the other page-1 tenants; no new
; math-coeffs.inc constants beyond what's already emitted.
                include "fp_sin.asm"

; fp_rnd (math pack slice 2e, docs/spec-basic-mathpack-slice2.md §15): the
; NINTH and LAST page-1 tenant, RND(x). Reuses fsc_pack_arga directly
; (fp_sin.asm, same assembly unit, already included above) for its own
; zero-safe FAC pack tail; needs NEITHER fat_copy18/fp_poly_horner NOR any
; math-coeffs.inc record (its own A/C constants are page-1 data local to
; fp_rnd.asm) -- RND is the only slice-2 tenant that calls no resident fp
; op at all (§15.2). Resident-ABI surface subset: dig15_iszero +
; arga_pack_fac only (no widen_fac_to/widen_uint_to, since RND never widens
; an fp record through the resident ops either).
                include "fp_rnd.asm"

; CALL FORMAT build/write engine (index 10 = format_tenant, sub/format.asm): the
; TENTH page-1 tenant and the FIRST that is a SPLIT (not a whole leaf) — its
; main-side counterpart (basic/format.asm) keeps the interactive menu resident.
; Needs no resident-ABI import (unlike fp_sqrt/the transcendentals): it is a
; pure RAM + BIOS(CALSLT) leaf, own header has the full rationale.
                include "format.asm"

; scan_stmt_end (index 11 = SUBROM_IDX_SCANSTMT, sub/errtrap.asm): RESUME
; NEXT's statement-advance (error-handling S2b). A pure-leaf tenant (needs no
; resident-ABI import, same shape as fp_rnd/format_tenant) -- args/result
; marshalled through RAM (SSE_IN/SSE_OUT/SSE_EOL), own header has the full
; rationale.
                include "errtrap.asm"

; FAT12 primitive/sector layer (index 12 = fatprim_tenant, sub/fatprim.asm):
; the TWELFTH page-1 tenant, Phase 1 of the disk/file cluster eviction
; (docs/spec-evict-diskfile-cluster.md §11). Needs no resident-ABI import
; (same shape as fp_rnd/format_tenant/scan_stmt_end): a pure RAM+BIOS(CALSLT)
; leaf -- own header has the full rationale.
                include "fatprim.asm"

; KILL/NAME directory-verb I/O bodies (index 13 = dirverb_tenant, sub/
; dirverb.asm): the THIRTEENTH page-1 tenant, Phase 2 of the disk/file cluster
; eviction (docs/spec-evict-diskfile-cluster.md §12). Needs no resident-ABI
; import (same shape as fatprim_tenant): a pure RAM+BIOS(CALSLT) leaf whose two
; bodies call the Phase-1 fatprim primitives (included just above) sub-locally.
; Placed AFTER fatprim so its sub-local calls resolve within the same page-1
; region -- own header has the full rationale.
                include "dirverb.asm"

; --- pad page 1 to the 32 KB ($8000) end -----------------------------------
                ds      $8000 - $, $FF
