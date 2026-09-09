; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; GENERATED FILE -- do not hand-edit. Produced by
; tools/gen_resident_abi.py from build/basic-reloc.sym (Makefile rule);
; regenerated on every build so a page-0-low shift can never leave this
; sub-ROM calling stale addresses. docs/spec-basic-subrom-mathpack.md §4.
;
; Clean-room: every value below is an address inside THIS project's own
; main ROM, read out of our own build's symbol file. Nothing here is derived
; from a disassembly or byte-copy of any reference ROM.

fp_add equ 03440H
fp_sub equ 034F2H
fp_mul equ 0352DH
fp_div equ 03614H
fp_cmp equ 036B6H
dig15_iszero equ 0327AH
arga_pack_fac equ 03373H
widen_fac_to equ 037EEH
widen_uint_to equ 03B4BH
flt_to_int16 equ 03229H
vars_reset equ 03D1BH
penderr_set equ 02853H
flt_fmt equ 03076H
