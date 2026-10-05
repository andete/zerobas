; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; GENERATED FILE -- do not hand-edit. Produced by
; tools/gen_resident_abi.py from build/basic-reloc.sym (Makefile rule);
; regenerated on every build so a page-0-low shift can never leave this
; sub-ROM calling stale addresses. docs/spec-basic-subrom-mathpack.md §4.
;
; Clean-room: every value below is an address inside THIS project's own
; main ROM, read out of our own build's symbol file. Nothing here is derived
; from a disassembly or byte-copy of any reference ROM.

fp_add equ 03355H
fp_sub equ 03407H
fp_mul equ 03444H
fp_div equ 0352EH
fp_cmp equ 035D0H
dig15_iszero equ 031A5H
arga_pack_fac equ 03299H
widen_fac_to equ 036FFH
widen_uint_to equ 03A39H
flt_to_int16 equ 03152H
vars_reset equ 03C86H
penderr_set equ 027BDH
flt_fmt equ 02FF8H
rl_vpeek equ 03B65H
rl_vpoke equ 03B70H
rl_vaddr equ 03B7DH
rl_lastrow equ 03BA4H
