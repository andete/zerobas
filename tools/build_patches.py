#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Build the zerobas ROM patches (IPS + BPS) — portable, no shell required.

This replaces the old `build-patches.sh` + `tape/build-patches.sh` so the patch
build runs identically on Linux, macOS, and Windows (the shell scripts were /bin/sh
and hardcoded a macOS C-BIOS path). All host-specific path discovery lives in
`openmsx_paths.py`.

Two patch sets, selected by mode:

  page1 (default)  zerobas BASIC spliced into a stock C-BIOS main ROM's slot-0
                   page 1 ($4000-$7FFF) -> zerobas-msx1.ips / .bps. On a real MSX,
                   BASIC sits there next to the BIOS; C-BIOS leaves it almost empty.

  tape (--tape)    the cassette-BIOS patch assembled from tape/tape.asm alone (no
                   C-BIOS compiled) -> tape/zerobas-tape-msx1.ips / .bps.

The stock C-BIOS main ROM is the patch *target* (and the BPS's CRC32 source). Pass
it explicitly, or it is auto-detected from your openMSX install. The IPS is
universal; the BPS is CRC-locked to that exact stock ROM and fails cleanly on a
mismatch.

    python3 tools/build_patches.py [STOCK_ROM]          # page-1 BASIC patch
    python3 tools/build_patches.py --tape [STOCK_ROM]   # cassette patch
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile

import openmsx_paths

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(REPO, "tools")
PASMO = os.environ.get("PASMO", "pasmo")
PY = sys.executable  # this interpreter -- avoids assuming `python3` on PATH (Windows)


def run(cmd, **kw):
    """Run a command, echoing it; raise on failure."""
    print("  " + " ".join(cmd))
    subprocess.run(cmd, check=True, **kw)


def ensure_basic_rom() -> str:
    """The page-1 patch needs build/basic.rom. When invoked via the Makefile it is
    already built (a prerequisite); assemble it here too so the script also works
    standalone, with no `make` dependency."""
    rom = os.path.join(REPO, "build", "basic.rom")
    if not os.path.isfile(rom):
        print("building build/basic.rom...")
        os.makedirs(os.path.dirname(rom), exist_ok=True)
        run([PASMO, "--bin", os.path.join(REPO, "basic", "main.asm"), rom])
        run([PY, os.path.join(TOOLS, "pad_rom.py"), rom, "16384"])
    return rom


def resolve_stock(explicit, names) -> str | None:
    stock = openmsx_paths.find_cbios_rom(names, explicit)
    if stock and not os.path.isfile(stock):
        stock = None
    return stock


def build_page1(explicit_stock):
    rom = ensure_basic_rom()
    stock = resolve_stock(explicit_stock, "cbios_main_msx1.rom")
    if not stock:
        sys.exit("error: stock C-BIOS main ROM not found.\n"
                 "       pass it: python3 tools/build_patches.py /path/to/cbios_main_msx1.rom")

    patch = os.path.join(TOOLS, "rom_patch.py")
    overlay = os.path.join(TOOLS, "overlay_page1.py")
    with tempfile.TemporaryDirectory() as work:
        combined = os.path.join(work, "combined.rom")
        print("splicing zerobas into C-BIOS page 1...")
        run([PY, overlay, stock, rom, combined])
        print("making patches...")
        run([PY, patch, "make", stock, combined, os.path.join(REPO, "zerobas-msx1.ips")])
        run([PY, patch, "make", stock, combined, os.path.join(REPO, "zerobas-msx1.bps")])
    print("done.")


def build_tape(explicit_stock):
    tape_dir = os.path.join(REPO, "tape")
    patch = os.path.join(TOOLS, "rom_patch.py")
    stock = resolve_stock(explicit_stock, "cbios_main_msx1_eu.rom")

    with tempfile.TemporaryDirectory() as work:
        tape_bin = os.path.join(work, "tape.bin")
        tape_sym = os.path.join(work, "tape.sym")
        print("assembling tape.asm (our code only)...")
        run([PASMO, "--bin", os.path.join(tape_dir, "tape.asm"), tape_bin, tape_sym])

        def forge(out, with_source):
            cmd = [PY, patch, "forge", out, "--bin", tape_bin, "--sym", tape_sym,
                   "--base", "0xE1", "--region", "0xE2:0xF6", "--region", "0x3A72:tape_end"]
            if with_source:
                cmd += ["--source", stock]
            run(cmd)

        ips = os.path.join(tape_dir, "zerobas-tape-msx1.ips")
        bps = os.path.join(tape_dir, "zerobas-tape-msx1.bps")
        if stock:
            forge(ips, with_source=True)
            forge(bps, with_source=True)
        else:
            print(f"note: stock ROM not found; building IPS only "
                  f"(BPS needs the stock ROM for its CRC32).")
            print("      pass it: python3 tools/build_patches.py --tape "
                  "/path/to/cbios_main_msx1_eu.rom")
            forge(ips, with_source=False)
    print("done.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tape", action="store_true",
                    help="build the cassette-BIOS patch instead of the page-1 patch")
    ap.add_argument("stock", nargs="?",
                    help="stock C-BIOS main ROM (auto-detected from openMSX if omitted)")
    args = ap.parse_args()
    if args.tape:
        build_tape(args.stock)
    else:
        build_page1(args.stock)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
