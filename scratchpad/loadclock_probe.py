#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-LOADRUN, re-measured 2026-10-10 with a clock OUTSIDE the guest.

scratchpad/loadrun_probe.py reads `TIME` as printed by the loaded program. On
2026-10-10 zerobas read 3 jiffies for a 1 KB AND a 14 KB load (its own control
refused: the large load did not exceed the small one), so either the load is
that fast or zerobas's `TIME` does not advance while it loads. This probe tells
the two apart: the same programs and driver (loadrun_probe's seed/build), but
the time is openMSX's EMULATED time, stamped by a watchpoint on the published
CURLIN cell's low byte ($F41C) -- RAM only, clean room on both machines:

  t0  CURLIN := 20, the driver's `20 LOAD"x",R` starting
  t1  CURLIN := 10 after it, the LOADED program's first line starting

(A first cut watched JIFFY's high byte, $FC9F, as a "nearly unique" stamp; it
read 0.000 s on both machines -- the timer interrupt reads AND writes the
16-bit JIFFY every tick.)

and the jiffies the program printed beside it. Emulated seconds against
jiffies/Hz says whether the guest's clock kept time during the load.

    python3 -u scratchpad/loadclock_probe.py [cf3300|zb]
"""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import loadrun_probe as LR                                  # seed / build / marks
import omsx_repl

TCL = r"""
set ::t0 -1
set ::t1 -1
proc ::dump {} { set f [open {OUT} w]; puts $f "$::t0 $::t1"; close $f }
debug set_watchpoint write_mem 0xF41C {} {
  if {$::t0 < 0 && $::wp_last_value == 20} { set ::t0 [machine_info time]; ::dump } elseif {$::t0 >= 0 && $::t1 < 0 && $::wp_last_value == 10} { set ::t1 [machine_info time]; ::dump }
}
"""


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    tmpd = tempfile.mkdtemp(prefix="loadclock_")
    for tag, machine, reset, hz in LR.SIDES:
        if only and only != tag:
            continue
        seeded, _n = LR.seed(machine, reset, tmpd, tag)
        dsk, sizes, _per = LR.build(seeded, tmpd, tag)
        print(f"\n=== {tag} ({machine}, {hz} Hz) ===  sizes {sizes}", flush=True)
        print(f"  {'case':5} {'bytes':>6} {'emulated s':>11} {'jiffies printed':>16} {'= s':>7}")
        for name in ("S", "M", "L"):
            out = os.path.join(tmpd, f"{tag}_{name}")
            open(out, "w").close()
            cap = omsx_repl.run_cases(machine, [("stored", ["TIME=0", f'LOAD"{name}.BAS",R'])],
                                      batch=False, reset=reset, boot=LR.BOOT, step=LR.STEP,
                                      cap_gap=LR.CAP_GAP, diska=dsk, capture="screen",
                                      prologue=(TCL.replace("{OUT}", "{" + out + "}"),))[0]
            t = open(out).read().split()
            k = LR.marks(cap or "", LR.MARK)
            if len(t) != 2 or float(t[1]) < 0 or not k:
                print(f"  {name:5} NO READING (clock {t}, printed {k})", flush=True)
                continue
            dt = float(t[1]) - float(t[0])
            print(f"  {name:5} {sizes[name]:6} {dt:11.3f} {k[0]:16} {k[0] / hz:7.3f}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
