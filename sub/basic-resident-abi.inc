; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; GENERATED FILE -- do not hand-edit. Produced by
; tools/gen_resident_abi.py from build/basic-reloc.sym (Makefile rule);
; regenerated on every build so a page-0-low shift can never leave this
; sub-ROM calling stale addresses. docs/spec-basic-subrom-mathpack.md §4.

fp_add equ 034C6H
fp_sub equ 03578H
fp_mul equ 035B3H
fp_div equ 0369EH
fp_cmp equ 03743H
dig15_iszero equ 032DFH
arga_pack_fac equ 033DFH
widen_fac_to equ 03874H
widen_uint_to equ 03BDDH
