#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Knives for resnextend-acceptance (D-RESNEXTDIRECT). Each cut is byte-neutral
and must turn both zerobas rows red. The ROMs are hashed around every cut, an
unbuilt cut is refused, and build() lets the clock tick (make's 1-second mtimes).

  K-C  sub/errtrap.asm the erroring line is not restored (`ld (CURLINE),hl` ->
       three `nop`s): the run loop steps on from the HANDLER's line
  K-L  sub/errtrap.asm an end-of-line resumes one byte PAST the line's $00
       (sse_eol's label above the `inc hl`): the old shape, a resume point
       outside the line
"""
import hashlib, os, subprocess, sys, time
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)
KNIVES = [
    ("K-C", "sub/errtrap.asm", "resnextend",
     "                ld      (CURLINE),hl        ; restore the erroring line (the run loop\n",
     "                nop\n                nop\n                nop                 ; restore the erroring line (the run loop\n"),
    ("K-L", "sub/errtrap.asm", "resnextend",
     "sse_colon:\n                inc     hl                  ; HL -> the next statement (same line)\nsse_eol:",
     "sse_colon:\nsse_eol:\n                inc     hl                  ; HL -> the next statement (same line)\n"),
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
for name, path, gate, old, new in KNIVES:
    src = open(path).read()
    if src.count(old) != 1:
        sys.exit(f"{name}: anchor found {src.count(old)} times")
    open(path, "w").write(src.replace(old, new))
    try:
        build()
        cut = hashes()
        if cut == base:
            sys.exit(f"{name}: ROMs did not move ({cut}) -- refusing an inert knife")
        r = subprocess.run([sys.executable, "-u", f"probes/basic/basic_probe_{gate}.py"],
                           capture_output=True, text=True)
    finally:
        open(path, "w").write(src)
    red = sorted(ln.split()[0] for ln in r.stdout.splitlines() if "DIVERGES" in ln)
    ok = set(red) == set(ZB)          # two programs: a machine can be red twice
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
