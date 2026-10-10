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

fp_add equ 0340EH
fp_sub equ 034C0H
fp_mul equ 034FDH
fp_div equ 035E7H
fp_cmp equ 03689H
dig15_iszero equ 0325EH
arga_pack_fac equ 03352H
widen_fac_to equ 037B8H
widen_uint_to equ 03AF2H
flt_to_int16 equ 0320BH
vars_reset equ 03D44H
penderr_set equ 02818H
flt_fmt equ 030B1H
rl_vpeek equ 03C1EH
rl_vpoke equ 03C29H
rl_vaddr equ 03C36H
rl_lastrow equ 03C5DH
