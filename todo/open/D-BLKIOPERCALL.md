- [ ] 🔴 **D-BLKIOPERCALL — EVERY BLOCK I/O CALL STILL RE-MOUNTS AND RE-FINDS, AND EVERY WRBLK
      REWRITES THE DIRECTORY: 3.1× (read) AND 8.7× (write) THE CF-3300 ON 32 KB
      (filed 2026-10-01 with D-WRBLKSEEK)**
      🎚️ TIER 5 — on-par speed: inside T2's 10×, so this is the ratio, not the rung.
      📏 **RE-MEASURED 2026-11-08** ([`blkio_1108.out`](../../scratchpad/blkio_1108.out), wrblkalt-acceptance's own command line): the
      32 KB WSEEK write **193.60 s against the CF-3300's 30.95 (6.3x)**, the SEEK read 46.00
      against 14.65 (3.1x). 🔮 Predicted "write ~unchanged (D-PUTCACHE holds PUT's sectors
      only), read better (D-KEYSKIP)": the write HIT (6.6x -> 6.3x), the read MISSED (3.1x
      unchanged). The largest speed ratio left in the queue. ➡️ NEXT: D-PUTCACHE's shape for
      WRBLK -- the data sector held across calls (write when full, at a seek away, or at
      FCLOSE) and the directory / FAT deferred to FCLOSE, as the CF-3300's counts below
      show; wroe reads into SECTOR_BUF (FAT_DBUF), not FAT_MBUF, so rh_check's hit rule
      (destination FAT_MBUF) needs the buffer in the tag, or WRBLK moved onto FAT_MBUF.
      📏 **EXPERIMENT 2026-11-08 (D-WRBLKDIR, reverted): THE DIRECTORY AT FCLOSE, NOT PER CALL.**
      Dropping wrblk_body's per-call fat_dir_update and writing the entry in close_read from
      the FCB (wrblk_fcbstate + fat_dir_update): **WSEEK 193.6 -> 106.3 s (6.3x -> 3.4x)**, the
      ALT write phase 7.35 s against the CF-3300's 9.65; every FCB snapshot still byte-
      identical ([`blkio_wrblkdir.out`](../../scratchpad/blkio_wrblkdir.out)). 🔮 Predicted 110-130 s: hit. **BUT ALT1.BIN NOT WRITTEN --
      wrblkalt-acceptance RED, and it is a real bug the per-call update was hiding:** the
      exerciser FMAKEs ALT1 and ALT2 and alternates WRBLKs; FMAKE sets the GLOBAL
      BDOS_WRMODE, so the FIRST FCLOSE takes bdos_close_write, which writes the entry from
      the GLOBALS (FAT_FILESIZE / FWR_DIRSEC -- the last-used file's, ALT2's), never the
      closed FCB's own. And close-from-the-FCB for every written file is not safe either:
      WRSEQ's writeback (wrseq_wr_writeback) marks the FCB written but keeps the size in
      globals, not FCB +16. ➡️ **The design it needs:** the FCB authoritative for every
      writer (WRSEQ keeping +16 as WRBLK / WRRND already do), then ONE close rule -- write
      the closed FCB's entry from the FCB. Witnesses: wrblkalt-acceptance (two FCBs),
      bdos-acceptance, the roundtrip probe, tests/test_wrseq_position.py.
      🅿️ **PARKED ON 17 B (2026-11-08), [`wrblkdir_wip.patch`](../../scratchpad/wrblkdir_wip.patch).** Built further: (1) the per-call
      update dropped and `cr_dir` (close_read: wrblk_fcbstate + fat_dir_update from the FCB);
      (2) `bdos_close_wm` -- with BDOS_WRMODE set but NOTHING written sequentially
      (BDOS_WRCLUS = 0) the close goes the FCB way, so a WRSEQ file keeps its globals path.
      That made ALT1 get an entry -- with ALT2's cluster: 🔴 fat_dir_update writes FWR_FIRST /
      FWR_BYTES (= BDOS_WRFIRST $ED56 / BDOS_WRBYTES $ED5B), NOT the FAT_FIRSTCLUS /
      FAT_FILESIZE wrblk_fcbstate loads, and those still hold the LAST-written file's. (3)
      cr_dir must copy FAT_FIRSTCLUS -> BDOS_WRFIRST and FAT_FILESIZE -> BDOS_WRBYTES (not
      contiguous: 17 B) -- and no disk.rom hole holds 17 B any more (the largest outside the
      FDC window is 15; cr_dir fills the $782B one, bdos_close_wm the $7F7C one).
      ➡️ A carve of >= ~20 B first (a D-DISKCARVE round), then land (1)-(3) together and run
      wrblkalt / bdos / roundtrip. Measured with (1) alone: WSEEK 193.6 -> 106-108 s.
      ✅ **LANDED 2026-11-08 -- NO CARVE NEEDED.** (3) split in two: `cr_copy1` (FAT_FIRSTCLUS ->
      BDOS_WRFIRST, 9 B, the $5FD6 hole before the $5FE5 pin) jumps to `cr_copy2` (FAT_FILESIZE
      -> BDOS_WRBYTES, then `jp fat_dir_update`, 14 B, the runtime hole's last 14 B); cr_dir
      calls cr_copy1 where it called fat_dir_update. 🔮 Predicted every file AS EXPECTED and
      WSEEK ~106 s: **HIT** ([`blkio_wrblkdir3.out`](../../scratchpad/blkio_wrblkdir3.out)) -- ALT1 [372], ALT2 [373], OUT, OUT2, BIGW
      all as written on both machines, FCB snapshots byte-identical, **WSEEK 193.6 -> 107.7 s
      (6.3x -> 3.5x the CF-3300)**, the ALT write phase 7.75 s against its 9.65.
      (blkio_wrblkdir.out was overwritten by the second run; the first experiment's
      106.3 s / ALT1 NOT WRITTEN reading is in commit ad6f298a.)
      🎯 For the C-BIOS port goal ([[disk-core-portable-to-cbios]]): a written file's entry is
      now written from ITS OWN FCB at close, not from the last-used file's globals.
      📏 **WHAT IS LEFT, LOGGED (2026-11-08, after D-WRBLKDIR):** [`fdccount_1108.out`](../../scratchpad/fdccount_1108.out): the 32 KB
      phase now issues **257 writes / 292 reads** here against the CF-3300's 72 / 78 (🔮 ~256 / ~355:
      writes HIT, reads MISSED low). [`fdclog7_probe.py`](../../scratchpad/fdclog7_probe.py) logs each command's track / sector
      registers ([`fdclog7_1108.out`](../../scratchpad/fdclog7_1108.out)). Per 1 KB cluster (4 calls of 256 B): the **CF-3300** writes
      each data sector once and reads it once (2 W + 2 R), and touches NO FAT sector during the
      run; **ours** reads-modifies-writes the data sector EVERY call (4 R + 4 W) and, per
      allocation, ~6 FAT reads (the free scan re-reads s3 / s2 / s3 -- the buffer is "clean", so
      fac_cacheinit trusts nothing) + 4 FAT writes (the mark, then the link, each to both
      copies). So the two levers are about equal: (a) the data sector held across calls
      (D-PUTCACHE's shape), (b) the FAT sector held dirty across calls until FCLOSE / a seek
      away (D-RECSLOW's bit 1, across calls instead of within one). 🔴 **BOTH NEED BYTES:**
      `check_disk_walls.py` shows NO usable hole left (the only run >= 16 B is the FDC window).
      ➡️ **NEXT: a D-DISKCARVE round** (its candidate list: the fdc_read_phys / fdc_write_phys
      prefix ~34 B, the getalloc / fat_have_free_cluster scan bodies ~60 B), then (b), then (a).
      💰 **D-DISKCARVE2 (2026-11-08): +44 B.** fdc_read_phys / fdc_write_phys (disk/driver.asm)
      shared three pieces, now once: `fdc_prep` (DI, select drive / side / motor, settle, two
      tries), `fdc_seek`, `fdc_again` (the retry countdown; on the last failure it drops the
      caller's return and ends at fdc_io_done, as both tails did). The helpers sit in the read
      side's pad before $436C; the write side's freed bytes join its 7 B before $4462:
      `check_disk_walls.py` now lists **a 44 B usable hole at $4436** (before: none >= 16 B
      outside the FDC window). 🔮 ~28 B: the saving was ~28; the hole is larger because it
      merged with the old 7 B and the read pad's slack.
      ✅ **D-WRBLKFAT (2026-11-08): lever (b)'s within-call half -- 3.5x -> 3.0x.** WRBLK's chain
      extension took frl_ext's shape (D-RECSLOW): `wroe_ext` (disk/driver.asm, 35 B of the new
      $4436 hole) defers the new cluster's EOC mark AND the link (frl_defer ->
      fat_write_fat_entry_hot), then writes the sector to both FATs once (frl_flush); a failure
      ends through frl_xfail. Nothing outlives the call. wroe_need_extend (disk/kernel.asm) keeps
      only the first-cluster bookkeeping (19 B back before $75A5). 📏 [`fdccount_wfat.out`](../../scratchpad/fdccount_wfat.out): phase 7
      **257 W / 292 R -> 195 / 261** (🔮 ~193 / ~260: HIT); [`blkio_wfat.out`](../../scratchpad/blkio_wfat.out): every file AS
      EXPECTED on both machines, FCB snapshots byte-identical, **WSEEK 107.7 -> 93.45 s (3.0x
      the CF-3300)**. ➡️ Left: the free scan's ~4 FAT reads an allocation (the hint is reset per
      call, M30, and a clean FAT_MBUF is not trusted -- WRBLK's multiply scratch WRBLK_MUL* is
      WBUF+500..511, INSIDE FAT_MBUF, so nothing FAT-shaped survives a call), and (a) the data
      sector's read-modify-write every call.
      📏 **THE READ SIDE, LOGGED (2026-11-08):** `FDCLOG_PHASE=5` [`fdclog7_probe.py`](../../scratchpad/fdclog7_probe.py) ->
      [`fdclog5_1108.out`](../../scratchpad/fdclog5_1108.out) (the 32 KB SEEK read, 256 B RDBLKs): the **CF-3300 reads each data
      sector ONCE** and no FAT sector; **ours reads every data sector TWICE** -- a call starting
      mid-sector goes through `k47b2_mid` (disk/kernel.asm), whose fat_read_file_sector re-reads
      what the previous call left in SECTOR_BUF -- plus one FAT sector each cluster
      (fat_next_cluster). Halving the data reads is the read side's lever (SEEK 3.1x).
      🔴 **DESIGNED AND NOT BUILT -- THE TAG IS NOT SAFE WITHOUT THE W4 AUDIT.** The cheap shape
      ("read_sector hits when SECTOR_BUF still holds the sector RDBLK left; the tag set at
      RDBLK's exit, cleared at `dskio` entry, which every physical transfer -- the page-1 bounce
      through SECTOR_BUF included -- passes") is WRONG for writers that FILL SECTOR_BUF WITHOUT
      I/O: the BDOS sequential write accumulates there (BDOS_WRBUFLEN), and main's channel code
      shares it as FSECTOR_BUF. RDBLK on A, WRSEQ on B (buffered, no I/O), RDBLK on A mid-sector
      would serve B's bytes. Every SECTOR_BUF / FSECTOR_BUF writer must drop the tag (76 code
      lines; spec-diskwcache.md's W4 calls it "the widest audit, and it comes last"). ➡️ Picked
      up only with that audit; the FAT-per-cluster read waits on the same kind of tag for
      FAT_MBUF.
      📋 **THE W4 AUDIT, ROUND 2 (2026-11-14, [`dbuf_audit2.md`](../../scratchpad/dbuf_audit2.md)):** 11 sites change the buffer's
      bytes, a missed alias (BD_LINE, the boot date prompt), and the reads that bypass
      read_sector (the page-1 bounce, a direct dskio_rd overlapping the buffer). 🧩 **THE DESIGN
      IT POINTS TO -- the tag CLEARED IN dskio, not at read_sector:** every writer whose path did
      any disk I/O after RDBLK's read is then safe by construction (fat_media, SFIRST / SNEXT,
      the read-modify-writes and their failure paths); explicit clears only where bytes change
      with NO I/O -- the sequential writer's dta_rec, fip_store, bb_mark, the boot date line,
      dout_write's first half. Tag 0 = invalid (sector 0 is never an RDBLK data sector). ➡️
      Price it (dskio's clear must keep A / F / BC / DE / HL: ~8 B; five clears; the set and test
      in k47b2_mid) against the room below, then build with a gate row per explicit clear.
      💰 **PRICED (2026-11-14): ~65 B -- MORE THAN THERE IS.** The test and set belong in
      fat_read_file_sector's OWN entry (basic/fat-prim-body.inc: frs_head -> DE; DE = the tag
      -> skip the read; else read_sector_nh, then tag := DE), NOT in frs_to, whose HL is
      LOAD's program area (D-LOADDIRECT) -- ~22 B over today's 3 B entry, and every channel /
      LOAD-buffer reader through it gains the hit too; dskio's clear keeping A / F / BC / DE /
      HL ~8 B; five explicit clears ~6-8 B each, each in its own region. Against D-DISKCARVE3's
      32 + 24 B. ➡️ One more carve round first (diskngram.py: the de_name / de_ext loop pair ~4 B,
      fat_find / fat_dir_create's head ~3 B are small; read the 9-14 B pairs), or a cheaper
      clear rule (e.g. the tag cleared at the sequential writer's and the channel writer's
      ENTRIES -- one per writer, not per byte).
      ✂️ **D-DISKCARVE3 (2026-11-14): +26 B of disk ROM, for this.** (1) SFIRST is "cursor := 0,
      then SNEXT" (sfirst_body falls into snext_body: 13 B; the one change -- a SFIRST whose mount
      FAILS leaves the cursor 0, where it kept the old one); (2) boot_rd (disk/runtime.asm, in
      front of $7F7C): drive A's boot-sector read + signature test stood twice, in init.asm's
      boot_disk_go and in hk_system; both now call it, A / F at the boot call as before. Room
      after it (2026-11-14): 32 B in front of $5FE5, 24 B in front of $41EF (from 0 runs of
      16+). Unit tests, bdos / callsystem / bootenv / diskbasic / dosbasic acceptance green.
      🔬 From the code: `wrblk_body` runs `fat_mount` + `fat_find` +
      `fat_dir_update` every call, each a trip to track 0 and back. RDBLK only
      mounts when the geometry was never read. FCB +25 (filled since
      D-WRBLKSEEK (b)) gives the directory entry's location without a find.
      ⚠️ `fat_mount` also resets the allocation hint per operation (M30): a
      WRBLK that skips it must reset FAT_ALLOCHINT itself.
      📏 The row exists: `wrblkalt-acceptance`'s `--wseek`/`--seek` ratios.
      🤖 **AUTONOMOUS** — the reference settles it.
      🟡 **STEP 1 SHIPPED (2026-10-08): WRBLK NO LONGER MOUNTS OR FINDS PER CALL --
      8.8x -> 6.6x.** `wrblk_body`'s mount + find + entry recovery (37 B of the
      `$607B..$75A5` region, which has no room) became one call to
      `wrblk_fcbstate` in the fill beside `hk_fmake`: the geometry mounted only
      when never read (RDBLK's rule), M30's hint reset as fat_mount reset it,
      FAT_FIRSTCLUS from FCB +26, FAT_FILESIZE from +16..19 (wrblk_fcb_keep keeps
      both), the entry from +25 (close_read's arithmetic). 32 KB in 256 B blocks:
      **271.9 -> 202.8 emulated s** against the CF-3300's 30.95; every FCB snapshot
      still byte-identical, all six files as written
      ([`blkio_before.out`](../../scratchpad/blkio_before.out),
      [`blkio_after.out`](../../scratchpad/blkio_after.out)). 🔮 Predicted ~5x: PARTLY
      MISSED. ⚠️ No knife: the gate asserts "within 10x" only, so the old code
      passes it too -- the ratio reading is the witness, not a row that flips.
      ➡️ **What is left per call:** the data sector's read-modify-write and
      `fat_dir_update` (a directory read + write) EVERY call. Whether the CF-3300
      rewrites the entry per WRBLK or only at FCLOSE has to be MEASURED before
      deferring it -- through the FDC's I/O registers or the image between calls,
      not by stepping its ROM. The read side (3.1x) is unchanged.
      📏 **MEASURED THE SAME NIGHT -- THE REFERENCE WRITES EACH SECTOR ONCE AND
      DEFERS THE REST.** [`fdccount_probe.py`](../../scratchpad/fdccount_probe.py)
      counts WD2793 sector COMMANDS (a write watchpoint on the command register,
      `$7FB8` on both machines -- an I/O register, the permitted side) binned by
      the exerciser's phase byte ([`fdccount_run.out`](../../scratchpad/fdccount_run.out)).
      The 32 KB write (128 WRBLKs of 256 B = 64 data sectors, phase 7):
      | | write commands | read commands |
      |---|---|---|
      | CF-3300 | **72** | 78 |
      | ours | **384** | 483 |
      So the CF-3300 writes every 512 B data sector ONCE and its directory / FAT
      updates add ~8 more -- not per call. Ours does ~3 writes and ~4 reads a
      CALL: the data sector's read-modify-write, the directory entry, the FAT.
      🔴 An instrument fault of mine first: the counter watched Philips' FDC
      address (`$7FF8`) and read ZERO commands on both; watching `$7F80..$7FFF`
      found the National mapping (`$7FB8` command, `$7FBB` data).
      ➡️ **STEP 2 IS A WRITE-CACHE LAYER, A DESIGNED SLICE:** keep a half-filled
      data sector across calls (write it when full, at a seek away, or at
      FCLOSE), and defer `fat_dir_update` and the FAT copies to FCLOSE, as the
      reference's counts imply. ⚠️ That changes what is on the medium between
      calls -- a program that never closes loses the size on the reference too,
      which is the faithful face, but bdos-acceptance and the roundtrip probe
      must be re-read for any mid-sequence image comparison before building.
      📐 **DESIGNED 2026-10-10 — [`docs/spec-diskwcache.md`](../../docs/spec-diskwcache.md),
      for BASIC's sequential writer first.** [`fdcseq_probe.py`](../../scratchpad/fdcseq_probe.py)
      logs each WD2793 command with its track / sector registers (I/O, both
      machines; [`fdcseq_run.out`](../../scratchpad/fdcseq_run.out)) on D-FDCDI's
      PRINT# + CLOSE workload. The CF-3300 writes each data sector ONCE (+ a
      verify read) and touches the FAT and directory only at CLOSE; ours, per
      cluster, re-reads the BOOT sector (`fat_total_clusters`), reads the FAT
      sector 3× and writes BOTH copies twice (mark, then link), and per data
      sector writes / reads back / writes (`dout_write`'s two 256 B halves).
      Four slices, safest first: **W1** the cluster count kept from the mount;
      **W2** the FAT sector kept across calls (a tag every `FAT_MBUF` writer
      clears); **W3** the FAT written at CLOSE; **W4** the data half-sector kept.
      ✅ **W1 SHIPPED 2026-10-10:** the cluster count is `fat_mount`'s, kept in
      `FAT_ROOTSECS`'s cell (root sectors = FIRSTDATA − FIRSTROOT, computed by
      `fat_rootsecs`) — no new RAM, −4 B sub p1, −20 B disk.rom. 28 → 23 READs on
      the workload, every per-cluster `R0/1` gone (predicted exactly,
      [`fdcseq_w1.out`](../../scratchpad/fdcseq_w1.out)). Gate `wcache-acceptance`
      ([`disk_probe_wcache.py`](../../probes/disk/disk_probe_wcache.py),
      [`wcache_gate_w1.out`](../../scratchpad/wcache_gate_w1.out)): the file reads back
      whole on both, zerobas within 23 READs / 36 WRITEs; 🔪 K-WC1 (the boot read
      restored) → exactly `zb-reads` ([`wcache_knives.out`](../../scratchpad/wcache_knives.out)).
      ✅ **W2 SHIPPED 2026-10-10, narrower than designed — no audit needed:** the
      two re-reads are WITHIN one allocation (scan → mark → link), where nothing
      else touches `FAT_MBUF` and every FAT routine keeps `(FAT_FATSEC)` naming
      what it holds. `fat_write_fat_entry_hot` skips the read when the entry's
      sector is that one; used by `fac_found` and `ffds_alloc`'s link only. 23 →
      14 READs (predicted 13: MISSED by one, the first cluster has no link),
      [`fdcseq_w2.out`](../../scratchpad/fdcseq_w2.out), [`wcache_gate_w2.out`](../../scratchpad/wcache_gate_w2.out)
      — fewer READs than the CF-3300's 16 (its verify reads). disk.rom's
      body region (pinned at `$75A5`) had no room even for a 4-byte split, so the
      hot entry carries its own sector arithmetic in disk/fat.asm's `$47C1` fill;
      the sub-ROM's copy costs 62 B of sub page 1. 🔪 K-WC2 → exactly `zb-reads`
      ([`wcache_knives_w2.out`](../../scratchpad/wcache_knives_w2.out)).
      ✅ **W3a SHIPPED 2026-10-11 — one FAT write per chain extension:** the mark
      waits (`FAT_DEFER`, `$E5AC` in both maps, measured free —
      [`ramfree_e5ac.out`](../../scratchpad/ramfree_e5ac.out)), and the link writes the
      sector once with both entries; a link in ANOTHER sector writes the held one
      out first. 36 → 28 WRITEs (predicted exactly,
      [`fdcseq_w3a.out`](../../scratchpad/fdcseq_w3a.out)). New gate rows on a disk
      whose clusters 9..339 are pre-marked used, so a 3-cluster file takes 340,
      341, 342 across FAT sectors 0/1: `content-x` (read back) and `fat-x` (the
      chain read from the IMAGE: `340>341>342 EOC` on both,
      [`wcache_gate_w3a.out`](../../scratchpad/wcache_gate_w3a.out)). Knives
      ([`wcache_knives_w3a.out`](../../scratchpad/wcache_knives_w3a.out)): K-WC3 (no
      deferral) → `zb-writes`; K-WC4 (no flush before the other sector loads) →
      `fat-x`; K-WC2 now moves `zb-writes` too (its always-read path also flushes
      the held sector). 🔴 **K-WC4's FIRST RUN MOVED NOTHING, AND THAT WAS THE
      ROW BEING BLIND:** a lost mark is overwritten by the next link, and a lost
      mark on the LAST cluster reads back fine (readers stop at the size) — only
      the FAT shows it, so the row now reads the chain from the image and the file
      ends on the deferred cluster. Sub page 1 125 → 88 B. D-FDCDI's typed keys re-read after W2:
      9–10 of 22 at 3/5/8 s, unchanged (predicted a small rise: MISSED — the
      masked time is in the writes), and the workload's time now matches the
      CF-3300's ([`fdcdi_typeahead_w2_d3.out`](../../scratchpad/fdcdi_typeahead_w2_d3.out)).
      📏 **RE-READ AFTER W3a (2026-10-11):** the workload runs 10.8–11.2 s here
      against the CF-3300's 11.8, and typed keys kept rose to 10 / 10 / 13 of 22
      at 3 / 5 / 8 s (predicted 11–13: partly hit;
      [`_d3`](../../scratchpad/fdcdi_typeahead_w3a_d3.out),
      [`_d5`](../../scratchpad/fdcdi_typeahead_w3a_d5.out),
      [`_d8`](../../scratchpad/fdcdi_typeahead_w3a_d8.out)). 42 data/FAT commands
      against the CF-3300's 32: what still separates the key rates is the
      driver's masked DRQ wait per command, not the count.
      ⏸ **W3b / W4 PARKED** (spec §3: each needs a cross-call cache and a
      shared-buffer audit for 8–18 more commands) — pick up if speed or D-FDCDI
      asks again. D-FDCDI's own remaining lever is the DRQ-wait masking (the
      reverted idea in its block).
