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

fp_add equ 0334FH
fp_sub equ 03401H
fp_mul equ 0343EH
fp_div equ 03528H
fp_cmp equ 035CAH
dig15_iszero equ 0319FH
arga_pack_fac equ 03293H
widen_fac_to equ 036F9H
widen_uint_to equ 03A33H
flt_to_int16 equ 0314CH
vars_reset equ 03C80H
penderr_set equ 027BDH
flt_fmt equ 02FF2H
rl_vpeek equ 03B5FH
rl_vpoke equ 03B6AH
rl_vaddr equ 03B77H
rl_lastrow equ 03B9EH
