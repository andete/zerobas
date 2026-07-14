; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; GENERATED FILE -- do not hand-edit. Produced by
; tools/gen_resident_abi.py from build/basic-reloc.sym (Makefile rule);
; regenerated on every build so a page-0-low shift can never leave this
; sub-ROM calling stale addresses. docs/spec-basic-subrom-mathpack.md §4.

fp_add equ 034CFH
fp_sub equ 03581H
fp_mul equ 035BCH
fp_div equ 036A7H
fp_cmp equ 0374CH
dig15_iszero equ 032E8H
arga_pack_fac equ 033E8H
widen_fac_to equ 0387DH
widen_uint_to equ 03BE6H
