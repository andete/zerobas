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

fp_add equ 03428H
fp_sub equ 034DAH
fp_mul equ 03515H
fp_div equ 035FCH
fp_cmp equ 0369EH
dig15_iszero equ 0326FH
arga_pack_fac equ 03368H
widen_fac_to equ 037D6H
widen_uint_to equ 03B44H
flt_to_int16 equ 0321EH
vars_reset equ 03D11H
penderr_set equ 0281DH
