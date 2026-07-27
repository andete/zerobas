; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; GENERATED FILE -- do not hand-edit. Produced by
; tools/gen_resident_abi.py from build/basic-reloc.sym (Makefile rule);
; regenerated on every build so a page-0-low shift can never leave this
; sub-ROM calling stale addresses. docs/spec-basic-subrom-mathpack.md §4.

fp_add equ 034B8H
fp_sub equ 0356AH
fp_mul equ 035A5H
fp_div equ 03690H
fp_cmp equ 03735H
dig15_iszero equ 032D1H
arga_pack_fac equ 033D1H
widen_fac_to equ 03877H
widen_uint_to equ 03BE0H
flt_to_int16 equ 0327AH
vars_reset equ 03D9AH
