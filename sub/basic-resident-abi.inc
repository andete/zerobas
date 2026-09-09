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

fp_add equ 03454H
fp_sub equ 03506H
fp_mul equ 03541H
fp_div equ 03628H
fp_cmp equ 036CAH
dig15_iszero equ 0328EH
arga_pack_fac equ 03387H
widen_fac_to equ 03802H
widen_uint_to equ 03B5FH
flt_to_int16 equ 0323DH
vars_reset equ 03D2FH
penderr_set equ 02853H
flt_fmt equ 0308AH
