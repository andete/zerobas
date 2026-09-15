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

widen_rhs_operand equ 03900H
round_single_and_pack equ 0343BH
round_and_finalize equ 033E1H
ARGA equ 0F06AH
STRSCR equ 0E26DH
FN_RESUME equ 0E227H
DISKOP_STATUS equ 0E9FCH
FAC equ 0F01CH
FACTYP equ 0F01AH

; --- page-1 call-back targets: reached by an INTER-SLOT call (MSX2 TH), not an absolute one ---
fname_expr equ 06E91H
pdfcb_resume equ 06E8AH
dirverb_op equ 06C2FH
