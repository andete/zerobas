#!/usr/bin/env python3
"""D-IFGOTOBARE: what does `IF <cond> GOTO` with no line number do? (VG-8020 vs zerobas)

Each case is a stored program run once; the screen's `[..]` markers and any error say
how far the line went. Typed keys in, the text screen out.

    python3 -u scratchpad/ifgoto_probe.py [MACHINE ...]
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

CASES = {
    "true_end":   '10 IF 1 GOTO',
    "true_rest":  '10 IF 1 GOTO :PRINT"[R]"',
    "false_rest": '10 IF 0 GOTO :PRINT"[R]"',
    "true_else":  '10 IF 1 GOTO ELSE PRINT"[E]"',
    "false_else": '10 IF 0 GOTO ELSE PRINT"[E]"',
    "true_stmt":  '10 IF 1 GOTO PRINT"[X]"',
    "goto_bare":  '10 GOTO',
}


def main():
    for m in sys.argv[1:] or ["Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"]:
        for name, l10 in CASES.items():
            prog = ["NEW", l10, '20 PRINT"[N]"', "RUN"]
            scr = omsx_repl.run_cases(m, [("direct", prog)], batch=False, boot=10.0,
                                      reset=("SCREEN 0:WIDTH 40",), step=3.0, run_gap=6.0)[0]
            rows = [scr[i:i + 40].strip() for i in range(0, len(scr or ""), 40)]
            i = max((k for k, r in enumerate(rows) if r == "RUN"), default=-1)
            after = [r for r in rows[i + 1:] if r and r not in ("Ok", "ZB") and not r.startswith("color")]
            print(f"{m:30s} {name:10s} {' | '.join(after)}", flush=True)


if __name__ == "__main__":
    main()
