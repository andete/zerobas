#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""install_cbios_msx2 -- openMSX machines running a C-BIOS checkout's OWN MSX2 / MSX2+ builds (D-MSX2SPEC).

The MSX2 / MSX2+ spec pages (docs/msx2/) measure C-BIOS against three references (Joost 2026-11-23: openMSX's
generic machines -- Sony HB-F900, Philips NMS 8250, Panasonic FS-A1WSX). openMSX ships a C-BIOS of its own; this
installs machines that run the C-BIOS built from a checkout instead, so a page measures the code under review.

For each variant the bundled openMSX config is copied, its ROMs' <sha1> pins dropped and their <filename>s
pointed at copies of the checkout's derived/bin ROMs (~/.openMSX/share/zerobas-cbios2/<tag>/), under the name
CBIOS2_<TAG>_<VARIANT> in ~/.openMSX/share/machines. probes/bios/biosl_run.py's msx2* rows use TAG CUR.

    python3 tools/install_cbios_msx2.py --cbios <built C-BIOS checkout> [--tag CUR]
"""
import argparse
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUNDLED = "/Applications/openMSX.app/Contents/Resources/share/machines"
USER = os.path.expanduser("~/.openMSX/share/machines")
# variant -> the bundled config it is made from
VARIANTS = {"MSX2_EU": "C-BIOS_MSX2_EU", "MSX2_JP": "C-BIOS_MSX2_JP", "MSX2P_JP": "C-BIOS_MSX2+_JP"}


def install(cbios, tag):
    binp = os.path.join(cbios, "derived", "bin")
    if not os.path.isdir(binp):
        sys.exit(f"install_cbios_msx2: {binp} missing -- run `make` in the checkout first")
    # outside the repo's build/: `make clean` (routine before a ROM build) wiped the copies there once (2026-11-23)
    # and every msx2* row refused until they were reinstalled
    dest = os.path.join(os.path.dirname(USER), "zerobas-cbios2", tag.lower())
    os.makedirs(dest, exist_ok=True)
    for f in os.listdir(binp):
        if f.endswith(".rom"):
            shutil.copyfile(os.path.join(binp, f), os.path.join(dest, f))
    names = []
    for var, src in VARIANTS.items():
        xml = open(os.path.join(BUNDLED, src + ".xml")).read()
        xml = re.sub(r"\s*<sha1>[0-9a-f]+</sha1>", "", xml)

        def repoint(m):
            p = os.path.join(dest, m.group(1))
            if not os.path.exists(p):
                sys.exit(f"install_cbios_msx2: {src} wants {m.group(1)}, not built in {binp}")
            return f"<filename>{p}</filename>"
        xml = re.sub(r"<filename>([^<]+)</filename>", repoint, xml)
        name = f"CBIOS2_{tag.upper()}_{var}"
        open(os.path.join(USER, name + ".xml"), "w").write(xml)
        names.append(name)
    print("installed: " + ", ".join(names) + f"  (ROMs in {dest})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cbios", required=True)
    ap.add_argument("--tag", default="CUR")
    a = ap.parse_args()
    install(os.path.abspath(os.path.expanduser(a.cbios)), a.tag)
    return 0


if __name__ == "__main__":
    sys.exit(main())
