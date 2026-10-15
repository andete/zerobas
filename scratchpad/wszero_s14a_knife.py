#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO S14a knife: do the rows SEE each S14a move -- and are the WRONG
placements caught?

Positive (one group back at its pre-S14a home, the S14A_* guards disabled --
they refuse every group put back):
K-WS56 CVT back at $F0E6            -> s14eq
K-WS57 RVDESC back at $EFF2         -> s14eq
K-WS58 CVT_MODE / VS_TARGET_TYPE / VS_INT_VAL / MC_TYPE back -> s14eq
K-WS59 DISKOP_STATUS back at $EE39  -> s14eq
Negative controls (guards left ON):
K-WS60 CVT onto ARGA (live: flt_out unpacks into it) -> the build refuses
       (S14A_CVT_MUST_BE_EXACTLY_ARGB)
K-WS61 VS_INT_VAL onto TKVALEND (INPUT's read-back) -> the build refuses
       (S14A_DAC_TAIL_GUESTS_MUST_NOT_SHARE_A_BYTE)
K-WS62 VARTYPE onto TKDCOUNT -- the placement the plan proposed and
       test_control_flow refuted (READ) -> `ovdac` DIVERGES (no guard covers
       VARTYPE: the row must)
"""
import os, re, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "wszero_s14a_knife")
SRC = "basic/sysvars.inc"
KNIVES = [
    ("K-WS56", {"CVT": "$F0E6"}, ["ctl", "s14eq"], ["s14eq"]),
    ("K-WS57", {"RVDESC": "$EFF2"}, ["ctl", "s14eq"], ["s14eq"]),
    ("K-WS58", {"CVT_MODE": "$F11E", "VS_TARGET_TYPE": "$F169", "VS_INT_VAL": "$F16A",
                "MC_TYPE": "$F16D"}, ["ctl", "s14eq"], ["s14eq"]),
    ("K-WS59", {"DISKOP_STATUS": "$EE39"}, ["ctl", "s14eq"], ["s14eq"]),
    ("K-WS60", {"CVT": "ARGA"}, [], "BUILDFAIL:S14A_CVT_MUST_BE_EXACTLY_ARGB"),
    ("K-WS61", {"VS_INT_VAL": "$F804"}, [], "BUILDFAIL:S14A_DAC_TAIL_GUESTS_MUST_NOT_SHARE_A_BYTE"),
    ("K-WS62", {"VARTYPE": "$F7FF"}, ["ctl", "ovdac"], ["ovdac"]),
]


def cut(text, names):
    for n, addr in names.items():
        pat = re.compile(rf"^({n}\s+equ\s+)(\$[0-9A-F]{{4}}|ARGB)\b", re.M)
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
            if not isinstance(pred, str):
                # a positive knife puts a group back in the window, which the S14A
                # overlay-fit guards REFUSE (first run: all four NOT SCORED on
                # their own S12_* symbol) -- disable them so the ROWS are what
                # is measured; K-WS53 / 54 keep them and test the guards
                cutt = cutt.replace("                db      S14A_", "                ; KNIFE db S14A_")
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
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    red = suite("restore", ["ctl", "s14eq", "ovdac", "ovargb"])
    print(f"restored: build rc={brc}; {'DIVERGE ' + str(red) if red else 'SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
