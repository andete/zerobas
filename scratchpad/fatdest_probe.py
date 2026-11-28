#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-COPYSLOW / Joost 2026-11-28 "where does the reference cache this?": WHERE does each FAT-sector read land in RAM?
While a read command to a FAT sector (track 0, sectors 2-7) runs -- from the command-register write to the next one,
at either mirror ($7FB8 / $BFB8) -- a RAM write watch ($8000-$FFFF) records only the ADDRESSES written (min, max,
count). No byte is read: not the reference's RAM-resident code, not the data, no PC (clean room). Also the same for
FAT-sector WRITES: none of the RAM is read, only the command's track/sector registers.
    python3 -u scratchpad/fatdest_probe.py [SRC] [MACHINE ...]
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
machines = sys.argv[2:] or ["National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"]
D.SESSION = [("boot", None, 14), ("date", "", 5), ("mode", "MODE 40", 4), ("copy", f"COPY {src} BIG.ROM", 1)]
# The RAM watch is CREATED at a FAT-read command and REMOVED at the next command: armed for the whole run, its condition
# ran Tcl on every page-2/3 write (every push) and the CF-3300 crawled for 39 min without passing the date prompt (2026-11-28).
CMD = ("set ::wid {}; set ::fcur {}; set ::b [dict create]\n"
       "proc __cmd {base} { if {!$::counting} return; "
       "if {$::wid ne {}} { debug remove_watchpoint $::wid; set ::wid {} }; "
       "if {$::fcur ne {}} { puts $::fl \"$::fcur $::b\" }; set ::fcur {}; "
       "set c [expr {$::wp_last_value >> 4}]; set t [peek [expr {$base + 1}]]; set s [peek [expr {$base + 2}]]; puts $::fl \"C $c $t $s\"; "
       "if {$c == 8 && $t == 0 && $s >= 2 && $s <= 7} { set ::fcur \"R$s\"; set ::b [dict create]; "
       "set ::wid [debug set_watchpoint write_mem {0x8000 0xFFFF} {} { set a $::wp_last_address; "
       "if {$a < 0xBF80 || $a > 0xBFBF} { dict incr ::b [expr {$a >> 6}] } }] } }\n"
       "debug set_watchpoint write_mem {0x7F80 0x7FBF} {$::counting} {if {($::wp_last_address & 7) == 0} {__cmd 0x7FB8}}\n"
       "debug set_watchpoint write_mem {0xBF80 0xBFBF} {$::counting} {if {($::wp_last_address & 7) == 0} {__cmd 0xBFB8}}\n")
for m in machines:
    td = tempfile.mkdtemp()
    dsk = os.path.join(td, "d.dsk")
    subprocess.run(["cp", os.environ.get("DSK", os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")), dsk], check=True)
    out = os.path.join(td, "o.txt")
    fl = os.path.join(td, "fat.txt")
    tcl = D.tcl(out)
    tcl = tcl.replace("set throttle off", "set throttle off\nset ::counting 0\nset ::fcur {}\n"
                      f"set ::fl [open {{{fl}}} w]\n" + CMD, 1)
    a = "  close $f }"
    assert tcl.count(a) == 1
    tcl = tcl.replace(a, "  if {$tag eq \"mode\"} {set ::counting 1}\n  if {$tag eq \"copy\"} {set ::counting 0; flush $::fl}\n" + a)
    tcl = tcl.replace("$::tries > 240", "$::tries > 12000")
    sf = os.path.join(td, "s.tcl")
    open(sf, "w").write(tcl)
    subprocess.run(omsx_preflight.guarded(["openmsx", "-machine", m, "-diska", dsk, "-command",
                   "set renderer none; set sound_driver null", "-script", sf]),
                   stdout=open(os.path.join(td, "err.txt"), "w"), stderr=subprocess.STDOUT, timeout=2400)
    print("   (emulator log: " + os.path.join(td, "err.txt") + ")")
    allr = [ln.split() for ln in open(fl).read().splitlines()]
    rows = [r for r in allr if r[0] != "C"]
    # the command order (every FDC command while counting): r/w = data read/write, R<s>/W<s> = FAT sector s,
    # D<s> = other track-0 (directory) sector, x<class> = a non-transfer command; runs collapsed as tok*n
    seq = []
    for r in allr:
        if r[0] != "C":
            continue
        c, t, sc = int(r[1]), int(r[2]), int(r[3])
        if c in (8, 10):
            k = ("R" if c == 8 else "W") if t == 0 and 2 <= sc <= 7 else ("D" if c == 8 else "E") if t == 0 else ("r" if c == 8 else "w")
            tok = k + (str(sc) if t == 0 else "")
        else:
            tok = f"x{c}"
        if seq and seq[-1][0] == tok:
            seq[-1][1] += 1
        else:
            seq.append([tok, 1])
    print("   order: " + " ".join(t if n == 1 else f"{t}*{n}" for t, n in seq))
    print(f"== {m}: {len(rows)} FAT-sector reads during the COPY")
    # a sector landing in a buffer writes each byte once: 64-byte blocks with >= 48 writes, grouped into runs
    agg = {}
    for r in rows:
        blk = {int(r[i]): int(r[i + 1]) for i in range(1, len(r) - 1, 2)}
        full = sorted(k for k, v in blk.items() if v >= 48)
        runs, st = [], None
        for k in full:
            if st is None or k != prev + 1:
                if st is not None: runs.append((st, prev))
                st = k
            prev = k
        if st is not None: runs.append((st, prev))
        key = (r[0], tuple(runs))
        agg[key] = agg.get(key, 0) + 1
    for (sec, runs), k in sorted(agg.items()):
        print(f"   {sec} x{k}: " + ", ".join(f"${a * 64:04X}-${b * 64 + 63:04X}" for a, b in runs))
