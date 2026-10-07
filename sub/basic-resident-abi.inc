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

fp_add equ 0335CH
fp_sub equ 0340EH
fp_mul equ 0344BH
fp_div equ 03535H
fp_cmp equ 035D7H
dig15_iszero equ 031ACH
arga_pack_fac equ 032A0H
widen_fac_to equ 03706H
widen_uint_to equ 03A40H
flt_to_int16 equ 03159H
vars_reset equ 03C8DH
penderr_set equ 027CAH
flt_fmt equ 02FFFH
rl_vpeek equ 03B6CH
rl_vpoke equ 03B77H
rl_vaddr equ 03B84H
rl_lastrow equ 03BABH
