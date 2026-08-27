#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Build the zerobas ROM patches (IPS + BPS) — portable, no shell required.

This replaces the old `build-patches.sh` + `tape/build-patches.sh` so the patch
build runs identically on Linux, macOS, and Windows (the shell scripts were /bin/sh
and hardcoded a macOS C-BIOS path). All host-specific path discovery lives in
`openmsx_paths.py`.

Two patch sets, selected by mode:

  page1 (default)  RETIRED 2026-07-29. Spliced the LEAN 16 KB BASIC into a stock
                   C-BIOS main ROM's page 1 -> zerobas-msx1.ips / .bps. That build and
                   both files are gone (docs/spec-lean-retire-s2-switch.md); the mode
                   now exits with a message rather than recreating them.

  tape (--tape)    the cassette-BIOS patch assembled from tape/tape.asm alone (no
                   C-BIOS compiled) -> tape/zerobas-tape-msx1.ips / .bps.

The stock C-BIOS main ROM is the patch *target* (and the BPS's CRC32 source). Pass
it explicitly, or it is auto-detected from your openMSX install. The IPS is
universal; the BPS is CRC-locked to that exact stock ROM and fails cleanly on a
mismatch.

  main (--main)    the merged repack main ROM (D4): repacked C-BIOS + relocated
                   BASIC ($2812-$7FFF) + tape, diffed vs pristine stock built from
                   the pinned tag -> zerobas-main-eu.ips / .bps.

    python3 tools/build_patches.py [STOCK_ROM]          # page-1 BASIC patch
    python3 tools/build_patches.py --tape [STOCK_ROM]   # cassette patch
    python3 tools/build_patches.py --main               # merged repack main ROM
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile

import openmsx_paths

# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "probes", "lib"))
import omsx_preflight  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(REPO, "tools")
PASMO = os.environ.get("PASMO", "pasmo")
PY = sys.executable  # this interpreter -- avoids assuming `python3` on PATH (Windows)


def run(cmd, **kw):
    """Run a command, echoing it; raise on failure."""
    print("  " + " ".join(cmd))
    subprocess.run(omsx_preflight.guarded(cmd), check=True, **kw)


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
        if b[0xDB] != 0xC3:
            sys.exit(f"  FAIL {name}: $00DB = {b[0xDB]:02X}, expected C3 (GTPAD "
                     f"must be a JP vector we can repoint)")
        if b[0xDE] != 0xC3:
            sys.exit(f"  FAIL {name}: $00DE = {b[0xDE]:02X}, expected C3 (GTPDL "
                     f"must be a JP vector we can repoint)")
        fill = b[FREE_ORG_ADDR:tape_end]
        if any(x != 0x00 for x in fill):
            bad = FREE_ORG_ADDR + next(i for i, x in enumerate(fill) if x)
            sys.exit(f"  FAIL {name}: page-0 fill ${FREE_ORG_ADDR:04X}..${tape_end:04X} is not all "
                     f"0x00 (first non-zero at ${bad:04X}) -- our routine bodies "
                     f"would collide with stock code")
    print(f"  OK: $00A5/$00DB/$00DE/$00E1 are JP vectors and ${FREE_ORG_ADDR:04X}..${tape_end:04X} is free "
          f"in all {len(roms)} ROM(s).")


FREE_ORG_ADDR = 0x09EE   # D5 revision 2026-07-11: was 0x3A72 (see tape/tape.asm FREE_ORG)


def resolve_stock(explicit, names) -> str | None:
    stock = openmsx_paths.find_cbios_rom(names, explicit)
    if stock and not os.path.isfile(stock):
        stock = None
    return stock


def build_page1(explicit_stock):
    # RETIRED 2026-07-29 (RETIRE THE LEAN 16 KB CART, S2 --
    # docs/spec-lean-retire-s2-switch.md). This mode splices the LEAN 16 KB basic.rom
    # into a stock C-BIOS page 1 and writes zerobas-msx1.ips/.bps, which are DELETED
    # from the tree. Running it would silently resurrect a retired deliverable at its
    # old tracked path, where `git status` makes it look like a legitimate rebuild --
    # so it refuses rather than defaulting to the retired build.
    sys.exit(
        "error: the page-1 (lean) patch mode is RETIRED.\n"
        "       It writes zerobas-msx1.ips/.bps from the lean 16 KB build, which zerobas\n"
        "       no longer builds or ships (docs/spec-lean-retire-s2-switch.md).\n"
        "       The shipped BASIC patch is zerobas-main-eu.ips/.bps:\n"
        "           make release            # or: build_patches.py --main --cbios <checkout>\n"
        "       The cassette patch is unaffected:  build_patches.py --tape")


# DELETED 2026-08-05 (D-DSKJUDGE §3.3, docs/spec-rom-gate-diskrom.md): the body of
# the retired lean page-1 mode, `_build_page1_retired()`, and the `ensure_basic_rom()`
# helper that only it called. Neither had a caller: `build_page1()` above `sys.exit`s
# the mode, and nothing anywhere calls `_build_page1_retired` (grepped across tools/,
# probes/, tests/ and both Makefiles). It was kept as a reference body when the lean
# cart was retired on 2026-07-29; a year of `git log` is a better reference than a
# function that cannot run.
#
# 🔴 AND IT WOULD HAVE FAILED IF IT RAN. `ensure_basic_rom()` assembled basic/main.asm
# and called `pad_rom.py <rom> 16384` -- but basic/main.asm has assembled at
# BASIC_ORG = $2812, spanning to $8000, since the same retirement: 22510 bytes, which
# pad_rom now answers with `exceeds target 16384`. Dead code does not rot quietly; it
# rots into a call that takes the build down the first time anything reaches it.
# The retired mode itself is documented in docs/spec-lean-retire-s2-switch.md.


def build_tape(explicit_stock, out_dir=None):
    """`out_dir` redirects the patch pair, so `check_patch_freshness.py` can
    regenerate it hermetically and diff it against the tracked one without
    touching the working copy. Same contract as `build_main`."""
    tape_dir = out_dir if out_dir else os.path.join(REPO, "tape")
    os.makedirs(tape_dir, exist_ok=True)
    patch = os.path.join(TOOLS, "rom_patch.py")
    stock = resolve_stock(explicit_stock, "cbios_main_msx1_eu.rom")

    with tempfile.TemporaryDirectory() as work:
        tape_bin = os.path.join(work, "tape.bin")
        tape_sym = os.path.join(work, "tape.sym")
        print("assembling tape.asm (our code only)...")
        run([PASMO, "--bin", os.path.join(REPO, "tape", "tape.asm"),
             tape_bin, tape_sym])   # SOURCE is always the repo's

        # Verify the patch's page-0 assumptions hold in EVERY C-BIOS main ROM, so
        # the one universal IPS stays byte-safe across all variants (DESIGN.md):
        #   - $00A5 is a C3 JP vector (we repoint its target -> LPTOUT)
        #   - $00DB/$00DE are C3 JP vectors (we repoint them -> GTPAD/GTPDL)
        #   - $00E1 is a C3 JP vector (the cassette table -- long-standing)
        #   - $09EE..tape_end is 0x00 fill (our routine bodies land there)
        verify_all_variants(tape_sym)

        def forge(out, with_source):
            cmd = [PY, patch, "forge", out, "--bin", tape_bin, "--sym", tape_sym,
                   "--base", "0xA5",
                   "--region", "0xA5:0xA8",         # $00A5 LPTOUT vector
                   "--region", "0xDB:0xE1",         # $00DB GTPAD + $00DE GTPDL vectors
                   "--region", "0xE2:0xF6",         # seven cassette vector targets
                   "--region", "0x9EE:tape_end"]    # routine bodies (cassette + LPTOUT + PAD/PDL)
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


def build_main(cbios_checkout, out_dir=None):
    """Merged main-ROM patch (cbios-repack arc, WS-3 / D4): repacked C-BIOS +
    relocated BASIC ($2812-$7FFF) + tape, diffed vs the PRISTINE stock built from
    the same pinned tag -> one zerobas-main-eu.ips/.bps. The repacked + pristine
    ROMs are built reproducibly from the user's C-BIOS checkout (no C-BIOS bytes
    in-repo, D1).

    `out_dir` redirects EVERY output — the intermediate ROMs as well as the patch
    pair — under one directory, so a freshness check can regenerate the shipped
    deliverable through this exact code path without touching either the tracked
    files or `build/`. It must be all-or-nothing: redirecting only the patches
    would still write `build/`, which races a parallel gate battery
    (tools/check_patch_freshness.py, docs/spec-patch-freshness-gate.md)."""
    patch = os.path.join(TOOLS, "rom_patch.py")
    build = out_dir if out_dir else os.path.join(REPO, "build")
    dest = out_dir if out_dir else REPO
    os.makedirs(build, exist_ok=True)
    repacked = os.path.join(build, "cbios_main_msx1_eu-repacked.rom")
    pristine = os.path.join(build, "cbios_main_msx1_eu-pristine.rom")
    reloc = os.path.join(build, "basic-reloc.rom")
    merged = os.path.join(build, "zerobas-main-eu.rom")

    print("building repacked + pristine C-BIOS from the pinned tag...")
    run([PY, os.path.join(TOOLS, "build_repacked_cbios.py"),
         "--cbios", cbios_checkout, "-o", repacked, "--pristine", pristine])
    print("assembling relocated BASIC ($2812) + tape...")
    run([PASMO, "--bin", os.path.join(REPO, "basic", "main.asm"), reloc])
    with tempfile.TemporaryDirectory() as work:
        tape_bin = os.path.join(work, "tape.bin")
        tape_sym = os.path.join(work, "tape.sym")
        run([PASMO, "--bin", os.path.join(REPO, "tape", "tape.asm"), tape_bin, tape_sym])
        print("merging the main ROM...")
        run([PY, os.path.join(TOOLS, "build_mainrom.py"),
             repacked, reloc, tape_bin, tape_sym, merged])
    print("making patches (vs pristine stock)...")
    run([PY, patch, "make", pristine, merged, os.path.join(dest, "zerobas-main-eu.ips")])
    run([PY, patch, "make", pristine, merged, os.path.join(dest, "zerobas-main-eu.bps")])
    print("done.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--tape", action="store_true",
                      help="build the cassette-BIOS patch instead of the page-1 patch")
    mode.add_argument("--main", action="store_true",
                      help="build the merged repack main-ROM patch (cbios-repack arc)")
    ap.add_argument("--cbios", default="~/projects/cbios",
                    help="C-BIOS checkout for --main (default ~/projects/cbios)")
    ap.add_argument("--out-dir",
                    help="--main / --tape: write the patch pair (and, for "
                         "--main, the intermediate ROMs) under this directory "
                         "instead of build/ and the repo root. Used by the "
                         "freshness check to regenerate hermetically.")
    ap.add_argument("stock", nargs="?",
                    help="stock C-BIOS main ROM (auto-detected from openMSX if omitted)")
    args = ap.parse_args()
    if args.main:
        build_main(args.cbios, args.out_dir)
    elif args.tape:
        build_tape(args.stock, args.out_dir)
    elif args.out_dir:
        sys.exit("--out-dir is only meaningful with --main or --tape")
    else:
        build_page1(args.stock)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
