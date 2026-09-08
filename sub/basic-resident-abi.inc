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

fp_add equ 03451H
fp_sub equ 03503H
fp_mul equ 0353EH
fp_div equ 03625H
fp_cmp equ 036C7H
dig15_iszero equ 0328BH
arga_pack_fac equ 03384H
widen_fac_to equ 037FFH
widen_uint_to equ 03B5CH
flt_to_int16 equ 0323AH
vars_reset equ 03D2CH
penderr_set equ 02853H
flt_fmt equ 03087H
