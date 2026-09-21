#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-MERGEWIN: does main's ASCII line path write into disk's SECTOR_BUF window?

🔴 THE QUESTION STEP 11 TURNS ON, AND IT IS ABOUT OUR OWN TREE, NOT THE
REFERENCE. §6.6ap established the SHAPE: the reference's crossing is once per
file and the transfer above it is per byte, so `ascii_read_lines` and the
tokeniser stay in main. What that shape requires of US is something the
reference never has to worry about: **our `disk.rom` borrows main's RAM for its
sector buffer.** `SECTOR_BUF` is `$E2A0..$E49F`, and §6.6al measured 510 of
those 512 bytes as occupied by MAIN cells — `STRSCR`'s body, `SH_*`, the
temp-descriptor pool, the PAINT span stack.

A seam finer than once-per-file means the disk side's sector buffer must survive
main running in between. For step 11 the code that runs in between is exactly
`mrg_storeline` — tokenise the line, store it — plus the handful of instructions
around it. **If that path writes anywhere into `$E2A0..$E49F`, step 11 is
blocked on RAM exactly as step 10 is, and the "unblocked" verdict of §6.6ap
covers the call-back objection only.**

⚠️ §6.6q FILED THIS HAZARD AND NOTHING HAS RETIRED IT. `TODO.md` says so in as
many words — *"no suite runs `PAINT` then `LOAD`"*. This measures the half of it
step 11 needs, on the path step 11 would create, before any code is written.

🔬 THE METHOD. A `write_mem` watchpoint over the window, ARMED at
`mrg_storeline`'s entry and DISARMED at `arl_getbyte`'s entry. Those two
breakpoints bracket precisely "main is running between two byte reads": the
loop is getbyte … getbyte … CR → `mrg_storeline` → `arl_newline` →
`arl_charloop` → `arl_getbyte`. Every address written inside that bracket is an
address the disk side's sector buffer could not survive.

🔴 SILENCE IS NOT EVIDENCE, SO THERE IS A SECOND WATCHPOINT. An empty window
band and a misconfigured watchpoint print the same thing. A CONTROL band over
`TOKBUF` — which `mrg_storeline` must write, it is where the tokenised line goes
— is armed and disarmed by the SAME two breakpoints and MUST fire. If the
control is silent the run is withheld: the arming is wrong, not the tree clean.

🔴 AND THE ARM PROVES ITS OWN SUBJECT RAN. The fixture's lines increment `A` and
its last line prints `A`, so a `MERGE` that errored, or one whose file was
short, contributes no row at all rather than a quiet clean window.

CLEAN ROOM: not applicable in the usual direction — every address here is OUR
OWN (`build/basic-reloc.sym`), the machine is our own build, and no reference
ROM is involved at any point.

--- THE PREDICTION, STATED BEFORE THE RUN ------------------------------------
  P1 the CONTROL band fires (without this nothing below is readable).
  P2 the WINDOW band stays silent: tokenising and storing a program line
     evaluates no expression, so it should touch neither the temp-descriptor
     pool nor the string scratch, and it is not graphics.
  ⚠️ P2 is the comfortable answer and therefore the one to distrust. The whole
  point of running this is that `mrg_storeline` reaches `dispatch_line`, whose
  surface nobody has walked for this question.
"""
from __future__ import annotations

import os
import re
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import probe_tmp                                              # noqa: E402,F401
import omsx_repl                                              # noqa: E402
import loadrun_probe as LR                                    # noqa: E402
import mergeshape_probe as MS                                 # noqa: E402

ZB = "C-BIOS_MSX1_EU_BASIC_DISK"
RESET = ("", "SCREEN 0", "CLOSE", "NEW", "CLS")
BOOT, STEP, CAP_GAP = 14.0, 25.0, 8.0
SYM = os.path.join(REPO, "build", "basic-reloc.sym")

# disk.rom's TWO buffers, as `disk/equates.inc` binds them. Both must survive,
# not just the data one: `fat_io_getbyte` re-reads a FAT sector into the
# metadata buffer whenever the stream crosses a cluster boundary, so a path that
# clobbers `WBUF` breaks the transfer just as surely as one that clobbers
# `SECTOR_BUF`. ⚠️ `WBUF $E560..$E75F` sits ON TOP of main's own
# `FSECTOR_BUF $E5C0` and the cassette buffers -- designed aliasing between
# contexts that were mutually exclusive until this seam is cut.
WIN_LO, WIN_HI = 0xE2A0, 0xE49F          # SECTOR_BUF / FAT_DBUF
WIN2_LO, WIN2_HI = 0xE560, 0xE75F        # WBUF / FAT_MBUF
# the control: where a tokenised line lands. `mrg_storeline` cannot avoid it.
CTL_LO, CTL_HI = 0xEC00, 0xEC7F
LINES = 40
# 🔴 A FLOOR IS NOT A SURFACE. `N A=A+1` tokenises without a string literal, a
# DATA item or a long body, so the addresses it touches are the addresses the
# SIMPLEST line touches. `--rich` runs the same bracket over lines that carry a
# quoted string, a REM tail and a multi-statement body, which is what a real
# merged program looks like. Both are reported as what they are: a measurement
# of THIS fixture, never of "the line path".
RICH = True
CAP = 400


def read_sym(path: str) -> dict:
    """pasmo's symbol file -> {NAME: addr}. Refuses an empty parse."""
    out = {}
    for ln in open(path):
        m = re.match(r"^(\S+)\s+EQU\s+0*([0-9A-Fa-f]+)H\s*$", ln.strip())
        if m:
            out[m.group(1)] = int(m.group(2), 16)
    if not out:
        raise ValueError("no symbols parsed from %s" % path)
    return out


def need(sym: dict, *names) -> list:
    missing = [n for n in names if n not in sym]
    if missing:
        raise KeyError("absent from the symbol file: %s" % ", ".join(missing))
    return [sym[n] for n in names]


TCL = r'''
set ::win 0
set ::ctl_hits 0
set ::win_hits 0
set ::logged 0
set ::capped 0
set ::arm 0
set ::dis 0
set ::fin 0
debug set_bp @ARM@ {} { set ::win 1 ; incr ::arm }
debug set_bp @DIS@ {} { set ::win 0 ; incr ::dis }
# 🔴 ROUND 1 LEAKED, AND THE `arm` / `dis` COUNTS ARE WHAT SHOWED IT. The
# bracket opens at `mrg_storeline` and closes at the NEXT `arl_getbyte` -- but
# after the LAST line there is no next getbyte, so `win` stayed 1 through the
# `RUN` that proves the merge worked, and RUN's own string traffic was being
# counted as the line path's. A third breakpoint at `arl_ok`, the reader's
# success exit, closes the bracket for good.
debug set_bp @END@ {} { set ::win 0 ; incr ::fin }
debug set_watchpoint write_mem {@WLO@ @WHI@} {} {
    if {!$::win} { return }
    incr ::win_hits
    if {$::logged >= @CAP@} { set ::capped 1 ; return }
    incr ::logged
    set k $::wp_last_address
    if {[info exists ::hit($k)]} { incr ::hit($k) } else { set ::hit($k) 1 }
}
debug set_watchpoint write_mem {@W2LO@ @W2HI@} {} {
    if {!$::win} { return }
    incr ::win_hits
    if {$::logged >= @CAP@} { set ::capped 1 ; return }
    incr ::logged
    set k $::wp_last_address
    if {[info exists ::hit($k)]} { incr ::hit($k) } else { set ::hit($k) 1 }
}
debug set_watchpoint write_mem {@CLO@ @CHI@} {} {
    if {!$::win} { return }
    incr ::ctl_hits
}
proc __dump {} {
    set f [open {@OUT@} w]
    puts $f "META arm $::arm dis $::dis fin $::fin win $::win_hits ctl $::ctl_hits logged $::logged capped $::capped"
    foreach k [array names ::hit] { puts $f "H $k $::hit($k)" }
    close $f
    after time 1 __dump
}
after time 1 __dump
'''


def prologue(out_path, arm, dis, end):
    t = TCL
    for k, v in (("@OUT@", out_path), ("@ARM@", str(arm)), ("@DIS@", str(dis)),
                 ("@END@", str(end)),
                 ("@WLO@", str(WIN_LO)), ("@WHI@", str(WIN_HI)),
                 ("@W2LO@", str(WIN2_LO)), ("@W2HI@", str(WIN2_HI)),
                 ("@CLO@", str(CTL_LO)), ("@CHI@", str(CTL_HI)),
                 ("@CAP@", str(CAP))):
        t = t.replace(k, v)
    return (t,)


def parse(path: str) -> tuple:
    meta, hits = {}, {}
    try:
        for ln in open(path):
            p = ln.split()
            if p and p[0] == "META":
                it = iter(p[1:])
                meta = {k: int(v) for k, v in zip(it, it)}
            elif p and p[0] == "H" and len(p) >= 3:
                hits[int(p[1])] = int(p[2])
    except (OSError, ValueError):
        pass
    return meta, hits


def runs(addrs) -> list:
    """Contiguous [lo, hi] runs over a sorted address list."""
    out = []
    for a in sorted(addrs):
        if out and a == out[-1][1] + 1:
            out[-1][1] = a
        else:
            out.append([a, a])
    return [tuple(r) for r in out]


def verdict(meta: dict, hits: dict) -> str:
    """-> 'withheld' | 'clean' | 'dirty'. The control decides readability."""
    if not meta or not meta.get("arm"):
        return "withheld"
    if not meta.get("ctl"):
        return "withheld"
    return "dirty" if hits else "clean"


def selftest() -> int:
    ok = {}
    sym = read_sym(SYM)
    ok["A1 the symbol file parses and carries our own labels"] = all(
        n in sym for n in ("mrg_storeline", "arl_getbyte", "ascii_read_lines"))
    try:
        need(sym, "mrg_storeline", "no_such_label_here")
        ok["A2 a missing label REFUSES"] = False
    except KeyError:
        ok["A2 a missing label REFUSES"] = True
    try:
        read_sym(os.devnull)
        ok["A3 NEGATIVE: an empty symbol file REFUSES"] = False
    except ValueError:
        ok["A3 NEGATIVE: an empty symbol file REFUSES"] = True

    ok["A4 runs() coalesces adjacency and splits a gap"] = (
        runs([5, 6, 7, 20]) == [(5, 7), (20, 20)])
    ok["A5 runs() of nothing is nothing"] = runs([]) == []

    ok["A6 no control hits -> WITHHELD, never 'clean'"] = (
        verdict({"arm": 3, "ctl": 0}, {}) == "withheld")
    ok["A7 never armed -> WITHHELD"] = (
        verdict({"arm": 0, "ctl": 9}, {}) == "withheld")
    ok["A8 armed + control fired + no window hits -> clean"] = (
        verdict({"arm": 3, "ctl": 9}, {}) == "clean")
    ok["A9 NEGATIVE: one window hit -> dirty, not clean"] = (
        verdict({"arm": 3, "ctl": 9}, {0xE300: 1}) == "dirty")
    ok["A10 NEGATIVE: an empty meta is WITHHELD, not clean"] = (
        verdict({}, {}) == "withheld")

    ok["A11 the window is disk's SECTOR_BUF, 512 bytes"] = (
        WIN_HI - WIN_LO + 1 == 512)
    ok["A12 the control band overlaps NEITHER window"] = (
        (CTL_LO > WIN_HI or CTL_HI < WIN_LO) and
        (CTL_LO > WIN2_HI or CTL_HI < WIN2_LO))
    ok["A14 the two windows are disjoint, so a hit belongs to one"] = (
        WIN2_LO > WIN_HI)
    ok["A13 the fixture has the line count it claims"] = (
        MS.ascii_program(LINES).count(b"\r\n") == LINES + 1)
    r = rich_program(3)
    ok["A15 the rich fixture still counts its own lines"] = (
        r.count(b"\r\n") == 4 and r.endswith(b"\x1a"))
    ok["A16 NEGATIVE: the rich fixture is NOT the plain one"] = (
        r != MS.ascii_program(3))
    ok["A17 the rich fixture carries a quoted string and a REM"] = (
        b'"' in r and b"REM" in r)

    for k, v in ok.items():
        print(f"  {'PASS' if v else '🔴 FAIL'}  {k}")
    bad = [k for k, v in ok.items() if not v]
    print(f"selftest: {'🔴 RED' if bad else 'GREEN'} "
          f"({len(ok) - len(bad)}/{len(ok)})")
    return 1 if bad else 0


def rich_program(n: int) -> bytes:
    """The same self-counting shape, with the line SHAPES a real program has."""
    if n < 1:
        raise ValueError("a fixture with no lines cannot prove itself")
    recs = []
    for i in range(1, n + 1):
        recs.append(b'%d A=A+1:B$="PAYLOAD%02d":C=LEN(B$):REM tail text here'
                    % (10 * i, i % 100))
    recs.append(b"9000 PRINT CHR$(%d)+CHR$(%d);A" % MS.MARK)
    return b"\r\n".join(recs) + b"\r\n\x1a"


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()

    sym = read_sym(SYM)
    arm, dis, end = need(sym, "mrg_storeline", "arl_getbyte", "arl_ok")
    print(f"armed at mrg_storeline ${arm:04X}, disarmed at arl_getbyte "
          f"${dis:04X}, closed for good at arl_ok ${end:04X} -- the bracket "
          "is 'main between two byte reads', and nothing after the merge")
    print(f"windows ${WIN_LO:04X}..${WIN_HI:04X} (SECTOR_BUF/FAT_DBUF) and "
          f"${WIN2_LO:04X}..${WIN2_HI:04X} (WBUF/FAT_MBUF)")
    print(f"control ${CTL_LO:04X}..${CTL_HI:04X} (TOKBUF) -- it MUST fire")

    tmpd = tempfile.mkdtemp(prefix="mergewin-")
    seeded, _n = LR.seed(ZB, RESET, tmpd, "mw")
    rich = "--rich" in sys.argv
    fixture = rich_program(LINES) if rich else MS.ascii_program(LINES)
    print(f"fixture: {'RICH' if rich else 'plain'}, {len(fixture)} B")
    dsk, _sizes, _per = LR.build(seeded, tmpd, "mw",
                                 extra={"A       BAS": fixture})

    fd, out = tempfile.mkstemp(prefix="mergewin-", suffix=".txt")
    os.close(fd)
    caps = omsx_repl.run_cases(ZB, [("direct", ['MERGE"A.BAS"', "RUN"])],
                               batch=False, reset=RESET, boot=BOOT, step=STEP,
                               cap_gap=CAP_GAP, diska=dsk, capture="screen",
                               prologue=prologue(out, arm, dis, end))
    screen = (caps or [None])[0] or ""
    fence = MS.read_fence(screen)
    meta, hits = parse(out)
    if os.path.exists(out):
        os.unlink(out)

    print(f"\nself-proof: MERGE read {fence} line(s), fixture has {LINES}")
    if fence != LINES:
        print("🔴 THE MERGE DID NOT DO ITS JOB. A clean window from a MERGE "
              "that never ran is not evidence about the path. Withheld.")
        return 1

    print(f"meta: {meta}")
    v = verdict(meta, hits)
    if v == "withheld":
        print("🔴 WITHHELD: the bracket never armed, or the CONTROL band never "
              "fired. A silent window band is then the watchpoint, not the "
              "tree. Nothing is concluded.")
        return 1

    print(f"\n=== WRITES INTO disk's SECTOR_BUF WINDOW, between byte reads ===")
    if v == "clean":
        print("  (none)")
        print("\n🟢 CLEAN: across "
              f"{meta['arm']} bracketed intervals with the control firing "
              f"{meta['ctl']} time(s), main's ASCII line path wrote NOTHING "
              "into EITHER disk buffer window. A disk-side sector buffer there "
              "would survive the tokeniser.")
    else:
        for lo, hi in runs(hits):
            n = sum(hits[a] for a in range(lo, hi + 1) if a in hits)
            print(f"  ${lo:04X}..${hi:04X}  {hi - lo + 1:4d} B, "
                  f"{n} write(s)")
        print(f"\n🔴 DIRTY: {len(hits)} distinct address(es) in the window are "
              "written between byte reads. A disk-side sector buffer there "
              "would be destroyed mid-transfer -- step 11 is blocked on RAM "
              "exactly as step 10 is.")
    if meta.get("capped"):
        print("  ⚠️ the per-address log CAPPED: the run count above is a "
              "floor, the address SET is not affected")

    print("\n--- PREDICTIONS SCORED ---")
    print(f"  P1 the control band fires: "
          f"{'HIT' if meta.get('ctl') else '🔴 MISS'} ({meta.get('ctl')} hits)")
    print(f"  P2 the window band stays silent: "
          f"{'HIT' if v == 'clean' else '🔴 MISS'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
