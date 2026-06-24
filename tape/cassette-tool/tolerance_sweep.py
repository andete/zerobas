#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Sweep one degradation parameter and report the decode tolerance envelope.

Drives degrade_wav.py across a range of values for a single impairment, runs a
caller-supplied decode command on each degraded WAV, and prints the pass/fail
envelope plus the contiguous passing range. The decode step is a command
template (so this stays decoupled from any particular decoder): `{wav}` is
substituted with the degraded file's path and the command must exit 0 on a
successful decode.

Example -- map the zerobas-tape read path's speed-error lock range:

  python3 cassette-tool/tolerance_sweep.py clean.wav \\
    --param speed --values=-30,-20,-10,0,10,20,30 \\
    --decode 'python3 probes/lib/omsx_run.py --machine C-BIOS_MSX1_EU_TAPE \\
       --cart /tmp/fileR.rom --cassette {wav} --bp 0x7FF0 \\
       --mem memory:0xE000:28 --out /tmp/c.txt >/dev/null 2>&1 && \\
       python3 probes/tape/bios_probe_tapfile.py --analyze /tmp/c.txt | grep -q "^MATCH"'

`--base` passes extra fixed degrade_wav.py args applied on every run (e.g. a
background "--noise 0.03"). Parameters that take HZ:PCT (wow) accept those values
verbatim in --values.
"""
from __future__ import annotations

import argparse, os, shlex, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEGRADE = os.path.join(HERE, "degrade_wav.py")


def run(clean: str, param: str, value: str, base: list[str], decode: str) -> bool:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        out = tf.name
    try:
        cmd = [sys.executable, DEGRADE, clean, out, f"--{param}", value, *base]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            sys.stderr.write(r.stderr)
            raise SystemExit(f"degrade_wav.py failed for {param}={value}")
        dec = decode.replace("{wav}", shlex.quote(out))
        return subprocess.run(dec, shell=True).returncode == 0
    finally:
        os.unlink(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clean", help="clean baseline WAV")
    ap.add_argument("--param", required=True,
                    help="degrade_wav.py parameter to sweep (speed/lowpass/bias/gain/noise/wow)")
    ap.add_argument("--values", required=True,
                    help="comma-separated values for the parameter")
    ap.add_argument("--decode", required=True,
                    help="shell command to decode {wav}; exit 0 == pass")
    ap.add_argument("--base", default="",
                    help="extra fixed degrade_wav.py args applied every run")
    args = ap.parse_args()

    base = shlex.split(args.base)
    values = [v.strip() for v in args.values.split(",")]
    results: list[tuple[str, bool]] = []
    print(f"sweeping --{args.param} over {values}"
          + (f"  (base: {args.base})" if args.base else ""))
    for v in values:
        ok = run(args.clean, args.param, v, base, args.decode)
        results.append((v, ok))
        print(f"  {args.param} = {v:>8}: {'PASS' if ok else 'FAIL'}")

    passing = [v for v, ok in results if ok]
    if passing:
        print(f"passing: {passing[0]} .. {passing[-1]} "
              f"({len(passing)}/{len(results)})")
    else:
        print("passing: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
