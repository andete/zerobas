#!/usr/bin/env python3
"""D-ERRORARG: what does ERROR raise for a malformed or out-of-range argument, and does
the statement-end check come before the range check? (VG-8020 vs zerobas). Each case is
`20 <stmt>` under `ON ERROR GOTO 100`, which prints `[E <ERR> <ERL>]`.

    python3 -u scratchpad/errorarg_probe.py [MACHINE ...]
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

CASES = {
    "str":       'ERROR "A"',
    "bare":      'ERROR',
    "ovf":       'ERROR 70000',
    "extra":     'ERROR 1,1',
    "zero_x":    'ERROR 0,1',
    "big_x":     'ERROR 300,1',
    "neg_x":     'ERROR -1,1',
    "str_x":     'ERROR "A",1',
    "junk":      'ERROR 1 X',
    "colon":     'ERROR 7:PRINT 9',
    "round":     'ERROR 1.5',
    "zero":      'ERROR 0',
    "b256":      'ERROR 256',
    "u255":      'ERROR 255',
    "ok":        'ERROR 11',
}


def main():
    for m in sys.argv[1:] or ["Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"]:
        for name, stmt in CASES.items():
            prog = ["NEW", "10 ON ERROR GOTO 100", f"20 {stmt}", '30 PRINT"[N]":END',
                    '100 PRINT"[E";ERR;ERL;"]":END', "RUN"]
            scr = omsx_repl.run_cases(m, [("direct", prog)], batch=False, boot=10.0,
                                      reset=("SCREEN 0:WIDTH 40",), step=3.0, run_gap=6.0)[0]
            rows = [scr[i:i + 40].strip() for i in range(0, len(scr or ""), 40)]
            i = max((k for k, r in enumerate(rows) if r == "RUN"), default=-1)
            after = [r for r in rows[i + 1:] if r and r not in ("Ok", "ZB") and not r.startswith("color")]
            print(f"{m:30s} {name:7s} {stmt:16s} {' | '.join(after)}", flush=True)


if __name__ == "__main__":
    main()
