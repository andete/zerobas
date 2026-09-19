#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-LOADPROTO: how does the reference's `LOAD` actually TALK to its disk ROM?

🏗️ JOOST, 2026-09-19: *"as long as we don't fully know how e.g. LOAD works on
the reference, we can't implement it properly."* This is the instrument for
that. D-HOOKCOUNT established WHICH cells `LOAD` enters and HOW OFTEN; it
deliberately captured no register, so it could not say WHO CALLS WHOM. That is
the whole of the protocol question, and it is the one §6.6r had to RETRACT a
sentence over: a per-sector count of 29 is consistent with a loop in main
calling a disk service 29 times AND with a loop inside the disk ROM's own
handler. Counts cannot separate those. **A return address can.**

🎯 THE MEASUREMENT. At a breakpoint on a hook cell the Z80 has not yet executed
the cell's first byte, so the word at (SP) is the RETURN ADDRESS INTO WHOEVER
CALLED THE HOOK. Classify that address by its page and that page's selected
slot and you learn which ROM the caller was in:

    $0000-$3FFF, slot 0          -> MAIN ROM page 0
    $4000-$7FFF, slot 0          -> MAIN ROM page 1
    $4000-$7FFF, slot 3-1        -> DISK ROM
    $8000-$FFFF, or slot 3-0     -> RAM

So at `$FFCF`/`$FFD4` -- the per-sector service -- a caller in MAIN means main
drives the sector loop, and a caller in the DISK ROM means the loop lives below
the boundary. That is exactly the A-versus-B shape question step 9 has been
waiting on a RULING for, and it is a measurement, not a preference.

🔴 CLEAN ROOM. This reads registers (SP, IX, IY), ONE word of RAM (the stack
top), and the slot-select state. It classifies an address into a REGION and
reports the region. It never reads a ROM byte, never follows a hook cell's
`<lo> <hi>`, never single-steps into ROM, never disassembles. That line is the
one `disk/docs/expansion-protocol.md` §7 already operates on -- that spike's
findings came from "setting openMSX breakpoints on documented hook addresses and
reading the live Z80 register file / system work areas" -- and §2's rule stands
unchanged: a target address inside the reference ROM is its internal detail,
noted and never called. Raw addresses are kept out of the REPORT precisely so
nothing here can be mistaken for a transcription; only regions and counts print.

🔴 FOUR CONTROLS, because a classifier that always answers "MAIN" would look
exactly like a finding.
  K1 DISCRIMINATOR   `H.TIMI $FD9F` is entered from the BIOS interrupt handler,
                     which is in MAIN page 0. If the classifier cannot say that
                     about a cell whose caller is known a priori, no other row
                     it produces means anything.
  K2 CONTINUITY      the per-sector cells' entry count between arming and the
                     end of the run must match D-HOOKCOUNT's measured LOAD delta
                     for this image (3 data sectors + 5 mount calls = 8). If it
                     does not, the arming window missed part of the verb and the
                     trace is of something other than a whole LOAD.
  K3 NEGATIVE        the `quiet` case runs no verb, so `$FE67` never fires and
                     the trace must be EMPTY. A probe that logs during boot is
                     measuring the machine, not the verb.
  K4 SLOT GROUND     the disk ROM must be observed paged into page 1 at least
                     once. Without it, `get_selected_slot` could be returning a
                     constant and every region would be a guess.

⚠️ ONE HONEST LIMIT, stated before the run. The word at (SP) is the return
address only when the hook was reached by a CALL. A hook reached by a JP shows
its caller's caller instead. The report therefore names the quantity as
"top-of-stack region at entry", and K1 is what makes that reading credible for
this machine: a cell whose caller is independently known must classify right.
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

# The cells D-HOOKCOUNT measured. $FE67 is LOAD's verb entry (LOAD + MERGE and
# nothing else); $FFCF/$FFD4 are the per-sector service, named by BEHAVIOUR
# because they sit past the last cell C-BIOS's table documents.
C_VERB   = 0xFE67
C_NULO   = 0xFE5D
C_BINL   = 0xFE76
C_SECT   = (0xFFCF, 0xFFD4)
C_TIMI   = 0xFD9F          # K1: caller known a priori -> MAIN page 0
C_SAVE   = 0xFE6C          # never entered by LOAD -- a second negative
CELLS    = (C_VERB, C_NULO, C_BINL, C_TIMI, C_SAVE) + C_SECT

RST30, CALSLT = 0x0030, 0x001C     # the two public inter-slot entries
CAP = 6000                         # event ceiling; a whole small LOAD fits


# ---------------------------------------------------------------- classifier
def region(addr: int, pri, sec) -> str:
    """Name the REGION an address lives in, given its page's selected slot.

    Kept in Python (not Tcl) so `--selftest` can drive it with constructed
    inputs including ones the machine would never produce.
    """
    page = addr >> 14
    if page >= 2:
        return "RAM"
    if pri == 0:
        return "MAIN-P0" if page == 0 else "MAIN-P1"
    if pri == 3 and sec == 1:
        return "DISK" if page == 1 else "DISK?p0"
    if pri == 3 and sec == 0:
        return "RAM"
    return "SLOT%s-%s" % (pri, sec)


def selftest() -> int:
    """Positive rows, then a NEGATIVE control the classifier must NOT accept."""
    ok = True
    for addr, pri, sec, want in (
            (0x0159, 0, 0, "MAIN-P0"),     # BIOS/BASIC page 0
            (0x6A31, 0, 0, "MAIN-P1"),     # BASIC page 1, same slot
            (0x6A31, 3, 1, "DISK"),        # SAME address, disk slot -> disk ROM
            (0x8123, 3, 0, "RAM"),
            # 🔴 PAGES 2 AND 3 ARE RAM ON THIS MACHINE WHATEVER THE SLOT
            # REGISTER SAYS. Without a page-2 row whose slot is NOT the
            # RAM subslot, a classifier that only special-cases page 3
            # passes every other row here -- measured, not assumed: that
            # exact mutation went GREEN before this line existed.
            (0x8123, 0, 0, "RAM"),
            (0xF380, 0, 0, "RAM"),         # page 3 is RAM whatever slot says
            (0x4002, 3, 0, "RAM"),         # page 1 mapped to the RAM subslot
    ):
        got = region(addr, pri, sec)
        if got != want:
            print("SELFTEST RED: region(%04X, %s, %s) = %s, want %s"
                  % (addr, pri, sec, got, want))
            ok = False
    # 🔴 THE NEGATIVE CONTROL. $6A31 is MAIN-P1 under slot 0 and DISK under slot
    # 3-1. If those two ever agree, the classifier is ignoring the slot and
    # every DISK/MAIN verdict this probe prints is the address alone -- which is
    # precisely the ambiguity the measurement exists to resolve.
    if region(0x6A31, 0, 0) == region(0x6A31, 3, 1):
        print("SELFTEST RED: the classifier is SLOT-BLIND -- one address, two "
              "slots, same answer. Every DISK verdict would be unfounded.")
        ok = False
    # And an unknown slot must not be silently folded into a known region.
    if region(0x4000, 2, 0) in ("MAIN-P1", "DISK", "RAM"):
        print("SELFTEST RED: an UNKNOWN slot was folded into a known region")
        ok = False
    print("SELFTEST GREEN" if ok else "SELFTEST RED")
    return 0 if ok else 1


# ---------------------------------------------------------------------- Tcl
TCL = r'''
proc __w16 {a} { expr {[debug read memory $a] + 256*[debug read memory [expr {$a+1}]]} }
set ::armed 0
set ::n 0
set ::seq 0
array set ::pre {}
array set ::tot {}
set ::lf [open {@OUT@} w]
proc __lg {s} { puts $::lf $s ; flush $::lf }

# top-of-stack at entry, with the SELECTED SLOT of the page it points into
proc __caller {} {
    set c [__w16 [reg SP]]
    set p [expr {$c >> 14}]
    set s [get_selected_slot $p]
    set pri [lindex $s 0]
    set sec [lindex $s 1]
    if {$sec eq ""} { set sec 0 }
    return "$c $pri $sec"
}
proc __ev {tag} {
    incr ::seq
    if {!$::armed} return
    if {$::n >= @CAP@} return
    incr ::n
    __lg "$::n $tag [__caller] [reg SP]"
}
# counted ALWAYS, logged only inside the window -- K2 needs the pre-arm total
proc __cnt {a tag} {
    if {![info exists ::tot($a)]} { set ::tot($a) 0 }
    incr ::tot($a)
    __ev $tag
}
proc __dump {} {
    set f [open {@SUM@} w]
    foreach a [lsort -integer [array names ::tot]] {
        set p 0
        if {[info exists ::pre($a)]} { set p [set ::pre($a)] }
        puts $f "$a [set ::tot($a)] $p"
    }
    puts $f "ARMED $::armed EVENTS $::n"
    close $f
    after time 1 __dump
}
foreach a {@SECT@} { set ::tot($a) 0 ; debug set_bp $a {} "__cnt $a SECT" }
set ::tot(@TIMI@) 0
debug set_bp @TIMI@ {} "__cnt @TIMI@ TIMI"
set ::tot(@SAVEC@) 0
debug set_bp @SAVEC@ {} "__cnt @SAVEC@ SAVEC"
set ::tot(@NULO@) 0
debug set_bp @NULO@ {} "__cnt @NULO@ NULO"
set ::tot(@BINL@) 0
debug set_bp @BINL@ {} "__cnt @BINL@ BINL"
# 🔴 ARM ON THE VERB ENTRY. The window is "from LOAD's own cell onward", which
# is the subject itself -- not a wall-clock guess at when typing finished.
set ::tot(@VERB@) 0
debug set_bp @VERB@ {} {
    foreach k [array names ::tot] { set ::pre($k) [set ::tot($k)] }
    incr ::tot(@VERB@)
    set ::armed 1
    __ev VERB
}
debug set_bp @RST30@ {} { __ev RST30 }
debug set_bp @CALSLT@ {} {
    incr ::seq
    if {$::armed && $::n < @CAP@} {
        incr ::n
        __lg "$::n CALSLT [__caller] [reg SP] IX=[reg IX] IYH=[expr {[reg IY]>>8}]"
    }
}
after time 1 __dump
'''


def prologue(out_path, sum_path):
    t = TCL
    for k, v in (("@OUT@", out_path), ("@SUM@", sum_path), ("@CAP@", str(CAP)),
                 ("@SECT@", " ".join(str(a) for a in C_SECT)),
                 ("@TIMI@", str(C_TIMI)), ("@SAVEC@", str(C_SAVE)),
                 ("@NULO@", str(C_NULO)), ("@BINL@", str(C_BINL)),
                 ("@VERB@", str(C_VERB)), ("@RST30@", str(RST30)),
                 ("@CALSLT@", str(CALSLT))):
        t = t.replace(k, v)
    return (t,)


def _sub(tok: str) -> int:
    """openMSX reports a NON-EXPANDED slot's secondary as `X`, not a number.

    🔴 THIS COST THE FIRST RUN. `int("X")` is a crash, not a wrong answer, which
    is the good kind of failure -- but it is worth naming why `X` is folded to
    0: an unexpanded primary slot has exactly one subslot and it is subslot 0,
    so `(0, X)` and `(0, 0)` are the same physical page. On this machine slot 0
    (BIOS+BASIC) is unexpanded and slot 3 IS expanded, which is what makes
    `3-1` a meaningful disk-ROM verdict at all.
    """
    return 0 if tok in ("X", "-", "") else int(tok)


def run(tag, lines, dsk):
    import omsx_repl
    fd, out = tempfile.mkstemp(prefix="loadproto-%s-" % tag, suffix=".txt")
    os.close(fd)
    fd, summ = tempfile.mkstemp(prefix="loadproto-%s-sum-" % tag, suffix=".txt")
    os.close(fd)
    caps = omsx_repl.run_cases(REF, [("direct", lines)], batch=False,
                               reset=RESET, boot=BOOT, step=STEP,
                               cap_gap=CAP_GAP, diska=dsk, capture="screen",
                               prologue=prologue(out, summ))
    events, totals, meta = [], {}, {}
    try:
        for ln in open(out):
            p = ln.split()
            if len(p) >= 6:
                events.append(dict(n=int(p[0]), tag=p[1], caller=int(p[2]),
                                   pri=int(p[3]), sec=_sub(p[4]),
                                   sp=int(p[5]), extra=p[6:]))
    except OSError:
        pass
    try:
        for ln in open(summ):
            p = ln.split()
            if p and p[0] == "ARMED":
                meta = dict(armed=int(p[1]), events=int(p[3]))
            elif len(p) >= 3:
                totals[int(p[0])] = (int(p[1]), int(p[2]))
    except OSError:
        pass
    for f in (out, summ):
        if os.path.exists(f):
            os.unlink(f)
    return events, totals, meta, (caps or [None])[0]


def report(tag, events, totals, meta):
    print("\n=== %s ===" % tag)
    print("armed=%s logged=%s events=%d"
          % (meta.get("armed"), meta.get("events"), len(events)))
    if not events:
        print("  (no events inside the window)")
        return {}
    # region histogram per trapped tag -- REGIONS ONLY, never a raw address
    hist: dict = {}
    for e in events:
        r = region(e["caller"], e["pri"], e["sec"])
        hist.setdefault(e["tag"], {}).setdefault(r, 0)
        hist[e["tag"]][r] += 1
    for t in sorted(hist):
        rows = ", ".join("%s=%d" % (r, n)
                         for r, n in sorted(hist[t].items(),
                                            key=lambda kv: -kv[1]))
        print("  %-7s %s" % (t, rows))
    print("  cell totals (total, at-arm):")
    for a in sorted(totals):
        tot, pre = totals[a]
        print("    $%04X  total=%-5d at-arm=%-5d  delta=%d" % (a, tot, pre, tot - pre))
    return hist


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    import loadrun_probe as LR
    tmpd = tempfile.mkdtemp(prefix="loadproto-")
    seeded, _n = LR.seed(REF, RESET, tmpd, "ref")
    dsk, sizes, _per = LR.build(seeded, tmpd, "ref")
    print("images: S=%d B  M=%d B  L=%d B" % (sizes["S"], sizes["M"], sizes["L"]))

    results = {}
    # 🔬 BOTH SIZES, BECAUSE A 3-SECTOR FILE COULD TAKE A SPECIAL PATH. If the
    # region verdict is the same at 3 data sectors and at 29, it is the shape of
    # the loop and not an artefact of a file that happens to fit somewhere.
    for tag, lines in (("quiet", ["REM"]), ("loadS", ['LOAD"S.BAS"']),
                       ("loadL", ['LOAD"L.BAS"'])):
        ev, tot, meta, cap = run(tag, lines, dsk)
        results[tag] = (ev, tot, meta)
        hist = report(tag, ev, tot, meta)
        results[tag] = (ev, tot, meta, hist)
        if cap:
            print("  screen tail: %s" % " | ".join(
                x for x in str(cap).splitlines()[-3:] if x.strip()))

    print("\n=== CONTROLS ===")
    ok = True
    qev = results["quiet"][0]
    # D-HOOKCOUNT's measured per-cell LOAD deltas, by image.
    EXPECT = {"loadS": 8, "loadL": 34}
    lev, ltot, lmeta, lhist = results["loadS"]

    # K3 -- the quiet case must never arm
    if qev:
        print("K3 NEGATIVE  RED: the quiet case logged %d events -- $FE67 fired "
              "with no verb typed, so the window is not the verb's" % len(qev))
        ok = False
    else:
        print("K3 NEGATIVE  green: quiet logged nothing (the window is the verb's)")

    # K1 -- HTIMI's caller is known a priori
    timi = lhist.get("TIMI", {})
    if timi and max(timi, key=timi.get) == "MAIN-P0":
        print("K1 DISCRIM   green: H.TIMI's top-of-stack is MAIN-P0 (%s)" % timi)
    else:
        print("K1 DISCRIM   RED: H.TIMI classified as %s, not MAIN-P0 -- the "
              "classifier cannot be trusted on any other row" % (timi or "nothing"))
        ok = False

    # K2 -- the window must cover the whole verb.
    # 🔴 THIS CONTROL WAS WRONG ON ITS FIRST RUN AND THE MEASUREMENT WAS FINE.
    # D-HOOKCOUNT's "+8 for the 1055 B image" is EACH CELL's own delta -- the
    # table lists $FFCF and $FFD4 as two rows, not one summed row -- and summing
    # them here produced 16 against a threshold of 8 and withheld a verdict that
    # every other control supported. The two cells are 5 bytes apart, i.e. two
    # ADJACENT hook slots, and both read exactly 8: a matched pair entered once
    # per sector each. Compare per cell.
    for case, want in EXPECT.items():
        tot_c = results[case][1]
        deltas = {a: tot_c.get(a, (0, 0))[0] - tot_c.get(a, (0, 0))[1]
                  for a in C_SECT}
        shown = {"$%04X" % k: v for k, v in deltas.items()}
        if all(v == want for v in deltas.values()):
            print("K2 CONTINUITY green (%s): each sector cell shows %s inside "
                  "the window == D-HOOKCOUNT's measured delta" % (case, shown))
        else:
            print("K2 CONTINUITY RED (%s): sector-cell deltas %s, D-HOOKCOUNT "
                  "measured %d each -- the window missed part of the verb"
                  % (case, shown, want))
            ok = False

    # K4 -- the disk ROM must actually be seen in page 1
    seen = {(e["pri"], e["sec"]) for e in lev if (e["caller"] >> 14) == 1}
    if (3, 1) in seen:
        print("K4 SLOT      green: page 1 observed selected to slot 3-1 (the "
              "disk ROM) -- get_selected_slot is not returning a constant")
    else:
        print("K4 SLOT      RED: the disk ROM was never observed in page 1 "
              "(page-1 slots seen: %s)" % sorted(seen))
        ok = False

    # 🔬 CROSS-CHECK A -- NESTING. If the sector calls happen INSIDE the verb
    # handler, their stack is deeper (SP lower) than the verb entry's. This is a
    # different quantity from the caller region and can disagree with it; two
    # measurements of one claim is the point.
    vsp = [e["sp"] for e in lev if e["tag"] == "VERB"]
    ssp = [e["sp"] for e in lev if e["tag"] == "SECT"]
    if vsp and ssp:
        print("\n=== CROSS-CHECK A: nesting ===")
        deeper = sum(1 for x in ssp if x < vsp[0])
        print("  verb-entry SP vs sector-service SP: %d of %d sector entries sit "
              "DEEPER than the verb entry" % (deeper, len(ssp)))
        print("  -> the sector work is %s the verb call"
              % ("NESTED INSIDE" if deeper == len(ssp) else "NOT consistently inside"))
        # 🔴 AND THE SAME TEST FOR THE OTHER MAIN-CALLED CELLS. A cell whose
        # caller is MAIN can still be reached from INSIDE the verb call, if the
        # disk side crossed back and main then called it. Depth separates
        # "sequential step in main" from "nested under the verb" where the
        # caller region cannot.
        # ⚠️ AND A LABEL THIS REPORT DELIBERATELY DOES NOT APPLY. For a cell
        # whose caller is MAIN, a deeper stack does NOT mean "inside the verb
        # call" -- main can descend into its own subroutines to any depth
        # without the verb call still being open. Depth alone cannot separate
        # those, so the relation is printed and not translated. It is only for
        # SECT, whose caller is independently the DISK ROM, that depth plus
        # region together place the work below the crossing.
        for t in ("NULO", "BINL"):
            xs = [e["sp"] for e in lev if e["tag"] == t]
            if xs:
                d = sum(1 for x in xs if x < vsp[0])
                print("  %-5s: %d of %d entries sit deeper than the verb entry "
                      "(caller is MAIN, so this is main's own descent -- NOT "
                      "evidence of nesting under the crossing)" % (t, d, len(xs)))

    # 🔬 CROSS-CHECK B -- WHERE THE DISK SIDE CALLS OUT TO. CALSLT takes the
    # target slot in IY's high byte and the address in IX. The slot BYTE format
    # is public (TH §2): bit7 expanded, bits1-0 primary, bits3-2 secondary. We
    # decode it to a SLOT, pair it with IX's PAGE, and print the region -- never
    # the address. This is the `calbak` direction: does the disk ROM call back
    # into main during a load?
    if any(e["tag"] == "CALSLT" for e in lev):
        print("\n=== CROSS-CHECK B: where the disk side calls out to ===")
        tgt: dict = {}
        for e in lev:
            if e["tag"] != "CALSLT":
                continue
            ix = iyh = None
            for x in e["extra"]:
                if x.startswith("IX="):
                    ix = int(x[3:])
                elif x.startswith("IYH="):
                    iyh = int(x[4:])
            if ix is None or iyh is None:
                continue
            pri, sec = iyh & 3, ((iyh >> 2) & 3) if (iyh & 0x80) else 0
            frm = region(e["caller"], e["pri"], e["sec"])
            to = region(ix, pri, sec)
            tgt["%s -> %s" % (frm, to)] = tgt.get("%s -> %s" % (frm, to), 0) + 1
        for k, v in sorted(tgt.items(), key=lambda kv: -kv[1]):
            print("  %-22s %d" % (k, v))

    # 🔑 THE CROSSING CENSUS -- and the headline here is a NEGATIVE.
    print("\n=== CROSSING DIRECTIONS OBSERVED (both public inter-slot entries) ===")
    cross: dict = {}
    for e in lev:
        if e["tag"] not in ("RST30", "CALSLT"):
            continue
        cross.setdefault("%s from %s" % (e["tag"],
                                         region(e["caller"], e["pri"], e["sec"])), 0)
        cross["%s from %s" % (e["tag"],
                              region(e["caller"], e["pri"], e["sec"]))] += 1
    for k, v in sorted(cross.items(), key=lambda kv: -kv[1]):
        print("  %-22s %d" % (k, v))
    if not any(k.endswith("from DISK") and "CALSLT" not in k for k in cross) \
            and not any(e["tag"] == "CALSLT" and
                        region(e["caller"], e["pri"], e["sec"]) == "DISK" and
                        "MAIN" in str(e["extra"]) for e in lev):
        print("  -> NO disk-side call INTO main was observed at either public "
              "entry for the whole load.")

    # 🔑 THE ANSWER, stated only if every control held
    print("\n=== THE QUESTION §6.6r COULD NOT ANSWER ===")
    if not ok:
        print("WITHHELD: a control is red, so no region verdict is reportable.")
    else:
        for case in EXPECT:
            h = results[case][3].get("SECT", {})
            if not h:
                print("%-6s WITHHELD: no sector-service entries logged" % case)
                continue
            print("%-6s per-sector service callers: %s -> the sector loop is "
                  "driven from %s" % (case, h, max(h, key=h.get)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
