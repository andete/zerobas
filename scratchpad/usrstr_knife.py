#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Knife for usrstr-acceptance (D-USRSTR). The cut is byte-neutral and must turn
both zerobas rows red. The ROMs are hashed around it, an unbuilt cut is refused,
and build() lets the clock tick (make's 1-second mtimes).

  K-U  basic/usr.asm the string probe is never taken (`jr nc,evu_num` ->
       `jr evu_num`): a string argument goes the numeric way, Type mismatch
"""
import hashlib, os, subprocess, sys, time
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)
KNIVES = [
    ("K-U", "basic/usr.asm",
     "                jr      nc,evu_num\n                push    hl\n",
     "                jr      evu_num\n                push    hl\n"),
]
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
        r = subprocess.run([sys.executable, "-u", "probes/basic/basic_probe_usrstr.py"],
                           capture_output=True, text=True)
    finally:
        open(path, "w").write(src)
    red = sorted(ln.split()[0] for ln in r.stdout.splitlines() if "DIVERGES" in ln)
    ok = red == sorted(ZB)
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
