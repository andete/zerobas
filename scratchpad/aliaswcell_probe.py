#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-ALIASWCELL -- which of main's engine cells does a verb move on the WRITE side?

D-ALIASBITE's READ side is fixed (`chan_gate` now flushes before the crossing
and re-stages after it) and every verb reads back correctly. The WRITE side is
4 of 8: `KILL`, `FILES`, `COPY` and `SAVE` now commit the right file, while
`NAME`, `DSKF`, `DSKI$` and `DSKO$` still lose it.

🔴 ONE MECHANISM FOR THAT WAS ALREADY REFUTED. The failing set is exactly the
set that writes above `$E75F`, and the inference was that the re-stage
overwrote disk's resident code living there. Moving that code changed NOTHING --
and the inference was untestable by `aliaswrite_probe.py` anyway, because each
arm performs ONE crossing and clobbered code could only show on the NEXT one.
**Do not guess a third time.**

📏 SO NAME THE CELLS. `aliascell_probe.py` did exactly this for the READ program
and answered it (not one engine cell moved; only the buffer did). This is that
same named-cell snapshot diff pointed at the WRITE program, with the arms chosen
so the comparison is FIXED-vs-BROKEN rather than verb-vs-control:

    `KILL` is now CLEAN and `NAME`/`DSKF` are still BROKEN, on the same program.
    A cell that moves across `NAME` and NOT across `KILL` is a candidate cause;
    a cell that moves across both is not.

⚠️ THE CONTROL IS STILL REQUIRED, IN BOTH DIRECTIONS. `no-disk` must move
nothing (or nothing here is attributable) and the cells common to `KILL` are
subtracted, so an ordinary bookkeeping move is not read as a finding.

🔬 FOUR PHASES, because "the verb moved it" and "the re-stage moved it" and "the
second PRINT# moved it" are three different bugs: 1 = before the verb, 2 = after
the verb (i.e. after `chan_gate`'s flush + re-stage, which is what the crossing
now does), 3 = after the second `PRINT#`, 4 = after `CLOSE`. A missing phase 4
means the arm never finished and the row REFUSES instead of accusing a verb.

    python3 -u scratchpad/aliaswcell_probe.py [--selftest]
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp  # noqa: E402,F401  -- module level, sets tempfile.tempdir
import omsx_repl  # noqa: E402

ZB = "C-BIOS_MSX1_EU_REPACK_DISK"
SRC_DSK = os.path.join(ROOT, "disk", "test720.dsk")
# $D000 is the marker cell aliascell_probe.py uses. It is NOT private -- the
# machine writes 15/240 there 32 times while sizing RAM -- but every one of
# those lands at t=0.00..0.03, before any program runs, and the phase parser
# keeps only the values this probe pokes. Re-verified by the no-disk control:
# if a foreign write reached a phase slot the control would carry a diff.
PHASE = 0xD000

# The regions to watch, and the names inside them (basic/sysvars.inc). Named so
# the readout says `FWR_DIRSEC`, not `$E9F7` -- the whole point of the probe.
REGIONS = [("ctl", 0xE011, 0xE012), ("chan", 0xE0FC, 0xE0FF),
           ("engine", 0xE9C0, 0xE9FF), ("modes", 0xEA00, 0xEA0F),
           ("buf16", 0xE5C0, 0xE5CF), ("marks", 0xD000, 0xD000)]
NAMES = {
    0xE011: "MAXF", 0xE012: "FCH_ACTIVE",
    0xE0FC: "FILES_ENTIDX/IN_RDLEN", 0xE0FD: "FCH_NUM", 0xE0FE: "FCH_MODE",
    0xE0FF: "FCH_RDMODE",
    0xE9C0: "FAT_SECPERCLUS", 0xE9C1: "FAT_FATSTART", 0xE9C3: "FAT_FIRSTROOT",
    0xE9C5: "FAT_ROOTSECS", 0xE9C7: "FAT_FIRSTDATA", 0xE9C9: "FAT_CURCLUS",
    0xE9CB: "FAT_CLUSSEC", 0xE9CC: "FAT_FIRSTCLUS", 0xE9CE: "FAT_FILESIZE",
    0xE9D2: "FAT_NUMFATS", 0xE9D3: "FAT_SECPERFAT", 0xE9D5: "FAT_PARITY",
    0xE9D6: "FAT_BYTEIDX", 0xE9D8: "FAT_FATSEC", 0xE9DA: "FAT_B0",
    0xE9DB: "FAT_B1", 0xE9DC: "FAT_NAMEPTR", 0xE9DE: "FAT_DIRSEC",
    0xE9E0: "FAT_DIRREM", 0xE9E2: "FAT_WRTMP", 0xE9E4: "FAT_WRTMP2",
    0xE9E6: "FREAD_OFF", 0xE9E8: "FREAD_LEFT", 0xE9EC: "FWR_CLUS",
    0xE9EE: "FWR_FIRST", 0xE9F0: "FWR_SECIDX", 0xE9F1: "FWR_BUFLEN",
    0xE9F3: "FWR_BYTES", 0xE9F7: "FWR_DIRSEC", 0xE9F9: "FWR_DIROFF",
    0xE9FB: "DISKOP block",
    0xEA00: "FCH_MODES",
}
# The per-channel state block fch_save_active/fch_load_ctx copy in and out.
# chan_gate does NOT take that path -- it flushes and re-stages the BUFFER only
# -- so a cell in here that a verb moves is one nothing restores.
STATE0, STATE_END = 0xE9C9, 0xE9FA


def name_of(addr):
    """The declared cell an address falls in, plus its offset -- so a byte in
    the middle of FWR_BYTES reads as `FWR_BYTES+2` and not as an unknown."""
    best = None
    for a in NAMES:
        if a <= addr and (best is None or a > best):
            best = a
    if best is None or addr - best > 15:
        return f"${addr:04X}"
    off = addr - best
    return NAMES[best] + (f"+{off}" if off else "")


def in_state(addr):
    """Is this byte inside the per-channel state block a channel SWITCH saves?"""
    return STATE0 <= addr <= STATE_END


# The write program of aliaswrite_probe.py, with a phase poke at each seam.
REC1 = "AAAABBBBCCCCDDDD"
REC2 = "EEEEFFFFGGGGHHHH"
BODY = [
    "5 MAXFILES=2",
    '10 OPEN"Y.DAT"FOR OUTPUT AS#2',    # a victim for KILL/NAME to act on
    '15 PRINT#2,"V"',
    "17 CLOSE#2",
    '20 OPEN"W.DAT"FOR OUTPUT AS#1',
    f'25 PRINT#1,"{REC1}"',
    "30 ON ERROR GOTO 99",
    "33 POKE&HD000,1",
]
TAIL = [
    "37 POKE&HD000,2",
    f'40 PRINT#1,"{REC2}"',
    "42 POKE&HD000,3",
    "45 CLOSE#1",
    "47 POKE&HD000,4",
    "95 END",
    '99 PRINTCHR$(91);"E";ERR;CHR$(93)',
    "RUN",
]
# 🔴 THE ARMS ARE CHOSEN AS A FIXED/BROKEN CONTRAST, NOT AS A VERB SWEEP.
# `KILL` is the arm the shipped fix REPAIRED and `NAME`/`DSKF` are two it did
# not, measured on this exact program (`scratchpad/aliaswrite_carved.out`). The
# question is what separates them, so running the other five verbs would cost
# five boots and answer nothing this pair does not.
ARMS = [("no-disk", ["35 X=1"]),            # NEGATIVE control -- MUST be quiet
        ("KILL", ['35 KILL"Y.DAT"']),       # FIXED by c59a427b
        ("NAME", ['35 NAME"Y.DAT"AS"V.DAT"']),   # still loses the file
        ("DSKF", ["35 X=DSKF(0)"])]              # still loses the file


def prologue(log):
    dumps = " ".join(
        f'{n}=[__hx {lo} {hi - lo + 1}]' for n, lo, hi in REGIONS)
    return (f'set ::sf [open "{log}" w]\n'
            'proc __hx {a l} { binary scan [debug read_block memory $a $l] H* h;'
            ' return $h }\n'
            f'debug set_watchpoint write_mem {PHASE} {{}} '
            f'{{ puts $::sf "p[debug read memory {PHASE}] {dumps}";'
            f'  flush $::sf }}\n')


def phases(path):
    """{phase: {region: bytes}} from the log, or None if it never wrote."""
    try:
        lines = [l for l in open(path).read().split("\n") if l.startswith("p")]
    except OSError:
        return None
    out = {}
    for l in lines:
        parts = l.split()
        ph = parts[0][1:]
        if ph not in ("1", "2", "3", "4"):
            continue
        out[ph] = {k: bytes.fromhex(v) for k, v in
                   (p.split("=", 1) for p in parts[1:])}
    return out or None


def diff(a, b):
    """[(name, addr, before, after)] for every byte that differs, named."""
    out = []
    for n, lo, _hi in REGIONS:
        if n not in a or n not in b:
            continue
        for i, (x, y) in enumerate(zip(a[n], b[n])):
            if x != y:
                out.append((name_of(lo + i), lo + i, x, y))
    return out


def selftest():
    fails = 0

    def arm(label, cond):
        nonlocal fails
        if not cond:
            print(f"  selftest: FAIL {label}")
            fails += 1

    arm("an exact cell is named", name_of(0xE9F7) == "FWR_DIRSEC")
    arm("a byte inside a 4-byte cell keeps the cell name",
        name_of(0xE9F5) == "FWR_BYTES+2")
    arm("a byte inside FCH_MODES keeps that name",
        name_of(0xEA0F) == "FCH_MODES+15")
    # NEGATIVE: an address far past every declared cell must NOT borrow a name.
    arm("NEGATIVE: an address past every cell is NOT named",
        name_of(0xEA40).startswith("$"))
    arm("NEGATIVE: an address below every cell is NOT named",
        name_of(0xD000).startswith("$"))
    # The state window is the load-bearing classification: chan_gate does not
    # save it, so "inside" vs "outside" is the probe's whole verdict.
    arm("FWR_DIROFF+1 is the LAST byte inside the state block",
        in_state(0xE9FA))
    arm("NEGATIVE: the DISKOP block is OUTSIDE the state block",
        not in_state(0xE9FB))
    arm("NEGATIVE: FAT_SECPERCLUS is OUTSIDE the state block",
        not in_state(0xE9C0))
    z = {"engine": bytes(4)}
    arm("a changed byte is reported",
        diff({"engine": bytes([1, 0, 0, 0])}, z) ==
        [("FAT_SECPERCLUS", 0xE9C0, 1, 0)])
    # NEGATIVE: identical dumps must yield NOTHING -- without this the diff
    # could report every byte and every run would look like a finding.
    arm("NEGATIVE: identical dumps diff to nothing", diff(z, z) == [])
    arm("NEGATIVE: a missing region is skipped, not crashed", diff({}, z) == [])
    p = tempfile.mkstemp(suffix=".log")[1]
    open(p, "w").write("p1 engine=0102\np4 engine=0103\n")
    got = phases(p)
    arm("the log parses into phases",
        got == {"1": {"engine": b"\x01\x02"}, "4": {"engine": b"\x01\x03"}})
    # NEGATIVE: the machine's own boot-time writes to $D000 are 15 and 240 and
    # must not be mistaken for a phase.
    open(p, "w").write("p15 engine=0102\np240 engine=0103\n")
    arm("NEGATIVE: boot-time 15/240 writes are not phases", phases(p) is None)
    open(p, "w").write("")
    arm("NEGATIVE: an empty log is None, not an empty reading",
        phases(p) is None)
    print("  selftest: PASS" if not fails else f"  selftest: {fails} FAILURE(S)")
    return fails


def run(label, lines):
    tmp = tempfile.mkstemp(suffix=".dsk")[1]
    shutil.copyfile(SRC_DSK, tmp)
    log = probe_tmp.tmp(f"aliaswcell_{label}.log")
    omsx_repl.run_cases(ZB, [(label, BODY + lines + TAIL)], batch=False,
                        reset=(), boot=8.0, step=3.0, cap_gap=2.5,
                        run_gap=60.0, timeout=900.0, diska=tmp,
                        prologue=(prologue(log),))
    return phases(log)


SEAMS = [("VERB", "1", "2"), ("PRINT#", "2", "3"), ("CLOSE", "3", "4")]


def report(label, ph):
    if not ph or not {"1", "2", "3", "4"} <= set(ph):
        print(f"  {label}: REFUSED — phases {sorted(ph or [])}, want 1,2,3,4")
        return None
    out = {}
    for seam, a, b in SEAMS:
        out[seam] = diff(ph[a], ph[b])
    print(f"  {label}: " + ", ".join(
        f"{len(out[s])} across the {s}" for s, _, _ in SEAMS))
    return out


def show(title, rows):
    print(f"\n  {title} ({len(rows)}):")
    if not rows:
        print("    (none)")
        return
    for nm, ad, b, a in rows[:32]:
        tag = "  <- NOT saved by a channel switch" if in_state(ad) else ""
        print(f"    {nm:<24} ${b:02X} -> ${a:02X}{tag}")
    if len(rows) > 32:
        print(f"    … and {len(rows) - 32} more")


def main(argv):
    print("D-ALIASWCELL: which cells separate a FIXED verb from a BROKEN one?\n")
    if "--selftest" in argv:
        return 1 if selftest() else 0
    out = {}
    for name, lines in ARMS:
        out[name] = report(f"{name:8}", run(name, lines))
    if not out.get("no-disk") or not out.get("KILL"):
        print("\nREFUSED: a control arm produced no usable phase set")
        return 2
    # 🔴 THE CONTROL MUST BE QUIET ACROSS THE VERB SEAM, or nothing below is
    # attributable: `35 X=1` touches no file machinery at all.
    ctl_verb = out["no-disk"]["VERB"]
    print(f"\n  CONTROL across the VERB: {len(ctl_verb)} cell-byte(s) "
          f"{'— quiet, as required' if not ctl_verb else '— NOT QUIET'}")
    for name in ("KILL", "NAME", "DSKF"):
        if not out.get(name):
            continue
        for seam, _, _ in SEAMS:
            ctl = {c[1] for c in out["no-disk"][seam]}
            show(f"{name}: moved across the {seam} and not in the control",
                 [c for c in out[name][seam] if c[1] not in ctl])
    # 🎯 THE COMPARISON THIS PROBE EXISTS FOR.
    if out.get("KILL") and out.get("NAME"):
        for seam, _, _ in SEAMS:
            k = {c[1] for c in out["KILL"][seam]}
            for broken in ("NAME", "DSKF"):
                if not out.get(broken):
                    continue
                only = [c for c in out[broken][seam] if c[1] not in k]
                show(f"🎯 {broken} moved it across the {seam} and the FIXED "
                     f"KILL did NOT", only)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
