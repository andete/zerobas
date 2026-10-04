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

fp_add equ 033D2H
fp_sub equ 03484H
fp_mul equ 034C1H
fp_div equ 035ABH
fp_cmp equ 0364DH
dig15_iszero equ 03220H
arga_pack_fac equ 03315H
widen_fac_to equ 0377CH
widen_uint_to equ 03ABDH
flt_to_int16 equ 031CBH
vars_reset equ 03C9EH
penderr_set equ 027C5H
flt_fmt equ 0301FH
