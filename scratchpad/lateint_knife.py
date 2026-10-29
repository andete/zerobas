#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Knives for D-LATEINT's gcdi-acceptance rows `raise` and `dimshift`: each cut
takes one `ei` out again, and must turn exactly its own row red on both zerobas
targets. The ROMs are hashed around every cut, and an unbuilt cut is refused.

  K-E  basic/interp.asm raise_error_hl's `ei`   -> `raise` (NODISK: the DISK
       target raises that OPEN on the disk path)
  K-V  sub/arrays.asm the new-scalar LDDR's `ei` -> `dimshift`
  K-Z  sub/arrays.asm DIM's zero-fill `ei`      -> `dimshift`
  K-X  sub/arrays.asm ERASE's LDIR `ei`         -> `dimshift`
"""
import hashlib, os, subprocess, sys, time
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))

KNIVES = [
    ("K-E", "basic/interp.asm",
     "raise_error_hl:\n                ei ", "raise_error_hl:\n                nop", "raise"),
    ("K-V", "sub/arrays.asm",
     "                ei\n                lddr\n                di\n",
     "                nop\n                lddr\n                di\n", "dimshift"),
    ("K-Z", "sub/arrays.asm",
     "                ei                          ; D-LATEINT: a big DIM's fill",
     "                nop                         ; D-LATEINT: a big DIM's fill", "dimshift"),
    ("K-X", "sub/arrays.asm",
     "                ei                          ; D-LATEINT: as scv's LDDR",
     "                nop                         ; D-LATEINT: as scv's LDDR", "dimshift"),
]
ROWS = ["raise", "dimshift"]
ZB = ["C-BIOS_MSX1_EU_REPACK_NODISK", "C-BIOS_MSX1_EU_REPACK_DISK"]


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
    # make compares mtimes to the SECOND here: a source written in the second this
    # build finished is not "newer", and the next build silently skips it (it hit
    # K-S on 2026-10-29). Let the clock tick before anything is written.
    time.sleep(1.1)


def gate():
    """the two rows, zerobas targets only (the VG-8020 run is the control)."""
    code = ("import sys, basic_probe_gcdi as g\n"
            f"g.ROWS = {{k: v for k, v in g.ROWS.items() if k in {ROWS!r}}}\n"
            "sys.exit(g.main())\n")
    r = subprocess.run([sys.executable, "-u", "-c", code], capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path[:2])))
    return [tuple(ln.split()[:2]) for ln in r.stdout.splitlines() if "DIVERGES" in ln]


build()
base = hashes()
hit = 0
for name, path, old, new, row in KNIVES:
    src = open(path).read()
    if src.count(old) != 1:
        sys.exit(f"{name}: anchor found {src.count(old)} times")
    open(path, "w").write(src.replace(old, new))
    try:
        build()
        cut = hashes()
        if cut == base:
            sys.exit(f"{name}: ROMs did not move ({cut}) -- refusing an inert knife")
        red = sorted(gate())
    finally:
        open(path, "w").write(src)
    # K-E: the DISK target raises `OPEN "NUL:"` on the disk path, not through p0cb
    want = sorted((row, m) for m in (ZB[:1] if name == "K-E" else ZB))
    ok = red == want
    hit += ok
    print(f"{name} ROMs {base} -> {cut}  red {red}  want {want}  {'HIT' if ok else 'MISS'}",
          flush=True)
build()
after = hashes()
print(f"restored ROMs {after} {'== clean' if after == base else '!= CLEAN'}")
print(f"{hit}/{len(KNIVES)} knives HIT")
sys.exit(0 if after == base and hit == len(KNIVES) else 1)
