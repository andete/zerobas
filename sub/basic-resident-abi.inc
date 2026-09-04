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

fp_add equ 03459H
fp_sub equ 0350BH
fp_mul equ 03546H
fp_div equ 0362DH
fp_cmp equ 036CFH
dig15_iszero equ 03293H
arga_pack_fac equ 0338CH
widen_fac_to equ 03807H
widen_uint_to equ 03B73H
flt_to_int16 equ 03242H
vars_reset equ 03D43H
penderr_set equ 0284EH
flt_fmt equ 0308FH
