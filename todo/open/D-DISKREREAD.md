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
      * Slice C -- OPEN: [`AE_reread_C.md`](../../scratchpad/AE_reread_C.md), ~176 B claimed in the low-risk rows (2026-11-26, at a89a93d15).
      * Slice D -- OPEN: [`AE_reread_D.md`](../../scratchpad/AE_reread_D.md), ~295 B claimed in the low-risk rows (2026-11-26, at a89a93d15).
      Medium-risk rows (an inline-word call-back helper, a table reorder) are skipped until the low rows are spent.
