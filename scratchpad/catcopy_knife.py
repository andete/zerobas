#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Knife for catcopy-acceptance (D-CATCOPY). Each cut is built, the ROMs hashed
around the plant (an unbuilt cut is refused), the gate run, the source restored.

  K-1  INSTR back to str_snapshot_to_temp (always copy) -> `temp` AND `var` red
  K-2  str_snapshot_ro without its scalar keep (copies a variable again)
                                                        -> `var` red, `temp` green
"""
import hashlib, os, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)
KNIVES = [
    ("K-1", [("basic/str-engine.asm", "call    str_snapshot_ro     ; HL = aT",
              "call    str_snapshot_to_temp ; HL = aT"),
             ("basic/str-engine.asm", "call    str_snapshot_ro     ; HL = bT",
              "call    str_snapshot_to_temp ; HL = bT")], {"temp", "var"}),
    ("K-2", [("basic/files.asm", "                ld      hl,(STRPTR)         ; a scalar: use it where it is\n                ret",
              "                jp      str_snapshot_arg    ; KNIFE: no scalar keep")], {"var"}),
]


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
print(f"ROMs {base} (clean)")
for tag, cuts, want in KNIVES:
    saved = {}
    for path, old, new in cuts:
        src = saved.get(path) or open(path).read()
        saved.setdefault(path, src)
        cur = open(path).read()
        if cur.count(old) != 1:
            for p, s in saved.items():
                open(p, "w").write(s)
            sys.exit(f"{tag}: anchor not found exactly once in {path}")
        open(path, "w").write(cur.replace(old, new))
    try:
        build()
        cut = hashes()
        if cut == base:   # the build did not happen: an inert knife must not pass
            sys.exit(f"{tag}: ROMs did not move ({cut}) -- refusing an inert knife")
        r = subprocess.run([sys.executable, "-u", "probes/basic/basic_probe_catcopy.py"],
                           capture_output=True, text=True)
    finally:
        for p, s in saved.items():
            open(p, "w").write(s)
    red = {ln.split()[0] for ln in r.stdout.splitlines() if "DIVERGES" in ln}
    print(f"{tag} ROMs {cut} (CHANGED)  rc={r.returncode}  red rows {sorted(red)}  "
          f"want {sorted(want)}  {'HIT' if red == want else 'MISS'}")
build()
after = hashes()
print(f"restored ROMs {after} {'== clean' if after == base else '!= CLEAN'}")
if after != base:
    sys.exit("restore did not reproduce the clean ROMs")
