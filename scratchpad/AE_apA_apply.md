# Slice A re-read: what was applied (2026-11-26)

Measured per candidate as the change in the $00 fill in front of each pin, from a
from-scratch `build/disk.rom` (rm, then make) before and after each edit (script:
a throwaway pad-measuring helper, not kept). Baseline: a fresh rebuild of the unmodified sources.
Comments at each site are tagged `D-DISKREREAD (2026-11-26)`.

**Total applied: 178 B.** By region (pin: before -> after):
$41EF 1->62 (+61) · $4C29 4->43 (+39) · $4E4B 0->20 (+20) · $7F7C 8->24 (+16) ·
$436C 4->17 (+13) · $44F4 2->12 (+10) · $46BA 7->16 (+9) · $461D 0->5 (+5) ·
$43A4 0->3 (+3) · $4392 1->3 (+2).
`check_disk_walls.py`: 0 B usable -> 182 B in 6 runs (largest 62 B before $41EF).

| # | Candidate | Result | Measured | Region |
|---|---|---|---|---|
| 1 | build_drvtbl template + HL-dest loop | APPLIED | 32 B (list said 26: the old code had SEVEN word stores, +1..+13, not six) | $41EF |
| 2 | dnm_body -> call nz,dst_put | APPLIED | 14 B | $4C29 |
| 3 | page0_ram_in bit-merge (14 B version, $FFFF read after `out`) | APPLIED | 14 B | $41EF |
| 4 | dskio_head shared head; dskio_ok folded into dskio_err | APPLIED | 13 B | $436C |
| 5 | rdblk_getbyte H>=2 test | APPLIED | 9 B | $46BA |
| 6 | lsec_chs 16-bit sbc loop | APPLIED | 9 B | $4E4B |
| 7 | fwd_nowin bit tests | APPLIED | 9 B (flags S/Z/H/PV/N/C checked identical on every arm, incl. the fall-through) | $4C29 |
| 8 | basent_pending tested once in init | APPLIED | 7 B (fat.asm's basent_resume comment updated) | $41EF |
| 9 | set_ramad: no push/pop around SNSMAT; arithmetic count | APPLIED | 7 B | $41EF |
| 10 | bl_bs -> bd_puts cinl_bs | APPLIED | 7 B (references kernel.asm's `cinl_bs`; kernel not edited) | $4C29 |
| 11a/b | bsr_have size test; BC=n before hl_x128 | APPLIED | 6 B | $461D |
| 11c | bsr_borrow loop (C out 0 instead of n) | SKIPPED | the list itself rates it LOW-MEDIUM; seqread's callers (bdos_tab, wrseq_rd, rdrnd_body, driver.asm:549) not all audited for C | - |
| 12 | blit1 helper (dta_put + bsr_padloop) | APPLIED | net 6 B: +9 at $44F4, -3 at $461D (helper lives after bsr_eof) | $44F4/$461D |
| 13 | fwe_cmp -> call fac_flushdirty | APPLIED | 5 B | $4C29 |
| 14 | frnd_pass_len shared tail, no 2nd `or a` | APPLIED | 6 B (list said 5) | $7F7C |
| 15 | close_size_upd `sbc a,a` | APPLIED | 5 B (dwr_fail checked: ignores A/flags) | $7F7C |
| 16 | fopen_fill_body `jp clr_f306` | APPLIED | 4 B | $4E4B |
| 17 | BD_DAY/BD_MON swapped, `ld de,(BD_DAY)` | APPLIED | 4 B | $4C29 |
| 18 | dskio_bump `dec (hl)` | SKIPPED | premise false at the last sector: when the count reaches 0 the loop head does NOT reload HL, so DSKIO's exit HL would change from the last LSEC+1 to FDC_CNT's address | - |
| 19 | lay_page0_env `ldi` | SKIPPED | premise "BC is dead" false: dos_handoff_keep never sets BC before `call BOOT_ENTRY`, so BC (0 today, from install_dos_env's last LDIR) reaches the disk's boot code; ldi would change it | - |
| 20 | fdc_seek -> fdc_cmd (fdc_restore's store) | APPLIED | 3 B | $43A4 |
| 21 | cinl_store `ld hl,(CONIN_MAX)` | APPLIED | 3 B | $7F7C |
| 22 | fopen_fill_body >>7 via add hl,hl | APPLIED | 3 B | $4E4B |
| 23 | install_hook `ld (hl),n` | APPLIED | 2 B | $4392 |
| 24 | abs_ign inline $F306 clear | APPLIED | 2 B (flags incl. C identical) | $4E4B |
| 25 | seq_load offset from DE | APPLIED | 2 B (BC exit unchanged anyway: to_wrbytes' LDIR) | $461D |
| 26 | wa_stub on page0_ram_out's RET | APPLIED | 1 B | $41EF |
| 27 | conout_body `inc a` | APPLIED | 1 B | $7F7C |
| 28 | frl_cache `xor a` | APPLIED | 1 B | $7F7C |
| 29 | fopen_fill_body +30/+31 `xor a` | APPLIED | 1 B | $4E4B |
| 30 | abs_go `ld c,b` | APPLIED | 1 B | $4E4B |
| 31 | tok_payload `ld c,1 / jr z` | APPLIED | 1 B (disk; also assembled into sub.rom: builds) | $44F4 |
| 32 | fdc_issue helper | SKIPPED | LOW-MEDIUM (timing between command write and first poll) | - |
| M1-M9 | medium/high | SKIPPED | by rule | - |

No candidate was reverted.

Builds: `make -s build/disk.rom` rc 0 after every step. `make -s build/sub.rom` rc 0.
`make -s basic-reloc` rc 2, but every ROM/ABI check in it is OK; the one FAIL is the
citation audit: untracked `scratchpad/AE_bufinctl_keys.out`, cited by the owner's
uncommitted `todo/open/D-BUFINCTL.md` -- not from this slice.
`python3 tests/run.py`: ALL 100 TEST FILE(S) PASSED.

Files touched: disk/init.asm, disk/driver.asm, disk/fat.asm, disk/runtime.asm,
basic/tokpay-body.inc. disk/kernel.asm not touched.
