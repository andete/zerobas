"""D-ADDR29 S3, the premise: RAMFOOT saw the VG-8020 WRITE `CNSDFG` ($F3DE) on
CLS and `ATRBYT` ($F3F2) on COLOR where zerobas does not. A write that stores
the value already there is invisible to a program -- so what a PEEK READS is
measured here before anything is priced.

Each case runs on a fresh boot (VG-8020 vs zerobas NODISK) and prints the two
cells after a numeric fence. Clean room: typed BASIC, documented work-area
cells, screen text. No ROM byte.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
READ = "PRINT12345;PEEK(&HF3DE);PEEK(&HF3F2)"
CASES = [
    ("boot",       []),
    ("cls",        ["CLS"]),
    ("keyoff",     ["KEY OFF"]),
    ("keyoff_cls", ["KEY OFF:CLS"]),
    ("keyon",      ["KEY OFF:KEY ON"]),
    ("color5",     ["COLOR 5"]),
    ("color5_1_4", ["COLOR 5,1,4"]),
    ("color_bg",   ["COLOR ,1"]),
    ("sc2_color",  ["SCREEN 2:COLOR 9:SCREEN 0"]),
]


def answer(raw):
    rows = [raw[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS].strip()
            for r in range(omsx_repl.ROWS)]
    hit = [r for r in rows if r.startswith("12345 ")]
    return " ".join(hit[-1].split()[1:]) if hit else None


def main():
    got = {}
    for m in (REF, ZB):
        specs = [("direct", pre + [READ]) for _k, pre in CASES]
        res = omsx_repl.run_cases(m, specs, batch=False,
                                  reset=("", "SCREEN 0", "NEW"), boot=8.0,
                                  capture="screen")
        got[m] = [answer(r or "") for r in res]
    bad = 0
    print(f"{'case':11s}  CNSDFG ATRBYT   ref | zb")
    for i, (k, pre) in enumerate(CASES):
        r, z = got[REF][i], got[ZB][i]
        same = r is not None and r == z
        bad += not same
        print(f"{'SAME' if same else 'DIFF'} {k:11s} {r or '<NO OUTPUT>':>9} | {z or '<NO OUTPUT>':9}  {' / '.join(pre)}")
    print(f"\nDIFF: {bad}/{len(CASES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
