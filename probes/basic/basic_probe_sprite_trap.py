#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""SPRITE interrupt-trap characterization / differential — slice T4.

docs/spec-traps-t4-sprite.md §1 and §8. This is the probe that produced every
reading in §1; it runs as a straight REPORTING differential between the reference
oracle (Philips VG-8020) and the relocated repack build. It is deliberately NOT
yet wired to a `make` target: `ON SPRITE GOSUB` is unimplemented on the zerobas
side (D-G7-4 left `SPRITE ON/OFF/STOP` a no-op), so the asserting gate
`make sprite-trap-acceptance` arrives with the implementation, built from these
same cases and the reference values recorded in the spec.

WHAT MAKES T4'S APPARATUS THE SIMPLEST IN THE ARC: the event is produced by the
BASIC program itself -- two overlapping sprites. There is no keyboard matrix to
drive (T2/T3), no PSG port-A + R14 injection (T2), and no C-BIOS hook (T3). Every
case is `-machine <name>` and a program. That is why the gate can be fully
deterministic.

WHAT IS STILL NOT OPTIONAL (the standing arc requirements, inherited verbatim
from the T3 gate -- these are what three void characterization rounds cost):

  * RAM SENTINELS, never screen text -- the REPL echoes every typed program line.
    $D000 fire count, $D001 who, $D002 trapped ERR, $D003 DONE, $D004/5/6 aux.
  * EVERY READING IS GATED ON `done`. The capture polls $D003 and fires the
    moment the program sets it; a program that errored out or is still running at
    the hard deadline is captured with done==0 and is a FAILURE, never a zero.
  * THE COUNTER SATURATES at 250. SPRITE fires once per frame while two sprites
    overlap (§1.1), so an uncapped counter would reach 256, and `POKE 256` raises
    ERR 5 -- turning the correct "fires every frame" answer into an error case.
  * NO STRING BUILDING, and NO `TIME`: it is not implemented on zerobas (absent
    from basic/kwtable.inc, so it parses as the variable `TI` and reads 0
    forever) and a TIME-bounded loop there never terminates. Windows are sized by
    iteration count.
  * CONTROLS MUST DISCRIMINATE. A_hit/A2_miss and the STATFL hit/miss pair are
    there so a run where both sides agree is recognised as a broken apparatus
    rather than banked as a pass.

THE CADENCE IS A RATIO, NOT A COUNT (§1.2). The fire count is a function of how
many frames elapse in a window whose duration differs ~7x between the two
machines, so it is NOT an equality-differential. The machine-independent
invariant is fires/frames ~= 1 in a tight loop, asserted per machine -- the same
shape as T3's auto-repeat finding.

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

BASE = 0xD000          # $D000 cnt, D001 who, D002 err, D003 done, D004..6 aux
JIFFY = 0xFC9E         # published work area: the frame counter
STATFL = 0xF3E7        # published work area: the ISR's S#0 copy (spec §2)
COLLISION = 0x20       # S#0 bit 5


def run(machine, prog, *, boot=8.0, step=3.0, poll_from=2.0,
        deadline=600.0, timeout=900):
    """Boot `machine`, inject `prog` + RUN through KEYBUF, and capture the
    sentinels the moment $D003 is set -- or at `deadline` emulated seconds,
    which captures done==0 and fails the case. One boot per call = power-on
    fresh. Times are EMULATED seconds (throttle off)."""
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="sprtrap_")
    os.close(out_fd)
    lines = [
        "set throttle off",
        f'proc __cap {{}} {{ set f [open {{{out_path}}} w];'
        f' binary scan [debug read_block memory {BASE} 8] H* m;'
        f' puts $f "m=$m t=[expr {{int([machine_info time])}}]"; close $f; exit }}',
        # Poll for `done` rather than waiting a fixed span: the two machines run
        # the same program ~7x apart, so a fixed window either truncates the slow
        # side or wastes the fast one.
        f'proc __poll {{}} {{ if {{[debug read memory {BASE + 3}] != 0}} {{ __cap }}'
        f' else {{ after time 1 __poll }} }}',
        # KEYBUF injection (probes/lib/omsx_repl.py, docs/spec-acceptance-harness-
        # rework.md): write the bytes into the 40-byte type-ahead buffer and point
        # GETPNT/PUTPNT at them, so CHGET delivers the line with no matrix scan and
        # no per-character typing schedule to race. openMSX `type` cost the T3 gate
        # three rounds to flake -- and every flake looked like a semantic failure.
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

    fd, tcl_path = tempfile.mkstemp(suffix=".tcl", prefix="sprtrap_")
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
                       aux=b[4], aux2=b[5], aux3=b[6])
        else:
            res[k] = int(v)
    return res


# --- program fragments ------------------------------------------------------
# Every line stays under MAX_DIRECT so it lands in one KEYBUF write.
ONERR = "1 ONERRORGOTO900"
CLR = ["5 FORZ=0TO6:POKE&HD000+Z,0:NEXT"]
ERRH = "900 POKE&HD002,ERR:POKE&HD003,1:END"
END = "790 POKE&HD003,1:END"
# The counter SATURATES -- see the module docstring.
HANDLER = ["800 A=PEEK(&HD000):IFA<250THENPOKE&HD000,A+1", "810 RETURN"]
SETUP = ["10 SCREEN2", "20 SPRITE$(0)=STRING$(8,255)"]   # a solid 8x8 pattern
HIT = ["30 PUTSPRITE0,(100,100),15,0", "40 PUTSPRITE1,(104,100),15,0"]
MISS = ["30 PUTSPRITE0,(40,40),15,0", "40 PUTSPRITE1,(160,140),15,0"]


def prog(body, *, hit=True, handler=True, subs=()):
    """`subs` are SUBROUTINES and must sort AFTER the END line -- if execution can
    fall into them, their RETURN raises ERR 3 (RETURN without GOSUB). That is not
    hypothetical: the first WAIT30 did exactly that on every case that used it.
    Note it is the LINE NUMBER that decides, not the order lines are typed in --
    moving the text after END changed nothing, because 600 < 790. Hence 950+."""
    p = [ONERR] + CLR + SETUP + (HIT if hit else MISS) + body + [END]
    return p + list(subs) + (HANDLER if handler else []) + [ERRH]


def esyn(stmt):
    """A parse-surface case: no sprite setup, the ON ERROR handler records ERR."""
    return [ONERR] + CLR + ["10 " + stmt, END, ERRH]


ARM = ["50 ONSPRITEGOSUB800"]

# WAIT30: let 30 FRAMES pass, machine-independently. Counting JIFFY *changes* in a
# single byte needs no 16-bit compose, so it cannot tear and needs no float; and
# unlike `FOR I=1 TO n` it means the same thing on two machines that run BASIC ~7x
# apart. That difference is not cosmetic -- every fixed-iteration window in the
# first version of this probe SATURATED all three saturating counters at 250 on
# zerobas, which reads as "no information", not as a failure.
#
# It waits on the JIFFY DELTA, not on 30 iterations of a change-detector. The
# iteration version looked equivalent and was not: on zerobas each iteration spans
# several frames (the handler runs between every statement, ~7x slower), so "30
# iterations" was ~387 FRAMES there against ~30 on the reference -- which
# saturated every counter at 250 and read as a dispatcher firing many times per
# frame. Breakpoints said otherwise: 387 latches over that span, i.e. exactly one
# per frame, with every fire paid for by a latch. The apparatus was the anomaly.
#
# It also ZEROES the fire counter once its window has opened, so every caller's
# reading means "fires during THIS 30 frames" rather than "fires since SPRITE ON".
# Without that, the count carries the run-up before the window -- which is a
# couple of statements on the reference and ~60 frames on zerobas, where the first
# float/tenant path through a line is expensive. That turned a 30-frame window
# into a 96-fire reading and looked like a 3x cadence divergence.
WAIT30 = ["950 H=PEEK(&HFC9F):W=PEEK(&HFC9E)+256*H:IFH<>PEEK(&HFC9F)THEN950",
          "951 POKE&HD000,0",
          "952 H=PEEK(&HFC9F):V=PEEK(&HFC9E)+256*H:IFH<>PEEK(&HFC9F)THEN952",
          "954 IFV-W<30THEN952",
          "956 RETURN"]

CASES = {
    # --- §1.1 the event: does an overlap fire, and how often -----------------
    # A_hit/A2_miss are THE discriminating pair. If they ever agree, the run is
    # void -- a broken apparatus, not a pass.
    "A_hit": prog(ARM + ["60 SPRITEON", "70 FORI=1TO400:NEXT"], hit=True),
    "A2_miss": prog(ARM + ["60 SPRITEON", "70 FORI=1TO400:NEXT"], hit=False),

    # F: the cadence, read as a RATIO -- CNT fires against AUX frames over exactly
    # the same window, so "one fire per frame" is measured rather than inferred
    # from wall-clock time.
    #
    # THE WINDOW IS BOUNDED BY FRAMES, NOT BY AN ITERATION COUNT, and that is not a
    # detail. A fixed `FOR I=1 TO 200` cannot serve both machines: zerobas runs it
    # ~7x slower, so the same loop spans ~30 frames on the VG-8020 and ~210 on the
    # repack build, which SATURATES both saturating counters at 250 and reports the
    # ratio as 1.00 for a reason that has nothing to do with the trap. Measured
    # exactly that on the first run. Polling JIFFY instead makes the window 40
    # frames on BOTH machines by construction -- no calibration, no per-machine
    # constant to drift. (JIFFY does tick on zerobas; only `TIME` is unimplemented.)
    #
    # JIFFY IS READ WITH A RE-READ GUARD, and that is not paranoia -- it is the
    # apparatus bug this case actually had. Reading lo-then-hi TEARS whenever the
    # low byte wraps between the two PEEKs (~once per 256 frames): the composed
    # value comes out 256 LOW, so K-J goes negative. The first version "handled"
    # that by restarting the window (J=K) -- which resets the FRAME count while the
    # fire counter, cleared only once at line 5, keeps accumulating across every
    # restart. Result: zerobas read cnt=156 against aux=65, i.e. an apparent 2.4
    # fires per frame, and it looked exactly like a dispatcher bug. It was not:
    # breakpoint counts at htimi_guard and the latch site were 200/200 against 200
    # frames -- a perfect once-per-frame source. Re-reading the high byte and
    # retrying makes the tear impossible, so the ratio means what it says.
    #
    # AND THE TWO COUNTERS MUST COVER THE SAME SPAN, which is what actually made
    # zerobas read ~2 fires per frame after the tear was fixed. The fire counter is
    # cleared once at line 5 and the trap is armed from line 60, so it accrues over
    # `SPRITE ON` -> capture, INCLUDING the frames after END while the capture poll
    # (1 emulated second of granularity) has not yet fired; the JIFFY delta covers
    # only lines 62->72. On the reference the loop dominates and the skew hides; on
    # zerobas, ~7x slower, it was most of the reading. Breakpoint counts settled it:
    # over the armed span, 237 latches against ~212 dispatched fires -- one per
    # frame, exactly right. So line 68 re-zeroes the counter at the window's start
    # and line 74 disarms at its end, and only then is D recorded.
    "F_cadence": prog(ARM + ["60 SPRITEON",
                             f"62 H=PEEK(&H{JIFFY + 1:X}):J=PEEK(&H{JIFFY:X})+256*H"
                             f":IFH<>PEEK(&H{JIFFY + 1:X})THEN62",
                             "68 POKE&HD000,0",
                             f"70 H=PEEK(&H{JIFFY + 1:X}):K=PEEK(&H{JIFFY:X})+256*H"
                             f":IFH<>PEEK(&H{JIFFY + 1:X})THEN70",
                             "72 D=K-J:IFD<150THEN70",
                             "74 SPRITEOFF",
                             "76 POKE&HD004,D"], hit=True),

    # --- §1.3 arm vs enable vs suspend --------------------------------------
    "B_armed_not_on": prog(ARM + ["70 FORI=1TO400:NEXT"], hit=True),
    "C_off": prog(ARM + ["60 SPRITEOFF", "70 FORI=1TO400:NEXT"], hit=True),
    "E_no_handler": prog(["60 SPRITEON", "70 FORI=1TO400:NEXT"],
                         hit=True, handler=False),

    # G/H: does STOP LATCH a pending collision and release it at the next ON, or
    # is STOP just OFF? Built to be decisive: collide while suspended, then move
    # the sprites APART and let the flag clear BEFORE enabling -- so a latched
    # event shows as cnt>0 with nothing currently colliding. AUX/AUX2 prove the
    # suspended phase really did stay silent.
    "G_stop_latch": prog(ARM + ["60 SPRITESTOP", "70 FORI=1TO200:NEXT",
                                "72 POKE&HD004,PEEK(&HD000)",
                                "74 PUTSPRITE1,(160,140),15,0",
                                "76 FORI=1TO100:NEXT",
                                "78 POKE&HD005,PEEK(&HD000)",
                                "80 SPRITEON", "82 FORI=1TO200:NEXT"], hit=True),
    "H_off_latch": prog(ARM + ["60 SPRITEOFF", "70 FORI=1TO200:NEXT",
                               "72 POKE&HD004,PEEK(&HD000)",
                               "74 PUTSPRITE1,(160,140),15,0",
                               "76 FORI=1TO100:NEXT",
                               "78 POKE&HD005,PEEK(&HD000)",
                               "80 SPRITEON", "82 FORI=1TO200:NEXT"], hit=True),

    # --- §1.4 arming is independent of state --------------------------------
    # R: a BARE `ON SPRITE GOSUB` clears the handler slot (count freezes).
    # S: re-arming resumes firing WITHOUT re-issuing `SPRITE ON` -- the state
    #    byte and the handler link are independent, exactly as ZTRAP models them.
    # AUX = the count at the moment of the bare disarm, AUX2 = the count 30 frames
    # later. Frozen (aux2 == aux) proves the slot was cleared; S_rearm's AUX3 then
    # proves firing resumes after re-arming ALONE, with no second `SPRITE ON`.
    # Each phase is its own 30-frame window with its own count, so the readings are
    # machine-independent: AUX = fires while armed (>0), AUX2 = fires in the window
    # AFTER the bare disarm (must be 0), AUX3 = fires after re-arming (>0 again,
    # with no second `SPRITE ON`).
    "R_bare_disarms": prog(ARM + ["60 SPRITEON",
                                  "70 GOSUB950",
                                  "72 POKE&HD004,PEEK(&HD000)",
                                  "74 ONSPRITEGOSUB",
                                  "76 GOSUB950",
                                  "78 POKE&HD005,PEEK(&HD000)"], hit=True, subs=WAIT30),
    "S_rearm": prog(ARM + ["60 SPRITEON",
                           "70 GOSUB950",
                           "72 POKE&HD004,PEEK(&HD000)",
                           "74 ONSPRITEGOSUB",
                           "76 GOSUB950",
                           "78 POKE&HD005,PEEK(&HD000)",
                           "80 ONSPRITEGOSUB800",
                           "82 GOSUB950",
                           "84 POKE&HD006,PEEK(&HD000)"], hit=True, subs=WAIT30),

    # --- §1.6 the trap must NOT consume S#0 bit 5 ---------------------------
    "N_statfl_on": prog(ARM + ["60 SPRITEON", "70 GOSUB950",
                               "72 POKE&HD004,VDP(8)",
                               f"74 POKE&HD005,PEEK(&H{STATFL:X})"], hit=True, subs=WAIT30),
    "N2_statfl_off": prog(ARM + ["60 SPRITEOFF", "70 GOSUB950",
                                 "72 POKE&HD004,VDP(8)",
                                 f"74 POKE&HD005,PEEK(&H{STATFL:X})"], hit=True, subs=WAIT30),

    # --- §1.5 the parse surface ---------------------------------------------
    "J_syn_on_goto": esyn("ONSPRITEGOTO800"),
    "K_syn_bare": esyn("SPRITE"),
    "P_syn_junk": esyn("SPRITEFOO"),
    "M_undef_line": esyn("ONSPRITEGOSUB777"),
    "L_syn_noline": esyn("ONSPRITEGOSUB"),
    # ...and the FAMILY SWEEP that turned L_syn_noline from a T4 question into a
    # T1 defect: the reference accepts a missing line reference for ALL FOUR
    # events and CLEARS the slot. zerobas's shipped ex_on_stop raises ERR 2.
    # Q5/Q6 prove the parser stops cleanly rather than swallowing the statement.
    "Q1_stop_noline": esyn("ONSTOPGOSUB"),
    "Q2_strig_noline": esyn("ONSTRIGGOSUB"),
    "Q3_key_noline": esyn("ONKEYGOSUB"),
    "Q5_sprite_then": esyn("ONSPRITEGOSUB:POKE&HD004,77"),
    "Q6_stop_then": esyn("ONSTOPGOSUB:POKE&HD004,77"),

    # SCREEN 0 has no sprites -- arming there is legal and simply never fires.
    "I_screen0": [ONERR] + CLR + ["10 SCREEN0"] + ARM +
                 ["60 SPRITEON", "70 FORI=1TO300:NEXT", END] + HANDLER + [ERRH],

    # --- §3, the D-T4-2 argument, MEASURED ----------------------------------
    # T_tenant is the case that exists because §3 REASONS rather than measures.
    # SIN runs the fp_sin sub-ROM PAGE-1 tenant, so on zerobas htimi_guard is
    # skipping event_poll for most of this loop. The trap must still fire.
    # Same frame-bounded window as F_cadence, with SIN in the loop. On zerobas
    # nearly every frame of this window lands inside a page-1 tenant, i.e. exactly
    # the frames htimi_guard skips -- so had the poll been left in page-1
    # event_poll this would collapse, and with the low-region stanza it must not.
    "T_tenant": prog(ARM + ["60 SPRITEON",
                            f"62 H=PEEK(&H{JIFFY + 1:X}):J=PEEK(&H{JIFFY:X})+256*H"
                            f":IFH<>PEEK(&H{JIFFY + 1:X})THEN62",
                            "68 POKE&HD000,0",
                            "70 X=SIN(1)",
                            f"72 H=PEEK(&H{JIFFY + 1:X}):K=PEEK(&H{JIFFY:X})+256*H"
                            f":IFH<>PEEK(&H{JIFFY + 1:X})THEN72",
                            "74 D=K-J:IFD<150THEN70",
                            "76 SPRITEOFF",
                            "78 POKE&HD004,D"], hit=True),
}

# --- D-T-4: the event SOURCE, measured directly (spec §2) -------------------
# A single sample cannot tell "set every frame" from "stuck set", so the loop
# COUNTS iterations that saw the bit. The MISS row is the control.
_SRC_TAIL = ["60 C=0",
             f"70 FORI=1TO200:IF(PEEK(&H{STATFL:X})AND{COLLISION})<>0THENC=C+1",
             "72 NEXT",
             "74 IFC>250THENC=250",
             "76 POKE&HD004,C",
             f"78 POKE&HD005,PEEK(&H{STATFL:X})",
             END, ERRH]
CASES["V_statfl_src_hit"] = [ONERR] + CLR + SETUP + HIT + _SRC_TAIL
CASES["V2_statfl_src_miss"] = [ONERR] + CLR + SETUP + MISS + _SRC_TAIL


def fmt(r):
    if not r:
        return "NO CAPTURE (apparatus failure)"
    if not r["done"]:
        return f"VOID done=0 {r}"          # never read as a zero -- see docstring
    return (f"cnt={r['cnt']:>3} err={r['err']} aux={r['aux']:>3} "
            f"aux2={r['aux2']:>3} aux3={r['aux3']:>3} t={r['t']}")


# --- what each case ASSERTS -------------------------------------------------
# `eq`  : fields that must match the reference EXACTLY. The bulk of the surface --
#         error codes, no-fire cases, the STATFL readings -- is an equality
#         differential, because none of it depends on how fast the machine runs.
# `per` : predicates checked on EACH machine independently. Anything counting
#         fires lives here: a fire count is a function of how many frames fit in
#         the window, and the two machines run BASIC ~7x apart, so asserting
#         equality would gate the wrong thing and fail a correct implementation
#         (the same conclusion T3 reached for auto-repeat).
# Every case additionally requires done==1; a reading from a program that errored
# out or never finished is a FAILURE, never a zero.
EQ, PER = "eq", "per"
EXPECT = {
    "A_hit":              {PER: [("fires", lambda r: r["cnt"] > 0)]},
    "A2_miss":            {EQ: ["cnt", "err"]},          # the discriminating control
    "F_cadence":          {PER: [("fires/frame ~= 1",
                                  lambda r: r["aux"] > 0 and 0.75 <= r["cnt"] / r["aux"] <= 1.35)]},
    "B_armed_not_on":     {EQ: ["cnt", "err"]},
    "C_off":              {EQ: ["cnt", "err"]},
    "E_no_handler":       {EQ: ["cnt", "err"]},
    "G_stop_latch":       {EQ: ["cnt", "err"]},
    "H_off_latch":        {EQ: ["cnt", "err"]},
    # shape, not magnitude: armed fires, bare-disarm freezes, re-arm resumes
    "R_bare_disarms":     {EQ: ["err"],
                           PER: [("armed fires", lambda r: r["aux"] > 0),
                                 ("disarmed is silent", lambda r: r["aux2"] == 0)]},
    "S_rearm":            {EQ: ["err"],
                           PER: [("armed fires", lambda r: r["aux"] > 0),
                                 ("disarmed is silent", lambda r: r["aux2"] == 0),
                                 ("re-arm resumes", lambda r: r["aux3"] > 0)]},
    "N_statfl_on":        {EQ: ["err", "aux", "aux2"],   # VDP(8)/STATFL unchanged...
                           PER: [("fires", lambda r: r["cnt"] > 0)]},
    "N2_statfl_off":      {EQ: ["cnt", "err", "aux", "aux2"]},   # ...by an enabled trap
    "J_syn_on_goto":      {EQ: ["cnt", "err"]},
    "K_syn_bare":         {EQ: ["cnt", "err"]},
    "P_syn_junk":         {EQ: ["cnt", "err"]},
    "M_undef_line":       {EQ: ["cnt", "err"]},
    "L_syn_noline":       {EQ: ["cnt", "err"]},
    "Q1_stop_noline":     {EQ: ["cnt", "err"]},
    "Q2_strig_noline":    {EQ: ["cnt", "err"]},
    "Q3_key_noline":      {EQ: ["cnt", "err"]},
    "Q5_sprite_then":     {EQ: ["cnt", "err", "aux"]},   # aux==77 -> parser stopped clean
    "Q6_stop_then":       {EQ: ["cnt", "err", "aux"]},
    "I_screen0":          {EQ: ["cnt", "err"]},
    # the D-T4-2 argument, measured: the low-region poll must keep firing through
    # page-1 tenant windows. Per-machine -- on the reference SIN is slow enough
    # that the loop is boundary-limited, so the RATIO is not comparable.
    "T_tenant":           {PER: [("still fires inside a tenant window",
                                  lambda r: r["cnt"] > 0)]},
    # D-T-4's source, on both machines, with its own discriminating control
    "V_statfl_src_hit":   {PER: [("STATFL bit5 set on nearly every frame",
                                  lambda r: r["aux"] >= 150 and r["aux2"] & COLLISION)]},
    "V2_statfl_src_miss": {EQ: ["aux", "aux2"],
                           PER: [("no collision -> bit5 clear",
                                  lambda r: r["aux"] == 0 and not r["aux2"] & COLLISION)]},
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", action="append", default=None,
                    help="substring filter on case names (repeatable)")
    ap.add_argument("--ref-only", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--report", action="store_true",
                    help="print readings without asserting (characterization mode)")
    a = ap.parse_args()

    names = [n for n in CASES if not a.only or any(o in n for o in a.only)]
    if a.list:
        for n in names:
            print(f"--- {n}")
            for ln in CASES[n]:
                print("   ", ln)
        return 0

    print(f"ref = {REF_MACHINE}\nzb  = {ZB_MACHINE}\n")
    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL':5} {label}" + (f"  {detail}" if detail else ""))
        ok = ok and cond

    for n in names:
        ref = run(REF_MACHINE, CASES[n])
        zb = None if a.ref_only else run(ZB_MACHINE, CASES[n])
        if a.report:
            print(f"{n}\n    ref  {fmt(ref)}" + ("" if a.ref_only else f"\n    zb   {fmt(zb)}"),
                  flush=True)
            continue
        spec = EXPECT.get(n, {})
        # `done` first: without it no other field means anything.
        check(f"[ref] {n:20} {fmt(ref)}", bool(ref) and ref["done"] == 1)
        for lbl, pred in spec.get(PER, []):
            check(f"[ref] {n:20} {lbl}", bool(ref) and ref["done"] == 1 and pred(ref))
        if a.ref_only:
            continue
        check(f"[zb ] {n:20} {fmt(zb)}", bool(zb) and zb["done"] == 1)
        for lbl, pred in spec.get(PER, []):
            check(f"[zb ] {n:20} {lbl}", bool(zb) and zb["done"] == 1 and pred(zb))
        fields = spec.get(EQ, [])
        if fields and ref and zb:
            same = all(ref[f] == zb[f] for f in fields)
            check(f"[zb ] {n:20} == ref on {','.join(fields)}", same,
                  "" if same else f"ref={ {f: ref[f] for f in fields} } zb={ {f: zb[f] for f in fields} }")

    print("\n" + ("ALL PASS" if ok else "SOME FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
