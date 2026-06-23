#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""String-variable probe — validate zerobas's minimal string support for PRINT.

zerobas Phase 1 has just enough string handling to PRINT a `$`-suffixed string
variable: assign a literal (A$="HELLO"), copy a string var (B$=A$), and PRINT a
string var, including alongside a literal (PRINT "X=";A$). The full string engine
(heap, concat, LEFT$/MID$/CHR$/…, string arrays) is Phase 2 and out of scope.

Each case types one direct-mode line into the zerobas REPL, then reads the
on-screen output by dumping the SCREEN 0 name table from VRAM (offset 0x0000, the
40x24 text grid) and decoding the MSX character codes — the same screen-output
technique basic_probe_list.py / basic_probe_screen.py use. This is pure screen
output (no cassette I/O), so it runs on C-BIOS_MSX1 and syncs on a generous
--time window that outlasts the keystrokes. zerobas's REPL drops a trailing CR
that shares a burst with text, so every Enter is a SEPARATE, later --type event.

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
MACHINE = "C-BIOS_MSX1"
COLS = 40                 # SCREEN 0 (TEXT1) width
ROWS = 24
NAMETBL_LEN = COLS * ROWS


def run_lines(cart, lines, base=6.0, step=3.0, tail=6.0):
    """Type each direct-mode line (each followed by a separate Enter), then
    capture the SCREEN 0 name table once the dust settles."""
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="strvar_cap_")
    os.close(out_fd)
    cmd = [sys.executable, OMSX_RUN, "--machine", MACHINE, "--cart", cart]
    t = base
    for line in lines:
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
        rows.append("".join(chr(c) if 32 <= c < 127 else " " for c in row).strip())
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cart", required=True, help="zerobas basic.rom")
    args = ap.parse_args()

    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL'}  {label}" + (f"  {detail}" if detail else ""))
        if not cond:
            ok = False

    # Each case: (direct-mode lines typed) -> (expected output line that must
    # appear as an exact stripped screen row). The PRINT runs on the same line as
    # the assignment (via ':'), so each case is one typed line.
    # String-LITERAL bytes are kept verbatim by the tokeniser (not upcased), so
    # the literal content is typed in upper case to make the expected screen row
    # unambiguous; the variable names (outside the quotes) are upcased anyway.
    cases = [
        ("assign literal + PRINT the string var",
         ['a$="HELLO":print a$'],
         "HELLO"),
        ("PRINT literal ; string var",
         ['a$="HELLO":print "X=";a$'],
         "X=HELLO"),
        ("copy string var (B$=A$) + PRINT the copy",
         ['a$="WORLD":b$=a$:print b$'],
         "WORLD"),
        ("LET keyword form + PRINT",
         ['let a$="ABC":print a$'],
         "ABC"),
        ("two string vars are independent",
         ['a$="ONE":b$="TWO":print a$;b$'],
         "ONETWO"),
        ("reassign a string var",
         ['a$="FIRST":a$="SECOND":print a$'],
         "SECOND"),
    ]

    for label, lines, expected in cases:
        rows = screen_lines(run_lines(args.cart, lines))
        cond = expected in rows
        detail = "" if cond else f"got rows={[r for r in rows if r and 'zb>' not in r][:8]}"
        check(label, cond, detail)

    print("\nALL PASS" if ok else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
