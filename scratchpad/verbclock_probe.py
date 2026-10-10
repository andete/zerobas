#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-HOOKDI: does TIME keep running while each long disk verb works, as on the
National CF-3300? (D-LOADDI found disk.rom's LOAD hook running masked from start
to end -- every hook is entered through CALSLT, which returns DI.)

Per verb, a fresh copy of loadrun_probe's disk (S/M/L.BAS, 1-14 KB tokenised)
and a three-line program run in front of whatever is loaded:

    1 TIME=0
    2 <the verb>
    3 PRINT"@K";TIME:END

t0 / t1 = openMSX EMULATED time when the published CURLIN's low byte ($F41C)
is written with 2 / 3 -- RAM only, clean room on both machines. The reading is
emulated seconds against TIME's seconds; their ratio is how much of the verb
the guest's clock saw (the CF-3300 kept ~50 % of a LOAD; zerobas's masked LOAD
kept ~1 %).

    python3 -u scratchpad/verbclock_probe.py [cf3300|zb] [verb ...]   (VC_STEP=45: a
    longer wait before the capture, for a verb slower than loadrun's 25 s step)
"""
import os, shutil, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import loadrun_probe as LR                                  # seed / build / marks
import omsx_repl

TCL = r"""
set ::t0 -1
set ::t1 -1
proc ::dump {} { set f [open {OUT} w]; puts $f "$::t0 $::t1"; close $f }
debug set_watchpoint write_mem 0xF41C {} {
  if {[peek 0xF41D] != 0} return
  if {$::t0 < 0 && $::wp_last_value == 2} { set ::t0 [machine_info time]; ::dump } elseif {$::t0 >= 0 && $::t1 < 0 && $::wp_last_value == 3} { set ::t1 [machine_info time]; ::dump }
}
"""
# (pre-typed direct lines, the verb on line 2). No `load` row: a LOAD stops the
# running program, so line 3 never runs -- D-LOADDI's own gate covers it.
VERBS = {
    "save":   (['LOAD"L.BAS"'], 'SAVE"X.BAS"'),     # the 14 KB program, saved
    "asave":  (['LOAD"M.BAS"'], 'SAVE"A.BAS",A'),   # ASCII save, 7 KB tokenised
    "copy":   ([], 'COPY"L.BAS"TO"C.BAS"'),
    "files":  ([], "FILES"),
    "kill":   ([], 'KILL"L.BAS"'),
    "name":   ([], 'NAME"L.BAS"AS"N.BAS"'),
    "dskf":   ([], "X=DSKF(0)"),
    "bsave":  ([], 'BSAVE"B.BIN",&H9000,&HAFFF'),
    "bload":  (['BSAVE"B.BIN",&H9000,&HAFFF'], 'BLOAD"B.BIN"'),
}


def main():
    args = sys.argv[1:]
    only = args[0] if args and args[0] in ("cf3300", "zb") else None
    verbs = [a for a in args if a in VERBS] or list(VERBS)
    tmpd = tempfile.mkdtemp(prefix="verbclock_")
    for tag, machine, reset, hz in LR.SIDES:
        if only and only != tag:
            continue
        seeded, _n = LR.seed(machine, reset, tmpd, tag)
        dsk0, sizes, _per = LR.build(seeded, tmpd, tag)
        print(f"\n=== {tag} ({machine}, {hz} Hz) ===  sizes {sizes}", flush=True)
        print(f"  {'verb':6} {'emulated s':>11} {'TIME s':>8} {'kept':>6}")
        for v in verbs:
            pre, verb = VERBS[v]
            dsk = os.path.join(tmpd, f"{tag}_{v}.dsk")
            shutil.copyfile(dsk0, dsk)
            out = os.path.join(tmpd, f"{tag}_{v}")
            open(out, "w").close()
            typed = (["NEW"] + pre + ["1 TIME=0", f"2 {verb}",
                                      '3 PRINT"@K";TIME:END', "RUN"])
            cap = omsx_repl.run_cases(machine, [("direct", typed)], batch=False,
                                      reset=reset, boot=LR.BOOT,
                                      step=float(os.environ.get("VC_STEP", LR.STEP)),
                                      cap_gap=LR.CAP_GAP, diska=dsk, capture="screen",
                                      prologue=(TCL.replace("{OUT}", "{" + out + "}"),))[0]
            t = open(out).read().split()
            k = LR.marks(cap or "", LR.MARK)
            if len(t) != 2 or float(t[1]) < 0 or not k:
                rows = [(cap or "")[i:i + 40].strip() for i in range(0, len(cap or ""), 40)]
                tail = " | ".join(r for r in rows if r)[-120:]
                print(f"  {v:6} NO READING (clock {t}, printed {k}) screen: {tail}", flush=True)
                continue
            dt = float(t[1]) - float(t[0])
            ts = k[-1] / hz
            print(f"  {v:6} {dt:11.3f} {ts:8.3f} {ts / dt if dt > 0 else 0:6.0%}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
