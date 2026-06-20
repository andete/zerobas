#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause

"""Install tape-enabled C-BIOS machines into your openMSX user folder.

For each C-BIOS machine openMSX ships this writes a "<name>_TAPE" machine that is
byte-for-byte the stock machine with the cbios-tape cassette patch applied to its
main ROM on load. The patch's only ROM dependency is a spare ROM region present in
every C-BIOS variant (it carries its own motor routine), so the *same* .ips applies
to MSX1, MSX2, and MSX2+ alike.

It does NOT copy or modify any ROM. The generated config points at openMSX's own
bundled ROMs by absolute path and lists the .ips as a load-time <patches> entry, so
openMSX still loads the pristine ROM and patches it in memory each boot.

    python3 tools/install-openmsx-machine.py            # auto-detect everything
    python3 tools/install-openmsx-machine.py --dry-run   # show what it would write
    python3 tools/install-openmsx-machine.py --share /path/to/openmsx/share \
                                             --user  /path/to/.openMSX

Then launch openMSX and pick e.g. "C-BIOS_MSX1_EU_TAPE", or:
    openmsx -machine C-BIOS_MSX1_EU_TAPE

The full cassette round-trip is validated on MSX1, MSX2, and MSX2+ (both 1200 and
2400 baud), so every generated machine is a first-class target.
"""
from __future__ import annotations

import argparse, glob, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IPS = os.path.join(REPO, "cbios-tape-msx1.ips")

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


def patch_config(text: str, share_machines: str) -> str:
    """Make every bare ROM <filename> absolute, then add the .ips as a load-time
    patch on the main ROM (the one whose filename is cbios_main_msx1*.rom)."""
    def absolutize(m):
        name = m.group(2)
        if "/" in name:                      # already a path -- leave it
            return m.group(0)
        return f"{m.group(1)}{os.path.join(share_machines, name)}{m.group(3)}"
    text = re.sub(r"(<filename>)([^<]+)(</filename>)", absolutize, text)

    # Inject <patches> right after the main ROM's (now absolute) filename line.
    pat = re.compile(r"^([ \t]*)<filename>([^<]*cbios_main_msx[^<]*)</filename>\s*$",
                     re.MULTILINE)
    def inject(m):
        ind = m.group(1)
        block = (f"{m.group(0)}\n"
                 f"{ind}<patches>\n"
                 f"{ind}  <ips>{IPS}</ips>\n"
                 f"{ind}</patches>")
        return block
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
        sys.exit(f"error: patch not found: {IPS} (run `make` first)")

    share = args.share or first_existing(SHARE_CANDIDATES, "openMSX share dir")
    user = args.user or first_existing(USER_CANDIDATES, "openMSX user dir")
    share_machines = os.path.join(share, "machines")
    user_machines = os.path.join(user, "share", "machines")

    stock = sorted(p for p in glob.glob(os.path.join(share_machines, "C-BIOS_MSX*.xml"))
                   if "_TAPE" not in p)
    if not stock:
        sys.exit(f"error: no C-BIOS machines in {share_machines}")

    if not args.dry_run:
        os.makedirs(user_machines, exist_ok=True)

    print(f"source machines : {share_machines}")
    print(f"install into    : {user_machines}")
    print(f"patch           : {IPS}\n")
    for src in stock:
        base = os.path.splitext(os.path.basename(src))[0]      # C-BIOS_MSX1_EU
        out = os.path.join(user_machines, f"{base}_TAPE.xml")
        out_text = patch_config(open(src).read(), share_machines)
        if args.dry_run:
            print(f"would write {os.path.basename(out)}")
        else:
            open(out, "w").write(out_text)
            print(f"wrote {base}_TAPE   (-> machine \"{base}_TAPE\")")
    print("\nDone. Launch openMSX and pick one of the *_TAPE machines.")


if __name__ == "__main__":
    main()
