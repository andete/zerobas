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
p0_bp_ret equ 06965H   ; main's bp_ret
p0_skip_spaces equ 042E0H   ; main's skip_spaces
p0_exec_stmt equ 04136H   ; main's exec_stmt
p0_pl_syntax equ 05BFAH   ; main's pl_syntax
p0_gb_illegal equ 04560H   ; main's gb_illegal
p0_ers_undef equ 07B80H   ; main's ers_undef
p0_req_gosub equ 040F0H   ; main's req_gosub
p0_lref_bc equ 04104H   ; main's lref_bc
p0_find_line_bc equ 076ABH   ; main's find_line_bc
p0_onoff_decode equ 06EC0H   ; main's onoff_decode
p0_set_state equ 05DF7H   ; main's set_state
p0_trap_pend equ 05D30H   ; main's trap_pend
p0_skip_eq equ 042D1H   ; main's skip_eq
p0_eval_addr equ 02F56H   ; main's eval_addr
p0_check_fperr_only equ 04413H   ; main's check_fperr_only
p0_ztrap_entry equ 05DEBH   ; main's ztrap_entry
p0_skip_comma equ 042CBH   ; main's skip_comma
p0_inc_skip_paren equ 042C7H   ; main's inc_skip_paren
p0_inc_eval equ 04AD5H   ; main's inc_eval
p0_get_byte_arg equ 04557H   ; main's get_byte_arg
p0_stmt_error equ 042F7H   ; main's stmt_error
p0_raise_error equ 04317H   ; main's raise_error
p0_pdf_badname equ 027BFH   ; main's pdf_badname
p0_oo_fail_bfn equ 068B8H   ; main's oo_fail_bfn
p0_dpl_dio equ 067B7H   ; main's dpl_dio
p0_dpl_direct equ 067B2H   ; main's dpl_direct
p0_df_notfound equ 0691BH   ; main's df_notfound
p0_loc_missing equ 0638BH   ; main's loc_missing
p0_clr_wipe equ 053A2H   ; main's clr_wipe
p0_end_line_end equ 06FC0H   ; main's end_line_end
p0_disk_error equ 06908H   ; main's disk_error
p0_load_error equ 06559H   ; main's load_error
p0_dev_lpt equ 06D0FH   ; main's dev_lpt
p0_dev_crt equ 06D14H   ; main's dev_crt
p0_dev_grp equ 06D19H   ; main's dev_grp
p0_dev_cas equ 06971H   ; main's dev_cas
p0_fname_expr equ 06D25H   ; main's fname_expr
p0_dev_cmp equ 06CF6H   ; main's dev_cmp
p0_nodisk_dev equ 02812H   ; main's nodisk_dev
p0_pdfcb_resume equ 06D1EH   ; main's pdfcb_resume
p0_skipsp_test equ 028DFH   ; main's skipsp_test
p0_upcase equ 042D7H   ; main's upcase
p0_eval equ 04AD6H   ; main's eval
p0_eval_byte_arg equ 04552H   ; main's eval_byte_arg
p0_stmt_bare_end equ 042E7H   ; main's stmt_bare_end
p0_mxf_require_end equ 03F62H   ; main's mxf_require_end
p0_oo_parse_reclen equ 06D4AH   ; main's oo_parse_reclen
p0_fch_check_d equ 06ED8H   ; main's fch_check_d
p0_fch_check_nz equ 06EE9H   ; main's fch_check_nz
p0_fch_modes_ptr equ 067EDH   ; main's fch_modes_ptr
p0_fch_ctx_addr equ 06E68H   ; main's fch_ctx_addr
p0_fch_do_close_ch equ 06EF3H   ; main's fch_do_close_ch
p0_fch_close_all equ 06F28H   ; main's fch_close_all
p0_fopen_cross equ 068CEH   ; main's fopen_cross
p0_fatprim_op equ 064E2H   ; main's fatprim_op
p0_cas_capture_cut equ 03FA7H   ; main's cas_capture_cut
p0_cas_open_match equ 065C9H   ; main's cas_open_match
p0_cas_bufp_set equ 065D8H   ; main's cas_bufp_set
p0_cas_ascii_setup equ 06753H   ; main's cas_ascii_setup
p0_cas_write_ea_header equ 06820H   ; main's cas_write_ea_header
p0_cas_ascii_drive equ 0675AH   ; main's cas_ascii_drive
p0_dsk_aopen equ 06F98H   ; main's dsk_aopen
p0_dsk_ascii_drive equ 06FACH   ; main's dsk_ascii_drive
p0_run_prog_top equ 06594H   ; main's run_prog_top
p0_do_tape_prog equ 065E3H   ; main's do_tape_prog
p0_disk_prog_load equ 06791H   ; main's disk_prog_load
p0_sv_tenant equ 068A9H   ; main's sv_tenant
p0_bload_cont equ 064EFH   ; main's bload_cont
p0_fch_park equ 03BC4H   ; main's fch_park
p0_list_all equ 063C3H   ; main's list_all
p0_cas_ascii_finish equ 06843H   ; main's cas_ascii_finish
p0_cas_capture_name equ 0659BH   ; main's cas_capture_name
p0_cas_name_cut equ 03FAAH   ; main's cas_name_cut
p0_req_comma equ 02E2DH   ; main's req_comma
p0_check_expr_errors equ 04413H   ; main's check_expr_errors
