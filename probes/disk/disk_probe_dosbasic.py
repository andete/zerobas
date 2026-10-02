#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DOSBASIC + D-DOSDATEBASIC (gate: dosbasic-acceptance): MSX-DOS's BASIC
command reaches disk BASIC, and a date set in DOS reaches BASIC's file stamps --
as on the CF-3300.

SDATE 1999-12-31 in a COM, then `BASIC`, then `10 REM` + SAVE"DDB.BAS", on both
machines; the disk image's DDB.BAS entry (time, date, size) must be identical
and present. Before the fix ours never left DOS: zerobas had put its own banner
at $4022, the standard disk-ROM BASENT entry the BASIC command calls
(scratchpad/sdatebasic_after.out is that red). Exit 0 on a match; 1 otherwise.
"""
import os, shutil, struct, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
from disk_probe_bdos import fat12_add               # noqa: E402
import disk_probe_wrblk_roundtrip as RT             # noqa: E402
import disk_probe_wrblk_alt as W                    # noqa: E402
import probe_tmp                                    # noqa: E402
HERE = os.path.dirname(os.path.abspath(__file__))  # probes/disk/, beside sdatex.asm
com = probe_tmp.tmp("sdatex.com")
subprocess.run(["pasmo", "--bin", os.path.join(HERE, "sdatex.asm"), com], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
COM = open(com, "rb").read()
got = {}
for tag, machine in (("STOCK", RT.REF_MACHINE), ("OURS", RT.OUR_MACHINE)):
    dsk = probe_tmp.tmp(f"sdatebasic_{tag}.dsk")
    shutil.copyfile(RT.DEFAULT_DOS, dsk)
    img = bytearray(open(dsk, "rb").read())
    fat12_add(img, "SDATEX", "COM", COM)
    fat12_add(img, "AUTOEXEC", "BAT", b"SDATEX\r\nBASIC\r\n")
    open(dsk, "wb").write(img)
    tcl = ("" if tag == "STOCK" else 'after time 24 { type "BASIC\\r" }\n') + \
          'after time 40 { type "NEW\\r10 REM\\rSAVE\\"DDB.BAS\\"\\r" }\n'
    scr = probe_tmp.tmp(f"sdatebasic_{tag}.vram")
    tcl += (f"proc dumpv {{t}} {{ set f [open {{{scr}}} a]; set l {{}}; "
            "set nb [expr {([vdpreg 2] & 15) * 1024}]; set w [expr {([vdpreg 1] & 16) ? 40 : 32}]; "
            "lappend l $w; for {set i 0} {$i < 960} {incr i} { lappend l [debug read VRAM [expr {$nb + $i}]] }; "
            "puts $f \"$t $l\"; close $f }\n"
            "after time 38 { dumpv 38 }\nafter time 58 { dumpv 58 }\n")
    W.run_once(machine, dsk, 14, 60, 300, cmd="SDATEX", extra_tcl=tcl)
    if os.path.exists(scr):
        for ln in open(scr):
            t, w, *v = ln.split()
            w = int(w)
            txt = "".join(chr(int(x)) if 32 <= int(x) < 127 else " " for x in v)
            rows = [txt[i:i + w].rstrip() for i in range(0, 24 * w, w)]
            print(f"--- {tag} screen at {t} s:")
            for r in rows:
                if r.strip():
                    print("   |" + r)
    f = RT.Fat12(dsk)
    b = f.img
    bps = struct.unpack_from("<H", b, 11)[0]
    root = (struct.unpack_from("<H", b, 14)[0] + b[16] * struct.unpack_from("<H", b, 22)[0]) * bps
    d = f.dirent("DDB", "BAS")
    if d is None:
        print(f"{tag}: DDB.BAS NOT WRITTEN")
        got[tag] = None
        continue
    t, dt = struct.unpack_from("<HH", b, root + d["idx"] * 32 + 22)
    got[tag] = (t, dt, d["size"])
    print(f"{tag}: DDB.BAS time {t:04X} date {dt:04X} = "
          f"{1980 + (dt >> 9)}-{(dt >> 5) & 15:02d}-{dt & 31:02d}  size {d['size']}")
if got.get("STOCK") is None:
    print("\nINSTRUMENT FAULT: the CF-3300 wrote no DDB.BAS -- no reference")
    sys.exit(2)
ok = got.get("OURS") == got["STOCK"]
print(f"\n{'PASS' if ok else 'FAIL'}: A>BASIC, then SAVE, "
      + ("matches the CF-3300" if ok else f"differs (ours {got.get('OURS')}, CF-3300 {got['STOCK']})"))
sys.exit(0 if ok else 1)
