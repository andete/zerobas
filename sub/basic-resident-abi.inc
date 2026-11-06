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
fp_sub equ 03479H
fp_mul equ 034A8H
fp_div equ 03525H
fp_cmp equ 035E5H
dig15_iszero equ 030D2H
arga_pack_fac equ 0331CH
widen_fac_to equ 036FDH
widen_uint_to equ 03999H
flt_to_int16 equ 0307FH
vars_reset equ 03BE1H
penderr_set equ 02827H
flt_fmt equ 02FBDH
rl_vpeek equ 03AD6H
rl_vpoke equ 03AE1H
rl_vaddr equ 03AEEH
rl_lastrow equ 03B15H

; --- page-0 call-back (p0cb) targets: zerobas-sub's p0cb / p1cb reach these through CLPRIM, never by absolute address ---
p0_chrgtr equ 00160H   ; main's chrgtr
p0_outdo equ 00177H   ; main's outdo
p0_bp_ret equ 06739H   ; main's bp_ret
p0_skip_spaces equ 042D3H   ; main's skip_spaces
p0_exec_stmt equ 04133H   ; main's exec_stmt
p0_gb_illegal equ 04557H   ; main's gb_illegal
p0_eval_addr equ 02ECFH   ; main's eval_addr
p0_ztrap_entry equ 05DB0H   ; main's ztrap_entry
p0_skip_comma equ 042BEH   ; main's skip_comma
p0_ex_key_stmt equ 03F30H   ; main's ex_key_stmt
p0_stmt_error equ 042EAH   ; main's stmt_error
p0_raise_error equ 04313H   ; main's raise_error
p0_pdf_badname equ 027B7H   ; main's pdf_badname
p0_oo_fail_bfn equ 06687H   ; main's oo_fail_bfn
p0_dpl_dio equ 06586H   ; main's dpl_dio
p0_dpl_direct equ 06581H   ; main's dpl_direct
p0_df_notfound equ 066EAH   ; main's df_notfound
p0_loc_missing equ 062AAH   ; main's loc_missing
p0_clr_wipe equ 053ABH   ; main's clr_wipe
p0_end_line_end equ 06FC8H   ; main's end_line_end
p0_disk_error equ 066D7H   ; main's disk_error
p0_load_error equ 06464H   ; main's load_error
p0_dev_lpt equ 06D0FH   ; main's dev_lpt
p0_dev_crt equ 06D14H   ; main's dev_crt
p0_dev_grp equ 06D19H   ; main's dev_grp
p0_dev_cas equ 06745H   ; main's dev_cas
p0_fname_expr equ 06D25H   ; main's fname_expr
p0_dev_cmp equ 06CF6H   ; main's dev_cmp
p0_nodisk_dev equ 0280AH   ; main's nodisk_dev
p0_pdfcb_resume equ 06D1EH   ; main's pdfcb_resume
p0_skipsp_test equ 028D9H   ; main's skipsp_test
p0_upcase equ 042CAH   ; main's upcase
p0_eval equ 04A86H   ; main's eval
p0_eval_byte_arg equ 04549H   ; main's eval_byte_arg
p0_stmt_bare_end equ 042DAH   ; main's stmt_bare_end
p0_mxf_require_end equ 03DCCH   ; main's mxf_require_end
p0_oo_parse_reclen equ 06D4AH   ; main's oo_parse_reclen
p0_fch_check_d equ 06EE1H   ; main's fch_check_d
p0_fch_check_nz equ 06EF2H   ; main's fch_check_nz
p0_fch_modes_ptr equ 065BCH   ; main's fch_modes_ptr
p0_fch_ctx_addr equ 06E70H   ; main's fch_ctx_addr
p0_fch_do_close_ch equ 06EFCH   ; main's fch_do_close_ch
p0_fch_close_all equ 06F30H   ; main's fch_close_all
p0_fopen_cross equ 0669DH   ; main's fopen_cross
p0_fatprim_op equ 063EDH   ; main's fatprim_op
p0_cas_capture_cut equ 03DF0H   ; main's cas_capture_cut
p0_cas_open_match equ 064D5H   ; main's cas_open_match
p0_cas_bufp_set equ 064E4H   ; main's cas_bufp_set
p0_cas_ascii_setup equ 06522H   ; main's cas_ascii_setup
p0_cas_write_ea_header equ 065EFH   ; main's cas_write_ea_header
p0_cas_ascii_drive equ 06529H   ; main's cas_ascii_drive
p0_dsk_aopen equ 06FA0H   ; main's dsk_aopen
p0_dsk_ascii_drive equ 06FB4H   ; main's dsk_ascii_drive
p0_dsk_agetbyte equ 06FA8H   ; main's dsk_agetbyte
p0_run_prog_top equ 064A0H   ; main's run_prog_top
p0_disk_prog_load equ 06560H   ; main's disk_prog_load
p0_sv_tenant equ 06678H   ; main's sv_tenant
p0_bload_cont equ 063FAH   ; main's bload_cont
p0_fch_park equ 03AD2H   ; main's fch_park
p0_list_all equ 062E2H   ; main's list_all
p0_cas_ascii_finish equ 06612H   ; main's cas_ascii_finish
p0_cas_capture_name equ 064A7H   ; main's cas_capture_name
p0_cas_name_cut equ 03DF3H   ; main's cas_name_cut
p0_req_comma equ 02DBCH   ; main's req_comma
p0_check_expr_errors equ 04411H   ; main's check_expr_errors
p0_key_drain equ 05AA3H   ; main's key_drain
p0_req_operand equ 04126H   ; main's req_operand
p0_eval_byte_checked equ 0453DH   ; main's eval_byte_checked
p0_spr_tenant equ 06197H   ; main's spr_tenant
p0_key_repaint equ 05A83H   ; main's key_repaint
p0_key_op equ 05A95H   ; main's key_op
p0_cas_ascii_load equ 0650FH   ; main's cas_ascii_load
p0_load_commit_prog equ 064EFH   ; main's load_commit_prog
p0_dpl_err equ 0657CH   ; main's dpl_err
p0_dpl_oom equ 0658EH   ; main's dpl_oom
p0_print_msg equ 07656H   ; main's print_msg
p0_err_verify equ 06502H   ; main's err_verify
p0_exa_loop equ 076D2H   ; main's exa_loop
p0_le_call_op equ 06E76H   ; main's le_call_op
p0_print_string equ 045DFH   ; main's print_string
p0_list_num equ 0631CH   ; main's list_num
p0_print_in_hl equ 0762CH   ; main's print_in_hl
p0_rn_undefined equ 001B5H   ; main's rn_undefined
