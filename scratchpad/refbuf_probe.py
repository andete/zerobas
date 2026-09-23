#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-REFBUF -- how many sector buffers does the REFERENCE use, and where?

D-ALIASBITE: on zerobas a disk verb (`KILL`, `NAME`, `DSKF`, ...) between two
reads of an open channel corrupts the channel, because main's `FSECTOR_BUF`
and disk's `WBUF` partly overlap. The reference does NOT have the bug
(scratchpad/aliaswrite_ref.out). Three remedies are on the table -- (a) two
buffers at the same address, (b) one shared buffer, (c) two DISJOINT buffers --
and the question is WHICH ONE THE REFERENCE'S ARCHITECTURE ACTUALLY IS.

🎯 THE DISCRIMINATOR IS A WRITE-ADDRESS HISTOGRAM OVER ALL OF RAM, taken in
POKE-bracketed windows around (1) OPEN, (3) the first read, (5) the verb,
(7) the second read and (9) CLOSE. A 512-byte contiguous run of writes is a
sector being staged; the addresses of those runs, window by window, say whether
the channel's staging and the verb's staging are one region, overlapping
regions, or disjoint ones -- and window 7 says whether the channel RE-READS its
sector after a verb (a cache) or serves the next bytes from somewhere the verb
never touched (a per-channel record buffer).

🔴 CLEAN ROOM (disk/docs/expansion-protocol.md §7, §8.5). This probe records
WRITE ADDRESSES, the writer's REGION (never its PC), the marker cell's values,
and four documented work-area words (MEMSIZ/STKTOP/BOTTOM/HIMEM). It reads no
ROM byte, dumps no RAM span, follows no hook, and never decodes the contents
of the RAM-resident code clusters (§8.5); an address inside one is reported as
an address.

🔴 CONTROLS, in the same run:
  * the `no-verb` arm (`X=1` in window 5) MUST show NO disk-region writes in
    windows 5 and 7 -- otherwise the bracket does not isolate the verb;
  * the `DSKI$` arm MUST stage a 512 B run in window 5 -- otherwise the
    watchpoint is blind. NOT `KILL`: on the reference KILL finds its directory
    sector cached and stages nothing, which is a FINDING (measured 09-23);
  * the marker cell's whole write history is logged with its writer region and
    the run REFUSES unless the sequence is exactly the program's own
    [[a-marker-cell-is-a-claim-nobody-else-writes-it]];
  * `--machine C-BIOS_MSX1_EU_REPACK_DISK` points the identical apparatus at
    zerobas, where the answer is KNOWN (KILL writes $E5C0.. inside main's
    FSECTOR_BUF): an apparatus that cannot see that has no standing on the
    reference.

⚠️ `run_gap`, not `cap_gap` -- see aliasbite_probe.py's note and
tests/test_capture_budget.py.

    python3 -u scratchpad/refbuf_probe.py [--selftest] [--machine M]
        [--arms a,b,..] [--side in|out|both] [--shape warm|cold] [--read2 N]

MEASURED 2026-09-23 (outputs: scratchpad/refbuf_zb_in.out, refbuf_ref_in.out
[warm], refbuf_ref_cold_in.out, refbuf_ref_out.out, refbuf_ref_r255.out,
refbuf_ref_open2.out): the reference keeps each channel's bytes in a PRIVATE
256 B record buffer inside its 267 B pool block, stages file data in a disk-
side buffer at $ED95..$EF94 (an identity cache, re-read when another channel
displaces it) and stages directory/raw sectors in a SEPARATE buffer at
$EB95..$ED94 -- the two never overlap, and no verb writes the data buffer.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp  # noqa: E402,F401  -- module level, sets tempfile.tempdir
import omsx_repl  # noqa: E402

REF = "National_CF-3300"
ZB = "C-BIOS_MSX1_EU_REPACK_DISK"
SRC_DSK = os.path.join(ROOT, "disk", "test720.dsk")
# 🔴 NOT $D000: the machine writes every $xx00 boundary at boot and on
# zerobas 32 times per disk program (scratchpad/cellpriv.out); $CFFE measured
# quiet (scratchpad/findquiet.out) and is RE-VERIFIED per run below.
PHASE = 0xCFFE
WATCH_LO, WATCH_HI = 0x8000, 0xFFFF
SNAP = 90          # the program pokes this BEFORE its CLEAR: log boot geometry
DONE = 99
# the program's own marker sequence; anything else REFUSES the run
SEQ_IN = [SNAP, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, DONE]
WINDOWS = {1: "OPEN", 3: "read #1 (4 B)", 5: "VERB", 7: "read #2",
           9: "CLOSE"}
WINDOWS_OUT = {1: "OPEN", 3: "PRINT# #1", 5: "VERB", 7: "PRINT# #2",
               9: "CLOSE"}

# 🔴 THE PRELUDE THE REFERENCE NEEDS: it boots SCREEN 1 and `reset` in
# boot-per-case mode is typed, so these are DIRECT lines.
PRELUDE = ["", "SCREEN 0", "NEW", "CLS"]

HEAD = [
    f"0 POKE&H{PHASE:04X},{SNAP}",
    # BASIC's ceiling well below the marker; 600 B of string space because a
    # 255 B INPUT$ result must fit (200 raised ERR 14 and REFUSED the r255 run)
    "1 CLEAR 600,&HBFFF",
    "5 MAXFILES=2",
    '10 OPEN"Y.DAT"FOR OUTPUT AS#1',   # the victim KILL/NAME act on
    '15 PRINT#1,"X"',
    "17 CLOSE#1",
    '20 OPEN"Z.DAT"FOR OUTPUT AS#1',
    '30 PRINT#1,"ABCDEFGHIJKLMNOP"',
    "40 CLOSE#1",
    "45 ON ERROR GOTO 199",
]


def mk(ph, stmt):
    return [f"{ph * 10 + 50} POKE&H{PHASE:04X},{ph}", f"{ph * 10 + 52} {stmt}",
            f"{ph * 10 + 54} POKE&H{PHASE:04X},{ph + 1}"]


# 🔴 WARM vs COLD. In the `warm` shape the channel reads back Z.DAT, which
# the HEAD has JUST written -- on a caching disk system every sector the
# windows need is already in RAM and NO window stages anything (measured on
# the reference: scratchpad/refbuf_ref_in.out). The `cold` shape reads
# TEST.BIN, a 2048 B file on the fixture that nothing has touched since boot,
# so window 3 MUST fetch a data sector from the medium; that fetch displaces
# whatever a shared buffer held, which is what makes windows 5 and 7 speak.
COLD_FILE = "TEST.BIN"


def program(verb, side, shape="cold", read2=4):
    if side == "in":
        f = "Z.DAT" if shape == "warm" else COLD_FILE
        body = (mk(1, f'OPEN"{f}"FOR INPUT AS#1') + mk(3, "A$=INPUT$(4,#1)")
                + mk(5, verb) + mk(7, f"B$=INPUT$({read2},#1)") + mk(9, "CLOSE#1"))
    else:
        body = (mk(1, 'OPEN"W.DAT"FOR OUTPUT AS#1')
                + mk(3, 'PRINT#1,"AAAABBBBCCCCDDDD"') + mk(5, verb)
                + mk(7, 'PRINT#1,"EEEEFFFFGGGGHHHH"') + mk(9, "CLOSE#1"))
    return HEAD + body + [
        f"150 POKE&H{PHASE:04X},{DONE}",
        "160 END",
        f'199 PRINTCHR$(91);"E";ERR;CHR$(93):POKE&H{PHASE:04X},98',
        "RUN",
    ]


ARMS = [("no-verb", "X=1"),                     # NEGATIVE: windows 5/7 quiet
        ("KILL", 'KILL"Y.DAT"'),                # the D-ALIASBITE subject
        # 🔴 THE POSITIVE CONTROL IS A FORCED RAW READ, NOT KILL. On a caching
        # reference KILL may find its directory sector already in RAM and stage
        # nothing, which is a finding and not a blind watchpoint. DSKI$(0,0)
        # cannot be served from any cache: 512 bytes MUST land in RAM.
        ("DSKI$", "Q$=DSKI$(0,0)"),
        # displace BOTH disk-side buffers seen so far, then see what a read
        # that crosses the channel's 256 B record boundary has to fetch
        ("DSKI$x2", "Q$=DSKI$(0,0):R$=DSKI$(0,1)"),
        ("FILES", "FILES"),                     # 7 directory sectors in a row
        # a SECOND channel's data read: does it displace channel 1's sector
        # from the data buffer, and does channel 1's refill then re-read it?
        ("OPEN2", 'OPEN"HI.TXT"FOR INPUT AS#2:C$=INPUT$(4,#2):CLOSE#2'),
        ("DSKF", "X=DSKF(0)"),
        ("NAME", 'NAME"Y.DAT"AS"V.DAT"')]

TCL = r'''
set ::lf [open "@LOG@" w]
set ::win 0
set ::wp ""
set ::nwrites 0
array set ::hit {}
proc __region {} {
    set pc [reg PC]
    set p [expr {$pc >> 14}]
    if {$p >= 2} { return "RAM" }
    set s [get_selected_slot $p]
    set pri [lindex $s 0]
    set sec [lindex $s 1]
    if {$sec eq ""} { set sec 0 }
    if {$pri == 0} { if {$p == 0} { return "MAIN-P0" } else { return "MAIN-P1" } }
    if {$pri == 3 && $sec == 1} { return "DISK" }
    return "SLOT$pri-$sec"
}
proc __rec {} {
    incr ::nwrites
    set k "$::win,[__region],$::wp_last_address"
    if {[info exists ::hit($k)]} { incr ::hit($k) } else { set ::hit($k) 1 }
}
proc __open {ph} {
    set ::win $ph
    if {$::wp eq ""} {
        set ::wp [debug set_watchpoint write_mem {@LO@ @HI@} {} {__rec}]
    }
}
proc __close {} {
    if {$::wp ne ""} { debug remove_watchpoint $::wp ; set ::wp "" }
    set ::win 0
}
proc __word {a} {
    expr {[debug read memory $a] + 256 * [debug read memory [expr {$a + 1}]]}
}
debug set_watchpoint write_mem @PH@ {} {
    set v $::wp_last_value
    puts $::lf "PH $v [__region] [machine_info time] SP=[reg SP]"
    if {$v == @SNAP@} {
        puts $::lf "GEOM MEMSIZ=[__word 0xF672] STKTOP=[__word 0xF674] BOTTOM=[__word 0xFC48] HIMEM=[__word 0xFC4A]"
    } elseif {$v == @DONE@ || $v == 98} {
        __close
        puts $::lf "DONE $v"
    } elseif {$v % 2 == 1} {
        __open $v
    } else {
        __close
    }
    flush $::lf
}
proc __dump {} {
    set f [open "@OUT@" w]
    puts $f "N $::nwrites"
    foreach k [array names ::hit] { puts $f "H $k $::hit($k)" }
    close $f
    after time 1 __dump
}
after time 1 __dump
'''


def prologue(log, out):
    t = TCL
    for k, v in (("@LOG@", log), ("@OUT@", out), ("@PH@", str(PHASE)),
                 ("@LO@", str(WATCH_LO)), ("@HI@", str(WATCH_HI)),
                 ("@SNAP@", str(SNAP)), ("@DONE@", str(DONE))):
        t = t.replace(k, v)
    return (t,)


# --- host-side analysis --------------------------------------------------

def parse(log_path, out_path):
    """(phases, geom, hits) or None when a file is missing.

    phases: list of (value, region, time, sp); hits: {(win, region, addr): n}
    """
    try:
        log = open(log_path).read()
        out = open(out_path).read()
    except OSError:
        return None
    phases = []
    geom = {}
    for ln in log.splitlines():
        m = re.match(r"PH (\d+) (\S+) ([\d.]+) SP=(\d+)", ln)
        if m:
            phases.append((int(m.group(1)), m.group(2), float(m.group(3)),
                           int(m.group(4))))
        m = re.match(r"GEOM (.*)", ln)
        if m:
            geom = {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", m.group(1))}
    hits = {}
    for ln in out.splitlines():
        p = ln.split()
        if p and p[0] == "H" and len(p) == 3:
            w, reg, a = p[1].split(",")
            hits[(int(w), reg, int(a))] = int(p[2])
    return phases, geom, hits


def marker_ok(phases, seq):
    """The marker cell's history must be EXACTLY the program's own sequence.

    Writes BEFORE the program's first value are boot traffic and are reported,
    not refused: the gate only opens on the program's own values. Anything
    after the first program value that is not the next expected value REFUSES.
    """
    vals = [v for v, _r, _t, _sp in phases]
    if seq[0] not in vals:
        return False, "the program's first marker never arrived"
    tail = vals[vals.index(seq[0]):]
    if tail != seq:
        return False, f"marker history {tail} is not the program's {seq}"
    return True, ""


def runs(addrs):
    """Contiguous runs [(start, length)] of a sorted iterable of addresses."""
    out = []
    for a in sorted(addrs):
        if out and out[-1][0] + out[-1][1] == a:
            out[-1] = (out[-1][0], out[-1][1] + 1)
        else:
            out.append((a, 1))
    return out


def window(hits, w):
    """{addr: {region: n}} for one window."""
    d = {}
    for (ww, reg, a), n in hits.items():
        if ww == w:
            d.setdefault(a, {})[reg] = d.get(a, {}).get(reg, 0) + n
    return d


def stackish(run, sp):
    """A run that ends within 4 B below the SP recorded at window open is
    the stack (SP at open is the TOP of what the window can push)."""
    start, n = run
    return sp - 4 <= start + n <= sp + 2 and n <= 512


def describe(hits, w, sp, minlen=4):
    d = window(hits, w)
    lines = []
    for start, n in runs(d):
        regs = {}
        tot = 0
        for a in range(start, start + n):
            for r, c in d[a].items():
                regs[r] = regs.get(r, 0) + c
                tot += c
        tag = ""
        if stackish((start, n), sp):
            tag = " STACK"
        elif n in (512, 256, 128):
            tag = f" <-- {n} B"
        if n >= minlen or "DISK" in regs or "RAM" in regs:
            rs = " ".join(f"{r}={c}" for r, c in sorted(regs.items()))
            lines.append(f"      ${start:04X}..${start + n - 1:04X} "
                         f"({n:3d} B) x{tot:<5d} {rs}{tag}")
    return lines, d


def sector_runs(hits, w, sp):
    """Runs >= 256 B in window w that are not the stack, with their region."""
    d = window(hits, w)
    out = []
    for start, n in runs(d):
        if n >= 256 and not stackish((start, n), sp):
            regs = set()
            for a in range(start, start + n):
                regs |= set(d[a])
            out.append((start, n, tuple(sorted(regs))))
    return out


def overlap(r1, r2):
    a0, a1 = r1[0], r1[0] + r1[1]
    b0, b1 = r2[0], r2[0] + r2[1]
    return max(0, min(a1, b1) - max(a0, b0))


def relation(chan, verb):
    """How the channel's sector-sized runs relate to the verb's."""
    if not chan:
        return "NO CHANNEL STAGING SEEN"
    if not verb:
        return "VERB STAGES NOTHING sector-sized"
    same = [c for c in chan for v in verb if c[0] == v[0] and c[1] == v[1]]
    if same:
        return f"SAME REGION: {', '.join('$%04X' % c[0] for c in same)}"
    ov = [(c, v, overlap(c, v)) for c in chan for v in verb if overlap(c, v)]
    if ov:
        return "PARTIAL OVERLAP: " + ", ".join(
            f"${c[0]:04X}+{c[1]} vs ${v[0]:04X}+{v[1]} share {o} B" for c, v, o in ov)
    return "DISJOINT"


def selftest():
    fails = 0

    def arm(label, cond):
        nonlocal fails
        if not cond:
            print(f"  selftest: FAIL {label}")
            fails += 1

    arm("runs merges contiguous, splits gaps",
        runs([1, 2, 3, 5, 6]) == [(1, 3), (5, 2)])
    arm("runs of nothing is nothing", runs([]) == [])
    ph = [(v, "MAIN-P1", 1.0, 0xBF00) for v in SEQ_IN]
    arm("the program's own sequence is accepted", marker_ok(ph, SEQ_IN)[0])
    arm("boot writes BEFORE the first marker are tolerated",
        marker_ok([(15, "MAIN-P0", 0.1, 0)] + ph, SEQ_IN)[0])
    # 🔴 NEGATIVE: a foreign write inside the program's run REFUSES
    bad = ph[:3] + [(15, "MAIN-P0", 2.0, 0)] + ph[3:]
    arm("NEGATIVE: a foreign write mid-run REFUSES", not marker_ok(bad, SEQ_IN)[0])
    arm("NEGATIVE: a truncated run (no DONE) REFUSES",
        not marker_ok(ph[:-1], SEQ_IN)[0])
    arm("NEGATIVE: an empty history REFUSES", not marker_ok([], SEQ_IN)[0])
    hits = {(5, "DISK", a): 1 for a in range(0xE000, 0xE200)}
    hits.update({(3, "DISK", a): 1 for a in range(0xE000, 0xE200)})
    hits.update({(5, "RAM", a): 1 for a in range(0xBEF0, 0xBF00)})   # stack
    sr5 = sector_runs(hits, 5, 0xBF00)
    arm("a 512 B run is found", sr5 == [(0xE000, 512, ("DISK",))])
    arm("NEGATIVE: the stack run is not a sector",
        all(s[0] != 0xBEF0 for s in sr5))
    arm("NEGATIVE: an empty window has no sector runs",
        sector_runs(hits, 7, 0xBF00) == [])
    arm("same region", relation(sector_runs(hits, 3, 0xBF00), sr5).startswith("SAME"))
    arm("disjoint", relation([(0xD000, 512, ())], sr5) == "DISJOINT")
    arm("partial overlap", relation([(0xE100, 512, ())], sr5).startswith("PARTIAL"))
    arm("NEGATIVE: no channel staging is named, not 'DISJOINT'",
        relation([], sr5).startswith("NO CHANNEL"))
    arm("NEGATIVE: a missing file parses to None",
        parse("/nonexistent/a", "/nonexistent/b") is None)
    p = tempfile.mkstemp()[1]
    q = tempfile.mkstemp()[1]
    open(p, "w").write("PH 90 MAIN-P1 20.5 SP=48000\nGEOM MEMSIZ=1 STKTOP=2 BOTTOM=3 HIMEM=4\n")
    open(q, "w").write("N 7\nH 5,DISK,57344 3\n")
    r = parse(p, q)
    arm("parse reads phases, geometry and hits",
        r is not None and r[0] == [(90, "MAIN-P1", 20.5, 48000)]
        and r[1]["HIMEM"] == 4 and r[2] == {(5, "DISK", 57344): 3})
    print("  selftest: PASS" if not fails else f"  selftest: {fails} FAILURE(S)")
    return fails


def run(machine, label, prog, boot):
    tmp = tempfile.mkstemp(suffix=".dsk")[1]
    shutil.copyfile(SRC_DSK, tmp)          # never write the tracked fixture
    # 🔴 the label lands inside a Tcl string: `DSKI$x2` would read `$x2`
    safe = label.replace("$", "S")
    log = probe_tmp.tmp(f"refbuf_{safe}.log")
    out = probe_tmp.tmp(f"refbuf_{safe}.hits")
    pre = PRELUDE if machine != ZB else []
    scr = omsx_repl.run_cases(machine, [(label, pre + prog)], batch=False,
                              reset=(), boot=boot, step=3.0, cap_gap=2.5,
                              run_gap=60.0, timeout=900.0, diska=tmp,
                              prologue=prologue(log, out))
    r = parse(log, out)
    if r is not None and 98 in [v for v, _r, _t, _sp in r[0]]:
        m = re.search(r"\[E\s*(\d+)\s*\]", scr[0] or "")
        print(f"  the program hit ON ERROR: ERR {m.group(1) if m else '?'}")
    return r


def report(label, res, side):
    print(f"\n=== {label} ===")
    if res is None:
        print("  REFUSED: no log/hits file (the run produced nothing)")
        return None
    phases, geom, hits = res
    ok, why = marker_ok(phases, SEQ_IN)
    pre = [(v, r, t) for v, r, t, _ in phases if v not in SEQ_IN]
    if pre:
        print(f"  marker cell: {len(pre)} write(s) outside the program's set, "
              f"e.g. {pre[:4]}")
    if not ok:
        print(f"  REFUSED: {why}")
        print("  marker history: " + " ".join(f"{v}@{r}" for v, r, _, _ in phases))
        return None
    regs = {r for _v, r, _t, _sp in phases}
    print(f"  marker sequence intact; POKEs came from {sorted(regs)}")
    print("  geometry at line 0: " + " ".join(f"{k}=${v:04X}" for k, v in geom.items()))
    sps = {v: sp for v, _r, _t, sp in phases}
    names = WINDOWS if side == "in" else WINDOWS_OUT
    sec = {}
    for w, name in names.items():
        lines, d = describe(hits, w, sps.get(w, 0))
        nd = sum(1 for a in d if "DISK" in d[a])
        print(f"  window {w} [{name}]: {len(d)} cell(s) written, {nd} by DISK, "
              f"SP at open ${sps.get(w, 0):04X}")
        for ln in lines:
            print(ln)
        sec[w] = sector_runs(hits, w, sps.get(w, 0))
    return sec


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--machine", default=REF)
    ap.add_argument("--arms", default="no-verb,KILL")
    ap.add_argument("--side", default="in", choices=["in", "out", "both"])
    ap.add_argument("--shape", default="cold", choices=["warm", "cold"])
    ap.add_argument("--read2", type=int, default=4,
                    help="bytes for the second read; 255 (the byte-sized max) "
                         "crosses the 256 B record boundary after the first 4")
    a = ap.parse_args(argv)
    print("D-REFBUF: how many sector buffers does the reference use, and where?\n")
    if a.selftest:
        return 1 if selftest() else 0
    boot = 16.0 if a.machine != ZB else 8.0
    want = a.arms.split(",")
    if "no-verb" not in want:
        print("REFUSING: the no-verb control must be in every run")
        return 2
    arms = [(n, v) for n, v in ARMS if n in want]
    sides = ["in", "out"] if a.side == "both" else [a.side]
    verdict = {}
    for side in sides:
        for name, verb in arms:
            label = f"{side}-{a.shape}-{name}"
            if a.read2 != 4:
                label += f"-r{a.read2}"
            res = run(a.machine, label, program(verb, side, a.shape, a.read2), boot)
            verdict[label] = report(label, res, side)
    print("\n=== SECTOR-SIZED RUNS (>= 256 B, not the stack), per window ===")
    for label, sec in verdict.items():
        if sec is None:
            print(f"  {label}: REFUSED")
            continue
        for w, rs in sec.items():
            for s, n, regs in rs:
                print(f"  {label:14} w{w}: ${s:04X}..${s + n - 1:04X} ({n} B) {regs}")
    print("\n=== RELATION: channel staging (w1+w3) vs verb staging (w5) ===")
    for label, sec in verdict.items():
        if sec is None:
            continue
        chan = sec.get(1, []) + sec.get(3, [])
        print(f"  {label:14} {relation(chan, sec.get(5, []))}; "
              f"after the verb, window 7 stages {len(sec.get(7, []))} sector(s)")
    ctl = verdict.get(f"{sides[0]}-{a.shape}-no-verb")
    if ctl is not None and (ctl.get(5) or ctl.get(7)):
        print("\n🔴 INSTRUMENT FAULT: the no-verb control stages a sector in "
              "window 5 or 7 -- the bracket does not isolate the verb")
        return 2
    pos = verdict.get(f"{sides[0]}-{a.shape}-DSKI$")
    if pos is None:
        print("\n⚠️  no DSKI$ arm: the POSITIVE control is absent, so a window "
              "with no sector run is not evidence that nothing was staged")
    elif not pos.get(5):
        print("\n🔴 INSTRUMENT FAULT: DSKI$(0,0) staged no 512 B run in window "
              "5 -- the watchpoint is blind on this machine")
        return 2
    else:
        print("\n  positive control: DSKI$(0,0) staged "
              + ", ".join(f"${s:04X}+{n}" for s, n, _ in pos[5]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
