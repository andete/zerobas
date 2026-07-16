; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; GENERATED FILE -- do not hand-edit. Produced by
; tools/gen_resident_abi.py from build/basic-reloc.sym (Makefile rule);
; regenerated on every build so a page-0-low shift can never leave this
; sub-ROM calling stale addresses. docs/spec-basic-subrom-mathpack.md §4.

fp_add equ 034C5H
fp_sub equ 03577H
fp_mul equ 035B2H
fp_div equ 0369DH
fp_cmp equ 03742H
dig15_iszero equ 032DEH
arga_pack_fac equ 033DEH
widen_fac_to equ 03873H
widen_uint_to equ 03BDCH
