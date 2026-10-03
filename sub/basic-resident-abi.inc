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

fp_add equ 0347FH
fp_sub equ 03531H
fp_mul equ 0356EH
fp_div equ 03658H
fp_cmp equ 036FAH
dig15_iszero equ 032CDH
arga_pack_fac equ 033C2H
widen_fac_to equ 03829H
widen_uint_to equ 03B6AH
flt_to_int16 equ 03278H
vars_reset equ 03D4BH
penderr_set equ 02872H
flt_fmt equ 030CCH
