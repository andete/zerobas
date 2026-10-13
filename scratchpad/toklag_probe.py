#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TOKLAG, measure first: what loses `PRINT "ALIVE";1+1` on zerobas?

The filing blamed the refused 253-character line. But tokovf_after.out shows the
line AFTER it (the SUM loop) running fine on zerobas, and in direct mode the
harness injects lines `step` (2.5 s) apart -- `run_gap` is only the wait after the
LAST line -- so `PRINT "ALIVE"` reached the key buffer while the SUM loop was
still RUNNING. The competing explanation is TYPE-AHEAD: zerobas discards keys
that arrive while a program runs, and the VG-8020 keeps them.

  (a) timing   the SUM loop between program-written marks (docs/spec-probe-mark.md)
  (b) KEYBUF   `PRINT "AHEAD"` injected into the key buffer (the harness's way)
               2.5 s into `FOR I=1 TO 5000:NEXT:PRINT "DONE"`
  (c) keyboard the same line TYPED through the keyboard matrix (openMSX `type`,
               a person's keystrokes) 1 s into the same loop

Prediction (2026-10-13): (a) the loop runs longer than 2.5 s on both, longer on
zerobas; (b) and (c): the VG-8020 prints DONE then AHEAD; zerobas prints DONE
and loses AHEAD.
"""
import os, sys
os.environ.setdefault("ZEROBAS_REFCACHE", "0")
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(_R, "probes", "lib"), os.path.join(_R, "probes", "basic")]
import omsx_repl                                   # noqa: E402

MACHINES = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")
# 2000, not 5000: the empty loop takes 8.1 s on the VG-8020 and 33.8 s here
# (toklag_control.out), so run 1's 30 s window closed before zerobas's DONE.
# At 2000 the VG-8020 (~3.2 s) is still running when AHEAD arrives at +2.5 s.
LOOP = 'FOR I=1 TO 2000:NEXT:PRINT "DONE"'


def flat(raw):
    s = (raw or "").replace("\n", "")
    return " ".join(s[i:i + 40].strip() for i in range(0, len(s), 40) if s[i:i + 40].strip())


def outcome(raw):
    txt = flat(raw)
    # the TYPED echo of `PRINT "AHEAD"` carries a quote; the program's output does not
    printed = [w for w in ("DONE", "AHEAD") if f" {w}" in txt.replace('"' + w, "")]
    return txt, printed


def main():
    for m in MACHINES:
        print(f"=== {m}", flush=True)
        so = {}
        omsx_repl.run_case(m, "stored", ["POKE&HC000,201",
                                          "S=0:FOR I=&HEE40 TO &HEF3F:S=S+PEEK(I):NEXT",
                                          "POKE&HC000,202"],
                           sentinel=(0xC000, 202), sentinel_capture=True,
                           cap_gap=60.0, timeout=300.0, settle_out=so)
        mk = so.get("marks", {}).get(0, [])
        t1 = [t for t, v in mk if v == 201]
        t2 = [t for t, v in mk if v == 202]
        print(f"   (a) SUM loop: {t2[0] - t1[0]:.2f} s" if t1 and t2 else "   (a) NO MARKS", flush=True)
        raw = omsx_repl.run_cases(m, [("direct", [LOOP, 'PRINT "AHEAD"'])], batch=False,
                                  reset=("",), run_gap=40.0)[0]
        txt, printed = outcome(raw)
        print(f"   (b) KEYBUF  : printed {printed}   | {txt[-120:]}", flush=True)
        raw = omsx_repl.run_cases(m, [("direct", [LOOP])], batch=False, reset=("",),
                                  run_gap=40.0,
                                  prologue=('after time 11.5 { type "PRINT \\"AHEAD\\"\\r" }',))[0]
        txt, printed = outcome(raw)
        print(f"   (c) keyboard: printed {printed}   | {txt[-120:]}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
