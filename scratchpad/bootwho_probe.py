#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""Why does test.dsk with MSXDOS.SYS and COMMAND.COM deleted host-side still boot MSX-DOS? (seen in D-COPYSLOW's Q5
runs, 2026-11-28; Joost: "it may be that msxdos.sys and command.com sit at fixed locations?"). BLACK BOX ONLY: the
boot code on the disk is reference code and is not read; each variant changes the image's directory / FAT / data
from the host and the machine's screen after a fixed boot time is all that is looked at.
  control  the image as it is
  del      both entries deleted (first byte E5, chains freed)
  delzero  as del, and every freed sector zeroed -- if it still boots, the code does not come from those sectors
  renmsx   MSXDOS.SYS's name changed to XSXDOS.SYS, nothing else -- if it still boots, the loader does not match the
           full name
  rencom   COMMAND.COM's name changed to XOMMAND.COM, nothing else
    python3 -u scratchpad/bootwho_probe.py [MACHINE ...]
"""
import os
import struct
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_preflight  # noqa: E402

machines = sys.argv[1:] or ["National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"]
SRC = os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")


def geom(img):
    bps, spc, res, nf, nroot, _t, _m, spf = struct.unpack_from("<HBHBHHBH", img, 11)
    root = (res + nf * spf) * bps
    return bps, spc, res, nf, nroot, spf, root, root + nroot * 32


def entry(img, name):
    bps, spc, res, nf, nroot, spf, root, data = geom(img)
    for i in range(nroot):
        o = root + 32 * i
        if img[o:o + 11].decode("latin1") == name:
            return o
    raise SystemExit(f"{name!r} not on the image")


def delete(img, name, zero):
    bps, spc, res, nf, nroot, spf, root, data = geom(img)
    o = entry(img, name)
    c = struct.unpack_from("<H", img, o + 26)[0]
    img[o] = 0xE5
    while 2 <= c < 0xFF8:
        nxt = None
        for k in range(nf):
            fo = (res + k * spf) * bps + c * 3 // 2
            v = struct.unpack_from("<H", img, fo)[0]
            if nxt is None:
                nxt = v >> 4 if c & 1 else v & 0xFFF
            struct.pack_into("<H", img, fo, v & 0x000F if c & 1 else v & 0xF000)
        if zero:
            d = data + (c - 2) * spc * bps
            img[d:d + spc * bps] = bytes(spc * bps)
        c = nxt


def variant(v):
    img = bytearray(open(SRC, "rb").read())
    if v in ("del", "delzero"):
        delete(img, "MSXDOS  SYS", v == "delzero")
        delete(img, "COMMAND COM", v == "delzero")
    elif v == "renmsx":
        img[entry(img, "MSXDOS  SYS")] = ord("X")
    elif v == "rencom":
        img[entry(img, "COMMAND COM")] = ord("X")
    return img


TCL = """set throttle off
proc rd {a} { debug read memory $a }
proc rd16 {a} { expr {[rd $a] + 256*[rd [expr {$a+1}]]} }
after time 16 {
  set m [rd 0xFCAF]
  if {$m == 0} { set base [rd16 0xF3B3]; set w 40 } else { set base [rd16 0xF3BD]; set w 32 }
  binary scan [debug read_block VRAM $base [expr {$w*24}]] H* h
  set f [open {OUT} w]; puts $f "$w $h"; close $f; exit }
"""
for m in machines:
    print(f"== {m}")
    for v in ("control", "del", "delzero", "renmsx", "rencom"):
        td = tempfile.mkdtemp()
        dsk, out, sf = os.path.join(td, "d.dsk"), os.path.join(td, "o.txt"), os.path.join(td, "s.tcl")
        open(dsk, "wb").write(variant(v))
        open(sf, "w").write(TCL.replace("{OUT}", "{" + out + "}"))
        subprocess.run(omsx_preflight.guarded(["openmsx", "-machine", m, "-diska", dsk, "-command",
                       "set renderer none; set sound_driver null", "-script", sf]),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
        if not os.path.exists(out):
            print(f"   {v:8s} NO SCREEN -- instrument failed")
            continue
        w, h = open(out).read().split()
        w, b = int(w), bytes.fromhex(h)
        rows = [b[k * w:(k + 1) * w].decode("latin1").rstrip() for k in range(24)]
        print(f"   {v:8s} " + " / ".join(r.strip() for r in rows if r.strip())[:150])
