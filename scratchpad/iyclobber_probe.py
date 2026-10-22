#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-PLAYIY triage, zerobas ONLY (its own code): type a direct-mode line, arm at a
zerobas label, and log the PC and the stack (mapped to zerobas symbols) the first
times IY takes a given value after that -- who hands the caller a clobbered IY.

    python3 -u scratchpad/iyclobber_probe.py ['A$="CDE":B$="EFG":PLAY "C",A$,B$'] \
        [--arm pl_voice] [--iy 0x8B00] [--machine C-BIOS_MSX1_EU_REPACK_NODISK]
"""
import argparse, os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_preflight  # noqa: E402

OMSX = os.environ.get("OPENMSX", shutil.which("openmsx") or "/opt/homebrew/bin/openmsx")


def syms():
    out = []
    for f in ("basic-reloc.sym",):
        for ln in open(os.path.join(REPO, "build", f)):
            m = re.match(r"(\S+)\s+EQU\s+0*([0-9A-Fa-f]+)H", ln.strip())
            if m and not m.group(1).isupper():
                out.append((int(m.group(2), 16), m.group(1)))
    return sorted(out)


def name(table, a):
    c = [s for s in table if s[0] <= a]
    return f"{c[-1][1]}+{a - c[-1][0]:#x}" if c and a < 0xC000 else f"{a:04X}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("line", nargs="?", default='A$="CDE":B$="EFG":PLAY "C",A$,B$')
    ap.add_argument("--arm", default="pl_voice")
    ap.add_argument("--iy", default="0x8B00")
    ap.add_argument("--machine", default="C-BIOS_MSX1_EU_REPACK_NODISK")
    a = ap.parse_args()
    table = syms()
    arm = dict((n, v) for v, n in table)[a.arm]
    td = tempfile.mkdtemp(prefix="iyclob_")
    try:
        out = os.path.join(td, "o.txt")
        esc = a.line
        for ch in '\\"$[]':
            esc = esc.replace(ch, "\\" + ch)
        tcl = [
            "set ::armed 0; set ::hits 0",
            "proc __w {x} { expr {[debug read memory [expr {$x & 0xFFFF}]] + 256*[debug read memory [expr {($x+1) & 0xFFFF}]]} }",
            "proc __log {tag} {",
            f"  set f [open {{{out}}} a]",
            "  set sp [reg sp]; set st {}",
            "  for {set i 0} {$i < 12} {incr i} { lappend st [format %04X [__w [expr {$sp + 2*$i}]]] }",
            "  puts $f \"$tag [format %04X [reg pc]] [format %04X [reg iy]] $st\"",
            "  close $f",
            "}",
            f"debug set_bp {arm:#x} {{}} {{ set ::armed 1; __log ARM }}",
            f"debug set_condition {{$::armed && [reg iy] == {a.iy}}} {{ incr ::hits; __log HIT; if {{$::hits >= 3}} {{ set ::armed 0 }} }}",
            "set throttle off",
            f'after time 8 {{ type "{esc}\\r" }}',
            "after time 14 { exit }",
        ]
        s = os.path.join(td, "s.tcl")
        open(s, "w").write("\n".join(tcl) + "\n")
        subprocess.run(omsx_preflight.guarded([OMSX, "-machine", a.machine, "-command",
                        "set renderer none; set sound_driver null", "-script", s]),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
        if not os.path.exists(out):
            print("<NO OUTPUT>")
            return
        for ln in open(out):
            p = ln.split()
            print(f"{p[0]} pc={name(table, int(p[1], 16))} iy={p[2]}")
            print("     stack: " + " ".join(name(table, int(x, 16)) for x in p[3:]))
    finally:
        shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    main()
