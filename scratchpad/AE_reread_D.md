# Re-read D: disk/kernel.asm 6100-9243 + basic/fat-prim-body.inc. Byte candidates

Read-only pass. Nothing was built or run. Sizes are hand-counted Z80 encodings.
Addresses come from build/disk.sym (2026-11-26 04:21).

## Premise correction (read first)
**basic/fat-prim-body.inc is NOT shared any more.** Only disk/kernel.asm:6012 includes it.
sub/fatprim.asm:190-200 says the sub-ROM include went on 2026-10-19 (D-ROMSIZE step 1),
the file's own header says so (fat-prim-body.inc:44-49), and `grep include.*fat-prim-body`
finds only kernel.asm. Changes there need to be right for disk.rom only, and they do not
count double. These comments are now wrong: basic/main.asm:46-48 ("assembled into disk.rom
as well") and kernel.asm:6962 (fat_locate: "fat-prim-body.inc keeps its own three copies
(the sub ROM assembles that body too)").

Regions: fat-prim-body.inc and kernel 6012..7651 fill before the $75A5 pin. 7652..8056 fill
before $77B8, 8057..8145 before $782B, and 8146..9243 run on toward runtime.asm's pins.
None of the candidates below moves a pinned label.

Totals: **~295 B low risk, ~304 B in all** (49 entries). The ranking is by bytes x confidence.

---

## Tier 1: big and low risk

### 1. fat-prim-body.inc:203-297 fat_mount, 23 B (low)
Seven independent cuts:
- 207-212: the 512-B/sector check. `ld a,(BPS);or a;jr nz;ld a,(BPS+1);cp 2;jr nz` (13 B) becomes
  `ld hl,(FAT_DBUF+BPB_BYTSPERSEC); ld a,h; xor 2; or l; jr nz,fat_mount_bad` (9 B). **-4.** HL and A are
  reloaded right after.
- 223 + 227-228: drop `ld hl,0` and `ld de,(FAT_FATSTART) / add hl,de`. HL already holds RSVDSECCNT
  (215), and nothing between 216 and 224 touches HL. So fm_fatacc accumulates onto it and gives the same
  `rsvd + n*spf`. **-8.**
- 232-236: `add hl,hl` x5 becomes `call hl_x32` (disk/driver.asm:433 touches only HL and flags). **-2.**
- 239-245: `push hl` after `ld (FAT_FIRSTROOT),hl`, then `ld e,h; srl e; ld d,0; pop hl; add hl,de`
  replaces `ld a,h; srl a; ld l,a; ld h,0; ld de,(FAT_FIRSTROOT); add hl,de`. Old 11 B, new 7+1 B. **-3.**
- 213 + 259-260: add `ld c,a` after `ld (FAT_SECPERCLUS),a` (+1) and delete `ld a,(FAT_SECPERCLUS); ld c,a`
  (-4). C is untouched from 213 to 261 (checked every instruction). **-3.**
- 258 + 274-275: `ld de,0` becomes `ld de,2`; delete the two `inc de` at fm_divdone. **-2.**
- 293: `or a` before `ret`. The `xor a` at 277 already leaves A=0, Z=1, C=0, and the `ld`s in between
  do not touch flags. **-1.**

Exit state on success is identical: A=0, Z=1, C=0, HL=2, DE=TOTCLUS, B=0, C=SPC. On the bad path
only A differs (it was never a code). (Side note, not a byte saving: fm_div never terminates sanely
when the data sectors are not a multiple of SPC. HL wraps through `dec h`.)

### 2. fat-prim-body.inc:501-512 + 751-766: share the "B0 / byte1 / straddle?" fetch, 22 B (low)
New helper, called from both places:
```
fat_b01:                      ; BC = buffer -> FAT_B0 stored, A = buf[idx+1], HL = &buf[idx+1],
        ld   hl,(FAT_BYTEIDX) ; Z = the entry straddles (idx == 511)
        add  hl,bc
        ld   a,(hl)
        ld   (FAT_B0),a
        inc  hl
        ld   a,(hl)
        ld   de,(FAT_BYTEIDX)
        inc  de
        dec  d
        dec  d                ; idx+1 == $0200 <=> idx == 511 (idx is 0..511)
        ret                   ; 18 B
fnc_have:      call fat_b01 / jr nz,fnc_combine          (5 B, was 21)
fac_entry_from_wbuf: ld bc,FAT_MBUF / call fat_b01 / jr nz,fac_comb   (8 B, was 32)
```
HL at fac_comb is still &MBUF[idx+1], which keeps the "HL IS KEPT" constraint at 781-784. The
speculative read of buf[512] was already done by the old fnc path. In fac, BC is now clobbered on
the non-straddle path; its straddle path already clobbered it. Every caller was checked:
fac_have_sec (no BC); fac_cached_entry -> fhfc_loop (kernel 5172) and getalloc (re-pops BC every
pass); frnd_next (fat.asm:130) -> frl_have (no BC). Cy=0 on return is kept (see 3).
Variant without the helper (inline `inc/dec` test only): 3 + 10 B = 13 B.

### 3. fat-prim-body.inc:519-549 fnc_combine, 20 B (low)
FAT_B0 ($ECC4) and FAT_B1 ($ECC5) are adjacent, and nothing reads either cell after fnc_combine
(grep: only fnc_combine and fcf, and fcf writes its own first). So:
```
fnc_combine:
        ld   hl,FAT_B1
        ld   (hl),a
        ld   a,(FAT_PARITY)
        or   a
        jr   z,fnc_even
        xor  a                ; odd: (HL) and A nibble-rotate
        rrd                   ; (B1) := B1>>4,               A low := B1 low
        dec  hl
        rrd                   ; (B0) := B1low<<4 | B0>>4
fnc_even:
        ld   hl,(FAT_B0)      ; L = B0, H = B1
        ld   a,h
        and  $0F
        ld   h,a
        ret                   ; 24 B, was 44
```
Out: HL = the entry and Cy=0, as before (`and` clears C, and `rrd` keeps it). A is now H rather
than B0 or (B0>>4), and Z is meaningless in both versions. All 11 callers were checked
(kernel 2679 push/pop af, 4506 via fat_open_at, 4891/4923 hl_cmp_eoc, 4900, 7779 `ld a,h`,
7942, 8953, fat-delete-body:62, fac_comb -> `ld a,d;or e`, frnd_next `or a`). None reads A or Z.

### 4. fat-prim-body.inc:1052-1073 fcf (fat_count_upto) zero test, 16 B (low)
```
fcf_haveb1:                  ; A = byte1
        ld   c,a
        ld   a,(FWR_CLUS)
        rra                  ; Cy = odd cluster
        ld   a,(FAT_B0)
        jr   nc,fcf_even
        and  $F0             ; odd: (B0 & F0) | B1
        or   c
        jr   fcf_test
fcf_even:
        ld   b,a
        ld   a,c
        and  $0F             ; even: B0 | (B1 & 0F)
        or   b
fcf_test:
        jr   nz,fcf_used
fcf_free: ...                 ; 22 B, was 38 (incl. the dead `ld (FAT_B1),a`)
```
B and C are dead in the fcf loop, which reloads everything from RAM. FAT_B1 is no longer written,
and nothing reads it.

### 5. kernel.asm:8705-8718 name_cmp_wild duplicates name_cmp, 14 B (low)
name_cmp (fat-prim-body:385) runs the same instructions: `$3F`=='?', the same `call toupper_cmp`,
the same `inc/inc/djnz/ret`. name_cmp_wild only adds a redundant `ld a,(de)` (`cp` does not change
A). Delete name_cmp_wild and `call name_cmp` at kernel 4718 and 8616. Its "C preserved" comment
is false for both, because toupper_cmp does `ld c,a`. Neither caller relies on C: 8616 pushes BC,
and 4718's next lines do not read C. The routine is preceded by `ret` (ds_none), so nothing falls
into it.

### 6. kernel.asm:8552-8572 dirscan_match shifts BDOS_SRCHIDX>>4 twice, 14 B (low)
```
        ld   hl,(BDOS_SRCHIDX) / ld b,4 / dsm_shr: srl h / rr l / djnz dsm_shr
        push hl                       ; idx>>4, kept for the DIRREM subtraction
        ld   de,(FAT_FIRSTROOT) / add hl,de / ld (FAT_DIRSEC),hl
        call fat_rootsecs             ; (fat.asm:469, no inputs)
        pop  de
        or a / sbc hl,de ...          ; unchanged from here
```
Old 38 B, new 24 B. The registers at `sbc` are the same as before.

### 7. kernel.asm:6849-6864 + 6913-6919 df_emit: one "room for 13?" test, 12 B (low)
Head becomes `call op_lfiles / jr z,de_field / ld a,(CSRX) / dec a / call nz,df_room`, falling into
de_field. Tail gets a label: `ld a,(CSRX) / dec a / df_room: ld b,a / ld a,(LINLEN) / sub b /
cp 13 / ret nc` then falls into df_crlf, as now. The `or a` after `dec a` was already redundant.
df_crlf/df_out keep HL, and de_field reloads B. Head goes from 19 B to 7 B.

### 8. kernel.asm:8647-8689 dsm_found DTA build, 12 B (low)
- 8654-8655 `push hl / pop de`: DE already equals HL (`ld h,d / ld l,e` just above). **-2.**
- After `ld (de),a` (DTA+13), DE is still live, because only HL is popped. Replace
  `ld de,(DOS_DTAPTR) / ld a,e / add a,16 / ld e,a / jr nc / inc d` (11 B) with `inc de` x3. **-8.**
- Drop the `push hl` (8667) and `pop hl` (8678). After `ldir_11`, HL = entry+11, so use
  `ld bc,4` instead of `ld bc,15`. **-2.**
DOS_DTAPTR is the scratch pointer set by dsm_p1_pre, which is the same value DE was loaded from
at 8648.

### 9. kernel.asm:7586-7595 wr_reset as a fill loop, 10 B (low)
WRCLUS..WRBYTES+3 = $ED54..$ED5E is 11 contiguous bytes (equates.inc:462-466).
```
wr_reset: xor a / ld hl,BDOS_WRCLUS / ld b,11 / wrr: ld (hl),a / inc hl / djnz wrr / ld h,a / ld l,a / ret
```
13 B, was 23. Out: HL=0 (1646 relies on it), A=0, and the flags from `xor a`, all as before. B
is now 0; neither caller (1646, 2090) reads B.

### 10. kernel.asm:8028-8044 mulacc_cmp as a loop, 10 B (low)
```
mulacc_cmp: ld de,WRBLK_MULACC+3 / ld hl,FAT_FILESIZE+3 / ld b,4
mc: ld a,(de) / cp (hl) / ret nz / dec de / dec hl / djnz mc / ret        ; 16 B, was 26
```
Z and C have the same meaning. DE and B are newly clobbered. Callers: 4362 then wrblk_size_max
or wrblk_shrink, both of which set HL/DE/BC before use (to_wrbytes). 4823 sets HL, DE and BC right
after.

### 11. kernel.asm:6307-6312 KILL's "file open" arm into NAME's, 9 B (low)
`jr nc,hkk_none_open / ld a,64 / ld (DISKOP_ERR),a / ld a,2 / jr hkk_done` (11 B) becomes
`jr c,hkn_open` (2 B). hkn_open does the same: ERR=64, A=2, then hkn_done = hk_claim_status, the
same as hkk_done. Reach: `jr` at $6FA5 to hkn_open $7024-9 = $701B gives +116. In range.

### 12. kernel.asm:6573-6577 hkc_open, 9 B (low)
Point both `jr c,hkc_open` (6563, 6569) at hkn_open and delete the 9-B hkc_open body. hkc_done
is also hk_claim_status. Reach: about -$50. hkc_open is only entered by those two jumps; it is
preceded by `jr hkc_done`.

### 13. fat-prim-body.inc:303-378 + 1212-1223: shared "record the slot" helper, 9 B (low)
```
slot_rec: push hl / or a / sbc hl,de / ld (FWR_DIROFF),hl / ld de,(FAT_DIRSEC) / ld (FWR_DIRSEC),de / pop hl / ret  ; 17 B
ff_found:      ... ld de,FAT_DBUF / call slot_rec     (replaces 19 B)
fdcr_useslot:  ... ld de,FAT_MBUF / call slot_rec     (replaces 19 B)
```
These are the only two writers of these cells in the body (grep). HL is kept.

### 14. fat-prim-body.inc:1022-1051 fcf byte fetch and straddle test, 11 B (low)
After `call fat_wclus_x15 / and 1 / ld h,a`:
```
        ld d,h / ld e,l / inc de / dec d / dec d   ; Z: idx == 511
        ld de,FAT_DBUF / add hl,de                 ; ADD HL,DE leaves Z alone
        ld a,(hl) / ld (FAT_B0),a / inc hl / ld a,(hl)
        jr nz,fcf_haveb1
        ld hl,(FWR_FIRST) / inc hl / ex de,hl / call rs_mbuf / ld a,(FAT_MBUF)
fcf_haveb1:                                       ; now reached by fall-through
```
The 17-B head replaces 28 B (the push/pop B0 block, the 6-B two-byte test, `fcf_b1_same` and
the straddle's `jr`). fcf cannot use fat_b01 (2), because fcf keeps its limit in FAT_BYTEIDX.

### 15. fat-prim-body.inc:92-191 read/write sector entries, 8 B (low)
Reorder so both fall into dskio_calslt:
```
fws_mbuf: ld hl,FAT_MBUF
fatprim_write_sector: xor a / scf / jr rw_go
rs_mbuf: ld hl,FAT_MBUF / jr read_sector
rs_dbuf: ld hl,FAT_DBUF
read_sector: call rh_check
read_sector_nh: xor a                 ; drive 0, Cy = 0 = read
rw_go: ld bc,$0100                    ; B = 1 sector, C = 0 media
dskio_calslt: call bdos_dskio
dc_result: ...                        (unchanged)
```
The old entries took 16 B; the new take 8 (the read entry loses `jr dskio_calslt`). DSKIO's inputs
(A=0, B=1, C=0, Cy) are identical. rh_check's hit path (driver.asm:576-580) still drops exactly
read_sector's return. The routine above the include ends in `ret` (kernel 5992). dskio_calslt and
dc_* are referenced only inside the body.

### 16. kernel.asm:6866-6898 de_name/de_ext: redundant push/pop around df_out, 8 B (low)
df_out (6938) pushes and pops HL, DE and BC itself. So `push hl / push bc / ... / pop bc / pop hl`
in both loops is dead (4 B each).

### 17. fat-prim-body.inc:901-917 fwe_same_odd, 7 B (low)
`ld a,d / xor e / and $0F / xor e / rrca x4 / ld (hl),a` (10 B) replaces 17 B. t = ((d^e)&$0F)^e
has its low nibble = d.lo and its high nibble = e.hi; rotating 4 gives d.lo:e.hi = (value>>4)&$FF.
B is no longer used.

### 18. kernel.asm:7913-7916 k47b2 `ld hl,(WRBLK_REC+1)`, 5 B (low)
`ld a,(REC+2) / ld h,a / ld a,(REC+1) / ld l,a` becomes `ld hl,(WRBLK_REC+1)`. A is reloaded at 7920.

### 19. fat-prim-body.inc:1299-1307 fat_dir_update, 5 B (low)
After `ld (hl),d` HL is at +27, so `inc hl` gives +28. Drop `push hl / pop hl / ld de,28 /
add hl,de`.

### 20. fat-prim-body.inc:362-376 ff_found field reads, 5 B (low)
```
push hl / ld de,26 / add hl,de / ld e,(hl) / inc hl / ld d,(hl) / inc hl / ld (FAT_FIRSTCLUS),de
ld de,FAT_FILESIZE / ld bc,4 / ldir / pop hl / or a / ret
```
This drops the second pop/push and `ld de,28 / add`. Keep the `or a`: Z at exit changes without it,
and callers were not audited for Z.

### 21. Small fat-prim-body items, all low
| line | change | B |
|---|---|---|
| 374, 1313 | `ld bc,4 / ldir` -> `call copy4` (kernel 4832, `ld bc,4/ldir/ret`) | 2+2 |
| 644-650 | fat_read_fat_sector: `call fat_locate / jp rd_fatsec` (kernel 759 is exactly `ld (FAT_FATSEC),hl / ex de,hl / jp rs_mbuf`) | 4 |
| 771-776 | fac_straddle: `ld hl,(FAT_FATSEC) / inc hl / ld (FAT_WRTMP2),hl / call rd_fatsec` | 4 |
| 842-848 | fwe straddle test `ld bc,(FAT_BYTEIDX) / inc bc / dec b / dec b / jr nz,fwe_b1_same` | 4 |
| 1168-1172 | ffds tail after `ret c`: `ld hl,FWR_SECIDX / inc (hl) / ret` (Cy=0 already; Z/S same as old `or a`; A and HL differ, and all 6 callers test only C) | 4 |
| 1233-1243 | fdcr: `xor a / ld b,21 / lp: ld (de),a / inc de / djnz lp` | 4 |
| 1247-1252 | fdir_wrback: `ld de,(FWR_DIRSEC) / jp fws_mbuf` (dc_result's success exit is `xor a` = A0/Z/NC, exactly what `or a` made; the error exit is unchanged) | 3 |
| 827-838 | fwe_odd0: `ld a,e / rlca x4 / xor (hl) / and $F0 / xor (hl) / ld (hl),a` | 3 |
| 893-899 | fwe even byte1: `ld a,(hl) / xor d / and $F0 / xor d / ld (hl),a` | 2 |
| 1110-1118 | pad loop as do-while (count >= 1 guaranteed): `ld (hl),0 / inc hl / dec bc / ld a,b / or c / jr nz` | 2 |
| 1143-1146 | `push hl / ex de,hl / pop de / push de` -> `ex de,hl / push de` | 2 |
| 731-734 | fac_found `push hl/inc hl/ld (),hl/pop hl` -> `inc hl / ld (),hl / dec hl` | 1 |
| 823-824 | `ld a,e / ld (hl),a` -> `ld (hl),e` | 1 |
| 937 | fwe_finish `or a`: `or 2` already gave C=0 and NZ | 1 |
| 941 | fwe_err `scf`: both entries are `jr c` | 1 |

### 22. Small kernel items, all low
| line | change | B |
|---|---|---|
| 8939-8942 | fdel_body success tail -> `jr` to the identical tail at 8974 (`call clr_f306 / ld h,a / ld l,a / ret`) | 4 |
| 7955-7960 | `ld hl,(WRBLK_REC) / ld a,h / and 1 / ld h,a / or l` | 3 |
| 8782 + 8793-8795 | `jr z,fdc_rd_ok` -> `ret z` (after `and`: A=0, Z, NC is what `or a` produced); delete fdc_rd_ok (single referrer) | 3 |
| 9168-9171 | rdrnd: `call rdrnd_ex / jr wrrnd_zero`, with a label at wrrnd_ok+6 (`xor a/ld h,a/ld l,a/jr rrnd_finish`) | 3 |
| 7536/7538 | fmt_pr: `push hl/pop hl` around conout_emit_e, which saves HL itself (runtime.asm:933/952) | 2 |
| 7617-7630 | wrbytes_add: `ld hl,X / ld a,RECSIZE / ld b,4 / or a / lp: adc a,(hl) / ld (hl),a / inc hl / ld a,0 / djnz lp / ret` | 2 |
| 7781-7786 | ws_walk EOC test -> `ld a,l / add a,8 / ld a,h / adc a,$F0 / jr nc,ws_ok` (as frl_have 8105 does) | 2 |
| 8520-8521 | ga_fail: A=0 after clr_f306, so `ld d,a/ld e,a/ld h,a/ld l,a` | 2 |
| 7669-7671 | fcb_mark_written: `xor a / ld (hl),a / inc hl / ld (hl),a` (old A/flags were date_fat_word garbage; callers 7684/7831/9198/runtime 797 do not read them) | 1 |
| 8831-8834 | `jr nc,bsw_m34_buffer / ld a,1 / ret` -> `jr c,bsw_full / jr bsw_m34_buffer` | 1 |
| 9000-9001 | mf_find `push ix/pop de/inc de/ex de,hl` -> `push ix/pop hl/inc hl` (fat_find reads no DE; both callers reload DE) | 1 |

---

## Tier 2: medium risk (needs a gate run or one more read)

| where | change | B | what would prove it |
|---|---|---|---|
| kernel 8993-8994 | mnt_find's first `push ix / pop de` looks dead. fat_mount -> fat_geom_read sets `ld de,1` after `dsel_bdos`, and fren_miss reads no DE | 3 | drv_select (kernel 645, the BASIC-side path reached through $F37D) reads no DE. Not fully traced. |
| kernel 6213-6223 | hdl_ok/nf/ascii/io by the `ld bc,nn` skip trick: `AF 01 / 3E01 01 / 3E02 01 / 3E03` | 3 | Correct (traced all four entries, including `jp hdl_ok` from 7080), but it clobbers BC and the repo has no precedent for the idiom. A style ruling. |
| fat-prim 1012 | fcf `or a` before `sbc`: `add hl,de` of FATSTART + (ofs>>9) does not carry for any sane BPB | 1 | A garbage BPB with FATSTART >= $FF00 could only cost a cache miss or false hit. |
| fat-prim 735 | fac_found `or a`: Cy=0 already after `ret c`. Z changes | 1 | 6 callers, all `jr/jp c` (checked); none reads Z. Low-medium. |
| fat-prim 580 | fat_read_file_sector `or a`: C is 0 already. Z changes (old Z=1 via A=0) | 1 | Audit every frs/fat_read_file_sector caller for Z. Not done. |
| fat-prim 1003/1086 | fcf `jp nc,fcf_done` / `jp fcf_loop` -> `jr` once 4+14 land (fcf_loop $6BCE, fcf_used $6C5C, about 151 B before, about 123 after) | 2 | Recompute from the .sym after the cuts. |

## Looked at and rejected
- **getalloc_body's scan (kernel 8465-8503) re-using fat_count_free:** about 30 B, but fcf writes
  FWR_CLUS and FWR_FIRST (= BDOS_WRCLUS/WRFIRST) and FAT_DBUF. ALLOC can run while a DOS file is open
  for write, so this would corrupt live write state. High risk.
- **hk_dpload's 11-way `cp/jp z` chain -> table:** the FOPEN_SEL values are sparse ($41..$5A). A
  (byte, word) table saves about 3 B, and it would clobber HL/DE/BC before every handler. Not worth it.
- **Directory attribute check helper (ff_entloop / df_entloop):** 1 B.
- **br_cals_tmpl, p1_blit_tmpl, wa_seg, res_print:** these are RAM templates. Their size is also RAM
  layout, so left alone.
- **fdc_read_data_body polling:** timing-critical, left alone.
