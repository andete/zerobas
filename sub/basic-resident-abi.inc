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

fp_add equ 03400H
fp_sub equ 034B2H
fp_mul equ 034EDH
fp_div equ 035D4H
fp_cmp equ 03676H
dig15_iszero equ 03247H
arga_pack_fac equ 03340H
widen_fac_to equ 037AEH
widen_uint_to equ 03B1CH
flt_to_int16 equ 031F6H
vars_reset equ 03CE9H
penderr_set equ 0281DH
