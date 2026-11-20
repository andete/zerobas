#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TRGFLGISR part 2: what each machine's key-scan interrupt does to PSG R15. Black box, I/O only.
  latch  R15 := $AC (port 1 selected, trigger pins low, bits 2 / 3 / 5 / 7 set), wait for scans, read R15:
         a plain read-modify-write (bits kept, port 1 then port 2 selected) would leave $EF. MEASURED
         (run1): the references leave $CF -- bit 5 cleared, i.e. AND $BF OR $03, then AND $DF OR $4C.
  input  R15 := $CF, R7 := $38 (port B an INPUT, so a read of R15 returns the pins), wait, R7 := $B8,
         read R15: a scan that reads R15 back while port B is an input writes the pins ($FF) back.
No ROM byte is read.
    python3 -u scratchpad/r15scan_probe.py > scratchpad/R15SCAN_run1.out   (run2: after the fix)"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides  # noqa: E402

PROGS = {
    "latch": ["10 OUT &HA0,15:OUT &HA1,&HAC", "20 FOR I=1 TO 400:NEXT",
              "30 OUT &HA0,15:PRINT \"R=\";INP(&HA2)", "RUN"],
    "input": ["10 OUT &HA0,15:OUT &HA1,&HCF:OUT &HA0,7:OUT &HA1,&H38", "20 FOR I=1 TO 400:NEXT",
              "30 OUT &HA0,7:OUT &HA1,&HB8:OUT &HA0,15:PRINT \"R=\";INP(&HA2)", "RUN"],
}
for side in ("vg8020", "cf3300", "zb"):
    m = probe_sides.MACHINES[side]
    for name, prog in PROGS.items():
        scr = omsx_repl.run_batch(m["machine"], [("direct", prog)], boot=m["boot"], reset=m["reset"])[0] or ""
        v = re.findall(r"R=\s*(\d+)", scr)
        print(f"{side:7} {name:6} R15 = " + (f"${int(v[-1]):02X}" if v else "<none>"))
