# D-WSZERO S9 — making the disk-only cells legitimately disk-only (read-only design, 2026-10-15)

Nothing in the repo was edited, built or run. Every address comes from `build/basic-reloc.sym` /
`build/sub.sym` (2026-10-15 20:45, the S10 working tree; S10 was equates-only so code addresses
equal the S8 build). Walls: read from `s8_reloc.out` (session scratchpad, the last measure; S10
changed no code): **main low 57 B, main page 1 171 B, sub p0 17 B, sub p1 1240 B, disk.rom 2857 B
in 27 runs** — the same as the brief's figures. The window census used here is
`window_census.py` / `window_census.out` beside this file (imports `tools/ram_map.py`, writes nothing
in the repo; `-B`, no bytecode). **(unverified)** marks every claim not read off the code.

## 0. The pin geometry (this decides every row of the table)

Main is ONE image, `BASIC_ORG $2765 .. $8000`, include order = address order. The four pins cut it
into six segments. Every pad was computed from the sym and is **0 B today**:

| seg | span | what is in it (include order) | pad in front of the pin | free |
|---|---|---|---|---|
| A | `$2765..$3297` | str-engine, input.asm, float, float-arith up to `basicint_3297` | `ds $3297-$` after `dig15_shr`: **not computed** (needs a listing); S9 touches nothing here | 0 (must net 0) |
| B | `$3299..$3FC7` (`__MEAS_LOW_END`) | rest of float-arith, subromcall, edscreen, keytrap, arrays, poke, sound, title | — (padded to `$4000` independently) | **57 B** |
| C | `$4000..$6CF3` | header, interp.asm (boot, `init` $4010), initext, subrom-boot, repl, vars, **strvar**, expr, … cload, **files.asm up to `oo_dev_crt`** (`seq_end` $6B8B, `disk_error` $6B9A) | `jr oo_dev_open` ends at `$6CF3` exactly: **0** | 0 (net 0) |
| D | `$6CF6..$73AC` | rest of files.asm (`init_filechan` $6F5E, `mc_ioerr` $711D, `diskslot_test`), grpdev, basicrom, **field.asm up to `lrset_common`** (`fld_init` $7251, `fld_find` $7272, `field_prologue` $72C2, `ex_lset` $7397) | `jr lrc_go` ends at `$73AC`: **0** | 0 (net 0) |
| E | `$73AC..$73E5` | `basicint_run` (pinned head), `lrc_go`, **`lrset_tgt`** $73BD, **`ex_on_key`** (6 B refill) $73DF | ex_on_key ends at `$73E5`: **0** | 0 (net 0) |
| F | `$73E8..$7F55` | rest of field.asm (`lrset_rhs`, `fld_lookup` $741C, GET/PUT head), format, program, missing | — | **171 B** |

So: any byte added in A/C/D/E must be removed in the SAME segment (or a chunk moved across a pin
in the opposite direction); a net positive overflows the `ds`, and pasmo then writes an EMPTY
binary with rc 0. New code goes in F (or B). Sub page 0 has no pins, but `sub/deftype.asm:99` has a
page-align pad (`IF (low $) > 252`) after arrays.asm: `edt_codes` is at `$34B3`, +5 B moves it to
`$B8` — no pad fires.

## 1. Corrections to the classification (found while re-locating by symbol)

1. **FLD_CHAN is ALREADY disk-only — S9's "store FLD_CHAN after fch_mode_class" is VOID.**
   `field_prologue` is a call-back from disk.rom's `hk_field` (D-FIELDMOVE): on a diskless machine
   `ex_field` → `chan_gate_bare` finds `H_FIELD` unclaimed and raises ERR 5 before any call-back
   ([field.asm:289](basic/field.asm:289), [files.asm:233](basic/files.asm:233)). The other writers are
   `lrset_tgt` (call-back) and disk.rom `hk_lrset`. No edit; a control row (`lset`, below) PEEKs it.
2. **DISKOP_ERR has a SECOND diskless reader the classification missed: `seq_end`**
   ([files.asm:321](basic/files.asm:321)). A tape channel's `cas_in_getbyte` returns CF at Ctrl-Z
   ([cload.asm:913](basic/cload.asm:913)), so `LINE INPUT#`/`INPUT#` past the end of a CAS: file
   reaches `seq_end`, which raises whatever `$EF06` holds before it ever tests for 55. On the
   diskless machine nothing writes `$EF06` (power-on RAM; D-CASBRK measured 255 there at its old
   address). **Prediction (UNMEASURED): reading past the end of a tape data file on diskless
   zerobas raises a garbage code where the VG-8020 says `Input past end` (55)** — a live TIER 3
   defect today if `$EF06` powers on nonzero, and certain after S15. No existing row reads past a
   tape file's end (`casrbrk` `inb` reads exactly 40 of 40 lines; `eofcas` uses EOF()).
3. **`mc_ioerr` is UNREACHABLE** since D-CASTYPE (the tape search filters by type — TODO's
   2026-10-11 closing inventory: "files.asm's two `cp ASCII_ID` tests, UNREACHABLE"). The retarget
   stays (0 B, the brief asks for it) but has NO behavioural witness; and edit E13 below makes
   `disk_error` itself safe, which covers it anyway.
4. **VALTYP is write-only in the ROMs but READ by five unit tests** (`tests/test_strvar.py`,
   `test_str_engine.py`, `test_str_fn.py`, `test_str_verbs.py`, `test_str_compare.py` take
   `s["VALTYP"]` from the sym and assert `== 1`). Deleting the equate makes them KeyError; they must
   drop those asserts in the same commit (CF + STRPTR remain the contract). `ld a,1` is KEPT (A=1 on
   return is not proven unused by every str_eval caller), so the saving is −3 B, not −5.
5. **The A17 alias rule can LAUNDER a diskless user.** `disk_floor()` accepts a bare alias of a
   tagged name ([ram_map.py:957](tools/ram_map.py:957)). `PLY_NUMOVF equ DISKOP_A` (PLAY, diskless)
   would pass as tagged the moment DISKOP_A gets its DISK-ONLY tag; `BN_STAT/CM_STATUS/DEFT_STATUS/
   LE_STATUS/AUDIO_STATUS equ DISKOP_STATUS` and `FOPEN_SEL/LE_OP/AUDIO_VMASK equ DISKOP_OP` likewise.
   Hence: split PLY_NUMOVF to a literal, and **do NOT tag DISKOP_OP / DISKOP_STATUS** (diskless users
   via aliases — they are Y cells for S11/S12, not D).
6. Side observation, not S9 (file it for S11/S12's planner): `TSV_NAME` is declared `(1 B)` but
   `tape_parse_name` writes 6 bytes `$EF62..$EF67` ([save.asm:673](basic/save.asm:673)) — over
   FILES_ENTIDX/IN_RDLEN, the S10-vacated `$EF64/$EF65` (now look like HOLES), FCH_RDMODE and GFX_X1's
   low byte. A planner that packs a persistent cell into `$EF64` would be clobbered by every
   CSAVE / SAVE"CAS:" / OPEN"CAS:"FOR OUTPUT.

## 2. The edit table

Groups (G1..G7) are the revert units; each is net 0 in every pinned segment, so reverting ONE
group (a knife) is pin-safe too.

| # | grp | file / symbol | before | after | Δ B | region / seg | pin safety |
|---|---|---|---|---|---|---|---|
| E1 | G1 | [strvar.asm](basic/strvar.asm:256) `str_eval_ok` | `ld a,1` / `ld (VALTYP),a` / `scf` / `ret` | `ld a,1` / `scf` / `ret` | **−3** | main p1, **seg C** (ahead of $6CF3/$73AC/$73E5) | paired with E2 → seg C net 0 |
| E2 | G1 | [interp.asm](basic/interp.asm:154) boot, right after `call init_ext_roms` | — | `call fld_init_g` (DISKSLOT_OK is valid only from here; the two earlier boot inits read power-on DRVINF) | **+3** | seg C | E1+E2 = 0. Clobbers A,B,DE,HL: next is `xor a / ld (KEYARG),a / sr_inl0` — nothing live (read off the code) |
| E3 | G1 | [sysvars.inc](basic/sysvars.inc:1746) | `VALTYP equ $EF35` (+ its block), `FOSIGN equ $F0D2`, `FOMBYTES equ $F0D4` | deleted (VALTYP's REJECT-UNOBSERVABLE prose → a one-line tombstone) | 0 | — | equates only. ⚠️ FOMBYTES' comment says the next paragraph JOINS it in ram_map: regenerate `docs/ram-map.md` |
| E4 | G2 | new `fld_init_g`, seg F (e.g. right after `fld_lookup`) | — | `call diskslot_test` / `ret z` / `jp fld_init` | **+7** | main p1 **seg F** (past every pin) | free space |
| E5 | G2 | [vars.asm](basic/vars.asm:1230) `clear_vars` tail | `jp fld_init` | `jp fld_init_g` | 0 | seg C | same size |
| E6 | G2 | [files.asm](basic/files.asm:1598) `init_filechan` tail | `jp fld_init` | `jp fld_init_g` | 0 | seg D | same size |
| E7 | G3 | [field.asm](basic/field.asm:716) `fld_lookup` head | `call fld_find` … | `call diskslot_test` / `ret z` / `call fld_find` … (`or a` leaves CF=0 = "not fielded") | **+4** | **seg F** ($741C) | free space |
| E8 | G4 | [sub/arrays.asm](sub/arrays.asm:313) `aer_fldfix` head | `or a` / `sbc hl,de` … | `ld a,(DISKSLOT_OK)` / `or a` / `ret z` / … | **+5** | **sub p0** (17 → 12) | no pins; deftype align pad does not fire ($34B3 → $34B8) |
| E9 | G5 | [field.asm](basic/field.asm:546) `ex_lset` / `ex_rset` / `lrset_common` | `xor a` (1) ; `ld a,1` (2) ; `ld (LRSET_JUST),a` (3) | all three deleted (ex_lset = `ld de,H_LSET / jr lrset_common`, ex_rset = `ld de,H_RSET`, falls in) | **−6** | **seg D** | refilled by E10 |
| E10 | G5 | field.asm: the `IF BASICINT_PINS` `ex_on_key` block (`ld bc,10*256+0` / `jp eon_trap_in`, 6 B, a `jp z` target only — [program.asm:2511](basic/program.asm:2511)) | in seg E, just before `ds $73E5-$` | moved into seg D, between `fld_add`'s `ret` and `ex_lset` (after an unconditional transfer; still inside `IF BASICINT_PINS`, program.asm's ELSE copy untouched) | D **+6**, E **−6** | seg D / seg E | D: −6+6 = 0; E: see E11 |
| E11 | G5 | [field.asm](basic/field.asm:615) `lrset_tgt`, after `ld hl,(FN_RESUME)` | — | `dec hl` / `ld a,(hl)` / `inc hl` / `ld (LRSET_JUST),a` — the verb's own token ($B8 LSET / $B9 RSET, FN_RESUME = token+1 since `lrset_common`'s `inc hl`) + a 0-B assert `IF (LSET_TOKEN & 1) != 0 \|\| RSET_TOKEN != LSET_TOKEN + 1` | **+6** | **seg E** | E: −6 (E10) + 6 = 0; `jr lrc_go` and basicint_run untouched. lrset_tgt runs ONLY as hk_lrset's call-back → never diskless |
| E12 | G5 | [sub/lrsetst.asm](sub/lrsetst.asm:101) | `ld a,(LRSET_JUST)` / `or a` / `jr z,lrst_copy` | `ld a,(LRSET_JUST)` / `rra` / `jr nc,lrst_copy` (bit 0 = right) | 0 | sub p0 | same size; both arms reload A. sysvars.inc LRSET_JUST comment: "the LSET/RSET token; bit 0 = right-justify". test_field pokes 0/1 → still valid |
| E13 | G6 | new `se_pending`, seg F | — | `call diskslot_test` / `ret z` (A = 0: nothing pending without a disk ROM) / `ld a,(DISKOP_ERR)` / `ret` | **+8** | **seg F** | free space |
| E13a | G6 | [files.asm](basic/files.asm:322) `seq_end` | `ld a,(DISKOP_ERR)` | `call se_pending` | 0 | seg C | 3 ↔ 3 B; the `or a / jp nz,raise_error` after it is unchanged |
| E13b | G6 | [files.asm](basic/files.asm:339) `disk_error` | `ld a,(DISKOP_ERR)` | `call se_pending` | 0 | seg C | 3 ↔ 3 B; every caller of disk_error (mc_ioerr included) is now safe diskless: `load error`, as with no code pending |
| E14 | G7 | [files.asm](basic/files.asm:2333) `mc_ioerr` | `pop hl` / `jp disk_error` | `pop hl` / `jp load_error` | 0 | seg D | same size; UNREACHABLE (§1.3) |
| E15 | — | field_prologue FLD_CHAN reorder | — | **not done** (§1.1) | 0 | — | — |
| E16 | G7 | [sysvars.inc](basic/sysvars.inc:3096) alias splits | `FMT_GEOMSEL equ TSV_CNT` ; `FMT_RESULT equ TSV_NAME` ; `PLY_NUMOVF equ DISKOP_A` | `FMT_GEOMSEL equ $EF61 ; DISK-ONLY: …` ; `FMT_RESULT equ $EF62 ; DISK-ONLY: …` ; `PLY_NUMOVF equ $EE3A ; …` (no tag). FILES_ENTIDX / IN_RDLEN are already two literals: tag FILES_ENTIDX only | 0 | — | same VALUES → all four ROMs byte-identical for E16+E17 alone (check by hash). `ram-width-allow.txt` key `DISKOP_A/PLY_NUMOVF` is by name-set at the address → unchanged |
| E17 | G7 | sysvars.inc tags | — | `DISK-ONLY:` at the comment head (first 120 chars before any `;`, the `disk_floor` rule) on: FLD_CUROFF, FLD_CHAN, LRSET_JUST, LRSET_W, LRSET_DEST; DISK_FCB, DISK_FCB_NAME (not a bare alias); DSV_PTR, DSV_END; FMT_GEOMSEL, FMT_RESULT, FMT_SEC, FMT_DESC; FILES_ENTIDX, FILES_HASPAT; DSKBUF_PTR ($F351, disk.rom only); FAT_SECPERCLUS..FAT_WRTMP2, FREAD_OFF, FREAD_LEFT, FWR_CLUS..FWR_DIROFF (27 names; FCH_STATE0 inherits as a bare alias); DISKOP_A, DISKOP_HL (BN_PTR inherits); DISKOP_ERR; FCH_RECLENS, FCH_RECNOS; FLD_TAB, GP_RECNO..GP_FLAGS, GP_RECLEN, GP_SRC, GP_LEFT; COPY_SRC, COPY_CLUS, COPY_LEFT. `BOOT-ONLY:` on SCAN_PRIM, SCAN_SLOT, SCAN_INIT, SCAN_IY (SCAN_IY is also disk-DSKIO: legit on the disk machine). FLD_TABEND / FN_STK_FLOOR: `NOT-A-CELL` (both are bounds, not cells; FN_STK_FLOOR's allow line then goes — the ratchet's good direction). **Untagged on purpose:** DISKOP_OP, DISKOP_STATUS, TSV_*, IN_RDLEN, FCH_RDMODE, PLY_NUMOVF, GFX_BAD / GFX_DJ (probe-only — S11+ or a SELFTEST tag, not S9) | 0 | — | equates/comments only. The D list is the classification's census (unverified by me beyond §1) — the `dskonly` row below is its runtime check |
| E18 | G7 | [tools/ram_map.py](tools/ram_map.py:955) `disk_floor.tag()` | `"DISK-ONLY" in head` | `"DISK-ONLY" in head or "BOOT-ONLY" in head`; selftest: "A17 a BOOT-ONLY tag is accepted", "A17 NEGATIVE: `BOOT ONLY` (no hyphen) is RED"; optional advisory `--floor-top F380` that lists the offenders of the PROJECTED floor `[TXTMAX, $F380)` without failing (S15's census, and the witness for E16's split) | 0 ROM | — | — |
| E19 | G1 | the 5 `tests/test_str*.py` | `VALTYP = s["VALTYP"]` + `== 1` asserts | asserts dropped (CF + STRPTR stay) | 0 ROM | — | — |

### Cost per region

| region | Δ | wall after |
|---|---|---|
| main low (seg A / seg B) | 0 / 0 | 57 B |
| main page 1, seg C / D / E | 0 / 0 / 0 (every pad stays 0) | — |
| main page 1, seg F (the free tail) | **+19** (E4 7 + E7 4 + E13 8) | **171 → 152 B** |
| sub p0 | **+5** (E8) | **17 → 12 B** |
| sub p1 | 0 | 1240 B |
| disk.rom | 0 (the LRSET token is read main-side, see alternatives) | 2857 B |

Fallback homes for E4/E7/E13 if seg F is wanted elsewhere: seg B (57 B), anywhere after the `$3297`
pin and before `__MEAS_LOW_END`.

🎯 Side effect for TIER 5 (estimate, unmeasured): a diskless string-variable read no longer walks
16 FLD_TAB slots (~1000 T) — `call diskslot_test` + `ret z` is ~45 T; the disk machine pays ~45 T
more per string read.

### Why not the brief's literal shape (each considered, priced)

- **Gate in `fld_find` instead of `fld_lookup`** (+4 B in seg D → needs a refill): `fld_find`'s only
  other caller is `lrset_tgt`, a disk call-back; `fld_lookup` is the only diskless reader and sits in
  seg F. Same coverage, no pin work.
- **Inline gate in `fld_init`** (+4 B seg D): G5 already spends seg D's only exact refill (ex_on_key);
  the wrapper costs 3 B more but 0 in D.
- **LRSET_JUST via disk.rom** (`hk_lset` / `hk_rset` split entries, ~8 B disk.rom, LRSET_JUST added to
  `gen_resident_abi.py`'s export list): equally valid, but main still loses 6 B in seg D and needs
  E10 anyway; the call-back form keeps the decision beside the parse. Choose it if a later slice wants
  seg E's 6 B back.
- **Rehoming LRSET_JUST** (equates only, 0 B): spends one of the ~7 idle published 1-byte singles S14
  already counts on. Kept as the zero-code fallback.
- **seq_end gated by channel type** (FCH_MODE = CAS_IN_MODE) instead of by machine: would also fix the
  disk machine's stale-code-at-tape-EOF case (§4), but +7 B in seg C with no refill there.

## 3. Witnesses

### Existing gates that must stay green (regressions)

| edit | gate / row | what it already shows |
|---|---|---|
| E9-E12 | `nodisk-acceptance` `h.field` / `h.lset` / `h.rset` ([basic_probe_nodisk.py:110](probes/basic/basic_probe_nodisk.py:110)) | ERR 5 diskless on both machines — the gate still precedes everything |
| E9-E12, E8 | `lrvar-acceptance` (CF-3300 vs zb DISK: LSET vs RSET justification on non-fielded targets; `e.erase` keeps a field across ERASE), `fldary-acceptance`, `fldwidth-acceptance` | the disk machine's LSET/RSET and the FLD_TAB re-key |
| E4-E7 | `diskbasic-acceptance` (disk_probe_field / getput), `fldary-acceptance` | FIELD → fielded read on the disk machine (DISKSLOT_OK = 1 path) |
| E13 | `geteject-acceptance` (D-LINEJECT: a failed disk read raises 70 via seq_end) | the disk arm of se_pending |
| E14 | `castype-acceptance` `mt` / `mta` | MERGE on a wrong-typed tape: both search on (19 after break) |
| all | `wszero-acceptance` 20 rows (`rich2` = ERASE + string reads after a full-window $A5 load) | must stay SAME. ⚠️ `rich2` is BLIND to FLD_TAB: a $A5 k0 never equals a scalar's key ($41-$5A) — slice 4's "FIELD table fatal: MISS" |
| E1, E12 | `make unit-test` (test_str*.py edited by E19; test_field pokes 0/1 into LRSET_JUST — valid under the bit-0 rule) | — |
| E3, E16-E18 | `make ram-map-check` (A17 + regenerated `docs/ram-map.md`), `ram_map --selftest` | — |

### New rows (wszero-acceptance pattern: our own tape, VG-8020 vs `C-BIOS_MSX1_EU_REPACK_NODISK`; every address from `build/basic-reloc.sym`)

All VG-8020 values are **predictions** (the reference keeps no state below $F380 after `CLEAR
100,&HE000` — consistent with S10.0's PARM1 fill, not measured for these spans).

| row | tape (lo..hi, fill) | program | VG-8020 (predicted) | ZB before S9 (predicted) | after | edit witnessed |
|---|---|---|---|---|---|---|
| `fldread` | `FLD_TAB-1 .. FLD_TABEND-1`, **fill $41** (the `ret` lands on `$F018`, a hole; every entry = chan 65, key `A`,`A`) | `10 CLEAR 100,&HE000:BLOAD"CAS:",R` / `20 AA$="OK":PRINT"[";AA$;LEN(AA$);"]"` | `[OK 2]` | DIVERGES: fld_lookup hits, `fch_select(65)` loads a garbage context (face unknown — garbage string or a crash) | SAME | E7 |
| `fldclr` | same span, fill $A5 | `10 … BLOAD"CAS:",R` / `20 CLEAR 100,&HE000:PRINT"[";PEEK(FLD_TAB);PEEK(FLD_TAB+6);PEEK(FLD_TAB+90);"]"` | `[165 165 165]` | `[0 0 0]` (fld_init zeroes each chan byte) | SAME | E4-E6 |
| `flderase` | same span, fill $A5 | `10 CLEAR 100,&HE000:DIM W(9):BLOAD"CAS:",R` / `20 ERASE W:PRINT"[";PEEK(FLD_TAB+1);PEEK(FLD_TAB+2);"]"` | `[165 165]` | k1 rewritten (offset $25A5 − stride; exact value unverified) | SAME | E8 |
| `lset` | `all` (the full window), fill $A5 | `10 CLEAR 100,&HE000:ON ERROR GOTO 100:BLOAD"CAS:",R` / `20 LSET A$="X":RSET A$="X":FIELD#1,2 AS A$` / `30 PRINT"[";PEEK(LRSET_JUST);PEEK(FLD_CHAN);"]":END` / `100 PRINT"[E";ERR;"]";:RESUME NEXT` | `[E 5][E 5][E 5][165 165]` | `[… 1 165]` (RSET's `ld a,1` stored before the gate) | SAME | E9-E12; FLD_CHAN = control for §1.1 |
| `inpeof` | `all`, fill $A5, **then** `cas_encode.build_cas_ascii("D","HELLO\n")` appended | `10 CLEAR 100,&HE000:ON ERROR GOTO 100:BLOAD"CAS:",R` / `20 OPEN"CAS:D"FOR INPUT AS#1:LINE INPUT#1,A$:LINE INPUT#1,B$` / `30 PRINT"[";A$;"]":END` / `100 PRINT"[E";ERR;ERL;"]";:RESUME 30` | `[E 55 20][HELLO]` | `[E 165 20]…` (DISKOP_ERR = the loaded $A5) | SAME | E13 (§1.2) |
| `inpeof0` | `ctl` ($C000, below the window) + the same ASCII file | same program | `[E 55 20][HELLO]` | **UNMEASURED** — tells whether §1.2 is live TODAY at power-on (`$EF06`'s cold value) | SAME | E13, and whether S9 also fixes a shipped TIER 3 defect |
| `valtyp` | `all`, fill $A5 | `10 … BLOAD"CAS:",R` / `20 A$="X":PRINT"[";PEEK(&HEF35);"]"` (the probe refuses if any sym names `$EF35`) | `[165]` | `[1]` | SAME | E1 |
| `dskonly` (census, optional) | `all`, fill $A5 | after the load, under `ON ERROR … RESUME NEXT`: FILES, KILL"X", NAME"A"AS"B", LSET, RSET, FIELD, GET#1, PUT#1, OPEN"A:X", LOAD"A:X", BSAVE"A:X",0,1, COPY"A"TO"B", DSKF(0), a string read, ERASE, CLEAR; then one `S=S+PEEK(I)` sum per DISK-ONLY span, the spans GENERATED from the E17 tags (aliases with a diskless user excluded) | 165 × bytes per span | differs on FLD_TAB, LRSET_JUST, $EF35 | SAME | the E17 tag set as a runtime claim; S15's regression row. ⏱ keep under the 40 s run gap (the S8 `persist` lesson) |

Not a row: **MERGE"CAS:" of a binary file.** D-CASTYPE measured that the VG-8020 skips a wrong-typed
file and searches on (`19 in 20` after Ctrl-STOP) for a TOKENISED file; for a BINARY ($D0) file the
same is a **prediction**. zerobas's matcher skips it too, so `mc_ioerr` cannot be reached and its
retarget has no behavioural witness (static only: no diskless-reachable `ld a,(DISKOP_ERR)` remains
after E13 — `grep` it). A cheap regression row: castype `mb` (tape = binary X only, `MERGE"CAS:X"`,
break after 20 s) → predicted `[E 19 20]` on both.

### Knives (each one group or one byte; every knife build must first prove it BUILT: non-empty ROM, `tools/pin_plan.py --check` green, ROM hash ≠ the S9 build — a negative `ds` gives an empty binary with rc 0, and an empty ROM would make every row "HIT" for the wrong reason)

| knife | change (byte-neutral or a whole-group revert to pre-S9 code, which is pin-consistent by construction) | predicted |
|---|---|---|
| K-WS22 | E7's `ret z` → `nop` (seg F) | `fldread` diverges, nothing else |
| K-WS23 | E4's `ret z` → `nop` (seg F) | `fldclr` diverges |
| K-WS24 | E8's `ret z` → `nop` (sub p0) | `flderase` diverges |
| K-WS25 | revert G5 whole (ex_on_key back to seg E, the store back in lrset_common, lrsetst `or a / jr z`) | `lset` diverges (`1` for `165`); lrvar stays green |
| K-WS26 | E13's `ret z` → `nop` (seg F) | `inpeof` diverges; `inpeof0` diverges iff `$EF06` powers on nonzero |
| K-WS27 | revert G1 (VALTYP store back, E2's call removed) | `valtyp` diverges |
| K-WS28 | E2's `call fld_init_g` → three `nop` | **predicted BLIND** on openMSX: the disk machine's FLD_TAB at boot is power-on RAM, which holds no key a program can name ($FF / $00). Stated so nobody counts E2 as covered |
| K-WS29 | re-alias `PLY_NUMOVF equ DISKOP_A` | `ram_map --floor-top F380` stops listing PLY_NUMOVF (laundered by A17's alias rule) — the tool-level witness for E16 |

## 4. Risk on the DISK machine

- Every gate reads `DISKSLOT_OK` = DRVINF `$FB21` (S8). On a disk boot it is 1 after the scan; a
  SHIFT-suppressed disk ROM leaves 0 — then FIELD is unclaimed anyway (ERR 5) and the diskless
  ceiling is chosen, so skipping FLD_TAB is consistent.
- **Boot order is the real hazard.** `clear_vars` ([interp.asm:44](basic/interp.asm:44)) and
  `init_filechan` ([interp.asm:148](basic/interp.asm:148)) both run BEFORE `init_ext_roms`
  ([interp.asm:154](basic/interp.asm:154)) zeroes and sets DISKSLOT_OK. Gated, they read power-on
  DRVINF: nonzero → they init (on diskless that is a boot-time write, before any program exists — the
  same argument as SCAN_*'s BOOT-ONLY); zero → skipped, and **E2's post-scan call is what initialises
  FLD_TAB on the disk machine**. Without E2 a real disk machine would read power-on garbage as fields
  until the first NEW / RUN / CLEAR. ⚠️ At S15, re-check that the boot stack is nowhere near FLD_TAB
  ($F019) when those early boot inits run (unverified).
- LSET/RSET now derive the justification from the token at `(FN_RESUME)-1`: only `hk_lrset` reaches
  `lrset_tgt`, and FN_RESUME is untouched between `lrset_common` and the call-back (read off
  chan_gate_bare / hk_lrset). `lrvar-acceptance`'s RSET rows are the falsifier.
- `se_pending` on the disk machine returns DISKOP_ERR exactly as before. **Residual, to file
  (unmeasured):** on the DISK machine a tape INPUT# past the end still raises a STALE disk code if an
  earlier disk read failed (seq_end cannot tell a tape channel from a disk one). Not an S9 concern —
  the cell is legitimately the disk machine's — but a TIER 3 face.
- Speed: +~45 T per string-variable read on the disk machine (E7), unmeasured.
- Generated mirrors: `disk/basic-resident-abi.inc` and `sub/basic-resident-abi.inc` carry page-1
  call-back addresses (`lrset_tgt`, `field_prologue`, `pdfcb_resume`, …); the build regenerates them.
  G5 does not move `lrset_tgt` ($73BD, seg E start) — good, but `field_item` / `field_prologue` move
  by +6 −6 inside seg D only if they sit after the edit points (they are BEFORE ex_on_key's new home:
  unchanged). Only interp→strvar code between E2 and E1 shifts (+3), all of it in seg C below the
  mirrored `main_fat_*` ($6455) — re-check after the build anyway.

## 5. Order of work (suggested)

1. E16 + E17 + E18 (+ E3's FOSIGN/FOMBYTES) — equates/tool only; prove all four ROMs byte-identical
   by hash, then `make ram-map-check`.
2. Add the rows (`fldread`, `fldclr`, `flderase`, `lset`, `inpeof`, `inpeof0`, `valtyp`) and run them
   on the CURRENT build first: every "before" prediction above is scored before any code changes
   (the S10 discipline), and `inpeof0` decides whether §1.2 is a shipped defect.
3. G6 (se_pending), G3, G2 + G1, G4, G5 — one group per build, `pin_plan.py --check` after each.
4. Knives K-WS22..29, then the full battery once.
