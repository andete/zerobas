#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Run the example programs of the per-keyword docs (docs/keywords/) on zerobas
AND on the reference, and print both screens, so every output a doc shows is a
measurement rather than a guess.

Clean-room: typed BASIC in, the screen (and for disk examples the machine's own
scratch disk image) out. No reference ROM byte is read.

  python3 -u scratchpad/kwdoc_examples.py CHR$      # one keyword
  python3 -u scratchpad/kwdoc_examples.py           # all of them

Exit 0 when every example's screen agrees between the two machines, 1 otherwise.
"""
import os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402

VG = "Philips_VG_8020"
CF = "National_CF-3300"
OURS_NODISK = "C-BIOS_MSX1_EU_REPACK_NODISK"
OURS_DISK = "C-BIOS_MSX1_EU_REPACK_DISK"

# keyword -> (reference, ours, needs a disk, typed lines). Every line <= 39 chars.
EXAMPLES = {
    "CHR$": (VG, OURS_NODISK, False, [
        "10 FOR I=65 TO 69:A$=A$+CHR$(I):NEXT",
        "20 PRINT A$",
        "30 PRINT LEN(CHR$(0));ASC(CHR$(65.7))",
        "40 ON ERROR GOTO 70",
        "50 PRINT CHR$(256)",
        "60 END",
        '70 PRINT "Error";ERR:RESUME NEXT',
        "RUN",
    ]),
    # disk/test720.dsk holds TEST.BIN HI.TXT PROG.BIN PROG.BAS PROG2.BAS PROG3.BAS
    "COPY": (CF, OURS_DISK, True, [
        "10 ON ERROR GOTO 90",
        '20 COPY "HI.TXT" TO "HI2.TXT"',
        '30 COPY "HI.TXT" TO "X?.TXT"',
        '40 COPY "NONE.TXT" TO "N.TXT"',
        '50 COPY "HI.TXT" TO "HI.TXT"',
        "60 FILES",
        "70 END",
        '90 PRINT "Error";ERR;"in";ERL:RESUME NEXT',
        "RUN",
    ]),
}


def rows(screen):
    """The screen as its non-blank 40-column rows."""
    if screen is None:
        return None
    out = [screen[i:i + 40].rstrip() for i in range(0, len(screen), 40)]
    return [r for r in out if r]


def run(kw):
    ref, ours, disk, lines = EXAMPLES[kw]
    got = {}
    for tag, machine in (("reference " + ref, ref), ("zerobas   " + ours, ours)):
        kwargs = dict(batch=False, reset=("", "SCREEN 0:WIDTH 40"), step=3.0)
        if disk:
            dsk = probe_tmp.tmp(f"kwdoc_{re.sub(r'[^A-Za-z]', '_', kw)}_{machine}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            kwargs.update(diska=dsk, boot=14.0, step=4.5, run_gap=30.0)
        raw = omsx_repl.run_cases(machine, [("direct", lines)], **kwargs)[0]
        got[tag] = rows(raw)
    for tag, r in got.items():
        print(f"--- {kw}: {tag}")
        print("\n".join(r) if r is not None else "<NO CAPTURE>")
    # zerobas's prompt reads `ZB` where the reference's reads `Ok` (Joost's
    # ruling: the text stays) -- a prompt row is not part of the comparison.
    a, b = ([x for x in r if x not in ("Ok", "ZB")] if r is not None else None
            for r in got.values())
    same = a is not None and a == b
    print(f"=== {kw}: {'SAME' if same else 'DIFFERENT'}\n")
    return same


def main():
    only = sys.argv[1:] or list(EXAMPLES)
    results = [run(kw) for kw in only]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
