#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""C-BIOS integration step 2 (Joost 2026-11-27): disk.rom builds STANDALONE, from its own sources and the
COMMITTED resident-ABI include, with no main-ROM build.

    disk_standalone_check.py <reference disk.rom> <source> ...

Copies exactly the listed sources (the Makefile passes $(DISK_SRC) $(DISK_PARTS) disk/basic-resident-abi.inc)
into an EMPTY directory -- no build/, no main-ROM symbols, no make -- assembles there with pasmo as the Makefile
does (`pasmo -I disk --bin disk/disk.asm`), checks the 16 KB size, and compares the image with the reference
(build/disk.rom from the normal build). Refuses:

  * a missing include  -> pasmo fails inside the empty directory: the source list is not complete;
  * a different image  -> the standalone image is not the one the battery tested;
  * a dirty ABI include -> disk/basic-resident-abi.inc untracked, or modified and not staged (the port
                          takes the COMMITTED one; gate_wt gates a commit, where the index is HEAD).

The shared FAT / SAVE bodies in basic/*.inc are SOURCES of disk.rom (D-FATENG Option 2: one engine, two ROMs), not
main-ROM build products; a port carries them with disk/.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import probe_tmp  # noqa: E402,F401 -- sets tempfile.tempdir under the temp root
ABI = "disk/basic-resident-abi.inc"
SIZE = 16384


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    ref, srcs = argv[1], argv[2:]
    if ABI not in srcs:
        print(f"diskstandalone: REFUSED -- {ABI} is not in the source list")
        return 2
    # the COMMITTED include: tracked, and the working copy equal to the index (staged-before-the-gate is the
    # workflow; gate_wt gates a commit, where index == HEAD)
    tracked = subprocess.run(["git", "-C", REPO, "ls-files", "--error-unmatch", ABI],
                             capture_output=True).returncode == 0
    dirty = subprocess.run(["git", "-C", REPO, "diff", "--quiet", "--", ABI]).returncode
    if not tracked or dirty:
        print(f"diskstandalone: RED -- {ABI} is {'untracked' if not tracked else 'modified and not staged'}; "
              f"the port takes the committed include")
        return 1
    pasmo = os.environ.get("PASMO", "pasmo")
    td = tempfile.mkdtemp(prefix="zb_diskalone_")
    try:
        for s in srcs:
            os.makedirs(os.path.join(td, os.path.dirname(s)), exist_ok=True)
            shutil.copyfile(os.path.join(REPO, s), os.path.join(td, s))
        out = os.path.join(td, "disk.rom")
        r = subprocess.run([pasmo, "-I", "disk", "--bin", "disk/disk.asm", out], cwd=td,
                           capture_output=True, text=True)
        if r.returncode != 0 or not os.path.isfile(out):
            print(f"diskstandalone: RED -- pasmo failed in an empty directory holding only {len(srcs)} sources "
                  f"(a dependency is missing from the list):\n{(r.stdout + r.stderr).strip()[-800:]}")
            return 1
        img = open(out, "rb").read()
        want = open(os.path.join(REPO, ref), "rb").read()
        h, hw = hashlib.sha1(img).hexdigest(), hashlib.sha1(want).hexdigest()
        if len(img) != SIZE:
            print(f"diskstandalone: RED -- standalone image is {len(img)} B, not {SIZE}")
            return 1
        if img != want:
            print(f"diskstandalone: RED -- standalone sha1 {h} != {ref} sha1 {hw}")
            return 1
        print(f"diskstandalone: GREEN -- {len(srcs)} sources in an empty directory, no main-ROM build -> "
              f"{SIZE} B, sha1 {h} == {ref}")
        return 0
    finally:
        shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
