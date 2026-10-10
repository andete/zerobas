"""D-DIMRESERVE side reading: after the same `DIM A(X)` at the same K, zerobas's
FRE(0) reads 30 B LOWER than the VG-8020's (K-22 against K+8,
scratchpad/dimedge_run.out). Is that a different FRE(0), or does a scalar / an
array cost more here? FRE(0) differences between steps, both machines:

    boot   FRE(0) after NEW and CLEAR 200
    X      a new double scalar (X=1)
    X%     a new integer scalar
    A$     a new string scalar (empty)
    DIM1   DIM A(9)      (10 doubles)
    DIM2   DIM B%(9)     (10 integers)
    DIM3   DIM C(3,3)    (16 doubles, 2 dims)

Clean room: typed BASIC in, the text screen out.

    python3 -u scratchpad/varcost_probe.py
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
STEPS = ["boot", "X", "X%", "A$", "DIM1", "DIM2", "DIM3"]
PROG = ["NEW",
        "10 CLEAR 200:F1=0:F2=0:F3=0:F4=0:F5=0:F6=0:F7=0:F1=FRE(0):X=1:F2=FRE(0):X%=1:F3=FRE(0):A$=\"\":F4=FRE(0)",
        "20 DIM A(9):F5=FRE(0):DIM B%(9):F6=FRE(0):DIM C(3,3):F7=FRE(0)",
        '30 PRINT"[";F1;F2;F3;F4;F5;F6;F7;"]"', "RUN"]


def main():
    got = {}
    for m in (REF, ZB):
        raw = omsx_repl.run_cases(m, [("direct", PROG)], batch=False, reset=("CLS",),
                                  boot=8.0, capture="screen")[0]
        f = re.findall(r"\[([^\]]*)\]", (raw or "").replace("\n", ""))
        nums = [int(v) for v in f[-1].split()] if f else None
        got[m] = nums
        print(f"{m}: {nums}")
    if not all(got.values()):
        print("INSTRUMENT FAULT: a side gave no reading")
        return 2
    print(f"\n  {'step':6} {'VG-8020':>8} {'zerobas':>8}")
    print(f"  {'boot':6} {got[REF][0]:8} {got[ZB][0]:8}")
    for i, s in enumerate(STEPS[1:], 1):
        print(f"  {s:6} {got[REF][i - 1] - got[REF][i]:8} {got[ZB][i - 1] - got[ZB][i]:8}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
