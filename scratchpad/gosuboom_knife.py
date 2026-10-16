#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-GOSUBOOM knife: do probes/basic/basic_probe_gosuboom.py's rows see each half?

K-GO1 CTL_FRAME_MARGIN back at 768 (the pool reset kept) -> `edge` DIVERGES, alone
K-GO2 gosub_stk_over without the pool reset (the margin kept at 256) -> `ret` and
      `for` DIVERGE (the frames stand: the handler's RETURN / NEXT find them)
Page 1 / sysvars only: no pinned segment changes size (gosub_stk_over is past the
last pin); each cut must still prove it BUILT.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "gosuboom_knife")
KNIVES = [
    ("K-GO1", "basic/sysvars.inc", [("CTL_FRAME_MARGIN equ   256", "CTL_FRAME_MARGIN equ   768")],
     ["edge"]),
    ("K-GO2", "basic/program.asm",
     [("                call    ctl_reset\n                xor     a\n"
       "                ld      (TRAPSVC),a         ; no trap in service: its record went too\n",
       "")],
     ["ret", "for"]),
]


def cut(text, edits):
    for old, new in edits:
        if text.count(old) != 1:
            raise SystemExit(f"anchor x{text.count(old)}: {old[:50]!r}")
        text = text.replace(old, new)
    return text


def rows(tag):
    log = f"{TMP}/{tag}.log"
    with open(log, "w") as fh:
        subprocess.call([sys.executable, "-u", "probes/basic/basic_probe_gosuboom.py"],
                        stdout=fh, stderr=subprocess.STDOUT, timeout=3600)
    return [ln.split()[1] for ln in open(log) if ln.startswith("ROW") and "DIVERGES" in ln]


def main():
    os.makedirs(TMP, exist_ok=True)
    saved = {f: open(f).read() for _t, f, _e, _p in KNIVES}
    for _t, f, edits, _p in KNIVES:
        cut(saved[f], edits)
    for tag, f, edits, pred in KNIVES:
        before = knife_guard.hashes()
        try:
            open(f, "w").write(cut(saved[f], edits))
            moved, _, brc = knife_guard.build(f"{TMP}/mk_{tag}.log", before)
            pins = subprocess.call(["make", "pin-check"], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
            if brc or not moved or pins:
                print(f"{tag}: build rc={brc} ROM moved={moved} pin-check rc={pins} -- NOT SCORED",
                      flush=True)
                continue
            subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
            red = rows(tag)
            print(f"{tag}: diverging {red}; predicted {pred} -> "
                  f"{'HIT' if sorted(red) == sorted(pred) else 'MISS'}", flush=True)
        finally:
            for p, t in saved.items():
                open(p, "w").write(t)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    red = rows("restore")
    print(f"restored: build rc={brc}; {'DIVERGE ' + str(red) if red else 'SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
