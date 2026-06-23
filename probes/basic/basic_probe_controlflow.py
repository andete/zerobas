#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Control-flow execution probe — validate zerobas Step B (GOTO / IF…THEN…ELSE /
END/STOP / comparisons) by running real stored programs on openMSX.

zerobas has no PRINT, so each program POKEs a sentinel to free RAM ($D000) and we
read it back after the run. A low line that always runs pre-zeroes the sentinel,
so a *skipped* branch (sentinel still 0) is distinguishable from one that *ran*.

Each test types numbered lines into the zerobas REPL, then `RUN`, then a direct
`bload"cas:",r` whose loaded blob ends in `JR $` (LANDMARK) — that handoff both
freezes RAM deterministically and proves the program terminated (no hang). RAM is
then dumped at the breakpoint. These are self-checking assertions (spec-defined
outcomes), not a reference differential — the reference tokenises integers
differently and also lacks a comparable direct-mode path here.

Clean-room: observed inputs/outputs only. See the clean-room firewall (CONTRIBUTING.md)
and docs/test-strategy-stepb.md.
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
MACHINE = "Philips_VG_8020"
T = 0xD000      # sentinel, free RAM (clear of the $C000 blob / $E000 JONG marker)
U = 0xD001
ERRMARK = 0xE010


def run_program(machine, cart, cas, prog, mems, base=8.0, step=4.0):
    """Type numbered lines, RUN, then a direct bload to freeze at LANDMARK."""
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="cf_cap_")
    os.close(out_fd)
    cmd = [sys.executable, OMSX_RUN, "--machine", machine, "--cart", cart,
           "--cassette", cas]
    # Each numbered line + a separately-timed Enter (a trailing CR in the same
    # burst is dropped under `throttle off`), then RUN, then the freeze line.
    events = []
    for line in list(prog) + ["run", 'bload"cas:",r']:
        events.append(line)
        events.append("\r")
    t = base
    for text in events:
        cmd += ["--type", text, "--type-delay", f"{t:g}"]
        t += step
    cmd += ["--bp", hex(LANDMARK), "--reg", "PC"]
    for m in mems:
        cmd += ["--mem", m]
    # A healthy run hits LANDMARK in well under a second; cap low so a hang
    # (e.g. a malformed program that loops) fails fast instead of stalling.
    cmd += ["--out", out_path, "--timeout", "30"]
    subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cap = ""
    if os.path.exists(out_path):
        with open(out_path) as f:
            cap = f.read()
        os.unlink(out_path)
    return cap


def memval(cap, addr, length):
    key = f"mem.memory:0x{addr:04X}:{length}="
    for line in cap.splitlines():
        if line.startswith(key):
            return line[len(key):]
    return None


def reached_landmark(cap):
    return f"reg.PC=0x{LANDMARK:04X}" in cap


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=MACHINE)
    ap.add_argument("--cart", required=True, help="zerobas basic.rom")
    args = ap.parse_args()

    cas = build_cas("BLOAD", LOAD_ADDR, LOAD_ADDR, build_blob())
    cas_fd, cas_path = tempfile.mkstemp(suffix=".cas", prefix="cf_probe_")
    os.write(cas_fd, cas)
    os.close(cas_fd)

    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL'}  {label}" + (f"  {detail}" if detail else ""))
        ok = ok and cond

    # 1. GOTO skips a line and lands on the target.
    cap = run_program(args.machine, args.cart, cas_path,
                      [f"10 poke &h{T:04x},0", "20 goto 40",
                       f"30 poke &h{T:04x},99", f"40 poke &h{U:04x},1"],
                      [f"memory:0x{T:04X}:2"])
    check("GOTO skips line 30, lands on 40", memval(cap, T, 2) == "0001",
          f"D000..1={memval(cap, T, 2)} landmark={reached_landmark(cap)}")

    # 2. GOTO to a non-existent line -> undefined-line landmark $DB at ERRMARK.
    cap = run_program(args.machine, args.cart, cas_path,
                      [f"10 poke &h{T:04x},0", "20 goto 999"],
                      [f"memory:0x{ERRMARK:04X}:1", f"memory:0x{T:04X}:1"])
    check("GOTO 999 -> undefined-line $DB",
          memval(cap, ERRMARK, 1) == "db" and memval(cap, T, 1) == "00",
          f"E010={memval(cap, ERRMARK, 1)} D000={memval(cap, T, 1)}")

    # 3. IF true runs the THEN statement.
    cap = run_program(args.machine, args.cart, cas_path,
                      [f"10 poke &h{T:04x},0", f"20 if 1 then poke &h{T:04x},42"],
                      [f"memory:0x{T:04X}:1"])
    check("IF 1 THEN <poke> runs", memval(cap, T, 1) == "2a", f"D000={memval(cap, T, 1)}")

    # 4. IF false skips the THEN statement.
    cap = run_program(args.machine, args.cart, cas_path,
                      [f"10 poke &h{T:04x},0", f"20 if 0 then poke &h{T:04x},42"],
                      [f"memory:0x{T:04X}:1"])
    check("IF 0 THEN <poke> skipped", memval(cap, T, 1) == "00", f"D000={memval(cap, T, 1)}")

    # 5. IF false takes the ELSE clause.
    cap = run_program(args.machine, args.cart, cas_path,
                      [f"10 poke &h{T:04x},0",
                       f"20 if 0 then poke &h{T:04x},1 else poke &h{T:04x},2"],
                      [f"memory:0x{T:04X}:1"])
    check("IF 0 ... ELSE runs", memval(cap, T, 1) == "02", f"D000={memval(cap, T, 1)}")

    # 6. IF true runs THEN and skips ELSE.
    cap = run_program(args.machine, args.cart, cas_path,
                      [f"10 poke &h{T:04x},0",
                       f"20 if 1 then poke &h{T:04x},1 else poke &h{T:04x},2"],
                      [f"memory:0x{T:04X}:1"])
    check("IF 1 THEN ... skips ELSE", memval(cap, T, 1) == "01", f"D000={memval(cap, T, 1)}")

    # 7. tok_skip stress: the skipped THEN clause holds &HA100 (operand bytes
    #    00 A1) — the A1 must NOT be mistaken for the ELSE token.
    cap = run_program(args.machine, args.cart, cas_path,
                      [f"10 poke &h{T:04x},0",
                       f"20 if 0 then poke &ha100,1 else poke &h{T:04x},2"],
                      [f"memory:0x{T:04X}:1"])
    check("ELSE skip steps over &HA100 operand", memval(cap, T, 1) == "02",
          f"D000={memval(cap, T, 1)}")

    # 8. IF ... THEN <line> (implicit GOTO form).
    cap = run_program(args.machine, args.cart, cas_path,
                      [f"10 poke &h{T:04x},0", "20 if 5 then 40",
                       f"30 poke &h{T:04x},99", f"40 poke &h{T:04x},5"],
                      [f"memory:0x{T:04X}:1"])
    check("IF 5 THEN 40 branches", memval(cap, T, 1) == "05", f"D000={memval(cap, T, 1)}")

    # 9. END stops the run before later lines.
    cap = run_program(args.machine, args.cart, cas_path,
                      [f"10 poke &h{T:04x},7", "20 end", f"30 poke &h{T:04x},99"],
                      [f"memory:0x{T:04X}:1"])
    check("END stops before line 30", memval(cap, T, 1) == "07", f"D000={memval(cap, T, 1)}")

    # 10. Comparison operator in a condition: A>=7 with A=7 is true.
    cap = run_program(args.machine, args.cart, cas_path,
                      [f"10 poke &h{T:04x},0", "20 a=7",
                       f"30 if a>=7 then poke &h{T:04x},55"],
                      [f"memory:0x{T:04X}:1"])
    check("IF A>=7 (A=7) true", memval(cap, T, 1) == "37", f"D000={memval(cap, T, 1)}")

    os.unlink(cas_path)
    print("\nALL PASS" if ok else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
