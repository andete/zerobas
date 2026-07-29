; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; GENERATED FILE -- do not hand-edit. Produced by
; tools/gen_resident_abi.py from build/basic-reloc.sym (Makefile rule);
; regenerated on every build so a page-0-low shift can never leave this
; sub-ROM calling stale addresses. docs/spec-basic-subrom-mathpack.md §4.

fp_add equ 034B7H
fp_sub equ 03569H
fp_mul equ 035A4H
fp_div equ 0368FH
fp_cmp equ 03734H
dig15_iszero equ 032D0H
arga_pack_fac equ 033D0H
widen_fac_to equ 03876H
widen_uint_to equ 03BDFH
flt_to_int16 equ 03279H
vars_reset equ 03D9DH
