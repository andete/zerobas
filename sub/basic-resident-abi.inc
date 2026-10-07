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

fp_add equ 0339BH
fp_sub equ 0344DH
fp_mul equ 0348AH
fp_div equ 03574H
fp_cmp equ 03616H
dig15_iszero equ 031EBH
arga_pack_fac equ 032DFH
widen_fac_to equ 03745H
widen_uint_to equ 03A7FH
flt_to_int16 equ 03198H
vars_reset equ 03CCCH
penderr_set equ 027CAH
flt_fmt equ 0303EH
rl_vpeek equ 03BABH
rl_vpoke equ 03BB6H
rl_vaddr equ 03BC3H
rl_lastrow equ 03BEAH
