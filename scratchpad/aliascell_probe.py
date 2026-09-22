#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-ALIASCELL -- WHICH cell goes to zero? (why EMPTY and not GARBAGE)

`aliasbite_probe.py` reports the OUTCOME: `KILL`/`NAME`/`DSKF` between two reads
of an open channel make the second `INPUT$(4,#1)` return a 0-character string.
`aliasscope_probe.py` reports the FOOTPRINT, and the footprint does NOT predict
the outcome -- `OPEN…FOR INPUT AS#2` writes the same bytes and the channel
survives [[a-footprint-does-not-predict-an-outcome]].

🔴 THE PUZZLE THIS PROBE EXISTS FOR. A buffer that is overwritten while main
still BELIEVES it should hand back the WRONG BYTES. Four characters at offset
4..7 need no new sector, so a stale-cache story predicts GARBAGE. We measure
EMPTY, which means a COUNT reached zero -- and every obvious counter
(`FREAD_OFF`/`FREAD_LEFT` at $E9E6/$E9E8, the `FCH_STATE0` span $E9C9..$E9FA)
lies OUTSIDE the clobbered window, so the obvious candidates are excluded.

📏 SO DUMP THE STATE AND DIFF IT, naming cells rather than addresses: a hex dump
answers "something changed" and this question needs "WHICH". Three phases --
before the verb, after the verb, and after the second read -- because a cell the
READ zeroes and a cell the VERB zeroes are different bugs with different fixes.

⚠️ THE CONTROL IS THE SAME PROGRAM WITH A NON-DISK STATEMENT. Cells move between
two markers for ordinary reasons; only a cell that moves in the SUBJECT and not
in the CONTROL is attributable to the verb.

    python3 -u scratchpad/aliascell_probe.py [--selftest]
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
PHASE = 0xD000

# The regions to watch, and the names inside them (basic/sysvars.inc). Named so
# the readout says `FREAD_LEFT`, not `$E9E8` -- the whole point of the probe.
REGIONS = [("chan", 0xE0F0, 0xE0FF), ("engine", 0xE9C0, 0xE9FF),
           ("buf16", 0xE5C0, 0xE5CF), ("marks", 0xD000, 0xD003)]
NAMES = {
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
}


def name_of(addr):
    """The declared cell an address falls in, plus its offset -- so a byte in
    the middle of FAT_FILESIZE reads as `FAT_FILESIZE+2` and not as an unknown."""
    best = None
    for a in NAMES:
        if a <= addr and (best is None or a > best):
            best = a
    if best is None or addr - best > 8:
        return f"${addr:04X}"
    off = addr - best
    return NAMES[best] + (f"+{off}" if off else "")


BODY = [
    "5 MAXFILES=2",
    '10 OPEN"Y.DAT"FOR OUTPUT AS#1',
    '15 PRINT#1,"X"',
    "17 CLOSE#1",
    '20 OPEN"Z.DAT"FOR OUTPUT AS#1',
    '30 PRINT#1,"ABCDEFGHIJKLMNOP"',
    "40 CLOSE#1",
    "45 ON ERROR GOTO 99",
    '50 OPEN"Z.DAT"FOR INPUT AS#1',
    "60 A$=INPUT$(4,#1)",
    "65 POKE&HD000,1",
]
TAIL = [
    "75 POKE&HD000,2",
    "80 B$=INPUT$(4,#1)",
    # 🔴 THE LENGTH AND THE FIRST BYTE, READ OFF RAM AND NOT OFF THE SCREEN.
    # A NUL is INVISIBLE to CHPUT, so a B$ of four $00 characters and an EMPTY
    # B$ paint the same `[ABCD]` -- the readout cannot tell "returned nothing"
    # from "returned four zero bytes", and the first three headlines of this
    # investigation were read off that screen
    # [[readout-blind-to-its-own-subject]].
    # `ASC` errors on an empty string, so a CHR$(1) sentinel is appended: the
    # cell reads 1 only when B$ is genuinely empty.
    "81 POKE&HD001,LEN(B$)",
    "83 POKE&HD002,ASC(B$+CHR$(1))",
    "84 POKE&HD000,3",
    "85 CLOSE#1",
    "95 PRINTCHR$(91);A$;B$;CHR$(93):END",
    '99 PRINTCHR$(91);"E";ERR;CHR$(93)',
    "RUN",
]
# ⚠️ ALL THREE TRUNCATING VERBS, BECAUSE "TRUNCATED" WAS A SCREEN READING.
# The extent sweep scored these off VRAM, where a NUL is invisible, so "nothing
# after ABCD" and "four zero bytes" painted identically. Each verb now reports
# its own LEN and first byte out of RAM instead of being assumed to match KILL.
# 🔴 `FILES` AND `COPY` ARE THE CONTRAST PAIR THIS PROBE EXISTS TO RESOLVE.
# The write-side sweep found 7 of 8 judged verbs damage a file being written and
# `FILES` alone does not -- while `LFILES`, the SAME directory walk differing
# only in where the characters go, is not evidence either way (its arm blocks
# before `CLOSE`). So "it mounts, therefore it corrupts" is not the rule, and
# `FILES` beside a verb that DOES corrupt is the comparison that can name the
# difference. `COPY` is that verb.
#
# ⚠️ AND THE READ SIDE IS A SEPARATE QUESTION FROM THE WRITE SIDE. `FILES` was
# only ever measured against a file being WRITTEN; whether it corrupts a file
# being READ has never been run. Both are here.
#
# ⚠️ A PRINTING VERB IS FINE IN THIS PROBE AND ONLY IN THIS PROBE: every
# quantity here -- LEN, the first byte, the cell dumps -- is read out of RAM by
# watchpoint, so a listing that scrolls the screen disturbs nothing.
ARMS = [("CONTROL", ["70 X=1"]),
        ("KILL", ['70 KILL"Y.DAT"']),
        ("NAME", ['70 NAME"Y.DAT"AS"W.DAT"']),
        ("DSKF", ["70 X=DSKF(0)"]),
        ("FILES", ["70 FILES"]),
        ("COPY", ['70 COPY"Y.DAT"TO"C.DAT"'])]


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
        if ph not in "123":
            continue
        out[ph] = {k: bytes.fromhex(v) for k, v in
                   (p.split("=", 1) for p in parts[1:])}
    return out or None


def diff(a, b):
    """[(name, before, after)] for every byte that differs, named."""
    out = []
    for n, lo, _hi in REGIONS:
        if n not in a or n not in b:
            continue
        for i, (x, y) in enumerate(zip(a[n], b[n])):
            if x != y:
                out.append((name_of(lo + i), x, y))
    return out


def selftest():
    fails = 0

    def arm(label, cond):
        nonlocal fails
        if not cond:
            print(f"  selftest: FAIL {label}")
            fails += 1

    arm("an exact cell is named", name_of(0xE9E8) == "FREAD_LEFT")
    arm("a byte inside a 4-byte cell keeps the cell name",
        name_of(0xE9EA) == "FREAD_LEFT+2")
    # $E9FF is the LAST byte of the 5-byte DISKOP block, so it is correctly
    # named -- the first cut asserted it was not, and the selftest caught the
    # ARM rather than the code. Both halves are pinned now: inside a real cell
    # it keeps the name, and far past every cell it must not borrow one.
    arm("the last byte of the DISKOP block keeps that name",
        name_of(0xE9FF) == "DISKOP block+4")
    # NEGATIVE: an address far past every declared cell must NOT borrow a name.
    arm("NEGATIVE: an address past every cell is NOT named",
        name_of(0xEA40).startswith("$"))
    arm("NEGATIVE: an address below every cell is NOT named",
        name_of(0xE0F0).startswith("$"))
    z = {"engine": bytes(4)}
    arm("a changed byte is reported",
        diff({"engine": bytes([1, 0, 0, 0])}, z) == [("FAT_SECPERCLUS", 1, 0)])
    # NEGATIVE: identical dumps must yield NOTHING -- without this the diff
    # could report every byte and every run would look like a finding.
    arm("NEGATIVE: identical dumps diff to nothing", diff(z, z) == [])
    arm("NEGATIVE: a missing region is skipped, not crashed",
        diff({}, z) == [])
    p = tempfile.mkstemp(suffix=".log")[1]
    open(p, "w").write("p1 engine=0102\np2 engine=0103\n")
    got = phases(p)
    arm("the log parses into phases",
        got == {"1": {"engine": b"\x01\x02"}, "2": {"engine": b"\x01\x03"}})
    open(p, "w").write("")
    arm("NEGATIVE: an empty log is None, not an empty reading",
        phases(p) is None)
    # The marks region must be READ, not assumed: a probe that reports a length
    # it never parsed would print "0 char(s)" for every run.
    open(p, "w").write("p3 marks=00044100\n")
    arm("the marks region carries LEN and the first byte",
        phases(p)["3"]["marks"][1:3] == b"\x04\x41")
    print("  selftest: PASS" if not fails else f"  selftest: {fails} FAILURE(S)")
    return fails


def run(label, lines):
    tmp = tempfile.mkstemp(suffix=".dsk")[1]
    shutil.copyfile(SRC_DSK, tmp)
    log = probe_tmp.tmp(f"aliascell_{label}.log")
    omsx_repl.run_cases(ZB, [(label, BODY + lines + TAIL)], batch=False,
                        reset=(), boot=8.0, step=3.0, cap_gap=2.5,
                        run_gap=60.0, timeout=900.0, diska=tmp,
                        prologue=(prologue(log),))
    return phases(log)


def report(label, ph):
    if not ph or not {"1", "2", "3"} <= set(ph):
        print(f"  {label}: REFUSED — phases {sorted(ph or [])}, want 1,2,3")
        return None
    v = diff(ph["1"], ph["2"])
    r = diff(ph["2"], ph["3"])
    m = ph["3"].get("marks", b"\0\0\0\0")
    ln, first = m[1], m[2]
    what = ("EMPTY" if first == 1 and ln == 0
            else f"{ln} char(s), first byte ${first:02X}")
    print(f"  {label}: {len(v)} cell-byte(s) moved across the VERB, "
          f"{len(r)} across the READ; B$ = {what}")
    return {"verb": v, "read": r, "len": ln, "first": first}


def main(argv):
    print("D-ALIASCELL: which cell goes to zero? (empty, not garbage)\n")
    if "--selftest" in argv:
        return 1 if selftest() else 0
    out = {}
    for name, lines in ARMS:
        out[name] = report(f"{name:8}", run(name, lines))
    if not out.get("CONTROL") or not out.get("KILL"):
        print("\nREFUSED: an arm produced no usable phase set")
        return 2
    # 🔴 EVERY ARM, NOT JUST THE FIRST ONE. The first cut printed KILL's diff
    # and nothing else, which is exactly the shape that hides the interesting
    # row: `FILES` is the arm this sweep was extended for and its diff was not
    # being shown at all [[readout-blind-to-its-own-subject]].
    for name in [n for n, _ in ARMS if n != "CONTROL"]:
        if not out.get(name):
            continue
        for when in ("verb", "read"):
            ctl = {c[0] for c in out["CONTROL"][when]}
            only = [c for c in out[name][when] if c[0] not in ctl]
            print(f"\n  {name}: moved across the {when.upper()} and NOT in "
                  f"the control ({len(only)}):")
            for nm, b, a in only[:24]:
                print(f"    {nm:<24} ${b:02X} -> ${a:02X}")
            if len(only) > 24:
                print(f"    … and {len(only) - 24} more")
            if not only:
                print("    (none)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
