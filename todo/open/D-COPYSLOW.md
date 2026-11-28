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
            🔴 CORRECTED 2026-11-28: "a disk with MSXDOS.SYS and COMMAND.COM deleted still came up at the MSX-DOS date
            prompt" was MY MISREADING -- the bare `Enter date (--):` / `(M-D-Y):` is the DISK ROM's question before
            Disk BASIC starts (docs/concepts/disk.md), not COMMAND.COM's "Current date is ... / Enter new date:".
            Settled black-box ([bootwho_probe.py](../../scratchpad/bootwho_probe.py), [AE_bootwho.out](../../scratchpad/AE_bootwho.out); Joost asked "fixed locations?"): MSXDOS.SYS deleted,
            deleted with its sectors zeroed, or merely renamed -> Disk BASIC on both machines; COMMAND.COM renamed ->
            MSX-DOS's "Insert DOS disk" on both. Found BY NAME, not by position; the two machines agree.
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
      📏 SIZED 2026-11-28 for the plan: inside the CF-3300's buffer spans zerobas keeps its 2 sector buffers, 73 disk-ROM
      state cells (~350 B: $ECAD-$EDBD, $EFDA-$F022) and 66 zerobas-BASIC Disk BASIC cells (~700 B: $EDB9-$F09D); the
      CF-3300's own state is ~41 B ($F1A0-$F1C8) plus the fixed area, which zerobas already fills. No reference-shaped
      place for our cells exists yet. 🧭 JOOST 2026-11-28: "Measure Disk BASIC first" --
        Q7  where the CF-3300 keeps Disk BASIC channel state (MAXFILES 2, OPEN / PRINT# / CLOSE / INPUT#);
        Q8  whether the CF-3300 ever writes $DE77-$DF93, or drive B's image span, when B: is never used.
      Then a plan that puts each zerobas cell where the CF keeps the same kind of state.
      📏 **Q7 + Q8 MEASURED (2026-11-28, [bfiles_probe.py](../../scratchpad/bfiles_probe.py), [AE_bfiles.out](../../scratchpad/AE_bfiles.out); Disk BASIC via `BASIC` at A>, MAXFILES=2,
      OPEN / PRINT# 720 B / CLOSE / OPEN for INPUT / INPUT# / CLOSE; every write in $C000-$F37F per 16 B block):**
        HIMEM ($FC4A): $DF93 at boot, $DE77 in BASIC on BOTH machines, MAXFILES=2 does not move it (🔮 "~300 B per
          file": MISS).
        Q7  channel BUFFERS: the SAME addresses on both -- #1 at $DC60-$DD6F (1440 writes each during PRINT#), #2 at
            $DD70-$DE7F (the CF fills it at OPEN, zerobas at the first INPUT#). Channel CONTROL state: the CF-3300 at
            $DEB0-$DEFF, inside the 284 B $DE77-$DF93 that entering BASIC claims; zerobas at $E4B0-$E52F, inside the
            span the CF keeps for drive B's FAT image. The CF also writes $F1B0-$F1CF at CLOSE and the fixed area;
            zerobas neither.
        Q8  under BASIC the CF-3300 DOES use $DE77-$DF93 (channel state; untouched in a COPY); drive B's image span
            is untouched but for the 16 B block at $E590, which it writes in every phase (cells just under A's image).
      ➡️ So zerobas BASIC's channel cells have a reference place: $DE77-$DF93. The plan next.
      📐 **PLAN DRAFT (2026-11-28; for Joost, NOTHING BUILT).** Inventory of zerobas vs the CF-3300's places, by kind:
          kind                         zerobas today                              CF-3300 place
          FAT image, drive A           none (one sector, re-read)                 $E595-$EB94  1536 B
          FAT image, drive B           none                                       $DF94-$E593  1536 B (CTRL boot drops it:
                                                                                  HIMEM $E48D = $DE77 + 1536 + ~22, D-BOOTKEYS)
          dir / FAT sector buffer      WBUF / FWBUF $EAAD                         $EB95  512 B
          file-data buffer             SECTOR_BUF / FSECTOR_BUF $E8AD             $ED95  512 B
          media-check buffer           none                                       $EF95  512 B
          disk-ROM state               73 cells ~350 B ($ECAD-$EDBD, $EFDA-$F022)  ~41 B $F1A0-$F1C8 + the fixed area
                                                                                  (which zerobas already fills)
          Disk BASIC channel state     DSK_ENGTAB 15 x 50 B ~750 B ($E4BF-$E7AC;  inside the 284 B $DE77-$DF93
                                       Joost 2026-09-27 "the reference's shape")   (~80 B seen for 2 channels)
          other Disk BASIC state       66 cells ~700 B ($EDB9-$F09D)              not seen anywhere else
        zerobas keeps ~1.8 KB of disk state where the CF-3300 keeps ~0.3 KB plus its fixed area. Following its layout is
        therefore a REDESIGN that shrinks our state by ~1.5 KB, not a relocation: even A's image alone needs DSK_ENGTAB's
        tail, both sector buffers and BASIC's $E7AD-$E8AC workspace moved out of $E595-$EB94 first.
        Unknowns that would shape a redesign: the CF's per-channel state size at MAXFILES 15 (284 B / 15 ~ 18 B a
        channel, against our 50); what the CF keeps in the $E590 block; what zerobas's $E7AD-$E8AC workspace holds.
        🙋 The shape of the work goes to Joost before anything else.
      🧭 JOOST 2026-11-28: "Full redesign, staged" -- first the last unknowns (U1 the CF's per-channel state at
      MAXFILES 15, U2 its $E590 cells, U3 what zerobas's $E7AD-$E8AC workspace holds), then the steps, each FULL-gated
      and each brought to him: (1) compact the channel table into $DE77-$DF93; (2) the buffers to the CF's places;
      (3) the FAT image(s) with the CF's write-back (dirty-only, both copies, read back); (4) shrink the disk-ROM state.
      📏 **U1 + U2 + U3 MEASURED (2026-11-28, [bfiles_probe.py](../../scratchpad/bfiles_probe.py) MF15 / MFSTEP / MFHI / MFCRT, [AE_bfiles_u1.out](../../scratchpad/AE_bfiles_u1.out); per-BYTE write
      counts in $DE77-$DF93 and $E580-$E59F):**
        U1  the CF-3300's Disk BASIC keeps a disk channel as a STANDARD 37-BYTE MSX-DOS FCB, SIX of them, at
            $DEB5-$DF92: each OPEN fills the next 37 B ($DEB5-$DED9, $DEDA-$DEFE, ... $DF6E-$DF92). Disk files take #1-#6
            only -- even with MAXFILES=15, OPEN of a disk file AS #7 or #15 (nothing else open) is "Bad file number";
            "CRT:" AS #7 opens. 🔮 "~18 B a channel at a fixed stride": MISS (37 B, six). zerobas: 15 disk channels,
            50 B DSK_ENGTAB rows, nothing in $DE77-$DF93 -> the number limit filed as D-DISKFNUM6.
        U2  the CF's one cell in that block is $E594, the byte under A's image, written in every operation (the other
            bytes written there are the image's own first bytes, re-read).
        U3  zerobas's $E7AD-$E8AC: no named cell and no offset use in any of the four ROMs, no write in these runs --
            256 B that look unused (a computed-offset cell would be invisible to the search).
        Still unknown: what the CF keeps in $DE77-$DEB4 (62 B, never written in these runs).
      📏 **FCB SLOTS + FIELDS (2026-11-28, bfiles_probe.py MFSLOT / MFWR, appended to [AE_bfiles_u1.out](../../scratchpad/AE_bfiles_u1.out)):** OPEN #3 then #1 ->
        slot 3 ($DEFF) then slot 1 ($DEB5): the slot IS the file number, FCB(n) = $DEB5 + 37*(n-1). While a file is
        WRITTEN (1.3 KB, past one cluster) the CF-3300 updates FCB +16..+24, +26..+31 and +33..+35 -- never +25 or +32;
        CLOSE the same set but +26..+27. So it tracks its clusters INSIDE the standard FCB.
      📐 **STEP 1 DRAFT (the channel table; nothing built):**
          channel n's FCB  : DSK_ENGTAB row n (+0..36, TXTMAX-based, 50 B stride)  ->  $DEB5 + 37*(n-1), n = 1..6 (CF)
          disk OPEN #7+    : opens  ->  "Bad file number" (follows from six slots; D-DISKFNUM6)
          row +37..38      : the channel block's address  ->  no cell: derived from FILTAB as BASIC already can
          row +39          : flags (DOUT_RFULL / DOUT_DEAD)  ->  NO CF PLACE MEASURED -- 🙋 question
          row +40..+44     : first cluster / current cluster / sector index  ->  FCB +26..27 / +28..29 / derived from
                             +30..31 and +33..35, the fields the CF itself updates while writing
          row +45..+48     : directory sector + offset  ->  FCB +25 (the directory entry), set at OPEN
          freed            : DSK_ENGTAB's 750 B ($E4BF-$E7AC) -- needed by step 2 (A's FAT image starts $E595)
          unknown          : $DE77-$DEB4 (62 B) on the CF -- never written in any run
          gates            : FULL (a RAM-address move) + diskbasic suites, knife re-pin, disk corpus, a C-BIOS re-pin
                             note (the disk ROM changes)
      🧭 JOOST 2026-11-28: "Build; measure flags first" -- one more address-only run for the flags byte's two states
      (a full record not yet written; a CLOSE that failed), then build step 1 as drafted (FULL gate, knives, disk corpus,
      a C-BIOS re-pin note).
      📏 **THE FLAGS BYTE'S TWO STATES (2026-11-28, bfiles_probe.py MFFLAG / MFFULL, appended to [AE_bfiles_u1.out](../../scratchpad/AE_bfiles_u1.out); per-byte $DC00-$DF93):**
      NEITHER EXISTS ON THE CF-3300.
        record full (CLEAR 1000; PRINT #1,STRING$(254,"A") = 256 B): the CF fills $DD77-$DE76 and WRITES THE SECTOR IN
          THE SAME PRINT# (FCB +16.. and $E594 updated in that step); zerobas fills it and writes on the NEXT PRINT#
          (DOUT_RFULL). (Without CLEAR both said "Out of string space" -- the first run reached nothing.)
          🔴 CORRECTED 2026-11-28 (reading dout_put before slice 2): zerobas ALSO writes a full record AT ONCE --
          dout_put falls into dout_write the moment the record fills. "Writes on the NEXT PRINT#" was an INSTRUMENT
          BLIND SPOT: zerobas's FCB sits in its row at $E4BF+, outside the per-byte window ($DC00-$DF93), so its FCB
          updates were invisible and read as "no flush". DOUT_RFULL is "a full record whose WRITE FAILED", retried by
          the next PRINT# (D-DISKFULL: a full disk fails every later PRINT#). Where the CF keeps THAT state is the
          open question (measured next).
        CLOSE failed (the disk swapped for a write-protected copy): both "Disk write protected"; a SECOND CLOSE on the
          CF fails AGAIN (the channel stays open, it retries); on zerobas it succeeds silently (DOUT_DEAD frees it).
        So step 1 DROPS the flags byte and moves both behaviours to the reference's: write a full record at once; a
        failed CLOSE leaves the channel open.
        🔴 CORRECTED 2026-11-28 (before any code): "DOUT_DEAD does not exist on the CF" was TOO STRONG. D-DISKFULL
        measured a FULL disk on the CF-3300: CLOSE "Disk full", channel open, and the SECOND CLOSE FREES IT SILENTLY --
        DOUT_DEAD's face. Today's write-protect case retries instead. The CF's outcome depends on WHY the close failed;
        whether that takes a flag, or only the ORDER (the pending record consumed before the allocation fails), is
        being measured before DOUT_DEAD is touched. The channel BLOCK already matches (header $DD6E: +0 mode, +4 device,
        +6 position; record $DD77, the same bytes written on both). Unknown, not chased: the CF writes $DC61-$DC65 and
        $DC6C in every step, zerobas does not.
        🔮 "a full record shows only as its position byte; the second CLOSE clears the slot": MISS on both.
      🔎 **STEP 1 INVENTORY (2026-11-28, read-only sweep of basic / sub / sub2 / disk):** ONLY the disk ROM computes a
      row, through ONE routine, dout_row (disk/kernel.asm:1829; wrapper dout_live, ~14 callers). Row fields past the
      FCB: DOUT_BLK +37 (2 uses), DOUT_FLG +39 (RFULL, DEAD -- and a THIRD bit, DIN_CRPEND: an INPUT row's "a CR was
      handed over, its LF unread", disk/fat.asm:664), DOUT_FIRST / DIN_LEFT +40 (overlaid), DOUT_CLUS +42,
      DOUT_SECIDX +44, DOUT_DIRSEC / DIROFF +45..48; +49 unused. FCH_CEIL 15 also sizes FCH_MODES / FCH_RECLENS and
      the MAXFILES bound (those stay: non-disk channels open as #7+ on the CF too); hkk_open_check walks 1..15 with a
      hard-coded `cp 16` (kernel.asm:6398); the HIMEM asserts at kernel.asm:5919-5922 reserve the old table.
      STILL UNPLACED before building: DIN_CRPEND (the flags byte's third bit), DIN_LEFT (perhaps the block's +6
      position the CF already keeps), and the CTRL boot (HIMEM $E48D sits ABOVE $DEB5 -- are the CF's FCB slots fixed
      or do they follow the claim? $DEB5 = $DE77 + 62).
      📏 **THE LAST THREE PLACED (2026-11-28, bfiles_probe.py MFCTRL / MFIN, [AE_bfiles_u2.out](../../scratchpad/AE_bfiles_u2.out)):**
        CTRL boot (one drive, HIMEM $E48D): the CF-3300's FCB slots FOLLOW THE CLAIM -- slot 1 at $E4CB, slot 2 at
          $E4F0 -- i.e. slot 1 = HIMEM + 62 in both boots ($DE77 + 62 = $DEB5). A 517 B run at $E5A9, straight after the
          six slots, is written at OPEN: its disk area is laid out RELATIVE TO THE CLAIM. 🔮 "follows the claim, $E4CB":
          HIT. So step 1's slots are (the disk claim) + 62 + 37*(n-1), not a hard-wired $DEB5. zerobas: $E4BF / $E4F1.
        INPUT row: the same characters on both (INPUT$(1) 65; INPUT$(2) 66 13; INPUT$(1) 10; INPUT # "CD"). The CF keeps
          NO CR-pending flag: every read writes the channel block's +3 (zerobas never writes it) and +6 (the position,
          which zerobas also keeps). So DIN_LEFT -> the block's +6; DIN_CRPEND -> nothing of ours: the CF's state is in
          block +3 (its meaning unmeasured -- a one-character read-ahead is a guess). 🔮 "no flag; the count is +6":
          HIT, with +3 as the unpredicted part.
      ✅ EVERY ROW FIELD NOW HAS A MEASURED CF PLACE OR HAS NO CF COUNTERPART. Step 1 is buildable as ruled.
      📏 **A FAILED CLOSE ON THE CF-3300 IS A MODE CHANGE, NOT A FLAG (2026-11-28, bfiles_probe.py MFDFULL + header values,
      appended to [AE_bfiles_u2.out](../../scratchpad/AE_bfiles_u2.out); channel #1's block header $DD6E-$DD76 READ after every step -- BASIC's data, a
      work-area read, not code):** block +0 (the mode) is 02 after OPEN for OUTPUT; the failing CLOSE sets it to 04 --
      the RANDOM mode -- on a FULL disk AND on a write-protected one. The second CLOSE is then a mode-4 close (the
      directory entry only): on the full disk it succeeds and +0 goes 00 (freed); on the write-protected disk the
      entry write fails again and +0 stays 04. ONE mechanism gives both faces (D-DISKFULL's and today's). 🔮 "the
      record count is cleared before the allocation fails": MISS.
      ALSO: the CF's block +1..+2 = the FCB's ADDRESS ($DEB5) -- the link runs block -> FCB, the reverse of our
      row -> block (DOUT_BLK); its +3 / +5 / +7 / +8 hold values (00 / FC / 00 / 04 here) where zerobas leaves FF --
      VARPTR(#n)-visible (D-FCBSHAPE's subject).
      📐 STEP 1 MAPPING, REVISED: DOUT_DEAD -> the block's +0 := 4 (and FCH_MODES) on a failing CLOSE, the next CLOSE
      taking the RANDOM path that already exists -- which ALSO fixes the write-protect face; DOUT_BLK -> the block's
      +1..+2 := the FCB address, as the CF; DOUT_RFULL -> gone (write the full record at once); DIN_LEFT -> block +6;
      DIN_CRPEND -> block +3 (the CF's own read-state byte; its exact meaning unmeasured, stated as such).
      ✅ **STEP 1a, SLICE 1 BUILT (2026-11-28): A FAILING CLOSE IS THE CF-3300'S MODE CHANGE.** hk_chclose sets the channel
      block's +0 mode to 4 before an OUTPUT / APPEND close's writes; dwr_fail recognises "+0 = 4 while FCH_MODES is not
      4" as that close (frees the chain as D-PRINTFULLSTAMP measured, then FCH_MODES := 4); a CLOSE that succeeds
      leaves +0 = 00 (hcc_done), as the CF. DOUT_DEAD is no longer read or written (its equate goes with the row in
      1b). New gate: closefail-acceptance ([disk_probe_closefail.py](../../probes/disk/disk_probe_closefail.py)) -- a write-protected and a full disk,
      the messages and block +0 after every CLOSE, against the CF-3300: 2/2 ([AE_s1a_closefail.out](../../scratchpad/AE_s1a_closefail.out)); KNIFE: the
      previous kernel.asm turns both rows red, ROM hash moved and restored ([AE_s1a_closefail_knife.out](../../scratchpad/AE_s1a_closefail_knife.out)).
      🔮 "wp: Disk write protected twice, +0 04 04; full: +0 04 00 04, zerobas the same": HIT (after two parser
      fixes in the new probe -- a wrapped line and repeated CLOSE lines; the machines agreed from the first run).
      Subject suites green: diskfull, nodiskerr, fcbhdr, dout, clearclose, putdir, diskbasic.
      📏 **DOUT_RFULL'S TWO FACES ON THE CF-3300 (2026-11-28, bfiles_probe.py MFRFAIL / MFAPP, appended to [AE_bfiles_u2.out](../../scratchpad/AE_bfiles_u2.out)):**
        (1) full disk: the PRINT# that fills a record says "Disk full" and +6 wraps to 00 -- the record is DROPPED;
            the next PRINT# SUCCEEDS (+6 = 03). zerobas retried it ("Disk full" again). D-DISKFULL's "a full disk
            fails every later PRINT#" had never been measured past the first error (its program stopped there).
        (2) APPEND to a file of exactly 256 B (host-injected): LOC 0, LOF 256 on both; then PRINT #1,"X" + CLOSE --
            the CF-3300's file is 256 B, "X" CR LF ^Z OVER ITS FIRST FOUR BYTES (sha1 6b7d325ca727, checked against the
            constructed bytes): it overwrites the last record from its start. zerobas appended (260 B).
        🔮 "no extra state, +6 wraps": HIT; "the next PRINT# fails again": MISS.
      🧭 JOOST 2026-11-28: "Copy the CF exactly" -- drop DOUT_RFULL outright, both faces as the CF-3300's, gate rows
      against it, the APPEND loss documented as a reference behaviour in the keyword docs.
      ✅ **STEP 1a, SLICE 2 BUILT (2026-11-28): DOUT_RFULL GONE, BOTH FACES THE CF-3300'S.** dout_put no longer retries a
      failed full record (the position has wrapped, the next PRINT# starts a fresh one); hk_fapp's whole last record
      re-loads at position 0, so APPEND overwrites it from its start; dwr_lof no longer clears a flag. AND, found by
      the new app256 row: the CF-3300 writes its WHOLE 256 B record buffer, where dout_write zero-padded past the
      fill (zerobas's first app256 file was "X" CR LF ^Z + 252 zeros, sha1 a1a2dfcb4d4a) -- dout_write now copies the
      whole record; the fill (still the count) moves the random record and the size only. closefail-acceptance
      grew rfail + app256: 4/4 ([AE_s1a_closefail.out](../../scratchpad/AE_s1a_closefail.out)). 🔮 "4/4": HIT only after the unpredicted padding fix.
      Subject suites green: append (differential byte-identical), dout, savetail, loadtail, diskfull, fcbhdr, lof,
      putdir, diskbasic; redundant-load, ramatlas, knife re-pin (verdicts unchanged).
      🧭 JOOST 2026-11-28, on the APPEND overwrite ("that seems a serious bug?"): "Measure first, then decide" --
      which files lose data on the CF-3300: BASIC-written files (ending in its Ctrl-Z) at 256 / 512 B, host files of
      a 256 multiple with and without a final Ctrl-Z. The copied behaviour stays until he decides.
      📏 **THE CF-3300'S INPUT CHANNEL KEEPS A ONE-BYTE READ-AHEAD (2026-11-28, bfiles_probe.py MFIN2, [AE_bfiles_in2.out](../../scratchpad/AE_bfiles_in2.out); block
      header values across a record boundary, 363 B file):** +3 = a byte FETCHED but not yet consumed (after OPEN it is
      the file's first byte, $30; after EOF() the byte EOF looked at, $34; $00 when none is held), +6 = the INDEX of the
      last byte fetched from the record (OPEN 00, INPUT$(255) FE, INPUT$(1) FF, the next INPUT$(1) -- a refill -- 00,
      EOF() 01, INPUT$(8) 08). It fetches eagerly at OPEN and at each refill, so +6 = 255 means "record spent": no
      ambiguity. zerobas's +6 counts bytes CONSUMED (FF / 00 / 01 / 09 at those steps). Same characters read on both.
      So DIN_LEFT and DIN_CRPEND fold into the CF's +3 / +6 scheme -- a bigger slice than the others (the end of a
      record and of the file are found differently; LOC may move). Unmeasured: how the CF tells "nothing held" from a
      held $00 byte.
      📏 **WHICH FILES THE CF-3300'S APPEND OVERWRITES (2026-11-28, bfiles_probe.py MFAPP2, [AE_bfiles_app2.out](../../scratchpad/AE_bfiles_app2.out); APPEND "X" to
      each, every result checked against constructed bytes):** ONLY a file WITHOUT a final Ctrl-Z whose size is a
      multiple of 256 -- A256 (256 B) and A512 (512 B: bytes 256-511 overwritten) keep their size and lose their last
      record's start; Z256 / Z512 (ending in Ctrl-Z) and B256 (written by BASIC, which ends every file with one) append
      correctly (259 / 515 / 259 B). zerobas is byte-identical on all five. 🔮 "BASIC-written files append correctly":
      HIT. So the loss hits files from MSX-DOS programs or a PC, never a file Disk BASIC wrote. 🙋 Joost to decide.
      🧭 JOOST 2026-11-28: "Keep it: copy the CF" -- the APPEND overwrite stays, documented with its exact condition
      (no final Ctrl-Z, a 256 multiple) on docs/keywords/OPEN.md, gated by closefail's app256 row.
      📏 **DIN_CRPEND IS A LEAD-IN RULE, NOT STATE (2026-11-28, bfiles_probe.py MFIN3-6, [AE_bfiles_inlf.out](../../scratchpad/AE_bfiles_inlf.out)):**
        a held $00: the CF returns 65 0 66 13 correctly and keeps no visible "held" flag in +0..+8 (🔮 "+7": MISS).
        After INPUT$ took "AB" CR, INPUT #1,X / Y with what FOLLOWS the LF varied -- CF / zerobas:
          LF "12" CR LF "9"       12 9 / 0 12        LF " 12 " ...  0 12 / 0 12
          LF ",12" ...             0 12 / 0 0         LF CR LF "12"  12 9 / 0 12
        and with no CR before (INPUT$ took "A", "AB" CR LF, "AB"; or none): BOTH agree, blanks skipped. ONE rule fits
        every CF result, D-INPLF's old cases A and H included: AN LF MET IN INPUT #'s LEAD-IN IS SKIPPED BUT TURNS
        BLANK-SKIPPING OFF for the rest of that lead-in (a space or comma then ends an EMPTY item; CR / LF still
        skipped). An item-ending CR takes its LF with it, so ordinary files never meet one. INPUT$ leaves no state.
        🔮 "a multi-byte INPUT$ holds the LF in +3": MISS (no LF held after either). zerobas's D-INPLF (A) rule -- a
        CR taken by INPUT$ makes a following LF an empty item -- coincided with the CF only when a blank followed the
        LF (two-rules-that-coincide). Step 1a's INPUT slice: the lead-in rule replaces DIN_CRPEND.
      ✅ **STEP 1a, SLICE 3 BUILT (2026-11-28): DIN_CRPEND GONE, THE CF-3300'S LEAD-IN RULE IN ITS PLACE.** din_num: an LF
      in the lead-in is taken and the rest of that lead-in skips only CR / LF (dnm_lf), so a blank or comma ends the
      item empty; hk_chin's INPUT$ no longer marks a CR, din_take no longer clears it, the equate is gone.
      closefail-acceptance grew `inlf` (the nine files, each by its own line; its parser now reads every step from its
      own snapshot -- the long session scrolled the first ones off): 5/5 ([AE_s1a_closefail.out](../../scratchpad/AE_s1a_closefail.out)). KNIFE: the
      previous fat.asm gives P1 0 12 / P3 0 0 / P4 0 12 again, ROM hash moved and restored ([AE_s1a3_knife.out](../../scratchpad/AE_s1a3_knife.out)).
      🔮 "5/5, P1 / P3 / P4 now the CF's": HIT. docs/keywords/INPUT.md's D-INPLF paragraph corrected. Subject suites
      green: diskbasic, fcbhdr, lof, readflt, diskascii, dout, inputdn; redundant-load, ramatlas; knife re-pinned
      (verdicts unchanged).
      🔁 **SLICE 3 REFINED (2026-11-28; its first gate RED on tests/test_seqin.py, which pinned "blanks only = the end" --
      zerobas's own guess, never measured):** the CF-3300 on four blanks files ([AE_bfiles_bl.out](../../scratchpad/AE_bfiles_bl.out)) -- " " CR LF " "
      reads 0 with EOF 0, " " CR LF reads 0 with EOF -1, CR LF " " CR LF 0 / 0, LF " 5" 0 / 0. So (a) a BLANK after the LF
      ends an empty item and stays UNREAD (a comma is taken), and (b) the END reached after skipping is an empty item,
      not "Input past end" -- that error is only for a channel already at its end (zerobas raised it, a divergence
      older than slice 3). din_num reworked; the unit test corrected from the readings (+ the " " CR LF row);
      closefail grew `inbl` (B1-B4): inlf and inbl both agree with the CF-3300 ([AE_s1a3_inbl.out](../../scratchpad/AE_s1a3_inbl.out)). unit-test and the
      INPUT subject suites green.
