#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""STRIG interrupt-trap acceptance — slice T2 (docs/spec-traps-t2-strig.md).

Differential of `ON STRIG GOSUB` / `STRIG(n) ON|OFF|STOP` against the reference
oracle Philips VG-8020, alongside the relocated repack build
(C-BIOS_MSX1_EU_REPACK_DISK, overridable via $ZEROBAS_BASIC_MACHINE). Both carry
BASIC in ROM, so each case is `-machine <name>` only: one boot per case.

METHODOLOGY (inherited from the T1 stop-trap gate, plus one new mechanism):
  * RAM SENTINELS, never screen text -- the REPL echoes every typed program line,
    so a handler marker like PRINT"HIT" shows up in the LISTING echo whether or not
    the handler ran. $D000 = fire COUNT, $D001 = which handler, $D002 = trapped ERR.
  * TRIGGER 0 is the SPACE key: keyboard matrix row 8 bit 0 IS joystick trigger 0,
    so `keymatrixdown 8 0x01` is a real press.
  * TRIGGERS 1..4 have no openMSX button command. They are driven by putting PSG
    port A into OUTPUT mode (R7 bit 6) so the AY returns register 14's LATCH
    instead of the joystick pins, then writing R14 (active low): bit 4 presses
    STRIG(1)+STRIG(2), bit 5 presses STRIG(3)+STRIG(4), 0xFF releases. Verified
    byte-identical on both machines, and a press/release/press counts exactly two
    rising edges on both (spec §7.3). This needs the acceptance machine to carry
    <ignorePortDirections>false</> like Philips_VG_8020.xml does -- openMSX
    defaults it to true and silently drops the R7 write (D-T2-6). Residual: the
    latch sits behind the port-A/port-B multiplexer, so STRIG(1)/(2) and
    STRIG(3)/(4) cannot be told apart -- every trigger is pressable, but "which
    physical port" stays untested.

THE SEMANTIC MODEL BEING GATED (all VG-8020-measured, spec §1): a trigger is
sampled while its entry is ON *or* SERVICING (never while OFF or STOP); a 0->1
transition against a per-entry shadow bit sets PENDING; and any transition INTO ON
seeds the shadow "pressed", so a trigger already held cannot manufacture an edge.
That is why a 3 s hold fires ONCE (edge, not level), why a press predating the
enable is invisible, why a press during an OFF/STOP window is forgotten -- and why
a press DURING the handler is remembered and fires once after RETURN.

Clean-room: observed I/O only.
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

CNT, WHO, ERRC = 0xD000, 0xD001, 0xD002
SPACE_ROW, SPACE_BIT = 8, 0x01

# --- the trigger-1..4 injection (spec §7.3) --------------------------------
PSG_OUT = 'debug write "PSG regs" 7 0xF8'          # port A -> output: R14 reads the latch
def press(mask):        # active low
    return f'{PSG_OUT}; debug write "PSG regs" 14 {mask}'
PRESS_A = press("0xEF")     # bit 4 -> STRIG(1) and STRIG(2)
PRESS_B = press("0xDF")     # bit 5 -> STRIG(3) and STRIG(4)
RELEASE = 'debug write "PSG regs" 14 0xFF'

# --- key events -------------------------------------------------------------
def kdown():
    return f"keymatrixdown {SPACE_ROW} {hex(SPACE_BIT)}"
def kup():
    return f"keymatrixup {SPACE_ROW} {hex(SPACE_BIT)}"


def run(machine, prog, events, *, boot=8.0, step=2.0, cap_after=30.0, timeout=300):
    """Boot `machine`, type `prog` + RUN, fire `events` = [(seconds_after_RUN, tcl)],
    then dump the three sentinels. One boot per call = power-on fresh."""
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="strigtrap_")
    os.close(out_fd)
    lines = ["set throttle off",
             f'proc __cap {{}} {{ set f [open {{{out_path}}} w];'
             f' puts $f "cnt=[debug read memory {CNT}] who=[debug read memory {WHO}]'
             f' err=[debug read memory {ERRC}]"; close $f; exit }}']
    t = boot
    for text in list(prog) + ["RUN"]:
        lines.append(f'after time {t:g} {{ type {_tcl_dquote(text)} }}'); t += step
        lines.append(f'after time {t:g} {{ type {_tcl_dquote(chr(13))} }}'); t += step
    run_done = t
    last = run_done
    for dt, tcl in events:
        lines.append(f'after time {run_done + dt:g} {{ {tcl} }}')
        last = max(last, run_done + dt)
    lines.append(f"after time {last + cap_after:g} {{ __cap }}")

    fd, tcl_path = tempfile.mkstemp(suffix=".tcl", prefix="strigtrap_")
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
    res = None
    if os.path.exists(out_path):
        txt = open(out_path).read().strip()
        os.unlink(out_path)
        if txt:
            res = {k: int(v) for k, v in (kv.split("=") for kv in txt.split())}
    return res


# --- program fragments ------------------------------------------------------
CLR = "5 POKE&HD000,0:POKE&HD001,0:POKE&HD002,0"
ONERR = "1 ONERRORGOTO900"
ERRH = "900 POKE&HD002,ERR:END"
# handlers COUNT their fires (level-vs-edge only shows in the count) and RETURN,
# so the auto-resume is exercised on every case that fires.
H1 = "100 POKE&HD000,PEEK(&HD000)+1:POKE&HD001,1:RETURN"
H2 = "200 POKE&HD000,PEEK(&HD000)+1:POKE&HD001,2:RETURN"
H3 = "300 POKE&HD000,PEEK(&HD000)+1:POKE&HD001,3:RETURN"
POLL = "60 FORI=1TO32000:NEXT:END"
DELAY = "20 FORI=1TO9000:NEXT"          # ~7 s of MSX time; a press lands mid-way

TAP = [(1.0, kdown()), (1.15, kup())]
HOLD3 = [(1.0, kdown()), (4.0, kup())]
TWO_TAPS = [(1.0, kdown()), (1.15, kup()), (3.0, kdown()), (3.15, kup())]

# label, program, events, expected {sentinel: value} -- asserted on BOTH machines
FIRING = [
    ("A_fires", [CLR, "10 ON STRIG GOSUB 100", "30 STRIG(0) ON", POLL, H1],
     TAP, {"cnt": 1, "who": 1}),

    # edge, not level: three seconds of holding is still ONE fire (oracle Q2)
    ("B_hold_fires_once", [CLR, "10 ON STRIG GOSUB 100", "30 STRIG(0) ON", POLL, H1],
     HOLD3, {"cnt": 1, "who": 1}),

    ("C_two_taps", [CLR, "10 ON STRIG GOSUB 100", "30 STRIG(0) ON", POLL, H1],
     TWO_TAPS, {"cnt": 2, "who": 1}),

    ("D_no_enable", [CLR, "10 ON STRIG GOSUB 100", POLL, H1],
     TAP, {"cnt": 0}),

    # THE SHADOW CASE: held from mid-delay THROUGH the enable -> no edge, no fire
    ("E_arm_while_held",
     [CLR, "10 ON STRIG GOSUB 100", DELAY, "30 STRIG(0) ON", POLL, H1],
     [(1.0, kdown()), (12.0, kup())], {"cnt": 0}),

    # ...and the same, re-issuing the enable while still held (this is the path
    # where set_state must PRESERVE the shadow bit -- a host-test invariant too)
    ("F_reenable_while_held",
     [CLR, "10 ON STRIG GOSUB 100", "30 STRIG(0) ON", DELAY, "40 STRIG(0) ON",
      POLL, H1],
     [(1.0, kdown()), (12.0, kup())], {"cnt": 0}),

    ("G_off_forgets",
     [CLR, "10 ON STRIG GOSUB 100", "15 STRIG(0) OFF", DELAY, "40 STRIG(0) ON",
      POLL, H1],
     TAP, {"cnt": 0}),

    ("H_stop_suspends",
     [CLR, "10 ON STRIG GOSUB 100", "15 STRIG(0) STOP", DELAY, "40 STRIG(0) ON",
      POLL, H1],
     TAP, {"cnt": 0}),

    # A press while the handler runs is LATCHED, not lost: it cannot fire during
    # SERVICING, but RETURN restores ON and it fires once more -> cnt 2. (The T2
    # characterization first read this as "lost" purely because its capture window
    # closed before the slow handler returned; this gate caught that.)
    # Two harness notes, both learned the hard way here:
    #   * the handler is split across lines -- long typed lines drop keystrokes
    #     under `throttle off` (the standing rule);
    #   * zerobas runs an empty FOR loop MUCH slower than the VG-8020 (~7x on this
    #     loop), so the delay is short enough for zerobas and the window is long,
    #     and the delay is taken on the FIRST invocation only -- otherwise the
    #     second fire would spend another full delay before the capture.
    ("I_press_in_handler",
     [CLR, "10 ON STRIG GOSUB 100", "30 STRIG(0) ON", POLL,
      "100 POKE&HD000,PEEK(&HD000)+1",
      "102 POKE&HD001,1",
      "104 IFPEEK(&HD000)=1THENFORJ=1TO3000:NEXT",
      "106 RETURN"],
     [(1.0, kdown()), (1.15, kup()), (3.0, kdown()), (3.15, kup())],
     {"cnt": 2, "who": 1}, 60.0),

    # the list is positional: slot 0 is trigger 0 (oracle R5)
    ("J_slot0_is_trig0",
     [CLR, "10 ON STRIG GOSUB 100,200", "30 STRIG(0) ON", POLL, H1, H2],
     TAP, {"cnt": 1, "who": 1}),

    # an EMPTY slot clears that trigger's handler (oracle S3/R4)
    ("K_empty_slot_clears",
     [CLR, "10 ON STRIG GOSUB 100", "12 ON STRIG GOSUB ,300", "30 STRIG(0) ON",
      POLL, H1, H3],
     TAP, {"cnt": 0}),
]

# Triggers 1..4, driven by the PSG-latch injection (spec §7.3).
INJECTED = [
    ("L_trig1_fires",
     [CLR, "10 ON STRIG GOSUB 100,200", "30 STRIG(1) ON", POLL, H1, H2],
     [(2.0, PRESS_A), (6.0, RELEASE)], {"cnt": 1, "who": 2}),

    ("M_trig1_hold_once",
     [CLR, "10 ON STRIG GOSUB 100,200", "30 STRIG(1) ON", POLL, H1, H2],
     [(2.0, PRESS_A)], {"cnt": 1, "who": 2}),

    ("N_trig1_two_presses",
     [CLR, "10 ON STRIG GOSUB 100,200", "30 STRIG(1) ON", POLL, H1, H2],
     [(2.0, PRESS_A), (5.0, RELEASE), (8.0, PRESS_A), (11.0, RELEASE)],
     {"cnt": 2, "who": 2}),

    # trigger 3 rides R14 bit 5; trigger 1 (bit 4) must stay quiet
    ("O_trig3_fires",
     [CLR, "10 ON STRIG GOSUB 100,200,200,300", "30 STRIG(3) ON", POLL, H1, H2, H3],
     [(2.0, PRESS_B), (6.0, RELEASE)], {"cnt": 1, "who": 3}),

    ("P_trig1_ignores_bit5",
     [CLR, "10 ON STRIG GOSUB 100,200", "30 STRIG(1) ON", POLL, H1, H2],
     [(2.0, PRESS_B), (6.0, RELEASE)], {"cnt": 0}),

    ("Q_trig1_arm_while_held",
     [CLR, "10 ON STRIG GOSUB 100,200", DELAY, "30 STRIG(1) ON", POLL, H1, H2],
     [(0.2, PRESS_A), (14.0, RELEASE)], {"cnt": 0}),
]

# Parse / error surface -- no press needed; ERR is captured by ON ERROR.
PARSE = [
    ("R_range", [CLR, ONERR, "10 STRIG(5) ON", "20 END", ERRH], [], {"err": 5}),
    ("S_bare", [CLR, ONERR, "10 STRIG(0)", "20 END", ERRH], [], {"err": 2}),
    ("T_on_strig_bare", [CLR, ONERR, "10 ON STRIG", "20 END", ERRH], [], {"err": 2}),
    ("U_on_strig_goto", [CLR, ONERR, "10 ON STRIG GOTO 100", "20 END", H1, ERRH],
     [], {"err": 2}),
    ("V_undef_line", [CLR, ONERR, "10 ON STRIG GOSUB 999", "20 END", ERRH],
     [], {"err": 8}),
    ("W_five_slots", [CLR, ONERR, "10 ON STRIG GOSUB 100,100,100,100,100",
                      "20 STRIG(4) ON", "30 END", H1, ERRH], [], {"err": 0}),
    ("X_frac_index", [CLR, ONERR, "10 ON STRIG GOSUB 100", "30 STRIG(.4) ON",
                      POLL, H1, ERRH], TAP, {"cnt": 1, "err": 0}),
    ("Y_unspaced", [CLR, ONERR, "10 ON STRIG GOSUB 100", "30 STRIG(0)ON",
                    POLL, H1, ERRH], TAP, {"cnt": 1, "err": 0}),
]

# zerobas-only: a DOCUMENTED DEVIATION (D-T2-4). A sixth slot takes the REFERENCE
# machine down (no clean error, sentinels revert to the power-on pattern,
# reproducible x3 -- consistent with a handler-table overrun). Replicating that is
# neither clean-room-achievable nor desirable, so zerobas raises a trappable ERR 2.
DEVIATION = [
    ("Z_six_slots_deviation",
     [CLR, ONERR, "10 ON STRIG GOSUB 100,100,100,100,100,100", "20 END", H1, ERRH],
     [], {"err": 2}),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=REF_MACHINE, help="reference oracle machine")
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE)
    ap.add_argument("--only", help="run only cases whose label contains this substring")
    ap.add_argument("--ref-only", action="store_true", help="oracle-lock only")
    ap.add_argument("--zb-only", action="store_true", help="zerobas side only")
    args = ap.parse_args()
    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL':5} {label}" + (f"  {detail}" if detail else ""))
        ok = ok and cond

    def matches(got, want):
        return got is not None and all(got.get(k) == v for k, v in want.items())

    def differential(group, cases):
        print(f"\n--- {group} ---")
        for label, prog, events, want, *rest in cases:
            if args.only and args.only not in label:
                continue
            cap = rest[0] if rest else 30.0     # per-case capture window (seconds)
            ref = None
            if not args.zb_only:
                ref = run(args.machine, prog, events, cap_after=cap)
                check(f"[ref] {label:24} {ref} want {want}", matches(ref, want))
            if args.ref_only:
                continue
            zb = run(args.zb_machine, prog, events, cap_after=cap)
            good = matches(zb, want) and (ref is None or zb == ref)
            check(f"[zb ] {label:24} {zb} want {want}"
                  + ("" if ref is None else f", == ref {ref}"), good)

    differential("FIRING semantics, trigger 0 (SPACE via the keyboard matrix)", FIRING)
    differential("TRIGGERS 1..4 (PSG-latch injection, spec §7.3)", INJECTED)
    differential("PARSE / error surface", PARSE)

    # the deviation is asserted on zerobas ALONE -- the reference has no defined
    # behaviour here (it crashes), so a differential would be meaningless.
    print("\n--- DOCUMENTED DEVIATION (zerobas only; the reference crashes) ---")
    for label, prog, events, want, *rest in DEVIATION:
        if args.only and args.only not in label:
            continue
        if args.ref_only:
            continue
        zb = run(args.zb_machine, prog, events, cap_after=rest[0] if rest else 30.0)
        check(f"[zb ] {label:24} {zb} want {want}", matches(zb, want))

    print("\nALL PASS" if ok else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
