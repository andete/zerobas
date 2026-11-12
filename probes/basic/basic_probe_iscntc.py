#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BIOSRUNG (3), ISCNTC / CKCNTC ($00BA / $00BD): the two entries called DIRECTLY with
a STOP state pending, VG-8020 against zerobas.

biosregs-acceptance's `iscntc` / `ckcntc` rows call them with nothing pending, where a
stub that does nothing returns the same registers -- they agreed for the wrong reason.
Here INTFLG ($FC9B, the published work-area cell the keyboard ISR sets: 3 = CTRL-STOP,
4 = STOP) is POKEd before the call; the readout is the registers the stub stores, INTFLG
after the call, and any `Break` / error line on the screen (a CTRL-STOP may leave the
program). Black-box: registers, work-area RAM and the text screen only.

    python3 -u probes/basic/basic_probe_iscntc.py [--gate] [ROW ...]

`make iscntc-acceptance` runs every row (D-BIOSRUNG, 2026-11-12); the development copy
with its cuts' history is scratchpad/iscntc_probe.py. A `<NO OUTPUT>` reading is a
reading -- the VG-8020's STOP wait prints nothing -- and `iscntc_f4_stop` is the row
that separates that wait from a hang (both machines return A = 4 after the press). An
empty capture is an instrument fault (exit 2).
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import basic_probe_biosregs as B   # noqa: E402  (prog, MACHINES)
import omsx_repl                   # noqa: E402

AFTER = 'PRINT "[C";PEEK(&HD10A);"]"'
# 🔴 FIRST CUT (2026-11-12, kept in iscntc_run.out): INTFLG was POKEd from BASIC, and the
# VG-8020's interpreter checks it BETWEEN STATEMENTS -- "Break in 10", the POKE's own line,
# before the USR call ran. So the stub sets INTFLG itself, right before the call:
# ld a,v / ld ($FC9B),a, then biosregs' body.
_stub = B.stub
_flag = {"v": 0}


def stub_set(addr, a, bc, de, hl, buf=None):
    # 🔴 SECOND CUT: with INTFLG still set after the call, the VG-8020's interpreter breaks
    # at the USR line on its own ("Break in 30" whatever the entry did). So after the
    # stores: ld a,($FC9B) / ld ($D10A),a (INTFLG as the entry left it) / xor a /
    # ld ($FC9B),a -- a row printed means the entry RETURNED; no row, it did not.
    body = _stub(addr, a, bc, de, hl, buf)
    assert body[-1] == 0xC9
    pre = [0x3E, _flag["v"], 0x32, 0x9B, 0xFC]
    if _flag.get("waitkey"):                # (3e) ei / w: ld a,(INTFLG) / or a / jr z,w:
        pre += [0xFB, 0x3A, 0x9B, 0xFC, 0xB7, 0x28, 0xFA]   # call while the key is DOWN
    if _flag.get("basrom"):                 # (3d) ld a,n / ld (BASROM),a ... and back to 0
        pre = [0x3E, _flag["basrom"], 0x32, 0xB1, 0xFB] + pre
    post = [0xAF, 0x32, 0xB1, 0xFB] if _flag.get("basrom") else []
    if _flag.get("waitkey"):
        # 🔴 (3e) FIRST CUT read <NO OUTPUT> on the VG-8020 -- which an ISCNTC that RETURNED
        # also gives: the key still down re-latches INTFLG and the interpreter PAUSES on
        # it. So before going back to BASIC: w: ld a,(NEWKEY+7) / and $10 / jr z,w (up) /
        # halt / xor a / ld (INTFLG),a.
        post += [0x3A, 0xEC, 0xFB, 0xE6, 0x10, 0x28, 0xF9, 0x76, 0xAF, 0x32, 0x9B, 0xFC]
    return (pre + body[:-1]
            + [0x3A, 0x9B, 0xFC, 0x32, 0x0A, 0xD1, 0xAF, 0x32, 0x9B, 0xFC] + post + [0xC9])


B.stub = stub_set
ROWS = {}
for name, addr in (("iscntc", 0x00BA), ("ckcntc", 0x00BD)):
    for v in (0, 3, 4):
        _flag["v"] = v
        ROWS[f"{name}_f{v}"] = B.prog(addr, 0, after=AFTER)
# (3c) WHAT ENDS THE STOP WAIT: entered with INTFLG = 4, then a key TAPPED (1 s) about
# RUN + 3.5 s -- STOP again, or CTRL-STOP. (A hold needs no run_gap: run_cases moves the
# press to RUN + run_gap + lead -- intflg_isr_probe.py's lesson.)
HOLDS = {}
_flag["v"] = 4
for key, combo in (("stop", ((7, 0x10),)), ("cstop", ((6, 0x02), (7, 0x10)))):
    ROWS[f"iscntc_f4_{key}"] = B.prog(0x00BA, 0, after=AFTER)
    HOLDS[f"iscntc_f4_{key}"] = combo


# (3c') A ON RETURN: the f0 rows went in with A = 0 and the STOP-wait row came back with
# A = 4 -- INTFLG's value, or the entry's own? Both again with A = $5A going in.
_flag["v"] = 0
ROWS["iscntc_f0_a5a"] = B.prog(0x00BA, 0x5A, after=AFTER)
ROWS["ckcntc_f0_a5a"] = B.prog(0x00BD, 0x5A, after=AFTER)
_flag["v"] = 4
ROWS["iscntc_f4_stop_a5a"] = B.prog(0x00BA, 0x5A, after=AFTER)
HOLDS["iscntc_f4_stop_a5a"] = ((7, 0x10),)


# (3d) BASROM ($FBB1) != 0 -- the published "a protected ROM BASIC is not broken".
_flag["basrom"] = 1
for v in (0, 3):
    _flag["v"] = v
    ROWS[f"iscntc_f{v}_basrom"] = B.prog(0x00BA, 0x5A, after=AFTER)
    ROWS[f"ckcntc_f{v}_basrom"] = B.prog(0x00BD, 0x5A, after=AFTER)
_flag["basrom"] = 0
# (3e) THE KEY STILL DOWN AT THE CALL (intflg_isr_run6.out: INTFLG is a LATCH -- still 4
# ten frames after the release). The stub waits for the ISR to latch STOP, then calls at
# once, inside ONE 1 s tap: a VG-8020 that waits for the release AND a second press never
# returns here (no row); one that only re-reads INTFLG returns at once.
_flag["v"], _flag["waitkey"] = 0, 1
ROWS["iscntc_held"] = B.prog(0x00BA, 0x5A, after=AFTER)
HOLDS["iscntc_held"] = ((7, 0x10),)
_flag["waitkey"] = 0


# (3f) BASIC CONSUMES THE LATCH: `ON STOP GOSUB` + `STOP ON` takes a CTRL-STOP, then
# the program prints INTFLG -- VG-8020 0; zerobas was 3 before rp_break cleared it
# (scratchpad/intflg_left_run.out).
ROWS["basic_left"] = ["NEW", "10 C=0:ON STOP GOSUB 70:STOP ON", "20 IF C=0 THEN 20",
                      "30 T=TIME:STOP OFF", "40 IF TIME-T<50 THEN 40",
                      '50 PRINT"[L";C>0;PEEK(&HFC9B);"]"', "60 END", "70 C=C+1:RETURN", "RUN"]
HOLDS["basic_left"] = ((6, 0x02), (7, 0x10))


def read(machine, p, hold=None):
    kw = (dict(holds=[hold], hold_lead=0.5, hold_secs=1.0) if hold
          else dict(run_gap=20.0))
    scr = omsx_repl.run_cases(machine, [("direct", p)], batch=False,
                              reset=("", "SCREEN 0:WIDTH 40"), step=3.0, **kw)[0]
    if not scr:
        return None
    rows = [scr[i:i + 40].strip() for i in range(0, len(scr), 40)]
    keep = [x for x in rows if x.startswith("[R") or x.startswith("[C") or x.startswith("[L") or "rror" in x
            or "Break" in x]
    return " | ".join(keep) or "<NO OUTPUT>"


def main():
    only = [a for a in sys.argv[1:] if a != "--gate"] or list(ROWS)
    bad, blind = [], []
    for name in only:
        got = {side: read(m, ROWS[name], HOLDS.get(name)) for side, m in B.MACHINES}
        if not got["VG"] or not got["ZB"]:
            verdict = "NO-READING"
            blind.append(name)
        elif got["VG"] == got["ZB"]:
            verdict = "SAME"
        else:
            verdict = "DIVERGES"
            bad.append(name)
        print(f"ROW {name:18} VG=[{got['VG']}] ZB=[{got['ZB']}] {verdict}", flush=True)
    if blind:
        print(f"\nINSTRUMENT FAULT: no capture on {', '.join(blind)}")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: ISCNTC / CKCNTC against the VG-8020 "
          f"({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
