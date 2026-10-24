#!/usr/bin/env python3
"""D-P0CB's tape-loop study (2026-10-24): how much time does CLOAD's byte loop have
between two TAPIN calls before the load breaks?

Moving do_tape_prog into a sub2 tenant would put a p0cb round trip (page 0 back to
the BIOS, and again) on every TAPIN call. This measures the MARGIN that cost would
spend: a build plants N passes of `djnz` (13 T each) at the top of ctp_body -- once
per program byte -- and a tokenised 40-line program is CLOADed from a CSAVE-shaped
tape on zerobas diskless; the run LISTs and RUNs it. Our own ROM, our own tape.

    python3 -u scratchpad/tapin_margin.py LABEL      (run against the INSTALLED build)
"""
import os, shutil, subprocess, sys, tempfile, time
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(REPO, "probes", "lib"), os.path.join(REPO, "probes", "disk")]
import omsx_repl  # noqa: E402
from cas_encode import build_cas_basic_csave  # noqa: E402
from bas_tokenise import make_multiline_program  # noqa: E402

LINES = [(10 * i, f'S=S+{i}:A$="LINE{i:02d}"+STRING$(20,"*")') for i in range(1, 39)]
LINES += [(390, 'PRINT "[S";S;A$;"]"'), (400, "END")]
WANT = "[S 741 LINE38********************]"


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "run"
    prog = make_multiline_program(LINES, 0x8001)
    td = tempfile.mkdtemp(prefix="tapin_")
    cas = os.path.join(td, "p.cas")
    open(cas, "wb").write(build_cas_basic_csave("PROG", prog))
    t0 = time.time()
    scr = omsx_repl.run_cases("C-BIOS_MSX1_EU_REPACK_NODISK",
                              [("direct", ["CLOAD", "RUN"])], batch=False,
                              reset=("", "SCREEN 0:WIDTH 40"), step=3.0, run_gap=60.0,
                              cassette=cas)[0] or ""
    rows = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)]
    got = next((r.strip() for r in rows if r.strip().startswith("[S")), None)
    print(f"{label}: {'OK' if got == WANT else 'BROKEN'}  got={got!r}  ({time.time() - t0:.0f} s wall)")
    for r in rows:
        if r.strip():
            print("   |" + r)
    shutil.rmtree(td)


if __name__ == "__main__":
    main()
