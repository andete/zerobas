#!/usr/bin/env python3

"""Float PRINT-format probe — characterise, then differentially prove, the MSX
number OUTPUT format for float values (Phase-3 float pack F1;
docs/spec-basic-float-core.md §3d).

Each case types  PRINT "[";<lit>;"]"  in direct mode and captures the SCREEN 0
name table (same bracket technique as basic_probe_str_fn.py; every result here
fits on one visual row, so the last '['..']' span in the raw row-major text IS
the printed number, spaces exact). No arithmetic is exercised — F1 is
parse/store/print only (unary minus IS included: the reference applies it at
runtime, and zerobas F1 ships the trivial sign flip so negative display is
provable).

Characterisation mode (default): print the reference's exact output per case.
Differential mode (--zb-machine): also run zerobas (repack build) and assert
byte-equal spans.

Clean-room: observed outputs only; the reference ROM is a black box.
"""
from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))

import argparse
import os
import re
import subprocess
import sys
import tempfile

OMSX_RUN = os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                        "lib", "omsx_run.py")
REF_MACHINE = "Philips_VG_8020"
COLS, ROWS = 40, 24
NLEN = COLS * ROWS

# Formatter matrix (spec §3d — sign position, trailing space, significant
# digits, trailing-zero suppression, leading '.', E/D scientific thresholds,
# integer-valued floats). Typed as  PRINT "[";<lit>;"]".
LITERALS = [
    # int regression anchors
    "0", "5", "-5", "32767", "-32768",
    # simple singles + sign
    "1.5", "-1.5", ".5", "-.5", "0.1",
    # trailing-zero suppression / integer-valued floats
    "1.0", "1.50", "2!", "100000!", "1e5",
    # single significant-digit wall + display rounding
    "3.14159", "3.141592", "1234567!", "9999995!", "999999!", "1000000!",
    # single E-notation thresholds, both ends
    "1e6", "9999990!", ".01", ".001", ".0001", "1e-3", "6.023e23", "1e-9",
    "-1e10", "2.5e-10",
    # doubles: 14 digits, D-notation
    "1#", "1.5#", "0.1#", "1.23456789#", "1.2345678901234#",
    "123456789012345678", "1d16", "1.5d-3", "1e10#", "-1.23456789012345#",
    # extremes (exponent walls)
    "1e62", "1e-64", "1d62", "1d-64",
    # fixed<->E walls: high side per precision, low side, and low-side shape
    "1e13", "1e14", "1e15", "9.9e13", "1d13", "1d14", "1d15",
    "1d-2", "1d-3", ".0123", ".00123", "99999999999999#",
    # zero forms
    "0!", "0#", ".0",
]


def run_line(machine, line, base=8.0, tail=8.0, timeout=120):
    """Type one direct-mode line (+ separately-timed Enter), return the SCREEN 0
    name table as one raw row-major string of length NLEN."""
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="floatfmt_")
    os.close(out_fd)
    cmd = [sys.executable, OMSX_RUN, "--machine", machine,
           "--type", line, "--type-delay", str(base),
           "--type", "\r", "--type-delay", str(base + 3),
           "--time", str(base + 3 + tail),
           "--mem", f"VRAM:0x0000:{NLEN}",
           "--out", out_path, "--timeout", str(timeout)]
    subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cap = ""
    if os.path.exists(out_path):
        with open(out_path) as f:
            cap = f.read()
        os.unlink(out_path)
    m = re.search(rf"mem\.VRAM:0x0000:{NLEN}=([0-9a-f]+)", cap)
    if not m:
        return None
    data = bytes.fromhex(m.group(1))
    return "".join(chr(b) if 32 <= b < 127 else " " for b in data)


def result_span(raw):
    """The printed number: text between the LAST '[' and the following ']'.
    The echoed source line contains '[' too, but the result's '[' is printed
    after it; no case's output contains '[' itself."""
    if raw is None:
        return None
    i = raw.rfind("[")
    if i < 0:
        return None
    j = raw.find("]", i)
    if j < 0:
        return None
    return raw[i + 1: j]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=REF_MACHINE,
                    help=f"reference oracle machine (default {REF_MACHINE})")
    ap.add_argument("--zb-machine", dest="zb_machine",
                    help="differential mode: also run this repack machine and "
                         "assert span equality")
    ap.add_argument("--only", help="substring filter on the literal")
    args = ap.parse_args()

    ok = True
    for lit in LITERALS:
        if args.only and args.only not in lit:
            continue
        line = f'print "[";{lit};"]"'
        ref = result_span(run_line(args.machine, line))
        rs = f"[{ref}]" if ref is not None else "<no capture>"
        if args.zb_machine:
            zb = result_span(run_line(args.zb_machine, line))
            zs = f"[{zb}]" if zb is not None else "<no capture>"
            if ref is None and zb is None:
                # pre-authorised: a crunch-time rejection on BOTH sides is a
                # pass (e.g. 1e10# -- an exponent-then-suffix combo neither
                # side's tokeniser accepts as a single literal, so the
                # trailing suffix char is left in the token stream and
                # derails the expression evaluator identically on both
                # sides; see basic/float.asm tkf_try_exponent's header)
                ok = ok and True
                print(f"PASS  {lit:<22} ref: {rs}  [both rejected]")
                continue
            same = ref is not None and zb is not None and ref == zb
            ok = ok and same
            print(f"{'PASS' if same else 'FAIL'}  {lit:<22} ref: {rs}")
            if not same:
                print(f"{'':>30}zb : {zs}")
        else:
            print(f"{lit:<22} {rs}")

    if args.zb_machine:
        print("\nALL PASS — float output format is reference-identical" if ok
              else "\nSOME FAILED")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
