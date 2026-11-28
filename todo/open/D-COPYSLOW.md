- [ ] **A LARGE COPY UNDER MSX-DOS TAKES 4-6x THE CF-3300'S TIME, AND THE RATIO GROWS WITH THE FILE (D-COPYSLOW, found
      2026-11-27 under D-P1WRITE).**
      🎚️ TIER 2 — reasonable time: copying a file at A> is the plainest thing MSX-DOS does.
      🤖 **AUTONOMOUS** — black box: emulated seconds from the typed COPY to the prompt, the CF-3300 the reference.
      MEASURED (scratchpad/copytime_probe.py -- disk_probe_dossession's own driver, snapshots stamped by machine time;
      zerobas DISK machine, the copies byte-identical on both, after D-P1WRITE):
        32 KB  (MSXBUNSE.ROM):  CF-3300 21.8 s,  zerobas  86.5 s  (4.0x)  [AE_copytime32.out](../../scratchpad/AE_copytime32.out)
        128 KB (MSXBUDIC.ROM):  CF-3300 68.8 s,  zerobas 407.3 s  (5.9x)  [AE_copytime128.out](../../scratchpad/AE_copytime128.out)
      The ratio GROWS with the size: a per-cluster cost that depends on the file's length (a FAT-chain walk from the
      first cluster on each write? a FAT re-read per cluster?) rather than a constant overhead. MEASURE where the time
      goes first (DSKIO calls and sectors per copy, both machines -- the FDC's command traffic is readable).
      Related: D-F37DNODISK's nested note (SEQWRITE writes through: 153 s against 93 s for a SEQREAD/SEQWRITE copy).
      ACCEPTANCE: the 128 KB COPY within ~1.5x the CF-3300's, the copy byte-identical (the session's bigbytes row).
      📏 **WHERE THE TIME GOES (2026-11-27,** scratchpad/copytime_probe.py with the FDC's command register watched at every
      mirror of $7F80-$7FBF -- hardware traffic, no PC; [AE_copyslow_fdc32.out](../../scratchpad/AE_copyslow_fdc32.out), [AE_copyslow_secs.out](../../scratchpad/AE_copyslow_secs.out)): the 32 KB COPY issues, on
      zerobas, 380 seeks / 241 reads / 139 writes -- ONE SEEK PER SECTOR COMMAND (with verify: the ID it reads lets the
      wanted sector pass) -- against the CF-3300's 5 / 24 / 9 (its counts may miss multi-sector traffic; not relied on).
      And most of zerobas's sector commands are the FAT: track 0 physical sectors 2 / 3 (FAT copy 1) read 49 + 55 times,
      written 8 + 28, and FAT copy 2 (sectors 5 / 6) written 8 + 28 -- for ONE file. The file's cluster entries straddle
      FAT sectors 2 and 3, and the engine caches ONE FAT sector (FAT_MBUF), so every switch evicts the other: a thrash,
      and every FAT change is written through to both copies at once.
      ✅ STEP 1 (2026-11-27): fdc_seek skips the seek when the Track register already holds the track (moved to the
      $75A5 hole for room): 380 -> 128 seeks, 86.8 -> 82.8 s ([AE_copyslow_fdc32_fix.out](../../scratchpad/AE_copyslow_fdc32_fix.out); 🔮 "25-35 s": MISS -- the seeks
      were not the cost, the 380 sector commands and their rotational waits are).
      ➡️ STEP 2 (a design decision, not done): a FAT cache that holds the whole FAT (720 KB disk: 3 sectors, 1.5 KB) or
      at least two sectors, and FAT writes deferred to FCLOSE / a flush -- the FAT engine is SHARED with the sub-ROM
      (D-FATENG Option 2), and RAM for it is not free.
      🧭 JOOST 2026-11-27: "Size it first" -- write up the options (RAM available, 2 sectors vs the whole FAT, deferred
      writes and when to flush: FCLOSE / disk change / DSKRST, what the CF-3300 does visibly -- its FAT writes per copy,
      measured -- and the expected speed-up), then he chooses. Do not build before that.
      📐 **SIZING (2026-11-27, Joost "Size it first"; zerobas-only call chains, scratchpad/fatpath_probe.py --
      [AE_copyslow_fatpaths.out](../../scratchpad/AE_copyslow_fatpaths.out)).** The FAT commands of the 32 KB COPY come from three paths:
        (a) CHAIN RE-WALKS from the file's first cluster to find the current one -- fat_advance from frs_head (the
            source's reads: 31 + 6) and from wroe_incluster (the copy's writes: 25 + 6): ~68 reads. The cost per sector
            grows with the position in the file -> quadratic: why 4.0x at 32 KB became 5.9x at 128 KB.
        (b) the FREE-CLUSTER SCAN at each extension -- fac_loop from wroe_ext: 26 + 5 + 2 reads.
        (c) FAT WRITE-THROUGH to both copies at each extension -- fwba_loop from wx_out: 25 + 25 + 6 + 6 + 2 + 2 writes.
      OPTIONS (no new RAM for any; the engine is shared with the sub-ROM -- each needs the BASIC side checked too):
        A. keep the RUNNING CLUSTER per open file and continue from it (MSX-DOS FCBs already carry one: +28 the current
           cluster, +30 its index -- zerobas fills them; the CF-3300's FOPEN does too). Removes (a). Biggest win; also
           what makes the time linear in the file size.
        B. DEFER FAT writes to FCLOSE / DSKRST / a disk change, reusing FAT_DEFER (D-WCACHE W3a, today BASIC's chain
           extension only). Removes most of (c): ~66 writes -> 4 (two sectors x two FATs). Risk: a crash or a disk
           swap before close leaves the FAT stale -- the CF-3300's own behaviour on that is NOT measured yet (needs a
           black-box test: pull the disk mid-copy, read the image).
        C. start the free-cluster scan at the last allocated cluster (FAT_ALLOCHINT exists; check why fac_loop still
           reads per extension -- likely the deferred / single-buffer interplay). Removes most of (b).
      ESTIMATE: A + B + C leave ~64 data reads + 64 data writes + ~10 FAT / directory commands ~= 140 commands (380 today)
      -> the 32 KB COPY ~30 s (82.8 s today; CF-3300 21.8 s) and LINEAR -- 128 KB ~120 s (407 s today; CF-3300 68.8 s).
      The rest of the gap is per-sector rotational waits the CF-3300 seems not to pay (its command counts are not
      reliable to us -- multi-sector traffic?). A alone: ~380 -> ~300 commands, but the 128 KB case improves most.
      🧭 JOOST 2026-11-27: "A first" -- build A (the running cluster), re-measure, then decide on B / C.
      🔴 CORRECTION (same day, before building): (a) is NOT a re-walk from the first cluster. frs_head / fat_advance step
      ONE cluster from FAT_CURCLUS (the running cluster zerobas already keeps); the 31 / 25 reads are one per cluster
      (32 KB = 32 one-KB clusters). Read from call-chain labels, not the code -- "quadratic" and option A as written were
      wrong; Joost's "A first" was asked on that premise. What the counts show is the ONE FAT buffer shared by both files:
      the source's next-cluster entries (mostly FAT sector 2) and the copy's free-scan / link / step (mostly sector 3)
      evict each other at every cluster -- ~5 FAT commands per cluster, linear in the size.
      REVISED OPTIONS (no new RAM unless said):
        A'. the writer steps to the cluster it has just allocated without reading the FAT (it knows the number): ~31 reads.
        D.  the reader prefetches its chain's next ~16 cluster numbers whenever it reads a FAT sector (a 32 B table; a
            142 B run is free at $EDBF): most of the ~37 source reads.
        B / C as above (deferred FAT writes; the free-scan start).
      🧭 JOOST 2026-11-27 (asked again on the corrected sizing): "A′ + D" -- both read-side fixes, re-measure, then B.
      ✅ A' BUILT 2026-11-27: wroe_step (disk/kernel.asm, in the $5C11 pad) -- when the writer's cluster is the one this
      BDOS operation allocated last (FAT_CURCLUS + 1 = FAT_ALLOCHINT; the hint is the allocation + 1, reset to 2 by every
      fat_mount), its entry is the end-of-chain just written: no FAT read. No new RAM. 32 KB COPY: reads 241 -> 209,
      82.8 -> 76.5 s, the copy byte-identical (AE_copyslow_aprime.out; 🔮 "~210 reads, ~-7 s": HIT); the copy's step reads
      (wroe_incluster, 25 + 6) gone from the path histogram (AE_copyslow_fatpaths2.out). bdos / bdos-cfhost / seqmix /
      wrblkalt / dossession / nobasic / diskbasic / bdosf37d acceptance, unit tests green; knife re-pinned; disk corpus
      identical. ➡️ D (the source's read-ahead) needs a 32 B table: RAM first -- $EDBF-$EDFC has no name in any ROM but
      sits under BASIC_WS_CEIL, NOT a safe assumption; find atlas-verified free RAM before building.
      📏 **WHAT THE CF-3300 DOES (2026-11-28, Joost "Do we know what reference does?"; [AE_copyslow_byarea.out](../../scratchpad/AE_copyslow_byarea.out)):** its
      driver issues most commands through the PAGE-2 mirror of the FDC registers ($BFB8-$BFBF; the interface maps
      $4000-$BFFF) -- the page-1-only watch saw 24 reads / 9 writes and was blind. Both mirrors, the 32 KB COPY by area:
                        CF-3300   zerobas (after A')
        data read         128        128
        data write         64         64
        FAT read           12         72
        FAT write           6         72
        track 0 other    10 + 2     9 + 3
      The data traffic is IDENTICAL; the whole gap is the FAT. The reference keeps the FAT in RAM and writes it back
      rarely -- both read caching (D / C) and deferred writes (B). So B is "in line with reference", not a risk we would
      be adding on our own; what the CF-3300 leaves on disk if the disk is swapped mid-copy is still unmeasured.
      ROOM: 269 B free (largest hole 43 B); D alone ~85 B.
      📏 **WHERE THE CF-3300 KEEPS ITS FAT (2026-11-28, Joost "We first need to figure out where reference caches
      this"; [fatdest_probe.py](../../scratchpad/fatdest_probe.py), [AE_fatdest.out](../../scratchpad/AE_fatdest.out)):**
      while each FAT-sector read command runs, a RAM write watch records only the ADDRESSES written, as a 64-byte-block
      histogram (no byte read, no PC). Validated on zerobas: its reads land at $E8AD-$EAAC = SECTOR_BUF. The CF-3300's
      12 FAT reads, in time order, during the 32 KB COPY on the 720 KB test disk:
        0      sector 2       -> $EF95-$F194 (the 512 B directly under its DPB at $F195)
        1-3    sectors 2,3,4  -> $E595-$E794, $E795-$E994, $E995-$EB94: THE WHOLE FIRST FAT COPY, 1536 B, read once
        4-5    sectors 2,3    -> $EB95-$ED94 (one 512 B buffer, both times)
        6-11   sectors 2..7   -> nothing stored (<= 111 writes, the stack / interrupt noise): one per FAT sector of
                                 both copies, in order -- matches read-back VERIFIES of its 6 FAT writes (unconfirmed)
      So the reference caches the FAT as ONE CONTIGUOUS 1536 B IMAGE at $E595, inside the claim zerobas also takes
      (both HIMEM $DE77 at DOS); its 512 B buffers sit at $EB95 / $ED95 / $EF95. zerobas's SECTOR_BUF ($E8AD-$EAAC) and
      its FAT state ($ECAD-...) occupy that same span with a different layout: following the reference = MOVING zerobas's
      buffers to the CF's places (a RAM-address move -> FULL gate), not finding new RAM. Unmeasured: whether the image
      size follows the disk's FAT (3 sectors here) or a fixed maximum; whether the 6 no-store reads are verifies.
      🙋 Joost to decide the layout before anything is built.
      🧭 JOOST 2026-11-28: "Measure more, then plan" -- address-only, before any code: (1) does the FAT image follow the
      disk's FAT size (a 360 KB disk, 2-sector FATs) or a fixed maximum; (2) are the 6 no-store reads verifies (the
      command order around each FAT write); (3) when the FATs are written back. Then a cell-by-cell move plan to him.
      📏 **MEASURED MORE (2026-11-28, same probe + every FDC command in order; [mk360_dsk.py](../../scratchpad/mk360_dsk.py) builds a
      360 KB disk, 2-sector FATs; [AE_fatdest.out](../../scratchpad/AE_fatdest.out)).** (FDC sector numbers are 1-based per track:
      720 KB FAT1 = sectors 2-4, FAT2 = 5-7; 360 KB FAT1 = 2-3, FAT2 = 4-5, root from 6.)
        (1) THE IMAGE IS FIXED AT $E595, SIZED FOR THE LARGEST FAT: on 360 KB the 2 FAT sectors land at $E595-$E994;
            on 720 KB the 3 at $E595-$EB94, which ends exactly where the next 512 B buffer ($EB95) begins.
        (2) THE NO-STORE READS ARE VERIFIES, PER FAT COPY: the COPY's tail is  E1 D1  W2 W3 W4 R2 R3 R4  W5 W6 W7 R5 R6 R7
            (720 KB; 360 KB: W2 W3 R2 R3 W4 W5 R4 R5) -- the directory sector written and read back, then each FAT copy
            written whole and read back whole. 🔮 "W2 R2 W3 R3 ...": PARTIAL MISS (deferred to the end: hit; per copy, not
            per sector).
        (3) WRITTEN BACK ONCE, AT THE END: no FAT write during the data phase on the CF-3300; zerobas writes R2 W2 W5
            (read, then both copies) at EVERY cluster.
      So the CF-3300's buffers below its DPB: $E595 FAT image (1536 B) · $EB95 sector buffer (directory on 360 KB) ·
      $ED95 file data (D-FATBUF 2026-09-18) · $EF95 the mount's first-FAT-sector read (media check).
      ALSO SEEN, NOT CHASED: the CF-3300 reads the source in runs of 18 sectors per track (r*18 between steps) and all
      64 before any write; zerobas alternates r w r w -- it reads each destination sector before writing it (the
      read-or-extend). Both total 128 data reads, but the reference's runs cost far fewer rotations: likely most of
      the rest of the gap once the FAT is cached.
      ➡️ NEXT: the cell-by-cell move plan to Joost (his ruling), nothing built before he approves it.
      🧭 JOOST 2026-11-28: "Lets make sure we get as much info as possible before we start writing any code to fix
      this" -- NO CODE until every question below is measured (address-only, clean room) or explicitly waived by him:
        Q1  where the CF-3300 keeps its SMALL state cells (clusters, positions, flags) -- a write-address histogram
            over $DE77-$F37F for a whole COPY (zerobas's ~1 KB of cells sit inside the CF's buffer spans)
        Q2  what the CF-3300's 64 data reads AFTER the data writes are (destination re-read? track numbers)
        Q3  when the CF-3300 re-reads its FAT image: a second COPY / DIR straight after; after a disk swap
        Q4  what the CF-3300 leaves on disk when the disk is swapped mid-COPY (the deferred-write risk, option B)
        Q5  whether the same buffers serve other operations: a sequential write, delete, rename, Disk BASIC SAVE / LOAD
        Q6  drive B: on the one drive -- one FAT image shared, or one per drive
      📏 **Q1 + Q2 MEASURED (2026-11-28, [cfcells_probe.py](../../scratchpad/cfcells_probe.py), [AE_cfcells.out](../../scratchpad/AE_cfcells.out); every RAM write in
      $DE77-$F37F for a whole COPY, per 16 B block, addresses only):**
        Q1  the CF-3300's small state lives ABOVE its buffers: $F1A0-$F1C8 (after its DPB at $F195) and the fixed area
            $F230-$F35F, plus one 16 B block at $E590 (just under the FAT image). NOTHING in $DE77-$E58F. Its data buffer
            ($ED95) is barely touched in a COPY (data moves straight to the DTA); its $EF95 buffer is busy in every phase.
            🔮 "the fixed area, little below $E595": HIT. zerobas, same COPY: its cells sit INSIDE the CF's buffer spans,
            and $EB95-$ED94 (its BDOS / RDBLK cells) takes 469,420 writes during the data reads -- per-byte bookkeeping
            in RAM, a CPU cost the CF-3300 does not have; a separate item to size.
        Q2  the CF-3300's 64 data reads after the writes are a READ-BACK OF THE DESTINATION: source r15-r18 (64), then
            w37-w41 (64), then r37-r41 (64), same tracks, same order. zerobas reads each destination sector BEFORE
            writing it (r37 w37 r37 w37 ...): equal counts, different reason, and per-sector alternation costs a
            rotation per sector.
      📏 **Q3 MEASURED (2026-11-28, [fatcache_probe.py](../../scratchpad/fatcache_probe.py), [AE_fatcache.out](../../scratchpad/AE_fatcache.out); COPY, DIR, COPY, disk SWAPPED, DIR, COPY):**
        the CF-3300's FAT image lives for ONE COMMAND, not the session: each of the three COPYs reads it again
        (12 FAT reads + 6 writes, identical every time) and each DIR reads it again (6 reads). 🔮 "read once, kept
        until the swap": MISS. A swap BETWEEN commands is therefore harmless on the CF-3300 -- and on zerobas: both
        said "File not found" on the swapped-in disk and wrote BIG3.ROM onto it correctly. zerobas: 72 / 8 / 67 / 3 / 72.
        So the cache to follow is PER-OPERATION (a COPY's whole run), with the write-back at its end.
      📏 **Q4 MEASURED (2026-11-28, [swapmid_probe.py](../../scratchpad/swapmid_probe.py), [AE_swapmid.out](../../scratchpad/AE_swapmid.out); the disk swapped after the COPY's 30th
      and, again, 10th data write, for a copy of the original with DUMP.BIN deleted so a stale write would show;
      baseline: test.dsk already has 31 lost clusters):**
        CF-3300: writes the remaining data sectors onto the new disk, seeks back for its read-back, issues ONE read
          (track 37 sector 8) and then NO FDC command for the rest of the wait (~3000 emulated s), no message, no
          prompt. Its FAT image and directory sector are NEVER written: the swapped-in disk keeps its own FAT and
          directory (31 lost, DUMP.BIN stays deleted); the first disk keeps an empty BIG.ROM entry. Same at write 30
          and 10. Whether that is a real hang or an artefact of openMSX swapping mid-command is NOT decidable without
          tracing the reference (clean room) -- recorded as seen.
        zerobas: "1 file copied"; the first disk +15 lost clusters (empty BIG.ROM entry), the swapped-in disk +18 lost
          clusters and no file -- it writes the FAT through at every cluster onto whichever disk is in.
        🔮 "the CF-3300 writes its stale FAT onto the new disk": MISS -- it writes nothing to track 0 after the swap.
        So deferring the FAT the CF's way adds no risk that zerobas's write-through avoids today: zerobas already
        leaks clusters on both disks and reports success for a file that exists nowhere.
      📏 **Q5 (MSX-DOS part) MEASURED (2026-11-28, [dosops_probe.py](../../scratchpad/dosops_probe.py), [AE_dosops.out](../../scratchpad/AE_dosops.out); COPY of a small file, TYPE, REN,
      DEL, DIR; every track-0 read's landing window):** the CF-3300 runs the SAME mount sequence in every operation:
      sector 2 -> $EF95 (media check), sectors 2,3,4 -> the image $E595 / $E795 / $E995, sectors 2,3 -> $EB95 too,
      directory sectors -> $EB95. The FAT is written back (both copies, each read back) only by COPY and DEL; REN
      writes ONE directory sector and NO FAT; TYPE and DIR write nothing -- so the write-back happens only when the
      image has CHANGED (a dirty flag). zerobas: everything through $E8AD / $EAAD. 🔮 "image every op, directory in
      $EB95, FAT written by COPY / REN / DEL": partial miss (REN writes no FAT). Disk BASIC SAVE / LOAD: still open.
      📏 **Q5 (Disk BASIC) + Q6 MEASURED (2026-11-28, [sessops_probe.py](../../scratchpad/sessops_probe.py), [AE_sessops.out](../../scratchpad/AE_sessops.out)):**
        Q5  the CF-3300's Disk BASIC (reached by `BASIC` at A>) uses the SAME mount sequence, image ($E595) and
            directory buffer ($EB95) as MSX-DOS: SAVE / LOAD / FILES. SAVE writes data, directory, and both FAT copies
            (each read back) before returning (SESS=basic3: 20 s of quiet after SAVE, every write inside the step).
            🔴 APPARATUS, CAUGHT: SESS=basic / basic2 had put the CF's SAVE writes in the NEXT step -- the driver's
            still-screen test (no prompt test for BASIC steps) fired while the CF's SAVE was silent for over a second;
            "the CF defers SAVE's writes" would have been a false finding. zerobas: SAVE writes one FAT sector per copy.
            🔮 "same buffers, only SAVE writes the FAT": HIT.
            Unexplained, not chased: a test.dsk copy with MSXDOS.SYS AND COMMAND.COM deleted host-side still came up
            at the MSX-DOS date prompt on BOTH machines.
        Q6  ONE FAT IMAGE PER DRIVE on the CF-3300: after the drive-B: prompt, B's FAT lands at $DF94-$E593 (1536 B,
            directly below A's at $E595); back on A:, A's is read again into $E595. 🔮 "one shared image": MISS.
            (zerobas's DOS_RESV_TOP is $DF93 -- the byte below B's image.) The same run showed zerobas listing B: with
            NO swap prompt -> filed D-DOSDRVBX (TIER 3).
      ✅ ALL SIX QUESTIONS MEASURED. The reference's design to follow, in one place:
        - per drive, a FAT image sized for the largest FAT (1536 B): A at $E595, B at $DF94;
        - 512 B buffers: $EB95 directory / FAT sectors, $ED95 file data (little used by COPY: data goes to the DTA),
          $EF95 the mount's first-FAT-sector (media) read;
        - small state above them: $F1A0-$F1C8 and the fixed area; nothing in $DE77-$DF93;
        - every operation re-reads the image (media check, then the whole FAT); it is written back -- both copies,
          each read back -- only when changed, at the end of the operation; the directory sector is written and
          read back the same way; data writes are read back after the whole file;
        - a mid-operation swap: the CF never writes its image to the other disk (it stalls; hang or artefact unknown).
      ➡️ NEXT: the cell-by-cell move plan to Joost, from this list. No code before he approves it.
