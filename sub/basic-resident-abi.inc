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

fp_add equ 0335EH
fp_sub equ 03410H
fp_mul equ 0344DH
fp_div equ 03537H
fp_cmp equ 035D9H
dig15_iszero equ 031AEH
arga_pack_fac equ 032A2H
widen_fac_to equ 03708H
widen_uint_to equ 03A42H
flt_to_int16 equ 0315BH
vars_reset equ 03C1AH
penderr_set equ 027BFH
flt_fmt equ 03001H
