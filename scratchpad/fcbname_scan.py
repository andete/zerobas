#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-FCBNAME -- WHERE does the reference keep the per-channel filename, and in
what form?

WHY THIS EXISTS, AND THE CORRECTION THAT PRODUCED IT. `dupopen_probe.py` measured
the CF-3300's duplicate-open rule black-box and the rows FORCE the conclusion
that the machine retains the name per channel: it allows `ts.dat` after `TS.DAT`
(so the compare is not case-folded), refuses `"TS.DAT "` (so it is the parsed 8.3
field, not the raw typed string), and refuses a name that is not on the disk at
all (so there is no directory entry to compare). I then wrote that whether it is
a dedicated field or a DOS-style FCB "we cannot see -- it is a black-box oracle".

🔴 THAT WAS WRONG, AND JOOST SAID SO IN FOUR WORDS: *"you can see RAM, no?"*
We can. `PEEK` is part of the reference's own observable surface and this tree
already reads it that way (`dskiwhere_probe.py` checksums pages of $C000..$FFFF,
`ramfree_probe.py` reads the published work area). Black-box means we do not
disassemble the ROM; it never meant we cannot look at the machine's RAM while it
runs. An inference was filed where a measurement was available.

THE INSTRUMENT. Open a file whose name cannot occur anywhere else, then have the
machine scan its own $C000..$FFFF for the signature and print every hit. The
name is BUILT FROM `CHR$` so the literal is not in the program text -- otherwise
the BASIC text area would answer with the probe's own source.

🔴 THE CONTROL IS THE WHOLE INSTRUMENT. `N$` exists either way, so the string
heap holds the signature in BOTH rows; so does any copy the OPEN parser leaves in
a scratch buffer. Only an address that appears with the file OPEN and NOT in the
control is evidence about per-channel storage.

\U0001f534 THIS PROBE WRITES TO THE SHARED FIXTURE, AND `fixture-integrity-check`
CAUGHT IT. `OPEN ... AS #n` on a name that is not on `disk/test720.dsk` CREATES
it, so a run leaves directory entries behind and every later disk probe is then
answering about an image nobody described. The gate named the exact repair:
`rm disk/test720.dsk && make test-dsk` (plain `make test-dsk` will NOT rebuild
it -- make only compares timestamps). Run that after this probe, or run the
battery and let the gate tell you again
[[a-mechanical-fix-can-break-a-different-invariant]].

⚠️ A NEGATIVE IS A READING, NOT A FAILURE. No separating hit means the name is
held outside $C000..$FFFF, or below it, or in RAM the BASIC slot configuration
hides from PEEK -- it does not mean the name is not stored, which the behavioural
rows already settled.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

DSK = os.path.join(ROOT, "disk", "test720.dsk")
CF = "National_CF-3300"

# "QZX" -- three bytes that do not occur in the probe's own program text, in the
# BASIC keyword table, or in a FAT12 boot sector's OEM name.
SIG = (0x51, 0x5A, 0x58)


def program(open_line, sig):
    """Scan $C000..$FFFF for `sig`, printing every hit address in hex.

    Only the FIRST byte is PEEKed per address; the other two are checked only on
    a hit, which keeps this to ~16384 PEEKs rather than three times that.
    """
    a, b, c = sig
    return [
        '10 ON ERROR GOTO 900',
        '20 MAXFILES = 2',
        # built from CHR$ so the signature is NOT in the program text
        '30 N$ = CHR$(81) + CHR$(90) + CHR$(88) + CHR$(74) + ".DAT"',
        '35 M$ = CHR$(113) + CHR$(122) + CHR$(120) + CHR$(106) + ".DAT"',
        f'40 {open_line}',
        '45 PRINT "ZP"; 1; "PZ"',
        '50 D$ = ""',
        f'60 FOR A = &HC000 TO &HFFFF',
        f'70 IF PEEK(A) <> {a} THEN 100',
        f'80 IF PEEK(A + 1) <> {b} THEN 100',
        f'90 IF PEEK(A + 2) = {c} THEN D$ = D$ + HEX$(A) + " "',
        '100 NEXT',
        '110 PRINT "ZQ"; D$; "QZ" : END',
        '900 PRINT "ZQ"; "E"; ERR; "QZ" : END',
    ]


LOWER = (0x71, 0x7A, 0x78)

CASES = [
    ("f.open", program('OPEN N$ AS #1 LEN = 128', SIG),
     "UPPER-case name open on #1; scan for the UPPER signature"),
    ("f.ctl", program('REM no open at all', SIG),
     "CONTROL: the identical program with NO file open. Every address here is "
     "the string heap or a parser scratch buffer and means nothing"),
    # 🎯 THE FORM ROW. The behavioural rule is case-SENSITIVE, so a stored name
    # that is upper-cased would contradict it. Open the LOWER-case spelling and
    # look for the UPPER signature: a hit means the machine folds case on the
    # way in, and the duplicate rule would then have to live somewhere else.
    ("f.lower.upsig", program('OPEN M$ AS #1 LEN = 128', SIG),
     "lower-case name open; scan for the UPPER signature -- a hit means the "
     "stored form IS case-folded, which the behavioural rows say it is not"),
    ("f.lower.losig", program('OPEN M$ AS #1 LEN = 128', LOWER),
     "lower-case name open; scan for the LOWER signature -- where it is kept "
     "verbatim"),
    # \U0001f3af THE DECISIVE ROW FOR THE COST QUESTION. One open cannot tell a
    # PER-CHANNEL field from a single parser scratch buffer -- both hold the name
    # once. Open TWO channels with DIFFERENT names and scan for the FIRST one: if
    # its signature survives the second open, the storage is per-channel; if the
    # second open overwrites it, it is one shared buffer and the duplicate check
    # must be reading something else.
    ("f.two", program('OPEN N$ AS #1 LEN = 128 : OPEN "TS2.DAT" AS #2 LEN = 128',
                      SIG),
     "TWO channels, different names; scan for channel 1's signature AFTER "
     "channel 2 is open -- survives = per-channel, gone = one shared buffer"),
]


# \U0001f534 THE READOUT WRAPS, AND A WRAPPED HEX TOKEN SPLITS IN TWO. The first
# run reported open-only addresses `['66', 'F8', ...]` -- `F866` broken across the
# 40-column boundary and read as two. `f.lower.losig` printed the same address
# intact, which is the only reason it was visible at all. Addresses are 4 hex
# digits by construction, so re-join anything shorter with its neighbour rather
# than reporting a 2-digit "address"
# [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].
def unwrap(toks):
    out = []
    for t in toks:
        if out and len(out[-1]) < 4 and len(out[-1]) + len(t) <= 4:
            out[-1] += t
        else:
            out.append(t)
    return [t for t in out if len(t) == 4]


def hits(scr):
    if scr is None:
        return None
    for g in reversed(re.findall(r"ZQ\s*([0-9A-FE ]*?)\s*QZ", scr)):
        if any(ch in g for ch in '"$;'):
            continue
        return g.strip()
    return None


def main():
    only = sys.argv[1].split(",") if len(sys.argv) > 1 else None
    sel = [c for c in CASES if not only or any(o in c[0] for o in only)]
    out = {}
    for lab, prog, _why in sel:
        # 🔴 `run_gap`, NOT `cap_gap` -- the window between RUN and the
        # capture is `run_gap`; `cap_gap` is the gap AFTER the capture and buys
        # this case nothing. A 16384-iteration PEEK loop needs the whole of it,
        # and with `cap_gap` the screen is read before the loop finishes and the
        # row reads blank -- which looks exactly like "the name is not in RAM".
        # And the disk argument is `diska`, not `disk`.
        caps = omsx_repl.run_cases(
            CF, [(lab, prog + ["RUN"])],
            batch=False, reset=("", "SCREEN 0", "NEW"), boot=14.0, step=5.0,
            run_gap=240.0, timeout=900.0, diska=DSK)
        out[lab] = hits(caps[0])
        print(f"  ran {lab:16s} -> {out[lab]!r}", flush=True)

    print()
    w = max(len(l) for l, _, _ in sel)
    for lab, _p, why in sel:
        print(f"  {lab:<{w}}  {out[lab]!r}\n      {why}")

    if "f.open" in out and "f.ctl" in out:
        o = set(unwrap((out['f.open'] or '').split()))
        c = set(unwrap((out['f.ctl'] or '').split()))
        if out["f.open"] is None or out["f.ctl"] is None:
            print("\n  ⚠️ NOT MEASURED: a row returned no reading at all.")
            return 2
        sep = sorted(o - c, key=lambda h: int(h, 16))
        print(f"\n  open-only addresses (the evidence): {sep or 'NONE'}")
        if not sep:
            print("  ⚠️ NEGATIVE: nothing separates. The name is held outside "
                  "$C000..$FFFF, or where PEEK cannot reach it. This does NOT "
                  "retract the behavioural finding that it IS retained.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
