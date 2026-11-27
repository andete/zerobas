#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-CLAIM473 step 1: where does a disk machine write after a foreign claim of N bytes, and does it install?

probes/disk/claimfill.asm claims N and fills $A5 over its claim [$F380-N, $F380) and over [$D000, $EF80). At three
RAM moments -- the H.RUNC hook ($FECB, first entry), the boot code's entry ($C01E, page 3 = slot 3) and 25 s (A>) --
the probe dumps those regions; every byte no longer $A5 was written after the cartridge's INIT. Printed as address
RANGES (RAM), plus HIMEM, DRVTBL ($FB21-$FB22), the disk interface's SLTWRK page-1 entry (slot 3-1: $FD73) and
whether the boot code was reached. Clean room: RAM / slot state only -- no PC, no ROM byte.
    python3 -u scratchpad/claim473_probe.py [N ...]      (default 0 439 456 473 474 480 491)
"""
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_preflight  # noqa: E402

MACHINES = os.environ.get("CLAIM_MACHINES", "National_CF-3300,C-BIOS_MSX1_EU_REPACK_DISK").split(",")
NS = [int(x) for x in sys.argv[1:]] or [0, 439, 456, 473, 474, 480, 491]
DOS = os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")
PAT = 0xA5


def cart(td, n):
    out = os.path.join(td, "cf.bin")
    subprocess.run(["pasmo", "--bin", os.path.join(REPO, "probes", "disk", "claimfill.asm"), out], check=True,
                   capture_output=True)
    b = bytearray(open(out, "rb").read())
    b[0x10:0x12] = n.to_bytes(2, "little")
    rom = os.path.join(td, f"cf_{n}.rom")
    open(rom, "wb").write(bytes(b) + bytes(16384 - len(b)))
    return rom


def ranges(base, data):
    out, start = [], None
    for i, v in enumerate(data + bytes([PAT])):
        if v != PAT and start is None:
            start = i
        elif v == PAT and start is not None:
            out.append((base + start, base + i - 1))
            start = None
    return out


def run(m, n):
    td = tempfile.mkdtemp()
    dsk = os.path.join(td, "d.dsk")
    subprocess.run(["cp", DOS, dsk], check=True)
    log = os.path.join(td, "o.txt")
    lo = 0xF380 - n
    tcl = f"""set throttle off
set f [open {{{log}}} w]
proc dump {{a k}} {{ binary scan [debug read_block memory $a $k] H* h; return $h }}
proc snap {{tag}} {{ global f
  puts $f "SNAP $tag HIMEM=[format %04X [peek16 0xFC4A]] FB21=[format %02X%02X [peek 0xFB21] [peek 0xFB22]] SW31=[format %04X [peek16 0xFD73]] LOW=[dump 0xD000 [expr {{0xEF80-0xD000}}]] CLAIM=[dump {lo} {n}]"
  flush $f }}
set ::h 0; set ::c 0
debug set_bp 0xFECB {{}} {{ if {{[incr ::h] == 1}} {{ snap HRUNC }} }}
debug set_bp 0xC01E {{[expr {{([debug read ioports 0xA8] >> 6) == 3}}]}} {{ if {{[incr ::c] == 1}} {{ snap C01E }} }}
after time 25 {{ snap A; exit }}
"""
    sf = os.path.join(td, "s.tcl")
    open(sf, "w").write(tcl)
    # the cartridge goes in at N = 0 too: it claims nothing and still lays the pattern (the baseline row)
    cmd = ["openmsx", "-machine", m, "-diska", dsk, "-cart", cart(td, n)]
    cmd += ["-command", "set renderer none; set sound_driver null", "-script", sf]
    subprocess.run(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
    snaps = {}
    for ln in (open(log).read().splitlines() if os.path.exists(log) else []):
        p = ln.split()
        if p and p[0] == "SNAP":
            kv = dict(x.split("=", 1) for x in p[2:])
            snaps[p[1]] = kv
    return snaps


def fmt(rs):
    return ", ".join(f"${a:04X}" + (f"-${b:04X}" if b != a else "") for a, b in rs) or "-"


for n in NS:
    for m in MACHINES:
        s = run(m, n)
        print(f"== N={n:<3d} {m}")
        for tag in ("HRUNC", "C01E", "A"):
            if tag not in s:
                print(f"   {tag:5s} (not reached)")
                continue
            kv = s[tag]
            low = ranges(0xD000, bytes.fromhex(kv["LOW"]))
            cl = ranges(0xF380 - n, bytes.fromhex(kv.get("CLAIM", ""))) if n else []
            print(f"   {tag:5s} HIMEM={kv['HIMEM']} DRVTBL={kv['FB21']} SLTWRK3-1p1={kv['SW31']}")
            print(f"         written in the claim [{0xF380 - n:04X},F380): {fmt(cl)}")
            print(f"         written in [D000,EF80): {fmt(low)}")
        sys.stdout.flush()
