#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BIOSCONTRACT2 gap 8: the queue and voice entries out of their idle state -- the
VG-8020 against zerobas.

biosregs / strtms compare LFTQ ($00F6) on an empty queue, PUTQ ($00F9) on one with room, and
GETVCP ($0150) / GETVC2 ($0153) for voice 0 only. Each row: our code calls GICINI ($0090) for
a known state, then the entries; it stores what they answered, and BASIC prints it.

  lftq3      3 x PUTQ into queue 0, then LFTQ queue 0      -> HL (the room left)
  putqfull   PUTQ into queue 0 until it answers Z (full)    -> how many went in, LFTQ's HL
  lftq1      3 x PUTQ into queue 1, then LFTQ queues 1, 0   -> both HLs (the queues apart)
  getvcp1/2  GETVCP with A = 1 / 2                          -> HL
  getvc2     VOICEN ($FB38) := 2, GETVC2 with L = 5         -> HL

  stick_r / stick_ur / stick_l   GTSTCK ($00D5) stick 0 (the cursor keys) with RIGHT /
                                 UP+RIGHT / LEFT held                -> A
  trig0      GTTRIG ($00D8) trigger 0 (SPACE) held                  -> A
The held rows press the key-matrix bits through the harness (`holds`); their code HALT-loops
up to 255 frames until the entry answers non-zero, so the press's timing does not matter.
  latch_*    GTSTCK / GTTRIG ports 1 / 2: OUR code puts PSG port A in OUTPUT mode (R7 bit 6)
             and writes R14's stick / trigger bits itself (active low), so the PSG returns that
             latch as the joystick pins -- docs/spec-traps-t2-strig.md §7.3's injection, done
             through the I/O ports instead of the debugger; R7 is put back after.
  pdl_* / pad_*  GTPDL / GTPAD called directly with an openMSX paddle / arkanoidpad PLUGGED
             (input-devices-acceptance's plug prologues; there they are reached through BASIC).

Black box: registers and the work-area cell VOICEN. Unwritten result words read 0000. Interrupts stay on: GICINI leaves PLAY
idle (MUSICF 0), so nothing drains the queues behind the row's back.

    python3 -u probes/basic/basic_probe_biosq.py [ROW ...]      (`make biosq-acceptance`)
Exit 0 all SAME; 1 a divergence; 2 the VG-8020 gave no reading.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK"))
GICINI, PUTQ, LFTQ, GETVCP, GETVC2 = 0x0090, 0x00F9, 0x00F6, 0x0150, 0x0153
VOICEN = 0xFB38
OUT = 0xD100                                   # result words at $D100, $D102, $D104


def call(a):
    return [0xCD, a & 255, a >> 8]


def st_hl(slot):
    return [0x22, (OUT + 2 * slot) & 255, (OUT + 2 * slot) >> 8]


def puts(queue, n):
    c = []
    for i in range(n):
        c += [0x3E, queue, 0x1E, 0x41 + i] + call(PUTQ)
    return c


def lftq(queue, slot):
    return [0x3E, queue] + call(LFTQ) + st_hl(slot)


def putqfull():
    # ld c,0 / lp: push bc / xor a / ld e,$55 / call PUTQ / pop bc / jr z,full / inc c /
    # jr nz,lp / full: ld a,c / ld (OUT),a ; then LFTQ 0 -> OUT+2
    body = [0x0E, 0x00]
    lp = len(body)
    body += [0xC5, 0xAF, 0x1E, 0x55] + call(PUTQ) + [0xC1, 0x28, 0x03, 0x0C, 0x20]
    body += [(lp - (len(body) + 1)) & 255]
    body += [0x79, 0x32, OUT & 255, OUT >> 8]
    return body + lftq(0, 1)


ROWS = {
    "lftq3": puts(0, 3) + lftq(0, 0),
    "putqfull": putqfull(),
    "lftq1": puts(1, 3) + lftq(1, 0) + lftq(0, 1),
    "getvcp1": [0x3E, 1] + call(GETVCP) + st_hl(0),
    "getvcp2": [0x3E, 2] + call(GETVCP) + st_hl(0),
    "getvc2": [0x3E, 2, 0x32, VOICEN & 255, VOICEN >> 8, 0x2E, 5] + call(GETVC2) + st_hl(0),
}


GTSTCK, GTTRIG = 0x00D5, 0x00D8
# name -> (entry, the matrix bits held: row 8 = SPACE 0x01, LEFT 0x10, UP 0x20, RIGHT 0x80)
HELD = {"stick_r": (GTSTCK, ((8, 0x80),)), "stick_ur": (GTSTCK, ((8, 0xA0),)),
        "stick_l": (GTSTCK, ((8, 0x10),)), "trig0": (GTTRIG, ((8, 0x01),))}


def held_code(entry):
    # xor a / ld (OUT),a / ld b,0 / lp: halt / push bc / xor a / call ENTRY / pop bc / or a /
    # jr nz,got / djnz lp / got: ld (OUT),a / ret
    return ([0xAF, 0x32, OUT & 255, OUT >> 8, 0x06, 0x00,
             0x76, 0xC5, 0xAF] + call(entry) + [0xC1, 0xB7, 0x20, 0x02, 0x10, 0xF4,
             0x32, OUT & 255, OUT >> 8, 0xC9])


def read_held(machine, entry, key):
    c = held_code(entry)
    prog = [f"CLEAR 200,&HCFFF:FOR I=0 TO {len(c) - 1}:READ X:POKE &HD000+I,X:NEXT",
            'DEFUSR=&HD000:Q=USR(0):PRINT "[Q";PEEK(&HD100);"]"',
            "DATA " + ",".join(str(b) for b in c)]
    scr = omsx_repl.run_cases(machine, [("stored", prog)], batch=False,
                              reset=("", "SCREEN 0:WIDTH 40"), step=3.0,
                              holds=[key], hold_lead=0.5, hold_secs=3.0)[0] or ""
    m = re.findall(r"\[Q\s*(\d+)\s*\]", re.sub(r"\s+", " ", scr))
    return m[-1] if m else None


def latch_code(mask, entry, a):
    # di / R7 -> saved / R7 := $F8 (port A output) / R14 := mask / ld a,PORT / call ENTRY /
    # ld (OUT),a / R7 := saved / ei / ret
    return ([0xF3, 0x3E, 7, 0xD3, 0xA0, 0xDB, 0xA2, 0xF5,
             0x3E, 0xF8, 0xD3, 0xA1, 0x3E, 14, 0xD3, 0xA0, 0x3E, mask, 0xD3, 0xA1,
             0x3E, a] + call(entry) + [0x32, OUT & 255, OUT >> 8,
             0x3E, 7, 0xD3, 0xA0, 0xF1, 0xD3, 0xA1, 0xFB, 0xC9])


def series_code(entry, args):
    # for each A in args: ld a,A / call ENTRY / ld (OUT+i),a  (byte results, in order)
    c = []
    for i, a in enumerate(args):
        c += [0x3E, a] + call(entry) + [0x32, (OUT + i) & 255, (OUT + i) >> 8]
    return c


# name -> (code body, plug prologue). R14: bit 0 up, 1 down, 2 left, 3 right, 4 trigger A,
# 5 trigger B -- active low. Each expects a NON-ZERO answer: an injection the entry did not
# see reads 0 on both machines, which would agree blind.
DEVICE = {
    "latch_stk1r":  (latch_code(0xF7, GTSTCK, 1), ()),        # port 1 RIGHT -> 3
    "latch_stk2ul": (latch_code(0xFA, GTSTCK, 2), ()),        # port 2 UP+LEFT -> 8
    "latch_trg1":   (latch_code(0xEF, GTTRIG, 1), ()),        # port 1 trigger A -> 255
    "latch_trg4":   (latch_code(0xDF, GTTRIG, 4), ()),        # port 2 trigger B -> 255
    "pdl_paddleA":  (series_code(0x00DE, [1, 3, 5]), ("plug joyporta paddle",)),
    "pdl_paddleB":  (series_code(0x00DE, [2, 4, 6]), ("plug joyportb paddle",)),
    "pad_arkA":     (series_code(0x00DB, [0, 1, 2, 3]), ("plug joyporta arkanoidpad",)),
    "pad_arkB":     (series_code(0x00DB, [4, 5, 6, 7]), ("plug joyportb arkanoidpad",)),
}


def code(body):
    # the result words zeroed first: putqfull stores ONE byte at $D100, and $D101's power-on
    # garbage ($00 on the VG-8020, $FF here) read as a divergence (scratchpad/BQ_run1.out)
    clr = [0x21, 0, 0, 0x22, OUT & 255, OUT >> 8, 0x22, (OUT + 2) & 255, (OUT + 2) >> 8]
    return clr + call(GICINI) + body + [0xC9]


def read(machine, c, prologue=()):
    prog = ["NEW", "10 CLEAR 200,&HCFFF",
            f"20 FOR I=0 TO {len(c) - 1}:READ X:POKE &HD000+I,X:NEXT",
            '30 DEFUSR=&HD000:Q=USR(0):PRINT "[Q";PEEK(&HD100)+256*PEEK(&HD101);'
            'PEEK(&HD102)+256*PEEK(&HD103);"]"',
            "50 DATA " + ",".join(str(b) for b in c), "RUN"]
    raw = omsx_repl.run_cases(machine, [("direct", prog)], batch=False, reset=("", "SCREEN 0"),
                              step=3.0, run_gap=8.0, prologue=tuple(prologue))[0] or ""
    m = re.findall(r"\[Q\s*(\d+)\s+(\d+)\s*\]", re.sub(r"\s+", " ", raw))
    return f"{int(m[-1][0]):04X} {int(m[-1][1]):04X}" if m else None


def main():
    only = sys.argv[1:] or list(ROWS) + list(HELD) + list(DEVICE)
    bad = blind = 0
    for name in only:
        if name in DEVICE:
            body, plug = DEVICE[name]
            got = {side: read(m, code(body), plug) for side, m in MACHINES}
        elif name in HELD:
            got = {side: read_held(m, *HELD[name]) for side, m in MACHINES}
        else:
            got = {side: read(m, code(ROWS[name])) for side, m in MACHINES}
        if got["VG"] is None or got["ZB"] is None:
            verdict, blind = "NO-READING", blind + 1
        else:
            verdict = "SAME" if got["ZB"] == got["VG"] else "DIVERGES"
            bad += verdict == "DIVERGES"
        print(f"ROW {name:9} VG=[{got['VG']}] ZB=[{got['ZB']}] {verdict}", flush=True)
    if blind:
        print("INSTRUMENT FAULT: a side gave no reading")
        return 2
    print(f"{'PASS' if not bad else 'FAIL'}: the queue / voice / stick entries out of the idle state "
          f"({len(only) - bad}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
