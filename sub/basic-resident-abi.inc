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

fp_add equ 033DAH
fp_sub equ 03460H
fp_mul equ 0348FH
fp_div equ 0350CH
fp_cmp equ 035CCH
dig15_iszero equ 0308DH
arga_pack_fac equ 0331CH
widen_fac_to equ 036AAH
widen_uint_to equ 03946H
flt_to_int16 equ 03042H
vars_reset equ 03B68H
penderr_set equ 02827H
flt_fmt equ 02F80H
rl_vpeek equ 03A5DH
rl_vpoke equ 03A68H
rl_vaddr equ 03A75H
rl_lastrow equ 03A9CH

; --- page-0 call-back (p0cb) targets: zerobas-sub's p0cb / p1cb reach these through CLPRIM, never by absolute address ---
p0_chrgtr equ 00160H   ; main's chrgtr
p0_outdo equ 00177H   ; main's outdo
p0_bp_ret equ 066BBH   ; main's bp_ret
p0_skip_spaces equ 042CFH   ; main's skip_spaces
p0_exec_stmt equ 04136H   ; main's exec_stmt
p0_gb_illegal equ 04553H   ; main's gb_illegal
p0_eval_addr equ 02E9DH   ; main's eval_addr
p0_ztrap_entry equ 05D37H   ; main's ztrap_entry
p0_skip_comma equ 042BAH   ; main's skip_comma
p0_ex_key_stmt equ 03EB7H   ; main's ex_key_stmt
p0_stmt_error equ 042E6H   ; main's stmt_error
p0_raise_error equ 0430FH   ; main's raise_error
p0_pdf_badname equ 027B7H   ; main's pdf_badname
p0_oo_fail_bfn equ 0660EH   ; main's oo_fail_bfn
p0_dpl_dio equ 0650DH   ; main's dpl_dio
p0_dpl_direct equ 06508H   ; main's dpl_direct
p0_df_notfound equ 06671H   ; main's df_notfound
p0_loc_missing equ 06231H   ; main's loc_missing
p0_clr_wipe equ 053ABH   ; main's clr_wipe
p0_end_line_end equ 06FB6H   ; main's end_line_end
p0_disk_error equ 0665EH   ; main's disk_error
p0_load_error equ 063EBH   ; main's load_error
p0_dev_lpt equ 06D0FH   ; main's dev_lpt
p0_dev_crt equ 06D14H   ; main's dev_crt
p0_dev_grp equ 06D19H   ; main's dev_grp
p0_dev_cas equ 066C7H   ; main's dev_cas
p0_fname_expr equ 06D25H   ; main's fname_expr
p0_dev_cmp equ 06CF6H   ; main's dev_cmp
p0_nodisk_dev equ 0280AH   ; main's nodisk_dev
p0_pdfcb_resume equ 06D1EH   ; main's pdfcb_resume
p0_skipsp_test equ 028D9H   ; main's skipsp_test
p0_upcase equ 042C6H   ; main's upcase
p0_eval equ 04AC1H   ; main's eval
p0_eval_byte_arg equ 04545H   ; main's eval_byte_arg
p0_stmt_bare_end equ 042D6H   ; main's stmt_bare_end
p0_mxf_require_end equ 03D53H   ; main's mxf_require_end
p0_oo_parse_reclen equ 06D4AH   ; main's oo_parse_reclen
p0_fch_check_d equ 06ECFH   ; main's fch_check_d
p0_fch_check_nz equ 06EE0H   ; main's fch_check_nz
p0_fch_modes_ptr equ 06543H   ; main's fch_modes_ptr
p0_fch_ctx_addr equ 06E5EH   ; main's fch_ctx_addr
p0_fch_do_close_ch equ 06EEAH   ; main's fch_do_close_ch
p0_fch_close_all equ 06F1EH   ; main's fch_close_all
p0_fopen_cross equ 06624H   ; main's fopen_cross
p0_fatprim_op equ 06374H   ; main's fatprim_op
p0_cas_capture_cut equ 03D77H   ; main's cas_capture_cut
p0_cas_open_match equ 0645CH   ; main's cas_open_match
p0_cas_bufp_set equ 0646BH   ; main's cas_bufp_set
p0_cas_ascii_setup equ 064A9H   ; main's cas_ascii_setup
p0_cas_write_ea_header equ 06576H   ; main's cas_write_ea_header
p0_cas_ascii_drive equ 064B0H   ; main's cas_ascii_drive
p0_dsk_aopen equ 06F8EH   ; main's dsk_aopen
p0_dsk_ascii_drive equ 06FA2H   ; main's dsk_ascii_drive
p0_run_prog_top equ 06427H   ; main's run_prog_top
p0_disk_prog_load equ 064E7H   ; main's disk_prog_load
p0_sv_tenant equ 065FFH   ; main's sv_tenant
p0_bload_cont equ 06381H   ; main's bload_cont
p0_fch_park equ 03A59H   ; main's fch_park
p0_list_all equ 06269H   ; main's list_all
p0_cas_ascii_finish equ 06599H   ; main's cas_ascii_finish
p0_cas_capture_name equ 0642EH   ; main's cas_capture_name
p0_cas_name_cut equ 03D7AH   ; main's cas_name_cut
p0_req_comma equ 02D97H   ; main's req_comma
p0_check_expr_errors equ 0440DH   ; main's check_expr_errors
p0_key_drain equ 05A98H   ; main's key_drain
p0_req_operand equ 04129H   ; main's req_operand
p0_eval_byte_checked equ 04539H   ; main's eval_byte_checked
p0_spr_tenant equ 0611EH   ; main's spr_tenant
p0_key_repaint equ 05A78H   ; main's key_repaint
p0_key_op equ 05A8AH   ; main's key_op
p0_cas_ascii_load equ 06496H   ; main's cas_ascii_load
p0_load_commit_prog equ 06476H   ; main's load_commit_prog
p0_dpl_err equ 06503H   ; main's dpl_err
p0_dpl_oom equ 06515H   ; main's dpl_oom
p0_print_msg equ 07662H   ; main's print_msg
p0_err_verify equ 06489H   ; main's err_verify
p0_exa_loop equ 076DEH   ; main's exa_loop
p0_le_call_op equ 06E64H   ; main's le_call_op
p0_print_string equ 045D6H   ; main's print_string
p0_list_num equ 062A3H   ; main's list_num
p0_print_in_hl equ 07638H   ; main's print_in_hl
p0_rn_undefined equ 001B5H   ; main's rn_undefined
