#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""RAM order step (1), measure first (Joost, 2026-10-13: biggest invented
regions first; "go ahead with that order"): WHICH BUFFER does the VG-8020 use
for cassette I/O?

zerobas keeps a 512 B page-aligned double buffer for it (CAL_BUF / CAL_BUF2,
CAS_WBUF), parked inside its 1 KB of FAT sector buffers -- which is what keeps
those buffers out of the diskless build's reach. If the reference does tape
I/O through the CHANNEL's own buffer (each FCB block carries one), the
cassette pair can move there and the FAT buffers become wholly disk-only.

METHOD (refwork_probe.py's): one boot per case per machine; a write watch
armed after boot over $8000..$F37F and the work area's data span
$F39A..$FD99 (the reference's RAM-resident code below $F39A and the hooks from
$FD9A are excluded; ADDRESSES only, never a value); each case MINUS its
control (the same typed program, the cassette verb replaced). The channel
blocks are located by VARPTR(#0) / VARPTR(#1) in a separate run, so a written
range can be NAMED, not guessed.

  save     SAVE"CAS:X",A of a 2-line program        (a fresh recording tape)
  load     LOAD"CAS:X" of a 2-line ASCII tape        (built by cas_encode)
  openout  OPEN"CAS:Y" FOR OUTPUT AS #1: PRINT#1: CLOSE
  openin   OPEN"CAS:X" FOR INPUT AS #1: INPUT#1,A$: CLOSE

Prediction: on the VG-8020 every case writes inside a channel block's buffer
(#0 for SAVE / LOAD, #1 for OPEN AS #1) and nowhere else of size; no
separate 256 B buffer.
"""
import os, sys, tempfile
os.environ["ZEROBAS_REFCACHE"] = "0"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
import omsx_repl                                   # noqa: E402

MACHINES = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")
SPANS = ((0x8000, 0xF37F), (0xF39A, 0xFD99))
PROG = ["10 REM HELLO WORLD", "20 PRINT 12345"]


def tape(path):
    from basic_probe_cas_ascii import build_ascii_cas
    open(path, "wb").write(build_ascii_cas("X", ["10 REM HELLO WORLD", "20 PRINT 12345"]))


def run(machine, lines, cas_cmd, gap=12.0):
    fd, path = tempfile.mkstemp(suffix=".txt", prefix="casbuf_")
    os.close(fd)
    os.unlink(path)
    pro = ["set ::__wseen [dict create]", f"set ::__wf {{{path}}}",
           "proc __wrec {} { set a $::wp_last_address; "
           "if {![dict exists $::__wseen $a]} { dict set ::__wseen $a 1; "
           "set f [open $::__wf a]; puts $f $a; close $f } }"]
    if cas_cmd:
        pro.append(cas_cmd)
    pro += [f"after time 7.5 {{debug set_watchpoint write_mem {{0x{lo:04X} 0x{hi:04X}}} {{}} {{__wrec}}}}"
            for lo, hi in SPANS]
    omsx_repl.run_cases(machine, [("direct", ["NEW"] + lines)], batch=False,
                        reset=("", "SCREEN 0"), run_gap=gap, prologue=tuple(pro))
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


def fcbs(machine):
    raw = omsx_repl.run_cases(machine, [("direct", ["NEW", 'A=VARPTR(#0):B=VARPTR(#1):?"["A;B"]"'])],
                              batch=False, reset=("", "SCREEN 0"), run_gap=6.0)[0]
    v = omsx_repl.result_span(raw) if raw else None
    try:
        a, b = (int(x) & 0xFFFF for x in v.split())
        return a, b
    except Exception:
        return None


def main():
    tmp = tempfile.mkdtemp(prefix="casbuf_")
    cas = os.path.join(tmp, "in.cas")
    tape(cas)
    for machine in MACHINES:
        f = fcbs(machine)
        print(f"=== {machine}: VARPTR(#0), VARPTR(#1) = "
              + (", ".join(f"${x:04X}" for x in f) if f else "NO READING"), flush=True)
        cases = {
            "save": (PROG + ['SAVE"CAS:X",A'], PROG + ["LIST"],
                     f"cassetteplayer new {{{os.path.join(tmp, machine + '_s.wav')}}}", 30.0),
            "load": (['LOAD"CAS:X"'], ["PRINT 1"], f"cassetteplayer insert {{{cas}}}", 30.0),
            "openout": (['OPEN"CAS:Y" FOR OUTPUT AS #1:PRINT#1,"HELLO WORLD":CLOSE#1'], ['PRINT"HELLO WORLD"'],
                        f"cassetteplayer new {{{os.path.join(tmp, machine + '_o.wav')}}}", 30.0),
            "openin": (['OPEN"CAS:X" FOR INPUT AS #1:INPUT#1,A$:CLOSE#1'], ['A$="HELLO WORLD"'],
                       f"cassetteplayer insert {{{cas}}}", 30.0),
        }
        for name, (lines, ctl, cc, gap) in cases.items():
            got, base = run(machine, lines, cc, gap), run(machine, ctl, cc, gap)
            if got is None or base is None:
                print(f"   {name:8s} NO READING")
                continue
            extra = got - base
            rs = ranges(extra)
            big = [(lo, hi) for lo, hi in rs if hi - lo + 1 >= 8]
            print(f"   {name:8s} {len(extra):4d} B beyond its control; runs >= 8 B: "
                  + (", ".join(f"${lo:04X}..${hi:04X} ({hi - lo + 1})" for lo, hi in big) or "none"),
                  flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
