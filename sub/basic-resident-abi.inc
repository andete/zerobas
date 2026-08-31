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

fp_add equ 03406H
fp_sub equ 034B8H
fp_mul equ 034F3H
fp_div equ 035DAH
fp_cmp equ 0367CH
dig15_iszero equ 0324DH
arga_pack_fac equ 03346H
widen_fac_to equ 037B4H
widen_uint_to equ 03B1DH
flt_to_int16 equ 031FCH
vars_reset equ 03CEAH
penderr_set equ 0281DH
