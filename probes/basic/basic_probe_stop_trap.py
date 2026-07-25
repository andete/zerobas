#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""STOP interrupt-trap acceptance — slice T1 (docs/spec-traps-t1-stop-reslice.md §9.2/§12).

Differential of `ON STOP GOSUB` / `STOP ON|OFF|STOP` against the reference oracle
Philips VG-8020, alongside the relocated repack build (C-BIOS_MSX1_EU_REPACK_DISK,
overridable via $ZEROBAS_BASIC_MACHINE). Both machines carry BASIC in-ROM, so each
case is `-machine <name>` only, one boot per case.

METHODOLOGY (why standalone, POKE-sentinel, boot-per-case):
  * Ctrl-STOP is a TWO-KEY combo on different matrix rows (CTRL row6 bit1 + STOP
    row7 bit4), driven via openMSX keymatrixdown/up (cont.py established this).
  * The signal is a RAM SENTINEL ($D000/$D001), not screen text: the REPL echoes
    each typed program line, so a handler marker like PRINT"TRAPPED" appears in the
    LISTING echo whether or not the handler ran -- fatal for the "no-fire" cases.
    A POKEd byte in free RAM is echo-immune. Lines are kept short so openMSX `type`
    injection is reliable (long lines drop keystrokes under `throttle off`).

THE DISCRIMINATING REGIME (the load-bearing lesson, oracle-characterized 2026-07-25):
a HELD Ctrl-STOP in a tight `GOTO` loop BREAKS on BOTH machines -- that regime does
NOT discriminate. The feature's happy path only appears with a brief TAP during a
DELAY (`FOR..NEXT`) followed by a poll loop: real MSX latches the Ctrl-STOP at
interrupt time (INTFLG) so the released tap still fires the handler a boundary later.
zerobas catches the same tap via its live BREAKX poll; the fix (spec §12.2, "R1") was
to stop the freshly-entered handler from re-breaking on its own first boundary while
the triggering key is still (briefly) down -- a one-VBLANK grace (STOPGRACE) cleared
by event_poll, mirroring INTFLG's clear-on-fire / re-set-next-frame window.

Cases (sentinel $D000 = handler-fire flag; short lines; tap@+0.3s during the FOR):

  A  on_fires     10 ON STOP GOSUB 100 : 20 STOP ON : 30 FOR..NEXT : 40 GOTO40
                  100 POKE flag,1:END        tap during the FOR -> handler runs -> flag=1
  B  armed_off    (no STOP ON) the arm alone must NOT enable        -> break, flag=0
  B2 stop_off     20 STOP ON:STOP OFF  an enabled trap, then disabled -> flag=0
       (B2 also gates the statement-continuation fix: `ret` after the arming sub-
        keyword used to SWALLOW the rest of the line, so `STOP OFF` was a no-op.)

All three are machine-agnostic RAM facts, asserted absolutely AND diffed
zerobas==reference. A fourth case (D, interruptible) runs a tap-then-hold and is
reported as a straight differential -- its two-press timing is not robust enough to
assert, but the handler being Ctrl-STOP-abortable is oracle-confirmed and host-tested
(tests/test_traps.py trap_return_check). Clean-room: observed I/O only.
"""
from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))          # siblings
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared

import argparse
import os
import shutil
import signal
import subprocess
import tempfile
import time

from omsx_run import _tcl_dquote  # noqa: E402  (Tcl `type` literal: CR -> \r)

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
if not (os.path.sep in OMSX and os.path.isfile(OMSX)):
    OMSX = "openmsx"

REF_MACHINE = "Philips_VG_8020"
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

FLAG = 0xD000    # handler sentinel: 0 = never ran; 1 = fired (2 = handler completed body)
CTRL_ROW, CTRL_BIT = 6, 0x02
STOP_ROW, STOP_BIT = 7, 0x10


def run(machine, prog, presses, *, cap_after=9.0, timeout=90):
    """Boot `machine` (BASIC in-ROM, no cart), type `prog` + RUN, apply the Ctrl-STOP
    `presses` (each a (down, up) offset in emulated seconds after RUN), then dump
    FLAG and exit. Returns FLAG (int) or None. One boot per call = power-on fresh."""
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="stoptrap_")
    os.close(out_fd)
    lines = ["set throttle off",
             "proc __b {a} { return [debug read memory $a] }",
             f'proc __cap {{}} {{ set f [open {{{out_path}}} w];'
             f' puts $f "flag=[__b {FLAG}]"; close $f; exit }}']

    def emit(t, text):
        lines.append(f'after time {t:g} {{ type {_tcl_dquote(text)} }}')

    t = 6.0
    for text in list(prog) + ["RUN"]:
        emit(t, text); t += 2.0
        emit(t, "\r"); t += 2.0
    run_done = t
    last = run_done
    for dn, up in presses:
        for row, mask in ((CTRL_ROW, CTRL_BIT), (STOP_ROW, STOP_BIT)):
            lines.append(f'after time {run_done + dn:g} {{ keymatrixdown {row} {hex(mask)} }}')
        for row, mask in ((STOP_ROW, STOP_BIT), (CTRL_ROW, CTRL_BIT)):
            lines.append(f'after time {run_done + up:g} {{ keymatrixup {row} {hex(mask)} }}')
        last = run_done + up
    lines.append(f"after time {last + cap_after:g} {{ __cap }}")

    fd, tcl_path = tempfile.mkstemp(suffix=".tcl", prefix="stoptrap_")
    os.write(fd, ("\n".join(lines) + "\n").encode())
    os.close(fd)
    cmd = [OMSX, "-machine", machine, "-command", "set renderer none", "-script", tcl_path]
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
    val = None
    if os.path.exists(out_path):
        with open(out_path) as f:
            for ln in f:
                if ln.startswith("flag="):
                    val = int(ln.strip().split("=")[1])
        os.unlink(out_path)
    return val


# --- cases (short lines; tap@+0.3s lands inside the FOR delay on both machines) ---
# FOR..NEXT then a distinct GOTO poll loop: the tap fires the trap during the FOR;
# the handler ENDs. A trailing GOTO keeps the program alive if it did NOT fire.
DELAY = "30 FORI=1TO4000:NEXT"
POLL = "40 GOTO40"
HEND = "100 POKE&HD000,1:END"
TAP = [(0.3, 0.33)]

ASSERTED = [
    ("A_on_fires", ["5 POKE&HD000,0", "10 ON STOP GOSUB 100", "20 STOP ON",
                    DELAY, POLL, HEND], TAP, 1),
    ("B_armed_off", ["5 POKE&HD000,0", "10 ON STOP GOSUB 100",
                     DELAY, POLL, HEND], TAP, 0),
    ("B2_stop_off", ["5 POKE&HD000,0", "10 ON STOP GOSUB 100", "20 STOP ON:STOP OFF",
                     DELAY, POLL, HEND], TAP, 0),
]

# D: fire (tap), then HOLD during the handler's own delay -> the handler must abort
# (flag stays 1, the completion POKE 2 never runs). Straight differential (timing).
D_CASE = ("D_interruptible",
          ["5 POKE&HD000,0", "10 ON STOP GOSUB 100", "20 STOP ON",
           "30 FORI=1TO3000:NEXT:GOTO30",
           "100 POKE&HD000,1", "105 FORK=1TO9000:NEXT", "108 POKE&HD000,2:END"],
          [(0.3, 0.33), (1.0, 5.0)])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=REF_MACHINE, help="reference oracle machine")
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE,
                    help="zerobas repack machine")
    ap.add_argument("--only", help="run only cases whose label contains this substring")
    ap.add_argument("--ref-only", action="store_true", help="oracle-lock only")
    ap.add_argument("--trials", type=int, default=2, help="repeats per case (robustness)")
    args = ap.parse_args()
    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL':5} {label}" + (f"  {detail}" if detail else ""))
        ok = ok and cond

    def sample(machine, prog, presses, cap=9.0):
        return [run(machine, prog, presses, cap_after=cap) for _ in range(args.trials)]

    print(f"--- ASSERTED cases: zerobas == VG-8020, robust across {args.trials} trials ---")
    for label, prog, presses, want in ASSERTED:
        if args.only and args.only not in label:
            continue
        ref = sample(args.machine, prog, presses)
        ref_ok = all(r == want for r in ref)
        check(f"[ref] {label:16} {ref} (want all {want})", ref_ok)
        if args.ref_only:
            continue
        zb = sample(args.zb_machine, prog, presses)
        zb_ok = all(z == want for z in zb) and zb == ref
        check(f"[zb ] {label:16} {zb} (want all {want}, == ref {ref})", zb_ok)

    # D: straight differential (best-effort; not asserted -- two-press timing)
    if not args.only or "D_interruptible" in (args.only or ""):
        label, prog, presses = D_CASE
        print("\n--- D_interruptible: fire then hold -> handler aborts (differential) ---")
        ref = sample(args.machine, prog, presses)
        print(f"  [ref] {label:16} {ref}")
        if not args.ref_only:
            zb = sample(args.zb_machine, prog, presses)
            match = zb == ref
            check(f"[zb ] {label:16} {zb} (ref {ref}) -- differential", match)

    print("\nALL PASS" if ok else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
