#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TPAP1: what an MSX-DOS program sees in page 1, and the page-0 inter-slot
entries ($000C RDSLT, $0014 WRSLT, $001C CALSLT, $0024 ENASLT, $0030 CALLF) called
from the TPA -- on the CF-3300 and on zerobas.

Our own program (probes/disk/p1vec.asm) runs from AUTOEXEC.BAT. Each step writes
its number to $C000 before it runs (8 = all done), its answer to $C001..; read
back at T40 from the `Main RAM` debuggable and compared byte for byte. Before
D-TPAP1 zerobas ran a DOS program with the disk ROM in page 1 (a plain store to
$4300 was lost) and died in CALLF (step 5); with RAM in page 1, the old page-1
entries died in RDSLT (step 2, measured on our disk ROM in the CF-3300).
Black box: our own program, our own bytes; nothing of the reference is read.
"""
import os, shutil, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
from disk_probe_bdos import fat12_add               # noqa: E402
import disk_probe_wrblk_roundtrip as RT             # noqa: E402
import disk_probe_wrblk_alt as W                    # noqa: E402
import probe_tmp                                    # noqa: E402
HERE = os.path.dirname(os.path.abspath(__file__))
NAMES = ["step", "store", "RDSLT", "WRSLT", "CALSLT", "CALLF", "ENASLT", "afterBDOS",
         "subslots", "A8"]

com = probe_tmp.tmp("p1vec.com")
subprocess.run(["pasmo", "--bin", os.path.join(HERE, "p1vec.asm"), com], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
got = {}
for tag, machine in (("STOCK", RT.REF_MACHINE), ("OURS", RT.OUR_MACHINE)):
    dsk = probe_tmp.tmp(f"p1vec_{tag}.dsk")
    shutil.copyfile(RT.DEFAULT_DOS, dsk)
    img = bytearray(open(dsk, "rb").read())
    fat12_add(img, "P1VEC", "COM", open(com, "rb").read())
    fat12_add(img, "AUTOEXEC", "BAT", b"P1VEC\r\n")
    open(dsk, "wb").write(img)
    dump = probe_tmp.tmp(f"p1vec_{tag}.mem")
    if os.path.exists(dump):
        os.remove(dump)
    tcl = (f"after time 40 {{ set f [open {{{dump}}} w]; "
           "binary scan [debug read_block {Main RAM} 0xC000 10] H* b; "
           "puts $f $b; close $f }\n")
    W.run_once(machine, dsk, 14, 42, 300, cmd="P1VEC", extra_tcl=tcl, type_cmd=False)
    got[tag] = bytes.fromhex(open(dump).read().split()[0]) if os.path.exists(dump) else b""
    print(f"{tag}: " + ("<NO OUTPUT>" if not got[tag] else
          "  ".join(f"{n}={v:02X}" for n, v in zip(NAMES, got[tag]))))
S, O = got["STOCK"], got["OURS"]
ok = len(S) == len(O) == 10 and S[0] == 8 and O == S
print("PASS: a DOS program runs with RAM in page 1, and every page-0 inter-slot entry "
      "answers from the TPA as on the CF-3300" if ok else
      "FAIL: a step differs (see above; step = the last one STARTED)")
sys.exit(0 if ok else 1)
