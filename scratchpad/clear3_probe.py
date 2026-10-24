#!/usr/bin/env python3
"""D-CLEAR3ARG: which error wins when CLEAR has a bad argument AND trailing junk?
(VG-8020 vs zerobas). Each case is `20 <stmt>` under `ON ERROR GOTO 100`, which
prints `[E <ERR>]`; `[N]` means the statement was accepted.

    python3 -u scratchpad/clear3_probe.py [MACHINE ...]
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

CASES = {
    "bad2_3rd":   "CLEAR 1,2,3",
    "ok2_3rd":    "CLEAR 200,&HF000,3",
    "ovf1_3rd":   "CLEAR 99999,&HF000,3",
    "ovf2_3rd":   "CLEAR 200,70000,3",
    "oom2_3rd":   "CLEAR 200,&H8100,3",
    "bad2_comma": "CLEAR 1,2,",
    "bad2_junk":  "CLEAR 1,2 X",
    "bad2_colon": "CLEAR 1,2:PRINT 9",
    "neg1_3rd":   "CLEAR -1,&HF000,3",
    "ok_ctl":     "CLEAR 200,&HF000",
    # the ONE-argument form takes the same end check (it enters at clr_chk)
    "one_junk":   "CLEAR 200 X",
    "one_oomjunk": "CLEAR 30000 X",
    "one_ok":     "CLEAR 300",
}


def main():
    for m in sys.argv[1:] or ["Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"]:
        for name, stmt in CASES.items():
            prog = ["NEW", "10 ON ERROR GOTO 100", f"20 {stmt}", '30 PRINT"[N]":END',
                    '100 PRINT"[E";ERR;"]":END', "RUN"]
            scr = omsx_repl.run_cases(m, [("direct", prog)], batch=False, boot=10.0,
                                      reset=("SCREEN 0:WIDTH 40",), step=3.0, run_gap=6.0)[0]
            rows = [scr[i:i + 40].strip() for i in range(0, len(scr or ""), 40)]
            i = max((k for k, r in enumerate(rows) if r == "RUN"), default=-1)
            after = [r for r in rows[i + 1:] if r and r not in ("Ok", "ZB") and not r.startswith("color")]
            print(f"{m:30s} {name:11s} {stmt:24s} {' | '.join(after)}", flush=True)


if __name__ == "__main__":
    main()
