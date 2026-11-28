#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-COPYSLOW Q4 (Joost 2026-11-28 "as much info as possible before ... any code"): what does the reference leave on
disk when the disk is SWAPPED in the middle of a COPY -- the risk of keeping the FAT in RAM and writing it back at the
end? The image is swapped (openMSX `diska`) for a copy of the original with DUMP.BIN deleted (so it
differs) right after the copy's Nth data-sector
write command; then DIR. Only FDC registers are watched (no RAM byte, no PC). Both images are then checked from the
host: the listing, FAT1 == FAT2, clusters marked used that no file reaches (lost), and chains that end early or loop.
    python3 -u scratchpad/swapmid_probe.py [N] [MACHINE ...]
"""
import os
import struct
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "disk"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import disk_probe_dossession as D  # noqa: E402
import omsx_preflight  # noqa: E402

n_at = int(sys.argv[1]) if len(sys.argv) > 1 else 30
machines = sys.argv[2:] or ["National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"]
SRC = os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")
D.SESSION = [("boot", None, 14), ("date", "", 5), ("mode", "MODE 40", 4),
             ("copy", "COPY MSXBUNSE.ROM BIG.ROM", 1), ("dir", "DIR BIG*.*", 2)]


def integrity(img):
    bps, spc, res, nf, nroot, tot, _m, spf = struct.unpack_from("<HBHBHHBH", img, 11)
    f1 = img[res * bps:(res + spf) * bps]
    f2 = img[(res + spf) * bps:(res + 2 * spf) * bps]
    ncl = (tot - res - nf * spf - nroot * 32 // bps) // spc + 2

    def ent(c):
        v = struct.unpack_from("<H", f1, c * 3 // 2)[0]
        return v >> 4 if c & 1 else v & 0xFFF
    root = (res + nf * spf) * bps
    reach, bad = set(), []
    for i in range(nroot):
        e = img[root + 32 * i: root + 32 * i + 32]
        if e[0] in (0, 0xE5) or e[11] & 0x08:
            continue
        name = e[0:11].decode("latin1")
        c, size = struct.unpack_from("<H", e, 26)[0], struct.unpack_from("<I", e, 28)[0]
        need = -(-size // (spc * bps)) if not e[11] & 0x10 else None
        k = 0
        while 2 <= c < 0xFF8 and c < ncl and c not in reach:
            reach.add(c)
            k += 1
            c = ent(c)
        if need is not None and k != need:
            bad.append(f"{name.strip()} chain {k} clusters, size wants {need}")
    used = {c for c in range(2, ncl) if ent(c) != 0}
    lost = sorted(used - reach)
    return f"FAT1{'==' if f1 == f2 else '!='}FAT2, lost clusters {len(lost)}, bad chains {bad or 'none'}"


def host_delete(path, fname):
    """Delete fname from the image the way DOS does (entry E5, clusters freed in every FAT copy) -- so the swapped-in
    disk DIFFERS from the first one and a stale FAT / directory sector written onto it is visible."""
    img = bytearray(open(path, "rb").read())
    bps, spc, res, nf, nroot, _t, _m, spf = struct.unpack_from("<HBHBHHBH", img, 11)
    root = (res + nf * spf) * bps
    for i in range(nroot):
        o = root + 32 * i
        if img[o:o + 11].decode("latin1") == fname:
            c = struct.unpack_from("<H", img, o + 26)[0]
            img[o] = 0xE5
            while 2 <= c < 0xFF8:
                nxt = None
                for k in range(nf):
                    fo = (res + k * spf) * bps + c * 3 // 2
                    v = struct.unpack_from("<H", img, fo)[0]
                    if nxt is None:
                        nxt = v >> 4 if c & 1 else v & 0xFFF
                    v = v & 0x000F if c & 1 else v & 0xF000
                    struct.pack_into("<H", img, fo, v)
                c = nxt
            open(path, "wb").write(img)
            return
    raise SystemExit(f"{fname!r} not on the image")


for m in machines:
    td = tempfile.mkdtemp()
    dsk, dsk2 = os.path.join(td, "d.dsk"), os.path.join(td, "d2.dsk")
    subprocess.run(["cp", SRC, dsk], check=True)
    subprocess.run(["cp", SRC, dsk2], check=True)
    host_delete(dsk2, "DUMP    BIN")
    out = os.path.join(td, "o.txt")
    fl = os.path.join(td, "cmd.txt")
    tcl = D.tcl(out)
    cmd = ("set ::counting 0; set ::wn 0\n"
           "proc __cmd {base} { if {!$::counting} return; "
           "set c [expr {$::wp_last_value >> 4}]; set t [peek [expr {$base + 1}]]; set s [peek [expr {$base + 2}]]; "
           "puts $::fl \"C $c $t $s\"; "
           f"if {{$c == 10 && $t != 0}} {{ incr ::wn; if {{$::wn == {n_at}}} "
           f"{{ after time 0.02 {{diska {{{dsk2}}}; puts $::fl SWAP}} }} }} }}\n"
           "debug set_watchpoint write_mem {0x7F80 0x7FBF} {$::counting} {if {($::wp_last_address & 7) == 0} {__cmd 0x7FB8}}\n"
           "debug set_watchpoint write_mem {0xBF80 0xBFBF} {$::counting} {if {($::wp_last_address & 7) == 0} {__cmd 0xBFB8}}\n")
    tcl = tcl.replace("set throttle off", f"set throttle off\nset ::fl [open {{{fl}}} w]\n" + cmd, 1)
    a = "  close $f }"
    assert tcl.count(a) == 1
    tcl = tcl.replace(a, "  if {$tag eq \"mode\"} {set ::counting 1}\n"
                         "  if {$tag eq \"dir\"} {set ::counting 0; flush $::fl}\n" + a)
    tcl = tcl.replace("$::tries > 240", "$::tries > 12000")
    sf = os.path.join(td, "s.tcl")
    open(sf, "w").write(tcl)
    subprocess.run(omsx_preflight.guarded(["openmsx", "-machine", m, "-diska", dsk, "-command",
                   "set renderer none; set sound_driver null", "-script", sf]),
                   stdout=open(os.path.join(td, "err.txt"), "w"), stderr=subprocess.STDOUT, timeout=2400)
    lines = open(fl).read().splitlines()
    print(f"== {m}: swap after data write {n_at}   (log {td})")
    if "SWAP" not in lines:
        print("   THE SWAP NEVER HAPPENED -- instrument failed, not a finding")
    else:
        i = lines.index("SWAP")
        after = lines[i + 1:]
        w = sum(1 for ln in after if ln.split()[1] == "10" and ln.split()[2] != "0")
        fw = sum(1 for ln in after if ln.split()[1] == "10" and ln.split()[2] == "0")
        r0 = sum(1 for ln in after if ln.split()[1] == "8" and ln.split()[2] == "0")
        print(f"   after the swap: {w} data writes, {fw} track-0 writes (FAT / dir), {r0} track-0 reads")
    for lbl, f in (("first image", dsk), ("swapped-in image", dsk2)):
        img = bytearray(open(f, "rb").read())
        big = [e[:60] for e in D.disk_listing(img) if e.startswith(("BIG", "DUMP.BIN"))]
        print(f"   {lbl}: {' | '.join(big) or 'no BIG*'};  {integrity(img)}")
    snaps = {ln.split()[0]: ln for ln in open(out).read().splitlines()}
    for step in ("copy", "dir"):
        if step in snaps:
            p = snaps[step].split()
            wd = int(p[1][2:])
            b = bytes.fromhex(p[3])
            rows = [b[k * wd:(k + 1) * wd].decode("latin1").rstrip() for k in range(24)]
            print(f"   screen at {step}: " + " / ".join(r for r in rows if r.strip())[-220:])
