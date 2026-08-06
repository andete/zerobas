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

fp_add equ 034A7H
fp_sub equ 03559H
fp_mul equ 03594H
fp_div equ 0367FH
fp_cmp equ 03724H
dig15_iszero equ 032C0H
arga_pack_fac equ 033C0H
widen_fac_to equ 03866H
widen_uint_to equ 03BCFH
flt_to_int16 equ 03269H
vars_reset equ 03D9DH
