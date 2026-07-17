; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; GENERATED FILE -- do not hand-edit. Produced by
; tools/gen_resident_abi.py from build/basic-reloc.sym (Makefile rule);
; regenerated on every build so a page-0-low shift can never leave this
; sub-ROM calling stale addresses. docs/spec-basic-subrom-mathpack.md §4.

fp_add equ 034CCH
fp_sub equ 0357EH
fp_mul equ 035B9H
fp_div equ 036A4H
fp_cmp equ 03749H
dig15_iszero equ 032E5H
arga_pack_fac equ 033E5H
widen_fac_to equ 0387AH
widen_uint_to equ 03BE3H
