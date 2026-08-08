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

fp_add equ 034B4H
fp_sub equ 03566H
fp_mul equ 035A1H
fp_div equ 0368CH
fp_cmp equ 03731H
dig15_iszero equ 032CDH
arga_pack_fac equ 033CDH
widen_fac_to equ 03873H
widen_uint_to equ 03BDCH
flt_to_int16 equ 03276H
vars_reset equ 03DAAH
