#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-RAMCODE: WHERE does the RAM-resident part of the protocol live, and who put it there?

§6.6y found that part of the crossing executes from RAM: eleven of the twelve
bytes of a third name copy at `$F5B3..$F5BD`, plus `$F5C2`, `$F5C4` and
`$F5CA..$F5CD`, are written by code whose PC is in pages 2-3 -- neither the disk
ROM page nor main ROM. No design in this project has assumed RAM-resident code,
so it needs locating and sizing before step 9 can be priced.

🎯 AN EXECUTION DETECTOR, NOT A DATA-ACCESS ONE. `disk/docs/openmsx-probing-
toolbox.md` §1 records the validated fact that a `read_mem` watchpoint fires on
the Z80 OPCODE FETCH as well as on data reads, and that PC at that moment is the
executing instruction. So `wp_last_address == PC` selects FETCHES and rejects
data reads: the addresses that survive are addresses being EXECUTED. The previous
probes recorded PC at data accesses, which only ever sampled instructions that
happened to touch the watched band; this samples execution itself.

🔴 THE CLEAN-ROOM LINE IS SHARPER HERE THAN ANYWHERE ELSE IN THIS ARC. Code sitting
in RAM is reference ROM content that has merely been RELOCATED -- reading its
bytes is reading the reference. This probe records an address RANGE, a SIZE, the
REGION of whoever wrote it and WHEN. It never reads a byte of it, never
disassembles it, never single-steps it. That restriction is why the output is
ranges and counts and nothing else.

🔴 CONTROLS. Two of them have a KNOWN ANSWER, which is what makes the rest
readable.
  K3   the `quiet` case never opens the window: the executed set must be EMPTY.
  K10  POSITIVE -- the detector must fire at all; silence is a misconfigured
       watchpoint, not "nothing executes in RAM".
  K18  🔑 KNOWN-EXECUTED -- `$FE5D` holds `F7` (a claimed cell, §6.6v) and every
       probe in this arc has watched it execute. It MUST appear in the executed
       set. If it does not, the detector is missing fetches.
  K19  🔑 KNOWN-DATA -- `$F864..$F870` is the file-name block the disk side READS
       (§6.6x) and nothing executes there. It must NOT appear. If it does, the
       `wp_last_address == PC` filter is passing data reads and every range below
       is inflated.
  K15  DETERMINISM -- two runs of one case must give an identical executed set.

Phase 2 then watches WRITES to the located range from reset, recording the
writer's region and the emulated time, which says whether the code is installed
at boot (an obligation a faithful `disk.rom` would inherit) or built per call.
"""
import argparse
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))

from selector_probe import pcregion                           # noqa: E402
from diskreads_probe import addr_runs                         # noqa: E402

REF = "National_CF-3300"
RESET = ("", "SCREEN 0", "CLOSE", "NEW", "CLS")
BOOT, STEP, CAP_GAP = 14.0, 30.0, 8.0

C_NULO = 0xFE5D
EXEC_LO, EXEC_HI = 0x8000, 0xFFFF      # pages 2-3: all RAM on this machine
HOOK_LO, HOOK_HI = 0xFD9A, 0xFFE7      # the published hook table
K18_ADDR = C_NULO                      # known to execute
K19_LO, K19_HI = 0xF864, 0xF870        # known to be data only (§6.6x)
CAP = 40000
ASCII_BAS = b"10 REM Z\r\n20 REM Z\r\n"


PHASE1 = r'''
set ::win 0
set ::fetches 0
set ::capped 0
array set ::x {}
debug set_bp @CELL@ {} { set ::win 1 }
debug set_bp [expr {@CELL@ + 4}] {} { set ::win 0 }
debug set_watchpoint read_mem {@LO@ @HI@} {} {
    if {!$::win} return
    # 🔑 FETCH, NOT DATA: the watchpoint fires on both, and only on a fetch does
    # the address being read equal PC.
    if {$::wp_last_address != [reg PC]} return
    incr ::fetches
    if {[array size ::x] >= @CAP@} { set ::capped 1 ; return }
    set a $::wp_last_address
    if {[info exists ::x($a)]} { incr ::x($a) } else { set ::x($a) 1 }
}
proc __dump {} {
    set f [open {@OUT@} w]
    puts $f "F $::fetches CAPPED $::capped DISTINCT [array size ::x]"
    foreach a [array names ::x] { puts $f "X $a $::x($a)" }
    close $f
    after time 1 __dump
}
after time 1 __dump
'''


PHASE2 = r'''
set ::n 0
set ::lf [open {@OUT@} w]
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
# 🔴 PIN THE CROSSING'S OWN TIME. "The writes happen at t=3.8, which looks like
# boot" is an inference; logging the time of the `$FE5D` entry turns it into a
# comparison. Without it the whole "installed at boot, not per call" reading
# rests on my assumption about when typing starts.
debug set_bp @CELL@ {} { puts $::lf "C [format %.4f [machine_info time]]" ; flush $::lf }
# 🔴 ALL FIVE CLUSTERS IN ONE RUN, NOT FIVE RUNS. Each watchpoint tags its own
# cluster, so the five ranges are watched under ONE boot -- which also means the
# install TIMES are directly comparable rather than being read off five separate
# timelines that only happen to start the same way.
@WATCHES@
'''


def run_phase1(tag, lines, dsk):
    import omsx_repl
    fd, out = tempfile.mkstemp(prefix="ramcode1-%s-" % tag, suffix=".txt")
    os.close(fd)
    t = PHASE1
    for k, v in (("@OUT@", out), ("@CELL@", str(C_NULO)), ("@LO@", str(EXEC_LO)),
                 ("@HI@", str(EXEC_HI)), ("@CAP@", str(CAP))):
        t = t.replace(k, v)
    omsx_repl.run_cases(REF, [("direct", lines)], batch=False, reset=RESET,
                        boot=BOOT, step=STEP, cap_gap=CAP_GAP, diska=dsk,
                        capture="screen", prologue=(t,))
    meta, ex = {}, {}
    try:
        for ln in open(out):
            p = ln.split()
            if not p:
                continue
            if p[0] == "F" and len(p) >= 6:
                meta = dict(fetches=int(p[1]), capped=int(p[3]),
                            distinct=int(p[5]))
            elif p[0] == "X" and len(p) >= 3:
                ex[int(p[1])] = int(p[2])
    except (OSError, ValueError):
        pass
    if os.path.exists(out):
        os.unlink(out)
    return meta, ex


def run_phase2(tag, lines, dsk, ranges):
    """`ranges` = [(lo, hi), ...] -- every cluster watched under ONE boot."""
    import omsx_repl
    fd, out = tempfile.mkstemp(prefix="ramcode2-%s-" % tag, suffix=".txt")
    os.close(fd)
    w = "\n".join(
        'debug set_watchpoint write_mem {%d %d} {} {\n'
        '    incr ::n\n'
        '    if {$::n <= 8000} {\n'
        '        puts $::lf "W %d [format %%.4f [machine_info time]] '
        '[__region] $::wp_last_address"\n'
        '        flush $::lf\n'
        '    }\n'
        '}' % (lo, hi, i) for i, (lo, hi) in enumerate(ranges))
    t = PHASE2
    for k, v in (("@OUT@", out), ("@WATCHES@", w), ("@CELL@", str(C_NULO))):
        t = t.replace(k, v)
    omsx_repl.run_cases(REF, [("direct", lines)], batch=False, reset=RESET,
                        boot=BOOT, step=STEP, cap_gap=CAP_GAP, diska=dsk,
                        capture="screen", prologue=(t,))
    ws, cross = [], []
    try:
        for ln in open(out):
            p = ln.split()
            if p and p[0] == "W" and len(p) >= 5:
                ws.append((int(p[1]), float(p[2]), p[3], int(p[4])))
            elif p and p[0] == "C" and len(p) >= 2:
                cross.append(float(p[1]))
    except (OSError, ValueError):
        pass
    if os.path.exists(out):
        os.unlink(out)
    return ws, cross


def clusters(addrs, gap=16):
    """Group executed addresses into ranges, allowing small gaps.

    A routine is not a contiguous run of EXECUTED bytes -- operands are fetched
    as data, and a `jr` skips forward -- so a strict run would shatter one
    routine into dozens of fragments. `gap` bridges that; it is reported so the
    number is not mistaken for a measured extent.
    """
    out, cur = [], []
    for a in sorted(addrs):
        if cur and a - cur[-1] <= gap:
            cur.append(a)
        else:
            if cur:
                out.append((cur[0], cur[-1]))
            cur = [a]
    if cur:
        out.append((cur[0], cur[-1]))
    return out


def in_hooks(lo, hi):
    return lo >= HOOK_LO and hi <= HOOK_HI


def selftest() -> int:
    ok = True
    if clusters([10, 12, 40, 41], gap=16) != [(10, 12), (40, 41)]:
        print("SELFTEST RED: clusters() gave %r" % clusters([10, 12, 40, 41], 16))
        ok = False
    # 🔴 the gap must actually bridge: a strict-run version would split these
    if clusters([10, 20, 30], gap=16) != [(10, 30)]:
        print("SELFTEST RED: clusters() did not bridge a gap it was told to")
        ok = False
    # 🔴 NEGATIVE: gap=0 must NOT merge non-adjacent addresses, or the parameter
    # does nothing and every cluster is one big range.
    if clusters([10, 20, 30], gap=0) != [(10, 10), (20, 20), (30, 30)]:
        print("SELFTEST RED: gap=0 still merged -- the parameter is inert")
        ok = False
    if not in_hooks(HOOK_LO, HOOK_HI) or in_hooks(HOOK_LO - 1, HOOK_HI):
        print("SELFTEST RED: in_hooks() boundary is wrong")
        ok = False
    if addr_runs([1, 2, 5]) != [(1, 2), (5, 1)]:
        print("SELFTEST RED: imported addr_runs() misbehaves")
        ok = False
    if pcregion(dict(pc=0x6A31, pri=0, sec=0)) == pcregion(dict(pc=0x6A31, pri=3, sec=1)):
        print("SELFTEST RED: the imported pcregion() is SLOT-BLIND")
        ok = False
    print("SELFTEST GREEN" if ok else "SELFTEST RED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    if ap.parse_args().selftest:
        return selftest()

    import loadrun_probe as LR
    tmpd = tempfile.mkdtemp(prefix="ramcode-")
    seeded, _n = LR.seed(REF, RESET, tmpd, "ref")
    dsk, sizes, _per = LR.build(seeded, tmpd, "ref",
                                extra={"A       BAS": ASCII_BAS})
    print("images: S=%d B" % sizes["S"])

    print("\n=== PHASE 1: what executes from RAM inside the crossing ===")
    res = {}
    for tag, lines in (("quiet", ["REM"]), ("loadS", ['LOAD"S.BAS"']),
                       ("loadS2", ['LOAD"S.BAS"'])):
        meta, ex = run_phase1(tag, lines, dsk)
        res[tag] = (meta, ex)
        print("  %-7s fetches=%s distinct=%s capped=%s"
              % (tag, meta.get("fetches"), meta.get("distinct"),
                 meta.get("capped")))

    print("\n=== CONTROLS ===")
    ok = True
    if res["quiet"][1]:
        print("K3  NEGATIVE  RED: the quiet case recorded RAM execution")
        ok = False
    else:
        print("K3  NEGATIVE  green: nothing executed in the quiet window")

    m, ex = res["loadS"]
    if not ex:
        print("K10 POSITIVE  RED: the detector never fired -- misconfigured, "
              "and silence is not evidence that nothing executes in RAM")
        return 1
    print("K10 POSITIVE  green: %d fetch(es), %d distinct address(es)"
          % (m["fetches"], m["distinct"]))
    if K18_ADDR in ex:
        print("K18 KNOWN-EXEC green: $%04X (a claimed cell's `F7`) IS in the "
              "executed set, x%d -- the detector sees fetches"
              % (K18_ADDR, ex[K18_ADDR]))
    else:
        print("K18 KNOWN-EXEC RED: $%04X is known to execute and is ABSENT -- "
              "the detector is missing fetches" % K18_ADDR)
        ok = False
    leak = [a for a in ex if K19_LO <= a <= K19_HI]
    if leak:
        print("K19 KNOWN-DATA RED: %d address(es) in the READ-ONLY name block "
              "appear as executed -- the fetch filter is passing data reads"
              % len(leak))
        ok = False
    else:
        print("K19 KNOWN-DATA green: the $%04X..$%04X name block, which is read "
              "and never run, does NOT appear" % (K19_LO, K19_HI))
    if res["loadS"][1] == res["loadS2"][1]:
        print("K15 DETERMIN  green: two runs give an identical executed set")
    else:
        d = set(res["loadS"][1]) ^ set(res["loadS2"][1])
        print("K15 DETERMIN  RED: two runs differ in %d address(es)" % len(d))
        ok = False
    if m["capped"]:
        print("K14 CAP       ⚠️  the distinct-address ceiling was reached -- the "
              "set is a PREFIX")
    else:
        print("K14 CAP       green: ceiling not reached; the set is complete")

    if not ok:
        print("\nWITHHELD: a control is red.")
        return 1

    print("\n=== WHERE RAM CODE RUNS DURING THE CROSSING ===")
    cl = clusters(ex.keys(), gap=16)
    non_hook = []
    for lo, hi in cl:
        n = sum(v for a, v in ex.items() if lo <= a <= hi)
        tag = "the published HOOK TABLE" if in_hooks(lo, hi) else "**RAM CODE**"
        print("  $%04X..$%04X  span %4d B, %3d distinct, %6d fetch(es)  %s"
              % (lo, hi, hi - lo + 1,
                 sum(1 for a in ex if lo <= a <= hi), n, tag))
        if not in_hooks(lo, hi):
            non_hook.append((lo, hi))
    print("  (clusters bridge gaps of up to 16 B: operands are fetched as data "
          "and a `jr` skips forward, so a strict run would shatter one routine)")

    if not non_hook:
        print("\nNo non-hook RAM code found; nothing to trace in phase 2.")
        return 0

    # 🔑 EVERY non-hook cluster, not just the biggest. §6.6z traced the 79-byte
    # block and left the other four unmeasured; this reports each one's writers
    # and install times under a single boot, and repeats the run because one
    # green pass is weak evidence.
    print("\n=== PHASE 2: who writes each RAM-code cluster, and when ===")
    runs = []
    for rep in ("a", "b"):
        ws, cross = run_phase2("rep" + rep, ['LOAD"S.BAS"'], dsk, non_hook)
        runs.append((ws, cross))
    (ws, cross), (ws2, cross2) = runs

    def summarise(w):
        out = {}
        for idx, t, reg, _a in w:
            e = out.setdefault(idx, {}).setdefault(reg, [0, t, t])
            e[0] += 1
            e[1] = min(e[1], t)
            e[2] = max(e[2], t)
        return out

    sm, sm2 = summarise(ws), summarise(ws2)
    ok2 = True
    if not ws:
        print("  RED: NO writes to ANY cluster were seen -- either none is ever "
              "written (which cannot be, they hold code) or the watchpoints are "
              "misconfigured. These must not read the same way; UNRESOLVED.")
        return 1
    # 🔴 POSITIVE PER CLUSTER. A cluster with no writes is not "never installed";
    # it is a watchpoint that did not fire, and saying otherwise would be the
    # silence-is-not-evidence error.
    silent = [i for i in range(len(non_hook)) if i not in sm]
    if silent:
        print("  🔴 %d cluster(s) saw NO writes: %s -- treat as UNRESOLVED, not "
              "as 'never installed'"
              % (len(silent), " ".join("$%04X" % non_hook[i][0] for i in silent)))
        ok2 = False
    if {k: {r: v[0] for r, v in d.items()} for k, d in sm.items()} != \
       {k: {r: v[0] for r, v in d.items()} for k, d in sm2.items()}:
        print("  🔴 two runs disagree on the writer counts -- no timing claim is "
              "safe")
        ok2 = False
    else:
        print("  two runs agree on every cluster's writers and counts")
    if not cross:
        print("  ⚠️  the crossing was never reached, so 'before the crossing' "
              "cannot be checked -- timing UNRESOLVED")
        return 1
    print("  the crossing is at t=%.4f\n" % cross[0])
    for i, (lo, hi) in enumerate(non_hook):
        d = sm.get(i, {})
        print("  $%04X..$%04X (%d B)" % (lo, hi, hi - lo + 1))
        for reg, (n, t0, t1) in sorted(d.items(), key=lambda kv: kv[1][1]):
            print("      %-8s x%-5d t=%.4f..%.4f" % (reg, n, t0, t1))
        last = max((v[2] for v in d.values()), default=None)
        if last is None:
            print("      (no writes seen)")
        elif last < cross[0]:
            print("      -> installed %.2f emulated seconds BEFORE the crossing;"
                  " not rebuilt per call" % (cross[0] - last))
        else:
            print("      -> written AT OR AFTER the crossing: rebuilt during the "
                  "operation")
    return 0 if ok2 else 1


if __name__ == "__main__":
    sys.exit(main())
