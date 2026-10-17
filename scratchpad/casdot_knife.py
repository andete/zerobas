#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CASDOT / D-TSVOVL knives: does each gate row see its own fix?

  K-CD1 cas_name_cut never cuts (cnc_find's `cp '.'` -> `cp $FF`, same size; a
        first cut that jumped PAST the fill left cnc_fill dead, check_dead_code
        refused the build, and it read NOT SCORED -- casdot_knife_run1.out)
                                           -> casbin bdot, odot; cassave
                                              sav-cas-dot:name, bsv-cas-dot:name
  K-CD2 no leading-dot check in MAIN (`jp z,pdf_badname` -> `jp nz,...`, which is
        never taken for a name that does not START with '.')   and in the
        TENANT (`jr z,cnc_bad` -> `jr nz,...`)             -> casbin blead
  K-TO1 TSV_NAME back in BUFTX (the S14f overlap)          -> cassave
        sav-cas-4:name (and the dotted names it corrupts too)
Rows run: casbin bnn bdot odot blead (bnn the control); cassave on the VG-8020
and zerobas, the name readings only. Each cut must prove it BUILT (the ROM moved)
and keep the pins (`make pin-check`).
"""
import os, re, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "casdot_knife")
CB = "basic/cascut-body.inc"
KNIVES = [
    # K-CD1's first cut jumped PAST the fill: cnc_fill went dead and check_dead_code
    # refused the build (NOT SCORED). Now the test itself is blunted, same size.
    ("K-CD1", {CB: [("                ld      a,(hl)\n                cp      '.'\n",
                     "                ld      a,(hl)\n                cp      $FF\n")]},
     {"bdot", "odot", "sav-cas-dot:name", "bsv-cas-dot:name"}),
    ("K-CD2", {CB: [("                jp      z,pdf_badname       ; nothing before the '.': 56 (raise_error\n",
                     "                jp      nz,cnc_k2           ; KNIFE (raise_error\n"),
                    ("                jr      z,cnc_bad           ; nothing before the '.': 56 (below)\n",
                     "                jr      nz,cnc_k2           ; KNIFE\n"),
                    ("                push    hl\n                ld      hl,CAS_WANT\n",
                     "cnc_k2:\n                push    hl\n                ld      hl,CAS_WANT\n")]},
     {"blead"}),
    ("K-TO1", {"basic/sysvars.inc": [("TSV_NAME        equ     CAS_WANT ;", "TSV_NAME        equ     BUFTX ;")]},
     {"sav-cas-4:name", "sav-cas-dot:name", "bsv-cas-dot:name"}),
]
CASBIN = ["bnn", "bdot", "odot", "blead"]


def cut(text, edits):
    for old, new in edits:
        if text.count(old) != 1:
            raise SystemExit(f"anchor x{text.count(old)}: {old[:60]!r}")
        text = text.replace(old, new)
    return text


def red_rows(tag):
    red = set()
    log = f"{TMP}/{tag}_casbin.log"
    with open(log, "w") as fh:
        subprocess.call([sys.executable, "-u", "probes/basic/basic_probe_casbin.py"] + CASBIN,
                        stdout=fh, stderr=subprocess.STDOUT, timeout=3600)
    red |= {ln.split()[1].rstrip(":") for ln in open(log) if ln.startswith("DIVERGES")}
    log = f"{TMP}/{tag}_cassave.log"
    with open(log, "w") as fh:
        subprocess.call([sys.executable, "-u", "probes/basic/basic_probe_cassave.py",
                         "--sides", "vg8020,zb", "--only", "sav-cas-dot,sav-cas-4,bsv-cas-dot,sav-cas"],
                        stdout=fh, stderr=subprocess.STDOUT, timeout=3600)
    red |= {ln.split()[1] for ln in open(log) if ln.startswith("DIFF")}
    return red


def main():
    os.makedirs(TMP, exist_ok=True)
    files = sorted({f for _t, fe, _p in KNIVES for f in fe})
    saved = {f: open(f).read() for f in files}
    for _t, fe, _p in KNIVES:                     # every anchor first, before any build
        for f, edits in fe.items():
            cut(saved[f], edits)
    for tag, fe, pred in KNIVES:
        if sys.argv[1:] and tag not in sys.argv[1:]:
            continue
        before = knife_guard.hashes()
        try:
            for f, edits in fe.items():
                open(f, "w").write(cut(saved[f], edits))
            moved, _, brc = knife_guard.build(f"{TMP}/mk_{tag}.log", before)
            pins = subprocess.call(["make", "pin-check"], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
            if brc or not moved or pins:
                print(f"{tag}: build rc={brc} ROM moved={moved} pin-check rc={pins} -- NOT SCORED",
                      flush=True)
                continue
            red = red_rows(tag)
            print(f"{tag}: diverging {sorted(red)}; predicted {sorted(pred)} -> "
                  f"{'HIT' if red == pred else 'MISS'}", flush=True)
        finally:
            for p, t in saved.items():
                open(p, "w").write(t)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    red = red_rows("restore")
    print(f"restored: build rc={brc}; {'DIVERGE ' + str(sorted(red)) if red else 'SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
