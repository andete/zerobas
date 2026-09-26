"""D-KEYSCR1: the function-key line in SCREEN 1, byte for byte.

The screen scrape reads the SCREEN 0 name table, so in SCREEN 1 it returns
pattern bytes (keycls_probe.py). This reads row 23 of the SCREEN 1 name table
($1800 + 23*32) with VPEEK inside the program, returns to SCREEN 0, and prints
the 32 bytes as hex -- on both machines. `KEY OFF` is the negative.

Diskless pair, fresh boot per case. Clean room: typed BASIC, VRAM contents.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
GRAB = "DIM V(31):FOR X=0 TO 31:V(X)=VPEEK(&H1AE0+X):NEXT:SCREEN 0"
SHOW = 'FOR X=0 TO 31:PRINT RIGHT$("0"+HEX$(V(X)),2);:NEXT:PRINT"!"'
CASES = [
    ("enter",   ["SCREEN 1:" + GRAB, SHOW]),
    ("cls",     ["SCREEN 1:CLS:" + GRAB, SHOW]),
    ("keyoff",  ["SCREEN 1:KEY OFF:" + GRAB, SHOW]),
]


def answer(raw):
    t = "".join("".join(raw or "").split())
    i = t.rfind("!")
    if i < 64:
        return None
    h = t[i - 64:i]
    try:
        return bytes.fromhex(h).decode("latin1")
    except ValueError:
        return None


def main():
    got = {m: [answer(r) for r in
               omsx_repl.run_cases(m, [("stored", l) for _k, l in CASES],
                                   batch=False, cap_gap=4.0)]
           for m in (REF, ZB)}
    bad = 0
    for i, (k, _l) in enumerate(CASES):
        r, z = got[REF][i], got[ZB][i]
        same = r is not None and r == z
        bad += not same
        print(f"{'SAME' if same else 'DIFF'} {k:7s} ref {r!r}  zb {z!r}")
    print(f"\nDIFF: {bad}/{len(CASES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
