#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BIOSRUNG / STRTMS step (3): PUTQ ($00F9) and STRTMS ($0099), called DIRECTLY.

Our code PUTQs a packet table onto queue A (A = 0, E = the byte, one call per byte),
then calls STRTMS (or not -- the control), and stores MUSICF ($FB3F), PLYCNT ($FB40)
and voice A's QUETAB descriptor ($F959, 6 B) at once. BASIC waits 10 jiffies, reads PSG
R0 / R1 / R8 through RDPSG ($0096, a second stub), waits 3 s, reads MUSICF again.
Black-box: registers, work-area RAM, PSG registers through the published RDPSG.

    python3 -u scratchpad/strtms_probe.py [ROW ...]
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
import biossweep_probe as S        # noqa: E402  (B with read2)

B = S.B


def code(table, strtms=True, voices=(0,), plycnt=None, musicf=None):
    # the table is PUTQ'd onto each queue in `voices` in turn; voices B / C get only
    # the table's last byte (the FF end marker) when listed as -1 / -2
    c, tbl = [], 0xD000 + 96
    for v in voices:
        q, t, n = (v, tbl, len(table)) if v >= 0 else (-v, tbl + len(table) - 1, 1)
        lp = len(c) + 5
        c += [0x21, t & 255, t >> 8, 0x06, n,          # ld hl,TBL / ld b,n
              0x5E, 0x3E, q, 0xE5, 0xC5, 0xCD, 0xF9, 0x00,  # lp: ld e,(hl) / ld a,q / push hl / push bc / call PUTQ
              0xC1, 0xE1, 0x23, 0x10, 0]                    # pop bc / pop hl / inc hl / djnz lp
        c[-1] = (lp - len(c)) & 255
    if plycnt is not None:
        c += [0x3E, plycnt, 0x32, 0x40, 0xFB]          # ld a,n / ld (PLYCNT),a
    if musicf is not None:
        c += [0x3E, musicf, 0x32, 0x3F, 0xFB]          # ld a,n / ld (MUSICF),a
    if strtms:
        c += [0xCD, 0x99, 0x00]                       # call STRTMS
    c += [0x3A, 0x3F, 0xFB, 0x32, 0x00, 0xD1,          # MUSICF -> $D100
          0x3A, 0x40, 0xFB, 0x32, 0x01, 0xD1,          # PLYCNT -> $D101
          0x21, 0x59, 0xF9, 0x11, 0x02, 0xD1, 0x01, 6, 0, 0xED, 0xB0,   # QUETAB A -> $D102
          0xC9]
    assert len(c) <= 96, len(c)
    return c + [0] * (96 - len(c)) + list(table)


# second stub at $D080: RDPSG R0 / R1 / R8 -> $D110..$D112
PSG = [0x3E, 0, 0xCD, 0x96, 0x00, 0x32, 0x10, 0xD1,
       0x3E, 1, 0xCD, 0x96, 0x00, 0x32, 0x11, 0xD1,
       0x3E, 8, 0xCD, 0x96, 0x00, 0x32, 0x12, 0xD1, 0xC9]


def prog(table, strtms=True, **kw):
    c = code(table, strtms, **kw)
    h = lambda a: f'RIGHT$("0"+HEX$(PEEK(&H{a:X})),2)'
    return ["NEW",
            "10 CLEAR 200,&HCFFF",
            f"20 FOR I=0 TO {len(c) - 1}:READ X:POKE &HD000+I,X:NEXT",
            f"25 FOR I=0 TO {len(PSG) - 1}:READ X:POKE &HD080+I,X:NEXT",
            "30 DEFUSR=&HD000:DEFUSR1=&HD080:Q=USR(0):T=TIME",
            "40 IF TIME-T<10 THEN 40",
            "50 Q=USR1(0):T=TIME",
            "60 IF TIME-T<150 THEN 60",
            '70 S$="":FOR I=0 TO 7:S$=S$+' + h(0xD100) .replace("D100", "D100+I") + ":NEXT",
            '80 PRINT "[C";S$;" ";' + h(0xD110) + ';' + h(0xD111) + ';' + h(0xD112) + ';" ";' + h(0xFB3F) + ';"]"',
            *[f"{90 + k} DATA " + ",".join(str(b) for b in c[i:i + 40])
              for k, i in enumerate(range(0, len(c), 40))],
            "97 DATA " + ",".join(str(b) for b in PSG),
            "RUN"]


NOTE_C = [0x60, 0x19, 0x88, 0x01, 0xAC, 0xFF]     # PLAY "C"'s bytes on the VG-8020
ROWS = {
    "strtms_c":  prog(NOTE_C),
    "putq_only": prog(NOTE_C, strtms=False),
    # ROUND 2: what STRTMS needs -- the other voices' end markers, PLYCNT
    "abc_ff":    prog(NOTE_C, voices=(0, -1, -2)),
    "abc_ply1":  prog(NOTE_C, voices=(0, -1, -2), plycnt=1),
    "a_ply1":    prog(NOTE_C, plycnt=1),
    # ROUND 3: PLYCNT 2; STRTMS while MUSICF is already set (busy)
    "abc_ply2":  prog(NOTE_C, voices=(0, -1, -2), plycnt=2),
    "abc_busy":  prog(NOTE_C, voices=(0, -1, -2), plycnt=1, musicf=1),
    # ROUND 4: PUTQ itself -- where 3 bytes land (VOICAQ+0..4 after, no STRTMS), and the
    # registers / F after one call (A = 0, E = $44)
    "putq_pos":  ["NEW", "10 CLEAR 200,&HCFFF",
                  "20 FOR I=0 TO 18:READ X:POKE &HD000+I,X:NEXT",
                  '30 DEFUSR=&HD000:Q=USR(0):S$="":FOR I=0 TO 4:S$=S$+RIGHT$("0"+HEX$(PEEK(&HF975+I)),2):NEXT',
                  '40 PRINT "[C";S$;" ";HEX$(PEEK(&HF959));" ";HEX$(PEEK(&HF95A));"]"',
                  # xor a / ld e,$11 / call PUTQ / xor a / ld e,$22 / call PUTQ / xor a / ld e,$33 / call PUTQ / ret
                  "50 DATA 175,30,17,205,249,0,175,30,34,205,249,0,175,30,51,205,249,0,201",
                  "RUN"],
    "putq_regs": S.prog_f(0x00F9, 0, bc=0x1122, de=0x3344, hl=0x5566),
}


def main():
    for name in sys.argv[1:] or list(ROWS):
        got = {side: B.read(m, ROWS[name]) for side, m in B.MACHINES}
        v = "NO-REFERENCE" if not got["VG"] else ("SAME" if got["VG"] == got["ZB"] else "DIVERGES")
        print(f"ROW {name:10} VG=[{got['VG']}] ZB=[{got['ZB']}] {v}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
