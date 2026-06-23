#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""DATA / READ / RESTORE execution probe — validate zerobas Step B by running
real stored programs on openMSX.

The reference stores DATA items as verbatim ASCII text (oracle: `data 5,6` ->
$84 $20 '5' ',' '6'), so READ parses ASCII from the stored program at run time
and a DATA cursor walks the $84-tagged statements across lines. Each program
POKEs the values it READs to free RAM ($D000..) and we read them back; a direct
`bload"cas:",r` ending in `JR $` (LANDMARK) freezes RAM and proves termination.

Clean-room: observed inputs/outputs only. See the clean-room firewall (CONTRIBUTING.md)
and docs/test-strategy-stepb.md.
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
T, U, V = 0xD000, 0xD001, 0xD002
ERRMARK = 0xE010


def run_program(machine, cart, cas, prog, mems, base=8.0, step=4.0):
    """Type numbered lines, RUN, then a direct bload to freeze at LANDMARK
    (zerobas REPL: each Enter is a separate, later event under throttle off)."""
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="data_cap_")
    os.close(out_fd)
    cmd = [sys.executable, OMSX_RUN, "--machine", machine, "--cassette", cas,
           "--cart", cart]
    events = []
    for line in list(prog) + ["run", 'bload"cas:",r']:
        events += [line, "\r"]
    t = base
    for text in events:
        cmd += ["--type", text, "--type-delay", f"{t:g}"]
        t += step
    cmd += ["--bp", hex(LANDMARK), "--reg", "PC"]
    for m in mems:
        cmd += ["--mem", m]
    cmd += ["--out", out_path, "--timeout", "30"]
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=MACHINE)
    ap.add_argument("--cart", required=True, help="zerobas basic.rom")
    args = ap.parse_args()

    cas = build_cas("BLOAD", LOAD_ADDR, LOAD_ADDR, build_blob())
    cas_fd, cas_path = tempfile.mkstemp(suffix=".cas", prefix="data_probe_")
    os.write(cas_fd, cas)
    os.close(cas_fd)

    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL'}  {label}" + (f"  {detail}" if detail else ""))
        ok = ok and cond

    def zb(prog, addrs):
        mems = [f"memory:0x{a:04X}:1" for a in addrs]
        cap = run_program(args.machine, args.cart, cas_path, prog, mems)
        return {a: memval(cap, a, 1) for a in addrs}

    # 1. Sequential single-variable READs drain a DATA list in order.
    vals = zb(["10 data 7,8,9", "20 read a:read b:read c",
               f"30 poke &h{T:04x},a:poke &h{U:04x},b:poke &h{V:04x},c", "40 end"],
              [T, U, V])
    check("READ drains DATA 7,8,9 in order",
          vals[T] == "07" and vals[U] == "08" and vals[V] == "09",
          f"a={vals[T]} b={vals[U]} c={vals[V]}")

    # 2. One READ fills several variables.
    vals = zb(["10 data 11,22", "20 read a,b",
               f"30 poke &h{T:04x},a:poke &h{U:04x},b", "40 end"], [T, U])
    check("READ a,b fills both", vals[T] == "0b" and vals[U] == "16",
          f"a={vals[T]} b={vals[U]}")

    # 3. A READ crosses from one DATA statement (and line) to the next.
    vals = zb(["10 data 1,2", "20 data 3", "30 read a,b,c",
               f"40 poke &h{T:04x},a:poke &h{U:04x},b:poke &h{V:04x},c", "50 end"],
              [T, U, V])
    check("READ crosses DATA statements/lines",
          vals[T] == "01" and vals[U] == "02" and vals[V] == "03",
          f"a={vals[T]} b={vals[U]} c={vals[V]}")

    # 4. RESTORE rewinds to the first DATA item.
    vals = zb(["10 data 5,6", "20 read a", "30 restore", "40 read b",
               f"50 poke &h{T:04x},a:poke &h{U:04x},b", "60 end"], [T, U])
    check("RESTORE rewinds to first item", vals[T] == "05" and vals[U] == "05",
          f"a={vals[T]} b={vals[U]}")

    # 5. RESTORE <line> rewinds to a specific line's DATA.
    vals = zb(["10 data 1,2", "20 data 30,40", "30 read a", "40 restore 20",
               "50 read b", f"60 poke &h{T:04x},a:poke &h{U:04x},b", "70 end"],
              [T, U])
    check("RESTORE 20 rewinds to that line", vals[T] == "01" and vals[U] == "1e",
          f"a={vals[T]} b={vals[U]}")

    # 6. &H hex and negative DATA items parse correctly.
    vals = zb(["10 data &hff,-2", "20 read a,b",
               f"30 poke &h{T:04x},a:poke &h{U:04x},b", "40 end"], [T, U])
    check("&H and negative DATA items", vals[T] == "ff" and vals[U] == "fe",
          f"a={vals[T]} b(low)={vals[U]}")

    # 7. A statement after DATA on the same line still runs (DATA skips to ':').
    vals = zb([f"10 data 5:poke &h{T:04x},9", f"20 read a:poke &h{U:04x},a", "30 end"],
              [T, U])
    check("statement after DATA: on same line runs",
          vals[T] == "09" and vals[U] == "05", f"T={vals[T]} a={vals[U]}")

    # 8. Reading past the end raises "out of data" ($CA at ERRMARK).
    cap = run_program(args.machine, args.cart, cas_path,
                      ["10 data 1", "20 read a,b"],
                      [f"memory:0x{ERRMARK:04X}:1"])
    em = memval(cap, ERRMARK, 1)
    check("READ past end -> out of data $CA", em == "ca", f"E010={em}")

    os.unlink(cas_path)
    print("\nALL PASS" if ok else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
