"""D-DIMRESERVE: how many bytes must a DIM leave (by FRE(0)) to succeed?

D-PAINTSP's tight rows found zerobas's `DIM` refusing (`Out of memory`) with
~260 B of FRE(0) still to spare, where the VG-8020's fits down to ~145. This
bisects the edge on both machines: for each K, `DIM A(X)` with
X = INT((FRE(0)-K)/8) (8 B per double element, the default type), under an
ON ERROR handler; the reading is ERR (0 = the DIM fitted) and FRE(0) after.

The gap between FRE(0) and what an allocation may actually take is the
machine's own stack reserve -- the number this item is about.

    python3 -u scratchpad/dimedge_probe.py
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
KS = [400, 320, 280, 260, 240, 200, 170, 150, 140, 130, 120, 100]


def prog(k):
    return ["NEW", f"10 CLEAR 200:ON ERROR GOTO 90:X=INT((FRE(0)-{k})/8):DIM A(X)",
            '20 PRINT"[";0;FRE(0);"]":END',
            '90 PRINT"[";ERR;FRE(0);"]":END', "RUN"]


def val(raw):
    m = re.findall(r"\[([^\]]*)\]", raw or "")
    got = [x for x in m if re.match(r"^\s*-?\d+\s+-?\d+\s*$", x)]
    return " ".join(got[-1].split()) if got else None


def main():
    res = {m: omsx_repl.run_cases(m, [("direct", prog(k)) for k in KS], batch=False,
                                  reset=("CLS",), boot=8.0, capture="screen")
           for m in (REF, ZB)}
    print(f"{'K':>5} {'VG-8020 (ERR FRE)':>20} {'zerobas (ERR FRE)':>20}")
    for i, k in enumerate(KS):
        print(f"{k:>5} {str(val(res[REF][i])):>20} {str(val(res[ZB][i])):>20}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
