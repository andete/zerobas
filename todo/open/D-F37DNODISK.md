- [ ] **D-F37DNODISK — WITH NO DISK INTERFACE $F37D HOLDS $C9 HERE, $00 ON THE VG-8020
      (found 2026-11-10 by D-BIOSLADDER B8's NODISK row)**
      🎚️ TIER 6 — a work-area cell nobody should call without checking H.PHYD first.
      🤖 **AUTONOMOUS** — pinned in biosl_run.py ALLOW (b8save $A002). Find what writes $C9
      there on the diskless target, and whether the VG-8020's $00 is worth matching (a CALL
      $F37D there runs into $00s; ours returns).

      - [ ] **SEQWRITE writes through: COPY by SEQREAD / SEQWRITE 153 s against 93** -- 🎚️ TIER 5 —
            on-par speed. Each record re-reads and writes its sector (the CF-3300 writes a
            sector once). The lever: hold the partial sector as DIRTY with an owner tag and
            flush it when anyone else reads into the shared buffer (dskio / read_sector) --
            the W4 audit's tag ([`dbuf_audit2.md`](../../scratchpad/dbuf_audit2.md)) with a dirty bit; the reads that bypass
            read_sector are why it must sit in dskio.
            🏗️ RULED (Joost 2026-11-14): *"leave at tier 5"*.

      - [x] **tools/check_disk_walls.py counts the dead FDC window $7F80-$7FBF as free** --
            🎚️ APPARATUS — its "largest usable hole" today is that window (65 B at $7F7F, the 1 B
            before it real). A reading that offers unfetchable memory as room cost one RED gate
            (cr_copy1, 11-13) and one plan (this item). Exclude $7F80-$7FBF from the scan.
            ✅ **FIXED the same day:** the scan masks $7F80-$7FBF; `make basic-reloc` now reads
            disk.rom's free as 26 B in one run, $758B-$75A4, on 2026-11-13 (it read 91 B).
      🔴 **AND A FIX TO D-DSKFMT'S CALL FORMAT, found writing this:** its work area ran from
      STREND to FRETOP - 64 -- but the BASIC stack lies between the arrays and the strings,
      so on a full machine that reached over the live stack (it worked with ~28 KB free
      only). Now STREND .. SP - 256 (fmt_basic, both paths). With 4214 B free the format
      refuses (DSKFMT's 14 -> main's load error) and BASIC is untouched -- FRE(0) the same
      after ([`callfmt_lowmem.out`](../../scratchpad/callfmt_lowmem.out)). The CF-3300's own answer there is unmeasured (TIER 6).
      ✂️ **DEFRAG STEP 1 (2026-11-09):** the build needs ~350-400 B in ONE place (the menu text,
      a geometry table, the Write Track loop, our boot sector, FATs, root). Ten small
      routines (calbak, hkn_up, fill_rec, wrblk_full, wrblk_set_wrfirst, rnd_rec, rh_init,
      pg0_mainrom_out, hkds_run, hdl_oom; 4-9 B each, `call` / `jp`-entered,
      scratchpad/movescout.py) moved OUT of the region in front of $75A5 into the 8-14 B pin
      holes (scratchpad/move_routine.py: the routine and its comment, before the pin's
      `ds`); two tail `jr`s became `jp` (out of reach after the move), and k47b2_nextbyte
      went back -- it falls into k47b2_nextbyte_get by a `jr nz`. **That region: 2 -> 72 B.**
      Next steps: the duplicated spans inside it (scratchpad/diskngram.py), then more moves.
      ✂️ **DEFRAG STEP 2 (2026-11-09):** clus_sec (disk/kernel.asm: HL = cluster, A = the sector in
      it -> DE = the absolute sector) stood a second and third time, inline, in frs_head and
      ffds_haveclus (basic/fat-prim-body.inc); both call it now. Their exit A / HL differ
      from the inline copies' -- checked against the HL lesson above: frs_head's one caller
      pops HL and passes only DE / Cy on, ffds_haveclus reloads HL and A at once.
      **That region: 72 -> 113 B.** L5_journal / L5_stock and BDOSX3 / BDOSX9 / WRZER clean
      before the battery.
      ✂️ **DEFRAG STEP 3 (2026-11-09):** rrnd_sector carried clus_sec's arithmetic a fourth time
      (plus an RRND_CLUSSEC cell only it read); it tails into clus_sec now (both callers
      reload HL, write_sector sets A / B / C), and the two `ds 1` net-zero fillers beside it
      went. **The region in front of $7F7C: 11 -> 36 B** -- a home for the CHOICE text and the
      geometry table (data, reached by address), the code staying in front of $75A5 (113 B).
      ✂️ **DEFRAG STEP 4 (2026-11-09):** wrseq_writeback / wrseq_wr_writeback shared two runs --
      K := BDOS_SEQREC + 1 with +32 CR / +12 EX (28 B) and +30 from K - 1 (12 B) -- now
      seq_k_adv / seq_k30 (replaced by RANGE, each range checked to hold exactly the expected
      instructions: the source interleaves full-line comments, which defeated a text
      anchor). **The region in front of $75A5: 113 -> 137 B.** BDOSX / 2 / 3 / 8 clean.
      ✂️ **DEFRAG STEP 5 (2026-11-09):** the fifteen bodiless canonical entries (k_4919 .. k_782B)
      share ONE `ret` (they stood as fifteen); `ld (FAT_FATSEC),hl` / `ex de,hl` / `ld
      hl,FAT_MBUF` / `call read_sector` stood four times -> rd_fatsec (tail `jp`, the same
      registers out). **$75A5's region 141 B, $7F7C's 57 B.** L5_journal / L5_stock (the BSAVE
      that caught the HL fault) and BDOSX3 / 8 / 9 / WRZER clean.
      ✂️ **DEFRAG STEP 6 (2026-11-09):** four more moves into holes (rd_fatsec -> $50D5,
      bdos_close_wm -> $5006, dsm_bump -> $46C8, rrnd_sector -> $5462; each ends `ret` /
      `jp`). A dec32 helper (the 4-byte decrement in rgb_have and fig_have) was tried and
      REVERTED: fig_have shares the target region with where the helper had to go, so the
      region LOST 4 B. **$75A5's region 151 B, $7F7C's 91 B -- 242 B.** 📐 A compact DSKFMT
      sized at ~300 B: the CHOICE text (~85 B) and a 4 x 3 B geometry table in $7F7C's region;
      in $75A5's, a run-length table of the WD2793 track image (gaps / sync / marks, ~40 B),
      the Write Track loop (~60 B), the boot sector (BPB + a minimal loader of our own) and
      the FAT / root zeroing (~70 B).
      🏗️ **RULED (Joost 2026-11-10): ALL FOUR CHOICES, as the CF-3300** -- asked "full (~375 B,
      the menu and choices 1-4) or reduced (~290 B, choice 4 only, CHOICE HL = 0)?": *"Indeed
      we need to support the same as the cf-3300. A carve or re-read will be needed to reduce
      size."* So the FULL version, the room from carving or re-reading OUR code, inside the
      one page. (All four are MFM, 9 x 512 B a track: 180 / 360 / 360 / 720 KB.) The
      ladder-first order question is moot: D-DOSLADDER closed the same day.
      ✂️ **CARVE STEPS 7-8 (2026-11-10):** fcb_fatst -- FCB +26 -> FAT_FIRSTCLUS and +16..19 ->
      FAT_FILESIZE, 27 B inline in wfs_geom and rrnd_position (D-RNDLIVE made the second) --
      **$5E10's region 2 -> 26 B** (the helper sits in rrnd_position's, $7F7C 39 -> 35);
      spc_div (the divide by FAT_SECPERCLUS, three times: wrblk_seek, k47b2_seek,
      wfk_cache) and ci_cache (walk from the FCB's cached cluster or the first, twice:
      wrblk_seek, k47b2_seek; Cy = from the first) -- **$77B8's region 5 -> 42 B**. Both
      callers' registers after the old inline code checked: A / DE / HL are reloaded
      before use, and wfk_cache still returns Cy = 1. Skipped as not identical: hk_finp /
      hk_frnd's found tail (+26 against DOUT_FIRST = +40) and the 13 B write-state reset
      (one copy in fatiocreate-body.inc, which sub/save.asm also includes). Unit tests 94/94,
      bdos-acceptance 25/25 on each step.
      ✂️ **CARVE STEPS 9-10 (2026-11-10):** new_taken -- "is the NEW name taken?" with
      FWR_DIRSEC / DIROFF kept, 22 B inline in bb_rename (BASIC-side FREN) and hkn_a (NAME);
      the flags survive its pops and `ret` -- **$55DB's region 3 -> 22 B**. mnt_find / mf_find
      -- fat_mount then fat_find the FCB's name, a miss DROPPING the return address into
      fren_miss (identical to the callers' `jp c, fren_miss`: none has anything else pushed,
      fdel_one's free loop pops before each branch) -- in fopen_fill_body, fdel_one and
      fdel_relocate. **Free in disk.rom: 328 B before step 7 -> 421 B.** Step 11: rgb_have's
      32-bit BDOS_BYTESLEFT decrement written out (19 B) became a carry-chained loop counted
      in E (11 B; every caller saves or reloads DE) -- 429 B. Unit tests 94/94,
      bdos-acceptance 25/25; NAME's three gates and the BASIC-side BDOS probe
      (scratchpad/bdosset_probe.py zb: RENAME of a missing name $FF, a real one 0 and the
      file then deletable) green.
