; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; fld-fill-body.inc — fld_fill_record shared body (space-fill the record buffer).
;
; docs/spec-eviction-g4-space.md §3 (carve #1). Extracted verbatim from
; basic/field.asm so the SAME source feeds two homes:
;   * (retired) the lean 16 KB cart, inline at this
;     file's ORIGINAL position (right before "FIELD #f, ... AS v$") --
;     BYTE-IDENTICAL to the pre-eviction build.
;   * sub-ROM PAGE-1 tenant (sub/randio.asm, repack): fld_fill_record is
;     called sub-locally by fat_rand_open (basic/randio-body.inc, included
;     right after this file in sub/randio.asm) -- no marshalling, it is a
;     pure-RAM leaf (fills FSECTOR_BUF, no CALSLT).
;
; Kept SEPARATE from basic/randio-body.inc only because fld_fill_record sits
; BEFORE the "FIELD #f, ..." section in the original field.asm, while the
; fat_rand_* engine sits much further down (after LSET/RSET) -- the SAME
; two-file split rationale as basic/fat-prim-body.inc / basic/fat-delete-
; body.inc (kept apart only so the original byte ORDER is preserved; see
; that file's own header).
;
; Clean-room: our own code, extracted verbatim from basic/field.asm (see that
; file's header for the full FIELD/random-access-record provenance).

; fld_fill_record — fill the active channel's record buffer (FSECTOR_BUF, 512
; bytes) with spaces. Used by a RANDOM open so unwritten fields read as spaces.
; Clobbers A? no — only BC/DE/HL.
fld_fill_record:
                ld      hl,FAT_DBUF
                ld      de,FAT_DBUF+1
                ld      bc,511
                ld      (hl),' '
                ldir
                ret
