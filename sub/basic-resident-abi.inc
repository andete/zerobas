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

fp_add equ 03430H
fp_sub equ 034E2H
fp_mul equ 0351DH
fp_div equ 03607H
fp_cmp equ 036ACH
dig15_iszero equ 03277H
arga_pack_fac equ 03370H
widen_fac_to equ 037E4H
widen_uint_to equ 03B52H
flt_to_int16 equ 03226H
vars_reset equ 03D1FH
penderr_set equ 0281DH
