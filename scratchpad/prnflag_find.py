#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-BUFINCTL: WHICH RAM CELL HOLDS MSX-DOS 1's PRINTER-ECHO FLAG (Ctrl-P on / Ctrl-N off)? At A> on the
CF-3300 (and zerobas), RAM $C000-$FFFF is dumped idle, idle again (the noise), after Ctrl-P, after Ctrl-N.
A cell that differs only across the keys, and back, is the candidate. Clean room: RAM contents only."""
import os, shutil, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_preflight, probe_tmp  # noqa: E402
DOS = os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")
for side, m in (("CF", "National_CF-3300"), ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK")):
    td = tempfile.mkdtemp(dir=probe_tmp.ROOT)
    d = os.path.join(td, "d.dsk"); shutil.copyfile(DOS, d)
    out = os.path.join(td, "o.txt"); prn = os.path.join(td, "p.txt")
    def dump(tag, t):
        return (f'after time {t} {{ set f [open {{{out}}} a]; binary scan [debug read_block memory 0xC000 0x4000] H* v; '
                f'puts $f "{tag} $v"; close $f }}\n')
    def ctl(k, t):
        return (f"after time {t} {{keymatrixdown 6 2}}\nafter time {t+0.1} {{type {k}}}\n"
                f"after time {t+0.5} {{keymatrixup 6 2}}\n")
    s = (f"set throttle off\nset printerlogfilename {{{prn}}}\nplug printerport logger\n"
         + dump("idle1", 30) + dump("idle2", 31) + ctl("p", 32) + dump("ctlp", 34)
         + ctl("n", 35) + dump("ctln", 37) + "after time 38 exit\n")
    tcl = os.path.join(td, "s.tcl"); open(tcl, "w").write(s)
    subprocess.run(omsx_preflight.guarded(["openmsx", "-machine", m, "-diska", d, "-command",
                   "set renderer none; set sound_driver null", "-script", tcl]),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    dm = {l.split()[0]: bytes.fromhex(l.split()[1]) for l in open(out)} if os.path.exists(out) else {}
    if len(dm) < 4:
        print(side, "NO READING"); continue
    noise = {i for i in range(0x4000) if dm["idle1"][i] != dm["idle2"][i]}
    hits = [i for i in range(0x4000) if i not in noise
            and dm["idle2"][i] != dm["ctlp"][i] and dm["ctln"][i] == dm["idle2"][i]]
    other = [i for i in range(0x4000) if i not in noise and i not in hits
             and (dm["idle2"][i] != dm["ctlp"][i] or dm["ctlp"][i] != dm["ctln"][i])]
    print(side, "toggled by ^P and restored by ^N:",
          ", ".join(f"${0xC000+i:04X} {dm['idle2'][i]:02X}->{dm['ctlp'][i]:02X}->{dm['ctln'][i]:02X}" for i in hits) or "none")
    print(side, f"other changed cells: {len(other)}", ", ".join(f"${0xC000+i:04X}" for i in other[:24]))
    shutil.rmtree(td, ignore_errors=True)
