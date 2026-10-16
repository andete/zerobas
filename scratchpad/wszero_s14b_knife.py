#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO S14b knife: does `s14lst` see the window's move, and does `ovkey`
catch the KEY-bar repaint writing BUF?

K-WS63 the render window + the detok cells back at their pre-S14b homes (the
       S14B_* guards disabled) -> `s14lst` DIVERGES
K-WS64 NEGATIVE CONTROL: S14b's addresses kept, keystr_tenant's old order
       restored (db_begin BEFORE the paint / blank dispatch) -> every keypress
       of a LINE INPUT writes DB_WIN[0] = $F600 = the answer's 163rd byte ->
       `ovkey` DIVERGES
"""
import os, re, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "wszero_s14b_knife")
SRC = "basic/sysvars.inc"
KNIVES = [
    ("K-WS63", {"DB_WIN": "$ED9D", "DB_SKIP": "$EFEC", "DB_MORE": "$EFEE", "DB_RESSKIP": "$EFEF",
                "DB_RESUME": "$EFF1", "DB_SP": "$F0A0", "DT_TOK": "$F0A2", "DT_TOKN": "$F0A4",
                "DB_RESPTR": "$F0A6", "DB_CUR": "$F123"}, ["ctl", "s14lst"], ["s14lst"]),
    ("K-WS64", {}, ["ctl", "ovkey"], ["ovkey"]),
]
KSRC = "sub/keystr.asm"
NEW_ORDER = """                ld      a,(KEYARG)
                cp      KEYOP_FNKPAINT
                jp      z,ks_paint   ; (jp: D-KEYSHIFT's 8 B put ks_paint out of jr range)
                cp      KEYOP_FNKBLANK
                jr      z,ks_blank
"""
OLD_ORDER = """                call    db_begin            ; KNIFE K-WS64
                ld      (de),a
                ld      a,(KEYARG)
                cp      KEYOP_FNKPAINT
                jp      z,ks_paint
                cp      KEYOP_FNKBLANK
                jr      z,ks_blank
"""


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
            ktext = open(KSRC).read()
            if tag == "K-WS64":
                if ktext.count(NEW_ORDER) != 1:
                    raise SystemExit("K-WS64: keystr anchor")
                open(KSRC, "w").write(ktext.replace(NEW_ORDER, OLD_ORDER))
            if not isinstance(pred, str):
                # a positive knife puts a group back in the window, which the S14A
                # overlay-fit guards REFUSE (first run: all four NOT SCORED on
                # their own S12_* symbol) -- disable them so the ROWS are what
                # is measured; K-WS53 / 54 keep them and test the guards
                cutt = cutt.replace("                db      S14B_", "                ; KNIFE db S14B_")
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
            open(KSRC, "w").write(ktext)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    red = suite("restore", ["ctl", "s14lst", "ovkey"])
    print(f"restored: build rc={brc}; {'DIVERGE ' + str(red) if red else 'SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
