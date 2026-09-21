#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-FILESLOCAL -- does moving FILES into disk.rom stop the clock?

🔴 WHY THIS EXISTS, AND IT IS A PREDICTION MADE BEFORE THE MOVE. `hk_kill`'s
header records D-XSLOTPRICE 0c's finding -- a hook handler is entered with
interrupts OFF, and ~1 s of disk-ROM work advanced TIME by 3 frames -- and then
says out loud that KILL's own `ei` measured to zero effect BECAUSE the verb is
~33 ms and because `subrom_call` does `di / call CALSLT / ei` unconditionally,
so the moment the tenant ran, interrupts came back on regardless.

⚠️ THE SAME HEADER NAMES THE CASE THAT RE-OPENS IT: *"A phase-3 body that does
long work in THIS ROM rather than inside a call-back re-opens it, and 0c's
numbers are the ones to re-read then."* `FILES` IS THAT BODY. It is a whole
root-directory walk plus a CHPUT per emitted character, and today every one of
its sector reads goes through the sub-ROM tenant, whose `read_sector` reaches
the drive by CALSLT -- which EIs on the way. A disk.rom-local `read_sector` is a
plain `call dskio` with no CALSLT anywhere, so nothing hands the interrupts back.

🎯 SO THIS IS A BEFORE/AFTER ON THE SHIPPED TREE, NOT AN a-priori ei/no-ei
comparison. Run it on the CURRENT build to get the baseline; run it again after
the move. The question it answers is the one that matters -- *did relocating the
body freeze the clock?* -- and it needs no scaffolded build to ask, which the
ei/no-ei form does (scratchpad/xslot_noei.py, D-DISKVERB phase 2).

📏 THE SUBJECT: a bare `FILES` over disk/test720.dsk, which is a real directory
walk with real emit. `TIME` is sampled either side in the program itself, so the
figure is frames of VBLANK that actually landed -- the clock the freeze stops.

⚠️ THE DISK IS COPIED FIRST. openMSX writes back to a .dsk it has mounted, and
a probe must not be able to edit a tracked fixture.

    python3 -u scratchpad/filesei_probe.py [--selftest]
"""
from __future__ import annotations
import os, re, shutil, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import probe_tmp  # noqa: E402,F401  -- module level: it sets tempfile.tempdir
import omsx_repl  # noqa: E402

ZB = "C-BIOS_MSX1_EU_REPACK_DISK"
SRC_DSK = os.path.join(REPO, "disk", "test720.dsk")

# ⚠️ STORED LINES <= 34 COLUMNS. The fence is printed by the program rather than
# read off the listing, because a run that never reaches its PRINT reads the
# TYPED LINE back as a value [[a-probes-fence-is-also-in-the-source-it-echoes]].
PROG = [
    "10 ON ERROR GOTO 100",
    "20 T=TIME:FILES",
    '30 PRINT "[";TIME-T;"]":END',
    '100 PRINT "[";TIME-T;"]":END',
    "RUN",
]

# \U0001f534 THE INSTRUMENT'S OWN CONTROLS, AND THEY ARE NOT OPTIONAL HERE. The
# subject arm read the SAME number before and after the move. "No change" is
# also exactly what a dead fence prints, so the run that concludes it must
# carry a POSITIVE control (a pure BASIC loop, interrupts certainly on, whose
# reading must GROW with its length) and a NEGATIVE one (two samples with
# nothing between them, which must read 0). Without them this probe cannot tell
# "the clock kept running" from "the clock was never being read".
# \U0001f534 THE COUNTS ARE VARIABLES BECAUSE THE FIRST CUT HARD-CODED THEM TWICE --
# once in the program and once in the print label -- and resizing the loops left
# the label naming the OLD counts. A label that names an input the run did not
# use is the "plausible table from a misread input" class, reached by editing.
CTRL_SHORT, CTRL_LONG = 60, 240
CTRL = [
    "10 T=TIME:PRINT \"[\";TIME-T;\"]\"",
    f"20 T=TIME:FOR I=1 TO {CTRL_SHORT}:NEXT",
    '30 PRINT "[";TIME-T;"]"',
    f"40 T=TIME:FOR I=1 TO {CTRL_LONG}:NEXT",
    '50 PRINT "[";TIME-T;"]"',
    "RUN",
]

FENCE = re.compile(r"\[\s*(-?\d+)\s*\]")


def frames_from(scr):
    """The LAST fence in the capture, or None. Last, not first: the listing of
    line 30 contains the fence's own source text, and a `[` there would score
    the PROGRAM rather than its OUTPUT."""
    hits = FENCE.findall(scr or "")
    return int(hits[-1]) if hits else None


def selftest():
    """A GREEN control and a NEGATIVE one. Without the negative, "the regex
    matched" is equally what a regex matching the source line prints."""
    fails = 0
    if frames_from('30 PRINT "[";TIME-T;"]":END\n[ 14 ]\nOk') != 14:
        print("  selftest: the OUTPUT fence was not the one read"); fails += 1
    if frames_from("[ 0 ]") != 0:
        print("  selftest: a zero reading did not survive"); fails += 1
    if frames_from("Ok\n") is not None:
        print("  selftest: NEGATIVE -- a capture with no fence scored anyway"); fails += 1
    if frames_from("") is not None:
        print("  selftest: NEGATIVE -- an EMPTY capture scored anyway"); fails += 1
    # a capture carrying ONLY the echoed source must NOT score: that is the
    # exact failure the `last hit` rule exists to prevent, so pin it.
    if frames_from('30 PRINT "[";TIME-T;"]":END') is not None:
        print("  selftest: NEGATIVE -- the echoed SOURCE line scored as output")
        fails += 1
    print("  selftest: PASS" if not fails else f"  selftest: {fails} FAILURE(S)")
    return fails


def main(argv):
    if "--selftest" in argv:
        return 2 if selftest() else 0
    if not os.path.exists(SRC_DSK):
        print(f"INSTRUMENT FAULT: no test disk at {SRC_DSK}")
        return 2
    tmp = tempfile.mkstemp(suffix=".dsk")[1]
    shutil.copyfile(SRC_DSK, tmp)
    caps = omsx_repl.run_cases(ZB, [("files.bare", PROG)], batch=False, reset=(),
                               boot=8.0, step=3.0, cap_gap=45.0, timeout=900.0,
                               diska=tmp)
    scr = caps[0] or ""
    frames = frames_from(scr)
    if frames is None:
        print("=== screen ===\n" + scr)
        print("\nINSTRUMENT FAULT (rc 2): the fence never printed.")
        return 2
    print(f"bare FILES over test720.dsk: TIME advanced {frames} frame(s)")
    print()
    print("READ IT AS A BEFORE/AFTER, NOT AS AN ABSOLUTE. On the pre-move tree")
    print("the walk's sector reads cross by CALSLT, which EIs; a disk.rom-local")
    print("read_sector does not. A figure that COLLAPSES after the move is the")
    print("freeze 0c predicted, and is the case for an `ei` on entry.")
    print()
    caps = omsx_repl.run_cases(ZB, [("fence.control", CTRL)], batch=False,
                               reset=(), boot=8.0, step=3.0, cap_gap=45.0,
                               timeout=900.0, diska=tmp)
    cscr = caps[0] or ""
    hits = [int(h) for h in FENCE.findall(cscr)]
    # the listing echoes each fence's SOURCE too, so take the LAST three.
    hits = hits[-3:]
    if len(hits) != 3:
        print("=== screen ===\n" + cscr)
        print("\nINSTRUMENT FAULT (rc 2): the control fences did not all print.")
        return 2
    zero, short, long_ = hits
    print(f"CONTROLS: empty window {zero} \u00b7 FOR 1..{CTRL_SHORT} {short} \u00b7 "
          f"FOR 1..{CTRL_LONG} {long_} frame(s)")
    bad = []
    # \U0001f534 THE NEGATIVE CONTROL IS NOT ASSERTED AT EXACTLY 0, AND THE FIRST CUT
    # WAS WRONG TO. Measured, two TIME samples with only a PRINT between them
    # read 1: the PRINT itself straddles a frame boundary. 1 is therefore what
    # "no elapsed work" LOOKS like on this fence, and it is the floor the
    # subject's figure has to be read against -- a FILES that reads 4 is 4
    # against a floor of 1, not 4 against 0.
    if zero > 1:
        bad.append(f"the NEGATIVE control read {zero}, above its measured floor "
                   f"of 1 -- the fence is counting work outside its own window")
    if short <= 0:
        bad.append("the POSITIVE control read nothing -- the fence is DEAD, and "
                   "the subject's reading means nothing")
    if long_ <= short:
        bad.append(f"the long loop ({long_}) did not exceed the short one "
                   f"({short}) -- the fence does not scale with duration")
    if bad:
        for b in bad:
            print("  \U0001f534 " + b)
        return 2
    print(f"  \U0001f7e2 the fence reads {zero} across nothing, grows with the work "
          f"and scales -- so the subject's figure is a reading, not a silence.")
    print()
    print("\U0001f3af AND THE *BEFORE* BUILD IS THE SUBJECT'S OWN POSITIVE CONTROL.")
    print("   Pre-move, the walk's sector reads crossed by CALSLT, which hands")
    print("   interrupts back -- so whatever that build reads IS this verb's")
    print("   interrupts-on figure. A post-move reading that MATCHES it is the")
    print("   answer; one that falls toward the empty-window floor is the freeze.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
