#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-TAPELOAD RUNS? triage (Joost 2026-10-28: "yes, triage the RUNS? tapes after the
deferred work"). tapecorpus_run.py calls a title RUNS? when both machines run it and
the last screens are far apart. Timing or a real difference? Per title, both machines
are captured every 2 emulated seconds from T400 to T420 (VRAM, VDP registers, PC,
CURLIN -- the same black-box capture as the runner), and three numbers are printed:

  per-table bytes apart at T420 -- the VDP's own tables, at the bases its registers
      give (names, patterns, colours, sprite attributes, sprite patterns)
  best   -- the fewest bytes apart over EVERY ref frame x zb frame of the window: a
            phase / timing difference shows up as a small best
  always -- bytes that differ in EVERY frame pair: a real, persistent difference

The software is RUN, never decoded. TAPECORPUS_DIR names the collection; never written
here. Titles: the RUNS? rows of the last run (the list below), or --only SUBSTR.
    TAPECORPUS_DIR=... python3 -u scratchpad/runsq_triage.py [--only SUBSTR]
"""
import os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tapecorpus_run as T  # noqa: E402

TITLES = ["BMX Simulator", "Ballblazer", "Blagger", "Blocker", "Blow Up", "Buzz Off",
          "Chuckie Egg", "Demonia", "Elite", "Fruit Panic", "Jump Jet", "Lazer Bykes",
          "Lazy Jones", "Manic Miner", "Navy Moves", "Ninja 2", "Punch & Judy",
          "Shark Hunter", "Sorcery", "Space", "Space Shuttle"]
TIMES = [float(t) for t in range(400, 421, 2)]
if "--late" in sys.argv:                 # a later window (Shark Hunter, 2026-10-28)
    TIMES = [float(t) for t in range(440, 481, 4)]


def tables(regs, mode):
    r = regs
    name = (r[2] & 0x0F) << 10
    sattr = (r[5] & 0x7F) << 7
    spat = (r[6] & 0x07) << 11
    if mode == "S2":
        col, pat = ((r[3] & 0x80) << 6, 0x1800), ((r[4] & 0x04) << 11, 0x1800)
        nlen = 0x300
    elif mode == "S1":
        col, pat, nlen = (r[3] << 6, 32), ((r[4] & 0x07) << 11, 0x800), 0x300
    else:                                   # S0 / S3: names + patterns only
        col, pat, nlen = (0, 0), ((r[4] & 0x07) << 11, 0x800), 960
    return {"names": (name, nlen), "patterns": pat, "colours": col,
            "sattr": (sattr, 128), "spat": (spat, 2048)}


def apart(a, b, lo=0, n=16384):
    return sum(1 for x, y in zip(a[lo:lo + n], b[lo:lo + n]) if x != y)


def main():
    only = sys.argv[sys.argv.index("--only") + 1].lower() if "--only" in sys.argv else ""
    d = os.environ["TAPECORPUS_DIR"]
    for t in [x for x in TITLES if only in x.lower()]:
        td = tempfile.mkdtemp(prefix="runsq_")
        try:
            cas = T.unpack(os.path.join(d, t + ".zip"), td)
            ref = T.run_one(T.REF, cas, TIMES)
            zb = T.run_one(T.ZB, cas, TIMES)
        finally:
            shutil.rmtree(td, ignore_errors=True)
        last = f"T{int(TIMES[-1])}"  # the window's last capture
        if not ref or not zb or last not in ref or last not in zb:
            print(f"{t:14s} NO READING", flush=True)
            continue
        r, z = ref[last], zb[last]
        mode = T.D.mode_of(r["regs"])
        per = {k: apart(r["vram"], z["vram"], lo, n) for k, (lo, n) in tables(r["regs"], mode).items()}
        rv = [ref[k]["vram"] for k in ref]
        zv = [zb[k]["vram"] for k in zb]
        best = min(apart(a, b) for a in rv for b in zv)
        always = sum(1 for i in range(16384)
                     if all(a[i] != b[i] for a in rv for b in zv))
        rmove = max(apart(rv[0], a) for a in rv)
        print(f"{t:14s} {mode} ref L{r['curlin']} zb L{z['curlin']}  {last} "
              + " ".join(f"{k}={v}" for k, v in per.items())
              + f"  best={best} always={always} ref-moves={rmove}", flush=True)


if __name__ == "__main__":
    main()
