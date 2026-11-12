#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""strtms-acceptance (D-BIOSRUNG / STRTMS, 2026-11-12): STRTMS ($0099) and PUTQ ($00F9)
called DIRECTLY, and PLYCNT / MUSICF around BASIC PLAY statements -- VG-8020 against
zerobas.

PUTQ / STRTMS rows: our code PUTQs PLAY "C"'s packet bytes onto queue A (and an end
marker onto B / C), sets PLYCNT, calls STRTMS, stores MUSICF / PLYCNT / voice A's
QUETAB descriptor; RDPSG reads R0 / R1 / R8 ten jiffies later; MUSICF is read again
after 2.5 s. PUTQ's own rows: where three bytes land, and the registers after one
call. PLYCNT rows: right after a PLAY, behind a long note, two behind, a ring-filling
PLAY, voices B / C's end markers, and after the music ended.

Not a row: STRTMS with MUSICF POKEd non-zero (the VG-8020's servicer does not run a
voice it did not start; ours does -- scratchpad/strtms_run5.out abc_busy).
Development copies: scratchpad/strtms_probe.py, scratchpad/plycnt_probe.py.
Black-box: registers, work-area RAM, PSG registers through the published RDPSG.

    python3 -u probes/basic/basic_probe_strtms.py [--gate] [ROW ...]
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
import omsx_repl                     # noqa: E402
import basic_probe_biosregs as B     # noqa: E402  (prog, MACHINES)


def read2(machine, p):
    import omsx_repl
    scr = omsx_repl.run_cases(machine, [("direct", p)], batch=False,
                              reset=("", "SCREEN 0:WIDTH 40"), step=3.0, run_gap=20.0)[0]
    if not scr:
        return None
    r = [scr[i:i + 40].strip() for i in range(0, len(scr), 40)]
    return " | ".join(x for x in r if x.startswith("[R") or x.startswith("[C") or "rror" in x) or None



def prog_f(addr, a=0, bc=0x1122, de=0x3344, hl=0x5566, before="", after=""):
    """B.prog with F captured too: `push af` right after the call, popped after the
    register stores into $D10A (low byte = F), printed as [F..]."""
    body = [0x01, bc & 255, bc >> 8, 0x11, de & 255, de >> 8, 0x21, hl & 255, hl >> 8,
            0x3E, a, 0xCD, addr & 255, addr >> 8, 0xF5,
            0x22, 0x00, 0xD1, 0xED, 0x53, 0x02, 0xD1, 0xED, 0x43, 0x04, 0xD1,
            0x32, 0x06, 0xD1, 0xE1, 0x22, 0x0A, 0xD1, 0xC9]
    p = B.prog(addr, a, bc, de, hl, before=before, after=after)
    # replace the DATA lines with this stub's bytes and add the F print
    p = [l for l in p if not (l.startswith("60 DATA") or l.startswith("70 DATA"))]
    i = p.index("RUN")
    p[i:i] = ["60 DATA " + ",".join(str(b) for b in body[:40])]
    p = [l.replace("FOR I=0 TO " + l.split("FOR I=0 TO ")[1].split(":")[0], f"FOR I=0 TO {len(body) - 1}")
         if l.startswith("20 FOR") else l for l in p]
    p = [l.replace(';"]"', ';" F";HEX$(PEEK(&HD10A));"]"') if l.startswith("50 PRINT") else l for l in p]
    return p


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
    "abc_ff":    prog(NOTE_C, voices=(0, -1, -2)),
    "abc_ply1":  prog(NOTE_C, voices=(0, -1, -2), plycnt=1),
    "a_ply1":    prog(NOTE_C, plycnt=1),
    "abc_ply2":  prog(NOTE_C, voices=(0, -1, -2), plycnt=2),
    "putq_pos":  ["NEW", "10 CLEAR 200,&HCFFF",
                  "20 FOR I=0 TO 18:READ X:POKE &HD000+I,X:NEXT",
                  '30 DEFUSR=&HD000:Q=USR(0):S$="":FOR I=0 TO 4:S$=S$+RIGHT$("0"+HEX$(PEEK(&HF975+I)),2):NEXT',
                  '40 PRINT "[C";S$;" ";HEX$(PEEK(&HF959));" ";HEX$(PEEK(&HF95A));"]"',
                  # xor a / ld e,$11 / call PUTQ / ... $22 / ... $33 / ret
                  "50 DATA 175,30,17,205,249,0,175,30,34,205,249,0,175,30,51,205,249,0,201",
                  "RUN"],
    "putq_regs": prog_f(0x00F9, 0, bc=0x1122, de=0x3344, hl=0x5566),
}

SHOW = 'PRINT "[C";A;B;C;D;"]"'
PLY = {
    "short":  ['PLAY "C":A=PEEK(&HFB40):B=PEEK(&HFB3F):C=0:D=0', SHOW],
    "behind": ['PLAY "T32L1C":A=PEEK(&HFB40):B=PEEK(&HFB3F):PLAY "D":C=PEEK(&HFB40):D=PEEK(&HFB3F)', SHOW],
    "two_bh": ['PLAY "T32L1C":PLAY "D":PLAY "E":A=PEEK(&HFB40):B=PEEK(&HFB3F):C=0:D=0', SHOW],
    "long":   ['PLAY "T255L64CDEFGABCDEFGABCDEFGABCDEFGABCDEFGABCDEFGAB":A=PEEK(&HFB40):B=PEEK(&HFB3F):C=0:D=0', SHOW],
    "bc_put": ['PLAY "C":A=PEEK(&HF95F):B=PEEK(&HF965):C=PEEK(&HF959):D=0', SHOW],
    "after":  ['PLAY "C":T=TIME', "IF TIME-T<60 THEN 20", 'A=PEEK(&HFB40):B=PEEK(&HFB3F):C=0:D=0', SHOW],
}


def ply_read(machine, names):
    raws = omsx_repl.run_cases(machine, [("stored", PLY[n]) for n in names],
                               batch=False, run_gap=12.0)
    out = {}
    for n, raw in zip(names, raws):
        txt = " ".join("".join(raw or "").split())
        i = txt.rfind("[C")
        out[n] = txt[i:txt.find("]", i) + 1] if i >= 0 else None
    return out


def main():
    args = [a for a in sys.argv[1:] if a != "--gate"]
    bad = blind = 0
    names = [n for n in args if n in ROWS] if args else list(ROWS)
    for name in names:
        got = {side: read2(m, ROWS[name]) for side, m in B.MACHINES}
        if not got["VG"] or not got["ZB"]:
            v, blind = "NO-READING", blind + 1
        elif got["VG"] == got["ZB"]:
            v = "SAME"
        else:
            v, bad = "DIVERGES", bad + 1
        print(f"ROW {name:10} VG=[{got['VG']}] ZB=[{got['ZB']}] {v}", flush=True)
    pn = [n for n in args if n in PLY] if args else list(PLY)
    if pn:
        got = {side: ply_read(m, pn) for side, m in B.MACHINES}
        for n in pn:
            a, z = got["VG"][n], got["ZB"][n]
            if not a or not z:
                v, blind = "NO-READING", blind + 1
            elif a == z:
                v = "SAME"
            else:
                v, bad = "DIVERGES", bad + 1
            print(f"ROW {n:10} VG=[{a}] ZB=[{z}] {v}", flush=True)
    if blind:
        print("INSTRUMENT FAULT: a side gave no reading")
        return 2
    n = len(names) + len(pn)
    print(f"{'PASS' if not bad else 'FAIL'}: STRTMS / PUTQ / PLYCNT against the VG-8020 ({n - bad}/{n})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
