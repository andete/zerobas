#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""LIST statement probe — validate zerobas's detokeniser by round-tripping a
stored program back to source on the screen.

Each test types one or more numbered lines into the zerobas REPL, then `LIST`,
and checks the on-screen output. LIST detokenises the stored crunched lines (the
inverse of the tokeniser): line number, a space, the de-crunched body, CR/LF. We
read the result by dumping the SCREEN 0 name table from VRAM (offset 0x0000, the
40x24 text grid) and decoding the MSX character codes (ASCII for printables) —
the same screen-output technique the dev-workflow "PRINT / screen output" recipe
uses.

LIST writes only to the screen (no cassette I/O), so this runs on C-BIOS_MSX1
and syncs on a generous --time window that outlasts the keystrokes. zerobas's
REPL drops a trailing CR that shares a burst with text, so every Enter is a
SEPARATE, later --type event (the screen probe's pattern).

The expectations encode the tokeniser/detokeniser round-trip, which matches a
real MSX-BASIC LIST: keywords upper-cased, the space the tokeniser drops between
PRINT and a string literal stays dropped, integer/&H constants and line-number
references render in their source form, ':'+ELSE prints as " ELSE", ':'+REM+mark
prints as "'", and DATA / REM / string-literal bodies are verbatim.

Clean-room: observed inputs/outputs only. See the clean-room firewall (CONTRIBUTING.md).
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra

import argparse
import os
import re
import subprocess
import sys
import tempfile


OMSX_RUN = os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib", "omsx_run.py")
# LIST is pure screen output; any MSX1 BIOS renders it identically. C-BIOS boots
# fast, so the --time window stays short.
# ⚠️ zerobas now runs on the REPACK machine, which carries the merged main ROM in
# slot 0 -- there is no cartridge to insert. It used to be C-BIOS_MSX1 (or the
# VG-8020) with the retired lean 16 KB cart in a slot; that build is gone
# (RETIRE THE LEAN 16 KB CART S3, docs/spec-lean-retire-s3-gates.md).
MACHINE = "C-BIOS_MSX1_EU_REPACK_DISK"
COLS = 40                 # SCREEN 0 (TEXT1) width
ROWS = 24
NAMETBL_LEN = COLS * ROWS


def run_list(prog_lines, base=6.0, step=3.0, tail=6.0):
    """Type each numbered line (each followed by a separate Enter), then LIST +
    Enter, and capture the SCREEN 0 name table once the dust settles."""
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="list_cap_")
    os.close(out_fd)
    cmd = [sys.executable, OMSX_RUN, "--machine", MACHINE]
    t = base
    for line in list(prog_lines) + ["list"]:
        cmd += ["--type", line, "--type-delay", str(t)]
        t += step
        cmd += ["--type", "\r", "--type-delay", str(t)]
        t += step
    cmd += ["--time", str(t + tail),
            "--mem", f"VRAM:0x0000:{NAMETBL_LEN}",
            "--out", out_path, "--timeout", "240"]
    subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cap = ""
    if os.path.exists(out_path):
        with open(out_path) as f:
            cap = f.read()
        os.unlink(out_path)
    return cap


def screen_lines(cap):
    """Decode the captured name table into a list of stripped text rows."""
    m = re.search(rf"mem\.VRAM:0x0000:{NAMETBL_LEN}=([0-9a-f]+)", cap)
    if not m:
        return []
    data = bytes.fromhex(m.group(1))
    rows = []
    for r in range(ROWS):
        row = data[r * COLS:(r + 1) * COLS]
        # SCREEN 0's text area carries a one-column left margin (the title and
        # prompt rows show it too), so strip both ends for comparison.
        rows.append("".join(chr(c) if 32 <= c < 127 else " " for c in row).strip())
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    args = ap.parse_args()

    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL'}  {label}" + (f"  {detail}" if detail else ""))
        if not cond:
            ok = False

    # Each case: (program lines typed) -> (expected LIST output lines). The
    # expected forms are the tokeniser/detokeniser round-trip (== a real MSX-BASIC
    # LIST): keywords upper-cased; PRINT's dropped space before a string stays
    # dropped; constants/line-refs in source form; ':'ELSE -> " ELSE"; ' verbatim.
    cases = [
        ("print + string + : + assignment + &H",
         ['10 print "hi":a=&hff'],
         ['10 PRINT "hi":A=&HFF']),
        ("FOR / TO / STEP with int + word constants",
         ['20 for i=1 to 10 step 2'],
         ['20 FOR I=1 TO 10 STEP 2']),
        ("IF / THEN line-ref + ELSE + multi-char vars + operator",
         ['30 if a>5 then 10 else b=c+1'],
         ['30 IF A>5 THEN 10 ELSE B=C+1']),
        ("POKE word + byte constants, REM verbatim tail",
         ['40 poke 256,255:rem done'],
         ['40 POKE 256,255:REM done']),
        ("PRINT ; and , separators",
         ['50 print a;b,c'],
         ['50 PRINT A;B,C']),
        ("DATA verbatim ASCII body",
         ['60 data 1,2,3'],
         ['60 DATA 1,2,3']),
        ("apostrophe comment round-trips to '",
         ["70 x=1 'loop start"],
         ["70 X=1 'loop start"]),
        ("multi-line program lists in order",
         ['100 a=1', '90 b=2', '110 c=3'],
         ['90 B=2', '100 A=1', '110 C=3']),
    ]

    for label, prog, expected in cases:
        rows = screen_lines(run_list(prog))
        # Find the contiguous block of LIST output: the expected lines should all
        # appear, in order, somewhere after the typed input echo. We match each
        # expected line as an exact (stripped) screen row.
        present = [exp in rows for exp in expected]
        # also enforce ordering of the matched rows
        order_ok = True
        if all(present):
            idxs = [rows.index(exp) for exp in expected]
            order_ok = idxs == sorted(idxs)
        cond = all(present) and order_ok
        detail = "" if cond else f"got rows={[r for r in rows if r and 'ZB' != r.strip()][:8]}"
        check(label, cond, detail)

    print("\nALL PASS" if ok else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
