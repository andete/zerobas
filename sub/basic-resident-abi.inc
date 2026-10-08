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

fp_add equ 033E9H
fp_sub equ 0349BH
fp_mul equ 034D8H
fp_div equ 035C2H
fp_cmp equ 03664H
dig15_iszero equ 03239H
arga_pack_fac equ 0332DH
widen_fac_to equ 03793H
widen_uint_to equ 03ACDH
flt_to_int16 equ 031E6H
vars_reset equ 03D1AH
penderr_set equ 02818H
flt_fmt equ 0308CH
rl_vpeek equ 03BF9H
rl_vpoke equ 03C04H
rl_vaddr equ 03C11H
rl_lastrow equ 03C38H
