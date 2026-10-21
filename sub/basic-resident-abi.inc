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

fp_add equ 033D8H
fp_sub equ 0348AH
fp_mul equ 034C7H
fp_div equ 035A3H
fp_cmp equ 03679H
dig15_iszero equ 03207H
arga_pack_fac equ 0331CH
widen_fac_to equ 0379FH
widen_uint_to equ 03A8CH
flt_to_int16 equ 031BFH
vars_reset equ 03CEEH
penderr_set equ 02835H
flt_fmt equ 03065H
rl_vpeek equ 03BC8H
rl_vpoke equ 03BD3H
rl_vaddr equ 03BE0H
rl_lastrow equ 03C07H

; --- page-0 call-back (p0cb) targets: zerobas-sub2 page 0 reaches these through CLPRIM, never by absolute address ---
p0_chrgtr equ 00160H   ; main's chrgtr
p0_outdo equ 00177H   ; main's outdo
p0_bp_ret equ 06CCDH   ; main's bp_ret
p0_skip_spaces equ 042EFH   ; main's skip_spaces
