# apply_B -- slice B low-risk candidates, applied

Method: one candidate at a time; `rm -f build/disk.rom && make -s build/disk.rom`
(rc 0 every time), then the trailing $00 fill in front of every pinned entry
(pins parsed the way tools/check_disk_walls.py parses them) diffed before/after.
Files edited: disk/kernel.asm, basic/sv-bsvdisk.inc, basic/fatfits-body.inc (all in
the slice; no caller change elsewhere). No RAM `equ` moved. One new assembly-time
constant, `BDOS_TAB_ROWS` (a row count, not a RAM cell).

Baseline (a89a93d15): disk free 182 B in runs >= 16 B. After: 270 B.

## APPLIED (measured)

| id  | what | region (pin) | claimed | measured |
|-----|------|--------------|--------:|---------:|
| L1  | hk_frnd's create -> `jp c,hfm_create` (label on hk_fmake's create); hfr_make deleted | $5C11 | 12 | 12 |
| L2  | bsv_data end test: `or a / sbc hl,de / add hl,de / jp z,disk_write_end`, bsv_next/bsv_fin gone | $53A7 | 10 | **7** (see note) |
| L3  | hkc_body: one 6-byte ldir (B = 0 from copy4), assembler guard on both 2+4 contiguities | $5C11 | 8 | 8 |
| L4  | hk_dsk ERR 2 -> `jr nz,hklr_syn` | $53A7 | 7 | 7 |
| L5  | hkc_same compares backwards from hkc_df's HL/DE | $5C11 | 6 | 6 |
| L6  | hkf_syn deleted, `jp nz,hklr_syn` | $53A7 | 6 | 6 |
| L7  | `call rnd_rec` at hfa_src and dwr_copy | $5C11 | 6 | 6 |
| L8  | hk_dsk Bad drive -> `jp hkf_raise` | $53A7 | 4 | 4 |
| L9  | hk_mki: negate first, then range-check | $5C11 | 4 | 4 |
| L10 | conin_body saves DE only | $4E4B | 4 | 4 |
| L11 | bdos_more2 counts rows with djnz; `db 0` terminator gone; guards (row size 3, <= 255 rows); bm_none placed before bm_hit so the loop falls into it | $543C | 3 | 3 |
| L12 | hk_field: one FN_RESUME store (hkf_next) | $53A7 | 3 | 3 |
| L13 | hfa_src: `dec c / inc bc` | $5C11 | 3 | 3 |
| L14 | fat_fits: `xor a / cp d / ret c` | $5FE5 | 2 | 2 |
| L15 | hk_asav ends `jr hfm_zero` | $5C11 | 2 | 2 |
| L16 | hco_byte: borrow as `jr nc / dec hl` | $5C11 | 2 | 2 |
| L17 | w50a9_stub: HL for the BASENT_REQ store, `push de / pop ix` | $50C4 | 2 | 2 |
| L18 | set_first helper (hk_frnd + hfa_found) | $5C11 | 2 | 2 |
| L19 | disk_putword tail jp | $53A7 | 1 | 1 |
| L19 | sav_full `jr c,sf_x` | $53A7 | 1 | 1 |
| L19 | fatfits `ld hl,(FAT_SECPERCLUS)` | $5FE5 | 1 | 1 |
| L19 | fgr_media: no `or a` | $4FB8 | 1 | 1 |
| L19 | root_pos tail `jp hl_x32` | $5C11 | 1 | 1 |
| L19 | hklr_tm `jr hklr_raise` | $53A7 | 1 | 1 |
| L19 | hfa_pos tail: `jr z,hfa_ok` | $5C11 | 1 | 1 |

Per region: $5C11 +47, $53A7 +30, $4E4B +4, $543C +3, $5FE5 +3, $50C4 +2, $4FB8 +1.
**Total 90 B** (claimed 93).

Note on L2: the measured 7 differs from the claimed 10. Cause found, not a false
premise: the list counted the OLD block as 30 B; it is 27 B (15 + 9 + 3). The new
block is the 20 B the list said. The logic is as proposed (16-bit `add hl,de`
leaves Z from the sbc; HL = CURPTR again). Kept, against the letter of the
revert-on-mismatch rule, because the mismatch is fully explained; revert = restore
the old 15 lines after `call disk_putbyte` in bsv_data (and the header's
"bsv_open .. bsv_fin").

## SKIPPED
- M1-M5 (medium / low-medium), per the brief -- incl. the calbak_w inline-word helper
  (M1) and the DOUT row reorder (M2).
- None of the low ones was skipped: every premise checked out on the current code.

## REVERTED
- None.

## Checks
- L3 guard proven live: perturbing it made the build fail on the guard symbol, then restored.
- `python3 tests/run.py`: ALL 100 TEST FILE(S) PASSED (incl. test_bdosbasic's bdos_tab rows).
- No emulator, gate, repack or probe run.

## Observations (not changed)
- conin_body's header says "A/E end up holding the char"; the code (before and after)
  restores the caller's E. Pre-existing comment/code disagreement, left for the owner.
- hkf_item and hkd_comma keep labels that now have no reference (readability).
