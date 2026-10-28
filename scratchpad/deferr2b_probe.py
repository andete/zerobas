#!/usr/bin/env python3
"""D-DEFERRSTUDY family 2b (2026-10-28): the shared overflow writers' other callers (from deferr_side_probe.py) step 1a: does evaluation RUN ON past a fault? (VG-8020 vs zerobas)

A deferred error and an immediately raised one differ observably ONLY when something
with a visible effect happens between the fault and the point where it is raised. Two
such effects are counted here, black-box:

  * a USR routine that counts its calls (D-CATUSR's rig: `ld hl,$D010 / inc (hl) / ret`
    POKEd at $D000, installed with DEFUSR) placed AFTER the faulting operand;
  * PRINT text AFTER the faulting item -- does it reach the screen?

Direct mode: the faulting line prints its error, the next typed line reads the counter.
`[C n]` is the count; `[N]` would mean the faulting statement completed.

    python3 -u scratchpad/deferr_side_probe.py [MACHINE ...]
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

POKES = ['POKE-12288,33:POKE-12287,16', 'POKE-12286,208:POKE-12285,52',
         'POKE-12284,201:DEFUSR=-12288']
READ = 'PRINT"[C";PEEK(-12272);"]"'
CASES = {
    "ctl_once":  'A=1+USR(0):PRINT"[N]"',
    # the SHARED writers' other callers (spec §2d): fac_to_int_go ...
    "and":       'A=(1 AND 40000)+USR(0):PRINT"[N]"',
    "not":       'A=(NOT 40000)+USR(0):PRINT"[N]"',
    "idiv":      'A=(40000\\1)+USR(0):PRINT"[N]"',
    "poke":      'POKE 70000+USR(0),1:PRINT"[N]"',
    # ... and round_and_finalize
    "fadd":      'A=1E38+1E38+USR(0):PRINT"[N]"',
    "fdiv":      'A=1E38/1E-38+USR(0):PRINT"[N]"',
    "fpow":      'A=10^40+USR(0):PRINT"[N]"',
}


def main():
    for m in sys.argv[1:] or ["Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"]:
        for name, stmt in CASES.items():
            lines = POKES + ['POKE-12272,0', stmt, READ]
            scr = omsx_repl.run_cases(m, [("direct", lines)], batch=False, boot=10.0,
                                      reset=("SCREEN 0:WIDTH 40",), step=3.0, run_gap=4.0)[0]
            rows = [scr[i:i + 40].strip() for i in range(0, len(scr or ""), 40)]
            i = max((k for k, r in enumerate(rows) if r == stmt[:40]), default=-1)
            after = [r for r in rows[i + 1:] if r and r not in ("Ok", "ZB") and r != READ[:40]
                     and not r.startswith("color")]
            print(f"{m:30s} {name:9s} {stmt:36s} {' | '.join(after)}", flush=True)


if __name__ == "__main__":
    main()
