#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""CONT / Ctrl-STOP break probe — validate zerobas run-control on openMSX.

Exercises, on the default C-BIOS_MSX1 machine:

  (a) the STOP statement halts a RUNning program at its point in the line;
  (b) a direct CONT resumes the STOPped program (incl. across a line boundary);
  (c) CONT with nothing to continue reports "can't continue" (ERRMARK $C9):
      never ran, ran to completion with no STOP, or the program was edited
      since the break;
  (d) a real Ctrl-STOP key press breaks a *running loop* back to the REPL,
      where it is then observably alive again.

zerobas has no readable PRINT-to-RAM, so each program POKEs sentinels to free
RAM ($D000/$D001) and we read them back after the run. Capture is timing-robust:
we boot one openMSX per case, type the REPL lines on an emulated-time schedule
(`set throttle off`), and at a later fixed emulated time dump the sentinel /
ERRMARK bytes via `debug read_block`, then exit. (The earlier bload-LANDMARK
freeze used by the other functional probes proved unreliable here — after a
break/CONT the freeze line did not always land within the host watchdog — so
this probe uses fixed-time capture instead. Same clean-room methodology: observe
RAM after the program runs; the cartridge is a black box.)

Ctrl-STOP is a *key event*, not a typeable character. zerobas polls it with BIOS
BREAKX ($00B7) in its RUN loop (between statements/lines, and on every FOR/NEXT
iteration). openMSX exposes the key via the keyboard matrix; we press CTRL
(row 6 bit 1) + STOP (row 7 bit 4) for a short emulated window while a program
loops. The discriminator for (d) is an *infinite* loop (`goto`): a direct POKE
typed after the press can only execute if the break actually returned to the
REPL — without the press the loop never yields and the sentinel stays cleared.

Clean-room: observed inputs/outputs only. See the clean-room firewall (CONTRIBUTING.md).
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
import signal
import subprocess
import shutil
import sys
import tempfile
import time

from omsx_run import _tcl_dquote  # noqa: E402  (Tcl `type` literal: CR -> \r)

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
if not (os.path.sep in OMSX and os.path.isfile(OMSX)):
    OMSX = "openmsx"

# ⚠️ zerobas now runs on the REPACK machine, which carries the merged main ROM in
# slot 0 -- there is no cartridge to insert. It used to be C-BIOS_MSX1 (or the
# VG-8020) with the retired lean 16 KB cart in a slot; that build is gone
# (RETIRE THE LEAN 16 KB CART S3, docs/spec-lean-retire-s3-gates.md).
MACHINE = "C-BIOS_MSX1_EU_REPACK_DISK"
T = 0xD000          # sentinel A, free RAM (clear of any cart blob)
U = 0xD001          # sentinel B
ERRMARK = 0xE010    # zerobas error landmark byte
CANT_CONT = 0xC9    # ex_cont_no landmark ("can't continue")

# Keyboard-matrix coordinates of the Ctrl-STOP combination (MSX2 TH keyboard
# matrix): CTRL = row 6 bit 1; STOP = row 7 bit 4.
CTRL_ROW, CTRL_BIT = 6, 0x02
STOP_ROW, STOP_BIT = 7, 0x10


def run(cart, events, mems, ctrlstop_at=None, cap_at=None, timeout=70):
    """Boot one openMSX, replay `events`, capture `mems`, exit.

    events       : list of (emu_time, "text") REPL injections (Enter is its own
                   event, e.g. (8.0, "\\r")).
    mems         : list of (addr, length) blocks to dump at capture time.
    ctrlstop_at  : optional emu_time to press CTRL+STOP (held ~1.5 s).
    cap_at       : emu_time at which to dump `mems` and exit (defaults to last
                   event + 7 s).
    Returns {hex(addr): "hh.." } for each requested block (missing -> None).
    """
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="cont_cap_")
    os.close(out_fd)
    if cap_at is None:
        cap_at = (max((t for t, _ in events), default=6.0)) + 7.0
    lines = [
        "set throttle off",
        "proc __hex {dbg addr len} {",
        "  binary scan [debug read_block $dbg $addr $len] H* h; return $h",
        "}",
        "proc __cap {} {",
        f"  set f [open {{{os.path.abspath(out_path)}}} w]",
    ]
    for addr, length in mems:
        lines.append(
            f'  puts $f "mem.0x{addr:04X}=[__hex {{memory}} {addr} {length}]"')
    lines += ["  close $f", "  exit", "}"]
    for t, text in events:
        # A literal CR byte inside the Tcl `type` argument gets mangled and the
        # Enter keystroke is lost, so render via omsx_run's Tcl-quoter (CR -> \r).
        lines.append(f'after time {t:g} {{ type {_tcl_dquote(text)} }}')
    if ctrlstop_at is not None:
        lines.append(f'after time {ctrlstop_at:g} {{ keymatrixdown {CTRL_ROW} {hex(CTRL_BIT)} }}')
        lines.append(f'after time {ctrlstop_at:g} {{ keymatrixdown {STOP_ROW} {hex(STOP_BIT)} }}')
        up = ctrlstop_at + 1.5
        lines.append(f'after time {up:g} {{ keymatrixup {STOP_ROW} {hex(STOP_BIT)} }}')
        lines.append(f'after time {up:g} {{ keymatrixup {CTRL_ROW} {hex(CTRL_BIT)} }}')
    lines.append(f"after time {cap_at:g} {{ __cap }}")
    tcl = "\n".join(lines) + "\n"

    fd, tcl_path = tempfile.mkstemp(suffix=".tcl", prefix="cont_")
    os.write(fd, tcl.encode())
    os.close(fd)
    cmd = [OMSX, "-machine", MACHINE,
           "-command", "set renderer none", "-script", tcl_path]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
        deadline = time.time() + timeout
        while proc.poll() is None and time.time() < deadline:
            time.sleep(0.1)
        if proc.poll() is None:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    finally:
        os.unlink(tcl_path)
    vals = {}
    if os.path.exists(out_path):
        with open(out_path) as f:
            for ln in f:
                if ln.startswith("mem.0x"):
                    k, _, v = ln.strip().partition("=")
                    vals[k[len("mem."):]] = v
        os.unlink(out_path)
    return vals


def lines_for(prog, *tail):
    """Build a (time,text) event list: each prog line + Enter, then tail lines.

    Numbered/direct lines are typed at widening emulated times so each lands in
    its own REPL window under `throttle off`.
    """
    ev = []
    t = 6.0
    for text in list(prog) + list(tail):
        ev.append((t, text)); t += 2.0
        ev.append((t, "\r")); t += 2.0
    return ev


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    args = ap.parse_args()

    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL'}  {label}" + (f"  {detail}" if detail else ""))
        ok = ok and cond

    # (a) STOP halts: poke,1 runs, STOP breaks before poke,2 -> T stays 01.
    v = run(cart, lines_for([f"10 poke &h{T:04x},1:stop:poke &h{T:04x},2", "run"]),
            [(T, 1)])
    check("STOP halts before the post-STOP statement (T=1)",
          v.get(f"0x{T:04X}") == "01", f"T={v.get(f'0x{T:04X}')}")

    # (b) STOP then CONT resumes: the statement after STOP runs -> T=02.
    v = run(cart, lines_for([f"10 poke &h{T:04x},1:stop:poke &h{T:04x},2",
                             "run", "cont"]), [(T, 1)])
    check("STOP then CONT resumes (T=2)",
          v.get(f"0x{T:04X}") == "02", f"T={v.get(f'0x{T:04X}')}")

    # (c) CONT resumes across a line boundary: STOP ends line 10, CONT runs 20.
    v = run(cart, lines_for([f"10 poke &h{T:04x},1:stop", f"20 poke &h{U:04x},9",
                             "run", "cont"]), [(T, 2)])
    check("CONT resumes onto the next line (T=1,U=9)",
          v.get(f"0x{T:04X}") == "0109", f"D000..1={v.get(f'0x{T:04X}')}")

    # (d) bare CONT (never ran) -> "can't continue" ($C9).
    v = run(cart, lines_for(["cont"]), [(ERRMARK, 1)])
    check("bare CONT (never ran) -> can't continue $C9",
          v.get(f"0x{ERRMARK:04X}") == f"{CANT_CONT:02x}",
          f"E010={v.get(f'0x{ERRMARK:04X}')}")

    # (e) CONT after a clean (STOP-less) RUN -> can't continue.
    v = run(cart, lines_for([f"10 poke &h{T:04x},1", "run", "cont"]),
            [(ERRMARK, 1)])
    check("CONT after a STOP-less RUN -> can't continue $C9",
          v.get(f"0x{ERRMARK:04X}") == f"{CANT_CONT:02x}",
          f"E010={v.get(f'0x{ERRMARK:04X}')}")

    # (f) editing the program after a STOP invalidates CONT -> can't continue,
    #     and poke,2 must NOT have run (T stays 01).
    v = run(cart, lines_for([f"10 poke &h{T:04x},1:stop:poke &h{T:04x},2",
                             "run", "5 rem edit", "cont"]),
            [(T, 1), (ERRMARK, 1)])
    check("edit after STOP invalidates CONT -> can't continue $C9",
          v.get(f"0x{ERRMARK:04X}") == f"{CANT_CONT:02x}"
          and v.get(f"0x{T:04X}") == "01",
          f"E010={v.get(f'0x{ERRMARK:04X}')} T={v.get(f'0x{T:04X}')}")

    # (g) Ctrl-STOP breaks an INFINITE loop back to the REPL. Line 10 loops
    #     forever (goto); after the key press a direct POKE sets U=09 — which is
    #     only reachable if the break returned to the REPL. The press is timed to
    #     land while the loop spins (run at t=11/13, press at t=16).
    prog = [f"10 poke &h{T:04x},1:goto 10"]
    ev = lines_for(prog, "run") + [(18.0, f"poke &h{U:04x},9"), (20.0, "\r")]
    v = run(cart, ev, [(T, 2)], ctrlstop_at=16.0, cap_at=27.0)
    broke = v.get(f"0x{T:04X}") == "0109"
    check("Ctrl-STOP breaks a running loop back to the REPL (U=9)",
          broke, f"D000..1={v.get(f'0x{T:04X}')}")

    print("\nALL PASS" if ok else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
