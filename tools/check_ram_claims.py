#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""ram-claim-check — a RAM "this window is FREE" claim may not contain a NAME.

🔴 WHY THIS EXISTS (filed 2026-08-22 by the D-DEFFN RAM hunt,
docs/deffn-ramhunt-2026-08-22.md §1; built 2026-09-04). `make
wall-assertion-check` polices ROM free-space figures and dates them. **RAM
figures had no gate at all**, so they rot silently: `basic/sysvars.inc`
advertised *"376 B spare"* where **10** bytes were, for three slices, and what
caught it was the ASSEMBLER rather than any reading.

🎯 AND THE CLASS BIT AGAIN THE DAY THIS WAS WRITTEN, one commit old. D-CTLPOOL
added `CTLLIM equ $E056` and left a neighbouring comment claiming
`$E056..$E080 is FREE` — the cache's own two bytes, advertised as free. Nothing
would have found that; this check finds it in 40 ms.

WHAT IT CHECKS. Every `$AAAA..$BBBB … free` claim in the scanned files is
resolved, and **no `NAME equ <expr>` may land inside it**. The `equ` chain is
walked to a fixed point so `X equ Y + N*M` forms resolve.

🔴 WHAT IT DOES **NOT** CHECK, AND THIS IS THE POINT OF THE FILING. An address
says where a cell STARTS and never how long it is, so *"no name inside the
span"* does **not** mean the span is free: a cell whose name sits below the
claim can extend up into it. `TOKBUF`'s 612-byte delta to the next name is 36
bytes free; `LINEBUF`'s 256-byte delta is 0. **This check cannot see that**, and
promoting `scratchpad/rammap_sweep.py` to a gate on deltas alone would have
encoded exactly the error the filing warned about.

⚠️ So this is the CHEAP HALF, and it says so rather than implying coverage it
does not have. The expensive half is empirical — fill the window, work the
machine, read it back (`scratchpad/ramfree_probe.py`) — and it is the only thing
that can settle extent. A claim listed in `tools/ram-claims-unverified.txt`
is acknowledged as name-checked but NOT extent-checked.

⚠️ OVERLAP IS DESIGNED IN THIS TREE, NOT A BUG. Windows are deliberately aliased
between mutually exclusive execution contexts (the disk ROM's `SECTOR_BUF` over
the string pool; DRAW's frame buffer over PAINT's span stack). A name from
component B inside component A's claimed hole is therefore not automatically a
finding — which is why each file is checked against ITS OWN component's names,
and cross-component aliasing is reported separately as advisory.

Exit: 0 clean, 1 a claim contains a name, 2 the instrument could not measure.

    python3 tools/check_ram_claims.py [--selftest]
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOW = os.path.join(ROOT, "tools", "ram-claims-unverified.txt")

# Files whose `equ` names define a component's map, and whose comments carry the
# claims. Kept explicit: a glob would drag in the disk ROM's aliased windows and
# report designed overlap as breakage.
SCAN = ["basic/sysvars.inc"]

EQU = re.compile(r"^([A-Z_][A-Z_0-9]*)\s+equ\s+(.+?)\s*(?:;.*)?$", re.M)

# 🔴 A CLAIM IS **DECLARED**, NOT PROSE-MATCHED, AND THE FIRST CUT LEARNED WHY.
# It matched `$AAAA..$BBBB` followed by a free/FREE token within 90 characters
# and reported SEVEN violations, of which most were its own misreading: it took
# `$EA10..$EA2F` (a cell's own extent) off a line whose actual claim is
# `$EA92..$EAFF`; it flagged a layout table's `STRENG_SPARE $E3E5 .. $E3E6 1 B
# FREE`, where FREE describes the named cell rather than an empty span; and it
# flagged a comment QUOTING a historical claim it had itself corrected. A
# plausible table from a misread input is the failure this project keeps meeting
# [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]], so the shape
# is now explicit and unambiguous:
#
#     ; FREE-RAM $E058..$E080  <why it is free>
#
# ⚠️ AND PROSE IS NOT SILENTLY DROPPED. Anything free-shaped that is NOT declared
# is listed as ADVISORY, so the set can be migrated deliberately instead of a
# stale prose claim hiding behind a tighter regex.
CLAIM = re.compile(r"^\s*;\s*FREE-RAM\s+\$([0-9A-Fa-f]{4})\s*\.\.\s*"
                   r"\$([0-9A-Fa-f]{4})\b", re.M)
PROSE = re.compile(r"\$([0-9A-Fa-f]{4})\s*\.\.\s*\$([0-9A-Fa-f]{4})"
                   r"[^\n]{0,90}?\b(?:FREE|free)\b")
MIN_NAMES = 200      # a map smaller than this means the parse broke
MIN_CLAIMS = 3       # ...and so does a file with almost no claims in it


def resolve(text):
    """NAME -> int for every `equ` that reduces to a number, walked to a fixed
    point so `X equ Y + N*M` chains resolve. Non-numeric forms are dropped."""
    raw = dict(EQU.findall(text))
    out, changed = {}, True
    while changed:
        changed = False
        for name, expr in raw.items():
            if name in out:
                continue
            e = expr.replace("$", "0x")
            try:
                val = eval(e, {"__builtins__": {}}, dict(out))   # noqa: S307
            except Exception:
                continue
            if isinstance(val, int):
                out[name] = val
                changed = True
    return out


def load_allow():
    if not os.path.exists(ALLOW):
        return {}
    out = {}
    for line in open(ALLOW):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, why = line.partition(" ")
        out[key] = why.strip()
    return out


def check(path, allow):
    text = open(os.path.join(ROOT, path)).read()
    names = resolve(text)
    claims = [(int(m.group(1), 16), int(m.group(2), 16), m.start())
              for m in CLAIM.finditer(text)]
    declared = {(lo, hi) for lo, hi, _ in claims}
    prose = [(int(m.group(1), 16), int(m.group(2), 16), m.start())
             for m in PROSE.finditer(text)]
    undeclared = [(lo, hi, off) for lo, hi, off in prose
                  if (lo, hi) not in declared and hi > lo]
    if len(names) < MIN_NAMES or len(claims) < MIN_CLAIMS:
        print(f"INSTRUMENT FAULT: {path} parsed {len(names)} name(s) and "
              f"{len(claims)} claim(s); floors are {MIN_NAMES}/{MIN_CLAIMS}. The "
              f"parse broke -- a clean run here would mean nothing.")
        return None, None, None
    line_of = lambda off: text.count("\n", 0, off) + 1     # noqa: E731
    bad, acked = [], []
    for lo, hi, off in claims:
        if hi <= lo:
            continue                                        # a reversed pair is prose
        inside = sorted((v, n) for n, v in names.items() if lo <= v < hi)
        if not inside:
            continue
        key = f"{path}:${lo:04X}..${hi:04X}"
        (acked if key in allow else bad).append((key, line_of(off), inside))
    return bad, acked, (len(names), len(claims), undeclared, line_of)


def selftest():
    """A GREEN control and a PLANTED claim that must go red. Without the plant,
    "0 violations" is equally what a check that matches nothing prints."""
    # ⚠️ NO TEMP FILE. The first cut made a `tempfile.TemporaryDirectory()`,
    # wrote the fixture into it and then never opened it -- every assertion below
    # works on the string. `make temp-root-check` caught the unused call escaping
    # the project temp root [[one-temp-root]], which is the right answer to an
    # allocation nothing reads.
    fails = 0
    base = ("FOO             equ     $E100\n" * 1 +
            "\n".join(f"N{i:03d}          equ     $D{i:03X}" for i in range(260)) +
            "\n; FREE-RAM $E200..$E300 clean\n; FREE-RAM $E0F0..$E110 planted\n"
            "; FREE-RAM $E400..$E500 clean\n; $E600..$E700 free (prose, advisory)\n")
    if True:
        names = resolve(base)
        if len(names) < 260:
            print(f"  selftest: resolve() found {len(names)} names, want >=260"); fails += 1
        claims = CLAIM.findall(base)
        if len(claims) != 3:
            print(f"  selftest: found {len(claims)} declared claims, want 3"); fails += 1
        # ...and the prose line must be seen as ADVISORY, not as a claim
        pr = [c for c in PROSE.findall(base)]
        if len(pr) != 1:
            print(f"  selftest: found {len(pr)} prose spans, want 1"); fails += 1
        # FOO ($E100) lies inside the planted $E0F0..$E110 claim and must be seen
        hit = [n for n, v in names.items() if 0xE0F0 <= v < 0xE110]
        if hit != ["FOO"]:
            print(f"  selftest: planted overlap not detected (got {hit})"); fails += 1
        # ...and the $E200..$E300 claim must NOT be flagged
        if [n for n, v in names.items() if 0xE200 <= v < 0xE300]:
            print("  selftest: clean claim reported as overlapping"); fails += 1
        # a chained equ must resolve, or real maps under-parse silently
        ch = resolve("A equ $E000\nB equ A + 2*8\n")
        if ch.get("B") != 0xE010:
            print(f"  selftest: chained equ resolved to {ch.get('B')}"); fails += 1
    print("  selftest: PASS" if not fails else f"  selftest: {fails} FAILURE(S)")
    return fails


def main(argv):
    if "--selftest" in argv:
        return 2 if selftest() else 0
    allow = load_allow()
    total_bad, total_ack, any_parsed = [], [], False
    advisory = []
    for path in SCAN:
        bad, acked, counts = check(path, allow)
        if bad is None:
            return 2
        any_parsed = True
        nnames, nclaims, undeclared, line_of = counts
        print(f"== {path} == ({nnames} names, {nclaims} declared FREE-RAM claim(s))")
        advisory += [(path, lo, hi, line_of(off)) for lo, hi, off in undeclared]
        total_bad += bad
        total_ack += acked
    if not any_parsed:
        print("INSTRUMENT FAULT: nothing scanned.")
        return 2
    for key, line, inside in total_ack:
        print(f"  [acknowledged] {key} (line {line}) contains "
              f"{', '.join(n for _v, n in inside)}")
    for key, line, inside in total_bad:
        print(f"  🔴 {key} (line {line}) is claimed FREE but contains "
              + ", ".join(f"{n} (${v:04X})" for v, n in inside))
    if advisory:
        print(f"\n  ADVISORY -- {len(advisory)} free-shaped span(s) in PROSE, not "
              f"declared and therefore NOT checked. Convert to `; FREE-RAM $A..$B`"
              f" or leave as narrative; a claim nobody gates is a reading with a "
              f"date on it:")
        for path, lo, hi, line in advisory:
            print(f"    {path}:{line}  ${lo:04X}..${hi:04X}")
    print(f"\n{len(total_bad)} violation(s)"
          + (f", {len(total_ack)} acknowledged" if total_ack else ""))
    if total_bad:
        print("  A claimed-free window with a name in it is a stale figure: either "
              "the cell moved and the comment did not, or the claim was written "
              "from a delta between two names -- which is not free space.")
    else:
        print("  clean -- no claimed-free RAM window contains a named cell.")
    print("⚠️ NAME-LEVEL ONLY. An address says where a cell STARTS, never how long "
          "it is, so this cannot see a cell extending up into a claim from below "
          "(TOKBUF: 612 B delta, 36 B free). Extent needs the machine -- "
          "scratchpad/ramfree_probe.py.")
    return 1 if total_bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
