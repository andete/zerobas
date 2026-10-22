#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-TPAP1 step 1: WHEN does MSX-DOS call the disk work area's segment hooks --
$F368 ("disk ROM into page 1") and $F36B ("RAM into page 1") -- and what is page 1
before and after each call? On the CF-3300 and on zerobas.

Black box: breakpoints on the two WORK-AREA RAM cells (not ROM), registers, the
caller's return address (an address, never its bytes), the primary slot register
and slot 3's subslots at entry and at the return. Our own .COM drives it: the
D-P1DOS disk (probes/disk/p1dta.asm, run from AUTOEXEC.BAT) -- OPEN, SETDTA, RDBLK,
SEQRD, SFIRST, then back to DOS.

    python3 -u scratchpad/wahook_probe.py [--machines ref,zb] [--end 40] [--max 80]
"""
import argparse, os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
from disk_probe_bdos import fat12_add               # noqa: E402
import disk_probe_wrblk_roundtrip as RT             # noqa: E402
import omsx_preflight                               # noqa: E402

MACH = {"ref": "National_CF-3300", "zb": "C-BIOS_MSX1_EU_REPACK_DISK"}


def tcl(out, end, cap):
    st = ("format \"A8=%02X SUB=%02X\" [debug read ioports 0xA8] "
          "[expr {255 - [debug read memory 0xFFFF]}]")
    return f'''set throttle off
proc __w {{a}} {{ expr {{[debug read memory [expr {{$a & 0xFFFF}}]] + 256*[debug read memory [expr {{($a+1) & 0xFFFF}}]]}} }}
proc __put {{s}} {{ set f [open {{{out}}} a]; puts $f $s; close $f }}
set ::n 0
array set ::rb {{}}
proc __ret {{r t}} {{
  __put [format "%8.3f   ret %s  %s" [machine_info time] $t [{st}]]
  if {{[info exists ::rb($r)]}} {{ debug remove_bp $::rb($r); unset ::rb($r) }}
}}
proc __h {{t}} {{
  if {{[incr ::n] > {cap}}} return
  set r [__w [reg sp]]
  __put [format "%8.3f %s from %04X  %s" [machine_info time] $t $r [{st}]]
  if {{![info exists ::rb($r)]}} {{ set ::rb($r) [debug set_bp $r {{}} [list __ret $r $t]] }}
}}
debug set_bp 0xF368 {{}} {{__h F368_ROM}}
debug set_bp 0xF36B {{}} {{__h F36B_RAM}}
after time {end} {{ exit }}
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--machines", default="ref,zb")
    ap.add_argument("--end", type=float, default=40)
    ap.add_argument("--max", type=int, default=80)
    a = ap.parse_args()
    import probe_tmp
    com = probe_tmp.tmp("p1dta.com")
    subprocess.run(["pasmo", "--bin", os.path.join(REPO, "probes", "disk", "p1dta.asm"), com],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    data = bytes((i * 37 + 11) & 0xFF for i in range(512))
    for m in a.machines.split(","):
        dsk = probe_tmp.tmp(f"wahook_{m}.dsk")
        shutil.copyfile(RT.DEFAULT_DOS, dsk)
        img = bytearray(open(dsk, "rb").read())
        fat12_add(img, "P1DTA", "COM", open(com, "rb").read())
        fat12_add(img, "P1DATA", "BIN", data)
        fat12_add(img, "P1SMALL", "BIN", data[:300])
        fat12_add(img, "AUTOEXEC", "BAT", b"P1DTA\r\n")
        open(dsk, "wb").write(img)
        out = probe_tmp.tmp(f"wahook_{m}.txt")
        s = probe_tmp.tmp(f"wahook_{m}.tcl")
        open(s, "w").write(tcl(out, a.end, a.max))
        subprocess.run(omsx_preflight.guarded([RT.OMSX, "-machine", MACH[m], "-diska", dsk,
                        "-command", "set renderer none; set sound_driver null", "-script", s]),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
        print(f"### {m} ({MACH[m]})")
        print(open(out).read().rstrip() if os.path.exists(out) else "<NO OUTPUT>")


if __name__ == "__main__":
    main()
