#!/usr/bin/env python3
r"""D-GICINI, the amplitude half: does the abort SILENCE the PSG, or only zero MUSICF?

`gicini_probe.py` measured the BASIC-visible fact (MUSICF goes 0 on both
references after an untrapped error / STOP / BEEP, and stays 1 on zerobas). That
fixes WHAT diverges but not HOW WIDE the fix must be:

  * if the reference only zeroes MUSICF, the servicer stops writing and the last
    amplitude SUSTAINS -- a note that never ends;
  * if it runs a real GICINI-equivalent, the amplitudes go to 0 as well.

🔴 THE FIRST IS PHYSICALLY ABSURD AND THAT IS EXACTLY WHY IT MUST BE MEASURED
RATHER THAN ARGUED. "Obviously it must silence" is the shape of a justification
parenthesis, which is the class that produced this whole slice.

The instrument is `probes/lib/psgtrace.py` -- the same per-VBLANK PSG register
trace that characterised the Slice-3 drain. R8/R9/R10 are the three amplitudes.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "lib"))
import psgtrace

# 🔴 ROUND 2 TYPED BEFORE THE MACHINES HAD BOOTED. It used one fixed tp=6.0 s
# for all three sides; `basic_probe_deffn.SIDES` records boot=8.0/14.0/8.0 and a
# per-side reset burst. Five of six runs read peak amplitude 0 -- and the sixth's
# 3-frame blip was the boot click, not music. The instrument was measuring an
# unbooted machine and reporting silence. Timings and the reset now come from
# the SAME table the row probe uses, so the two cannot drift apart.
MACHINES = {
    "vg8020": ("Philips_VG_8020", 8.0, ""),
    "cf3300": ("National_CF-3300", 14.0, "\\rSCREEN 0\\rNEW\\r"),
    "zb":     ("C-BIOS_MSX1_EU_REPACK_DISK", 8.0, ""),
}
# 🔴 ROUND 1 WAS BLIND AND ITS OWN OUTPUT PROVED IT: all three sides read
# amplitudes 0 on EVERY sampled frame, which is what "the abort silenced it"
# and "the program never ran" look like alike. The quotes were double-escaped
# (`\\"` here plus psgtrace's own `.replace`), so the typed line was garbage.
# The fix is BOTH halves: escape once, and add a POSITIVE CONTROL stimulus with
# no abort in it -- a run that must show NONZERO amplitudes, or the instrument
# is not looking at music. [[readout-blind-to-its-own-subject]]
STIM = {
    "ctl":  '10 PLAY"L1CDEFGAB"\\r20 GOTO 20\\rRUN',   # never aborts: music plays
    "stop": '10 PLAY"L1CDEFGAB"\\r20 STOP\\rRUN',      # the `e.stop` row, traced
}
# 🔴 ROUND 3 STILL READ PEAK 0 ON THE CONTROL, AND THAT IS THE ONLY REASON THE
# ROUND-3 SUBJECT ROWS WERE NOT BELIEVED. The separator must be the TWO-CHARACTER
# sequence backslash-r, which Tcl turns into Enter inside the generated script; a
# real 0x0D byte written into the .tcl does not survive. Smoke-tested both ways
# on the VG-8020 before this run: single direct PLAY -> peak 136, two-line
# program + RUN -> peak 136, real-CR form -> peak 0.
for side in (sys.argv[1:] or ["vg8020", "cf3300", "zb"]):
    machine, boot, reset = MACHINES[side]
    tp, arm = boot + 1.0, boot + 6.0
    for kind, stmt in STIM.items():
        out = f"/tmp/zerobas/psg_{side}_{kind}.txt"
        psgtrace.trace(machine, reset + stmt, out, n=400, tp=tp, arm=arm,
                       deadline=arm + 14.0)
        rows = psgtrace.parse(out) if os.path.exists(out) else []
        amps = [(r[8], r[9], r[10]) for _, r in rows]
        peak = max((max(a) for a in amps), default=None)
        print(f"\n=== {side}/{kind}: {len(rows)} frames, peak amplitude {peak} ===")
        if not rows:
            print("  <NO TRACE>"); continue
        prev = None
        shown = 0
        for fc, r in rows:
            a = (r[8], r[9], r[10])
            if a != prev and shown < 12:
                print(f"  f{fc:<7d} R8={r[8]:<3d} R9={r[9]:<3d} R10={r[10]:<3d}"
                      f"  R7={r[7]:#04x}")
                prev = a; shown += 1
        fc, r = rows[-1]
        print(f"  LAST f{fc}: amps=({r[8]},{r[9]},{r[10]})")
print("\ndone")
