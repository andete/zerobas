#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""VPOKE / VPEEK / OUT / INP / VARPTR / BASE probe — validate the zerobas
memory / I-O access primitives.

Boots the zerobas cartridge, types a line into its REPL, and reads the result
back from RAM. Each result-bearing line ends in `bload"cas:",r`, whose loaded
blob `JR $` landmark (LANDMARK) freezes RAM after the line ran — so this MUST
use `--machine Philips_VG_8020` (C-BIOS does not service tape, so the landmark
would never fire there). Modelled on basic_probe_statements.py: POKEs target
0xD000 (clear of the blob at 0xC000.. and its JONG marker at 0xE000).

What each check proves:
  * VPOKE/VPEEK : write a byte to VRAM, read it back, POKE the result to RAM.
  * INP         : a port read completes and the line reaches the landmark
                  (the read value is hardware-dependent, so it is not asserted).
  * VARPTR      : VARPTR(b) returns the address of b's value cell in zerobas's
                  own variable table; PEEKing there recovers b's 16-bit value
                  (LE). NOTE: this is zerobas's table address, not the reference
                  ROM's variable-area address (documented divergence).
  * OUT         : a port write completes and the rest of the line runs.
  * BASE        : descoped — BASE(n) returns 0 and sets ERRMARK ($DD at $E010),
                  but the line continues (the following POKE still runs).

Clean-room: this only observes zerobas's own behaviour; no reference disassembly.
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra

import argparse
import os
import subprocess
import sys
import tempfile


from basic_probe_bload import build_blob, LOAD_ADDR, LANDMARK  # noqa: E402
from cas_encode import build_cas  # noqa: E402

OMSX_RUN = os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib", "omsx_run.py")
MACHINE = "Philips_VG_8020"
T = 0xD000   # POKE target, free RAM
ERRMARK = 0xE010


def run(machine, cart, cas, line, mems, bp=None, secs=None, type_delay=8):
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="vdpio_cap_")
    os.close(out_fd)
    cmd = [sys.executable, OMSX_RUN, "--machine", machine, "--cart", cart]
    if cas:
        cmd += ["--cassette", cas]
    cmd += ["--type", line, "--type-delay", str(type_delay),
            "--type", "\r", "--type-delay", str(type_delay + 4)]
    if bp is not None:
        cmd += ["--bp", hex(bp), "--reg", "PC"]
    else:
        cmd += ["--time", str(secs)]
    for m in mems:
        cmd += ["--mem", m]
    cmd += ["--out", out_path, "--timeout", "120"]
    subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cap = ""
    if os.path.exists(out_path):
        with open(out_path) as f:
            cap = f.read()
        os.unlink(out_path)
    return cap


def memval(cap, addr, length):
    key = f"mem.memory:0x{addr:04X}:{length}="
    for line in cap.splitlines():
        if line.startswith(key):
            return line[len(key):]
    return None


def landmark(cap):
    return f"reg.PC=0x{LANDMARK:04X}" in cap


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=MACHINE)
    ap.add_argument("--cart", required=True, help="zerobas basic.rom")
    args = ap.parse_args()

    cas = build_cas("BLOAD", LOAD_ADDR, LOAD_ADDR, build_blob())
    cas_fd, cas_path = tempfile.mkstemp(suffix=".cas", prefix="vdpio_probe_")
    os.write(cas_fd, cas)
    os.close(cas_fd)

    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL'}  {label}" + (f"  {detail}" if detail else ""))
        if not cond:
            ok = False

    # 1. VPOKE then VPEEK round-trip through VRAM.
    cap = run(args.machine, args.cart, cas_path,
              f'vpoke &h1800,65:a=vpeek(&h1800):poke &h{T:04x},a:bload"cas:",r',
              [f"memory:0x{T:04X}:1"], bp=LANDMARK)
    check("VPOKE &H1800,65 ; VPEEK -> 65", memval(cap, T, 1) == "41",
          f"D000={memval(cap, T, 1)} PC@landmark={'yes' if landmark(cap) else 'no'}")

    # 2. VPOKE/VPEEK with a different value, confirming it is a real read-back.
    cap = run(args.machine, args.cart, cas_path,
              f'vpoke &h1801,200:a=vpeek(&h1801):poke &h{T:04x},a:bload"cas:",r',
              [f"memory:0x{T:04X}:1"], bp=LANDMARK)
    check("VPOKE &H1801,200 ; VPEEK -> 200", memval(cap, T, 1) == "c8",
          f"D000={memval(cap, T, 1)}")

    # 3. INP: a port read completes; value is hardware-dependent, so just assert
    #    the line ran (POKE after INP fired, landmark reached).
    cap = run(args.machine, args.cart, cas_path,
              f'a=inp(&ha2):poke &h{T:04x},77:bload"cas:",r',
              [f"memory:0x{T:04X}:1"], bp=LANDMARK)
    check("INP(&HA2) read completes, line runs",
          memval(cap, T, 1) == "4d" and landmark(cap),
          f"D000={memval(cap, T, 1)} PC@landmark={'yes' if landmark(cap) else 'no'}")

    # 4. OUT: a port write completes and the rest of the line runs.
    cap = run(args.machine, args.cart, cas_path,
              f'out &ha0,7:poke &h{T:04x},88:bload"cas:",r',
              [f"memory:0x{T:04X}:1"], bp=LANDMARK)
    check("OUT &HA0,7 completes, line runs",
          memval(cap, T, 1) == "58" and landmark(cap),
          f"D000={memval(cap, T, 1)} PC@landmark={'yes' if landmark(cap) else 'no'}")

    # 5. VARPTR round-trip: PEEK the value cell VARPTR points at and recover the
    #    16-bit value (LE). zerobas's own table address, but a valid cell.
    cap = run(args.machine, args.cart, cas_path,
              (f'b=&h1234:a=varptr(b):c=peek(a):d=peek(a+1):'
               f'poke &h{T:04x},c:poke &h{T+1:04x},d:bload"cas:",r'),
              [f"memory:0x{T:04X}:2"], bp=LANDMARK)
    check("VARPTR(b) cell holds b=&H1234 (LE)", memval(cap, T, 2) == "3412",
          f"D000..1={memval(cap, T, 2)}")

    # 6. BASE descope: BASE(0) returns 0 + sets ERRMARK, but the line continues
    #    (the following POKE runs). We assert D000 ran and ERRMARK = $DD.
    cap = run(args.machine, args.cart, cas_path,
              f'a=base(0):poke &h{T:04x},99:bload"cas:",r',
              [f"memory:0x{T:04X}:1", f"memory:0x{ERRMARK:04X}:1"], bp=LANDMARK)
    check("BASE(0) descoped (returns 0, sets ERRMARK, line continues)",
          memval(cap, T, 1) == "63" and memval(cap, ERRMARK, 1) == "dd",
          f"D000={memval(cap, T, 1)} ERRMARK={memval(cap, ERRMARK, 1)}")

    os.unlink(cas_path)
    print("\nALL PASS" if ok else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
