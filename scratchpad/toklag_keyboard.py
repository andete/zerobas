#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TOKLAG, the deciding run: does a person TYPING lose a line after the refused
253-character line?

tokovf_after.out lost `PRINT "ALIVE";1+1` on zerobas -- but those lines were put
into the key buffer by the harness's injector, which by design OVERWRITES keys
still pending there (probes/lib/omsx_repl.py key_proc: "anything pending is
overwritten"), and zerobas's slower SUM loop (4.86 s against 1.44 s,
toklag_probe.out) leaves them pending longer. A real keyboard APPENDS. This types
the same five lines through the keyboard matrix (openMSX `type`) on both
machines, the long line first given time to finish typing.

Prediction (2026-10-13): both machines show every line, `ALIVE 2` included.
"""
import os, sys
os.environ.setdefault("ZEROBAS_REFCACHE", "0")
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(_R, "probes", "lib"), os.path.join(_R, "scratchpad")]
import omsx_repl                                   # noqa: E402
import tokovf_probe as t                           # noqa: E402


def tcl(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


SEQ = [(11.0, t.SUM), (16.0, t.LONG), (45.0, t.SUM), (47.5, 'PRINT "ALIVE";1+1'), (50.0, "LIST")]


def main():
    pro = tuple(f'after time {tt} {{ type "{tcl(s)}\\r" }}' for tt, s in SEQ)
    for m in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"):
        raw = omsx_repl.run_cases(m, [("direct", ["@WAIT70"])], batch=False, reset=("",),
                                  run_gap=75.0, prologue=pro)[0] or ""
        flat = raw.replace("\n", "")
        rows = [flat[i:i + 40].rstrip() for i in range(0, len(flat), 40) if flat[i:i + 40].strip()]
        print(f"=== {m}: ALIVE 2 printed: {'ALIVE 2' in flat}; overflow: {'overflow' in flat}",
              flush=True)
        for r in rows[-12:]:
            print("   |" + r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
