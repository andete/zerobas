#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""The sub-ROM wall readout, gated (docs/spec-subwall-readout.md).

    python3 tools/check_sub_walls.py build/sub.rom build/sub.sym

check_reloc.py prints the two MAIN walls on every build from __MEAS_LOW_END /
__MEAS_PAGE1_END, and its docstring says why its .sym argument is REQUIRED: an
optional sym is exactly the shape in which a wall readout silently stops printing
while the gate still exits 0. The sub ROM had neither label and no readout, so
every sub-ROM wall figure this project ever recorded was hand-measured, per slice,
with whatever instrument that slice reached for -- and nothing cross-checked one
against the next. Two of them were wrong before anybody noticed:

  * sub page 0 3869 -> 3852 at b5f4135. The 17 B are D-LPTVERB's own LPRINT/LPOS
    keyword entries, which live in basic/kwtable.inc, which sub/sub.asm is the
    sole include site of -- so they land on THIS page. The slice measured the 17
    (its as-built table says "+17 is exactly the 9 B LPRINT + 8 B LPOS entries")
    and two rows above wrote "sub sides unchanged".
  * sub page 1 1821 recorded as 1824 at fa0b952. That value occurs at 0 of the 424
    buildable commits in this ROM's entire history.

THE MODEL. The zero-byte labels are the measurement; the trailing-$FF scan is a
ONE-SIDED cross-check. The sub ROM pads with $FF, not $00, so a scan cannot
separate pad from content that happens to end in $FF -- it can only OVER-report.
Everything after a label IS pad, therefore

    scan >= label,  always, for a matched .rom/.sym pair

and `scan - label` is the exact size of the lie a hand scan would tell today. It
is printed rather than hidden. `scan < label` is impossible for a matched pair, so
check 5 firing means the .sym and the .rom came from different builds -- which is
the staleness class this repo keeps paying for.

⚠️ CHECK 2 IS THE POSITIVE CONTROL, AND IT IS NOT DECORATION. Point checks 1/3/4/5
at 32768 bytes of $FF with the real sub.sym and every one of them PASSES: right
size, labels present and in range, and every byte after each label is $FF --
because every byte is. The readout then prints the CORRECT free figures for a ROM
with no ROM in it. A gate whose answer is "nothing is there" cannot tell a correct
answer from a dead subject, so the run needs one thing that must be PRESENT: the
"CD" sub-ROM signature at $0000 and the deliberately-not-"AB" "S1" marker at
$4000, both of which sub/sub.asm states in prose and both of which die on an
all-$FF, an all-$00 and a truncated image alike. It is check_reloc.py's own
"AB"-at-$4000 pin, one ROM over.

EXIT CODES. 1 = the subject regressed (check 4: a wall overran its page). 2 = the
instrument was not functioning and nothing below it was measured (checks 1/2/3/5).
⚠️ The distinction is only visible when this tool is invoked DIRECTLY: `make`
exits 2 for any failed recipe, so a runner shelling out to `make basic-reloc`
cannot tell rc 1 from rc 2.
"""
from __future__ import annotations

import re
import sys

P0_BASE, P0_TOP = 0x0000, 0x4000
P1_BASE, P1_TOP = 0x4000, 0x8000
ROM_SIZE = 0x8000
PAD = 0xFF

# The two structural anchors. Not free space, not derived: sub/sub.asm pins both
# by address and says why in its header ("CD" = MSX2 sub-ROM signature; "S1" =
# page-1 marker chosen NOT to be "AB" so the cartridge scan skips it).
ANCHORS = ((P0_BASE, b"CD"), (P1_BASE, b"S1"))

PAGES = (
    ("sub page 0", "__MEAS_SUB_P0_END", P0_BASE, P0_TOP,
     "$0000-$3FFF, the callable-from-main island"),
    ("sub page 1", "__MEAS_SUB_P1_END", P1_BASE, P1_TOP,
     "$4000-$7FFF, the BIOS-visible island"),
)


def load_syms(path):
    syms = {}
    pat = re.compile(r"^(\S+)\s+EQU\s+([0-9A-Fa-f]+)H", re.IGNORECASE)
    with open(path) as fh:
        for line in fh:
            m = pat.match(line.strip())
            if m:
                syms[m.group(1)] = int(m.group(2), 16)
    return syms


def tail_run(image, base, top):
    """Trailing-$FF run length in [base, top) -- the hand instrument, kept only
    so its over-report can be reported."""
    i = top
    while i > base and image[i - 1] == PAD:
        i -= 1
    return top - i


def main(argv) -> int:
    if len(argv) != 3:
        sys.exit(__doc__)
    image = open(argv[1], "rb").read()
    bad = []                      # instrument faults -> rc 2
    regressed = []                # subject regressions -> rc 1

    # 1 -- the image is the ROM it claims to be
    if len(image) != ROM_SIZE:
        bad.append(f"{argv[1]} is {len(image)} B, not {ROM_SIZE} "
                   f"($0000-$7FFF) -- nothing below this was measured")
        for e in bad:
            print("FAIL:", e, file=sys.stderr)
        return 2

    # 2 -- the positive control (see the header)
    for addr, want in ANCHORS:
        got = image[addr:addr + len(want)]
        if got != want:
            bad.append(f"{want.decode()} anchor missing at {addr:#06x}: {got!r} "
                       f"-- this image is not a live sub ROM, and the free-space "
                       f"figures below would be CORRECT for a dead one")

    # 3 -- both labels present (check_reloc.py's REQUIRED-sym argument, same reason)
    syms = load_syms(argv[2])
    missing = [n for _, n, _, _, _ in PAGES if n not in syms]
    if missing:
        bad.append(f"{argv[2]} defines no {', '.join(missing)} -- the sub-ROM WALL "
                   f"READOUT would print nothing, which is how a wall measurement "
                   f"becomes a hand-carried number again")

    if bad:
        for e in bad:
            print("FAIL:", e, file=sys.stderr)
        return 2

    rows = []
    for title, label, base, top, where in PAGES:
        end = syms[label]
        # 4 -- the label is inside its own page. A body that overran would put it
        # past `top`; a swapped pair would put it below `base`.
        if not base <= end <= top:
            regressed.append(
                f"{label} @ {end:#06x} is outside {title} "
                f"({base:#06x}-{top:#06x}) -- the page overran, or the labels are "
                f"swapped. Free space is not a number here")
            continue
        # 5 -- everything from the label to the page end must BE pad. This is the
        # cross-check, and the only thing that can catch a .sym from another build.
        first_bad = next((i for i in range(end, top) if image[i] != PAD), None)
        if first_bad is not None:
            bad.append(
                f"{title}: {label} @ {end:#06x} claims the pad starts there, but "
                f"{argv[1]} has {image[first_bad]:#04x} at {first_bad:#06x} -- "
                f"{argv[2]} and {argv[1]} are NOT from the same build")
            continue
        rows.append((title, label, end, top - end, tail_run(image, base, top), where))

    if regressed:
        for e in regressed:
            print("FAIL:", e, file=sys.stderr)
        return 1
    if bad:
        for e in bad:
            print("FAIL:", e, file=sys.stderr)
        return 2

    print(f"OK: sub ROM {len(image)} B, 'CD' @ $0000, 'S1' @ $4000, both wall "
          f"labels inside their page and both pads verified")
    for title, label, end, free, scan, where in rows:
        print(f"    measure: {title} free       = {free} B "
              f"({where}, {label} @ {end:#06x})")
        # ⚠️ GUARDED ON `>`, NOT `!=`, AND THAT IS NOT PEDANTRY. Knife K6 neutered
        # check 5 and this line printed `-279 B too many: the content ends in -279
        # $FF byte(s)` -- a negative over-report, which is not a smaller finding
        # than the mismatch, it is the SAME finding rendered as a confident
        # sentence that reads like a measurement. `scan < free` is impossible for
        # a matched pair, so if it is ever reached the instrument is broken and
        # must SAY SO rather than narrate a negative.
        if scan > free:
            print(f"             ⚠️ a trailing-$FF scan reads {scan} B here, "
                  f"{scan - free} B too many: the content ends in {scan - free} "
                  f"$FF byte(s). The LABEL is the measurement")
        elif scan < free:
            print(f"FAIL: {title}: trailing-$FF scan reads {scan} B but {label} "
                  f"claims {free} B free. A scan can only ever OVER-report, so "
                  f"this is impossible for a matched pair -- check 5 should have "
                  f"caught it first and did not: THE INSTRUMENT IS BROKEN",
                  file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
