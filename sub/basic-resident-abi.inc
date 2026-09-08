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

fp_add equ 0344EH
fp_sub equ 03500H
fp_mul equ 0353BH
fp_div equ 03622H
fp_cmp equ 036C4H
dig15_iszero equ 03288H
arga_pack_fac equ 03381H
widen_fac_to equ 037FCH
widen_uint_to equ 03B59H
flt_to_int16 equ 03237H
vars_reset equ 03D29H
penderr_set equ 02853H
flt_fmt equ 03084H
