; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — randio.asm  (fat_rand_* random-access record engine tenant)
; ===========================================================================
; The on-disk record I/O bodies of FIELD/GET/PUT (fat_rand_open/fat_rand_get/
; fat_rand_put + private helpers), evicted from the repack main ROM's
; basic/field.asm into sub-ROM PAGE 1 (docs/spec-eviction-g4-space.md §3,
; carve #1 of the G4-space eviction slice). The FIELD/LSET/RSET/GET/PUT parse
; heads (ex_field/fld_add/ex_lset/ex_rset/lrset_store/fld_lookup/ex_get/
; ex_put/gp_common) stay MAIN-RESIDENT -- a page-1 tenant cannot reach
; fch_select/eval/raise_error/load_error -- and marshal into DISK_FCB_NAME /
; GP_RECNO / FSECTOR_BUF / FWR_* (page-3 RAM, visible from both sides) before
; a single subrom_call hands off to this tenant for the CALSLT-side sector
; work (spec §3's head/body split, the exact `dirverb` precedent).
;
; SAME fp_table/DISKOP_OP selector as fatprim (sub/fatprim.asm), extended
; with three MORE rows (DISKOP_SEL_RAND_OPEN/GET/PUT = 15/16/17) rather than a
; whole new tenant index -- the bodies below need nothing a fresh SUBROM_IDX
; would buy them. Placed AFTER fatprim.asm (+ dirverb.asm) in sub/sub.asm so
; every FAT12 primitive this engine calls (fat_mount/fat_find/fat_dir_create/
; fat_alloc_cluster/fat_write_fat_entry/fat_read_fat_sector/read_sector/
; write_sector/fat_dir_update) resolves to fatprim's own sub-local copies
; (basic/fat-prim-body.inc) with NO rewiring -- co-located ordinary in-slot
; `call`s, no nested subrom_call/CALSLT. This is exactly why the carve is
; cheap: Phase 1 (fatprim) already put the heavy sector/cluster engine here.
;
; RESULT MARSHALLING. Cy cannot ride back through subrom_call/CALSLT (its own
; `or a` always clears it, sub/format.asm's rule) -- so sub/fatprim.asm's
; t_fat_rand_open/get/put wrappers funnel each body's disposition through
; fp_stash_ok/fp_stash_err (DISKOP_STATUS = 0 ok / nonzero error), the SAME
; uniform convention every other fatprim primitive already uses. All three
; bodies here are plain Cy-only (no caller reads DISKOP_HL/DISKOP_A back for
; any of them -- field.asm/files.asm only test Cy), so no bespoke tail is
; needed.
;
; CLEAN-ROOM: original code, extracted verbatim from our own basic/field.asm
; (basic/randio-body.inc / basic/fld-fill-body.inc — the shared bodies also
; included, byte-identical, in the lean 16 KB cart's basic/field.asm; see
; those files' own headers for the full FIELD/GET/PUT provenance). The
; dispatch/marshalling glue is own-design, the CALL FORMAT / fatprim /
; dirverb precedent + MSX2 Technical Handbook CALSLT ABIs. No reference-ROM
; disassembly. See sub/PROVENANCE.md.
; ===========================================================================

                include "basic/fld-fill-body.inc"
                include "basic/randio-body.inc"
