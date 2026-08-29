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

fp_add equ 033FEH
fp_sub equ 034B0H
fp_mul equ 034EBH
fp_div equ 035D2H
fp_cmp equ 03674H
dig15_iszero equ 03245H
arga_pack_fac equ 0333EH
widen_fac_to equ 037ACH
widen_uint_to equ 03B1AH
flt_to_int16 equ 031F4H
vars_reset equ 03CE7H
penderr_set equ 0281DH
