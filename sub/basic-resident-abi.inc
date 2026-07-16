; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; GENERATED FILE -- do not hand-edit. Produced by
; tools/gen_resident_abi.py from build/basic-reloc.sym (Makefile rule);
; regenerated on every build so a page-0-low shift can never leave this
; sub-ROM calling stale addresses. docs/spec-basic-subrom-mathpack.md §4.

fp_add equ 034C2H
fp_sub equ 03574H
fp_mul equ 035AFH
fp_div equ 0369AH
fp_cmp equ 0373FH
dig15_iszero equ 032DBH
arga_pack_fac equ 033DBH
widen_fac_to equ 03870H
widen_uint_to equ 03BD9H
