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

fp_add equ 03484H
fp_sub equ 03536H
fp_mul equ 03573H
fp_div equ 0365DH
fp_cmp equ 036FFH
dig15_iszero equ 032CEH
arga_pack_fac equ 033C3H
widen_fac_to equ 0382EH
widen_uint_to equ 03B6FH
flt_to_int16 equ 03279H
vars_reset equ 03D4CH
penderr_set equ 02872H
flt_fmt equ 030CDH
