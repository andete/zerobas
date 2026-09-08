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

fp_add equ 03452H
fp_sub equ 03504H
fp_mul equ 0353FH
fp_div equ 03626H
fp_cmp equ 036C8H
dig15_iszero equ 0328CH
arga_pack_fac equ 03385H
widen_fac_to equ 03800H
widen_uint_to equ 03B5DH
flt_to_int16 equ 0323BH
vars_reset equ 03D2DH
penderr_set equ 02853H
flt_fmt equ 03088H
