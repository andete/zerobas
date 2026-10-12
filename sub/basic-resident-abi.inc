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

fp_add equ 033D7H
fp_sub equ 03489H
fp_mul equ 034C6H
fp_div equ 035B0H
fp_cmp equ 03652H
dig15_iszero equ 03227H
arga_pack_fac equ 0331BH
widen_fac_to equ 03781H
widen_uint_to equ 03ABBH
flt_to_int16 equ 031D4H
vars_reset equ 03D1DH
penderr_set equ 02818H
flt_fmt equ 0307AH
rl_vpeek equ 03BF7H
rl_vpoke equ 03C02H
rl_vaddr equ 03C0FH
rl_lastrow equ 03C36H
