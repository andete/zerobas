<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Disk write path: fewer sector commands (D-BLKIOPERCALL step 2, D-FDCDI)

Status: **W1 and W2 built 2026-10-10** (§3: 28 → 23 → 14 READs on the
workload, gate `wcache-acceptance`); W3–W4 are design. TIER 5 (on-par speed),
and the lever of D-FDCDI (TIER 3: keys typed during long disk work are lost,
because the driver masks interrupts inside each sector command).

## 1. What was measured

`scratchpad/fdcseq_probe.py` logs every WD2793 command with its track and sector
registers. These are I/O registers at `$7FB8..$7FBC` on both machines, the
permitted side of the clean room. The workload is D-FDCDI's: `OPEN "X" FOR OUTPUT`,
200 × `PRINT#1` of 19 characters (4200 B), `CLOSE`
([`fdcseq_run.out`](../scratchpad/fdcseq_run.out)).

The disk is 720 KB with 9 sectors a track. On track 0, sector 1 is the boot
sector, sectors 2–4 are FAT copy 1, 5–7 are FAT copy 2, and 8 onward is the root
directory. The data starts on track 1.

**CF-3300: 16 WRITE, 16 READ, 3 seeks.** Each data sector is written once and
read back once, which looks like a verify. The FAT and the directory are touched
only at `CLOSE`:

    W1/2 R1/2  W1/3 R1/3 … W1/9 R1/9  W2/1 R2/1          9 data sectors
    W0/8 R0/8  W0/2 W0/3 W0/4 R… W0/5 W0/6 W0/7 R…      CLOSE: directory, FAT 1, FAT 2

**zerobas: 36 WRITE, 28 READ, 64 seeks** (one before every command). Per
cluster of 2 sectors:

    R0/1                    fat_total_clusters re-reads the BOOT sector
    R0/2                    fat_alloc_cluster's scan (its sector cache is reset per call)
    R0/2 W0/2 W0/5          the new entry marked used, both FAT copies written
    R0/2 W0/2 W0/5          the previous entry linked to it, both copies again
    W1/n R1/n W1/n          per data sector: first half written padded, read back,
                            second half merged and written (dout_write)

So 4 FAT writes and 4 reads per cluster where the CF-3300 has none, and 3
commands per data sector where it has 2 (and its second is a verify).

## 2. Where it comes from

- `fat_total_clusters` (basic/fat-prim-body.inc) reads the boot sector into
  `FAT_MBUF` on every call, to recompute a number the mount already had.
- `fat_alloc_cluster` caches its FAT sector only within one call
  (`FAT_WRTMP2 := $FFFF` at entry). Marking the entry and linking the previous
  one each re-read the sector and write BOTH copies.
- `dout_write` (disk/kernel.asm) writes the channel's 256 B record as one HALF of
  a 512 B sector. A first half is written padded at once, and the second half
  re-reads the sector (`dout_secread`) to complete it. The channel's record buffer
  is 256 B (the reference's FCB shape), and the sector buffer `FAT_DBUF` is shared
  by every disk operation, so nothing holds the first half across calls.

## 3. The slices, cheapest and safest first

Each slice must leave the bytes on the medium after `CLOSE` identical, so
`bdos-acceptance`, `wrblk_roundtrip`, `diskfull` and `fatio` keep their images.
**W3 and W4 also change what is on the medium BETWEEN calls**; any row that
compares a mid-sequence image must be re-read before they are built.

**W1 — total clusters computed once, at mount. ✅ BUILT 2026-10-10.**
`fat_mount` already parses the BPB; it now stores the cluster count, and
`fat_total_clusters` returns it, with no read and so no failure. **No new RAM:**
the count lives in the cell `FAT_ROOTSECS` held (`$E4A5` in disk.rom's map,
`$E9C5` in BASIC's), because the root-sector count is `FAT_FIRSTDATA −
FAT_FIRSTROOT`, two cells the mount already keeps. Its five readers call
`fat_rootsecs` instead; four of them were one 12-byte root-scan setup, now
`fat_dir_start`. That is −4 B in sub page 1 and −20 B in disk.rom. Only
`fat_mount` writes the geometry, so the count is as trustworthy across calls
as `FAT_FIRSTDATA`. Measured: 28 → 23 READs, 36 WRITEs unchanged, every
`R0/1` gone (predicted exactly, [`fdcseq_w1.out`](../scratchpad/fdcseq_w1.out)).
Knife K-WC1 (the boot read restored) moves only `zb-reads`
([`wcache_knives.out`](../scratchpad/wcache_knives.out)).

**W2 — the FAT sector kept WITHIN an allocation. ✅ BUILT 2026-10-10, narrower
than first designed.** A tag kept *across* calls needs all 38 `FAT_MBUF` users
audited. But the two re-reads happen within one allocation: the scan loads
the sector, the mark re-reads it, and the link re-reads it. Nothing else
touches `FAT_MBUF` in between. Every FAT routine keeps `(FAT_FATSEC)` naming
the sector `FAT_MBUF` holds: the scan, both straddle paths, and
`fat_write_buf_allfats`, which leaves both as they were. So
`fat_write_fat_entry_hot` skips the read when the entry's sector is that one.
It is used at exactly two sites: `fac_found` (right after its scan) and
`ffds_alloc`'s link (right after the allocation). Every other caller keeps the
plain entry.
- **Measured:** 23 → 14 READs (predicted 13: MISSED by one — the first
  cluster has no link to save), writes unchanged, the file whole on both
  ([`fdcseq_w2.out`](../scratchpad/fdcseq_w2.out)).
- **Where it lives:** the body's region in disk.rom (pinned at `$75A5`) had no
  room, even for a 4-byte split of `fat_read_fat_sector`; the build assembled
  EMPTY twice. So the hot entry carries its own copy of the sector arithmetic,
  in disk/fat.asm's `$47C1` fill for disk.rom, and in the body for the sub-ROM
  (`IF SUB_BUILD`, 62 B of sub page 1).
- **Knife:** K-WC2 (the hot entry always reads) moves only `zb-reads`.

**W3 — the FAT written at CLOSE, as the CF-3300 does.** Mark-used and link
only change `FAT_MBUF` (dirty flag). The dirty sector is written to both copies
when another FAT sector is needed, at `CLOSE`, and before any operation that
reads the FAT from disk. That saves 4 WRITEs per cluster. It changes the
medium between calls; that is the faithful face (D-PRINTFULLSTAMP already
records that the CF-3300 commits the FAT at close), but `dwr_fail`'s
chain-release path and every disk-full row must be re-read.

**W4 — the data sector's first half kept, not written.** A tag holds the sector
whose first half `FAT_DBUF` holds unwritten. The second half then merges with no
read, and one write follows. Any other user of `FAT_DBUF` must flush first. That
covers every channel, the mount, the directory work and the BDOS, so this is
the widest audit, and it comes last. It saves 1 READ and 1 WRITE per data
sector.

Expected for the workload: 64 commands down to about 26 (W1 −5, W2 −10,
W3 −20 +2, W4 −18 +3). The CF-3300's 32 include its verify reads, which
zerobas does not do.

## 4. How each slice is witnessed

- `fdcseq_probe.py` / `fdcdi_count.py`: the command sequence, before and after,
  each slice predicted by command kind.
- `fdcdi_typeahead.py`: the share of 22 typed keys that arrive (D-FDCDI; the
  CF-3300 keeps ~77 %, zerobas ~42 %).
- The image after `CLOSE`, byte for byte against the pre-slice build
  (`wrblkalt-acceptance`, `asavedev-acceptance`, `diskfull`).
- A knife per slice: undo the tag (or the deferral) and the command count must
  return, exactly.
