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
