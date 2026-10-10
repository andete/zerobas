# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DIMRESERVE S3 (gate: dimedge-acceptance): how close to the end of memory a
DIM and a line store may reach, VG-8020 vs zerobas.

  dim-K     `CLEAR 200:X=INT((FRE(0)-K)/8):DIM A(X)` -- REFUSED (`Out of memory
            in 10`) or FITTED (anything after line 10: the next statement may
            itself run out, as on the reference, which is why no row reads a
            value at the edge). The VG-8020 fits from K=110, refuses at 108.
  store-n   after `CLEAR 300,TXTTAB+1000` and `99 REM Z`, is `20 REM` + n B
            stored (LIST)? The VG-8020 stores n=13 and refuses n=14.

The reserves are basic/sysvars.inc's STK_EDGE_RESERVE (DIM, a new scalar: 116,
the floor zerobas's own unguarded stack sets, measured by
scratchpad/lowpoint_probe.py and scratchpad/edgesafe_probe.py) and
STK_STORE_RESERVE (the line store: 141, the reference's edge to the byte). The
DIM edge still differs by ~30 B -- zerobas's statement stack is deeper than the
reference's -- and those rows are KNOWN_DIVERGE, pinned to their exact value.

Prints `ROW <name> VG=[...] ZB=[...] <verdict>`; exit 0 all agree (or match
their pin), 1 a divergence, 2 the VG-8020 gave no reading.
Clean-room: typed BASIC in, the text screen out. VG-8020 vs zerobas NODISK.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"


def dim_case(k):
    return ["NEW", f"10 CLEAR 200:X=INT((FRE(0)-{k})/8):DIM A(X)",
            '20 PRINT"[";"FIT";"]":END', "RUN"]


def store_case(n):
    return ["A=PEEK(&HF676)+256*PEEK(&HF677)", "CLEAR 300,A+1000", "99 REM Z",
            "20 REM " + "B" * n, "LIST"]


CASES = [("dim-100", dim_case(100)), ("dim-108", dim_case(108)),
         ("dim-120", dim_case(120)), ("dim-136", dim_case(136)),
         ("dim-144", dim_case(144)), ("dim-200", dim_case(200)),
         ("store-12", store_case(12)), ("store-13", store_case(13)),
         ("store-14", store_case(14)), ("store-26", store_case(26))]

# The DIM edge's residual (D-DIMRESERVE): the VG-8020 fits these, zerobas
# refuses them. A pin that stops describing zerobas is a failure too.
KNOWN_DIVERGE = {"dim-120": "REFUSED", "dim-136": "REFUSED"}


def rows(raw):
    s = raw or ""
    return [s[i:i + 40].strip() for i in range(0, len(s), 40)]


def dim_reading(raw):
    r = rows(raw)
    if not any(x == "RUN" for x in r):
        return None
    if any(re.search(r"Out of memory in 10\b", x) for x in r):
        return "REFUSED"
    return "FITTED"


def store_reading(raw):
    r = rows(raw)
    i = max((k for k, x in enumerate(r) if x == "LIST"), default=None)
    if i is None:
        return None
    return "STORED" if any(x.startswith("20 REM") for x in r[i + 1:]) else "REFUSED"


def main():
    got = {}
    for side, m in (("VG", REF), ("ZB", ZB)):
        out = omsx_repl.run_cases(m, [("direct", c) for _n, c in CASES], batch=False,
                                  reset=("CLS",), boot=8.0, capture="screen")
        got[side] = [(dim_reading if n.startswith("dim") else store_reading)(o)
                     for (n, _c), o in zip(CASES, out)]
    bad, blind = [], []
    for i, (name, _c) in enumerate(CASES):
        vg, zb = got["VG"][i], got["ZB"][i]
        if vg is None or zb is None:
            verdict = "NO-READING"
            blind.append(name)
        elif name in KNOWN_DIVERGE:
            if vg != zb and zb == KNOWN_DIVERGE[name]:
                verdict = "KNOWN_DIVERGE"
            else:
                verdict = f"PIN-ROTTED (pinned ZB={KNOWN_DIVERGE[name]})"
                bad.append(name)
        elif vg == zb:
            verdict = "SAME"
        else:
            verdict = "DIVERGES"
            bad.append(name)
        print(f"ROW {name} VG=[{vg}] ZB=[{zb}] {verdict}", flush=True)
    if blind:
        print(f"\nINSTRUMENT FAULT: no reading on {', '.join(blind)}")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: DIM and line-store edges "
          f"({len(CASES) - len(bad)}/{len(CASES)}, {len(KNOWN_DIVERGE)} pinned)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
