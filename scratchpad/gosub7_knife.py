#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""GOSUB 8 -> 7 B knives: does a gate see the frame's one-byte gdelta?

The 7-byte frame keeps the previous GOSUB frame as prevFSP + gdelta; gdelta is 3 when
a trap's service record sits between them, 0 otherwise. Only a GOSUB pushed INSIDE a
trap handler stores a 3, so only those rows can see it.
  K-GS1 the push stores gdelta 0 always (`ld a,l` -> `xor a`)
  K-GS2 RETURN ignores it (`ld a,(de)` -> `xor a`)
Gates run: trapsvc-acceptance, trapdepth-acceptance, interval-trap-acceptance.
Each cut must prove it BUILT (the ROM moved) and keep the pins (`make pin-check`).
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "gosub7_knife")
P = "basic/program.asm"
GATES = ["trapsvc-acceptance", "trapdepth-acceptance", "interval-trap-acceptance"]
KNIVES = [
    ("K-GS1", {P: [("                sbc     hl,de               ; GSP - FSP: 0, or 3 under a trap record\n"
                    "                ld      a,l\n",
                    "                sbc     hl,de               ; GSP - FSP: 0, or 3 under a trap record\n"
                    "                xor     a                   ; KNIFE K-GS1\n")]}),
    ("K-GS2", {P: [("                ld      a,(de)              ; [6] gdelta\n",
                    "                xor     a                   ; KNIFE K-GS2\n")]}),
]


def cut(text, edits):
    for old, new in edits:
        if text.count(old) != 1:
            raise SystemExit(f"anchor x{text.count(old)}: {old[:60]!r}")
        text = text.replace(old, new)
    return text


def red_gates(tag):
    red = []
    for g in GATES:
        log = f"{TMP}/{tag}_{g}.log"
        with open(log, "w") as fh:
            rc = subprocess.call(["make", g], stdout=fh, stderr=subprocess.STDOUT, timeout=3600)
        if rc:
            red.append(g)
    return red


def main():
    os.makedirs(TMP, exist_ok=True)
    saved = {P: open(P).read()}
    for _t, fe in KNIVES:
        for f, edits in fe.items():
            cut(saved[f], edits)
    for tag, fe in KNIVES:
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
            red = red_gates(tag)
            print(f"{tag}: red gates {red} -> {'HIT' if red else 'MISS (no gate sees it)'}", flush=True)
        finally:
            for p, t in saved.items():
                open(p, "w").write(t)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    red = red_gates("restore")
    print(f"restored: build rc={brc}; {'RED ' + str(red) if red else 'all green'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
