# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DIMRESERVE S3 (gate: dimedge-acceptance): how close to the end of memory a
DIM and a line store may reach, VG-8020 vs zerobas.

  dim-K     `CLEAR 200:X=0:X=INT((FRE(0)-K)/8):DIM A(X)` -- REFUSED (`Out of
            memory in 10`) or FITTED (anything after line 10: the next statement
            may itself run out, as on the reference, which is why no row reads a
            value at the edge). The VG-8020 fits from K=109 and refuses at 108
            (scratchpad/dimedge_scan_pre.out, K one by one). X EXISTS FIRST since
            2026-10-17: a LET whose target is new reads FRE(0) 11 B lower on the
            VG-8020, which creates the target before the right side
            (scratchpad/freabs_run.out) -- a separate difference, not the edge,
            and closed by D-LETNEWFIRST (2026-10-19: zerobas creates first too);
            X=0 stays first so the rows read the edge alone.
            ("fits from 110" stood here until then; it was stale.)
  eval-pP-K deepexpr-acceptance's flat `B=1` / `PRINT"[";E;A(X);"]"` after an edge
            DIM (8-byte elements), phase P (`:` pads): FITTED or REFUSED. Pins
            STK_EVAL_RESERVE (115) to the byte from both sides (D-EVALSLOPE).
  store-n   after `CLEAR 300,TXTTAB+1000` and `99 REM Z`, is `20 REM` + n B
            stored (LIST)? The VG-8020 stores n=13 and refuses n=14.

The reserves are basic/sysvars.inc's STK_EDGE_RESERVE (DIM, a new scalar: 131 --
116 was the floor zerobas's own unguarded stack sets, measured by
scratchpad/lowpoint_probe.py and scratchpad/edgesafe_probe.py) and
STK_STORE_RESERVE (the line store: 141, the reference's edge to the byte). The
DIM edge differed by ~30 B until D-FREPLUS14 (2026-10-17): that gap was FRE(0)'s
(zerobas read it against the pool top, the reference against the live SP). With
FRE(0) on the reference's depth the edge sat 15 B past the reference's, and
STK_EDGE_RESERVE 131 (was 116) puts it on the reference's to the byte
(scratchpad/dimedge_scan_131e.out / _131o.out: both FRE(0) parities, 2-B elements).

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
    return ["NEW", f"10 CLEAR 200:X=0:X=INT((FRE(0)-{k})/8):DIM A(X)",
            '20 PRINT"[";"FIT";"]":END', "RUN"]


def eval_case(k, pad):
    """D-EVALSLOPE (2026-10-20): deepexpr-acceptance's own flat statement after an edge
    DIM, `B=1` then `PRINT"[";E;A(X);"]"`, trapped -- scratchpad/deepctl_edge_probe.py's
    program, byte for byte. The room left is K + (0..7) by FRE(0)'s phase; `pad` extra `:`
    pick the phase. A 1-byte change of STK_EVAL_RESERVE moves the edge in ONE phase only:
    pad 5 (the VG-8020 fits from 134) is where a smaller R would fit at 133, pad 4 (fits
    from 127) where a larger one would refuse 127 -- so these four rows pin R to the byte
    in both directions (deepctl_phase_r115.out)."""
    return ["NEW", "10 CLEAR 200:X=0:E=0:B=0:ON ERROR GOTO 100",
            f"20 X=INT((FRE(0)-{k})/8):DIM A(X):A(X)=12345", "30 B=1" + ":" * pad,
            '40 PRINT"[";E;A(X);"]":PRINT"[";"OK";"]":END', "100 E=ERR:RESUME 40", "RUN"]


def store_case(n):
    return ["A=PEEK(&HF676)+256*PEEK(&HF677)", "CLEAR 300,A+1000", "99 REM Z",
            "20 REM " + "B" * n, "LIST"]


CASES = [("dim-100", dim_case(100)), ("dim-108", dim_case(108)),
         ("dim-109", dim_case(109)), ("dim-120", dim_case(120)),
         ("dim-144", dim_case(144)), ("dim-200", dim_case(200)),
         ("store-12", store_case(12)), ("store-13", store_case(13)),
         ("store-14", store_case(14)), ("store-26", store_case(26)),
         ("eval-p4-126", eval_case(126, 4)), ("eval-p4-127", eval_case(127, 4)),
         ("eval-p5-133", eval_case(133, 5)), ("eval-p5-134", eval_case(134, 5))]

# The DIM edge's residual (D-DIMRESERVE) -- dim-120 / dim-136, which the VG-8020
# fitted and zerobas refused -- closed with D-FREPLUS14 (2026-10-17): the edge rows
# above (108 refused, 109 fitted) agree to the byte. A pin that stops describing
# zerobas is a failure too, so the dictionary stays, empty.
KNOWN_DIVERGE = {}


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


def eval_reading(raw):
    """FITTED when the statement after the edge DIM printed `[OK]`; REFUSED when the
    program ran (its `RUN` is on screen) and never got there -- the trapped ERR 7 loops
    on its own RESUME, as on the reference."""
    r = rows(raw)
    if not any(x == "RUN" for x in r):
        return None
    return "FITTED" if "[OK]" in (raw or "").replace(" ", "") else "REFUSED"


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
        got[side] = [(dim_reading if n.startswith("dim") else
                      eval_reading if n.startswith("eval") else store_reading)(o)
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
