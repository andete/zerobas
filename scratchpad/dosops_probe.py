#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-COPYSLOW Q5 (Joost 2026-11-28 "as much info as possible before ... any code"): do OTHER operations use the same
buffers and the same FAT policy as COPY? One MSX-DOS session -- a small COPY (sequential write), TYPE (sequential
read), REN, DEL, DIR -- with every FDC command logged by step, and for every track-0 READ the 512 B window it lands in
(a RAM write watch armed only during that read, 64-byte-block histogram: ADDRESSES ONLY, no byte, no PC).
    python3 -u scratchpad/dosops_probe.py [MACHINE ...]
"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "disk"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import disk_probe_dossession as D  # noqa: E402
import omsx_preflight  # noqa: E402

machines = sys.argv[1:] or ["National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"]
SRC = os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")
STEPS = [("copy", "COPY MSXDOS.SYS X.SYS"), ("type", "TYPE README.TXT"), ("ren", "REN X.SYS Y.SYS"),
         ("del", "DEL Y.SYS"), ("dir", "DIR B*.*")]
D.SESSION = [("boot", None, 14), ("date", "", 5), ("mode", "MODE 40", 4)] + [(t, x, 2) for t, x in STEPS]
CMD = ("set ::step none; set ::wid {}; set ::fcur {}; set ::b [dict create]\n"
       "proc __cmd {base} { if {!$::counting} return; "
       "if {$::wid ne {}} { debug remove_watchpoint $::wid; set ::wid {} }; "
       "if {$::fcur ne {}} { puts $::fl \"B $::fcur $::b\" }; set ::fcur {}; "
       "set c [expr {$::wp_last_value >> 4}]; set t [peek [expr {$base + 1}]]; set s [peek [expr {$base + 2}]]; "
       "puts $::fl \"C $::step $c $t $s\"; "
       "if {$c == 8 && $t == 0} { set ::fcur \"$::step:$s\"; set ::b [dict create]; "
       "set ::wid [debug set_watchpoint write_mem {0x8000 0xFFFF} {} { set a $::wp_last_address; "
       "if {$a < 0xBF80 || $a > 0xBFBF} { dict incr ::b [expr {$a >> 6}] } }] } }\n"
       "debug set_watchpoint write_mem {0x7F80 0x7FBF} {$::counting} {if {($::wp_last_address & 7) == 0} {__cmd 0x7FB8}}\n"
       "debug set_watchpoint write_mem {0xBF80 0xBFBF} {$::counting} {if {($::wp_last_address & 7) == 0} {__cmd 0xBFB8}}\n")
order = ["mode"] + [t for t, _ in STEPS]
for m in machines:
    td = tempfile.mkdtemp()
    dsk = os.path.join(td, "d.dsk")
    subprocess.run(["cp", SRC, dsk], check=True)
    out = os.path.join(td, "o.txt")
    fl = os.path.join(td, "cmd.txt")
    tcl = D.tcl(out)
    tcl = tcl.replace("set throttle off", "set throttle off\nset ::counting 0\n"
                      f"set ::fl [open {{{fl}}} w]\n" + CMD, 1)
    a = "  close $f }"
    assert tcl.count(a) == 1
    hook = "  if {$tag eq \"mode\"} {set ::counting 1}\n"
    for k, v in zip(order, order[1:]):
        hook += f"  if {{$tag eq \"{k}\"}} {{set ::step {v}}}\n"
    hook += f"  if {{$tag eq \"{order[-1]}\"}} {{set ::counting 0; flush $::fl}}\n"
    tcl = tcl.replace(a, hook + a)
    tcl = tcl.replace("$::tries > 240", "$::tries > 12000")
    sf = os.path.join(td, "s.tcl")
    open(sf, "w").write(tcl)
    subprocess.run(omsx_preflight.guarded(["openmsx", "-machine", m, "-diska", dsk, "-command",
                   "set renderer none; set sound_driver null", "-script", sf]),
                   stdout=open(os.path.join(td, "err.txt"), "w"), stderr=subprocess.STDOUT, timeout=2400)
    print(f"== {m}   (log {td})")
    lines = open(fl).read().splitlines()
    if not any(ln.startswith("C ") for ln in lines):
        print("   NO FDC COMMANDS RECORDED -- instrument failed, not a finding")
    cnt, wins = {}, {}
    for ln in lines:
        p = ln.split()
        if p[0] == "C":
            step, c, t, s = p[1], int(p[2]), int(p[3]), int(p[4])
            if c not in (8, 10):
                continue
            k = ("FAT" if 2 <= s <= 7 else "t0") if t == 0 else "data"
            k += "r" if c == 8 else "w"
            cnt.setdefault(step, {}).setdefault(k, 0)
            cnt[step][k] += 1
        elif p[0] == "B":
            step, sec = p[1].split(":")
            blk = {int(p[i]): int(p[i + 1]) for i in range(2, len(p) - 1, 2)}
            full = sorted(k for k, v in blk.items() if v >= 48)
            # one window = a run of full blocks; its start from the partial block before it
            runs, st, prev = [], None, None
            for k in full:
                if st is None or k != prev + 1:
                    if st is not None:
                        runs.append((st, prev))
                    st = k
                prev = k
            if st is not None:
                runs.append((st, prev))
            desc = [f"${a * 64 - blk.get(a - 1, 0):04X}" for a, b in runs if b - a >= 5] or ["none"]
            wins.setdefault(step, {}).setdefault(f"s{sec}->" + ",".join(desc), 0)
            wins[step][f"s{sec}->" + ",".join(desc)] += 1
    for step in order[1:]:
        print(f"   {step:5s} " + "  ".join(f"{k}={v}" for k, v in sorted(cnt.get(step, {}).items())))
        if step in wins:
            print("         track-0 reads land: " + "  ".join(f"{k} x{v}" for k, v in sorted(wins[step].items())))
    snaps = {ln.split()[0]: ln for ln in open(out).read().splitlines()}
    if "dir" in snaps:
        p = snaps["dir"].split()
        wd = int(p[1][2:])
        b = bytes.fromhex(p[3])
        rows = [b[k * wd:(k + 1) * wd].decode("latin1").rstrip() for k in range(24)]
        print("   final screen: " + " / ".join(r for r in rows if r.strip())[-300:])
