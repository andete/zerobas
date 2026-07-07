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


def _sym_value(sym_path: str, label: str) -> int:
    """Read one label's address from a pasmo .sym file (`LABEL\tEQU\tXXXXH`)."""
    for line in open(sym_path):
        parts = line.replace(":", " ").split()
        if parts and parts[0] == label:
            return int(parts[-1].rstrip("Hh"), 16)
    raise SystemExit(f"label {label!r} not found in {sym_path}")


def verify_all_variants(tape_sym: str) -> None:
    """Assert the page-0 layout the tape patch relies on holds in EVERY C-BIOS main
    ROM present, so the single universal IPS is byte-safe across all variants (the
    DESIGN.md universality guarantee). Fails the build on any violation; warns (does
    not fail) if no ROMs are found — the IPS is still produced, just unverified."""
    import glob
    tape_end = _sym_value(tape_sym, "tape_end")
    roms = []
    for share in openmsx_paths.SHARE_CANDIDATES:
        roms += sorted(glob.glob(os.path.join(share, "machines", "cbios_main_msx*.rom")))
    roms = [r for r in roms if os.path.isfile(r)]
    if not roms:
        print("  warning: no C-BIOS main ROMs found -- skipping multi-variant "
              "layout verification (the IPS is still universal by construction).")
        return
    print(f"  verifying page-0 layout across {len(roms)} C-BIOS main ROM(s)...")
    for r in roms:
        b = open(r, "rb").read()
        name = os.path.basename(r)
        if b[0xA5] != 0xC3:
            sys.exit(f"  FAIL {name}: $00A5 = {b[0xA5]:02X}, expected C3 (LPTOUT "
                     f"must be a JP vector we can repoint)")
        if b[0xE1] != 0xC3:
            sys.exit(f"  FAIL {name}: $00E1 = {b[0xE1]:02X}, expected C3 (cassette "
                     f"jump table)")
        fill = b[FREE_ORG_ADDR:tape_end]
        if any(x != 0x00 for x in fill):
            bad = FREE_ORG_ADDR + next(i for i, x in enumerate(fill) if x)
            sys.exit(f"  FAIL {name}: page-0 fill $3A72..${tape_end:04X} is not all "
                     f"0x00 (first non-zero at ${bad:04X}) -- our routine bodies "
                     f"would collide with stock code")
    print(f"  OK: $00A5/$00E1 are JP vectors and $3A72..${tape_end:04X} is free "
          f"in all {len(roms)} ROM(s).")


FREE_ORG_ADDR = 0x3A72


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

        # Verify the patch's page-0 assumptions hold in EVERY C-BIOS main ROM, so
        # the one universal IPS stays byte-safe across all variants (DESIGN.md):
        #   - $00A5 is a C3 JP vector (we repoint its target -> LPTOUT)
        #   - $00E1 is a C3 JP vector (the cassette table -- long-standing)
        #   - $3A72..tape_end is 0x00 fill (our routine bodies land there)
        verify_all_variants(tape_sym)

        def forge(out, with_source):
            cmd = [PY, patch, "forge", out, "--bin", tape_bin, "--sym", tape_sym,
                   "--base", "0xA5",
                   "--region", "0xA5:0xA8",         # $00A5 LPTOUT vector
                   "--region", "0xE2:0xF6",         # seven cassette vector targets
                   "--region", "0x3A72:tape_end"]   # routine bodies (cassette + LPTOUT)
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
