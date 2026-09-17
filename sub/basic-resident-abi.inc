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

fp_add equ 03458H
fp_sub equ 0350AH
fp_mul equ 03547H
fp_div equ 03631H
fp_cmp equ 036D3H
dig15_iszero equ 03299H
arga_pack_fac equ 03392H
widen_fac_to equ 03802H
widen_uint_to equ 03B4EH
flt_to_int16 equ 03244H
vars_reset equ 03D24H
penderr_set equ 02864H
flt_fmt equ 03091H
