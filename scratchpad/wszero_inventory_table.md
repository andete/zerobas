| addr | width | names | class | home | group | users (file:refs) | job (own comment, truncated) |
|---|---|---|---|---|---|---|---|
| $E9A1 | 2 | ISRCH_A | D | PUB | G1 INSTR/MID$ scratch + probe byte | strheap.asm:3, sysvars.inc:1 | resolved A-operand body base (2 B) |
| $E9A3 | 2 | ISRCH_B | D | PUB | G1 INSTR/MID$ scratch + probe byte | strheap.asm:3, sysvars.inc:1 | $E9A3: resolved B-operand body base (2 B) TMISMATCH ($E3E5, 1 B) STOOD HERE -- the string-comparison D-2 marke |
| $E9A5 | 1 | GFX_BAD/STRENG_SPARE | D | PUB | G1 INSTR/MID$ scratch + probe byte | graphics.asm:1, sysvars.inc:1 | VRAM read-back mismatch count (1) |
| $E9A6 | 2 | MIDS_DEST | D | PUB | G1 INSTR/MID$ scratch + probe byte | field.asm:1, str-engine.asm:1, vars.asm:1, sysvars.inc:1 | MID$ statement: the target descriptor's address (2 B) Console INPUT (repack build only): the LINEBUF read curs |
| $E9A9 | 1 | GFX_POVF | D | PUB | G2 PAINT/CIRCLE/sprite scratch union | graphics.asm:4, graphics.asm:1 | 1 = the stack overflowed; resident raises ERR 7 (1) |
| $E9AA | 1 | GFX_PTESTX | D | PUB | G2 PAINT/CIRCLE/sprite scratch union | graphics.asm:9 | gfx_paint_inside/gfx_paint_plot: pixel-under-test X (1) |
| $E9AB | 1 | GFX_PTESTY | D | PUB | G2 PAINT/CIRCLE/sprite scratch union | graphics.asm:8 | ...Y (1) |
| $E9AC | 1 | GFX_PFY | D | PUB | G2 PAINT/CIRCLE/sprite scratch union | graphics.asm:11 | gfx_paint_flood/_process: current span's row (1) |
| $E9AD | 1 | GFX_PXL | D | PUB | G2 PAINT/CIRCLE/sprite scratch union | graphics.asm:10 | ...current span's left column (1) |
| $E9AE | 1 | GFX_PXR | D | PUB | G2 PAINT/CIRCLE/sprite scratch union | graphics.asm:10 | ...current span's right column (1) |
| $E9AF | 1 | GFX_PSCX | D | PUB | G2 PAINT/CIRCLE/sprite scratch union | graphics.asm:17 | gfx_paint_process/_scan_row: scan cursor column (1) |
| $E9B0 | 1 | GFX_PSCY | D | PUB | G2 PAINT/CIRCLE/sprite scratch union | graphics.asm:4 | gfx_paint_scan_row: the neighbour row being scanned (1) |
| $E9B1 | 1 | GFX_PSPA | D | PUB | G2 PAINT/CIRCLE/sprite scratch union | graphics.asm:2 | gfx_paint_scan_row: pending sub-span's start column (1) |
| $E9B2 | 44 | GFX_CS_M1/GFX_PSTK/GFX_VBUF | D | PUB | G2 PAINT/CIRCLE/sprite scratch union | graphics.asm:17, sysvars.inc:7, graphics.asm:1 | $E9B2: D-ARCMASK: 2*M*M during the M floor-correction (was cross_ge0's mag1) (4) |
| $E9B6 | 4 | GFX_CS_M2 | D | PUB | G2 PAINT/CIRCLE/sprite scratch union | graphics.asm:3 | $E9B6: r*r for the same compare (4) CONTIGUOUS with M1 -- gcx_zlp tests both as one 8-byte run. (The width mov |
| $E9BA | 2 | GFX_PSP | D | PUB | G2 PAINT/CIRCLE/sprite scratch union | graphics.asm:5 | the span stack's top (lowest used byte) (2) |
| $E9BC | 2 | GFX_PBASE | D | PUB | G2 PAINT/CIRCLE/sprite scratch union | graphics.asm:2 | its empty position = SP - GFX_PAINT_MARGIN (2) |
| $E9BE | 2 | GFX_PFLOOR | D | PUB | G2 PAINT/CIRCLE/sprite scratch union | graphics.asm:2 | the lowest byte it may use = ARYEND + 2 (2) D-PAINTSP: how far below the SP at gfx_pstk_reset the entries star |
| $E9D2 | 2 | GFX_SN | D | PUB | G2 PAINT/CIRCLE/sprite scratch union | graphics.asm:2, graphics.asm:2, sysvars.inc:1 | $E9D2: SPRITE$ entry index / PUT SPRITE plane (2) |
| $E9D4 | 1 | GFX_VLEN | D | PUB | G2 PAINT/CIRCLE/sprite scratch union | graphics.asm:2, sysvars.inc:1, graphics.asm:1 | $E9D4: the entry size the tenant read back (1) |
| $E9D5 | 2 | GFX_SDESC | D | PUB | G2 PAINT/CIRCLE/sprite scratch union | graphics.asm:1, sysvars.inc:1, graphics.asm:1 | $E9D5: SPRITE$(n)= RHS string descriptor ([len][ptr]); the tenant dereferences it (2) |
| $E9D7 | 2 | GFX_SC | D | PUB | G2 PAINT/CIRCLE/sprite scratch union | graphics.asm:1, sysvars.inc:1, graphics.asm:1 | $E9D7: PUT SPRITE colour (2). x/y need no cells -- (2 B) they ride the arc's pinned GXPOS/GYPOS pair, which PU |
| $E9D9 | 2 | GFX_SPATN | D | PUB | G2 PAINT/CIRCLE/sprite scratch union | graphics.asm:1, sysvars.inc:1, graphics.asm:1 | $E9D9: ...pattern number (2) |
| $E9DB | 1 | GFX_SSIZE | D | PUB | G2 PAINT/CIRCLE/sprite scratch union | graphics.asm:2, sysvars.inc:1, graphics.asm:1 | $E9DB: SCREEN's sprite-size argument while a mode set is in flight (RG1SAV bits 1..0 hold it after) (1) |
| $E9DC | 1 | GFX_SARGN | D | PUB | G2 PAINT/CIRCLE/sprite scratch union | screen.asm:3, graphics.asm:1, sysvars.inc:1 | $E9DC: how many extra SCREEN arguments have been seen -- only the FIRST is the sprite size (1) |
| $E9DD | 1 | GFX_SFLAGS | D | PUB | G2 PAINT/CIRCLE/sprite scratch union | graphics.asm:6, graphics.asm:3, sysvars.inc:1 | $E9DD: which arguments were GIVEN -- (1 B) bit0 = coordinates, bit1 = colour, bit2 = pattern; an omitted one k |
| $E9DE | 2 | GFX_DPTR | D | PUB | G3a DRAW parser state | graphics.asm:9, graphics.asm:6, circleparse.asm:4, sysvars.inc:1 | $E9DE: parse cursor in the current frame (2) |
| $E9E0 | 2 | GFX_DEND | D | PUB | G3a DRAW parser state | graphics.asm:4, sysvars.inc:1 | $E9E0: one past the current frame's last byte (2) |
| $E9E2 | 1 | GFX_DFTOP | D | PUB | G3a DRAW parser state | graphics.asm:6, sysvars.inc:1 | $E9E2: X-frame stack depth (1) |
| $E9E3 | 32 | GFX_DFSTK | D | PUB | G3a DRAW parser state | graphics.asm:2, sysvars.inc:1 | $E9E3: saved [ptr][end] per outer frame -- 32 B total, 4 B each * GFX_DFCAP. 🔴 THE TOTAL COMES FIRST ON PURPOS |
| $EA03 | 2 | GFX_DCMD | D | PUB | G3a DRAW parser state | graphics.asm:2, sysvars.inc:1 | $EA03: current command's start cursor, the rewind point for a substitution (2) |
| $EA05 | 1 | GFX_DSUBN | D | PUB | G3a DRAW parser state | graphics.asm:6, sysvars.inc:1 | $EA05: substitutions RESOLVED for this command (1) |
| $EA06 | 1 | GFX_DSUBI | D | PUB | G3a DRAW parser state | graphics.asm:3, sysvars.inc:1 | $EA06: substitutions SEEN so far this re-parse (1) |
| $EA07 | 4 | GFX_DSUB | D | PUB | G3a DRAW parser state | graphics.asm:2, sysvars.inc:1 | $EA07: the resolved values, 2 slots (M takes two) (4) |
| $EA0B | 1 | GFX_DSUBLEN | D | PUB | G3a DRAW parser state | graphics.asm:2, sysvars.inc:1 | $EA0B: slot 0's string length (X only) (1) |
| $EA0C | 1 | GFX_DREQ | D | PUB | G3a DRAW parser state | circleparse.asm:7, graphics.asm:4, graphics.asm:2, sysvars.inc:1 | $EA0C: tenant->resident: 0 = done, 1 = resolve an int, 2 = resolve a string (1) |
| $EA0D | 1 | GFX_DRESUME | D | PUB | G3a DRAW parser state | graphics.asm:4, sysvars.inc:1, circleparse.asm:1, graphics.asm:1 | $EA0D: resident->tenant: 1 = resuming (1) |
| $EA0E | 2 | GFX_DVAL | D | PUB | G3a DRAW parser state | graphics.asm:3, graphics.asm:3, circleparse.asm:2, sysvars.inc:1 | $EA0E: the resolved int16, or a string body ptr (2) |
| $EA10 | 1 | GFX_DVLEN | D | PUB | G3a DRAW parser state | graphics.asm:3, graphics.asm:1, sysvars.inc:1 | $EA10: that string's length (1) |
| $EA11 | 24 | GFX_DEXP | D | PUB | G3a DRAW parser state | graphics.asm:2, graphics.asm:2, sysvars.inc:1 | $EA11: NUL-terminated copy of the text between `=`/`X` and its `;`, so the resident's eval runs on a BOUNDED b |
| $EA29 | 1 | GFX_DFB | D | PUB | G3a DRAW parser state | graphics.asm:3, sysvars.inc:1 | $EA29: 1 = B (blank move) prefix pending (1) |
| $EA2A | 1 | GFX_DFN | D | PUB | G3a DRAW parser state | graphics.asm:3, sysvars.inc:1 | $EA2A: 1 = N (no-update) prefix pending (1) |
| $EA2B | 2 | GFX_DARG | D | PUB | G3a DRAW parser state | graphics.asm:17, sysvars.inc:1 | $EA2B: last parsed argument (int16 LE) (2) |
| $EA2D | 2 | GFX_DDX | D | PUB | G3a DRAW parser state | graphics.asm:5, sysvars.inc:1 | $EA2D: this command's dx (int16) (2) |
| $EA2F | 2 | GFX_DDY | D | PUB | G3a DRAW parser state | graphics.asm:5, sysvars.inc:1 | $EA2F: ...dy (2) |
| $EA31 | 2 | GFX_DTX | D | PUB | G3a DRAW parser state | graphics.asm:5, sysvars.inc:1 | $EA31: move target X (2) |
| $EA33 | 2 | GFX_DTY | D | PUB | G3a DRAW parser state | graphics.asm:5, sysvars.inc:1 | $EA33: ...Y (2) |
| $EA35 | 2 | GFX_DTMP | D | PUB | G3a DRAW parser state | graphics.asm:9, sysvars.inc:1 | $EA35: mul/rotate/sign scratch (2) |
| $EA37 | 2 | GFX_DSP | D | PUB | G3a DRAW parser state | graphics.asm:3, sysvars.inc:1 | $EA37: tenant entry SP -- an error deep in the (2 B) parse restores it and exits, so every helper can just jum |
| $EA39 | 2 | DEFT_PTR/RDV_LINE | D | PUB | G3b READ/DEFtype/target marshalling | usr.asm:2, sysvars.inc:2, deftype.asm:2, program.asm:1, readdata-body.inc:1 | $EA39: token cursor in AND out (2) |
| $EA3B | 2 | RDV_VAL | D | PUB | G3b READ/DEFtype/target marshalling | program.asm:2, sysvars.inc:1, readdata.asm:1 | $EA3B: the value read (int16 LE) (2) |
| $EA3D | 1 | RDV_ST | D | PUB | G3b READ/DEFtype/target marshalling | program.asm:1, sysvars.inc:1, readdata.asm:1 | $EA3D: tenant -> main STATUS (1): (1 B) 0 = out of data (ERR 4) 1 = an item was read (RDV_VAL / STRSCR) 2 = th |
| $EA3E | 1 | RDV_MODE | D | PUB | G3b READ/DEFtype/target marshalling | program.asm:2, readdata-body.inc:1, sysvars.inc:1 | $EA3E: main -> tenant MODE (1 B), D-READVAR: 0 = numeric, data_parse_int -> RDV_VAL 1 = string, the item's RAW |
| $EA3F | 2 | TGT_ADDR | D | PUB | G3b READ/DEFtype/target marshalling | vars.asm:6, sysvars.inc:2, field.asm:1, program.asm:1, str-engine.asm:1 | $EA3F: element address, or 0 = scalar (2) D-DEFINTTOK (2026-08-18) / D-DEFTYPETOK (2026-08-19): all four DEFty |
| $EA41 | 1 | GFX_DSCALE | C | PUB | G3c DRAW persistent scale/angle | sysvars.inc:2, graphics.asm:2, interp.asm:1 | $EA41: persistent scale, quarter units, 0 = NEVER SET (D-DSCALE): a distinct state from S4, in which no scalin |
| $EA42 | 1 | GFX_DANGLE | C | PUB | G3c DRAW persistent scale/angle | graphics.asm:2, interp.asm:1, sysvars.inc:1 | $EA42: persistent angle 0..3 (1) Boot 0 and an explicit `A0` are the SAME state (measured, d.a0.32k): no senti |
| $EA43 | 2 | GFX_G8N/GFX_PPITCH | D | PUB | G3d VDP()/BASE() marshalling | graphics.asm:17, sysvars.inc:2, graphics.asm:1 | $EA43: written index n (int16 LE) (2) |
| $EA45 | 2 | GFX_G8V | D | PUB | G3d VDP()/BASE() marshalling | graphics.asm:3, graphics.asm:2, sysvars.inc:1 | $EA45: written value (int16 LE) (2) |
| $EA47 | 96 | DB_WIN | D | SHARE | G4 LIST/PRINT USING render window | printusing.asm:2, detok.asm:2, list.asm:1, sysvars.inc:1, printusing.asm:1 | the render window, one page (96 B) |
| $EAC0 | 1 | FAT_SECPERCLUS | D | FLOOR | G5 FAT engine + file stream state (disk) | kernel.asm:18, fat-prim-body.inc:6, randio-body.inc:2, fatfits-body.inc:1, disk.asm:1, fat.asm:1 | sectors per cluster (byte) |
| $EAC1 | 2 | FAT_FATSTART | D | FLOOR | G5 FAT engine + file stream state (disk) | fat-prim-body.inc:7, fat.asm:2, kernel.asm:2 | first FAT sector (= reserved sectors) (word) |
| $EAC3 | 2 | FAT_FIRSTROOT | D | FLOOR | G5 FAT engine + file stream state (disk) | fat-prim-body.inc:4, kernel.asm:4, fat.asm:3 | first root-directory sector (word) |
| $EAC5 | 2 | FAT_TOTCLUS | D | FLOOR | G5 FAT engine + file stream state (disk) | fat-prim-body.inc:2 | total clusters + 2, from fat_mount (word; D-WCACHE W1 -- was FAT_ROOTSECS, now fat_rootsecs: FIRSTDATA - FIRST |
| $EAC7 | 2 | FAT_FIRSTDATA | D | FLOOR | G5 FAT engine + file stream state (disk) | fat-prim-body.inc:4, kernel.asm:3, fat.asm:2, randio-body.inc:1 | first data sector (word) |
| $EAC9 | 2 | FAT_CURCLUS/FCH_STATE0 | D | FLOOR | G5 FAT engine + file stream state (disk) | kernel.asm:11, fat-prim-body.inc:6, sysvars.inc:2, fatprim.asm:2, fiawalked-body.inc:1 | current cluster in the open file's chain (word) |
| $EACB | 1 | FAT_CLUSSEC | D | FLOOR | G5 FAT engine + file stream state (disk) | kernel.asm:9, fat-prim-body.inc:8, fiawalked-body.inc:3 | sector index within current cluster (byte) |
| $EACC | 2 | FAT_FIRSTCLUS | D | FLOOR | G5 FAT engine + file stream state (disk) | kernel.asm:13, fat-prim-body.inc:2, fat-delete-body.inc:1, randio-body.inc:1, fat.asm:1 | first cluster of the found file (word) |
| $EACE | 4 | FAT_FILESIZE | D | FLOOR | G5 FAT engine + file stream state (disk) | kernel.asm:12, randio-body.inc:6, fat.asm:5, fiawalked-body.inc:3, fatiocreate-body.inc:2, lofu32.asm:2 | file size in bytes (4-byte LE) |
| $EAD2 | 1 | FAT_NUMFATS | D | FLOOR | G5 FAT engine + file stream state (disk) | fat-prim-body.inc:2, fat.asm:2 | number of FAT copies (byte; from BPB +16) (1 B) |
| $EAD3 | 2 | FAT_SECPERFAT | D | FLOOR | G5 FAT engine + file stream state (disk) | fat-prim-body.inc:2, fat.asm:2 | sectors per FAT copy (word; from BPB +22) FAT12 working scratch (transient within a single call). |
| $EAD5 | 1 | FAT_PARITY | D | FLOOR | G5 FAT engine + file stream state (disk) | fat-prim-body.inc:9, kernel.asm:2, randio-body.inc:1, fat.asm:1 | 1 = odd cluster, 0 = even (FAT12 nibble pack) (1 B) |
| $EAD6 | 2 | FAT_BYTEIDX | D | FLOOR | G5 FAT engine + file stream state (disk) | fat-prim-body.inc:18, kernel.asm:4, randio-body.inc:3, fat.asm:2 | byte index within a FAT sector (word, 0..511) |
| $EAD8 | 2 | FAT_FATSEC | D | FLOOR | G5 FAT engine + file stream state (disk) | fat-prim-body.inc:11, fat.asm:3, kernel.asm:2, randio-body.inc:1 | FAT sector currently read (word) |
| $EADA | 1 | FAT_B0 | D | FLOOR | G5 FAT engine + file stream state (disk) | fat-prim-body.inc:9, randio-body.inc:3 | first FAT byte of a 12-bit entry (1 B) |
| $EADB | 1 | FAT_B1 | D | FLOOR | G5 FAT engine + file stream state (disk) | fat-prim-body.inc:9, randio-body.inc:3 | second FAT byte of a 12-bit entry (1 B) |
| $EADC | 2 | FAT_NAMEPTR | D | FLOOR | G5 FAT engine + file stream state (disk) | fat-prim-body.inc:5, kernel.asm:3 | -> 11-byte search name (word) |
| $EADE | 2 | FAT_DIRSEC | D | FLOOR | G5 FAT engine + file stream state (disk) | kernel.asm:13, fat-prim-body.inc:9, fat.asm:2 | current root-dir sector being scanned (word) |
| $EAE0 | 2 | FAT_DIRREM | D | FLOOR | G5 FAT engine + file stream state (disk) | kernel.asm:10, fat-prim-body.inc:7, fat.asm:1 | root-dir sectors remaining to scan (word) |
| $EAE2 | 2 | FAT_WRTMP | D | FLOOR | G5 FAT engine + file stream state (disk) | fat-prim-body.inc:9, kernel.asm:2, fat.asm:1 | transient scratch for the FAT12 write helpers (word) |
| $EAE4 | 2 | FAT_WRTMP2 | D | FLOOR | G5 FAT engine + file stream state (disk) | fat-prim-body.inc:8, kernel.asm:6, fiawalked-body.inc:4, fatprim.asm:1 | second transient (free-cluster scan cached sector) (2 B) Read byte-stream state (fat_io_open / fat_io_getbyte) |
| $EAE6 | 2 | FREAD_OFF | D | FLOOR | G5 FAT engine + file stream state (disk) | fatio-body.inc:6, bload.asm:3 | next byte index within FSECTOR_BUF (0..512) (word) |
| $EAE8 | 4 | FREAD_LEFT | D | FLOOR | G5 FAT engine + file stream state (disk) | fatio-body.inc:4, bload.asm:4 | bytes of the open file still undelivered (4-byte LE) Write byte-stream state (fat_io_create / fat_io_putbyte / |
| $EAEC | 2 | FWR_CLUS | D | FLOOR | G5 FAT engine + file stream state (disk) | fat-prim-body.inc:11, kernel.asm:5, fatfits-body.inc:1, fatiocreate-body.inc:1, fiawalked-body.inc:1 | chain-tail cluster currently being filled (word) |
| $EAEE | 2 | FWR_FIRST | D | FLOOR | G5 FAT engine + file stream state (disk) | fat-prim-body.inc:6, randio-body.inc:4, kernel.asm:4, fatfits-body.inc:1, fatiocreate-body.inc:1 | file's first cluster, 0 until first allocated (word) |
| $EAF0 | 1 | FWR_SECIDX | D | FLOOR | G5 FAT engine + file stream state (disk) | kernel.asm:6, fat-prim-body.inc:5, fiawalked-body.inc:3, fatiocreate-body.inc:1 | sector index within the current cluster (byte) |
| $EAF1 | 2 | FWR_BUFLEN | D | FLOOR | G5 FAT engine + file stream state (disk) | fatiow-body.inc:5, fiawalked-body.inc:4, kernel.asm:3, fat-prim-body.inc:2, fatiocreate-body.inc:1 | bytes currently buffered in FSECTOR_BUF (word, 0..512) |
| $EAF3 | 4 | FWR_BYTES | D | FLOOR | G5 FAT engine + file stream state (disk) | randio-body.inc:10, kernel.asm:10, fat-prim-body.inc:5, fiawalked-body.inc:3, field.asm:2, fatiocreate-body.inc:2 | total bytes written so far = final file size (4-byte LE) |
| $EAF7 | 2 | FWR_DIRSEC | D | FLOOR | G5 FAT engine + file stream state (disk) | fat-prim-body.inc:5, kernel.asm:4, fat-delete-body.inc:2, str-engine.asm:1, dirverb.asm:1 | logical sector holding the open file's dir entry (word) |
| $EAF9 | 2 | FWR_DIROFF | D | FLOOR | G5 FAT engine + file stream state (disk) | kernel.asm:4, fat-prim-body.inc:3, fat-delete-body.inc:1, sysvars.inc:1 | byte offset of that dir entry within its sector (word) DISKOP marshalling block (repack eviction, docs/spec-ev |
| $EAFB | 1 | AUDIO_VMASK/DISKOP_OP/FOPEN_SEL/LE_OP | D | PUB | G6 tenant op/status marshalling | kernel.asm:9, play.asm:3, playparse.asm:3, files.asm:3, sysvars.inc:3, list.asm:2 | $EAFB main->tenant: voices-present bitmask |
| $EAFC | 1 | AUDIO_STATUS/BN_STAT/CM_STATUS/DEFT_STATUS/DISKOP_STATUS/LE_STATUS | D | PUB | G6 tenant op/status marshalling | kernel.asm:14, lineedit.asm:10, playparse.asm:5, sysvars.inc:5, files.asm:3, deftype.asm:2 | $EAFC tenant->main: 0 ok / nonzero ERR code play_parse_tenant parse scratch -- transient, dead outside a PLAY  |
| $EAFD | ? | DISKOP_A/PLY_NUMOVF | D | PUB | G6 tenant op/status marshalling | playparse.asm:4, fatprim.asm:2, fat.asm:1, sysvars.inc:1 | tenant -> main: the primitive's real A output, if it has one (read_sector/write_sector's DSKIO error code); re |
| $EAFE | ? | BN_PTR/DISKOP_HL | D | PUB | G6 tenant op/status marshalling | bload.asm:2, fcbname.asm:2, fatprim.asm:2, fat.asm:1, sysvars.inc:1 | main <-> tenant: filename ptr (in) / advanced ptr = closing '"' (out) (2) |
| $EB00 | 16 | FCH_MODES | C | DYN | G7a channel modes | files.asm:3, grpdev.asm:1, fat-prim-body.inc:1, fatprim.asm:1, kernel.asm:1 | 16 B ($EB00..$EB0F) D-LNLIST (docs/spec-basic-lnlist.md R-L1..R-L3): the tokeniser's LINE-NUMBER MODE. A branc |
| $EB10 | 32 | FCH_RECLENS | D | FLOOR | G7b record lengths / numbers (disk) | field.asm:2, files.asm:1, randio-body.inc:1 | 32 B ($EB10..$EB2F). ~~$EA92..$EAFF free (110 B)~~ \U0001f534 STALE SINCE D-DEFFN: $EA9C..$EB00 is FN_PAREA (t |
| $EB30 | 2 | RN_PTR | D | FLOOR | G7b record lengths / numbers (disk) | lineedit.asm:6, program.asm:2 | RENUM: the reference-pass cursor (2) |
| $EB32 | 2 | AU_NUM/RN_NEW | D | FLOOR | G7b record lengths / numbers (disk) | lineedit.asm:9, program.asm:4, sysvars.inc:1 | AUTO: the line number being prompted (2) |
| $EB34 | 2 | RN_OLD | D | FLOOR | G7b record lengths / numbers (disk) | lineedit.asm:3 | RENUM: old line to start renumbering at (2) |
| $EB36 | 2 | AU_INC/RN_INC | D | FLOOR | G7b record lengths / numbers (disk) | lineedit.asm:10, program.asm:1, sysvars.inc:1 | AUTO: the increment (2) read_line's mode flag. 0 = block in CHGET (the REPL); 1 = poll CHSNS and BREAKX (an AU |
| $EB38 | 1 | RL_AUTO | D | FLOOR | G7b record lengths / numbers (disk) | program.asm:2, repl.asm:2 | read_line: 1 = AUTO's polling mode (1) |
| $EB39 | 1 | LPTPOS | D | FLOOR | G7b record lengths / numbers (disk) | print.asm:4, str-engine.asm:2, expr.asm:1, files.asm:1, kernel.asm:1 | printer head column, 0-based (1) |
| $EB3A | 2 | GP_SRC | D | FLOOR | G7b record lengths / numbers (disk) | randio-body.inc:6 | pass cursor into FSECTOR_BUF (2) |
| $EB3C | 2 | GP_LEFT | D | FLOOR | G7b record lengths / numbers (disk) | randio-body.inc:7 | record bytes still to move, ends $EA3E (2 B) |
| $EB3E | 2 | CLR_SAVE | D | FLOOR | G7b record lengths / numbers (disk) | main.asm:2, screen.asm:2 | fg+bg, in flight across a COLOR statement (2) FREE-RAM $EB80..$EB92 (D-LOC took $EA40..$EA5F for FCH_RECNOS, 2 |
| $EB40 | 32 | FCH_RECNOS | D | FLOOR | G7b record lengths / numbers (disk) | randio-body.inc:2, expr.asm:1, field.asm:1 | 32 B ($EB40..$EB5F): per-channel record number of the last GET/PUT 🔴 THE RANGE IS SPELLED OUT BECAUSE "32 B" A |
| $EB60 | 32 | PU_NUM | D | PUB | G8 PRINT USING numeric buffer | printusing.asm:8, punum.asm:5, printusing.asm:1 | PRINT USING numeric render buffer, 0-terminated (32 B) |
| $EB92 | 2 | FN_BASE/FN_PTR/FOR_STK_END | C | PUB | G9 DEF FN frame + parameter area | sysvars.inc:12, deffn.asm:11, deffn.asm:4 | $EB92: base of the whole DEF FN frame |
| $EB94 | 2 | FN_DPTR | C | PUB | G9 DEF FN frame + parameter area | deffn.asm:11 | 2 B: the definition cursor, tenant-only ⚠️ THERE IS NO `FN_REQ` CELL, AND THERE WAS: the request/answer byte t |
| $EB96 | 2 | FN_KEY | C | PUB | G9 DEF FN frame + parameter area | deffn.asm:4, deffn.asm:2 | 2 B: the formal (or the $FFFF result slot) |
| $EB98 | 1 | FN_TYP | C | PUB | G9 DEF FN frame + parameter area | deffn.asm:5, deffn.asm:3 | 1 B: its type -- and the ERR code on req 0 |
| $EB99 | 1 | FN_FEND | C | PUB | G9 DEF FN frame + parameter area | deffn.asm:4, interp.asm:1, usr.asm:1, arrays.asm:1, strheap.asm:1 | 1 B: low byte of one-past the live frame. == low FN_PAREA means "no FN call in progress" -- the fast miss ever |
| $EB9A | 1 | FN_SLOTP | C | PUB | G9 DEF FN frame + parameter area | deffn.asm:5 | 1 B: low byte of the slot the NEXT formal takes |
| $EB9B | 1 | FN_RTYPE | C | PUB | G9 DEF FN frame + parameter area | deffn.asm:3 | 1 B: the FN's own resolved type (its result type) |
| $EB9C | ? | FN_PAREA | C | PUB | G9 DEF FN frame + parameter area | deffn.asm:6, sysvars.inc:2, interp.asm:1, usr.asm:1, arrays.asm:1, strheap.asm:1 | the shadow-parameter slots themselves |
| $EBFF | ? | FN_PAREA_END | C | PUB | G9 DEF FN frame + parameter area |  |  |
| $EC10 | 1 | ERRMARK | D | ELIM | G10a ERRMARK | program.asm:5, interp.asm:2, missing.asm:2, bload.asm:1, cload.asm:1, bload.asm:1 | error landmark marker byte (1 B) |
| $EC12 | 1 | FCH_ACTIVE | C | PUB | G10b FCH_ACTIVE | files.asm:12, kernel.asm:7, fat-prim-body.inc:2, randio-body.inc:1, fatprim.asm:1 | channel live in the engine globals, 0 = none (1) FCH_MODES — per-channel mode array [0..FCH_CEIL]; [0] unused, |
| $EC13 | 1 | TKLNUM | D | PUB | G10c tokeniser line-number mode | tokenise.inc:9 | tokeniser: 1 = line-number mode is armed (1) |
| $EC16 | 1 | INDLR_N | D | PUB | G10d INPUT$ count | strvar.asm:4 | INPUT$(n,#f): remaining bytes to read (transient, 1) (1 B) |
| $EC17 | 2 | MRG_PTR | D | PUB | G10e MERGE cursor | files.asm:5 | MERGE: write cursor into LINEBUF for the current line (2) Random-access (FIELD/LSET/RSET) transient parse/stor |
| $EC19 | 2 | FLD_CUROFF | D | FLOOR | G10f FIELD/LSET/RSET scratch (disk) | field.asm:7 | FIELD: running byte offset into the record buffer (2) |
| $EC1B | 1 | FLD_CHAN | D | FLOOR | G10f FIELD/LSET/RSET scratch (disk) | field.asm:6, kernel.asm:1 | FIELD/LSET/RSET: the channel being fielded (1) |
| $EC1C | 1 | LRSET_JUST | D | FLOOR | G10f FIELD/LSET/RSET scratch (disk) | field.asm:1, lrsetst.asm:1 | LSET/RSET: 0 = left-justify, 1 = right-justify (1) |
| $EC1D | 1 | LRSET_W | D | FLOOR | G10f FIELD/LSET/RSET scratch (disk) | lrsetst.asm:3, field.asm:1, kernel.asm:1 | LSET/RSET: destination field width (1) |
| $EC1E | 2 | LRSET_DEST | D | FLOOR | G10f FIELD/LSET/RSET scratch (disk) | field.asm:1, lrsetst.asm:1, kernel.asm:1 | LSET/RSET: destination ADDRESS of the store (2). (2 B) D-LRVAR renamed this from LRSET_OFF (same address, 0 RA |
| $EC20 | 2 | CURPTR | A | PUB | G11 BLOAD start/end/exec | bload-body.inc:10, sv-bsvdisk.inc:6, sv-bsvcas.inc:5, save.asm:2 | current load pointer (2 bytes) |
| $EC22 | 2 | ENDPTR | A | PUB | G11 BLOAD start/end/exec | bload-body.inc:6 | final load address (2 bytes) |
| $EC24 | 2 | EXECPTR | A | PUB | G11 BLOAD start/end/exec | bload-body.inc:6, save.asm:4, bload.asm:1, sv-bsvcas.inc:1, sv-bsvdisk.inc:1 | execution address (2 bytes) |
| $EC26 | 2 | PRGEND | C | ELIM | G12 PRGEND | lineedit.asm:19, arrays.asm:1, basicrom.asm:1, clear.asm:1, cload.asm:1, program.asm:1 | addr of the $0000 end-of-program marker (2 bytes) |
| $EC28 | 1 | ARY_OP/TKNAME | D | PUB | G13a array/tokeniser/CLOAD marshalling | tokenise.inc:6, vars.asm:4, arrays.asm:3, arrays.asm:1 | 0=RESOLVE (read/write element, auto-dim on read) / 1=DIM (explicit declare) / 2=ERASE (free, slice-2, docs/spe |
| $EC29 | ? | ARY_KEY/TKRADIX | D | PUB | G13a array/tokeniser/CLOAD marshalling | arrays.asm:7, tokenise.inc:4, vars.asm:3, arrays.asm:2 | name0/name1 key (BC round-trip: written via `ld (ARY_KEY),bc`, read via `ld bc,(ARY_KEY)` on both sides -- byt |
| $EC2A | 1 | TKRTOK | D | PUB | G13a array/tokeniser/CLOAD marshalling | tokenise.inc:3 | tokeniser: &H/&O constant token to emit, $0C/$0B (1 B) |
| $EC2B | ? | ARY_TYPE/CLPTR | D | PUB | G13a array/tokeniser/CLOAD marshalling | arrays.asm:7, kernel.asm:7, cload.asm:6, arrays.asm:4, vars.asm:4 | 2/4/8 (int/single/double) (1) |
| $EC2C | 1 | ARY_NIDX | D | PUB | G13a array/tokeniser/CLOAD marshalling | arrays.asm:7, arrays.asm:3 | parsed subscript/bound count for the CURRENT reference (1) |
| $EC2D | 2 | ARY_IDXP/CLINK | D | PUB | G13a array/tokeniser/CLOAD marshalling | arrays.asm:6, casmatch-body.inc:6, cload.asm:3, kernel.asm:3, arrays.asm:1 | [D-ARR-C] POINTER to the parsed subscripts (RESOLVE) or bounds (DIM) -- int16 LE, ndim of them, living in the  |
| $EC2F | 1 | RUNFLAG | A | PUB | G13b RUNFLAG | bload.asm:5, cload.asm:1, bload-body.inc:1 | 1 = ,R handoff requested (set while parsing) (1) |
| $EC30 | ? | GFX_OP/LST_LO/RN_TGT/SL_DELLO/SL_NUM | D | PUB | G13c graphics/LIST/RENUM/store marshalling | lineedit.asm:11, graphics.asm:6, sysvars.inc:3, list.asm:2, program.asm:2, graphics.asm:1 | main->tenant op: 0=selftest(G1) 1=plot(PSET/PRESET) 2=point (1) |
| $EC31 | 1 | GFX_C | D | PUB | G13c graphics/LIST/RENUM/store marshalling | graphics.asm:9, graphics.asm:6, circleparse.asm:2, grpprt.asm:1 | main->tenant: resolved plot colour 0..15 (PSET/PRESET) (1) |
| $EC32 | ? | GFX_RES/SL_SLOT | D | PUB | G13c graphics/LIST/RENUM/store marshalling | lineedit.asm:10, graphics.asm:6, graphics.asm:6, circleparse.asm:4 | tenant->main: POINT result colour 0..15 (1) |
| $EC33 | 1 | GFX_REL | D | PUB | G13c graphics/LIST/RENUM/store marshalling | graphics.asm:2 | parse_coord: 1 = STEP (relative) coordinate, 0 = absolute (1) Graphics G3 (LINE) marshalling + Bresenham state |
| $EC34 | ? | LST_HI/RN_LINE/SL_DELHI/SL_SIZE | D | PUB | G13c graphics/LIST/RENUM/store marshalling | lineedit.asm:14, sysvars.inc:3, list.asm:2, program.asm:1 | LIST: high end of the range (2) |
| $EC35 | ? | ARY_ADDR | D | PUB | G13c graphics/LIST/RENUM/store marshalling | arrays.asm:5, vars.asm:4, arrays.asm:2, str-engine.asm:1 | [tenant return, RESOLVE] element address (2) -- also SCALAR_FIND/SCALAR_ALLOC's own return (§4b): the scalar e |
| $EC36 | ? | LST_PTR/SL_DELPTR/SL_TOK | D | PUB | G13c graphics/LIST/RENUM/store marshalling | lineedit.asm:5, program.asm:2, sysvars.inc:2, list.asm:1 | LIST: the statement cursor, on the token |
| $EC37 | 1 | ARY_ERR | D | PUB | G13c graphics/LIST/RENUM/store marshalling | arrays.asm:13, arrays.asm:1 | [tenant return] 0 ok; 1 Subscript-oor; (1 B) 2 Illegal-fn (negative); 3 Redimensioned; 4 Out of memory -- an A |
| $EC38 | 2 | CURLINE | C | ELIM | G14 run-loop control (CURLINE, GOTO/END/RESUME flags) | program.asm:13, interp.asm:4, errtrap.asm:3, arrays.asm:1, str-engine.asm:1, traps.asm:1 | link-field addr of the line being executed (2) |
| $EC3A | 2 | GOTOTGT | C | ELIM | G14 run-loop control (CURLINE, GOTO/END/RESUME flags) | program.asm:3, interp.asm:1 | pending branch-target line addr (2) |
| $EC3C | 1 | GOTOFLAG | C | ELIM | G14 run-loop control (CURLINE, GOTO/END/RESUME flags) | program.asm:5, interp.asm:1 | 1 = a branch (GOTO) is pending (1 B) |
| $EC3D | 1 | ENDFLAG | C | ELIM | G14 run-loop control (CURLINE, GOTO/END/RESUME flags) | program.asm:6, arrays.asm:1 | 1 = END/STOP reached, stop the run (1 B) Mid-line resume: GOTO branches to a line *start*, but RETURN and NEXT |
| $EC3E | 2 | RESUMEPTR | C | ELIM | G14 run-loop control (CURLINE, GOTO/END/RESUME flags) | program.asm:4, interp.asm:1 | mid-line resume token pointer (2) |
| $EC40 | 1 | RESUMEFLAG | C | ELIM | G14 run-loop control (CURLINE, GOTO/END/RESUME flags) | program.asm:8, interp.asm:1 | 1 = resume at RESUMEPTR (set by RETURN / NEXT) (1 B) CONT / Ctrl-STOP break-resume state (own-design; see PROV |
| $EC41 | 2 | GSP | C | PUB | G15a GSP/FSP | program.asm:5, traps.asm:1, strheap.asm:1 | newest GOSUB frame's address; == CTLTOP if none (2) |
| $EC43 | 2 | FSP | C | PUB | G15a GSP/FSP | program.asm:5, traps.asm:1, strheap.asm:1 | the FOR run's FLOOR: FOR frames are [CSP,FSP) (2) D-FORFLOAT (docs/spec-basic-forfloat.md): a FOR frame is 25  |
| $EC45 | 1 | SEQ_EOF | D | PUB | G15b SEQ_EOF, ARY_CUR | bload.asm:2, input.asm:1 | seqio tenant -> main: 1 = no byte / at the end (D-SEQEOF) (1 B) FREE-RAM $EC48..$EC50 the old 11-byte FOR_CUR, |
| $EC46 | 2 | ARY_CUR | D | PUB | G15b SEQ_EOF, ARY_CUR | arrays.asm:3 | [D-ARR-C] the text cursor, parked across the engine call (2) subrom_call/CALSLT clobbers HL, and the fused ary |
| $EC50 | 2 | CSP | C | PUB | G15c CSP/CTLTOP/TSP/CTLLIM/SL_CEIL | program.asm:8, deffn.asm:7, str-engine.asm:3, clear.asm:2, strheap.asm:2, traps.asm:1 | the pool's allocation frontier, descending (2) |
| $EC52 | 2 | CTLTOP | C | PUB | G15c CSP/CTLTOP/TSP/CTLLIM/SL_CEIL | program.asm:1, strheap.asm:1 | the pool's TOP = strheap_varceil(), cached (2) |
| $EC54 | 2 | TSP | C | PUB | G15c CSP/CTLTOP/TSP/CTLLIM/SL_CEIL | traps.asm:5, strheap.asm:1 | newest trap SERVICE record; valid iff TRAPSVC != 0 (2) |
| $EC56 | 2 | CTLLIM | C | PUB | G15c CSP/CTLTOP/TSP/CTLLIM/SL_CEIL | expr.asm:1, str-engine.asm:1, deffn.asm:1, playparse.asm:1, strheap.asm:1 | the pool's collision FLOOR = ARYEND+2 (2). Written (2 B) sub-side by strheap_ctllim at the two allocator succe |
| $EC58 | 2 | SL_CEIL | C | PUB | G15c CSP/CTLTOP/TSP/CTLLIM/SL_CEIL | program.asm:1, lineedit.asm:1 | store_line: the ceiling a store stays below (2 B) i.e. the VARIABLE region's. D-TXTCEIL: written by dl_store f |
| $EC5A | 32 | PU_DIG | D | PUB | G16 flt_fmt digit buffer | punum.asm:2 | D-PUEXP: flt_fmt's significant digits, point removed (32 B) |
| $EC7A | 2 | CSR_ADDR | D | PUB | G17 editor cursor | cursor.asm:3 | VRAM address of the cell the cursor covers (2 B) |
| $EC7C | 1 | CSR_CHAR | D | PUB | G17 editor cursor | cursor.asm:2 | the character it covers, put back on removal (1 B) |
| $EC7D | 1 | CSR_ON | D | PUB | G17 editor cursor | cursor.asm:4, interp.asm:1 | 1 while the cursor is shown, else 0 (1 B) FREE-RAM $EC7E..$EC80 the rest of the retired GOSUB_STK (PU_DIG took |
| $EC80 | 11 | COPY_SRC | D | FLOOR | G18 COPY scratch (disk) | kernel.asm:10 | the source's 11-byte 8.3 name field |
| $EC8B | 2 | COPY_CLUS | D | FLOOR | G18 COPY scratch (disk) | kernel.asm:2 | the source's first cluster (word) |
| $EC8D | 4 | COPY_LEFT | D | FLOOR | G18 COPY scratch (disk) | kernel.asm:14 | bytes still to copy (4-byte LE) D-SCREDIT (docs/spec-basic-screditor.md): read_line's marshalling to the readl |
| $EC91 | 2 | RL_HL | D | PUB | G19 readline marshalling | readline.asm:3, repl.asm:2 | main -> tenant: the write cursor (LINEBUF, or AUTO's preset) (2) |
| $EC93 | 1 | RL_STAT | D | PUB | G19 readline marshalling | repl.asm:1, readline.asm:1 | tenant -> main: 0 = Enter, $FF = Ctrl-STOP / Ctrl-C (1) |
| $EC94 | 1 | RL_ROW0 | D | PUB | G19 readline marshalling | readline.asm:2, repl.asm:1, edctrl.asm:1 | the row where input began (1-based; 0 once scrolled off) (1) |
| $EC95 | 1 | RL_COL0 | D | PUB | G19 readline marshalling | repl.asm:1, readline.asm:1, edctrl.asm:1 | the column where input began, after any prompt (1) |
| $EC96 | 1 | RL_LAST | D | PUB | G19 readline marshalling | readline.asm:5 | the logical line's last row at Enter (1) |
| $EC97 | 1 | RL_KEY | D | PUB | G19 readline marshalling | repl.asm:2, readline.asm:1, edctrl.asm:1 | main -> tenant: the key CHGET returned (main waits in CHGET, as before) (1) D-DISKERR (docs/spec-basic-diskerr |
| $EC98 | 1 | DISKOP_ERR | D | FLOOR | G20a DISKOP_ERR | kernel.asm:12, fat-prim-body.inc:5, files.asm:2, randio-body.inc:1, sv-bsvdisk.inc:1, bload.asm:1 | tenant -> main: ERR code of the last DSKIO failure, 0 = none (1) D-FNPOOL (docs/spec-basic-fnpool.md): `DEF FN |
| $EC99 | 2 | FNSP | C | PUB | G20b FNSP, FN_FST | deffn.asm:6, strheap.asm:2, interp.asm:1 | newest FN frame's address, 0 = no FN call live (2) |
| $EC9B | 1 | FN_FST | C | PUB | G20b FNSP, FN_FST | deffn.asm:2, deffn.asm:1 | tenant -> main: 0 = frame saved, 1 = pool full -> ERR 7 (1) FREE-RAM $ECB6..$ECB8 the rest of the pre-D-FORVAR |
| $EC9C | 29 | FOR_CUR | D | DYN | G21 NEXT working FOR frame | program.asm:9, vars.asm:5, sysvars.inc:5 | scratch: a working copy of one FOR frame (25), and ALSO the key a NEXT parses into before it matches (spec §4. |
| $EC9F | 9 | FOR_LIM | D | DYN | G21 NEXT working FOR frame | program.asm:2 | the limit slot [type][8] (9) |
| $ECA8 | 9 | FOR_STEP | D | DYN | G21 NEXT working FOR frame | program.asm:2 | the step slot [type][8] (9) |
| $ECB1 | 2 | FOR_LINE | D | DYN | G21 NEXT working FOR frame | program.asm:2 | CURLINE of the FOR (2) |
| $ECB3 | 2 | FOR_BODY | D | DYN | G21 NEXT working FOR frame | program.asm:2 | the loop body's text pointer (2) |
| $ECB5 | 1 | FOR_SIGN | D | DYN | G21 NEXT working FOR frame | program.asm:2 | NEXT's scratch: the step's sign byte (1) $E04E was FOR_NEW — NEXT's freshly-stepped loop value, parked in RAM  |
| $ECB8 | 1 | DATASTATE | C | PUB | G22 DATA pointer state | readdata-body.inc:4, program.asm:3, arrays.asm:1 | 0 = unpositioned (RESTORE), 1 = ready, 2 = exhausted (1 B) |
| $ECB9 | 2 | DATAPTR | C | PUB | G22 DATA pointer state | readdata-body.inc:3, program.asm:1 | next unread DATA item (ASCII) in the program (2) |
| $ECBB | 2 | DATALINE | C | PUB | G22 DATA pointer state | readdata-body.inc:5, program.asm:1 | link-field of the line holding DATAPTR (2) |
| $ECBD | 2 | RESTORE_LINE | C | PUB | G22 DATA pointer state | program.asm:2, readdata-body.inc:2 | link-field a READ seeks DATA from when unpositioned (2) $E0BF was READVAR — the ONE letter ex_read latched as  |
| $ECC0 | ? | INP_CURSOR/NUMBUF | D | PUB | G23 INPUT cursor / NUMBUF | detok.inc:6, strheap.asm:5, input.asm:4, print.asm:4, printusing.asm:3, list.asm:1 | console INPUT LINEBUF read pointer (2 B, aliases NUMBUF) |
| $ECC8 | 1 | VALTYP | D | PUB | G24a private VALTYP | strvar.asm:1 | 0 = numeric result, 1 = string result (1 byte) |
| $ECC9 | 2 | STRPTR | D | PUB | G24b STRPTR | str-engine.asm:21, printusing.asm:5, arrays.asm:5, graphics.asm:3, deffn.asm:2, strvar.asm:2 | pointer to the [len][bytes] descriptor (2 bytes) PRINT output destination (Phase 2 PRINT#). 0 = screen (CHPUT) |
| $ECCB | 1 | PRDEST | C | PUB | G24c PRDEST/PRDEV | print.asm:5, save.asm:5, interp.asm:2, arrays.asm:1, files.asm:1, input.asm:1 | PRINT destination: 0=screen, 1=file channel (1) When PRDEST=1, PRDEV selects WHICH sink pchar uses: 0 = disk f |
| $ECCC | 1 | PRDEV | C | PUB | G24c PRDEST/PRDEV | print.asm:5, save.asm:3, files.asm:1, list.asm:1 | PRINT# device sink selector (1) |
| $ECCD | ? | OO_DEVTYPE | D | PUB | G24d OPEN device type | files.asm:6, fatprim.asm:2 | OPEN device-channel type being parsed (transient, 1) ascii_read_lines' byte-source vector (files.asm D2 getbyt |
| $ECCE | 2 | ARL_GETBYTE | C | PUB | G24e ARL_GETBYTE vector | files.asm:4, input.asm:3, cload.asm:2, strvar.asm:1 | ascii_read_lines byte-source vector (2) S10.B (2026-10-06): a disk file open FOR OUTPUT is mode 3 -- its chann |
| $ECD0 | 2 | CONTLINE | C | PUB | G25 CONT state | program.asm:2 | saved CURLINE for CONT (2) |
| $ECD2 | 2 | CONTPTR | C | PUB | G25 CONT state | program.asm:2 | saved resume token pointer for CONT (2) |
| $ECD4 | 1 | CONTVALID | C | PUB | G25 CONT state | program.asm:6 | 1 = a CONT resume point is valid (1) Extension-ROM INIT scan scratch (initext.asm). Used ONCE at INIT, entirel |
| $ECD5 | 1 | SCAN_PRIM | D | SHARE | G26 boot slot scan scratch | islands.asm:5 | primary slot currently being scanned (1) |
| $ECD6 | 1 | SCAN_SLOT | D | SHARE | G26 boot slot scan scratch | islands.asm:4, basicrom.asm:2, subrom-boot.asm:2 | candidate slot id for RDSLT/CALSLT (1) |
| $ECD7 | 2 | SCAN_INIT | D | SHARE | G26 boot slot scan scratch | islands.asm:4 | candidate ROM's INIT entry address (2) |
| $ECD9 | 2 | SCAN_IY | D | SHARE | G26 boot slot scan scratch | islands.asm:2, fat-prim-body.inc:2, format.asm:2 | CALSLT slot word: high byte = slot (IYh) (2) Disk filename scratch (the disk loader/saver verbs). Built by par |
| $ECDB | ? | DISK_FCB/DISK_FCB_DRV | A | PUB | G27a disk/tape name block (FCB name) | sysvars.inc:2, pdfcb-body.inc:2, fatprim.asm:1 | scratch name block ($E0DB.., 12 bytes) |
| $ECDC | 11 | DISK_FCB_NAME | A | PUB | G27a disk/tape name block (FCB name) | kernel.asm:14, fcbname-body.inc:4, cload.asm:2, randio-body.inc:2, files.asm:1, fat-delete-body.inc:1 | +1..+11: 8.3 name field (11 bytes) Disk-ROM slot id recorded by the INIT scan (initext.asm) when it inits an e |
| $ECE7 | 1 | DISKSLOT | C | PUB | G27b DISKSLOT/_OK | interp.asm:1, islands.asm:1, fat-prim-body.inc:1, format.asm:1 | disk ROM slot id for CALSLT (1) |
| $ECE8 | 1 | DISKSLOT_OK | C | PUB | G27b DISKSLOT/_OK | islands.asm:2, bload-body.inc:2, format.asm:1, program.asm:1, sv-diskwr.inc:1, kernel.asm:1 | 1 = DISKSLOT holds a valid disk-ROM slot id (1 B) BSAVE/BLOAD ",S" VRAM select (page $E0 free gap $E0E9..$E0EC |
| $ECE9 | 1 | VRAM_FLAG | A | PUB | G28a VRAM_FLAG | bload.asm:5, save.asm:2, bload-body.inc:2, sv-bsvdisk.inc:1 | 1 = ",S" VRAM save/load (1) CAL_CURHI: cassette ASCII load's DOUBLE-BUFFER "which buffer is being served" poin |
| $ECEA | ? | CAL_CNT | A | DYN | G28b cassette ASCII double-buffer state | cal-refill-body.inc:3, casmatch.asm:3, bload.asm:1 | cassette ASCII load: read position in the current 256-byte tape block, 0..255 (1) |
| $ECEB | 1 | CAL_NEEDFILL | A | DYN | G28b cassette ASCII double-buffer state | cload.asm:2, bload.asm:2, casmatch.asm:2 | cassette ASCII load: whether the buffer CAL_CURHI (1 B) does NOT point at holds a live pre-fetched block. 0 =  |
| $ECEC | ? | CAL_SAVE/CAS_WCNT | A | DYN | G28b cassette ASCII double-buffer state | save.asm:7, casmatch.asm:2 | cassette ASCII load: parked byte across a prefetch (1) Cassette ASCII SAVE (save.asm cas_wbyte) block-fill cou |
| $ECED | 2 | DSV_PTR | D | FLOOR | G28c disk SAVE scratch | sv-savdisk.inc:5, sv-diskwr.inc:2 | SAVE: current source byte pointer (2) |
| $ECEF | 2 | DSV_END | D | FLOOR | G28c disk SAVE scratch | sv-bsvdisk.inc:3, sv-savdisk.inc:2, save.asm:1 | SAVE/BSAVE: last source byte addr, inclusive (2) Tape CSAVE / BSAVE write scratch (page $E0, $E0F1.. gap; dead |
| $ECF1 | 2 | SSE_OUT/TSV_PTR | A | PUB | G28d tape save scratch / statement-scan result | sv-tsb.inc:5, sv-tne.inc:4, errtrap.asm:3, sv-tputw.inc:2, interp.asm:1, sysvars.inc:1 | tenant -> main: next statement's start, or $0000 if the erroring line's own link was $0000 (degenerate -- noth |
| $ECF3 | 2 | TSV_END | A | PUB | G28d tape save scratch / statement-scan result | sv-bsvcas.inc:2, sv-tsb.inc:2, save.asm:1 | tape save: last source-byte address, inclusive (2) |
| $ECF5 | 1 | FMT_GEOMSEL/TSV_CNT | A | PUB | G28d tape save scratch / statement-scan result | sv-tsb.inc:5, sv-bsvcas.inc:3, save.asm:2, sv-tne.inc:2, format.asm:1, kernel.asm:1 | main -> tenant: 0 = 360k, 1 = 720k (1) |
| $ECF6 | 1 | FMT_RESULT/TSV_NAME | A | PUB | G28d tape save scratch / statement-scan result | format.asm:2, format.asm:1, kernel.asm:1, files.asm:1, save.asm:1, sv-tne.inc:1 | tenant -> main: 0 = ok, 1 = DSKIO write error (1) scan_stmt_end (SUBROM_IDX_SCANSTMT, sub/errtrap.asm) result  |
| $ECFC | 1 | FILES_ENTIDX/IN_RDLEN | A | PUB | G28e FILES idx / INPUT$ read length | files.asm:5, kernel.asm:4, strvar.asm:4, bload.asm:4 | FILES: dir entry index 0..15 within a sector (1) Sequential file-channel state (Phase 2). A SINGLE open channe |
| $ECFD | 1 | FCH_NUM | C | DYN | G28f FCH_NUM/MODE/RDMODE | files.asm:3 | open channel's file number, 0 = none open (1) |
| $ECFE | 1 | FCH_MODE | C | DYN | G28f FCH_NUM/MODE/RDMODE | files.asm:13, main.asm:1, print.asm:1, bload.asm:1 | open mode: 0=none, 1=INPUT, 2=OUTPUT (1) |
| $ECFF | 1 | FCH_RDMODE | C | DYN | G28f FCH_NUM/MODE/RDMODE | input.asm:4, files.asm:2, strvar.asm:1, bload.asm:1 | current read: 0=INPUT# (stop at ','/CR), 1=LINE (1) The read-length counter overlays FILES_ENTIDX ($E0FC): FIL |
| $ED00 | 2 | GFX_X1 | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:12, graphics.asm:2 | LINE endpoint 1 X (int16 LE) -- resident marshals, tenant reads |
| $ED02 | 2 | GFX_Y1 | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:16, graphics.asm:2 | LINE endpoint 1 Y (int16 LE) |
| $ED04 | 2 | GFX_X2 | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:12, graphics.asm:1 | LINE endpoint 2 X (int16 LE) |
| $ED06 | 2 | GFX_Y2 | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:13, graphics.asm:1 | LINE endpoint 2 Y (int16 LE) |
| $ED08 | 1 | GFX_MODE | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:2, graphics.asm:2 | GFX_OP=3 sub-mode: 0=segment 1=box outline 2=box fill (1) |
| $ED09 | 2 | GFX_CX | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:9 | Bresenham: current pixel X (int16, may be off-screen) (2) |
| $ED0B | 2 | GFX_CY | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:9 | Bresenham: current pixel Y (int16) (2) |
| $ED0D | 2 | GFX_ERR | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:4 | Bresenham: error accumulator, in [0,DMAJ) (2) |
| $ED0F | 2 | GFX_DMAJ | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:6 | Bresenham: major-axis delta (2) |
| $ED11 | 2 | GFX_DMIN | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:5 | Bresenham: minor-axis delta (2) |
| $ED13 | 2 | GFX_CNT | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:3 | Bresenham: major steps still to take (2) |
| $ED15 | 1 | GFX_STEEP | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:4 | Bresenham: 0 = x-major, 1 = y-major (1) |
| $ED16 | 2 | GFX_SMIN | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:3 | Bresenham: minor-axis step, $0001 (+1) or $FFFF (-1) (2) |
| $ED18 | 1 | GFX_SDX | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:4 | init scratch: sign of (x2-x1), $01/$FF (1) |
| $ED19 | 1 | GFX_SDY | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:4 | init scratch: sign of (y2-y1), $01/$FF (1) |
| $ED1A | 2 | GFX_TX1 | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:12 | box: stashed corner 1 X (2) |
| $ED1C | 2 | GFX_TY1 | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:8 | box: stashed corner 1 Y (2) |
| $ED1E | 2 | GFX_TX2 | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:11 | box: stashed corner 2 X (2) |
| $ED20 | 2 | GFX_TY2 | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:7 | box: stashed corner 2 Y (2) |
| $ED22 | 2 | GFX_FILLCNT | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:3 | box fill: scanlines remaining (2) |
| $ED24 | 2 | GFX_YSTEP | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:2 | box fill: row step, $0001/$FFFF (2) -> ends $E126 (2 B) Graphics G4 (CIRCLE, docs/spec-basic-graphics-g4.md §6 |
| $ED26 | 2 | GFX_CXC | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:4, graphics.asm:1 | centre X (int16 LE) (2) |
| $ED28 | 2 | GFX_CYC | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:5, graphics.asm:1 | centre Y (int16 LE) (2) |
| $ED2A | 2 | GFX_R | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:5, circleparse.asm:1 | radius (int16, >=0 -- resident guards G4-rneg) (2) |
| $ED2C | 1 | GFX_ASPMAJ | D | PUB | G29 LINE/CIRCLE/POINT graphics state | circleparse.asm:3, graphics.asm:2 | 0 = x-major (aspect<=1), 1 = y-major (aspect>1) (1) |
| $ED2D | 2 | GFX_ASPS | D | PUB | G29 LINE/CIRCLE/POINT graphics state | circleparse.asm:2, graphics.asm:1 | 8.8 minor scale S, round(minor_ratio*256); 256=no scale (2) |
| $ED2F | 1 | GFX_ARCF | D | PUB | G29 LINE/CIRCLE/POINT graphics state | circleparse.asm:2, graphics.asm:2 | 0 = full circle (ignore S/E), 1 = arc (apply the mask) (1) |
| $ED30 | 2 | GFX_SVX | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:2 | start boundary vector X, screen-offset scaled ints (2) |
| $ED32 | 2 | GFX_SVY | D | PUB | G29 LINE/CIRCLE/POINT graphics state |  | start boundary vector Y (2) |
| $ED34 | 2 | GFX_EVX | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:2 | end boundary vector X (2) |
| $ED36 | 2 | GFX_EVY | D | PUB | G29 LINE/CIRCLE/POINT graphics state |  | end boundary vector Y (2) |
| $ED38 | 1 | GFX_FULLW | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:3 | full-wrap flag (0/1): the two boundaries land in the SAME (octant,pos) cell but their RAW (oct,u14) records di |
| $ED39 | 2 | GFX_QX | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:21 | midpoint-circle octant state: x (2) |
| $ED3B | 2 | GFX_QY | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:18 | midpoint-circle octant state: y (2) |
| $ED3D | 2 | GFX_QD | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:6 | midpoint-circle octant state: d (signed) (2) |
| $ED3F | 2 | GFX_PX | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:10 | tenant scratch: current (mirrored+scaled) offset X, used as the arc cross-product test point P (2) |
| $ED41 | 2 | GFX_PY | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:10 | tenant scratch: current offset Y (2) |
| $ED43 | 2 | GFX_CS_AX | D | PUB | G29 LINE/CIRCLE/POINT graphics state | circleparse.asm:2, graphics.asm:2 | circleparse scratch: cpt_angle_from_arga's neg-flag cell address stash (was gfx_cross_ge0's A.x -- that routin |
| $ED45 | 2 | GFX_CS_AY | D | PUB | G29 LINE/CIRCLE/POINT graphics state | circleparse.asm:3 | circleparse scratch: cpt_angle_from_arga / cpt_boundary_prep's dest-record-base stash (2) |
| $ED47 | 2 | GFX_M | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:7 | D-ARCMASK: M = floor(r/sqrt(2)), the octant's top step index; gfx_circ_wedge_prep, once per CIRCLE (2) |
| $ED49 | 2 | GFX_WS_P | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:4 | wedge START boundary: in-octant position, 0..M-1 (2) |
| $ED4B | 1 | GFX_WS_O | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:4 | wedge START boundary: octant 0..7 (1) |
| $ED4C | 2 | GFX_SOCT | D | PUB | G29 LINE/CIRCLE/POINT graphics state | circleparse.asm:2, graphics.asm:2 | start: trunc(/a0/*4/pi), RAW/unmasked int16 (the full word feeds the full-wrap detector; only the low 3 bits a |
| $ED4E | 2 | GFX_SU14 | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:1 | start: trunc(frac * 16384), 0..16383 (2) |
| $ED50 | 2 | GFX_EOCT | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:2, circleparse.asm:1 | end: trunc(/a1/*4/pi), RAW/unmasked (2) |
| $ED52 | 2 | GFX_EU14 | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:1 | end: trunc(frac * 16384) (2) |
| $ED54 | 1 | GFX_SNEG | D | PUB | G29 LINE/CIRCLE/POINT graphics state | circleparse.asm:2, graphics.asm:2 | resident: start angle was negative -> spoke pending (1) |
| $ED55 | 1 | GFX_ENEG | D | PUB | G29 LINE/CIRCLE/POINT graphics state | circleparse.asm:2, graphics.asm:2 | resident: end angle was negative -> spoke pending (1) |
| $ED56 | ? | GFX_B/GFX_WE_P | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:7, graphics.asm:2 | border colour B, RANGE-CHECKED against the mode's domain before it is stored: 0..255 in SCREEN 2, 0..15 in MUL |
| $ED57 | ? | GFX_CPHASE | D | PUB | G29 LINE/CIRCLE/POINT graphics state | circleparse.asm:7 | CIRCLE-parse co-routine phase (sub/circleparse.asm): which arg the tenant last requested, so it resumes at the |
| $ED58 | 1 | GFX_PTX/GFX_WE_O | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:7, graphics.asm:1 | main->tenant: POINT target X, 0..255 (1) |
| $ED59 | 1 | GFX_PTY/GFX_WRAPF | D | PUB | G29 LINE/CIRCLE/POINT graphics state | graphics.asm:6, graphics.asm:1 | main->tenant: POINT target Y, 0..191 (1) -> ends $E15A |
| $EDC2 | 1 | DIRECTF | C | ELIM | G30a DIRECTF | program.asm:6, arrays.asm:1, cload.asm:1, deffn.asm:1, files.asm:1, interp.asm:1 | 1 = executing a DIRECT-mode line, 0 = running a (1 B) stored program. Read by fre_abort_low to decide the run- |
| $EDC3 | 2 | SAVSTK | C | PUB | G30b SAVSTK | program.asm:5, cload.asm:2, deffn.asm:2, arrays.asm:1, interp.asm:1 | 2 B: SP anchor for the trap unwind. Written by run_prog / dispatch_line's direct-exec path before any statemen |
| $EDCB | 4 | ERRRESUME | C | PUB | G30c ERRRESUME | interp.asm:4, errtrap.asm:2 | 4 B: resume context captured at trap time — [0..1] the erroring statement's CURLINE (link addr), [2..3] the er |
| $EDCF | 2 | SAVTXT | C | PUB | G30d SAVTXT | interp.asm:3, program.asm:1 | 2 B: the CURRENT statement's text pointer, refreshed at every exec_stmt entry (line start AND after every ':'  |
| $EDD1 | 54 | ZTRAP | B | PUB | G30e ZTRAP table | traps.asm:9, program.asm:8, graphics.asm:1, keytrap.asm:1, sprtrap-body.inc:1 | 18 entries * 3 B = 54 B ($EDD1..$EE06; it was $E1D1..$E207 before D-RAMSHIFT, and that stale range let the RAM |
| $EE07 | 2 | ZINTVAL | B | PUB | G30f INTERVAL reload/counter | traps.asm:4, program.asm:1 | 2 B: INTERVAL reload period in frames (0 = disarmed) |
| $EE09 | 2 | ZINTCNT | B | PUB | G30f INTERVAL reload/counter | traps.asm:3, program.asm:1 | 2 B: INTERVAL live down-counter (frames to next fire) |
| $EE0B | 1 | TRAPENA | B | ELIM | G30g TRAPENA/TRAPSVC | traps.asm:8 | 1 B: count of traps currently in state ON. Gates the H.TIMI event_poll (fast-out when 0 — the common no-trap p |
| $EE0C | 1 | TRAPSVC | B | ELIM | G30g TRAPENA/TRAPSVC | traps.asm:3, program.asm:1 | 1 B: count of live SERVICING entries == depth of the service stack. Gates ex_return's re-enable hook (0 = no a |
| $EE0D | ? | SH_BASE/SH_OP | D | PUB | G30h string-engine marshalling SH_* | str-engine.asm:7, expr.asm:3, sysvars.inc:2, vars.asm:1, strheap.asm:1 | the retired TRAPSTK's FREE-RAM run; SH_OP..SH_ERR is exactly 18 B and ends at $E21E, one below TRAPPEND $E21F  |
| $EE0E | 1 | SH_LEN | D | PUB | G30h string-engine marshalling SH_* | strheap.asm:10, str-engine.asm:7, files.asm:1, input.asm:1, sysvars.inc:1 | ALLOC/TEMP_ALLOC/BUILD_CONCAT arg: requested length / operand count (1 B) |
| $EE0F | 2 | SH_SRC | D | PUB | G30h string-engine marshalling SH_* | strheap.asm:28, str-engine.asm:6, input.asm:1, vars.asm:1, sysvars.inc:1 | SNAPSHOT arg: source descriptor address (2 B) |
| $EE11 | 2 | SH_PTR | D | PUB | G30h string-engine marshalling SH_* | strheap.asm:20, str-engine.asm:5, files.asm:1, input.asm:1, sysvars.inc:1 | result: ALLOC's body ptr / GC's new FRETOP / BUILD_CONCAT's & TEMP_ALLOC's & SNAPSHOT's new temp-stack slot (2 |
| $EE13 | 2 | SH_PTR2 | D | PUB | G30h string-engine marshalling SH_* | str-engine.asm:1, sysvars.inc:1, strheap.asm:1 | result: TEMP_ALLOC's body-to-fill address (0 if length 0 or OOM) (2 B) |
| $EE15 | 1 | SH_START | D | PUB | G30h string-engine marshalling SH_* | strheap.asm:5, str-engine.asm:2, sysvars.inc:1 | SLICE (op=5) arg: 0-based start (1 B) |
| $EE16 | 1 | SH_COUNT | D | PUB | G30h string-engine marshalling SH_* | strheap.asm:4, str-engine.asm:1, sysvars.inc:1 | SLICE (op=5) arg: byte count (1 B) |
| $EE17 | 2 | SH_NUM | D | PUB | G30h string-engine marshalling SH_* | strheap.asm:4, str-engine.asm:2, sysvars.inc:1 | HEX_BUILD/OCT_BUILD (op=6/7) arg: the unsigned-16 value to render (2 B) |
| $EE19 | 1 | SH_FILLBYTE | D | PUB | G30h string-engine marshalling SH_* | str-engine.asm:3, sysvars.inc:1, strheap.asm:1 | FILL (op=8) arg: the byte to repeat SH_LEN times (1 B) — covers SPACE$/ STRING$/CHR$'s shared "n copies of one |
| $EE1A | 2 | SH_DEST | D | PUB | G30h string-engine marshalling SH_* | strheap.asm:14, str-engine.asm:5, vars.asm:1, sysvars.inc:1 | MID_STORE (op=9) arg: the MID$- statement destination (A$) descriptor address (2 B) — SH_SRC doubles as the so |
| $EE1C | 2 | SH_P | D | PUB | G30h string-engine marshalling SH_* | str-engine.asm:1, sysvars.inc:1, strheap.asm:1 | INSTR_SEARCH (op=11) arg: p (2 B) |
| $EE1E | 1 | SH_ERR | D | PUB | G30h string-engine marshalling SH_* | strheap.asm:38, str-engine.asm:8, input.asm:1, program.asm:1, vars.asm:1 | result: 0 ok, 1 Out of memory, 2 = temp-descriptor stack full (1 B) Temp-descriptor stack (§6): replaces the o |
| $EE1F | 1 | TRAPPEND | B | PUB | G30i TRAPPEND | traps.asm:3, keytrap.asm:1, program.asm:1, sprtrap-body.inc:1 | 1 B (was just past the retired TRAPSTK): 1 = event_poll has latched a PENDING on some ON trap since the last d |
| $EE20 | 1 | GFX_DJ | D | ELIM | G31a GFX_DJ probe | graphics.asm:3 | JIFFY delta observed while drawing under EI (1) |
| $EE21 | 2 | BL_PTR | A | PUB | G31b BLOAD/SAVE marshalling | bload.asm:1, bload.asm:1 | 2 B: main -> tenant, the token cursor after BLOAD |
| $EE23 | 1 | BL_STAT | A | PUB | G31b BLOAD/SAVE marshalling | bload.asm:4, bload.asm:1, bload-body.inc:1 | 1 B: tenant -> main. 0 = loaded, 1 = `load error` PRINTED, and ANY OTHER VALUE IS THE MSX ERR CODE THE RESIDEN |
| $EE24 | 1 | SV_OP | A | PUB | G31b BLOAD/SAVE marshalling | save.asm:1, save.asm:1 | 1 B: main -> tenant, SV_OP_* engine selector |
| $EE25 | 1 | SV_STAT | A | PUB | G31b BLOAD/SAVE marshalling | save.asm:2, save.asm:1 | 1 B: tenant -> main, 0 = written, 1 = load_error |
| $EE27 | 2 | FN_RESUME | A | PUB | G31c FN_RESUME | field.asm:12, kernel.asm:8, files.asm:7, bload.asm:3, save.asm:3, cload.asm:2 | D-FNEXPR: cursor past a filename expr (2 B) parked by fname_expr while the staged name is parsed out of STRSCR |
| $EE29 | 1 | LOC_COL | D | PUB | G31d LOCATE/SWAP scratch | missing.asm:3 | 1 B: LOCATE's parsed column, pre-clamp |
| $EE2A | 1 | LOC_ROW | D | PUB | G31d LOCATE/SWAP scratch | missing.asm:3 | 1 B: LOCATE's parsed row, pre-clamp |
| $EE2B | 2 | BL_OFS/SVT_SP/SW_ADDR | D | PUB | G31d LOCATE/SWAP scratch | missing.asm:4, bload.asm:2, save.asm:2, sysvars.inc:2, bload-body.inc:1 | 2 B: main -> tenant, BLOAD's offset (0 = none) |
| $EE2D | 1 | SW_TYPE | D | PUB | G31d LOCATE/SWAP scratch | missing.asm:4 | 1 B: its type (1 = string, 2/4/8 numeric) |
| $EE2E | 2 | SW_ADDR1 | D | PUB | G31d LOCATE/SWAP scratch | missing.asm:2 | 2 B: operand 1, held across operand 2's parse |
| $EE30 | 1 | SW_TYPE1 | D | PUB | G31d LOCATE/SWAP scratch | missing.asm:3 | 1 B: operand 1's type |
| $EE31 | 1 | SW_MODE | D | PUB | G31d LOCATE/SWAP scratch | missing.asm:3 | 1 B: 0 = this operand MAY be created, 1 = must exist |
| $EE32 | 2 | POOLSIZE | C | ELIM | G31e POOLSIZE | clear.asm:7, interp.asm:1, strheap.asm:1 | 2 B: the size CLEAR recorded. Written ONLY by `CLEAR <n>`; initialised to 200 at cold boot and deliberately NO |
| $EE34 | 2 | PLN_NUM | D | PUB | G31f line-number parse | program.asm:1, lineno.asm:1 | 2 B: the parsed line number (BC), $FFFF if the BC*10+digit chain carried (pl_sat's saturation -- dl_store's ce |
| $EE36 | 2 | PLN_PTR | D | PUB | G31f line-number parse | program.asm:1, lineno.asm:1 | 2 B: LINEBUF pointer at the body (HL) FREE-RAM $EE3E..$EE40 below STRTAB/VAREND, which begin at $E240 [D-RAMSH |
| $EE38 | 2 | DB_SKIP | D | ELIM | G31g LIST window resume | detok.asm:3, list.asm:1 | rendered bytes still to discard (2 B; TEMPTOP's old cell) |
| $EE3A | 1 | DB_MORE | D | ELIM | G31g LIST window resume | detok.asm:3, list.asm:1, printusing.asm:1, printusing.asm:1 | 1 = the render ran past the window (1 B) 🔁 RESUMPTION (D-DETOKBUF S1, second cut): re-rendering a whole line p |
| $EE3B | 2 | DB_RESSKIP | D | ELIM | G31g LIST window resume | list.asm:1, detok.asm:1 | resume: bytes of the resume token already drained (2 B) |
| $EE3D | 1 | DB_RESUME | D | ELIM | G31g LIST window resume | detok.asm:3, list.asm:1 | 1 = this render may abort + resume (detok only) (1 B) |
| $EE68 | 2 | FRETOP | C | PUB | G32a FRETOP | strheap.asm:14, print.asm:2, arrays.asm:2, printusing.asm:1, str-engine.asm:1 | heap low boundary; heap occupies (2 B) [FRETOP,C), grows DOWN as strings alloc. Reset to the ceiling C at cold |
| $EE6A | 2 | TXTCEIL | C | ELIM | G32b TXTCEIL | cload.asm:2, interp.asm:2, str-engine.asm:2, strheap.asm:2 | the text ceiling boot chose: TXTMAX or TXTMAX_NODISK (2 B) 🏛️ D-CASFCB (2026-10-13): the cassette buffer is th |
| $EE6C | 3 | RVDESC | D | PUB | G32c RVDESC | str-engine.asm:4, fldlook.asm:3, vars.asm:2 | [len:1][ptr:2] scratch descriptor (3 B) for a value whose body is NOT in the heap (a token-stream literal / ST |
| $EE6F | 2 | CAS_BUFP | A | PUB | G32d CAS_BUFP | save.asm:2, bload.asm:2, cload.asm:1, cal-refill-body.inc:1, casmatch-body.inc:1, casmatch.asm:1 | base of the tape buffer in use (2 B) 🪟 D-DETOKBUF S1 (docs/spec-detokbuf-drop.md, Joost 2026-09-25 "Drop DETOK |
| $EF64 | 96 | FLD_TAB | C | FLOOR | G33 FIELD table | field.asm:4, sysvars.inc:1, arrays.asm:1 | field table base ($EF64..$EFC3, 96 bytes) |
| $EFC4 | 2 | FLD_TABEND/GP_RECNO | D | FLOOR | G34 GET/PUT scratch (disk) | field.asm:6, randio-body.inc:5 | $EFC4 |
| $EFC6 | 2 | GP_SEC | D | FLOOR | G34 GET/PUT scratch (disk) | randio-body.inc:7 | file logical-sector index of the record (2) |
| $EFC8 | 2 | GP_WITHIN | D | FLOOR | G34 GET/PUT scratch (disk) | randio-body.inc:6 | byte offset of the record within its sector (0/256, 2) (2 B) |
| $EFCA | 2 | GP_CLUS | D | FLOOR | G34 GET/PUT scratch (disk) | randio-body.inc:5 | current cluster during the chain walk (2) |
| $EFCC | 2 | GP_CLIDX | D | FLOOR | G34 GET/PUT scratch (disk) | randio-body.inc:4 | cluster steps still to walk (2) |
| $EFCE | 1 | GP_SECINCL | D | FLOOR | G34 GET/PUT scratch (disk) | randio-body.inc:2 | sector index within the final cluster (1) |
| $EFCF | 2 | GP_PHYS | D | FLOOR | G34 GET/PUT scratch (disk) | randio-body.inc:4 | resolved absolute physical sector (2) |
| $EFD1 | 2 | GP_OLDNSEC | D | FLOOR | G34 GET/PUT scratch (disk) | randio-body.inc:2 | file's old sector count (ceil(size/512), 2) (2 B) |
| $EFD3 | 1 | GP_FLAGS | D | FLOOR | G34 GET/PUT scratch (disk) | randio-body.inc:4 | bit0 = extend (PUT allocates; GET does not) (1) |
| $EFD4 | 1 | GP_MODE | D | FLOOR | G34 GET/PUT scratch (disk) | field.asm:2 | 0 = GET (read), 1 = PUT (write) (1) |
| $EFD5 | 1 | GP_CHAN | D | FLOOR | G34 GET/PUT scratch (disk) | field.asm:4, randio-body.inc:1 | the channel number being GET/PUT (1) |
| $EFD6 | 2 | PU_FMTD | D | SHARE | G35a PRINT USING format cells | printusing.asm:2, printusing.asm:1 | -> the format's [len][ptr] descriptor (2) |
| $EFD8 | 3 | PU_FDESC | D | SHARE | G35a PRINT USING format cells | printusing.asm:2 | [len][ptr] copy for a format that cannot move (3) FREE-RAM $EFDB..$EFF5 PU_FMT's tail, given up by D-PULONG (2 |
| $EFF6 | 1 | PU_FMTLEN | D | SHARE | G35a PRINT USING format cells | pu-render.inc:13, printusing.asm:2 | live format length (1) |
| $EFF7 | 1 | PU_POS | D | SHARE | G35a PRINT USING format cells | pu-render.inc:30, printusing.asm:1 | current scan index into the format (1) |
| $EFF8 | 1 | PU_W | D | SHARE | G35a PRINT USING format cells | pu-render.inc:3, printusing.asm:1, printusing.asm:1, punum.asm:1 | current field width (1) |
| $EFF9 | 1 | PU_TYPE | D | SHARE | G35a PRINT USING format cells | pu-render.inc:9, printusing.asm:2, printusing.asm:2 | field type: 0 num #, 1 str &, 2 str !, 3 str \..\ (1) BIT2 = D-PUDOLLAR's floating `$`, a MODIFIER on the nume |
| $EFFA | 1 | PU_FLAGS | D | SHARE | G35a PRINT USING format cells | pu-render.inc:21, printusing.asm:8, punum.asm:5, printusing.asm:3 | bit0 = trailing separator (suppress NL); bit1 = wrapped (1) |
| $EFFB | 1 | PU_COMMAS/PU_WP | D | SHARE | G35a PRINT USING format cells | punum.asm:9, printusing.asm:2 | PRINT USING `,`: commas to insert (D-PUCOMMA) (1) |
| $EFFC | 1 | PU_DEC | D | SHARE | G35a PRINT USING format cells | pu-render.inc:9, punum.asm:5 | PRINT USING `.`: decimal places requested (D-PUDOT) (1) CALL FORMAT loop counter — the current sector being wr |
| $EFFD | 1 | FMT_SEC | D | FLOOR | G35b CALL FORMAT (disk) | format-body.inc:9 | CALL FORMAT: current sector index being written (1) |
| $EFFE | 2 | FMT_DESC | D | FLOOR | G35b CALL FORMAT (disk) | format-body.inc:4 | CALL FORMAT: chosen geometry descriptor pointer (2) |
| $F006 | 2 | GP_RECLEN | D | FLOOR | G35c OPEN/FILES/GET scratch (disk) | randio-body.inc:4 | active channel's record length (word), loaded per calc |
| $F008 | 1 | OO_RECLEN_CHAN | D | FLOOR | G35c OPEN/FILES/GET scratch (disk) | files.asm:3, randio-body.inc:1 | OPEN scratch: channel # stashed across the LEN= eval (1) |
| $F009 | 1 | FILES_HASPAT | D | FLOOR | G35c OPEN/FILES/GET scratch (disk) | kernel.asm:3 | FILES: 1 = a filespec pattern is in DISK_FCB_NAME (1) |
| $F00A | 6 | CAS_WANT | A | PUB | G36 cassette name search / CLOAD? state | files.asm:1, cascap-body.inc:1, casmatch-body.inc:1 | requested 6-char tape name, space-padded (6) |
| $F010 | 1 | CAS_WANT_ON | A | PUB | G36 cassette name search / CLOAD? state | cload.asm:2, casmatch-body.inc:2, bload-body.inc:1, cascap-body.inc:1 | bit 0: 1 = match CAS_WANT, 0 = next file (bare form); bit 7: CLOAD = want $D3; bit 6: BLOAD = $D0 (D-CASBIN);  |
| $F011 | 6 | CAS_HDRNAME | A | PUB | G36 cassette name search / CLOAD? state | casmatch-body.inc:3 | 6-char name read from the current tape header (6) |
| $F017 | 1 | CAS_HDRID | A | PUB | G36 cassette name search / CLOAD? state | casmatch-body.inc:3, files.asm:2, cload.asm:1 | file-type id byte read from the current header (1) |
| $F018 | 1 | CAS_VERIFY | A | PUB | G36 cassette name search / CLOAD? state | cload.asm:8 | 1 = CLOAD? compare-mode (no store) (1) |
| $F019 | 1 | CAS_VMIS | A | PUB | G36 cassette name search / CLOAD? state | cload.asm:3 | sticky: 1 = a verify mismatch was seen (1) |
| $F01A | 1 | FACTYP | D | PUB | G37a FACTYP | expr.asm:6, float-arith.asm:5, program.asm:3, vars.asm:3, kernel.asm:3, arrays.asm:2 | 2=int / 4=single / 8=double (1) TKOVF: the tokeniser's crunch-time reject -- 0 = ok, else the ERR CODE (6 a fl |
| $F01B | 1 | TKOVF | D | PUB | G37b TKOVF | program.asm:3, tokenise.inc:3, strheap.asm:3, tkfloat.asm:1 | tokeniser reject code, 0 = ok (1 B) 🏗️ D-ADDR29 DAC, the FAC half (2026-09-25): FAC IS the published DAC. The  |
| $F01C | 2 | DB_SP | D | ELIM | G37c LIST resume cells | detok.asm:2 | the render's SP to abort to (2 B; FAC's old cell) |
| $F01E | 2 | DT_TOK | D | ELIM | G37c LIST resume cells | detok.inc:1, detok.asm:1 | detok: the current token's start in the line (2 B) |
| $F020 | 2 | DT_TOKN | D | ELIM | G37c LIST resume cells | detok.asm:3, detok.inc:2 | detok: bytes the current token has emitted (2 B) |
| $F022 | 2 | DB_RESPTR | D | ELIM | G37c LIST resume cells | list.asm:1, detok.asm:1 | resume: the token to restart at (2 B) |
| $F024 | 2 | PLY_XSP | D | PUB | G37d PLAY X saved SP | playparse.asm:3 | PLAY X: saved SP at pt_voice's call (2) D-OKSTORE (2026-09-24, scratchpad/okstore_probe.py): does a prompt fol |
| $F026 | 1 | PRMWANT | D | ELIM | G37e PRMWANT | program.asm:2, repl.asm:2 | D-OKSTORE: nonzero = print the prompt (1) |
| $F027 | 1 | STOPHOLD | B | PUB | G37f STOPHOLD | traps.asm:2 | D-STOPTAP: frames Ctrl-STOP has been held (1) |
| $F03C | 24 | TKDIG | D | PUB | G38 float-literal scan + formatter scratch | tkfloat.asm:9, detok.inc:4 | tokeniser/formatter: significant-digit array, $F03C..$F053 one decimal digit value (0-9) per byte (24) tk_floa |
| $F054 | 1 | TKPOS | D | PUB | G38 float-literal scan + formatter scratch | tkfloat.asm:5 | running digit-position counter (1) |
| $F055 | 1 | TKINTLEN | D | PUB | G38 float-literal scan + formatter scratch | tkfloat.asm:4 | integer-part digit count = P (1) |
| $F056 | 1 | TKHAVESIG | D | PUB | G38 float-literal scan + formatter scratch | tkfloat.asm:4 | 1 once the first nonzero digit is seen (1) |
| $F057 | 1 | TKNZPOS | D | PUB | G38 float-literal scan + formatter scratch | tkfloat.asm:4 | position of the first nonzero digit = f (1) |
| $F058 | 1 | TKDCOUNT | D | PUB | G38 float-literal scan + formatter scratch | tkfloat.asm:11 | classification digit count = D, saturating (1) |
| $F059 | 1 | TKSTORED | D | PUB | G38 float-literal scan + formatter scratch | tkfloat.asm:3 | digits actually written to TKDIG, capped 24 (1) |
| $F05A | 1 | TKFLAGS | D | PUB | G38 float-literal scan + formatter scratch | tkfloat.asm:13 | bit0=dot bit1=exp bit2=expD bit3=! bit4=# bit5=% (1) |
| $F05B | 2 | TKEXP | D | PUB | G38 float-literal scan + formatter scratch | tkfloat.asm:4 | signed explicit exponent, saturated +-9999 (2) |
| $F05D | 1 | TKEXPD | D | PUB | G38 float-literal scan + formatter scratch | tkfloat.asm:3 | 1 = the exponent marker being parsed is D/d (1) |
| $F05E | 1 | TKEXPSIGN | D | PUB | G38 float-literal scan + formatter scratch | tkfloat.asm:3 | 1 = the exponent being parsed is negative (1) |
| $F05F | 1 | TKPC | D | PUB | G38 float-literal scan + formatter scratch | tkfloat.asm:8 | target precision digit count: 6 / 14 (1) |
| $F060 | 2 | TKDEXP | D | PUB | G38 float-literal scan + formatter scratch | tkfloat.asm:4 | signed dec_exp, pre-/post-round (2) |
| $F062 | 1 | TKLEAD | D | PUB | G38 float-literal scan + formatter scratch | tkfloat.asm:4 | computed lead byte (sign+excess-64 exponent) (1) flt_out formatter scratch (own choice — free RAM; transient,  |
| $F063 | 1 | FOSIGN | D | PUB | G38 float-literal scan + formatter scratch |  | UNUSED since C8 -- the sign is ARGA+FPNUM_SIGN now, so the cell is reclaimable. It held 0 / $80, the value's s |
| $F064 | ? | FOSIGCOUNT/TKVALEND | D | PUB | G38 float-literal scan + formatter scratch | float.asm:7, tkfloat.asm:3, tokenise.inc:2, input.asm:1, strheap.asm:1 | significant digit count = s, trailing zeros stripped (1) |
| $F065 | 1 | FOMBYTES | D | PUB | G38 float-literal scan + formatter scratch |  | (1 B) UNUSED since C8 -- widen_fac_to reads FACTYP itself. It also sits on TKVALEND's high half. It held the m |
| $F067 | 2 | TKSRCSAVE | D | PUB | G38 float-literal scan + formatter scratch | tkfloat.asm:4 | (2) |
| $F069 | 1 | FPERR | D | PUB | G38 float-literal scan + formatter scratch | interp.asm:6, fp_pow.asm:3, kernel.asm:3, expr.asm:2, str-engine.asm:2, bload.asm:2 | runtime numeric-error flag: 0 none / 1 overflow / (1 B) 2 division by zero (spec §10.2 D-F2-1) / 3 illegal fun |
| $F06A | 18 | ARGA | D | PUB | G39 float operand records + product | float-arith.asm:57, fp_sqrt.asm:24, fp_sin.asm:16, float.asm:14, circleparse.asm:11, fp_exp.asm:11 | operand A / working result, FPNUM record (18) |
| $F07C | 18 | ARGB | D | PUB | G39 float operand records + product | float-arith.asm:35, fp_sqrt.asm:21, circleparse.asm:5, fp_atan.asm:2, fp_pow.asm:2, fp_sin.asm:2 | operand B, FPNUM record (18) |
| $F08E | ? | MULPROD/RND_ACCLE | D | PUB | G39 float operand records + product | sysvars.inc:7, float-arith.asm:5, fp_rnd.asm:4 | fp_mul: 28-digit product (14x14), MSD first (28) |
| $F09C | 1 | RND_I | D | PUB | G39 float operand records + product | fp_rnd.asm:10 | multiply-add loop: S/acc digit index i (0..13), the SAME MULPROD cell's own spare second half (1) |
| $F09D | 1 | RND_J | D | PUB | G39 float operand records + product | fp_rnd.asm:5 | multiply-add loop: A's digit index j (0..13) (1) |
| $F09E | 1 | RND_IJ | D | PUB | G39 float operand records + product | fp_rnd.asm:2 | multiply-add loop: i+j, the target accumulator index for the current (i,j) pair (1) |
| $F09F | 1 | RND_AJ | D | PUB | G39 float operand records + product | fp_rnd.asm:2 | multiply-add loop: A_LE[j], stashed across the inner i-loop (1) |
| $F0A0 | 1 | RND_CARRY | D | PUB | G39 float operand records + product | fp_rnd.asm:6 | multiply-add loop: running BCD carry, shared by both the multiply phase (per outer j pass) and the final +C ri |
| $F0A1 | 1 | RND_K | D | PUB | G39 float operand records + product | fp_rnd.asm:6 | output normalisation: count of leading zero digits in the post-advance state (0..14 -- 14 means S=0, the astro |
| $F0AA | 15 | DIVPAD | D | PUB | G40a float division/convert/combine scratch | float-arith.asm:5 | fp_div: divisor zero-padded to 15 digits (15) |
| $F0B9 | 15 | DIVREM | D | PUB | G40a float division/convert/combine scratch | float-arith.asm:6 | fp_div: running remainder, 15 digits (15) |
| $F0C8 | 18 | CVT | D | PUB | G40a float division/convert/combine scratch | float-arith.asm:9 | fac_to_int_strict/addr + flt_to_int16 (float.asm) shared unpack scratch, FPNUM-shaped (18) |
| $F0DA | 1 | LHS_FACTYP | D | PUB | G40a float division/convert/combine scratch | float-arith.asm:3 | ev_e/ev_t binary-op sites: the LHS operand's FACTYP, popped off the machine-stack frame (spec §1 bullet 4: "fi |
| $F0DB | 8 | LHS_FAC | D | PUB | G40a float division/convert/combine scratch | float-arith.asm:5 | ...and the LHS operand's raw FAC bytes (8) Small general scratch cells, own choice — free RAM, grouped so each |
| $F0E3 | 1 | FP_SHIFTAMT | D | PUB | G40a float division/convert/combine scratch | float-arith.asm:9 | dig15_shr/dig15_shl: shift-amount parameter (1) |
| $F0E4 | 2 | FP_LHSVAL | D | PUB | G40a float division/convert/combine scratch | float-arith.asm:11 | combine_*: the LHS operand's plain int16 value, stashed off the machine stack (2) |
| $F0E6 | 2 | FP_TMP_B | D | PUB | G40a float division/convert/combine scratch | float-arith.asm:16 | combine_*: the RHS operand's plain int16 value, stashed so it survives a widen_* call (2) |
| $F0E8 | 1 | FP_RSIGN | D | PUB | G40a float division/convert/combine scratch | float-arith.asm:11 | signed_div_de_bc/signed_mod_de_bc: result sign (1) |
| $F0E9 | ? | KEYARG/WIDIG | D | PUB | G40b KEY op / widen digit | screen.asm:3, interp.asm:2, float-arith.asm:2, subromcall.asm:1, keystr.asm:1 | D-KEYSTR: main -> keystr_tenant op/slot (0 = defaults, 1..10 = store, 255 = LIST). ALIASES WIDIG below: that i |
| $F0EE | 1 | MUL_I | D | PUB | G40c multiply / widen / convert scratch | float-arith.asm:8 | fp_mul: outer-loop digit index i, 13 downto 0; widen_int_to: digit count N, 0..5 (shared, dead between uses) ( |
| $F0EF | 1 | MUL_ADIG | D | PUB | G40c multiply / widen / convert scratch | float-arith.asm:2 | fp_mul: A[i], the current outer-loop digit (1) |
| $F0F0 | 1 | MUL_CARRY | D | PUB | G40c multiply / widen / convert scratch | float-arith.asm:7 | fp_mul: running carry within one outer pass; fp_div's fpd_trial_digit: trial-subtract count (shared, dead betw |
| $F0F1 | 2 | MUL_PP | D | PUB | G40c multiply / widen / convert scratch | float-arith.asm:4 | fp_mul: MULPROD write-cursor for the inner loop (2) |
| $F0F3 | 2 | MULCAND | D | PUB | G40c multiply / widen / convert scratch | float-arith.asm:2 | mul16x16_32: multiplicand operand (2) |
| $F0F5 | 2 | MULTPLR | D | PUB | G40c multiply / widen / convert scratch | float-arith.asm:3 | mul16x16_32: multiplier operand, shifted in place (2) |
| $F0F7 | 4 | MUL32 | D | PUB | G40c multiply / widen / convert scratch | float-arith.asm:12 | mul16x16_32: 32-bit unsigned product, LE (low16 then high16) (4) |
| $F0FB | 2 | WSRC | D | PUB | G40c multiply / widen / convert scratch | float-arith.asm:3 | widen_fac_to/widen_lhsframe_to (shared unpack body): address of the source's lead+mantissa bytes, FAC or LHS_F |
| $F0FD | 2 | WSRC_TYP | D | PUB | G40c multiply / widen / convert scratch | float-arith.asm:4 | ...and the address of its type byte, FACTYP or LHS_FACTYP (2) |
| $F0FF | 1 | FP_OPMODE | D | PUB | G40c multiply / widen / convert scratch | float-arith.asm:3 | combine_add/combine_sub shared body: 0=add, 1=sub (1) |
| $F100 | ? | CVT_MODE | D | PUB | G40c multiply / widen / convert scratch | float-arith.asm:2, float.asm:1 | domain_convert_core: 0=strict int16 domain, 1=address domain (1) |
| $F101 | 2 | PLF_RA | D | PUB | G40c multiply / widen / convert scratch | float-arith.asm:2 | pop_lhs_and_probe: scratch home for its own "call"-pushed return address (2) |
| $F103 | 2 | PLF_RA2 | D | PUB | G40c multiply / widen / convert scratch | float-arith.asm:2 | ...and for its DIRECT caller's (combine_add/ (2 B) sub/mul/cmp/div_float's own) "call"-pushed return address,  |
| $F105 | 1 | SUB_PING | C | PUB | G41a SUB_PING/SUBSLOT/SUBSLOT_OK | sub.asm:2, sub2.asm:2 | PING page tag: $C0 (page 0) / $C1 (page 1) (1 B) |
| $F106 | 1 | SUBSLOT | C | PUB | G41a SUB_PING/SUBSLOT/SUBSLOT_OK | subrom-boot.asm:1, subromcall.asm:1, grpprt.asm:1 | slot id of zerobas-sub (bit7 exp / 3-2 / 3), 1 (1 B) |
| $F107 | 1 | SUBSLOT_OK | C | PUB | G41a SUB_PING/SUBSLOT/SUBSLOT_OK | subrom-boot.asm:2, interp.asm:1, islands.asm:1, str-engine.asm:1, subromcall.asm:1 | 1 = a CD sub-ROM was found and recorded, else 0 (1 B) |
| $F108 | 2 | DB_CUR | D | ELIM | G41b DB_CUR | detok.asm:4, printusing.asm:4, keystr.asm:1 | wave-3 detok: the DETOKBUF write cursor, held across (2 B) the whole sub-side walk (the core clobbers DE/HL, s |
| $F10A | 64 | SUB_INT_RAM | B | ELIM | G42a SUB_INT_RAM trampoline | subrom-boot.asm:1, subromcall.asm:1, sub.asm:1, sub2.asm:1 | the copied trampoline stub (<= 64 B; executes from RAM) |
| $F14A | 1 | INT_MAIN_PRIM | B | PUB | G42b INT_MAIN_PRIM/SUBSLOT2 | subromcall.asm:2, subrom-boot.asm:1 | page-0 primary field of the MAIN (BIOS) slot (=0) (1 B) $F14B-$F14C were INT_SUB_PRIM / INT_SUB_SUBSL until D- |
| $F14B | 1 | SUBSLOT2 | B | PUB | G42b INT_MAIN_PRIM/SUBSLOT2 | islands.asm:1, subrom-boot.asm:1, subromcall.asm:1 | slot id of zerobas-sub2 ("Z2", 3-3: $8F); 0 = absent. Cleared by init_ext_roms before the scan (RAM survives a |
| $F14C | 1 | GRP_HDR | D | PUB | G42c GRP_HDR/SUB_INT_DELTA | grpdev.asm:1, grpprt.asm:1 | D-OPENGRP: bit 0 = a CHR$(1) header is pending on the GRP: channel (the next byte draws glyph byte-64). Cleare |
| $F14D | 1 | SUB_INT_DELTA | D | PUB | G42c GRP_HDR/SUB_INT_DELTA | sub.asm:1 | self-test tenant result: JIFFY ticks observed under EI (1) |
| $F14E | 1 | VARTYPE | D | PUB | G43 variable-type scratch | arrays.asm:5, vars.asm:4, expr.asm:2, deffn.asm:1, interp.asm:1, missing.asm:1 | var_name_key: the RESOLVED type (2/4/8) of the just-parsed name's suffix (unsuffixed -> 8, hardcoded double in |
| $F14F | 1 | VS_TARGET_TYPE | D | PUB | G43 variable-type scratch | vars.asm:3, arrays.asm:2 | var_store_fac/var_alloc_or_find (vars.asm): the target type parameter, stashed across the coercion calls that  |
| $F150 | 2 | VS_INT_VAL | D | PUB | G43 variable-type scratch | arrays.asm:2, vars.asm:1 | var_store_fac (vars.asm): the coerced int16 value (fac_to_int_strict's DE), stashed across the var_alloc_or_fi |
| $F152 | 1 | LHS_VARTYPE | D | PUB | G43 variable-type scratch | interp.asm:2 | ex_let (interp.asm): the LHS variable's resolved type, latched from (VARTYPE) BEFORE eval -- every RHS variabl |
| $F16D | 1 | MC_TYPE | D | PUB | G44 transcendental/SQR/RND scratch | expr.asm:2 | evmc_sub1 (expr.asm): the operand's FACTYP (4/8), stashed across fp_sub's forced-double round_and_finalize so  |
| $F16E | ? | HORNER_G/MATH_T/RND_LE/SQRT_X | D | PUB | G44 transcendental/SQR/RND scratch | sysvars.inc:3, fp_sqrt.asm:3, fp_exp.asm:2, fp_log.asm:2, fp_rnd.asm:2 | fp_poly_horner's "g" input cell (an alias of MATH_T -- fp_atan's reduction scratch is retired by the time it c |
| $F180 | ? | MATH_A/RND_STATE/SQRT_Y | D | PUB | G44 transcendental/SQR/RND scratch | fp_sqrt.asm:9, fp_rnd.asm:5, fp_log.asm:3, fp_sin.asm:3, sysvars.inc:2, fp_exp.asm:2 | fp_atan's persistent reduced-argument "a" -- set by the sign-fold/reduction steps, held canonical across the w |
| $F192 | 2 | MATH_N/MATH_SIGN/SQRT_K | D | PUB | G44 transcendental/SQR/RND scratch | fp_exp.asm:7, fp_log.asm:7, fp_sqrt.asm:6, fp_sin.asm:4, fp_pow.asm:3, fp_atan.asm:2 | fp_exp's n8 (steps 2-4)/n (steps 4-8) or fp_log's e' (whole routine) -- SIGNED int16, 2 bytes spanning SQRT_K+ |
| $F193 | 1 | MATH_RECIP/SQRT_ITER | D | PUB | G44 transcendental/SQR/RND scratch | fp_sqrt.asm:7, fp_atan.asm:3, sysvars.inc:1 | fp_atan's reduction-1 flag (1 = "a:=1/a" was applied, so the reconstruction needs PI_2-r); alias of SQR's Hero |
| $F194 | 1 | MATH_BREAK/MATH_J/SQRT_POW10 | D | PUB | G44 transcendental/SQR/RND scratch | fp_sin.asm:7, fp_exp.asm:6, fp_log.asm:6, fp_sqrt.asm:4, fp_atan.asm:3, float-arith.asm:2 | fp_atan's reduction-2 flag (1 = the a>BREAK substitution was applied, so the reconstruction needs r+PI_6); ali |
| $F200 | ? | FN_STK_FLOOR | - | - | FN_STK_FLOOR: NOT-A-CELL constant |  |  |
| $F351 | 2 | DSKBUF_PTR | X | KEEP | G46 DSKBUF_PTR (disk ROM cell, measured on the CF-3300) | dirverb.asm:1, kernel.asm:1 | word -> the DSKI$/DSKO$ sector buffer (2) |
