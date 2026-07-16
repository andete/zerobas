; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — equates.inc
; ===========================================================================
; Shared constants for the built-in MSX2-style sub-ROM (docs/spec-basic-subrom.md).
; ===========================================================================

; --- Entry-table bases (the $4010-style fixed dispatch contract, §3c/D-5) -----
; One append-only `jp` table per page; a tenant is addressed by
; IX = base + 3*index. Page 0 tenants see main BASIC (slot-0 page 1) but not the
; BIOS and run under DI; page 1 tenants see the BIOS but not main BASIC. The two
; pages are opposite islands (§3b). Entry 0 of each is the S2a round-trip PING.
SUBROM_ENTRY_BASE_P0    equ     $0010   ; page-0 table (clear of the CD header)
SUBROM_ENTRY_BASE_P1    equ     $4010   ; page-1 table (mirrors the $4010 disk DSKIO)

; --- Page-0 tenant indices (append-only; IX = SUBROM_ENTRY_BASE_P0 + 3*index) --
; index 0 = the S2a round-trip PING (kept as a standing discovery self-check).
; index 1 = the WHOLE TOKENISER (WAVE 2 eviction, sub/tokenise.inc + the wave-1
; tk_float crunch sub/tkfloat.asm, now its in-slot callee); its main-ROM stub is
; basic/interp.asm `tokenise`. Wave 2 repurposed wave 1's per-literal tk_float
; entry into this whole-body entry (the float stub + per-literal CALSLT were
; reverted, spec §5) — the crunch is no longer a dispatch target, just an internal
; `jp tk_float` from the co-located loop. Never renumber an existing entry —
; a main-ROM stub hard-codes only its index.
; index 2 = the DETOKENISER CORE (WAVE 3 eviction, sub/detok.asm): the token->text
; walk (detok/dt_*/detok_op/detok_kw*/the number renderers) rewritten to append into
; DETOKBUF instead of streaming through pchar. Its main-ROM stub is basic/list.asm
; `detok`; the resident side drains DETOKBUF via print_string (honouring PRDEST, so
; the one core feeds both LIST->screen and ASCII-SAVE->disk). Reuses the co-located
; sub kwtable (shared with the wave-2 tokeniser -> the resident copy is now dropped,
; spec §2). docs/spec-basic-subrom-wave3-detok.md.
SUBROM_IDX_PING         equ     0
SUBROM_IDX_TOKENISE     equ     1
SUBROM_IDX_DETOK        equ     2
; index 3 = the INTERRUPT SELF-TEST tenant (trampoline slice, sub/sub.asm
; sub_int_selftest): a standing self-check that a page-0 tenant can run EI and
; have interrupts serviced through the sub-ROM's own $0038 trampoline. It reads
; JIFFY, EI's, spins past one 50/60 Hz frame, DI's, and stores the JIFFY delta in
; SUB_INT_DELTA; the subrom-inttest gate CALSLTs it and asserts delta >= 1 (which
; reads 0 if the trampoline is absent or the tenant left interrupts off).
; docs/spec-basic-subrom-trampoline.md.
SUBROM_IDX_INTTEST      equ     3
; index 4 = the ARRAY ENGINE tenant (arrays slice-1 SPLIT design, sub/
; arrays.asm ary_engine): docs/spec-basic-arrays.md §10. A pure-RAM leaf --
; ary_find/ary_alloc/ary_resolve (the descriptor walk, offset arithmetic,
; bound/negative/wrong-ndim checks, DIM allocation) -- reading the ARY_OP..
; ARY_ERR param block (basic/sysvars.inc §10.2). Its main-ROM stub is
; basic/arrays.asm `ary_engine_call` (ex_dim / ex_let_arr / ev_f_arr).
SUBROM_IDX_ARY          equ     4
; index 5 = the STRING HEAP tenant (arrays slice-4a, sub/strheap.asm
; strheap_engine): docs/spec-basic-arrays-slice4a-string-heap.md §9. A
; pure-RAM leaf -- heap_alloc (bump allocator on the downward frontier
; FRETOP) + GC (root enumeration over STRTAB/array elements/the temp-
; descriptor stack, then compaction) -- reading the SH_OP..SH_ERR param
; block (basic/sysvars.inc). Its main-ROM stub is basic/str-engine.asm
; `str_heap_alloc`. Also called IN-PAGE (no CALSLT) by sub/arrays.asm's
; aeng_copy_str (string array element store) and ary_alloc's own GC-before-
; OOM retry (§5.4), since both are co-resident in the same sub-ROM page-0
; image.
SUBROM_IDX_STRHEAP      equ     5

; --- S2a boot-gate scratch (page-3 RAM, visible from either sub-ROM page) ------
; The skeleton PING tenants write a page-tag byte here so the boot-gate probe can
; confirm a CALSLT to each entry round-tripped through the correct page. This is
; a fixed own-choice RAM cell in the repack-only free window ($F105, right after
; the float pack's last claim PLF_RA2 $F103 and below zerobas-disk's DRVA_DPB
; $F195 — see basic/sysvars.inc). S2a proves the mechanism by injection, so the
; main ROM does not yet reference this cell; S2b's dispatch stub will formalise
; the SUB_ARG/result marshalling block that starts here.
SUB_PING                equ     $F105   ; PING page tag: $C0 (page 0) / $C1 (page 1)
SUB_PING_P0             equ     $C0     ; written by the page-0 ping
SUB_PING_P1             equ     $C1     ; written by the page-1 ping
