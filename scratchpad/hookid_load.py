#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-LOADHOOK: WHICH hook cell is `LOAD`'s?  Un-claim one and see who notices.

Step 9 of `disk/docs/spec-diskcode-eviction.md` is blocked on this and on nothing
else (§6.6h). The tokenised-LOAD stream layer is already in `disk.rom` and
`fat_io_getbyte` resolves locally there; the hook body is designed and needs no
call-backs. What is missing is the ADDRESS to install it at. `disk/equates.inc`
names sixteen hook cells and none of them is LOAD's.

THE METHOD, unchanged from `scratchpad/hookid_probe.py` (which answered FIELD,
LSET and RSET the same way): a claimed hook holds `F7 <slot> <lo> <hi> C9`; an
UNCLAIMED one is a bare `RET`. `POKE <cell>,201` un-claims it live on the
reference, and the verb that then changes its answer owns that cell. Black-box
throughout -- a POKE and a reading. 🔴 NO REFERENCE INSTRUCTION IS EVER READ:
`disk/docs/expansion-protocol.md` §2 permits a cell's SLOT and IDIOM, and the
target addresses are noted and never followed.

🔴 THE SUBJECT DESTROYS THE INSTRUMENT, WHICH IS WHY MERGE WAS NEVER MEASURED.
`hookid_probe.py` records that MERGE "merges into the RUNNING PROGRAM, so it
destroys the probe that asks the question". `LOAD` REPLACES the running program,
which is worse. The way through is to choose a case that FAILS BEFORE it touches
the program: `LOAD"<missing>"` should raise ERR 53 with the program intact, so an
`ON ERROR` trap can still print. ⚠️ **That is ESTABLISHED by round 0, not
assumed** -- if the baseline does not read 53 the probe refuses and measures
nothing.

⚠️ AND A HIT MAY BE SILENCE. If un-claiming LOAD's cell drops the verb onto the
CASSETTE path, the machine may sit waiting for tape rather than raising -- so a
row that prints NOTHING is a CHANGE, not an apparatus failure, and is scored as a
hit. Naming that in advance is the point: an unnamed outcome reads as no outcome
[[an-unnamed-outcome-reads-as-no-outcome]].

🔴 CONTROLS -- the same three that made the FIELD answer trustworthy:
  base      poke NOTHING: `LOAD"<missing>"` must read ERR 53, twice over --
            it proves the verb raises AND that the program survives to report.
  ctrl_file poke `H_FILE $FE7B`, a cell we have ALREADY named, and run `FILES`.
            It must flip ERR 70 -> ERR 5. THIS is what proves the METHOD; without
            it a flip in an unnamed cell proves nothing.
  ctrl_cross poke that same `H_FILE` and run the LOAD case. It must NOT move --
            if un-claiming any hook broke every verb, a hit would be meaningless.

⚠️ A POKE IS STICKY FOR THE WHOLE BOOT, so every case gets its own machine
(`batch=False`) and no set is ever reused.
"""
import os, re, subprocess, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                              # noqa: E402

REF = "National_CF-3300"
REF_KW = dict(boot=14.0, reset=("", "SCREEN 0"), batch=False)
H_FILE = 0xFE7B                       # already named -- the method's control
MISSING = 'LOAD"NOSUCH.BAS"'
BASE_ERR = 53                         # File not found, established by round 0

# The SIXTEEN cells disk/equates.inc already names. Parsed, not transcribed, so
# this cannot drift from the source of truth.
EQUATES = os.path.join(REPO, "disk", "equates.inc")


def named_cells():
    out = {}
    for ln in open(EQUATES):
        m = re.match(r"(H_[A-Z]+)\s+equ\s+\$([0-9A-Fa-f]{4})", ln)
        if m:
            out[int(m.group(2), 16)] = m.group(1)
    return out


def claimed_cells():
    """The cells the reference's disk ROM claims, READ THROUGH THE DEBUGGER.

    🔴 NOT through the screen: D-CFARCH found a BASIC `PEEK` sweep reported 27
    when the real figure is 35, because its single-line output was TRUNCATED --
    a census taken through the screen is bounded by the screen.
    """
    out = os.path.join(tempfile.mkdtemp(prefix="loadhook_"), "cells.txt")
    tcl = out + ".tcl"
    # THE SCAN IS `scratchpad/cf3300_arch_probe.py`'s, DELIBERATELY UNCHANGED --
    # three details of it are load-bearing and the first cut of this function got
    # all three wrong, returning ZERO claimed cells:
    #   * `after time 40` -- the hooks do not exist at machine creation. The disk
    #     ROM's INIT writes them during boot, so a scan at t=0 reads a table of
    #     zeros and reports an empty world.
    #   * `debug read memory`, not `peek`.
    #   * STEP BY 1, not by 5. A cell is five bytes, but nothing promises the
    #     table starts aligned at $FD9A -- stepping 5 tests one phase out of five
    #     and silently misses the other four.
    # The refusal below is what caught it: an empty match set is not a finding.
    open(tcl, "w").write(
        'after time 40 {\n'
        '  set f [open "%s" w]\n'
        '  for {set a 64922} {$a <= 65487} {incr a} {\n'
        '    if {[debug read memory $a] == 247 &&\n'
        '        [debug read memory [expr {$a+4}]] == 201} {\n'
        '      puts $f [format "%%04X" $a]\n'
        '    }\n'
        '  }\n'
        '  close $f\n'
        '  exit\n'
        '}\n' % out)
    subprocess.run(["openmsx", "-machine", REF, "-command", "source %s" % tcl],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.exists(out):
        sys.exit("REFUSING: openMSX produced no census -- nothing was measured")
    return [int(l, 16) for l in open(out).read().split() if l.strip()]


def prog(pokes, stmt):
    b = [None] + ["POKE %d,201" % a for a in pokes] + \
        [stmt, 'PRINT"<X>":END', 'PRINT"<E";ERR;">":END']
    b[0] = "ON ERROR GOTO %d" % (10 * len(b))
    return b


def read_err(cap):
    """The ERR the trap printed, or None for 'nothing / no error'.

    🔴 None IS A READING HERE, not a failure: see the header. A LOAD that falls
    to the cassette path may never come back.
    """
    m = re.search(r"<E\s*(\d+)\s*>", cap or "")
    if m:
        return int(m.group(1))
    return "OK" if "<X>" in (cap or "") else None


def selftest():
    """The READER is what a wrong answer would come through, so it is tested."""
    ok1 = read_err("junk <E 53 > junk") == 53
    print("%s S1 an ERR trap reading is parsed" % ("PASS" if ok1 else "FAIL"))
    ok2 = read_err("<X>") == "OK"
    print("%s S2 a no-error run reads OK, not an ERR" % ("PASS" if ok2 else "FAIL"))
    # the NEGATIVE control: silence must NOT be parsed as the baseline, or a
    # hung LOAD would be scored as "no change" and the hit would be invisible.
    ok3 = read_err("") is None and read_err(None) is None
    print("%s S3 silence reads None -- NOT %d -- so a hung LOAD cannot pass as "
          "the baseline" % ("PASS" if ok3 else "FAIL", BASE_ERR))
    ok4 = read_err("<E 5 >") == 5 and read_err("<E 5 >") != BASE_ERR
    print("%s S4 a DIFFERENT ERR is not the baseline" % ("PASS" if ok4 else "FAIL"))
    nc = named_cells()
    ok5 = nc.get(0xFE7B) == "H_FILE" and nc.get(0xFE2B) == "H_FIELD"
    print("%s S5 the named-cell set is PARSED from disk/equates.inc (%d cells)"
          % ("PASS" if ok5 else "FAIL", len(nc)))
    return 0 if all((ok1, ok2, ok3, ok4, ok5)) else 1


def run(cases):
    caps = omsx_repl.run_cases(REF, [c[1] for c in cases], capture="screen",
                               **REF_KW)
    return [(cases[i][0], read_err(caps[i])) for i in range(len(cases))]


def main():
    if "--selftest" in sys.argv:
        return selftest()

    named = named_cells()
    claimed = claimed_cells()
    cand = [a for a in claimed if a not in named]
    print("claimed hook cells (debugger): %d" % len(claimed))
    print("named in disk/equates.inc:     %d" % len(named))
    print("candidates for LOAD:           %d\n" % len(cand))
    if not cand:
        sys.exit("REFUSING: no candidate cells -- the census or the parse is "
                 "wrong, and an empty match set is not a finding")

    # --- ROUND 0: establish the baseline and prove the method ---------------
    r0 = run([
        ("base",       prog([], MISSING)),
        ("ctrl_file",  prog([H_FILE], "FILES")),
        ("ctrl_cross", prog([H_FILE], MISSING)),
    ])
    for n, v in r0:
        print("  %-11s -> %s" % (n, v))
    d = dict(r0)
    if d["base"] != BASE_ERR:
        sys.exit("\nREFUSING: `%s` read %r, not ERR %d. The whole method needs "
                 "a case that FAILS BEFORE it replaces the program; this one "
                 "does not, so nothing below would mean anything."
                 % (MISSING, d["base"], BASE_ERR))
    if d["ctrl_file"] != 5:
        sys.exit("\nREFUSING: un-claiming the NAMED cell $%04X did not flip "
                 "FILES to ERR 5 (read %r). The METHOD is not working here, so "
                 "a flip anywhere else would prove nothing." % (H_FILE, d["ctrl_file"]))
    if d["ctrl_cross"] != BASE_ERR:
        sys.exit("\nREFUSING: un-claiming FILES's cell MOVED the LOAD case "
                 "(%r). Un-claiming any hook would then look like a hit."
                 % d["ctrl_cross"])
    print("\n🟢 round 0: the case raises ERR %d with the program intact, the "
          "method flips a named cell, and it does NOT flip this verb.\n" % BASE_ERR)

    # --- ROUND 1: every candidate, one at a time ----------------------------
    rows = run([("$%04X" % a, prog([a], MISSING)) for a in cand])
    print("| cell | LOAD\"missing\" reads | |")
    print("|---|---|---|")
    hits = []
    for n, v in rows:
        hit = v != BASE_ERR
        if hit:
            hits.append(n)
        print("| %s | %s | %s |" % (n, v, "🔴 **CHANGED**" if hit else "—"))
    print()
    if len(hits) == 1:
        print("🟢 **LOAD's HOOK CELL IS %s** -- it is the only candidate whose "
              "un-claiming moves the verb." % hits[0])
        return 0
    if not hits:
        print("🔴 NO CANDIDATE MOVED IT. Either LOAD is not hooked at all on "
              "this machine, or its cell is one of the SIXTEEN already named -- "
              "which would mean a cell serves two verbs. Neither is assumable; "
              "this is a finding, not a failure.")
        return 1
    print("🔴 %d CANDIDATES MOVED IT (%s). A verb with two cells is possible "
          "but must be shown, not chosen -- re-run each hit ALONE before naming "
          "one." % (len(hits), ", ".join(hits)))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
