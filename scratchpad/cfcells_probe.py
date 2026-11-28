#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-COPYSLOW Q1 + Q2 (Joost 2026-11-28 "as much info as possible before ... any code").
Q1: WHERE does the reference keep its small disk-system state? For a whole COPY, every RAM write in $DE77-$F37F (its
claim up to the fixed area's end) is counted per 16-byte block and per the KIND of the last FDC command before it
(F = FAT-sector, D = other track-0 sector, r / w = data read / write, x = no transfer). ADDRESSES ONLY: no byte is read,
no PC (clean room). The four 512 B buffers measured by fatdest_probe.py are folded into one line each.
Q2: every data command's track, in order, so the reads after the data writes can be placed (source or destination).
    python3 -u scratchpad/cfcells_probe.py [SRC] [MACHINE ...]      (DSK=image to use another disk)
"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "disk"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import disk_probe_dossession as D  # noqa: E402
import omsx_preflight  # noqa: E402

src = sys.argv[1] if len(sys.argv) > 1 else "MSXBUNSE.ROM"
machines = sys.argv[2:] or ["National_CF-3300"]
D.SESSION = [("boot", None, 14), ("date", "", 5), ("mode", "MODE 40", 4), ("copy", f"COPY {src} BIG.ROM", 1)]
# the buffers fatdest_probe.py measured on the CF-3300 (folded; their per-block counts are not state cells)
BUFS = [(0xE595, 0xEB94, "FAT image"), (0xEB95, 0xED94, "sector buf"), (0xED95, 0xEF94, "data buf"),
        (0xEF95, 0xF194, "mount buf")]
CMD = ("set ::kind x; set ::cells [dict create]\n"
       "proc __cmd {base} { if {!$::counting} return; "
       "set c [expr {$::wp_last_value >> 4}]; set t [peek [expr {$base + 1}]]; set s [peek [expr {$base + 2}]]; "
       "puts $::fl \"C $c $t $s\"; "
       "if {$c == 8 || $c == 10} { if {$t == 0} { set ::kind [expr {$s >= 2 && $s <= 7 ? {F} : {D}}] } "
       "else { set ::kind [expr {$c == 8 ? {r} : {w}}] } } else { set ::kind x } }\n"
       "debug set_watchpoint write_mem {0x7F80 0x7FBF} {$::counting} {if {($::wp_last_address & 7) == 0} {__cmd 0x7FB8}}\n"
       "debug set_watchpoint write_mem {0xBF80 0xBFBF} {$::counting} {if {($::wp_last_address & 7) == 0} {__cmd 0xBFB8}}\n"
       "debug set_watchpoint write_mem {0xDE77 0xF37F} {$::counting} { set a $::wp_last_address; "
       "if {$a < 0xBF80 || $a > 0xBFBF} { dict incr ::cells \"[expr {$a >> 4}]:$::kind\" } }\n")
for m in machines:
    td = tempfile.mkdtemp()
    dsk = os.path.join(td, "d.dsk")
    subprocess.run(["cp", os.environ.get("DSK", os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")), dsk], check=True)
    out = os.path.join(td, "o.txt")
    fl = os.path.join(td, "cmd.txt")
    tcl = D.tcl(out)
    tcl = tcl.replace("set throttle off", "set throttle off\nset ::counting 0\n"
                      f"set ::fl [open {{{fl}}} w]\n" + CMD, 1)
    a = "  close $f }"
    assert tcl.count(a) == 1
    tcl = tcl.replace(a, "  if {$tag eq \"mode\"} {set ::counting 1}\n"
                         "  if {$tag eq \"copy\"} {set ::counting 0; puts $::fl \"CELLS $::cells\"; flush $::fl}\n" + a)
    tcl = tcl.replace("$::tries > 240", "$::tries > 12000")
    sf = os.path.join(td, "s.tcl")
    open(sf, "w").write(tcl)
    subprocess.run(omsx_preflight.guarded(["openmsx", "-machine", m, "-diska", dsk, "-command",
                   "set renderer none; set sound_driver null", "-script", sf]),
                   stdout=open(os.path.join(td, "err.txt"), "w"), stderr=subprocess.STDOUT, timeout=2400)
    lines = open(fl).read().splitlines()
    big = [e for e in D.disk_listing(bytearray(open(dsk, "rb").read())) if e.startswith("BIG.")]
    print(f"== {m}: {' | '.join(big) or 'NO BIG.ROM -- the COPY did not happen'}   (log {td})")
    cl = next((ln for ln in lines if ln.startswith("CELLS ")), "CELLS").split()[1:]
    cells = {}
    for i in range(0, len(cl) - 1, 2):
        blk, kind = cl[i].split(":")
        cells.setdefault(int(blk) * 16, {})[kind] = int(cl[i + 1])
    if not cells:
        print("   NO CELL WRITES RECORDED -- instrument failed, not a finding")
    print("   -- Q1: writes per 16 B block in $DE77-$F37F, by the last FDC command's kind (F FAT, D track-0 other, "
          "r/w data, x none) --")
    folded = {}
    for a in sorted(cells):
        b = next((n for lo, hi, n in BUFS if lo <= a <= hi), None)
        if b:
            for k, v in cells[a].items():
                folded.setdefault(b, {}).setdefault(k, 0)
                folded[b][k] += v
            continue
        print(f"   ${a:04X}  " + "  ".join(f"{k}={v}" for k, v in sorted(cells[a].items())))
    for lo, hi, n in BUFS:
        if n in folded:
            print(f"   [{n} ${lo:04X}-${hi:04X}]  " + "  ".join(f"{k}={v}" for k, v in sorted(folded[n].items())))
    # Q2: data commands' tracks in order, runs collapsed
    seq = []
    for ln in lines:
        p = ln.split()
        if p[0] != "C" or int(p[1]) not in (8, 10) or int(p[2]) == 0:
            continue
        tok = ("r" if int(p[1]) == 8 else "w") + p[2]
        if seq and seq[-1][0] == tok:
            seq[-1][1] += 1
        else:
            seq.append([tok, 1])
    print("   -- Q2: data commands as <r|w><track>*count, in order --")
    print("   " + " ".join(t if n == 1 else f"{t}*{n}" for t, n in seq))
