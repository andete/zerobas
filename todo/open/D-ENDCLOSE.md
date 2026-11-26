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
      ✅ MEASURED 2026-11-26 (`make endclose-acceptance`, probes/disk/disk_probe_endclose.py, scratchpad/AE_endclose1.out):
      THE REFERENCES DO NOT SPLIT. `10 OPEN "<dev>" FOR OUTPUT AS #1:END` / RUN / `PRINT #1,"[X]"` -- the VG-8020 + Sony
      HBD-F1 (composed as Philips_VG_8020_HBDF1 from openMSX's own configs) and the CF-3300 both answer `File not OPEN`,
      for a disk file AND for CRT:. 🔮 "the CF-3300 keeps a disk file open" (END.md's old note): MISS -- it closes it;
      END.md corrected. zerobas keeps both open (CRT: prints [X]; the disk file takes the line silently). No ruling
      needed: the fix is END closing every file, as both references do. Pinned in the gate as KNOWN until it lands.
      ⏸️ A BASIC-side fix (END's path in basic/, closing through the disk hooks): it waits behind the disk ROM per
      Joost's focus (2026-11-25).
