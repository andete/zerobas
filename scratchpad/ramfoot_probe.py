#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-RAMFOOT: the RAM FOOTPRINT of one BASIC operation, on the VG-8020 and here.

TIER 4 (RAM usage), goals (b) same addresses and (c) same economy -- Joost,
2026-09-24: proof is *"the whole RAM map"*, and *"I have a hunch reference is
very economical with RAM"*. This is the measurement half; any ADJUSTMENT it
suggests goes back to him.

🎯 METHOD. Each case is ONE program line,
    10 POKE&HE000,201:<op>:POKE&HE000,202
and a `write_mem` watchpoint over $E001..$FFFF counts only while the window the
program opened itself is open. Every address written is recorded with the SP
range seen during the window, so stack pushes are CLASSIFIED (never counted as
cells). One batched boot per machine; the window index keys the cases.

🔴 CONTROLS -- a region verdict means nothing without them.
  C0  `ctl` (empty op): the background -- the interrupt, and the evaluation of
      the closing POKE itself. Op-specific writes are case - ctl.
  C1  POSITIVE: `POKE&HE001,7` MUST record $E001 on both machines, or the
      watchpoint is misconfigured and the run is REFUSED.
  C2  every case's window must have opened AND closed (an unclosed window is
      a program that errored before its closing POKE -- named, not scored).

🔴 CLEAN ROOM. RAM addresses, RAM contents and SP only. No ROM byte is read,
nothing is single-stepped, PC is never read. The reference's RAM-resident
code clusters (§8.5) are not in this band on a diskless VG-8020.
"""
import os
import re
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))

REF = "Philips_VG_8020"
ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
MARK, OPEN, CLOSE = 0xE000, 201, 202
LO, HI = 0xE001, 0xFFFF
# 🔴 WINDOWS ARE KEYED BY A TAG THE CASE WRITES, NOT BY THEIR ORDER. The first
# run counted opens, and zerobas's rows from `cls` on carried the PREVIOUS
# case's cells (RND showed CSRY/LINTTB). Each case now pokes its own index to
# $E002 first thing inside the window; an untagged window is not scored.
TAG = 0xE002
HTIMI = 0xFD9F                 # H.TIMI: a RAM hook cell the interrupt calls
STD = 0xF380                   # the MSX standard work area starts here

CASES = [
    ("ctl", ""),
    ("pos", "POKE&HE001,7"),
    # the interrupt SIGNATURE: a window held open across one tick by a loop
    # whose own cells are written all through it, so only the ISR's are close
    ("isr", "X7=TIME:FOR J7=1 TO 2:J7=1-(TIME<>X7):NEXT"),
    ("num", "A=1"),
    ("int", "A%=1"),
    ("str", 'A$="AB"'),
    ("dim", "DIM Z(5)"),
    ("for", "FOR I=1 TO 2:NEXT"),
    ("print", "PRINT 1"),
    ("locate", "LOCATE 1,1"),
    ("cls", "CLS"),
    ("rnd", "X=RND(1)"),
    ("sin", "X=SIN(1)"),
    ("strd", "A$=STR$(5)"),
    ("left", 'A$=LEFT$("AB",1)'),
    ("fre", "X=FRE(0)"),
    ("color", "COLOR 15"),
    ("peek", "X=PEEK(0)"),
    ("inkey", "A$=INKEY$"),
]

TCL = r'''
set ::w -1
set ::open 0
array set ::hit {}
array set ::sp0 {}
array set ::spmin {}
array set ::closed {}
debug set_watchpoint write_mem @MARK@ {} {
    if {$::wp_last_value == @OPEN@} {
        incr ::w
        set ::open 1
        set ::sp0($::w) [reg SP]
        set ::spmin($::w) [reg SP]
        set ::t0($::w) [machine_info time]
        set ::nint($::w) 0
    } elseif {$::wp_last_value == @CLOSE@ && $::open} {
        set ::open 0
        set ::closed($::w) 1
        set ::dt($::w) [expr {[machine_info time] - $::t0($::w)}]
    }
}
array set ::t0 {}
array set ::dt {}
array set ::nint {}
debug set_bp @HTIMI@ {} { if {$::open} { incr ::nint($::w)
    lappend ::th($::w) [expr {[machine_info time] - $::t0($::w)}] } }
array set ::tag {}
array set ::tt {}
array set ::many {}
array set ::th {}
debug set_watchpoint write_mem {@LO@ @HI@} {} {
    if {!$::open} { return }
    if {$::wp_last_address == @TAGA@} { set ::tag($::w) $::wp_last_value }
    set sp [reg SP]
    if {$sp < $::spmin($::w)} { set ::spmin($::w) $sp }
    set k "$::w,$::wp_last_address"
    set t [expr {[machine_info time] - $::t0($::w)}]
    if {[info exists ::hit($k)]} { incr ::hit($k) } else { set ::hit($k) 1 ; set ::tt($k) {} }
    if {[llength $::tt($k)] < 32} { lappend ::tt($k) $t } else { set ::many($k) 1 }
}
proc __dump {} {
    set f [open {@OUT@} w]
    puts $f "W $::w"
    foreach k [array names ::sp0] {
        set c 0
        if {[info exists ::closed($k)]} { set c 1 }
        puts $f "S $k $::sp0($k) $::spmin($k) $c"
    }
    foreach k [array names ::hit] {
        set m 0
        if {[info exists ::many($k)]} { set m 1 }
        puts $f "H $k $::hit($k) $m $::tt($k)"
    }
    foreach k [array names ::th] { puts $f "I $k $::th($k)" }
    foreach k [array names ::tag] { puts $f "T $k $::tag($k)" }
    foreach k [array names ::dt] { puts $f "D $k $::dt($k) $::nint($k)" }
    close $f
    after time 1 __dump
}
after time 1 __dump
'''


def prologue(out):
    t = TCL
    for k, v in (("@OUT@", out), ("@MARK@", str(MARK)), ("@OPEN@", str(OPEN)),
                 ("@CLOSE@", str(CLOSE)), ("@LO@", str(LO)), ("@HI@", str(HI)),
                 ("@TAGA@", str(TAG)), ("@HTIMI@", str(HTIMI))):
        t = t.replace(k, v)
    return (t,)


def case_lines(op, idx=0):
    """⏱ Lines 5-6 wait for TIME to tick (kwtime's sync), so a short window
    opens just after an interrupt and usually holds none."""
    body = (f"10 POKE&H{MARK:04X},{OPEN}:POKE&H{TAG:04X},{idx}:"
            + (op + ":" if op else "") + f"POKE&H{MARK:04X},{CLOSE}")
    return ["NEW", "5 X7=TIME", "6 IF TIME=X7 THEN 6", body, "RUN"]


def parse(path):
    """-> {window: {"sp0", "spmin", "closed", "cells": {addr: n}}}"""
    out = {}
    for ln in open(path):
        p = ln.split()
        if not p:
            continue
        if p[0] == "S" and len(p) == 5:
            w = int(p[1])
            out.setdefault(w, {"cells": {}}).update(
                sp0=int(p[2]), spmin=int(p[3]), closed=p[4] == "1")
        elif p[0] == "H" and len(p) >= 4:
            w, a = (int(x) for x in p[1].split(","))
            d = out.setdefault(w, {"cells": {}})
            d["cells"][a] = int(p[2])
            # None = more than 32 writes: a loop's cell, never the interrupt's
            d.setdefault("times", {})[a] = (None if p[3] == "1"
                                            else [float(x) for x in p[4:]])
        elif p[0] == "I" and len(p) >= 3:
            out.setdefault(int(p[1]), {"cells": {}})["ticks"] = [float(x) for x in p[2:]]
        elif p[0] == "D" and len(p) == 4:
            d = out.setdefault(int(p[1]), {"cells": {}})
            d["dt"], d["nint"] = float(p[2]), int(p[3])
        elif p[0] == "T" and len(p) == 3:
            out.setdefault(int(p[1]), {"cells": {}})["tag"] = int(p[2])
    # re-key by TAG; an untagged window is dropped (it was not one of ours)
    return {d["tag"]: d for d in out.values() if "tag" in d}


def split_stack(win):
    """-> (cells, stack): an address inside [spmin, sp0+2) is a push, not a cell;
    the mark and tag cells are the probe's own."""
    lo, hi = win.get("spmin", 0), win.get("sp0", 0) + 2
    cells = {a for a in win["cells"] if not (lo <= a < hi) and a != TAG}
    return cells, set(win["cells"]) - cells - {TAG}


ISR_PRE, ISR_POST = 0.0003, 0.003    # s around an H.TIMI hit


def isr_cells(win, cells):
    """cells EVERY write of which falls near SOME H.TIMI hit (0.3 ms before ..
    3 ms after). Used ONLY on the `isr` control, whose loop writes its own cells
    all through the window, to extract each machine's interrupt SIGNATURE.
    🔴 PER WRITE, NOT A FIRST..LAST SPAN: a span made JIFFY, written at two ticks
    20 ms apart, look like a cell written throughout. 🔴 AND NEVER PER OP: an op
    that happens to run just after a tick would lose real cells (it flagged
    FORCLR on COLOR). 🔴 NOT `iff` either: zerobas writes ARYTAB/FRETOP/CTLLIM
    under DI (its slot switches)."""
    ticks, times = win.get("ticks", []), win.get("times", {})
    return {a for a in cells if times.get(a) and all(
        any(h - ISR_PRE <= t <= h + ISR_POST for h in ticks) for t in times[a])}


def run(machine, boot):
    import omsx_repl
    fd, out = tempfile.mkstemp(prefix="ramfoot-", suffix=".txt")
    os.close(fd)
    specs = [("direct", case_lines(op, i)) for i, (_k, op) in enumerate(CASES)]
    omsx_repl.run_cases(machine, specs, batch=True, reset=("CLS",), boot=boot,
                        capture="screen", prologue=prologue(out))
    try:
        return parse(out)
    finally:
        os.unlink(out)


def names():
    """address -> 'NAME' from docs/ram-map.md (basic's names first)."""
    nm = {}
    for ln in open(os.path.join(REPO, "docs", "ram-map.md"), encoding="utf-8"):
        m = re.match(r"^\| `\$([0-9A-F]{4})` \| [^|]* \| `(\w+)` \| `([^`]+)`", ln)
        if m:
            a = int(m.group(1), 16)
            if m.group(2) == "basic" or a not in nm:
                nm[a] = m.group(3)
    return nm


def runs(addrs):
    out, s = [], sorted(addrs)
    for a in s:
        if out and a == out[-1][1] + 1:
            out[-1][1] = a
        else:
            out.append([a, a])
    return out


def fmt(addrs, nm):
    parts = []
    for a, b in runs(addrs):
        tag = nm.get(a, "")
        parts.append((f"${a:04X}" if a == b else f"${a:04X}-${b:04X}")
                     + (f"({tag})" if tag else ""))
    return " ".join(parts) or "-"


def selftest():
    ok = True
    w = {"sp0": 0xF000, "spmin": 0xEFF0, "cells": {0xEFF4: 1, 0xF001: 1, 0xF3A0: 2}}
    c, s = split_stack(w)
    ok &= c == {0xF3A0} and s == {0xEFF4, 0xF001}
    # NEGATIVE: an address just ABOVE the stack window is a cell, not a push
    ok &= split_stack({"sp0": 0xF000, "spmin": 0xF000, "cells": {0xF002: 1}})[0] == {0xF002}
    ok &= runs([1, 2, 3, 7]) == [[1, 3], [7, 7]]
    ok &= case_lines("", 0)[3] == "10 POKE&HE000,201:POKE&HE002,0:POKE&HE000,202"
    ok &= case_lines("A=1", 4)[3] == "10 POKE&HE000,201:POKE&HE002,4:A=1:POKE&HE000,202"
    fd, p = tempfile.mkstemp()
    # window 0 is tagged 5, window 1 untagged -> only tag 5 survives, re-keyed
    os.write(fd, b"W 1\nS 0 61440 61430 1\nS 1 61440 61440 0\n"
                 b"H 0,57345 3 0 0.001 0.002 0.002\nH 0,62000 1 1\nT 0 5\n")
    os.close(fd)
    got = parse(p)
    os.unlink(p)
    ok &= list(got) == [5] and got[5]["closed"] and got[5]["cells"] == {0xE001: 3, 62000: 1}
    # isr_cells: a cell whose writes all sit near a tick is the interrupt's;
    # NEGATIVE: one also written far from it is the operation's
    w2 = {"ticks": [0.010, 0.030],
          "times": {1: [0.0101, 0.0301], 2: [0.001, 0.0102], 3: None}}
    ok &= isr_cells(w2, {1, 2, 3}) == {1}      # 1: at BOTH ticks; 2: also far; 3: a loop
    ok &= isr_cells({"ticks": [], "times": {1: [0.0]}}, {1}) == set()
    print("selftest:", "GREEN" if ok else "RED")
    return 0 if ok else 1


def main():
    if "--selftest" in sys.argv:
        return selftest()
    nm = names()
    res = {"ref": run(REF, 8.0), "zb": run(ZB, 8.0)}
    keys = [k for k, _ in CASES]
    # C1 positive and C2 closure -- refuse before scoring anything
    for side, r in res.items():
        if sorted(r) != list(range(len(CASES))):
            print(f"REFUSE: {side} tagged windows {sorted(r)}, expected "
                  f"0..{len(CASES) - 1}")
            return 2
        pos = r[keys.index("pos")]
        if MARK + 1 not in pos["cells"]:
            print(f"REFUSE: {side}: the positive control did not record $E001 "
                  f"-- the band watchpoint is not seeing writes")
            return 2
    ctl = {s: split_stack(res[s][0])[0] for s in res}
    global ISRSIG
    ISRSIG = {}
    for s in res:
        w = res[s][keys.index("isr")]
        c, _ = split_stack(w)
        if not w.get("ticks"):
            print(f"REFUSE: {s}: the isr control saw no interrupt")
            return 2
        ISRSIG[s] = isr_cells(w, c)
        print(f"interrupt signature ({s}, {len(ISRSIG[s])} cells): {fmt(ISRSIG[s], nm)}")
    print("window duration ms / interrupts inside, per case:")
    for i, (k, _op) in enumerate(CASES):
        print(f"  {k:8} " + "  ".join(
            f"{s} {res[s][i].get('dt', float('nan')) * 1e3:8.3f} ms "
            f"int={res[s][i].get('nint', '?')}" for s in res))
    print(f"background (ctl, excluded from every op): "
          f"ref {len(ctl['ref'])} cells, zb {len(ctl['zb'])} cells")
    print(f"  ref: {fmt(ctl['ref'], nm)}")
    print(f"  zb : {fmt(ctl['zb'], nm)}\n")
    print(f"{'op':8} {'ref std':>7} {'ref own':>7} {'zb std':>6} {'zb own':>6}  shared-std")
    econ = []
    for i, (k, op) in enumerate(CASES):
        if k in ("ctl", "pos", "isr"):
            continue
        row = {}
        for s in res:
            win = res[s][i]
            if not win.get("closed"):
                row[s] = None
                continue
            c, _st = split_stack(win)
            row[s] = c - ctl[s] - ISRSIG[s]
        if row["ref"] is None or row["zb"] is None:
            print(f"{k:8} UNCLOSED on " + " ".join(s for s in row if row[s] is None))
            continue
        rs = {a for a in row["ref"] if a >= STD}
        ro = row["ref"] - rs
        zs = {a for a in row["zb"] if a >= STD}
        zo = row["zb"] - zs
        econ.append((k, len(row["ref"]), len(row["zb"])))
        print(f"{k:8} {len(rs):7} {len(ro):7} {len(zs):6} {len(zo):6}  {len(rs & zs)}")
        print(f"   ref std only: {fmt(rs - zs, nm)}")
        print(f"   zb  std only: {fmt(zs - rs, nm)}")
        print(f"   ref below $F380: {fmt(ro, nm)}")
        print(f"   zb  below $F380: {fmt(zo, nm)}")
    fewer = sum(1 for _k, r, z in econ if r < z)
    print(f"\nECONOMY (distinct non-stack cells, background removed): the reference "
          f"writes FEWER on {fewer} of {len(econ)} ops; "
          f"totals ref {sum(r for _k, r, _z in econ)} vs zb {sum(z for _k, _r, z in econ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
