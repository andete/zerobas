#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-ALIASFIELD -- do the RANDOM-file verbs damage an open SEQUENTIAL file?

The verb sweep (D-ALIASWRITE) judged nine verbs and had to leave `FIELD`/`LSET`
OUT: they need a RANDOM channel (`OPEN ... AS #n LEN=`) that its control does
not have, so bolting them on would have changed the PROGRAM under test rather
than the interposed statement. They get their own control here, and `PUT`/`GET`
come with them because those are the random verbs that actually move a sector.

🎯 THE QUESTION. D-ALIASBITE's rule is *"a verb corrupts an open channel when it
REFILLS MAIN'S STAGED SECTOR"* -- not merely when it mounts, which `FILES`
proved by mounting, walking the whole root directory and touching nothing. The
random verbs are the untested half of that rule: `PUT`/`GET` move a sector by
definition, `FIELD`/`LSET` only rearrange a buffer descriptor.

📏 THE READOUT IS THE HOST-PARSED IMAGE plus two RAM markers, NEVER THE SCREEN.
A NUL is invisible to `CHPUT`, so "nothing appeared" and "zero bytes were
delivered" paint identically; three headlines of this investigation came off
that screen and three were wrong [[readout-blind-to-its-own-subject]]. Here the
emulator writes a scratch `.dsk`, the run ends, and the host walks the FAT chain
and compares the file BYTE FOR BYTE.

⚠️ AND AN ERRORING ARM IS NOT A HANGING ARM. `ON ERROR` records `ERR` in RAM and
RESUMEs, so a verb our BASIC refuses is reported as a refusal WITH ITS CODE
rather than vanishing into a missing `CLOSE` and reading as damage
[[an-unnamed-outcome-reads-as-no-outcome]].

    python3 -u scratchpad/aliasfield_probe.py [--selftest]
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

ZB = "C-BIOS_MSX1_EU_REPACK_DISK"
SRC_DSK = os.path.join(ROOT, "disk", "test720.dsk")
TARGET = "W       DAT"          # 8.3, space-padded -- the file under test
ERR_CELL = 0xCFFD               # ON ERROR pokes ERR here, then RESUMEs
ERL_CELL = 0xCFFC               # ...and the LINE it came from
# 🔴 `ERR` WITHOUT `ERL` IS NOT A DIAGNOSIS. The first run of this probe had
# every arm reporting ERR 15 -- including the no-disk control -- which means
# the raise is in the SHARED BODY, and `RESUME 40` would then skip the
# interposed statement in every arm and make each CLEAN row meaningless. The
# line number is what separates "the verb raised" from "the scaffolding did".
# 🔴 THE MARKER CELLS ARE NOT $D000, AND THAT IS A MEASURED FACT NOT A STYLE
# CHOICE. `scratchpad/cellpriv.out`: during one ordinary disk program THE MACHINE
# writes $D000 **32 times**, alternating 15 and 240, and `CLEAR` does not stop
# it. The first cut of this probe read those writes as `ERR 15` and reported an
# error in EVERY arm including the no-disk control. `scratchpad/findquiet.out`
# swept ten candidates: every $xx00 page-boundary address takes the same 32
# writes, and **$CFFE takes none**. A marker cell is a CLAIM that nobody else
# writes it -- measure the claim [[a-coverage-row-whose-geometry-cannot-reach-the-case]].
DONE_CELL = 0xCFFE              # the arm pokes 9 here after CLOSE

# Two records, distinct and self-describing, so a diff names WHICH half moved.
REC1 = "AAAABBBBCCCCDDDD"
REC2 = "EEEEFFFFGGGGHHHH"

BODY = [
    # CLEAR puts BASIC's ceiling well below the marker cells; measured
    # benign for these programs (D-TWOFILE ran with and without it).
    "1 CLEAR 200,&HBFFF",
    "5 MAXFILES=3",
    '10 OPEN"Y.DAT"FOR OUTPUT AS#3',    # a victim for the KILL control
    '15 PRINT#3,"V"',
    "17 CLOSE#3",
    '20 OPEN"R.DAT"AS#2 LEN=16',        # the RANDOM channel every arm needs
    "22 FIELD#2,16 AS F$",
    # 🔴 SEED THE RANDOM FILE, OR THE `GET` ARM CANNOT BE JUDGED. On an empty
    # R.DAT, `GET#2,1` correctly raises `Input past end` (ERR 55 -- the
    # reference's own behaviour, basic/field.asm) and the arm dies before its
    # CLOSE, so it reports REFUSED. That was a FIXTURE fault, not a finding
    # about GET [[an-arm-for-the-neighbouring-case-reads-like-an-arm-for-yours]].
    '23 LSET F$="SEEDRECORD"',
    "24 PUT#2,1",
    '25 OPEN"W.DAT"FOR OUTPUT AS#1',    # the SEQUENTIAL file under test
    f'30 PRINT#1,"{REC1}"',
    "32 ON ERROR GOTO 99",
]
TAIL = [
    f'40 PRINT#1,"{REC2}"',
    "45 CLOSE#1",
    "47 CLOSE#2",
    "50 POKE&HCFFE,9",
    "95 END",
    # An arm whose verb RAISES must still reach its CLOSE, or an unsupported
    # verb is indistinguishable from one that hangs. The code is recorded so a
    # refusal can be told from a success.
    "99 POKE&HCFFD,ERR:POKE&HCFFC,ERL",
    "98 RESUME 40",
    "RUN",
]

# 🔴 EVERY ARM HAS THE RANDOM CHANNEL, INCLUDING BOTH CONTROLS -- opened and
# FIELDed in the shared body above, so the ONLY thing that differs between arms
# is the interposed statement. That is the whole reason this is a separate probe
# from aliaswrite_probe.py rather than four more rows in it.
#
# ⚠️ TWO CONTROLS, IN BOTH DIRECTIONS, IN THE SAME RUN: `no-disk` MUST come back
# clean or nothing is attributable, and `KILL` MUST come back damaged or the
# sweep has lost the ability to see the defect and every CLEAN row below is a
# false acquittal.
#
# `PUT`/`GET` are here beside `FIELD`/`LSET` because they are the random verbs
# that actually MOVE A SECTOR -- if the rule is "it refills main's staged
# sector", they are where it should show.
# 🔴 THE POSITIVE CONTROL IS A CONSTRUCTED ONE, NOT A VERB -- same correction
# aliaswrite_probe.py took on 2026-09-23 and for the same reason. `KILL` held
# the role while `KILL` was broken; once D-ALIASWCELL fixed it, the guard fired
# on the FIX and the sweep returned rc=2 with every row clean and nothing
# judged. A positive control the subject can repair is not a control.
# `truncate!` re-opens the file FOR OUTPUT, which truncates it whatever any
# buffer does, so it keeps reporting damage after every fix.
# ⚠️ It is a CONTROL, not one of the random-file verbs: excluded from the tally.
POSITIVE = "truncate!"
ARMS = [("no-disk", ["35 X=1"]),            # NEGATIVE control -- MUST be clean
        (POSITIVE, ['35 CLOSE#1:OPEN"W.DAT"FOR OUTPUT AS#1']),  # MUST be damaged
        ("KILL", ['35 KILL"Y.DAT"']),
        ("FIELD", ["35 FIELD#2,16 AS G$"]),
        ("LSET", ['35 LSET F$="ZZZZ"']),
        ("PUT", ["35 PUT#2,1"]),
        ("GET", ["35 GET#2,1"])]

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
           f'{{ puts $::df [debug read memory {DONE_CELL}]; flush $::df }}\n'
           f'debug set_watchpoint write_mem {ERR_CELL} {{}} '
           f'{{ puts $::df [debug read memory {ERR_CELL}]; flush $::df }}\n'
           f'debug set_watchpoint write_mem {ERL_CELL} {{}} '
           f'{{ puts $::df "L[debug read memory {ERL_CELL}]"; flush $::df }}\n')
    omsx_repl.run_cases(ZB, [(label, BODY + lines + TAIL)], batch=False,
                        reset=(), boot=8.0, step=3.0, cap_gap=2.5,
                        run_gap=60.0, timeout=900.0, diska=tmp,
                        prologue=(pro,))
    try:
        seen = open(log).read().split()
    except OSError:
        seen = []
    done = "9" in seen
    err = next((v for v in seen if not v.startswith("L") and v not in ("9", "0")), None)
    erl = next((v[1:] for v in seen if v.startswith("L") and v != "L0"), None)
    got = read_file(open(tmp, "rb").read(), TARGET)
    tag = "ran to END" if done else "DID NOT FINISH"
    if err:
        tag += f" (ERR {err} at line {erl or '?'})"
    print(f"  {label:9} {tag}  {got!r}")
    return (done, got)


def main(argv):
    print("D-ALIASFIELD: do the RANDOM-file verbs corrupt an open "
          "SEQUENTIAL file?\n")
    if "--selftest" in argv:
        return 1 if selftest() else 0
    if not os.path.exists(SRC_DSK):
        print(f"INSTRUMENT FAULT: no test disk at {SRC_DSK}")
        return 2
    out = {n: run(n, l) for n, l in ARMS}
    if not out["no-disk"][0]:
        print("\nINSTRUMENT FAULT: the CONTROL never reached its CLOSE")
        return 2
    ctl = out["no-disk"][1]
    print()
    rows = [(n, verdict(ctl, out[n][1], out[n][0])) for n, _ in ARMS[1:]]
    for name, v in rows:
        print(f"  {name:8} {v}")
    # 🔴 THE POSITIVE CONTROL IS CHECKED, NOT JUST PRINTED. A sweep whose known
    # -damaged arm comes back CLEAN has lost the ability to see the defect, and
    # every "clean" below it would be a false acquittal.
    pos = dict(rows)[POSITIVE]
    if not pos.startswith(("DATA LOST", "GONE", "DIFFERS")):
        print(f"\n🔴 INSTRUMENT FAULT: the CONSTRUCTED positive control "
              f"({POSITIVE}) came back {pos.split(chr(8212))[0].strip()} — it "
              f"truncates the file by construction, so a sweep that cannot see "
              f"THAT cannot see anything and no 'CLEAN' row above is evidence.")
        return 2
    kill = dict(rows)["KILL"]
    if not kill.startswith(("DATA LOST", "GONE", "DIFFERS")):
        print("\n🟢 KILL came back CLEAN, and the sweep is NOT blind: the "
              "constructed positive control still reports damage. KILL is a "
              "FIXED verb here (D-ALIASWCELL), not a blind row.")
    # 🔴 A REFUSAL IS NOT A FINDING. The first cut counted "anything not CLEAN"
    # as damage, which swept the one arm that could not be judged into the
    # accusation -- the tally line would have said 8 where the evidence supports
    # 7 [[an-unnamed-outcome-reads-as-no-outcome]].
    verbs = [(n, v) for n, v in rows if n != POSITIVE]
    bad = [n for n, v in verbs if v.startswith(("DATA LOST", "GONE", "DIFFERS"))]
    ref = [n for n, v in verbs if v.startswith("REFUSED")]
    judged = len(verbs) - len(ref)
    print(f"\nVERDICT: {len(bad)} of {judged} JUDGED verbs damage the file: "
          f"{', '.join(bad) if bad else '(none)'}")
    if ref:
        print(f"  {len(ref)} arm(s) could not be judged and are NOT counted "
              f"either way: {', '.join(ref)}")
    print(f"  controls: no-disk clean (negative) and {POSITIVE} damaged "
          f"(positive), both in this run")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
