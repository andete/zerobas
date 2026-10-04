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

fp_add equ 033B5H
fp_sub equ 03467H
fp_mul equ 034A4H
fp_div equ 0358EH
fp_cmp equ 03630H
dig15_iszero equ 03205H
arga_pack_fac equ 032F9H
widen_fac_to equ 0375FH
widen_uint_to equ 03A9AH
flt_to_int16 equ 031B2H
vars_reset equ 03C7BH
penderr_set equ 027C3H
flt_fmt equ 03008H
