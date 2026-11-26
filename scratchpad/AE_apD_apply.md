# D-DISKREREAD slice D: applying the low-risk candidates

Input: `scratchpad/AE_reread_D.md` (slice D of the read-only re-read: disk/kernel.asm
6100-9243 + basic/fat-prim-body.inc). Applied on top of slices A/B/C (a89a93d15,
6fc519f4d, 5d02d1a8f). No git operations, no emulator, no gates.

## Method

For each LOW-risk candidate, one at a time:

1. Re-checked the premise against the current source. Line numbers had shifted by about
   40 lines, and FAT_B0/B1 are `$ECC4/$ECC5` in disk/equates.inc, not sysvars.inc. No
   premise had been consumed by A/B/C.
2. Made the edit with a `D-DISKREREAD (2026-11-26): <what>, N B` comment at the change.
3. Ran `rm -f build/disk.rom && make -s build/disk.rom`: rc 0 every time, with only the
   pre-existing warnings.
4. Measured the change in the run of trailing `$00` before every pinned `ds $XXXX - $`
   entry. A throwaway script in the session scratchpad diffed it against a checkpoint
   taken after the previous candidate. Where the measured figure differed from the claim,
   I recounted the encodings by hand (see the table notes).

Confirmed first: `basic/fat-prim-body.inc` (and fat-delete-body.inc) are included only by
disk/kernel.asm. sub/fatprim.asm mentions it only in a comment. So nothing here changes
the main or sub-ROM builds.

## Applied

| id | what | region (pin) | claimed | measured |
|---|---|---|---|---|
| 1 | fat_mount: word BPS test, accumulate onto RSVD, `call hl_x32`, FIRSTROOT via stack, C=SPC from the top, DE starts at 2, drop final `or a` | $75A5 | 23 | 23 |
| 2 | `fat_b01` helper shared by fnc_have and fac_entry_from_wbuf | $75A5 | 22 | 22 |
| 3 | fnc_combine: `rrd` nibble rotate of the adjacent B0/B1, one word load | $75A5 | 20 | 20 |
| 4 | fcf zero test: byte1 in C, one OR per case, no FAT_B1 write | $75A5 | 16 | 16 |
| 5 | delete name_cmp_wild; its 2 callers call name_cmp | $7F7C | 14 | **17** (a) |
| 6 | dirscan_match: shift SRCHIDX>>4 once, push/pop it | $7F7C | 14 | **12** (b) |
| 7 | df_emit: the head calls the tail's room test (`df_room`) | $75A5 | 12 | 12 |
| 8 | dsm_found DTA build: drop push/pop, walk DE/HL on from ldir_11 | $7F7C | 12 | 12 |
| 9 | wr_reset as an 11-byte fill loop (+ assembly-time contiguity guard) | $75A5 | 10 | 10 |
| 10 | mulacc_cmp as a 4-pass loop | $77B8 | 10 | 10 |
| 11 | KILL's "file open" arm: `jr c,hkn_open` | $75A5 | 9 | 9 (11+12 = 18) |
| 12 | COPY's two `jr c,hkc_open` go to hkn_open; hkc_open deleted | $75A5 | 9 | 9 |
| 13 | `slot_rec` helper shared by ff_found and fdcr_useslot | $75A5 | 9 | 9 |
| 14 | fcf byte fetch: straddle test first, same-sector case falls through | $75A5 | 11 | 11 |
| 15 | read/write sector entries moved in front of dskio_calslt; both fall in; `ld bc,$0100` | $75A5 | 8 | 8 |
| 16 | de_name/de_ext: drop push/pop around df_out | $75A5 | 8 | 8 |
| 17 | fwe_same_odd: masked merge + nibble swap | $75A5 | 7 | 7 |
| 18 | k47b2_seek: `ld hl,(WRBLK_REC+1)` | $77B8 | 5 | 5 |
| 19 | fat_dir_update: `inc hl` to +28, no push/pop/add | $75A5 | 5 | 5 |
| 20 | ff_found field reads walk on to +28 | $75A5 | 5 | **4** (c) |
| 21 | ff_found `ldir` -> copy4 | $75A5 | 2 | 2 |
| 21 | fat_dir_update `ldir` -> copy4 | $75A5 | 2 | 2 |
| 21 | fat_read_fat_sector -> `jp rd_fatsec` | $75A5 | 4 | 4 |
| 21 | fac_straddle -> `call rd_fatsec` | $75A5 | 4 | 4 |
| 21 | fwe straddle test `inc bc / dec b / dec b` | $75A5 | 4 | 4 |
| 21 | ffds success tail `ld hl,FWR_SECIDX / inc (hl) / ret` | $75A5 | 4 | 4 |
| 21 | fdcr: one zero loop of 21 | $75A5 | 4 | **3** (d) |
| 21 | fdir_wrback: `jp fws_mbuf` | $75A5 | 3 | 3 |
| 21 | fwe_odd0 masked merge | $75A5 | 3 | 3 |
| 21 | fwe even byte1 masked merge | $75A5 | 2 | **3** (e) |
| 21 | ffds pad loop as do-while | $75A5 | 2 | 2 |
| 21 | ffds `push/ex/pop/push` -> `ex/push` | $75A5 | 2 | 2 |
| 21 | fac_found `inc/ld/dec` | $75A5 | 1 | 1 |
| 21 | fwe even byte0 `ld (hl),e` | $75A5 | 1 | 1 |
| 21 | fwe_finish `or a` dropped | $75A5 | 1 | 1 |
| 21 | fwe_err `scf` dropped | $75A5 | 1 | 1 |
| 22 | fdel_body success tail -> `jr fdel_ok` | $7F7C | 4 | 4 |
| 22 | k47b2 `ld hl,(WRBLK_REC) / ld a,h / and 1 / ld h,a / or l` | $77B8 | 3 | 3 |
| 22 | fdc_rd_status `ret z`; fdc_rd_ok deleted | $7F7C | 3 | 3 |
| 22 | rdrnd -> `jr wrrnd_zero` | $7F7C | 3 | 3 |
| 22 | fmt_pr push/pop hl dropped | $75A5 | 2 | 2 |
| 22 | wrbytes_add_recsize as one adc loop | $75A5 | 2 | 2 |
| 22 | ws_walk EOC test, 16-bit `add/adc` | $77B8 | 2 | 2 |
| 22 | ga_fail `ld d,a/e,a/h,a/l,a` | $7F7C | 2 | 2 |
| 22 | fcb_mark_written `xor a / ld (hl),a` x2 | $77B8 | 1 | 1 |
| 22 | bsw_m34_needclus `jr c,bsw_full / jr bsw_m34_buffer` | $7F7C | 1 | 1 |
| 22 | mf_find `push ix / pop hl / inc hl` | $7F7C | 1 | 1 |

**Total measured: 293 B.** By pin: $75A5 116 -> 333 (+217), $77B8 1 -> 22 (+21),
$7F7C 24 -> 79 (+55). `tools/check_disk_walls.py`: 424 -> 718 B in runs of 16 B or more.
(The $77B8 fill is 22 B and the $7F7C fill 79 B; both now count in the 16-B readout.)

Notes on differences:
- (a) 5: name_cmp_wild was 17 B (`ld b,11` 2, `ld a,(de)` 1, `cp` 2, `jr` 2, `ld a,(de)` 1,
  `call` 3, `ret nz` 1, inc/inc 2, `djnz` 2, `ret` 1). The claim undercounted it.
- (b) 6: the code removed after the first shift was 25 B and its replacement is 13 B. The
  claim's "38 -> 24" was a miscount.
- (c) 20: kept `ld a,(hl) / ld e,a` instead of `ld e,(hl)`, at a cost of 1 B. That way
  fat_find's exit A (the cluster's low byte) and Z (from the kept `or a`) stay exactly as
  before. Without it, Z would come from nc_ptr's last compare, and fat_find has 12 callers
  (one, at kernel 6588, returns its flags as hk_srcfind's). Exit A, F, HL, DE and BC are now
  identical to the old code.
- (d) fdcr zero: the old code was 10 B and the new is 7 B (the claim said 4).
- (e) fwe even byte1: the old code was 9 B and the new is 6 B (the claim said 2).

## Contract checks

- **fat_mount** (1): the success exit is unchanged: A=0, Z=1, Cy=0 (from `xor a`, with
  only `ld`s after it), HL=2, DE=TOTCLUS, B=0, C=SPC. On the bad path only A differs, and
  it is not a code. C survives from the `ld c,a` to fm_div: djnz, `call hl_x32` (HL and
  flags only, driver.asm:433), `srl e`, push/pop and sbc do not touch it.
- **fnc_combine / fat_next_cluster** (3): HL is the entry and Cy=0 (from `and`). A=H now.
  Callers: kernel 2688 (push/pop af around it), 4872 (hl_cmp_eoc), 4880 and 4902 (store
  HL), 7740 (`ld a,h`), 7903 (pop de / dec de), 8914 (ex (sp),hl), fat-delete-body 78
  (ex de,hl), fat_advance -> fat_open_at (`xor a`). None reads A or Z.
  fac_entry_from_wbuf -> fac_comb: callers fac_have_sec (`ld a,d / or e`), fat.asm
  frnd_next (`or a`), and runtime fac_cached_entry -> kernel 5153 (`ret c`) and 8448
  (`jr c`). Cy=0 holds on both paths.
- **fat_b01** (2): BC is clobbered on fac's non-straddle path. Every path that reaches it:
  fac_loop (DE/HL only); fhfc_loop (DE/HL only); ga_scanloop (pops BC each pass);
  frnd_next -> frl_have (BC already clobbered by that path's read). HL at fac_comb is
  still &MBUF[idx+1], so the "HL IS KEPT" note still holds.
- **FAT_B0/FAT_B1** (3, 4): writers and readers are only fnc_combine, fat_b01 and fcf, and
  fcf writes its own B0. FAT_B1 is now written only by fnc_combine. The `rrd` rotation
  changes the cells, and no one reads them afterwards.
- **fcf** (4, 14): B, C and D/E are dead in the loop. fcf_free, fcf_used and fcf_loop
  reload everything from RAM.
- **fat_find** (13, 20, 21): exit registers and flags are identical to the old code (see
  note c). slot_rec keeps A and HL.
- **fdir_wrback** (21): its callers are fat_dir_create (fall-through) and fat_dir_update
  (`jr`). dc_result's success exit is `xor a`, which gives the same A and flags as the old
  `or a` with A=0. Its error exit is unchanged.
- **fwe_finish / fwe_err** (21): `or 2` and `or a` on the same A set the same flags. Both
  `fwe_err` referrers are `jr c`. B/C are no longer set on the even and odd store paths;
  fat_write_buf_allfats loads B itself, and fwe_byte1 reloads BC.
- **fat_flush_data_sector** tail (21): Cy=0 and Z/S follow the `inc`; A and HL differ.
  Callers: kernel 2134 (`jp c`), 2807 (pop bc / `jr c`), 7570 (`jp c`), 8828 (`jr c`),
  fatiow 63 (pop bc / `ret c`), fatiow 116 (`ret c`). All test Cy only, and the next
  instruction reloads A/HL or does not read them.
- **name_cmp** (5): these are the same instructions with the same registers in and out.
  Both callers (kernel 4702, 8577) see no change.
- **df_emit** (7): df_room returns `nc` (room) to de_field. Otherwise it falls into
  df_crlf -> df_out, whose `ret` returns to de_field. df_out keeps HL/DE/BC; B is reloaded
  at de_field.
- **dsm_found** (8): DE = DTAPTR base + 16 by walking. DOS_DTAPTR is the base DE came from
  (set by dsm_p1_pre).
- **wr_reset** (9): A=0, HL=0 and the flags of `xor a` are as before; B=0 is new. Callers:
  kernel 1654 (uses HL=0, then `ld a,1`, `xor a`, ret; B is junk to BDOS as before) and 2098
  (reloads HL; hkc_loop does not read B). An `IF` guard fails the assembly if
  WRCLUS..WRBYTES+3 ever stops being 11 contiguous bytes.
- **mulacc_cmp** (10): Z/Cy mean the same (16-bit dec and djnz keep the last `cp`'s
  flags). DE and B are newly clobbered. Callers: wrblk_zero_path -> wzp_decided (`jr c`)
  -> wrblk_size_max (to_wrbytes loads DE/BC) or wrblk_shrink (to_wrbytes first); kernel
  4803 wrblk_size_max (same).
- **hkn_open as KILL's and COPY's arm** (11, 12): DISKOP_ERR=64, A=2, then
  hk_claim_status; hkk_done, hkn_done and hkc_done all end there. The stack is balanced at
  every jump (COPY's push/pop af happens before the second `jr c`).
- **fdc_rd_status** `ret z` (22): A=0, Z, Cy=0 as before; only H differs (`and` sets H).
  Not in the polling loop.
- **wrbytes_add_recsize** (22): A=0 out now. The one caller (kernel 8777) calls
  fat_flush_data_sector next, which takes no A.
- **fcb_mark_written** (22): A=0 and Z now, where they were junk. Callers: kernel 7632
  (`ld (hl),$40`), 7778 (`ld a,(...)`), 9108 (wrrnd_extend reloads A from ix+18), runtime
  792 (pop hl / seq_k30 loads A). None reads them.
- **ws_walk** (22): fat_next_cluster's HL is 12-bit (H <= $0F, now also by construction in
  fnc_combine), so `HL >= $0FF8` equals the old two-byte test. ws_ok does not read A, and
  the EOC path reloads A.
- **mf_find** (22): fat_find reads no DE, and fat_dir_start -> fat_rootsecs overwrites DE
  before any exit, so DE out is unchanged.
- **fdel_ok, wrrnd_zero, bsw_full, ga_fail**: each jump target is byte-identical to the
  code it replaces. ga_fail's A=0 comes from clr_f306's `xor a`.
- **Section 15** (the sector entries): DSKIO sees the same A=0, B=1, C=0 and Cy. rh_check's
  hit path still drops read_sector's return. Nothing falls into fws_mbuf: kernel 5953 is a
  `ret`.

## Skipped

- All Tier-2 rows (mnt_find's first push/pop, the `ld bc,nn` skip trick, fcf `or a`,
  fac_found `or a`, fat_read_file_sector `or a`, fcf `jp` -> `jr`). They are medium or
  low-medium risk, so out of scope.
- Nothing low-risk was skipped. Every premise held against the current source. Slices
  A-C had touched neighbouring lines (for example wzp_dirupdate and fhfc_loop), but none
  of this slice's candidates.

## Reverted

- None. One partial adjustment: in candidate 20 the `ld e,(hl)` became `ld a,(hl) / ld e,a`
  to keep fat_find's exit A/Z (1 B less than claimed; see note c).

## Checks run

- `make -s build/disk.rom`: rc 0 after every candidate.
- `python3 tools/check_disk_walls.py`: OK, 718 B in runs of 16 B or more (was 424).
- `make -s basic-reloc`: rc 0, and the dead-code check reports 0 dead in main, sub and disk.
- `python3 tests/run.py`: ALL 100 TEST FILE(S) PASSED.
- No emulator, gate or `repack-machine` runs.

## Observations

- The re-read's premise correction holds: fat-prim-body.inc is disk-only. The prose that
  says otherwise is still stale and was not touched: basic/main.asm:46-48, and the
  fat_locate note in kernel.asm about "the sub ROM assembles that body too".
- Three of the five figures that differed were hand-count errors in the candidate list.
  The fourth (note c) was a deliberate 1-B cost. The candidate's "keep the `or a`" advice
  alone would not have kept Z, because A had changed.
- The fcf/fwe/fac/fnc straddle tests now all use the same `inc / dec d / dec d` idiom,
  which encodes D-FATSTRAD's 9-bit rule (idx == 511) directly.
- No RAM `equ` moved. No pinned entry moved: every `ds` pad assembled non-negative, and
  check_disk_walls parsed all 66 pins.
