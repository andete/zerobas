- [ ] **BDOS $00 THROUGH $F37D: THE REST OF THE CALLING LINE STILL RUNS ON ZEROBAS (D-F37DTERMLINE, filed 2026-11-26 when
      D-F37DTERM landed its program-end half).**
      🎚️ TIER 6 — every edge: a program that calls function 0 through $F37D, with more statements after the call.
      🤖 **AUTONOMOUS** — the gate pins it (`make f37dterm-acceptance`, row `after`).
      `30 DEFUSR=&HD000:X=USR(0):PRINT "AFTER"` with the stub `ld c,0 / call $F37D / ret`: the CF-3300 prints nothing
      more; zerobas (bb_term sets ENDFLAG as END does) ends the run at the END of line 30, so AFTER still prints. END
      stops mid-line because its handler RETURNS to the run loop instead of jumping on to exec_stmt; a flag set from
      inside a USR call cannot do that -- the assignment's handler goes on to the next statement. Options (all BASIC
      side, main ROM): (a) exec_stmt tests ENDFLAG at every statement head (cheap in bytes, a cost on EVERY
      statement -- tier 5); (b) a value in INTFLG that es_latch (basic/keytrap.asm, only reached when INTFLG <> 0)
      turns into a silent run end -- no fast-path cost, but INTFLG is the published STOP-key cell; (c) a page-0
      routine the disk ROM jumps to that restores page 1 to BASIC's slot and unwinds to SAVSTK with interrupts back
      on, as the abort funnel does without its message. Measure first how the CF-3300 leaves interrupts and the
      stack (FRE(0) is already SAME).
