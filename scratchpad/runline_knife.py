#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-RUNLINE2 knife — can `runline-acceptance` actually see the defect it gates?

The rows were GREEN the day they were written, because D-RUNARG had already
fixed the defect. A gate whose rows have never been red is exactly the shape
this tree keeps finding: it would report `5/5 PASS` just as happily if it had
gone blind [[a-knife-can-be-inert-because-the-build-did-not-happen]].

K-RL1 restores the pre-D-RUNARG behaviour at its source: `dl_bare` decides
whether the REPL keyword is followed by an ARGUMENT, and returning CF set
unconditionally puts every form back on the bare fast path, where the argument
is discarded and the program runs from the TOP.

\U0001f3af THE PREDICTION IS ASYMMETRIC, WHICH IS WHAT MAKES IT EVIDENCE:

    r.20 r.30 r.colon   MOVE     -- their line number is discarded -> `ABC`
    r.ctl               HOLDS    -- already runs from the top; nothing to lose
    r.nospace           HOLDS    -- `RUN20` never matches `is_cmd`, so `dl_bare`
                                    is never reached and the cut cannot touch it

If `r.nospace` moved too, the cut would be breaking something wider than the
fast path and the red would prove nothing; if `r.ctl` moved, the fixture broke.
"""
import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp                                                  # noqa: E402,F401

SRC = os.path.join(ROOT, "basic", "program.asm")
ROMS = ("build/zerobas-main-eu.rom", "build/sub.rom")
FIND = "dl_bare:\n                push    hl"
REPL = "dl_bare:\n                scf\n                ret\n                push    hl"
WANT_MOVED = {"r.20", "r.30", "r.colon"}
WANT_HELD = {"r.ctl", "r.nospace"}


def sh(cmd, out):
    with open(out, "w") as f:
        return subprocess.call(cmd, shell=True, cwd=ROOT, stdout=f,
                               stderr=subprocess.STDOUT)


def rom_hash():
    h = hashlib.sha1()
    for r in ROMS:
        p = os.path.join(ROOT, r)
        h.update(open(p, "rb").read() if os.path.exists(p) else b"ABSENT")
    return h.hexdigest()[:12]


def rows(path):
    """{row: zb value} from the gate's own table; None if it printed no table."""
    out = {}
    for line in open(path, errors="replace"):
        parts = line.split()
        for i, tok in enumerate(parts):
            if tok.startswith("r.") and any(p.startswith("zb=") for p in parts):
                zb = next(p for p in parts if p.startswith("zb="))
                out[tok] = zb[3:]
                break
    return out or None


def main() -> int:
    sh("make repack-machine", probe_tmp.tmp("rl_base_build.out"))
    base_hash = rom_hash()
    sh("caffeinate -i -s python3 probes/basic/basic_probe_runline.py",
       probe_tmp.tmp("rl_base.out"))
    base = rows(probe_tmp.tmp("rl_base.out"))
    if not base or set(base) != WANT_MOVED | WANT_HELD:
        print(f"\U0001f534 BASE TABLE UNREADABLE OR INCOMPLETE ({base}) -- "
              f"refusing to score the arm.")
        return 2
    print(f"base ROMs {base_hash}  {base}")

    orig = open(SRC, errors="replace").read()
    if FIND not in orig:
        print(f"\U0001f534 PLANT SITE NOT FOUND in {SRC} -- arm skipped, NOT green")
        return 2
    try:
        open(SRC, "w").write(orig.replace(FIND, REPL, 1))
        rc = sh("make repack-machine", probe_tmp.tmp("rl_k_build.out"))
        h = rom_hash()
        if rc != 0 or h == base_hash:
            print(f"K-RL1: INERT -- rc={rc} roms={h}; DISCARDED")
            return 2
        sh("caffeinate -i -s python3 probes/basic/basic_probe_runline.py",
           probe_tmp.tmp("rl_k.out"))
        got = rows(probe_tmp.tmp("rl_k.out")) or {}
        moved = {k for k in base if got.get(k) != base[k]}
    finally:
        open(SRC, "w").write(orig)
        sh("make repack-machine", probe_tmp.tmp("rl_restore.out"))

    ok = moved == WANT_MOVED
    print(f"K-RL1: roms={h}  moved={sorted(moved) or '<none>'}\n"
          f"       want={sorted(WANT_MOVED)}  held={sorted(WANT_HELD)}  "
          f"{'PASS' if ok else 'FAIL'}")
    if not ok:
        print(f"       unexpected={sorted(moved - WANT_MOVED)}  "
              f"missed={sorted(WANT_MOVED - moved)}")
    print(f"restored {rom_hash()} (base {base_hash}) "
          f"{'OK' if rom_hash() == base_hash else '*** MISMATCH ***'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
