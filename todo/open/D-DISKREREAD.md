- [ ] 💰 **DISK-ROM ROOM BY RE-READING THE CODE, NEVER BY ADDING ROM SPACE (D-DISKREREAD, Joost 2026-11-26).**
      🎚️ TIER 3 — the room pays for D-BUFINCTL (Ctrl-C / Ctrl-P at A>) and the filed disk fixes behind it.
      🤖 **AUTONOMOUS** — the candidate lists exist; each slice is applied, gated FULL and committed on its own.
      Joost: "we need to do re-reading to create size in the disk rom. We managed to do the disk rom without artificial
      extra rom space, it would be a shame if we had to do that now." A four-way read-only re-read of disk/*.asm and
      the disk-only basic/*.inc split the ROM into slices A..D; each candidate is re-checked against the current
      source and the build before it lands, one at a time, its saving measured as fill in front of the next pin
      (tools/check_disk_walls.py).
      * Slice A (init / driver / fat / runtime) -- DONE a89a93d15: 178 B, room 8 -> 182 B
        ([`AE_apA_apply.md`](../../scratchpad/AE_apA_apply.md)).
      * Slice B (kernel.asm's BASIC hooks, the BDOS table, BSAVE, fat_fits) -- DONE: 90 B of 93 claimed (one item's
        old block was miscounted), room 182 -> 270 B ([`AE_apB_apply.md`](../../scratchpad/AE_apB_apply.md)). Disk corpus:
        every class as slice A's but YOUMAKOR, a sampling-phase flip measured on both builds (D-DISKRUN).
      * Slice C (the date code, WRBLK / WRRND / FSIZE / SETRND, KILL, tokenised SAVE, the banner) -- DONE 2026-11-26:
        138 B (two items' old blocks miscounted, +1 / -1), room 270 -> 424 B in runs of 16 B or more
        ([`AE_apC_apply.md`](../../scratchpad/AE_apC_apply.md), [`AE_reread_C.md`](../../scratchpad/AE_reread_C.md)). Disk corpus as slice B's but
        YOUMAKOR (phase, back to BOTH-RUN) and three no-readings that re-ran to their old classes
        ([`AE_apC_corpus3.out`](../../scratchpad/AE_apC_corpus3.out)). Left for later: fat.asm's wrblk_full can `jp wrblk_fin_req`
        (3 B before $46E6, reach unchecked).
      * Slice D (fat-prim-body: mount, FAT12 pack / unpack, the sector entries, directory search; kernel.asm's
        SFIRST / SNEXT, FDEL, RDRND, RDBLK, WRBLK, sequential write, FILES, CALL FORMAT) -- DONE 2026-11-26: 293 B
        (four list miscounts; one item kept 1 B short on purpose to keep fat_find's exit A / Z), room 424 -> 718 B
        in runs of 16 B or more ([`AE_apD_apply.md`](../../scratchpad/AE_apD_apply.md), [`AE_reread_D.md`](../../scratchpad/AE_reread_D.md)). Disk corpus: every class as
        slice C's resolved classes ([`AE_apD_diskcorpus.out`](../../scratchpad/AE_apD_diskcorpus.out)).
      ✅ THE ROOM IS MADE: ~8 B -> 718 B (2026-11-26, after slice D), every byte from re-reading. What is left is a
      RESERVE, to spend when a fix needs more -- not work to do for its own sake:
        - the medium / low-medium rows of all four lists (an inline-word call-back helper, a table reorder, ...);
        - fat.asm's wrblk_full can `jp wrblk_fin_req` (3 B before $46E6, jp reach unchecked);
        - basic/fat-prim-body.inc keeps three inline copies of fat_locate's 19 instructions; only the disk ROM
          includes it now, so they can call fat_locate (not measured).
