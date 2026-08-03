#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

r"""Oracle probe: how a real MSX (VG-8020) holds the cassette write-baud state.

Clean-room oracle observation for zerobas-tape. Drives the Philips VG-8020 as a
BLACK BOX -- boots its MSX-BASIC, sets the cassette baud the documented way
(`SCREEN [,,,baud]`), and reads back the *work-area RAM* (a side-effect / output),
never any ROM code. See tape/docs/clean-room-policy.md.

What it established:

  * The cassette WRITE-timing work area, per C-BIOS systemvars.asm (allowed src):
        CS120  $F3FC   1200-baud signal lengths
        CS240  $F401   2400-baud signal lengths
        LOW    $F406 / HIGH $F408   active signal lengths (copied from CS120/CS240)
        HEADER $F40A   active leader length
    On the oracle these read (default boot, 1200):
        F3FC: 53 5C 26 2D 0F | 25 2D 0E 16 1F | 53 5C 26 2D 0F | ...
              \ CS120 (1200) / \ CS240 (~half) / \ active LOW/HIGH /
    -> our original baud selector at $F3FC stomped the live CS120 table (since
       fixed: TAPOON now reads the active table and caches the baud in WINWID).

  * `SCREEN ,,,baud` copies the chosen reference table into the active slots
    (verified -- see `--screen`):
        SCREEN ,,,1 -> active LOW = 53 5C (CS120)   [1200]
        SCREEN ,,,2 -> active LOW = 25 2D (CS240)   [2400]
    So the active LOW word at $F406 *is* the live baud indicator. zerobas-tape's
    TAPOON reads it (cas_baud) to honour whatever baud the system chose, with no
    private flag; CONLO $F66A is BASIC scratch, not a baud byte (it reads the
    same after either SCREEN baud).

Reliable headless typing: inject the BASIC line and its Enter as ONE keystroke
string with a real trailing CR, and bracket it with a sentinel POKE whose
read-back proves the line actually executed before trusting the RAM dump. (An
earlier split command/Enter with an escaped "\r" silently dropped the Enter,
which is what made past spot checks look flaky.)

Usage:
    python3 probes/tape/cas_baud_oracle.py [--machine Philips_VG_8020] [--screen]

Requires the VG-8020 system ROMs installed in openMSX (the oracle machine).
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "lib"))
import omsx_preflight  # noqa: E402

# Shared infra lives in probes/lib/ (driven as a subprocess, like realtape).
OMSX_RUN = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib", "omsx_run.py")

# Cassette write-timing work area (C-BIOS systemvars.asm; allowed source).
TABLES = [
    (0xF3FC, 5, "CS120  (1200-baud signal lengths)"),
    (0xF401, 5, "CS240  (2400-baud signal lengths)"),
    (0xF406, 2, "LOW    (active low-signal length)"),
    (0xF408, 2, "HIGH   (active high-signal length)"),
    (0xF40A, 2, "HEADER (active leader length)"),
    (0xFCA4, 1, "LOWLIM (read threshold)"),
    (0xFCA5, 1, "WINWID (read window; zerobas-tape caches CASBAUD here)"),
]

SENTINEL = 0xE000   # sentinel POKE target: proves the typed BASIC line executed


def run(machine: str, mems: list[str], types: list[tuple[str, float]], secs: int) -> dict:
    """Boot the machine, optionally type lines, dump memory; return {addr: byte}."""
    out = tempfile.NamedTemporaryFile("r", suffix=".txt", delete=False)
    out.close()
    cmd = [sys.executable, OMSX_RUN, "--machine", machine]
    for text, delay in types:
        cmd += ["--type", text, "--type-delay", str(delay)]
    for m in mems:
        cmd += ["--mem", m]
    cmd += ["--time", str(secs), "--out", out.name, "--timeout", "120"]
    subprocess.run(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    d = {}
    for line in open(out.name):
        m = re.match(r"mem\.memory:0x([0-9A-Fa-f]+):\d+=([0-9a-f]*)", line.strip())
        if m:
            base = int(m.group(1), 16)
            for i, x in enumerate(bytes.fromhex(m.group(2))):
                d[base + i] = x
    os.unlink(out.name)
    return d


def screen_baud(b: int) -> list[tuple[str, float]]:
    """One keystroke string: select baud and set the sentinel, with a real CR so
    the Enter is not dropped. Read $E000 back == 0x42 to confirm it executed."""
    return [(f"SCREEN ,,,{b}:POKE &H{SENTINEL:04X},&H42\r", 5.0)]


def dump_tables(machine: str, base: dict) -> None:
    print("cassette write-timing work area:")
    for addr, n, name in TABLES:
        val = " ".join(f"{base.get(addr + i, 0):02x}" for i in range(n))
        print(f"  0x{addr:04X} {name:<48} {val}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default="Philips_VG_8020", help="oracle machine id")
    ap.add_argument("--screen", action="store_true",
                    help="also run the verified SCREEN ,,,1 vs ,,,2 active-table diff")
    args = ap.parse_args()

    print(f"oracle: {args.machine}\n")

    # 1. Annotated dump of the write-timing tables at default boot (1200).
    base = run(args.machine, ["memory:0xF3FC:16", "memory:0xFCA4:2"], [], 6)
    print("default boot (no SCREEN):")
    dump_tables(args.machine, base)

    if not args.screen:
        print("\n(pass --screen to confirm SCREEN ,,,baud copies CS120/CS240 into "
              "the active slots)")
        return 0

    # 2. SCREEN ,,,1 vs ,,,2: dump the active table, each gated on the sentinel.
    mems = ["memory:0xF3FC:16", "memory:0xFCA4:2",
            f"memory:0x{SENTINEL:04X}:1", "memory:0xF66A:2"]
    rc = 0
    for b in (1, 2):
        d = run(args.machine, mems, screen_baud(b), 8)
        ran = d.get(SENTINEL) == 0x42
        print(f"\nSCREEN ,,,{b}  (line executed: {'yes' if ran else 'NO -- distrust'}):")
        if not ran:
            rc = 1
        dump_tables(args.machine, d)
        low = " ".join(f"{d.get(0xF406 + i, 0):02x}" for i in range(2))
        ref = "CS120/1200" if low == "53 5c" else "CS240/2400" if low == "25 2d" else "??"
        print(f"  -> active LOW = {low}  ({ref})")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
