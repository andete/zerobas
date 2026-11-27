- [ ] **GATE_WT'S PRIVATE SHARE DOES NOT ISOLATE THE RTC: openMSX's SRAM (.cmos) goes to ~/.openMSX/persistent unless
      OPENMSX_HOME is set too (D-GATEWTRTC, from the C-BIOS session's rig note 2026-11-27).**
      🎚️ APPARATUS — a gate run and a main-tree run (or two worktrees) can share RTC state; an MSX2 row that reads or
      writes the RTC (SET SCREEN, SDFSCR -- D-SDFSCR) would depend on what ran before.
      🤖 **AUTONOMOUS** — tools/gate_wt.py sets OPENMSX_USER_DATA only (its private share); set OPENMSX_HOME to a
      directory in the worktree as well, and check where .cmos lands with a run that writes the RTC.
      Today no gated row writes the RTC on purpose (every gated machine but the MSX2 / MSX2+ NOBASIC hosts is MSX1);
      MEASURE that before calling it harmless.
