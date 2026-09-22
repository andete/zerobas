#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-ALIASBITE -- does the main/disk buffer overlap CORRUPT an open channel?

🔴 THE SUBJECT. `docs/ram-map.md` shows the two ROMs' FAT buffers are not merely
at different addresses, they are PARTLY ALIASED WITHOUT AGREEING:

    main DATA  FSECTOR_BUF  $E5C0..$E7BF
    main META  FWBUF        $E7C0..$E9BF
    disk DATA  SECTOR_BUF   $E2A0..$E49F
    disk META  WBUF         $E560..$E75F      <-- overlaps main DATA by 416 B

So `disk.rom`'s METADATA buffer covers `$E5C0..$E75F` -- the first 416 bytes of
MAIN's file-data buffer. Joost's question (*"shouldn't we use the same address
for the same thing?"*) is the architecture half; this probe asks the half that
comes first: **is that overlap a live defect TODAY?**

🎯 WHY IT COULD BE. `basic/files.asm:435` -- `OPEN … FOR INPUT` calls
`fat_io_open`, which PRIMES THE READ: a sector is cached in `FAT_DBUF`, which in
MAIN is `FSECTOR_BUF` `$E5C0`, and `FREAD_OFF` tracks the position within it
ACROSS STATEMENTS. Meanwhile every disk-ROM verb that mounts writes its own
`WBUF` at `$E560`. Put a mount between two reads of one open channel and the
second read is served from bytes the disk side has just overwritten.

📏 THE DIFFERENTIAL IS THE SAME PROGRAM ± ONE STATEMENT, which is what makes a
corrupted second read attributable:

    ...open T.DAT for input, read 4 chars, [KILL a file], read 4 more...

`KILL` is used rather than `FILES` because it mounts and prints NOTHING -- a
listing would scroll the screen the fence is read from, and an apparatus that
disturbs its own readout is this project's oldest tax.

⚠️ THE CONTROL IS THE ARM THAT MAKES IT READABLE. Without the KILL the second
read MUST return the next four bytes; if it does not, the probe is measuring its
own file handling and says so instead of blaming the overlap.

    python3 -u scratchpad/aliasbite_probe.py [--selftest]
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp  # noqa: E402,F401  -- module level, sets tempfile.tempdir
import omsx_repl  # noqa: E402

ZB = "C-BIOS_MSX1_EU_REPACK_DISK"
SRC_DSK = os.path.join(ROOT, "disk", "test720.dsk")

# ⚠️ STORED LINES <= 34 COLUMNS.
# \U0001f534 `ON ERROR` IS NOT DECORATION HERE. The first cut had none, and when the
# program failed it printed NOTHING -- an untrapped disk error left a blank
# screen and the probe had no way to say what went wrong. Every failure now
# lands on line 90 and reports its ERR number
# [[an-unnamed-outcome-reads-as-no-outcome]].
# \u26a0\ufe0f AND THE `A:` PREFIX IS GONE, BUT NOT BECAUSE IT WAS THE BUG. It was my
# first suspect and it was WRONG: `OPEN"A:W.DAT"FOR INPUT` on an existing file
# reads fine, measured against a prefix-free twin in the same run. Dropped only
# because the shorter form is the one proven to work end-to-end here.
BODY = [
    '10 OPEN"Y.DAT"FOR OUTPUT AS#1',
    '15 PRINT#1,"X"',
    "17 CLOSE#1",
    '20 OPEN"Z.DAT"FOR OUTPUT AS#1',
    '30 PRINT#1,"ABCDEFGHIJKLMNOP"',
    "40 CLOSE#1",
    "45 ON ERROR GOTO 99",
    '50 OPEN"Z.DAT"FOR INPUT AS#1',
    "60 A$=INPUT$(4,#1)",
]
TAIL = [
    "80 B$=INPUT$(4,#1)",
    "85 CLOSE#1",
    # \U0001f534 THE FENCE IS BUILT WITH CHR$ SO THE SOURCE CANNOT CONTAIN IT.
    # The first cut printed "[";A$;"|";B$;"]" and the capture scored the ECHOED
    # LINE 95 -- `[";A$;"|";B$;"]` -- because the program produced no output and
    # the only bracket on screen was its own source. "Take the LAST hit" guards
    # against the source appearing BEFORE the output, not against there being no
    # output at all [[a-probes-fence-is-also-in-the-source-it-echoes]].
    "95 PRINTCHR$(91);A$;B$;CHR$(93):END",
    '99 PRINTCHR$(91);"E";ERR;CHR$(93)',
    "RUN",
]
VERB = '70 KILL"Y.DAT"'             # mounts in disk.rom, prints nothing

# 8 characters exactly: two 4-char reads concatenated, no separator needed.
FENCE = re.compile(r"\[([A-Za-z0-9 ]{0,16})\]")


def read_fence(scr):
    """(first read, second read) from the LAST fence, or None.

    LAST, because the listing of line 95 contains the fence's own source text
    and a `[` there would score the PROGRAM rather than its OUTPUT."""
    hits = FENCE.findall(scr or "")
    if not hits:
        return None
    s = hits[-1].strip()
    return (s[:4], s[4:])


def verdict(ctl, sub):
    """Named before the run, so the outcome cannot be chosen after it."""
    if ctl is None or sub is None:
        return "REFUSED (a run produced no fence)"
    if ctl != ("ABCD", "EFGH"):
        return (f"INSTRUMENT FAULT: the CONTROL read {ctl}, not "
                f"('ABCD', 'EFGH') -- the probe is measuring its own file "
                f"handling, not the overlap")
    if sub == ("ABCD", "EFGH"):
        return ("CLEAN — a disk-ROM mount between two reads of an open channel "
                "does NOT corrupt it; the 416 B overlap does not bite today")
    return (f"BITES — the control reads {ctl} and the same program with one "
            f"KILL between the reads reads {sub}: a disk-ROM mount destroys an "
            f"open channel's cached sector")


def selftest():
    fails = 0

    def arm(label, cond):
        nonlocal fails
        if not cond:
            print(f"  selftest: FAIL {label}")
            fails += 1

    arm("the OUTPUT fence is read",
        read_fence("95 PRINTCHR$(91);A$;B$;CHR$(93)\n[ABCDEFGH]\nOk")
        == ("ABCD", "EFGH"))
    # \U0001f534 THE ARM THE FIRST CUT NEEDED AND DID NOT HAVE: the source line must
    # not be scoreable at all, even when the program printed nothing.
    arm("NEGATIVE: the echoed SOURCE line alone scores nothing",
        read_fence('95 PRINT"[";A$;"|";B$;"]"\nOk') is None)
    arm("NEGATIVE: a capture with no fence scores nothing",
        read_fence("Ok\n") is None)
    arm("NEGATIVE: an empty capture scores nothing", read_fence("") is None)
    arm("a short fence is still a reading, not a refusal",
        read_fence("[ABCD]") == ("ABCD", ""))
    good = ("ABCD", "EFGH")
    arm("both clean -> CLEAN", verdict(good, good).startswith("CLEAN"))
    arm("subject differs -> BITES", verdict(good, ("ABCD", "\x00\x00")).startswith("BITES"))
    # 🔴 THE ARM THAT KEEPS A BROKEN PROBE FROM BLAMING THE ROM: if the CONTROL
    # is already wrong, no verdict about the overlap may be issued at all.
    arm("NEGATIVE: a bad CONTROL is an INSTRUMENT FAULT, never 'BITES'",
        verdict(("AB", "CD"), ("ABCD", "EFGH")).startswith("INSTRUMENT FAULT"))
    arm("NEGATIVE: a missing run refuses", verdict(None, good).startswith("REFUSED"))
    print("  selftest: PASS" if not fails else f"  selftest: {fails} FAILURE(S)")
    return fails


def run(label, prog):
    tmp = tempfile.mkstemp(suffix=".dsk")[1]
    shutil.copyfile(SRC_DSK, tmp)      # never write the tracked fixture
    caps = omsx_repl.run_cases(ZB, [(label, prog)], batch=False, reset=(),
                               boot=8.0, step=3.0, cap_gap=45.0, timeout=900.0,
                               diska=tmp)
    scr = caps[0] or ""
    r = read_fence(scr)
    # \u26a0\ufe0f THE SCREEN IS PRINTED WHENEVER THE READING IS NOT THE EXPECTED
    # ONE, not only when it is missing: a WRONG fence is exactly the case that
    # needs the picture, and the first cut printed nothing for it.
    if r != ("ABCD", "EFGH"):
        print(f"=== {label} screen ===\n{scr}\n=== end ===")
    print(f"  {label}: {r}")
    return r


def main(argv):
    if "--selftest" in argv:
        return 2 if selftest() else 0
    if not os.path.exists(SRC_DSK):
        print(f"INSTRUMENT FAULT: no test disk at {SRC_DSK}")
        return 2
    print("D-ALIASBITE: does a disk-ROM mount corrupt an open main channel?\n")
    ctl = run("CONTROL no-verb", BODY + TAIL)
    sub = run("SUBJECT  with-KILL", BODY + [VERB] + TAIL)
    print("\nVERDICT:", verdict(ctl, sub))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
