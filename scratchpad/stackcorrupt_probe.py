"""D-STACKFLOOR: does a deep expression overwrite an array DIM'd to the edge?

scratchpad/stackhw_probe.py measured zerobas's machine stack reaching 756 B below
the pool frontier for 20 nested parentheses and 1332 B for 32 nested ABS --
while `ctl_alloc`/DIM keep only CTL_STACK_MARGIN (256 B) clear below it. If the
margin is the only floor, an array filled up to that margin sits inside the
region a deep expression then descends into.

Each row DIMs a double array leaving K bytes (by FRE(0)), writes a sentinel into
its LAST element and into a string, evaluates one nested expression, and prints
the last element, the string and the expression's value -- or the error.

    python3 -u scratchpad/stackcorrupt_probe.py          # the rows, both machines
    python3 -u scratchpad/stackcorrupt_probe.py --leaf   # the leaf sweep, zerobas
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
P = lambda n: "(" * n + "1" + "+1)" * n
ABS = lambda n: "ABS(" * n + "1" + ")" * n
ROWS = [
    ("k2000p20", 2000, P(20)),       # control: plenty of room
    ("k280p0",   280,  "1"),         # a FLAT expression at the DIM edge: a guard
    ("k300p0",   300,  "1"),         # must not refuse it
    ("k300p8",   300,  P(8)),
    ("k300p20",  300,  P(20)),
    ("k300a24",  300,  ABS(24)),
    ("k600p20",  600,  P(20)),
    ("k900p32",  900,  P(32)),
]


def prog(k, expr):
    return ["NEW", f'10 CLEAR 200:ON ERROR GOTO 90:S$="SENTINEL":X=INT((FRE(0)-{k})/8):DIM A(X):A(X)=12345',
            f"20 B={expr}",
            '30 PRINT CHR$(91);A(X);S$;B;FRE(0);CHR$(93):END',
            '90 PRINT CHR$(91);"ERR";ERR;ERL;A(X);S$;CHR$(93):END', "RUN"]


def reading(raw):
    m = re.findall(r"\[([^\]\"]*)\]", raw or "")
    return " ".join(m[-1].split()) if m else "NO READING"


# D-STACKFLOOR's LEAF SWEEP (zerobas only -- a corruption shows for itself). The
# evaluator guard reserves STK_EVAL_RESERVE below the last factor that PASSED it;
# what runs below that is a leaf. For each K (DIM edge) and leaf, one program
# nests the leaf ever deeper, one line per depth, checking the array's last
# element after each: wherever the guard last passed, the leaf ran under it.
LEAVES = [("sin", "SIN(1)"), ("log", "LOG(3)"), ("val", 'VAL("1.5")'),
          ("str", "LEN(STR$(1.5))")]
LEAF_K = [280, 290, 300, 310, 320]
DEPTHS = list(range(0, 16, 2))


def leaf_prog(k, leaf):
    lines = ["NEW", f"10 CLEAR 200:ON ERROR GOTO 90:X=INT((FRE(0)-{k})/8):DIM A(X):A(X)=12345"]
    for i, d in enumerate(DEPTHS):
        expr = "(" * d + leaf + "+1)" * d
        lines.append(f"{20 + i} B={expr}:IF A(X)<>12345 THEN PRINT CHR$(91);"
                     f'"CORRUPT";{d};CHR$(93):END')
    lines += ['80 PRINT CHR$(91);"OK";CHR$(93):END',
              '90 PRINT CHR$(91);"ERR";ERR;"DEPTH";(ERL-20)*2;A(X);CHR$(93):END', "RUN"]
    return lines


def main():
    if "--leaf" in sys.argv:
        cases = [(k, n, l) for k in LEAF_K for n, l in LEAVES]
        got = omsx_repl.run_cases(ZB, [("direct", leaf_prog(k, l)) for k, _n, l in cases],
                                  batch=False, reset=("CLS",), boot=8.0, step=3.0,
                                  run_gap=20.0, capture="screen")
        print("leaf sweep, zerobas: OK = every depth fitted; ERR 7 DEPTH d = the guard "
              "refused at d with A(X) intact; CORRUPT / NO READING = a leaf ran below it")
        for (k, n, l), raw in zip(cases, got):
            print(f"  K={k} {n:4} {reading(raw)}")
        return 0
    res = {m: omsx_repl.run_cases(m, [("direct", prog(k, e)) for _t, k, e in ROWS], batch=False,
                                  reset=("CLS",), boot=8.0, step=3.0, run_gap=20.0,
                                  capture="screen")
           for m in (REF, ZB)}
    print(f"{'row':9} {'VG-8020  [A(X) S$ B FRE | ERR]':38} zerobas")
    for i, (t, k, e) in enumerate(ROWS):
        r, z = reading(res[REF][i]), reading(res[ZB][i])
        print(f"{'  ' if r == z else '✗ '}{t:9} {r:38} {z}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
