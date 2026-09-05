#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CASFCH -- what do GET/PUT/FIELD/INPUT$ do on a `CAS:` channel? MEASURED.

TODO filed this as INFERRED: D-NOTOPEN2 swept `FCH_MODES` 0-6 against the
CF-3300 and sent 7/8 (the cassette modes) down the *device* arm BY ANALOGY with
`LPT:`/`CRT:`, giving GET/PUT -> 58, FIELD -> 5, INPUT$ -> 55. It was then
re-examined on 2026-08-09 and recorded NOT MEASURABLE, on two counts:

    "no harness on either side drives a tape and a disk at once"
    "there is no reading to falsify"

🔴 BOTH ARE STALE, AND THE SECOND IS THE INTERESTING ONE.

* The tape-and-disk blocker was already false when it was written:
  `basic_probe_cas_verbs.py` runs on `C-BIOS_MSX1_EU_REPACK_DISK`, whose own
  `<CassettePort/>` sits beside the disk, and `basic_probe_cas_match_cf3300.py`
  boots the **stock CF-3300 with `-diska` AND `-cassetteplayer` together**. That
  is the exact combination the entry says nobody has.
* 🎯 AND IT DOES NOT MATTER, because **no tape is needed at all**. `OPEN"CAS:T"
  FOR OUTPUT` succeeds with NO cassette attached -- measured, `E0=0` -- so the
  channel exists and can be interrogated with nothing in the drive. The blocker
  described an apparatus for a harder experiment than the question needs.
* "No reading to falsify" was true of the FILING and not of the WORLD: an
  inference predicts values, and a prediction is falsifiable. Ours are
  0/5/58/58/55.

METHOD. Both sides run the same program. zerobas is typed on the repack disk
machine. The CF-3300 cannot be typed at (its disk-BASIC date prompt hijacks the
keyboard -- the constraint `basic_probe_cas_match_cf3300.py` documents), so the
program ships as an auto-running `AUTOEXEC.BAS` on a FAT12 data disk and the
answers come back through RAM, read with `debug read_block`. Same rig, same
addresses ($D005.. -- the region that probe already POKEs safely), no tape.

⚠️ THE `LPT:` ARM IS THE CONTROL AND IT RUNS LAST, AFTER THE CAS DONE-MARKER.
It re-measures the analogy's own source on the same machine in the same run, so
"CAS: matches the inference" cannot be confused with "this rig reads 58 for
everything". It is last because `LPT:` with no printer attached is the one arm
that could hang; if it does, the CAS answers and their marker are already in RAM.

    python3 scratchpad/casfch_probe.py
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
sys.path.insert(0, os.path.join(ROOT, "probes", "disk"))
import omsx_preflight                                              # noqa: E402
import omsx_repl                                                   # noqa: E402
from make_test_dsk import Fat12Image                               # noqa: E402
from basic_probe_cas_ascii import build_ascii_cas                  # noqa: E402

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
BASE = 0xD005                    # the window basic_probe_cas_match_cf3300 pokes
ZB = "C-BIOS_MSX1_EU_REPACK_DISK"

# offset -> what it holds. The CAS done-marker sits BEFORE the LPT arm on purpose.
SLOTS = [("open",  0, 'OPEN"CAS:T"FOR OUTPUT AS#1'),
         ("field", 1, "FIELD#1,10 AS A$"),
         ("get",   2, "GET#1,1"),
         ("put",   3, "PUT#1,1"),
         ("inp",   4, "A$=INPUT$(1,#1)"),
         ("MARK",  5, "-- cas done marker &HA5 --"),
         ("l.open", 6, 'OPEN"LPT:"FOR OUTPUT AS#2'),
         ("l.field", 7, "FIELD#2,10 AS B$"),
         ("l.get",  8, "GET#2,1"),
         ("l.inp",  9, "A$=INPUT$(1,#2)"),
         ("LMARK", 10, "-- lpt done marker &HA5 --"),
         ("i.open", 11, 'OPEN"CAS:D"FOR INPUT AS#3   (CAS_IN_MODE 8)'),
         ("i.field", 12, "FIELD#3,10 AS C$"),
         ("i.get",  13, "GET#3,1"),
         ("i.put",  14, "PUT#3,1"),
         ("i.inp",  15, "A$=INPUT$(1,#3)"),
         ("IMARK", 16, "-- cas-input done marker &HA5 --"),
         ("i.byte", 17, "ASC(A$) after INPUT$ -- 72 = 'H' of HELLO")]

# 🔴 `MAXFILES=2` IS LOAD-BEARING AND THE FIRST RUN DID NOT HAVE IT. The LPT
# control opened `AS#2` while MAXFILES defaulted to 1, so all four LPT slots read
# 52 (Bad file number) on BOTH machines -- a tidy, agreeing, WRONG column that
# measured "channel 2 does not exist" rather than LPT:'s per-verb codes. A
# control that varies the wrong axis is not a control
# [[a-case-that-agrees-can-agree-for-the-wrong-reason]]. `MAXFILES=` also does an
# implicit CLEAR, so it must precede everything.
LINES = [
    "5 MAXFILES=3",
    "10 ONERRORGOTO900",
    f'20 E=0:OPEN"CAS:T"FOR OUTPUT AS#1:POKE&H{BASE + 0:04X},E',
    f"30 E=0:FIELD#1,10 AS A$:POKE&H{BASE + 1:04X},E",
    f"40 E=0:GET#1,1:POKE&H{BASE + 2:04X},E",
    f"50 E=0:PUT#1,1:POKE&H{BASE + 3:04X},E",
    f"60 E=0:A$=INPUT$(1,#1):POKE&H{BASE + 4:04X},E",
    f"65 POKE&H{BASE + 5:04X},&HA5",
    f'70 E=0:OPEN"LPT:"FOR OUTPUT AS#2:POKE&H{BASE + 6:04X},E',
    f"72 E=0:FIELD#2,10 AS B$:POKE&H{BASE + 7:04X},E",
    f"74 E=0:GET#2,1:POKE&H{BASE + 8:04X},E",
    f"76 E=0:A$=INPUT$(1,#2):POKE&H{BASE + 9:04X},E",
    f"78 POKE&H{BASE + 10:04X},&HA5",
    # --- CAS_IN_MODE (8): needs a tape carrying an $EA data file, which is the
    # ONE arm here that cannot run on a bare machine -- with no tape, OPEN FOR
    # INPUT searches to end-of-tape and hangs. It runs last for that reason.
    f'79 E=0:OPEN"CAS:D"FOR INPUT AS#3:POKE&H{BASE + 11:04X},E',
    f"81 E=0:FIELD#3,10 AS C$:POKE&H{BASE + 12:04X},E",
    f"82 E=0:GET#3,1:POKE&H{BASE + 13:04X},E",
    f"83 E=0:PUT#3,1:POKE&H{BASE + 14:04X},E",
    f"84 E=0:A$=INPUT$(1,#3):POKE&H{BASE + 15:04X},E",
    f"86 POKE&H{BASE + 16:04X},&HA5",
    "88 END",
    "900 E=ERR:RESUME NEXT",
]


# --input-only: the CAS_IN arm ALONE, for isolating why the CF-3300 did not
# reach it in the full program. Three candidates and the run separates them:
# too little time, the OUTPUT arm having recorded over the tape, or the search
# itself never terminating.
if "--input-only" in sys.argv:
    LINES = ["5 MAXFILES=3", "10 ONERRORGOTO900",
             f'79 E=0:OPEN"CAS:D"FOR INPUT AS#3:POKE&H{BASE + 11:04X},E',
             f"81 E=0:FIELD#3,10 AS C$:POKE&H{BASE + 12:04X},E",
             f"82 E=0:GET#3,1:POKE&H{BASE + 13:04X},E",
             f"83 E=0:PUT#3,1:POKE&H{BASE + 14:04X},E",
             f'84 E=0:A$="":A$=INPUT$(1,#3):POKE&H{BASE + 15:04X},E',
             # 🎯 record WHAT was read, not just that it did not raise: a 0 in the
             # error slot is equally "succeeded" and "never ran". The $EA tape's
             # one line is HELLO, so a real read puts 72 ("H") here.
             f'85 IF LEN(A$)>0 THEN POKE&H{BASE + 17:04X},ASC(A$)',
             f"86 POKE&H{BASE + 16:04X},&HA5", "88 END",
             "900 E=ERR:RESUME NEXT"]


def run(machine, cap=40.0, timeout=150.0):
    """One machine, one run: AUTOEXEC.BAS on a FAT12 disk, an $EA data file on
    tape, answers read straight out of RAM.

    🎯 BOTH SIDES USE THIS SAME RIG. An earlier cut typed the program on zerobas
    and auto-ran it only on the CF-3300, which is a second difference between the
    columns on an item whose whole complaint is that its answer was reached by
    ANALOGY. Same disk, same tape, same addresses, same read-out."""
    subprocess.run(["pkill", "-9", "openmsx"], capture_output=True)
    time.sleep(1.0)
    tmp = tempfile.mkdtemp(prefix="casfch_")
    d = Fat12Image()
    d.add_file("AUTOEXEC", "BAS", ("\r\n".join(LINES) + "\r\n").encode())
    dk = os.path.join(tmp, "d.dsk")
    open(dk, "wb").write(d.finish())
    tape = os.path.join(tmp, "d.cas")
    open(tape, "wb").write(build_ascii_cas("D", ["HELLO"]))
    out = os.path.join(tmp, "o.txt")
    tcl = (f"set throttle off\nset renderer none\nset sound_driver null\n"
           f"proc cap {{}} {{ set f [open {{{out}}} w]; "
           f"binary scan [debug read_block {{memory}} 0x{BASE:04X} 18] H* p; "
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


def main():
    print(__doc__.split("METHOD.")[0].strip()[:0] or "", end="")
    print("=== D-CASFCH: GET/PUT/FIELD/INPUT$ on a CAS: channel, MEASURED ===\n")
    print("program (identical on both sides):")
    for l in LINES:
        print("   ", l)
    for label, mach in (("zerobas", ZB), ("CF-3300", "National_CF-3300")):
        print(f"\n-- {label}: AUTOEXEC.BAS from disk + $EA tape, RAM read back --")
    zb = run(ZB)
    ref = run("National_CF-3300")
    if zb is None or ref is None:
        who = "zerobas" if zb is None else "CF-3300"
        print(f"  🔴 INSTRUMENT FAULT: the {who} run produced no RAM dump.")
        return 2

    print(f"\n  {'slot':8} {'statement':28} {'CF-3300':>9} {'zerobas':>9}")
    bad = []
    # in --input-only the CAS-OUT and LPT arms are not in the program at all;
    # their slots are untouched RAM on BOTH sides and must not be scored.
    live = {n for n, _o, _s in SLOTS}
    if "--input-only" in sys.argv:
        live = {n for n in live if n.startswith("i.") or n == "IMARK"}
    for name, off, stmt in SLOTS:
        if name not in live:
            continue
        r, z = ref[off], zb[off]
        if name in ("MARK", "LMARK"):
            note = "  (ran)" if r == 0xA5 else "  🔴 DID NOT REACH IT"
            print(f"  {name:8} {stmt:28} {r:9} {z:9}{note}")
            if r != 0xA5:
                bad.append(name)
            continue
        flag = "" if r == z else "  🔴 DIFF"
        if r != z:
            bad.append(name)
        print(f"  {name:8} {stmt:28} {r:9} {z:9}{flag}")
    print("\n" + ("ALL AGREE — the inference is CONFIRMED by measurement"
                  if not bad else f"🔴 {len(bad)} row(s) disagree: {bad}"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
