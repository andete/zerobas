#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-EOFCAS -- EOF(n) on a CAS: channel, which nothing had measured.

`make eofcas-acceptance` (exit 1 on any DIFF; a NO-ORACLE cell is not one).

Joost asked (2026-09-30) whether channels are disk only or tape too. They are
both, and EOF() sends EVERY non-disk channel to Illegal function call (5): that
was measured for CRT: only (both references say 5). On a tape opened FOR INPUT,
EOF is how the ordinary read loop ends -- so if the reference answers there,
this is a happy-path gap.

THE RIG IS casfch_probe.py's, unchanged in method: AUTOEXEC.BAS on a FAT12 disk,
an $EA ASCII data file on tape (two lines, HELLO and WORLD), both machines run
the SAME program, answers read straight out of RAM at $D005.. . The CF-3300 is
the reference because it has the disk this rig needs to autostart.

Slots (E = the ERR a statement raised, 0 if none; A = EOF's value AND 255 with a
7 planted first, so 7 means "EOF never assigned"):
  0,1  EOF(1) right after OPEN "CAS:D" FOR INPUT
  2,3  after the first LINE INPUT#1
  4,5  after the second (the last line): the end
  6    done marker &HA5 for the input block
  7,8  EOF(2) on OPEN "CAS:T" FOR OUTPUT, run AFTER the input block so the
       recording cannot overwrite the tape before it is read
  9    done marker &HA5 for the whole program
"""
from __future__ import annotations
import os, shutil, signal, subprocess, sys, tempfile, time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "tools"))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
import omsx_preflight                                              # noqa: E402
from make_test_dsk import Fat12Image                               # noqa: E402
from basic_probe_cas_ascii import build_ascii_cas                  # noqa: E402

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
BASE = 0xD005
ZB = "C-BIOS_MSX1_EU_REPACK_DISK"


def P(off, val):
    return f"POKE&H{BASE + off:04X},{val}"


LINES = [
    "5 MAXFILES=2",
    "10 ONERRORGOTO900",
    '20 OPEN"CAS:D"FOR INPUT AS#1',
    f"30 E=0:A=7:A=EOF(1):{P(0, 'E')}:{P(1, 'A AND 255')}",
    "40 LINE INPUT#1,A$",
    f"50 E=0:A=7:A=EOF(1):{P(2, 'E')}:{P(3, 'A AND 255')}",
    "60 LINE INPUT#1,B$",
    f"70 E=0:A=7:A=EOF(1):{P(4, 'E')}:{P(5, 'A AND 255')}",
    f"72 {P(6, '&HA5')}",
    '75 E=0:A=7:OPEN"CAS:T"FOR OUTPUT AS#2',
    f"77 A=EOF(2):{P(7, 'E')}:{P(8, 'A AND 255')}",
    f"80 {P(9, '&HA5')}",
    "88 END",
    "900 E=ERR:RESUME NEXT",
]
SLOTS = [("open.E", 0), ("open.A", 1), ("line1.E", 2), ("line1.A", 3),
         ("line2.E", 4), ("line2.A", 5), ("IMARK", 6),
         ("out.E", 7), ("out.A", 8), ("MARK", 9)]


# 🎯 THE BUFFER-BOUNDARY BRANCH (D-EOFCAS's second cut). Two lines of 126 +
# CRLF (bytes 0..127 and 128..255) put the second CR at byte 254 and its LF at
# byte 255 -- the
# LAST byte of the tape block buffer -- so the EOF peek after them must step
# into the read-ahead buffer (or find nothing there). Two tapes: a third line
# follows (EOF 0), and the file ends right there (EOF -1). `len` = 126 is the
# witness that the geometry held: the first cut used ONE 254-character line,
# LINE INPUT refused it on BOTH machines, a later E=0 hid that, and every cell
# agreed for the wrong reason (LEN 0 both sides). The second cut (126 + 124)
# read cleanly and still missed: its LF sat at byte 253 -- my arithmetic. Plus the device control: EOF on CRT: is 5
# on both references (D-EVFERR), and the tenant now answers it.
BLINES = [
    "5 MAXFILES=2",
    "7 CLEAR 1000",                  # 126 + 126 characters: the default 200 is ERR 14
    "10 ONERRORGOTO900",
    '20 OPEN"CAS:D"FOR INPUT AS#1',
    f"40 E=0:LINE INPUT#1,A$:{P(3, 'E')}",
    f"45 E=0:LINE INPUT#1,B$:{P(4, 'E')}",
    f"50 E=0:A=7:A=EOF(1):{P(0, 'E')}:{P(1, 'A AND 255')}:{P(2, 'LEN(B$)')}",
    f"60 {P(6, '&HA5')}",
    '70 E=0:A=7:OPEN"CRT:"FOR OUTPUT AS#2',
    f"75 A=EOF(2):{P(7, 'E')}:{P(8, 'A AND 255')}",
    f"80 {P(9, '&HA5')}",
    "88 END",
    "900 E=ERR:RESUME NEXT",
]
BSLOTS = [("li1.E", 3), ("li2.E", 4), ("eof.E", 0), ("eof.A", 1), ("len", 2), ("IMARK", 6),
          ("crt.E", 7), ("crt.A", 8), ("MARK", 9)]


def run(machine, lines=None, tape_lines=("HELLO", "WORLD"), cap=60.0, timeout=180.0):
    lines = LINES if lines is None else lines
    # 🔴 NO `pkill -9 openmsx` HERE (D-PKILL, 2026-09-30). casfch_probe's rig began
    # with one, and copied into a GATE it killed every emulator the parallel pool
    # was running -- kwtime read 51, then 32 rows HANG in two FULL batteries.
    # This run's own openMSX is killed by its process group below.
    tmp = tempfile.mkdtemp(prefix="eofcas_")
    d = Fat12Image()
    d.add_file("AUTOEXEC", "BAS", ("\r\n".join(lines) + "\r\n").encode())
    dk = os.path.join(tmp, "d.dsk")
    open(dk, "wb").write(d.finish())
    tape = os.path.join(tmp, "d.cas")
    open(tape, "wb").write(build_ascii_cas("D", list(tape_lines)))
    out = os.path.join(tmp, "o.txt")
    tcl = (f"set throttle off\nset renderer none\nset sound_driver null\n"
           f"proc cap {{}} {{ set f [open {{{out}}} w]; "
           f"binary scan [debug read_block {{memory}} 0x{BASE:04X} 10] H* p; "
           f'puts $f "ram=$p"; close $f; exit }}\n'
           f"after time {cap} {{ cap }}\n")
    tp = os.path.join(tmp, "s.tcl")
    open(tp, "w").write(tcl)
    cmd = [OMSX, "-machine", machine, "-diska", dk, "-cassetteplayer", tape,
           "-script", tp]
    p = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    dl = time.time() + timeout
    while p.poll() is None and time.time() < dl:
        time.sleep(0.1)
    if p.poll() is None:
        os.killpg(os.getpgid(p.pid), signal.SIGKILL)
    if not os.path.exists(out):
        return None
    for ln in open(out):
        k, _, v = ln.strip().partition("=")
        if k == "ram":
            return [int(v[i:i + 2], 16) for i in range(0, len(v), 2)]
    return None


def show(title, slots, ref, zb):
    print(f"\n  {title}")
    print(f"  {'slot':8} {'CF-3300':>8} {'zerobas':>8}")
    done = ref[9] == 0xA5
    for name, off in slots:
        r, z = ref[off], zb[off]
        if not done and off in (7, 8, 9):
            print(f"  {name:8} {r:8} {z:8}   NO-ORACLE (the CF-3300 never got here)")
            continue
        print(f"  {name:8} {r:8} {z:8}   {'SAME' if r == z else 'DIFF'}")
        if r != z:
            DIFFS.append(f"{title}:{name}")


DIFFS: list[str] = []


def main():
    runs = [("two lines, HELLO / WORLD", SLOTS, LINES, ("HELLO", "WORLD")),
            ("boundary, a third line follows", BSLOTS, BLINES, ("A" * 126, "B" * 126, "X")),
            ("boundary, the file ends there", BSLOTS, BLINES, ("A" * 126, "B" * 126))]
    for title, slots, lines, tape in runs:
        ref = run("National_CF-3300", lines, tape)
        zb = run(ZB, lines, tape)
        if ref is None or zb is None:
            print(f"INSTRUMENT FAULT ({title}): no RAM dump from "
                  f"{'CF-3300' if ref is None else 'zerobas'}")
            return 2
        show(title, slots, ref, zb)
    print(f"\n{len(DIFFS)} rows diverging  " + " ".join(DIFFS))   # not `DIFF:` -- rowshape-check
    return 1 if DIFFS else 0


if __name__ == "__main__":
    sys.exit(main())
