#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-HOOKCENSUS: which hook cells does each machine CLAIM? Reference vs zerobas.

`disk/docs/expansion-protocol.md` §8.1 records that the reference claims 35 of
the 118 published slots, and §8 is otherwise a description of the reference
alone. The gap analysis needs the same census on OUR machine, taken the same way
and by the same code, so the two sides are comparable rather than one measured
and one read off a source table.

🎯 WHY MEASURE OUR OWN SIDE INSTEAD OF READING `hook_tab`. The table is what the
source INTENDS to install; the census is what the machine ENDS UP with. Those
have already diverged once in this project's history (a build switch that had
been dead since D-DUPSPAN2), and a table row does not prove an installed cell.

🔴 CONTROLS -- a two-sided known-answer pair on EACH machine, per
[[validate-a-filter-with-two-known-answers]].
  reference: `$FD9F` (H.TIMI) must be CLAIMED -- expansion-protocol.md §2
             observed its `F7 87 ...` directly; `$FE67` must be UNCLAIMED --
             §6.6v measured it as a bare `C9`.
  zerobas:   `$FE7B` (H_FILE) must be CLAIMED -- it is in `hook_tab`; `$FE5D`
             (H_FOPEN) must be UNCLAIMED -- `disk/kernel.asm` records that the
             row was built and BACKED OUT.
Each pair catches a reader that is wrong in one direction; neither alone does.

🔴 CLEAN ROOM. `disk/docs/expansion-protocol.md` §2 permits reading a hook cell's
five bytes for its SLOT and its IDIOM. This reads the FIRST byte of each
published slot and classifies it as claimed (`F7`) or not (`C9`), for every slot.
No target address is followed, no ROM byte is read, nothing is disassembled.
"""
import argparse
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))

RESET = ("", "SCREEN 0", "CLOSE", "NEW", "CLS")
BOOT, STEP, CAP_GAP = 14.0, 10.0, 8.0
HOOK_LO, HOOK_HI, HOOK_STEP = 0xFD9A, 0xFFE7, 5

REF = "National_CF-3300"
ZB = "C-BIOS_MSX1_EU_BASIC_DISK"

# known answers, per machine: (must be claimed, must be unclaimed)
KNOWN = {REF: (0xFD9F, 0xFE67), ZB: (0xFE7B, 0xFE5D)}

# what `hook_tab` in disk/kernel.asm intends to install (disk/equates.inc)
ZB_TABLE = {
    0xFE12: "H_DSKF", 0xFE30: "H_MKI", 0xFE35: "H_MKS", 0xFE3A: "H_MKD",
    0xFE3F: "H_CVI", 0xFE44: "H_CVS", 0xFE49: "H_CVD", 0xFDF9: "H_NAME",
    0xFDFE: "H_KILL", 0xFDEF: "H_DSKO", 0xFE17: "H_DSKI", 0xFE08: "H_COPY",
    0xFEFD: "H_ERRP", 0xFE21: "H_LSET", 0xFE26: "H_RSET", 0xFE2B: "H_FIELD",
    0xFE7B: "H_FILE",
}


TCL = r'''
proc __dump {} {
    set f [open {@OUT@} w]
    for {set a @LO@} {$a <= @HI@} {incr a @STEP@} {
        puts $f "S $a [format %02X [debug read memory $a]]"
    }
    close $f
    after time 1 __dump
}
after time 1 __dump
'''


def census(machine):
    import omsx_repl
    fd, out = tempfile.mkstemp(prefix="hookcensus-", suffix=".txt")
    os.close(fd)
    t = TCL
    for k, v in (("@OUT@", out), ("@LO@", str(HOOK_LO)), ("@HI@", str(HOOK_HI)),
                 ("@STEP@", str(HOOK_STEP))):
        t = t.replace(k, v)
    omsx_repl.run_cases(machine, [("direct", ["REM"])], batch=False,
                        reset=RESET, boot=BOOT, step=STEP, cap_gap=CAP_GAP,
                        capture="screen", prologue=(t,))
    cells = {}
    try:
        for ln in open(out):
            p = ln.split()
            if len(p) >= 3 and p[0] == "S":
                cells[int(p[1])] = p[2]
    except (OSError, ValueError):
        pass
    if os.path.exists(out):
        os.unlink(out)
    return cells


def claimed(cells):
    return {a for a, b in cells.items() if b == "F7"}


def check_known(machine, cells):
    """Both arms of the known-answer pair. -> (ok, message)."""
    must, mustnot = KNOWN[machine]
    c = claimed(cells)
    if must not in c:
        return False, ("$%04X must be CLAIMED on %s and reads %s"
                       % (must, machine, cells.get(must, "??")))
    if mustnot in c:
        return False, ("$%04X must be UNCLAIMED on %s and reads F7"
                       % (mustnot, machine))
    return True, ("$%04X claimed and $%04X unclaimed, both as known in advance"
                  % (must, mustnot))


def selftest() -> int:
    ok = True
    cells = {0xFD9F: "F7", 0xFE67: "C9", 0xFE7B: "F7", 0xFE5D: "C9"}
    if claimed(cells) != {0xFD9F, 0xFE7B}:
        print("SELFTEST RED: claimed() gave %r" % sorted(claimed(cells)))
        ok = False
    good, _m = check_known(REF, cells)
    if not good:
        print("SELFTEST RED: a correct census failed the reference arms")
        ok = False
    # 🔴 NEGATIVE, one per DIRECTION -- a checker that only tests "must be
    # claimed" passes a machine that claims everything, and vice versa.
    bad1 = {**cells, 0xFD9F: "C9"}
    if check_known(REF, bad1)[0]:
        print("SELFTEST RED: a MISSING required claim was accepted")
        ok = False
    bad2 = {**cells, 0xFE67: "F7"}
    if check_known(REF, bad2)[0]:
        print("SELFTEST RED: an EXTRA forbidden claim was accepted")
        ok = False
    # and an empty census must not pass
    if check_known(REF, {})[0]:
        print("SELFTEST RED: an EMPTY census passed the arms")
        ok = False
    print("SELFTEST GREEN" if ok else "SELFTEST RED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    if ap.parse_args().selftest:
        return selftest()

    out = {}
    for m in (REF, ZB):
        cells = census(m)
        out[m] = cells
        print("%-28s %d slot(s) read, %d CLAIMED"
              % (m, len(cells), len(claimed(cells))))

    print("\n=== CONTROLS ===")
    ok = True
    for m in (REF, ZB):
        good, msg = check_known(m, out[m])
        print("  %-28s %s: %s" % (m, "green" if good else "RED", msg))
        ok = ok and good
    if not ok:
        print("\nWITHHELD: a control is red.")
        return 1

    r, z = claimed(out[REF]), claimed(out[ZB])
    print("\n=== THE CENSUS ===")
    print("  reference claims %d, zerobas claims %d, %d in COMMON"
          % (len(r), len(z), len(r & z)))
    print("\n  claimed by BOTH (%d):" % len(r & z))
    for a in sorted(r & z):
        print("      $%04X  %s" % (a, ZB_TABLE.get(a, "")))
    print("\n  claimed by ZEROBAS ONLY (%d) -- cells the reference leaves bare:"
          % len(z - r))
    for a in sorted(z - r):
        print("      $%04X  %s" % (a, ZB_TABLE.get(a, "")))
    print("\n  claimed by the REFERENCE ONLY (%d) -- cells we leave bare:"
          % len(r - z))
    print("      %s" % " ".join("$%04X" % a for a in sorted(r - z)))

    # 🔴 THE TABLE IS AN INTENTION; THE CENSUS IS THE MACHINE. Compare them.
    print("\n=== does `hook_tab` match what the machine ended up with? ===")
    miss = sorted(a for a in ZB_TABLE if a not in z)
    extra = sorted(a for a in z if a not in ZB_TABLE)
    if not miss and not extra:
        print("  green: every `hook_tab` row is installed, and nothing else is")
    else:
        if miss:
            print("  🔴 in the table but NOT installed: %s"
                  % " ".join("$%04X %s" % (a, ZB_TABLE[a]) for a in miss))
        if extra:
            print("  ⚠️  installed but not in the table: %s"
                  % " ".join("$%04X" % a for a in extra))
    return 0


if __name__ == "__main__":
    sys.exit(main())
