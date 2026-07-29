; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; GENERATED FILE -- do not hand-edit. Produced by
; tools/gen_resident_abi.py from build/basic-reloc.sym (Makefile rule);
; regenerated on every build so a page-0-low shift can never leave this
; sub-ROM calling stale addresses. docs/spec-basic-subrom-mathpack.md §4.

fp_add equ 034AEH
fp_sub equ 03560H
fp_mul equ 0359BH
fp_div equ 03686H
fp_cmp equ 0372BH
dig15_iszero equ 032C7H
arga_pack_fac equ 033C7H
widen_fac_to equ 0386DH
widen_uint_to equ 03BD6H
flt_to_int16 equ 03270H
vars_reset equ 03D68H
