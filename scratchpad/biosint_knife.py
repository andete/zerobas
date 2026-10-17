#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BIOSINT knives: do the biosregs-acceptance `kscan` rows see the $0D12 entry
(cbios-repack/bios-keyscan.patch)? A `+` line of the patch replaced by ONE line of the
SAME size, so the diff still applies and nothing moves (C-BIOS still ends at
$2785); the repack's sha1 pin is skipped for the knife build only:
  K-KS1 kscan does not keep IX (`push ix` / `pop ix` -> `jr $+2`, 2 B each)
  K-KS2 A = low(PUTPNT), not the difference (`sub l` -> `nop`)
  K-KS3 C = 0, not $FF (`ld c,$FF` -> `ld c,$00`)
  K-KS4 HL = PUTPNT, not GETPNT (`ld hl,(GETPNT)` -> `ld hl,(PUTPNT)`): A is then
        0 too -- `kscan3` and `kscanw` only, the empty row has GETPNT = PUTPNT
  K-KS5 $0D12 is the reset again (`jp kscan` -> `rst 0`, the pad fills to $0D16)
Each predicts the kscan rows named and no other (all ten rows run). DE and B
have no cut: kscan does not load them (key_in leaves DE = KEYBUF and B = 0). Each cut must
prove it BUILT (the ROM moved) and keep the pins (`make pin-check`).
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "biosint_knife")
SHA = ("            if got != REPACKED_SHA1:", "            if False:")
BR = "probes/basic/basic_probe_biosregs.py"
P = "cbios-repack/bios-keyscan.patch"
KS = ["kscan", "kscan3", "kscanw"]
N2 = "+                jr      $+2\n"
KNIVES = [
    ("K-KS1", {P: [("+                push    ix\n", N2), ("+                pop     ix\n", N2)],
               "tools/build_repacked_cbios.py": [SHA]}, BR, None, KS),
    ("K-KS2", {P: [("+                sub     l\n", "+                nop\n")],
               "tools/build_repacked_cbios.py": [SHA]}, BR, None, KS),
    ("K-KS3", {P: [("+                ld      c,$FF\n", "+                ld      c,$00\n")],
               "tools/build_repacked_cbios.py": [SHA]}, BR, None, KS),
    ("K-KS4", {P: [("+                ld      hl,(GETPNT)\n", "+                ld      hl,(PUTPNT)\n")],
               "tools/build_repacked_cbios.py": [SHA]}, BR, None, ["kscan3", "kscanw"]),
    ("K-KS5", {P: [("+                jp      kscan\n", "+                rst     0\n")],
               "tools/build_repacked_cbios.py": [SHA]}, BR, None, KS),
]


def cut(text, edits):
    for old, new in edits:
        if text.count(old) != 1:
            raise SystemExit(f"anchor x{text.count(old)}: {old[:60]!r}")
        text = text.replace(old, new)
    return text


def rows(tag, probe, only):
    log = f"{TMP}/{tag}.log"
    with open(log, "w") as fh:
        subprocess.call([sys.executable, "-u", probe] + (only or []),
                        stdout=fh, stderr=subprocess.STDOUT, timeout=3600)
    return [ln.split()[1] for ln in open(log) if ln.startswith("ROW") and "DIVERGES" in ln]


def main():
    os.makedirs(TMP, exist_ok=True)
    files = sorted({f for _t, fe, _p, _o, _r in KNIVES for f in fe})
    saved = {f: open(f).read() for f in files}
    for _t, fe, _p, _o, _r in KNIVES:          # every anchor first, before any build
        for f, edits in fe.items():
            cut(saved[f], edits)
    for tag, fe, probe, only, pred in KNIVES:
        before = knife_guard.hashes()
        try:
            for f, edits in fe.items():
                open(f, "w").write(cut(saved[f], edits))
            moved, _, brc = knife_guard.build(f"{TMP}/mk_{tag}.log", before)
            pins = subprocess.call(["make", "pin-check"], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
            if brc or not moved or pins:
                print(f"{tag}: build rc={brc} ROM moved={moved} pin-check rc={pins} "
                      f"-- NOT SCORED", flush=True)
                continue
            red = rows(tag, probe, only)
            print(f"{tag}: diverging {red}; predicted {pred} -> "
                  f"{'HIT' if sorted(red) == sorted(pred) else 'MISS'}", flush=True)
        finally:
            for p, t in saved.items():
                open(p, "w").write(t)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    red = rows("restore_br", BR, None)
    print(f"restored: build rc={brc}; {'DIVERGE ' + str(red) if red else 'SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
