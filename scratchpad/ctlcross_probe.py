#!/usr/bin/env python3
r"""D-CTLCROSS -- when a FOR frame and a GOSUB frame INTERLEAVE, what happens?

WHY THIS EXISTS. The control-frame-pool arc (TODO.md, out of D-STACKPOOL) wants
GSP/FSP/TRAPSVC to become pointers into ONE descending pool. zerobas today has
THREE SEPARATE ARRAYS, and separate arrays make one whole class of question
invisible: a `NEXT` can always see its `FOR` frame because no GOSUB frame can
ever be "in the way". Put them in one pool and that stops being true -- the
frames interleave, and the machine has to DECIDE what a `NEXT` does when the
newest frame is a GOSUB's.

🎯 SO THIS IS A DESIGN INPUT, NOT A BUG HUNT. Whatever the references do is what
a pooled zerobas must do, and the answer changes the frame layout: "walk past
it" needs a per-frame TAG, "it is not there" does not.

⚠️ THE CURRENT (three-array) zerobas IS ALREADY AN ANSWER TO THESE ROWS, and it
is the answer that falls out of the arrays rather than one anybody chose. If it
already agrees with the references, the pooled design has to PRESERVE a
behaviour, and these rows are its regression guard. If it does not, the arc has
a divergence to close as well.

Reads `[R E]`: R = 1 iff the statement after the cross-`NEXT` ran, E = the ERR
that stopped the program (0 = none). The GOSUB frame's fate is E:
    E=0  -> the cross NEXT left the GOSUB frame standing; its RETURN worked
    E=3  -> `RETURN without GOSUB`: the NEXT consumed the frame it walked past
    E=1  -> `NEXT without FOR`: the NEXT never saw the FOR at all

Every row CLS's before its fence so no typed echo can be read as a value, and
the digits-only guard is stackpool_probe's (a run that never reaches its PRINT
would otherwise report the ECHO of that line).
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

SIDES = {
    "vg8020": ("Philips_VG_8020", 8.0, ("NEW",)),
    "cf3300": ("National_CF-3300", 14.0, ("", "SCREEN 0", "NEW")),
    "zb": (os.environ.get("ZEROBAS_BASIC_MACHINE",
                          "C-BIOS_MSX1_EU_REPACK_DISK"), 8.0, ("NEW",)),
}

TAIL = ["800 E=ERR:RESUME900",
        '900 CLS:PRINT"[";R;E;"]":END']

CASES = [
    # --- the CONTROL. No interleaving at all: the FOR is opened INSIDE the
    #     subroutine, so its frame is newer than the GOSUB's and the NEXT is an
    #     ordinary one. Must read `1 0` everywhere, or nothing below is readable.
    ("x.ctl", ["10 ONERRORGOTO800", "20 E=0:R=0",
               "40 GOSUB100",
               "50 GOTO900",
               "100 FORI=1TO1",
               "110 NEXTI",
               "120 R=1",
               "130 RETURN", *TAIL],
     "FOR opened inside the sub -- no interleave"),

    # --- 🎯 THE SUBJECT. The FOR is opened OUTSIDE and the NEXT runs INSIDE the
    #     subroutine, so at the NEXT the frame order is [GOSUB][FOR] with the
    #     GOSUB's newer. E is the whole reading: 1 = the NEXT could not see the
    #     FOR past the GOSUB frame; 3 = it saw it and DESTROYED the GOSUB frame
    #     reaching it; 0 = it saw it and left the GOSUB frame alone.
    ("x.nxgos", ["10 ONERRORGOTO800", "20 E=0:R=0",
                 "30 FORI=1TO1",
                 "40 GOSUB100",
                 "50 GOTO900",
                 "100 NEXTI",
                 "110 R=1",
                 "120 RETURN", *TAIL],
     "NEXT inside a sub, FOR opened outside"),

    # --- THE DEEPER INTERLEAVE. [FOR J][GOSUB][FOR I] with the NEXT naming the
    #     OUTERMOST. A named NEXT already discards inner FOR frames (that is
    #     `NEXT without FOR`'s walk); this asks whether the walk also crosses a
    #     GOSUB frame, and what it leaves behind when it does.
    ("x.nxdeep", ["10 ONERRORGOTO800", "20 E=0:R=0",
                  "30 FORI=1TO1",
                  "40 GOSUB100",
                  "50 GOTO900",
                  "100 FORJ=1TO1",
                  "110 NEXTI",
                  "120 R=1",
                  "130 RETURN", *TAIL],
     "NEXT I across [FOR J][GOSUB][FOR I]"),

    # --- THE LOOP-CONTINUES ARM, which the three rows above cannot reach: every
    #     one of them ends its loop on the first NEXT (`TO 1`). Here the NEXT
    #     resumes the loop BODY -- which is the GOSUB on line 40 -- so a second
    #     GOSUB frame is pushed with the first still standing. N counts the
    #     handler entries, so a machine that stops early says so.
    ("x.nxagain", ["10 ONERRORGOTO800", "20 E=0:R=0:N=0",
                   "30 FORI=1TO2",
                   "40 GOSUB100",
                   "50 GOTO900",
                   "100 N=N+1",
                   "110 NEXTI",
                   "120 R=N",
                   "130 RETURN", *TAIL],
     "the NEXT resumes the loop body = the GOSUB (R=N)"),

    # --- THE D-FORRET CONTROL, the mirror direction: a RETURN discarding the FOR
    #     frames opened since its GOSUB. Already measured (spec-basic-forret.md);
    #     re-run here so the pair is read on one apparatus. E=1 means the RETURN
    #     did discard the inner FOR; E=0 means it survived.
    ("x.retfor", ["10 ONERRORGOTO800", "20 E=0:R=0",
                  "40 GOSUB100",
                  "50 R=1:NEXTJ",
                  "60 GOTO900",
                  "100 FORJ=1TO1",
                  "110 RETURN", *TAIL],
     "RETURN over an inner FOR, then NEXT J outside"),
]

NUM = re.compile(r"^[-0-9 ]+$")


def run(side, prog):
    machine, boot, reset = SIDES[side]
    raw = "".join(omsx_repl.run_cases(machine,
                                      [("direct", list(reset) + prog + ["RUN"])],
                                      batch=False, reset=(), boot=boot, step=20.0,
                                      cap_gap=10.0, timeout=300.0)[0] or "")
    for m in re.finditer(r"\[([^\[\]]*)\]", raw):
        if NUM.match(m.group(1)):
            return " ".join(m.group(1).split())
    return "<NO OUTPUT>"


sides = ["vg8020", "cf3300", "zb"]
w = max(len(lab) for lab, _, _ in CASES)
print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>12}" for s in sides) + "   verdict")
for lab, prog, why in CASES:
    v = [run(s, prog) for s in sides]
    tag = "refs agree" if v[0] == v[1] else "🔴 REFS SPLIT"
    zb = "" if v[1] == v[2] else "   🔴 zb DIFF"
    print(f"{lab:<{w}}  " + "  ".join(f"{x:>12}" for x in v) + f"   {tag}{zb}   {why}")
print("""
read `[R E]`:  R = the statement after the cross-NEXT ran;  E = the stopping ERR
  E=0  the NEXT walked PAST the GOSUB frame and left it intact  -> a pooled
       design needs a per-frame TAG and a skipping walk
  E=3  the NEXT reached its FOR by DISCARDING the GOSUB frame   -> a pooled
       design needs a tag and a truncating walk
  E=1  the NEXT never saw the FOR frame at all                  -> frames are
       matched only above the newest GOSUB frame""")
