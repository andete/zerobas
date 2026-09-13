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

fp_add equ 0347EH
fp_sub equ 03530H
fp_mul equ 0356DH
fp_div equ 03657H
fp_cmp equ 036F9H
dig15_iszero equ 032BFH
arga_pack_fac equ 033B8H
widen_fac_to equ 03829H
widen_uint_to equ 03B75H
flt_to_int16 equ 0326AH
vars_reset equ 03D42H
penderr_set equ 02864H
flt_fmt equ 030B7H
