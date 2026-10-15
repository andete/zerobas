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

fp_add equ 033D4H
fp_sub equ 03486H
fp_mul equ 034C3H
fp_div equ 035ADH
fp_cmp equ 0364FH
dig15_iszero equ 03224H
arga_pack_fac equ 03318H
widen_fac_to equ 0377EH
widen_uint_to equ 03AB8H
flt_to_int16 equ 031D1H
vars_reset equ 03D1AH
penderr_set equ 02818H
flt_fmt equ 03077H
rl_vpeek equ 03BF4H
rl_vpoke equ 03BFFH
rl_vaddr equ 03C0CH
rl_lastrow equ 03C33H
