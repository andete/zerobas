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
