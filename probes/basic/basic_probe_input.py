#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Oracle + differential probe -- console INPUT / LINE INPUT (input slice S3).

Console INPUT / LINE INPUT, per docs/spec-basic-input.md. Delivered through the
typing-free KEYBUF-injection REPL driver (probes/lib/omsx_repl.py), like the
string/float acceptance halves -- NOT the old omsx_run matrix-typing path, whose
per-char Enter could land mid-line and garble a program. Each case is a small
stored program typed as numbered direct-mode lines, then `RUN`, then the INPUT
*response(s)* injected as trailing raw lines AFTER RUN (spec §6). This is exactly
the basic_probe_inkey.py shape: read_line blocks until Enter, so a response's
exact arrival instant is not timing-critical -- only its ORDER after RUN -- and a
re-prompt (?redo) case simply queues a second response line after the first, which
lands on the re-prompt while the read is still blocked. The KEYBUF injection means
no matrix scan, so the old "Enter fires mid-type" garble mode is gone.

Two halves, modelled on basic_probe_str_cmp.py:

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

Batched by default: all cases share ONE boot per machine, `("NEW","CLS")` reset
between cases (NEW clears the case's INPUT variables, CLS the screen so each capture
holds only its own case). Console INPUT completes and returns to the prompt between
cases, so no case wedges the shared boot; still, `--boot-per-case` isolates every
case in its own boot to rule out inter-case leakage / a response racing the next
case's NEW (the guardrail from docs/spec-acceptance-batching.md).

Clean-room: this only *observes* black-box behaviour (type a program, type a response,
read the screen). The reference ROM is never read as code. See CONTRIBUTING.md.

    python3 probes/basic/basic_probe_input.py
    python3 probes/basic/basic_probe_input.py --ref-only        # oracle-lock only
    python3 probes/basic/basic_probe_input.py --boot-per-case   # isolation escape hatch
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


def spec(c):
    """The omsx_repl direct-mode case for `c`: the numbered program lines, `RUN`,
    then each INPUT response as a trailing raw line injected after RUN. The line
    editor consumes the program lines + RUN (and their CRs) in order, so by the
    time a response is injected RUN is executing and the read is blocked; the
    response's CR-terminated line lands in KEYBUF and CHGET hands it to INPUT."""
    return ("direct", list(c.prog) + ["RUN"] + list(c.responses))


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
    ap.add_argument("--boot-per-case", dest="boot_per_case", action="store_true",
                    help="isolate each case in its own boot instead of the default "
                         "single-boot batch (to rule out inter-case leakage / a "
                         "response racing the next case's NEW)")
    args = ap.parse_args()

    cases = [c for c in CASES if not args.only or args.only in c.label]
    if not cases:
        print(f"no cases match --only {args.only!r}")
        return 1

    ok = True
    batch = not args.boot_per_case

    # One boot per machine drives the whole matrix; NEW clears each case's INPUT
    # variables, CLS the screen (so each capture holds only its own case's output).
    specs = [spec(c) for c in cases]
    ref_raws = omsx_repl.run_cases(args.machine, specs, batch=batch, reset=("NEW", "CLS"))
    zb_raws = (omsx_repl.run_cases(args.zb_machine, specs, batch=batch, reset=("NEW", "CLS"))
               if not args.ref_only else [None] * len(specs))

    print(f"--- reference oracle lock ({args.machine}, §1 contract) ---")
    ref_captured = {}
    for c, ref_raw in zip(cases, ref_raws):
        got = extract_bracket(ref_raw)
        ref_captured[c.label] = got
        good = got == c.expect
        ok = ok and good
        print(f"{'PASS' if good else 'FAIL':5} {c.label:14} got={got!r} want={c.expect!r}")

    if not args.ref_only:
        print(f"\n--- zerobas == reference ({args.zb_machine}) ---")
        for c, zb_raw in zip(cases, zb_raws):
            zb = extract_bracket(zb_raw)
            ref = ref_captured.get(c.label)
            good = ref is not None and zb is not None and zb == ref
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} {c.label:14} zb={zb!r} ref={ref!r}")

    print("\nALL PASS -- reference matches §1, zerobas matches reference" if ok
          else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
