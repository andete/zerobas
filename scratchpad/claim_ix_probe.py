#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-CLAIM473: does the drive-A DPB move with a foreign claim? Reads the published DPB-pointer list's
first word ($F355, drive A) at the boot code's entries ($C01E, page 3 = slot 3) and at 20 s (A>), with HIMEM,
DRVTBL and the slot-3-1 SLTWRK entry there, with probes/disk/claimonce.asm claiming N. Registers / RAM / slots only --
no PC, no ROM byte.
    python3 -u scratchpad/claim_ix_probe.py [N ...]       (default 0 300 473)
"""
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_preflight  # noqa: E402

NS = [int(x) for x in sys.argv[1:]] or [0, 300, 473]
MACHINES = ["National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"]


def cart(td, n):
    out = os.path.join(td, "c.bin")
    subprocess.run(["pasmo", "--bin", os.path.join(REPO, "probes", "disk", "claimonce.asm"), out], check=True,
                   capture_output=True)
    b = bytearray(open(out, "rb").read())
    b[0x10:0x12] = n.to_bytes(2, "little")
    rom = os.path.join(td, f"c{n}.rom")
    open(rom, "wb").write(bytes(b) + bytes(16384 - len(b)))
    return rom


for n in NS:
    for m in MACHINES:
        td = tempfile.mkdtemp()
        dsk = os.path.join(td, "d.dsk")
        subprocess.run(["cp", os.path.expanduser("~/Documents/msx/msx/disks/test.dsk"), dsk], check=True)
        log = os.path.join(td, "o.txt")
        tcl = f"""set throttle off
set f [open {{{log}}} w]
set ::c 0
debug set_bp 0xC01E {{[expr {{([debug read ioports 0xA8] >> 6) == 3}}]}} {{
  if {{[incr ::c] <= 2}} {{ puts $::f "C01E#$::c DPBLIST=[format %04X [peek16 0xF355]] HIMEM=[format %04X [peek16 0xFC4A]] DRVTBL=[format %02X%02X%02X%02X [peek 0xFB21] [peek 0xFB22] [peek 0xFB23] [peek 0xFB24]] SW31=[format %04X [peek16 0xFD73]]"; flush $::f }} }}
after time 20 {{ puts $::f "A> DPBLIST=[format %04X [peek16 0xF355]] HIMEM=[format %04X [peek16 0xFC4A]]"; flush $::f }}
after time 25 exit
"""
        sf = os.path.join(td, "s.tcl")
        open(sf, "w").write(tcl)
        cmd = ["openmsx", "-machine", m, "-diska", dsk]
        if n:
            cmd += ["-cart", cart(td, n)]
        cmd += ["-command", "set renderer none; set sound_driver null", "-script", sf]
        subprocess.run(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
        print(f"N={n:<3d} {m:28s} " + (open(log).read().strip().replace("\n", " | ") if os.path.exists(log) else "-"))
