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

fp_add equ 033D7H
fp_sub equ 0345DH
fp_mul equ 0348CH
fp_div equ 03509H
fp_cmp equ 035C9H
dig15_iszero equ 030D3H
arga_pack_fac equ 0331CH
widen_fac_to equ 036A7H
widen_uint_to equ 03955H
flt_to_int16 equ 03088H
vars_reset equ 03B82H
penderr_set equ 02827H
flt_fmt equ 02F80H
rl_vpeek equ 03A74H
rl_vpoke equ 03A7FH
rl_vaddr equ 03A8CH
rl_lastrow equ 03AB3H

; --- page-0 call-back (p0cb) targets: zerobas-sub2 page 0 reaches these through CLPRIM, never by absolute address ---
p0_chrgtr equ 00160H   ; main's chrgtr
p0_outdo equ 00177H   ; main's outdo
p0_bp_ret equ 06695H   ; main's bp_ret
p0_skip_spaces equ 042E5H   ; main's skip_spaces
p0_exec_stmt equ 04136H   ; main's exec_stmt
p0_pl_syntax equ 05A86H   ; main's pl_syntax
p0_gb_illegal equ 04563H   ; main's gb_illegal
p0_ers_undef equ 07B4AH   ; main's ers_undef
p0_req_gosub equ 040F0H   ; main's req_gosub
p0_lref_bc equ 04104H   ; main's lref_bc
p0_find_line_bc equ 076B7H   ; main's find_line_bc
p0_onoff_decode equ 06EBDH   ; main's onoff_decode
p0_set_state equ 05CF1H   ; main's set_state
p0_trap_pend equ 05C2AH   ; main's trap_pend
p0_skip_eq equ 042D6H   ; main's skip_eq
p0_eval_addr equ 02E9DH   ; main's eval_addr
p0_check_fperr_only equ 0441DH   ; main's check_fperr_only
p0_ztrap_entry equ 05CE5H   ; main's ztrap_entry
p0_skip_comma equ 042D0H   ; main's skip_comma
p0_inc_skip_paren equ 042CCH   ; main's inc_skip_paren
p0_inc_eval equ 04AC7H   ; main's inc_eval
p0_get_byte_arg equ 0455AH   ; main's get_byte_arg
p0_stmt_error equ 042FCH   ; main's stmt_error
p0_raise_error equ 04325H   ; main's raise_error
p0_pdf_badname equ 027B7H   ; main's pdf_badname
p0_oo_fail_bfn equ 065E8H   ; main's oo_fail_bfn
p0_dpl_dio equ 064E7H   ; main's dpl_dio
p0_dpl_direct equ 064E2H   ; main's dpl_direct
p0_df_notfound equ 0664BH   ; main's df_notfound
p0_loc_missing equ 06201H   ; main's loc_missing
p0_clr_wipe equ 053B1H   ; main's clr_wipe
p0_end_line_end equ 06FBDH   ; main's end_line_end
p0_disk_error equ 06638H   ; main's disk_error
p0_load_error equ 063C6H   ; main's load_error
p0_dev_lpt equ 06D0FH   ; main's dev_lpt
p0_dev_crt equ 06D14H   ; main's dev_crt
p0_dev_grp equ 06D19H   ; main's dev_grp
p0_dev_cas equ 066A1H   ; main's dev_cas
p0_fname_expr equ 06D25H   ; main's fname_expr
p0_dev_cmp equ 06CF6H   ; main's dev_cmp
p0_nodisk_dev equ 0280AH   ; main's nodisk_dev
p0_pdfcb_resume equ 06D1EH   ; main's pdfcb_resume
p0_skipsp_test equ 028D9H   ; main's skipsp_test
p0_upcase equ 042DCH   ; main's upcase
p0_eval equ 04AC8H   ; main's eval
p0_eval_byte_arg equ 04555H   ; main's eval_byte_arg
p0_stmt_bare_end equ 042ECH   ; main's stmt_bare_end
p0_mxf_require_end equ 03D8CH   ; main's mxf_require_end
p0_oo_parse_reclen equ 06D4AH   ; main's oo_parse_reclen
p0_fch_check_d equ 06ED5H   ; main's fch_check_d
p0_fch_check_nz equ 06EE6H   ; main's fch_check_nz
p0_fch_modes_ptr equ 0651DH   ; main's fch_modes_ptr
p0_fch_ctx_addr equ 06E65H   ; main's fch_ctx_addr
p0_fch_do_close_ch equ 06EF0H   ; main's fch_do_close_ch
p0_fch_close_all equ 06F25H   ; main's fch_close_all
p0_fopen_cross equ 065FEH   ; main's fopen_cross
p0_fatprim_op equ 0634FH   ; main's fatprim_op
p0_cas_capture_cut equ 03DB0H   ; main's cas_capture_cut
p0_cas_open_match equ 06436H   ; main's cas_open_match
p0_cas_bufp_set equ 06445H   ; main's cas_bufp_set
p0_cas_ascii_setup equ 06483H   ; main's cas_ascii_setup
p0_cas_write_ea_header equ 06550H   ; main's cas_write_ea_header
p0_cas_ascii_drive equ 0648AH   ; main's cas_ascii_drive
p0_dsk_aopen equ 06F95H   ; main's dsk_aopen
p0_dsk_ascii_drive equ 06FA9H   ; main's dsk_ascii_drive
p0_run_prog_top equ 06401H   ; main's run_prog_top
p0_disk_prog_load equ 064C1H   ; main's disk_prog_load
p0_sv_tenant equ 065D9H   ; main's sv_tenant
p0_bload_cont equ 0635CH   ; main's bload_cont
p0_fch_park equ 03A70H   ; main's fch_park
p0_list_all equ 06239H   ; main's list_all
p0_cas_ascii_finish equ 06573H   ; main's cas_ascii_finish
p0_cas_capture_name equ 06408H   ; main's cas_capture_name
p0_cas_name_cut equ 03DB3H   ; main's cas_name_cut
p0_req_comma equ 02D97H   ; main's req_comma
p0_check_expr_errors equ 0441DH   ; main's check_expr_errors
p0_key_drain equ 05A46H   ; main's key_drain
p0_req_operand equ 04129H   ; main's req_operand
p0_eval_byte_checked equ 04549H   ; main's eval_byte_checked
p0_spr_tenant equ 060E5H   ; main's spr_tenant
p0_key_repaint equ 05A26H   ; main's key_repaint
p0_key_op equ 05A38H   ; main's key_op
p0_cas_ascii_load equ 06470H   ; main's cas_ascii_load
p0_load_commit_prog equ 06450H   ; main's load_commit_prog
p0_dpl_err equ 064DDH   ; main's dpl_err
p0_dpl_oom equ 064EFH   ; main's dpl_oom
p0_print_msg equ 0765AH   ; main's print_msg
p0_err_verify equ 06463H   ; main's err_verify
p0_exa_loop equ 076D7H   ; main's exa_loop
p0_le_call_op equ 06E6BH   ; main's le_call_op
p0_print_string equ 045EBH   ; main's print_string
p0_list_num equ 06276H   ; main's list_num
p0_print_crlf equ 057A9H   ; main's print_crlf
p0_rn_undefined equ 001B5H   ; main's rn_undefined
p0_rn_in equ 01BB3H   ; main's in_msg
