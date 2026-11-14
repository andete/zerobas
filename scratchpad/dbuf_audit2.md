# W4 audit, round 2 (2026-11-14): who changes the shared sector buffer without a read

Buffer $E8AD..$EAAC. The same address under several names:
- SECTOR_BUF (disk/equates.inc), FAT_DBUF, FSECTOR_BUF (basic/sysvars.inc; disk/disk.asm asserts
  they are equal).
- BD_LINE (disk/fat.asm, the boot date prompt), with BD_MON / BD_DAY at +25 / +26. Missing from
  round 1.

The search covered every reference to those names, the pointer behind each base load followed to
its stores, all 53 ldir / lddr destinations, and the routines that hand back a pointer into the
buffer. A read-only agent did the search; fat_media's row was spot-checked by hand.

## Sites that change bytes

| # | site | change | read before it in the call? | written out after? |
|---|---|---|---|---|
| 1 | bdos_seqwrite_body -> dta_rec | 128 B from the DTA, at +BDOS_WRBUFLEN | no | later (at 512 B, seq_flush, close) |
| 2 | fip_store (fatiow-body.inc; via hco_byte, sv-diskwr) | 1 B at +FWR_BUFLEN | no | later |
| 3 | dsm_p1_pre / dsm_found (SFIRST/SNEXT) | a 33 B entry, the DTA pointed into the buffer | yes (read_sector) | no |
| 4 | fat_media (every normal mount) | a made-up BPB at +11..+23 over sector 1 | yes (rd_dbuf) | no |
| 5 | bb_mark | the BASENT trampoline, run there | no | no |
| 6 | bd_line / bd_parse (boot date) | the typed line | no | no |
| 7 | fat_flush_data_sector pad loop | zeros from FWR_BUFLEN | depends on the caller | yes (on failure: no) |
| 8 | dout_write (PRINT#) | the first half: no read; the second half after dout_secread | first half: no | yes (dwr_fail: no) |
| 9 | wrblk_body -> dta_chunk | a chunk | yes | yes (on failure: no) |
| 10 | wrrnd_body -> dta_rec | 128 B | yes | yes (on failure: no) |
| 11 | close_read stamp, hkn_stamp, fren_wild, fdl_marked | a directory entry edited in place | yes | yes (on failure: no) |

## Physical reads that bypass read_sector

- dskio_next's page-1 bounce.
- A direct dskio_rd whose destination range overlaps the buffer: RDABS with the DTA there,
  frs_to, BLOAD.
- A failed or partial read leaves the buffer half-filled.

## The design this points to

The tag is "the buffer holds sector S, as RDBLK read it":

- Set it at RDBLK's own successful read.
- Clear it in dskio itself (every physical transfer, the bypasses above included). Then every
  writer whose path did any disk I/O after RDBLK's read is safe by construction: rows 3, 4, 7
  (COPY's path), 9, 10 and 11, the failure paths included.

Explicit clears are then needed only where bytes change with NO I/O since RDBLK could have set
the tag:
- #1 dta_rec in the sequential writer;
- #2 fip_store;
- #5 bb_mark;
- #6 bd_line, or the tag invalid from INIT;
- #8 dout_write's first half.

Tag value 0 means invalid: sector 0 is the boot sector, never an RDBLK data sector.

Accepted, as the CF-3300 also reads a data sector once across calls: a disk swapped between two
RDBLK calls with no I/O between them is not noticed.

Left open:
- Whether MSXDOS.SYS or a user program writes into the buffer: its address is not published to
  them.
- P1_BLIT with a user DTA inside the buffer: not traced.
