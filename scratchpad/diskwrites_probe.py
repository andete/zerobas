#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DISKWRITE: the OUTPUT half of the crossing -- what changes, and who changed it.

§6.6w measured what main HANDS the disk side at `$FE5D`; §6.6x measured what the
disk side FETCHES for itself. This measures the return direction: what the disk
ROM WRITES into the shared work area during the crossing, and what has actually
CHANGED by the time main gets control back. Those are two different questions and
the probe asks both, because they can disagree and the disagreement is the
interesting part.

🎯 TWO HALVES, DELIBERATELY REDUNDANT.
  (a) a `write_mem` watchpoint over the band, armed between the `$FE5D` entry
      breakpoint and its exit at cell+4, filtered to writers whose PC region is
      the DISK ROM. That is "what the disk side wrote".
  (b) a snapshot of the whole band at the entry AND at the exit, subtracted.
      That is "what main sees on return" -- the actual output contract.

🔴 THEY ARE NOT THE SAME SET AND NEITHER IS REDUNDANT. A cell the disk side
writes and then restores appears in (a) and NOT in (b). A cell changed by a
writer in another region -- the 60 Hz interrupt runs throughout, in MAIN page 0
(§6.6x) -- appears in (b) and NOT in (a). Reporting only one would silently pick
a side; reporting both names which cells are which, and THAT is the result.

🔴 CONTROLS, carried over from D-DISKREAD because they are what make a region
verdict mean anything, plus one new.
  K3   the `quiet` case never opens the window: both sets must be EMPTY.
  K10  POSITIVE -- the watchpoint must fire. Silence is a misconfigured
       watchpoint, not "the disk side writes nothing", and the two must never be
       reported the same way.
  K11  WINDOW -- writes must occur both inside and outside the window, or the
       "during the crossing" qualifier is unearned.
  K12  REGION -- the writer classifier must produce more than one region, or
       every DISK row is a tautology.
  K13  STACK -- SP at the crossing must lie OUTSIDE the band, or these are
       push/pop writes wearing a work-area address.
  K14  CAP -- the ceiling is REPORTED, so a truncated set is never presented as
       a complete one.
  K15  DETERMINISM -- two runs of one case must agree exactly, in BOTH halves.
  K16  🆕 CROSS-CHECK -- the two halves are compared cell by cell and their
       disagreement is printed rather than reconciled.

🔴 CLEAN ROOM. RAM addresses, RAM contents and the slot-select state, at
breakpoints on RAM addresses in the published hook table. No ROM byte is read, no
hook target is followed, nothing is single-stepped into ROM, nothing is
disassembled. PC is never printed -- only the region it falls in.
"""
import argparse
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))

# 🎯 REUSE, DO NOT REWRITE. Every one of these is already mutation-proved in its
# own module's selftest; a second copy could drift from the first.
from selector_probe import pcregion                           # noqa: E402
from diskreads_probe import (BAND_LO, BAND_HI, addr_runs, at,  # noqa: E402
                             band_ok, cells, regions)

REF = "National_CF-3300"
RESET = ("", "SCREEN 0", "CLOSE", "NEW", "CLS")
BOOT, STEP, CAP_GAP = 14.0, 30.0, 8.0

C_NULO = 0xFE5D
CAP = 20000
ASCII_BAS = b"10 REM Z\r\n20 REM Z\r\n"


TCL = r'''
set ::win 0
set ::tot 0
set ::inw 0
set ::outw 0
set ::logged 0
set ::capped 0
set ::sp 0
set ::snapA ""
set ::snapB ""
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
proc __band {} {
    set b [debug read_block memory @LO@ [expr {@HI@ - @LO@ + 1}]]
    binary scan $b H* hx
    return $hx
}
debug set_bp @CELL@ {} {
    set ::win 1
    set ::sp [reg SP]
    if {$::snapA eq ""} { set ::snapA [__band] }
}
debug set_bp [expr {@CELL@ + 4}] {} {
    set ::win 0
    if {$::snapB eq ""} { set ::snapB [__band] }
}
debug set_watchpoint write_mem {@LO@ @HI@} {} {
    incr ::tot
    if {$::win} { incr ::inw } else { incr ::outw ; return }
    if {$::logged >= @CAP@} { set ::capped 1 ; return }
    incr ::logged
    set k "[__region],$::wp_last_address"
    if {[info exists ::hit($k)]} { incr ::hit($k) } else { set ::hit($k) 1 }
}
proc __dump {} {
    set f [open {@OUT@} w]
    puts $f "TOT $::tot IN $::inw OUT $::outw LOGGED $::logged CAPPED $::capped SP $::sp"
    puts $f "SNAPA $::snapA"
    puts $f "SNAPB $::snapB"
    foreach k [array names ::hit] { puts $f "H $k $::hit($k)" }
    close $f
    after time 1 __dump
}
after time 1 __dump
'''


def prologue(out_path):
    t = TCL
    for k, v in (("@OUT@", out_path), ("@CELL@", str(C_NULO)),
                 ("@LO@", str(BAND_LO)), ("@HI@", str(BAND_HI)),
                 ("@CAP@", str(CAP))):
        t = t.replace(k, v)
    return (t,)


def run(tag, lines, dsk):
    import omsx_repl
    fd, out = tempfile.mkstemp(prefix="diskwrite-%s-" % tag, suffix=".txt")
    os.close(fd)
    omsx_repl.run_cases(REF, [("direct", lines)], batch=False, reset=RESET,
                        boot=BOOT, step=STEP, cap_gap=CAP_GAP, diska=dsk,
                        capture="screen", prologue=prologue(out))
    meta, hits = {}, {}
    try:
        for ln in open(out):
            p = ln.split()
            if not p:
                continue
            if p[0] == "TOT" and len(p) >= 12:
                meta.update(tot=int(p[1]), inw=int(p[3]), outw=int(p[5]),
                            logged=int(p[7]), capped=int(p[9]), sp=int(p[11]))
            elif p[0] in ("SNAPA", "SNAPB") and len(p) >= 2:
                meta[p[0].lower()] = p[1]
            elif p[0] == "H" and len(p) >= 3:
                reg, addr = p[1].split(",")
                hits[(reg, int(addr))] = int(p[2])
    except (OSError, ValueError):
        pass
    if os.path.exists(out):
        os.unlink(out)
    return meta, hits


def changed(meta):
    """Half (b): the cells whose CONTENT differs between entry and exit.

    🔴 REFUSES on a missing snapshot rather than returning an empty set: an
    absent snapshot subtracts to "nothing changed", which is the quietest
    possible way for this probe to be wrong.
    """
    a, b = meta.get("snapa"), meta.get("snapb")
    if not a or not b or len(a) != len(b):
        return None
    return {BAND_LO + i // 2 for i in range(0, len(a), 2)
            if a[i:i + 2] != b[i:i + 2]}


def selftest() -> int:
    ok = True
    m = {"snapa": "00112233", "snapb": "00FF2233"}
    if changed(m) != {BAND_LO + 1}:
        print("SELFTEST RED: changed() gave %r" % changed(m))
        ok = False
    # 🔴 NEGATIVE: a missing or ragged snapshot must REFUSE, not report "nothing
    # changed" -- those two must never print the same way.
    for bad in ({"snapa": "0011"}, {"snapb": "0011"},
                {"snapa": "0011", "snapb": "001122"}, {}):
        if changed(bad) is not None:
            print("SELFTEST RED: changed() returned a set for %r" % bad)
            ok = False
    if changed({"snapa": "0011", "snapb": "0011"}) != set():
        print("SELFTEST RED: two identical snapshots must give an EMPTY set, "
              "which is different from a refusal")
        ok = False
    # the imported helpers must still behave; a drifted import would be silent
    if addr_runs([1, 2, 5]) != [(1, 2), (5, 1)]:
        print("SELFTEST RED: imported addr_runs() misbehaves")
        ok = False
    if band_ok(BAND_LO) or not band_ok(BAND_LO - 1):
        print("SELFTEST RED: imported band_ok() misbehaves")
        ok = False
    if at("53202020", BAND_LO, 4) != "S   ":
        print("SELFTEST RED: imported at() misbehaves")
        ok = False
    if cells({("DISK", 9): 1, ("RAM", 8): 2}, "DISK") != {9: 1}:
        print("SELFTEST RED: imported cells() misbehaves")
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
    tmpd = tempfile.mkdtemp(prefix="diskwrite-")
    seeded, _n = LR.seed(REF, RESET, tmpd, "ref")
    dsk, sizes, _per = LR.build(seeded, tmpd, "ref",
                                extra={"A       BAS": ASCII_BAS})
    print("images: S=%d B  L=%d B" % (sizes["S"], sizes["L"]))

    cases = [("quiet", ["REM"]), ("loadS", ['LOAD"S.BAS"']),
             ("loadS2", ['LOAD"S.BAS"']), ("saveT", ['SAVE"T.BAS"'])]
    res = {}
    for tag, lines in cases:
        meta, hits = run(tag, lines, dsk)
        res[tag] = (meta, hits)
        ch = changed(meta)
        print("\n=== %s === in=%s out=%s logged=%s capped=%s"
              % (tag, meta.get("inw"), meta.get("outw"), meta.get("logged"),
                 meta.get("capped")))
        print("   writers inside the window: %s" % (regions(hits) or "none"))
        print("   cells changed across the crossing: %s"
              % ("REFUSED (snapshot missing)" if ch is None else len(ch)))

    print("\n=== CONTROLS ===")
    ok = True
    qm, qh = res["quiet"]
    qch = changed(qm)
    if cells(qh, "DISK") or qch:
        print("K3  NEGATIVE  RED: the quiet case produced disk writes or a "
              "change set")
        ok = False
    else:
        print("K3  NEGATIVE  green: nothing in the quiet case")

    m, h = res["loadS"]
    if not m:
        print("REFUSING: no meta for loadS")
        return 1
    if m["tot"] == 0:
        print("K10 POSITIVE  RED: the watchpoint never fired -- misconfigured, "
              "and silence is not evidence that nothing is written")
        ok = False
    else:
        print("K10 POSITIVE  green: %d write(s) in the band" % m["tot"])
    if m["inw"] and m["outw"]:
        print("K11 WINDOW    green: %d inside the crossing, %d outside"
              % (m["inw"], m["outw"]))
    else:
        print("K11 WINDOW    RED: in=%d out=%d -- the 'during the crossing' "
              "qualifier is unearned" % (m["inw"], m["outw"]))
        ok = False
    rg = regions(h)
    if len(rg) > 1:
        print("K12 REGION    green: %d distinct writer regions (%s)"
              % (len(rg), ", ".join(sorted(rg))))
    else:
        print("K12 REGION    RED: one region only (%s) -- every DISK row would "
              "be a tautology" % rg)
        ok = False
    if band_ok(m["sp"]):
        print("K13 STACK     green: SP at the crossing is OUTSIDE the band")
    else:
        print("K13 STACK     RED: SP is INSIDE the band -- these are push/pop "
              "writes wearing a work-area address")
        ok = False
    ch = changed(m)
    if ch is None:
        print("K14 SNAPSHOT  RED: a band snapshot is missing, so 'what main "
              "sees on return' cannot be computed")
        ok = False
    if res["loadS"][1] == res["loadS2"][1] and changed(res["loadS2"][0]) == ch:
        print("K15 DETERMIN  green: two runs of one case agree in BOTH halves")
    else:
        print("K15 DETERMIN  RED: two runs of one case disagree -- there is a "
              "noise floor and no per-verb claim is safe")
        ok = False
    if m["capped"]:
        print("K14 CAP       ⚠️  the ceiling WAS reached (%d) -- the write set "
              "is a PREFIX, not all of it" % m["logged"])
    else:
        print("K14 CAP       green: %d logged, ceiling %d not reached"
              % (m["logged"], CAP))

    if not ok:
        print("\nWITHHELD: a control is red.")
        return 1

    print("\n=== (a) WHAT THE DISK ROM WRITES DURING THE CROSSING ===")
    for tag in ("loadS", "saveT"):
        mm, hh = res[tag]
        d = cells(hh, "DISK")
        print("\n  %s -- %d distinct cell(s), %d write(s)"
              % (tag, len(d), sum(d.values())))
        for start, n in addr_runs(sorted(d)):
            print("      $%04X..$%04X (%2d B) x%d"
                  % (start, start + n - 1, n,
                     sum(d[a] for a in range(start, start + n))))

    print("\n=== (b) WHAT MAIN SEES ON RETURN (entry vs exit) ===")
    for tag in ("loadS", "saveT"):
        mm, _hh = res[tag]
        c = changed(mm) or set()
        print("\n  %s -- %d cell(s) changed" % (tag, len(c)))
        for start, n in addr_runs(sorted(c)):
            before = at(mm.get("snapa", ""), start, n)
            after = at(mm.get("snapb", ""), start, n)
            print("      $%04X..$%04X (%2d B)  [%s] -> [%s]"
                  % (start, start + n - 1, n, before, after))

    # 🔴 K17 -- THE INSTRUMENT CHECK THE FIRST RUN ASKED FOR. If a cell's
    # CONTENT changed across the crossing, some instruction wrote it, and the
    # watchpoint covers the whole band for the whole window. A changed cell with
    # NO recorded writer therefore means the watchpoint has a BLIND SPOT, not
    # that the cell changed by itself. Half (b) would then be right and half (a)
    # incomplete, and every "the disk side does not write this" reading would be
    # unfounded.
    print("\n=== K17: does every CHANGED cell have a recorded writer? ===")
    for tag in ("loadS", "saveT"):
        mm, hh = res[tag]
        ch2 = changed(mm) or set()
        bywho: dict = {}
        for (reg, a2), n in hh.items():
            bywho.setdefault(a2, {})[reg] = n
        orphan = sorted(a2 for a2 in ch2 if a2 not in bywho)
        print("  %s: %d changed, %d with NO writer recorded"
              % (tag, len(ch2), len(orphan)))
        if orphan:
            print("     🔴 BLIND SPOT -- %s"
                  % " ".join("$%04X" % a2 for a2 in orphan[:24]))
        # and who wrote the changed cells the DISK did not
        other: dict = {}
        for a2 in sorted(ch2):
            regs = {r for r in bywho.get(a2, {}) if r != "DISK"}
            if regs and "DISK" not in bywho.get(a2, {}):
                other.setdefault(",".join(sorted(regs)), []).append(a2)
        for k, v in sorted(other.items()):
            print("     changed, written only by %-8s : %s" % (
                k, " ".join("$%04X" % a2 for a2 in v[:16])
                + (" ..." if len(v) > 16 else "")))

    print("\n=== K16 CROSS-CHECK: the two halves are NOT the same set ===")
    for tag in ("loadS", "saveT"):
        mm, hh = res[tag]
        wrote = set(cells(hh, "DISK"))
        ch2 = changed(mm) or set()
        print("  %s: disk wrote %d, changed %d, both %d"
              % (tag, len(wrote), len(ch2), len(wrote & ch2)))
        print("      written by DISK but UNCHANGED on return (written then "
              "restored, or written back the same): %d cell(s)"
              % len(wrote - ch2))
        print("      CHANGED but not written by DISK (another region -- the "
              "60 Hz interrupt runs throughout): %d cell(s)" % len(ch2 - wrote))
    return 0


if __name__ == "__main__":
    sys.exit(main())
