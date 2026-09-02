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

def run(machine, setup, delay, value=None):
    prog = ["10 ON ERROR GOTO 100"]
    if setup:
        prog.append(f"20 {setup}")
    if delay:
        prog.append(f"25 {delay}")
    prog += [f"30 PRINTCHR$(35);{value or V};CHR$(35):END",
             "100 PRINTCHR$(35);CHR$(69);ERR;CHR$(35)", "RUN"]
    raw = omsx_repl.run_case(machine, "direct", prog) or ""
    m = re.findall(r"#([^#]*)#", raw)
    return " ".join(m[-1].split()) if m else None

# ── D-PLAYWIN (2026-09-02): the item's own open question is "WHAT exactly, and
# for HOW LONG". The first round answered neither; these rows ask both.
#
# 🎯 THE SHAPE QUESTION. Playing ONLY voice 2 gives the reference `-1 -1 -1 0` --
# voices 1 AND 2 active. So it is NOT "the voice that got music is marked", and
# the obvious reading of the original row (voice 2 sounds when unasked) is the
# wrong generalisation. Candidates:
#   S1  voices 1 and 2 are ALWAYS marked, whatever was supplied
#   S2  voices 1..k are marked for k = (number of strings) + 1
#   S3  all three are marked and voice 3 clears fastest
# Voice-3-only separates them: S1 predicts `-1 -1 -1 -1`(v3 also playing),
# S2 predicts all three, S3 predicts all three.
# Two and three strings pin S2 directly.
#
# ⏱ THE WIDTH QUESTION. A `CLS` closes it, so the window is short. `TIME` is the
# jiffy counter, so a FOR loop calibrated against it measures the width in
# ticks rather than in "a CLS suffices".
CASES = [
    ("one voice, no delay",   'PLAY"L1CDEFGAB"',        ""),
    ("one voice, CLS",        'PLAY"L1CDEFGAB"',        "CLS"),
    ("one voice, FOR 200",    'PLAY"L1CDEFGAB"',        "FOR I=1 TO 200:NEXT"),
    ("voice 2, no delay",     'PLAY "","L1CDEFGAB"',    ""),
    ("voice 2, FOR 200",      'PLAY "","L1CDEFGAB"',    "FOR I=1 TO 200:NEXT"),
    # --- SHAPE ----------------------------------------------------------
    ("voice 3 only, no delay",'PLAY "","","L1CDEFGAB"', ""),
    ("two strings, no delay", 'PLAY"L1CDE","L1CDE"',    ""),
    ("three strings, nodelay",'PLAY"L1CDE","L1CDE","L1CDE"', ""),
    ("empty string, no delay",'PLAY""',                 ""),
    # 🔴 NEW, NOT IN THE FILED SET: `PLAY""` reads `-1 0 0 0` on the reference
    # and `-1 -1 0 0` here -- zerobas marks VOICE 1 ACTIVE for an empty string.
    # Settled rows say whether that is the same transient or a real difference.
    ("empty string, CLS",     'PLAY""',                 "CLS"),
    ("empty string, FOR 200", 'PLAY""',                 "FOR I=1 TO 200:NEXT"),
    # and the two-empty / three-empty forms, to see if it scales with strings
    ("two empty, FOR 200",    'PLAY"",""',              "FOR I=1 TO 200:NEXT"),
    # 🟢 CONTROL: no PLAY at all. Whatever this reads is the resting state, and
    # every row above must be read against it rather than against 0.
    ("no PLAY at all",        '',                       ""),
    # --- WIDTH: a FOR loop of increasing length, in the same fixture ------
    ("one voice, FOR 1",      'PLAY"L1CDEFGAB"',        "FOR I=1 TO 1:NEXT"),
    ("one voice, FOR 5",      'PLAY"L1CDEFGAB"',        "FOR I=1 TO 5:NEXT"),
    ("one voice, FOR 20",     'PLAY"L1CDEFGAB"',        "FOR I=1 TO 20:NEXT"),
    ("one voice, FOR 50",     'PLAY"L1CDEFGAB"',        "FOR I=1 TO 50:NEXT"),
    # and the same delays measured in JIFFIES, so "FOR 20" becomes a number
    ("width: TIME for FOR 20",'TIME=0',                 "FOR I=1 TO 20:NEXT"),
    ("width: TIME for FOR 50",'TIME=0',                 "FOR I=1 TO 50:NEXT"),
]
# the two `width:` rows print TIME, not PLAY(n) -- swap the value expression.
WIDTH_V = "TIME"
print(f"{'case':24} {'vg8020':14} {'zb':14}")
for name, setup, delay in CASES:
    val = WIDTH_V if name.startswith("width:") else None
    r = run(REF, setup, delay, val)
    z = run(ZB, setup, delay, val)
    flag = "" if r == z else "   <-- DIFFER"
    print(f"{name:24} {str(r):14} {str(z):14}{flag}")
