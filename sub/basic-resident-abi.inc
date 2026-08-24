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

fp_add equ 0342CH
fp_sub equ 034DEH
fp_mul equ 03519H
fp_div equ 03603H
fp_cmp equ 036A8H
dig15_iszero equ 03273H
arga_pack_fac equ 0336CH
widen_fac_to equ 037E1H
widen_uint_to equ 03B50H
flt_to_int16 equ 03222H
vars_reset equ 03D1DH
penderr_set equ 0281DH
