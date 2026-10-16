#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO S14e knife: does `s14math` see the math block move, and does
`ovmath` catch a wrapper that forgets to restore its host?

K-WS71 SQRT_X / SQRT_Y / SQRT_K / SQRT_ITER / SQRT_POW10 back at $F16E.. (the
       S14E_* guard off) -> `s14math` DIVERGES
K-WS72 NEGATIVE CONTROL: math_wrap's restore LDIR replaced by two NOPs (the
       saved host is never put back) -> `ovmath` DIVERGES (the FN formals after
       SQR, INPUT's unread answer, PRINT USING's render)
"""
import os, re, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "wszero_s14e_knife")
SRC = "basic/sysvars.inc"
KNIVES = [
    ("K-WS71", {"SQRT_X": "$F16E", "SQRT_Y": "$F180", "SQRT_K": "$F192", "SQRT_ITER": "$F193",
                "SQRT_POW10": "$F194"}, ["ctl", "s14math"], ["s14math"]),
    ("K-WS72", {}, ["ctl", "ovmath"], ["ovmath"]),
]
MWSRC = "sub/mathwrap.asm"
RESTORE = "                ldir                        ; stack -> host: put back what was live\n"
NO_RESTORE = "                nop                         ; KNIFE K-WS72\n                nop\n"


def cut(text, names):
    for n, addr in names.items():
        pat = re.compile(rf"^({n}\s+equ\s+)(MW_HOST \+ \d+|MW_HOST)(?=\s)", re.M)
        if len(pat.findall(text)) != 1:
            raise SystemExit(f"anchor {n}: {len(pat.findall(text))}")
        text = pat.sub(lambda m: m.group(1) + addr, text)
    return text


def suite(tag, rows):
    log = f"{TMP}/{tag}.log"
    with open(log, "w") as fh:
        subprocess.call([sys.executable, "-u", "probes/basic/basic_probe_wszero.py", *rows],
                        stdout=fh, stderr=subprocess.STDOUT, timeout=3600)
    return [ln.split()[1] for ln in open(log) if ln.startswith("ROW") and "DIVERGES" in ln]


def main():
    os.makedirs(TMP, exist_ok=True)
    text = open(SRC).read()
    for tag, names, _r, _p in KNIVES:
        cut(text, names)                            # refuses before anything is touched
    only = sys.argv[1:]
    for tag, names, rows, pred in KNIVES:
        if only and tag not in only:
            continue
        before = knife_guard.hashes()
        try:
            cutt = cut(text, names)
            mwtext = open(MWSRC).read()
            if tag == "K-WS72":
                if mwtext.count(RESTORE) != 1:
                    raise SystemExit("K-WS72: anchor")
                open(MWSRC, "w").write(mwtext.replace(RESTORE, NO_RESTORE))
            if not isinstance(pred, str):
                # a positive knife puts a group back in the window, which the S14A
                # overlay-fit guards REFUSE (first run: all four NOT SCORED on
                # their own S12_* symbol) -- disable them so the ROWS are what
                # is measured; K-WS53 / 54 keep them and test the guards
                cutt = cutt.replace("                db      S14E_", "                ; KNIFE db S14E_")
            open(SRC, "w").write(cutt)
            log = f"{TMP}/mk_{tag}.log"
            moved, _, brc = knife_guard.build(log, before)
            if isinstance(pred, str):               # a guard must REFUSE this layout
                sym = pred.split(":", 1)[1]
                refused = brc != 0 and sym in open(log).read()
                print(f"{tag}: build rc={brc}, {sym} {'named' if sym in open(log).read() else 'NOT named'}"
                      f" in the log; predicted the guard refuses -> {'HIT' if refused else 'MISS'}", flush=True)
                continue
            pins = subprocess.call(["make", "pin-check"], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
            if brc or not moved or pins:
                print(f"{tag}: build rc={brc} ROM moved={moved} pin-check rc={pins} -- NOT SCORED",
                      flush=True)
                continue
            subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
            red = suite(tag, rows)
            print(f"{tag}: rows {rows} diverging {red}; predicted {pred} -> "
                  f"{'HIT' if sorted(red) == sorted(pred) else 'MISS'}", flush=True)
        finally:
            open(SRC, "w").write(text)
            open(MWSRC, "w").write(mwtext)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    red = suite("restore", ["ctl", "s14math", "ovmath"])
    print(f"restored: build rc={brc}; {'DIVERGE ' + str(red) if red else 'SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
