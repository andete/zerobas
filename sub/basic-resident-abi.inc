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

fp_add equ 033DAH
fp_sub equ 0348CH
fp_mul equ 034C9H
fp_div equ 035B3H
fp_cmp equ 03655H
dig15_iszero equ 0322AH
arga_pack_fac equ 0331EH
widen_fac_to equ 03784H
widen_uint_to equ 03ABEH
flt_to_int16 equ 031D7H
vars_reset equ 03D20H
penderr_set equ 02818H
flt_fmt equ 0307DH
rl_vpeek equ 03BFAH
rl_vpoke equ 03C05H
rl_vaddr equ 03C12H
rl_lastrow equ 03C39H
