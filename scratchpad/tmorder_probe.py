#!/usr/bin/env python3
"""D-DEFERRSTUDY step 1b: WHERE does a type mismatch raise? (VG-8020 vs zerobas)

step 1a (scratchpad/deferr_side_probe.py, this file's template) found the REFERENCE
evaluating `USR(0)` after `1+"X"` while zerobas raised first. These cases vary what
follows the mismatch. The rig and the readout are step 1a's.

A deferred error and an immediately raised one differ observably ONLY when something
with a visible effect happens between the fault and the point where it is raised. Two
such effects are counted here, black-box:

  * a USR routine that counts its calls (D-CATUSR's rig: `ld hl,$D010 / inc (hl) / ret`
    POKEd at $D000, installed with DEFUSR) placed AFTER the faulting operand;
  * PRINT text AFTER the faulting item -- does it reach the screen?

Direct mode: the faulting line prints its error, the next typed line reads the counter.
`[C n]` is the count; `[N]` would mean the faulting statement completed.

    python3 -u scratchpad/tmorder_probe.py [MACHINE ...]
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

POKES = ['POKE-12288,33:POKE-12287,16', 'POKE-12286,208:POKE-12285,52',
         'POKE-12284,201:DEFUSR=-12288']
READ = 'PRINT"[C";PEEK(-12272);"]"'
CASES = {
    "same":      'A=1+"X"+USR(0)',
    "minus":     'A=1-"X"+USR(0)',
    "strfirst":  'A="X"+1+USR(0)',
    "higher":    'A=1+"X"*USR(0)',
    "paren":     'A=(1+"X")+USR(0)',
    "rel":       'A=1+"X"<USR(0)',
    "and":       'A=1+"X" AND USR(0)',
    "tail":      'A=1+"X"+USR(0)+1',
    "print":     'PRINT 1+"X";USR(0)',
    "fnarg":     'A=ABS(1+"X")+USR(0)',
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
