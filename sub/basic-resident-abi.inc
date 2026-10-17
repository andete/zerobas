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

fp_add equ 033D8H
fp_sub equ 0348AH
fp_mul equ 034C7H
fp_div equ 035B1H
fp_cmp equ 03653H
dig15_iszero equ 03226H
arga_pack_fac equ 0331CH
widen_fac_to equ 03779H
widen_uint_to equ 03A25H
flt_to_int16 equ 031DEH
vars_reset equ 03C87H
penderr_set equ 0283BH
flt_fmt equ 03084H
rl_vpeek equ 03B61H
rl_vpoke equ 03B6CH
rl_vaddr equ 03B79H
rl_lastrow equ 03BA0H
