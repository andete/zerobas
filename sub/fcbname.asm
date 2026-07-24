; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — fcbname.asm  (8.3-FCB-name builder tenant)
; ===========================================================================
; build_83_name (+ bn_star_name/bn_star_ext/bn_star_fill), the disk 8.3-FCB-name
; builder from basic/bload.asm, evicted whole into sub-ROM PAGE 1 (docs/spec-
; basic-interrupt-traps.md §10.4, D-T-8c/D-T-8d) to free repack-main page-1 space
; for the interrupt-traps T1 slice. Follows the casmatch/title eviction pattern:
; the moved code is VERBATIM (shared via basic/fcbname-body.inc, included both
; here and at basic/bload.asm's own original position for the lean 16 KB cart --
; byte-identical there).
;
; PAGE 1, not page 0: the page-0 dispatch table is FULL (12 rows fill $0010..$0037
; up to the $0038 interrupt vector). A page-1 tenant has no such cap and can host
; a 13th-plus entry. The one cost: a page-1 tenant runs with main-ROM page 1
; switched OUT, so it can't reach the resident `upcase` -- INLINE a byte-identical
; clone here (below). With that, the body is a pure RAM leaf: it reads the source
; filename via HL, writes DISK_FCB_NAME, both always-mapped page-3 RAM. No BIOS,
; no eval/float, no page-0-low escape -> passes tools/check_tenant_closure.py
; --page1.
;
; MARSHALLING (SPLIT, cf. casmatch): build_83_name takes HL in and returns HL
; (advanced) + CF (reject). subrom_call clobbers all registers and forces CF=0 on
; return, so both outputs ride through RAM. The resident stub (basic/bload.asm
; `build_83_name`, repack branch) stores HL -> BN_PTR before the call; this tenant
; reads BN_PTR into HL, runs the body, writes the advanced HL back to BN_PTR and
; the CF result to BN_STAT (0 = success / 1 = reject); the stub reloads HL <- BN_PTR
; and `rra`s BN_STAT back into CF. BN_PTR/BN_STAT alias the shared DISKOP_HL/
; DISKOP_STATUS cells (basic/sysvars.inc): the FCB-name build runs entirely in the
; disk-verb PARSE phase, strictly before any fat_io_* primitive, so the fatprim
; marshalling cells are provably dead -- the CM_STATUS/LE_STATUS "never in flight
; at once" precedent.
;
; CLEAN-ROOM: original code, extracted verbatim from our own basic/bload.asm (see
; basic/PROVENANCE.md §disk-BLOAD scratch FCB for the 8.3-name rules provenance).
; The dispatch/marshalling glue is own-design, the casmatch/fatprim precedent. No
; reference-ROM disassembly. See sub/PROVENANCE.md.
; ===========================================================================

; --- fcbname_tenant: the SUBROM_IDX_FCBNAME entry --------------------------
fcbname_tenant:
                ld      hl,(BN_PTR)         ; source filename ptr (from the stub)
                call    build_83_name       ; HL advanced -> closing quote; CF = reject
                ld      (BN_PTR),hl         ; advanced ptr back (ld preserves CF)
                jr      c,fcbn_reject
                xor     a
                jr      fcbn_store
fcbn_reject:
                ld      a,1
fcbn_store:
                ld      (BN_STAT),a
                ret

; --- fcb_upcase: sub-local upcaser (byte-identical clone of basic/interp.asm
; upcase). Named fcb_upcase, NOT upcase: the sub image already defines `upcase`
; in its PAGE 0 (sub/tkfloat.asm, for the page-0 tenants), and that page-0 clone
; is unmapped while this PAGE-1 tenant runs (page 0 shows the main slot). So the
; shared body's `call fcb_upcase` binds to this co-located page-1 clone; in the
; lean cart the same name is a zero-byte EQU onto the resident upcase.
fcb_upcase:
                cp      'a'
                ret     c
                cp      'z'+1
                ret     nc
                sub     $20
                ret

                include "basic/fcbname-body.inc"    ; build_83_name..bn_star_fill
