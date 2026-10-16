#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO S14d knife: does `s14buf` see BUFTX's guests move, and do the rows
catch INPUT$ staging in BUF again?

K-WS68 FOR_CUR, PU_FDESC / PU_WP / PU_COMMAS / PU_DEC, GFX_DEXP, GFX_DFTOP back at
       their pre-S14d homes (S14D_* guards off) -> `s14buf` DIVERGES
K-WS69 NEGATIVE CONTROL: BUFTX kept, basic/strvar.asm and basic/missing.asm taken
       from HEAD -- the old INPUT$ that stages its bytes in STRSCR (and pl_exit
       back in missing.asm, so the $6CF3 segment keeps its size) -> `ovbuftx`
       DIVERGES (INPUT$(40) writes over FOR's frame at $F567) and `inpoom` DIVERGES
       (the keys are read before the out-of-space error)
K-WS70 BUFTX one byte too low (LINEBUF + 8, MKx$'s last STRSCR byte) with the
       guards ON -> the build refuses (S14D_BUFTX_GUESTS_OUTSIDE_THEIR_57_BYTES)
"""
import os, re, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "wszero_s14d_knife")
SRC = "basic/sysvars.inc"
KNIVES = [
    ("K-WS68", {"FOR_CUR": "$EF0A", "PU_FDESC": "$F08D", "PU_WP": "$F095", "PU_COMMAS": "$F095",
                "PU_DEC": "$F096", "GFX_DEXP": "$ED67", "GFX_DFTOP": "$ED38"},
     ["ctl", "s14buf"], ["s14buf"]),
    ("K-WS69", {}, ["ctl", "ovbuftx", "inpoom"], ["ovbuftx", "inpoom"]),
    ("K-WS70", {"BUFTX": "LINEBUF + 8"}, [], "BUILDFAIL:S14D_BUFTX_GUESTS_OUTSIDE_THEIR_57_BYTES"),
]
HEAD_FILES = ("basic/strvar.asm", "basic/missing.asm")


def cut(text, names):
    for n, addr in names.items():
        pat = re.compile(rf"^({n}\s+equ\s+)(\$[0-9A-F]{{4}}|BUFTX \+ \d+|BUFTX|LINEBUF \+ 9)(?=\s)", re.M)
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
            saved = {f: open(f).read() for f in HEAD_FILES}
            if tag == "K-WS69":
                for f in HEAD_FILES:
                    open(f, "w").write(subprocess.check_output(["git", "show", "HEAD:" + f], text=True))
            if not isinstance(pred, str):
                # a positive knife puts a group back in the window, which the S14A
                # overlay-fit guards REFUSE (first run: all four NOT SCORED on
                # their own S12_* symbol) -- disable them so the ROWS are what
                # is measured; K-WS53 / 54 keep them and test the guards
                cutt = cutt.replace("                db      S14D_", "                ; KNIFE db S14D_")
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
            for f, t in saved.items():
                open(f, "w").write(t)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    red = suite("restore", ["ctl", "s14buf", "ovbuftx", "inpoom"])
    print(f"restored: build rc={brc}; {'DIVERGE ' + str(red) if red else 'SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
