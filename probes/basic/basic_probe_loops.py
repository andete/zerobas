#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Loop / subroutine execution probe — validate zerobas GOSUB/RETURN and
FOR/NEXT (Step B) by running real stored programs on openMSX.

Like basic_probe_controlflow.py, each program POKEs sentinels to free RAM
($D000..) and we read them back after the run. A direct `bload"cas:",r` whose
blob ends in `JR $` (LANDMARK) freezes RAM deterministically and proves the
program terminated — a runaway loop (missed NEXT test, lost RETURN) never
reaches the freeze and fails fast on the host watchdog.

Most checks cover *universal* semantics — a 1..5 loop runs five times,
GOSUB/RETURN nest, RETURN resumes mid-line — outcomes no BASIC dialect disagrees
on. One edge (the empty loop `for i=2 to 1`) is dialect-sensitive: whether the
body runs zero or one time. That was settled by *observing the oracle* — a real
Philips VG-8020, driven in direct mode:

    poke&hd000,0:for i=2 to 1:poke&hd000,1:next i:poke&hd001,i
      -> D000 = 01 (body ran once), i = 03

i.e. MSX-BASIC's FOR is bottom-tested: the body always runs at least once, the
limit test happens at NEXT. (The reference can't be driven through a stored
program + RUN via this harness — only its direct-execution path is reachable —
so that oracle value is recorded here as the expected outcome rather than
re-derived live each run.) zerobas's stored-program FOR must reproduce it.

Clean-room: observed inputs/outputs only; the reference ROM is a black box. See
the clean-room firewall (CONTRIBUTING.md) and docs/test-strategy-stepb.md.
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
T = 0xD000      # sentinels in free RAM (clear of the $C000 blob / $E000 marker)
U = 0xD001
V = 0xD002


def run_program(machine, cart, cas, prog, mems, base=8.0, step=4.0):
    """Type numbered lines, RUN, then a direct bload to freeze at LANDMARK.

    Targets the zerobas REPL, whose CHGET loop needs each Enter injected as a
    separate, later event under `throttle off` (a trailing CR in the same burst
    is dropped). The built-in reference BASIC isn't driven here: this harness
    can't reach its stored-program RUN path, only its direct-execution path.
    """
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="loop_cap_")
    os.close(out_fd)
    cmd = [sys.executable, OMSX_RUN, "--machine", machine, "--cassette", cas,
           "--cart", cart]
    events = []
    for line in list(prog) + ["run", 'bload"cas:",r']:
        events += [line, "\r"]
    t = base
    for text in events:
        cmd += ["--type", text, "--type-delay", f"{t:g}"]
        t += step
    cmd += ["--bp", hex(LANDMARK), "--reg", "PC"]
    for m in mems:
        cmd += ["--mem", m]
    # A healthy run hits LANDMARK in well under a second; cap low so a hang
    # (runaway loop) fails fast instead of stalling on the watchdog.
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
    cas_fd, cas_path = tempfile.mkstemp(suffix=".cas", prefix="loop_probe_")
    os.write(cas_fd, cas)
    os.close(cas_fd)

    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL'}  {label}" + (f"  {detail}" if detail else ""))
        ok = ok and cond

    def zb(prog, addrs):
        mems = [f"memory:0x{a:04X}:1" for a in addrs]
        cap = run_program(args.machine, args.cart, cas_path, prog, mems)
        return {a: memval(cap, a, 1) for a in addrs}, reached_landmark(cap)

    # 1. GOSUB runs the subroutine; RETURN comes back to the line after GOSUB.
    vals, lm = zb([f"10 poke &h{T:04x},0", "20 gosub 100",
                   f"30 poke &h{U:04x},5", "40 end",
                   f"100 poke &h{T:04x},9", "110 return"], [T, U])
    check("GOSUB runs sub, RETURN resumes at next line",
          vals[T] == "09" and vals[U] == "05" and lm,
          f"T={vals[T]} U={vals[U]} landmark={lm}")

    # 2. Nested GOSUB: 100 calls 200, both RETURNs unwind in order.
    vals, lm = zb([f"10 poke &h{T:04x},0", "20 gosub 100", "30 end",
                   f"100 poke &h{T:04x},1", "110 gosub 200",
                   f"120 poke &h{U:04x},2", "130 return",
                   f"200 poke &h{V:04x},3", "210 return"], [T, U, V])
    check("nested GOSUB unwinds in order",
          vals[T] == "01" and vals[U] == "02" and vals[V] == "03",
          f"T={vals[T]} U={vals[U]} V={vals[V]}")

    # 3. RETURN resumes *mid-line* — the statement after GOSUB on the same line.
    vals, lm = zb([f"10 poke &h{T:04x},0:gosub 100:poke &h{U:04x},7",
                   "20 end", f"100 poke &h{T:04x},3", "110 return"], [T, U])
    check("RETURN resumes mid-line after GOSUB",
          vals[T] == "03" and vals[U] == "07", f"T={vals[T]} U={vals[U]}")

    # 4. FOR i=1 TO 5 runs the body five times; i ends at 6.
    vals, lm = zb(["10 s=0", "20 for i=1 to 5", "30 s=s+1", "40 next i",
                   f"50 poke &h{T:04x},s", f"60 poke &h{U:04x},i", "70 end"], [T, U])
    check("FOR 1 TO 5 -> 5 trips, i ends 6",
          vals[T] == "05" and vals[U] == "06", f"trips={vals[T]} i={vals[U]}")

    # 5. STEP 2 over 0..10 -> 6 trips (0,2,4,6,8,10); i ends at 12.
    vals, lm = zb(["10 s=0", "20 for i=0 to 10 step 2", "30 s=s+1", "40 next i",
                   f"50 poke &h{T:04x},s", f"60 poke &h{U:04x},i", "70 end"], [T, U])
    check("FOR 0 TO 10 STEP 2 -> 6 trips, i ends 12",
          vals[T] == "06" and vals[U] == "0c", f"trips={vals[T]} i={vals[U]}")

    # 6. Negative STEP counts down 5..1 -> 5 trips; i ends at 0.
    vals, lm = zb(["10 s=0", "20 for i=5 to 1 step -1", "30 s=s+1", "40 next i",
                   f"50 poke &h{T:04x},s", f"60 poke &h{U:04x},i", "70 end"], [T, U])
    check("FOR 5 TO 1 STEP -1 -> 5 trips, i ends 0",
          vals[T] == "05" and vals[U] == "00", f"trips={vals[T]} i={vals[U]}")

    # 7. Single-line FOR..NEXT (mid-line resume into the body after FOR).
    vals, lm = zb(["10 s=0", f"20 for i=1 to 4:s=s+1:next i",
                   f"30 poke &h{T:04x},s", "40 end"], [T])
    check("single-line FOR..NEXT -> 4 trips", vals[T] == "04", f"trips={vals[T]}")

    # 8. Nested FOR..NEXT: inner runs to completion each outer trip (3*4 = 12).
    vals, lm = zb(["10 s=0", "20 for i=1 to 3", "30 for j=1 to 4",
                   "40 s=s+1", "50 next j", "60 next i",
                   f"70 poke &h{T:04x},s", "80 end"], [T])
    check("nested FOR..NEXT -> 12 trips", vals[T] == "0c", f"trips={vals[T]}")

    # 9. Empty loop `for i=2 to 1` (init already past limit, positive step).
    #    Oracle (VG-8020, direct mode): body runs once, i ends at 3 — MSX-BASIC's
    #    FOR is bottom-tested. zerobas's stored-program FOR must agree.
    vals, lm = zb([f"10 poke &h{T:04x},0", "20 for i=2 to 1",
                   f"30 poke &h{T:04x},1", "40 next i",
                   f"50 poke &h{U:04x},i", "60 end"], [T, U])
    check("empty loop runs body once, i ends 3 (oracle: bottom-tested)",
          vals[T] == "01" and vals[U] == "03", f"body={vals[T]} i={vals[U]}")

    os.unlink(cas_path)
    print("\nALL PASS" if ok else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
