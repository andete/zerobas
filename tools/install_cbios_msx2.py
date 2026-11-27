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
It also writes CBIOS2_<TAG>_MSX1_EU_NOBASIC_DISK: the checkout's MSX1 EU build with NO BASIC and zerobas's disk ROM
(build/disk.rom) in slot 3-1 -- the C-BIOS port's host (docs/disk/port-readiness.md gap 3; `make
nobasic-dossession-acceptance CBIOS=...`).

    python3 tools/install_cbios_msx2.py --cbios <built C-BIOS checkout> [--tag CUR]
    python3 tools/install_cbios_msx2.py --pinned

--pinned (C-BIOS integration step 3, 2026-11-27) needs no checkout: it writes only the NOBASIC machine, from the
ROM copies already in <share>/zerobas-cbios2/cur/, and only when they hash to tools/cbios-nobasic.pin (exit 2
otherwise: an instrument fault, never a green). Machines go to the share openMSX reads ($OPENMSX_USER_DATA when set
-- tools/gate_wt.py's private share), and the disk ROM is THIS tree's build/disk.rom, so a gate worktree measures
its own commit.
"""
import argparse
import os
import re
import shutil
import hashlib
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUNDLED = "/Applications/openMSX.app/Contents/Resources/share/machines"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import openmsx_paths  # noqa: E402
# the share openMSX reads -- $OPENMSX_USER_DATA (gate_wt's private share) when set
USER = os.path.join(openmsx_paths.find_user_share(), "machines")
PIN = os.path.join(ROOT, "tools", "cbios-nobasic.pin")
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
    names.append(install_nobasic(dest, tag))
    print("installed: " + ", ".join(names) + f"  (ROMs in {dest})")


def read_pin():
    pin = {}
    for ln in open(PIN):
        p = ln.split()
        if len(p) == 2 and not ln.startswith("#"):
            pin[p[0]] = p[1]
    return pin


def install_pinned(tag):
    dest = os.path.join(os.path.dirname(USER), "zerobas-cbios2", tag.lower())
    pin = read_pin()
    for f, want in pin.items():
        if f == "rev":
            continue
        p = os.path.join(dest, f)
        got = hashlib.sha1(open(p, "rb").read()).hexdigest() if os.path.isfile(p) else "missing"
        if got != want:
            print(f"install_cbios_msx2: INSTRUMENT FAULT -- {p} is {got}, tools/cbios-nobasic.pin wants {want} "
                  f"(C-BIOS {pin.get('rev')}); install it with --cbios <checkout at that revision>, or move the pin")
            return 2
    name = install_nobasic(dest, tag)
    print(f"installed: {name}  (C-BIOS {pin.get('rev')}, pinned; disk ROM {os.path.join(ROOT, 'build', 'disk.rom')})")
    return 0


def install_nobasic(dest, tag):
    # 💽 docs/disk/port-readiness.md gap 3 (2026-11-26): the C-BIOS PORT'S HOST -- the checkout's own MSX1 EU build,
    # NO BASIC anywhere, zerobas's disk ROM in slot 3-1 behind the CF-3300-style FDC. openMSX's bundled C-BIOS (0.29)
    # is not that host: it predates the disk-host work (HIMEM, MS-BASIC's layout at the scan), so it is the
    # checkout's build that is measured.
    import importlib.util
    spec = importlib.util.spec_from_file_location("inst", os.path.join(ROOT, "tools", "install-openmsx-machine.py"))
    inst = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inst)
    disk_rom = os.path.join(ROOT, "build", "disk.rom")
    xml = open(os.path.join(BUNDLED, "C-BIOS_MSX1_EU.xml")).read()
    xml = re.sub(r"\s*<sha1>[0-9a-f]+</sha1>", "", xml)
    xml = re.sub(r"<filename>([^<]+)</filename>", lambda m: f"<filename>{os.path.join(dest, m.group(1))}</filename>", xml)
    xml = inst.expand_slot3(xml, disk_rom, "")
    name = f"CBIOS2_{tag.upper()}_MSX1_EU_NOBASIC_DISK"
    open(os.path.join(USER, name + ".xml"), "w").write(xml)
    return name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cbios")
    ap.add_argument("--pinned", action="store_true")
    ap.add_argument("--tag", default="CUR")
    a = ap.parse_args()
    if a.pinned:
        return install_pinned(a.tag)
    if not a.cbios:
        ap.error("--cbios <checkout> or --pinned")
    install(os.path.abspath(os.path.expanduser(a.cbios)), a.tag)
    return 0


if __name__ == "__main__":
    sys.exit(main())
