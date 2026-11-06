# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FATRES: does the CF-3300 keep the PHANTOM drive B:'s FAT resident too, and
where? Normal boot, disk/test720.dsk in the one drive: `FILES` (drive A), then
`FILES "B:"` (the change-disk prompt answered with a key: the same disk), then RAM
$8000-$FFFF is dumped and every copy of the FAT's 1536 bytes is located. RAM ONLY
(clean-room)."""
import os, shutil, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import omsx_preflight, probe_tmp  # noqa: E402
from omsx_repl import key_proc  # noqa: E402
import run_programs as rp  # noqa: E402

TCL = r"""
set throttle off
KEYPROC
proc __dump {f} { set o [open $f w]; fconfigure $o -translation binary; puts -nonewline $o [debug read_block memory 0x8000 0x8000]; close $o }
after time 6 { type "\r" }
after time 10 { type "\r" }
after time 16 { __key "FILES\r" }
after time 22 { __dump {OUT}.a; __key "FILES \"B:\"\r" }
after time 26 { type " " }
after time 34 { __dump {OUT}.b; exit }
"""
dsk = probe_tmp.tmp("fatresb.dsk")
shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
out = probe_tmp.tmp("fatresb")
tcl = probe_tmp.tmp("fatresb.tcl")
open(tcl, "w").write(TCL.replace("{OUT}", out).replace("KEYPROC", key_proc()))
fat = open(dsk, "rb").read()[512:512 + 1536]
subprocess.run(omsx_preflight.guarded([rp.OMSX, "-machine", "National_CF-3300", "-command",
               "set renderer none; set sound_driver null", "-script", tcl, "-diska", dsk]),
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
for lab, f in (("after FILES (A:)", out + ".a"), ('after FILES "B:"', out + ".b")):
    ram = open(f, "rb").read()
    hits, i = [], 0
    while True:
        j = ram.find(fat[:12], i)
        if j < 0:
            break
        n = 0
        while n < 1536 and j + n < len(ram) and ram[j + n] == fat[n]:
            n += 1
        hits.append(f"${0x8000 + j:04X} ({n} B)")
        i = j + 1
    print(f"{lab}: FAT copies at " + (", ".join(hits) or "NONE"))
