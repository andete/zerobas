#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Knife for gcdi-acceptance (D-GCDI): remove ONE of the two `ei`s, rebuild,
run the gate, restore, rebuild. Each cut must turn its own row red; sub.rom is
hashed around every plant so an inert (unbuilt) knife cannot pass for a blind
gate.

  K-S  strheap_engine's ei (sub/strheap.asm)  -> the `scalar` row red
  K-A  aeng_copy_str's ei (sub/arrays.asm)       -> the `array` row red
  K-R  readdata_tenant's ei (sub/readdata.asm)  -> the `read` row red
  K-M  math_wrap's ei (sub/mathwrap.asm)        -> the `math` row red
  K-H  htimi_guard skips again (basic/subromcall.asm) -> play-trace di_safety red
"""
import hashlib, os, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)
KNIVES = [
    ("K-S", "sub/strheap.asm", "                ei\n                call    she_dispatch",
     "                call    she_dispatch", "scalar"),
    ("K-A", "sub/arrays.asm", "aeng_copy_str:\n                ei                          ; D-GCDI",
     "aeng_copy_str:\n                                            ; D-GCDI", "array"),
    ("K-R", "sub/readdata.asm", "readdata_tenant:\n                ei                          ; D-GCDI3",
     "readdata_tenant:\n                                            ; D-GCDI3", "read"),
    ("K-M", "sub/mathwrap.asm", "math_wrap:\n                ei                          ; D-GCDI2",
     "math_wrap:\n                                            ; D-GCDI2", "math"),
]
# K-H: htimi_guard back to SKIPPING the frame while a page-1 tenant owns page 1.
# Its witness is play-trace-acceptance (di_safety: PLAY starves in a SIN loop).
KH = ("basic/subromcall.asm",
      "htg_skip:\n                ; D-GCDI2 (2026-10-29): SERVE the frame",
      "htg_skip:\n                pop     af\n                ret\n                ; D-GCDI2 (2026-10-29): SERVE the frame")


def hashes():
    return hashlib.sha256(open("build/sub.rom", "rb").read()).hexdigest()[:8]


def build():
    r = subprocess.run(["make", "repack-machine"], capture_output=True, text=True)
    if r.returncode:
        sys.exit("build failed:\n" + r.stdout[-2000:] + r.stderr[-2000:])


build()
base = hashes()
print(f"sub.rom {base} (clean)")
for tag, path, old, new, row in KNIVES:
    src = open(path).read()
    if src.count(old) != 1:
        sys.exit(f"{tag}: anchor not found exactly once in {path}")
    open(path, "w").write(src.replace(old, new))
    try:
        build()
        cut = hashes()
        if cut == base:   # the build did not happen: an inert knife must not pass
            open(path, "w").write(src)
            sys.exit(f"{tag}: sub.rom did not move ({cut}) -- refusing an inert knife")
        r = subprocess.run([sys.executable, "-u", "probes/basic/basic_probe_gcdi.py"],
                           capture_output=True, text=True)
    finally:
        open(path, "w").write(src)
    red = [ln for ln in r.stdout.splitlines() if ln.startswith(row) and "DIVERGES" in ln]
    other = [ln for ln in r.stdout.splitlines() if "DIVERGES" in ln and not ln.startswith(row)]
    print(f"{tag} sub.rom {cut} {'(CHANGED)' if cut != base else '(UNCHANGED: INERT)'}  "
          f"rc={r.returncode}  {row} red on {len(red)}/2 zerobas rows, other rows red {len(other)}")
    for ln in red + other:
        print("   " + ln)
build()
# K-H, against the PLAY trace gate; the main ROM is what moves
def mhash():   # every built image: whichever one carries the low region moves
    h = hashlib.sha256()
    for f in sorted(os.listdir("build")):
        if f.endswith(".rom"):
            h.update(open(os.path.join("build", f), "rb").read())
    return h.hexdigest()[:8]
mbase = mhash()
path, old, new = KH
src = open(path).read()
if src.count(old) != 1:
    sys.exit("K-H: anchor not found exactly once")
open(path, "w").write(src.replace(old, new))
try:
    build()
    mcut = mhash()
    if mcut == mbase:   # the build did not happen: an inert knife must not pass
        open(path, "w").write(src)
        sys.exit(f"K-H: main ROM did not move ({mcut}) -- refusing an inert knife")
    r = subprocess.run([sys.executable, "-u", "probes/basic/basic_probe_playtrace.py"],
                       capture_output=True, text=True)
finally:
    open(path, "w").write(src)
red = [ln for ln in r.stdout.splitlines() if "FAIL" in ln and "di_safety" in ln]
print(f"K-H main {mcut} (CHANGED)  rc={r.returncode}  di_safety red: {len(red)}")
for ln in red:
    print("   " + ln)
build()
if mhash() != mbase:
    sys.exit("restore did not reproduce the clean main ROM")
after = hashes()
print(f"restored sub.rom {after} {'== clean' if after == base else '!= CLEAN'}")
if after != base:
    sys.exit("restore did not reproduce the clean sub.rom")
