"""D-FCBSHAPE step 2: where the reference's 2 extra bytes per channel live.

`FRE(0)` charges 267 B per MAXFILES channel on the VG-8020, the FCB stride is
265 (fcbfields_probe.py). This reads the published FILTAB cell ($F860), the
words it points at, and every VARPTR(#n), at MAXFILES 1, 2 and 3 -- work-area
RAM via PEEK, clean-room legal. zerobas has no VARPTR(#n) yet, so VG-8020 only.

Two apparatus notes, both hit while writing it: `MAXFILES=` performs an
implicit CLEAR, so the DEF FN must come AFTER it on the line; and the output is
fenced with CHR$(91)/CHR$(93) and read only BELOW the `RUN` echo, because a
fence typed in the source matches the source.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF = "Philips_VG_8020"
W = "DEF FNW(A)=PEEK(A)+256*PEEK(A+1)"
Q, E = "CHR$(91)", "CHR$(93)"


def case(n):
    return ["NEW", f"10 MAXFILES={n}:{W}:T=FNW(&HF860):PRINT {Q};\"FT\";HEX$(T);{E}",
            f"20 FOR K=0 TO {n}:PRINT {Q};K;HEX$(FNW(T+2*K));{E};:NEXT:PRINT",
            f"30 FOR K=1 TO {n}:PRINT {Q};\"V\";K;HEX$(VARPTR(#K));{E};:NEXT:"
            f"PRINT {Q};\"F\";FRE(0);{E}",
            "RUN"]


def main():
    ns = (1, 2, 3)
    got = omsx_repl.run_cases(REF, [("direct", case(n)) for n in ns], batch=False,
                              reset=("CLS",), boot=8.0, capture="screen")
    for n, raw in zip(ns, got):
        rows = [(raw or "")[i * omsx_repl.COLS:(i + 1) * omsx_repl.COLS]
                for i in range(omsx_repl.ROWS)]
        runi = [i for i, r in enumerate(rows) if r.strip() == "RUN"]
        out = "".join(rows[runi[-1] + 1:]) if runi else ""
        print(f"MAXFILES={n}:", " ".join(re.findall(r"\[([^\[\]]*)\]", "".join(out.split()))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
