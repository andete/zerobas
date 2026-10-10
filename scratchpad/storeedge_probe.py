"""D-DIMRESERVE S3: where is the LINE STORE's edge, against the same shrink
lnblank's `crf-oom*` rows use (`CLEAR 300,TXTTAB+1000`, then `99 REM Z`)?

After the shrink and `99 REM Z`, type `20 REM <n x B>` and LIST: the longest
line still stored is the store's edge. zerobas's store bound is
STK_EDGE_RESERVE-relative (basic/program.asm, SL_CEIL); the references' is
their own. Program bytes are the same on every machine, so equal edges in n
mean the same programs fit.

Clean room: typed BASIC in, the text screen out.

    python3 -u scratchpad/storeedge_probe.py [n ...]      (STE_ONLY=REF|ZB)
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
NS = [0, 4, 8, 12, 16, 20, 24, 26]


def prog(n):
    return ["A=PEEK(&HF676)+256*PEEK(&HF677)", "CLEAR 300,A+1000", "99 REM Z",
            "20 REM " + "B" * n, "LIST"]


def stored(raw):
    rows = [(raw or "")[i:i + 40].strip() for i in range(0, len(raw or ""), 40)]
    i = max((k for k, r in enumerate(rows) if r == "LIST"), default=None)
    if i is None:
        return None
    return any(r.startswith("20 REM") for r in rows[i + 1:])


def main():
    ns = [int(a) for a in sys.argv[1:]] or NS
    only = os.environ.get("STE_ONLY")
    sides = [m for k, m in (("REF", REF), ("ZB", ZB)) if only in (None, k)]
    got = {m: omsx_repl.run_cases(m, [("direct", prog(n)) for n in ns], batch=False,
                                  reset=("CLS",), boot=8.0, capture="screen")
           for m in sides}
    print(f"{'n':>4} " + " ".join(f"{m[:14]:>14}" for m in sides))
    for i, n in enumerate(ns):
        print(f"{n:>4} " + " ".join(f"{str(stored(got[m][i])):>14}" for m in sides))
    return 0


if __name__ == "__main__":
    sys.exit(main())
