#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Knife for pustardol-acceptance (D-PUSTARDOL): the `$` after `**` is never
recognised (its compare becomes `cp $FF`), so `**$` falls back to a literal `$`
before the field. Both zerobas rows must go red. The ROMs are hashed around the
cut, and an unbuilt cut is refused.
"""
import hashlib, os, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)
PATH = "basic/pu-render.inc"
OLD = "                ld      a,(hl)\n                cp      '$'\n                jr      nz,ptf_star_go"
NEW = "                ld      a,(hl)\n                cp      $FF                 ; KNIFE\n                jr      nz,ptf_star_go"


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
src = open(PATH).read()
if src.count(OLD) != 1:
    sys.exit("anchor not found exactly once")
open(PATH, "w").write(src.replace(OLD, NEW))
try:
    build()
    cut = hashes()
    if cut == base:   # the build did not happen: an inert knife must not pass
        sys.exit(f"ROMs did not move ({cut}) -- refusing an inert knife")
    r = subprocess.run([sys.executable, "-u", "probes/basic/basic_probe_pustardol.py"],
                       capture_output=True, text=True)
finally:
    open(PATH, "w").write(src)
red = [ln.split()[0] for ln in r.stdout.splitlines() if "DIVERGES" in ln]
want = ["C-BIOS_MSX1_EU_REPACK_NODISK", "C-BIOS_MSX1_EU_REPACK_DISK"]
print(f"K-D ROMs {base} -> {cut}  rc={r.returncode}  red {red}  "
      f"{'HIT' if red == want else 'MISS'}")
build()
after = hashes()
print(f"restored ROMs {after} {'== clean' if after == base else '!= CLEAN'}")
if after != base:
    sys.exit("restore did not reproduce the clean ROMs")
