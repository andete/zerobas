<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# The RAM map — every declared address, and what it is for

🔴 **GENERATED. Do not edit.** `make ram-map-doc` rewrites it from
`basic/sysvars.inc`, `sub/`, `disk/equates.inc` and `disk/*.asm`;
`make ram-map-check` fails if it has drifted. Change a cell's
comment, not this file.

Each row is ONE address. **Purpose is the author's own comment**,
quoted and truncated, never a paraphrase — a generated map that
summarises is a second place for the truth to drift.

🔴 **THREE THINGS THIS TABLE CANNOT TELL YOU**, and they are the
three that have cost this project days:

* **A cell addressed only as an offset in code has no `equ` and is
  not here at all.** Absence from this table is not emptiness.
* **A blank SIZE means the extent is not machine-readable** — it is
  pinned in `tools/ram-width-allow.txt` with the reason. It does
  NOT mean one byte.
* **A width can be present and WRONG.** `; 32 B … (word)` read as 2
  and `; (4 B each)` read as 4 for a 32-byte array, both on
  2026-09-21. No gate catches that; only reading does.

⚠️ **OVERLAP IS DESIGNED HERE.** The standalone disk ROM's buffers
sit on top of BASIC's cells on purpose, and the cassette buffers
sit inside both of main's disk buffers. The `also` column names the
other component's cell at the same address; the `inside` column
names the other component's BUFFER this address falls within. That
second one is the question a per-component map cannot answer.

* **basic** — 427 declared addresses in this project's own workspace `$E000..$F37F` (397 with a machine-readable width), plus **102** in the MSX standard work area at or above `$F380`.
* **disk** — 126 declared addresses in this project's own workspace `$E000..$F37F` (112 with a machine-readable width), plus **25** in the MSX standard work area at or above `$F380`.

## This project's own workspace (`$E000..$F37F`)

| address | size | component | name(s) | purpose | inside |
|---|---|---|---|---|---|
| `$E010` | 1 B | `basic` | `ERRMARK` | error landmark marker byte (1 B) |  |
| `$E011` | 1 B | `basic` | `MAXF` | current MAXFILES ceiling (0..FCH_CEIL); default 1 (1) |  |
| `$E012` | 1 B | `basic` | `FCH_ACTIVE` | channel live in the engine globals, 0 = none (1) |  |
| `$E013` | 1 B | `basic` | `TKLNUM` | tokeniser: 1 = line-number mode is armed (1) |  |
| `$E016` | 1 B | `basic` | `INDLR_N` | INPUT$(n,#f): remaining bytes to read (transient, 1) (1 B) |  |
| `$E017` | 2 B | `basic` | `MRG_PTR` | MERGE: write cursor into LINEBUF for the current line (2) |  |
| `$E019` | 2 B | `basic` | `FLD_CUROFF` | FIELD: running byte offset into the record buffer (2) |  |
| `$E01B` | 1 B | `basic` | `FLD_CHAN` | FIELD/LSET/RSET: the channel being fielded (1) |  |
| `$E01B` | 1 B | `disk` | `FLD_CHAN` | FIELD/LSET/RSET: the channel being fielded (1) |  |
| `$E01C` | 1 B | `basic` | `LRSET_JUST` | LSET/RSET: 0 = left-justify, 1 = right-justify (1) |  |
| `$E01D` | 1 B | `basic` | `LRSET_W` | LSET/RSET: destination field width (1) |  |
| `$E01D` | 1 B | `disk` | `LRSET_W` | LSET/RSET: destination field width (1) |  |
| `$E01E` | 2 B | `basic` | `LRSET_DEST` | LSET/RSET: destination ADDRESS of the store (2). (2 B) |  |
| `$E01E` | 2 B | `disk` | `LRSET_DEST` | LSET/RSET: destination ADDRESS of the store (2). (2 B) |  |
| `$E020` | 2 B | `basic` | `CURPTR` | current load pointer (2 bytes) |  |
| `$E022` | 2 B | `basic` | `ENDPTR` | final load address (2 bytes) |  |
| `$E024` | 2 B | `basic` | `EXECPTR` | execution address (2 bytes) |  |
| `$E026` | 2 B | `basic` | `PRGEND` | addr of the $0000 end-of-program marker (2 bytes) |  |
| `$E026` | 2 B | `disk` | `PRGEND` | addr of the $0000 end-of-program marker (2 bytes) |  |
| `$E028` | 1 B | `basic` | `ARY_OP/TKNAME` | tokeniser: 1 = previous char was part of a name |  |
| `$E029` |  | `basic` | `ARY_KEY/TKRADIX` | tokeniser: &H/&O accumulator radix (16 or 8) |  |
| `$E02A` | 1 B | `basic` | `TKRTOK` | tokeniser: &H/&O constant token to emit, $0C/$0B (1 B) |  |
| `$E02B` |  | `basic` | `ARY_TYPE/CLPTR` | CLOAD/LOAD: store cursor into the program area (2) |  |
| `$E02B` | 2 B | `disk` | `CLPTR` | CLOAD/LOAD: store cursor into the program area (2) |  |
| `$E02C` | 1 B | `basic` | `ARY_NIDX` | parsed subscript/bound count for the CURRENT | `disk` CLPTR |
| `$E02D` | 2 B | `basic` | `ARY_IDXP/CLINK` | CLOAD/LOAD: saved link word of the current line |  |
| `$E02D` | 2 B | `disk` | `CLINK` | CLOAD/LOAD: saved link word of the current line |  |
| `$E02F` |  | `basic` | `ARY_CUR/RUNFLAG` | [D-ARR-C] the text cursor, parked across the |  |
| `$E030` |  | `basic` | `GFX_OP/LST_LO/RN_TGT/SL_DELLO/SL_NUM` | main->tenant op: 0=selftest(G1) 1=plot(PSET/PRESET) 2=point (1) |  |
| `$E031` | 1 B | `basic` | `GFX_C` | main->tenant: resolved plot colour 0..15 (PSET/PRESET) (1) |  |
| `$E032` |  | `basic` | `GFX_RES/SL_SLOT` | tenant->main: POINT result colour 0..15 (1) |  |
| `$E033` | 1 B | `basic` | `GFX_REL` | parse_coord: 1 = STEP (relative) coordinate, 0 = absolute (1) |  |
| `$E034` |  | `basic` | `LST_HI/RN_LINE/SL_DELHI/SL_SIZE` | RENUM: the OLD number of the line it is in -- |  |
| `$E035` |  | `basic` | `ARY_ADDR` | [tenant return, RESOLVE] element address (2) |  |
| `$E036` |  | `basic` | `LST_PTR/SL_DELPTR/SL_TOK` | DELETE: the statement cursor, on the token |  |
| `$E037` | 1 B | `basic` | `ARY_ERR` | [tenant return] 0 ok; 1 Subscript-oor; (1 B) |  |
| `$E038` | 2 B | `basic` | `CURLINE` | link-field addr of the line being executed (2) |  |
| `$E03A` | 2 B | `basic` | `GOTOTGT` | pending branch-target line addr (2) |  |
| `$E03C` | 1 B | `basic` | `GOTOFLAG` | 1 = a branch (GOTO) is pending (1 B) |  |
| `$E03D` | 1 B | `basic` | `ENDFLAG` | 1 = END/STOP reached, stop the run (1 B) |  |
| `$E03E` | 2 B | `basic` | `RESUMEPTR` | mid-line resume token pointer (2) |  |
| `$E040` | 1 B | `basic` | `RESUMEFLAG` | 1 = resume at RESUMEPTR (set by RETURN / NEXT) (1 B) |  |
| `$E041` | 2 B | `basic` | `GSP` | newest GOSUB frame's address; == CTLTOP if none (2) |  |
| `$E043` | 2 B | `basic` | `FSP` | the FOR run's FLOOR: FOR frames are [CSP,FSP) (2) |  |
| `$E045` | 6 B | `basic` | `FOR_CUR` | scratch: a working copy of one FOR frame (11), and |  |
| `$E050` | 2 B | `basic` | `CSP` | the pool's allocation frontier, descending (2) |  |
| `$E052` | 2 B | `basic` | `CTLTOP` | the pool's TOP = strheap_varceil(), cached (2) |  |
| `$E054` | 2 B | `basic` | `TSP` | newest trap SERVICE record; valid iff TRAPSVC != 0 (2) |  |
| `$E056` | 2 B | `basic` | `CTLLIM` | the pool's collision FLOOR = ARYEND+2 (2). Written (2 B) |  |
| `$E058` | 2 B | `basic` | `SL_CEIL` | store_line: the ceiling a store stays below (2 B) |  |
| `$E05A` | 32 B | `basic` | `PU_DIG` | D-PUEXP: flt_fmt's significant digits, point removed (32 B) |  |
| `$E07A` | 2 B | `basic` | `CSR_ADDR` | VRAM address of the cell the cursor covers (2 B) |  |
| `$E07C` | 1 B | `basic` | `CSR_CHAR` | the character it covers, put back on removal (1 B) |  |
| `$E07D` | 1 B | `basic` | `CSR_ON` | 1 while the cursor is shown, else 0 (1 B) |  |
| `$E080` | 11 B | `basic` | `COPY_SRC` | the source's 11-byte 8.3 name field |  |
| `$E080` | 11 B | `disk` | `COPY_SRC` | the source's 11-byte 8.3 name field |  |
| `$E08B` | 2 B | `basic` | `COPY_CLUS` | the source's first cluster (word) |  |
| `$E08B` | 2 B | `disk` | `COPY_CLUS` | the source's first cluster (word) |  |
| `$E08D` | 4 B | `basic` | `COPY_LEFT` | bytes still to copy (4-byte LE) |  |
| `$E08D` | 4 B | `disk` | `COPY_LEFT` | bytes still to copy (4-byte LE) |  |
| `$E091` | 2 B | `basic` | `RL_HL` | main -> tenant: the write cursor (LINEBUF, or AUTO's preset) (2) |  |
| `$E093` | 1 B | `basic` | `RL_STAT` | tenant -> main: 0 = Enter, $FF = Ctrl-STOP / Ctrl-C (1) |  |
| `$E094` | 1 B | `basic` | `RL_ROW0` | the row where input began (1-based; 0 once scrolled off) (1) |  |
| `$E095` | 1 B | `basic` | `RL_COL0` | the column where input began, after any prompt (1) |  |
| `$E096` | 1 B | `basic` | `RL_LAST` | the logical line's last row at Enter (1) |  |
| `$E097` | 1 B | `basic` | `RL_KEY` | main -> tenant: the key CHGET returned (main waits in CHGET, as before) (1) |  |
| `$E098` | 1 B | `basic` | `DISKOP_ERR` | tenant -> main: ERR code of the last DSKIO failure, 0 = none (1) |  |
| `$E098` | 1 B | `disk` | `DISKOP_ERR` | tenant -> main: ERR code of the last DSKIO failure, 0 = none (1) |  |
| `$E099` | 2 B | `basic` | `FNSP` | newest FN frame's address, 0 = no FN call live (2) |  |
| `$E09B` | 1 B | `basic` | `FN_FST` | tenant -> main: 0 = frame saved, 1 = pool full -> ERR 7 (1) |  |
| `$E0B8` | 1 B | `basic` | `DATASTATE` | 0 = unpositioned (RESTORE), 1 = ready, 2 = exhausted (1 B) |  |
| `$E0B9` | 2 B | `basic` | `DATAPTR` | next unread DATA item (ASCII) in the program (2) |  |
| `$E0BB` | 2 B | `basic` | `DATALINE` | link-field of the line holding DATAPTR (2) |  |
| `$E0BD` | 2 B | `basic` | `RESTORE_LINE` | link-field a READ seeks DATA from when unpositioned (2) |  |
| `$E0C0` |  | `basic` | `INP_CURSOR/NUMBUF` | console INPUT LINEBUF read cursor (1 B, aliases NUMBUF) |  |
| `$E0C8` | 1 B | `basic` | `VALTYP` | 0 = numeric result, 1 = string result (1 byte) |  |
| `$E0C9` | 2 B | `basic` | `STRPTR` | pointer to the [len][bytes] descriptor (2 bytes) |  |
| `$E0C9` | 2 B | `disk` | `STRPTR` | pointer to the [len][bytes] descriptor (2 bytes) |  |
| `$E0CB` | 1 B | `basic` | `PRDEST` | PRINT destination: 0=screen, 1=file channel (1) |  |
| `$E0CC` | 1 B | `basic` | `PRDEV` | PRINT# device sink selector (1) |  |
| `$E0CD` |  | `basic` | `OO_DEVTYPE` | OPEN device-channel type being parsed (transient, 1) |  |
| `$E0CE` | 2 B | `basic` | `ARL_GETBYTE` | ascii_read_lines byte-source vector (2) |  |
| `$E0D0` | 2 B | `basic` | `CONTLINE` | saved CURLINE for CONT (2) |  |
| `$E0D2` | 2 B | `basic` | `CONTPTR` | saved resume token pointer for CONT (2) |  |
| `$E0D4` | 1 B | `basic` | `CONTVALID` | 1 = a CONT resume point is valid (1) |  |
| `$E0D5` | 1 B | `basic` | `SCAN_PRIM` | primary slot currently being scanned (1) |  |
| `$E0D6` | 1 B | `basic` | `SCAN_SLOT` | candidate slot id for RDSLT/CALSLT (1) |  |
| `$E0D7` | 2 B | `basic` | `SCAN_INIT` | candidate ROM's INIT entry address (2) |  |
| `$E0D9` | 2 B | `basic` | `SCAN_IY` | CALSLT slot word: high byte = slot (IYh) (2) |  |
| `$E0DB` |  | `basic` | `DISK_FCB/DISK_FCB_DRV` | +0: drive code (0=default,1=A,2=B; ignored) |  |
| `$E0DC` | 11 B | `basic` | `DISK_FCB_NAME` | +1..+11: 8.3 name field (11 bytes) |  |
| `$E0DC` | 11 B | `disk` | `DISK_FCB_NAME` | +1..+11: 8.3 name field (11 bytes) |  |
| `$E0E7` | 1 B | `basic` | `DISKSLOT` | disk ROM slot id for CALSLT (1) |  |
| `$E0E8` | 1 B | `basic` | `DISKSLOT_OK` | 1 = DISKSLOT holds a valid disk-ROM slot id (1 B) |  |
| `$E0E8` | 1 B | `disk` | `DISKSLOT_OK` | 1 = DISKSLOT holds a valid disk-ROM slot id (1 B) |  |
| `$E0E9` | 1 B | `basic` | `CAL_CURHI/VRAM_FLAG` | cassette ASCII load: served buffer high (1 B) |  |
| `$E0EA` |  | `basic` | `CAL_CNT` | cassette ASCII load: read position in the |  |
| `$E0EB` | 1 B | `basic` | `CAL_NEEDFILL` | cassette ASCII load: whether the buffer CAL_CURHI (1 B) |  |
| `$E0EC` |  | `basic` | `CAL_SAVE/CAS_WCNT` | cassette ASCII load: parked byte across a prefetch (1) |  |
| `$E0ED` | 2 B | `basic` | `DSV_PTR` | SAVE: current source byte pointer (2) |  |
| `$E0ED` | 2 B | `disk` | `DSV_PTR` | SAVE: current source byte pointer (2) |  |
| `$E0EF` | 2 B | `basic` | `DSV_END` | SAVE/BSAVE: last source byte addr, inclusive (2) |  |
| `$E0EF` | 2 B | `disk` | `DSV_END` | SAVE/BSAVE: last source byte addr, inclusive (2) |  |
| `$E0F1` | 2 B | `basic` | `SSE_OUT/TSV_PTR` | tenant -> main: next statement's start, or |  |
| `$E0F3` | 2 B | `basic` | `TSV_END` | tape save: last source-byte address, inclusive (2) |  |
| `$E0F5` | 1 B | `basic` | `FMT_GEOMSEL/TSV_CNT` | main -> tenant: 0 = 360k, 1 = 720k (1) |  |
| `$E0F6` | 1 B | `basic` | `FMT_RESULT/TSV_NAME` | tape save: 6-char filename buffer (space-padded) (1 B) |  |
| `$E0FC` | 1 B | `basic` | `FILES_ENTIDX/IN_RDLEN` | FILES: dir entry index 0..15 within a sector (1) |  |
| `$E0FC` | 1 B | `disk` | `FILES_ENTIDX` | FILES: dir entry index 0..15 within a sector (1) |  |
| `$E0FD` | 1 B | `basic` | `FCH_NUM` | open channel's file number, 0 = none open (1) |  |
| `$E0FE` | 1 B | `basic` | `FCH_MODE` | open mode: 0=none, 1=INPUT, 2=OUTPUT (1) |  |
| `$E0FF` | 1 B | `basic` | `FCH_RDMODE` | current read: 0=INPUT# (stop at ','/CR), 1=LINE (1) |  |
| `$E100` | 2 B | `basic` | `GFX_X1` | LINE endpoint 1 X (int16 LE) -- resident marshals, tenant reads |  |
| `$E102` | 2 B | `basic` | `GFX_Y1` | LINE endpoint 1 Y (int16 LE) |  |
| `$E104` | 2 B | `basic` | `GFX_X2` | LINE endpoint 2 X (int16 LE) |  |
| `$E106` | 2 B | `basic` | `GFX_Y2` | LINE endpoint 2 Y (int16 LE) |  |
| `$E108` | 1 B | `basic` | `GFX_MODE` | GFX_OP=3 sub-mode: 0=segment 1=box outline 2=box fill (1) |  |
| `$E109` | 2 B | `basic` | `GFX_CX` | Bresenham: current pixel X (int16, may be off-screen) (2) |  |
| `$E10B` | 2 B | `basic` | `GFX_CY` | Bresenham: current pixel Y (int16) (2) |  |
| `$E10D` | 2 B | `basic` | `GFX_ERR` | Bresenham: error accumulator, in [0,DMAJ) (2) |  |
| `$E10F` | 2 B | `basic` | `GFX_DMAJ` | Bresenham: major-axis delta (2) |  |
| `$E111` | 2 B | `basic` | `GFX_DMIN` | Bresenham: minor-axis delta (2) |  |
| `$E113` | 2 B | `basic` | `GFX_CNT` | Bresenham: major steps still to take (2) |  |
| `$E115` | 1 B | `basic` | `GFX_STEEP` | Bresenham: 0 = x-major, 1 = y-major (1) |  |
| `$E116` | 2 B | `basic` | `GFX_SMIN` | Bresenham: minor-axis step, $0001 (+1) or $FFFF (-1) (2) |  |
| `$E118` | 1 B | `basic` | `GFX_SDX` | init scratch: sign of (x2-x1), $01/$FF (1) |  |
| `$E119` | 1 B | `basic` | `GFX_SDY` | init scratch: sign of (y2-y1), $01/$FF (1) |  |
| `$E11A` | 2 B | `basic` | `GFX_TX1` | box: stashed corner 1 X (2) |  |
| `$E11C` | 2 B | `basic` | `GFX_TY1` | box: stashed corner 1 Y (2) |  |
| `$E11E` | 2 B | `basic` | `GFX_TX2` | box: stashed corner 2 X (2) |  |
| `$E120` | 2 B | `basic` | `GFX_TY2` | box: stashed corner 2 Y (2) |  |
| `$E122` | 2 B | `basic` | `GFX_FILLCNT` | box fill: scanlines remaining (2) |  |
| `$E124` | 2 B | `basic` | `GFX_YSTEP` | box fill: row step, $0001/$FFFF (2) -> ends $E126 (2 B) |  |
| `$E126` | 2 B | `basic` | `GFX_CXC` | centre X (int16 LE) (2) |  |
| `$E128` | 2 B | `basic` | `GFX_CYC` | centre Y (int16 LE) (2) |  |
| `$E12A` | 2 B | `basic` | `GFX_R` | radius (int16, >=0 -- resident guards G4-rneg) (2) |  |
| `$E12C` | 1 B | `basic` | `GFX_ASPMAJ` | 0 = x-major (aspect<=1), 1 = y-major (aspect>1) (1) |  |
| `$E12D` | 2 B | `basic` | `GFX_ASPS` | 8.8 minor scale S, round(minor_ratio*256); 256=no scale (2) |  |
| `$E12F` | 1 B | `basic` | `GFX_ARCF` | 0 = full circle (ignore S/E), 1 = arc (apply the mask) (1) |  |
| `$E130` | 2 B | `basic` | `GFX_SVX` | start boundary vector X, screen-offset scaled ints (2) |  |
| `$E132` | 2 B | `basic` | `GFX_SVY` | start boundary vector Y (2) |  |
| `$E134` | 2 B | `basic` | `GFX_EVX` | end boundary vector X (2) |  |
| `$E136` | 2 B | `basic` | `GFX_EVY` | end boundary vector Y (2) |  |
| `$E138` | 1 B | `basic` | `GFX_FULLW` | full-wrap flag (0/1): the two boundaries land in the |  |
| `$E139` | 2 B | `basic` | `GFX_QX` | midpoint-circle octant state: x (2) |  |
| `$E13B` | 2 B | `basic` | `GFX_QY` | midpoint-circle octant state: y (2) |  |
| `$E13D` | 2 B | `basic` | `GFX_QD` | midpoint-circle octant state: d (signed) (2) |  |
| `$E13F` | 2 B | `basic` | `GFX_PX` | tenant scratch: current (mirrored+scaled) offset X, |  |
| `$E141` | 2 B | `basic` | `GFX_PY` | tenant scratch: current offset Y (2) |  |
| `$E143` | 2 B | `basic` | `GFX_CS_AX` | circleparse scratch: cpt_angle_from_arga's neg-flag |  |
| `$E145` | 2 B | `basic` | `GFX_CS_AY` | circleparse scratch: cpt_angle_from_arga / |  |
| `$E147` | 2 B | `basic` | `GFX_M` | D-ARCMASK: M = floor(r/sqrt(2)), the octant's top |  |
| `$E149` | 2 B | `basic` | `GFX_WS_P` | wedge START boundary: in-octant position, 0..M-1 (2) |  |
| `$E14B` | 1 B | `basic` | `GFX_WS_O` | wedge START boundary: octant 0..7 (1) |  |
| `$E14C` | 2 B | `basic` | `GFX_SOCT` | start: trunc(\|a0\|*4/pi), RAW/unmasked int16 (the |  |
| `$E14E` | 2 B | `basic` | `GFX_SU14` | start: trunc(frac * 16384), 0..16383 (2) |  |
| `$E150` | 2 B | `basic` | `GFX_EOCT` | end: trunc(\|a1\|*4/pi), RAW/unmasked (2) |  |
| `$E152` | 2 B | `basic` | `GFX_EU14` | end: trunc(frac * 16384) (2) |  |
| `$E154` | 1 B | `basic` | `GFX_SNEG` | resident: start angle was negative -> spoke pending (1) |  |
| `$E155` | 1 B | `basic` | `GFX_ENEG` | resident: end angle was negative -> spoke pending (1) |  |
| `$E156` |  | `basic` | `GFX_B/GFX_WE_P` | wedge END boundary: in-octant position, 0..M-1 (2) |  |
| `$E157` |  | `basic` | `GFX_CPHASE` | CIRCLE-parse co-routine phase (sub/circleparse.asm): |  |
| `$E158` | 1 B | `basic` | `GFX_PTX/GFX_WE_O` | main->tenant: POINT target X, 0..255 (1) |  |
| `$E159` | 1 B | `basic` | `GFX_PTY/GFX_WRAPF` | main->tenant: POINT target Y, 0..191 (1) -> ends $E15A |  |
| `$E1C2` | 1 B | `basic` | `DIRECTF` | 1 = executing a DIRECT-mode line, 0 = running a (1 B) |  |
| `$E1C3` | 2 B | `basic` | `SAVSTK` | 2 B: SP anchor for the trap unwind. Written by |  |
| `$E1CB` | 4 B | `basic` | `ERRRESUME` | 4 B: resume context captured at trap time — |  |
| `$E1CF` | 2 B | `basic` | `SAVTXT` | 2 B: the CURRENT statement's text pointer, |  |
| `$E1D1` | 55 B | `basic` | `ZTRAP` | 18 entries * 3 B = 54 B ($E1D1..$E207). Each |  |
| `$E207` | 2 B | `basic` | `ZINTVAL` | 2 B: INTERVAL reload period in frames (0 = disarmed) |  |
| `$E209` | 2 B | `basic` | `ZINTCNT` | 2 B: INTERVAL live down-counter (frames to next fire) |  |
| `$E20B` | 1 B | `basic` | `TRAPENA` | 1 B: count of traps currently in state ON. Gates the |  |
| `$E20C` | 1 B | `basic` | `TRAPSVC` | 1 B: count of live SERVICING entries == depth of the |  |
| `$E20D` |  | `basic` | `SH_BASE/SH_OP` | the retired TRAPSTK's FREE-RAM run; SH_OP..SH_ERR |  |
| `$E20E` | 1 B | `basic` | `SH_LEN` | ALLOC/TEMP_ALLOC/BUILD_CONCAT arg: |  |
| `$E20F` | 2 B | `basic` | `SH_SRC` | SNAPSHOT arg: source descriptor |  |
| `$E211` | 2 B | `basic` | `SH_PTR` | result: ALLOC's body ptr / GC's new |  |
| `$E213` | 2 B | `basic` | `SH_PTR2` | result: TEMP_ALLOC's body-to-fill |  |
| `$E215` | 1 B | `basic` | `SH_START` | SLICE (op=5) arg: 0-based start (1 B) |  |
| `$E216` | 1 B | `basic` | `SH_COUNT` | SLICE (op=5) arg: byte count (1 B) |  |
| `$E217` | 2 B | `basic` | `SH_NUM` | HEX_BUILD/OCT_BUILD (op=6/7) arg: the |  |
| `$E219` | 1 B | `basic` | `SH_FILLBYTE` | FILL (op=8) arg: the byte to repeat |  |
| `$E21A` | 2 B | `basic` | `SH_DEST` | MID_STORE (op=9) arg: the MID$- |  |
| `$E21C` | 2 B | `basic` | `SH_P` | INSTR_SEARCH (op=11) arg: p (2 B) |  |
| `$E21E` | 1 B | `basic` | `SH_ERR` | result: 0 ok, 1 Out of memory, 2 = |  |
| `$E21F` | 1 B | `basic` | `TRAPPEND` | 1 B (was just past the retired TRAPSTK): 1 = |  |
| `$E220` | 1 B | `basic` | `GFX_DJ` | JIFFY delta observed while drawing under EI (1) |  |
| `$E221` | 2 B | `basic` | `BL_PTR` | 2 B: main -> tenant, the token cursor after BLOAD |  |
| `$E223` | 1 B | `basic` | `BL_STAT` | 1 B: tenant -> main. 0 = loaded, 1 = `load |  |
| `$E224` | 1 B | `basic` | `SV_OP` | 1 B: main -> tenant, SV_OP_* engine selector |  |
| `$E225` | 1 B | `basic` | `SV_STAT` | 1 B: tenant -> main, 0 = written, 1 = load_error |  |
| `$E226` | 1 B | `basic` | `TRACEFLAG` | 1 B: TRON state (0 = TROFF) |  |
| `$E227` | 2 B | `basic` | `FN_RESUME` | D-FNEXPR: cursor past a filename expr (2 B) |  |
| `$E227` | 2 B | `disk` | `FN_RESUME` | D-FNEXPR: cursor past a filename expr (2 B) |  |
| `$E229` | 1 B | `basic` | `LOC_COL` | 1 B: LOCATE's parsed column, pre-clamp |  |
| `$E22A` | 1 B | `basic` | `LOC_ROW` | 1 B: LOCATE's parsed row, pre-clamp |  |
| `$E22B` | 2 B | `basic` | `SW_ADDR` | 2 B: the operand just resolved |  |
| `$E22D` | 1 B | `basic` | `SW_TYPE` | 1 B: its type (1 = string, 2/4/8 numeric) |  |
| `$E22E` | 2 B | `basic` | `SW_ADDR1` | 2 B: operand 1, held across operand 2's parse |  |
| `$E230` | 1 B | `basic` | `SW_TYPE1` | 1 B: operand 1's type |  |
| `$E231` | 1 B | `basic` | `SW_MODE` | 1 B: 0 = this operand MAY be created, 1 = must exist |  |
| `$E232` | 2 B | `basic` | `POOLSIZE` | 2 B: the size CLEAR recorded. Written ONLY by |  |
| `$E234` | 2 B | `basic` | `PLN_NUM` | 2 B: the parsed line number (BC), $FFFF if the |  |
| `$E236` | 2 B | `basic` | `PLN_PTR` | 2 B: LINEBUF pointer at the body (HL) |  |
| `$E238` | 2 B | `basic` | `DB_SKIP` | rendered bytes still to discard (2 B; TEMPTOP's old cell) |  |
| `$E23A` | 1 B | `basic` | `DB_MORE` | 1 = the render ran past the window (1 B) |  |
| `$E23B` | 2 B | `basic` | `DB_RESSKIP` | resume: bytes of the resume token already drained (2 B) |  |
| `$E23D` | 1 B | `basic` | `DB_RESUME` | 1 = this render may abort + resume (detok only) (1 B) |  |
| `$E268` | 2 B | `basic` | `FRETOP` | heap low boundary; heap occupies (2 B) |  |
| `$E26A` | 3 B | `basic` | `RVDESC` | $E26A: [len:1][ptr:2] scratch descriptor (3 B) |  |
| `$E26D` | 256 B | `basic` | `STRSCR` | [len][bytes:STRMAX] staging, $E26D..$E36C |  |
| `$E26D` | 256 B | `disk` | `STRSCR` | [len][bytes:STRMAX] staging, $E26D..$E36C |  |
| `$E299` | 1 B | `disk` | `FDC_IFF` | saved caller IFF2 across a sector op (1 = was EI) (1 B) | `basic` STRSCR |
| `$E29A` | 1 B | `disk` | `FDC_CNT` | remaining sector count (1 B) | `basic` STRSCR |
| `$E29B` | 2 B | `disk` | `FDC_LSEC` | current logical sector (word) | `basic` STRSCR |
| `$E29D` | 2 B | `disk` | `FDC_DEST` | current transfer address (word) | `basic` STRSCR |
| `$E29F` | 1 B | `disk` | `FDC_TRY` | read attempt counter (1 B) | `basic` STRSCR |
| `$E381` | 96 B | `basic` | `DB_WIN` | the render window, one page (96 B) |  |
| `$E3E1` | 2 B | `basic` | `ISRCH_A` | resolved A-operand body base (2 B) |  |
| `$E3E3` | 2 B | `basic` | `ISRCH_B` | $E3E3: resolved B-operand body base (2 B) |  |
| `$E3E5` | 1 B | `basic` | `GFX_BAD/STRENG_SPARE` | VRAM read-back mismatch count (1) |  |
| `$E3E6` |  | `basic` | `MIDS_DEST` |  |  |
| `$E3E8` | 1 B | `basic` | `GFX_PTOP` | span-stack top-of-stack index, 0..GFX_PSTK_CAP (1) |  |
| `$E3E9` | 1 B | `basic` | `GFX_POVF` | 1 = the stack overflowed; resident raises ERR 7 (1) |  |
| `$E3EA` | 1 B | `basic` | `GFX_PTESTX` | gfx_paint_inside/gfx_paint_plot: pixel-under-test X (1) |  |
| `$E3EB` | 1 B | `basic` | `GFX_PTESTY` | ...Y (1) |  |
| `$E3EC` | 1 B | `basic` | `GFX_PFY` | gfx_paint_flood/_process: current span's row (1) |  |
| `$E3ED` | 1 B | `basic` | `GFX_PXL` | ...current span's left column (1) |  |
| `$E3EE` | 1 B | `basic` | `GFX_PXR` | ...current span's right column (1) |  |
| `$E3EF` | 1 B | `basic` | `GFX_PSCX` | gfx_paint_process/_scan_row: scan cursor column (1) |  |
| `$E3F0` | 1 B | `basic` | `GFX_PSCY` | gfx_paint_scan_row: the neighbour row being scanned (1) |  |
| `$E3F1` | 1 B | `basic` | `GFX_PSPA` | gfx_paint_scan_row: pending sub-span's start column (1) |  |
| `$E3F2` |  | `basic` | `GFX_CS_M1/GFX_DBUF/GFX_PSTK/GFX_VBUF` | span-stack array base: GFX_PSTK_CAP * [y][xL][xR] |  |
| `$E3F6` | 8 B | `basic` | `GFX_CS_M2` | $E3F6: r*r for the same compare, CONTIGUOUS with |  |
| `$E412` | 2 B | `basic` | `GFX_SN` | $E412: SPRITE$ entry index / PUT SPRITE plane (2) |  |
| `$E414` | 1 B | `basic` | `GFX_VLEN` | $E414: the entry size the tenant read back (1) |  |
| `$E415` | 2 B | `basic` | `GFX_SDESC` | $E415: SPRITE$(n)= RHS string descriptor |  |
| `$E417` | 2 B | `basic` | `GFX_SC` | $E417: PUT SPRITE colour (2). x/y need no cells -- (2 B) |  |
| `$E419` | 2 B | `basic` | `GFX_SPATN` | $E419: ...pattern number (2) |  |
| `$E41B` | 1 B | `basic` | `GFX_SSIZE` | $E41B: SCREEN's sprite-size argument while a mode |  |
| `$E41C` | 1 B | `basic` | `GFX_SARGN` | $E41C: how many extra SCREEN arguments have been |  |
| `$E41D` | 1 B | `basic` | `GFX_SFLAGS` | $E41D: which arguments were GIVEN -- (1 B) |  |
| `$E4A0` | 1 B | `disk` | `FAT_SECPERCLUS` | sectors per cluster (byte) |  |
| `$E4A1` | 2 B | `disk` | `FAT_FATSTART` | first FAT sector (= reserved sectors) (word) |  |
| `$E4A3` | 2 B | `disk` | `FAT_FIRSTROOT` | first root-directory sector (word) |  |
| `$E4A5` | 2 B | `disk` | `FAT_ROOTSECS` | number of root-directory sectors (word) |  |
| `$E4A7` | 2 B | `disk` | `FAT_FIRSTDATA` | first data sector (word) |  |
| `$E4A9` | 2 B | `disk` | `FAT_CURCLUS` | current cluster in the open file's chain (word) |  |
| `$E4AB` | 1 B | `disk` | `FAT_CLUSSEC` | sector index within current cluster (byte) |  |
| `$E4AC` | 2 B | `disk` | `FAT_FIRSTCLUS` | first cluster of the found file (word) |  |
| `$E4AE` | 4 B | `disk` | `FAT_FILESIZE` | file size in bytes (4-byte LE) |  |
| `$E4B2` | 1 B | `disk` | `FAT_PARITY` | 1 = odd cluster, 0 = even (FAT12 nibble pack) (1 B) |  |
| `$E4B3` | 2 B | `disk` | `FAT_BYTEIDX` | byte index within a FAT sector (word, 0..511) |  |
| `$E4B5` | 2 B | `disk` | `FAT_FATSEC` | FAT sector currently read (word) |  |
| `$E4B7` |  | `disk` | `FAT_B0` | first FAT byte of a 12-bit entry |  |
| `$E4B8` |  | `disk` | `FAT_B1` | second FAT byte of a 12-bit entry |  |
| `$E4B9` | 2 B | `disk` | `FAT_NAMEPTR` | -> 11-byte search name (word) |  |
| `$E4BB` | 2 B | `disk` | `FAT_DIRSEC` | current root-dir sector being scanned (word) |  |
| `$E4BD` | 2 B | `disk` | `FAT_DIRREM` | root-dir sectors remaining to scan (word) |  |
| `$E4BF` |  | `disk` | `BDOS_RECIDX` | next 128-byte record within SECTOR_BUF (0..4) |  |
| `$E4C0` | 2 B | `disk` | `BDOS_DTA` | current DTA pointer (word; default DTA_DEFAULT) |  |
| `$E4F2` | 2 B | `basic` | `GFX_DPTR` | $E4F2: parse cursor in the current frame (2) |  |
| `$E4F4` | 2 B | `basic` | `GFX_DEND` | $E4F4: one past the current frame's last byte (2) |  |
| `$E4F6` | 2 B | `basic` | `GFX_DFREE` | $E4F6: next free byte in GFX_DBUF (2) |  |
| `$E4F8` | 1 B | `basic` | `GFX_DFTOP` | $E4F8: X-frame stack depth (1) |  |
| `$E4F9` | 32 B | `basic` | `GFX_DFSTK` | $E4F9: saved [ptr][end] per outer frame -- |  |
| `$E519` | 2 B | `basic` | `GFX_DCMD` | $E519: current command's start cursor, |  |
| `$E51B` | 1 B | `basic` | `GFX_DSUBN` | $E51B: substitutions RESOLVED for this command (1) |  |
| `$E51C` | 1 B | `basic` | `GFX_DSUBI` | $E51C: substitutions SEEN so far this re-parse (1) |  |
| `$E51D` | 4 B | `basic` | `GFX_DSUB` | $E51D: the resolved values, 2 slots (M takes two) (4) |  |
| `$E521` | 1 B | `basic` | `GFX_DSUBLEN` | $E521: slot 0's string length (X only) (1) |  |
| `$E522` | 1 B | `basic` | `GFX_DREQ` | $E522: tenant->resident: 0 = done, 1 = resolve an |  |
| `$E523` | 1 B | `basic` | `GFX_DRESUME` | $E523: resident->tenant: 1 = resuming (1) |  |
| `$E524` | 2 B | `basic` | `GFX_DVAL` | $E524: the resolved int16, or a string body ptr (2) |  |
| `$E526` | 1 B | `basic` | `GFX_DVLEN` | $E526: that string's length (1) |  |
| `$E527` | 24 B | `basic` | `GFX_DEXP` | $E527: NUL-terminated copy of the text between |  |
| `$E53F` | 1 B | `basic` | `GFX_DFB` | $E53F: 1 = B (blank move) prefix pending (1) |  |
| `$E540` | 1 B | `basic` | `GFX_DFN` | $E540: 1 = N (no-update) prefix pending (1) |  |
| `$E541` | 2 B | `basic` | `GFX_DARG` | $E541: last parsed argument (int16 LE) (2) |  |
| `$E542` | 4 B | `disk` | `BDOS_BYTESLEFT` | bytes of the open file not yet delivered (4-byte LE) | `basic` GFX_DARG |
| `$E543` | 2 B | `basic` | `GFX_DDX` | $E543: this command's dx (int16) (2) | `disk` BDOS_BYTESLEFT |
| `$E545` | 2 B | `basic` | `GFX_DDY` | $E545: ...dy (2) | `disk` BDOS_BYTESLEFT |
| `$E546` | 1 B | `disk` | `BDOS_WRMODE` | 1 = a file is open for sequential write (byte) | `basic` GFX_DDY |
| `$E547` | 2 B | `basic` | `GFX_DTX` | $E547: move target X (2) |  |
| `$E547` | 2 B | `disk` | `BDOS_WRCLUS/FWR_CLUS` | chain-tail cluster currently being filled (word) |  |
| `$E549` | 2 B | `basic` | `GFX_DTY` | $E549: ...Y (2) |  |
| `$E549` | 2 B | `disk` | `BDOS_WRFIRST/FWR_FIRST` | file's first cluster, 0 until first allocated (word) |  |
| `$E54B` | 2 B | `basic` | `GFX_DTMP` | $E54B: mul/rotate/sign scratch (2) |  |
| `$E54B` | 1 B | `disk` | `BDOS_WRSECIDX/FWR_SECIDX` | sector index within the current cluster (byte) |  |
| `$E54C` | 2 B | `disk` | `BDOS_WRBUFLEN/FWR_BUFLEN` | bytes currently buffered in SECTOR_BUF (word, 0..512) | `basic` GFX_DTMP |
| `$E54D` | 2 B | `basic` | `GFX_DSP` | $E54D: tenant entry SP -- an error deep in the (2 B) | `disk` BDOS_WRBUFLEN/FWR_BUFLEN |
| `$E54E` | 4 B | `disk` | `BDOS_WRBYTES/FWR_BYTES` | total bytes written so far = final file size (4-byte LE) | `basic` GFX_DSP |
| `$E54F` | 2 B | `basic` | `DEFT_PTR` | $E54F: token cursor in AND out (2) | `disk` BDOS_WRBYTES/FWR_BYTES |
| `$E551` | 2 B | `basic` | `RDV_VAL` | $E551: the value read (int16 LE) (2) | `disk` BDOS_WRBYTES/FWR_BYTES |
| `$E552` | 2 B | `disk` | `BDOS_DIRSEC/FWR_DIRSEC` | logical sector holding the open file's dir entry (word) | `basic` RDV_VAL |
| `$E553` | 1 B | `basic` | `RDV_ST` | $E553: tenant -> main STATUS (1): (1 B) | `disk` BDOS_DIRSEC/FWR_DIRSEC |
| `$E554` | 1 B | `basic` | `RDV_MODE` | $E554: main -> tenant MODE (1 B), D-READVAR: |  |
| `$E554` | 2 B | `disk` | `BDOS_DIROFF/FWR_DIROFF` | byte offset of that dir entry within its sector (word) |  |
| `$E555` | 2 B | `basic` | `TGT_ADDR` | $E555: element address, or 0 = scalar (2) | `disk` BDOS_DIROFF/FWR_DIROFF |
| `$E556` | 2 B | `disk` | `FAT_WRTMP` | transient scratch for the FAT12 write helpers (word) | `basic` TGT_ADDR |
| `$E558` |  | `disk` | `FAT_WRTMP2` | second transient (free-cluster scan cached sector) |  |
| `$E55A` | 1 B | `basic` | `GFX_DSCALE/GFX_PSTK_END` | $E55A: persistent scale, quarter units, |  |
| `$E55A` | 1 B | `disk` | `FAT_NUMFATS` | number of FAT copies (byte; from BPB +16) (1 B) |  |
| `$E55B` |  | `basic` | `GFX_DANGLE` | $E55B: persistent angle 0..3 (1). Boot 0 |  |
| `$E55B` | 2 B | `disk` | `FAT_SECPERFAT` | sectors per FAT copy (word; from BPB +22) |  |
| `$E55C` | 2 B | `basic` | `GFX_G8N/GFX_PPITCH` | $E55C: 1 or 4, live only inside a PAINT | `disk` FAT_SECPERFAT |
| `$E55D` | 1 B | `disk` | `HOOK_SLOT` | our slot byte for the HPHYD inter-slot hook (1) | `basic` GFX_G8N/GFX_PPITCH |
| `$E55E` | 2 B | `basic` | `GFX_G8V` | $E55E: written value (int16 LE) (2) |  |
| `$E55E` | 2 B | `disk` | `BDOS_SRCHIDX` | runtime dir-search cursor (word; M19) |  |
| `$E560` | 1 B | `disk` | `BOOT_SV_A8/RRND_RECSEC` | r0 & 3 (record-in-sector) across the sector-seek loop (1 B) |  |
| `$E561` | 1 B | `disk` | `BOOT_SV_SEC/RRND_CLUSSEC` | FAT_CLUSSEC-1 across the cluster->sector multiply loop (1 B) |  |
| `$E562` | 2 B | `disk` | `R30_HL` | $0030 handler: saved caller HL (word) |  |
| `$E564` | 2 B | `disk` | `R30_BC` | $0030 handler: saved caller BC (word) |  |
| `$E566` | 2 B | `disk` | `R30_DE` | $0030 handler: saved caller DE (word) |  |
| `$E568` | 2 B | `disk` | `R30_AF` | $0030 handler: saved caller AF incl. carry (word) |  |
| `$E56A` | 2 B | `disk` | `CALSLT_HL` | CALSLT handler: HL stash across the call setup (word) |  |
| `$E56C` |  | `disk` | `FREAD_LEFT/RDBLK_REQ` | records requested (HL on entry) (word) |  |
| `$E56E` | 2 B | `disk` | `RDBLK_RECSIZE` | record size from FCB+14 (word) |  |
| `$E570` | 2 B | `disk` | `RDBLK_DONE` | records delivered so far (word; = HL on return) |  |
| `$E572` | 2 B | `disk` | `RDBLK_CNT` | bytes left in the current record (word) |  |
| `$E574` | 2 B | `disk` | `FREAD_OFF/RDBLK_BUFPOS` | byte index within FAT_DBUF (0..512) (word) |  |
| `$E576` | 2 B | `disk` | `RDBLK_DST` | current DTA write pointer (word; from BDOS_DTA) |  |
| `$E578` | 2 B | `disk` | `P1_DEST` | saved page-1 destination word (dskio bounce path) |  |
| `$E57A` | 3 B | `disk` | `WRBLK_REC` | 24-bit target record number for the current step (3 bytes) |  |
| `$E57D` | 1 B | `disk` | `WRBLK_RECSEC` | WRBLK_REC & 3 (record-in-sector) across the seek/extend loop (1 B) |  |
| `$E57E` | 2 B | `disk` | `WRBLK_RS` | resolved record size (FCB+14..15, 0 -> 128) (word) |  |
| `$E580` | 2 B | `disk` | `WRBLK_CNT` | records still to process this call (word, counts down to 0) |  |
| `$E582` | 2 B | `disk` | `WRBLK_REQ` | the ORIGINAL requested count (word; HL is pinned-preserved |  |
| `$E584` | 2 B | `disk` | `WRBLK_PREVCLUS` | cluster before the current step's advance/allocate (word); |  |
| `$E586` | 2 B | `disk` | `WRBLK_KEEPCNT` | shrink path: clusters-to-keep walk countdown (word) |  |
| `$E588` | 2 B | `disk` | `WRBLK_NEXTCLUS` | shrink path: next cluster to free, saved across the |  |
| `$E58A` | 1 B | `disk` | `WRBLK_CURVALID` | byte: 0 = iterator not yet positioned this call (1 B) |  |
| `$E58B` | 2 B | `disk` | `WRBLK_CURSEC` | word: sector-in-file the iterator currently sits |  |
| `$E58D` | 2 B | `disk` | `FAT_ALLOCHINT` | next cluster to try in fat_alloc_cluster's scan (word) |  |
| `$E58F` | 3 B | `disk` | `RDBLK_RRSTART` | k_47B2 entry RR, FCB+33..35 (24-bit, 3 bytes) |  |
| `$E592` | 20 B | `disk` | `DRV_TRAMP` | 4 CALLF trampolines, 5 bytes each ($E592-$E5A5; |  |
| `$E5A6` | 2 B | `disk` | `BDOS_SEQREC` | records delivered so far by RDSEQ (K, word) |  |
| `$E5A8` | 2 B | `disk` | `DBUF_PTR` | word -> the 512-byte DATA/sector buffer |  |
| `$E5AA` | 2 B | `disk` | `MBUF_PTR` | word -> the 512-byte FAT/dir METADATA buffer |  |
| `$E5C0` | 512 B | `basic` | `FAT_DBUF/FSECTOR_BUF` | file data / read sector buffer ($E5C0..$E7BF) |  |
| `$E5C0` | 512 B | `disk` | `FAT_DBUF/FSECTOR_BUF/SECTOR_BUF` | 512-byte sector buffer ($E5C0-$E7BF) = main FSECTOR_BUF |  |
| `$E600` | 256 B | `basic` | `CAL_BUF/CAS_WBUF` | cassette ASCII load: 256-byte tape block buffer (in idle FSECTOR_BUF) | `disk` FAT_DBUF/FSECTOR_BUF/SECTOR_BUF |
| `$E7C0` | 512 B | `basic` | `FAT_MBUF/FWBUF` | FAT/dir metadata sector buffer ($E7C0..$E9BF) |  |
| `$E7C0` | 512 B | `disk` | `FAT_MBUF/FWBUF/WBUF` | write-back FAT/dir sector buffer ($E7C0..$E9BF) = main FWBUF |  |
| `$E800` | 256 B | `basic` | `CAL_BUF2` | cassette ASCII load: 256-byte read-ahead buffer (in idle FWBUF) | `disk` FAT_MBUF/FWBUF/WBUF |
| `$E9B4` | 4 B | `disk` | `WRBLK_MULACC` | 32-bit product accumulator (LE) | `basic` FAT_MBUF/FWBUF |
| `$E9B8` | 4 B | `disk` | `WRBLK_MULOP` | 32-bit shifted-RS operand (LE), doubled each iteration | `basic` FAT_MBUF/FWBUF |
| `$E9BC` | 3 B | `disk` | `WRBLK_MULN` | 24-bit shifting copy of RR_start (bit tested each iteration) | `basic` FAT_MBUF/FWBUF |
| `$E9C0` | 1 B | `basic` | `FAT_SECPERCLUS` | sectors per cluster (byte) |  |
| `$E9C1` | 2 B | `basic` | `FAT_FATSTART` | first FAT sector (= reserved sectors) (word) |  |
| `$E9C3` | 2 B | `basic` | `FAT_FIRSTROOT` | first root-directory sector (word) |  |
| `$E9C5` | 2 B | `basic` | `FAT_ROOTSECS` | number of root-directory sectors (word) |  |
| `$E9C7` | 2 B | `basic` | `FAT_FIRSTDATA` | first data sector (word) |  |
| `$E9C9` | 2 B | `basic` | `FAT_CURCLUS/FCH_STATE0` | current cluster in the open file's chain (word) |  |
| `$E9CB` | 1 B | `basic` | `FAT_CLUSSEC` | sector index within current cluster (byte) |  |
| `$E9CC` | 2 B | `basic` | `FAT_FIRSTCLUS` | first cluster of the found file (word) |  |
| `$E9CE` | 4 B | `basic` | `FAT_FILESIZE` | file size in bytes (4-byte LE) |  |
| `$E9D2` | 1 B | `basic` | `FAT_NUMFATS` | number of FAT copies (byte; from BPB +16) (1 B) |  |
| `$E9D3` | 2 B | `basic` | `FAT_SECPERFAT` | sectors per FAT copy (word; from BPB +22) |  |
| `$E9D5` | 1 B | `basic` | `FAT_PARITY` | 1 = odd cluster, 0 = even (FAT12 nibble pack) (1 B) |  |
| `$E9D6` | 2 B | `basic` | `FAT_BYTEIDX` | byte index within a FAT sector (word, 0..511) |  |
| `$E9D8` | 2 B | `basic` | `FAT_FATSEC` | FAT sector currently read (word) |  |
| `$E9DA` | 1 B | `basic` | `FAT_B0` | first FAT byte of a 12-bit entry (1 B) |  |
| `$E9DB` | 1 B | `basic` | `FAT_B1` | second FAT byte of a 12-bit entry (1 B) |  |
| `$E9DC` | 2 B | `basic` | `FAT_NAMEPTR` | -> 11-byte search name (word) |  |
| `$E9DE` | 2 B | `basic` | `FAT_DIRSEC` | current root-dir sector being scanned (word) |  |
| `$E9E0` | 2 B | `basic` | `FAT_DIRREM` | root-dir sectors remaining to scan (word) |  |
| `$E9E2` | 2 B | `basic` | `FAT_WRTMP` | transient scratch for the FAT12 write helpers (word) |  |
| `$E9E4` | 2 B | `basic` | `FAT_WRTMP2` | second transient (free-cluster scan cached sector) (2 B) |  |
| `$E9E6` | 2 B | `basic` | `FREAD_OFF` | next byte index within FSECTOR_BUF (0..512) (word) |  |
| `$E9E8` | 4 B | `basic` | `FREAD_LEFT` | bytes of the open file still undelivered (4-byte LE) |  |
| `$E9EC` | 2 B | `basic` | `FWR_CLUS` | chain-tail cluster currently being filled (word) |  |
| `$E9EE` | 2 B | `basic` | `FWR_FIRST` | file's first cluster, 0 until first allocated (word) |  |
| `$E9F0` | 1 B | `basic` | `FWR_SECIDX` | sector index within the current cluster (byte) |  |
| `$E9F1` | 2 B | `basic` | `FWR_BUFLEN` | bytes currently buffered in FSECTOR_BUF (word, 0..512) |  |
| `$E9F3` | 4 B | `basic` | `FWR_BYTES` | total bytes written so far = final file size (4-byte LE) |  |
| `$E9F7` | 2 B | `basic` | `FWR_DIRSEC` | logical sector holding the open file's dir entry (word) |  |
| `$E9F7` | 2 B | `disk` | `main_FWR_DIRSEC` | main's FWR_DIRSEC -- logical sector holding the open file's dir entry (word) |  |
| `$E9F9` | 2 B | `basic` | `FWR_DIROFF` | byte offset of that dir entry within its sector (word) |  |
| `$E9F9` | 2 B | `disk` | `main_FWR_DIROFF` | main's FWR_DIROFF -- byte offset of that dir entry within its sector (word) |  |
| `$E9FB` | 1 B | `basic` | `AUDIO_VMASK/DISKOP_OP/FOPEN_SEL/LE_OP` | main -> tenant: DISKOP_SEL_* primitive selector (1) |  |
| `$E9FB` | 1 B | `disk` | `DISKOP_OP/FOPEN_SEL` | main -> tenant: DISKOP_SEL_* primitive selector (1) |  |
| `$E9FC` | 1 B | `basic` | `AUDIO_STATUS/BN_STAT/CM_STATUS/DEFT_STATUS/DISKOP_STATUS/LE_STATUS` | $E9FC tenant->main: 0 ok / nonzero ERR code |  |
| `$E9FC` | 1 B | `disk` | `DISKOP_STATUS` | tenant -> main: the disposition (1 B) |  |
| `$E9FD` |  | `basic` | `DISKOP_A/PLY_NUMOVF` | tenant -> main: the primitive's real A output, |  |
| `$E9FE` |  | `basic` | `BN_PTR/DISKOP_HL` | tenant -> main: the primitive's real HL output |  |
| `$EA00` | 16 B | `basic` | `FCH_MODES` | 16 B ($EA00..$EA0F) |  |
| `$EA10` | 32 B | `basic` | `FCH_RECLENS` | 32 B ($EA10..$EA2F). ~~$EA92..$EAFF free (110 B)~~ |  |
| `$EA30` | 2 B | `basic` | `RN_PTR` | RENUM: the reference-pass cursor (2) |  |
| `$EA32` | 2 B | `basic` | `AU_NUM/RN_NEW` | AUTO: the line number being prompted (2) |  |
| `$EA34` | 2 B | `basic` | `RN_OLD` | RENUM: old line to start renumbering at (2) |  |
| `$EA36` | 2 B | `basic` | `AU_INC/RN_INC` | AUTO: the increment (2) |  |
| `$EA38` | 1 B | `basic` | `RL_AUTO` | read_line: 1 = AUTO's polling mode (1) |  |
| `$EA39` | 1 B | `basic` | `LPTPOS` | printer head column, 0-based (1) |  |
| `$EA39` | 1 B | `disk` | `LPTPOS` | printer head column, 0-based (1) |  |
| `$EA3A` | 2 B | `basic` | `GP_SRC` | pass cursor into FSECTOR_BUF (2) |  |
| `$EA3C` | 2 B | `basic` | `GP_LEFT` | record bytes still to move, ends $EA3E (2 B) |  |
| `$EA3E` | 2 B | `basic` | `CLR_SAVE` | fg+bg, in flight across a COLOR statement (2) |  |
| `$EA40` | 32 B | `basic` | `FCH_RECNOS` | 32 B ($EA40..$EA5F): per-channel record number |  |
| `$EA60` | 32 B | `basic` | `PU_NUM` | PRINT USING numeric render buffer, 0-terminated (32 B) |  |
| `$EA92` | 2 B | `basic` | `FN_BASE/FN_PTR/FOR_STK_END` | RETIRED AS A STACK; the literal survives ONLY as |  |
| `$EA94` | 2 B | `basic` | `FN_DPTR` | 2 B: the definition cursor, tenant-only |  |
| `$EA96` | 2 B | `basic` | `FN_KEY` | 2 B: the formal (or the $FFFF result slot) |  |
| `$EA98` | 1 B | `basic` | `FN_TYP` | 1 B: its type -- and the ERR code on req 0 |  |
| `$EA99` | 1 B | `basic` | `FN_FEND` | 1 B: low byte of one-past the live frame. |  |
| `$EA9A` | 1 B | `basic` | `FN_SLOTP` | 1 B: low byte of the slot the NEXT formal takes |  |
| `$EA9B` | 1 B | `basic` | `FN_RTYPE` | 1 B: the FN's own resolved type (its result type) |  |
| `$EA9C` |  | `basic` | `FN_PAREA` | the shadow-parameter slots themselves |  |
| `$EA9C` |  | `disk` | `WA_SEG/WA_SEG_ROM` | base of the two hook bodies -- no width |  |
| `$EAA2` |  | `disk` | `WA_SEG_RAM` |  |  |
| `$EAB7` | 1 B | `disk` | `CONOUT_CHAR` | CONOUT: saved char (1 B) |  |
| `$EAB8` | 1 B | `disk` | `PG_SV_A8` | shared: saved $A8 config (1 B) |  |
| `$EAE9` |  | `disk` | `INT_SP_SAVE/INT_STK_TOP` | caller SP saved above the stack top (word) |  |
| `$EAEB` | 2 B | `disk` | `CONIN_BUF` | CONIN: buffer base (word) |  |
| `$EAED` | 1 B | `disk` | `CONIN_MAX` | CONIN: max length ([DE+0]) (1 B) |  |
| `$EAEE` | 1 B | `disk` | `CONIN_COUNT` | CONIN: running fill count (1 B) |  |
| `$EAFF` |  | `basic` | `FN_PAREA_END` |  |  |
| `$EB00` | 1 B | `basic` | `LINEBUF` | repack: ASCII input line from the keyboard (LINEMAX B) (1 B) |  |
| `$EC00` | 576 B | `basic` | `TOKBUF` | repack: crunch buffer, 576 B ($EC00..$EE3F) |  |
| `$EE40` | 27 B | `disk` | `P1_BLIT` | installed blit routine (27 B) -- declared |  |
| `$EE64` | 96 B | `basic` | `FLD_TAB` | field table base ($EE64..$EEC3, 96 bytes) |  |
| `$EEC4` | 2 B | `basic` | `FLD_TABEND/GP_RECNO` | record number, 1-based (2 B) |  |
| `$EEC6` | 2 B | `basic` | `GP_SEC` | file logical-sector index of the record (2) |  |
| `$EEC8` | 2 B | `basic` | `GP_WITHIN` | byte offset of the record within its sector (0/256, 2) (2 B) |  |
| `$EECA` | 2 B | `basic` | `GP_CLUS` | current cluster during the chain walk (2) |  |
| `$EECC` | 2 B | `basic` | `GP_CLIDX` | cluster steps still to walk (2) |  |
| `$EECE` | 1 B | `basic` | `GP_SECINCL` | sector index within the final cluster (1) |  |
| `$EECF` | 2 B | `basic` | `GP_PHYS` | resolved absolute physical sector (2) |  |
| `$EED1` | 2 B | `basic` | `GP_OLDNSEC` | file's old sector count (ceil(size/512), 2) (2 B) |  |
| `$EED3` | 1 B | `basic` | `GP_FLAGS` | bit0 = extend (PUT allocates; GET does not) (1) |  |
| `$EED4` | 1 B | `basic` | `GP_MODE` | 0 = GET (read), 1 = PUT (write) (1) |  |
| `$EED5` | 1 B | `basic` | `GP_CHAN` | the channel number being GET/PUT (1) |  |
| `$EED6` | 32 B | `basic` | `PU_FMT` | copied format string ($EED6..$EEF5, 32 chars) |  |
| `$EEF6` | 1 B | `basic` | `PU_FMTLEN` | live format length (1) |  |
| `$EEF7` | 1 B | `basic` | `PU_POS` | current scan index into PU_FMT (1) |  |
| `$EEF8` | 1 B | `basic` | `PU_W` | current field width (1) |  |
| `$EEF9` | 1 B | `basic` | `PU_TYPE` | field type: 0 num #, 1 str &, 2 str !, 3 str \..\ (1) |  |
| `$EEFA` | 1 B | `basic` | `PU_FLAGS` | bit0 = trailing separator (suppress NL); bit1 = wrapped (1) |  |
| `$EEFB` | 1 B | `basic` | `PU_COMMAS/PU_WP` | pu_fmt_int scratch write pointer (2) -- ALIASED by |  |
| `$EEFC` | 1 B | `basic` | `PU_DEC` | PRINT USING `.`: decimal places requested (D-PUDOT) (1) |  |
| `$EEFD` | 1 B | `basic` | `FMT_SEC` | CALL FORMAT: current sector index being written (1) |  |
| `$EEFE` | 2 B | `basic` | `FMT_DESC` | CALL FORMAT: chosen geometry descriptor pointer (2) |  |
| `$EF00` | 256 B | `basic` | `FLD_DESC` | transient fielded-read descriptor [len][bytes:255] (256 B) |  |
| `$F006` | 2 B | `basic` | `GP_RECLEN` | active channel's record length (word), loaded per calc |  |
| `$F008` | 1 B | `basic` | `OO_RECLEN_CHAN` | OPEN scratch: channel # stashed across the LEN= eval (1) |  |
| `$F009` | 1 B | `basic` | `FILES_HASPAT` | FILES: 1 = a filespec pattern is in DISK_FCB_NAME (1) |  |
| `$F009` | 1 B | `disk` | `FILES_HASPAT` | FILES: 1 = a filespec pattern is in DISK_FCB_NAME (1) |  |
| `$F00A` | 6 B | `basic` | `CAS_WANT` | requested 6-char tape name, space-padded (6) |  |
| `$F010` | 1 B | `basic` | `CAS_WANT_ON` | 1 = match CAS_WANT; 0 = load next file (bare form) (1) |  |
| `$F011` | 6 B | `basic` | `CAS_HDRNAME` | 6-char name read from the current tape header (6) |  |
| `$F017` | 1 B | `basic` | `CAS_HDRID` | file-type id byte read from the current header (1) |  |
| `$F018` | 1 B | `basic` | `CAS_VERIFY` | 1 = CLOAD? compare-mode (no store) (1) |  |
| `$F019` | 1 B | `basic` | `CAS_VMIS` | sticky: 1 = a verify mismatch was seen (1) |  |
| `$F01A` | 1 B | `basic` | `FACTYP` | 2=int / 4=single / 8=double (1) |  |
| `$F01A` | 1 B | `disk` | `FACTYP` | 2=int / 4=single / 8=double (1) |  |
| `$F01B` | 1 B | `basic` | `TKOVF` | tokeniser reject code, 0 = ok (1 B) |  |
| `$F01C` | 2 B | `basic` | `DB_SP` | the render's SP to abort to (2 B; FAC's old cell) |  |
| `$F01E` | 2 B | `basic` | `DT_TOK` | detok: the current token's start in the line (2 B) |  |
| `$F020` | 2 B | `basic` | `DT_TOKN` | detok: bytes the current token has emitted (2 B) |  |
| `$F022` | 2 B | `basic` | `DB_RESPTR` | resume: the token to restart at (2 B) |  |
| `$F024` | 2 B | `basic` | `PLY_XSP` | PLAY X: saved SP at pt_voice's call (2) |  |
| `$F026` | 1 B | `basic` | `PRMWANT` | D-OKSTORE: nonzero = print the prompt (1) |  |
| `$F027` | 1 B | `basic` | `STOPHOLD` | D-STOPTAP: frames Ctrl-STOP has been held (1) |  |
| `$F03C` | 1 B | `basic` | `TKDIG` | tokeniser/formatter: significant-digit array, (1 B) |  |
| `$F054` | 1 B | `basic` | `TKPOS` | running digit-position counter (1) |  |
| `$F055` | 1 B | `basic` | `TKINTLEN` | integer-part digit count = P (1) |  |
| `$F056` | 1 B | `basic` | `TKHAVESIG` | 1 once the first nonzero digit is seen (1) |  |
| `$F057` | 1 B | `basic` | `TKNZPOS` | position of the first nonzero digit = f (1) |  |
| `$F058` | 1 B | `basic` | `TKDCOUNT` | classification digit count = D, saturating (1) |  |
| `$F059` | 1 B | `basic` | `TKSTORED` | digits actually written to TKDIG, capped 24 (1) |  |
| `$F05A` | 1 B | `basic` | `TKFLAGS` | bit0=dot bit1=exp bit2=expD bit3=! bit4=# bit5=% (1) |  |
| `$F05B` | 2 B | `basic` | `TKEXP` | signed explicit exponent, saturated +-9999 (2) |  |
| `$F05D` | 1 B | `basic` | `TKEXPD` | 1 = the exponent marker being parsed is D/d (1) |  |
| `$F05E` | 1 B | `basic` | `TKEXPSIGN` | 1 = the exponent being parsed is negative (1) |  |
| `$F05F` | 1 B | `basic` | `TKPC` | target precision digit count: 6 / 14 (1) |  |
| `$F060` | 2 B | `basic` | `TKDEXP` | signed dec_exp, pre-/post-round (2) |  |
| `$F062` | 1 B | `basic` | `TKLEAD` | computed lead byte (sign+excess-64 exponent) (1) |  |
| `$F063` | 1 B | `basic` | `FOSIGN` | 0 / $80 = the value's sign bit (1) |  |
| `$F064` |  | `basic` | `FOSIGCOUNT/TKVALEND` | significant digit count = s, trailing zeros |  |
| `$F065` | 1 B | `basic` | `FOMBYTES` | mantissa byte count: 3 (single) / 7 (double) (1) |  |
| `$F067` | 2 B | `basic` | `TKSRCSAVE` | (2) |  |
| `$F069` | 1 B | `basic` | `FPERR` | runtime numeric-error flag: 0 none / 1 overflow / (1 B) |  |
| `$F06A` | 18 B | `basic` | `ARGA` | operand A / working result, FPNUM record (18) |  |
| `$F06A` | 18 B | `disk` | `ARGA` | operand A / working result, FPNUM record (18) |  |
| `$F07C` | 18 B | `basic` | `ARGB` | operand B, FPNUM record (18) |  |
| `$F08E` |  | `basic` | `MULPROD/RND_ACCLE` | fp_mul: 28-digit product (14x14), MSD first (28) |  |
| `$F09C` | 1 B | `basic` | `RND_I` | multiply-add loop: S/acc digit index i |  |
| `$F09D` | 1 B | `basic` | `RND_J` | multiply-add loop: A's digit index j |  |
| `$F09E` | 1 B | `basic` | `RND_IJ` | multiply-add loop: i+j, the target |  |
| `$F09F` | 1 B | `basic` | `RND_AJ` | multiply-add loop: A_LE[j], stashed |  |
| `$F0A0` | 1 B | `basic` | `RND_CARRY` | multiply-add loop: running BCD carry, |  |
| `$F0A1` | 1 B | `basic` | `RND_K` | output normalisation: count of leading |  |
| `$F0AA` | 15 B | `basic` | `DIVPAD` | fp_div: divisor zero-padded to 15 digits (15) |  |
| `$F0B9` | 15 B | `basic` | `DIVREM` | fp_div: running remainder, 15 digits (15) |  |
| `$F0C8` | 18 B | `basic` | `CVT` | fac_to_int_strict/addr + flt_to_int16 (float.asm) |  |
| `$F0DA` | 1 B | `basic` | `LHS_FACTYP` | ev_e/ev_t binary-op sites: the LHS operand's FACTYP, |  |
| `$F0DB` | 8 B | `basic` | `LHS_FAC` | ...and the LHS operand's raw FAC bytes (8) |  |
| `$F0E3` | 1 B | `basic` | `FP_SHIFTAMT` | dig15_shr/dig15_shl: shift-amount parameter (1) |  |
| `$F0E4` | 2 B | `basic` | `FP_LHSVAL` | combine_*: the LHS operand's plain int16 value, |  |
| `$F0E6` | 2 B | `basic` | `FP_TMP_B` | combine_*: the RHS operand's plain int16 value, |  |
| `$F0E8` | 1 B | `basic` | `FP_RSIGN` | signed_div_de_bc/signed_mod_de_bc: result sign (1) |  |
| `$F0E9` |  | `basic` | `KEYARG/WIDIG` | widen_int_to: binary->BCD digit scratch, up to |  |
| `$F0EE` | 1 B | `basic` | `MUL_I` | fp_mul: outer-loop digit index i, 13 downto 0; |  |
| `$F0EF` | 1 B | `basic` | `MUL_ADIG` | fp_mul: A[i], the current outer-loop digit (1) |  |
| `$F0F0` | 1 B | `basic` | `MUL_CARRY` | fp_mul: running carry within one outer pass; |  |
| `$F0F1` | 2 B | `basic` | `MUL_PP` | fp_mul: MULPROD write-cursor for the inner loop (2) |  |
| `$F0F3` | 2 B | `basic` | `MULCAND` | mul16x16_32: multiplicand operand (2) |  |
| `$F0F5` | 2 B | `basic` | `MULTPLR` | mul16x16_32: multiplier operand, shifted in place (2) |  |
| `$F0F7` | 4 B | `basic` | `MUL32` | mul16x16_32: 32-bit unsigned product, LE |  |
| `$F0FB` | 2 B | `basic` | `WSRC` | widen_fac_to/widen_lhsframe_to (shared unpack |  |
| `$F0FD` | 2 B | `basic` | `WSRC_TYP` | ...and the address of its type byte, FACTYP |  |
| `$F0FF` | 1 B | `basic` | `FP_OPMODE` | combine_add/combine_sub shared body: 0=add, |  |
| `$F100` |  | `basic` | `CVT_MODE` | domain_convert_core: 0=strict int16 domain, |  |
| `$F101` | 2 B | `basic` | `PLF_RA` | pop_lhs_and_probe: scratch home for its own |  |
| `$F103` | 2 B | `basic` | `PLF_RA2` | ...and for its DIRECT caller's (combine_add/ (2 B) |  |
| `$F105` | 1 B | `basic` | `SUB_PING` | PING page tag: $C0 (page 0) / $C1 (page 1) (1 B) |  |
| `$F106` | 1 B | `basic` | `SUBSLOT` | slot id of zerobas-sub (bit7 exp \| 3-2 \| 3), 1 (1 B) |  |
| `$F107` | 1 B | `basic` | `SUBSLOT_OK` | 1 = a CD sub-ROM was found and recorded, else 0 (1 B) |  |
| `$F108` | 2 B | `basic` | `DB_CUR` | wave-3 detok: the DETOKBUF write cursor, held across (2 B) |  |
| `$F10A` | 64 B | `basic` | `SUB_INT_RAM` | the copied trampoline stub (<= 64 B; executes from RAM) |  |
| `$F14A` | 1 B | `basic` | `INT_MAIN_PRIM` | page-0 primary field of the MAIN (BIOS) slot (=0) (1 B) |  |
| `$F14B` | 1 B | `basic` | `INT_SUB_PRIM` | page-0 primary field of the sub-ROM slot (=3, slot 3) (1 B) |  |
| `$F14C` | 1 B | `basic` | `INT_SUB_SUBSL` | page-0 subslot field of the sub-ROM slot (=2, i.e. 3-2) (1 B) |  |
| `$F14D` | 1 B | `basic` | `SUB_INT_DELTA` | self-test tenant result: JIFFY ticks observed under EI (1) |  |
| `$F14E` | 1 B | `basic` | `VARTYPE` | var_name_key: the RESOLVED type (2/4/8) of the |  |
| `$F14F` | 1 B | `basic` | `VS_TARGET_TYPE` | var_store_fac/var_alloc_or_find (vars.asm): |  |
| `$F150` | 2 B | `basic` | `VS_INT_VAL` | var_store_fac (vars.asm): the coerced int16 value |  |
| `$F152` | 1 B | `basic` | `LHS_VARTYPE` | ex_let (interp.asm): the LHS variable's resolved |  |
| `$F16D` | 1 B | `basic` | `MC_TYPE` | evmc_sub1 (expr.asm): the operand's FACTYP (4/8), |  |
| `$F16E` |  | `basic` | `HORNER_G/MATH_T/RND_LE/SQRT_X` | the efficiency-normalized argument x' (constant |  |
| `$F180` |  | `basic` | `MATH_A/RND_STATE/SQRT_Y` | fp_atan's persistent reduced-argument "a" -- |  |
| `$F192` | 2 B | `basic` | `MATH_N/MATH_SIGN/SQRT_K` | signed net count of the x'/y<->x/y-under-100^k |  |
| `$F193` | 1 B | `basic` | `MATH_RECIP/SQRT_ITER` | Heron loop iteration counter, 1-based (the stop- |  |
| `$F194` | 1 B | `basic` | `MATH_BREAK/MATH_J/SQRT_POW10` | final decision-loop (§10.4 step 4, REVISED |  |
| `$F195` | 18 B | `disk` | `DRVA_DPB` | drive-A DPB base (id byte + 18-byte DPB, §8.30) |  |
| `$F1AA` |  | `disk` | `W50A9_RET_DE` | DE (= IX) on return: disk work-area pointer |  |
| `$F1C9` |  | `disk` | `RES_PRINT` | resident $-string print routine the kernel CALLs (§8.28) |  |
| `$F200` |  | `basic` | `FN_STK_FLOOR` |  |  |
| `$F23D` | 2 B | `disk` | `DOS_DTAPTR` | disk work-area current-DTA cache (word, LE; M19) |  |
| `$F242` | 1 B | `disk` | `W50A9_WRKB` | the one work-area cell $50A9 clears (semantic: black-box) (1 B) |  |
| `$F247` | 1 B | `disk` | `CURDRV_CELL` | current-drive index ($00=A:); read by $50C4 (M18) (1 B) |  |
| `$F24E` |  | `disk` | `RES_STUBS` | no-op segment-hook stub table base (§8.29) |  |
| `$F2B8` |  | `disk` | `RES_STUBS_END` | one past the last stub ($F2B7); $F2B8+ = kernel data (§8.61) |  |
| `$F340` | 1 B | `disk` | `DOS_F340` | disk work-area flag the kernel reads at init (§8.33); $00 = ok (1 B) |  |
| `$F341` | 4 B | `disk` | `RAMAD0` | RAM-slot id per page ($F341-$F344), MSX2 TH work area |  |
| `$F347` | 1 B | `disk` | `DRVCNT` | DRVTBL-1: logical-drive count ($02); read by $50D5 (M17) (1 B) |  |
| `$F348` | 16 B | `disk` | `DRVTBL` | MSX-DOS-1 disk-driver table, $F348..$F357 (§8.22; |  |
| `$F351` | 2 B | `basic` | `DSKBUF_PTR` | word -> the DSKI$/DSKO$ sector buffer (2) |  |
| `$F351` | 2 B | `disk` | `DSKBUF_PTR` | word -> the DSKI$/DSKO$ sector buffer; the disk ROM writes it |  |
| `$F359` |  | `disk` | `W50A9_RET_HL` | HL on return: disk work-area pointer (DRVTBL+$11 region) |  |
| `$F365` |  | `disk` | `F365_STUB` | fixed disk-work-area slot-read stub (IN A,($A8);RET; M15 §7.1) |  |
| `$F368` | 21 B | `disk` | `WA_JMPTAB` | disk-work-area resident jump table ($F368-$F37C, 7 slots) |  |
| `$F37D` | 2 B | `disk` | `SYSTEM` | SYSTEM sysvar: BDOS entry-point word |  |

## The MSX standard work area (`$F380` and above)

🔴 **THIS PROJECT USES THESE CELLS; IT DOES NOT OWN THEM.**
Their addresses and meanings are the MSX standard's (and
C-BIOS's), not this tree's, so the *purpose* column quotes
our comment about why WE touch the cell — which is not the
same thing as the standard's definition of it. Look the cell
up in the MSX2 Technical Handbook before relying on a row.

⚠️ **AND THEY ARE DELIBERATELY OUTSIDE THE ARITHMETIC.** The
unattributed-run walk and the width ratchet both stop at
`$F380`: a gap here would be bytes the BIOS owns and
we merely never named, and demanding our comments re-declare
extents the standard already fixes would be noise, not rigour.

| address | size | component | name(s) | purpose | inside |
|---|---|---|---|---|---|
| `$F380` |  | `basic` | `CLR_HIMEM_TOP` | 62336: highest address CLEAR accepts |  |
| `$F39A` | 20 B | `basic` | `USRTAB` | 20 B total, 10 USR jump vectors of 2 B each. |  |
| `$F3AE` |  | `basic` | `LINL40` | text columns for SCREEN 0 (WIDTH default) |  |
| `$F3AF` |  | `basic` | `LINL32` | text columns for SCREEN 1 (WIDTH default) |  |
| `$F3B0` |  | `basic` | `LINLEN` | current line length (active width) |  |
| `$F3B0` |  | `disk` | `LINLEN` | current line length = the active width (ditto) |  |
| `$F3B1` |  | `basic` | `CRTCNT` | number of text rows on the screen (MSX work area; D-SCREDIT) |  |
| `$F3B3` | 2 B | `basic` | `BASETAB/TXTNAM` | BASE(0..19): 20 LE words, 4 groups of 5 (name, colour, |  |
| `$F3B7` | 2 B | `basic` | `TXTCGP` | SCREEN 0 pattern generator base (2 B) |  |
| `$F3BD` | 2 B | `basic` | `T32NAM` | SCREEN 1 name table base (2 B) |  |
| `$F3C1` | 2 B | `basic` | `T32CGP` | SCREEN 1 pattern generator base (2 B) |  |
| `$F3DB` | 1 B | `basic` | `CLIKSW` | keyboard click: 0 = off, nonzero = on (1) |  |
| `$F3DC` |  | `basic` | `CSRY` | cursor row (1-based); the CSRLIN pseudo-variable reads it |  |
| `$F3DD` |  | `basic` | `CSRX` | cursor column (1-based); C-BIOS sysvars / PRINT comma zones |  |
| `$F3DD` |  | `disk` | `CSRX` | cursor column, 1-based (MSX standard work area; |  |
| `$F3DE` |  | `basic` | `CNSDFG` | function-key display flag: $FF = shown, 0 = hidden |  |
| `$F3DF` | 8 B | `basic` | `RG0SAV` | VDP register 0..7 mirrors ($F3DF..$F3E6); RG1SAV = +1 |  |
| `$F3E0` | 2 B | `basic` | `RG1SAV` | VDP register 1 mirror; bits 1..0 = SCREEN's sprite-size |  |
| `$F3E7` |  | `basic` | `STATFL` | VDP status-register copy kept by the frame ISR |  |
| `$F3E9` |  | `basic` | `FORCLR` | foreground colour |  |
| `$F3EA` |  | `basic` | `BAKCLR` | background colour |  |
| `$F3EB` |  | `basic` | `BDRCLR` | border colour |  |
| `$F3F2` | 1 B | `basic` | `ATRBYT` | current graphics attribute / plot colour (1) |  |
| `$F3FC` | 2 B | `basic` | `CS120_LOW` | 1200-baud reference low-signal length word |  |
| `$F401` | 2 B | `basic` | `CS240_LOW` | 2400-baud reference low-signal length word |  |
| `$F406` | 2 B | `basic` | `ACT_LOW` | active low-signal length word (the live baud) |  |
| `$F414` | 1 B | `basic` | `ERRFLG` | 1 B: last error's MSX ERR code (0 = none yet). |  |
| `$F41C` |  | `basic` | `CURLIN` | D-CURLIN (Joost, 2026-09-24): the PUBLISHED current |  |
| `$F661` | 1 B | `basic` | `TTYPOS` | BASIC's 0-based print column (D-ADDR29 N set) (1) |  |
| `$F663` | 1 B | `basic` | `VALTYP_PUB` | PUBLISHED value type: 2 int / 4 single / 8 double (1) |  |
| `$F676` |  | `basic` | `TXTTAB` | sysvar: pointer to the BASIC text base |  |
| `$F678` | 2 B | `basic` | `TEMPPT` | PUBLISHED cursor: next free slot (2 B) |  |
| `$F67A` |  | `basic` | `TEMPPOOL` | TEMPST: low (deepest-push) address |  |
| `$F698` |  | `basic` | `TEMPBASE` | $F698: high boundary = the empty- |  |
| `$F6B3` | 2 B | `basic` | `ERRLIN` | 2 B: last error's line number, or 65535 if it |  |
| `$F6B5` | 2 B | `basic` | `DOT` | 2 B: the line `.` names. Cold value 0 (init). |  |
| `$F6B9` | 2 B | `basic` | `ONELIN` | 2 B: ON ERROR handler line's LINK address (the |  |
| `$F6BB` | 1 B | `basic` | `ONEFLG` | 1 B: $FF = currently inside a handler (no RESUME |  |
| `$F6C2` | 2 B | `basic` | `VARTAB` | PUBLISHED: variable-table base = (PRGEND)+2 (2 B) |  |
| `$F6C4` | 2 B | `basic` | `ARYTAB` | PUBLISHED: scalar-region end == array base (2 B) |  |
| `$F6C6` | 2 B | `basic` | `STREND` | PUBLISHED: array-region end = ARYEND (2 B) |  |
| `$F6CA` | 26 B | `basic` | `DEFTBL` | per-letter default-type map, A..Z (26) -- |  |
| `$F7C5` |  | `basic` | `FBUFFR` | published: number-conversion buffer (43 B) |  |
| `$F7C6` |  | `basic` | `FOUTBUF/HORNER_ACC/MATH_R/SQRT_R` | final-correction high-precision residual scratch |  |
| `$F7D8` | 1 B | `basic` | `HORNER_CNT` | fp_poly_horner's own remaining-term loop |  |
| `$F7D9` | 2 B | `basic` | `HORNER_PTR` | fp_poly_horner's own advancing coeff- |  |
| `$F7F6` | 8 B | `basic` | `DAC/FAC` | float accumulator = DAC: value bytes as tokenised (8) |  |
| `$F7F6` | 8 B | `disk` | `FAC` | float accumulator = DAC: value bytes as tokenised (8) |  |
| `$F857` |  | `basic` | `RNDX` | PUBLISHED 8 B seed; byte 0 reads 00 (1) |  |
| `$F858` | 7 B | `basic` | `RND_SEED` | packed BCD, MSD-first, 7 bytes ($F858..$F85E) |  |
| `$F87F` |  | `basic` | `FNKSTR` | measured base (D-KEYSTR scout) |  |
| `$F922` |  | `basic` | `NAMBAS` | name-table base of the current text mode (MSX work area; D-SCREDIT) |  |
| `$F92A` | 2 B | `basic` | `CLOC` | computed VRAM byte address of the current pixel (2) |  |
| `$F92C` | 1 B | `basic` | `CMASK` | MSB-first bit mask of the current pixel (1) |  |
| `$F959` | 6 B | `basic` | `QUETAB` | 4 x 6-byte ring descriptors (3 voice + 1 RS232) |  |
| `$F971` |  | `basic` | `PLY_LASTDUR` | QUEBAK+0 (2): saved write pointer across pt_length |  |
| `$F973` |  | `basic` | `PLY_BUFEND` | QUEBAK+2 (2): current voice buffer end (overflow guard) |  |
| `$F975` | 128 B | `basic` | `VOICAQ` | voice-0 packet buffer (128 B) |  |
| `$F9F5` | 128 B | `basic` | `VOICBQ` | voice-1 packet buffer (128 B) |  |
| `$FA75` | 128 B | `basic` | `VOICCQ` | voice-2 packet buffer (128 B) |  |
| `$FAF8` |  | `basic` | `EXBRSA` |  |  |
| `$FB38` |  | `basic` | `VOICEN` | voice currently being parsed (0..2) |  |
| `$FB3C` |  | `basic` | `MCLPTR` | address of the MML string being parsed (source cursor) |  |
| `$FB3E` |  | `basic` | `QUEUEN` | active queue # scratch (0..2) |  |
| `$FB3F` |  | `basic` | `MUSICF` | bitmask: bit v = voice v queue active (SET LAST) |  |
| `$FB40` |  | `basic` | `PLYCNT` | count of PLAY statements parsed, not yet executed |  |
| `$FB41` | 37 B | `basic` | `VCBA` | Voice Control Block, voice 0 (37 B) |  |
| `$FB66` |  | `basic` | `VCBB` | Voice Control Block, voice 1 |  |
| `$FB8B` |  | `basic` | `VCBC` | Voice Control Block, voice 2 |  |
| `$FBB2` |  | `basic` | `LINTTB` | per-row continuation table, one byte per row: 0 = the row |  |
| `$FBCD` | 1 B | `basic` | `FNKSWI` | function-key set shown: 1 = F1..F5 (D-ADDR29 N set) (1) |  |
| `$FBE5` | 11 B | `basic` | `NEWKEY` | key matrix snapshot, 11 B (row 6 bit 0 = SHIFT) |  |
| `$FC4A` | 2 B | `basic` | `HIMEM` | highest RAM address BASIC may use (2 bytes) |  |
| `$FC9E` |  | `basic` | `JIFFY` | MSX software clock, bumped by the timer ISR (MSX2 TH work area) |  |
| `$FCA8` | 1 B | `basic` | `INSFLG` | PUBLISHED insert-mode flag: $FF on, 0 off (D-INSMODE) (1 B) |  |
| `$FCA9` |  | `basic` | `CSRSW` | cursor display: 0 = off, 1 = on |  |
| `$FCAF` |  | `basic` | `SCRMOD` | current screen mode (0..3) |  |
| `$FCB3` | 2 B | `basic` | `GXPOS` | pending plot X (int16 LE) |  |
| `$FCB5` | 2 B | `basic` | `GYPOS` | pending plot Y (int16 LE) |  |
| `$FCB7` | 2 B | `basic` | `GRPACX` | last-referenced point X (int16 LE) |  |
| `$FCB9` | 2 B | `basic` | `GRPACY` | last-referenced point Y (int16 LE) |  |
| `$FCC1` | 1 B | `basic` | `EXPTBL` | expanded-slot flags, 1 byte/primary, bit7 = expanded |  |
| `$FCC1` | 1 B | `disk` | `EXPTBL` | expanded-slot flags, 1 byte/primary, bit 7 = expanded |  |
| `$FCC5` |  | `disk` | `SLTTBL` | SLTTBL base: per-primary mirror of the secondary-slot regs |  |
| `$FCC8` |  | `disk` | `SLTTBL3` | SLTTBL[3]: RAM mirror of slot-3 secondary-slot register (=SLTTBL+3) |  |
| `$FD9F` | 5 B | `basic` | `H_TIMI` | timer-interrupt hook, 5-byte inter-slot call area |  |
| `$FDEF` |  | `basic` | `H_DSKO` | DSKO$ handler -- 🔴 WAS $FDF4 AND THAT WAS WRONG |  |
| `$FDEF` |  | `disk` | `H_DSKO` | DSKO$ (D-DSKIO) -- 🔴 WAS $FDF4 (D-DSKOHOOK |  |
| `$FDF9` |  | `basic` | `H_NAME` | NAME handler (channel verbs, D-CHANHOOK) |  |
| `$FDF9` |  | `disk` | `H_NAME` | NAME (channel verbs, D-CHANHOOK) |  |
| `$FDFE` |  | `basic` | `H_KILL` | KILL handler |  |
| `$FDFE` |  | `disk` | `H_KILL` | KILL |  |
| `$FE08` |  | `basic` | `H_COPY` | COPY handler (D-COPY; the standard slot) |  |
| `$FE08` |  | `disk` | `H_COPY` | COPY (D-COPY) |  |
| `$FE12` |  | `basic` | `H_DSKF` | DSKF handler |  |
| `$FE12` |  | `disk` | `H_DSKF` | DSKF |  |
| `$FE17` |  | `basic` | `H_DSKI` | DSKI$ handler (D-DSKIO) |  |
| `$FE17` |  | `disk` | `H_DSKI` | DSKI$ (D-DSKIO) |  |
| `$FE21` |  | `basic` | `H_LSET` | LSET handler |  |
| `$FE21` |  | `disk` | `H_LSET` | LSET |  |
| `$FE26` |  | `basic` | `H_RSET` | RSET handler |  |
| `$FE26` |  | `disk` | `H_RSET` | RSET |  |
| `$FE2B` |  | `basic` | `H_FIELD` | FIELD handler |  |
| `$FE2B` |  | `disk` | `H_FIELD` | FIELD |  |
| `$FE30` |  | `basic` | `H_MKI` | MKI$ handler (disk/kernel.asm hk_present) |  |
| `$FE30` |  | `disk` | `H_MKI` | MKI$ -- the first verb routed this way (D-MKHOOK) |  |
| `$FE35` |  | `basic` | `H_MKS` | MKS$ handler |  |
| `$FE35` |  | `disk` | `H_MKS` | MKS$ |  |
| `$FE3A` |  | `basic` | `H_MKD` | MKD$ handler |  |
| `$FE3A` |  | `disk` | `H_MKD` | MKD$ |  |
| `$FE3F` |  | `basic` | `H_CVI` | CVI handler |  |
| `$FE3F` |  | `disk` | `H_CVI` | CVI |  |
| `$FE44` |  | `basic` | `H_CVS` | CVS handler |  |
| `$FE44` |  | `disk` | `H_CVS` | CVS |  |
| `$FE49` |  | `basic` | `H_CVD` | CVD handler |  |
| `$FE49` |  | `disk` | `H_CVD` | CVD |  |
| `$FE5D` |  | `basic` | `H_FOPEN` |  |  |
| `$FE5D` |  | `disk` | `H_FOPEN` |  |  |
| `$FE7B` |  | `basic` | `H_FILE` |  |  |
| `$FE7B` |  | `disk` | `H_FILE` |  |  |
| `$FEE4` |  | `basic` | `H_OUTD` | published hook OUTDO calls first (MSX2 TH hook table) |  |
| `$FEFD` |  | `basic` | `H_ERRP` | error-print hook (D-DISKERR): the errmsg tenant offers a code it |  |
| `$FEFD` |  | `disk` | `H_ERRP` | error-print hook (D-DISKERR): this ROM prints ERR 68..70 |  |
| `$FF48` |  | `basic` | `H_CHRG` | published hook CHRGTR calls first (MSX2 TH hook table) |  |
| `$FFA7` |  | `disk` | `HPHYD` | PHYDIO hook (5 RAM bytes, default C9) |  |
| `$FFCF` | 5 B | `basic` | `H_ZKEY` | fn-key delivery hook, 5-byte JP vector (zkey_install) |  |
| `$FFF9` |  | `basic` | `LINENO_CEIL` |  |  |

