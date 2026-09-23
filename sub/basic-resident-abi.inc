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

fp_add equ 0345EH
fp_sub equ 03510H
fp_mul equ 0354DH
fp_div equ 03637H
fp_cmp equ 036D9H
dig15_iszero equ 0329FH
arga_pack_fac equ 03398H
widen_fac_to equ 03808H
widen_uint_to equ 03B54H
flt_to_int16 equ 0324AH
vars_reset equ 03D2AH
penderr_set equ 02864H
flt_fmt equ 03097H
