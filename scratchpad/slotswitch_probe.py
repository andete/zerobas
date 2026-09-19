#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-SLOTSW: does the disk side hand control BACK to main inside the crossing?

§6.6v left this open and §6.6x/§6.6y narrowed it without closing it. `$FE76` is
entered with `MAIN-P1` on top of stack BETWEEN `$FE5D`'s entry and its exit. Two
readings fit: the disk side returned into main by a route that is not `$0030` or
`$001C` (a ROM can page slots itself with `out ($a8)`), or `$FE76` is reached by
a `jp` so its top-of-stack is a caller's caller.

🎯 THE DISCRIMINATOR IS THE SLOT REGISTER ITSELF. Page 1 (`$4000..$7FFF`) holds
main ROM page 1 in slot 0 and the disk ROM in slot 3-1; only one is visible at a
time, and switching means writing port `$A8`. Watch those writes inside the
window and the sequence of page-1 selections IS the control-flow answer:

  * page 1 goes MAIN -> DISK once and back at the end  => one handover, no return
  * page 1 goes DISK -> MAIN -> DISK inside the window => the disk side DID hand
    control back to main and take it again

⚠️ A SLOT SWITCH IS NOT THE SAME AS A CALL. `$A8` traffic proves which ROM is
VISIBLE, not who is executing -- an inter-slot call's own trampoline switches
slots too. So the probe reports the SEQUENCE and counts round trips, and the
verdict is stated in terms of visibility, which is what it measures.

🔴 CONTROLS, including a known-answer pair per [[validate-a-filter-with-two-known-answers]].
  K3   the `quiet` case never opens the window: no records.
  K10  POSITIVE -- the watchpoint must fire; every inter-slot call writes `$A8`,
       so silence is a misconfigured watchpoint and not a null result.
  K20  🔑 KNOWN-ANSWER (must be true) -- at the `$FE5D` entry breakpoint, page 1
       must be selected to MAIN. §6.6v measured main page 1 as the caller, so if
       the readout says otherwise the page-1 decode is wrong.
  K21  🔑 KNOWN-ANSWER (must be true) -- page 1 must be selected to the DISK ROM
       at some point inside the window, because §6.6u measured the disk ROM
       running the whole sector loop there. If it never is, the decode is wrong
       in the other direction.
  K15  DETERMINISM -- two runs of one case must give an identical sequence.

🔴 CLEAN ROOM. I/O port values, PC regions and the slot-select state. No ROM byte
is read, no hook target followed, nothing single-stepped into ROM, nothing
disassembled.
"""
import argparse
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))

REF = "National_CF-3300"
RESET = ("", "SCREEN 0", "CLOSE", "NEW", "CLS")
BOOT, STEP, CAP_GAP = 14.0, 30.0, 8.0

C_NULO, C_BINL = 0xFE5D, 0xFE76
CAP = 4000
ASCII_BAS = b"10 REM Z\r\n20 REM Z\r\n"


TCL = r'''
set ::win 0
set ::n 0
set ::tot 0
set ::lf [open {@OUT@} w]
# 🔴 openMSX renders a NON-EXPANDED slot's secondary as the literal `X`, not as
# an empty string -- so `$sec eq ""` does not catch it and the readout came out
# "0-X", which failed a control written against "0-0". Already recorded once in
# this arc and re-broken here; normalise in one place.
proc __sub {v} { if {$v eq "" || $v eq "X"} { return 0 } ; return $v }
proc __p1 {} {
    set s [get_selected_slot 1]
    return "[lindex $s 0]-[__sub [lindex $s 1]]"
}
proc __who {} {
    set pc [reg PC]
    set p [expr {$pc >> 14}]
    if {$p >= 2} { return "RAM" }
    set s [get_selected_slot $p]
    set pri [lindex $s 0]
    set sec [__sub [lindex $s 1]]
    if {$pri == 0} { if {$p == 0} { return "MAIN-P0" } else { return "MAIN-P1" } }
    if {$pri == 3 && $sec == 1} { return "DISK" }
    return "SLOT$pri-$sec"
}
debug set_bp @NULO@ {} {
    set ::win 1
    puts $::lf "OPEN [format %.4f [machine_info time]] [__p1]"
    flush $::lf
}
debug set_bp [expr {@NULO@ + 4}] {} {
    set ::win 0
    puts $::lf "SHUT [format %.4f [machine_info time]] [__p1]"
    flush $::lf
}
# 🔴 ALWAYS LOG, AND CARRY THE WINDOW STATE. Logging only when the window is
# open makes "the cell was never entered" and "it was entered outside the
# window" print identically -- and the first run of this probe showed no BINL
# mark at all while D-CROSSABI had measured it INSIDE the window, which is
# exactly the discrepancy that must not be silently swallowed.
debug set_bp @BINL@ {} {
    puts $::lf "BINL [format %.4f [machine_info time]] [__p1] WIN$::win"
    flush $::lf
}
debug set_watchpoint write_io 0xA8 {} {
    incr ::tot
    if {!$::win} return
    if {$::n >= @CAP@} return
    incr ::n
    # page-1 primary slot = bits 3-2 of the value written to $A8
    puts $::lf "A8 [format %.4f [machine_info time]] [__who] [expr {($::wp_last_value >> 2) & 3}] [__p1]"
    flush $::lf
}
proc __end {} { puts $::lf "TOT $::tot N $::n" ; flush $::lf ; after time 1 __end }
after time 1 __end
'''


def prologue(out_path):
    t = TCL
    for k, v in (("@OUT@", out_path), ("@NULO@", str(C_NULO)),
                 ("@BINL@", str(C_BINL)), ("@CAP@", str(CAP))):
        t = t.replace(k, v)
    return (t,)


def run(tag, lines, dsk):
    import omsx_repl
    fd, out = tempfile.mkstemp(prefix="slotsw-%s-" % tag, suffix=".txt")
    os.close(fd)
    omsx_repl.run_cases(REF, [("direct", lines)], batch=False, reset=RESET,
                        boot=BOOT, step=STEP, cap_gap=CAP_GAP, diska=dsk,
                        capture="screen", prologue=prologue(out))
    ev, meta = [], {}
    try:
        for ln in open(out):
            p = ln.split()
            if not p:
                continue
            if p[0] == "TOT" and len(p) >= 4:
                meta = dict(tot=int(p[1]), n=int(p[3]))
            elif p[0] in ("OPEN", "SHUT", "BINL") and len(p) >= 3:
                ev.append(dict(k=p[0], t=float(p[1]), p1=p[2],
                               win=(p[3] if len(p) > 3 else "")))
            elif p[0] == "A8" and len(p) >= 5:
                ev.append(dict(k="A8", t=float(p[1]), who=p[2],
                               bits=int(p[3]), p1=p[4]))
    except (OSError, ValueError):
        pass
    if os.path.exists(out):
        os.unlink(out)
    return ev, meta


def page1_sequence(ev):
    """The page-1 selection as it CHANGES, so a run of identical writes collapses."""
    seq = []
    for e in ev:
        v = e.get("p1")
        if v and (not seq or seq[-1] != v):
            seq.append(v)
    return seq


def round_trips(seq, disk="3-1"):
    """How many times the page-1 selection LEAVES the disk ROM and comes back.

    That is the shape that would mean a hand-back: DISK -> something -> DISK.
    """
    n, seen_disk, left = 0, False, False
    for v in seq:
        if v == disk:
            if seen_disk and left:
                n += 1
            seen_disk, left = True, False
        elif seen_disk:
            left = True
    return n


def selftest() -> int:
    ok = True
    ev = [dict(p1="0-0"), dict(p1="0-0"), dict(p1="3-1"), dict(p1="0-0"),
          dict(p1="3-1")]
    if page1_sequence(ev) != ["0-0", "3-1", "0-0", "3-1"]:
        print("SELFTEST RED: page1_sequence() gave %r" % page1_sequence(ev))
        ok = False
    if round_trips(["0-0", "3-1", "0-0", "3-1"]) != 1:
        print("SELFTEST RED: a DISK->MAIN->DISK excursion was not counted")
        ok = False
    # 🔴 NEGATIVE: one handover with no return must count ZERO round trips, or
    # the metric would report a hand-back on every single load.
    if round_trips(["0-0", "3-1", "0-0"]) != 0:
        print("SELFTEST RED: a single handover was counted as a round trip")
        ok = False
    if round_trips(["0-0"]) != 0 or round_trips([]) != 0:
        print("SELFTEST RED: a trivial sequence produced a round trip")
        ok = False
    # 🔴 NEGATIVE: consecutive identical selections are not excursions
    if round_trips(["3-1", "3-1", "3-1"]) != 0:
        print("SELFTEST RED: staying in the disk slot counted as a round trip")
        ok = False
    print("SELFTEST GREEN" if ok else "SELFTEST RED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    if ap.parse_args().selftest:
        return selftest()

    import loadrun_probe as LR
    tmpd = tempfile.mkdtemp(prefix="slotsw-")
    seeded, _n = LR.seed(REF, RESET, tmpd, "ref")
    dsk, sizes, _per = LR.build(seeded, tmpd, "ref",
                                extra={"A       BAS": ASCII_BAS})
    print("images: S=%d B" % sizes["S"])

    res = {}
    for tag, lines in (("quiet", ["REM"]), ("loadS", ['LOAD"S.BAS"']),
                       ("loadS2", ['LOAD"S.BAS"'])):
        ev, meta = run(tag, lines, dsk)
        res[tag] = (ev, meta)
        marks = [e["k"] for e in ev if e["k"] != "A8"]
        print("  %-7s %s $A8 write(s) in the window (%s total), marks: %s"
              % (tag, meta.get("n"), meta.get("tot"), " ".join(marks) or "none"))

    print("\n=== CONTROLS ===")
    ok = True
    if res["quiet"][0]:
        print("K3  NEGATIVE  RED: the quiet case recorded events")
        ok = False
    else:
        print("K3  NEGATIVE  green: nothing in the quiet case")

    ev, meta = res["loadS"]
    if not meta or meta.get("tot", 0) == 0:
        print("K10 POSITIVE  RED: the $A8 watchpoint never fired at all -- "
              "misconfigured, and silence is not a null result")
        return 1
    print("K10 POSITIVE  green: %d $A8 write(s) overall, %d inside the window"
          % (meta["tot"], meta["n"]))

    opens = [e for e in ev if e["k"] == "OPEN"]
    if opens and opens[0]["p1"] == "0-0":
        print("K20 KNOWN     green: at the crossing's entry, page 1 is MAIN "
              "(0-0) -- as §6.6v measured from the caller's region")
    else:
        print("K20 KNOWN     RED: at the crossing's entry page 1 reads %s, not "
              "MAIN -- the page-1 decode is wrong"
              % (opens[0]["p1"] if opens else "nothing"))
        ok = False
    inside = [e["p1"] for e in ev if e["k"] == "A8"]
    if "3-1" in inside:
        print("K21 KNOWN     green: page 1 IS selected to the disk ROM inside "
              "the window -- as §6.6u requires, since the disk ROM runs the loop")
    else:
        print("K21 KNOWN     RED: the disk ROM is never selected into page 1 "
              "inside the window (seen: %s)" % sorted(set(inside)))
        ok = False
    if page1_sequence(res["loadS"][0]) == page1_sequence(res["loadS2"][0]):
        print("K15 DETERMIN  green: two runs give an identical page-1 sequence")
    else:
        print("K15 DETERMIN  RED: two runs differ")
        ok = False

    if not ok:
        print("\nWITHHELD: a control is red.")
        return 1

    seq = page1_sequence(ev)
    print("\n=== THE PAGE-1 SELECTION THROUGH THE CROSSING ===")
    print("  %d change(s): %s" % (len(seq), " -> ".join(seq)))
    counts: dict = {}
    for e in ev:
        if e["k"] == "A8":
            counts[e["who"]] = counts.get(e["who"], 0) + 1
    print("  who wrote $A8 inside the window: %s" % counts)
    binl = [e for e in ev if e["k"] == "BINL"]
    if binl:
        print("  $FE76 entered at t=%.4f, page 1 = %s, window %s"
              % (binl[0]["t"], binl[0]["p1"],
                 "OPEN" if binl[0].get("win") == "WIN1" else "SHUT"))
    else:
        print("  $FE76 was NEVER entered in this run -- which differs from "
              "§6.6v's measurement and is a discrepancy, not a null result")
    rt = round_trips(seq)
    print("\n=== THE ANSWER ===")
    print("  DISK -> elsewhere -> DISK excursions inside the window: %d" % rt)
    if rt:
        print("  -> the disk ROM IS paged OUT and back IN during the crossing, "
              "so control leaves the disk side and returns. §6.6v's first "
              "reading is the right one.")
    else:
        print("  -> page 1 never leaves the disk ROM and comes back, so nothing "
              "hands control to main ROM page 1 mid-crossing. §6.6v's SECOND "
              "reading (a `jp`, so top-of-stack is a caller's caller) is what "
              "fits.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
