#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Does the BIOS maintain NEWKEY ($FBE5), the per-frame keyboard-matrix snapshot?

INTFLG ($FC9B) was MEASURED dead on the zerobas target (C-BIOS writes it once, at
boot), so the reference's break mechanism is unavailable. NEWKEY is the other
published per-frame product of the ISR's keyboard scan, and a run loop that reads
it pays a bit test instead of BREAKX's full matrix walk. Measure it: sample
NEWKEY+6 (bit 1 = CTRL) and NEWKEY+7 (bit 4 = STOP) before, during and after an
injected Ctrl-STOP, on zerobas AND on the CF-3300 as the control.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl, probe_sides, probe_tmp

T0 = 24.0
PROG = ['10 FOR I=1 TO 30000:NEXT', '20 PRINT"[ran to the end]"', 'RUN']

for side in ("cf3300", "zb"):
    cfg = probe_sides.sides(side)[side]
    log = probe_tmp.tmp(f"newkey_{side}.log")
    pro = (f'set ::lf [open "{log}" w]\n'
           f'proc rd {{t}} {{ puts $::lf "$t [debug read memory 0xFBEB] [debug read memory 0xFBEC]" }}\n'
           f'after time {T0}      {{ rd before }}\n'
           f'after time {T0+0.3}  {{ keymatrixdown 6 0x02 ; keymatrixdown 7 0x10 }}\n'
           f'after time {T0+0.9}  {{ rd held }}\n'
           f'after time {T0+1.2}  {{ keymatrixup 6 0x02 ; keymatrixup 7 0x10 }}\n'
           f'after time {T0+1.8}  {{ rd after ; flush $::lf ; close $::lf }}\n')
    cap = omsx_repl.run_cases(cfg["machine"], [("nk", PROG)], batch=False, boot=cfg["boot"],
                              reset=cfg["reset"], prologue=(pro,), run_gap=T0 + 8) or [""]
    rows = [l.split() for l in open(log).read().strip().split("\n") if l.strip()]
    print(f"  {side}:")
    for r in rows:
        t, r6, r7 = r[0], int(r[1]), int(r[2])
        print(f"     {t:7} NEWKEY+6=${r6:02X} CTRL={'DOWN' if not r6 & 0x02 else 'up  '}"
              f"   NEWKEY+7=${r7:02X} STOP={'DOWN' if not r7 & 0x10 else 'up  '}")
    scr = (cap[0] or "").replace("\n", " ")
    print(f"     screen tail: {scr[-70:]!r}")
