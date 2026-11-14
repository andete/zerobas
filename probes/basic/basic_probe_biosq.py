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


def code(body):
    # the result words zeroed first: putqfull stores ONE byte at $D100, and $D101's power-on
    # garbage ($00 on the VG-8020, $FF here) read as a divergence (scratchpad/BQ_run1.out)
    clr = [0x21, 0, 0, 0x22, OUT & 255, OUT >> 8, 0x22, (OUT + 2) & 255, (OUT + 2) >> 8]
    return clr + call(GICINI) + body + [0xC9]


def read(machine, c):
    prog = ["NEW", "10 CLEAR 200,&HCFFF",
            f"20 FOR I=0 TO {len(c) - 1}:READ X:POKE &HD000+I,X:NEXT",
            '30 DEFUSR=&HD000:Q=USR(0):PRINT "[Q";PEEK(&HD100)+256*PEEK(&HD101);'
            'PEEK(&HD102)+256*PEEK(&HD103);"]"',
            "50 DATA " + ",".join(str(b) for b in c), "RUN"]
    raw = omsx_repl.run_cases(machine, [("direct", prog)], batch=False, reset=("", "SCREEN 0"),
                              step=3.0, run_gap=8.0)[0] or ""
    m = re.findall(r"\[Q\s*(\d+)\s+(\d+)\s*\]", re.sub(r"\s+", " ", raw))
    return f"{int(m[-1][0]):04X} {int(m[-1][1]):04X}" if m else None


def main():
    only = sys.argv[1:] or list(ROWS)
    bad = blind = 0
    for name in only:
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
    print(f"{'PASS' if not bad else 'FAIL'}: the queue / voice entries out of the idle state "
          f"({len(only) - bad}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
