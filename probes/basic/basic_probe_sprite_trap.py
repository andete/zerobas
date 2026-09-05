#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""SPRITE interrupt-trap characterization / differential — slice T4.

docs/spec-traps-t4-sprite.md §1 and §8. This is the probe that produced every
reading in §1; it runs as a straight REPORTING differential between the reference
oracle (Philips VG-8020) and the relocated repack build. ~~It is deliberately NOT
yet wired to a `make` target, so the asserting gate `make sprite-trap-acceptance`
still has to be built from these cases and the reference values in the spec.~~

🔴 THAT SENTENCE IS FALSIFIED TOO (2026-09-05), AND IT NAMES THE TARGET THAT
RUNS IT. `sprite-trap-acceptance` exists in the Makefile, invokes THIS FILE with
`--only` / `--report` / `--frames`, is collected by `make gates` in the EMULATOR
tier, and ran green in 72 s in today's battery. So this is not a reporting
differential awaiting a gate; it IS the gate, and `--report` is the mode that
turns the asserting off. Struck rather than deleted, beside the D-G7-4 strike
below: this header has now been wrong about its own status twice, in two
different ways, and both were found by reading rather than by anything running.

🔴 THE REASON RECORDED HERE FOR THAT IS FALSIFIED (2026-08-26). It read:
`ON SPRITE GOSUB` is unimplemented on the zerobas side (D-G7-4 left
`SPRITE ON/OFF/STOP` a no-op)". IT FIRES. `basic/sprtrap-body.inc` is included
via `basic/subromcall.asm`, `ZTI_SPRITE` is a live ZTRAP index, and
`scratchpad/clrtrapstk_sprite.py` measured ONE fire on the VG-8020 and one on
zerobas across three control cases -- plus a divergence in the fourth, which is
a statement about `trap_return_check` and not about SPRITE being absent.
The conclusion (not yet gated) still stands; the reason for it does not.

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
  * NO STRING BUILDING. (The companion rule "no `TIME` on the zerobas side" is
    RETIRED as of 2026-07-26 -- `TIME` has landed, docs/spec-basic-time.md. This
    probe keeps its iteration-count windows because they work and rewriting a
    green gate buys nothing; new cases may use `TIME`, per-machine only.)
  * CONTROLS MUST DISCRIMINATE. A_hit/A2_miss and the STATFL hit/miss pair are
    there so a run where both sides agree is recognised as a broken apparatus
    rather than banked as a pass.

THE CADENCE IS COUNTED BY THE EMULATOR, NOT BY THE PROGRAM (§1.2.1, rebuilt
2026-07-26). A fire count is a function of how many frames elapse in a window
whose duration differs ~7x between the two machines, so it is not an
equality-differential -- but "assert the RATIO per machine" was not enough
either, and the case built that way passed at T4 by luck and went red on a commit
that does not touch the trap. A ratio whose denominator the main program computes
is measuring the main loop, because the handler competes with it for the
interpreter. run_emu counts both the fires and the frames with watchpoints, and
measures the handler's own cost in the same boot, so the assertion is a law with
no free parameters. The long block above CADENCE_LEAN is the whole account.

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

from omsx_repl import MAX_DIRECT, key_proc  # noqa: E402
# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "lib"))
import omsx_preflight  # noqa: E402

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
if not (os.path.sep in OMSX and os.path.isfile(OMSX)):
    OMSX = "openmsx"

REF_MACHINE = "Philips_VG_8020"
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

BASE = 0xD000          # $D000 cnt, D001 who, D002 err, D003 done, D004..6 aux
NBYTES = 16            # D008/9 J1, D00A/B J2 (the F_cadence_period stamp pair),
                       # D00C fire tick, D00D/E phase markers, D00F phase control
JIFFY = 0xFC9E         # published work area: the frame counter
STATFL = 0xF3E7        # published work area: the ISR's S#0 copy (spec §2)
COLLISION = 0x20       # S#0 bit 5

# The emulator-level cadence apparatus (F_cadence / F_cadence_period / F_cadence_off).
FIRE_TICK = 0xD00C     # the handler writes it ONCE per entry -> the fire anchor
PH1 = 0xD00D           # written by BASIC at `SPRITE ON`  -> phase 1 opens
PH2 = 0xD00E           # written by BASIC after `SPRITE OFF` -> phase 2 opens
PHCTL = 0xD00F         # written by the EMULATOR, polled by BASIC: 1 = end phase 1,
                       # 2 = end phase 2. The window boundaries are the emulator's,
                       # so the main program's progress cannot define them.

# The KEYBUF line driver, shared by both runners (probes/lib/omsx_repl.py,
# docs/spec-acceptance-harness-rework.md): write the bytes into the 40-byte
# type-ahead buffer where the machine is already looking, so CHGET delivers it
# with no matrix scan and no per-character typing schedule to race. openMSX
# `type` cost the T3 gate three rounds to flake -- and every flake looked like a
# semantic failure.
_INJECT_TCL = [
    # D-LATCH (docs/spec-probe-latch.md): IMPORTED, not copied. The copy this
    # replaced wrote at KEYBUF and RESET GETPNT -- moving GETPNT BACKWARDS
    # under a CPU that may have latched it, which is the whole delivery
    # race. `make latch-check` scores the shared proc; a copy here would
    # have sat outside that gate and kept the race.
    key_proc(),
    "proc __inj {s} { append s \"\\r\"; __key $s }",
]


def _schedule(prog, boot, step):
    """The typing schedule: every line chunked to <=MAX_DIRECT with CR only on the
    last piece. Returns (tcl lines, time just after RUN was typed)."""
    lines, t = [], boot
    for text in list(prog) + ["RUN"]:
        chunks = [text[i:i + MAX_DIRECT] for i in range(0, len(text), MAX_DIRECT)] or [text]
        for k, c in enumerate(chunks):
            proc = "__inj" if k == len(chunks) - 1 else "__key"   # CR only on last
            lines.append(f'after time {t:g} {{ {proc} {{{c}}} }}')
            t += step
    return lines, t


def _launch(machine, lines, timeout, out_path):
    """Write the script, boot one fresh machine, wait for it to exit, return the
    capture file's contents (or None)."""
    fd, tcl_path = tempfile.mkstemp(suffix=".tcl", prefix="sprtrap_")
    os.write(fd, ("\n".join(lines) + "\n").encode())
    os.close(fd)
    cmd = [OMSX, "-machine", machine, "-command", "set renderer none; set sound_driver null", "-script", tcl_path]
    try:
        proc = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL,
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
    return txt or None


def _sentinels(res, hexbytes):
    b = bytes.fromhex(hexbytes)
    res.update(cnt=b[0], who=b[1], err=b[2], done=b[3],
               aux=b[4], aux2=b[5], aux3=b[6],
               j1=b[8] + 256 * b[9], j2=b[10] + 256 * b[11])


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
        f' binary scan [debug read_block memory {BASE} {NBYTES}] H* m;'
        f' puts $f "m=$m t=[expr {{int([machine_info time])}}]"; close $f; exit }}',
        # Poll for `done` rather than waiting a fixed span: the two machines run
        # the same program ~7x apart, so a fixed window either truncates the slow
        # side or wastes the fast one.
        f'proc __poll {{}} {{ if {{[debug read memory {BASE + 3}] != 0}} {{ __cap }}'
        f' else {{ after time 1 __poll }} }}',
    ] + _INJECT_TCL
    sched, t = _schedule(prog, boot, step)
    lines += sched
    lines.append(f"after time {t + poll_from:g} {{ __poll }}")
    lines.append(f"after time {t + deadline:g} {{ __cap }}")
    txt = _launch(machine, lines, timeout, out_path)
    if not txt:
        return None
    res = {}
    for kv in txt.split():
        k, _, v = kv.partition("=")
        if k == "m":
            _sentinels(res, v)
        else:
            res[k] = int(v)
    return res


def run_emu(machine, prog, *, frames=300, boot=8.0, step=3.0,
            deadline=400.0, timeout=900):
    """THE CADENCE RUNNER: the fires and the frames are counted BY THE EMULATOR,
    and the window boundaries are the emulator's too. See the §1.2 block above
    CADENCE_LEAN for why the BASIC-counted form could not measure a cadence.

      frames  = write-watchpoint hits on JIFFY lo ($FC9E), which the ISR ticks
                once per frame
      fires   = write-watchpoint hits on $D00C, which the handler writes once per
                entry -- no saturation, no `POKE 256`, no BASIC arithmetic
      SYNC    = the handler called synchronously by GOSUB with the trap not yet
                enabled (opened by BASIC's write to $D00E) -- the handler's own
                cost, i.e. the denominator the trap-driven rate is compared to
      TRAP    = trap-driven (opened by BASIC's write to $D00D at `SPRITE ON`)

    Each window runs exactly `frames` ISR ticks and the emulator closes it by
    writing $D00F, so nothing about a window's extent depends on the main
    program's progress.

    THE SYNC WINDOW RUNS FIRST, AND THAT ORDER IS LOAD-BEARING. A handler that
    costs more than a frame STARVES THE MAIN PROGRAM COMPLETELY on the repack
    build: a fresh collision has always latched again by the time the handler
    RETURNs, so the pending trap fires at the same statement boundary forever and
    the interrupted statement never runs. Measured, with the T4 handler: the
    program sat at its poll line for 400 emulated seconds and never reached the
    next line -- $D00F=1 written by the emulator, $D00E still 0. Trap-first
    therefore cannot work: the main program would have to survive the trap window
    to open the sync window. Sync-first needs nothing of it after the switch (its
    last line is a bare `GOTO` and the capture is the emulator's), and during the
    sync window there is no trap to starve it. This is the T5 rule --  when the
    feature can starve the main program, the main program cannot be the
    instrument -- applied to the window boundaries as well as to the readings.

    Both anchors are plain RAM on BOTH machines, so this needs no symbol table and
    runs identically on the VG-8020 and the repack build."""
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="spremu_")
    os.close(out_fd)
    lines = [
        "set throttle off",
        "set ::ph 0",                     # 0 = between windows, 1 = TRAP, 2 = SYNC
        "set ::f1 0; set ::n1 0; set ::f2 0; set ::n2 0",
        f'proc __cap {{}} {{ set f [open {{{out_path}}} w];'
        f' binary scan [debug read_block memory {BASE} {NBYTES}] H* m;'
        f' puts $f "m=$m fires1=$::f1 frames1=$::n1 fires2=$::f2 frames2=$::n2'
        f' t=[expr {{int([machine_info time])}}]"; close $f; exit }}',
        # THE PHASE MARKERS MUST BE TIME-GATED, and this is the apparatus bug this
        # runner actually had: the VG-8020's boot writes $D00D while clearing RAM,
        # long before the program is injected. Ungated, phase 1 opened at boot,
        # closed 300 frames later at t=7 emulated seconds and reported 2 fires --
        # a self-consistent reading of nothing at all. A gate that is too LATE is
        # just as blind: opened after RUN was typed, it missed the program's own
        # marker write (line 60 runs a fraction of a second after RUN) and every
        # counter read zero. So it opens after the boot clear and before injection,
        # and zeroes the marker cells itself rather than trusting either boot.
        f"proc __open {{}} {{ set ::ph 0;"
        f" foreach a {{{FIRE_TICK} {PH1} {PH2} {PHCTL}}} {{ debug write memory $a 0 }};"
        f" debug set_watchpoint write_mem {PH1} {{}} {{ set ::ph 1 }};"
        f" debug set_watchpoint write_mem {PH2} {{}} {{ set ::ph 2 }};"
        f" debug set_watchpoint write_mem {FIRE_TICK} {{}} {{ __fire }};"
        f" debug set_watchpoint write_mem {JIFFY} {{}} {{ __tick }} }}",
        "proc __fire {} { if {$::ph == 1} { incr ::f1 } elseif {$::ph == 2} { incr ::f2 } }",
        # Closing a window parks ::ph at 0, so the frames and fires between the
        # emulator's write to $D00F and the main program getting around to opening
        # the next one belong to neither -- the two windows cannot overlap. SYNC
        # closes by handing control back to the program ($D00F=1); TRAP closes by
        # capturing on the spot, because by then the program may well be starved.
        "proc __tick {} {\n"
        "  if {$::ph == 2} {\n"
        f"    incr ::n2; if {{$::n2 >= {frames}}} {{ set ::ph 0;"
        f" debug write memory {PHCTL} 1 }}\n"
        "  } elseif {$::ph == 1} {\n"
        f"    incr ::n1; if {{$::n1 >= {frames}}} {{ set ::ph 0;"
        f" debug write memory {PHCTL} 2; __cap }}\n"
        "  }\n"
        "}",
    ] + _INJECT_TCL
    sched, t = _schedule(prog, boot, step)
    lines.insert(1, f"after time {boot - 2.0:g} {{ __open }}")
    lines += sched
    lines.append(f"after time {t + deadline:g} {{ __cap }}")
    txt = _launch(machine, lines, timeout, out_path)
    if not txt:
        return None
    res = {}
    for kv in txt.split():
        k, _, v = kv.partition("=")
        if k == "m":
            _sentinels(res, v)
        else:
            res[k] = int(v)
    res["want_frames"] = frames
    # rate1 = fires per frame with the trap driving; rate2 = the same handler's
    # SYNCHRONOUS call rate, i.e. 1/its cost in frames. `period` is the T5
    # inter-fire measurement from the handler's own JIFFY stamps.
    res["rate1"] = round(res["fires1"] / res["frames1"], 3) if res["frames1"] else 0
    res["rate2"] = round(res["fires2"] / res["frames2"], 3) if res["frames2"] else 0
    d = res["j2"] - res["j1"]
    res["period"] = round(d / STAMP_SPAN, 3) if (res["j1"] and res["j2"] and d > 0) else 0
    return res


def cost_ceiling(r):
    """The longest the trap's period may legitimately be: one frame, or -- when
    the handler does not fit inside a frame -- the handler's own measured cost.
    This is the denominator the T4 gate lacked, and it is measured on the SAME
    machine in the SAME boot, so it carries no per-machine constant."""
    return max(1.0, 1.0 / r["rate2"]) if r["rate2"] else 0.0


# --- program fragments ------------------------------------------------------
# Every line stays under MAX_DIRECT so it lands in one KEYBUF write.
ONERR = "1 ONERRORGOTO900"
# Clears $D000..$D00B only. The three cadence marker cells $D00D/E/F are
# DELIBERATELY not cleared here: a write to $D00D is what opens phase 1, so
# clearing it would open the window at line 5 -- before `SPRITE ON`. run_emu
# zeroes them itself, from the emulator side, before the program is injected.
CLR = ["5 FORZ=0TO11:POKE&HD000+Z,0:NEXT"]
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

    # (§1.2, the cadence, is NOT here: it needs the emulator-level runner and lives
    # in EMU_CASES below. What used to be in this slot could not measure a cadence
    # at all -- see the block above CADENCE_LEAN.)

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
    # A frame-bounded window with SIN in the loop. On zerobas nearly every frame of
    # this window lands inside a page-1 tenant, i.e. exactly the frames htimi_guard
    # skips -- so had the poll been left in page-1 event_poll this would collapse,
    # and with the low-region stanza it must not. It asserts cnt>0 and NOT a ratio,
    # which is why the JIFFY-polled window is still fine here: the main program's
    # progress bounds the window, and the reading does not divide by it.
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


# --- §1.2 THE CADENCE, measured at the emulator level -----------------------
# WHAT THE OLD ASSERTION IN THIS SLOT ACTUALLY MEASURED (2026-07-26, and it went
# RED on a build change that did not touch the trap). It read `cnt / aux`, a fire
# counter that SATURATES AT 250 over a JIFFY delta the MAIN PROGRAM computed by
# polling. Neither half survives inspection:
#
#   * The numerator saturates. Post-TIME it read cnt=250 aux=172 -- a ratio of
#     1.45 asserted as though 250 were a number, when the counter had simply run
#     out of range. Pre-TIME the same program read cnt=170 aux=163 = 1.04 and
#     PASSED. TIME's only contribution was a small interpreter slowdown that
#     pushed a saturating counter over its cliff.
#   * The ratio tracks the MAIN LOOP, not the trap. Three measurements of the
#     same quantity returned 1.00, >=1.43 and 0.67 fires/jiffy, differing only in
#     how long the HANDLER was -- because the frame delta is computed by main-loop
#     statements that the handler is competing with for the interpreter. It passed
#     at T4 by luck.
#
# AND THE UNDERLYING QUANTITY IS NOT 1.0 ON ZEROBAS, so no amount of fixing the
# counters rescues the old form. Measured between fires (the T5 technique -- the
# handler stamps JIFFY itself, so the main loop is out of the measurement): the
# period is 1.500 jiffies/fire on the repack build against 1.000 on the VG-8020,
# identically on a control built from the pre-TIME commit e3a2135.
#
# WHAT 1.5 IS: THE HANDLER'S OWN COST, NOT A LOST FIRE. Emulator-level counting
# (watchpoints on JIFFY and on the handler's own POKE, plus breakpoints on
# htimi_guard, sprtrap-body's `set 7,(hl)` latch and check_traps' fire exit)
# settled it in one run, exactly as it settled T4's four apparatus failures:
#
#     handler                     ref fires/frame   zb fires/frame   zb latch/isr
#     POKE + RETURN (lean)              0.997            0.997         300/300
#     the T4 counting+stamping          0.997            0.62          300/300
#     one extra float statement         0.24             0.727         251/300
#
# The source OFFERS a fire on every frame (latch 300 of 300 ISR entries) and the
# dispatcher DELIVERS every one it can (disp 299). With a lean handler zerobas
# fires on 299 of 300 frames -- the same as the reference, to the frame. What
# differs is that the T4-era handler costs 1.6 frames of zerobas interpreter time
# and 0.7 of the VG-8020's.
#
# So the invariant this case asserts is the general law, verified on both machines
# across a 30x range of handler lengths:
#
#     trap-driven rate == min(1 fire/frame, the same handler's synchronous rate)
#
# Both sides of it are measured in ONE boot by run_emu's two phases, so there is
# no per-machine constant, no tolerance band standing in for a denominator, and no
# way for a future interpreter slowdown to turn a correct implementation red: if
# the handler stops fitting in a frame, the ceiling moves with it. The reference
# is subject to the same law and fails it the same way if broken (its own float
# handler costs 4 frames, and its rate drops to 0.24 accordingly).
STAMP_SPAN = 100          # fires between the two JIFFY stamps (see F_cadence_period)

# The leanest handler that can still be counted: one POKE, then RETURN. On both
# machines it costs well under a frame (synchronous rate 7.5 ref / 4.8 zb), so
# `min(1, rate2)` is 1 and the law reduces to "one fire per frame".
CADENCE_LEAN = [f"800 POKE&H{FIRE_TICK:X},0:RETURN"]

# The T4-era counting + JIFFY-stamping handler -- the one whose cost produced the
# 1.5. Fires #1 and #1+STAMP_SPAN stamp JIFFY into $D008/9 and $D00A/B, so the
# period is measured BETWEEN FIRES by the handler itself and the main program is
# out of it entirely. The high byte is re-read: a lo-then-hi read TEARS when the
# low byte wraps (~once per 256 frames) and composes 256 low, which is the bug
# that made the T4 cadence case read 2.4 fires/frame.
CADENCE_STAMP = [
    f"800 POKE&H{FIRE_TICK:X},0:A=PEEK(&HD000):IFA<250THENPOKE&HD000,A+1",
    f"801 IFA<>0ANDA<>{STAMP_SPAN}THENRETURN",
    f"802 H=PEEK(&H{JIFFY + 1:X}):L=PEEK(&H{JIFFY:X})"
    f":IFH<>PEEK(&H{JIFFY + 1:X})THEN802",
    "803 IFA=0THENPOKE&HD008,L:POKE&HD009,H:RETURN",
    "804 POKE&HD00A,L:POKE&HD00B,H:RETURN",
]


def cadence(handler, *, enable=True):
    """SYNC window first: the MAIN program calls the handler in a tight loop with
    the trap armed but not yet enabled -- the same code on the same machine in the
    same boot, so its cost is measured under the conditions it will be judged
    against. Then `SPRITE ON` opens the TRAP window and the program's remaining
    job is nothing at all (a bare GOTO): the counters and the capture are the
    emulator's, which is what makes the case survive a handler that starves the
    interpreter (run_emu). Line 80 re-zeroes the fire counter and the stamp cells
    so F_cadence_period's stamps are the TRAP window's, not the sync window's."""
    return ([ONERR] + CLR + SETUP + HIT + ARM +     # always ARMED; `enable` is ON
            [f"60 POKE&H{PH2:X},1",
             f"70 GOSUB800:IFPEEK(&H{PHCTL:X})=0THEN70",
             "80 FORZ=0TO11:POKE&HD000+Z,0:NEXT",
             ("82 SPRITEON:" if enable else "82 ") + f"POKE&H{PH1:X},1",
             "84 GOTO84"] +
            [END] + handler + [ERRH])


EMU_CASES = {
    # The cadence itself: with a handler that fits in a frame, every frame fires.
    "F_cadence": cadence(CADENCE_LEAN),
    # The same law with the handler that does NOT fit on zerobas -- the case that
    # turns the T4 gate's handler-sensitivity from a mystery into a measurement.
    # It also carries the between-fires `period`, which must equal that handler's
    # own cost: no fire is lost beyond what the handler itself pays for.
    "F_cadence_period": cadence(CADENCE_STAMP),
    # THE DISCRIMINATING CONTROL, and it discriminates inside a single boot: the
    # trap is armed but never enabled, so phase 1 must count ZERO fires while
    # phase 2 -- the same handler, the same counter, called by the main program --
    # counts plenty. A run where phase 1 is silent because the apparatus is broken
    # cannot pass that pair.
    "F_cadence_off": cadence(CADENCE_LEAN, enable=False),
}


def fmt(r):
    if not r:
        return "NO CAPTURE (apparatus failure)"
    if not r["done"]:
        return f"VOID done=0 {r}"          # never read as a zero -- see docstring
    return (f"cnt={r['cnt']:>3} err={r['err']} aux={r['aux']:>3} "
            f"aux2={r['aux2']:>3} aux3={r['aux3']:>3} t={r['t']}")


def fmt_emu(r):
    if not r:
        return "NO CAPTURE (apparatus failure)"
    return (f"trap {r['fires1']:>4}/{r['frames1']:<4} = {r['rate1']:<6} "
            f"sync {r['fires2']:>4}/{r['frames2']:<4} = {r['rate2']:<6} "
            f"ceiling={cost_ceiling(r):.2f} period={r['period']:<6} "
            f"err={r['err']} t={r['t']}")


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

# The emulator-counted cadence cases (run_emu). `done` does not gate these: the
# capture is triggered by the emulator's own frame counter, not by the program
# reaching an END, precisely so a starved main program cannot void the reading --
# with the T4 handler on zerobas the main program gets so little of the
# interpreter that the direct form captured done==0, which is a FAILURE and not a
# zero. What gates them instead is the APPARATUS check: both windows must have run
# their full length, and the program must not have errored.
#
# EPS is one frame of endpoint quantisation over a 300-frame window, not a
# tolerance band standing in for an unknown: the measured readings are exact
# (fires == frames-1 at 120, 300 and 600 frames, on both machines).
EPS = 0.05
EXPECT_EMU = {
    "F_cadence": {
        EQ: ["frames1", "frames2"],
        PER: [("apparatus: both windows ran their full length",
               lambda r: r["frames1"] == r["want_frames"] == r["frames2"]
               and r["err"] == 0),
              # A PRECONDITION, asserted rather than assumed: this case can only
              # claim "one fire per frame" while the handler fits inside a frame.
              # If a future slowdown breaks that, THIS is the line that goes red
              # and says why, instead of the cadence silently meaning something
              # else. Measured headroom: 4.8x on zerobas, 7.5x on the reference.
              ("the handler fits inside a frame (rate2 > 1)",
               lambda r: r["rate2"] >= 1.2),
              ("fires ONCE PER FRAME, and never twice",
               lambda r: 1.0 - 2 * EPS <= r["rate1"] <= 1.0 + EPS)],
    },
    "F_cadence_period": {
        EQ: ["frames1", "frames2"],
        PER: [("apparatus: both windows ran their full length",
               lambda r: r["frames1"] == r["want_frames"] == r["frames2"]
               and r["err"] == 0),
              # The stamp pair must come from phase 1. The handler stamps at fire
              # #1 and #1+STAMP_SPAN and A only ever increases, so phase 2 cannot
              # re-stamp -- PROVIDED phase 1 got past STAMP_SPAN fires. Assert it.
              ("apparatus: the stamp pair is phase 1's",
               lambda r: r["period"] > 0 and r["fires1"] >= STAMP_SPAN + 5),
              # The law, both directions. Slower than the handler's own cost would
              # mean a fire was LOST; faster than one per frame would mean the
              # level was sampled more than once per frame.
              ("no fire lost: the period is at most the handler's own cost",
               lambda r: r["period"] <= cost_ceiling(r) + 0.15),
              ("and never faster than one fire per frame",
               lambda r: r["period"] >= 1.0 - EPS),
              ("rate == min(1/frame, the handler's own rate)",
               lambda r: (1.0 - EPS) * min(1.0, r["rate2"]) <= r["rate1"]
               <= 1.0 + EPS)],
    },
    "F_cadence_off": {
        EQ: ["fires1", "frames1", "frames2"],
        PER: [("apparatus: both windows ran their full length",
               lambda r: r["frames1"] == r["want_frames"] == r["frames2"]
               and r["err"] == 0),
              ("armed but never enabled: ZERO fires",
               lambda r: r["fires1"] == 0),
              # ...and the counter was working all along, in the same boot.
              ("the same handler, called by the program, IS counted",
               lambda r: r["fires2"] > r["want_frames"])],
    },
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", action="append", default=None,
                    help="substring filter on case names (repeatable)")
    ap.add_argument("--ref-only", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--report", action="store_true",
                    help="print readings without asserting (characterization mode)")
    ap.add_argument("--frames", type=int, default=300,
                    help="ISR ticks per phase for the emulator-counted cadence cases")
    a = ap.parse_args()

    allcases = dict(CASES, **EMU_CASES)
    names = [n for n in allcases if not a.only or any(o in n for o in a.only)]
    if a.list:
        for n in names:
            print(f"--- {n}")
            for ln in allcases[n]:
                print("   ", ln)
        return 0

    print(f"ref = {REF_MACHINE}\nzb  = {ZB_MACHINE}\n")
    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL':5} {label}" + (f"  {detail}" if detail else ""))
        ok = ok and cond

    for n in names:
        # The cadence cases run under the emulator-counted apparatus and are gated
        # on the apparatus check rather than on `done` -- see EXPECT_EMU.
        emu = n in EMU_CASES
        show, spec, gate = (
            (fmt_emu, EXPECT_EMU.get(n, {}), lambda r: bool(r)) if emu else
            (fmt, EXPECT.get(n, {}), lambda r: bool(r) and r["done"] == 1))
        if emu:
            ref = run_emu(REF_MACHINE, allcases[n], frames=a.frames)
            zb = None if a.ref_only else run_emu(ZB_MACHINE, allcases[n], frames=a.frames)
        else:
            ref = run(REF_MACHINE, allcases[n])
            zb = None if a.ref_only else run(ZB_MACHINE, allcases[n])
        if a.report:
            print(f"{n}\n    ref  {show(ref)}"
                  + ("" if a.ref_only else f"\n    zb   {show(zb)}"), flush=True)
            continue
        # `done` (or, for the emulator cases, a capture at all) first: without it no
        # other field means anything.
        check(f"[ref] {n:20} {show(ref)}", gate(ref))
        for lbl, pred in spec.get(PER, []):
            check(f"[ref] {n:20} {lbl}", gate(ref) and pred(ref))
        if a.ref_only:
            continue
        check(f"[zb ] {n:20} {show(zb)}", gate(zb))
        for lbl, pred in spec.get(PER, []):
            check(f"[zb ] {n:20} {lbl}", gate(zb) and pred(zb))
        fields = spec.get(EQ, [])
        if fields and ref and zb:
            same = all(ref[f] == zb[f] for f in fields)
            check(f"[zb ] {n:20} == ref on {','.join(fields)}", same,
                  "" if same else f"ref={ {f: ref[f] for f in fields} } zb={ {f: zb[f] for f in fields} }")

    print("\n" + ("ALL PASS" if ok else "SOME FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
