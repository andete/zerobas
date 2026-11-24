# zerobas RAM cells in $C000-$F37F, classified for the reference memory model (D-NMSHOST, 2026-11-24)

Read-only inventory (basic/*.inc|asm, disk/*.inc|asm equ definitions, tools/ram_map.py). Classes: A = has an MS-BASIC
published equivalent at $F380+ (merge); B = BASIC's dynamic layout below HIMEM; C = disk-only state (belongs in the disk
ROM's own HIMEM claim); D = boot-only scratch; E = not a cell (code label / constant / alias / dead). Totals: A 3, B 14,
C 155 (incl. 18 published MSX-DOS cells at $F1C9-$F37F that only need claiming), D 9, E 45 of 226 rows. No basic cell
lives in $C000-$DFFF; plain BASIC state is already at $F380 and above -- below $F380 it is almost all DISK-ONLY.

| name | address | width | marker | component | class | reasoning |
|---|---|---|---|---|---|---|
| BOOT_LOAD | $C000 | ? | - | disk / disk | **E** | MSX standard boot-sector load address/entry (the reference loads there too), a constant not a cell |
| BOOT_ENTRY | $C01E | ? | - | disk / disk | **E** | MSX standard boot-sector load address/entry (the reference loads there too), a constant not a cell |
| GETWRK_AREA | $DD0E | 128 | - | disk / disk | **C** | 128-B MSX-DOS work area returned by $4030, the stock $DD0E; must lie inside the disk ROM's claim ⚠️ (pinned by MSXDOS kernel placement) |
| INT_H_HIRAM | $DDAE | ? | - | disk / disk | **E** | RAM-resident CODE label (DOS-path slot bridge, LDIR'd by install_dos_env), not a variable; the block must sit inside the disk ROM's claimed RAM -- today $DDAE..$DF92 straddles DISK_HIMEM $DE77 |
| BR_MAININ | $DDC5 | ? | - | disk / disk | **E** | RAM-resident CODE label (DOS-path slot bridge, LDIR'd by install_dos_env), not a variable; the block must sit inside the disk ROM's claimed RAM -- today $DDAE..$DF92 straddles DISK_HIMEM $DE77 |
| BR_P0IN | $DDC9 | ? | - | disk / disk | **E** | RAM-resident CODE label (DOS-path slot bridge, LDIR'd by install_dos_env), not a variable; the block must sit inside the disk ROM's claimed RAM -- today $DDAE..$DF92 straddles DISK_HIMEM $DE77 |
| BR_BACK | $DE0D | ? | - | disk / disk | **E** | RAM-resident CODE label (DOS-path slot bridge, LDIR'd by install_dos_env), not a variable; the block must sit inside the disk ROM's claimed RAM -- today $DDAE..$DF92 straddles DISK_HIMEM $DE77 |
| BR_BACK_DI | $DE45 | ? | - | disk / disk | **E** | RAM-resident CODE label (DOS-path slot bridge, LDIR'd by install_dos_env), not a variable; the block must sit inside the disk ROM's claimed RAM -- today $DDAE..$DF92 straddles DISK_HIMEM $DE77 |
| BR1_RAM | $DE48 | ? | - | disk / disk | **E** | RAM-resident CODE label (DOS-path slot bridge, LDIR'd by install_dos_env), not a variable; the block must sit inside the disk ROM's claimed RAM -- today $DDAE..$DF92 straddles DISK_HIMEM $DE77 |
| BR_RDSLT | $DE48 | ? | - | disk / disk | **E** | RAM-resident CODE label (DOS-path slot bridge, LDIR'd by install_dos_env), not a variable; the block must sit inside the disk ROM's claimed RAM -- today $DDAE..$DF92 straddles DISK_HIMEM $DE77 |
| BR_WRSLT | $DE4F | ? | - | disk / disk | **E** | RAM-resident CODE label (DOS-path slot bridge, LDIR'd by install_dos_env), not a variable; the block must sit inside the disk ROM's claimed RAM -- today $DDAE..$DF92 straddles DISK_HIMEM $DE77 |
| BR_CALSLT | $DE56 | ? | - | disk / disk | **E** | RAM-resident CODE label (DOS-path slot bridge, LDIR'd by install_dos_env), not a variable; the block must sit inside the disk ROM's claimed RAM -- today $DDAE..$DF92 straddles DISK_HIMEM $DE77 |
| BR_ENASLT | $DE59 | ? | - | disk / disk | **E** | RAM-resident CODE label (DOS-path slot bridge, LDIR'd by install_dos_env), not a variable; the block must sit inside the disk ROM's claimed RAM -- today $DDAE..$DF92 straddles DISK_HIMEM $DE77 |
| BR2_RAM | $DE74 | ? | - | disk / disk | **E** | RAM-resident CODE label (DOS-path slot bridge, LDIR'd by install_dos_env), not a variable; the block must sit inside the disk ROM's claimed RAM -- today $DDAE..$DF92 straddles DISK_HIMEM $DE77 |
| BR_CALLF | $DE74 | ? | - | disk / disk | **E** | RAM-resident CODE label (DOS-path slot bridge, LDIR'd by install_dos_env), not a variable; the block must sit inside the disk ROM's claimed RAM -- today $DDAE..$DF92 straddles DISK_HIMEM $DE77 |
| DISK_HIMEM | $DE77 | ? | - | disk / disk | **E** | a HIMEM value (CF-3300's), not a cell; becomes the RESULT of the claim |
| WA_SEG | $DEB2 | ? | - | disk / disk | **E** | RAM-resident CODE label (DOS-path slot bridge, LDIR'd by install_dos_env), not a variable; the block must sit inside the disk ROM's claimed RAM -- today $DDAE..$DF92 straddles DISK_HIMEM $DE77 |
| WA_SEG_ROM | $DEB2 | ? | - | disk / disk | **E** | RAM-resident CODE label (DOS-path slot bridge, LDIR'd by install_dos_env), not a variable; the block must sit inside the disk ROM's claimed RAM -- today $DDAE..$DF92 straddles DISK_HIMEM $DE77 |
| WA_SEG_RAM | $DEB8 | ? | - | disk / disk | **E** | RAM-resident CODE label (DOS-path slot bridge, LDIR'd by install_dos_env), not a variable; the block must sit inside the disk ROM's claimed RAM -- today $DDAE..$DF92 straddles DISK_HIMEM $DE77 |
| BR3_RAM | $DECD | ? | - | disk / disk | **E** | RAM-resident CODE label (DOS-path slot bridge, LDIR'd by install_dos_env), not a variable; the block must sit inside the disk ROM's claimed RAM -- today $DDAE..$DF92 straddles DISK_HIMEM $DE77 |
| BR_BDOS | $DECD | ? | - | disk / disk | **E** | RAM-resident CODE label (DOS-path slot bridge, LDIR'd by install_dos_env), not a variable; the block must sit inside the disk ROM's claimed RAM -- today $DDAE..$DF92 straddles DISK_HIMEM $DE77 |
| BR_P1SV | $DEE7 | ? | - | disk / disk | **C** | operand/data byte inside the DOS-path bridge block (label-derived); moves with that block into the disk ROM's claim |
| BR5_RAM | $DEE8 | ? | - | disk / disk | **E** | RAM-resident CODE label (DOS-path slot bridge, LDIR'd by install_dos_env), not a variable; the block must sit inside the disk ROM's claimed RAM -- today $DDAE..$DF92 straddles DISK_HIMEM $DE77 |
| BR_GO | $DEE8 | ? | - | disk / disk | **E** | RAM-resident CODE label (DOS-path slot bridge, LDIR'd by install_dos_env), not a variable; the block must sit inside the disk ROM's claimed RAM -- today $DDAE..$DF92 straddles DISK_HIMEM $DE77 |
| BR_FRAME | $DEEE | ? | - | disk / disk | **E** | RAM-resident CODE label (DOS-path slot bridge, LDIR'd by install_dos_env), not a variable; the block must sit inside the disk ROM's claimed RAM -- today $DDAE..$DF92 straddles DISK_HIMEM $DE77 |
| BR_TGT | $DF11 | ? | - | disk / disk | **C** | operand/data byte inside the DOS-path bridge block (label-derived); moves with that block into the disk ROM's claim |
| BR_FRM | $DF13 | ? | - | disk / disk | **C** | operand/data byte inside the DOS-path bridge block (label-derived); moves with that block into the disk ROM's claim |
| BR_HL | $DF15 | ? | - | disk / disk | **C** | operand/data byte inside the DOS-path bridge block (label-derived); moves with that block into the disk ROM's claim |
| BR_CFOP | $DF17 | ? | - | disk / disk | **C** | operand/data byte inside the DOS-path bridge block (label-derived); moves with that block into the disk ROM's claim |
| BR6_RAM | $DF1D | ? | - | disk / disk | **E** | RAM-resident CODE label (DOS-path slot bridge, LDIR'd by install_dos_env), not a variable; the block must sit inside the disk ROM's claimed RAM -- today $DDAE..$DF92 straddles DISK_HIMEM $DE77 |
| BR_CALS | $DF1D | ? | - | disk / disk | **E** | RAM-resident CODE label (DOS-path slot bridge, LDIR'd by install_dos_env), not a variable; the block must sit inside the disk ROM's claimed RAM -- today $DDAE..$DF92 straddles DISK_HIMEM $DE77 |
| BC_FIELD | $DF79 | ? | - | disk / disk | **E** | RAM-resident CODE label (DOS-path slot bridge, LDIR'd by install_dos_env), not a variable; the block must sit inside the disk ROM's claimed RAM -- today $DDAE..$DF92 straddles DISK_HIMEM $DE77 |
| BC_JPIX | $DF82 | ? | - | disk / disk | **E** | RAM-resident CODE label (DOS-path slot bridge, LDIR'd by install_dos_env), not a variable; the block must sit inside the disk ROM's claimed RAM -- today $DDAE..$DF92 straddles DISK_HIMEM $DE77 |
| BC_TMP | $DF84 | ? | - | disk / disk | **C** | operand/data byte inside the DOS-path bridge block (label-derived); moves with that block into the disk ROM's claim |
| DOS_RESV_TOP | $DF93 | ? | - | disk / disk | **E** | a HIMEM value (CF-3300's), not a cell; becomes the RESULT of the claim |
| CTRL_HIMEM | $E48D | ? | NOT-A-CELL | disk / disk | **E** | a HIMEM value (CF-3300's), not a cell; becomes the RESULT of the claim |
| DSK_ENGTAB | $E48D | ? | NOT-A-CELL | basic / none | **E** | NOT-A-CELL base of the per-channel engine table ($E48D..$E7AC) -- that table itself is class B (file blocks via FILTAB) |
| TXTMAX | $E7AD | ? | NOT-A-CELL | basic+disk(ABI) / disk+main+sub | **E** | NOT-A-CELL ceiling constant -- but it IS the fixed-layout problem: becomes dynamic (text ceiling = f(HIMEM/MEMSIZ)) |
| BD_LINE | $E8AD | 512 | - | disk / disk | **D** | boot-date prompt line aliased into the sector buffer (BASENT path); boot/DOS-start scratch, moves with the buffer |
| FAT_DBUF | $E8AD | 512 | - | basic+disk(ABI) / disk+main | **C** | 512-B data/sector buffer; the reference disk ROM allocates its sector buffers by lowering HIMEM (phase 2: $F197->...->$DF95) |
| FSECTOR_BUF | $E8AD | 512 | DISK-ONLY | basic+disk(ABI) / disk | **C** | 512-B data/sector buffer; the reference disk ROM allocates its sector buffers by lowering HIMEM (phase 2: $F197->...->$DF95) |
| SECTOR_BUF | $E8AD | 512 | - | disk / disk | **C** | 512-B data/sector buffer; the reference disk ROM allocates its sector buffers by lowering HIMEM (phase 2: $F197->...->$DF95) |
| BD_MON | $E8C6 | 1 | - | disk / disk | **D** | boot-date parse scratch inside the sector buffer |
| BD_DAY | $E8C7 | 1 | - | disk / disk | **D** | boot-date parse scratch inside the sector buffer |
| FAT_MBUF | $EAAD | 512 | - | basic+disk(ABI) / disk | **C** | 512-B FAT/dir buffer; as above, a HIMEM-claimed disk-ROM buffer |
| FWBUF | $EAAD | 512 | DISK-ONLY | basic+disk(ABI) / disk | **C** | 512-B FAT/dir buffer; as above, a HIMEM-claimed disk-ROM buffer |
| WBUF | $EAAD | 512 | - | disk / disk | **C** | 512-B FAT/dir buffer; as above, a HIMEM-claimed disk-ROM buffer |
| WRBLK_MULACC | $ECA1 | 4 | - | disk / disk | **C** | WRBLK multiply accumulator aliased into WBUF's tail; disk-ROM state |
| WRBLK_MULOP | $ECA5 | 4 | - | disk / none | **E** | DEAD: no code reference (kernel.asm says 'no longer used') |
| WRBLK_MULN | $ECA9 | 3 | - | disk / none | **E** | DEAD: no code reference (kernel.asm says 'no longer used') |
| FAT_SECPERCLUS | $ECAD | 1 | - | disk / disk | **C** | mounted-disk geometry; the reference keeps it in the DPB inside its own claimed area |
| FAT_FATSTART | $ECAE | 2 | - | disk / disk | **C** | mounted-disk geometry; the reference keeps it in the DPB inside its own claimed area |
| FAT_FIRSTROOT | $ECB0 | 2 | - | disk / disk | **C** | mounted-disk geometry; the reference keeps it in the DPB inside its own claimed area |
| FAT_TOTCLUS | $ECB2 | 2 | - | disk / disk | **C** | mounted-disk geometry; the reference keeps it in the DPB inside its own claimed area |
| FAT_FIRSTDATA | $ECB4 | 2 | - | disk / disk | **C** | mounted-disk geometry; the reference keeps it in the DPB inside its own claimed area |
| FAT_CURCLUS | $ECB6 | 2 | - | disk / disk | **C** | standalone disk ROM's BDOS/stream state (MSX-DOS path); disk-ROM own area |
| FAT_CLUSSEC | $ECB8 | 1 | - | disk / disk | **C** | standalone disk ROM's BDOS/stream state (MSX-DOS path); disk-ROM own area |
| FAT_FIRSTCLUS | $ECB9 | 2 | - | disk / disk | **C** | standalone disk ROM's BDOS/stream state (MSX-DOS path); disk-ROM own area |
| FAT_FILESIZE | $ECBB | 4 | - | disk / disk+main | **C** | standalone disk ROM's BDOS/stream state (MSX-DOS path); disk-ROM own area |
| FAT_PARITY | $ECBF | 1 | - | disk / disk | **C** | FAT12 engine transient scratch (engine runs in disk.rom) |
| FAT_BYTEIDX | $ECC0 | 2 | - | disk / disk | **C** | FAT12 engine transient scratch (engine runs in disk.rom) |
| FAT_FATSEC | $ECC2 | 2 | - | disk / disk | **C** | FAT12 engine transient scratch (engine runs in disk.rom) |
| FAT_B0 | $ECC4 | 1 | - | disk / disk | **C** | FAT12 engine transient scratch (engine runs in disk.rom) |
| FAT_B1 | $ECC5 | 1 | - | disk / disk | **C** | FAT12 engine transient scratch (engine runs in disk.rom) |
| FAT_NAMEPTR | $ECC6 | 2 | - | disk / disk | **C** | FAT12 engine transient scratch (engine runs in disk.rom) |
| FAT_DIRSEC | $ECC8 | 2 | - | disk / disk | **C** | FAT12 engine transient scratch (engine runs in disk.rom) |
| FAT_DIRREM | $ECCA | 2 | - | disk / disk | **C** | FAT12 engine transient scratch (engine runs in disk.rom) |
| BDOS_RECIDX | $ECCC | ? | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| BDOS_DTA | $ECCD | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| STRENG_SPARE | $ECFC | ? | NOT-A-CELL | basic / none | **E** | NOT-A-CELL: a documented free byte |
| BDOS_BYTESLEFT | $ED4F | 4 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| BDOS_WRMODE | $ED53 | 1 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| BDOS_WRCLUS | $ED54 | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| FWR_CLUS | $ED54 | 2 | - | disk / disk | **C** | standalone disk ROM's BDOS/stream state (MSX-DOS path); disk-ROM own area |
| BDOS_WRFIRST | $ED56 | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| FWR_FIRST | $ED56 | 2 | - | disk / disk | **C** | standalone disk ROM's BDOS/stream state (MSX-DOS path); disk-ROM own area |
| BDOS_WRSECIDX | $ED58 | 1 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| FWR_SECIDX | $ED58 | 1 | - | disk / disk | **C** | standalone disk ROM's BDOS/stream state (MSX-DOS path); disk-ROM own area |
| BDOS_WRBUFLEN | $ED59 | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| FWR_BUFLEN | $ED59 | 2 | - | disk / disk+main | **C** | standalone disk ROM's BDOS/stream state (MSX-DOS path); disk-ROM own area |
| BDOS_WRBYTES | $ED5B | 4 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| FWR_BYTES | $ED5B | 4 | - | disk / disk+main | **C** | standalone disk ROM's BDOS/stream state (MSX-DOS path); disk-ROM own area |
| BDOS_DIRSEC | $ED5F | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| FWR_DIRSEC | $ED5F | 2 | - | disk / disk | **C** | standalone disk ROM's BDOS/stream state (MSX-DOS path); disk-ROM own area |
| BDOS_DIROFF | $ED61 | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| FWR_DIROFF | $ED61 | 2 | - | disk / disk | **C** | standalone disk ROM's BDOS/stream state (MSX-DOS path); disk-ROM own area |
| FAT_WRTMP | $ED63 | 2 | - | disk / disk | **C** | FAT12 engine transient scratch (engine runs in disk.rom) |
| FAT_WRTMP2 | $ED65 | ? | - | disk / disk | **C** | FAT12 engine transient scratch (engine runs in disk.rom) |
| FAT_NUMFATS | $ED67 | 1 | - | disk / disk | **C** | mounted-disk geometry; the reference keeps it in the DPB inside its own claimed area |
| FAT_SECPERFAT | $ED68 | 2 | - | disk / disk | **C** | mounted-disk geometry; the reference keeps it in the DPB inside its own claimed area |
| HOOK_SLOT | $ED6A | 1 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| BDOS_SRCHIDX | $ED6B | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| BOOT_SV_A8 | $ED6D | 1 | - | disk / disk | **D** | INIT-time slot save; registers/stack suffice |
| RRND_RECSEC | $ED6D | 1 | - | disk / none | **E** | DEAD alias: no code reference; the byte is BOOT_SV_* |
| BOOT_SV_SEC | $ED6E | 1 | - | disk / disk | **D** | INIT-time slot save; registers/stack suffice |
| RRND_CLUSSEC | $ED6E | 1 | - | disk / none | **E** | DEAD alias: no code reference; the byte is BOOT_SV_* |
| FREAD_LEFT | $ED79 | ? | - | disk / disk | **C** | standalone disk ROM's BDOS/stream state (MSX-DOS path); disk-ROM own area |
| RDBLK_REQ | $ED79 | ? | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| RDBLK_RECSIZE | $ED7B | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| RDBLK_DONE | $ED7D | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| RDBLK_CNT | $ED7F | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| FREAD_OFF | $ED81 | 2 | - | disk / disk | **C** | standalone disk ROM's BDOS/stream state (MSX-DOS path); disk-ROM own area |
| RDBLK_BUFPOS | $ED81 | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| RDBLK_DST | $ED83 | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| P1_DEST | $ED85 | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| COPY_STAMP | $ED87 | 4 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| WRBLK_REC | $ED87 | 4 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| WRBLK_RECSEC | $ED8A | 1 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| DPSAVE_SP | $ED8B | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| WRBLK_RS | $ED8B | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| WRBLK_CNT | $ED8D | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| WRBLK_REQ | $ED8F | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| WRBLK_PREVCLUS | $ED91 | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| WRBLK_KEEPCNT | $ED93 | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| WRBLK_NEXTCLUS | $ED95 | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| WRBLK_CURVALID | $ED97 | 1 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| WRBLK_CURSEC | $ED98 | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| FAT_ALLOCHINT | $ED9A | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| RDBLK_RRSTART | $ED9C | 3 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| DRV_TRAMP | $ED9F | 20 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim ⚠️ (DRVTBL publishes its address to MSXDOS) |
| BDOS_SEQREC | $EDB3 | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| DBUF_PTR | $EDB5 | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| MBUF_PTR | $EDB7 | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| FAT_DEFER | $EDB9 | 1 | DISK-ONLY | basic+disk(ABI) / disk | **C** | FAT write-cache / DSKCHG clock of the disk engine |
| FAT_FCACHE | $EDBA | 1 | DISK-ONLY | basic+disk(ABI) / disk | **C** | FAT write-cache / DSKCHG clock of the disk engine |
| RND_HSEC | $EDBB | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| DSK_STAMP | $EDBD | 2 | DISK-ONLY | basic+disk(ABI) / disk | **C** | FAT write-cache / DSKCHG clock of the disk engine |
| BASIC_WS_CEIL | $EDFD | ? | NOT-A-CELL | basic / none | **E** | NOT-A-CELL guard constant; dies with the fixed FAT block |
| FAT_SECPERCLUS | $EDFD | 1 | DISK-ONLY | basic / disk | **C** | mounted-disk geometry; the reference keeps it in the DPB inside its own claimed area |
| FAT_FATSTART | $EDFE | 2 | DISK-ONLY | basic / disk | **C** | mounted-disk geometry; the reference keeps it in the DPB inside its own claimed area |
| FAT_FIRSTROOT | $EE00 | 2 | DISK-ONLY | basic / disk | **C** | mounted-disk geometry; the reference keeps it in the DPB inside its own claimed area |
| FAT_TOTCLUS | $EE02 | 2 | DISK-ONLY | basic / disk | **C** | mounted-disk geometry; the reference keeps it in the DPB inside its own claimed area |
| FAT_FIRSTDATA | $EE04 | 2 | DISK-ONLY | basic / disk | **C** | mounted-disk geometry; the reference keeps it in the DPB inside its own claimed area |
| FAT_CURCLUS | $EE06 | 2 | DISK-ONLY | basic / disk | **B** | per-open-file stream state (live copy of the channel, LDIR'd to/from DSK_ENGTAB rows); the reference keeps it in the FCB inside the file's FILTAB buffer ⚠️ (the live engine copy could stay C) |
| FCH_STATE0 | $EE06 | 2 | - | basic / none | **E** | alias of FAT_CURCLUS: base of the 50-B live per-channel span |
| FAT_CLUSSEC | $EE08 | 1 | DISK-ONLY | basic / disk | **B** | per-open-file stream state (live copy of the channel, LDIR'd to/from DSK_ENGTAB rows); the reference keeps it in the FCB inside the file's FILTAB buffer ⚠️ (the live engine copy could stay C) |
| FAT_FIRSTCLUS | $EE09 | 2 | DISK-ONLY | basic / disk | **B** | per-open-file stream state (live copy of the channel, LDIR'd to/from DSK_ENGTAB rows); the reference keeps it in the FCB inside the file's FILTAB buffer ⚠️ (the live engine copy could stay C) |
| FAT_FILESIZE | $EE0B | 4 | DISK-ONLY | basic / disk+main | **B** | per-open-file stream state (live copy of the channel, LDIR'd to/from DSK_ENGTAB rows); the reference keeps it in the FCB inside the file's FILTAB buffer ⚠️ (the live engine copy could stay C) |
| FAT_NUMFATS | $EE0F | 1 | DISK-ONLY | basic / disk | **C** | mounted-disk geometry; the reference keeps it in the DPB inside its own claimed area |
| FAT_SECPERFAT | $EE10 | 2 | DISK-ONLY | basic / disk | **C** | mounted-disk geometry; the reference keeps it in the DPB inside its own claimed area |
| FAT_PARITY | $EE12 | 1 | DISK-ONLY | basic / disk | **C** | FAT12 engine transient scratch (engine runs in disk.rom) |
| FAT_BYTEIDX | $EE13 | 2 | DISK-ONLY | basic / disk | **C** | FAT12 engine transient scratch (engine runs in disk.rom) |
| FAT_FATSEC | $EE15 | 2 | DISK-ONLY | basic / disk | **C** | FAT12 engine transient scratch (engine runs in disk.rom) |
| FAT_B0 | $EE17 | 1 | DISK-ONLY | basic / disk | **C** | FAT12 engine transient scratch (engine runs in disk.rom) |
| FAT_B1 | $EE18 | 1 | DISK-ONLY | basic / disk | **C** | FAT12 engine transient scratch (engine runs in disk.rom) |
| FAT_NAMEPTR | $EE19 | 2 | DISK-ONLY | basic / disk | **C** | FAT12 engine transient scratch (engine runs in disk.rom) |
| FAT_DIRSEC | $EE1B | 2 | DISK-ONLY | basic / disk | **C** | FAT12 engine transient scratch (engine runs in disk.rom) |
| FAT_DIRREM | $EE1D | 2 | DISK-ONLY | basic / disk | **C** | FAT12 engine transient scratch (engine runs in disk.rom) |
| FAT_WRTMP | $EE1F | 2 | DISK-ONLY | basic / disk | **C** | FAT12 engine transient scratch (engine runs in disk.rom) |
| FAT_WRTMP2 | $EE21 | 2 | DISK-ONLY | basic / disk | **C** | FAT12 engine transient scratch (engine runs in disk.rom) |
| FREAD_OFF | $EE23 | 2 | DISK-ONLY | basic / disk | **B** | per-open-file stream state (live copy of the channel, LDIR'd to/from DSK_ENGTAB rows); the reference keeps it in the FCB inside the file's FILTAB buffer ⚠️ (the live engine copy could stay C) |
| FREAD_LEFT | $EE25 | 4 | DISK-ONLY | basic / disk | **B** | per-open-file stream state (live copy of the channel, LDIR'd to/from DSK_ENGTAB rows); the reference keeps it in the FCB inside the file's FILTAB buffer ⚠️ (the live engine copy could stay C) |
| FWR_CLUS | $EE29 | 2 | DISK-ONLY | basic / disk | **B** | per-open-file stream state (live copy of the channel, LDIR'd to/from DSK_ENGTAB rows); the reference keeps it in the FCB inside the file's FILTAB buffer ⚠️ (the live engine copy could stay C) |
| FWR_FIRST | $EE2B | 2 | DISK-ONLY | basic / disk | **B** | per-open-file stream state (live copy of the channel, LDIR'd to/from DSK_ENGTAB rows); the reference keeps it in the FCB inside the file's FILTAB buffer ⚠️ (the live engine copy could stay C) |
| FWR_SECIDX | $EE2D | 1 | DISK-ONLY | basic / disk | **B** | per-open-file stream state (live copy of the channel, LDIR'd to/from DSK_ENGTAB rows); the reference keeps it in the FCB inside the file's FILTAB buffer ⚠️ (the live engine copy could stay C) |
| FWR_BUFLEN | $EE2E | 2 | DISK-ONLY | basic / disk+main | **B** | per-open-file stream state (live copy of the channel, LDIR'd to/from DSK_ENGTAB rows); the reference keeps it in the FCB inside the file's FILTAB buffer ⚠️ (the live engine copy could stay C) |
| FWR_BYTES | $EE30 | 4 | DISK-ONLY | basic / disk+main | **B** | per-open-file stream state (live copy of the channel, LDIR'd to/from DSK_ENGTAB rows); the reference keeps it in the FCB inside the file's FILTAB buffer ⚠️ (the live engine copy could stay C) |
| FWR_DIRSEC | $EE34 | 2 | DISK-ONLY | basic / disk | **B** | per-open-file stream state (live copy of the channel, LDIR'd to/from DSK_ENGTAB rows); the reference keeps it in the FCB inside the file's FILTAB buffer ⚠️ (the live engine copy could stay C) |
| FWR_DIROFF | $EE36 | 2 | DISK-ONLY | basic / disk | **B** | per-open-file stream state (live copy of the channel, LDIR'd to/from DSK_ENGTAB rows); the reference keeps it in the FCB inside the file's FILTAB buffer ⚠️ (the live engine copy could stay C) |
| FCH_RECLENS | $EE4D | 32 | DISK-ONLY | basic+disk(ABI) / disk | **B** | per-channel record length table (16x2 B); in MS-BASIC the record length lives in each file's FCB in its FILTAB buffer, sized by MAXFILES |
| GP_SRC | $EE77 | 2 | DISK-ONLY | basic+disk(ABI) / disk | **C** | GET/PUT per-call transient (a Disk-BASIC verb, run by disk.rom) |
| GP_LEFT | $EE79 | 2 | DISK-ONLY | basic+disk(ABI) / disk | **C** | GET/PUT per-call transient (a Disk-BASIC verb, run by disk.rom) |
| GP_RECNO | $EE7D | 4 | DISK-ONLY | basic+disk(ABI) / disk | **C** | GET/PUT record number for the call ⚠️ (MS-BASIC also keeps the current record in the FCB -> B candidate) |
| FLD_CUROFF | $EEC3 | 2 | DISK-ONLY | basic+disk(ABI) / disk | **C** | FIELD transient (Disk-BASIC verb) |
| LRSET_JUST | $EEC6 | 1 | DISK-ONLY | basic+disk(ABI) / disk+sub | **C** | LSET/RSET transient; a Disk-BASIC verb on the reference ⚠️ (run by main+sub here, so a published TEMP cell, as D-WSZERO did for BL_PTR, may fit better) |
| LRSET_W | $EEC7 | 1 | DISK-ONLY | basic / main+sub | **C** | LSET/RSET transient; a Disk-BASIC verb on the reference ⚠️ (run by main+sub here, so a published TEMP cell, as D-WSZERO did for BL_PTR, may fit better) |
| LRSET_DEST | $EEC8 | 2 | DISK-ONLY | basic / main+sub | **C** | LSET/RSET transient; a Disk-BASIC verb on the reference ⚠️ (run by main+sub here, so a published TEMP cell, as D-WSZERO did for BL_PTR, may fit better) |
| COPY_SRC | $EEEE | 11 | DISK-ONLY | basic+disk(ABI) / disk | **A** | 11-B second filename -> FILNM2 ($F871), MS-BASIC's second-name buffer (zerobas already uses FILNM2 as CAS_HDRNAME) |
| COPY_CLUS | $EEF9 | 2 | DISK-ONLY | basic+disk(ABI) / disk | **C** | COPY transient (disk verb) |
| COPY_LEFT | $EEFB | 4 | DISK-ONLY | basic+disk(ABI) / disk | **C** | COPY transient (disk verb) |
| SCAN_PRIM | $EF42 | 1 | BOOT-ONLY | basic / main | **D** | BOOT-ONLY ROM-scan state; the NMS 1200 INIT overwrote $EF42-$EF47 (STEP 5) -- keep on the scan's own stack frame below STKTOP |
| SCAN_SLOT | $EF43 | 1 | BOOT-ONLY | basic / main | **D** | BOOT-ONLY ROM-scan state; the NMS 1200 INIT overwrote $EF42-$EF47 (STEP 5) -- keep on the scan's own stack frame below STKTOP |
| SCAN_INIT | $EF44 | 2 | BOOT-ONLY | basic / main | **D** | BOOT-ONLY ROM-scan state; the NMS 1200 INIT overwrote $EF42-$EF47 (STEP 5) -- keep on the scan's own stack frame below STKTOP |
| SCAN_IY | $EF46 | 2 | BOOT-ONLY | basic / main | **D** | BOOT-ONLY ROM-scan state; the NMS 1200 INIT overwrote $EF42-$EF47 (STEP 5) -- keep on the scan's own stack frame below STKTOP |
| DISK_FCB | $EF48 | ? | DISK-ONLY | basic / none | **E** | alias of DISK_FCB_DRV (block base) |
| DISK_FCB_DRV | $EF48 | ? | - | basic / main+sub | **C** | drive byte of the scratch FCB; no published byte beside FILNAM ($F865 is PTRFIL's high byte) ⚠️  |
| DK_FCB_DRV | $EF48 | 1 | - | disk / disk | **C** | drive byte of the scratch FCB; no published byte beside FILNAM ($F865 is PTRFIL's high byte) ⚠️  |
| DISK_FCB_NAME | $EF49 | 11 | DISK-ONLY | basic+disk(ABI) / disk+main+sub | **A** | 11-B 8.3 name -> FILNAM ($F866), MS-BASIC's filename buffer (zerobas already uses FILNAM+0 as CAS_WANT) |
| DSV_PTR | $EF59 | 2 | DISK-ONLY | basic+disk(ABI) / disk | **C** | SAVE/BSAVE source cursor; disk-ROM transient ⚠️  |
| DSV_END | $EF5B | 2 | DISK-ONLY | basic+disk(ABI) / disk | **A** | SAVE/BSAVE end address -> SAVEND ($F87D) ⚠️ (already TSV_END's home; same meaning for BSAVE, a stretch for SAVE) |
| FMT_GEOMSEL | $EF61 | 1 | DISK-ONLY | basic+disk(ABI) / none | **C** | CALL FORMAT main->tenant mailbox ⚠️ (no code reference found -- possibly dead -> E) |
| FMT_RESULT | $EF62 | 1 | DISK-ONLY | basic+disk(ABI) / disk+main | **C** | CALL FORMAT tenant->main result (format.asm reads it); disk-verb mailbox |
| FILES_ENTIDX | $EF63 | 1 | DISK-ONLY | basic+disk(ABI) / disk | **C** | FILES transient (disk verb) |
| F37D_STUB | $EFDA | 28 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| DSK_MEDIA | $EFF6 | 1 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| FDC_IFF | $EFF7 | 1 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| FDC_CNT | $EFF8 | 1 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| FDC_LSEC | $EFF9 | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| FDC_DEST | $EFFB | 2 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| FDC_TRY | $EFFD | 1 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| P1_BLIT | $EFFE | 27 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| FLD_END | $F019 | 2 | DISK-ONLY | basic+disk(ABI) / disk | **C** | FIELD transient (Disk-BASIC verb) |
| DSK_CURDRV | $F022 | 1 | - | disk / disk | **C** | disk-ROM-only state (BDOS / DSKIO / FDC / bounce); belongs in the disk ROM's HIMEM claim |
| GP_SEC | $F07B | 2 | DISK-ONLY | basic+disk(ABI) / disk | **C** | GET/PUT per-call transient (a Disk-BASIC verb, run by disk.rom) |
| GP_WITHIN | $F07D | 2 | DISK-ONLY | basic+disk(ABI) / disk | **C** | GET/PUT per-call transient (a Disk-BASIC verb, run by disk.rom) |
| GP_CLUS | $F07F | 2 | DISK-ONLY | basic+disk(ABI) / disk | **C** | GET/PUT per-call transient (a Disk-BASIC verb, run by disk.rom) |
| GP_CLIDX | $F081 | 2 | DISK-ONLY | basic+disk(ABI) / disk | **C** | GET/PUT per-call transient (a Disk-BASIC verb, run by disk.rom) |
| GP_SECINCL | $F083 | 1 | DISK-ONLY | basic+disk(ABI) / disk | **C** | GET/PUT per-call transient (a Disk-BASIC verb, run by disk.rom) |
| GP_PHYS | $F084 | 2 | DISK-ONLY | basic+disk(ABI) / disk | **C** | GET/PUT per-call transient (a Disk-BASIC verb, run by disk.rom) |
| GP_FLAGS | $F088 | 1 | DISK-ONLY | basic+disk(ABI) / disk | **C** | GET/PUT per-call transient (a Disk-BASIC verb, run by disk.rom) |
| FMT_SEC | $F097 | 1 | DISK-ONLY | basic / none | **E** | DEAD: no code reference (comments only) ⚠️  |
| FMT_DESC | $F098 | 2 | DISK-ONLY | basic / none | **E** | DEAD: no code reference (comments only) ⚠️  |
| GP_RECLEN | $F09A | 2 | DISK-ONLY | basic+disk(ABI) / disk | **C** | GET/PUT per-call transient (a Disk-BASIC verb, run by disk.rom) |
| FILES_HASPAT | $F09D | 1 | DISK-ONLY | basic+disk(ABI) / disk | **C** | FILES transient (disk verb) |
| DRVA_DPB | $F195 | 18 | - | disk / disk | **C** | drive-A DPB; reference allocates DPBs in its HIMEM claim (phase 2 $F197..) -- keep, make it claim-relative ⚠️ ($F195 sits below the $F1C1 phase-1 floor) |
| W50A9_RET_DE | $F1AA | ? | - | disk / disk | **E** | a pointer VALUE / end marker into the disk work area, not a cell |
| RES_PRINT | $F1C9 | ? | - | disk / disk | **C** | resident code: already at the fixed MSX-DOS disk work-area address ($F1C9..$F37F) the reference disk ROM claims in phase 1 (HIMEM $F380-$1BF) -- KEEP; conformant once claimed via HIMEM |
| FN_STK_FLOOR | $F200 | ? | NOT-A-CELL | basic / none | **E** | NOT-A-CELL stack-floor constant for DEF FN; must become STKTOP-relative (class B semantics) ⚠️  |
| DOS_DTAPTR | $F23D | 2 | - | disk / disk | **C** | MSX-DOS work-area DTA cache: already at the fixed MSX-DOS disk work-area address ($F1C9..$F37F) the reference disk ROM claims in phase 1 (HIMEM $F380-$1BF) -- KEEP; conformant once claimed via HIMEM |
| W50A9_WRKB | $F242 | 1 | - | disk / disk | **C** | stock work-area cell: already at the fixed MSX-DOS disk work-area address ($F1C9..$F37F) the reference disk ROM claims in phase 1 (HIMEM $F380-$1BF) -- KEEP; conformant once claimed via HIMEM |
| CURDRV_CELL | $F247 | 1 | - | disk / disk | **C** | current drive: already at the fixed MSX-DOS disk work-area address ($F1C9..$F37F) the reference disk ROM claims in phase 1 (HIMEM $F380-$1BF) -- KEEP; conformant once claimed via HIMEM |
| RES_STUBS | $F24E | ? | - | disk / disk | **C** | resident stub table: already at the fixed MSX-DOS disk work-area address ($F1C9..$F37F) the reference disk ROM claims in phase 1 (HIMEM $F380-$1BF) -- KEEP; conformant once claimed via HIMEM |
| RES_STUBS_END | $F2B8 | ? | - | disk / disk | **E** | a pointer VALUE / end marker into the disk work area, not a cell |
| DISKVE | $F323 | 2 | - | disk / disk | **C** | published DISKVE: already at the fixed MSX-DOS disk work-area address ($F1C9..$F37F) the reference disk ROM claims in phase 1 (HIMEM $F380-$1BF) -- KEEP; conformant once claimed via HIMEM |
| DATE_DAYS | $F33B | 2 | - | disk / disk | **C** | DOS date (CF-3300 location): already at the fixed MSX-DOS disk work-area address ($F1C9..$F37F) the reference disk ROM claims in phase 1 (HIMEM $F380-$1BF) -- KEEP; conformant once claimed via HIMEM |
| BASENT_REQ | $F33D | 2 | - | disk / disk | **C** | BASENT restart mark: already at the fixed MSX-DOS disk work-area address ($F1C9..$F37F) the reference disk ROM claims in phase 1 (HIMEM $F380-$1BF) -- KEEP; conformant once claimed via HIMEM |
| DOS_F340 | $F340 | 1 | - | disk / disk | **C** | kernel init flag: already at the fixed MSX-DOS disk work-area address ($F1C9..$F37F) the reference disk ROM claims in phase 1 (HIMEM $F380-$1BF) -- KEEP; conformant once claimed via HIMEM |
| RAMAD0 | $F341 | 4 | - | disk / disk | **C** | published RAMAD0-3: already at the fixed MSX-DOS disk work-area address ($F1C9..$F37F) the reference disk ROM claims in phase 1 (HIMEM $F380-$1BF) -- KEEP; conformant once claimed via HIMEM |
| DOS_F346 | $F346 | 1 | - | disk / disk | **C** | published "DOS booted" flag: already at the fixed MSX-DOS disk work-area address ($F1C9..$F37F) the reference disk ROM claims in phase 1 (HIMEM $F380-$1BF) -- KEEP; conformant once claimed via HIMEM |
| DRVCNT | $F347 | 1 | - | disk / disk | **C** | drive count: already at the fixed MSX-DOS disk work-area address ($F1C9..$F37F) the reference disk ROM claims in phase 1 (HIMEM $F380-$1BF) -- KEEP; conformant once claimed via HIMEM |
| DRVTBL | $F348 | 16 | - | disk / disk | **C** | published DRVTBL: already at the fixed MSX-DOS disk work-area address ($F1C9..$F37F) the reference disk ROM claims in phase 1 (HIMEM $F380-$1BF) -- KEEP; conformant once claimed via HIMEM |
| DSKBUF_PTR | $F351 | 2 | DISK-ONLY | basic+disk(ABI) / disk | **C** | pointer to the DSKI$/DSKO$ sector buffer at $F351, the published disk work-area SECBUF slot ⚠️ -- KEEP; conformant once $F1C9..$F37F is claimed via HIMEM |
| W50A9_RET_HL | $F359 | ? | - | disk / disk | **E** | a pointer VALUE / end marker into the disk work area, not a cell |
| F365_STUB | $F365 | ? | - | disk / disk | **C** | published $F365 slot-read stub: already at the fixed MSX-DOS disk work-area address ($F1C9..$F37F) the reference disk ROM claims in phase 1 (HIMEM $F380-$1BF) -- KEEP; conformant once claimed via HIMEM |
| WA_JMPTAB | $F368 | 21 | - | disk / disk | **C** | resident jump table $F368: already at the fixed MSX-DOS disk work-area address ($F1C9..$F37F) the reference disk ROM claims in phase 1 (HIMEM $F380-$1BF) -- KEEP; conformant once claimed via HIMEM |
| SYSTEM | $F37D | 2 | - | disk / disk | **C** | published BDOS entry $F37D: already at the fixed MSX-DOS disk work-area address ($F1C9..$F37F) the reference disk ROM claims in phase 1 (HIMEM $F380-$1BF) -- KEEP; conformant once claimed via HIMEM |
226 {'E': 45, 'C': 155, 'D': 9, 'B': 14, 'A': 3} []
