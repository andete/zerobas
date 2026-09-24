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

fp_add equ 03473H
fp_sub equ 03525H
fp_mul equ 03562H
fp_div equ 0364CH
fp_cmp equ 036EEH
dig15_iszero equ 032B4H
arga_pack_fac equ 033ADH
widen_fac_to equ 0381DH
widen_uint_to equ 03B69H
flt_to_int16 equ 0325FH
vars_reset equ 03D3FH
penderr_set equ 02864H
flt_fmt equ 030ACH
