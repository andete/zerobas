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

fp_add equ 03359H
fp_sub equ 0340BH
fp_mul equ 03448H
fp_div equ 03532H
fp_cmp equ 035D4H
dig15_iszero equ 031A9H
arga_pack_fac equ 0329DH
widen_fac_to equ 03703H
widen_uint_to equ 03A3DH
flt_to_int16 equ 03156H
vars_reset equ 03C35H
penderr_set equ 027BDH
flt_fmt equ 02FFCH
