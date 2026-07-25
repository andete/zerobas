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
  * The signal is a RAM SENTINEL ($D000), not screen text: the REPL echoes each
    typed program line, so a handler marker like PRINT"TRAPPED" appears in the
    LISTING echo whether or not the handler ran -- fatal for the "no-fire" cases.
    A POKEd byte in free RAM is echo-immune.
  * PROGRAM ENTRY GOES THROUGH KEYBUF INJECTION (probes/lib/omsx_repl.py), not
    openMSX `type` -- retrofitted from the T3 KEY gate, which hit three distinct
    `type` flake modes (a swallowed Enter concatenating two lines, every second
    character dropped by overlapping type streams, and a doubled keystroke turning
    `900 ...` into `9900 ...`). All three are INVISIBLE in the sentinels: the
    program never runs, the sentinels read power-on garbage, and the case looks
    like a semantic failure. Widening the per-character schedule traded one
    direction of flake for the other, which is the signal that timing was the wrong
    knob. `--screen` dumps the SCREEN 0 name table, which is the only way to tell a
    mangled line from a semantic failure. The Ctrl-STOP PRESSES still go through the
    real matrix: the trap's event source is the BIOS scan, so injecting them would
    bypass the mechanism under test.

EVERY READING IS GATED (retrofitted 2026-07-25, alongside the same fix to the T2
STRIG gate). A zero sentinel used to be accepted at face value, so a program that
never ran, died on a syntax error, or was still spinning was indistinguishable from
a correctly-not-firing trap -- the arc's standing "a baseline that cannot produce a
non-zero answer proves nothing" trap. In T2 that blind spot hid a real shipped
tokeniser bug for weeks. T1 cannot copy T3's single `done`-before-END sentinel,
because THREE OF ITS FOUR CASES DO NOT REACH AN `END`: B/B2/D terminate by BREAKING
out of the program, which by construction runs no BASIC code. So the gate carries
two bytes and demands both:

  $D002 RAN   1 = every arming statement executed (POKEd at line 25, after
                  `ON STOP GOSUB` / `STOP ON|OFF`, before the FOR delay). A syntax
                  error in the statement UNDER TEST leaves it 0 -> FAIL. This is
                  the byte that would have caught T2's bug.
              2 = the program fell PAST the infinite `40 GOTO40` poll loop, which
                  can only mean line 40 was mangled -> FAIL.
  $D003 DONE  1 = the machine is back at command level. It cannot be set by the
                  program (a break runs nothing), so the harness sets it: a direct
                  `POKE&HD003,1` is injected into KEYBUF a few emulated seconds
                  after the last key-up. If the program ENDED or BROKE, the REPL
                  reads it from the type-ahead buffer and executes it; if the
                  program is STILL RUNNING, the bytes sit unread in the buffer and
                  the capture reads 0 -> FAIL. So "the trap never fired AND the
                  Ctrl-STOP never broke the program either" can no longer pass as
                  a quiet zero.

The capture POLLS $D003 and fires the moment it is set, with a hard deadline that
captures done==0 and fails the case (the two machines' loop rates differ ~7x, so a
fixed wait would either truncate the slow one or idle on the fast one).

THE DISCRIMINATING REGIME (the load-bearing lesson, oracle-characterized 2026-07-25):
a HELD Ctrl-STOP in a tight `GOTO` loop BREAKS on BOTH machines -- that regime does
NOT discriminate. The feature's happy path only appears with a brief TAP during a
DELAY (`FOR..NEXT`) followed by a poll loop: real MSX latches the Ctrl-STOP at
interrupt time (INTFLG) so the released tap still fires the handler a boundary later.
zerobas catches the same tap via its live BREAKX poll; the fix (spec §12.2, "R1") was
to stop the freshly-entered handler from re-breaking on its own first boundary while
the triggering key is still (briefly) down -- a one-VBLANK grace (STOPGRACE) cleared
by event_poll, mirroring INTFLG's clear-on-fire / re-set-next-frame window.

Cases (sentinel $D000 = handler-fire flag; short lines; tap@+0.3s during the FOR;
all three assert ran==1 and done==1 as well):

  A  on_fires     10 ON STOP GOSUB 100 : 20 STOP ON : 25 POKE ran,1 : 30 FOR..NEXT
                  : 40 GOTO40 : 100 POKE flag,1:END
                  tap during the FOR -> handler runs -> flag=1, ends at the handler
  B  armed_off    (no STOP ON) the arm alone must NOT enable        -> break, flag=0
  B2 stop_off     20 STOP ON:STOP OFF  an enabled trap, then disabled -> flag=0
       (B2 also gates the statement-continuation fix: `ret` after the arming sub-
        keyword used to SWALLOW the rest of the line, so `STOP OFF` was a no-op.)

All three are machine-agnostic RAM facts, asserted absolutely AND diffed
zerobas==reference. A fourth case (D, interruptible) runs a tap-then-hold and is
reported as a straight differential -- its two-press timing is not robust enough to
assert its FLAG, though `ran`/`done` are asserted on both machines.

WHAT THE `done` GATE FOUND, AND THE SEMANTICS FIX IT FORCED (2026-07-25, spec §12.3).
D's old green was an artifact of a too-short capture window -- exactly the failure
mode this arc keeps re-learning. The old gate captured 9 s after the last key-up and
read flag==1 on BOTH machines, and called that agreement. The screen at that instant
shows the program STILL RUNNING: the handler's own `105 FORK=1TO9000:NEXT` takes
~15 s on the reference, so flag==1 did not mean "the handler was aborted", it meant
"the handler has not reached line 108 yet". Both sides were being read mid-loop.

Read once the machine is actually back at command level, the sides disagreed
(reproducibly, 2 trials x 5 press patterns incl. a 40-edge tap train and an 11 s
hold): the reference COMPLETED the handler, zerobas ABORTED it. `ON STOP GOSUB` +
`STOP ON` makes a program unbreakable from the keyboard -- that is what the statement
is FOR -- and zerobas's STOPGRACE, a one-VBLANK timer, aborted the handler the moment
it expired. Ctrl-STOP is instead EDGE-latched into PENDING while the entry is ON *or*
SERVICING and fires once after RETURN, which is the T2 STRIG model. That is now what
basic/program.asm rp_break does; STOPGRACE is gone (and page 1 gained 16 B).

The oracle also KILLED the obvious other half of that move. `STRIG(n) ON` seeds the
edge shadow so a trigger already held cannot manufacture a press, and ex_stop was
first written to mirror it. Case E says no: a handler that re-arms itself under a
held key fires again and keeps firing on the reference (122 fires vs the seeded
build's 1), so ex_stop carries no seed. Cases C/C2/E exist to pin all three rules.

This also withdrew the claim this docstring used to carry, that "the handler being
Ctrl-STOP-abortable is oracle-confirmed": that came from this same case through the
same short window. tests/test_traps.py pins zerobas's own state machine and was
green throughout -- it was the ORACLE half that had never really been measured.

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

FLAG = 0xD000    # handler sentinel: 0 = never ran; 1 = fired (2 = handler completed body)
RAN = 0xD002     # 1 = the arming statements all executed; 2 = fell past the poll loop
DONE = 0xD003    # 1 = back at command level (set by the INJECTED direct POKE)
CTRL_ROW, CTRL_BIT = 6, 0x02
STOP_ROW, STOP_BIT = 7, 0x10

DONE_CMD = f"POKE&H{DONE:04X},1"   # injected as a DIRECT line, see run()


def run(machine, prog, presses, *, boot=6.0, step=3.0, run_gap=2.0, done_gap=3.0,
        poll_from=1.0, deadline=900.0, timeout=900, screen=False):
    """Boot `machine` (BASIC in-ROM, no cart), inject `prog` + RUN through KEYBUF,
    apply the Ctrl-STOP `presses` (each a (down, up) offset in emulated seconds
    after RUN), then capture FLAG/RAN/DONE as soon as DONE is set -- or at
    `deadline` emulated seconds regardless, which captures done==0 and FAILS the
    case. Returns a dict or None. One boot per call = power-on fresh.

    `run_gap` is the delay from the RUN injection to the zero of the press
    timeline. It is 2.0 because that is exactly what the previous matrix-typing
    schedule produced (text at t, CR at t+2, presses measured from t+4 = CR+2), and
    the whole gate turns on the tap landing INSIDE the FOR delay -- moving the zero
    would move the tap out of the only regime that discriminates.

    `done_gap` is how long after the last key-up the direct `POKE&HD003,1` is
    injected. It must be long enough that the break (or the handler's END) has
    already returned the machine to command level, so the REPL consumes the line
    immediately; a program that is still running leaves it unread in KEYBUF and the
    case is captured with done==0."""
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="stoptrap_")
    os.close(out_fd)
    lines = [
        "set throttle off",
        f'proc __cap {{}} {{ set f [open {{{out_path}}} w];'
        f' puts $f "flag=[debug read memory {FLAG}] ran=[debug read memory {RAN}]'
        f' done=[debug read memory {DONE}] t=[expr {{int([machine_info time])}}]";'
        + (f' binary scan [debug read_block VRAM 0x0000 960] H* h;'
           f' puts $f "screen=$h";' if screen else '')
        + f' close $f; exit }}',
        f'proc __poll {{}} {{ if {{[debug read memory {DONE}] != 0}} {{ __cap }}'
        f' else {{ after time 1 __poll }} }}',
        # KEYBUF injection (probes/lib/omsx_repl.py): write the bytes into the
        # 40-byte type-ahead buffer and point GETPNT/PUTPNT at them, so CHGET
        # delivers the line with no matrix scan and no typing schedule.
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
        if len(text) <= MAX_DIRECT:
            lines.append(f'after time {t:g} {{ __inj {{{text}}} }}')
            t += step
            continue
        chunks = [text[i:i + MAX_DIRECT] for i in range(0, len(text), MAX_DIRECT)]
        for k, c in enumerate(chunks):
            proc = "__inj" if k == len(chunks) - 1 else "__key"   # CR only on last
            lines.append(f'after time {t:g} {{ {proc} {{{c}}} }}')
            t += step
    run_done = t - step + run_gap
    last = run_done
    for dn, up in presses:
        for row, mask in ((CTRL_ROW, CTRL_BIT), (STOP_ROW, STOP_BIT)):
            lines.append(f'after time {run_done + dn:g} {{ keymatrixdown {row} {hex(mask)} }}')
        for row, mask in ((STOP_ROW, STOP_BIT), (CTRL_ROW, CTRL_BIT)):
            lines.append(f'after time {run_done + up:g} {{ keymatrixup {row} {hex(mask)} }}')
        last = max(last, run_done + up)
    # THE `done` SENTINEL. A break runs no BASIC code, so the program cannot mark
    # its own termination in B/B2/D -- the harness marks it instead, from the
    # command line the break returns to. Injected AFTER the last key-up so it can
    # never be swallowed by the break itself.
    lines.append(f'after time {last + done_gap:g} {{ __inj {{{DONE_CMD}}} }}')
    lines.append(f"after time {last + done_gap + poll_from:g} {{ __poll }}")
    lines.append(f"after time {run_done + deadline:g} {{ __cap }}")

    fd, tcl_path = tempfile.mkstemp(suffix=".tcl", prefix="stoptrap_")
    os.write(fd, ("\n".join(lines) + "\n").encode())
    os.close(fd)
    cmd = [OMSX, "-machine", machine, "-command", "set renderer none", "-script", tcl_path]
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
    res = None
    if os.path.exists(out_path):
        txt = open(out_path).read().strip()
        os.unlink(out_path)
        if txt:
            res = {}
            for kv in txt.split():
                k, _, v = kv.partition("=")
                res[k] = v if k == "screen" else int(v)
    return res


def show_screen(res):
    """Render the SCREEN 0 name table ($0000, 40x24) captured with screen=True.
    Reading the SCREEN is how a mangled program line is told apart from a semantic
    failure -- in the sentinels alone the two are identical."""
    if not res or "screen" not in res:
        print("  (no screen captured)")
        return
    b = bytes.fromhex(res["screen"])
    for r in range(24):
        row = b[r * 40:(r + 1) * 40]
        line = "".join(chr(c) if 32 <= c < 127 else ("." if c else " ") for c in row)
        if line.strip():
            print(f"  {r:2d}|{line}")


# --- cases (short lines; tap@+0.3s lands inside the FOR delay on both machines) ---
# FOR..NEXT then a distinct GOTO poll loop: the tap fires the trap during the FOR;
# the handler ENDs. A trailing GOTO keeps the program alive if it did NOT fire.
CLR = "5 POKE&HD000,0:POKE&HD002,0:POKE&HD003,0"
RANOK = "25 POKE&HD002,1"        # every arming statement executed (see the header)
DELAY = "30 FORI=1TO4000:NEXT"
POLL = "40 GOTO40"
OVERRUN = "45 POKE&HD002,2:END"  # unreachable unless line 40 was mangled -> FAIL
HEND = "100 POKE&HD000,1:END"

# TAP LENGTH: 100 ms, not the 30 ms this gate shipped with. 30 ms is MARGINAL
# against the BIOS's per-VBLANK scan grid (20 ms on a PAL VG-8020) and whether it
# is seen depends on where it lands within a frame. Swept on the reference at six
# sub-frame phases x five durations while retrofitting the `done` sentinel:
#     30 ms fired at 3 of 6 phases, 50 ms at 5 of 6, 70/90/120 ms at 6 of 6.
# The old schedule passed because its absolute press time happened to sit on a
# lucky phase; moving to KEYBUF program entry shifted every press by one slot and
# the same 30 ms tap then MISSED on the reference -- which the new `done` sentinel
# reported as a failure instead of silently reading flag=0 as "correctly no fire".
# 100 ms is 5 PAL frames, still a brief RELEASED tap during the FOR delay (the only
# regime that discriminates -- a HELD key breaks on both machines), so it changes
# nothing about what is asserted; it just stops the gate depending on luck.
TAP = [(0.3, 0.40)]

# C/C2 gate the SERVICING semantics (spec §12.3, oracle-measured 2026-07-25): a
# Ctrl-STOP arriving while the handler runs must NOT abort it -- it is edge-latched
# and fires exactly once more after RETURN. The handler here COUNTS its fires and
# RETURNs (A/B/B2's handler ENDs, so they can never see a second one), and takes its
# long delay on the FIRST invocation only, so the second fire does not spend another
# full delay before the program finishes. The program sets `done` itself at line 40.
#
# C IS THE BASELINE AND IT IS PART OF THE MEASUREMENT: same program, same first tap,
# no press inside the handler -> the count MUST read exactly 1. Without it, "C2 reads
# 2" would not distinguish a latched second fire from a handler that fires twice on
# its own, and this arc has been burned by baselines that could not produce the
# discriminating answer.
CNTH = ["100 POKE&HD000,PEEK(&HD000)+1",
        "105 IFPEEK(&HD000)=1THENFORK=1TO4000:NEXT",   # long delay on the FIRST fire
        "108 RETURN"]
CPROG = [CLR, "10 ON STOP GOSUB 100", "20 STOP ON", RANOK,
         "30 FORI=1TO6000:NEXT", "40 POKE&HD003,1:END", *CNTH]

ASSERTED = [
    ("A_on_fires", [CLR, "10 ON STOP GOSUB 100", "20 STOP ON",
                    RANOK, DELAY, POLL, OVERRUN, HEND], TAP, 1),
    ("B_armed_off", [CLR, "10 ON STOP GOSUB 100",
                     RANOK, DELAY, POLL, OVERRUN, HEND], TAP, 0),
    ("B2_stop_off", [CLR, "10 ON STOP GOSUB 100", "20 STOP ON:STOP OFF",
                     RANOK, DELAY, POLL, OVERRUN, HEND], TAP, 0),
    ("C_handler_baseline", CPROG, TAP, 1),
    ("C2_press_in_handler_latches", CPROG, TAP + [(2.0, 2.10)], 2),
    # F: `ON STOP GOSUB` with NO LINE REFERENCE is ACCEPTED and CLEARS the handler.
    # This gates a MEASURED DIVERGENCE that zerobas shipped and that the T4 SPRITE
    # characterization round's family sweep caught (spec-traps-t4-sprite.md §1.5):
    # ex_on_stop used to raise a trappable ERR 2 here, where the reference accepts
    # the form for all four events and zeroes that entry's handler link.
    #
    # Line 40 writes flag=5 rather than just `done`, so the case discriminates all
    # THREE outcomes instead of lumping two of them into "0":
    #     flag 1 -> the trap FIRED  => the bare form did not clear the handler
    #     flag 5 -> the program ran to completion => Ctrl-STOP was swallowed
    #     flag 0 -> Ctrl-STOP broke the program mid-delay
    # and against the PRE-FIX build it fails for a fourth reason that is not a flag
    # value at all: the untrapped ERR 2 aborts the RUN before line 25, so `ran`
    # carries the failure. Both machines must agree on the same outcome -- that is
    # what makes this an equality differential rather than a restatement of the fix.
    #
    # MEASURED on the VG-8020: flag = 0, twice. So `STOP ON` with a CLEARED handler
    # does NOT swallow Ctrl-STOP -- the break happens normally. Worth stating because
    # it is the OPPOSITE of the KEY trap, where `KEY(1) ON` with an empty handler
    # slot still swallows the key and fires nothing (spec-traps-t3-key.md §1.2, and
    # diversion there follows the STATE ALONE). For STOP the break suppression tracks
    # handler!=0, not the state bit -- consistent with check_traps' fire condition
    # (state==ON && PENDING && handler!=0) but NOT derivable from the T3 analogue,
    # which is exactly why it is measured here instead of assumed.
    ("F_bare_gosub_disarms",
     [CLR, "10 ON STOP GOSUB 100", "20 STOP ON", "22 ON STOP GOSUB", RANOK, DELAY,
      "40 POKE&HD000,5:POKE&HD003,1:END", HEND], TAP, 0),
]

# E: NOT an equality differential -- the PROPERTY only (cf. the T3 KEY gate's REPEAT
# group). A handler that RE-ARMS ITSELF under a held Ctrl-STOP fires again, and keeps
# firing; the COUNT is a per-machine artifact of how many line boundaries fit in the
# run (the reference is ~7x faster on this loop), so asserting equality would gate the
# wrong thing. `102 STOP OFF:STOP ON` is deliberately ONE line: the run loop polls
# BREAKX per LINE, so there is no boundary inside the OFF window where the held key
# could break the program instead.
#
# This is the case that DELETED the arming seed. `STRIG(n) ON` seeds the edge shadow
# so a trigger already held cannot manufacture a press (T2 oracle); the obvious move
# was to mirror that in ex_stop, and it was written that way first. The reference says
# otherwise -- 122 fires against the seeded build's 1 -- so ex_stop carries no seed and
# says why. Without this case nothing would ever catch a well-meaning "harmonisation".
REARM = [
    ("E_rearm_under_held_key_refires",
     [CLR, "10 ON STOP GOSUB 100", "20 STOP ON", RANOK,
      "30 FORI=1TO6000:NEXT", "40 POKE&HD003,1:END",
      "100 POKE&HD000,PEEK(&HD000)+1",
      "102 STOP OFF:STOP ON",           # re-arm INSIDE the handler, key still down
      "106 RETURN"],
     [(0.3, 200.0)], 2),                # want flag >= 2, i.e. "it re-fires at all"
]

# D: fire (tap), then HOLD during the handler's own delay. flag 1 = the handler was
# aborted mid-delay; flag 2 = it ran to completion. Straight differential (the flag
# itself is not asserted -- two-press timing), but `ran`/`done` ARE asserted: a
# reading taken while the program is still spinning is not a datum. That gate is what
# exposed the STOPGRACE divergence written up in the header; both sides now read 2.
# Do not "fix" a future disagreement here by shortening the capture -- that is
# precisely how this case spent months agreeing on two mid-loop readings.
# No OVERRUN line: here the poll loop IS line 30 (`...:GOTO30`), so there is no
# fall-through slot to guard.
D_CASE = ("D_interruptible",
          [CLR, "10 ON STOP GOSUB 100", "20 STOP ON", RANOK,
           "30 FORI=1TO3000:NEXT:GOTO30",
           "100 POKE&HD000,1", "105 FORK=1TO9000:NEXT", "108 POKE&HD000,2:END"],
          [(0.3, 0.40), (1.0, 5.0)])       # same 100 ms tap, then the 4 s hold


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=REF_MACHINE, help="reference oracle machine")
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE,
                    help="zerobas repack machine")
    ap.add_argument("--only", help="run only cases whose label contains this substring")
    ap.add_argument("--ref-only", action="store_true", help="oracle-lock only")
    ap.add_argument("--trials", type=int, default=2, help="repeats per case (robustness)")
    ap.add_argument("--screen", action="store_true",
                    help="dump the SCREEN 0 name table for each trial -- the only "
                         "way to tell a mangled program line from a semantic failure")
    args = ap.parse_args()
    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL':5} {label}" + (f"  {detail}" if detail else ""))
        ok = ok and cond

    def sample(machine, tag, label, prog, presses):
        out = []
        for i in range(args.trials):
            r = run(machine, prog, presses, screen=args.screen)
            if args.screen:
                print(f"[{tag}] {label} trial {i}"); show_screen(r)
            out.append(r)
        return out

    def brief(rs):
        """flag/ran/done per trial -- the raw screen hex is for --screen, not the log"""
        return [None if r is None else
                {k: r.get(k) for k in ("flag", "ran", "done")} for r in rs]

    def gated(rs, want):
        """Every trial must have finished CLEANLY (ran==1: all the arming statements
        executed; done==1: the machine got back to command level) before its `flag`
        means anything at all. A zero from a program that never ran, died on a
        syntax error, or is still spinning is a FAILURE, not a no-fire."""
        return all(r is not None and r.get("ran") == 1 and r.get("done") == 1
                   and (want is None or r.get("flag") == want) for r in rs)

    def flags(rs):
        return [None if r is None else r.get("flag") for r in rs]

    print(f"--- ASSERTED cases: zerobas == VG-8020, robust across {args.trials} trials ---")
    for label, prog, presses, want in ASSERTED:
        if args.only and args.only not in label:
            continue
        ref = sample(args.machine, "ref", label, prog, presses)
        check(f"[ref] {label:16} {brief(ref)} (want all flag={want}, ran=1, done=1)",
              gated(ref, want))
        if args.ref_only:
            continue
        zb = sample(args.zb_machine, "zb ", label, prog, presses)
        zb_ok = gated(zb, want) and flags(zb) == flags(ref)
        check(f"[zb ] {label:16} {brief(zb)} (want all flag={want}, ran=1, done=1, "
              f"== ref {flags(ref)})", zb_ok)

    print("\n--- the RE-ARM property (per-machine, NOT an equality differential) ---")
    for label, prog, presses, atleast in REARM:
        if args.only and args.only not in label:
            continue
        for tag, mach in (("ref", args.machine), ("zb ", args.zb_machine)):
            if tag == "zb " and args.ref_only:
                continue
            rs = sample(mach, tag, label, prog, presses)
            good = all(r is not None and r.get("ran") == 1 and r.get("done") == 1
                       and r.get("flag", 0) >= atleast for r in rs)
            check(f"[{tag}] {label:16} {brief(rs)} (want all flag>={atleast}, "
                  f"ran=1, done=1) -- per-machine", good)

    # D: straight differential (best-effort; the FLAG is not asserted -- two-press
    # timing -- but `ran`/`done` are: an aborted or wedged program is never a datum)
    if not args.only or "D_interruptible" in (args.only or ""):
        label, prog, presses = D_CASE
        print("\n--- D_interruptible: fire then hold -> handler aborts (differential) ---")
        ref = sample(args.machine, "ref", label, prog, presses)
        check(f"[ref] {label:16} {brief(ref)} (want ran=1, done=1)", gated(ref, None))
        if not args.ref_only:
            zb = sample(args.zb_machine, "zb ", label, prog, presses)
            match = gated(zb, None) and flags(zb) == flags(ref)
            check(f"[zb ] {label:16} {brief(zb)} (want ran=1, done=1, "
                  f"== ref {flags(ref)}) -- differential", match)

    print("\nALL PASS" if ok else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
