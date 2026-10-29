#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Knives for puneglead-acceptance (D-PUNEGLEAD). Each cut is byte-neutral and
must turn both zerobas rows red. The ROMs are hashed around every cut, an unbuilt
cut is refused, and build() lets the clock tick (make's 1-second mtimes).

  K-Z  sub/punum.asm the `0` is never dropped (`jr nc` -> `jr`)
  K-S  basic/pu-render.inc `+.` is not a field (`cp '.'` -> `cp $FF`)
  K-L  basic/pu-render.inc a leading sign never makes the trailing one a
       literal (`bit 3,a` -> `bit 1,a`, the wrapped flag, clear here)
  K-D  sub/punum.asm `$$` has no integer column (`and $04` -> `and $00`)
"""
import hashlib, os, subprocess, sys, time
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)
KNIVES = [
    ("K-Z", "sub/punum.asm",
     "                jr      nc,pnt_lz_ok        ; it fits",
     "                jr      pnt_lz_ok           ; it fits"),
    ("K-S", "basic/pu-render.inc",
     "                cp      '.'                 ; D-PUNEGLEAD: `+.##`",
     "                cp      $FF                 ; D-PUNEGLEAD: `+.##`"),
    ("K-L", "basic/pu-render.inc",
     "                ld      a,(PU_FLAGS)\n                bit     3,a\n"
     "                jr      nz,ptf_num_fill",
     "                ld      a,(PU_FLAGS)\n                bit     1,a\n"
     "                jr      nz,ptf_num_fill"),
    ("K-D", "sub/punum.asm",
     "                ; VG-8020 -- although the scanner marked it D-PULEAD's way\n"
     "                ld      a,(PU_TYPE)\n                and     $04",
     "                ; VG-8020 -- although the scanner marked it D-PULEAD's way\n"
     "                ld      a,(PU_TYPE)\n                and     $00"),
]
ZB = sorted(["C-BIOS_MSX1_EU_REPACK_NODISK", "C-BIOS_MSX1_EU_REPACK_DISK"])


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
    time.sleep(1.1)


build()
base = hashes()
hit = 0
for name, path, old, new in KNIVES:
    src = open(path).read()
    if src.count(old) != 1:
        sys.exit(f"{name}: anchor found {src.count(old)} times")
    open(path, "w").write(src.replace(old, new))
    try:
        build()
        cut = hashes()
        if cut == base:
            sys.exit(f"{name}: ROMs did not move ({cut}) -- refusing an inert knife")
        r = subprocess.run([sys.executable, "-u", "probes/basic/basic_probe_puneglead.py"],
                           capture_output=True, text=True)
    finally:
        open(path, "w").write(src)
    red = sorted(ln.split()[0] for ln in r.stdout.splitlines() if "DIVERGES" in ln)
    ok = red == ZB
    hit += ok
    print(f"{name} ROMs {base} -> {cut}  red {red}  {'HIT' if ok else 'MISS'}", flush=True)
    for ln in r.stdout.splitlines():
        if ln.startswith("      ref"):
            print("   " + ln.strip())
build()
after = hashes()
print(f"restored ROMs {after} {'== clean' if after == base else '!= CLEAN'}")
print(f"{hit}/{len(KNIVES)} knives HIT")
sys.exit(0 if after == base and hit == len(KNIVES) else 1)
