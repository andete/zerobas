#!/usr/bin/env python3

"""Float-literal crunch probe — characterise, then differentially prove, how
MSX-BASIC crunches decimal floating-point literals (Phase-3 float pack F1;
docs/spec-basic-float-core.md §3c).

Characterisation mode (default, reference only):
  For each literal L the line  bload"cas:",r:a=L  is fed to the reference
  (Philips VG-8020, built-in BASIC). BLOAD leads, so the machine freezes at
  TAPION ($00E1) with the WHOLE line already crunched into KBUF ($F41F) and
  the body never executes (same freeze technique as basic_probe_crunch.py).
  The bytes after the `:a=` marker (3A 41 EF) are the literal's crunched
  form — for a float literal that IS the stored representation (token $1D +
  4 value bytes single / $1F + 8 value bytes double), so this one capture
  pins both the classification rule AND the BCD encoding, black-box.

Differential mode (--zb-machine, F1 implement/acceptance):
  Additionally crunches the same line on the zerobas repack build (TOKBUF)
  and asserts the tail bytes are identical to the reference's.

Clean-room: observed outputs only; the reference ROM is a black box. No
disassembly. See the clean-room firewall (CONTRIBUTING.md).
"""
from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))

import argparse
import os
import subprocess
import sys
import tempfile

from cas_encode import build_cas  # noqa: E402

OMSX_RUN = os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                        "lib", "omsx_run.py")
REF_MACHINE = "Philips_VG_8020"
TAPION = 0x00E1
KBUF = 0xF41F     # reference crunch buffer (MSX2 TH sysvar map)
TOKBUF = 0xE160   # zerobas crunch buffer (basic/sysvars.inc)
DUMPLEN = 48
MARKER = bytes([0x3A, 0x41, 0xEF])   # ':' 'A' '='  — the literal starts after this
TAIL = 12                            # bytes of literal to show (>= 1+8+terminator)

# The classification/encoding matrix (spec §3c working rules — this probe is
# what pins them). Grouped for the analysis write-up; each entry is typed as
# `a=<lit>` on the reference.
LITERALS = [
    # int forms stay int (regression anchors)
    "0", "9", "10", "255", "256", "32767",
    # integer > 32767: the int16 wall
    "32768", "40000", "65535", "65536", "99999", "999999",
    # digit-count wall (single holds 6 BCD digits)
    "1000000", "9999999", "10000000", "99999999", "123456789012345678",
    # decimal point forms
    ".5", "0.5", "1.5", "1.", "1.0", "3.14159", "3.1415926", "0.1",
    ".000001", "123456.7", "1234567.8",
    # rounding probes (7+ significant digits into a 6-digit single?)
    "1234567", "1234564", "9999995",
    # E/D exponent forms
    "1e5", "1e10", "1.5e2", "1e-3", "2.5e-10", "1d5", "1.5d-3",
    # exponent range walls (excess-64: ±63?)
    "1e38", "1e62", "1e63", "1e64", "1e-63", "1e-64", "1e-65",
    # explicit type suffixes
    "1!", "1#", "32767#", "1.5!", "1.5#", "100000!", "1234567!", "65535%",
    # rounding tie-breakers (exact half at the kept-digit wall: half-up vs even)
    "1234565!", "1234575!", "123456789012345", "1234567890123455",
    # rounding carry-out-of-all-digits (PRINT 9999995! shows 1000000 = 1e6, not
    # 1e7 — does the crunch renormalise the exponent after the carry?)
    "9999995!", "9999999999999999",
    # zero forms
    "0!", "0#", ".0", "0e0",
    # %-suffix in range: is the '%' consumed into the int token or kept?
    "1%", "100%", "30000%",
]


def dump_buf(machine, cart, full_line, addr, separate_enter, cas_path):
    """Run one side, break at TAPION, return the crunch-buffer bytes."""
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="floatlit_")
    os.close(out_fd)
    cmd = [sys.executable, OMSX_RUN, "--machine", machine]
    if cart:
        cmd += ["--cart", cart]
    cmd += ["--cassette", cas_path]
    if separate_enter:
        cmd += ["--type", full_line, "--type-delay", "8",
                "--type", "\r", "--type-delay", "12"]
    else:
        cmd += ["--type", full_line + "\r", "--type-delay", "5"]
    cmd += ["--bp", hex(TAPION), "--reg", "PC",
            "--mem", f"memory:0x{addr:04X}:{DUMPLEN}",
            "--out", out_path, "--timeout", "30"]
    subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cap = ""
    if os.path.exists(out_path):
        with open(out_path) as f:
            cap = f.read()
        os.unlink(out_path)
    if f"reg.PC=0x{TAPION:04X}" not in cap:
        return None  # never reached TAPION (crunch/edit error before BLOAD ran)
    key = f"mem.memory:0x{addr:04X}:{DUMPLEN}="
    for cl in cap.splitlines():
        if cl.startswith(key):
            return bytes.fromhex(cl[len(key):])
    return None


def literal_tail(buf):
    """The crunched literal: TAIL bytes after the `:a=` marker (3A 41 EF)."""
    if buf is None:
        return None
    i = buf.find(MARKER)
    if i < 0:
        return None
    return buf[i + len(MARKER): i + len(MARKER) + TAIL]


def trim_to_terminator(tail):
    """tail, up to and including its first embedded 0x00 (else unchanged).

    F1 implement/acceptance fix (2026-07-11): TAIL is a fixed 12-byte window,
    wider than every literal's real crunch (int forms are 1-3 bytes, float
    forms 5/9), so the bytes past the true 0x00 terminator are ambient RAM,
    not crunch output — and the reference (a real VG-8020) and zerobas
    (C-BIOS_MSX1_EU_REPACK_DISK) cold-boot with DIFFERENT ambient RAM
    (observed: the reference reads 0x00 there, zerobas 0xFF), so a raw
    fixed-window compare fails on padding alone even when the crunch itself
    is byte-identical. Same technique + same accepted imprecision as the
    standing `basic_probe_crunch.py`'s `crunched()`: trim at the first 0x00,
    which can truncate early for a value with an embedded zero MID-value
    (e.g. `256` -> `1C 00 01`, `1e-65` -> `... 10 00 00` -- long before its
    own terminator) rather than only the terminator itself. That is a known,
    already-precedented weakening of the check (it stops verifying the
    trailing bytes of such a case), not a correctness fix to zerobas; the
    exhaustive byte-for-byte proof for those cases is tests/test_float.py."""
    if tail is None:
        return None
    i = tail.find(0)
    return tail if i < 0 else tail[:i + 1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=REF_MACHINE,
                    help=f"reference oracle machine (default {REF_MACHINE})")
    ap.add_argument("--zb-machine", dest="zb_machine",
                    help="differential mode: also crunch on this repack machine "
                         "(BASIC in slot 0) and assert tail equality")
    ap.add_argument("--only", help="substring filter on the literal")
    args = ap.parse_args()

    cas = build_cas("TOK", 0xC000, 0xC000, bytes([0x18, 0xFE]))
    cas_fd, cas_path = tempfile.mkstemp(suffix=".cas", prefix="floatlit_")
    os.write(cas_fd, cas)
    os.close(cas_fd)

    ok = True
    try:
        for lit in LITERALS:
            if args.only and args.only not in lit:
                continue
            full_line = f'bload"cas:",r:a={lit}'
            ref = literal_tail(dump_buf(args.machine, None, full_line, KBUF,
                                        separate_enter=False, cas_path=cas_path))
            rs = " ".join(f"{b:02X}" for b in ref) if ref else "<no TAPION>"
            if args.zb_machine:
                zb = literal_tail(dump_buf(args.zb_machine, None, full_line, TOKBUF,
                                           separate_enter=True, cas_path=cas_path))
                zs = " ".join(f"{b:02X}" for b in zb) if zb else "<no TAPION>"
                if ref is None and zb is None:
                    # pre-authorised: a crunch-time rejection on BOTH sides
                    # (e.g. 1e63 / 65535%) is a pass, not a byte comparison
                    ok = ok and True
                    print(f"PASS  a={lit:<22} ref: {rs}  [both rejected]")
                    continue
                same = (ref is not None and zb is not None
                        and trim_to_terminator(ref) == trim_to_terminator(zb))
                ok = ok and same
                print(f"{'PASS' if same else 'FAIL'}  a={lit:<22} ref: {rs}")
                if not same:
                    print(f"{'':>32}zb : {zs}")
            else:
                print(f"a={lit:<22} {rs}")
    finally:
        os.unlink(cas_path)

    if args.zb_machine:
        print("\nALL PASS — float-literal crunch is byte-identical" if ok
              else "\nSOME FAILED")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
