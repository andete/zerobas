- [ ] 💰 **D-DISKCARVE -- TWO FIXES WAIT ON DISK-ROM BYTES THAT ARE NOT THERE (filed 2026-11-07)**
      🎚️ BUDGET — disk-ROM carve: the space D-SDSBOOT's ENASLT bridge (TIER 1, ~14 B in the
      int_h_hiram template, disk/runtime.asm) and the D-FATRES re-do (TIER 5, LOAD 3x the
      CF-3300; scratchpad/fatres_wip.patch, ~150 B in fragments, no longer applies) both need.
      🤖 **AUTONOMOUS** — a carve changes no behaviour; the battery and the disk collection settle it.
      📏 `make basic-reloc` (2026-11-07): disk.rom's only free run of 16 B or more is the FDC
      window ($7F7F-$7FD0), which code cannot use; the pads D-FATRES used were filled since
      (D-COPYALL, D-LOADRUN, D-LOADFAT). The main ROM's carve tools (jr_mapper, dupspan_indep,
      carve_scout) read only the main image.
      ✅ **FIRST CUT (2026-11-07): 23 B for D-SDSBOOT's bridge.** [`jr_mapper_disk.py`](../../scratchpad/jr_mapper_disk.py) (the main
      mapper pointed at disk.rom: [`diskcarve_jr.out`](../../scratchpad/diskcarve_jr.out), 9 sites, 1 in the region needed) and the
      pad roster (57 pads, 478 B, the largest 15): cpmver / stime / gtime (15 B) into the
      $4ECF pad and verify (2 B) into the $55F4 pad, both empty and never entered
      ([`padwatch_4ede.out`](../../scratchpad/padwatch_4ede.out), the ten DOS suites, positive control $4775 caught); the dirin /
      dskrst `jp` veneers removed (their one caller each jumps to the target). The $782B..$7F7C
      region took the bridge fix with 1 B to spare (2026-11-07).
      ✅ **SECOND CUT (2026-11-07, after Joost: "if we still need more room in the disk rom, that
      might be worth spending time on?"): 57 B from duplicate spans.** [`dupspan_disk.py`](../../scratchpad/dupspan_disk.py) (the main
      tool pointed at disk.rom: [`diskcarve_dupspan.out`](../../scratchpad/diskcarve_dupspan.out), 30 byte-identical groups, a measured safe
      net of 96 B on 2026-11-07, all page 1). (1) disk/kernel.asm's wroe_have_valid was a 47-byte PARALLEL
      COPY of the shared body's sector computation (basic/fat-prim-body.inc, now labelled
      frs_sector; SECTOR_BUF = FAT_DBUF in the disk build) -- now `jp frs_sector`: the $75A5
      pad 6 -> 52 B. (2) ffb_miss and fdel_miss were byte-identical to fren_miss: their five
      callers jump there (fdel's three `jr` became `jp`): $4E4B pad 5 -> 13, $7F7C pad 1 -> 6.
      The FAT / WRBLK unit tests are green (2026-11-07).
      ✅ **THIRD CUT (2026-11-07): 124 B more, from copies the label scan cannot see.** A plain
      repeated-byte scan over disk.rom ([`diskcarve_ngram.out`](../../scratchpad/diskcarve_ngram.out), sequences of 12 B or more, label
      boundaries ignored) found what dupspan_disk could not: (1) pg0_mainrom_in was a 66-byte
      copy of the bridge template's own page-0 switch (br_mainin_tmpl: EXPTBL into C, then
      br_p0in_tmpl -- the EXPTBL read before rather than after saving $A8, the same registers
      clobbered); it is `jp br_mainin_tmpl` now, the template's ROM bytes running in place
      (straight-line, absolute references only, the page they run in): $7F7C pad 6 -> 74.
      (2) the 19-instruction FAT12 locate (cluster -> FAT sector, parity, byte index) stood
      inline in getalloc's scan, fat_have_free_cluster's loop and fat_write_fat_entry_hot:
      one fat_locate in front of the $75A5 pin, three calls -- $4C29 7 -> 37, $7F7C 74 -> 104,
      $75A5 52 -> 48 (the helper's 34 B). basic/fat-prim-body.inc keeps its own three copies
      (the sub ROM assembles it). FAT / WRBLK unit tests green (2026-11-07).
      📏 **The four cuts together: ~204 B (2026-11-07)**, ~181 B of it free in pads now -- the
      largest 104 B in front of $7F7C -- against D-FATRES's ~150 B. The ngram scan lists more
      (the fdc_read_phys / fdc_write_phys prefix 34 B, the getalloc / fat_have_free_cluster
      scan bodies 60 B, rename / delete tails).
      📏 Verified on the FULL battery (250/250) + the excluded five; the disk collection
      ([`diskcorpus_dc5.out`](../../scratchpad/diskcorpus_dc5.out)) moved two rows, both explained: ss-final (the known interrupt-
      timing row, D-DISKRUN) and GAUNT -- bisected to the pg0_mainrom_in change, where the
      screen is IDENTICAL on both builds and only the classifier's one PC sample differed
      (scratchpad/gaunt_trans_good.out / _bad.out: the same transfers into disk.rom; a 10 T
      `jp` in the old routine did not flip it, so not timing either). That found the
      classifier fault D-SDSBOOT's reopening records.
      ➡️ D-FATRES's room is there now; what blocks it is its own three reds (DI gaps, the
      FAT_DEFER staleness, MSX-DOS's use of $DE8D..) -- re-apply scratchpad/fatres_wip.patch by
      hand onto today's tree first. The pads are FRAGMENTS (the largest 104 B).
      Next: the remaining safe groups (dirioin_done / const_notready +7, the `3effc9` tails,
      the `32aefc37c9` group), then a scan for a duplicate disk.rom routine already in the sub
      ROM, then a disk-ROM `jp` -> `jr` and duplicate-span scan over disk/*.asm (a freed byte is
      usable only in its own pinned region: rank the regions the two fixes need); then
      evictions of cold disk code into the sub ROM, as D-ROMSIZE did for main. The rule for every
      pad that takes code: `padwatch.py --also=` it first (D-PADSLIDE).
