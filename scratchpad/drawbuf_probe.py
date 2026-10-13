#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""RAM order step (2), RE-PRICED and measured first (Joost 2026-10-13: biggest
invented regions first, "go ahead with that order").

The order named "the PAINT span stack GFX_PSTK (360 B)". That premise is
STALE: D-PAINTSP (2026-09-27) already moved PAINT's spans below SP, as on the
VG-8020. What still holds the 360 B window ($E7F2..$E959 since D-FATFLOOR) is a
union whose binding tenant is DRAW: a 256 B frame buffer GFX_DBUF the strings
are COPIED into, an 8-deep X-frame stack GFX_DFSTK (32 B) and ~60 B of parse
state. So the question becomes: WHERE DOES THE VG-8020's DRAW KEEP ITS STRING
AND ITS X NESTING?

METHOD (casbuf_probe.py's): one boot per case per machine; a write watch armed
after boot over $8000..$F37F and the work area's data span $F39A..$FD99 (the
reference's RAM-resident code below $F39A and the hooks from $FD9A are
excluded; ADDRESSES only, never a value); each case MINUS its control (the same
program with the DRAW replaced by a string assignment of the same strings).
STKTOP and MEMSIZ are read in a separate run so a written range can be named.

  draw    DRAW of a 3-level X nest (A$ -> B$ -> C$), ~40 commands
  long    DRAW of one 200-character string (no X)

Prediction (2026-10-13): on the VG-8020 neither case writes a run >= 64 B; what
it writes beyond the control lies in the stack band below STKTOP and in a few
documented work-area cells. zerobas writes its frame buffer at $E7F2 (a run of
about the string's length) and its parse state above it.
"""
import os, sys, tempfile
os.environ["ZEROBAS_REFCACHE"] = "0"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

MACHINES = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")
SPANS = ((0x8000, 0xF37F), (0xF39A, 0xFD99))
STRS = ['5 CLEAR 1000', '10 C$="R3D3L3U3"', '20 B$="R6D6XC$;L6U6"', '30 A$="BM100,90R9D9XB$;L9U9XB$;"',
        '40 D$=STRING$(50,"R")+STRING$(50,"D")+STRING$(50,"L")+STRING$(50,"U")']
CASES = {
    "draw": ("60 DRAW\"XA$;\"", "60 E$=A$"),
    "long": ("60 DRAW\"BM40,40XD$;\"", "60 E$=D$"),
}


def run(machine, line60):
    fd, path = tempfile.mkstemp(suffix=".txt", prefix="drawbuf_")
    os.close(fd)
    os.unlink(path)
    pro = ["set ::__wseen [dict create]", f"set ::__wf {{{path}}}",
           "proc __wrec {} { set a $::wp_last_address; "
           "if {![dict exists $::__wseen $a]} { dict set ::__wseen $a 1; "
           "set f [open $::__wf a]; puts $f $a; close $f } }"]
    pro += [f"after time 7.5 {{debug set_watchpoint write_mem {{0x{lo:04X} 0x{hi:04X}}} {{}} {{__wrec}}}}"
            for lo, hi in SPANS]
    # 🔴 RUN 1 WAS VACUOUS: the default 200 B string space refused line 40
    # ("Out of string space in 40") on BOTH machines, so no DRAW ran and the
    # two readings agreed for the wrong reason. CLEAR 1000 above, and the run
    # must now print its marker or the reading is refused.
    prog = STRS + ["50 SCREEN 2", line60, "70 SCREEN 0", '80 PRINT"DONE"+"OK"', "RUN"]
    raw = omsx_repl.run_cases(machine, [("direct", ["NEW"] + prog)], batch=False,
                              reset=("", "SCREEN 0"), run_gap=14.0, prologue=tuple(pro))[0]
    if not raw or "DONEOK" not in raw:
        print(f"   INSTRUMENT FAULT ({machine}, {line60}): the program did not finish: "
              + (" ".join(raw.split())[-160:] if raw else "no screen"), flush=True)
        return None
    if not os.path.exists(path):
        return None
    out = {int(l) for l in open(path) if l.strip()}
    os.unlink(path)
    return out


def ranges(addrs):
    out, cur = [], None
    for a in sorted(addrs):
        if cur and a == cur[1] + 1:
            cur[1] = a
        else:
            cur = [a, a]
            out.append(cur)
    return out


def tops(machine):
    line = '?"["PEEK(&HF674)+256*PEEK(&HF675)PEEK(&HF672)+256*PEEK(&HF673)"]"'
    raw = omsx_repl.run_cases(machine, [("direct", ["NEW", line])],
                              batch=False, reset=("", "SCREEN 0"), run_gap=6.0)[0]
    v = omsx_repl.result_span(raw) if raw else None
    try:
        a, b = (int(x) for x in v.split())
        return a, b
    except Exception:
        return None


def main():
    for machine in MACHINES:
        t = tops(machine)
        print(f"=== {machine}: STKTOP, MEMSIZ = "
              + (", ".join(f"${x:04X}" for x in t) if t else "NO READING"), flush=True)
        for name, (case, ctl) in CASES.items():
            got, base = run(machine, case), run(machine, ctl)
            if got is None or base is None:
                print(f"   {name:5s} NO READING", flush=True)
                continue
            extra = got - base
            rs = ranges(extra)
            big = [(lo, hi) for lo, hi in rs if hi - lo + 1 >= 8]
            print(f"   {name:5s} {len(extra):4d} B beyond its control ({len(got)} written in all); "
                  "runs >= 8 B: "
                  + (", ".join(f"${lo:04X}..${hi:04X} ({hi - lo + 1})" for lo, hi in big) or "none"),
                  flush=True)
            small = [(lo, hi) for lo, hi in rs if hi - lo + 1 < 8]
            print(f"         smaller: " + " ".join(
                f"${lo:04X}" + (f"..${hi:04X}" if hi > lo else "") for lo, hi in small[:40]),
                flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
