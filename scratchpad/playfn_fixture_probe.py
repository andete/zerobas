#!/usr/bin/env python3
r"""Which fixture is telling the truth about PLAY(n)?

The scratchpad rows (deffn fixture: setup on line 20, `60 CLS:PRINT"[";…;"]"`)
read `-1 -1 0 0` on the reference after `PLAY"L1CDEFGAB"`. The new gate rows
(`20 PLAY… / 30 PRINTCHR$(35);…`) read `-1 -1 -1 0` for the SAME statement --
voice 2 apparently sounding when only one MML string was given.

Both cannot be right. The candidate difference is TIME: the deffn fixture does a
CLS before printing, and a voice is marked active from the moment PLAY queues it
until its queue drains. So vary ONLY the delay and watch the reference.
"""
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "probes", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "probes", "basic"))
import omsx_repl

REF = "Philips_VG_8020"
ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
V = "PLAY(0);PLAY(1);PLAY(2);PLAY(3)"

def run(machine, setup, delay):
    prog = ["10 ON ERROR GOTO 100"]
    if setup:
        prog.append(f"20 {setup}")
    if delay:
        prog.append(f"25 {delay}")
    prog += [f"30 PRINTCHR$(35);{V};CHR$(35):END",
             "100 PRINTCHR$(35);CHR$(69);ERR;CHR$(35)", "RUN"]
    raw = omsx_repl.run_case(machine, "direct", prog) or ""
    m = re.findall(r"#([^#]*)#", raw)
    return " ".join(m[-1].split()) if m else None

CASES = [
    ("one voice, no delay",   'PLAY"L1CDEFGAB"',        ""),
    ("one voice, CLS",        'PLAY"L1CDEFGAB"',        "CLS"),
    ("one voice, FOR 200",    'PLAY"L1CDEFGAB"',        "FOR I=1 TO 200:NEXT"),
    ("voice 2, no delay",     'PLAY "","L1CDEFGAB"',    ""),
    ("voice 2, FOR 200",      'PLAY "","L1CDEFGAB"',    "FOR I=1 TO 200:NEXT"),
]
print(f"{'case':24} {'vg8020':14} {'zb':14}")
for name, setup, delay in CASES:
    r = run(REF, setup, delay)
    z = run(ZB, setup, delay)
    flag = "" if r == z else "   <-- DIFFER"
    print(f"{name:24} {str(r):14} {str(z):14}{flag}")
