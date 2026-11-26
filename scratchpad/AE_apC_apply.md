# D-DISKREREAD slice C, applied: LOW-risk candidates only (2026-11-26)

## Method

The input was the slice C candidate list: disk/kernel.asm 3200-6100, basic/fat-delete-body.inc, basic/sv-diskwr.inc and basic/sv-savdisk.inc. Slices A and B had already landed.

Only the candidates marked **low** were applied. Every low-medium and medium one was skipped, and so was every sub-item of a candidate whose own risk was not low.

Each candidate went through the same steps, one at a time:

1. Re-check its premise against the CURRENT source. Labels, callers, flags at each entry and stack balance were re-grepped, since line numbers had moved after A and B.
2. Edit it, with a `; D-DISKREREAD (2026-11-26): <what>, N B` comment at the change.
3. Rebuild with `rm -f build/disk.rom && make -s build/disk.rom`. The return code was 0 every time.
4. Measure the run of trailing `$00` in front of EVERY pinned `ds $XXXX - $` entry, before and after. The only figure taken was the change, and it was always in the region the candidate named. No pinned entry moved: the image stays exactly 16384 B and each pin's `jp` sits at its address.

The arithmetic rewrites were checked exhaustively before they were applied. date_fat_word was checked for every year 1980..2099 x month x day. The sdate day test was checked for every day 0..255 x length 28..31.

## Applied

| id | what | region (pin) | claimed | measured |
|---|---|---|---|---|
| 22 | dos_clear_screen: CSRY/CSRX with one `ld ($F3DC),hl` ($0101) | R1 ($5E10) | 2 | 2 |
| 13a | gdate_core gc_yl: dead `or a` (CF = 0 from `and 3`) | R1 ($5E10) | 1 | 1 |
| 13c | gc_mond: `inc l / ld e,l` | R1 ($5E10) | 1 | 1 |
| 13d | sdate day check in E: `dec e / call month_len / dec a / cp e / jr c` | R1 ($5E10) | 3 | 3 |
| 13e | sdate year loop tested at the top | R1 ($5E10) | 2 | 2 |
| 12 | date_fat_word built in place in DE, one rotate, year from L | R1 ($5E10) | 6 | 6 |
| 14a | hk_aopen: status loaded before each `jr c`, the stubs gone | R2 ($5FE5) | 4 | 4 |
| 14b | hk_agetb: `sbc a,a / and 1` | R2 ($5FE5) | 2 | 2 |
| 23a | sav_fits moved in front of the fatfits include, so it falls into fat_fits | R2 ($5FE5) | 2 | 2 |
| 24a | basent_tramp `ld a,(hl)` ($FFC9 holds $C9 after the ldir) | R2 ($5FE5) | 1 | 1 |
| 24b | bcw_own: `jr nz,bcw_x` to a single `jp bdos_close_rd` | R2 ($5FE5) | 1 | 1 |
| 24c | frnd_update_size: `xor a / ld (ix+19),a` | R3 ($607B) | 1 | 1 |
| 18a | fsize_body: dead `push ix / pop de` | R4 ($75A5) | 3 | 3 |
| 18b | fsize_body: name pointer straight into HL | R4 ($75A5) | 1 | 1 |
| 18c | fsize_body: one shared `ld l,a / jp rrnd_finish` tail | R4 ($75A5) | 2 | 2 |
| 10a | wrblk_body RS: `ld e,(ix+14) / ld d,(ix+15)` | R4 ($75A5) | 2 | 2 |
| 10b | wrblk_body RR into WRBLK_REC through HL | R4 ($75A5) | 3 | 3 |
| 10c | wrblk_loop sector-in-file shifted in HL | R4 ($75A5) | 2 | 2 |
| 10d | wrblk_loop within: `ld de,(WRBLK_REC)`, masked in D, no `or a` | R4 ($75A5) | 2 | **3** |
| 10e | wrblk_loop: dead `or a` before the second sbc | R4 ($75A5) | 1 | 1 |
| 11 | wrblk_loop_done RR read straight into L/H | R4 ($75A5) | 2 | 2 |
| 2 | wrblk tail: loop_done `jr wzp_dirupdate`, one `ld hl,(WRBLK_REQ)`, wrblk_finish = `jp rrnd_finish` | R4 ($75A5) | 15 | 15 |
| 19 | wrblk_position_sec: dead `or a`, `ret z` for wpe_same | R4 ($75A5) | 4 | 4 |
| 16 | wroe: `add hl,de` for the reload, `jr c,wroe_have_valid` | R4 ($75A5) | 4 | 4 |
| 20 | fren_wild fw_lp: dead `pop hl / push hl` | R4 ($75A5) | 2 | 2 |
| 7 | seq_k_adv: K >> 7 as `ld a,l / rla / ld a,h / rla` | R4 ($75A5) | 7 | 7 |
| 17 | wrblk_shrink zero test walked down from to_wrbytes' HL | R4 ($75A5) | 4 | **3** |
| 21 | wshrink_walk: `call hl_cmp_eoc / add hl,de / jr c` | R4 ($75A5) | 3 | 3 |
| 9 | wshrink freeloop / atlast exits as `ret z` / `ret nc` / `ret c` | R4 ($75A5) | 9 | 9 |
| 24f | wshrink_empty: zero stored through DE | R4 ($75A5) | 1 | 1 |
| 24d | k47b2_xfer_rec: dead `or a` | R4 ($75A5) | 1 | 1 |
| 24e | setrnd_body: `ld (ix+36),a` after clr_f306 | R4 ($75A5) | 1 | 1 |
| 15 | fat_have_free_cluster: `ret c` / `ret z`, fhfc_found gone | R4 ($75A5) | 4 | 4 |
| 3 | wrrnd_extend: no +18/+19 stores, `ld h,a`, old - new and `ret nc` (`or a` kept) | R4 ($75A5) | 16 | 16 |
| 4 | disk_show_banner: `call hke_pr` | R4 ($75A5) | 9 | 9 |
| 6 | sav_data: one 16-bit compare, `jr z,disk_write_end` | R4 ($75A5) | 7 | 7 |
| 8b | fat-delete-body: `ret c` for `jr c,fdl_err` | R4 ($75A5) | 3 | 3 |
| 8c | fat-delete-body: fdl_marked moved up into fat_delete, its `jr` gone | R4 ($75A5) | 2 | 2 |
| 8d | fat-delete-body: FWR_DIRSEC kept on the stack, offset added through BC | R4 ($75A5) | 2 | 2 |

**Total measured: 138 B.** By pin: $5E10 +15, $5FE5 +10, $607B +1, $75A5 +112.

Two items measured differently from the claim. In both, the claim miscounted the OLD code's size; the logic is unchanged.

- **10d measured 3 B, claimed 2.** The old code was 16 B: `ld a,(nn)` 3, `and 1` 2, `ld d,a` 1, `ld a,(nn)` 3, `ld e,a` 1, `ld hl,512` 3, `or a` 1, `sbc` 2. The new code is 13 B. The list's figure looks like it left the `or a` out of the old size.
- **17 measured 3 B, claimed 4.** The old test was 11 B: `ld a,(nn)` 3, `ld hl,nn` 3, then 5 one-byte ops. The list said 12; the new form is 8 B.

`tools/check_disk_walls.py` now reports 424 B in runs of at least 16 B; it was 270 B. That is +154, not +138. The gaps in front of $5E10 (4 -> 19 B) and $5FE5 (9 -> 19 B) were too small to count before and now cross the 16 B threshold, so their whole length is added.

## Contract checks (registers and flags at each caller)

- **12 date_fat_word.** It returns DE as before. HL now holds the scratch value, not the old month/day, and BC is what gdate_core left. Both callers are covered: fcb_mark_written (kernel.asm) and dir_stamp_date (fat-prim-body.inc) push/pop HL around the call and treat BC as trashed.
- **13d sdate.** month_len keeps DE. D is no longer set to the month length, and nothing reads D before sd_mon reloads DE.
- **14 hk_aopen / hk_agetb.** These are reached by `jp` from the H_FOPEN dispatcher, and the return goes to main's chan_gate. Its cg_back reads only CF, and fopen_cross re-tests A with `or a`. hka_st still serves three users: hk_aopen, hk_agetb and the `jp hka_st` at kernel.asm ~6507. Each one sets A before it.
- **2 wrblk_finish (shared tail).** Its users are fat.asm's wrblk_full (sets A = 1 and HL), wrblk_ioerr/ioerr2 (A = 2, then HL through wrblk_fin_req), wzp_dirupdate (A = 0) and, via `jr`, wrblk_loop_done. rrnd_finish keeps A and F. clr_f306 touches only A, F and $F306, so HL survives as it did with the old push/pop.
- **3 wrrnd_extend.** The sole caller (the WRRND tail) tests only `jr c` and reloads A next.
- **7 seq_k_adv.** Callers: runtime.asm wrseq_wr_writeback and kernel.asm wrseq_writeback. Both `push hl` next and test no flag. B is no longer clobbered; the header comment was updated from "Clobber A, B" to "Clobber A, F".
- **9 / 21 wrblk_shrink.** The caller, wzp_shrink, tests only `jr c`. The stack is balanced at every new `ret`. When the walk falls through at EOC, DE = $0FF8, as before; wshrink_atlast does not read DE.
- **15 fat_have_free_cluster.** The sole caller (bsave, kernel.asm ~8804) tests only `jr nc`.
- **16 wroe.** HL and DE at wroe_have_valid equal the old values (HL - $FF8 and $FF8). The tail is `jp fat_read_file_sector`, which takes neither.
- **18 fsize_body.** fat_find takes HL only and stores it in FAT_NAMEPTR. fat_mount does not take DE, and DE still held the FCB pointer anyway.
- **19 wrblk_position_sec.** `ret z` returns the same flags `or a / ret` gave: A = 0, Z = 1, CF = 0. The caller tests only `jp c`.
- **8 fat-delete-body.** basic/fat-delete-body.inc is included only by disk/kernel.asm; the sub-ROM no longer includes it. Callers of fat_free_chain test CF. rs_dbuf -> rh_check does not write FWR_DIRSEC; it is written only by fat_find, new_taken and the close stamp. So the pushed value equals the one the old code reloaded.
- **6 sav_data.** basic/sv-savdisk.inc is included only by disk/kernel.asm. disk_write_end is entered with Z = 1 and CF = 0, as before, and it does not read A.

## Skipped

- **1 (hk_cv = hkcv_float, 17 B):** low-medium. It depends on main's pu_deref_body not writing FACTYP.
- **5 (month_len computed, 13 B):** low-medium.
- **13b (gc_mon `or a`):** low-medium, because it leans on month_len's returned CF.
- **8a (fdl_free 0/1 / >= $FF8 test, 10 B):** low-medium. It behaves differently for HL >= $1000.
- **18 medium variant (`sbc a,a` tail):** medium. It changes N and P/V on return.
- **23b (sav_fits `inc hl / inc hl`):** low-medium.
- **25 (dsel_bdos CR LF + text, 4 B):** medium. It crosses regions and costs 2 B in driver.asm's region.
- **3's extra `or a` (1 B):** relies on hl_x128's implicit carry. It was kept, as the list's low count did.

No low candidate's premise was false against the current source.

## Reverted

None.

## Checks run

- `rm -f build/disk.rom && make -s build/disk.rom` after every edit: rc 0 each time. Only the pre-existing "never used" / "3 pass" warnings appeared, plus pre-existing basic-reloc warnings once a basic/*.inc changed.
- The per-pin trailing-fill measurement before and after each edit (the table above).
- `python3 tools/check_disk_walls.py`: OK, 424 B in 11 runs >= 16 B.
- `make -s basic-reloc`: rc 0. The dead-code readout gives `disk: 1144 spans, 133 seeds -> 0 dead`; main and sub are also 0 dead.
- disk/basic-resident-abi.inc was regenerated by the build and is byte-identical (not modified in git).
- `python3 tests/run.py`: ALL 100 TEST FILE(S) PASSED (rc 0).
- Not run, as instructed: emulators, gates, `make repack-machine` and probes. The date (SDATE / GDATE / FAT stamp), WRBLK / WRRND / RDBLK, FSIZE, SETRND, KILL, SAVE, MERGE / ASCII LOAD, $4022 BASENT and the banner paths are all changed and are UNPROVEN until the disk gates run.

## Observations (not changed)

- **fat.asm wrblk_full** (`ld a,1 / ld hl,(WRBLK_REQ) / jp wrblk_finish`) could `jp wrblk_fin_req` now that the label exists. That saves 3 B in front of the $46E6 pin, but `jp` reach must be checked. It was not in slice C's list.
- **basic/sv-savdisk.inc comments.** The header and kernel.asm's include comment named `sav_fin`, which is gone; both now say `sav_data`. One new D-DISKREREAD comment mentions sav_fin's old `jr`, on purpose.
- **Stale comment in hk_cv (candidate 1, untouched).** The comment "RELOAD: the call clobbers A" and its $28C1 address look stale, per the list. Not verified.
- **Unreferenced labels on live code** are left in place: `fdl_marked`, `k47b2_pos_done`, `wrblk_ioerr2` (still used), `bcw_x` (new) and `basent_tramp_end`, which now sits on sav_fits. The dead-code sweep is clean.
