#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Knife for gcdi-acceptance (D-GCDI): remove ONE of the two `ei`s, rebuild,
run the gate, restore, rebuild. Each cut must turn its own row red; sub.rom is
hashed around every plant so an inert (unbuilt) knife cannot pass for a blind
gate.

  K-S  strheap_engine's ei (sub/strheap.asm)  -> the `scalar` row red
  K-A  aeng_copy_str's ei (sub/arrays.asm)       -> the `array` row red
"""
import hashlib, os, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)
KNIVES = [
    ("K-S", "sub/strheap.asm", "                ei\n                call    she_dispatch",
     "                call    she_dispatch", "scalar"),
    ("K-A", "sub/arrays.asm", "aeng_copy_str:\n                ei                          ; D-GCDI",
     "aeng_copy_str:\n                                            ; D-GCDI", "array"),
]


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
after = hashes()
print(f"restored sub.rom {after} {'== clean' if after == base else '!= CLEAN'}")
if after != base:
    sys.exit("restore did not reproduce the clean sub.rom")
