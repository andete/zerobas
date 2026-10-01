#!/usr/bin/env python3
"""D-DOSDATE design input: $F330..$F345 before/after SDATE 1999-12-31 on both
machines (work-area RAM, readable), and -- on OURS only -- the first page-1 PCs
during the SDATE call (our own ROM's entry). Clean room: no ROM bytes, no
reference code bytes; on the CF-3300 only RAM is read."""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
from disk_probe_bdos import fat12_add               # noqa: E402
import disk_probe_wrblk_roundtrip as RT             # noqa: E402
import disk_probe_wrblk_alt as W                    # noqa: E402
import probe_tmp                                    # noqa: E402

import subprocess                                  # noqa: E402
HERE = os.path.dirname(os.path.abspath(__file__))  # scratchpad/, beside sdatemem.asm
subprocess.run(["pasmo", "--bin", os.path.join(HERE, "sdatemem.asm"), probe_tmp.tmp("sdatemem.com")],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
COM = open(probe_tmp.tmp("sdatemem.com"), "rb").read()

for tag, machine in (("STOCK", RT.REF_MACHINE), ("OURS", RT.OUR_MACHINE)):
    dsk = probe_tmp.tmp(f"sdatemem_{tag}.dsk")
    shutil.copyfile(RT.DEFAULT_DOS, dsk)
    img = bytearray(open(dsk, "rb").read())
    fat12_add(img, "SDATEMEM", "COM", COM)
    fat12_add(img, "AUTOEXEC", "BAT", b"SDATEMEM\r\n")
    open(dsk, "wb").write(img)
    out = probe_tmp.tmp(f"sdatemem_{tag}.log")
    tcl = (f"set pl -1\nset pf [open {{{out}}} w]\nset npc 0\n"
           "proc pp {} { global pl pf; set v [debug read memory 0xC000]; "
           "if {$v != $pl} { set l {}; for {set i 0xF330} {$i <= 0xF345} {incr i} "
           "{ lappend l [format %02X [debug read memory $i]] }; "
           "puts $pf \"P $v [machine_info time] $l\"; flush $pf; set pl $v; "
           + ("if {$v == 1} { set ::cid [debug set_condition "
              "{[debug read memory 0xC000] == 3 && [reg PC] >= 0x4000 && [reg PC] < 0x8000} "
              "{ global pf npc; puts $pf \"PC [format %04X [reg PC]]\"; flush $pf; incr npc; "
              "if {$npc >= 6} { debug remove_condition $::cid } }] }; "
              if tag == "OURS" else "")
           + "}; after time 0.02 pp }\nafter time 1 pp\n")
    W.run_once(machine, dsk, 14, 60, 300, cmd="SDATEMEM", extra_tcl=tcl)
    print(f"== {tag}")
    for ln in open(out):
        print("  " + ln.rstrip())
