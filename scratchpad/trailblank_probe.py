#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-TRAILBLANK -- a trailing blank, delivered WITHOUT the line editor.

TODO (found 2026-07-31 by D-DECBLANK): at `--repeat 2` the references drop a
trailing blank and zerobas keeps it, in a `REM` tail as well as after a literal.
A `REM` tail is verbatim, so the difference is at **line ENTRY** — the editor —
not in any scanner. The entry names its own blocker and its own remedy:

    "The echo guard cannot referee it: echo_missing() rstrips every screen row,
     so a trailing blank is invisible to the guard no matter what the machine
     did with it ... Resolving the cell needs a delivery path that bypasses the
     line editor -- an ASCII LOAD"CAS:"."

🎯 THIS IS THAT PATH, and it settles a DIFFERENT question from the filed one on
purpose. Typing cannot referee the editor's own behaviour because the readout
that would referee it is `rstrip`ped. Loading an ASCII program from tape does not
go through the editor at all, so it establishes the GROUND TRUTH the filed
observation lacks: with the blank delivered verbatim, does the machine's
tokeniser keep it?

  * kept by all three  -> the tokeniser is innocent, and D-DECBLANK's difference
                          is the EDITOR alone, exactly as it suspected.
  * dropped by some    -> the crunch is in it after all, and the filing's
                          "not in any scanner" needs withdrawing.

⚠️ THE PAYLOAD PATH IS IDENTICAL ON ALL THREE MACHINES — the same $EA cassette
image — because the payload path is the subject. Only the COMMAND differs: the
VG-8020 and zerobas are typed at, while the CF-3300's disk-BASIC date prompt
hijacks the keyboard, so its `LOAD"CAS:"` ships as an AUTOEXEC.BAS on a disk. The
disk carries the command, never the payload.

The readout is the TOKENISED PROGRAM at TXTBASE, read with `debug read_block` —
bytes, not a screen, so nothing rstrips anything.

    python3 scratchpad/trailblank_probe.py
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
sys.path.insert(0, os.path.join(ROOT, "tools"))
import omsx_preflight                                              # noqa: E402
from basic_probe_cas_ascii import build_ascii_cas                  # noqa: E402
from make_test_dsk import Fat12Image                               # noqa: E402

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
TXTBASE = 0x8001
NBYTES = 48

# Each line ends in a REAL trailing blank. `10` is a REM tail (verbatim by the
# language's own rule) and `20` is a blank after a numeric literal -- D-DECBLANK's
# two shapes, so this run answers for both.
PAYLOAD = ["10 REM HELLO ", "20 A=1 "]

MACHINES = [("vg8020", "Philips_VG_8020", False),
            ("cf3300", "National_CF-3300", True),
            ("zb", "C-BIOS_MSX1_EU_REPACK_DISK", False)]


def run(machine, needs_disk, cap=34.0, timeout=150.0):
    subprocess.run(["pkill", "-9", "openmsx"], capture_output=True)
    time.sleep(1.0)
    tmp = tempfile.mkdtemp(prefix="trailblank_")
    tape = os.path.join(tmp, "t.cas")
    open(tape, "wb").write(build_ascii_cas("T", PAYLOAD))
    out = os.path.join(tmp, "o.txt")
    cmd = [OMSX, "-machine", machine, "-cassetteplayer", tape]
    if needs_disk:
        d = Fat12Image()
        d.add_file("AUTOEXEC", "BAS", b'10 LOAD"CAS:T"\r\n')
        dk = os.path.join(tmp, "d.dsk")
        open(dk, "wb").write(d.finish())
        cmd += ["-diska", dk]
        typing = ""
    else:
        typing = ('after time 6 { type "LOAD\\"CAS:T\\"" }\n'
                  'after time 8 { type "\\r" }\n')
    tcl = (f"set throttle off\nset renderer none\nset sound_driver null\n"
           f"{typing}"
           f"proc cap {{}} {{ set f [open {{{out}}} w]; "
           f"binary scan [debug read_block {{memory}} 0x{TXTBASE:04X} {NBYTES}] H* p; "
           f'puts $f "prog=$p"; close $f; exit }}\n'
           f"after time {cap} {{ cap }}\n")
    tp = os.path.join(tmp, "s.tcl")
    open(tp, "w").write(tcl)
    cmd += ["-script", tp]
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
        if k == "prog":
            return bytes.fromhex(v)
    return None


def lines_of(img):
    """Walk the tokenised program: [link][lineno][bytes...][00] per line."""
    out, i = [], 0
    while i + 4 < len(img):
        link = img[i] | (img[i + 1] << 8)
        if link == 0:
            break
        no = img[i + 2] | (img[i + 3] << 8)
        j = i + 4
        while j < len(img) and img[j] != 0:
            j += 1
        out.append((no, img[i + 4:j]))
        # the link is an ABSOLUTE address; step by the measured length instead
        i = j + 1
    return out


def show(body):
    txt = "".join(chr(b) if 32 <= b < 127 else f"<{b:02X}>" for b in body)
    return txt


def main():
    print("=== D-TRAILBLANK: a trailing blank delivered WITHOUT the editor ===\n")
    print("payload, as $EA ASCII on tape (note the real trailing spaces):")
    for l in PAYLOAD:
        print(f"    {l!r}")
    print()
    res = {}
    for label, mach, disk in MACHINES:
        img = run(mach, disk)
        if img is None:
            print(f"  {label:8} 🔴 INSTRUMENT FAULT: no memory dump")
            res[label] = None
            continue
        res[label] = lines_of(img)
        print(f"  {label:8} {len(res[label])} line(s) resident")
        for no, body in res[label]:
            trail = "TRAILING BLANK KEPT" if body.endswith(b" ") else "no trailing blank"
            print(f"      line {no:<4} {show(body)!r}   -> {trail}")
    print("\n=== verdict")
    good = {k: v for k, v in res.items() if v}
    if len(good) < 2:
        print("  🔴 too few machines answered to compare.")
        return 2
    for no in [l[0] for l in next(iter(good.values()))]:
        cells = {}
        for k, v in good.items():
            b = dict(v).get(no)
            cells[k] = (b is not None and b.endswith(b" "))
        same = len(set(cells.values())) == 1
        print(f"  line {no}: " + ", ".join(f"{k}={'kept' if c else 'dropped'}"
                                           for k, c in cells.items())
              + ("   AGREE" if same else "   🔴 DIFFER"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
