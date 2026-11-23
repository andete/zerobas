- [x] ✅ **TWO FILES WRITTEN AND READ TOGETHER CAME BACK WRONG — TWO BUGS, ONE OF THEM
      MINE (D-CHANSWITCH, found and fixed 2026-09-29).**
      🎚️ TIER 1 — happy path: writing two files at once (a report and a log, a
      merge) is ordinary.
      [`chanloop_run4.out`](scratchpad/chanloop_run4.out) (`scratchpad/chanloop_probe.py`,
      readable only since D-INPNUM): `PRINT #1,1:PRINT #2,10:PRINT #1,2:PRINT #2,20`
      reads back `1 2 | 10 20` on the CF-3300 and `1 0 2 0 || 55` here. With FOR
      or GOSUB frames standing it is worse (no reading at all). The `forloop`,
      `gosub` and `nested` cases were built to test a SEPARATE hypothesis, read off
      the code: `sh_chan_addr` derives the block address from `strheap_varceil`,
      which returns `min(ceiling, CSP)`. So a standing control frame would MOVE
      the channel blocks and a save would write over the newest frame. The
      straight-line failure comes first; the frame hypothesis is still unanswered.
      Also here: the STRING-item leading-blank divergence from D-INPNUM.
      🔬 **THE BYTES FIRST** ([`chanloop_run5.out`](scratchpad/chanloop_run5.out)): both
      files are BYTE-IDENTICAL on the two machines after the alternating writes
      (`INPUT$(LOF(1),#1)` read 55 on BOTH, since LOF counts the Ctrl-Z; the dump
      reads to EOF instead). Two INPUT channels switched with LINE INPUT agree too
      ([`chanloop_run7.out`](scratchpad/chanloop_run7.out)). So the fault was on the
      numeric READ side, and it was **(1) MINE, from D-INPNUM an hour earlier**.
      The numeric item ended at the blank after the number and left `" \r\n"`, so
      `EOF(1)` stayed false and the next read returned 0 or 55. Measured what the
      reference consumes ([`inpnum_run3.out`](scratchpad/inpnum_run3.out)): blanks,
      then ONE CR-LF or ONE comma, and any other byte stays for the next item
      (`" 1  2 "` leaves "2 "). That needs a PEEK, so the item now reads in the
      seqio tenant (`sq_numitem`, sub page 1, L = 4). `read_into_strscr` is back
      to its two modes, and a CAS: channel keeps the field rule.
      **(2) THE FRAME HYPOTHESIS, CONFIRMED** ([`chanloop_run8.out`](scratchpad/chanloop_run8.out)):
      with that fixed, the FOR / GOSUB / nested cases still gave NO READING and
      53. `sh_chan_addr` took the block address from `strheap_varceil`, whose
      D-CTLPOOL clamp returns CSP while a frame stands, so a channel switch saved
      306 B over the FOR/GOSUB frame. It now calls `strheap_chantab`, varceil's
      first half without the clamp (+3 B of sub page 0). Walls 2026-09-29: main low
      3 B, page 1 22 B, sub page 0 18 B, sub page 1 524 B
      ([`chanswitch_walls.out`](scratchpad/chanswitch_walls.out)).
      ✅ **After** ([`chanloop_run9.out`](scratchpad/chanloop_run9.out)): all six
      channel cases agree; all 26 numeric file cases agree
      ([`chanswitch_inpnum.out`](scratchpad/chanswitch_inpnum.out)). Rows `inputnum2`
      (the CR-LF goes with the number) and `chanfor` (two channels switched in a
      FOR loop) are SUPPORTED ([`chanswitch_kwsweep.out`](scratchpad/chanswitch_kwsweep.out)).
      One-line knives, hash-checked, turn each DIVERGENT and nothing else
      ([`chanswitch_knife.out`](scratchpad/chanswitch_knife.out)). Whole sweep SUPPORTED
      957 ([`chanswitch_kwsweep_full.out`](scratchpad/chanswitch_kwsweep_full.out)),
      kwtime OK 843 ([`chanswitch_kwtime.out`](scratchpad/chanswitch_kwtime.out)), knife
      BLIND unchanged ([`chanswitch_knife_all.out`](scratchpad/chanswitch_knife_all.out),
      [`chanswitch_knife_fn.out`](scratchpad/chanswitch_knife_fn.out)); all predicted.
      🔴 **THE LESSON, AND IT IS ONE I HAD FILED:** D-INPNUM's 20 file cases never
      read a number FOLLOWED by another read across a line end, so they could not
      see what the item consumed. The first reading of this bug blamed the channel
      switch; the bytes said otherwise.
      ~~⚠️ **Still open:** a STRING item keeps its leading blank here, and the
      CF-3300 strips it (`one1s`, [`chanloop_run3.out`](scratchpad/chanloop_run3.out)).
      The console's string rule is unmeasured.~~ → D-INPSTR / D-INPQUOTE below.
      ⚠️ Tape (CAS:) numeric items keep the field rule (no peek there).
