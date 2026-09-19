#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DISKREAD: WHICH work-area cells does the DISK ROM read during the crossing?

§6.6w measured what the registers carry at `$FE5D` -- `DE` an open mode, `HL` the
file buffer -- and showed there is no verb selector there. The remaining half of
the input contract is what the disk side goes and FETCHES for itself once control
has crossed. That set is the surface a faithful `disk.rom` would have to read the
same way, and it is the direct form of Joost's question.

🎯 THE METHOD. A `read_mem` watchpoint over the work area, armed between the
`$FE5D` entry breakpoint and its exit at cell+4, recording for each read the
ADDRESS (`$::wp_last_address`) and WHO read it -- PC's page plus that page's
selected slot. Keep the reads whose reader is the DISK ROM. Addresses are
deduplicated, so the output is a SET of cells and a hit count per cell rather
than a transcript.

🔴 THE BAND IS `$F380..$FFFF` AND THE REASON MATTERS. That is the MSX work area,
which sits ABOVE the stack -- so reads in it are work-area accesses rather than
push/pop traffic, and the watchpoint is affordable. ⚠️ That is an assumption
about this machine, so it is a CONTROL rather than a comment: SP is sampled at
the crossing and the probe refuses if it lands inside the band.

🔴 CONTROLS.
  K3   the `quiet` case types no verb, so the window never opens and the disk
       read set must be EMPTY.
  K10  POSITIVE -- the watchpoint must fire at all. Silence is not evidence of
       "the disk side reads nothing"; it is evidence of a misconfigured
       watchpoint, and the two must never be reported the same way.
  K11  WINDOW -- reads must occur both INSIDE and OUTSIDE the window. If none
       are outside, the window filter is removing nothing and the "during the
       crossing" qualifier is unearned.
  K12  REGION -- the reader classifier must produce more than one region across
       the whole log. A classifier that answers DISK for everything would make
       every row below a tautology.
  K13  STACK -- SP at the crossing must lie OUTSIDE the watched band, or the
       reads are stack traffic wearing a work-area address.
  K14  CAP -- the log has a ceiling, and whether it was reached is REPORTED. A
       truncated set silently presented as a complete one is the failure this
       probe is most likely to produce.

🔴 CLEAN ROOM. RAM addresses and the slot-select state, at a breakpoint on a RAM
address in the published hook table. No ROM byte is read, no hook target is
followed, nothing is single-stepped into ROM, nothing is disassembled. The
addresses reported are RAM work-area cells of the MACHINE; PC is never printed,
only the REGION it falls in.
"""
import argparse
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))

from selector_probe import pcregion                           # noqa: E402

REF = "National_CF-3300"
RESET = ("", "SCREEN 0", "CLOSE", "NEW", "CLS")
BOOT, STEP, CAP_GAP = 14.0, 30.0, 8.0

C_NULO = 0xFE5D
BAND_LO, BAND_HI = 0xF380, 0xFFFF
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
set ::snapped 0
set ::snap ""
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
# 🔑 SNAPSHOT THE BAND AT THE WINDOW OPEN. A list of addresses says WHICH
# cells the disk side consults; the bytes in them say WHAT they are. Identifying
# a block by its CONTENT is the same move that named IY's target at `$FE76`, and
# it beats matching against a work-area symbol table this tree does not have.
debug set_bp @CELL@ {} {
    set ::win 1
    set ::sp [reg SP]
    if {!$::snapped} {
        set ::snapped 1
        set b [debug read_block memory @LO@ [expr {@HI@ - @LO@ + 1}]]
        binary scan $b H* ::snap
    }
}
debug set_bp [expr {@CELL@ + 4}] {} { set ::win 0 }
debug set_watchpoint read_mem {@LO@ @HI@} {} {
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
    puts $f "SNAP $::snap"
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
    fd, out = tempfile.mkstemp(prefix="diskread-%s-" % tag, suffix=".txt")
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
                meta = dict(tot=int(p[1]), inw=int(p[3]), outw=int(p[5]),
                            logged=int(p[7]), capped=int(p[9]), sp=int(p[11]))
            elif p[0] == "SNAP" and len(p) >= 2:
                meta["snap"] = p[1]
            elif p[0] == "H" and len(p) >= 3:
                reg, addr = p[1].split(",")
                hits[(reg, int(addr))] = int(p[2])
    except (OSError, ValueError):
        pass
    if os.path.exists(out):
        os.unlink(out)
    return meta, hits


def addr_runs(addrs):
    """Contiguous runs, so a 13-byte block reads as one row instead of 13."""
    out, cur = [], []
    for a in addrs:
        if cur and a == cur[-1] + 1:
            cur.append(a)
        else:
            if cur:
                out.append((cur[0], len(cur)))
            cur = [a]
    if cur:
        out.append((cur[0], len(cur)))
    return out


def at(snap_hex, addr, n):
    """The bytes a cell run held at the crossing, rendered printable."""
    if not snap_hex:
        return ""
    i = (addr - BAND_LO) * 2
    chunk = snap_hex[i:i + n * 2]
    if len(chunk) < n * 2:
        return ""
    out = []
    for j in range(0, len(chunk), 2):
        c = int(chunk[j:j + 2], 16)
        out.append(chr(c) if 32 <= c < 127 else ".")
    return "".join(out)


def band_ok(sp: int) -> bool:
    """K13: the stack must not live inside the watched band."""
    return not (BAND_LO <= sp <= BAND_HI)


def regions(hits):
    out = {}
    for (reg, _a), n in hits.items():
        out[reg] = out.get(reg, 0) + n
    return out


def cells(hits, want):
    return {a: n for (reg, a), n in hits.items() if reg == want}


def selftest() -> int:
    ok = True
    h = {("DISK", 0xF400): 3, ("MAIN-P1", 0xF401): 5, ("DISK", 0xF7F8): 1}
    if regions(h) != {"DISK": 4, "MAIN-P1": 5}:
        print("SELFTEST RED: regions() gave %r" % regions(h))
        ok = False
    if cells(h, "DISK") != {0xF400: 3, 0xF7F8: 1}:
        print("SELFTEST RED: cells() gave %r" % cells(h, "DISK"))
        ok = False
    # 🔴 NEGATIVE: cells() must not leak another reader's rows into the answer.
    if any(a == 0xF401 for a in cells(h, "DISK")):
        print("SELFTEST RED: cells() leaked a MAIN read into the DISK set")
        ok = False
    # 🔴 K13's predicate, both ways. A stack inside the band is the difference
    # between a work-area read set and push/pop noise.
    if band_ok(BAND_LO) or band_ok(BAND_HI) or band_ok(BAND_LO + 1):
        print("SELFTEST RED: band_ok() accepted an SP inside the band")
        ok = False
    if not band_ok(BAND_LO - 1):
        print("SELFTEST RED: band_ok() rejected an SP below the band")
        ok = False
    # pcregion is imported; carry its slot-blindness negative here too, because a
    # blind classifier makes every DISK row in this probe a tautology.
    if addr_runs([1, 2, 3, 7, 8]) != [(1, 3), (7, 2)]:
        print("SELFTEST RED: addr_runs() gave %r" % addr_runs([1, 2, 3, 7, 8]))
        ok = False
    # 🔴 NEGATIVE: a SHORT snapshot must render nothing rather than a truncated
    # string that would read as content the cell does not hold.
    if at("414243", BAND_LO, 4) != "":
        print("SELFTEST RED: at() rendered a run the snapshot does not cover")
        ok = False
    if at("53202020", BAND_LO, 4) != "S   ":
        print("SELFTEST RED: at() mis-rendered a known run (%r)"
              % at("53202020", BAND_LO, 4))
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
    tmpd = tempfile.mkdtemp(prefix="diskread-")
    seeded, _n = LR.seed(REF, RESET, tmpd, "ref")
    dsk, sizes, _per = LR.build(seeded, tmpd, "ref",
                                extra={"A       BAS": ASCII_BAS})
    print("images: S=%d B  L=%d B" % (sizes["S"], sizes["L"]))

    # 🔴 loadS RUNS TWICE ON PURPOSE. openMSX is deterministic and omsx_repl
    # types at fixed emulated times, so two runs of one case must produce an
    # IDENTICAL hit map. Without that, a cell appearing in LOAD and not in SAVE
    # could be run-to-run variation rather than a difference between the verbs.
    cases = [("quiet", ["REM"]), ("loadS", ['LOAD"S.BAS"']),
             ("loadS2", ['LOAD"S.BAS"']), ("saveT", ['SAVE"T.BAS"'])]
    res = {}
    for tag, lines in cases:
        meta, hits = run(tag, lines, dsk)
        res[tag] = (meta, hits)
        print("\n=== %s === %s" % (tag, meta or "no meta"))
        print("   regions inside the window: %s" % (regions(hits) or "none"))

    print("\n=== CONTROLS ===")
    ok = True
    qm, qh = res["quiet"]
    if cells(qh, "DISK"):
        print("K3  NEGATIVE  RED: the quiet case produced disk reads")
        ok = False
    else:
        print("K3  NEGATIVE  green: no disk reads in the quiet case")

    m, h = res["loadS"]
    if not m:
        print("REFUSING: no meta for loadS -- nothing to report")
        return 1
    if m["tot"] == 0:
        print("K10 POSITIVE  RED: the watchpoint never fired -- it is "
              "misconfigured, and silence is not evidence that nothing is read")
        ok = False
    else:
        print("K10 POSITIVE  green: the watchpoint fired %d time(s) in the band"
              % m["tot"])
    if m["inw"] and m["outw"]:
        print("K11 WINDOW    green: %d read(s) inside the crossing, %d outside "
              "-- the window filter removes something" % (m["inw"], m["outw"]))
    else:
        print("K11 WINDOW    RED: in=%d out=%d -- the 'during the crossing' "
              "qualifier is unearned" % (m["inw"], m["outw"]))
        ok = False
    rg = regions(h)
    if len(rg) > 1:
        print("K12 REGION    green: the reader classifier produced %d distinct "
              "regions (%s)" % (len(rg), ", ".join(sorted(rg))))
    else:
        print("K12 REGION    RED: one region only (%s) -- every row below would "
              "be a tautology" % rg)
        ok = False
    if band_ok(m["sp"]):
        print("K13 STACK     green: SP at the crossing is OUTSIDE the watched "
              "band, so these are work-area reads and not push/pop traffic")
    else:
        print("K13 STACK     RED: SP at the crossing is INSIDE the watched band "
              "-- the reads are stack traffic wearing a work-area address")
        ok = False
    if res["loadS"][1] == res["loadS2"][1]:
        print("K15 DETERMIN  green: two runs of one case give an IDENTICAL hit "
              "map, so a cell present in one verb and absent in another is a "
              "difference between the VERBS")
    else:
        a, b = res["loadS"][1], res["loadS2"][1]
        d = set(a) ^ set(b)
        print("K15 DETERMIN  RED: two runs of one case differ in %d entr(ies) "
              "-- there is a noise floor and no per-verb claim is safe" % len(d))
        ok = False
    if m["capped"]:
        print("K14 CAP       ⚠️  the log CEILING WAS REACHED (%d) -- the set "
              "below is a PREFIX of the reads, not all of them" % m["logged"])
    else:
        print("K14 CAP       green: %d read(s) logged, ceiling %d not reached "
              "-- the set below is complete" % (m["logged"], CAP))

    if not ok:
        print("\nWITHHELD: a control is red.")
        return 1

    print("\n=== WHAT THE DISK ROM READS DURING THE CROSSING ===")
    for tag in ("loadS", "saveT"):
        _m, hh = res[tag]
        d = cells(hh, "DISK")
        print("\n  %s -- %d distinct cell(s), %d read(s)"
              % (tag, len(d), sum(d.values())))
        snap = res[tag][0].get("snap") or ""
        for start, n in addr_runs(sorted(d)):
            txt = at(snap, start, n)
            print("      $%04X..$%04X (%2d B) x%-4d %s"
                  % (start, start + n - 1, n, sum(d[a] for a in range(start, start + n)),
                     ("[%s]" % txt) if txt else ""))
    ds, dt = cells(res["loadS"][1], "DISK"), cells(res["saveT"][1], "DISK")
    both = set(ds) & set(dt)
    print("\n  shared by LOAD and SAVE: %d cell(s)" % len(both))
    print("  LOAD only: %s" % " ".join("$%04X" % a for a in sorted(set(ds) - set(dt))))
    print("  SAVE only: %s" % " ".join("$%04X" % a for a in sorted(set(dt) - set(ds))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
