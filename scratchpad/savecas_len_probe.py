#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-SESSIONS TIER 5 follow-up: SAVE "CAS:" of a 2-line program -- is the VG-8020's tape
LONGER than zerobas's, or the same tape written slower? Each machine records to a blank
tape; the WAV's length (seconds) and its decoded bytes (probes/lib/cas_decode.py) are
compared, plus where the signal is silent. Black box: the recorded signal only.

    python3 -u scratchpad/savecas_len_probe.py
"""
import os, sys, wave
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl, probe_tmp                       # noqa: E402
from cas_decode import decode_file, read_samples, zero_crossings  # noqa: E402


def segments(path):
    """Signal segments: zero crossings closer than 5 ms belong together."""
    smp, fr = read_samples(path)
    xs = zero_crossings(smp)
    if not xs:
        return fr, []
    gap, out, st, pv = int(fr * 0.005), [], xs[0], xs[0]
    for x in xs[1:]:
        if x - pv > gap:
            out.append((st / fr, pv / fr))
            st = x
        pv = x
    out.append((st / fr, pv / fr))
    return fr, out

PROG = ["NEW", '10 PRINT "TAPE SESSION"', "20 FOR I=1 TO 3:PRINT I*11:NEXT",
        'SAVE "CAS:ASC"', "@WAIT20"]
ref = b""
for side, m in (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK")):
    wav = probe_tmp.tmp(f"savecas_{side}.wav")
    if os.path.exists(wav):
        os.remove(wav)
    omsx_repl.run_cases(m, [("direct", PROG)], batch=False, reset=("", "SCREEN 0"),
                        prologue=(f"cassetteplayer new {{{wav}}}",), step=3.0, run_gap=25.0)
    with wave.open(wav) as w:
        secs = w.getnframes() / w.getframerate()
    data, info = decode_file(wav)
    fr, segs = segments(wav)
    print(f"{side}: {secs:.2f} s of tape, {len(data)} bytes decoded "
          f"({'the same' if side == 'ZB' and bytes(data) == ref else bytes(data)[:16].hex()})", flush=True)
    if side == "VG":
        ref = bytes(data)
    for a, b in segs:
        print(f"   signal {a:7.3f} .. {b:7.3f}  ({b - a:.3f} s)", flush=True)
