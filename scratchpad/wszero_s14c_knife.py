#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO S14c knife: does `s14stx` see the WSTX / tape-save moves, and is a
WSTX one byte too low caught -- by the row AND by the guard?

K-WS65 MIDS_DEST, CLR_SAVE, LOC_COL / LOC_ROW, LHS_VARTYPE, OO_DEVTYPE, TSV_PTR,
       TSV_CNT back at their pre-S14c homes (S14C_* guards off) -> `s14stx`
K-WS66 NEGATIVE CONTROL, guards off: WSTX = $F65D, the last byte INPUT$(255)
       stages into -> `ovstx` DIVERGES (MID$'s held target is overwritten)
K-WS67 the same WSTX with the guards ON -> the build refuses
       (S14C_SOMETHING_AN_EXPRESSION_RUNS_NOW_REACHES_WSTX)
"""
import os, re, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "wszero_s14c_knife")
SRC = "basic/sysvars.inc"
KNIVES = [
    ("K-WS65", {"MIDS_DEST": "$ECFD", "CLR_SAVE": "$EE7B", "LOC_COL": "$EFDF", "LOC_ROW": "$EFE0",
                "LHS_VARTYPE": "$F16C", "OO_DEVTYPE": "$EF3A", "TSV_PTR": "$EF5D", "TSV_CNT": "$EF61"},
     ["ctl", "s14stx"], ["s14stx"]),
    ("K-WS66", {"WSTX": "$F65D"}, ["ctl", "ovstx"], ["ovstx"]),
    ("K-WS67", {"WSTX": "$F65D"}, [], "BUILDFAIL:S14C_SOMETHING_AN_EXPRESSION_RUNS_NOW_REACHES_WSTX"),
]


def cut(text, names):
    for n, addr in names.items():
        pat = re.compile(rf"^({n}\s+equ\s+)(\$[0-9A-F]{{4}}|WSTX \+ 1|WSTX|LINEBUF \+ 256)(?=\s)", re.M)
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
                cutt = cutt.replace("                db      S14C_", "                ; KNIFE db S14C_")
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
    red = suite("restore", ["ctl", "s14stx", "ovstx"])
    print(f"restored: build rc={brc}; {'DIVERGE ' + str(red) if red else 'SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
