#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FATFLOOR: is docs/concepts/memory-map.md's example still true?

The page said `CLEAR 25000` is accepted on the VG-8020 and `Out of memory` on
diskless zerobas. D-FATFLOOR gave the diskless build 1024 B (boot FRE(0)
24711 -> 25735), so the claim is re-run, not carried: CLEAR n then FRE(0),
on both, for three sizes.

Prediction (2026-10-13): the VG-8020 accepts all three; zerobas accepts 25000
and refuses 26000 and 28000.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
os.environ.setdefault("ZEROBAS_REFCACHE", "0")
import omsx_repl  # noqa: E402

MACHINES = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")
SIZES = (25000, 26000, 28000)


def run(machine, n):
    line = '?"["FRE(0)"]"'
    raw = omsx_repl.run_cases(machine, [("direct", ["SCREEN 0", f"CLEAR {n}", line])],
                              batch=False, reset=("",), run_gap=6.0)[0]
    if not raw:
        return None, None
    oom = "Out of memory" in raw
    span = omsx_repl.result_span_after_echo(raw, line)
    fre = int(span) if span and span.strip().lstrip("-").isdigit() else None
    return oom, fre


def main():
    for m in MACHINES:
        for n in SIZES:
            oom, fre = run(m, n)
            verdict = ("INSTRUMENT FAULT" if fre is None else
                       "Out of memory" if oom else "accepted")
            print(f"{m:30s} CLEAR {n}: {verdict:16s} FRE(0) after = {fre}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
