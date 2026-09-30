"""D-CIRCANGLE: where exactly does CIRCLE refuse an arc angle?

T6 batch 7b: `CIRCLE(99,99),5,1,7`, `...,5,1,6.3` and the END angle
`...,5,1,1,7` are Illegal function call (5) on the VG-8020 and accepted here.
Before a check is written, the BOUNDARY: a ladder straddling 2*pi =
6.283185307..., on the start and on the end angle, positive and negative (a
negative angle draws a spoke, so its magnitude is what is bounded -- or not).

One boot per case, SCREEN 2, trapped; prints ERR (0 = drew).

    python3 -u scratchpad/circang_probe.py
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

VALS = ["6.28", "6.2831", "6.28318", "6.283185", "6.2831853", "6.28319", "6.2832",
        "-6.2831", "-6.2832", "7", "6.283185307#", "6.28318531#"]
# round 2: round 1 said the threshold is NOT 2*pi in any precision -- 6.2832 draws,
# 7 refuses, and the filed 6.3 refuses. Bisect the gap, and the negative side.
VALS2 = ["6.2835", "6.284", "6.285", "6.29", "6.295", "6.3", "6.4", "6.5", "-6.3", "-7"]
# round 3: 6.2832 draws, 6.2835 refuses -- the last digits and the equality case
VALS3 = ["6.28321", "6.28322", "6.28325", "6.2833", "6.2834", "6.28320001#", "6.2832#", "-6.28321"]
if "2" in sys.argv[1:]:
    VALS = VALS2
# round 4: 6.28322 draws, 6.28325 refuses
VALS4 = ["6.28323", "6.283235", "6.28324", "6.283245", "6.28323#", "6.28324#"]
if "3" in sys.argv[1:]:
    VALS = VALS3
# round 5: single 6.28324 draws, 6.28325 refuses -- where in DOUBLE?
VALS5 = ["6.283241#", "6.283243#", "6.2832449#", "6.283245#", "6.283247#", "6.28325#"]
if "4" in sys.argv[1:]:
    VALS = VALS4
if "5" in sys.argv[1:]:
    VALS = VALS5


def cases():
    out = []
    for v in VALS:
        for where, arc in (("start", f"{v},1"), ("end", f"1,{v}")):
            out.append((f"{where} {v}", ["NEW", "10 ON ERROR GOTO 90",
                                         f"20 SCREEN 2:CIRCLE(99,99),5,1,{arc}:E=0",
                                         "30 SCREEN 0:PRINT CHR$(91);E;CHR$(93):END",
                                         "90 E=ERR:RESUME 30", "RUN"]))
    return out


def main():
    cs = cases()
    got = {}
    for m in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"):
        raws = omsx_repl.run_cases(m, [("direct", p) for _k, p in cs], batch=False,
                                   reset=("CLS",), boot=8.0, step=3.0, capture="screen")
        for (k, _p), raw in zip(cs, raws):
            r = re.findall(r"\[\s*(-?\d+)\s*\]", raw or "")
            got[(m, k)] = r[-1] if r else "NO READING"
    print(f"{'case':22} {'VG-8020':>8} {'zerobas':>8}   (ERR; 0 = drew)")
    for k, _p in cs:
        a, b = got[("Philips_VG_8020", k)], got[("C-BIOS_MSX1_EU_REPACK_NODISK", k)]
        print(f"{'  ' if a == b else '✗ '}{k:20} {a:>8} {b:>8}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
