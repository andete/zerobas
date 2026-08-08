; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; lrsetst.asm -- the LSET/RSET record-field STORE as a PAGE-0 sub-ROM tenant
; (SUBROM_IDX_LRSETST). docs/spec-basic-fldary.md §6.4 -- the D-FLDARY funding
; carve.
;
; Clean-room: zerobas's own code, promoted verbatim out of the main ROM's
; FIELD/LSET layer to fund the array-element face of FIELD/LSET/RSET. Nothing
; here is derived from a disassembly or byte-copy of any reference ROM. Verb
; semantics (LSET left-justifies + space-pads, RSET right-justifies, a too-long
; value truncates from the right) follow the public MSX-BASIC language
; reference, unchanged from the resident body this replaces.
; Basis: basic/PROVENANCE.md §random-access records.
;
; WHY THIS ONE. D-FLDARY measured +38 B of main page 1 against 18 B free -- a
; 20 B shortfall -- and the obvious cluster carve was already refused:
; `carve_scout --entries ex_field,ex_lset,ex_rset,fld_add,fld_find` returns NOT
; page-0-evictable (313 absent-region callees reached THROUGH resident main
; page 1, because the statement heads drag stmt_error/eval and thus the whole
; interpreter). The LEAF-ONLY re-run
; (fld_add,fld_find,fld_clear_chan,fld_init,lrset_store) is page-0-tenant CLEAN
; with exactly one blocker, and lrset_store is the member worth taking:
;
;   * 68 B in ONE contiguous span ($7357..$739B in the pre-carve build), six
;     labels, ONE caller (lrset_common, basic/field.asm);
;   * 🎯 NOTHING MARSHALS THROUGH REGISTERS, and nothing new is invented to carry
;     anything. Every input is already a RAM cell that survives CALSLT --
;     LRSET_OFF, LRSET_W, LRSET_JUST, STRPTR, and FSECTOR_BUF ($E5C0, page 3) --
;     and the routine returns nothing at all. Its sibling fld_find could NOT have
;     moved on the same terms: it returns CF + HL, and CF collides with
;     subrom_call's own CF (which means "sub-ROM absent", never "found"), so it
;     would have needed a smuggling cell. This needs none, which is why the
;     resident stub is the minimum 11 B shape;
;   * its ONE blocker is 8 bytes. pu_deref_body (basic/str-engine.asm) is main
;     LOW REGION, which a page-0 CALSLT switches out outright -- so it is inlined
;     below in 5 B. The `push af`/`pop af` the resident body carries is NOT
;     needed here: that A-preservation is load-bearing for ex_print_using's
;     format copy, not for this caller, which reloads A from LRSET_W two
;     instructions later. Same disposition sub/fldlook.asm gives mk_rvdesc.
;
; COLD ENOUGH. This runs once per LSET/RSET statement -- already downstream of
; the resident side's fch_select, which LDIRs a 512-byte record buffer whenever
; the channel changes. One CALSLT round trip (~100 T) is noise against that.
;
; PAGE-0 CLEAN: RAM only. No BIOS call, no low-region call, no main page-1 call,
; no DATA target outside this file.

; --- lrset_store_tenant ----------------------------------------------------
; in:  (LRSET_OFF) = the field's byte offset into the record buffer
;      (LRSET_W)   = the field width, 0..255
;      (LRSET_JUST)= 0 left-justify (LSET) / 1 right-justify (RSET)
;      (STRPTR)   -> the source [len][ptr] descriptor
;      FSECTOR_BUF = the channel's record buffer (the resident stub's fch_select
;                    has already selected it)
; out: the field is space-filled and then min(srclen,width) bytes are copied into
;      it, left- or right-aligned. No failure mode.
; Clobbers AF,BC,DE,HL (tenant convention).
lrset_store_tenant:
                ld      hl,(LRSET_OFF)
                ld      de,FSECTOR_BUF
                add     hl,de               ; HL = field start
                ; space-fill the whole field
                push    hl
                ld      a,(LRSET_W)
                or      a
                jr      z,lrst_filled
                ld      b,a
lrst_fill:
                ld      (hl),' '
                inc     hl
                djnz    lrst_fill
lrst_filled:
                pop     hl                  ; HL = field start
                ld      de,(STRPTR)
                ld      a,(de)              ; source length
                ld      c,a                 ; C = source length
                push    hl                  ; guard field start
                ld      h,d
                ld      l,e                 ; HL = source descriptor addr
                ; --- pu_deref_body, INLINED (see the header): [len][ptr] -> body.
                ; The resident twin's push af/pop af is dropped on purpose -- A is
                ; dead here, reloaded from LRSET_W three instructions below.
                inc     hl
                ld      a,(hl)              ; ptr-lo
                inc     hl
                ld      h,(hl)              ; ptr-hi
                ld      l,a                 ; HL = source bytes
                ex      de,hl               ; DE = source bytes
                pop     hl                  ; HL = field start (restored)
                ld      a,(LRSET_W)
                cp      c
                jr      nc,lrst_ncopy       ; width >= len -> copy len
                ld      c,a                 ; width < len -> copy width (truncate)
lrst_ncopy:
                ld      a,(LRSET_JUST)
                or      a
                jr      z,lrst_copy         ; left: dest = field start
                ; right: dest = field start + (width - ncopy)
                ld      a,(LRSET_W)
                sub     c
                add     a,l
                ld      l,a
                jr      nc,lrst_copy
                inc     h
lrst_copy:
                ld      a,c
                or      a
                ret     z                   ; nothing to copy
                ld      b,c
lrst_cp:
                ld      a,(de)
                ld      (hl),a
                inc     de
                inc     hl
                djnz    lrst_cp
                ret
