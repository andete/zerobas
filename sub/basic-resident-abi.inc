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

fp_add equ 0340FH
fp_sub equ 034C1H
fp_mul equ 034FCH
fp_div equ 035E3H
fp_cmp equ 03685H
dig15_iszero equ 03256H
arga_pack_fac equ 0334FH
widen_fac_to equ 037BDH
widen_uint_to equ 03B26H
flt_to_int16 equ 03205H
vars_reset equ 03CF3H
penderr_set equ 0281DH
