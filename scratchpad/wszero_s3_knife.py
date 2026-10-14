#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO slice 3 knife: does wszero-acceptance SEE the run-loop block's move?

K-WS4  tools/ws_shift.py --move F6E8 F71C -AC2 --apply: PRGEND .. SL_CEIL back at
       $EC26-$EC59. Predicted: `loop` and `w2` DIVERGE.
Every source file under basic/ sub/ disk/ is snapshot first and restored after;
built through knife_guard (ROM must MOVE); then a CLEAN build and the rows re-run.
"""
import glob, os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "wszero_s3_knife")
ROWS = ["loop", "w2"]


def suite(tag):
    log = f"{TMP}/{tag}.log"
    with open(log, "w") as fh:
        subprocess.call([sys.executable, "-u", "probes/basic/basic_probe_wszero.py", *ROWS],
                        stdout=fh, stderr=subprocess.STDOUT, timeout=3600)
    return [ln.split()[1] for ln in open(log) if ln.startswith("ROW") and "DIVERGES" in ln]


def main():
    os.makedirs(TMP, exist_ok=True)
    files = [f for d in ("basic", "sub", "disk") for f in glob.glob(f"{d}/**/*", recursive=True)
             if f.endswith((".asm", ".inc"))]
    snap = {f: open(f).read() for f in files}
    before = knife_guard.hashes()
    try:
        rc = subprocess.call([sys.executable, "tools/ws_shift.py", "--move", "F6E8", "F71C", "-AC2",
                              "--apply"], stdout=open(f"{TMP}/shift.log", "w"), stderr=subprocess.STDOUT)
        if rc:
            print(f"K-WS4: ws_shift refused (rc={rc}) -- NOT SCORED")
        else:
            moved, _, brc = knife_guard.build(f"{TMP}/mk.log", before)
            if brc or not moved:
                print(f"K-WS4: build rc={brc} ROM moved={moved} -- NOT SCORED")
            else:
                subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                red = suite("K-WS4")
                print(f"K-WS4: diverging {red}; predicted {ROWS} -> "
                      f"{'HIT' if sorted(red) == sorted(ROWS) else 'MISS'}", flush=True)
    finally:
        for f, txt in snap.items():
            if open(f).read() != txt:
                open(f, "w").write(txt)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    red = suite("restore")
    print(f"restored: build rc={brc}; {'DIVERGE ' + str(red) if red else 'loop/w2 SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
