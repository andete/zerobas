#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-ALIASWRITE -- does a disk verb between two PRINT# corrupt the FILE?

The read side is settled (D-ALIASBITE): `KILL`/`NAME`/`DSKF` between two reads
of an open channel make the next read serve whatever the verb left in
`FSECTOR_BUF` -- 4 bytes of the wrong data, no error. The WRITE stream (`FWR_*`)
buffers through THAT SAME BUFFER until a sector fills, so a verb between two
`PRINT#`s may make `CLOSE` commit the verb's leftovers TO DISK.

🔴 THAT WOULD BE STRICTLY WORSE THAN THE READ SIDE. A bad read is transient and
lives in one variable; a bad write is on the medium, survives the session, and
is what the next program reads back.

📏 THE READOUT IS THE HOST-PARSED IMAGE, NOT THE SCREEN. This investigation
produced three wrong headlines off a screen scrape, because a NUL is invisible
to `CHPUT` and "nothing appeared" and "zero bytes were delivered" paint
identically [[readout-blind-to-its-own-subject]]. Here the emulator writes a
scratch `.dsk`, the run ends, and the host walks the FAT chain and compares the
file BYTE FOR BYTE against what the program printed. Nothing is inferred from
pixels.

⚠️ THE CONTROL IS THE SAME PROGRAM WITH A NON-DISK STATEMENT between the two
`PRINT#`s. Without it, a file that differs from the ideal proves nothing -- the
BASIC writer's own record format (CR/LF, padding) is not this probe's subject.

    python3 -u scratchpad/aliaswrite_probe.py [--selftest]
"""
from __future__ import annotations

import os
import shutil
import struct
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "scratchpad"))
import probe_tmp  # noqa: E402,F401  -- module level, sets tempfile.tempdir
import omsx_repl  # noqa: E402
import fatbuf_probe as FB  # noqa: E402

# 🔴 THE MACHINE IS OVERRIDABLE SO THE REFERENCE CAN ANSWER THE SAME QUESTION.
# `National_CF-3300` is a genuine MSX1 with its own `cf-3300_disk.rom` in slot
# 3-1 -- the tree's standing disk oracle. (An earlier note in this arc claimed
# there was no booted disk oracle here; that was WRONG, and it attached an
# unnecessary "not measured against a reference" caveat to every D-ALIASBITE
# finding.) `National_CF-3300_ZEROBASDISK` is a DIFFERENT machine -- real BIOS
# with OUR disk ROM -- and is a provider oracle, NOT a behaviour reference.
# ⚠️ CLEAN ROOM: this probe reads only the DISK IMAGE the machine wrote and the
# marker cell the PROGRAM pokes. It dumps no reference RAM span and no ROM byte,
# so §8.5 is not approached -- which is why aliascell_probe.py, which DOES dump
# RAM spans, must never be pointed at a reference.
ZB = os.environ.get("ZEROBAS_ALIAS_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
BOOT = float(os.environ.get("ZEROBAS_ALIAS_BOOT", "8.0"))
# 🔴 A STOCK MSX1 BOOTS SCREEN 1, AND THE SCRAPE ASSUMES SCREEN 0. `reset` is
# IGNORED in boot-per-case mode, so the reference needs these as typed DIRECT
# lines instead -- the same ("", "SCREEN 0", "NEW", "CLS") the other reference
# probes use. Without them the harness reports every slot BLIND and nothing is
# delivered at all, which reads as "the program did not finish".
PRELUDE = [x for x in os.environ.get("ZEROBAS_ALIAS_PRELUDE", "").split("|") if
           x or os.environ.get("ZEROBAS_ALIAS_PRELUDE", "").startswith("|")]
# ⚠️ ONLY THE NAMED ARMS, when asked: a reference run costs a boot per arm and
# the question ("does the reference corrupt it too?") is answered by the control
# plus one damaging verb. Narrowing is explicit, not silent.
ONLY = [x for x in os.environ.get("ZEROBAS_ALIAS_ONLY", "").split(",") if x]
SRC_DSK = os.path.join(ROOT, "disk", "test720.dsk")
TARGET = "W       DAT"          # 8.3, space-padded -- the file under test
DONE_CELL = 0xD000              # the arm pokes 9 here after CLOSE

# Two records, distinct and self-describing, so a diff names WHICH half moved.
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
]
TAIL = [
    f'40 PRINT#1,"{REC2}"',
    "45 CLOSE#1",
    # 🔴 THE COMPLETION MARKER, AND IT IS NOT OPTIONAL. An EMPTY file is what a
    # wiped file looks like AND what a program that never reached `CLOSE` looks
    # like -- the image alone cannot tell them apart, so four arms of the first
    # sweep were uninterpretable and read as findings. This cell is written
    # only if the arm ran to the end; a missing 9 makes the row REFUSE instead
    # of accusing a verb [[an-unnamed-outcome-reads-as-no-outcome]].
    "50 POKE&HD000,9",
    "95 END",
    '99 PRINTCHR$(91);"E";ERR;CHR$(93)',
    "RUN",
]
# 🔴 TWO CONTROLS, IN BOTH DIRECTIONS, IN THE SAME RUN. `no-disk` MUST come
# back clean or nothing here is attributable; `KILL` MUST come back damaged or
# the sweep has stopped being able to see the defect at all. One without the
# other leaves a whole direction unchecked
# [[a-null-result-needs-the-instrument-controls-in-the-same-run]].
#
# ⚠️ THE READOUT IS THE IMAGE, WHICH IS WHAT MAKES THE PRINTING VERBS TESTABLE.
# `FILES`/`LFILES` were excluded from the earlier sweeps only because a listing
# scrolls the screen the fence was read off; nothing here reads the screen.
#
# ⚠️ TWO VERBS ARE EXCLUDED, AND NOT FOR CONVENIENCE:
#   * `LOAD` replaces the stored program and returns to command level, so the
#     arm's own `PRINT#`/`CLOSE` never execute. The file would be damaged by the
#     MISSING CLOSE, not by the verb -- an arm that cannot attribute its result.
#   * `FIELD`/`LSET` need a RANDOM channel (`OPEN … AS #2 LEN=n`) that the
#     control does not have, so adding them changes the program under test.
#     They deserve their own sweep against their own control.
ARMS = [("no-disk", ["35 X=1"]),            # NEGATIVE control -- MUST be clean
        ("KILL", ['35 KILL"Y.DAT"']),       # POSITIVE control -- MUST be damaged
        ("NAME", ['35 NAME"Y.DAT"AS"V.DAT"']),
        ("DSKF", ["35 X=DSKF(0)"]),
        ("FILES", ["35 FILES"]),
        ("LFILES", ["35 LFILES"]),
        ("COPY", ['35 COPY"Y.DAT"TO"C.DAT"']),
        ("DSKI$", ["35 Q$=DSKI$(0,0)"]),
        # DSKO$ writes a RAW SECTOR, which would confound an image readout --
        # unless it writes back exactly what it just read. Paired with the
        # matching DSKI$ it rewrites sector 0 byte-identically, so the arm
        # measures the VERB and not a scribble (docs/spec-basic-dskio.md `o2`).
        ("DSKO$", ["35 Q$=DSKI$(0,0):DSKO$ 0,0"]),
        ("SAVE", ['35 SAVE"S.BAS"'])]


def geom(d):
    bps = struct.unpack("<H", d[11:13])[0]
    spc, rsv = d[13], struct.unpack("<H", d[14:16])[0]
    nf = d[16]
    nroot = struct.unpack("<H", d[17:19])[0]
    spf = struct.unpack("<H", d[22:24])[0]
    root_sec = rsv + nf * spf
    return dict(bps=bps, spc=spc, rsv=rsv, nf=nf, spf=spf, nroot=nroot,
                root_sec=root_sec,
                data_sec=root_sec + (nroot * 32 + bps - 1) // bps)


def read_file(img, name8):
    """The bytes of `name8` off the image, by walking its FAT chain.

    Returns None when the entry is absent -- which is DATA ("the file was never
    created"), a different outcome from an empty file, and the two must not be
    collapsed [[an-unnamed-outcome-reads-as-no-outcome]]."""
    g = geom(img)
    fat = bytearray(img[g["rsv"] * g["bps"]:(g["rsv"] + g["spf"]) * g["bps"]])
    for i in range(g["nroot"]):
        e = g["root_sec"] * g["bps"] + i * 32
        if img[e:e + 11] != name8.encode():
            continue
        clus = struct.unpack("<H", img[e + 26:e + 28])[0]
        size = struct.unpack("<I", img[e + 28:e + 32])[0]
        out, csz, seen = bytearray(), g["bps"] * g["spc"], set()
        while 2 <= clus < 0xFF0:
            if clus in seen:
                return b"<CHAIN LOOPS>"
            seen.add(clus)
            off = (g["data_sec"] + (clus - 2) * g["spc"]) * g["bps"]
            out += img[off:off + csz]
            clus = FB.fat12_get(fat, clus)
        return bytes(out[:size])
    return None


def verdict(ctl, sub, done=True):
    """Named before the run, so the outcome cannot be chosen after it."""
    if not done:
        return ("REFUSED — the arm never reached its CLOSE, so the file on "
                "disk shows a missing flush and NOT what the verb did to it")
    if ctl is None:
        return ("INSTRUMENT FAULT: the CONTROL never created the file, so no "
                "row can be attributed to a verb")
    if REC1.encode() not in ctl or REC2.encode() not in ctl:
        return (f"INSTRUMENT FAULT: the CONTROL file is missing a record "
                f"({ctl!r}) -- the probe is measuring its own file handling")
    if sub is None:
        return "GONE — the verb left no directory entry for the file at all"
    if sub == ctl:
        return "CLEAN — the file on disk is byte-identical to the control"
    miss = [r for r in (REC1, REC2) if r.encode() not in sub]
    if miss:
        return (f"DATA LOST ON THE MEDIUM — record(s) {', '.join(miss)} are "
                f"absent from the committed file; got {sub!r}")
    return f"DIFFERS but both records survive: {sub!r} vs {ctl!r}"


def selftest():
    fails = 0

    def arm(label, cond):
        nonlocal fails
        if not cond:
            print(f"  selftest: FAIL {label}")
            fails += 1

    good = (REC1 + "\r\n" + REC2 + "\r\n").encode()
    arm("identical file -> CLEAN", verdict(good, good).startswith("CLEAN"))
    # 🔴 THE ARM THAT KEEPS AN UNFINISHED RUN FROM ACCUSING A VERB: an empty
    # file from a program that never closed must REFUSE, not report DATA LOST.
    arm("NEGATIVE: an arm that did not finish REFUSES, whatever the file says",
        verdict(good, None, done=False).startswith("REFUSED"))
    arm("NEGATIVE: ...even when the file looks perfect",
        verdict(good, good, done=False).startswith("REFUSED"))
    lost = (("\x00" * 16) + "\r\n" + REC2 + "\r\n").encode()
    arm("first record replaced by NULs -> DATA LOST",
        verdict(good, lost).startswith("DATA LOST"))
    arm("a missing entry -> GONE", verdict(good, None).startswith("GONE"))
    # 🔴 THE ARM THAT KEEPS A BROKEN PROBE FROM BLAMING THE ROM: if the CONTROL
    # is already wrong, no verdict about a verb may be issued at all.
    arm("NEGATIVE: a control missing a record is an INSTRUMENT FAULT",
        verdict(b"short", good).startswith("INSTRUMENT FAULT"))
    arm("NEGATIVE: a control that is None is an INSTRUMENT FAULT",
        verdict(None, good).startswith("INSTRUMENT FAULT"))
    # and the reader: it must find a real file in a real image, and report None
    # for one that is absent -- without this the sweep could return None for
    # every arm and read as "GONE" everywhere.
    img = bytearray(open(SRC_DSK, "rb").read()) if os.path.exists(SRC_DSK) else None
    if img is not None:
        arm("NEGATIVE: an absent name reads None, not b''",
            read_file(bytes(img), "NOSUCH  XYZ") is None)
        g = geom(bytes(img))
        arm("the geometry parses (512 B sectors)", g["bps"] == 512)
    else:
        print("  selftest: SKIPPED the image arms (no test720.dsk)")
    print("  selftest: PASS" if not fails else f"  selftest: {fails} FAILURE(S)")
    return fails


def run(label, lines):
    tmp = tempfile.mkstemp(suffix=".dsk")[1]
    shutil.copyfile(SRC_DSK, tmp)      # never write the tracked fixture
    log = probe_tmp.tmp(f"aliaswrite_{label}.log")
    pro = (f'set ::df [open "{log}" w]\n'
           f'debug set_watchpoint write_mem {DONE_CELL} {{}} '
           f'{{ puts $::df [debug read memory {DONE_CELL}]; flush $::df }}\n')
    omsx_repl.run_cases(ZB, [(label, PRELUDE + BODY + lines + TAIL)], batch=False,
                        reset=(), boot=BOOT, step=3.0, cap_gap=2.5,
                        run_gap=60.0, timeout=900.0, diska=tmp,
                        prologue=(pro,))
    try:
        done = "9" in open(log).read().split()
    except OSError:
        done = False
    got = read_file(open(tmp, "rb").read(), TARGET)
    print(f"  {label:9} {'ran to END' if done else 'DID NOT FINISH'}  {got!r}")
    return (done, got)


def main(argv):
    print("D-ALIASWRITE: does a disk verb between two PRINT# corrupt the "
          "FILE?\n")
    if "--selftest" in argv:
        return 1 if selftest() else 0
    if not os.path.exists(SRC_DSK):
        print(f"INSTRUMENT FAULT: no test disk at {SRC_DSK}")
        return 2
    arms = [(n, l) for n, l in ARMS if not ONLY or n in ONLY]
    if ONLY and "no-disk" not in [n for n, _ in arms]:
        print("REFUSING: the no-disk control must be in every run")
        return 2
    out = {n: run(n, l) for n, l in arms}
    if not out["no-disk"][0]:
        print("\nINSTRUMENT FAULT: the CONTROL never reached its CLOSE")
        return 2
    ctl = out["no-disk"][1]
    print()
    rows = [(n, verdict(ctl, out[n][1], out[n][0])) for n, _ in arms[1:]]
    for name, v in rows:
        print(f"  {name:8} {v}")
    # 🔴 THE POSITIVE CONTROL IS CHECKED, NOT JUST PRINTED. A sweep whose known
    # -damaged arm comes back CLEAN has lost the ability to see the defect, and
    # every "clean" below it would be a false acquittal.
    kill = dict(rows).get("KILL")
    if kill is None:
        print("\n⚠️  no KILL arm in this run: the positive control is ABSENT, "
              "so a CLEAN row below is not evidence that the defect is gone")
        return 0
    # 🔴 AND THE POSITIVE CONTROL'S EXPECTATION INVERTS ON A REFERENCE. On OUR
    # machine a clean KILL means the sweep has gone blind and every CLEAN row is
    # a false acquittal. On a REFERENCE a clean KILL is the FINDING -- the whole
    # question is whether it corrupts the file too. Printing the same red line
    # in both cases would file the answer as an instrument fault.
    damaged = kill.startswith(("DATA LOST", "GONE", "DIFFERS"))
    on_reference = ZB != "C-BIOS_MSX1_EU_REPACK_DISK"
    if on_reference:
        print(f"\n🔬 REFERENCE RUN on {ZB}: KILL came back "
              f"{'DAMAGED' if damaged else 'CLEAN'}.")
        print("  CLEAN here is the ANSWER, not a blind sweep: the reference "
              "keeps an open file intact across the verb."
              if not damaged else
              "  DAMAGED here would mean the reference has the same defect.")
    elif not damaged:
        print(f"\n🔴 INSTRUMENT FAULT: the POSITIVE control (KILL) came back "
              f"{kill.split(chr(8212))[0].strip()} — on OUR machine the sweep "
              f"can no longer see the defect, so no 'CLEAN' row above is "
              f"evidence.")
        return 2
    # 🔴 A REFUSAL IS NOT A FINDING. The first cut counted "anything not CLEAN"
    # as damage, which swept the one arm that could not be judged into the
    # accusation -- the tally line would have said 8 where the evidence supports
    # 7 [[an-unnamed-outcome-reads-as-no-outcome]].
    bad = [n for n, v in rows if v.startswith(("DATA LOST", "GONE", "DIFFERS"))]
    ref = [n for n, v in rows if v.startswith("REFUSED")]
    judged = len(rows) - len(ref)
    print(f"\nVERDICT: {len(bad)} of {judged} JUDGED verbs damage the file: "
          f"{', '.join(bad) if bad else '(none)'}")
    if ref:
        print(f"  {len(ref)} arm(s) could not be judged and are NOT counted "
              f"either way: {', '.join(ref)}")
    print("  controls: no-disk clean (negative) and KILL damaged (positive), "
          "both in this run")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
