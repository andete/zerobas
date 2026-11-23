- [ ] 🐌 **AN ASCII BASIC TAPE (`RUN"CAS:"`) TAKES ~40% LONGER TO LOAD THAN ON THE VG-8020
      (D-ASCTAPESPD, found 2026-10-27 by D-TAPELOAD's corpus).**
      🎚️ TIER 5 — on-par speed of loading an ASCII program from tape (within T2's 10×)
      🤖 **AUTONOMOUS** — black-box timing settles it; ⏸️ speed is PAUSED (Joost 10-20:
      ROM space first), so this is filed, not chased.
      📏 [`tapeload_space_timing.out`](../../scratchpad/tapeload_space_timing.out): the collection's "Space"
      (`RUN"CAS:"` of an ASCII program), sampled every 30 s: the VG-8020 starts the
      program between T210 and T240, zerobas between T300 and T330 -- ~90 s later,
      reproduced exactly on a second run. The tape's data rate is the same on both, so
      the extra time is spent between blocks -- most likely tokenising and storing
      each block's lines while the motor is stopped. ➡️ First measurement when picked
      up: the same ASCII program loaded from DISK (LOAD"A:...") on both, and the time
      against the program's line count -- per-line cost vs per-block cost.
      📏 **MEASURED 2026-11-06 -- AND IT FOUND A BIGGER GAP NEXT TO IT.** A 150-line program
      of realistic statements ([`asctok_end.bas`](../../scratchpad/asctok_end.bas)) loaded by the
      program harness's own ASCII tape: **CF-3300 114.1 s, zerobas 173.9 s (1.5x)**
      ([`asctok_end.out`](../../scratchpad/asctok_end.out)); the same program with `SAVE "T.BAS",A`
      at line 10 ([`asctok_save.bas`](../../scratchpad/asctok_save.bas)): the SAVE ,A alone **~1.5 s
      there, ~44.5 s here (~30x)** ([`asctok_time.out`](../../scratchpad/asctok_time.out)). The FDC
      log of that SAVE ([`asave_fdc.out`](../../scratchpad/asave_fdc.out)) holds only 100 commands;
      1 ms PC samples ([`asave_pc.out`](../../scratchpad/asave_pc.out)) put ~65 % of it in the
      detokeniser's keyword search (dk_entry / dk_next, sub ROM): every token walks the
      whole kwtable, ~150 entries at ~260 T.
      ✅ **(a) THE WALK, 2026-11-06 (D-ASAVESPD):** detok_kw (basic/detok.inc) walks in HL, not
      IX / IY (~140 T an entry, no larger); LIST gets it too. The 150-line run 218.4 -> 203.5 s
      (🔮 ~-16 -> -14.9 HIT; [`asavespd_after.out`](../../scratchpad/asavespd_after.out)), the
      SAVE ,A ~44.5 -> ~29.6 s. tests/test_list.py (the round trip) green. ➡️ NEXT: the search
      is still ~half of it ([`asave_pc2.out`](../../scratchpad/asave_pc2.out)) -- a token -> entry
      index (~256 B of sub ROM: page 0 had 170 B free and page 1 ~90 B on 2026-11-06, so a carve first); then the tape
      load's own 1.5x (the tokeniser between blocks).
      ✅ **(b) THE TAPE LOAD, 2026-11-06:** PC samples over the load ([`asctape_pc.out`](../../scratchpad/asctape_pc.out),
      direct mode) found two costs besides the BIOS's tape reading: the tokeniser's match_kw
      (~30 s) and the line store's relink (~22 s). (1) match_kw (basic/tokenise.inc) rejects a
      kwtable entry on its FIRST char before any setup (C = the source's first char, upcased
      once; the table is in longest-match order, so the walk cannot stop early): 173.9 ->
      162.8 s (🔮 ~-14 -> -11.1, a near miss; [`tokfast_after.out`](../../scratchpad/tokfast_after.out)).
      (2) le_store (sub/lineedit.asm) relinks FROM SL_SLOT, not from TXTTAB: nothing before the
      slot moved and the line before it already points at the slot, so every earlier link is
      valid -- the token-aware relink per stored line made a load QUADRATIC: 162.8 -> 138.8 s
      (🔮 ~-22 -> -24 HIT; [`relinkslot_after.out`](../../scratchpad/relinkslot_after.out)). Out-of-order
      lines (inserts in the middle, a replace, a delete, a line before all) list identically
      on the VG-8020 ([`relinkslot_measure.out`](../../scratchpad/relinkslot_measure.out)).
      tests/test_tokenise.py / test_list.py / test_program.py green. **The tape load: CF-3300
      114.1 s, zerobas 138.8 s (1.22x), from 173.9.**
      ✅ **(c) ROUND 2, 2026-11-06:** re-sampled ([`asctape_pc2.out`](../../scratchpad/asctape_pc2.out)): the
      BIOS's own tape reading ~95 s of the 138.8, match_kw still ~24 s. Every kwtable keyword
      starts with a LETTER (161 of 161 -- tests/test_tokenise.py now asserts it), so match_kw
      returns "no keyword" at once for a source char outside A..Z (a space, an operator, a
      quote: the same NC the whole walk reached), and the walk is in HL instead of IX/IY.
      **138.8 -> 119.6 s against the CF-3300's 114.1 (1.05x)** (🔮 ~123: HIT, 3 s better;
      [`asctape_pc3.out`](../../scratchpad/asctape_pc3.out)); what is left is the BIOS reading the
      tape. tests/test_tokenise.py / test_list.py / test_program.py / test_statements.py
      green. ➡️ What stays open here: SAVE ,A's detokeniser search (the token -> entry index,
      a sub-ROM carve first).
      🔴 **RE-MEASURED 2026-11-11 ([`asave_1111.out`](../../scratchpad/asave_1111.out)) -- SAVE ,A IS STILL ~19.5x:** the 150-line
      program with and without `SAVE "T.BAS",A`: CF-3300 114.1 / 115.6 s (the SAVE 1.5 s),
      zerobas 119.3 / 148.6 s (the SAVE **29.3 s**). That is past T2's 10x -- a TIER 2 gap
      ("reasonable time") filed inside this TIER 5 item; the tape load itself is 1.05x.
      💰 **WHERE THE INDEX CAN GO:** detok_kw runs in the sub-ROM's PAGE-0 tenant, which reaches
      sub page 0 (69 B free on 2026-11-11), main page 1 and RAM -- NOT sub page 1 (354 B free on
      2026-11-11, since the quick format retired). So the ~256 B token -> entry index belongs in
      MAIN page 1's pin pads (1099 B free in front of $6CF3 on 2026-11-11, which the tenant can read), generated with
      kwtable.inc so it cannot drift; detok_kw's change is a few bytes in sub page 0. LIST
      gets it too. 🔮 to score: SAVE ,A ~29 -> under ~15 s (the search was ~half, asave_pc2.out).
      🔴 **CORRECTED THE SAME DAY: THE PLACEMENT ABOVE IS WRONG.** kwtable's ONLY copy is in the
      sub-ROM's page 0 (sub/sub.asm includes it, check_kwtable_identity.py), measured
      2026-11-11: 161 entries, 113 of them single-byte tokens, 1189 B at $3B16. An index in
      MAIN page 1 would hold SUB-ROM addresses -- a cross-ROM link the build does not have
      (main would need sub.sym). And re-sorting kwtable by token is out: match_kw takes the
      FIRST full match, so its order is load-bearing for the tokeniser. ➡️ Candidates, to
      price before choosing: (a) a 1-byte ORDINAL index in sub page 0 (128 B: token -> entry
      number, then skip that many entries at ~40 T instead of comparing at ~140 -- ~6x), needs
      ~60 B carved beside sub page 0's 69 B free (2026-11-11); (b) a generated kwidx.inc for
      main page 1 from sub.sym, built after the sub-ROM (a build-order change); (c) a
      per-SAVE index in an existing scratch buffer SAVE ,A does not use (no new RAM -- needs
      that buffer audit). 1-byte OFFSETS do not work: 1189 B > 255 x 4, entries unaligned.
      📏 **NARROWED (2026-11-11):** (b) is a BUILD CYCLE -- the sub-ROM already imports main's
      resident ABI (sub/basic-resident-abi.inc from main's symbols), so main cannot also
      depend on sub.sym. (c) has no buffer: LINEBUF ($F55E, 258 B) is the only idle-sized one
      and a direct-mode `LIST` / `SAVE ,A` RUNS from it (`LIST:PRINT 1` would lose its own
      line); FSECTOR_BUF (512 B) is busy writing the file during SAVE ,A and absent on the
      diskless build. Left: (a), after a ~60 B carve in sub page 0. 🔴 **AND THE CEILING:** the
      search is ~half of the 29.3 s, so even a perfect index leaves ~15 s -- still ~10x the
      CF-3300's 1.5 s. ➡️ Profile the OTHER half first (asave_pc2.out's non-search samples)
      and price both halves together before carving.
      📏 **PROFILED (2026-11-11, [`asave_pc3.out`](../../scratchpad/asave_pc3.out); 1 ms PC samples on line 10, 28.9 s):** the
      keyword walk (dk_entry and its 16-byte neighbour bucket) ~14.5k samples, **~50 %**; disk
      ~5.7k, **~20 %** -- fdq_win (the write's first-DRQ waits, a revolution each), frdw_poll /
      fwd_wait, fat_rootsecs: alone ~4x the CF-3300's WHOLE SAVE, D-BLKIOPERCALL's
      write-cache class; the rest ~8.7k, ~30 %, spread over the per-character channel output.
      ➡️ So the plan is two slices, not one: (1) the ordinal index ((a) above, after the ~60 B
      sub page 0 carve): -> ~14 s; (2) the write side's per-sector waits (D-BLKIOPERCALL's
      step 2, a write cache); only both together can approach T2's 10x.
      ✂️ **D-KWIDXCARVE 1 (2026-11-11, +20 B sub page 0: 69 -> 89 free):** the aspect's minor-axis
      scaling stood twice in sub/graphics.asm (gsv_ypos, gfx_circ_emit_point; 26 B each, a
      sub-ROM n-gram scan) -> gfx_asp_scale. test_graphics, graphics- and graphics-floor-
      acceptance green. ~50 B more to carve for the 128 B index + its lookup. ⚠️ The scan's
      names at $280A / $2827 are main-ABI equates sharing sub addresses -- read sub.lst
      there, not sub.sym.
      ✂️ **D-KWIDXCARVE 2 (2026-11-11, +107 B sub page 0: 89 -> 196 free; page 1 354 -> 244):** the
      DEFtype tenant moved to sub PAGE 1 -- page-0 row 9 retired, page-1 row 10 (the quick
      format's retired slot) is `jp deftype_tenant`, SUBROM_IDX_DEFTYPE = 10 and usr.asm
      dispatches with sc_inl1; its letter test inline (the page-0 is_letter / upcase are
      unmapped in page 1), and an assemble-time check that edt_codes stays inside one 256 B
      page. The tenant-closure checks pass; unit tests, forvar / deffn / array acceptance
      and kwsweep's DEF rows (all SUPPORTED) green. 🔮 THE INDEX, DESIGNED: ordinals (128 B)
      + bucket offsets every 16 entries (22 B) generated from kwtable.inc + sysvars.inc's
      *_TOKEN equates into kwidx.inc, a static check that regenerates and diffs it, and a
      host test that the index and the walk answer alike for every token.
      ✅ **D-KWIDX BUILT (2026-11-11): SAVE ,A 29.3 -> 13.9 s (CF-3300 1.5 s: 9.3x -- UNDER T2's 10x).**
      tools/gen_kwidx.py writes basic/kwidx.inc from kwtable.inc + sysvars.inc's token equates
      (the build switches' IF blocks evaluated): kw_ord (128 B, token -> the first tlen==1
      entry's ordinal, $FF none) and kw_bkt (every 16th entry's offset, 11 words); detok_kw
      jumps to the bucket and skips <= 15 entries. Verified three ways: the generator's
      output against the ASSEMBLED table (0 mismatches), tests/test_kwidx.py running detok_kw
      on the host for all 256 byte values against the walk's answer (113 keywords, 0
      mismatches), and `make kwidx-check` (static battery) regenerating and diffing. Knife
      ([`kwidx_knife.out`](../../scratchpad/kwidx_knife.out)): $81's ordinal off by one -> test_kwidx prints STOP for END and
      kwidx-check is RED. 📏 [`asave_kwidx.out`](../../scratchpad/asave_kwidx.out) (🔮 ~15 s: HIT). Sub page 0: 196 -> 22 B free.
      LIST gets it too. ➡️ Left of the 9.3x: the disk side (~20 %, D-BLKIOPERCALL's write
      cache) and the per-character channel output (~30 %).
      📏 **THE DISK SIDE, COUNTED (2026-11-11, [`asave_fdc2.out`](../../scratchpad/asave_fdc2.out)):** the SAVE line's FDC commands --
      CF-3300 **11** in 0.85 s (6 reads `82`, ONE multi-sector write `A2`, 4 `D0`); zerobas
      **100** (49 seeks, 12 reads, **39 single-sector writes** `A0`) for a ~5 KB file of ~10
      data sectors. Each sector is written several times: the ASCII channel moves 256 B
      blocks through FCB block I/O (S10.B), so a block is a read-modify-write of its 512 B
      sector plus directory work -- D-BLKIOPERCALL's "every WRBLK rewrites the directory".
      ➡️ The write cache to build is aimed there: hold a half-written data sector across the
      channel's block writes and write the directory entry at CLOSE (as the CF-3300 does,
      D-WRBLKDIR), not a general cross-call cache. 🔮 to score: the SAVE line's writes from
      39 toward ~12 (10 data + FAT + dir), the SAVE under ~10 s.
      🔬 **WHY 39 (2026-11-11, read in disk/kernel.asm dout_write):** RS = 1 and 256 B records, so a
      record is HALF a sector. A FIRST half is written padded at once and the cursor stepped
      back; the SECOND half re-reads the sector (dout_secread: FAT_DBUF is shared, so the first
      half cannot be trusted to still be there) and writes it whole -- 2 writes + 1 read per
      data sector, plus the FAT as clusters are allocated. ➡️ THE SLICE: skip the first-half
      write and HOLD it in FAT_DBUF, behind an ownership tag (channel + sector) that every
      other FAT_DBUF user clears -- i.e. flushes the held half first -- with CLOSE and the
      channel switch flushing too. That is the shared-buffer audit W3b / W4 names (every
      FAT_DBUF writer: fat_read_file_sector / frs_to, rd_dbuf, the RANDOM engine, BDOS reads,
      LOAD's first sector, FILES / KILL / NAME's directory reads); a missed one LOSES DATA,
      so the audit is a list with a gate row per writer, and the knife is "drop one flush".
      📋 **AUDIT LIST BUILT (2026-11-11, [`dbuf_audit.out`](../../scratchpad/dbuf_audit.out)):** 66 code references to the shared
      buffer (FAT_DBUF = SECTOR_BUF = FSECTOR_BUF) in ~45 routines -- fat_mount 6, getdpb /
      fdl_marked / dsm_p1_pre / bb_mark 3 each, then the channel (dout_write, close_read,
      cr_chkdir, hkn_stamp), the FAT walkers (fm_fatacc, fnc_straddle, fcf_*), LOAD (hd_rest,
      hd_last) and the BDOS (bsr_partial, dta_chunk, fip_store). ➡️ Next: classify each by
      hand (R read-into / C copy-into / W written-from / P pointer-only); every R and C site
      takes the "flush the held half first" rule, W and P need none.
      ✅ **CLASSIFIED (2026-11-11, same file):** 8 R, 3 W, 1 C by context; the other 54 read by
      hand -- nearly all P (parses of a sector already loaded). What PUTS NEW BYTES in the
      buffer is five places: (1) every read with the buffer as destination (read_sector,
      read_sector_nh -- LOAD's bypass since D-LOADHOLD --, rd_dbuf); (2) 🔴 dskio_next's
      PAGE-1 BOUNCE: a DSKIO read to page 1 goes through SECTOR_BUF -- invisible to a
      "who calls read_sector" search; (3) bb_mark's BASENT trampoline, copied in and run;
      (4) fat_media's writes at +11; (5) the owner's own exits (CLOSE, channel switch).
      ➡️ DESIGN: the flush lives in the READ PATHS' destination test (1, 2) -- D-PUTCACHE's
      rh_check pattern -- plus explicit calls at 3, 4, 5; read_sector_nh must keep a cheap
      "a half is held?" test (an ~85 T one cost LOAD a revolution: D-LOADHOLD), so the held
      flag should be one byte tested once per sector. Gate rows: one per place (a channel
      half-written, then that place's operation, then the file read back).
      ✂️ **ROOM FOR IT (2026-11-11, D-WRRESET, ~40 B of disk ROM):** the sequential writer's reset
      (no cluster, empty buffer, 0 bytes) stood three times -- bdos_create_body, fat_io_create,
      COPY's hkc_differ -- and is one `wr_reset` now (in front of $75A5, which set_rr's move
      to the $4558 slack made room for). Slack after: $553C 19 B, $5E10 20 B, $75A5 4 B (2026-11-11).
      COPY's copy gains the BUFLEN zeroing (right for a fresh destination). Unit tests,
      diskbasic / bdosunop / wrblkalt / copy / catcopy / bdos acceptance green.
      🧩 **DESIGN REFINED (2026-11-11):** the held half needs its SECTOR, so a word, not a flag bit
      (FAT_DEFER's bits 0 / 1 / 2 / 7 are taken anyway): DBUF_HSEC in $E5AC..$E5BF -- inside
      disk.rom's reserved area and MEASURED unused (scratchpad/ramfree_e5ac.out), so no HIMEM
      move (the RAM rung). dout_write's FIRST half sets it and skips the write; its SECOND half
      skips dout_secread only when DBUF_HSEC is its own sector -- anything that flushed in
      between cleared it, and the re-read happens as today, so a MISSED check costs a
      revolution, never a sector. Checks: fat_read_file_sector's entry (NOT frs_to -- LOAD's
      per-sector path stays as D-LOADHOLD left it), read_sector / rd_dbuf, dskio_next's page-1
      bounce, bb_mark, fat_media, CLOSE / the channel switch. Estimate ~70 B against the ~43 B
      D-WRRESET freed: one more carve first.
      ✂️ **D-FWESHARE (2026-11-11, +41 B in front of $75A5: 4 -> 45 free):** fat_write_fat_entry's
      sector-straddle path repeated the same-sector path's whole even / odd store (only HL
      differs); it sets HL = FAT_MBUF and joins it now (fwe_b1_store). Disk ROM free in the
      regions that matter (2026-11-11): $75A5 45 B, $5E10 20 B, $553C 19 B. test_fat_write_fat_entry
      (all four packing cases, every FAT copy), unit tests, wcache (the straddle rows fat-x /
      content-x) / diskbasic / copy / bdos acceptance green. The cache's room is there now.
      🔴 **THE DIAGNOSIS WAS WRONG FOR SAVE ,A (2026-11-12, [`wcache_asave_trace.out`](../../scratchpad/wcache_asave_trace.out)).** A validated
      skip of dout_write's second-half re-read (DBUF_HSEC at $EDBF -- measured free,
      scratchpad/ramfree_edbf.out --, cleared by read_sector / fat_read_file_sector /
      fat_flush_data_sector) was built and measured: SAVE ,A unchanged (133.1 s, 100 FDC
      commands, 12 reads; 🔮 ~12 s and ~10 fewer reads: MISSED), and a breakpoint trace
      showed why -- **dout_write never runs during SAVE ,A**: the listing goes through
      fat_io_putbyte (basic/fatiow-body.inc), ONE flush per full 512 B sector (17) plus a
      FAT read per cluster (12). The dout_write half-sector pattern is PRINT#'s, not SAVE's.
      REVERTED, nothing shipped: no workload measured a benefit for its 44 B. ➡️ SAVE ,A's
      disk waste is PER CLUSTER: of its 39 writes ~17 are data and ~22 FAT (each allocation
      writes the FAT sector to both copies), and a FAT sector is re-read per cluster; the
      CF-3300 writes the FAT once at CLOSE. So the lever is D-WCACHE W3b's FAT hold across
      allocations (W3a already defers within one), not a data-sector cache. The carves
      (D-WRRESET, D-FWESHARE) stand -- the room is useful either way.
      ✅ **D-ASAVEFAT (2026-11-12): SAVE ,A HOLDS THE FAT FOR THE WHOLE LISTING -- 13.9 -> 10.1 s (CF-3300
      1.5 s: 6.7x).** The hold already existed: tokenised SAVE's D-SAVEFAT (FAT_DEFER bit 2,
      fdh_rehold in ffds_alloc, sdw_end = frl_flush + fat_io_close at the end). SAVE ,A
      never turned it on. Now hk_asav sets it after fat_io_create and hk_chclose_e's
      no-channel close goes through sdw_end (+5 B, $5E10). 📏 [`asavefat_time.out`](../../scratchpad/asavefat_time.out): the SAVE
      line's FDC commands 100 -> 56 (writes 39 -> 23, reads 12 -> 5) -- 🔮 "~20 writes,
      several s": HIT. Knives ([`asavefat_knives.out`](../../scratchpad/asavefat_knives.out)): K1 (the close writes no held FAT)
      -> asavedev RED; K2 (no flush on the disk-full exit) moved NOTHING, and the code says
      why -- that exit is reached only through ffds_alloc's failure, whose ffds_undefer ->
      frl_xfail already flushed -- so that flush was redundant and is gone. asavedev /
      asavechan / diskfull / wcache / diskbasic / programs acceptance green. ➡️ Left of the
      6.7x: the per-character output (~30 % of the old profile) and 23 writes against the
      CF-3300's one multi-sector write.
      📏 **RE-PROFILED AFTER IT (2026-11-12, [`asave_pc4.out`](../../scratchpad/asave_pc4.out), 10.1 k samples on the SAVE line):** the
      cost is SPREAD now -- disk waits ~20 % (fdq_win, the write's first-DRQ wait, 1334;
      fwd_wait, frdw_poll, fat_rootsecs); detok_kw2 ~6 % (the two-byte $FF-prefixed function
      tokens -- SQR, CHR$ ... -- still WALK kwtable: D-KWIDX indexed single-byte tokens only);
      main-ROM page 0 $2410-$24F0 ~15 % (C-BIOS: most likely the 50 Hz interrupt's key scan --
      the VG-8020 pays its own, not ours to cut); the rest a long tail. ➡️ Levers left, each a
      slice: (1) a kw_ord2 index for detok_kw2 (~6 %, but sub page 0 has 22 B -- a carve);
      (2) multi-sector writes for a run of consecutive data sectors (D-BLKIOPERCALL's class:
      the CF-3300 writes the file in ONE command).
      ✅ **D-KWIDX2 (2026-11-12): LEVER (1) BUILT -- SAVE ,A 10.1 -> 9.9 s.** Room: the LOF tenant (lofu32,
      74 B, self-contained) moved to sub page 1 (page-0 row 17 retired, page-1 row 13 -- the
      dirverb tenant's retired slot -- `jp lofu32_tenant`, expr.asm via sr_inl1; sub page 0
      22 -> 96 B, page 1 244 -> 170). tools/gen_kwidx.py also emits kw_ord2 ($FF xx, xx in
      $81..$B0, 48 B); detok_kw2 takes it for $FF + an in-range byte and walks for anything
      else (the ':'-prefixed pair); detok_kw's locate is now dk_ordent, shared. test_kwidx now
      also runs detok_kw2 for every first byte any two-byte entry uses x every second byte
      (512 pairs, 0 mismatches); knife ([`kwidx2_knife.out`](../../scratchpad/kwidx2_knife.out)) -> RIGHT$ printed as MID$, RED.
      📏 [`asave_kwidx2.out`](../../scratchpad/asave_kwidx2.out): 9.9 s (🔮 ~9.5: MISSED, smaller -- the 6 % was a 16-byte sampling
      bucket shared with neighbours, and this program has few function tokens). Sub page 0
      15 B free after it (2026-11-12). LOF / unit tests green.
      🔴 **LEVER (2) WITHDRAWN (2026-11-12, [`asave_writegaps.out`](../../scratchpad/asave_writegaps.out)):** the data writes ARE consecutive sectors
      -- but ~0.48 s apart, and a sector write takes milliseconds. The producer sets the pace:
      ~1 ms per output byte, so a multi-sector write would save ~nothing. ➡️ **The real lever:
      ONE INTER-SLOT CROSSING PER LINE, NOT PER CHARACTER.** Every byte of the listing leaves
      main through H_CHOUT and crosses into disk.rom (hk_chout_e -> hco_asav -> fat_io_putbyte):
      a CALSLT per byte (~900 T in C-BIOS alone, D-LOOPPROF's measure); the CF-3300's whole
      SAVE is ~0.17 ms a byte. Design: hand disk.rom the detokenised LINE (DETOKBUF already
      holds it) in one crossing and let it fat_io_putbyte the buffer in-ROM. That is an output-
      path change (main's SAVE ,A loop + a buffer op behind the hook), to price before building.
      💰 **PRICED (2026-11-12):** basic/print.asm's pch_disk sends EVERY SAVE ,A byte through pchar's
      sink dispatch and a hook CALLF (H_CHOUT) into disk.rom -> hco_asav -> fat_io_putbyte; the
      listing reaches pchar one character at a time, drained from DETOKBUF. ~8.5 k bytes x
      ~1.1 k T a crossing ~ 9.4 M T ~ **2.6 s of the 9.9** -> SAVE ,A ~7.3 s (~4.9x the CF-3300).
      Cost: a "write this buffer" op behind the hook in disk.rom ($5E10 region: 15 B on
      2026-11-12) and, in main, the drain loop handing DETOKBUF over in one crossing when the
      sink is SAVE ,A's (PRDEST, PRDEV 0, no channel) -- main page 1 and disk.rom together, with
      a contract between them: a designed slice. SAVE ,A is under T2's 10x already (6.6x), so
      this is ordinary TIER 5.
      ✅ **D-ASAVELINE (2026-11-12): BUILT -- SAVE ,A 9.9 -> 6.1 s (CF-3300 1.5: ~4.1x).** One crossing
      per detok WINDOW, not per byte: basic/print.asm's new print_dbwin (moved from repl.asm, beside
      pchar) tests PRDEST 1 + PRDEV 0 + FCH_ACTIVE 0 and then enters pchar with A = 0 and HL = DB_WIN;
      pch_disk hands both to H_CHOUT unchanged, and disk.rom's hco_asav reads A = 0 as "a
      0-terminated buffer at HL" (hco_blk), each byte through the old one-byte path (hco_byte) so a
      66 / DSKIO fault raises exactly as before. Safe only for SAVE ,A: a listing never holds a $00,
      a channel's $00 is a real PRINT# byte -- hence FCH_ACTIVE in the test. Room: disk.rom $5E10
      15 -> 0 B; main page-1 pad at $6CF3 1093 -> 1073 B (2026-11-12). 📏 [`asave_line.out`](../../scratchpad/asave_line.out):
      6.1 s (🔮 ~7.3: MISSED, bigger -- the per-byte path also paid pchar's push/dispatch and RST 18h's
      H_OUTD call, not only the CALLF). Gates: asavedev, asavechan, diskfull, wcache, diskascii,
      cas-ascii green. Knives: K1 (`inc hl` -> `dec hl` in hco_blk) -> asavedev 0/3 RED
      ([`AL_k1.out`](../../scratchpad/AL_k1.out)); K2 (FCH_ACTIVE dropped from the test) -> sessions S16_diskprog
      DIFF after RUN, its PRINT #2,USING ([`AL_k2.out`](../../scratchpad/AL_k2.out)). H_OUTD is no longer called per byte of
      a disk listing; on the published machine the disk ROM is that hook's tenant during one.
      ✅ **D-ASAVEEND (2026-11-12): THE CLOSE IN THE RIGHT ORDER -- SAVE ,A 6.1 -> 5.7 s (~3.8x).** Re-profiled
      after D-ASAVELINE ([`asave_prof_line.out`](../../scratchpad/asave_prof_line.out)): disk waits ~34 % of the SAVE line (fdq_win, fwd_wait,
      frdw_poll), the disk-side byte path ~12 %, detok the rest. The FDC log ([`asave_fdc_line.out`](../../scratchpad/asave_fdc_line.out))
      showed the FAT written TWICE at the end: sdw_end flushed the held FAT sector, then
      fat_io_close's last partial sector started a new cluster and re-read the FAT and wrote
      both copies again (R2 W2 W5). sdw_end (moved from pageenv.asm to the $75A5 region: 45 ->
      27 B, $4217 4 -> 11 B, 2026-11-12) now writes the buffered last sector FIRST, still under
      the hold, then frl_flush, then fat_dir_update; a failing data write still sends the held
      sector out (frl_xfail keeps the CF). SAVE (sv-diskwr.inc) gets it too. 📏 [`asave_end.out`](../../scratchpad/asave_end.out)
      5.7 s (🔮 ~5.7: HIT); [`asave_fdc_end.out`](../../scratchpad/asave_fdc_end.out): the SAVE line 23 W / 5 R -> 21 W / 4 R (the last
      `A0` from fwd_chk is a lost-data retry of the directory write, D-FDCDI's class). Gates:
      asavedev, asavechan, diskfull, wcache, diskascii, savedev, savedate, savetail, fullclash,
      bsavevar, bdos, wrblkalt, diskbasic, programs green. No knife: the old order passes every
      row too -- the FDC count is the witness. ➡️ Left: the per-sector rotational wait (each
      data sector written alone, ~0.25 s apart -- the CF-3300 issues one multi-sector write) and
      the per-byte disk path (fip_store / fat_io_putbyte / fwr_bytes_inc, ~12 %).
      📏 **RE-MEASURED 2026-11-14 ([`asave_1114.out`](../../scratchpad/asave_1114.out), after the day's interpreter work --
      D-SEPONCE / D-ESIDXAL / D-ESINLINE):** the 150-line program 119.2 s, with SAVE ,A 125.1 --
      **the SAVE 5.9 s** (5.7 on 11-12; CF-3300 1.5): unchanged within a run's spread, as
      expected -- the statement dispatch is not SAVE ,A's path. The levers above stand.
