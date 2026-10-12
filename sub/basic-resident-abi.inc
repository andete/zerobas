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

fp_add equ 03408H
fp_sub equ 034BAH
fp_mul equ 034F7H
fp_div equ 035E1H
fp_cmp equ 03683H
dig15_iszero equ 03258H
arga_pack_fac equ 0334CH
widen_fac_to equ 037B2H
widen_uint_to equ 03AECH
flt_to_int16 equ 03205H
vars_reset equ 03D51H
penderr_set equ 02818H
flt_fmt equ 030ABH
rl_vpeek equ 03C2BH
rl_vpoke equ 03C36H
rl_vaddr equ 03C43H
rl_lastrow equ 03C6AH
