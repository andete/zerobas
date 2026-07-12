#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Oracle + differential probe -- INKEY$ (INKEY$ slice S3).

INKEY$, per docs/spec-basic-inkey.md. The first keyboard-reading string verb, so
this probe is the first to DRIVE THE KEYBOARD: it injects a keystroke mid-run and
asserts INKEY$ hands it to the program. Two halves, modelled on basic_probe_str_fn.py:

1. REFERENCE ORACLE (black-box, no disassembly). Runs each case on the real Philips
   VG-8020's built-in MSX-BASIC (no cartridge) and asserts the reference's own screen
   output matches the spec §2 contract (empty string when no key; the injected char
   when one is pending). Expected values are DERIVED from the contract, not assumed.

2. ZEROBAS DIFFERENTIAL. Runs the IDENTICAL case on the repack machine
   (C-BIOS_MSX1_EU_REPACK_DISK -- the string engine is repack-only) and asserts
   zerobas's result equals the reference's.

Two case shapes:
  * EMPTY path -- a direct-mode `PRINT "[";INKEY$;"]"` with no key pending prints an
    empty string `[]` on both. Deterministic; no injection. (This is exactly the case
    the S2 live smoke test found failing: PRINT INKEY$ hit "type mismatch" until the
    exp_loop $EC hook landed -- the same print.asm dispatch-gap class the string-
    functions slice hit with PRINT STRING$. It is kept as a literal PRINT test so the
    gate keeps guarding that hook.)
  * KEY path -- a bounded poll loop `10 A$=INKEY$:IF A$=""THEN10` / `20 PRINT"<";A$;">"`,
    RUN, then a key is INJECTED while the loop spins. Because the loop blocks until a
    key arrives, the exact injection instant is not timing-critical (both machines
    capture whatever key lands), which keeps the differential deterministic despite the
    real-time keyboard.

Clean-room: this only *observes* black-box behaviour (type a line, inject a key, read
the screen). The reference ROM is never read as code. See CONTRIBUTING.md.

    python3 probes/basic/basic_probe_inkey.py
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections import namedtuple

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402  typing-free KEYBUF-injection REPL driver

REF_MACHINE = "Philips_VG_8020"    # reference: built-in MSX-BASIC, no cartridge
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
COLS, ROWS = 40, 24
NLEN = COLS * ROWS


def run_line(machine, line, **_):
    """Inject one direct-mode line via omsx_repl (KEYBUF, typing-free) and return
    the SCREEN 0 name table as one raw row-major string of length NLEN (non-print
    bytes -> space). For the empty INKEY$ case: the line editor drains KEYBUF (the
    line + its CR) before the statement executes, so INKEY$ finds nothing pending
    and PRINT emits []."""
    return omsx_repl.run_case(machine, "direct", [line])


def run_key_prog(machine, key, **_):
    """Enter the INKEY$ poll-loop program as two direct-mode numbered lines, RUN
    it, then INJECT `key` as a trailing raw line while the loop spins; capture the
    SCREEN 0 name table. The line editor consumes each of `10 ...`, `20 ...`, `RUN`
    (and their CRs) in turn, so by the time `key` is injected RUN is already
    executing and the loop is spinning on INKEY$; the loop blocks until a key
    lands, so `key`'s exact arrival instant is not timing-critical (both machines
    capture whatever key arrives), keeping the differential deterministic despite
    the real-time keyboard. INKEY$ reads the single `key` char out of KEYBUF; the
    submitting CR left behind is harmless (the program has already left the loop)."""
    return omsx_repl.run_case(machine, "direct",
                              ['10 A$=INKEY$:IF A$=""THEN10',
                               '20 PRINT"<";A$;">"', 'RUN', key])


def extract_bracket(raw, open_c, close_c):
    """The content of the LAST non-nested `open_c ... close_c` pair. The echoed
    source line carries the SAME delimiters before the real result is printed, so
    (as in basic_probe_str_fn.extract) the result -- printed later, lower on the
    top-down-scrolling screen -- is the last match in row-major order."""
    if raw is None:
        return None
    matches = re.findall(rf"{re.escape(open_c)}([^{re.escape(open_c)}{re.escape(close_c)}]*)"
                         rf"{re.escape(close_c)}", raw)
    return matches[-1] if matches else None


# (label, shape, arg, expect) -- shape 'empty' => direct PRINT, no key, expect '';
#   shape 'key' => poll loop + inject arg, expect the injected char back.
Case = namedtuple("Case", "label shape arg expect")

CASES = [
    Case("empty",     "empty", None, ""),      # PRINT INKEY$ with no key -> []
    Case("key.letter", "key",  "Z",  "Z"),     # inject 'Z' -> <Z>
    Case("key.digit",  "key",  "5",  "5"),     # inject '5' -> <5>
]


def measure(machine, c, timeout):
    """Run one case on `machine`, return the observed result string (or None)."""
    if c.shape == "empty":
        return extract_bracket(run_line(machine, 'PRINT "[";INKEY$;"]"', timeout=timeout),
                               "[", "]")
    return extract_bracket(run_key_prog(machine, c.arg, timeout=timeout), "<", ">")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=REF_MACHINE,
                    help="reference machine (built-in BASIC oracle)")
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE,
                    help="zerobas repack machine (string engine is repack-only)")
    ap.add_argument("--only", help="run only cases whose label contains this substring")
    ap.add_argument("--ref-only", action="store_true",
                    help="skip the zerobas side (oracle-lock only)")
    args = ap.parse_args()

    cases = [c for c in CASES if not args.only or args.only in c.label]
    if not cases:
        print(f"no cases match --only {args.only!r}")
        return 1

    ok = True

    print(f"--- reference oracle lock ({args.machine}, §2 contract) ---")
    ref_captured = {}
    for c in cases:
        got = measure(args.machine, c, timeout=180)
        ref_captured[c.label] = got
        good = got == c.expect
        ok = ok and good
        print(f"{'PASS' if good else 'FAIL':5} {c.label:12} got={got!r} want={c.expect!r}")

    if not args.ref_only:
        print(f"\n--- zerobas == reference ({args.zb_machine}) ---")
        for c in cases:
            zb = measure(args.zb_machine, c, timeout=140)
            ref = ref_captured.get(c.label)
            good = ref is not None and zb is not None and zb == ref
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} {c.label:12} zb={zb!r} ref={ref!r}")

    print("\nALL PASS -- reference matches §2, zerobas matches reference" if ok
          else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
