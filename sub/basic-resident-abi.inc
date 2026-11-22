; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause

; GENERATED FILE -- do not hand-edit. Produced by
; tools/gen_resident_abi.py from build/basic-reloc.sym (Makefile rule);
; regenerated on every build so a page-0-low shift can never leave this
; sub-ROM calling stale addresses. docs/spec-basic-subrom-mathpack.md §4.
;
; Clean-room: every value below is an address inside THIS project's own
; main ROM, read out of our own build's symbol file. Nothing here is derived
; from a disassembly or byte-copy of any reference ROM.

fp_add equ 035B6H
fp_sub equ 03655H
fp_mul equ 03684H
fp_div equ 03701H
fp_cmp equ 037C1H
dig15_iszero equ 0330CH
arga_pack_fac equ 034F8H
widen_fac_to equ 038F7H
widen_uint_to equ 03B93H
flt_to_int16 equ 032B9H
vars_reset equ 03D68H
penderr_set equ 02C57H
flt_fmt equ 031EEH
rl_vpeek equ 00B9AH
rl_vpoke equ 00BA5H
rl_vaddr equ 00BB2H
rl_lastrow equ 00BD9H
st_go equ 001F6H
sub_isr_main equ 00B95H
scan_isbd equ 03F8CH
crt_rows equ 03461H
crt_cp equ 0346BH

; --- page-0 call-back (p0cb) targets: zerobas-sub's p0cb / p1cb reach these through CLPRIM, never by absolute address ---
p0_chrgtr equ 00168H   ; main's chrgtr
p0_outdo equ 0017AH   ; main's outdo
p0_bp_ret equ 069ECH   ; main's bp_ret
p0_skip_spaces equ 04234H   ; main's skip_spaces
p0_exec_stmt equ 04131H   ; main's exec_stmt
p0_gb_illegal equ 044AFH   ; main's gb_illegal
p0_eval_addr equ 065A4H   ; main's eval_addr
p0_ztrap_entry equ 05CCEH   ; main's ztrap_entry
p0_skip_comma equ 0421FH   ; main's skip_comma
p0_ex_key_stmt equ 0713EH   ; main's ex_key_stmt
p0_stmt_error equ 0424BH   ; main's stmt_error
p0_raise_error equ 0426BH   ; main's raise_error
p0_pdf_badname equ 02BE7H   ; main's pdf_badname
p0_oo_fail_bfn equ 0693AH   ; main's oo_fail_bfn
p0_dpl_dio equ 06839H   ; main's dpl_dio
p0_dpl_direct equ 06834H   ; main's dpl_direct
p0_df_notfound equ 0699DH   ; main's df_notfound
p0_loc_missing equ 061C9H   ; main's loc_missing
p0_clr_wipe equ 053ABH   ; main's clr_wipe
p0_end_line_end equ 06FFFH   ; main's end_line_end
p0_disk_error equ 0698AH   ; main's disk_error
p0_load_error equ 06701H   ; main's load_error
p0_dev_lpt equ 06D0FH   ; main's dev_lpt
p0_dev_crt equ 06D14H   ; main's dev_crt
p0_dev_grp equ 06D19H   ; main's dev_grp
p0_dev_cas equ 069F8H   ; main's dev_cas
p0_fname_expr equ 06D25H   ; main's fname_expr
p0_dev_cmp equ 06CF6H   ; main's dev_cmp
p0_nodisk_dev equ 02C3AH   ; main's nodisk_dev
p0_pdfcb_resume equ 06D1EH   ; main's pdfcb_resume
p0_skipsp_test equ 02D09H   ; main's skipsp_test
p0_upcase equ 0422BH   ; main's upcase
p0_eval equ 04A8AH   ; main's eval
p0_eval_byte_arg equ 044A1H   ; main's eval_byte_arg
p0_stmt_bare_end equ 0423BH   ; main's stmt_bare_end
p0_mxf_require_end equ 03F06H   ; main's mxf_require_end
p0_oo_parse_reclen equ 06D4AH   ; main's oo_parse_reclen
p0_fch_check_d equ 06F18H   ; main's fch_check_d
p0_fch_check_nz equ 06F29H   ; main's fch_check_nz
p0_fch_modes_ptr equ 0686FH   ; main's fch_modes_ptr
p0_fch_ctx_addr equ 06EA7H   ; main's fch_ctx_addr
p0_fch_do_close_ch equ 06F33H   ; main's fch_do_close_ch
p0_fch_close_all equ 06F67H   ; main's fch_close_all
p0_fopen_cross equ 06950H   ; main's fopen_cross
p0_fatprim_op equ 0631BH   ; main's fatprim_op
p0_cas_capture_cut equ 03F2AH   ; main's cas_capture_cut
p0_cas_open_match equ 0677DH   ; main's cas_open_match
p0_cas_bufp_set equ 0678CH   ; main's cas_bufp_set
p0_cas_ascii_setup equ 067CAH   ; main's cas_ascii_setup
p0_cas_write_ea_header equ 068A2H   ; main's cas_write_ea_header
p0_cas_ascii_drive equ 067D1H   ; main's cas_ascii_drive
p0_dsk_aopen equ 06FD7H   ; main's dsk_aopen
p0_dsk_ascii_drive equ 06FEBH   ; main's dsk_ascii_drive
p0_dsk_agetbyte equ 06FDFH   ; main's dsk_agetbyte
p0_run_prog_top equ 0673DH   ; main's run_prog_top
p0_disk_prog_load equ 06813H   ; main's disk_prog_load
p0_sv_tenant equ 0692BH   ; main's sv_tenant
p0_bload_cont equ 06697H   ; main's bload_cont
p0_fch_park equ 03CBFH   ; main's fch_park
p0_list_all equ 06201H   ; main's list_all
p0_cas_ascii_finish equ 068C5H   ; main's cas_ascii_finish
p0_cas_capture_name equ 0674FH   ; main's cas_capture_name
p0_cas_name_cut equ 03F2DH   ; main's cas_name_cut
p0_req_comma equ 031E6H   ; main's req_comma
p0_check_expr_errors equ 04369H   ; main's check_expr_errors
p0_key_drain equ 05AFDH   ; main's key_drain
p0_req_operand equ 04124H   ; main's req_operand
p0_eval_byte_checked equ 04495H   ; main's eval_byte_checked
p0_spr_tenant equ 060B6H   ; main's spr_tenant
p0_key_repaint equ 05ADDH   ; main's key_repaint
p0_key_op equ 05AEFH   ; main's key_op
p0_cas_ascii_load equ 067B7H   ; main's cas_ascii_load
p0_load_commit_prog equ 06797H   ; main's load_commit_prog
p0_dpl_err equ 0682FH   ; main's dpl_err
p0_dpl_oom equ 06841H   ; main's dpl_oom
p0_print_msg equ 0763FH   ; main's print_msg
p0_err_verify equ 067AAH   ; main's err_verify
p0_exa_loop equ 076BBH   ; main's exa_loop
p0_le_call_op equ 06EADH   ; main's le_call_op
p0_print_string equ 04510H   ; main's print_string
p0_list_num equ 0623BH   ; main's list_num
p0_print_in_hl equ 07615H   ; main's print_in_hl
p0_rn_undefined equ 001B8H   ; main's rn_undefined
