- [ ] 📼 **D-TAPINBLK — $72D4 PAST A BLOCK'S END, AND $72E9 WITH NO TAPE
      (2026-10-16)**
      🎚️ TIER 6 — no title known to need it.
      🤖 **AUTONOMOUS** — measure first.
      📏 scratchpad/basicint_tape_probe.out: reading 40 bytes from a one-file tape
      after one $72E9, the VG-8020 returns the 16-byte header, then `FF`, then the
      next block's bytes; zerobas raises 19 at the block's end (row `stop`). With
      no cassette the VG-8020's $72E9 waits (Ctrl-STOP ends it, row `break`);
      zerobas's raises 19 at once (row `notape`). Both are zerobas's own TAPION /
      TAPIN (tape/tape.asm) against the reference's: whether its TAPIN rides over
      a leader, and how long its TAPION waits on silence (cassette.md already
      lists the silence case as not compared).
