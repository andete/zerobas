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

fp_add equ 0346CH
fp_sub equ 0351EH
fp_mul equ 03559H
fp_div equ 03640H
fp_cmp equ 036E2H
dig15_iszero equ 032A6H
arga_pack_fac equ 0339FH
widen_fac_to equ 03816H
widen_uint_to equ 03B69H
flt_to_int16 equ 03255H
vars_reset equ 03D39H
penderr_set equ 02853H
flt_fmt equ 030A2H
