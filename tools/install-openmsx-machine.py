#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause

"""Install zerobas-equipped C-BIOS machines into your openMSX user folder.

For each MSX1 C-BIOS machine openMSX ships this writes a "<name>_BASIC" machine
that is byte-for-byte the stock machine with two load-time patches on its main ROM:
zerobas in slot-0 page 1 (BASIC next to the BIOS, the way a real MSX is laid out),
and the zerobas-tape cassette patch in page 0. C-BIOS's cold-boot cartridge scan
finds zerobas's "AB" header in page 1 and calls it, so the machine boots straight
to the zerobas prompt with no cartridge inserted -- and because the tape patch fills
in C-BIOS's failing cassette stubs, zerobas's `BLOAD"CAS:",R` actually completes.
The two patches touch disjoint regions (page 0 vs page 1), so they compose cleanly;
both are always applied.

It does NOT copy or modify any ROM. The generated config points at openMSX's own
bundled ROMs by absolute path and lists the .ips files as load-time <patches>
entries, so openMSX still loads the pristine ROM and patches it in memory each boot.

    python3 tools/install-openmsx-machine.py            # auto-detect everything
    python3 tools/install-openmsx-machine.py --dry-run   # show what it would write
    python3 tools/install-openmsx-machine.py --share /path/to/openmsx/share \
                                             --user  /path/to/.openMSX

Then launch openMSX and pick e.g. "C-BIOS_MSX1_EU_BASIC", or:
    openmsx -machine C-BIOS_MSX1_EU_BASIC

zerobas is MSX1 BASIC, so only the MSX1 C-BIOS variants are targeted.
"""
from __future__ import annotations

import argparse, glob, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IPS = os.path.join(REPO, "zerobas-msx1.ips")
TAPE_IPS = os.path.join(REPO, "tape", "zerobas-tape-msx1.ips")

# Where openMSX keeps its bundled machines + ROMs, by platform default.
SHARE_CANDIDATES = [
    "/Applications/openMSX.app/Contents/Resources/share",          # macOS
    "/opt/homebrew/share/openmsx", "/usr/local/share/openmsx",     # Homebrew
    "/usr/share/openmsx", "/usr/local/share/openMSX",              # Linux
]
USER_CANDIDATES = [
    os.path.expanduser("~/.openMSX"),
    os.path.expanduser("~/Documents/openMSX"),                     # some installs
]


def first_existing(paths, what):
    for p in paths:
        if os.path.isdir(p):
            return p
    sys.exit(f"error: could not auto-detect {what}; pass it explicitly "
             f"(looked in: {', '.join(paths)})")


def patch_config(text: str, share_machines: str, ips_list) -> str:
    """Make every bare ROM <filename> absolute, then add the .ips files as
    load-time patches on the main ROM (filename cbios_main_msx1*.rom). The
    patches are applied in the given order; they touch disjoint ROM regions."""
    def absolutize(m):
        name = m.group(2)
        if "/" in name:                      # already a path -- leave it
            return m.group(0)
        return f"{m.group(1)}{os.path.join(share_machines, name)}{m.group(3)}"
    text = re.sub(r"(<filename>)([^<]+)(</filename>)", absolutize, text)

    # Inject <patches> right after the main ROM's (now absolute) filename line.
    pat = re.compile(r"^([ \t]*)<filename>([^<]*cbios_main_msx1[^<]*)</filename>\s*$",
                     re.MULTILINE)
    def inject(m):
        ind = m.group(1)
        entries = "\n".join(f"{ind}  <ips>{p}</ips>" for p in ips_list)
        return (f"{m.group(0)}\n"
                f"{ind}<patches>\n"
                f"{entries}\n"
                f"{ind}</patches>")
    text, n = pat.subn(inject, text)
    if n != 1:
        raise RuntimeError(f"expected exactly one main-ROM filename, found {n}")
    return text


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--share", help="openMSX share dir (contains machines/)")
    ap.add_argument("--user", help="openMSX user dir (e.g. ~/.openMSX)")
    ap.add_argument("--dry-run", action="store_true", help="print, don't write")
    args = ap.parse_args()

    if not os.path.isfile(IPS):
        sys.exit(f"error: patch not found: {IPS} (run `sh build-patches.sh` first)")
    if not os.path.isfile(TAPE_IPS):
        sys.exit(f"error: tape patch not found: {TAPE_IPS} (run `make -C tape` first)")
    # Tape patch first (page 0), then zerobas (page 1) -- order is immaterial.
    ips_list = [TAPE_IPS, IPS]

    share = args.share or first_existing(SHARE_CANDIDATES, "openMSX share dir")
    user = args.user or first_existing(USER_CANDIDATES, "openMSX user dir")
    share_machines = os.path.join(share, "machines")
    user_machines = os.path.join(user, "share", "machines")

    # MSX1 C-BIOS only -- zerobas is MSX1 BASIC.
    stock = sorted(p for p in glob.glob(os.path.join(share_machines, "C-BIOS_MSX1*.xml"))
                   if "_BASIC" not in p)
    if not stock:
        sys.exit(f"error: no MSX1 C-BIOS machines in {share_machines}")

    if not args.dry_run:
        os.makedirs(user_machines, exist_ok=True)

    print(f"source machines : {share_machines}")
    print(f"install into    : {user_machines}")
    print(f"zerobas patch   : {IPS}")
    print(f"tape patch      : {TAPE_IPS}\n")
    for src in stock:
        base = os.path.splitext(os.path.basename(src))[0]      # C-BIOS_MSX1_EU
        out = os.path.join(user_machines, f"{base}_BASIC.xml")
        out_text = patch_config(open(src).read(), share_machines, ips_list)
        if args.dry_run:
            print(f"would write {os.path.basename(out)}")
        else:
            open(out, "w").write(out_text)
            print(f"wrote {base}_BASIC   (-> machine \"{base}_BASIC\")")
    print("\nDone. Launch openMSX and pick one of the *_BASIC machines.")


if __name__ == "__main__":
    main()
