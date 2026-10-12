#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BASICROM, measure first: a BASIC-program cartridge (an `AB` header whose
TEXT field points at a tokenised program in page 2) on the VG-8020 and on
zerobas. A ONE-OFF probe: the cartridge is a third-party ROM, run but never
decoded and never part of a gate (Joost, 2026-10-12) -- its path is an argument,
nothing of it is kept here.

    python3 -u scratchpad/basicrom_probe.py <rom>

Boots each machine with the cartridge in slot 1 (`-carta`), waits, and reads
published work-area cells -- TXTTAB $F676, VARTAB $F6C2, ARYTAB $F6C4, STREND
$F6C6, STKTOP $F674, MEMSIZ $F672, CURLIN $F41C (the running line; $FFFF in
direct mode), SCRMOD $FCAF -- and the primary slot register (port $A8). No ROM
byte and no RAM-resident code is read.

Prediction (first run, 3D Golf Simulation): the VG-8020 has TXTTAB = the
header's TEXT ($8010), page 2 mapped to slot 1, and a CURLIN of a running
line; zerobas ignores the TEXT field: TXTTAB $8001, CURLIN $FFFF, page 2 RAM.
"""
import os, signal, subprocess, sys, tempfile, time
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_preflight                               # noqa: E402

OMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")
MACHINES = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")
CELLS = (("TXTTAB", 0xF676, 2), ("VARTAB", 0xF6C2, 2), ("ARYTAB", 0xF6C4, 2),
         ("STREND", 0xF6C6, 2), ("STKTOP", 0xF674, 2), ("MEMSIZ", 0xF672, 2),
         ("CURLIN", 0xF41C, 2), ("SCRMOD", 0xFCAF, 1))


def run(machine, rom, at):
    fd, out = tempfile.mkstemp(suffix=".txt", prefix="basicrom_")
    os.close(fd)
    os.unlink(out)
    lines = [
        "set throttle off",
        "proc __w {a n} { binary scan [debug read_block memory $a $n] H* h; return $h }",
        f"after time {at} {{",
        f"  set f [open {{{out}}} w]",
        *[f'  puts $f "{n}=[__w {a} {k}]"' for n, a, k in CELLS],
        '  puts $f "A8=[format %02x [debug read ioports 0xA8]]"',
        "  close $f",
        "  exit",
        "}",
        f"after time {at + 20} {{ exit }}",
    ]
    fd, tcl = tempfile.mkstemp(suffix=".tcl", prefix="basicrom_")
    os.write(fd, ("\n".join(lines) + "\n").encode())
    os.close(fd)
    cmd = [OMSX, "-machine", machine, "-carta", rom,
           "-command", "set renderer none; set sound_driver null", "-script", tcl]
    try:
        p = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        t = time.time() + 120
        while p.poll() is None and time.time() < t:
            time.sleep(0.2)
        if p.poll() is None:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
    finally:
        os.unlink(tcl)
    if not os.path.exists(out):
        return None
    res = dict(l.strip().split("=", 1) for l in open(out) if "=" in l)
    os.unlink(out)
    return res


def le(h):
    return int(h[2:4] + h[0:2], 16) if len(h) == 4 else int(h, 16)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    rom = os.path.abspath(sys.argv[1])
    for at in (6.0, 15.0):
        for m in MACHINES:
            r = run(m, rom, at)
            if r is None:
                print(f"t={at:4.1f}s {m:30s} NO CAPTURE")
                continue
            cells = " ".join(f"{n} ${le(r[n]):04X}" if k == 2 else f"{n} {le(r[n])}"
                             for n, _, k in CELLS)
            print(f"t={at:4.1f}s {m:30s} {cells} A8 ${r['A8'].upper()}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
