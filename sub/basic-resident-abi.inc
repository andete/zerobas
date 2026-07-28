; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; GENERATED FILE -- do not hand-edit. Produced by
; tools/gen_resident_abi.py from build/basic-reloc.sym (Makefile rule);
; regenerated on every build so a page-0-low shift can never leave this
; sub-ROM calling stale addresses. docs/spec-basic-subrom-mathpack.md §4.

fp_add equ 034A1H
fp_sub equ 03553H
fp_mul equ 0358EH
fp_div equ 03679H
fp_cmp equ 0371EH
dig15_iszero equ 032BAH
arga_pack_fac equ 033BAH
widen_fac_to equ 03860H
widen_uint_to equ 03BC9H
flt_to_int16 equ 03263H
vars_reset equ 03D87H
