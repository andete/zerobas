#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO S10 knife: does wszero-acceptance SEE each S10 move out of the window?

One cell group back at its pre-S10 home per knife (the rest left in PARM1):
K-WS14 FCH_MODES $EE3D        -> `chan` DIVERGES ([E 52 20] for [C])
K-WS15 FCH_ACTIVE $EEBE       -> BLIND, predicted honestly: on the diskless
       machine only chan_gate / fch_select read it, and the tenant they reach
       writes nothing unless FCH_MODES[$A5] is 4
K-WS16 CSR_ADDR/CHAR/ON       -> `input` DIVERGES (VPEEK 165)
K-WS18 DIRECTF $EFC1          -> `midline` DIVERGES, `abort` SAME
K-WS19 ERRRESUME $EFC4        -> `resume` DIVERGES, `onerr` SAME
K-WS20 CONTVALID $EF41        -> `contdir` DIVERGES
K-WS21 PRMWANT $F0AA          -> `prm` DIVERGES, `all` SAME (its $A5 fill is blind)
Built through knife_guard (ROM must MOVE), restored, rebuilt CLEAN, re-run green.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "wszero_s10_knife")
SRC = "basic/sysvars.inc"
KNIVES = [
    ("K-WS14", [("FCH_MODES       equ     $F71C", "FCH_MODES       equ     $EE3D")],
     ['ctl', 'chan'], ['chan']),
    ("K-WS15", [("FCH_ACTIVE      equ     $F733", "FCH_ACTIVE      equ     $EEBE")],
     ['ctl', 'chan'], []),
    ("K-WS16", [("CSR_ADDR        equ     $F72C", "CSR_ADDR        equ     $EEEA"), ("CSR_CHAR        equ     $F734", "CSR_CHAR        equ     $EEEC"), ("CSR_ON          equ     $F735", "CSR_ON          equ     $EEED")],
     ['ctl', 'input'], ['input']),
    ("K-WS18", [("DIRECTF         equ     $F73C", "DIRECTF         equ     $EFC1")],
     ['abort', 'midline'], ['midline']),
    ("K-WS19", [("ERRRESUME       equ     $F73E", "ERRRESUME       equ     $EFC4")],
     ['onerr', 'resume'], ['resume']),
    ("K-WS20", [("CONTVALID       equ     $F736", "CONTVALID       equ     $EF41")],
     ['ctl', 'contdir'], ['contdir']),
    ("K-WS21", [("PRMWANT         equ     $F73D", "PRMWANT         equ     $F0AA")],
     ['all', 'prm'], ['prm']),
]


def suite(tag, rows):
    log = f"{TMP}/{tag}.log"
    with open(log, "w") as fh:
        rc = subprocess.call([sys.executable, "-u", "probes/basic/basic_probe_wszero.py", *rows],
                             stdout=fh, stderr=subprocess.STDOUT, timeout=3600)
    red = [ln.split()[1] for ln in open(log) if ln.startswith("ROW") and "DIVERGES" in ln]
    return rc, red


def main():
    os.makedirs(TMP, exist_ok=True)
    text = open(SRC).read()
    for tag, pairs, _r, _p in KNIVES:
        for old, new in pairs:
            if text.count(old) != 1:
                print(f"{tag}: REFUSED, anchor count {text.count(old)} for {old!r}", flush=True)
                return 2
    for tag, pairs, rows, pred in KNIVES:
        before = knife_guard.hashes()
        try:
            cut = text
            for old, new in pairs:
                cut = cut.replace(old, new)
            open(SRC, "w").write(cut)
            moved, _, brc = knife_guard.build(f"{TMP}/mk_{tag}.log", before)
            if brc or not moved:
                print(f"{tag}: build rc={brc} ROM moved={moved} -- NOT SCORED", flush=True)
                continue
            subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            rc, red = suite(tag, rows)
            print(f"{tag}: rows {rows} diverging {red}; predicted {pred} -> "
                  f"{'HIT' if sorted(red) == sorted(pred) else 'MISS'}", flush=True)
        finally:
            open(SRC, "w").write(text)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rc, red = suite("restore", ["ctl", "chan", "input", "midline", "resume", "contdir", "prm"])
    print(f"restored: build rc={brc}; {'DIVERGE ' + str(red) if red else 'SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
