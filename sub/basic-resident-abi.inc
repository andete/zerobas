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

fp_add equ 0344CH
fp_sub equ 034FEH
fp_mul equ 03539H
fp_div equ 03620H
fp_cmp equ 036C2H
dig15_iszero equ 03286H
arga_pack_fac equ 0337FH
widen_fac_to equ 037FAH
widen_uint_to equ 03B57H
flt_to_int16 equ 03235H
vars_reset equ 03D27H
penderr_set equ 02853H
flt_fmt equ 03082H
