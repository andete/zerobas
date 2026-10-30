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
dig15_iszero equ 03217H
arga_pack_fac equ 0331CH
widen_fac_to equ 0379FH
widen_uint_to equ 03A95H
flt_to_int16 equ 031CFH
vars_reset equ 03D04H
penderr_set equ 0282FH
flt_fmt equ 03075H
rl_vpeek equ 03BDEH
rl_vpoke equ 03BE9H
rl_vaddr equ 03BF6H
rl_lastrow equ 03C1DH

; --- page-0 call-back (p0cb) targets: zerobas-sub2 page 0 reaches these through CLPRIM, never by absolute address ---
p0_chrgtr equ 00160H   ; main's chrgtr
p0_outdo equ 00177H   ; main's outdo
p0_bp_ret equ 0672EH   ; main's bp_ret
p0_skip_spaces equ 042E5H   ; main's skip_spaces
p0_exec_stmt equ 04136H   ; main's exec_stmt
p0_pl_syntax equ 05B36H   ; main's pl_syntax
p0_gb_illegal equ 04569H   ; main's gb_illegal
p0_ers_undef equ 07B4AH   ; main's ers_undef
p0_req_gosub equ 040F0H   ; main's req_gosub
p0_lref_bc equ 04104H   ; main's lref_bc
p0_find_line_bc equ 076BBH   ; main's find_line_bc
p0_onoff_decode equ 06EC0H   ; main's onoff_decode
p0_set_state equ 05D33H   ; main's set_state
p0_trap_pend equ 05C6CH   ; main's trap_pend
p0_skip_eq equ 042D6H   ; main's skip_eq
p0_eval_addr equ 02F66H   ; main's eval_addr
p0_check_fperr_only equ 04423H   ; main's check_fperr_only
p0_ztrap_entry equ 05D27H   ; main's ztrap_entry
p0_skip_comma equ 042D0H   ; main's skip_comma
p0_inc_skip_paren equ 042CCH   ; main's inc_skip_paren
p0_inc_eval equ 04ADEH   ; main's inc_eval
p0_get_byte_arg equ 04560H   ; main's get_byte_arg
p0_stmt_error equ 042FCH   ; main's stmt_error
p0_raise_error equ 04325H   ; main's raise_error
p0_pdf_badname equ 027BFH   ; main's pdf_badname
p0_oo_fail_bfn equ 06681H   ; main's oo_fail_bfn
p0_dpl_dio equ 06580H   ; main's dpl_dio
p0_dpl_direct equ 0657BH   ; main's dpl_direct
p0_df_notfound equ 066E4H   ; main's df_notfound
p0_loc_missing equ 06291H   ; main's loc_missing
p0_clr_wipe equ 053F0H   ; main's clr_wipe
p0_end_line_end equ 06FC0H   ; main's end_line_end
p0_disk_error equ 066D1H   ; main's disk_error
p0_load_error equ 0645FH   ; main's load_error
p0_dev_lpt equ 06D0FH   ; main's dev_lpt
p0_dev_crt equ 06D14H   ; main's dev_crt
p0_dev_grp equ 06D19H   ; main's dev_grp
p0_dev_cas equ 0673AH   ; main's dev_cas
p0_fname_expr equ 06D25H   ; main's fname_expr
p0_dev_cmp equ 06CF6H   ; main's dev_cmp
p0_nodisk_dev equ 02812H   ; main's nodisk_dev
p0_pdfcb_resume equ 06D1EH   ; main's pdfcb_resume
p0_skipsp_test equ 028E1H   ; main's skipsp_test
p0_upcase equ 042DCH   ; main's upcase
p0_eval equ 04ADFH   ; main's eval
p0_eval_byte_arg equ 0455BH   ; main's eval_byte_arg
p0_stmt_bare_end equ 042ECH   ; main's stmt_bare_end
p0_mxf_require_end equ 03F78H   ; main's mxf_require_end
p0_oo_parse_reclen equ 06D4AH   ; main's oo_parse_reclen
p0_fch_check_d equ 06ED8H   ; main's fch_check_d
p0_fch_check_nz equ 06EE9H   ; main's fch_check_nz
p0_fch_modes_ptr equ 065B6H   ; main's fch_modes_ptr
p0_fch_ctx_addr equ 06E68H   ; main's fch_ctx_addr
p0_fch_do_close_ch equ 06EF3H   ; main's fch_do_close_ch
p0_fch_close_all equ 06F28H   ; main's fch_close_all
p0_fopen_cross equ 06697H   ; main's fopen_cross
p0_fatprim_op equ 063E8H   ; main's fatprim_op
p0_cas_capture_cut equ 03F9CH   ; main's cas_capture_cut
p0_cas_open_match equ 064CFH   ; main's cas_open_match
p0_cas_bufp_set equ 064DEH   ; main's cas_bufp_set
p0_cas_ascii_setup equ 0651CH   ; main's cas_ascii_setup
p0_cas_write_ea_header equ 065E9H   ; main's cas_write_ea_header
p0_cas_ascii_drive equ 06523H   ; main's cas_ascii_drive
p0_dsk_aopen equ 06F98H   ; main's dsk_aopen
p0_dsk_ascii_drive equ 06FACH   ; main's dsk_ascii_drive
p0_run_prog_top equ 0649AH   ; main's run_prog_top
p0_disk_prog_load equ 0655AH   ; main's disk_prog_load
p0_sv_tenant equ 06672H   ; main's sv_tenant
p0_bload_cont equ 063F5H   ; main's bload_cont
p0_fch_park equ 03BDAH   ; main's fch_park
p0_list_all equ 062C9H   ; main's list_all
p0_cas_ascii_finish equ 0660CH   ; main's cas_ascii_finish
p0_cas_capture_name equ 064A1H   ; main's cas_capture_name
p0_cas_name_cut equ 03F9FH   ; main's cas_name_cut
p0_req_comma equ 02E42H   ; main's req_comma
p0_check_expr_errors equ 04423H   ; main's check_expr_errors
p0_key_drain equ 05AE5H   ; main's key_drain
p0_req_operand equ 04129H   ; main's req_operand
p0_eval_byte_checked equ 0454FH   ; main's eval_byte_checked
p0_spr_tenant equ 06175H   ; main's spr_tenant
p0_key_repaint equ 05AC5H   ; main's key_repaint
p0_key_op equ 05AD7H   ; main's key_op
p0_cas_ascii_load equ 06509H   ; main's cas_ascii_load
p0_load_commit_prog equ 064E9H   ; main's load_commit_prog
p0_dpl_err equ 06576H   ; main's dpl_err
p0_dpl_oom equ 06588H   ; main's dpl_oom
p0_print_msg equ 0765EH   ; main's print_msg
p0_err_verify equ 064FCH   ; main's err_verify
p0_exa_loop equ 076DBH   ; main's exa_loop
p0_le_call_op equ 06E6EH   ; main's le_call_op
p0_print_string equ 045F1H   ; main's print_string
p0_list_num equ 0630DH   ; main's list_num
p0_print_crlf equ 05830H   ; main's print_crlf
p0_rn_undefined equ 001B5H   ; main's rn_undefined
p0_rn_in equ 01BB3H   ; main's in_msg
