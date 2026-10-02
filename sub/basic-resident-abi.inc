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

fp_add equ 03483H
fp_sub equ 03535H
fp_mul equ 03572H
fp_div equ 0365CH
fp_cmp equ 036FEH
dig15_iszero equ 032CDH
arga_pack_fac equ 033C2H
widen_fac_to equ 0382DH
widen_uint_to equ 03B6EH
flt_to_int16 equ 03278H
vars_reset equ 03D4BH
penderr_set equ 02872H
flt_fmt equ 030CCH
