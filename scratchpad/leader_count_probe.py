#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TAPOONDLY follow-up: how many leader cycles does TAPOON write -- long (A <> 0) and short
(A = 0) -- on the VG-8020 and on zerobas? Our own code calls TAPOON, TAPOUT x 4 ($00) and
TAPOOF; the recording's first signal segment is the leader: SHORT half-periods (the high
tone) up to the first LONG one (the start bit of the first byte). Counted as cycles (two
halves each). Black box: the recorded signal only.

    python3 -u scratchpad/leader_count_probe.py
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl, probe_tmp                                    # noqa: E402
from cas_decode import read_samples, zero_crossings, half_periods, auto_threshold  # noqa: E402

TAPOON, TAPOUT, TAPOOF = 0x00EA, 0x00ED, 0x00F0
BAUD = int(sys.argv[1]) if len(sys.argv) > 1 else 1    # SCREEN ,,,1 = 1200, ,,,2 = 2400


def code(a):
    c = [0x3E, a, 0xCD, TAPOON & 255, TAPOON >> 8]
    for _ in range(4):
        c += [0x3E, 0x00, 0xCD, TAPOUT & 255, TAPOUT >> 8]
    return c + [0xCD, TAPOOF & 255, TAPOOF >> 8, 0xFB, 0xC9]


def leader(path):
    smp, fr = read_samples(path)
    hp = half_periods(zero_crossings(smp))
    thr = auto_threshold(hp)
    n = 0
    for h in hp:
        if h > thr:
            break
        n += 1
    short = [h for h in hp[:n]]
    return n // 2, (sum(short) / len(short) / fr * 2) if short else 0, sum(short) / fr


for a, label in ((1, "long"), (0, "short")):
    for side, m in (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK")):
        wav = probe_tmp.tmp(f"leader_{label}_{side}.wav")
        if os.path.exists(wav):
            os.remove(wav)
        c = code(a)
        # the active LOW / HIGH / HEADER from the chosen reference table, POKEd on BOTH
        # machines (zerobas's SCREEN ,,,n does not copy it -- a separate gap)
        prog = ["NEW", "10 CLEAR 200,&HCFFF:" + (f"FOR I=0 TO 4:POKE &HF406+I,PEEK(&HF401+I):NEXT"
                                                    if BAUD == 2 else "REM"),
                f"20 FOR I=0 TO {len(c) - 1}:READ X:POKE &HD000+I,X:NEXT",
                "30 DEFUSR=&HD000:Q=USR(0)", "40 DATA " + ",".join(map(str, c)), "RUN", "@WAIT12"]
        omsx_repl.run_cases(m, [("direct", prog)], batch=False, reset=("", "SCREEN 0"),
                            prologue=(f"cassetteplayer new {{{wav}}}",), step=3.0, run_gap=15.0)
        cyc, period, secs = leader(wav)
        print(f"{label:5} {side}: {cyc} leader cycles, {secs:.3f} s "
              f"({1 / period:.0f} Hz)" if period else f"{label:5} {side}: no leader", flush=True)
