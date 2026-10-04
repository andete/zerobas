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

fp_add equ 033C3H
fp_sub equ 03475H
fp_mul equ 034B2H
fp_div equ 0359CH
fp_cmp equ 0363EH
dig15_iszero equ 03211H
arga_pack_fac equ 03306H
widen_fac_to equ 0376DH
widen_uint_to equ 03AAEH
flt_to_int16 equ 031BCH
vars_reset equ 03C8FH
penderr_set equ 027C5H
flt_fmt equ 03010H
