# Re-read C: disk/kernel.asm 3200-6100 + fat-delete-body.inc, sv-diskwr.inc, sv-savdisk.inc

I only read code. Nothing was edited or built. Addresses come from build/disk.sym (2026-11-26 04:21).

Regions the slice falls in (a saving turns into $00 fill in front of the NEXT pin, and no pinned label moves):
- **R1**: ... up to `ds $5E10 - $` (kernel 3200-3533: frnd_calc $5C86, sdate/gdate/month_len $5D65, dos_clear_screen $5DEE)
- **R2**: $5E10 .. `ds $5FE5 - $` (basent_body, fat_fits, sav_fits, hk_aopen, hk_format, stmt_hdl, hk_system, init_gate, bcw_own, fmt_err)
- **R3**: $5FE8 .. `ds $607B - $` (fat_rand_put .. cpmver_body)
- **R4**: $607E .. `ds $75A5 - $` (p0_env_tab .. hk_dpsave, including fat-delete-body / sv-diskwr / sv-savdisk)

No candidate moves a pinned label or changes a pinned 3-byte entry. Ranked by bytes x confidence; R = region.

Notes on the checks:
- Each piece of arithmetic marked "verified" was checked EXHAUSTIVELY in Python: every month x year 0..119; every year 1980..2099 x month x day; every K 0..65535; every cluster 0..$FFF; every length x day.
- "Label local" means I grepped disk/ basic/ sub/ (`*.asm`, `*.inc`, comments excluded) and found no reference outside the lines named. I also checked that nothing falls through into it.

---

## 1. hk_cv: the CVI arm IS hkcv_float -- 17 B, low-medium, R4
kernel.asm:5499-5509

**Now** (after `call pu_deref_body`):
```
ld a,c / cp 2 / jp nz,hkcv_float / ld e,(hl) / inc hl / ld d,(hl) / ld (FAC),de / ld a,2 / ld (FACTYP),a / scf / ret   ; 20 B
```
**Proposed:** `jp hkcv_float` (3 B)

**Why it is safe:**
- hkcv_float ($50A2) is `ld de,FAC / ldir / scf / ret`, and BC = the width (C = FACTYP, B = 0, set before the call).
- For width 2 the ldir copies (HL),(HL+1) to FAC,FAC+1, which is exactly what `ld (FAC),de` stores.
- `ld (FACTYP),2` writes back the value FACTYP already held: it was read as 2 at entry, and only pu_deref_body runs in between. That routine (basic/str-engine.asm:452, mapped to $2C7E) only reads the descriptor; it does `push af / ... / pop af` and touches no RAM.
- So the int arm and the float arm do the same thing. scf / ret are identical too.
- Side finding: the comment "⚠️ RELOAD: the call clobbers A" is false. pu_deref_body keeps A. The comment's $28C1 is also stale: the ABI file says $2C7E.

**Risk:** low-medium. It depends on main's pu_deref_body not writing FACTYP. A CVI / CVS / CVD row on kwsweep proves it.
Variant: inline the 7-byte hkcv_float body here (+4 B in R4) and free 7 B in front of $50A9.

## 2. wrblk_body tail: three exits share one tail, and wrblk_finish = rrnd_finish -- 15 B, low, R4
kernel.asm:4347-4394

**Now:**
- wrblk_loop_done ends `call wrblk_fcb_keep / xor a / ld hl,(WRBLK_REQ) / jr wrblk_finish`. That is byte-for-byte wzp_dirupdate's body.
- wrblk_ioerr repeats the `ld hl,(WRBLK_REQ)`.
- wrblk_finish is `push af / push hl / call clr_f306 / pop hl / pop af / ret`.

**Proposed:**
```
wrblk_loop_done: ...                               ; unchanged through `call wrblk_set_wrfirst`
                jr   wzp_dirupdate                 ; (replaces call wrblk_fcb_keep/xor/ld hl/jr: -7)
...
wzp_dirupdate:  call wrblk_fcb_keep
                xor  a
                jr   wrblk_fin_req                 ; (-3: one ld hl shared)
wrblk_ioerr:
wrblk_ioerr2:   ld   a,2
wrblk_fin_req:  ld   hl,(WRBLK_REQ)
wrblk_finish:   jp   rrnd_finish                   ; (8 B -> 3 B: -5)
```

**Why it is safe:**
- clr_f306 (kernel.asm:1479) is `xor a / ld ($F306),a / ret`. It never touches HL, so the push/pop of HL is dead.
- rrnd_finish ($7BEA) is `push af / call clr_f306 / pop af / ret`, so its A, F and HL are identical to wrblk_finish's.
- The external `jp wrblk_finish` (fat.asm:141) still resolves.
- wzp_dirupdate is ~25 B below the jr: in reach.

**Risk:** low.

## 3. wrrnd_extend: the +18/+19 stores write zeros that are already there -- 16 B (17 without the safety `or a`), low, R4
kernel.asm:5223-5255

**Now:** 50 B.

**Proposed:**
```
ld a,(ix+18) / or (ix+19) / ret nz          ; A = 0 from here
ld l,(ix+33) / ld h,a / inc hl / call hl_x128 ; HL = newsize
ld e,(ix+16) / ld d,(ix+17)                  ; DE = oldsize
ex de,hl / or a / sbc hl,de                  ; old - new: CF iff new > old
ret nc                                       ; no extension, CF = 0 (was wre_noext)
ld (ix+16),e / ld (ix+17),d
xor a                                        ; CF = 0
ret
```
That is 34 B.

**Why it is safe:**
- The `ret nz` guard means (ix+18)|(ix+19) = 0 on every path that reaches the stores, so `ld (ix+18),0 / ld (ix+19),0` (8 B) are no-ops.
- A = 0 there, so `ld h,0` becomes `ld h,a`.
- Equal sizes give `ret nc` (no extension), as the old `jr z`.
- The sole caller, kernel.asm:9199, tests only `jr c`. The header says AF/BC/DE/HL are trashed.
- The `or a` can go too (17 B): hl_x128 (driver.asm:430) ends in `add hl,hl`, and (r0+1)*128 <= $8000 never carries. That leans on an implicit flag, so I kept the `or a` in the low-risk count.

**Risk:** low.

## 4. disk_show_banner: its print loop IS hke_pr -- 9 B, low, R4
kernel.asm:5284-5292

**Now:** the dsb_lp loop (12 B): `ld a,(hl)/or a/jr z/inc hl/push hl/call CHPUT/pop hl/jr`.

**Proposed:** `call hke_pr` (3 B); dsb_end's pops follow.

**Why it is safe:**
- hke_pr ($667B) prints the 0-terminated string at HL through CHPUT and returns CF=1. The pop af restores the caller's flags, so every register is still preserved, as init requires.
- hke_pr already relies on CHPUT keeping HL, so the push/pop in dsb_lp guards nothing that hke_pr does not already assume.
- The same page-0 condition holds: drv_select at kernel.asm:659 uses hke_pr direct, as the banner uses CHPUT direct.
- The `k_7F7C: jp disk_show_banner` pin is untouched.

**Risk:** low.

## 5. month_len computed, month_days table dropped -- 13 B, low-medium (verified), R1
kernel.asm:3385-3404

**Now:** 23 B of code + the 12 B table.

**Proposed** (22 B):
```
month_len:      ld   a,b
                cp   1
                jr   z,ml_feb
                cp   7
                sbc  a,$FF          ; A = B + (B >= 7)
                and  1
                xor  31             ; even -> 31, odd -> 30
                ret
ml_feb:         ld   a,c
                and  3
                ld   a,28
                ret  nz             ; not a leap year
                inc  a              ; 29
                ret
```

**Why it is safe:**
- Verified exhaustively for B 0..11 x C 0..119 against the table.
- It keeps BC/DE/HL (it touches only A, F), as the contract says.
- It returns CF = 0 on every path, as the old one did (`cp 28` with A >= 28). Candidate 13b relies on that.
- Callers: 3267, 3279, 3360 only. month_days is referenced only at 3387.

**Risk:** low-medium (a rewrite, but a pure function). The date gate (SDATE / GDATE rows, FAT stamps) proves it.

## 6. sav_data loop -- 7 B, low, R4
basic/sv-savdisk.inc:57-75 (disk-only include)

**Proposed:**
```
sav_data:       ld   hl,(DSV_PTR)
                ld   a,(hl)
                call disk_putbyte
                ld   hl,(DSV_PTR)
                ld   de,(DSV_END)
                or   a
                sbc  hl,de
                jr   z,disk_write_end     ; was jr z,sav_fin / sav_fin: jr disk_write_end
                add  hl,de
                inc  hl
                ld   (DSV_PTR),hl
                jr   sav_data
```
This removes the reload of HL at sav_next (HL already = DSV_PTR), the byte-wise compare and the sav_fin hop.

**Why it is safe:**
- sav_next / sav_fin are local; sav_fin is only named in a kernel.asm comment.
- disk_write_end (sv-diskwr.inc) is ~55 B back: in jr reach.
- disk_putbyte clobbers all, so the `or a` stays.
- The only include is disk/kernel.asm:6050 (scratchpad copies aside).

**Risk:** low.

## 7. seq_k_adv: K >> 7 without the loop -- 7 B, low (verified), R4
kernel.asm:4787-4795

**Now:** `push hl / ld b,7 / ska_shr: srl h / rr l / djnz / ld a,l / pop hl` (11 B)

**Proposed:** `ld a,l / rla / ld a,h / rla` (4 B) gives A = (H<<1)|(L>>7) = low byte of K>>7.

**Why it is safe:**
- HL is kept.
- Callers runtime.asm:789 and kernel.asm:381 do `push hl` next and test no flags. B was clobbered before, so nobody relies on it.

**Risk:** low.

## 8. fat-delete-body.inc -- 17 B total, R4 (disk-only include: grep finds only disk/kernel.asm:6021)

**8a. Clusters 0/1 or >= $FF8 test** (fdl_free..fdl_hi, lines 45-59): 10 B, low-medium (verified for 0..$FFF).

Now: `ld a,h/or a/jr nz,fdl_hi/ld a,l/cp 2/jr c,fdl_done/jr fdl_isdata/fdl_hi: cp $0F/jr c,fdl_isdata/ld a,l/cp $F8/jr nc,fdl_done` (20 B) + `fdl_done: or a/ret` (2 B)

Proposed:
```
fdl_free:       ld   a,l
                cp   $F8
                ld   a,h
                sbc  a,$0F          ; CF iff HL < $FF8
                ret  nc             ; end of chain, CF = 0
                ld   a,l
                and  $FE
                or   h
                ret  z              ; cluster 0/1, CF = 0
fdl_isdata:     ...
```
- fdl_done / fdl_hi are local.
- HL >= $1000 differs from the old code (the old one called $1000..$FFFF with L < $F8 "data"). That never happens in FAT12: fat_next_cluster gives 12-bit values.

**8b. `jr c,fdl_err`** becomes `ret c` (CF is already 1, the stack is balanced after `pop hl`). fdl_err (`scf / ret`) goes. 3 B, low.

**8c. Move the fdl_marked block** straight after fat_delete's `call fat_free_chain / ret c` and drop `jr fdl_marked`. fat_free_chain follows as its own entry (fdl_marked ends in `jp`, so nothing falls into it). 2 B, low.

**8d. fdl_marked:** `ld de,(FWR_DIRSEC) / push de / call rs_dbuf / pop de / ret c / ld hl,(FWR_DIROFF) / ld bc,FAT_DBUF / add hl,bc / ld (hl),$E5 / ld hl,FAT_DBUF / jp fatprim_write_sector`. This drops the second `ld de,(FWR_DIRSEC)`. fatprim_write_sector sets B and C itself (fat-prim-body.inc:183). 2 B, low.

## 9. wshrink_freeloop / atlast exits -- 9 B, low, R4
kernel.asm:4905-4935

- `jr z,wshrink_freedone` becomes `ret z` (CF = 0 after `or l`).
- `push hl / call hl_cmp_eoc / pop hl / jr nc,wshrink_freedone` becomes `call hl_cmp_eoc / add hl,de / ret nc`.
- Both `jr c,wshrink_ioerr` (4905, 4927) become `ret c`.
- wshrink_freedone (2 B) and wshrink_ioerr (2 B) are deleted.

**Why `add hl,de` works:** hl_cmp_eoc (kernel.asm:8051) is `ld de,$FF8 / or a / sbc hl,de / ret`. `add hl,de` restores HL and its carry has the SAME sense: CF = 1 iff HL < $FF8. Checked case by case. The existing fdel loop at kernel.asm:8962 already uses this idiom.

**Why it is safe:** the stack is balanced at each ret. The caller (wzp_shrink) tests only `jr c`. Both labels are local.

**Risk:** low.

## 10. wrblk_body / wrblk_loop: register loads -- 10 B, low, R4
kernel.asm:4224-4339
- **4224-4229** RS: `ld e,(ix+14) / ld d,(ix+15) / ld a,d / or e` instead of four `ld a`/`ld r,a`. 2 B.
- **4235-4240** RR into WRBLK_REC: `ld l,(ix+33) / ld h,(ix+34) / ld (WRBLK_REC),hl / ld a,(ix+35) / ld (WRBLK_REC+2),a`. 3 B. HL is reloaded at once with `ld hl,(WRBLK_REQ)`.
- **4285-4290** `ld hl,(WRBLK_REC+1) / srl h / rr l / ld b,h / ld c,l`. 2 B.
- **4293-4300** `ld de,(WRBLK_REC) / ld a,d / and 1 / ld d,a / ld hl,512 / sbc hl,de`. 2 B. The `or a` goes because `and 1` cleared CF.
- **4304** `or a` before the second `sbc hl,de`: CF = 0 already (512 - within never borrows; push / ld leave flags). 1 B.

**Risk:** low.

## 11. wrblk_loop_done RR read -- 2 B, low, R4
kernel.asm:4334-4337: `ld l,(ix+33) / ld h,(ix+34)`.

## 12. date_fat_word -- 6 B, low (verified), R1
kernel.asm:3410-3428

**Proposed** (after `call gdate_core`):
```
ld a,l / sub $BC / add a,a / ld h,a          ; (year-1980)<<1; only L matters, year-1980 < 120
ld a,d / rrca / rrca / rrca / ld l,a          ; bit 0 = month>>3, bits 7..5 = month<<5
and 1 / or h / ld d,a
ld a,l / and $E0 / or e / ld e,a
ret
```

**Why it is safe:**
- Verified for every day 1980-2099 against `(y-1980)<<9 | m<<5 | d`.
- Callers kernel.asm:7661 and fat-prim-body.inc:1269 both push/pop HL around the call and treat BC as trashed. The new code trashes AF and HL only (plus gdate_core's BC).

**Risk:** low.

## 13. gdate / sdate small ones -- 7 B, R1
- **a.** kernel.asm:3351 `or a` at gc_yl is dead: `and 3` cleared CF and `jr nz` / `inc de` keep it. 1 B, low.
- **b.** kernel.asm:3363 `or a` in gc_mon is dead: month_len returns CF = 0 (old or new, see 5). 1 B, low-medium.
- **c.** kernel.asm:3370-3372 `ld a,l / inc a / ld e,a` becomes `inc l / ld e,l` (L is overwritten next). 1 B, low.
- **d.** kernel.asm:3264-3273, the sdate day check. Now `ld a,e/dec a/push af/call month_len/ld d,a/pop af/cp d/jr nc,sd_bad/ld l,a/ld h,0` (14 B). Proposed `dec e/call month_len/dec a/cp e/jr c,sd_bad/ld l,e/ld h,0` (11 B). Verified for day 0..255 x length 28..31 (day 0 wraps to 255 and is refused). month_len keeps DE. D is not used before sd_mon sets it. 3 B, low.
- **e.** kernel.asm:3284-3299, sd_yr loop tested at the top: `sd_yr: ld a,c/or a/jr z,sd_store/dec c/ld de,365/ld a,c/and 3/jr nz,sd_yadd/inc de/sd_yadd: add hl,de/jr sd_yr` (17 vs 19). 2 B, low. All sd_* labels are local.

## 14. hk_aopen / hk_agetb -- 6 B, low, R2
kernel.asm:3648-3686

**hk_aopen (4 B):** `call fat_mount / ld a,3 / jr c,hka_st / call fat_io_find / ld a,1 / jr c,hka_st / xor a / hka_st: ...`. The hka_nf / hka_io stubs go.
- `ld` leaves flags alone, so the flags at hka_st are identical.
- fat_io_find (fatio-body.inc:37) starts with ff_name and takes no A.
- hka_nf / hka_io are local.

**hk_agetb (2 B):** `call fat_io_getbyte / ld c,a / sbc a,a / and 1 / jr hka_st`. hkg_st goes.
- Only the Z flag differs on return, and nobody reads it: main's dsk_agetbyte (basic/files.asm:2213) decodes DISKOP_STATUS through fopen_cross, and hka_st does `scf`.

## 15. fat_have_free_cluster exits -- 4 B, low, R4
kernel.asm:5182-5195
- `jr z,fhfc_found` becomes `ret z` (CF = 0 after `or e`). fhfc_found (`or a / ret`) goes.
- `jr c,fhfc_none` becomes `ret c` (stack balanced after `pop hl`).
- The `jr nc,fhfc_none` site keeps fhfc_none's `scf`.

## 16. wroe (wrblk_read_or_extend_sector) -- 4 B, low, R4
kernel.asm:4513-4516
- `ld hl,(FAT_CURCLUS)` (reload) becomes `add hl,de`. DE = 2 and HL = cluster - 2 with no borrow, so this restores HL. 2 B.
- `jr nc,wroe_need_extend / jr wroe_have_valid` becomes `jr c,wroe_have_valid`, falling into wroe_need_extend. 2 B.

HL and DE at wroe_have_valid are what they were before (HL - $FF8, DE = $FF8).

## 17. wrblk_shrink zero test -- 4 B, low, R4
kernel.asm:4853-4859: after `call to_wrbytes` HL = WRBLK_MULACC+4 (documented: "HL / DE end past the copy").
Proposed `dec hl / ld a,(hl) / dec hl / or (hl) / dec hl / or (hl) / dec hl / or (hl)` (8 B, was 12).

## 18. fsize_body -- 6 B low (+3 B medium variant), R4
kernel.asm:4134-4174
- **a.** 4137-4138 `push ix / pop de` is dead: `push de / pop ix` left DE intact. 3 B, low.
- **b.** 4141-4144 `push ix / pop de / inc de / ex de,hl` becomes `push ix / pop hl / inc hl`. fat_find takes HL only (fat-prim-body.inc:305). 1 B, low.
- **c.** Tail: success `xor a / jr fsz_t`; `fsize_miss: ld a,$FF / fsz_t: ld l,a / jp rrnd_finish`. 2 B, low, flags identical.
  - Medium variant, 5 B instead of 2: success `or a`, falling into `fsize_miss: sbc a,a / ld l,a / jp rrnd_finish`. rrnd_finish passes F through, so on success N becomes 1 and P/V becomes 0 (xor gave N = 0, P = 1). That is only safe if no dispatcher reads them.

## 19. wpe (wrblk_position_sec) -- 4 B, low, R4
- kernel.asm:4425 `or a` is dead: CF = 0 from the `or a` at 4419. push / pop / ld leave flags. 1 B.
- kernel.asm:4429 `jr z,wpe_same` becomes `ret z` (CF = 0 after `or l`), and wpe_same (`or a / ret`) goes. 3 B. wpe_same is local.

## 20. fren_wild fw_lp -- 2 B, low, R4
kernel.asm:4697-4699: `fw_lp: pop hl / push hl` is dead on every entry.
- The first entry has HL = 0 = the pushed idx.
- fw_next does `pop hl / inc hl / push hl / jr fw_lp`.
- The rename path ends `push hl` and falls into fw_next.

Put fw_lp at `call fr_entry`.

## 21. wshrink_walk -- 3 B, low, R4
kernel.asm:4892-4896: `call fat_next_cluster / call hl_cmp_eoc / add hl,de / jr c,wshrink_walk`, falling into wshrink_atlast. This replaces the push/pop pair and `jr nc,atlast / jr walk`. The carry sense is the same as in 9.

## 22. dos_clear_screen -- 2 B, low, R1
kernel.asm:3529-3531: `ld hl,$0101 / ld ($F3DC),hl` instead of `ld a,1 / ld ($F3DC),a / ld ($F3DD),a`.
The sole caller (runtime.asm:522) falls into dos_handoff_keep, which reloads HL and A.

## 23. sav_fits -- 4 B, R2
- **a.** Move sav_fits's 14 B to just before `include "basic/fatfits-body.inc"` (after basent_tramp_end), so it FALLS into fat_fits and `jr fat_fits` goes. 2 B, low. basent_tramp_end still ends the trampoline, and `jp (hl)` precedes it.
- **b.** `ld de,2 / add hl,de` becomes `inc hl / inc hl`. 2 B, low-medium. fat_fits reads CF as bit 16. The CF left is sbc's borrow, 0 whenever PRGEND >= TXTTAB, and the add of 2 could not carry anyway.

## 24. One-byters -- 6 B, low
- **R2, kernel.asm:3589:** basent_tramp `ld a,$C9` becomes `ld a,(hl)`. After the ldir HL = $FD9A + $22F = $FFC9, and the ldir wrote $C9 there (DE ran $FD9B..$FFC9). This also makes the RAM copy 1 B shorter. Position-free is kept. 1 B.
- **R2, kernel.asm:3940-3943:** bcw_own `jp nz,bdos_close_rd / xor a / ld (BDOS_WRMODE),a / jp bdos_close_rd` becomes `jr nz,bcw_x / xor a / ld (BDOS_WRMODE),a / bcw_x: jp bdos_close_rd`. 1 B.
- **R3, kernel.asm:4027-4028:** frnd_update_size `ld (ix+19),0 / xor a` becomes `xor a / ld (ix+19),a`. 1 B.
- **R4, kernel.asm:5001:** k47b2_xfer_rec's `or a` is dead.
  - Its entries are the fall-through after `jr c,k47b2_eof` (CF = 0) and `jr k47b2_xfer_rec` from recdone.
  - recdone is reached only by `jr z` after `ld a,h / or l` (CF = 0), and `inc hl` keeps flags.
  - k47b2_pos_done is unreferenced.

  1 B.
- **R4, kernel.asm:5130:** setrnd_body `ld (ix+36),0` becomes `ld (ix+36),a`, moved after `call clr_f306` (A = 0; clr_f306 touches neither IX nor memory but $F306). 1 B.
- **R4, kernel.asm:4910-4913:** wshrink_empty `ld hl,(FAT_FIRSTCLUS) / ld de,0 / ld (FAT_FIRSTCLUS),de`. The freeloop needs only HL. 1 B.

## 25. dsel_bdos CR LF + text in one print -- 4 B net, MEDIUM (crosses regions), R4 -6 / driver.asm +2
kernel.asm:5690-5693: `ld hl,dsl_text_nl / call fmt_pr / ld hl,dsl_text_1 / call fmt_pr` becomes `ld hl,dsl_text_0 / call fmt_pr`, with `dsl_text_0: db 13,10` placed directly before `dsl_text_1:` in driver.asm:376.

dsl_text_1's own users (kernel.asm:661, `call nz,hke_pr` before it) keep the label.

This costs 2 B in driver.asm's region, so it only pays if that region has 2 B of fill. `make basic-reloc` would prove it.

---

## Looked at and rejected (so nobody re-reads them)
- **fmt_err `push af / call mtoff / pop af / ret`:** mtoff does `xor a`, so the save is needed.
- **The `push hl / pop hl` around hl_cmp_eoc everywhere:** it is needed unless replaced by `add hl,de` (done above where HL survives).
- **rnd_rd inline:** it has 2 callers (fat.asm:637).
- **hsy_boot `or a` (kernel.asm:3861):** CF is already 0, but Z changes for the boot sector code (BOOT_ENTRY reads F). Skipped.
- **k47b2_ok / eof (`db $01` skip trick, 1 B):** it clobbers BC before `ld b,h / ld c,l` reloads it, so it is safe, but a style call. Not counted.
- **k47b2_return `call clr_f306 / ld a,e / ret` -> `ld a,e / jp rrnd_finish` (1 B):** the returned F would change from Z/NC to leftover. Not counted.
- **bdos_dskio's 8x `inc sp`:** every register must survive, so there is no shorter form.
- **basent_body mark logic, install_basic_hooks, layout_rebuild, hrunc_h, hk_mkfloat, hk_errp, wmr_core, wrzer_body, frnd_calc, rdrnd_ex:** nothing found.
- **fsize `ld de,(FAT_FILESIZE+2)` / the shift loop:** already tight.

## Out-of-slice, noticed in passing (basic/fat-prim-body.inc, not mine)
- **fatprim_write_sector:** `ld b,1 / ld c,0 / ld a,0 / scf` becomes `ld bc,$0100 / xor a / scf` (2 B). write_sector in runtime.asm:887 already uses that form.

## Totals
- **Low / low-medium:** about 176 B over 46 edits: R1 29, R2 12, R3 1, R4 134.
- **With the medium ones** (dsel_bdos 4, fsize sbc variant +3, wrrnd_extend implicit CF +1): about 184 B.
