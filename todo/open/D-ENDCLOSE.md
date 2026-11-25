- [ ] 🐛 **END CLOSES OPEN FILES ON THE VG-8020; ZEROBAS LEAVES THEM OPEN (D-ENDCLOSE, found 2026-11-25 by D-KWSPEC's goldfish pass
      1 over END / STOP / CONT / RUN).**
      🎚️ TIER 6 — every edge: only a `PRINT #` after END can see it.
      🤖 **AUTONOMOUS** — [`kstop.py`](../../probes/basic/spec/kstop.py) -> [`KSP_run1.out`](../../scratchpad/KSP_run1.out)
      KST FY 2: `10 OPEN "CRT:" FOR OUTPUT AS #1:END` / `RUN` / `PRINT #1,"[X]"` -- the VG-8020 says `File not OPEN`,
      zerobas prints `[X]`. ⚠️ END.md's "Open files stay open" was measured on the CF-3300 (a disk file): the two
      references may DIFFER, or a disk file and `CRT:` may. Measure END + a disk file on the VG-8020 + Sony HBD-F1 and
      the CF-3300 before fixing; if the references split on a capability, the ruling for splits is Joost's.
      🧭 JOOST 2026-11-25: "yes, measure that" -- END with a DISK file open on the VG-8020 + Sony HBD-F1 and on the
      CF-3300 (probes/disk/disk_probe_dosmode.py's launcher takes `-ext`); not yet started (Joost: "don't do it now").
      Which machine zerobas follows if they truly split is still to be ruled.
