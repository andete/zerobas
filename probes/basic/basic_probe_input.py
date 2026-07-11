#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Oracle + differential probe -- console INPUT / LINE INPUT (input slice S3).

Console INPUT / LINE INPUT, per docs/spec-basic-input.md. Like basic_probe_inkey.py
this DRIVES THE KEYBOARD, but INPUT adds a genuinely new harness wrinkle (spec §6):
the program is typed and RUN first, and the INPUT *response* is a SEPARATE deliberate
keystroke burst delivered AFTER the prompt appears -- not batched with the program.
read_line blocks until Enter, so (as with the INKEY$ poll loop) the exact instant a
response lands is not timing-critical, only its ORDER after RUN; a re-prompt (?redo)
case simply queues a second response after the first.

Two halves, modelled on basic_probe_inkey.py:

1. REFERENCE ORACLE (black-box, no disassembly). Runs each case on the real Philips
   VG-8020's built-in MSX-BASIC (no cartridge) and asserts the reference's own screen
   output matches the spec §1 contract (numeric field -> the PRINTed integer; string
   var -> the raw field; multi-var comma split; LINE INPUT keeps commas/spaces; a bad
   numeric field or too-many values re-prompts/continues to the corrected value).
   Expected values are DERIVED from the contract.

2. ZEROBAS DIFFERENTIAL. Runs the IDENTICAL case on the repack machine
   (C-BIOS_MSX1_EU_REPACK_DISK -- console INPUT is repack-only) and asserts zerobas's
   result equals the reference's. The ?redo / ?extra *wording* differs (zerobas's own
   lowercase "?redo from start" / "?extra ignored"; spec D-2), so those cases assert
   the same FINAL VALUE (both machines re-prompt / continue to it), not the message --
   the same own-wording divergence handled by the compare / mid-stmt probes.

Each case prints its result inside a `<...>` bracket via a program line PRINTed after
the INPUT, so the result is the LAST bracket in the top-down-scrolling screen dump
(the echoed source line carries the same delimiters earlier / higher). This is the
extract_bracket trick from basic_probe_str_fn / basic_probe_inkey.

Clean-room: this only *observes* black-box behaviour (type a program, type a response,
read the screen). The reference ROM is never read as code. See CONTRIBUTING.md.

    python3 probes/basic/basic_probe_input.py
    python3 probes/basic/basic_probe_input.py --ref-only     # oracle-lock only
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from collections import namedtuple

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OMSX_RUN = os.path.join(REPO, "probes", "lib", "omsx_run.py")

REF_MACHINE = "Philips_VG_8020"    # reference: built-in MSX-BASIC, no cartridge
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
COLS, ROWS = 40, 24
NLEN = COLS * ROWS


def _capture(cmd_tail, timeout):
    """Run omsx_run with the given tail args + a VRAM dump; return the SCREEN 0
    name table as one raw, row-major string of length NLEN (None on failure)."""
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="input_cap_")
    os.close(out_fd)
    cmd = ([sys.executable, OMSX_RUN] + cmd_tail
           + ["--mem", f"VRAM:0x0000:{NLEN}", "--out", out_path, "--timeout", str(timeout)])
    subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cap = ""
    if os.path.exists(out_path):
        with open(out_path) as f:
            cap = f.read()
        os.unlink(out_path)
    m = re.search(rf"mem\.VRAM:0x0000:{NLEN}=([0-9a-f]+)", cap)
    if not m:
        return None
    data = bytes.fromhex(m.group(1))
    return "".join(chr(b) if 32 <= b < 127 else " " for b in data)


def run_prog(machine, prog_lines, responses, timeout=200):
    """Type each program line (each followed by a separately-timed Enter), RUN, then
    deliver each INPUT `response` (Enter-terminated) as its own keystroke burst AFTER
    RUN starts. Events are spaced ~3 emulated-seconds apart -- the real-speed
    reference needs the gap so its keyboard scan finishes a line before the Enter (a
    tighter gap fires Enter mid-type and garbles the line). Because read_line blocks
    on Enter, a response's arrival time need only be after the prompt appears -- not
    synchronised between machines -- and a second response naturally waits for the
    re-prompt."""
    tail = ["--machine", machine]
    t = 8.0
    for line in prog_lines:
        tail += ["--type", line, "--type-delay", f"{t}"]; t += 3
        tail += ["--type", "\r", "--type-delay", f"{t}"]; t += 3
    tail += ["--type", "RUN", "--type-delay", f"{t}"]; t += 3
    tail += ["--type", "\r", "--type-delay", f"{t}"]; t += 3
    for resp in responses:
        tail += ["--type", resp, "--type-delay", f"{t}"]; t += 3
        tail += ["--type", "\r", "--type-delay", f"{t}"]; t += 3
    tail += ["--time", f"{t + 4}"]
    return _capture(tail, timeout)


def extract_bracket(raw):
    """The content of the LAST non-nested `<...>` pair. The echoed source line carries
    the same delimiters earlier / higher on the top-down-scrolling screen, so the
    result -- PRINTed later, lower down -- is the last match in row-major order."""
    if raw is None:
        return None
    matches = re.findall(r"<([^<>]*)>", raw)
    return matches[-1] if matches else None


# (label, prog_lines, responses, expect) -- `expect` is the spec-derived <...> content.
# Numeric PRINT renders a positive int as " N " (leading sign space + trailing space)
# and a negative as "-N "; a multi-var numeric PRINT concatenates those. Strings print
# verbatim. Both machines share this PRINT format (locked by the string slices), so the
# differential holds; the reference oracle half checks these spec-derived values.
Case = namedtuple("Case", "label prog responses expect")

CASES = [
    # numeric field -> the parsed integer, PRINTed as " 42 "
    Case("numeric",
         ['10 INPUT A', '20 PRINT"<";A;">"'], ["42"], " 42 "),
    # negative numeric field
    Case("numeric.neg",
         ['10 INPUT A', '20 PRINT"<";A;">"'], ["-7"], "-7 "),
    # string var -> the raw field bytes
    Case("string",
         ['10 INPUT A$', '20 PRINT"<";A$;">"'], ["HELLO"], "HELLO"),
    # two vars, comma-split response -> " 3 " + " 4 "
    Case("multi",
         ['10 INPUT N,M', '20 PRINT"<";N;M;">"'], ["3,4"], " 3  4 "),
    # LINE INPUT keeps the commas AND the leading space (whole line, one string var)
    Case("line",
         ['10 LINE INPUT A$', '20 PRINT"<";A$;">"'], [" A,B C"], " A,B C"),
    # prompt ';' -> the quoted prompt then "? "; string field keeps the response
    Case("prompt.semi",
         ['10 INPUT"N";A$', '20 PRINT"<";A$;">"'], ["ZZ"], "ZZ"),
    # ?redo: a bad numeric field re-prompts; the corrected value is what lands.
    # Wording differs (D-2) -- assert the FINAL value matches on both machines.
    Case("redo.bad",
         ['10 INPUT A', '20 PRINT"<";A;">"'], ["X", "5"], " 5 "),
    # ?extra: too many values -> keep the matched one, continue (wording differs).
    Case("extra.toomany",
         ['10 INPUT A', '20 PRINT"<";A;">"'], ["5,9"], " 5 "),
]


def measure(machine, c, timeout):
    return extract_bracket(run_prog(machine, c.prog, c.responses, timeout=timeout))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=REF_MACHINE,
                    help="reference machine (built-in BASIC oracle)")
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE,
                    help="zerobas repack machine (console INPUT is repack-only)")
    ap.add_argument("--only", help="run only cases whose label contains this substring")
    ap.add_argument("--ref-only", action="store_true",
                    help="skip the zerobas side (oracle-lock only)")
    args = ap.parse_args()

    cases = [c for c in CASES if not args.only or args.only in c.label]
    if not cases:
        print(f"no cases match --only {args.only!r}")
        return 1

    ok = True

    print(f"--- reference oracle lock ({args.machine}, §1 contract) ---")
    ref_captured = {}
    for c in cases:
        got = measure(args.machine, c, timeout=220)
        ref_captured[c.label] = got
        good = got == c.expect
        ok = ok and good
        print(f"{'PASS' if good else 'FAIL':5} {c.label:14} got={got!r} want={c.expect!r}")

    if not args.ref_only:
        print(f"\n--- zerobas == reference ({args.zb_machine}) ---")
        for c in cases:
            zb = measure(args.zb_machine, c, timeout=200)
            ref = ref_captured.get(c.label)
            good = ref is not None and zb is not None and zb == ref
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} {c.label:14} zb={zb!r} ref={ref!r}")

    print("\nALL PASS -- reference matches §1, zerobas matches reference" if ok
          else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
