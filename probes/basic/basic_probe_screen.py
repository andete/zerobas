#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""SCREEN / COLOR / CLS / WIDTH / KEY screen-setup verb probe (zerobas).

Boots the zerobas cartridge, types a screen-setup line into its REPL, and checks
the effect by dumping the BIOS work-area system variables the verbs drive. Each
test line ends in `bload"cas:",r`: the screen verbs run first, then the loaded
blob's `JR $` landmark (LANDMARK) freezes RAM. Because a verb that raised a
syntax error would abort the line *before* the trailing BLOAD, simply reaching
LANDMARK already proves the verb parsed and executed; the sysvar read then
confirms the actual effect.

These are thin wrappers over C-BIOS entry points, so the expected effects are the
documented BIOS behaviours:
  SCREEN n -> CHGMOD writes SCRMOD ($FCAF)
  COLOR    -> FORCLR/BAKCLR/BDRCLR ($F3E9..$F3EB)
  WIDTH n  -> LINLEN ($F3B0) (re-applied via CHGMOD)
  CLS      -> cursor home, CSRY/CSRX ($F3DC..$F3DD) = 1,1
  KEY OFF/ON -> ERAFNK/DSPFNK (observed indirectly: the line continues to a
              trailing POKE sentinel)

POKE sentinels target 0xD000 — clear of the blob (0xC000..) and its marker.
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
# Run on a real-BIOS machine: the test lines end in `bload"cas:",r`, whose blob
# landmark freezes RAM, and only a real cassette BIOS services that load (the
# same machine the BLOAD/statements probes use). The screen verbs are plain BIOS
# jump-table calls, identical on any MSX1 BIOS.
MACHINE = "Philips_VG_8020"
T = 0xD000                # POKE sentinel target, free RAM

SCRMOD = 0xFCAF
FORCLR = 0xF3E9           # FORCLR, BAKCLR, BDRCLR are consecutive
LINLEN = 0xF3B0
CSRY = 0xF3DC             # CSRY, CSRX consecutive


def run(cart, cas, line, mems, bp=None, secs=None, type_delay=8):
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="scr_cap_")
    os.close(out_fd)
    cmd = [sys.executable, OMSX_RUN, "--machine", MACHINE, "--cart", cart]
    if cas:
        cmd += ["--cassette", cas]
    # zerobas REPL: type the line, then a separately-timed Enter (a trailing CR
    # in the same burst is dropped under `throttle off`).
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


def landed(cap):
    return f"reg.PC=0x{LANDMARK:04X}" in cap


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cart", required=True, help="zerobas basic.rom")
    args = ap.parse_args()

    cas = build_cas("BLOAD", LOAD_ADDR, LOAD_ADDR, build_blob())
    cas_fd, cas_path = tempfile.mkstemp(suffix=".cas", prefix="scr_probe_")
    os.write(cas_fd, cas)
    os.close(cas_fd)

    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL'}  {label}" + (f"  {detail}" if detail else ""))
        if not cond:
            ok = False

    def line(body, mems):
        return run(args.cart, cas_path, body, mems, bp=LANDMARK)

    # 1. SCREEN 2 -> SCRMOD = 2.
    cap = line('screen 2:bload"cas:",r', [f"memory:0x{SCRMOD:04X}:1"])
    check("SCREEN 2 -> SCRMOD=2", landed(cap) and memval(cap, SCRMOD, 1) == "02",
          f"SCRMOD={memval(cap, SCRMOD, 1)}")

    # 2. SCREEN 1 -> SCRMOD = 1 (different mode, proves the arg is applied).
    cap = line('screen 1:bload"cas:",r', [f"memory:0x{SCRMOD:04X}:1"])
    check("SCREEN 1 -> SCRMOD=1", landed(cap) and memval(cap, SCRMOD, 1) == "01",
          f"SCRMOD={memval(cap, SCRMOD, 1)}")

    # 3. SCREEN 1,1 -> extra sprite-size arg is parsed+ignored, mode still 1.
    cap = line('screen 1,1:bload"cas:",r', [f"memory:0x{SCRMOD:04X}:1"])
    check("SCREEN 1,1 (ignores extra arg) -> SCRMOD=1",
          landed(cap) and memval(cap, SCRMOD, 1) == "01",
          f"SCRMOD={memval(cap, SCRMOD, 1)}")

    # 4. COLOR fg,bg,border -> the three colour sysvars.
    cap = line('color 4,7,5:bload"cas:",r', [f"memory:0x{FORCLR:04X}:3"])
    check("COLOR 4,7,5 -> FORCLR/BAKCLR/BDRCLR", memval(cap, FORCLR, 3) == "040705",
          f"colours={memval(cap, FORCLR, 3)}")

    # 5. COLOR ,9 -> omitted fg leaves FORCLR, bg(BAKCLR=$F3EA) becomes 9.
    cap = line('color ,9:bload"cas:",r', [f"memory:0x{FORCLR+1:04X}:1"])
    check("COLOR ,9 -> BAKCLR=9 (fg omitted)", memval(cap, FORCLR + 1, 1) == "09",
          f"BAKCLR={memval(cap, FORCLR + 1, 1)}")

    # 6. WIDTH 32 -> LINLEN = 0x20.
    cap = line('width 32:bload"cas:",r', [f"memory:0x{LINLEN:04X}:1"])
    check("WIDTH 32 -> LINLEN=0x20", memval(cap, LINLEN, 1) == "20",
          f"LINLEN={memval(cap, LINLEN, 1)}")

    # 7. CLS -> cursor home (CSRY=CSRX=1).
    cap = line('cls:bload"cas:",r', [f"memory:0x{CSRY:04X}:2"])
    check("CLS -> cursor home (CSRY,CSRX=1,1)", memval(cap, CSRY, 2) == "0101",
          f"CSRY,CSRX={memval(cap, CSRY, 2)}")

    # 8. KEY OFF executes and the line continues to the sentinel POKE.
    cap = line(f'key off:poke &h{T:04x},77:bload"cas:",r', [f"memory:0x{T:04X}:1"])
    check("KEY OFF (line continues) -> sentinel poked",
          landed(cap) and memval(cap, T, 1) == "4d", f"D000={memval(cap, T, 1)}")

    # 9. KEY ON executes and the line continues to the sentinel POKE.
    cap = line(f'key on:poke &h{T:04x},78:bload"cas:",r', [f"memory:0x{T:04X}:1"])
    check("KEY ON (line continues) -> sentinel poked",
          landed(cap) and memval(cap, T, 1) == "4e", f"D000={memval(cap, T, 1)}")

    os.unlink(cas_path)
    print("\nALL PASS" if ok else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
