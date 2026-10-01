#!/usr/bin/env python3
"""D-DOSDATE: SDATE's return value and stored day count ($F33B, work-area RAM)
for valid and invalid dates, on both machines. Reads only RAM our program wrote."""
import os, shutil, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
from disk_probe_bdos import fat12_add               # noqa: E402
import disk_probe_wrblk_roundtrip as RT             # noqa: E402
import disk_probe_wrblk_alt as W                    # noqa: E402
import probe_tmp                                    # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
com = probe_tmp.tmp("sdatebad.com")
subprocess.run(["pasmo", "--bin", os.path.join(HERE, "sdatebad.asm"), com], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
COM = open(com, "rb").read()
CASES = ["2100-01-01", "1979-12-31", "1999-13-01", "1999-00-01", "1999-01-00",
         "1999-02-29", "1999-04-31", "2000-02-29", "1980-01-01", "2099-12-31", "1999-12-31"]

rows = {}
for tag, machine in (("STOCK", RT.REF_MACHINE), ("OURS", RT.OUR_MACHINE)):
    dsk = probe_tmp.tmp(f"sdatebad_{tag}.dsk")
    shutil.copyfile(RT.DEFAULT_DOS, dsk)
    img = bytearray(open(dsk, "rb").read())
    fat12_add(img, "SDATEBAD", "COM", COM)
    fat12_add(img, "AUTOEXEC", "BAT", b"SDATEBAD\r\n")
    open(dsk, "wb").write(img)
    out = probe_tmp.tmp(f"sdatebad_{tag}.ram")
    cells = " ".join(str(a) for a in [0xC000] + list(range(0xC010, 0xC010 + 3 * len(CASES))))
    tcl = (f"after time 55 {{ set f [open {{{out}}} w]; foreach a {{{cells}}} "
           f"{{ puts $f [debug read memory $a] }}; close $f }}\n")
    W.run_once(machine, dsk, 14, 60, 300, cmd="SDATEBAD", extra_tcl=tcl)
    r = [int(x) for x in open(out).read().split()]
    rows[tag] = [(r[1 + 3 * i], r[2 + 3 * i] | r[3 + 3 * i] << 8) for i in range(len(CASES))]
    print(f"{tag}: PHASE={r[0]} (2 = finished)")
print(f"\n{'date':12} {'STOCK A':>8} {'days':>6}   {'OURS A':>7} {'days':>6}")
for i, c in enumerate(CASES):
    (sa, sd), (oa, od) = rows["STOCK"][i], rows["OURS"][i]
    print(f"{c:12} {sa:8X} {sd:6d}   {oa:7X} {od:6d}" + ("" if (sa, sd) == (oa, od) else "   <- differs"))
