- [ ] 🐛 **ENTERING A PROGRAM LINE RESETS RND'S SEQUENCE ON THE VG-8020 (BACK TO ITS POWER-ON START), NOT HERE
      (D-RNDLINE, found 2026-11-24 by D-KWSPEC's RND unit).**
      🎚️ TIER 1 — a value difference in plain use: `PRINT RND(1)` typed in direct mode, then a program line typed or
      edited, then `PRINT RND(1)` again prints .59521943994623 on the reference (the sequence restarted) and the
      NEXT number of the old sequence here. A program that is typed and then RUN is unaffected (RUN resets on both).
      🤖 **AUTONOMOUS** — measured by [`krnd.py`](../../probes/basic/spec/krnd.py) (groups BOOT and GOTO2) ->
      [`KRN_run1.out`](../../scratchpad/KRN_run1.out); rule R-RND-START on [RND.md](../../docs/keywords/RND.md),
      cases KRN BOOT 6 (direct `RND(1)` x 3, `CLS`, `RND(1)`, then `10 REM`: RNDX is 00 40 64 96 51 37 23 58 there,
      the stepped 00 76 59 76 51 77 28 23 here) and KRN GOTO2 0 (a program, `RND(1)` x 2 and `RND(-7)` from direct
      mode, then `99 REM`, then `GOTO 5`; GOTO alone keeps the state on both, KRN GOTO 0). CLEAR, NEW and RUN reset it
      on both machines. 5 cases (BOOT 6-7, GOTO2 0-2).
      ➡️ When picked up: a program edit reaches `vars_reset` (basic/arrays.asm, via the relink in basic/files.asm)
      but not `clear_vars` (basic/vars.asm), which is where RNDX is set to S0 -- so an edit wipes the variables
      and keeps the seed. Whether the edit path skips anything ELSE `clear_vars` resets is not measured. The
      acceptance is R-RND-START and the control "entering a program line keeps the state -- zerobas's" in
      [`krnd_controls.py`](../../probes/basic/spec/krnd_controls.py).
