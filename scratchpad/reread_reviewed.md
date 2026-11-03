# D-REREAD: routines a batch reviewed (or deliberately skipped), one batch per line
batch7: sh_go_g stk_guard shx_finish fp_div req_comma eon_seek_nth evmc_prologue combine_pow str_lr_count str_arg_snap
batch7-skipped-hot: exec ex_next
batch8: ex_get mkf_back fac_zero_mantissa ev_str_arg ary_store_write err_syntax ex_deftype ex_clear pl_args fn_call
skipped: str_snapshot_ro stk_oom ev_logic pchar event_poll dispatch_line str_snapshot_to_temp
batch9: ex_erase ary_parse_call widen_fac_to ex_out ex_read ex_rset ex_sprite ex_preset ex_circle ex_draw
batch9-skipped: ctl_get nx_pack evsgn_settype psv_voice basicint_4ef8 spr_tenant
batch10: flo_emit_e ary_op0_resolve flt_fmt iv_seq sw_operand ex_vpoke ex_on ex_input ex_swap ex_locate
batch10-skipped-hot-or-shared: rl_loop tok_skip cl_jphl nx_pki evmc_arg_int var_name_key var_store_fac play_install pcz_pad pu_do_string pu_do_number exa_loop usr_setslot build_83_name
batch11: ex_poke ev_cv_back ex_cont list_walk detok_emit ex_base_assign ex_troff oo_parse_reclen ex_dim fch_do_close_ch
batch11-skipped-hot: ex_return ex_if caddsub_int eval psv_get parse_disk_fcb zkey_install basicint_run

# sub ROM batch 1 (2026-11-03): reread by file, not by span -- detok.inc, pu-render.inc, printusing, the sv-* bodies, save, readdata-body, format-body, fcbname-body, casmatch-body, bload-body, fp_log (flog_no_fold reviewed)
sd10_skip pet_done cas_ascii_setup ws_err sv_tape_err readdata_tenant sq_end pt_period fcbn_store flog_no_fold
