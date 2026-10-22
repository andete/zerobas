#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DISKRUN triage: boot ONE image of the disk collection on one machine, type a
script of key lines at given times, and print the screen text at each capture.
Black box -- keys in, the screen (VRAM name table), CURLIN and PC out; the software
is RUN, never decoded. The image is copied to /tmp first; the collection's location
comes from DISKCORPUS_DIR and is never written here.

    DISKCORPUS_DIR=... python3 -u scratchpad/disklook.py IMAGE MACHINE \
        "20:" "21:LIST 30" "24:"  [--ext Philips_NMS_1200]

Each step is `T:keys` -- at T seconds type `keys` + RETURN (nothing when empty), and
capture 2.5 s later. `^C` in keys is CTRL+STOP (typed as a key combo).
"""
import argparse, os, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_preflight  # noqa: E402  (no settings saved, autorun un-armed)
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import diskcorpus_run as D  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("machine")
    ap.add_argument("steps", nargs="+")
    ap.add_argument("--ext", action="append", default=[])
    ap.add_argument("--persist", help="a working image path OUTSIDE the repo: copied from\n"
                    "the collection only when absent, and KEPT -- a second boot sees what\n"
                    "the first one SAVEd")
    a = ap.parse_args()
    td = tempfile.mkdtemp(prefix="disklook_")
    try:
        src = os.path.join(os.environ["DISKCORPUS_DIR"], a.image)
        ext = os.path.splitext(src)[1].lower()
        dsk = a.persist or os.path.join(td, "d" + (".xsa" if ext == ".xsa" else ".dsk"))
        if not os.path.exists(dsk):
            shutil.copy(src, dsk)
        out = os.path.join(td, "c.txt")
        tcl = ["set throttle off",
               "proc __cap {tag} {",
               f"  set f [open {{{out}}} a]",
               "  binary scan [debug read_block VRAM 0 16384] H* v",
               "  set r {}",
               "  for {set i 0} {$i < 8} {incr i} { lappend r [vdpreg $i] }",
               "  binary scan [debug read_block memory 0xF41C 2] H* cl",
               "  puts $f \"$tag [reg pc] $r $cl $v\"",
               "  close $f",
               "}"]
        last = 0.0
        for k, st in enumerate(a.steps):
            t, keys = st.split(":", 1)
            t = float(t)
            if keys == "^C":
                tcl.append(f"after time {t} {{ keymatrixdown 6 0x02; keymatrixdown 7 0x10 }}")
                tcl.append(f"after time {t + 0.3} {{ keymatrixup 6 0x02; keymatrixup 7 0x10 }}")
            elif keys:
                # Tcl: a backslash, a quote, `$` (HEX$, A$) and brackets all mean
                # something inside "..." and must arrive as themselves
                esc = keys
                for ch in '\\"$[]':
                    esc = esc.replace(ch, "\\" + ch)
                tcl.append(f'after time {t} {{ type "{esc}\\r" }}')
            tcl.append(f"after time {t + 2.5} {{ __cap S{k} }}")
            last = t + 2.5
        tcl.append(f"after time {last + 0.5} {{ exit }}")
        open(os.path.join(td, "s.tcl"), "w").write("\n".join(tcl) + "\n")
        cmd = ["/opt/homebrew/bin/openmsx", "-machine", a.machine]
        for e in a.ext:
            cmd += ["-ext", e]
        cmd += ["-diska", dsk, "-command", "set renderer none; set sound_driver null",
                "-script", os.path.join(td, "s.tcl")]
        subprocess.run(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=60 + 2 * last)
        if not os.path.exists(out):
            print("<NO CAPTURE: the machine did not run>")
            return 1
        for ln in open(out):
            p = ln.split()
            cap = {"pc": int(p[1]), "regs": [int(x) for x in p[2:10]],
                   "curlin": int(p[10][2:4] + p[10][0:2], 16), "vram": bytes.fromhex(p[11])}
            print(f"== {p[0]} ({a.steps[int(p[0][1:])]!r})  pc={cap['pc']:04X} "
                  f"curlin={cap['curlin']:04X} mode={D.mode_of(cap['regs'])}")
            for row in D.screen_text(cap):
                print("   |" + row)
        return 0
    finally:
        shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
