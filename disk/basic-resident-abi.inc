; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; GENERATED FILE -- do not hand-edit. Produced by
; tools/gen_resident_abi.py from build/basic-reloc.sym (Makefile rule);
; regenerated on every build so a page-0-low shift can never leave this
; disk ROM calling stale addresses. docs/spec-basic-subrom-mathpack.md §4.
;
; Clean-room: every value below is an address inside THIS project's own
; main ROM, read out of our own build's symbol file. Nothing here is derived
; from a disassembly or byte-copy of any reference ROM.

widen_rhs_operand equ 038DCH
round_single_and_pack equ 03417H
round_and_finalize equ 033BDH
pu_deref_body equ 028C1H
ARGA equ 0F06AH
STRSCR equ 0E26DH
FN_RESUME equ 0E227H
DISKOP_STATUS equ 0E9FCH
DISK_FCB_NAME equ 0E0DCH
FILES_HASPAT equ 0F009H
FAC equ 0F01CH
FACTYP equ 0F01AH
FSECTOR_BUF equ 0E5C0H
FLD_CHAN equ 0E01BH
LRSET_W equ 0E01DH
LRSET_DEST equ 0E01EH
STRPTR equ 0E0C9H

; --- page-1 call-back targets: reached by an INTER-SLOT call (MSX2 TH), not an absolute one ---
fname_expr equ 06E6EH
pdfcb_resume equ 06E67H
dirverb_op equ 06C4DH
main_fat_mount equ 0641CH   ; main's fat_mount
main_fat_find equ 06420H   ; main's fat_find
parse_disk_fcb equ 065C1H
fat_count_free equ 0644FH
field_prologue equ 07265H
field_item equ 0729BH
lrset_tgt equ 07358H
lrset_rhs equ 0737AH
lrset_finish equ 07391H
