#!/usr/bin/env python3
"""D-CONTPROG and D-USRBARE: `CONT` inside a running program, and a bare `USR` /
`USR1` with no argument (VG-8020 vs zerobas).

Each case is a stored program run once (some also type a direct line after the
run); the screen's `[..]` markers and any error say how far it went. Typed keys
in, the text screen out.

    python3 -u scratchpad/contusr_probe.py [MACHINE ...]
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

TRAP = ['90 END', '100 PRINT"[E";ERR;ERL;"]":END']
CASES = {
    # CONT in a program: trapped, untrapped, with an argument
    "cont_trap":   (['10 ON ERROR GOTO 100', '20 CONT', '30 PRINT"[N]"'] + TRAP, []),
    "cont_plain":  (['10 PRINT"[A]"', '20 CONT', '30 PRINT"[N]"'], []),
    "cont1_trap":  (['10 ON ERROR GOTO 100', '20 CONT 1', '30 PRINT"[N]"'] + TRAP, []),
    # a live resume point (STOP, then a direct CONT) before the program's CONT
    "cont_live":   (['10 STOP', '20 PRINT"[B]"', '30 CONT', '40 PRINT"[N]"'], ['CONT']),
    "cont_live_t": (['5 ON ERROR GOTO 100', '10 STOP', '20 PRINT"[B]"', '30 CONT',
                     '40 PRINT"[N]"'] + TRAP, ['CONT']),
    # a bare USR: the default and a numbered one, trapped, and at end of statement
    "usr_trap":    (['10 ON ERROR GOTO 100', '20 A=USR', '30 PRINT"[N]"'] + TRAP, []),
    "usr1_trap":   (['10 ON ERROR GOTO 100', '20 A=USR1', '30 PRINT"[N]"'] + TRAP, []),
    "usr_colon":   (['10 ON ERROR GOTO 100', '20 A=USR:PRINT"[C]"', '30 PRINT"[N]"'] + TRAP, []),
    "usr_plus":    (['10 ON ERROR GOTO 100', '20 A=USR+1', '30 PRINT"[N]"'] + TRAP, []),
    "usr_print":   (['10 ON ERROR GOTO 100', '20 PRINT USR', '30 PRINT"[N]"'] + TRAP, []),
    "usr_plain":   (['10 A=USR', '20 PRINT"[N]"'], []),
}


def main():
    for m in sys.argv[1:] or ["Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"]:
        for name, (prog, after_run) in CASES.items():
            lines = ["NEW"] + prog + ["RUN"] + after_run
            scr = omsx_repl.run_cases(m, [("direct", lines)], batch=False, boot=10.0,
                                      reset=("SCREEN 0:WIDTH 40",), step=3.0, run_gap=6.0)[0]
            rows = [scr[i:i + 40].strip() for i in range(0, len(scr or ""), 40)]
            i = max((k for k, r in enumerate(rows) if r == "RUN"), default=-1)
            after = [r for r in rows[i + 1:] if r and r not in ("Ok", "ZB") and not r.startswith("color")]
            print(f"{m:30s} {name:11s} {' | '.join(after)}", flush=True)


if __name__ == "__main__":
    main()
