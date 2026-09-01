#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Functional + differential oracle for zerobas-BASIC PRINT USING (Phase 2).

PRINT USING formats values through a template: numeric `#` fields (right-justified,
`%` overflow), string fields (`\\ \\` fixed width, `!` first char, `&` whole), literal
passthrough, and format reuse when the value list outruns the template.

A small tagged program is RUN so each result lands on its own screen line, wrapped
`<tag><result>|` (the trailing ';' on the PRINT USING suppresses its newline, then
`PRINT"|"` bounds the field so trailing spaces are unambiguous):

  10 a$="cat"
  20 print"A";:print using"###";5;:print"|"      -> A  5|
  30 print"B";:print using"###";-7;:print"|"      -> B -7|
  40 print"C";:print using"##";1234;:print"|"     -> C%1234|   (field overflow)
  50 print"D";:print using"\\ \\";a$;:print"|"       -> Dcat|     (width-3 field)
  60 print"E";:print using"!";a$;:print"|"        -> Ec|       (first char)
  70 print"F";:print using"&";a$;:print"|"        -> Fcat|     (whole string)
  80 print"G";:print using"## ";1;2;3;:print"|"   -> G 1  2  3 |  (format reuse)

zerobas runs as a cartridge on a real Philips VG-8020; the reference is the same
machine's built-in MSX-BASIC. Same hardware, same SCREEN 0 — a true differential.
(zerobas is integer-only, so every value here is an integer; the float-only format
specs are a later phase.) Black-box: types REPL lines, reads VRAM.
"""
from __future__ import annotations


# ============================================================================
# 🔴 RETIRED 2026-09-01 (D-LEANRETIRE-PROBES) -- THE VEHICLE, NOT THE ROWS.
# This probe booted zerobas AS A CARTRIDGE on a real MSX BIOS machine. That
# delivery vehicle was the lean 16 KB cart, retired by
# docs/spec-lean-retire-s1..s3; the shipping artifact is now the 32 KB repack
# MAIN ROM, which by construction cannot be a cartridge on the VG-8020 (a cart
# maps at $4000-$7FFF; the repack image IS the machine's $0000-$7FFF). So the
# experiment has no vehicle, not merely no default -- no S1 machine flag can
# revive it.
# Its SUBJECT survives: PRINT USING coverage lives in the standing rows
# (docs/spec-print-hash-using.md) and disk_probe_printusing_file, which is
# archived AND re-provable on the repack machine.
# The file is kept for its harness patterns and history; running it says this
# instead of pretending to measure.
# ============================================================================
import sys as _retired_sys
if __name__ == "__main__" or True:
    _retired_sys.exit("RETIRED (D-LEANRETIRE-PROBES, 2026-09-01): this probe "
                      "booted zerobas as a CARTRIDGE on a real MSX BIOS -- the "
                      "lean-cart vehicle docs/spec-lean-retire-s1..s3 removed. "
                      "The repack main ROM cannot be that cartridge. "
                      "PRINT USING coverage: docs/spec-print-hash-using.md + disk_probe_printusing_file.")


# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra

import argparse
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "lib"))
import omsx_preflight  # noqa: E402

OMSX = shutil.which("openmsx") or "/Applications/openMSX.app/Contents/MacOS/openmsx"
ZEROBAS = os.environ.get("ZEROBAS", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CART = os.environ.get("ZEROBAS_ROM", os.path.join(ZEROBAS, "build", "basic.rom"))

PROGRAM = [
    'a$="cat"',
    'print"A";:print using"###";5;:print"|"',
    'print"B";:print using"###";-7;:print"|"',
    'print"C";:print using"##";1234;:print"|"',
    r'print"D";:print using"\ \";a$;:print"|"',
    'print"E";:print using"!";a$;:print"|"',
    'print"F";:print using"&";a$;:print"|"',
    'print"G";:print using"## ";1;2;3;:print"|"',
]
# number the lines so RUN replays them; the bare tag-prefixed output lines are then
# the only rows that START with a tag letter (echoed source rows start with a digit).
NUMBERED = [f"{(i+1)*10} {ln}" for i, ln in enumerate(PROGRAM)] + ["run"]

EXPECT = {"A": "  5", "B": " -7", "C": "%1234", "D": "cat",
          "E": "c", "F": "cat", "G": " 1  2  3 "}


def build_tcl(out_path, lines):
    body = ['after time 11 { type "\\r" }']   # dismiss any startup prompt
    t, step = 14, 7
    for ln in lines:
        body.append(f'after time {t} {{ type {{{ln}}} }}')
        body.append(f'after time {t+4} {{ type "\\r" }}')
        t += step
    body.append(f'after time {t+6} {{ puts $__f "scr=[__hex_v 0x0000 960]";'
                f' flush $__f; close $__f; exit }}')
    return ("set throttle off\n"
            f"set __f [open {{{out_path}}} w]\n"
            "proc __hex_v {a l} { binary scan [debug read_block VRAM $a $l] H* h;"
            " return $h }\n" + "\n".join(body) + "\n")


def run(out, cart):
    open(out + ".tcl", "w").write(build_tcl(out, NUMBERED))
    if os.path.exists(out):
        os.unlink(out)
    cmd = [OMSX, "-machine", "Philips_VG_8020"]
    if cart:
        cmd += ["-carta", cart]
    cmd += ["-command", "set renderer none; set sound_driver null", "-script", out + ".tcl"]
    proc = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    deadline = time.time() + 150
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        sys.exit("TIMEOUT")
    rows = []
    for ln in open(out):
        if ln.startswith("scr="):
            d = bytes.fromhex(ln.strip().partition("=")[2])
            s = "".join(chr(c) if 32 <= c < 127 else " " for c in d)
            rows = [s[i:i + 40] for i in range(0, 960, 40)]
    # an output row starts (ignoring leading spaces) with a tag letter and has a '|'.
    found = {}
    for row in rows:
        st = row.lstrip()
        if st[:1] in EXPECT and "|" in st:
            tag = st[0]
            found[tag] = st[1:st.index("|")]
    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-ref", action="store_true")
    args = ap.parse_args()

    got = run("/tmp/zpu.txt", CART)
    print("--- zerobas PRINT USING ---")
    okf = True
    for tag in sorted(EXPECT):
        g = got.get(tag)
        ok = g == EXPECT[tag]
        okf = okf and ok
        print(f"  {tag}: {g!r:12} {'ok' if ok else 'FAIL expected ' + repr(EXPECT[tag])}")
    print("functional:", "PASS" if okf else "FAIL")
    rc = 0 if okf else 1

    if not args.no_ref:
        ref = run("/tmp/zpu_ref.txt", None)
        print("\n--- VG-8020 differential ---")
        okr = True
        for tag in sorted(EXPECT):
            r = ref.get(tag)
            ok = r == got.get(tag) == EXPECT[tag]
            okr = okr and ok
            print(f"  {tag}: {r!r:12} {'ok' if ok else 'DIFFERS'}")
        print("differential:", "PASS — identical to zerobas" if okr else "FAIL")
        rc = rc or (0 if okr else 1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
