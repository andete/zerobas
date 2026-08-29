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

fp_add equ 03403H
fp_sub equ 034B5H
fp_mul equ 034F0H
fp_div equ 035D7H
fp_cmp equ 03679H
dig15_iszero equ 0324AH
arga_pack_fac equ 03343H
widen_fac_to equ 037B1H
widen_uint_to equ 03B1FH
flt_to_int16 equ 031F9H
vars_reset equ 03CECH
penderr_set equ 0281DH
