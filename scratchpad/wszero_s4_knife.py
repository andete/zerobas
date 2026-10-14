#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO slice 4 knife: does wszero-acceptance SEE FPERR's and the slot cells' moves?

K-WS5  basic/sysvars.inc + sub/equates.inc: FPERR back at $F069; SUBSLOT / SUBSLOT_OK
       / SUBSLOT2 back at $F106 / $F107 / $F14B; SUB_PING back at $F105.
       Predicted: `fperr`, `slot` and `all` DIVERGE.
Built through knife_guard (ROM must MOVE), restored, rebuilt CLEAN, re-run green.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "wszero_s4_knife")
CUTS = [
    ("K-WS5a", "basic/sysvars.inc", "FPERR           equ     $F7B9", "FPERR           equ     $F069", None),
    ("K-WS5b", "basic/sysvars.inc", "SUBSLOT         equ     $FD09", "SUBSLOT         equ     $F106", None),
    ("K-WS5c", "basic/sysvars.inc", "SUBSLOT_OK      equ     $FD0A", "SUBSLOT_OK      equ     $F107", None),
    ("K-WS5d", "basic/sysvars.inc", "SUBSLOT2        equ     $FD0B", "SUBSLOT2        equ     $F14B", None),
]
GROUPS = [("K-WS5", ["K-WS5a", "K-WS5b", "K-WS5c", "K-WS5d"], ["fperr", "slot", "all"], ["fperr", "slot", "all"])]


def suite(tag, rows):
    log = f"{TMP}/{tag}.log"
    with open(log, "w") as fh:
        rc = subprocess.call([sys.executable, "-u", "probes/basic/basic_probe_wszero.py", *rows],
                             stdout=fh, stderr=subprocess.STDOUT, timeout=3600)
    red = [ln.split()[1] for ln in open(log) if ln.startswith("ROW") and "DIVERGES" in ln]
    return rc, red


def main():
    os.makedirs(TMP, exist_ok=True)
    by = {c[0]: c for c in CUTS}
    for _t, src, old, new, _p in CUTS:
        if open(src).read().count(old) != 1:
            print(f"{_t}: REFUSED, anchor count {open(src).read().count(old)}", flush=True)
            return 2
    for tag, members, pred, rows in GROUPS:
        src = by[members[0]][1]
        text = open(src).read()
        cut = text
        for m in members:
            cut = cut.replace(by[m][2], by[m][3])
        before = knife_guard.hashes()
        try:
            open(src, "w").write(cut)
            moved, _, brc = knife_guard.build(f"{TMP}/mk_{tag}.log", before)
            if brc or not moved:
                print(f"{tag}: build rc={brc} ROM moved={moved} -- NOT SCORED", flush=True)
                continue
            subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            rc, red = suite(tag, rows)
            print(f"{tag}: rows {rows} diverging {red}; predicted {pred} -> "
                  f"{'HIT' if sorted(red) == sorted(pred) else 'MISS'}", flush=True)
        finally:
            open(src, "w").write(text)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rc, red = suite("restore", ["fperr", "slot", "all"])
    print(f"restored: build rc={brc}; trap {'DIVERGE ' + str(red) if red else 'SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
