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

fp_add equ 0345DH
fp_sub equ 0350FH
fp_mul equ 0354AH
fp_div equ 03631H
fp_cmp equ 036D3H
dig15_iszero equ 03297H
arga_pack_fac equ 03390H
widen_fac_to equ 0380BH
widen_uint_to equ 03B73H
flt_to_int16 equ 03246H
vars_reset equ 03D43H
penderr_set equ 02853H
flt_fmt equ 03093H
