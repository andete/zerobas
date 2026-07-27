; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; GENERATED FILE -- do not hand-edit. Produced by
; tools/gen_resident_abi.py from build/basic-reloc.sym (Makefile rule);
; regenerated on every build so a page-0-low shift can never leave this
; sub-ROM calling stale addresses. docs/spec-basic-subrom-mathpack.md §4.

fp_add equ 034BCH
fp_sub equ 0356EH
fp_mul equ 035A9H
fp_div equ 03694H
fp_cmp equ 03739H
dig15_iszero equ 032D5H
arga_pack_fac equ 033D5H
widen_fac_to equ 0387BH
widen_uint_to equ 03BE4H
flt_to_int16 equ 0327EH
vars_reset equ 03D9EH
