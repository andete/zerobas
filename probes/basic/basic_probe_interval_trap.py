#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""INTERVAL interrupt-trap characterization / differential — slice T5.

docs/spec-traps-t5-interval.md §1. Produced every reading in that §1. Runs as a
ASSERTING differential between the reference oracle (Philips VG-8020) and the
relocated repack build -- `make interval-trap-acceptance`. `--report` drops back
to the characterization mode that produced spec §1.

WHY THIS SLICE EXISTS AT ALL: see docs/spec-basic-interrupt-traps.md §0. The arc
excluded INTERVAL on 2026-07-24 as "an MSX2 keyword" after a crunch probe found
no keyword-table entry. The measurement was right; the inference was not.
INTERVAL is a reserved-word COMPOUND (`INT` + the literal bytes "ER" + `VAL`),
so it never needed a table entry, and it works on MSX1.

T5'S APPARATUS IS THE SIMPLEST IN THE ARC and its measurement is the hardest.
Simplest: the event source is a frame counter, so there is nothing to inject --
no matrix hold (T2/T3), no PSG port-A + R14 (T2), no C-BIOS hook (T3), not even
two sprites (T4). Hardest: EVERY OBSERVABLE IS A JIFFY COUNT, which is exactly
the quantity the TIME session found a batched harness makes a REPRODUCIBLE
confound of. Two consequences are designed in:

  * THE PERIOD IS MEASURED BETWEEN TWO FIRES, NOT OVER A WINDOW. The handler
    stamps JIFFY at fire #1 into $D004/5 and at fire #1+SPAN into $D006/7, so
    the reported period is (J2-J1)/SPAN -- independent of where the window
    started relative to the trap's own phase. A fires-per-window count has +-1
    of pure phase noise in it and would have to be repeated with deliberate
    phase shifts and reduced by MIN to mean anything (the TIME lesson). The
    difference-of-timestamps form has none.
  * EVERY READING IS GATED ON `done` ($D003). A program that errored out or was
    still running at the hard deadline is captured with done==0 and is a
    FAILURE, never a zero. This is the standing arc requirement retrofitted to
    T1/T2 in 36e2300 after two characterization rounds agreed on a wrong answer.

Other standing arc requirements, inherited verbatim from the T3/T4 gates:
RAM sentinels, never screen text (the REPL echoes every typed program line);
the fire counter SATURATES at 250 (`POKE 256` would raise ERR 5 and turn a
correct "fires often" answer into an error case); no string building; and
windows bounded by a JIFFY DELTA rather than an iteration count, which means
the same thing on two machines that run BASIC ~3-7x apart. (The T3-era rule "no
`TIME` on the zerobas side" is RETIRED as of 2026-07-26 -- `TIME` has landed,
docs/spec-basic-time.md -- but a JIFFY delta read by PEEK needs no keyword and
is what these windows already use.)

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

from omsx_repl import KEYBUF, GETPNT, PUTPNT, MAX_DIRECT  # noqa: E402

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
if not (os.path.sep in OMSX and os.path.isfile(OMSX)):
    OMSX = "openmsx"

REF_MACHINE = "Philips_VG_8020"
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

BASE = 0xD000     # D000 cnt  D001 who  D002 err  D003 done
                  # D004/5 J1 (JIFFY at fire #1)   D006/7 J2 (JIFFY at fire #1+SPAN)
                  # D008 aux  D009 aux2  D00A aux3  D00B aux4
NBYTES = 12
JIFFY = 0xFC9E    # published work area: the frame counter

# SPAN = how many PERIODS separate the two stamped fires. It is per-case, and
# that is not tuning for its own sake: each stamp is quantised to the STATEMENT
# BOUNDARY at which the trap dispatched, so the pair carries +-1 frame of
# endpoint jitter and the reported period carries +-1/SPAN. The first run of
# this probe used SPAN=10 everywhere and read n=5 as period 4.9 -- one frame of
# endpoint jitter, indistinguishable from a real 4.9. Cases that MEASURE a
# period widen SPAN until the jitter is an order of magnitude below the answer;
# cases that only ask "does it error" leave it at the default.
SPAN_DEFAULT = 10


def run(machine, prog, *, span=SPAN_DEFAULT, boot=8.0, step=3.0, poll_from=2.0,
        deadline=600.0, timeout=900):
    """Boot `machine`, inject `prog` + RUN through KEYBUF, capture the sentinels
    the moment $D003 is set -- or at `deadline` emulated seconds, which captures
    done==0 and fails the case. One boot per call = power-on fresh. Times are
    EMULATED seconds (throttle off)."""
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="ivltrap_")
    os.close(out_fd)
    lines = [
        "set throttle off",
        f'proc __cap {{}} {{ set f [open {{{out_path}}} w];'
        f' binary scan [debug read_block memory {BASE} {NBYTES}] H* m;'
        f' puts $f "m=$m t=[expr {{int([machine_info time])}}]"; close $f; exit }}',
        f'proc __poll {{}} {{ if {{[debug read memory {BASE + 3}] != 0}} {{ __cap }}'
        f' else {{ after time 1 __poll }} }}',
        # KEYBUF injection (probes/lib/omsx_repl.py): atomic, no per-character
        # typing schedule to race. openMSX `type` cost the T3 gate three rounds.
        "proc __key {s} {\n"
        "  set n [string length $s]\n"
        "  for {set i 0} {$i < $n} {incr i} {\n"
        f"    debug write memory [expr {{{KEYBUF} + $i}}] "
        "[scan [string index $s $i] %c]\n"
        "  }\n"
        f"  debug write memory {GETPNT} [expr {{{KEYBUF} & 0xFF}}]\n"
        f"  debug write memory [expr {{{GETPNT}+1}}] [expr {{({KEYBUF} >> 8) & 0xFF}}]\n"
        f"  set p [expr {{{KEYBUF} + $n}}]\n"
        f"  debug write memory {PUTPNT} [expr {{$p & 0xFF}}]\n"
        f"  debug write memory [expr {{{PUTPNT}+1}}] [expr {{($p >> 8) & 0xFF}}]\n"
        "}",
        "proc __inj {s} { append s \"\\r\"; __key $s }",
    ]
    t = boot
    for text in list(prog) + ["RUN"]:
        chunks = [text[i:i + MAX_DIRECT] for i in range(0, len(text), MAX_DIRECT)] or [text]
        for k, c in enumerate(chunks):
            proc = "__inj" if k == len(chunks) - 1 else "__key"   # CR only on last
            lines.append(f'after time {t:g} {{ {proc} {{{c}}} }}')
            t += step
    lines.append(f"after time {t + poll_from:g} {{ __poll }}")
    lines.append(f"after time {t + deadline:g} {{ __cap }}")

    fd, tcl_path = tempfile.mkstemp(suffix=".tcl", prefix="ivltrap_")
    os.write(fd, ("\n".join(lines) + "\n").encode())
    os.close(fd)
    cmd = [OMSX, "-machine", machine, "-command", "set renderer none; set sound_driver null", "-script", tcl_path]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
        dl = time.time() + timeout
        while proc.poll() is None and time.time() < dl:
            time.sleep(0.1)
        if proc.poll() is None:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    finally:
        os.unlink(tcl_path)
    if not os.path.exists(out_path):
        return None
    txt = open(out_path).read().strip()
    os.unlink(out_path)
    if not txt:
        return None
    res = {}
    for kv in txt.split():
        k, _, v = kv.partition("=")
        if k == "m":
            b = bytes.fromhex(v)
            res.update(cnt=b[0], who=b[1], err=b[2], done=b[3],
                       j1=b[4] + 256 * b[5], j2=b[6] + 256 * b[7],
                       aux=b[8], aux2=b[9], aux3=b[10], aux4=b[11])
        else:
            res[k] = int(v)
    if res:
        d = res["j2"] - res["j1"]
        res["span"] = span
        res["period"] = round(d / span, 3) if (res["j1"] and res["j2"] and d > 0) else 0
    return res


# --- program fragments ------------------------------------------------------
ONERR = "1 ONERRORGOTO900"
CLR = [f"5 FORZ=0TO{NBYTES - 1}:POKE&HD000+Z,0:NEXT"]
ERRH = "900 POKE&HD002,ERR:POKE&HD003,1:END"
END = "790 POKE&HD003,1:END"

# The handler. A saturates at 250 (see the docstring). Fires #1 and #1+span stamp
# JIFFY, read with a HIGH-BYTE RE-READ GUARD: a lo-then-hi read TEARS whenever the
# low byte wraps between the two PEEKs (~once per 256 frames) and composes 256 low
# -- the exact apparatus bug that made T4's cadence case read 2.4 fires/frame.
def handler(span=SPAN_DEFAULT):
    return [
        "800 A=PEEK(&HD000):IFA<250THENPOKE&HD000,A+1",
        f"801 IFA<>0ANDA<>{span}THENRETURN",
        f"802 H=PEEK(&H{JIFFY + 1:X}):L=PEEK(&H{JIFFY:X})"
        f":IFH<>PEEK(&H{JIFFY + 1:X})THEN802",
        "803 IFA=0THENPOKE&HD004,L:POKE&HD005,H:RETURN",
        "804 POKE&HD006,L:POKE&HD007,H:RETURN",
    ]

# WAITn: let n FRAMES pass, machine-independently, with the same re-read guard.
# Subroutines MUST sort after END -- if execution falls into them their RETURN
# raises ERR 3 (the T4 probe learned this the hard way, and it is the LINE
# NUMBER that decides, not the order the lines are typed in).
def waitn(line, n):
    return [f"{line} H=PEEK(&H{JIFFY + 1:X}):W=PEEK(&H{JIFFY:X})+256*H"
            f":IFH<>PEEK(&H{JIFFY + 1:X})THEN{line}",
            f"{line + 2} H=PEEK(&H{JIFFY + 1:X}):V=PEEK(&H{JIFFY:X})+256*H"
            f":IFH<>PEEK(&H{JIFFY + 1:X})THEN{line + 2}",
            f"{line + 4} IFV-W<{n}THEN{line + 2}",
            f"{line + 6} RETURN"]


WAIT160 = waitn(950, 160)     # GOSUB950
WAIT60 = waitn(960, 60)       # GOSUB960
WAIT300 = waitn(970, 300)     # GOSUB970


# A case is (program-lines, span). `span` reaches run() so the reported period is
# divided by the right number of periods.
def prog(body, *, hand=True, subs=WAIT160, span=SPAN_DEFAULT):
    p = [ONERR] + CLR + body + [END] + list(subs)
    return (p + (handler(span) if hand else []) + [ERRH], span)


def esyn(stmt):
    """A parse-surface case: the ON ERROR handler records ERR."""
    return ([ONERR] + CLR + ["10 " + stmt, END, ERRH], SPAN_DEFAULT)


def slowcase(n, *, burn, span=5):
    """A handler that optionally BURNS ~58 frames (600 empty FOR iterations at the
    VG-8020's ~625/s) and does its own stamping. `done` is set by the handler, so
    the capture is independent of the main program; $D00A==88 iff the main program
    ever resumed after the wait."""
    h = ["810 A=PEEK(&HD000):IFA<250THENPOKE&HD000,A+1"]
    if burn:
        h.append("811 FORQ=1TO600:NEXT")
    h += [f"812 IFA<>0ANDA<>{span}THENRETURN",
          f"813 H=PEEK(&H{JIFFY + 1:X}):L=PEEK(&H{JIFFY:X})"
          f":IFH<>PEEK(&H{JIFFY + 1:X})THEN813",
          "814 IFA=0THENPOKE&HD004,L:POKE&HD005,H:RETURN",
          "815 POKE&HD006,L:POKE&HD007,H:POKE&HD001,1:POKE&HD003,1:RETURN"]
    return prog([f"10 ONINTERVAL={n}GOSUB810", "20 INTERVALON",
                 "30 IFPEEK(&HD001)=0THEN30",
                 "40 INTERVALOFF:POKE&HD00A,88"],
                hand=False, span=span, subs=h)


def cadence(n, *, span=SPAN_DEFAULT, frames=160):
    """Arm at period n, enable, let a fixed FRAME window pass, disarm."""
    return prog([f"10 ONINTERVAL={n}GOSUB800", "20 INTERVALON",
                 "30 GOSUB950", "40 INTERVALOFF"],
                subs=waitn(950, frames), span=span)


CASES = {
    # --- §1.1 the event: period, measured BETWEEN FIRES ----------------------
    # cnt is the window count (phase-noisy by +-1); `period` = (J2-J1)/SPAN is
    # the real reading and is phase-free. n=1 additionally answers "can the trap
    # fire every frame at all", which bounds the whole design.
    # ⚠️ n=1 uses the HANDLER-SETS-DONE shape, not a main-program window. At one
    # fire per frame the handler is the whole frame on a machine ~3x slower than
    # the VG-8020, so the main program never resumes and a window-based case
    # captures done=0 -- the S_starves_main phenomenon, arriving here uninvited.
    # The reading is the inter-fire gap, which is exactly what n=1 is asking
    # about: the reference manages 1.0, zerobas is handler-limited above it.
    # Asserted per-machine as ">= 1" -- a trap cannot fire faster than its period.
    "A1_n1": slowcase(1, burn=False, span=30),
    "A2_n5": cadence(5, span=60, frames=340),
    "A3_n10": cadence(10, span=30, frames=340),
    "A4_n20": cadence(20, span=16, frames=340),

    # --- §1.2 the n domain and its errors ------------------------------------
    # n=0 is the interesting one: ERR 5, or "never fires", or "fires every frame"?
    "D0_n0": cadence(0),
    "D1_n255": cadence(255),
    "D2_n256": cadence(256),
    "D3_n32767": cadence(32767),
    "D4_n32768": cadence(32768),
    "D5_n65535": cadence(65535),
    "D6_nneg": cadence(-1),
    # 2.7: does the period come out 2 (truncate) or 3 (round)? The between-fires
    # measurement is what makes this answerable at all -- 60 periods is 162
    # frames if it rounds and 120 if it truncates, which no window count could
    # separate from ordinary cadence noise.
    # ⚠️ WAS 2.7. The truncate-vs-round question is real, but at n=2 the handler
    # costs MORE than the period on the repack build, so the measured gap is
    # handler-limited (2.3) and resolves nothing -- a case that cannot separate
    # its two hypotheses on one of the two machines is not a differential. The
    # same question at n=20.7 is 20 (truncate) against 21 (round), five per cent
    # apart, and both machines can measure it.
    "D7_nfrac": cadence(20.7, span=25, frames=560),
    "D8_nexpr": prog(["8 Q=7", "10 ONINTERVAL=QGOSUB800", "20 INTERVALON",
                      "30 GOSUB950", "40 INTERVALOFF"], span=20),

    # Round 2 of the domain. D1..D6 established that 255/256/32767/32768/65535/-1
    # are ALL accepted without error, which is only consistent with an UNSIGNED
    # 16-bit period -- and therefore with the same address-domain conversion
    # `TIME=n` needs (docs/spec-basic-time.md §4: wrap by -65536 above 32767,
    # truncate toward zero, ERR 6 outside -32768..65535). These five cases test
    # that hypothesis at its edges rather than inferring it:
    #   D9  65536   -> outside the domain: ERR 6 if the conversion is shared
    #   D10 -32768  -> the low edge, accepted (== 32768)
    #   D11 -32769  -> just outside: ERR 6
    #   D12 255 over a 700-frame window -> 2 fires, proving D1's silence was a
    #       long period and NOT a silent disarm (a zero that means two things is
    #       not a reading)
    #   D13 -65531  -> the DECISIVE one. Under the shared conversion this is out
    #       of domain (ERR 6). Under a raw mod-65536 it is period 5 and fires 68
    #       times in 340 frames. Nothing else separates the two.
    "D9_n65536": cadence(65536),
    "D10_nm32768": cadence(-32768),
    "D11_nm32769": cadence(-32769),
    "D12_n255_long": cadence(255, span=2, frames=700),
    "D13_nm65531": cadence(-65531, span=60, frames=340),

    # --- §1.3 arm vs enable vs suspend ---------------------------------------
    "B_armed_not_on": prog(["10 ONINTERVAL=10GOSUB800", "30 GOSUB950"]),
    "C1_off": prog(["10 ONINTERVAL=10GOSUB800", "20 INTERVALOFF", "30 GOSUB950"]),
    "C2_stop": prog(["10 ONINTERVAL=10GOSUB800", "20 INTERVALSTOP", "30 GOSUB950"]),
    # `INTERVAL ON` with no handler armed: error, or silently nothing?
    "E_no_handler": prog(["20 INTERVALON", "30 GOSUB950"], hand=False),

    # G/H: does STOP LATCH one elapsed period and release it at the next ON,
    # while OFF forgets? (the T1..T4 family answer -- STOP remembers, OFF does
    # not.) Suspend for well over one period, then enable and read the count in a
    # window SHORTER than one period, so a latched release is distinguishable
    # from an ordinary first fire.  aux = count during the suspended phase (must
    # be 0), cnt = count in the short window after re-enabling.
    "G_stop_latch": prog(["10 ONINTERVAL=60GOSUB800", "20 INTERVALON",
                          "22 GOSUB960", "24 INTERVALSTOP", "26 GOSUB970",
                          "28 POKE&HD008,PEEK(&HD000):POKE&HD000,0",
                          "30 INTERVALON", "32 GOSUB960", "34 INTERVALOFF"],
                         subs=WAIT60 + WAIT300),
    "H_off_latch": prog(["10 ONINTERVAL=60GOSUB800", "20 INTERVALON",
                         "22 GOSUB960", "24 INTERVALOFF", "26 GOSUB970",
                         "28 POKE&HD008,PEEK(&HD000):POKE&HD000,0",
                         "30 INTERVALON", "32 GOSUB960", "34 INTERVALOFF"],
                        subs=WAIT60 + WAIT300),

    # --- §1.4 where the period is counted FROM -------------------------------
    # P: n=300; run 200 frames, STOP, run 200 more, ON, run 200 more. If the
    #    counter is free-running from the arm, a fire lands inside the first
    #    200-frame post-resume span; if `INTERVAL ON` RELOADS it, none does.
    #    aux = count before the suspend (must be 0 -- 200 < 300 frames).
    "P_on_reloads": prog(["10 ONINTERVAL=300GOSUB800", "20 INTERVALON",
                          "22 GOSUB965", "24 INTERVALSTOP",
                          "26 POKE&HD008,PEEK(&HD000)", "28 GOSUB965",
                          "30 INTERVALON", "32 GOSUB965", "34 INTERVALOFF"],
                         subs=waitn(965, 200)),
    # P2: does RE-ARMING (`ON INTERVAL=n GOSUB` again, state untouched) reload
    #     the counter? Same shape, without ever leaving ON.
    "P2_rearm_reloads": prog(["10 ONINTERVAL=300GOSUB800", "20 INTERVALON",
                              "22 GOSUB965",
                              "24 POKE&HD008,PEEK(&HD000)",
                              "26 ONINTERVAL=300GOSUB800", "28 GOSUB965",
                              "30 POKE&HD009,PEEK(&HD000)",
                              "32 GOSUB965", "34 INTERVALOFF"],
                             subs=waitn(965, 200)),

    # --- §1.5 servicing: no catch-up ----------------------------------------
    # A handler that outlasts its own period. n=5 over a 300-frame window is 60
    # periods; if elapsed periods QUEUE, the count approaches 60, and if the trap
    # simply re-arms on RETURN it is bounded by 300/(handler length). The handler
    # burn is the discriminator, so it is deliberately long.
    # S/S2: does an elapsed period QUEUE while the handler is running, or is the
    # trap simply re-armed on RETURN? The discriminator is a handler that outlasts
    # its own period, and the reading is the INTER-FIRE GAP: no catch-up puts it at
    # the handler's length, queueing puts it at n.
    #
    # ⚠️ TWO ATTEMPTS AT THIS CASE CAPTURED done=0 -- VOID, never a zero. Both
    # sized the observation window in FRAMES and waited for it in the MAIN
    # program: with the handler dominating the CPU the frame-bounded wait loop
    # gets a couple of statements per period and does not finish inside the
    # deadline, whatever n and whatever the burn. The fix is not a bigger deadline
    # but a different observable: THE HANDLER DOES ITS OWN TIMING (it stamps JIFFY
    # at fire #1 and fire #1+span exactly as the cadence cases do) and the main
    # program just spins on a flag the handler sets. Nothing then depends on the
    # main program making frame-scale progress -- which is precisely the thing a
    # slow handler takes away. S2 is the control: same shape, no burn, so its gap
    # must come back at n and prove the apparatus can read a short gap at all.
    # ...and the THIRD shape is the one that works. `done` is set BY THE HANDLER at
    # the last stamp, so the capture never depends on the main program running at
    # all; $D00A (aux3) is poked 88 by the statement AFTER the wait, so whether
    # the main program ever resumed becomes a READING instead of a deadline.
    "S_starves_main": slowcase(20, burn=True),
    "S2_fast_control": slowcase(20, burn=False),
    # S3: the handler FITS inside its period (58 frames of burn, n=100), so the
    # main program is not starved -- and the inter-fire gap then answers a
    # question no other case can: is the next period counted from the FIRE
    # (gap == 100) or from the RETURN (gap == 100 + 58)?
    # ⚠️ WAS n=100, which fits the ~58-frame burn on the VG-8020 and NOT the
    # ~174 frames the same loop costs on the repack build -- so the slow side
    # starved and answered nothing. n=300 fits on both, and the question is
    # unchanged: gap == 300 means the period is counted from the FIRE, gap ==
    # 300 + handler means it is counted from RETURN.
    "S3_from_fire_or_return": slowcase(300, burn=True),

    # G2/H2: read the release DIRECTLY. Suspend for three whole periods, zero the
    # counter, re-enable, and read the count after a window far SHORTER than one
    # period -- so anything counted can only be a latch releasing, never an
    # ordinary first fire. G_stop_latch/H_off_latch inferred this from a 2-vs-1
    # count over a full period; this measures it.
    "G2_stop_release": prog(["10 ONINTERVAL=100GOSUB800", "20 INTERVALON",
                             "22 GOSUB950", "24 INTERVALSTOP", "26 GOSUB960",
                             "28 POKE&HD008,PEEK(&HD000):POKE&HD000,0",
                             "30 INTERVALON", "32 GOSUB940",
                             "34 INTERVALOFF"],
                            subs=waitn(940, 8) + waitn(950, 250) + waitn(960, 300)),
    # H3: after OFF and a re-ON, is the next fire a WHOLE period away (the arming
    # reload) or whatever was left of the interrupted one? The ON phase is 250
    # frames at n=100, so the counter is ~50 into its third period when OFF lands;
    # a 60-frame window after re-ON separates "reloaded" (0 fires) from "kept its
    # phase or free-ran" (1).
    "H3_off_reloads": prog(["10 ONINTERVAL=100GOSUB800", "20 INTERVALON",
                            "22 GOSUB950", "24 INTERVALOFF", "26 GOSUB940",
                            "28 POKE&HD008,PEEK(&HD000):POKE&HD000,0",
                            "30 INTERVALON", "32 GOSUB960", "34 INTERVALOFF"],
                           subs=waitn(940, 30) + waitn(950, 250) + waitn(960, 60)),
    "H2_off_release": prog(["10 ONINTERVAL=100GOSUB800", "20 INTERVALON",
                            "22 GOSUB950", "24 INTERVALOFF", "26 GOSUB960",
                            "28 POKE&HD008,PEEK(&HD000):POKE&HD000,0",
                            "30 INTERVALON", "32 GOSUB940",
                            "34 INTERVALOFF"],
                           subs=waitn(940, 8) + waitn(950, 250) + waitn(960, 300)),

    # --- §1.6 the parse surface ---------------------------------------------
    # L/R/R2 mirror T4's §1.4: does a BARE `ON INTERVAL=n GOSUB` (no line) CLEAR
    # the handler slot, as the reference does for all four other events (the
    # family sweep in T4 that exposed a shipped T1 divergence)?
    "L_syn_noline": esyn("ONINTERVAL=10GOSUB"),
    "R_bare_disarms": prog(["10 ONINTERVAL=10GOSUB800", "20 INTERVALON",
                            "22 GOSUB960",
                            "24 POKE&HD008,PEEK(&HD000):POKE&HD000,0",
                            "26 ONINTERVAL=10GOSUB", "28 GOSUB960",
                            "30 POKE&HD009,PEEK(&HD000)"], subs=WAIT60),
    "R2_rearm": prog(["10 ONINTERVAL=10GOSUB800", "20 INTERVALON",
                      "22 GOSUB960",
                      "24 POKE&HD008,PEEK(&HD000):POKE&HD000,0",
                      "26 ONINTERVAL=10GOSUB", "28 GOSUB960",
                      "30 POKE&HD009,PEEK(&HD000):POKE&HD000,0",
                      "32 ONINTERVAL=10GOSUB800", "34 GOSUB960",
                      "36 POKE&HD00A,PEEK(&HD000)"], subs=WAIT60),
    "J_syn_on_goto": esyn("ONINTERVAL=10GOTO800"),
    "K_syn_bare": esyn("INTERVAL"),
    "M_undef_line": esyn("ONINTERVAL=10GOSUB777"),
    "N_syn_no_eq": esyn("ONINTERVALGOSUB800"),
    "O_syn_junk": esyn("INTERVALFOO"),
    # Q: the parser must stop CLEANLY at the statement separator, not swallow it.
    "Q_noline_then": esyn("ONINTERVAL=10GOSUB:POKE&HD008,77"),
    "Q2_on_then": esyn("INTERVALON:POKE&HD008,77"),
}


# --- what each case ASSERTS -------------------------------------------------
# `eq`  : fields that must match the reference EXACTLY. Error codes, no-fire
#         cases and latch-release counts all live here -- none of them depends on
#         how fast the machine runs.
# `per` : predicates checked on EACH machine independently. Anything that is a
#         PERIOD lives here, with a tolerance of 1/span + 5%: the stamps are
#         quantised to the statement boundary the trap dispatched at, so the pair
#         carries +-1 frame of endpoint jitter by construction.
# Every case additionally requires done==1; a reading from a program that errored
# out or never finished is a FAILURE, never a zero.
EQ, PER = "eq", "per"


def _per(n):
    """period == n, within the span's own endpoint jitter."""
    # tolerance = the span's own endpoint jitter (+-1 frame over `span` periods)
    # plus 2%. It was 5%, which at n=20 is +-1.0 -- wide enough to accept 21 when
    # the answer is 20, i.e. wide enough to accept ROUNDING when the finding is
    # TRUNCATION. A tolerance that cannot reject the rival hypothesis is not one.
    return [(f"period == {n}",
             lambda r, n=n: r["period"] and abs(r["period"] - n) <= 1.0 / r["span"] + 0.02 * n)]


EXPECT = {
    # §1.1 the period is exactly n frames; n=1 fires EVERY frame
    # A1 is per-machine and one-sided: 1 frame is the floor, and the slow build
    # sits above it because the handler, not the period, is the limit there.
    "A1_n1": {EQ: ["err"], PER: [("fires, and never faster than its period",
                                  lambda r: r["period"] >= 1)]},
    "A2_n5": {PER: _per(5)},
    "A3_n10": {PER: _per(10)}, "A4_n20": {PER: _per(20)},
    # §1.2 the n domain IS the address domain -- an equality differential
    # throughout, since an error code does not depend on machine speed
    "D0_n0": {EQ: ["cnt", "err"]},          "D1_n255": {EQ: ["cnt", "err"]},
    "D2_n256": {EQ: ["cnt", "err"]},        "D3_n32767": {EQ: ["cnt", "err"]},
    "D4_n32768": {EQ: ["cnt", "err"]},      "D5_n65535": {EQ: ["cnt", "err"]},
    "D6_nneg": {EQ: ["cnt", "err"]},        "D7_nfrac": {EQ: ["err"], PER: _per(20)},
    "D8_nexpr": {EQ: ["err"], PER: _per(7)},
    "D9_n65536": {EQ: ["cnt", "err"]},      "D10_nm32768": {EQ: ["cnt", "err"]},
    "D11_nm32769": {EQ: ["cnt", "err"]},
    # D12: 255 really IS a 255-frame period and not a silent disarm. The COUNT is
    # per-machine (700 frames / 255), but "at least one fire" is the point.
    "D12_n255_long": {EQ: ["err"], PER: [("fires at all", lambda r: r["cnt"] >= 1)]},
    "D13_nm65531": {EQ: ["cnt", "err"]},
    # §1.3 arm vs enable vs suspend -- all equality, all zero-or-small counts
    "B_armed_not_on": {EQ: ["cnt", "err"]}, "C1_off": {EQ: ["cnt", "err"]},
    "C2_stop": {EQ: ["cnt", "err"]},        "E_no_handler": {EQ: ["cnt", "err"]},
    "G_stop_latch": {EQ: ["cnt", "err", "aux"]},
    "H_off_latch": {EQ: ["cnt", "err", "aux"]},
    # G2/H2 are THE decisive pair: the window after re-enabling is far shorter
    # than one period, so anything counted can only be a latch releasing.
    "G2_stop_release": {EQ: ["cnt", "err", "aux"]},
    "H2_off_release": {EQ: ["cnt", "err", "aux"]},
    # §1.4 where the period is counted from
    "P_on_reloads": {EQ: ["cnt", "err", "aux"]},
    "P2_rearm_reloads": {EQ: ["cnt", "err", "aux", "aux2"]},
    "H3_off_reloads": {EQ: ["cnt", "err", "aux"]},
    "S3_from_fire_or_return": {EQ: ["err", "aux3"], PER: _per(300)},
    # §1.5 a handler that outlasts its period starves the main program. aux3==0
    # (the statement after the wait never ran) is the READING, not a timeout.
    "S_starves_main": {EQ: ["err", "aux3"],
                       PER: [("gap >> n (no catch-up)", lambda r: r["period"] > 30)]},
    "S2_fast_control": {EQ: ["err", "aux3"], PER: _per(20)},
    # §1.6 the parse surface
    "L_syn_noline": {EQ: ["cnt", "err"]},
    "R_bare_disarms": {EQ: ["err", "aux2"],
                       PER: [("armed fires", lambda r: r["aux"] > 0)]},
    "R2_rearm": {EQ: ["err", "aux2"],
                 PER: [("armed fires", lambda r: r["aux"] > 0),
                       ("re-arm resumes", lambda r: r["aux3"] > 0)]},
    "J_syn_on_goto": {EQ: ["cnt", "err"]},  "K_syn_bare": {EQ: ["cnt", "err"]},
    "M_undef_line": {EQ: ["cnt", "err"]},   "N_syn_no_eq": {EQ: ["cnt", "err"]},
    "O_syn_junk": {EQ: ["cnt", "err"]},     "Q_noline_then": {EQ: ["cnt", "err", "aux"]},
    "Q2_on_then": {EQ: ["cnt", "err", "aux"]},
}


def fmt(r):
    if not r:
        return "NO CAPTURE (apparatus failure)"
    if not r["done"]:
        return f"VOID done=0 {r}"          # never read as a zero -- see docstring
    return (f"cnt={r['cnt']:>3} err={r['err']} "
            f"period={r['period']:>7} (span={r['span']}) "
            f"j1={r['j1']:>5} j2={r['j2']:>5} "
            f"aux={r['aux']:>3} aux2={r['aux2']:>3} aux3={r['aux3']:>3} t={r['t']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", action="append", default=None,
                    help="substring filter on case names (repeatable)")
    ap.add_argument("--ref-only", action="store_true")
    ap.add_argument("--zb-only", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--report", action="store_true",
                    help="print readings without asserting (characterization mode)")
    a = ap.parse_args()

    names = [n for n in CASES if not a.only or any(o in n for o in a.only)]
    if a.list:
        for n in names:
            lines, span = CASES[n]
            print(f"--- {n}  (span={span})")
            for ln in lines:
                print("   ", ln)
        return 0

    print(f"ref = {REF_MACHINE}\nzb  = {ZB_MACHINE}\n", flush=True)
    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL':5} {label}" + (f"  {detail}" if detail else ""),
              flush=True)
        ok = ok and cond

    for n in names:
        lines, span = CASES[n]
        ref = None if a.zb_only else run(REF_MACHINE, lines, span=span)
        zb = None if a.ref_only else run(ZB_MACHINE, lines, span=span)
        if a.report:
            out = [f"{n}"]
            if not a.zb_only:
                out.append(f"    ref  {fmt(ref)}")
            if not a.ref_only:
                out.append(f"    zb   {fmt(zb)}")
            print("\n".join(out), flush=True)
            continue
        spec = EXPECT.get(n, {})
        for side, r in (("ref", ref), ("zb ", zb)):
            if r is None and ((side == "ref" and a.zb_only) or (side == "zb " and a.ref_only)):
                continue
            # `done` FIRST: without it no other field means anything.
            check(f"[{side}] {n:24} {fmt(r)}", bool(r) and r["done"] == 1)
            for lbl, pred in spec.get(PER, []):
                check(f"[{side}] {n:24} {lbl}",
                      bool(r) and r["done"] == 1 and bool(pred(r)))
        fields = spec.get(EQ, [])
        if fields and ref and zb:
            same = all(ref[f] == zb[f] for f in fields)
            check(f"[zb ] {n:24} == ref on {','.join(fields)}", same,
                  "" if same else f"ref={ {f: ref[f] for f in fields} } "
                                  f"zb={ {f: zb[f] for f in fields} }")

    print("\n" + ("ALL PASS" if ok else "SOME FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
