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


def prog(body, *, hit=True, handler=True):
    p = [ONERR] + CLR + SETUP + (HIT if hit else MISS) + body + [END]
    return p + (HANDLER if handler else []) + [ERRH]


def esyn(stmt):
    """A parse-surface case: no sprite setup, the ON ERROR handler records ERR."""
    return [ONERR] + CLR + ["10 " + stmt, END, ERRH]


ARM = ["50 ONSPRITEGOSUB800"]

CASES = {
    # --- §1.1 the event: does an overlap fire, and how often -----------------
    # A_hit/A2_miss are THE discriminating pair. If they ever agree, the run is
    # void -- a broken apparatus, not a pass.
    "A_hit": prog(ARM + ["60 SPRITEON", "70 FORI=1TO400:NEXT"], hit=True),
    "A2_miss": prog(ARM + ["60 SPRITEON", "70 FORI=1TO400:NEXT"], hit=False),

    # F: the cadence, read as a RATIO. AUX is the JIFFY delta across exactly the
    # window the fires are counted over, so "one fire per frame" is measured, not
    # inferred from wall-clock time.
    "F_cadence": prog(ARM + ["60 SPRITEON",
                             f"62 J=PEEK(&H{JIFFY:X})+256*PEEK(&H{JIFFY + 1:X})",
                             "70 FORI=1TO200:NEXT",
                             f"72 K=PEEK(&H{JIFFY:X})+256*PEEK(&H{JIFFY + 1:X})",
                             "74 D=K-J:IFD>250THEND=250",
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
    "R_bare_disarms": prog(ARM + ["60 SPRITEON", "70 FORI=1TO150:NEXT",
                                  "72 POKE&HD004,PEEK(&HD000)",
                                  "74 ONSPRITEGOSUB",
                                  "76 FORI=1TO150:NEXT",
                                  "78 POKE&HD005,PEEK(&HD000)"], hit=True),
    "S_rearm": prog(ARM + ["60 SPRITEON", "70 FORI=1TO150:NEXT",
                           "72 POKE&HD004,PEEK(&HD000)",
                           "74 ONSPRITEGOSUB",
                           "76 FORI=1TO150:NEXT",
                           "78 POKE&HD005,PEEK(&HD000)",
                           "80 ONSPRITEGOSUB800",
                           "82 FORI=1TO150:NEXT"], hit=True),

    # --- §1.6 the trap must NOT consume S#0 bit 5 ---------------------------
    "N_statfl_on": prog(ARM + ["60 SPRITEON", "70 FORI=1TO100:NEXT",
                               "72 POKE&HD004,VDP(8)",
                               f"74 POKE&HD005,PEEK(&H{STATFL:X})"], hit=True),
    "N2_statfl_off": prog(ARM + ["60 SPRITEOFF", "70 FORI=1TO100:NEXT",
                                 "72 POKE&HD004,VDP(8)",
                                 f"74 POKE&HD005,PEEK(&H{STATFL:X})"], hit=True),

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
    "T_tenant": prog(ARM + ["60 SPRITEON",
                            f"62 J=PEEK(&H{JIFFY:X})+256*PEEK(&H{JIFFY + 1:X})",
                            "70 FORI=1TO60:X=SIN(I):NEXT",
                            f"72 K=PEEK(&H{JIFFY:X})+256*PEEK(&H{JIFFY + 1:X})",
                            "74 D=K-J:IFD>250THEND=250",
                            "76 POKE&HD004,D"], hit=True),
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
            f"aux2={r['aux2']:>3} t={r['t']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", action="append", default=None,
                    help="substring filter on case names (repeatable)")
    ap.add_argument("--ref-only", action="store_true")
    ap.add_argument("--zb-only", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    names = [n for n in CASES if not a.only or any(o in n for o in a.only)]
    if a.list:
        for n in names:
            print(f"--- {n}")
            for ln in CASES[n]:
                print("   ", ln)
        return 0

    print(f"ref = {REF_MACHINE}\nzb  = {ZB_MACHINE}\n"
          f"(characterization/differential — reporting only; the asserting gate "
          f"arrives with the T4 implementation)\n")
    for n in names:
        ref = None if a.zb_only else run(REF_MACHINE, CASES[n])
        zb = None if a.ref_only else run(ZB_MACHINE, CASES[n])
        print(f"{n}", flush=True)
        if not a.zb_only:
            print(f"    ref  {fmt(ref)}")
        if not a.ref_only:
            print(f"    zb   {fmt(zb)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
