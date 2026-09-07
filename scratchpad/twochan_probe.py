#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-TWOCHAN — zerobas shares ONE sector buffer where the reference gives each
channel its own. Does that lose data?

Joost, 2026-09-07: *"I don't think we should reserve buffers we don't use.
However we should be sure we don't need the buffers if the references do use
them."* This is that check.

## The structural risk, read from the source

    FSECTOR_BUF  $E5C0  file data / read sector buffer   -- ONE, GLOBAL
    FWBUF        $E7C0  FAT/dir metadata sector buffer   -- ONE, GLOBAL
    FCH_CTXSZ = FCH_STATESZ = 50 B   "block = state ONLY (no buffer)"

The reference reserves 267 B per channel; the measured difference is
`R = 293 + 267*MAXFILES` there against `R = 12 + 50*MAXFILES` here. The 50 bytes
are STATE, and the state includes position and cache markers -- FAT_CURCLUS,
FAT_CLUSSEC, and FAT_FATSEC ("FAT sector currently read"). `fch_select` LDIRs
that state per channel.

🎯 SO THE HAZARD IS SPECIFIC, NOT VAGUE: a channel's state can say "the sector I
need is already loaded" while the SHARED buffer holds a different channel's
sector. Per-channel buffers make that impossible; one buffer does not. If zerobas
re-reads on every access the sharing is safe and the reference's buffers are
simply memory we do not need. If it trusts the cache, interleaving two channels
serves the WRONG BYTES.

## The row

Two files whose contents cannot be confused, written by the program itself so no
fixture assumption is involved, then read INTERLEAVED:

    A.TXT = "AAAA..."   B.TXT = "BBBB..."
    X$ = INPUT$(3,#1)   -> AAA
    Y$ = INPUT$(3,#2)   -> BBB      <- this is what may evict #1's sector
    Z$ = INPUT$(3,#1)   -> AAA      <- the reading. BBB here is the bug.

`t.solo` is the CONTROL: the same reads on ONE channel, no interleaving. If it
also mis-reads, the fault is INPUT$ and not the buffer sharing, and the
interleaved row would prove nothing about buffers
[[a-case-that-agrees-can-agree-for-the-wrong-reason]].

⚠️ The VG-8020 is diskless; the CF-3300 is the only oracle.
⚠️ Every case gets a PRIVATE copy of the image -- these rows CREATE files.
"""
from __future__ import annotations

import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_tmp                                                  # noqa: E402

FIXTURE = os.path.join(ROOT, "disk", "test720.dsk")
SIDES = {
    "cf3300": ("National_CF-3300", 14.0, ("", "SCREEN 0", "NEW")),
    "zb": (os.environ.get("ZEROBAS_BASIC_MACHINE",
                          "C-BIOS_MSX1_EU_REPACK_DISK"), 8.0, ("NEW",)),
}

WRITE = ['10 MAXFILES=2',
         '20 OPEN"TWA.TXT"FOR OUTPUT AS #1:PRINT#1,"AAAAAAAAAAAA":CLOSE',
         '30 OPEN"TWB.TXT"FOR OUTPUT AS #1:PRINT#1,"BBBBBBBBBBBB":CLOSE']

CASES = [
    ("t.solo", WRITE + [
        '40 OPEN"TWA.TXT"FOR INPUT AS #1',
        '50 X$=INPUT$(3,#1)',
        '60 Y$=INPUT$(3,#1)',
        '70 Z$=INPUT$(3,#1)',
        '80 CLOSE',
        '90 PRINT"ZQ";X$;",";Y$;",";Z$;"QZ":END'],
     "CONTROL: one channel, no interleaving -- must read AAA,AAA,AAA"),
    ("t.two", WRITE + [
        '40 OPEN"TWA.TXT"FOR INPUT AS #1',
        '45 OPEN"TWB.TXT"FOR INPUT AS #2',
        '50 X$=INPUT$(3,#1)',
        '60 Y$=INPUT$(3,#2)',
        '70 Z$=INPUT$(3,#1)',
        '80 CLOSE',
        '90 PRINT"ZQ";X$;",";Y$;",";Z$;"QZ":END'],
     "THE ROW: interleaved. Z must be AAA -- BBB means #1 read #2's sector"),
]


def run(side, tag, prog):
    machine, boot, reset = SIDES[side]
    dsk = probe_tmp.tmp(f"twochan_{tag}_{side}.dsk")
    shutil.copyfile(FIXTURE, dsk)
    raw = "".join(omsx_repl.run_cases(
        machine, [("direct", list(reset) + prog + ["RUN"])], batch=False,
        # ⚠️ cap_gap=60. At 12 s the CF-3300 was STILL RUNNING when the capture
        # fired -- screen showed the program, `RUN`, and nothing else, with no
        # `Ok` and no error. That reads as `<NO READING>`, which is not an
        # outcome and which I nearly filed as "the reference produced nothing".
        # Two file creations plus four opens on emulated floppy simply take
        # longer than the default window.
        reset=(), boot=boot, step=8.0, cap_gap=60.0, timeout=400.0,
        diska=dsk)[0] or "")
    # 🔴 THE FENCE IS ALSO IN THE SOURCE THE MACHINE ECHOES. Line 90 contains
    # `ZQ";X$;",";Y$;",";Z$;"QZ` verbatim, so a first-match search reads the
    # TYPED LINE and reports `";X$;",";Y$;",";Z$;"` -- on BOTH sides, which then
    # agrees perfectly and means nothing [[trapsvc-echo-fence]]. The first cut of
    # this probe did exactly that and printed a confident green.
    # Two guards: take the LAST match (output follows the echo), and REFUSE any
    # match still carrying source punctuation.
    hits = re.findall(r"ZQ([^,]*),([^,]*),([^Q]*)QZ", raw)
    for g in reversed(hits):
        if any(ch in "".join(g) for ch in '"$;'):
            continue                       # that is the echo, not a reading
        return ",".join(x.strip() or "<empty>" for x in g)
    if re.search(r"ZQERR", raw):
        return "ERR"
    return "<NO READING (only the echo matched)>"


def main() -> int:
    rows = []
    for tag, prog, note in CASES:
        got = {s: run(s, tag, prog) for s in SIDES}
        rows.append((tag, note, got))
        print(f"  {tag:7s} " + "  ".join(f"{s}={got[s]:>16s}" for s in SIDES),
              flush=True)

    print(f"\n{'row':7s} {'cf3300':>16s} {'zb':>16s}   verdict")
    dis = []
    for tag, note, g in rows:
        c, z = g["cf3300"], g["zb"]
        verdict = "SAME" if c == z else "🔴 DIFF"
        if c != z:
            dis.append(tag)
        print(f"{tag:7s} {c:>16s} {z:>16s}   {verdict}")
        print(f"        {note}")
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    if not dis:
        print("🟢 The shared buffer does not lose data on this interleaving: "
              "the reference's per-channel buffers buy correctness zerobas "
              "already has by other means.")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
