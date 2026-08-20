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

fp_add equ 034A9H
fp_sub equ 0355BH
fp_mul equ 03596H
fp_div equ 03681H
fp_cmp equ 03726H
dig15_iszero equ 032C2H
arga_pack_fac equ 033C2H
widen_fac_to equ 03868H
widen_uint_to equ 03BDAH
flt_to_int16 equ 0326BH
vars_reset equ 03DA8H
penderr_set equ 02834H
