#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC, docs/msx2/main/README.md VA-13: run a probe on the three MSX2 / MSX2+ rows with every machine
CONFIGURED with 64 KB of VRAM -- DIFFERENT machines from the references (no HB-F900, NMS 8250 or FS-A1WSX was sold
with 64 KB; the variant answers what these BIOSes do on a VDP whose VRAM has no A16).

    python3 tools/agent_wt.py NAME --fresh -- python3 -u scratchpad/xva13_run.py probes/bios/spec/xva13.asm

Only inside an isolated instance (tools/agent_wt.py: $OPENMSX_USER_DATA is the instance's own share): it writes
<machine>_VRAM64.xml into that share's machines/ -- each a copy of the reference's config (openMSX's bundled
machines/) or of C-BIOS's machine (the instance's machines/) with `<vram>128</vram>` -> `<vram>64</vram>`, nothing
else -- and refuses to write into ~/.openMSX. biosl_run.py has no option to name a machine, so this script imports
it and points its msx2eu / msx2jp / msx2p rows at the variants in-process (the file is not edited).
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
sys.path.insert(0, os.path.join(REPO, "probes", "bios"))
import openmsx_paths  # noqa: E402
import biosl_run  # noqa: E402

SUFFIX = "_VRAM64"


def variant(src_dir, name, dst_dir):
    text = open(os.path.join(src_dir, name + ".xml")).read()
    if text.count("<vram>128</vram>") != 1:
        sys.exit(f"xva13_run: {name}.xml has not exactly one <vram>128</vram>")
    out = os.path.join(dst_dir, name + SUFFIX + ".xml")
    with open(out, "w") as f:
        f.write(text.replace("<vram>128</vram>", "<vram>64</vram>"))
    return name + SUFFIX


def main():
    user = os.environ.get("OPENMSX_USER_DATA")
    if not user or os.path.realpath(user).startswith(os.path.realpath(os.path.expanduser("~/.openMSX"))):
        sys.exit("xva13_run: run inside an isolated instance (tools/agent_wt.py), never against ~/.openMSX")
    machines = os.path.join(user, "machines")
    system = os.path.join(openmsx_paths.find_share(), "machines")
    for row in ("msx2eu", "msx2jp", "msx2p"):
        ref, ours = biosl_run.ROWS[row]
        biosl_run.ROWS[row] = (variant(system, ref, machines), variant(machines, ours, machines))
        print(f"xva13_run: {row} -> {biosl_run.ROWS[row]}", flush=True)
    sys.argv = [biosl_run.__file__, sys.argv[1], "--row", "msx2all"]
    return biosl_run.main()


if __name__ == "__main__":
    sys.exit(main())
