#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-SELECTOR: WHERE is the verb selector at the main->disk crossing?

D-CROSSABI (§6.6v) found the crossing -- `$FE5D`, the one claimed cell every file
verb enters -- and found that its REGISTERS carry nothing per-file: AF, BC, DE,
HL, IX and IY are invariant across four loads, including two files with the same
bytes under different names and a 3-sector against a 29-sector file. So whatever
tells the disk side WHICH verb it is serving travels in RAM. This looks for it.

🎯 THE METHOD IS A DIFFERENTIAL AT ONE INSTANT. At the `$FE5D` breakpoint --
before the crossing runs -- dump a band of RAM. Do that for several cases and
subtract:

    verb-dependent   LOAD"A.BAS" vs MERGE"A.BAS"   same file, same name
    name-dependent   LOAD"A.BAS" vs LOAD"QQQQQQQQ.BAS"  same BYTES, other name
    size-dependent   LOAD"S.BAS" vs LOAD"L.BAS"    3 vs 29 data sectors

    SELECTOR CANDIDATES = verb-dependent MINUS name-dependent MINUS size-dependent

A cell that moves with the VERB but not with the file's name or size is what a
selector is. Subtracting the other two is what keeps the answer from being the
typed input line, which differs in every one of these cases and is the obvious
false positive.

🔴 THE CONTROL THAT MAKES ALL OF THAT MEAN ANYTHING IS DETERMINISM. openMSX is
deterministic and `omsx_repl` types at fixed emulated times, so TWO RUNS OF ONE
CASE MUST PRODUCE BYTE-IDENTICAL DUMPS. If they do, every difference between two
cases was caused by the case and nothing else -- no noise floor to subtract, no
judgement about which differences are "real". If they do NOT, this whole
subtraction is invalid and the probe says so instead of reporting candidates.
⚠️ That control is cheap and it is the one thing this measurement cannot do
without, which is why it runs the same case twice on purpose.

🔴 AND TWO NEGATIVES:
  K3  the `quiet` case types no verb, so `$FE5D` is never entered and there must
      be NO dump at all.
  K9  the name-dependent set must be NON-EMPTY. `LOAD"A.BAS"` and
      `LOAD"QQQQQQQQ.BAS"` differ in the typed line and in the file name, so if
      subtracting them removes nothing, the band is not covering the memory the
      verb actually uses and an empty candidate set would mean nothing.

🔴 CLEAN ROOM. RAM only, at a breakpoint on a RAM address in the published hook
table. No ROM byte is read, no hook target is followed, nothing is single-stepped
into ROM, nothing is disassembled. Addresses reported are RAM work-area addresses
of the MACHINE, not of the reference ROM.
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

C_NULO = 0xFE5D            # the crossing (§6.6v): claimed, every file verb
BAND_LO, BAND_LEN = 0xE000, 0x2000     # $E000..$FFFF -- work area + hook table

ASCII_BAS = b"10 REM Z\r\n20 REM Z\r\n"


TCL = r'''
set ::done 0
proc __snap {} {
    if {$::done} return
    set ::done 1
    set b [debug read_block memory @LO@ @LEN@]
    binary scan $b H* hx
    set f [open {@OUT@} w]
    puts $f $hx
    close $f
}
debug set_bp @CELL@ {} { __snap }
'''


def prologue(out_path):
    t = TCL
    for k, v in (("@OUT@", out_path), ("@LO@", str(BAND_LO)),
                 ("@LEN@", str(BAND_LEN)), ("@CELL@", str(C_NULO))):
        t = t.replace(k, v)
    return (t,)


def run(tag, lines, dsk):
    import omsx_repl
    fd, out = tempfile.mkstemp(prefix="selector-%s-" % tag, suffix=".txt")
    os.close(fd)
    omsx_repl.run_cases(REF, [("direct", lines)], batch=False, reset=RESET,
                        boot=BOOT, step=STEP, cap_gap=CAP_GAP, diska=dsk,
                        capture="screen", prologue=prologue(out))
    blob = None
    try:
        h = open(out).read().strip()
        if h:
            blob = bytes.fromhex(h)
    except (OSError, ValueError):
        blob = None
    if os.path.exists(out):
        os.unlink(out)
    return blob


def diff(a, b):
    """Addresses where two dumps differ. Empty set when either is missing."""
    if not a or not b:
        return set()
    return {BAND_LO + i for i in range(min(len(a), len(b))) if a[i] != b[i]}


def runs(addrs):
    """Contiguous address runs, as (start, length), for readable reporting."""
    out, cur = [], []
    for a in sorted(addrs):
        if cur and a == cur[-1] + 1:
            cur.append(a)
        else:
            if cur:
                out.append((cur[0], len(cur)))
            cur = [a]
    if cur:
        out.append((cur[0], len(cur)))
    return out


# ---------------------------------------------------------------- phase 2
# 🔴 A CORRELATION IS NOT A MECHANISM, AND THIS PROJECT HAS PAID FOR THAT ONCE
# ALREADY (§6.6t: nine builds agreeing that an 18th hook cannot be installed,
# with no mechanism, downgraded to a correlation and parked). A byte that tracks
# the verb perfectly still has to be SHOWN to be read by the disk side. A
# `read_mem` watchpoint says who reads it: at the moment it fires, PC is the
# instruction doing the read, and PC's page plus that page's selected slot names
# the ROM it is in.
CONFIRM_TCL = r"""
proc __w16 {a} { expr {[debug read memory $a] + 256*[debug read memory [expr {$a+1}]]} }
set ::win 0
set ::rd 0
set ::lf [open {@OUT@} w]
proc __reg {} {
    set pc [reg PC]
    set p [expr {$pc >> 14}]
    set s [get_selected_slot $p]
    set sec [lindex $s 1]
    if {$sec eq ""} { set sec 0 }
    return "$pc [lindex $s 0] $sec"
}
debug set_bp @CELL@ {} { set ::win 1 ; puts $::lf "WIN-OPEN" ; flush $::lf }
debug set_bp [expr {@CELL@ + 4}] {} { set ::win 0 ; puts $::lf "WIN-SHUT" ; flush $::lf }
debug set_watchpoint read_mem @WATCH@ {} {
    incr ::rd
    if {$::rd < 200} { puts $::lf "READ $::win [__reg]" ; flush $::lf }
}
"""


def confirm(tag, lines, dsk, watch):
    import omsx_repl
    fd, out = tempfile.mkstemp(prefix="selconf-%s-" % tag, suffix=".txt")
    os.close(fd)
    t = CONFIRM_TCL
    for k, v in (("@OUT@", out), ("@CELL@", str(C_NULO)), ("@WATCH@", str(watch))):
        t = t.replace(k, v)
    omsx_repl.run_cases(REF, [("direct", lines)], batch=False, reset=RESET,
                        boot=BOOT, step=STEP, cap_gap=CAP_GAP, diska=dsk,
                        capture="screen", prologue=(t,))
    reads, marks = [], []
    try:
        for ln in open(out):
            p = ln.split()
            if p and p[0] == "READ" and len(p) >= 5:
                reads.append(dict(win=int(p[1]), pc=int(p[2]), pri=int(p[3]),
                                  sec=0 if p[4] == "X" else int(p[4])))
            elif p:
                marks.append(p[0])
    except OSError:
        pass
    if os.path.exists(out):
        os.unlink(out)
    return reads, marks


def pcregion(r):
    """The ROM a read came from. Pages 2-3 are RAM whatever the slot says."""
    page = r["pc"] >> 14
    if page >= 2:
        return "RAM"
    if r["pri"] == 0:
        return "MAIN-P0" if page == 0 else "MAIN-P1"
    if r["pri"] == 3 and r["sec"] == 1:
        return "DISK"
    return "SLOT%s-%s" % (r["pri"], r["sec"])


def missing_dumps(dumps, tags):
    """The cases that produced NO dump. Extracted so it can be TESTED.

    🔴 A MISSING DUMP SUBTRACTS TO AN EMPTY SET and would be reported as the
    cleanest row in the table -- the quietest possible way for this probe to
    lie. So the caller refuses on any, and this function is what the selftest
    drives.
    ⚠️ THE FIRST ARM WRITTEN FOR THIS WAS SELF-DEFEATING: it grepped the probe's
    own source for the refusal's message, and the needle was in the arm itself,
    so the file always contained it and the arm could never go red. Test the
    BEHAVIOUR, never the presence of a string in your own text.
    """
    # `not blob` rather than `is None`: an EMPTY dump is not None and would
    # subtract to an empty difference set exactly like a real one.
    return [t for t in tags if not dumps.get(t)]


def show(blob, addr, n=1):
    if blob is None:
        return "??"
    i = addr - BAND_LO
    return " ".join("%02X" % c for c in blob[i:i + n])


def selftest() -> int:
    ok = True
    A = bytes([0, 1, 2, 3, 4, 5, 6, 7])
    B = bytes([0, 9, 2, 3, 9, 9, 6, 7])
    d = diff(A, B)
    if d != {BAND_LO + 1, BAND_LO + 4, BAND_LO + 5}:
        print("SELFTEST RED: diff() found %r" % sorted(d))
        ok = False
    if runs(d) != [(BAND_LO + 1, 1), (BAND_LO + 4, 2)]:
        print("SELFTEST RED: runs() gave %r" % runs(d))
        ok = False
    # 🔴 NEGATIVE: a MISSING dump must not read as "no differences". A case whose
    # breakpoint never fired would otherwise subtract to nothing and look like
    # the cleanest result in the table.
    if diff(A, None) != set() or diff(None, None) != set():
        print("SELFTEST RED: a missing dump did not yield an empty set")
        ok = False
    # ...which is only safe because the caller REFUSES on a missing dump. Drive
    # that guard, positively and negatively.
    if missing_dumps({"a": A, "b": None, "c": B}, ["a", "b", "c"]) != ["b"]:
        print("SELFTEST RED: the missing-dump guard did not name the case whose "
              "dump is absent")
        ok = False
    if missing_dumps({"a": A, "b": B}, ["a", "b"]) != []:
        print("SELFTEST RED: the missing-dump guard fires when nothing is "
              "missing, which would refuse every run")
        ok = False
    # 🔴 AND AN EMPTY dump must count as missing too -- b"" is falsy but is NOT
    # None, and it would subtract to an empty set exactly like a real one.
    if missing_dumps({"a": b""}, ["a"]) != ["a"]:
        print("SELFTEST RED: an EMPTY dump was not treated as missing")
        ok = False
    # 🔴 NEGATIVE: unequal lengths must not silently compare only the overlap
    # without that being deliberate -- assert the documented behaviour.
    if diff(bytes([1, 2, 3]), bytes([1, 2])) != set():
        print("SELFTEST RED: short-dump comparison is not the overlap")
        ok = False
    # 🔴 pcregion() carries the SAME slot-blindness negative as D-LOADPROTO's
    # classifier: $4000-$7FFF is main page 1 AND the disk ROM, so one address
    # under two slots must give two answers or every DISK verdict is unfounded.
    if pcregion(dict(pc=0x6A31, pri=0, sec=0)) == pcregion(dict(pc=0x6A31, pri=3, sec=1)):
        print("SELFTEST RED: pcregion() is SLOT-BLIND")
        ok = False
    for pc, pri, sec, want in ((0x0159, 0, 0, "MAIN-P0"), (0x6A31, 0, 0, "MAIN-P1"),
                               (0x6A31, 3, 1, "DISK"), (0xF41F, 0, 0, "RAM"),
                               (0x9000, 3, 0, "RAM")):
        if pcregion(dict(pc=pc, pri=pri, sec=sec)) != want:
            print("SELFTEST RED: pcregion(%04X,%s,%s)=%s want %s"
                  % (pc, pri, sec, pcregion(dict(pc=pc, pri=pri, sec=sec)), want))
            ok = False
    print("SELFTEST GREEN" if ok else "SELFTEST RED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    if ap.parse_args().selftest:
        return selftest()

    import loadrun_probe as LR
    tmpd = tempfile.mkdtemp(prefix="selector-")
    seeded, _n = LR.seed(REF, RESET, tmpd, "ref")
    dsk, sizes, _per = LR.build(seeded, tmpd, "ref",
                                extra={"A       BAS": ASCII_BAS,
                                       "QQQQQQQQBAS": ASCII_BAS})
    print("images: S=%d B  L=%d B  A=Q=%d B" % (sizes["S"], sizes["L"],
                                                len(ASCII_BAS)))

    cases = [
        ("quiet",   ["REM"]),
        ("loadA",   ['LOAD"A.BAS"']),
        ("loadA2",  ['LOAD"A.BAS"']),          # the determinism control
        ("mergeA",  ['MERGE"A.BAS"']),
        ("loadQ",   ['LOAD"QQQQQQQQ.BAS"']),
        ("loadS",   ['LOAD"S.BAS"']),
        ("loadL",   ['LOAD"L.BAS"']),
        ("saveT",   ['SAVE"T.BAS"']),
        ("openA",   ['OPEN"A.BAS"FOR INPUT AS#1', "CLOSE"]),
    ]
    dumps = {}
    for tag, lines in cases:
        dumps[tag] = run(tag, lines, dsk)
        print("  %-8s dump: %s" % (tag, "%d B" % len(dumps[tag])
                                   if dumps[tag] else "NONE"))

    print("\n=== CONTROLS ===")
    ok = True
    if dumps["quiet"] is not None:
        print("K3 NEGATIVE   RED: the quiet case produced a dump -- $FE5D fired "
              "with no verb typed")
        ok = False
    else:
        print("K3 NEGATIVE   green: no dump in the quiet case")

    gone = missing_dumps(dumps, [t for t, _ in cases if t != "quiet"])
    if gone:
        print("REFUSING: no dump for %s -- a missing dump subtracts to an empty "
              "set and would be reported as the cleanest row in the table"
              % ", ".join(gone))
        return 1

    det = diff(dumps["loadA"], dumps["loadA2"])
    if det:
        print("K8 DETERMINISM RED: two runs of the SAME case differ in %d byte(s)"
              " -- there is a noise floor, so no difference between two "
              "different cases can be attributed to the case" % len(det))
        ok = False
    else:
        print("K8 DETERMINISM green: two runs of one case are byte-identical, so "
              "every difference below was caused by the case")

    name_dep = diff(dumps["loadA"], dumps["loadQ"])
    size_dep = diff(dumps["loadS"], dumps["loadL"])
    verb_dep = diff(dumps["loadA"], dumps["mergeA"])
    if not name_dep:
        print("K9 COVERAGE   RED: two different file names produced identical "
              "RAM -- the band does not cover what the verb uses")
        ok = False
    else:
        print("K9 COVERAGE   green: the name differential is non-empty (%d byte"
              "(s) over %d run(s))" % (len(name_dep), len(runs(name_dep))))

    print("\n=== THE DIFFERENTIALS ===")
    print("  verb-dependent  LOAD vs MERGE, same file : %4d bytes, %d runs"
          % (len(verb_dep), len(runs(verb_dep))))
    print("  name-dependent  A vs QQQQQQQQ, same bytes: %4d bytes, %d runs"
          % (len(name_dep), len(runs(name_dep))))
    print("  size-dependent  S vs L, 3 vs 29 sectors  : %4d bytes, %d runs"
          % (len(size_dep), len(runs(size_dep))))

    if not ok:
        print("\nWITHHELD: a control is red, so no candidate is reportable.")
        return 1

    cand = verb_dep - name_dep - size_dep
    print("\n=== SELECTOR CANDIDATES (verb-dependent, file-independent) ===")
    print("  %d byte(s) in %d run(s)" % (len(cand), len(runs(cand))))
    order = ["loadA", "mergeA", "loadS", "loadL", "loadQ", "saveT", "openA"]
    for start, n in runs(cand):
        if n > 16:
            print("  $%04X..$%04X (%d B) -- too wide to be a selector; reported "
                  "as a region" % (start, start + n - 1, n))
            continue
        print("  $%04X (%d B)" % (start, n))
        for t in order:
            print("      %-7s %s" % (t, show(dumps[t], start, n)))

    # 🔑 PHASE 2 -- WHO READS IT. A one-byte candidate that tracks the verb is
    # only the selector if the DISK side reads it.
    narrow = [(st, n) for st, n in runs(cand) if n == 1]
    if not narrow:
        print("\nNo single-byte candidate to confirm.")
        return 0
    watch = narrow[0][0]
    print("\n=== PHASE 2: WHO READS $%04X ===" % watch)
    for tag, lines in (("loadA", ['LOAD"A.BAS"']), ("mergeA", ['MERGE"A.BAS"'])):
        reads, marks = confirm(tag, lines, dsk, watch)
        if not reads:
            print("  %-7s RED: the watchpoint never fired -- it is misconfigured,"
                  " and silence here is not evidence of anything" % tag)
            continue
        hist, whist = {}, {}
        for r in reads:
            g = pcregion(r)
            hist[g] = hist.get(g, 0) + 1
            if r["win"]:
                whist[g] = whist.get(g, 0) + 1
        print("  %-7s window %s | all reads: %s | INSIDE the crossing: %s"
              % (tag, "opened+shut" if marks.count("WIN-OPEN") else "NEVER OPENED",
                 hist, whist or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
