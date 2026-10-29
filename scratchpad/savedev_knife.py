#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Knife for savedev-acceptance (D-SAVEDEV): disarm ONE device arm at a time
(its `jp z` becomes three NOPs, so the name falls through to the old path) and
check that exactly that device's two rows go red. The ROMs are hashed around
every cut, and an unbuilt cut is refused.
"""
import hashlib, os, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)
PATH = "sub2/loadsave.asm"
KNIVES = [("K-L", "jp      z,lsv_lpt", '"LPT:"'), ("K-C", "jp      z,lsv_crt", '"CRT:"'),
          ("K-G", "jp      z,lsv_grp", '"GRP:"')]


def hashes():
    h = hashlib.sha256()
    for f in sorted(os.listdir("build")):
        if f.endswith(".rom"):
            h.update(open(os.path.join("build", f), "rb").read())
    return h.hexdigest()[:8]


def build():
    r = subprocess.run(["make", "repack-machine"], capture_output=True, text=True)
    if r.returncode:
        sys.exit("build failed:\n" + r.stdout[-2000:] + r.stderr[-2000:])


build()
base = hashes()
for tag, old, dev in KNIVES:
    src = open(PATH).read()
    if src.count(old) != 1:
        sys.exit(f"{tag}: anchor not found exactly once")
    open(PATH, "w").write(src.replace(old, "nop\n                nop\n                nop ; KNIFE"))
    try:
        build()
        cut = hashes()
        if cut == base:   # the build did not happen: an inert knife must not pass
            sys.exit(f"{tag}: ROMs did not move -- refusing an inert knife")
        r = subprocess.run([sys.executable, "-u", "probes/basic/basic_probe_savedev.py"],
                           capture_output=True, text=True)
    finally:
        open(PATH, "w").write(src)
    red = [ln.split()[1] for ln in r.stdout.splitlines() if "DIVERGES" in ln]
    ok = red == [dev, dev]
    print(f"{tag} ROMs {cut}  rc={r.returncode}  red {red}  want [{dev}, {dev}]  "
          f"{'HIT' if ok else 'MISS'}")
build()
after = hashes()
print(f"restored ROMs {after} {'== clean' if after == base else '!= CLEAN'}")
if after != base:
    sys.exit("restore did not reproduce the clean ROMs")
