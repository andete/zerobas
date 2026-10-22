#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-TAPELOAD triage: LOAD a tape's program WITHOUT running it, then type key lines
(LIST ranges, PRINT FRE(0)) and read the screen -- on the VG-8020 and on zerobas.
What a user would do to see what arrived. Black box: keys in, the screen out; the
program is listed by the machine's own LIST, never decoded here, and nothing of it
is written into the repo beyond what a probe output shows.

    TAPECORPUS_DIR=... python3 -u scratchpad/tapelist_probe.py TITLE \
        'LOAD"CAS:"' 'LIST 130-140' ... [--wait 150] [--machines ref,zb]
The first key line is typed at T6; it may run for --wait seconds (the load); every
later line gets 4 s and its own screen capture.
"""
import argparse, os, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_preflight  # noqa: E402  (no settings saved, autorun un-armed)
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tapecorpus_run as T  # noqa: E402


def run(machine, cas, keys, wait, step=4.0):
    td = tempfile.mkdtemp(prefix="tlist_")
    try:
        out = os.path.join(td, "c.txt")
        lines = ["after time 0.3 { cassetteplayer insert {" + cas + "} }",
                 "set throttle off",
                 "proc __cap {tag} {",
                 f"  set f [open {{{out}}} a]",
                 "  binary scan [debug read_block VRAM 0 16384] H* v",
                 "  set r {}",
                 "  for {set i 0} {$i < 8} {incr i} { lappend r [vdpreg $i] }",
                 '  puts $f "$tag [reg pc] $r 0000 $v"',
                 "  close $f",
                 "}"]
        t = 6.0                               # past both machines' boot
        for k, key in enumerate(keys):
            esc = key
            for ch in '\\"$[]':
                esc = esc.replace(ch, "\\" + ch)
            lines.append(f'after time {t} {{ type "{esc}\\r" }}')
            t += wait if k == 0 else step
            lines.append(f"after time {t - 0.5} {{ __cap K{k} }}")
        lines.append(f"after time {t} {{ exit }}")
        open(os.path.join(td, "s.tcl"), "w").write("\n".join(lines) + "\n")
        subprocess.run(omsx_preflight.guarded([T.OMSX, "-machine", machine, "-command",
                        "set renderer none; set sound_driver null",
                        "-script", os.path.join(td, "s.tcl")]),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120 + 3 * t)
        caps = []
        if os.path.exists(out):
            for ln in open(out):
                p = ln.split()
                caps.append((p[0], T.D.screen_text({"pc": int(p[1]),
                                                    "regs": [int(x) for x in p[2:10]],
                                                    "curlin": 0, "vram": bytes.fromhex(p[11])})))
        return caps
    finally:
        shutil.rmtree(td, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("title")
    ap.add_argument("keys", nargs="+")
    ap.add_argument("--wait", type=float, default=150.0)
    ap.add_argument("--machines", default="ref,zb")
    ap.add_argument("--step", type=float, default=4.0,
                    help="seconds per later key line (long lines type slowly)")
    a = ap.parse_args()
    td = tempfile.mkdtemp(prefix="tlistz_")
    try:
        cas = T.unpack(os.path.join(os.environ["TAPECORPUS_DIR"], a.title + ".zip"), td)
        for m in a.machines.split(","):
            machine = T.REF if m == "ref" else T.ZB
            print(f"### {m} ({machine})")
            for tag, rows in run(machine, cas, a.keys, a.wait, a.step):
                print(f"== {tag} {a.keys[int(tag[1:])]!r}")
                for r in rows:
                    print("   |" + r)
    finally:
        shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    main()
