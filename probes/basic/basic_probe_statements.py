#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""REM / POKE / PEEK statement probe — validate the zerobas implementation.

Boots the zerobas cartridge (it needs `--cart`; there is no built-in BASIC
equivalent for these direct-mode lines on the reference, which tokenises numbers
differently — see spec-tokens-statements.md), types a line into its REPL, and
checks the result by dumping RAM. No PRINT is needed: POKE writes to memory and
we read it back.

Two capture modes:

  * BLOAD-landmark (deterministic): statements that run *before* a trailing
    `bload"cas:",r` execute, then the loaded blob's `JR $` landmark
    (LANDMARK) fires and freezes RAM. Also exercises the `:` statement loop.
  * --time (for REM): REM swallows the rest of the line *including* any trailing
    bload, so there is no landmark to break on. We type the line, let emulated
    time elapse, then dump RAM. The fake POKE hidden in the comment must NOT
    have run.

POKEs target 0xD000 — clear of the blob (0xC000..) and its JONG marker (0xE000).
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra

import argparse
import os
import subprocess
import sys
import tempfile


from basic_probe_bload import build_blob, LOAD_ADDR, LANDMARK  # noqa: E402
from cas_encode import build_cas  # noqa: E402

OMSX_RUN = os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib", "omsx_run.py")
# ⚠️ zerobas now runs on the REPACK machine, which carries the merged main ROM in
# slot 0 -- there is no cartridge to insert. It used to be C-BIOS_MSX1 (or the
# VG-8020) with the retired lean 16 KB cart in a slot; that build is gone
# (RETIRE THE LEAN 16 KB CART S3, docs/spec-lean-retire-s3-gates.md).
MACHINE = "C-BIOS_MSX1_EU_REPACK_DISK"
T = 0xD000  # POKE target, free RAM


def run(machine, cas, line, mems, bp=None, secs=None, type_delay=8):
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="stmt_cap_")
    os.close(out_fd)
    cmd = [sys.executable, OMSX_RUN, "--machine", machine]
    if cas:
        cmd += ["--cassette", cas]
    # zerobas REPL: type the line, then a separately-timed Enter (a trailing CR
    # in the same burst is dropped under `throttle off`).
    cmd += ["--type", line, "--type-delay", str(type_delay),
            "--type", "\r", "--type-delay", str(type_delay + 4)]
    if bp is not None:
        cmd += ["--bp", hex(bp), "--reg", "PC"]
    else:
        cmd += ["--time", str(secs)]
    for m in mems:
        cmd += ["--mem", m]
    cmd += ["--out", out_path, "--timeout", "120"]
    rc = subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cap = ""
    if os.path.exists(out_path):
        with open(out_path) as f:
            cap = f.read()
        os.unlink(out_path)
    return rc, cap


def memval(cap, addr, length):
    key = f"mem.memory:0x{addr:04X}:{length}="
    for line in cap.splitlines():
        if line.startswith(key):
            return line[len(key):]
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=MACHINE)
    args = ap.parse_args()

    cas = build_cas("BLOAD", LOAD_ADDR, LOAD_ADDR, build_blob())
    cas_fd, cas_path = tempfile.mkstemp(suffix=".cas", prefix="stmt_probe_")
    os.write(cas_fd, cas)
    os.close(cas_fd)

    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL'}  {label}" + (f"  {detail}" if detail else ""))
        if not cond:
            ok = False

    # 1. POKE + BLOAD landmark: poke runs, then bload hands off to the blob.
    rc, cap = run(args.machine, cas_path,
                  f'poke &h{T:04x},65:bload"cas:",r', [f"memory:0x{T:04X}:1"],
                  bp=LANDMARK)
    check("POKE &Hd000,65 then BLOAD,R",
          memval(cap, T, 1) == "41" and f"reg.PC=0x{LANDMARK:04X}" in cap,
          f"D000={memval(cap, T, 1)} PC@landmark={'yes' if f'0x{LANDMARK:04X}' in cap else 'no'}")

    # 2. PEEK + variable + multi-statement.
    rc, cap = run(args.machine, cas_path,
                  f'poke &h{T:04x},123:a=peek(&h{T:04x}):poke &h{T+1:04x},a:bload"cas:",r',
                  [f"memory:0x{T:04X}:2"], bp=LANDMARK)
    check("a=PEEK(...) round-trip", memval(cap, T, 2) == "7b7b",
          f"D000..1={memval(cap, T, 2)}")

    # 3. Arithmetic precedence: 2*3+4 == 10 (proves * binds tighter than +).
    rc, cap = run(args.machine, cas_path,
                  f'poke &h{T:04x},2*3+4:bload"cas:",r', [f"memory:0x{T:04X}:1"],
                  bp=LANDMARK)
    check("2*3+4 == 10", memval(cap, T, 1) == "0a", f"D000={memval(cap, T, 1)}")

    # 4. REM swallows the rest of the line (--time; the fake poke must not run).
    rc, cap = run(args.machine, None,
                  f'poke &h{T:04x},5:rem poke &h{T:04x},99', [f"memory:0x{T:04X}:1"],
                  secs=18)
    check("REM ignores trailing 'poke ...,99'", memval(cap, T, 1) == "05",
          f"D000={memval(cap, T, 1)}")

    # 5. ' (apostrophe) behaves as REM.
    rc, cap = run(args.machine, None,
                  f"poke &h{T:04x},6:'poke &h{T:04x},88", [f"memory:0x{T:04X}:1"],
                  secs=18)
    check("' ignores trailing 'poke ...,88'", memval(cap, T, 1) == "06",
          f"D000={memval(cap, T, 1)}")

    os.unlink(cas_path)
    print("\nALL PASS" if ok else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
