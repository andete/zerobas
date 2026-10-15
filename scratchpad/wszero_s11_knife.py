#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO S11 knife: do the vacated-sum rows SEE each group's move?

One group back at its pre-S11 home per knife (literal old addresses -- the old
chained equates would follow anchors that moved too); everything else stays in
its S11 host. Every row sums the 91 bytes S11 vacated after a full-window $A5
load, so a group whose users write their OLD home again makes the sum differ.
K-WS29 DRAW's 19 cells           -> s11gfx
K-WS30 LINE's X1..Y2             -> s11gfx
K-WS31 CIRCLE's 11 cells         -> s11gfx
K-WS32 sprites + G8 + SARGN/SSIZE -> s11gfx (through G8V; the sprite cells' old
       homes sit inside GFX_PSTK, which the sum does not cover)
K-WS33 the tokeniser's TK* cells  -> s11num, s11inp
K-WS34 the float core + KEYARG    -> s11num
K-WS35 NUMBUF + INP_CURSOR        -> s11num, s11inp
K-WS36 STRPTR / TGT_ADDR / RDV_MODE / PU_FMTD -> s11num, s11inp
Each build must MOVE the ROM (knife_guard) and pass `make pin-check`; restored,
rebuilt CLEAN, the three rows re-run.
"""
import os, re, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "wszero_s11_knife")
SRC = "basic/sysvars.inc"
OLD = {"GFX_DPTR": "ED34", "GFX_DEND": "ED36", "GFX_DCMD": "ED59", "GFX_DSUBN": "ED5B",
       "GFX_DSUBI": "ED5C", "GFX_DSUB": "ED5D", "GFX_DSUBLEN": "ED61", "GFX_DREQ": "ED62",
       "GFX_DRESUME": "ED63", "GFX_DVAL": "ED64", "GFX_DTX": "ED87", "GFX_DTY": "ED89",
       "GFX_DARG": "ED81", "GFX_DVLEN": "ED66", "GFX_DDX": "ED83", "GFX_DFN": "ED80",
       "GFX_DTMP": "ED8B", "GFX_DSP": "ED8D", "GFX_DDY": "ED85",
       "GFX_X1": "EF67", "GFX_Y1": "EF69", "GFX_X2": "EF6B", "GFX_Y2": "EF6D",
       "GFX_SOCT": "EFB3", "GFX_SU14": "EFB5", "GFX_EOCT": "EFB7", "GFX_EU14": "EFB9",
       "GFX_CXC": "EF8D", "GFX_CYC": "EF8F", "GFX_R": "EF91", "GFX_ASPS": "EF94",
       "GFX_CPHASE": "EFBE",
       "GFX_SN": "ED28", "GFX_SDESC": "ED2B", "GFX_SC": "ED2D", "GFX_SPATN": "ED2F",
       "GFX_G8N": "ED99", "GFX_VLEN": "ED2A", "GFX_G8V": "ED9B", "GFX_SSIZE": "ED31",
       "GFX_SFLAGS": "ED33", "GFX_SARGN": "ED32",
       "TKNZPOS": "F0C6", "TKDCOUNT": "F0C7", "TKSTORED": "F0C8", "TKFLAGS": "F0C9",
       "TKPC": "F0CE", "TKLEAD": "F0D1", "TKVALEND": "F0D3", "FOSIGCOUNT": "F0D3",
       "WSRC": "F119", "FP_LHSVAL": "F102", "FP_TMP_B": "F104", "FP_RSIGN": "F106",
       "MUL_ADIG": "F10D", "MUL_CARRY": "F10E", "KEYARG": "F107",
       "NUMBUF": "EF2D", "INP_CURSOR": "EF2D",
       "STRPTR": "EF36", "TGT_ADDR": "ED95", "RDV_MODE": "ED94", "PU_FMTD": "F08B"}
G = lambda s: s.split()
KNIVES = [
    ("K-WS29", G("GFX_DPTR GFX_DEND GFX_DCMD GFX_DSUBN GFX_DSUBI GFX_DSUB GFX_DSUBLEN GFX_DREQ "
                 "GFX_DRESUME GFX_DVAL GFX_DTX GFX_DTY GFX_DARG GFX_DVLEN GFX_DDX GFX_DFN GFX_DTMP "
                 "GFX_DSP GFX_DDY"), ["ctl", "s11gfx"], ["s11gfx"]),
    ("K-WS30", G("GFX_X1 GFX_Y1 GFX_X2 GFX_Y2"), ["ctl", "s11gfx"], ["s11gfx"]),
    ("K-WS31", G("GFX_SOCT GFX_SU14 GFX_EOCT GFX_EU14 GFX_CXC GFX_CYC GFX_R GFX_ASPS GFX_CPHASE"),
     ["ctl", "s11gfx"], ["s11gfx"]),
    ("K-WS32", G("GFX_SN GFX_SDESC GFX_SC GFX_SPATN GFX_G8N GFX_VLEN GFX_G8V GFX_SSIZE GFX_SFLAGS "
                 "GFX_SARGN"), ["ctl", "s11gfx"], ["s11gfx"]),
    ("K-WS33", G("TKNZPOS TKDCOUNT TKSTORED TKFLAGS TKPC TKLEAD TKVALEND FOSIGCOUNT"),
     ["s11num", "s11inp"], ["s11num", "s11inp"]),
    ("K-WS34", G("WSRC FP_LHSVAL FP_TMP_B FP_RSIGN MUL_ADIG MUL_CARRY KEYARG"),
     ["ctl", "s11num"], ["s11num"]),
    ("K-WS35", G("NUMBUF INP_CURSOR"), ["s11num", "s11inp"], ["s11num", "s11inp"]),
    ("K-WS36", G("STRPTR TGT_ADDR RDV_MODE PU_FMTD"), ["s11num", "s11inp"], ["s11num", "s11inp"]),
]


def cut(text, names):
    for n in names:
        pat = re.compile(rf"^({n}\s+equ\s+)\$[0-9A-F]{{4}}", re.M)
        if len(pat.findall(text)) != 1:
            raise SystemExit(f"anchor {n}: {len(pat.findall(text))}")
        text = pat.sub(lambda m: m.group(1) + "$" + OLD[n], text)
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
    for tag, names, rows, pred in KNIVES:
        before = knife_guard.hashes()
        try:
            open(SRC, "w").write(cut(text, names))
            moved, _, brc = knife_guard.build(f"{TMP}/mk_{tag}.log", before)
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
    red = suite("restore", ["ctl", "s11gfx", "s11num", "s11inp"])
    print(f"restored: build rc={brc}; {'DIVERGE ' + str(red) if red else 'SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
