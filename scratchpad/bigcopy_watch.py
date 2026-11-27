#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""A big COPY at MSX-DOS's A> (COPY MSXBUDIC.ROM BIG.ROM, 131072 B) on MACHINE, watched for SECONDS: the screen's last
lines, PC and the primary-slot register at each sample, then BIG.ROM in the image. RAM / registers / slots only.
    python3 -u scratchpad/bigcopy_watch.py MACHINE [SECONDS] [SRC]
"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "disk"))
import disk_probe_dossession as D  # noqa: E402

machine = sys.argv[1]
secs = int(sys.argv[2]) if len(sys.argv) > 2 else 120
src = sys.argv[3] if len(sys.argv) > 3 else "MSXBUDIC.ROM"
td = tempfile.mkdtemp()
dsk = os.path.join(td, "d.dsk")
subprocess.run(["cp", os.path.expanduser("~/Documents/msx/msx/disks/test.dsk"), dsk], check=True)
log = os.path.join(td, "o.txt")
times = [t for t in (20, 30, 45, 60, 90, 120, 240, 400) if t <= secs]
tcl = f"""set throttle off
set f [open {{{log}}} w]
proc last {{}} {{ set s ""; catch {{set s [get_screen]}}; set l [lsearch -all -inline -not [split $s "\\n"] {{}}]
  return "[string trim [lindex $l end-1]] | [string trim [lindex $l end]]" }}
after time 12 {{ type "87-11-23\\r" }}
after time 15 {{ type "COPY {src} BIG.ROM\\r" }}
""" + "".join(f'after time {t} {{ puts $f "t={t} [last] PC=[format %04X [reg PC]] A8=[format %02X '
              f'[debug read ioports 0xA8]]"; flush $f }}\n' for t in times) + f"after time {secs + 1} exit\n"
sf = os.path.join(td, "s.tcl")
open(sf, "w").write(tcl)
subprocess.run(["openmsx", "-machine", machine, "-diska", dsk, "-command", "set renderer none; set sound_driver null",
                "-script", sf], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=secs * 3 + 120)
print(f"== {machine} COPY {src} BIG.ROM")
print(open(log).read().rstrip())
for e in D.disk_listing(bytearray(open(dsk, "rb").read())):
    if e.startswith(("BIG.", src)):
        print("  " + e)


def body(img, want):
    import struct
    bps, spc, resv, nfat = struct.unpack_from("<H", img, 11)[0], img[13], struct.unpack_from("<H", img, 14)[0], img[16]
    nroot, fatsz = struct.unpack_from("<H", img, 17)[0], struct.unpack_from("<H", img, 22)[0]
    root = (resv + nfat * fatsz) * bps
    data = root + nroot * 32
    fat = img[resv * bps:(resv + fatsz) * bps]
    for i in range(nroot):
        e = img[root + i * 32:root + i * 32 + 32]
        if e[0] in (0, 0xE5):
            continue
        if (e[0:8].decode("latin-1").rstrip() + "." + e[8:11].decode("latin-1").rstrip()) != want:
            continue
        size, c, b = struct.unpack_from("<I", e, 28)[0], struct.unpack_from("<H", e, 26)[0], b""
        while 2 <= c < 0xFF0 and len(b) < size:
            b += img[data + (c - 2) * spc * bps:data + (c - 1) * spc * bps]
            v = struct.unpack_from("<H", fat, c * 3 // 2)[0]
            c = (v >> 4) if c & 1 else (v & 0xFFF)
        return b[:size]


img = bytearray(open(dsk, "rb").read())
a, b = body(img, src), body(img, "BIG.ROM")
if b:
    open(os.environ.get("BIGCOPY_SAVE", os.path.join(td, "BIG.ROM")), "wb").write(b)
if a and b:
    bad = [i for i in range(min(len(a), len(b))) if a[i] != b[i]]
    print(f"  bytes differing: {len(bad)} of {min(len(a), len(b))}" + (
        f"; first at {bad[0]:#06x}, last at {bad[-1]:#06x}; differing 512-B sectors: "
        f"{sorted({i // 512 for i in bad})[:40]}" if bad else ""))
